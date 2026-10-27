"""Bounded paper activity acquisition and immutable evidence publication."""
import asyncio
import codecs
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import uuid

import httpx

from .activity_projection import balances_match, canonical, digest, instant, input_digest, ledger_source, load_mapping, project
from .config import SYMBOLS
from .executor_ownership import account_identity
from .store import utcnow

ATTEMPT_SECONDS, STREAM_SECONDS, IDLE_SECONDS = 60, 30, 8
MAX_EVENTS, MAX_BYTES, MAX_FRAME = 10000, 8*1024*1024, 64*1024
SCHEMA = '''
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
        # Process CR, LF and CRLF, including CRLF split across transport chunks.
        while True:
            import re
            match = re.search(r'[\r\n]', self.pending)
            if not match:
                break
            index = match.start()
            if self.pending[index:] == '\r' and not final:
                break
            line = self.pending[:index]
            width = 2 if self.pending[index:index+2] == '\r\n' else 1
            self.pending = self.pending[index+width:]
            self.frame_size += len(line.encode())+width
            if self.frame_size > MAX_FRAME:
                raise FeedError('Activity frame budget exceeded')
            if line:
                self.lines.append(line)
            else:
                self._frame()
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
    """Use the adapter's authentication, process boundary and request budget."""
    from .broker import BrokerFailure
    import time
    instant(since); instant(until)
    if instant(since) >= instant(until):
        raise FeedError('Invalid activity interval')
    broker.account_lease.check_process()
    if not broker.settings.configured:
        raise BrokerFailure('Paper credentials unavailable', sent=False)
    if time.monotonic() < broker.cooldown['trading']:
        raise BrokerFailure('Provider cooldown active', 429, sent=False)
    broker.trading.take(False)
    parser, raw = SSEParser(), bytearray()
    result = {'events': [], 'raw': b'', 'complete': False, 'error': None, 'since': since, 'until': until}
    try:
        async with asyncio.timeout(STREAM_SECONDS):
            from .config import PAPER_URL
            async with broker.http.stream('GET', PAPER_URL+'/v2beta1/events/activities',
                                          params={'since': since, 'until': until}, timeout=IDLE_SECONDS) as response:
                broker.store.event('activity_request', {'method': 'GET', 'status': response.status_code, 'at': utcnow()})
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
    except (httpx.HTTPError, ValueError, TimeoutError, UnicodeError):
        result['error'] = 'activity_stream_incomplete'
    finally:
        result.update(events=[e for e, _ in parser.frames], raw=bytes(raw), received_at=utcnow())
        # Cancellation is re-raised by asyncio, but its evidence survives.
        broker._last_activity_stream = result
    return result


def start_batch(store, account, since, until):
    batch = uuid.uuid4().hex
    store.db.execute('INSERT INTO activity_batches VALUES(?,?,?,?,?)',
                     (batch, 'start', account, utcnow(), canonical({'since': since, 'until': until})))
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
            prior = store.rows('SELECT DISTINCT sha256 FROM activity_events WHERE account=? AND (event_id=? OR (type=? AND ref_id=?))',
                               (account, delivery, kind, ref))
            for old in prior:
                if old['sha256'] != sha:
                    conflict = {'prior_sha256': old['sha256'], 'new_sha256': sha, 'ref_id': event.get('ref_id')}
                    store.db.execute('INSERT OR IGNORE INTO activity_conflicts VALUES(?,?,?,?)',
                                     (digest(conflict), account, at, canonical(conflict)))
            frame = frames[index][1] if index < len(frames) else payload.encode()
            store.db.execute('INSERT INTO activity_events VALUES(?,?,?,?,?,?,?,?,?,?)',
                             (batch, index, account, delivery, ref, kind, at, sha, payload, frame))
        receipt = {key: value for key, value in result.items() if key not in ('events', 'raw')}
        receipt['raw_hex'] = result.get('raw', b'').hex()
        receipt['raw_sha256'] = hashlib.sha256(result.get('raw', b'')).hexdigest()
        store.db.execute('INSERT INTO activity_batches VALUES(?,?,?,?,?)', (batch, 'outcome', account, at, canonical(receipt)))


async def collect_batch(broker, store, *, critical=True, refresh_snapshot=False):
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
    batch = start_batch(store, binding, since, until)
    broker._last_activity_stream = None
    result = {'complete': False, 'events': [], 'raw': b'', 'since': since, 'until': until,
              'account_id': binding, 'received_at': utcnow(), 'error': 'activity_acquisition_incomplete',
              'request_attempts': 0}
    try:
        async with asyncio.timeout(ATTEMPT_SECONDS):
            if refresh_snapshot:
                result['request_attempts'] += 3
                snapshot = await broker.snapshot(critical=critical)
                if account_identity(snapshot['account']) != binding:
                    raise FeedError('Paper account identity changed')
                store.put('account_snapshot', snapshot)
            result['request_attempts'] += 1
            before = await broker.request('GET', '/v2/account', critical=critical)
            result['before'] = before
            if account_identity(before) != binding:
                raise FeedError('Paper account identity changed')
            if before.get('created_at'):
                created = datetime.fromisoformat(before['created_at'].replace('Z', '+00:00'))
                since = min(start, created).isoformat()
            until = utcnow()
            result['request_attempts'] += 1
            stream = await broker.stream_activities(since, until)
            result.update(stream, account_id=binding)
            result['request_attempts'] += 1
            after = await broker.request('GET', '/v2/account', critical=critical)
            result['after'] = after
            if account_identity(after) != binding:
                raise FeedError('Paper account identity changed')
            result['request_attempts'] += 1
            result['after_positions'] = await broker.request('GET', '/v2/positions', critical=critical)
            if not isinstance(result['after_positions'], list):
                raise FeedError('Post-stream positions unavailable')
            if any(e.get('account_id', binding) != binding for e in result['events']):
                raise FeedError('Activity belongs to another account')
    except asyncio.CancelledError:
        result.update(getattr(broker, '_last_activity_stream', None) or {}, complete=False, error='activity_acquisition_cancelled')
        raise
    except Exception:
        result.update(getattr(broker, '_last_activity_stream', None) or {}, complete=False, error='activity_acquisition_incomplete')
    finally:
        result['received_at'] = utcnow()
        retain_batch(store, batch, binding, result)
        broker._last_activity_acquisition = result
    return batch, result


def publish_projection(store, batch, mapping, *, now=None):
    now = now or utcnow()
    mapping = load_mapping(mapping)
    with store.transaction():
        source = ledger_source(store)
        binding = source['state']['account_binding']
        rows = store.rows("SELECT * FROM activity_batches WHERE id=? AND phase='outcome' AND account=?", (batch, binding))
        if not rows:
            raise FeedError('Completed acquisition required')
        coverage = json.loads(rows[0]['payload'])
        events = [json.loads(r['payload']) for r in store.rows('SELECT payload FROM activity_events WHERE batch=? ORDER BY ordinal', (batch,))]
        result = project(source, events, mapping, coverage, knowledge_cutoff=now)
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
        for prior in store.rows("SELECT DISTINCT ref_id,json_extract(payload,'$.at') AS at FROM activity_events WHERE account=? AND batch<>?", (binding, batch)):
            try: covered = instant(coverage['since']) <= instant(prior['at']) <= instant(coverage['until'])
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
        store.db.execute('INSERT INTO activity_projections VALUES(?,?,?,?,?)',
                         (uuid.uuid4().hex, binding, now, result['input_sha256'], canonical(result)))
        return result


def read_projection(store, *, cutoff=None):
    """Read-only compatibility with ledgers predating the new tables."""
    cutoff = cutoff or utcnow()
    if not store.rows("SELECT name FROM sqlite_master WHERE name='activity_projections'"):
        return None
    binding = store.get('account_binding')
    rows = store.rows('SELECT rowid,at FROM activity_projections WHERE account=? ORDER BY rowid DESC', (binding,))
    for row in rows:
        if instant(row['at']) <= instant(cutoff):
            result = json.loads(store.rows('SELECT payload FROM activity_projections WHERE rowid=?', (row['rowid'],))[0]['payload'])
            # A retained attempt cannot disappear behind an older publication.
            attempts = store.rows('SELECT id,at FROM activity_batches WHERE account=? ORDER BY rowid DESC', (binding,))
            latest = next((a for a in attempts if instant(a['at']) <= instant(cutoff)), None)
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


def current_accounting(store, *, enabled=False, now=None, max_snapshot_age=30):
    now = now or utcnow()
    with store.lock:
        source = ledger_source(store)
        result = read_projection(store, cutoff=now)
        reasons = []
        if not enabled: reasons.append('activity_reader_disabled')
        if not result: reasons.append('activity_projection_unavailable')
        else:
            reasons.extend(result['issues'])
            if result['fixture']: reasons.append('fixture_evidence_only')
            if input_digest(source) != result['input_sha256']: reasons.append('accounting_inputs_changed')
            if not 0 <= instant(now)-instant(result['coverage']['received_at']) <= 90: reasons.append('activity_acquisition_stale')
            try:
                if not 0 <= instant(now)-instant(source['state']['account_snapshot']['at']) <= max_snapshot_age:
                    reasons.append('accounting_snapshot_stale')
                if instant(source['state']['account_snapshot']['at']) > instant(result['coverage']['until']):
                    reasons.append('accounting_snapshot_outside_coverage')
            except (ValueError, KeyError, TypeError): reasons.append('accounting_snapshot_unavailable')
        by_symbol = {s: {'passed': not reasons and result['by_symbol'].get(s, {}).get('passed', False),
                          'status': 'matched' if not reasons and result['by_symbol'].get(s, {}).get('passed') else 'unverified'} for s in SYMBOLS}
        return {'accounting_by_symbol': by_symbol,
                'activity_coverage': {'status': 'current' if not reasons else 'incomplete', 'issues': sorted(set(reasons))},
                'association_summary': {'reviewed_records': result.get('association_count', 0) if result else 0},
                'cash_reconciliation': result['cash_reconciliation'] if result and not reasons else {'status': 'unknown', 'cash': None}}


def main():
    from .activity_validation import main as validate
    validate()


if __name__ == '__main__':
    main()
