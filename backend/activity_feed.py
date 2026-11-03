"""Bounded paper activity acquisition and immutable evidence publication."""
import asyncio
import codecs
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import uuid

import httpx

from .accounting_snapshot import bound_epoch, commit_snapshot, valid_epoch
from .activity_projection import balances_match, canonical, digest, instant, input_digest, ledger_source, load_mapping, project
from .config import SYMBOLS
from .executor_ownership import account_identity
from .store import utcnow
from .evidence_codec import pack_bytes, pack_text, reference_text, reference_bytes
from .activity_diagnostics import (ACTIVE, AcquisitionTrace, DiagnosticStorageError,
                                   classify, failure_kind, ledger_write, request_span, trace_extensions)

ATTEMPT_SECONDS, STREAM_SECONDS, IDLE_SECONDS = 60, 30, 8
MAX_EVENTS, MAX_BYTES, MAX_FRAME = 10000, 8*1024*1024, 64*1024
_SSE_LINE_END = re.compile(r'[\r\n]')
SCHEMA = '''
CREATE TABLE IF NOT EXISTS evidence_blobs(sha256 BLOB PRIMARY KEY,payload BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS activity_batches(id TEXT,phase TEXT,account TEXT,at TEXT,payload TEXT,PRIMARY KEY(id,phase));
CREATE TABLE IF NOT EXISTS activity_events(batch TEXT,ordinal INTEGER,account TEXT,event_id TEXT,ref_id TEXT,type TEXT,at TEXT,sha256 TEXT,payload TEXT,frame BLOB,PRIMARY KEY(batch,ordinal));
CREATE INDEX IF NOT EXISTS activity_delivery ON activity_events(account,event_id);
CREATE INDEX IF NOT EXISTS activity_identity ON activity_events(account,type,ref_id);
CREATE TABLE IF NOT EXISTS activity_associations(sha256 TEXT PRIMARY KEY,account TEXT,at TEXT,payload TEXT);
CREATE TABLE IF NOT EXISTS activity_conflicts(id TEXT PRIMARY KEY,account TEXT,at TEXT,payload TEXT);
CREATE TABLE IF NOT EXISTS activity_projections(id TEXT PRIMARY KEY,account TEXT,at TEXT,input_hash TEXT,payload TEXT);
'''


class FeedError(ValueError):
    pass


class SSEParser:
    """Incremental SSE framing; raw acquisition bytes are retained separately."""
    def __init__(self):
        self.decoder = codecs.getincrementaldecoder('utf-8-sig')('strict')
        self.pending, self.lines, self.frame_size, self.count, self.size = '', [], 0, 0, 0
        self.frames = []

    def feed(self, chunk, *, final=False):
        self.size += len(chunk)
        if self.size > MAX_BYTES:
            raise FeedError('Activity byte budget exceeded')
        self.pending += self.decoder.decode(chunk, final=final)
        # Consume a terminated line before validation, including on failure.
        consumed = 0
        try:
            while match := _SSE_LINE_END.search(self.pending, consumed):
                index = match.start()
                if self.pending[index] == '\r' and index+1 == len(self.pending) and not final:
                    break
                line = self.pending[consumed:index]
                width = 2 if (self.pending[index] == '\r' and index+1 < len(self.pending)
                              and self.pending[index+1] == '\n') else 1
                consumed = index+width
                self.frame_size += len(line.encode())+width
                if self.frame_size > MAX_FRAME:
                    raise FeedError('Activity frame budget exceeded')
                if line:
                    self.lines.append(line)
                else:
                    self._frame()
        finally:
            self.pending = self.pending[consumed:]
        if len(self.pending.encode())+self.frame_size > MAX_FRAME:
            raise FeedError('Activity frame budget exceeded')
        if final and (self.pending or self.lines):
            raise FeedError('Unfinished activity frame')

    def _frame(self):
        lines, self.lines, self.frame_size = self.lines, [], 0
        data = []
        for line in lines:
            if line.startswith(':'):
                # Unknown notices are not evidence of a complete finite replay.
                comment = line[1:].strip().lower()
                if comment and comment not in ('heartbeat', 'keepalive', 'keep-alive', 'ping', 'welcome to the alpaca events'):
                    raise FeedError('Unverified provider activity notice')
            elif line.startswith('data:'):
                value = line[5:]
                data.append(value[1:] if value.startswith(' ') else value)
            elif not line.startswith(('id:', 'event:', 'retry:')):
                raise FeedError('Unsupported SSE field')
        if not data:
            return
        self.count += 1
        if self.count > MAX_EVENTS:
            raise FeedError('Activity event budget exceeded')
        try:
            event = json.loads('\n'.join(data), parse_constant=lambda _: (_ for _ in ()).throw(FeedError('Nonfinite JSON')),
                               object_pairs_hook=unique_object)
            if not isinstance(event, dict):
                raise FeedError('Activity object required')
            canonical(event)
        except (ValueError, TypeError) as exc:
            raise FeedError('Malformed activity JSON') from exc
        self.frames.append((event, ('\n'.join(lines)+'\n\n').encode()))


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise FeedError('Duplicate JSON key')
        result[key] = value
    return result


def parse_sse(raw):
    parser = SSEParser()
    parser.feed(raw, final=True)
    return [event for event, _ in parser.frames]


async def stream_activities(broker, since, until):
    with request_span('GET', '/v2beta1/events/activities') as diagnostic:
        return await _stream_activities(broker, since, until, diagnostic)


async def _stream_activities(broker, since, until, diagnostic):
    """Use the adapter's authentication, process boundary and request budget."""
    from .broker import BrokerFailure
    import time
    instant(since); instant(until)
    if instant(since) >= instant(until):
        raise FeedError('Invalid activity interval')
    broker.account_lease.check_process()
    if not broker.settings.configured:
        diagnostic['denial'] = 'configuration'
        raise BrokerFailure('Paper credentials unavailable', sent=False)
    if time.monotonic() < broker.cooldown['trading']:
        diagnostic['denial'] = 'local-cooldown'
        raise BrokerFailure('Provider cooldown active', 429, sent=False)
    try:
        broker.trading.take(False)
    except BrokerFailure:
        diagnostic['denial'] = 'local-budget'
        raise
    parser, raw = SSEParser(), bytearray()
    result = {'events': [], 'raw': b'', 'complete': False, 'error': None, 'since': since, 'until': until}
    try:
        async with asyncio.timeout(STREAM_SECONDS):
            from .config import PAPER_URL
            diagnostic['dispatch'] = 'started-outcome-unknown'
            async with broker.http.stream('GET', PAPER_URL+'/v2beta1/events/activities',
                                          params={'since': since, 'until': until}, timeout=IDLE_SECONDS,
                                          extensions=trace_extensions(diagnostic)) as response:
                diagnostic.update(dispatch='response-received', http_status=response.status_code)
                ledger_write(broker.store.event, 'activity_request',
                             {'method': 'GET', 'status': response.status_code, 'at': utcnow()})
                if response.status_code == 429:
                    try: delay = float(response.headers.get('retry-after', '60'))
                    except ValueError: delay = 60
                    broker.cooldown['trading'] = time.monotonic()+min(300, max(1, delay))
                if response.status_code != 200 or response.headers.get('content-type', '').split(';')[0].strip() != 'text/event-stream':
                    raise FeedError('Activity stream response unavailable')
                async for chunk in response.aiter_bytes():
                    # Retain at most the explicit byte budget; overflow is an error.
                    raw.extend(chunk[:max(0, MAX_BYTES-len(raw))])
                    parser.feed(chunk)
                parser.feed(b'', final=True)
                result['complete'] = True
    except (httpx.HTTPError, ValueError, TimeoutError, UnicodeError) as exc:
        classify(diagnostic, exc)
        result['error'] = 'activity_stream_incomplete'
    finally:
        result.update(events=[e for e, _ in parser.frames], raw=bytes(raw), received_at=utcnow())
        # Cancellation is re-raised by asyncio, but its evidence survives.
        broker._last_activity_stream = result
    return result


def start_batch(store, account, since, until, *, batch_id=None, lifecycle=None):
    batch = batch_id or uuid.uuid4().hex
    ledger_write(store.db.execute, 'INSERT INTO activity_batches VALUES(?,?,?,?,?)',
                 (batch, 'start', account, utcnow(), canonical({'since': since, 'until': until})),
                 lifecycle=lifecycle)
    if lifecycle:
        lifecycle.batch_started = True
    return batch


def activity_identifier(value):
    return value if isinstance(value, str) and value else None


def retain_batch(store, batch, account, result):
    """Commit even rejected records before publishing or raising their failure."""
    at = result.get('imported_at') or result.get('received_at') or utcnow()
    parser = SSEParser()
    try: parser.feed(result.get('raw', b''), final=True)
    except (ValueError, UnicodeError): pass
    frames = parser.frames
    with store.transaction():
        for index, event in enumerate(result.get('events', [])):
            payload, sha = canonical(event), digest(event)
            delivery, kind, ref = (activity_identifier(event.get(k)) for k in ('event_id', 'activity_type', 'ref_id'))
            if None in (delivery, kind, ref):
                result.update(complete=False, error='invalid_activity_identity')
            # Keep both identity checks indexed as acquisition history grows.
            prior = store.rows('SELECT sha256 FROM activity_events WHERE account=? AND event_id=? '
                               'UNION SELECT sha256 FROM activity_events WHERE account=? AND type=? AND ref_id=?',
                               (account, delivery, account, kind, ref))
            for old in prior:
                if old['sha256'] != sha:
                    conflict = {'prior_sha256': old['sha256'], 'new_sha256': sha, 'ref_id': event.get('ref_id')}
                    store.db.execute('INSERT OR IGNORE INTO activity_conflicts VALUES(?,?,?,?)',
                                     (digest(conflict), account, at, canonical(conflict)))
            frame = frames[index][1] if index < len(frames) else payload.encode()
            try:
                body, retained_frame = reference_text(store.db, payload), reference_bytes(store.db, frame)
            except ValueError:
                # Preserve this delivery without replacing corrupt shared history.
                result.update(complete=False, evidence_integrity_error=True)
                result['error'] = result.get('error') or 'activity_evidence_integrity_error'
                body, retained_frame = pack_text(payload), pack_bytes(frame)
            store.db.execute('INSERT INTO activity_events VALUES(?,?,?,?,?,?,?,?,?,?)',
                             (batch, index, account, delivery, ref, kind, at, sha, body, retained_frame))
        receipt = {key: value for key, value in result.items() if key not in ('events', 'raw')}
        receipt['raw_hex'] = result.get('raw', b'').hex()
        receipt['raw_sha256'] = hashlib.sha256(result.get('raw', b'')).hexdigest()
        store.db.execute('INSERT INTO activity_batches VALUES(?,?,?,?,?)', (batch, 'outcome', account, at, pack_text(canonical(receipt))))


async def collect_batch(broker, store, *, critical=True, refresh_snapshot=False, batch_id=None, lifecycle=None):
    if refresh_snapshot and (broker.settings.enable_orders or broker.settings.mode != 'alpaca'):
        raise FeedError('Accounting snapshot refresh requires orders-off paper settings')
    binding = store.get('account_binding')
    if not binding:
        raise FeedError('Verified account binding required')
    earliest = store.rows("SELECT MIN(json_extract(payload,'$.at')) at FROM fills")[0]['at']
    start = datetime.now(timezone.utc)-timedelta(days=3)
    if earliest:
        start = min(start, datetime.fromisoformat(earliest.replace('Z', '+00:00'))-timedelta(days=1))
    since, until = start.isoformat(), utcnow()
    batch = start_batch(store, binding, since, until, batch_id=batch_id, lifecycle=lifecycle)
    broker._last_activity_stream = None
    trace = AcquisitionTrace(batch, lifecycle)
    acquisition_epoch = None
    token = ACTIVE.set(trace)
    result = {'complete': False, 'events': [], 'raw': b'', 'since': since, 'until': until,
              'account_id': binding, 'received_at': utcnow(), 'error': 'activity_acquisition_incomplete',
              'request_attempts': 0}
    cancelled = False
    try:
        async with asyncio.timeout(ATTEMPT_SECONDS):
            if refresh_snapshot:
                trace.stage = 'initial-snapshot'
                result['request_attempts'] += 3
                snapshot = await broker.snapshot(critical=critical)
                try:
                    with store.transaction():
                        committed_epoch = commit_snapshot(store, snapshot)
                except (sqlite3.Error, OSError):
                    # S1 snapshot rollback remains an ordinary incomplete attempt.
                    trace.failure = 'storage'
                    raise
                acquisition_epoch = committed_epoch
            trace.stage = 'identity-before'
            result['request_attempts'] += 1
            before = await broker.request('GET', '/v2/account', critical=critical)
            result['before'] = before
            if account_identity(before) != binding:
                raise FeedError('Paper account identity changed')
            if before.get('created_at'):
                created = datetime.fromisoformat(before['created_at'].replace('Z', '+00:00'))
                since = min(start, created).isoformat()
            with store.lock:
                until = utcnow()
                if not refresh_snapshot:
                    acquisition_epoch = bound_epoch(store, store.get('account_snapshot'))
            trace.stage = 'activity-stream'
            result['request_attempts'] += 1
            stream = await broker.stream_activities(since, until)
            result.update(stream, account_id=binding)
            trace.stage = 'identity-after'
            result['request_attempts'] += 1
            after = await broker.request('GET', '/v2/account', critical=critical)
            result['after'] = after
            if account_identity(after) != binding:
                raise FeedError('Paper account identity changed')
            trace.stage = 'positions-after'
            result['request_attempts'] += 1
            result['after_positions'] = await broker.request('GET', '/v2/positions', critical=critical)
            if not isinstance(result['after_positions'], list):
                raise FeedError('Post-stream positions unavailable')
            if any(e.get('account_id', binding) != binding for e in result['events']):
                raise FeedError('Activity belongs to another account')
    except DiagnosticStorageError:
        trace.failure = 'storage'
        result.update(complete=False, error='activity_acquisition_incomplete')
        raise
    except asyncio.CancelledError as exc:
        cancelled = True
        trace.failure = trace.failure or failure_kind(exc)
        result.update(getattr(broker, '_last_activity_stream', None) or {}, complete=False, error='activity_acquisition_cancelled')
        raise
    except Exception as exc:
        trace.failure = trace.failure or failure_kind(exc)
        result.update(getattr(broker, '_last_activity_stream', None) or {}, complete=False, error='activity_acquisition_incomplete')
    finally:
        result['received_at'] = utcnow()
        result['snapshot_epoch'] = acquisition_epoch
        result['diagnostics'] = trace.view()
        ACTIVE.reset(token)
        if lifecycle is None or not lifecycle.observation.storage_failed:
            if lifecycle:
                lifecycle.mark('retention_start')
            try:
                ledger_write(retain_batch, store, batch, binding, result, lifecycle=lifecycle)
            except DiagnosticStorageError:
                if not cancelled:
                    raise
            else:
                if lifecycle:
                    lifecycle.outcome_retained = True
                    lifecycle.mark('retention_end')
                broker._last_activity_acquisition = result
    return batch, result


class AccountingRead:
    """Private evidence for one locked read, never an authorization result."""

    def __init__(self, store, cutoff):
        self.store, self.cutoff = store, cutoff
        self.source = ledger_source(store)
        self.binding = self.source['state']['account_binding']
        self.input_sha256 = input_digest(self.source)
        self.batches = {}

    def check(self, store, cutoff=None):
        if self.store is not store or (cutoff is not None and instant(cutoff) != instant(self.cutoff)):
            raise FeedError('Accounting read context differs or has ended')

    def close(self):
        self.batches.clear()
        self.source = None
        self.store = None


@contextmanager
def accounting_read(store, *, cutoff=None):
    """The context cannot outlive the enclosing Store lock."""
    with store.lock:
        context = AccountingRead(store, cutoff or utcnow())
        try:
            yield context
        finally:
            context.close()


def batch_events(store, batch, *, read_context=None):
    if read_context is None:
        return _validate_batch(store, batch)
    read_context.check(store)
    if not isinstance(batch, str):
        raise FeedError('Activity batch identity required')
    key = (read_context.binding, batch)
    if key not in read_context.batches:
        try:
            read_context.batches[key] = _validate_batch(store, batch)
        except (ValueError, TypeError, KeyError) as exc:
            read_context.batches[key] = exc
    result = read_context.batches[key]
    if isinstance(result, Exception):
        raise result
    # Callers may add issues; none receives the retained mutable evidence.
    return deepcopy(result)


def _validate_batch(store, batch):
    """Validate the selected outcome and every delivery against its raw stream."""
    binding = store.get('account_binding')
    outcomes = store.rows("SELECT payload FROM activity_batches WHERE id=? AND phase='outcome' AND account=?", (batch, binding))
    if not outcomes:
        raise FeedError('Completed acquisition required')
    coverage = json.loads(outcomes[0]['payload'])
    if not isinstance(coverage, dict):
        raise FeedError('Activity outcome object required')
    rows = store.rows('SELECT ordinal,account,event_id,ref_id,type,payload,frame,sha256 FROM activity_events WHERE batch=? ORDER BY ordinal', (batch,))
    events = [json.loads(row['payload']) for row in rows]
    issues = ['incomplete_activity_coverage'] if coverage.get('complete') is not True else []
    try:
        if coverage.get('account_id') != binding or len(coverage['raw_hex']) > 2*MAX_BYTES:
            raise FeedError('Activity outcome binding or byte budget differs')
        raw = bytes.fromhex(coverage['raw_hex'])
        if hashlib.sha256(raw).hexdigest() != coverage['raw_sha256']:
            raise FeedError('Retained activity stream differs from its source hash')
        parser = SSEParser();parser.feed(raw, final=True)
        if len(rows) != len(parser.frames):
            raise FeedError('Retained activity delivery sequence is incomplete')
        for index, (row, event, (original, frame)) in enumerate(zip(rows, events, parser.frames)):
            if (not isinstance(event, dict) or row['ordinal'] != index or row['account'] != binding
                    or any(row[column] != activity_identifier(event.get(key)) for column, key in
                           (('event_id', 'event_id'), ('ref_id', 'ref_id'), ('type', 'activity_type')))
                    or digest(event) != row['sha256'] or digest(original) != row['sha256'] or row['frame'] != frame):
                raise FeedError('Retained activity differs from its source delivery')
    except (ValueError, TypeError, KeyError):
        issues.append('activity_evidence_integrity_error')
    return events, coverage, issues


def publish_projection(store, batch, mapping, *, now=None):
    now = now or utcnow()
    mapping = load_mapping(mapping)
    with store.transaction():
        source = ledger_source(store)
        binding = source['state']['account_binding']
        events, coverage, integrity_issues = batch_events(store, batch)
        if coverage.get('complete'):
            result = project(source, events, mapping, coverage, knowledge_cutoff=now)
        else:
            result = {'effects': [], 'issues': ['incomplete_activity_coverage'], 'net_books': {},
                      'by_symbol': {s: {'passed': False, 'status': 'unverified'} for s in SYMBOLS},
                      'cash_reconciliation': {'status': 'unknown', 'cash': None},
                      'mapping_sha256': digest(mapping), 'input_sha256': input_digest(source),
                      'association_count': 0, 'activity_count': len({e.get('ref_id') for e in events if isinstance(e.get('ref_id'), str)}),
                      'fixture': mapping['kind'] != 'reviewed-provider'}
        result['issues'].extend(integrity_issues)
        if coverage.get('error') == 'invalid_activity_identity':
            result['issues'].append('invalid_activity_evidence')
            result['activity_count'] = 0
        if not coverage.get('historical_import'):
            try:
                after = {'account': coverage['after'], 'positions': coverage['after_positions']}
                if not balances_match(source['state']['account_snapshot'], after):
                    result['issues'].append('post_stream_balances_changed')
            except (KeyError, TypeError, ValueError, AttributeError):
                result['issues'].append('post_stream_balances_unavailable')
        # Any omission from previously retained covered history blocks the scan.
        refs = {activity_identifier(e.get('ref_id')) for e in events}
        refs.discard(None)
        for prior in (store.rows("SELECT DISTINCT ref_id,payload FROM activity_events WHERE account=? AND batch<>?", (binding, batch)) if coverage.get('complete') else []):
            try: covered = instant(coverage['since']) <= instant(json.loads(prior['payload'])['at']) <= instant(coverage['until'])
            except (ValueError, KeyError): covered = True
            if covered and prior['ref_id'] not in refs:
                result['issues'].append('activity_disappeared_from_replay')
        if store.rows('SELECT id FROM activity_conflicts WHERE account=?', (binding,)):
            result['issues'].append('persistent_activity_conflict')
        if result['issues']:
            result['effects'] = []
            result['cash_reconciliation'].update(status='unknown', cash=None)
            for entry in result['by_symbol'].values(): entry.update(passed=False, status='unverified')
        sha = digest(mapping)
        store.db.execute('INSERT OR IGNORE INTO activity_associations VALUES(?,?,?,?)', (sha, binding, now, canonical(mapping)))
        result.update(batch=batch, published_at=now, coverage={k: coverage.get(k) for k in ('since', 'until', 'received_at', 'complete')})
        result['coverage']['snapshot_epoch'] = coverage.get('snapshot_epoch') if not coverage.get('historical_import') else None
        projection_id = uuid.uuid4().hex
        store.db.execute('INSERT INTO activity_projections VALUES(?,?,?,?,?)',
                         (projection_id, binding, now, result['input_sha256'], pack_text(canonical(result))))
        if not result['issues'] and not result['fixture']:
            store.put('activity_last_covered_projection', {'id': projection_id, 'sha256': digest(result)})
        return result


def read_projection(store, *, cutoff=None, diagnostics=None, read_context=None):
    """Read-only compatibility with ledgers predating the new tables."""
    if read_context is not None:
        read_context.check(store, cutoff)
    cutoff = cutoff or (read_context.cutoff if read_context is not None else utcnow())
    binding = store.get('account_binding')
    attempts = (store.rows('SELECT id,phase,at FROM activity_batches WHERE account=? ORDER BY rowid DESC', (binding,))
                if store.rows("SELECT name FROM sqlite_master WHERE name='activity_batches'") else [])
    latest = next((a for a in attempts if instant(a['at']) <= instant(cutoff)), None)
    if diagnostics is not None:
        diagnostics.update(latest_attempt=({**latest, 'status': 'pending' if latest['phase'] == 'start' else 'unpublished'}
                                           if latest else None))
    if not store.rows("SELECT name FROM sqlite_master WHERE name='activity_projections'"):
        return None
    rows = store.rows('SELECT rowid,at FROM activity_projections WHERE account=? ORDER BY rowid DESC', (binding,))
    for row in rows:
        if instant(row['at']) <= instant(cutoff):
            result = json.loads(store.rows('SELECT payload FROM activity_projections WHERE rowid=?', (row['rowid'],))[0]['payload'])
            # Decode and validate only the acquisition selected by the cutoff.
            try:
                retained, _, integrity_issues = batch_events(store, result['batch'], read_context=read_context)
                if not integrity_issues and len({event['ref_id'] for event in retained}) != result.get('activity_count'):
                    integrity_issues = ['activity_evidence_integrity_error']
                result['issues'].extend(integrity_issues)
            except (ValueError, TypeError, KeyError):
                result['issues'].append('activity_evidence_integrity_error')
            # A retained attempt cannot disappear behind an older publication.
            if diagnostics is not None and latest and latest['phase'] != 'start' and latest['id'] == result['batch']:
                diagnostics['latest_attempt']['status'] = 'complete' if result['coverage']['complete'] else 'incomplete'
            if latest and latest['id'] != result['batch']:
                result['issues'].append('new_activity_attempt_pending')
            conflicts = store.rows('SELECT at FROM activity_conflicts WHERE account=?', (binding,))
            if any(instant(c['at']) <= instant(cutoff) for c in conflicts):
                result['issues'].append('persistent_activity_conflict')
            if result['issues']:
                result['issues'] = sorted(set(result['issues']))
                result['effects'] = []
                result['cash_reconciliation'].update(status='unknown', cash=None)
                for entry in result['by_symbol'].values(): entry.update(passed=False, status='unverified')
            return result
    return None


def historical_checkpoint(store, *, cutoff, read_context=None):
    if read_context is not None:
        read_context.check(store, cutoff)
    try:
        pointer = store.get('activity_last_covered_projection')
        if not (isinstance(pointer, dict) and isinstance(pointer.get('id'), str) and isinstance(pointer.get('sha256'), str)):
            return None
        rows = store.rows('SELECT payload FROM activity_projections WHERE id=? AND account=?',
                          (pointer['id'], store.get('account_binding')))
        if not rows:
            return None
        result = json.loads(rows[0]['payload'])
        if result['issues'] or result['fixture'] or digest(result) != pointer['sha256'] or instant(result['published_at']) > instant(cutoff):
            return None
        _, _, issues = batch_events(store, result['batch'], read_context=read_context)
        if issues:
            return None
        return {**result['cash_reconciliation'], 'status': 'historical-only', 'current_authority': False, 'batch': result['batch'],
                'published_at': result['published_at'], 'coverage_until': result['coverage']['until'],
                'knowledge_cutoff': result['cash_reconciliation']['knowledge_cutoff']}
    except (ValueError, TypeError, KeyError):
        return None


def current_accounting(store, *, enabled=False, now=None, max_snapshot_age=30, read_context=None):
    if read_context is None:
        with accounting_read(store, cutoff=now) as local:
            return current_accounting(store, enabled=enabled, now=now,
                                      max_snapshot_age=max_snapshot_age, read_context=local)
    if read_context is not None:
        read_context.check(store, now)
    now = now or (read_context.cutoff if read_context is not None else utcnow())
    with store.lock:
        source = read_context.source if read_context is not None else ledger_source(store)
        diagnostics = {}
        reasons = []
        try:
            result = read_projection(store, cutoff=now, diagnostics=diagnostics, read_context=read_context)
        except (ValueError, TypeError, KeyError):
            result = None
            reasons.append('activity_evidence_integrity_error')
        # Current authority sees the latest retained attempt even after wall rollback.
        attempts = (store.rows('SELECT id,phase,at FROM activity_batches WHERE account=? ORDER BY rowid DESC LIMIT 1',
                               (store.get('account_binding'),))
                    if store.rows("SELECT name FROM sqlite_master WHERE name='activity_batches'") else [])
        latest = attempts[0] if attempts else None
        if latest:
            latest = {**latest, 'status': 'pending' if latest['phase'] == 'start' else 'unpublished'}
            if result and latest['id'] == result['batch'] and latest['phase'] == 'outcome':
                latest['status'] = 'complete' if result['coverage']['complete'] else 'incomplete'
            if not result or latest['id'] != result['batch']:
                reasons.append('new_activity_attempt_pending')
            try:
                if latest['phase'] not in {'start', 'outcome'} or instant(latest['at']) > instant(now):
                    reasons.append('activity_attempt_time_unavailable')
            except (ValueError, TypeError, KeyError):
                reasons.append('activity_attempt_time_unavailable')
        diagnostics['latest_attempt'] = latest
        epoch = bound_epoch(store, source['state'].get('account_snapshot'))
        if not enabled: reasons.append('activity_reader_disabled')
        if not result: reasons.append('activity_projection_unavailable')
        else:
            reasons.extend(result['issues'])
            if result['fixture']: reasons.append('fixture_evidence_only')
            acquired_epoch = result['coverage'].get('snapshot_epoch')
            if epoch is None: reasons.append('accounting_snapshot_epoch_unavailable')
            if not valid_epoch(acquired_epoch): reasons.append('activity_snapshot_epoch_unavailable')
            elif epoch is not None and epoch != acquired_epoch: reasons.append('accounting_snapshot_replaced')
            source_digest = read_context.input_sha256 if read_context is not None else input_digest(source)
            if source_digest != result['input_sha256']: reasons.append('accounting_inputs_changed')
            if not 0 <= instant(now)-instant(result['coverage']['received_at']) <= 90: reasons.append('activity_acquisition_stale')
            try:
                if not 0 <= instant(now)-instant(source['state']['account_snapshot']['at']) <= max_snapshot_age:
                    reasons.append('accounting_snapshot_stale')
                if instant(source['state']['account_snapshot']['at']) > instant(result['coverage']['until']):
                    reasons.append('accounting_snapshot_outside_coverage')
            except (ValueError, KeyError, TypeError): reasons.append('accounting_snapshot_unavailable')
        by_symbol = {s: {'passed': not reasons and result['by_symbol'].get(s, {}).get('passed', False),
                          'status': 'matched' if not reasons and result['by_symbol'].get(s, {}).get('passed') else 'unverified'} for s in SYMBOLS}
        latest = diagnostics.get('latest_attempt')
        evidence = {'snapshot_epoch': epoch,
                    'acquisition_epoch': result['coverage'].get('snapshot_epoch') if result else None,
                    'snapshot_at': (source['state'].get('account_snapshot') or {}).get('at'),
                    'coverage_until': result['coverage']['until'] if result else None,
                    'acquired_at': result['coverage']['received_at'] if result else None,
                    'published_at': result.get('published_at') if result else None,
                    'batch': result.get('batch') if result else None,
                    'input_sha256': result.get('input_sha256') if result else None,
                    'mapping_sha256': result.get('mapping_sha256') if result else None,
                    'latest_attempt': latest, 'historical_checkpoint': historical_checkpoint(
                        store, cutoff=now, read_context=read_context)}
        return {'accounting_evidence': evidence, 'accounting_by_symbol': by_symbol,
                'activity_coverage': {'status': 'current' if not reasons else 'incomplete', 'issues': sorted(set(reasons))},
                'association_summary': {'reviewed_records': result.get('association_count', 0) if result else 0},
                'cash_reconciliation': result['cash_reconciliation'] if result and not reasons else {'status': 'unknown', 'cash': None}}


def main():
    from .activity_validation import main as validate
    validate()


if __name__ == '__main__':
    main()
