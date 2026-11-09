"""Prospective G3 evidence qualification. No acquisition or trading authority.

Inputs are operator-attested evidence, never authentication of their contents.
The command is deliberately separate from the frozen original BTC validator.
"""
import argparse
import asyncio
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import (Decimal, localcontext, Inexact, FloatOperation, InvalidOperation,
                     DivisionByZero, Overflow, Underflow, DecimalException)
import hashlib
import importlib.metadata
import io
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import stat
import sys
import time

import httpx

from .activity_projection import canonical, digest, instant, load_mapping, symbol
from .activity_rollout import no_duplicates, read_document, source_identity
from .config import ROOT, PAPER_URL

DATA_BYTES = 32 * 1024 * 1024
RAW_BYTES = 8 * 1024 * 1024
CONTROL_BYTES = 1024 * 1024
COMPARE_MAX_GETS = 11
ROUTES = ['/v2/account', '/v2/positions', '/v2/clock', '/v2/orders',
          '/v2/account', '/v2beta1/events/activities', '/v2/account', '/v2/positions',
          '/v2/account', '/v2/positions', '/v2/clock']
CONTROLS = ('enable_orders', 'enable_news', 'enable_shadow', 'enable_exit_monitor',
            'enable_research', 'enable_codex_research', 'enable_activity_feed')
TABLES = {
    'orders': ('client_id', 'request', 'raw', 'status', 'external', 'deadline', 'created_at', 'updated_at'),
    'fills': ('id', 'client_id', 'at', 'payload'),
    'activities': ('id', 'type', 'at', 'payload'),
    'observations': ('id', 'at', 'request', 'outcome', 'context'),
    'events': ('seq', 'at', 'type', 'payload'),
}
OPTIONAL_STATE = ('fee_reconciliation_required', 'custody_checkpoint', 'snapshot_epoch', 'assets')
CHECKS = ('provenance', 'history', 'membership', 'mapping', 'movements', 'fills',
          'custody', 'books', 'projection', 'reopen', 'execution_preserved', 'inputs_preserved')
COMPARE_CHECKS = CHECKS + ('accepted_replay', 'fresh_offline', 'controls', 'transport',
                          'current_history', 'current_orders', 'current_balances')
EXIT = {'PASS': 0, 'FAIL': 1, 'REJECTED': 2, 'INCOMPLETE': 3, 'ERROR': 4}
PRIORITY = {'PASS': 0, 'INCOMPLETE': 1, 'ERROR': 2, 'REJECTED': 3, 'FAIL': 4}
DECIMAL_RE = re.compile(r'-?(?:0|[1-9][0-9]*)(?:[.][0-9]+)?(?:[eE][+-]?[0-9]{1,3})?\Z')


class QualificationError(Exception):
    def __init__(self, reason, status='REJECTED', detail=None):
        self.reason, self.status, self.detail = reason, status, detail
        super().__init__(reason)


def require(condition, reason, status='REJECTED', detail=None):
    if not condition:
        raise QualificationError(reason, status, detail)


def shape(value, fields, label):
    require(type(value) is dict and set(value) == set(fields.split()), 'schema', detail=label)
    return value


def text(value):
    require(isinstance(value, str) and bool(value), 'text_required')
    return value


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def hexsha(value):
    require(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value), 'sha256_required')
    return value


def parse(raw):
    return json.loads(raw, object_pairs_hook=no_duplicates,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite')))


def dec(value):
    require(isinstance(value, str) and len(value) <= 128 and DECIMAL_RE.fullmatch(value),
            'decimal_schema')
    mantissa = re.split('[eE]', value)[0]
    exponent = int(re.split('[eE]', value)[1]) if re.search('[eE]', value) else 0
    digits = sum(c.isdigit() for c in mantissa)
    result = Decimal(value)
    require(digits <= 50 and -100 <= exponent <= 100 and -100 <= result.as_tuple().exponent <= 100,
            'unsupported_decimal_precision', 'INCOMPLETE')
    return result


@contextmanager
def arithmetic():
    with localcontext() as ctx:
        ctx.prec, ctx.Emin, ctx.Emax = 50, -1000, 1000
        for signal in (Inexact, FloatOperation, InvalidOperation, DivisionByZero, Overflow, Underflow):
            ctx.traps[signal] = True
        yield


def environment():
    return {'executable': sys.executable, 'python': sys.version, 'sqlite': sqlite3.sqlite_version,
            'executable_sha256': sha(Path(sys.executable).read_bytes()),
            'packages': {name: importlib.metadata.version(name) for name in ('httpx', 'httpcore', 'python-dotenv')}}


def clocks():
    return {'utc': datetime.now(timezone.utc).isoformat(), 'monotonic': time.monotonic()}


def clean_path(value, *, existing=True):
    p = Path(text(value))
    require(p.is_absolute() and '..' not in p.parts, 'absolute_unaliased_path_required')
    require(p == p.resolve(strict=existing), 'path_alias')
    require(not p.is_relative_to(ROOT), 'repository_evidence_forbidden')
    require('runtime' not in p.parts and '.git' not in p.parts, 'reserved_path')
    return p


def identity(p):
    s = p.lstat()
    require(stat.S_ISREG(s.st_mode) and s.st_nlink == 1 and s.st_mode & 0o077 == 0,
            'private_regular_single_link_required')
    require(s.st_uid == os.getuid(), 'input_owner')
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)


def open_input(p):
    """Walk every component without following links, including parent races."""
    parent = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for name in p.parts[1:-1]:
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            os.close(parent)
            parent = child
        require(os.fstat(parent).st_mode & 0o077 == 0, 'private_input_parent')
        return os.open(p.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent)
    finally:
        os.close(parent)


def read_bytes(p, limit, *, expected_size=None, expected_identity=None, changed_reason='input_changed'):
    before = identity(p)
    if expected_size is not None:
        require(before[2] == expected_size, changed_reason, 'FAIL')
    if expected_identity is not None:
        require(before == expected_identity, changed_reason, 'FAIL')
    fd = open_input(p)
    with os.fdopen(fd, 'rb') as f:
        s = os.fstat(f.fileno())
        require((s.st_dev, s.st_ino) == before[:2], 'input_replaced', 'FAIL')
        raw = f.read(limit + 1)
    require(identity(p) == before, changed_reason, 'FAIL')
    require(len(raw) <= limit, 'input_budget', 'INCOMPLETE')
    return raw, before


def exclusive(p, raw):
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())


class Package:
    def __init__(self, args, argv):
        # Only the request is opened until all argument/approval bindings pass.
        self.args, self.raw, self.ids, self.entries = args, {}, {}, {}
        self.request_path = clean_path(args.request_file)
        request_raw, request_id = read_bytes(self.request_path, CONTROL_BYTES)
        class PinnedDocument:
            def open(self, mode):
                return io.BytesIO(request_raw)
        request, request_sha = read_document(PinnedDocument(), hexsha(args.request_sha256))
        require(sha(request_raw) == request_sha and identity(self.request_path) == request_id,
                'request_replaced', 'FAIL')
        shape(request, 'schema version operation attempt account invocation inputs source environment destinations controls limits start_window supervision attestation replay_receipt compare', 'request')
        require(request['schema'] == 'g3-v2-operation-request' and type(request['version']) is int and request['version'] == 1,
                'request_version')
        require(request['operation'] == args.operation, 'operation_binding')
        text(request['attempt']); text(request['account'])
        require(request['invocation'] == {'executable': sys.executable, 'module': 'backend.activity_qualification',
                                         'arguments': invocation_arguments(argv)}, 'invocation_binding')
        # The external request digest is intentionally not embedded in its own request.
        require(request['destinations'] == {'database': args.database, 'output_dir': args.output_dir}, 'destination_binding')
        require(request['controls'] == {k: False for k in CONTROLS}, 'request_controls')
        shape(request['limits'], 'input_bytes response_bytes total_response_bytes whole_seconds', 'limits')
        for key, value in request['limits'].items():
            require(type(value) is int and value > 0, 'finite_limits', detail=key)
        require(request['limits']['response_bytes'] <= RAW_BYTES and request['limits']['total_response_bytes'] <= DATA_BYTES,
                'response_budget')
        require(request['limits']['whole_seconds'] <= 3720, 'whole_call_budget')
        shape(request['start_window'], 'not_before before', 'window')
        now = instant(datetime.now(timezone.utc).isoformat())
        require(instant(request['start_window']['not_before']) <= now < instant(request['start_window']['before']), 'start_window')
        shape(request['attestation'], 'operator approved_at accepted', 'operator_attestation')
        text(request['attestation']['operator'])
        require(request['attestation']['accepted'] is True and instant(request['attestation']['approved_at']) <= now,
                'operator_attestation')
        shape(request['supervision'], 'request_sha256 method_sha256 stop_procedure qualified', 'supervision')
        hexsha(request['supervision']['request_sha256']); hexsha(request['supervision']['method_sha256'])
        text(request['supervision']['stop_procedure'])
        require(request['supervision']['qualified'] is True, 'supervision_unestablished', 'INCOMPLETE')
        if args.operation == 'compare':
            require(request['replay_receipt'] == {'path': args.replay_receipt, 'sha256': args.replay_receipt_sha256}, 'replay_binding')
            require(request['compare'] == {'method': 'GET', 'host': PAPER_URL, 'routes': ROUTES,
                                           'max_gets': COMPARE_MAX_GETS, 'credential_mechanism': 'Settings.from_env'}, 'compare_authority')
        else:
            require(request['replay_receipt'] is None and request['compare'] is None and not args.replay_receipt
                    and not args.replay_receipt_sha256, 'replay_has_no_network_authority')
        self.request, self.request_sha = request, request_sha
        self.raw[str(self.request_path)], self.ids[str(self.request_path)] = request_raw, request_id
        self.output = clean_path(args.output_dir, existing=False)
        self.database = clean_path(args.database, existing=False)
        require(self.database.parent == self.output and not self.output.exists() and not self.database.exists(), 'new_destination_required')
        require(self.output.parent.is_dir() and self.output.parent.stat().st_mode & 0o077 == 0, 'private_output_parent')
        require(type(request['inputs']) is list and request['inputs'], 'input_inventory')
        inode_set = {request_id[:2]}
        total = 0
        roles = {}
        for entry in request['inputs']:
            shape(entry, 'path role sha256 bytes', 'input')
            p = clean_path(entry['path'])
            hexsha(entry['sha256']); text(entry['role'])
            require(type(entry['bytes']) is int and entry['bytes'] >= 0, 'input_size')
            require(str(p) not in self.raw and str(p) not in self.entries, 'duplicate_input')
            require(not self.output.is_relative_to(p.parent) and not p.is_relative_to(self.output), 'input_output_overlap')
            self.entries[str(p)] = entry
            if entry['role'] != 'support':
                require(entry['role'] not in roles, 'ambiguous_role')
                roles[entry['role']] = str(p)
            total += entry['bytes']
        required = {'expectations': args.expectations_file, 'mapping': args.mapping_file,
                    'ledger': args.ledger_capture, 'capture': args.activity_capture, 'raw': args.raw_stream}
        if args.operation == 'compare':
            required['replay_receipt'] = args.replay_receipt
        require(roles == required, 'input_role_binding')
        require(total <= request['limits']['input_bytes'], 'input_budget', 'INCOMPLETE')
        require(not self.output.is_relative_to(self.request_path.parent), 'request_output_overlap')
        require(request['source'] == source_identity() and request['environment'] == environment(), 'source_environment_drift', 'FAIL')
        # Inventory and arguments are now fully authorized; read only those files.
        for path, entry in self.entries.items():
            ceiling = RAW_BYTES if entry['role'] == 'raw' else CONTROL_BYTES if entry['role'] == 'replay_receipt' else DATA_BYTES
            require(entry['bytes'] <= ceiling, 'input_budget', 'INCOMPLETE')
            raw, ident = read_bytes(Path(path), entry['bytes'], expected_size=entry['bytes'],
                                    changed_reason='sealed_input_changed')
            require(len(raw) == entry['bytes'] and sha(raw) == entry['sha256'], 'sealed_input_changed', 'FAIL')
            require(ident[:2] not in inode_set, 'input_alias')
            inode_set.add(ident[:2]); self.raw[path], self.ids[path] = raw, ident
        self.roles = roles
        self.ledger, self.capture, self.expected, self.mapping = [parse(self.raw[roles[r]]) for r in ('ledger', 'capture', 'expectations', 'mapping')]
        self.mapping = load_mapping(self.mapping)
        require(self.mapping['kind'] == 'reviewed-provider', 'reviewed_mapping_required')
        for name, h in self.mapping['source_files'].items():
            p = Path(name)
            p = p if p.is_absolute() else Path(args.mapping_file).parent / p
            self.reference(str(p), h)
        self.cutoff = self.expected.get('history', {}).get('knowledge_cutoff')
        self.validate_envelopes()

    def reference(self, path, expected_sha=None):
        require(path in self.entries, 'unapproved_reference')
        if expected_sha is not None:
            require(self.entries[path]['sha256'] == expected_sha, 'reference_hash_mismatch', 'FAIL')
        return self.raw[path]

    def refs(self, refs, *, needed=True):
        require(type(refs) is list and all(isinstance(r, str) for r in refs), 'reference_schema')
        require(bool(refs) or not needed, 'missing_evidence', 'INCOMPLETE')
        require(len(refs) == len(set(refs)), 'duplicate_reference')
        for ref in refs:
            self.reference(ref)
            require(self.entries[ref]['role'] in ('ledger', 'capture', 'raw', 'support'), 'downstream_evidence_reference')

    def preserve(self):
        for path, raw in self.raw.items():
            current, ident = read_bytes(Path(path), len(raw), expected_size=len(raw), expected_identity=self.ids[path])
            require(ident == self.ids[path] and current == raw, 'input_changed', 'FAIL')
        require(self.request['source'] == source_identity() and self.request['environment'] == environment(),
                'source_environment_drift', 'FAIL')

    def validate_envelopes(self):
        ledger, cap, expected = self.ledger, self.capture, self.expected
        shape(ledger, 'schema version capture_id account ledger_id captured_at selection producer_refs state optional_state rows', 'ledger')
        require(ledger['schema'] == 'g3-v2-selected-ledger' and type(ledger['version']) is int and ledger['version'] == 1, 'ledger_version')
        text(ledger['capture_id']); text(ledger['ledger_id']); self.refs(ledger['producer_refs'])
        require(ledger['selection'] == {k: list(v) for k, v in TABLES.items()}, 'ledger_selection')
        shape(ledger['rows'], 'orders fills activities observations events', 'rows')
        shape(ledger['optional_state'], ' '.join(OPTIONAL_STATE), 'optional_state')
        fields = ['mode', 'account_binding', 'account_snapshot']
        for key, present in ledger['optional_state'].items():
            require(type(present) is bool, 'optional_presence')
            if present:
                fields.append(key)
        shape(ledger['state'], ' '.join(fields), 'state')
        require(ledger['state']['mode'] == 'alpaca' and ledger['account'] == ledger['state']['account_binding']
                == self.request['account'] == self.mapping['account_id'], 'account_mismatch', 'FAIL')
        for table, columns in TABLES.items():
            require(type(ledger['rows'][table]) is list, 'row_array')
            ids = set()
            for row in ledger['rows'][table]:
                shape(row, ' '.join(columns), table)
                key = row[columns[0]]
                require(isinstance(key, (str, int)) and not isinstance(key, bool) and key not in ids, 'duplicate_row')
                ids.add(key)
                for field in columns:
                    value = row[field]
                    if field == 'external':
                        require(type(value) is int and value in (0, 1), 'external_flag')
                    if field in ('external', 'seq', 'id') and type(value) is int:
                        continue
                    if field == 'deadline':
                        require(type(value) in (int, float) and math.isfinite(value) and value >= 0, 'deadline')
                        continue
                    require(isinstance(value, str), 'lossless_text_required', 'INCOMPLETE')
                    if field in ('payload', 'context', 'request', 'raw'):
                        require(type(parse(value)) is dict, 'decoded_object_required')
        seqs = ledger['state'].get('custody_checkpoint', {}).get('seqs', [])
        require(type(seqs) is list and all(type(s) is int and s > 0 for s in seqs) and len(seqs) == len(set(seqs)), 'checkpoint_sequences')
        events = ledger['rows']['events']
        require(set(seqs) == {r['seq'] for r in events}, 'checkpoint_reference_closure', 'INCOMPLETE')
        for row in events:
            require(type(row['seq']) is int and row['seq'] > 0 and row['type'] == 'custody_snapshot', 'checkpoint_type')
            point = parse(row['payload'])
            require(type(point.get('snapshot')) is dict and type(point.get('working_orders')) is list, 'checkpoint_payload')
        snapshots = [ledger['state']['account_snapshot']]
        snapshots.extend(parse(r['payload'])['snapshot'] for r in events)
        snapshots.extend(parse(r['context'])['snapshot'] for r in ledger['rows']['observations'] if r['outcome'] == 'approved')
        for snap in snapshots:
            require(snap['account']['id'] == ledger['account'] and snap['account']['currency'] == 'USD', 'checkpoint_account', 'FAIL')
            if 'cash' in snap['account']:
                dec(snap['account']['cash'])
            positions(snap)
        shape(cap, 'schema version capture_id account request content_type stream_closed parse_errors limit_or_error termination raw_sha256 raw_bytes decoding_layer sent_at ended_at delivered_count distinct_count observation_refs producer_refs events', 'capture')
        require(cap['schema'] == 'g3-v2-activity-capture' and type(cap['version']) is int and cap['version'] == 1, 'capture_version')
        require(cap['capture_id'] == ledger['capture_id'] and cap['account'] == ledger['account'], 'capture_identity', 'FAIL')
        self.refs(cap['observation_refs']); self.refs(cap['producer_refs']); text(cap['decoding_layer'])
        shape(cap['request'], 'method host path status params received_at', 'capture_request')
        shape(cap['request']['params'], 'since until', 'capture_interval')
        require(cap['request']['method'] == 'GET' and cap['request']['host'] == PAPER_URL
                and cap['request']['path'] == ROUTES[5] and cap['request']['status'] == 200
                and cap['content_type'].split(';')[0].strip() == 'text/event-stream', 'capture_transport')
        require(cap['stream_closed'] is True and cap['parse_errors'] == [] and cap['limit_or_error'] is None
                and cap['termination'] == 'normal-finite', 'incomplete_capture', 'INCOMPLETE')
        raw = self.raw[self.roles['raw']]
        require(cap['raw_sha256'] == sha(raw) and cap['raw_bytes'] == len(raw), 'raw_binding', 'FAIL')
        from .activity_feed import parse_sse
        require(parse_sse(raw) == cap['events'], 'raw_delivery_mismatch', 'FAIL')
        require(type(cap['delivered_count']) is int and cap['delivered_count'] == len(cap['events'])
                and cap['distinct_count'] == len({e['ref_id'] for e in cap['events']}), 'capture_counts', 'FAIL')
        shape(expected, 'schema version account environment amendment_sha256 capture_id inputs mapping_sha256 mapping_digest source evaluator history deliveries movements orders fills economics custody coverage closing', 'expectations')
        require(expected['schema'] == 'g3-v2-reviewed-expectations' and type(expected['version']) is int and expected['version'] == 1, 'expectation_version')
        require(expected['account'] == ledger['account'] and expected['environment'] == 'paper'
                and expected['capture_id'] == ledger['capture_id'], 'expectation_identity', 'FAIL')
        hexsha(expected['amendment_sha256'])
        require(expected['source'] == self.request['source'] and expected['mapping_sha256'] == sha(self.raw[self.roles['mapping']])
                and expected['mapping_digest'] == digest(self.mapping), 'expectation_source_binding', 'FAIL')
        require(expected['inputs'] == [e for e in self.request['inputs'] if e['role'] not in ('expectations', 'replay_receipt', 'mapping')], 'expectation_input_inventory', 'FAIL')
        shape(expected['evaluator'], 'identity method sealed_at derivation_refs limitations independent', 'evaluator')
        text(expected['evaluator']['identity']); text(expected['evaluator']['method'])
        require(type(expected['evaluator']['limitations']) is list and expected['evaluator']['independent'] is True, 'independent_expectations', 'INCOMPLETE')
        self.refs(expected['evaluator']['derivation_refs'])
        require(instant(expected['evaluator']['sealed_at']) <= instant(self.request['attestation']['approved_at']), 'expectation_seal')
        history = shape(expected['history'], 'since until balance_at knowledge_cutoff created_at zero_origin evidence_refs', 'history')
        self.refs(history['evidence_refs'])
        require(history['zero_origin'] is True, 'unsupported_opening', 'INCOMPLETE')
        require(history['since'] == cap['request']['params']['since'] and history['until'] == cap['request']['params']['until'], 'sent_interval_mismatch', 'FAIL')
        require(instant(history['knowledge_cutoff']) * 1000000 == (instant(history['knowledge_cutoff']) * 1000000).to_integral_value(), 'cutoff_precision', 'INCOMPLETE')
        snap = ledger['state']['account_snapshot']
        require(snap['account']['id'] == ledger['account'] and snap['account']['currency'] == 'USD', 'snapshot_identity', 'FAIL')
        require(snap['at'] == history['balance_at'] and snap['account']['created_at'] == history['created_at'], 'closing_binding', 'FAIL')
        require(instant(history['since']) <= instant(history['created_at']) <= instant(history['balance_at'])
                <= instant(history['until']) <= instant(cap['request']['received_at']) <= instant(self.cutoff), 'history_incomplete', 'INCOMPLETE')
        require(instant(history['until']) <= instant(cap['sent_at']) <= instant(cap['ended_at']) <= instant(cap['request']['received_at']), 'capture_clocks')
        require(instant(self.mapping['known_at']) <= instant(self.cutoff) and instant(ledger['captured_at']) <= instant(self.cutoff), 'post_cutoff_evidence', 'INCOMPLETE')
        require(not ledger['rows']['activities'] and not ledger['state'].get('fee_reconciliation_required'), 'unsupported_legacy_overlap', 'INCOMPLETE')


def invocation_arguments(argv):
    result = list(argv)
    require(result.count('--request-sha256') == 1, 'explicit_request_digest')
    pos = result.index('--request-sha256')
    require(pos + 1 < len(result), 'explicit_request_digest')
    return result[:pos] + result[pos + 2:]


def timestamps(value):
    """All retained decision clocks, including raw terminal and checkpoint times."""
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, str) and (key == 'at' or key.endswith('_at') or key == 'knowledge_cutoff') and item:
                yield item
            elif key in ('payload', 'context', 'raw', 'request') and isinstance(item, str):
                yield from timestamps(parse(item))
            else:
                yield from timestamps(item)
    elif isinstance(value, list):
        for item in value:
            yield from timestamps(item)


def verify_time_precision(package):
    values = set(timestamps(package.ledger)) | {package.cutoff}
    pairs = [(instant(v), instant(datetime.fromisoformat(v.replace('Z', '+00:00')).isoformat())) for v in values]
    require(all(a <= instant(package.cutoff) for a, _ in pairs), 'post_cutoff_evidence', 'INCOMPLETE')
    # Every threshold predicate custody uses must survive datetime conversion.
    # Only values within 60 seconds can cross these decision boundaries.
    pairs.sort()
    for i, (exact, micro) in enumerate(pairs):
        for other, rounded in pairs[i:]:
            if other - exact > 61:
                break
            for threshold in (0, 15, 60):
                d, r = other - exact, rounded - micro
                require((d < threshold, d == threshold, d > threshold) ==
                        (r < threshold, r == threshold, r > threshold),
                        'unsupported_timestamp_precision', 'INCOMPLETE')


def order_description(row):
    raw, request = parse(row['raw']), parse(row['request'])
    if raw == {}:
        require(row['status'] == 'rejected' and row['external'] == 0, 'unidentified_order', 'INCOMPLETE')
        return {'client_id': row['client_id'], 'order_id': None, 'symbol': None, 'side': None,
                'status': 'rejected', 'book': None, 'filled_qty': '0', 'filled_avg_price': None,
                'row_sha256': digest(row)}
    strategy = request.get('intent', {}).get('strategy_id', 'manual')
    book = 'external' if row['external'] else 'manual' if strategy in ('manual', 'lifecycle_test') else strategy
    require(book in ('external', 'manual', 'intraday', 'swing') and symbol(raw['symbol']), 'unsupported_owner_symbol', 'INCOMPLETE')
    require(row['status'] in ('filled', 'canceled', 'expired', 'rejected', 'replaced') and raw['status'] == row['status'],
            'unsettled_order', 'INCOMPLETE')
    require(raw['client_order_id'] == row['client_id'] and raw['side'] in ('buy', 'sell'), 'order_identity', 'FAIL')
    dec(raw['filled_qty'])
    if raw.get('filled_avg_price') is not None:
        dec(raw['filled_avg_price'])
    return {'client_id': row['client_id'], 'order_id': raw['id'], 'symbol': symbol(raw['symbol']), 'side': raw['side'],
            'status': row['status'], 'book': book, 'filled_qty': raw['filled_qty'],
            'filled_avg_price': raw.get('filled_avg_price'), 'row_sha256': digest(row)}


def books_equal(actual, expected):
    require(type(actual) is dict and type(expected) is dict, 'book_schema')
    for s in set(actual) | set(expected):
        require(symbol(s) == s, 'unsupported_symbol', 'INCOMPLETE')
        for book in set(actual.get(s, {})) | set(expected.get(s, {})):
            require(book in ('manual', 'swing', 'intraday', 'external'), 'book_schema')
            if dec(actual.get(s, {}).get(book, '0')) != dec(expected.get(s, {}).get(book, '0')):
                return False
    return True


def positions(snapshot):
    result = {}
    for p in snapshot['positions']:
        name = symbol(p['symbol'])
        require(name and name not in result, 'position_identity', 'FAIL')
        require(dec(p['qty']) >= 0, 'negative_position', 'INCOMPLETE')
        result[name] = p['qty']
    return result


def economic_checks(p):
    """An independent movement schedule, never generated from projector output."""
    exp, mapping = p.expected, p.mapping
    events = p.capture['events']
    require(type(exp['deliveries']) is list and exp['deliveries'] == [
        {'event_id': e['event_id'], 'ref_id': e['ref_id'], 'sha256': digest(e)} for e in events], 'delivery_membership', 'FAIL')
    unique = {}
    for e in events:
        if e['ref_id'] in unique:
            require(e == unique[e['ref_id']], 'revised_history', 'INCOMPLETE')
        unique[e['ref_id']] = e
        require(e['status'] == 'executed' and not e.get('previous_id') and not e['details'].get('previous_id'), 'unsupported_revision', 'INCOMPLETE')
        require(instant(exp['history']['created_at']) <= instant(e['at']) <= instant(exp['history']['balance_at'])
                and instant(exp['history']['created_at']) <= instant(e['executed_at']) <= instant(exp['history']['balance_at']), 'movement_outside_history', 'INCOMPLETE')
        for key in ('qty', 'price', 'net_amount'):
            dec(e[key])
    movements = {ref: {'type': e['activity_type'], 'sha256': digest(e), 'at': e['at'], 'executed_at': e['executed_at']} for ref, e in unique.items()}
    require(exp['movements'] == movements and mapping['expected_events'] == {k: v['sha256'] for k, v in movements.items()}, 'movement_membership', 'FAIL')
    orders = {r['client_id']: order_description(r) for r in p.ledger['rows']['orders']}
    require(exp['orders'] == orders, 'order_membership', 'FAIL')
    provider_orders = {o['order_id']: o for o in orders.values() if o['order_id']}
    require(len(provider_orders) == sum(o['order_id'] is not None for o in orders.values()), 'duplicate_provider_order', 'FAIL')
    require(type(exp['economics']) is dict and set(exp['economics']) == set(unique), 'economics_membership', 'FAIL')
    fees = {a['fee_ref_id']: a for a in mapping['fee_associations']}
    trades = {r for r, e in unique.items() if e['activity_type'] == 'TRD'}
    journals = {r for r, e in unique.items() if e['activity_type'] == 'JNLC'}
    fee_refs = {r for r, e in unique.items() if e['activity_type'] in ('CFEE', 'FEE')}
    require(set(mapping['trade_contracts']) == trades and set(mapping['journal_contracts']) == journals and set(fees) == fee_refs,
            'mapping_membership', 'FAIL')
    require(trades | journals | fee_refs == set(unique), 'unsupported_movement', 'INCOMPLETE')
    cash, included = Decimal(0), Decimal(0)
    gross, net = defaultdict(lambda: defaultdict(Decimal)), defaultdict(lambda: defaultdict(Decimal))
    relations, unknowns, failures = [], [], []
    try:
        for ref, event in unique.items():
            item = exp['economics'][ref]
            shape(item, 'qty price net_amount currency symbol book order_id client_id treatment gross_value denomination evidence_refs equation_evidence', 'economic_movement')
            p.refs(item['evidence_refs'])
            require(all(item[k] == event[k] for k in ('qty', 'price', 'net_amount', 'currency')), 'source_value_mismatch', 'FAIL', ref)
            q, price, amount = (dec(item[k]) for k in ('qty', 'price', 'net_amount'))
            if ref in trades:
                owner = provider_orders.get(event['details']['order_id'])
                require(owner is not None and owner['client_id'] == event['details']['client_order_id']
                        and owner['symbol'] == symbol(event['details']['symbol']) and owner['side'] == event['details']['side'], 'trade_identity', 'FAIL')
                require(all(item[k] == owner[k] for k in ('symbol', 'book', 'order_id', 'client_id')), 'economic_owner', 'FAIL')
                require(item['currency'] == item['denomination'] == 'USD' and item['treatment'] == 'provider-net', 'trade_currency', 'FAIL')
                require(mapping['trade_contracts'][ref] == {'sha256': digest(event), 'symbol': owner['symbol'], 'book': owner['book'],
                                                          'currency': 'USD', 'cash_treatment': 'provider-net'}, 'trade_contract', 'FAIL')
                require(q > 0 and price > 0, 'execution_values', 'FAIL')
                g = dec(item['gross_value']); sign = Decimal(-1 if owner['side'] == 'buy' else 1)
                charges = [a for a in fees.values() if a.get('trade_ref_id') == ref and a['treatment'] != 'standalone-usd']
                require(charges, 'unsupported_zero_fee_trade', 'INCOMPLETE')
                fee = sum((dec(unique[a['fee_ref_id']]['net_amount']) for a in charges if a['treatment'] == 'included-usd'), Decimal(0))
                shape(item['equation_evidence'], 'gross_from_qty_price net_from_gross_and_included_fees', 'equations')
                for name, residual in (('gross_from_qty_price', g - q * price), ('net_from_gross_and_included_fees', amount - (sign * g + fee))):
                    declaration = shape(item['equation_evidence'][name], 'exactness_evidenced evidence_refs', 'equation_evidence')
                    require(type(declaration['exactness_evidenced']) is bool, 'equation_declaration')
                    p.refs(declaration['evidence_refs'], needed=False)
                    supported = declaration['exactness_evidenced'] and bool(declaration['evidence_refs'])
                    status = 'FAIL' if supported and residual else 'PASS' if supported else 'INCOMPLETE'
                    relations.append({'ref': ref, 'relation': name, 'evidence_refs': declaration['evidence_refs'], 'residual': str(residual), 'status': status})
                    if status == 'FAIL':
                        failures.append(ref)
                    elif status == 'INCOMPLETE':
                        unknowns.append(ref)
                cash += amount
                gross[owner['symbol']][owner['book']] -= sign * q
                net[owner['symbol']][owner['book']] -= sign * q
            elif ref in journals:
                require(q == 0 and item['currency'] == item['denomination'] == 'USD' and item['treatment'] == 'journal'
                        and all(item[k] is None for k in ('symbol', 'book', 'order_id', 'client_id', 'gross_value', 'equation_evidence')), 'journal_economics', 'INCOMPLETE')
                require(mapping['journal_contracts'][ref] == {'sha256': digest(event), 'currency': 'USD'}, 'journal_contract', 'FAIL')
                cash += amount
            else:
                a = fees[ref]
                require(symbol(item['symbol']) == item['symbol'] and item['book'] in ('manual', 'swing', 'intraday', 'external'),
                        'unsupported_fee_owner', 'INCOMPLETE')
                require(item['equation_evidence'] is None and item['gross_value'] is None, 'fee_schema')
                require(a['fee_sha256'] == digest(event) and item['treatment'] == a['treatment']
                        and item['symbol'] == a['symbol'] and item['book'] == a['book']
                        and item['order_id'] == a.get('order_id') and item['client_id'] == a.get('client_id'), 'fee_mapping', 'FAIL')
                treatment = a['treatment']
                if treatment != 'standalone-usd':
                    trade = unique.get(a.get('trade_ref_id'))
                    require(trade is not None and trade['ref_id'] in trades and a['trade_sha256'] == digest(trade), 'fee_trade_binding', 'FAIL')
                    owner = provider_orders.get(a['order_id'])
                    require(owner is not None and all(a[k] == owner[k] for k in ('client_id', 'symbol', 'book'))
                            and trade['details']['order_id'] == a['order_id'], 'fee_owner', 'FAIL')
                    require(event['details'].get('parent_id') in (None, trade['ref_id'])
                            and event['details'].get('order_id') in (None, a['order_id']), 'fee_parent', 'FAIL')
                if treatment == 'asset-debit':
                    require(item['denomination'] is not None, 'fee_denomination_unknown', 'INCOMPLETE')
                    require(item['denomination'] == item['symbol'] == event['currency'] and owner['side'] == 'buy', 'fee_denomination', 'FAIL')
                    require(q < 0 and amount == 0 and item['symbol'] in ('BTC', 'ETH', 'SOL'), 'asset_fee_economics', 'INCOMPLETE')
                    net[item['symbol']][item['book']] += q
                elif treatment in ('included-usd', 'standalone-usd'):
                    require(q == 0 and amount < 0 and item['currency'] == item['denomination'] == 'USD', 'usd_fee_economics', 'FAIL')
                    if treatment == 'included-usd':
                        included -= amount
                    else:
                        h = hexsha(a['standalone_evidence_sha256'])
                        require(any(p.entries[r]['sha256'] == h for r in item['evidence_refs']), 'standalone_evidence_unresolved', 'INCOMPLETE')
                        cash += amount
                else:
                    raise QualificationError('unsupported_fee_treatment', 'INCOMPLETE')
    except BaseException as exc:
        if failures:
            raise BaseExceptionGroup('Execution equations and later failure', [
                QualificationError('execution_equation_mismatch', 'FAIL', relations), exc]) from None
        raise
    # Check every exact relation before considering unsupported relations, so a
    # supported failure cannot be downgraded by an unrelated unknown.
    require(not failures, 'execution_equation_mismatch', 'FAIL', relations)
    require(not unknowns, 'unsupported_rounding_semantics', 'INCOMPLETE', relations)
    shape(exp['coverage'], 'included_usd asset_debit no_second_debit', 'coverage')
    for key, treatment in (('included_usd', 'included-usd'), ('asset_debit', 'asset-debit')):
        refs = exp['coverage'][key]
        require(type(refs) is list and refs and len(refs) == len(set(refs)), 'missing_real_fee_coverage', 'INCOMPLETE')
        require(all(r in fees and fees[r]['treatment'] == treatment for r in refs), 'fee_coverage', 'FAIL')
    p.refs(exp['coverage']['no_second_debit'])
    fills = exp['fills']
    require(type(fills) is dict and set(fills) == {r['id'] for r in p.ledger['rows']['fills']}, 'fill_membership', 'FAIL')
    assigned = []
    for row in p.ledger['rows']['fills']:
        f, want = parse(row['payload']), fills[row['id']]
        shape(want, 'row_sha256 client_id source at known_at quantity price value trade_refs evidence_refs', 'fill')
        p.refs(want['evidence_refs'])
        require(want['row_sha256'] == digest(row) and want['known_at'] == row['at']
                and all(want[k] == f[k] for k in ('client_id', 'source', 'at', 'quantity', 'price', 'value'))
                and row['client_id'] == f['client_id'], 'fill_source', 'FAIL')
        require(f['source'] == 'alpaca-cumulative-order-readback', 'fill_source_unsupported', 'INCOMPLETE')
        refs = want['trade_refs']
        require(type(refs) is list and refs and all(r in trades for r in refs), 'fill_partition', 'FAIL')
        require(all(exp['economics'][r]['client_id'] == row['client_id'] for r in refs), 'fill_owner', 'FAIL')
        require(dec(f['quantity']) == sum((dec(unique[r]['qty']) for r in refs), Decimal(0))
                and dec(f['value']) == sum((dec(exp['economics'][r]['gross_value']) for r in refs), Decimal(0)), 'fill_execution_mismatch', 'FAIL')
        require(dec(f['quantity']) * dec(f['price']) == dec(f['value']), 'unsupported_fill_rounding', 'INCOMPLETE')
        assigned.extend(refs)
    require(set(assigned) == trades and len(assigned) == len(trades), 'fill_partition', 'FAIL')
    for o in orders.values():
        require(dec(o['filled_qty']) == sum((dec(unique[r]['qty']) for r in trades if exp['economics'][r]['client_id'] == o['client_id']), Decimal(0)), 'order_filled_quantity', 'FAIL')
    shape(exp['closing'], 'cash included_fee_usd gross_books net_books positions', 'closing')
    gross = {s: {b: str(q) for b, q in v.items()} for s, v in gross.items()}
    net = {s: {b: str(q) for b, q in v.items()} for s, v in net.items()}
    require(cash == dec(exp['closing']['cash']) and included == dec(exp['closing']['included_fee_usd'])
            and books_equal(gross, exp['closing']['gross_books']) and books_equal(net, exp['closing']['net_books']), 'independent_closing_mismatch', 'FAIL')
    check_balances(p, p.ledger['state']['account_snapshot'])
    return {'cash': str(cash), 'included_fee_usd': str(included), 'gross_books': gross, 'net_books': net,
            'relations': relations, 'movement_hashes': {r: digest(e) for r, e in unique.items()}}


def check_balances(p, snapshot):
    require(snapshot['account']['id'] == p.request['account'], 'account_mismatch', 'FAIL')
    require(snapshot['account']['currency'] == 'USD' and dec(snapshot['account']['cash']) == dec(p.expected['closing']['cash']), 'cash_mismatch', 'FAIL')
    actual, expected = positions(snapshot), p.expected['closing']['positions']
    require(type(expected) is dict, 'positions_schema')
    for s in set(actual) | set(expected) | set(p.expected['closing']['net_books']):
        require(symbol(s) == s, 'unsupported_position', 'INCOMPLETE')
        require(dec(actual.get(s, '0')) == dec(expected.get(s, '0')) ==
                sum((dec(v) for v in p.expected['closing']['net_books'].get(s, {}).values()), Decimal(0)), 'position_mismatch', 'FAIL')


def import_ledger(store, ledger):
    with store.transaction():
        require(store.rows('SELECT seq FROM events') == [], 'destination_events_not_empty')
        for key, value in ledger['state'].items():
            store.put(key, value)
        for table in ('events', 'orders', 'fills', 'activities', 'observations'):
            columns = TABLES[table]
            for row in ledger['rows'][table]:
                store.db.execute('INSERT INTO '+table+' ('+','.join(columns)+') VALUES ('+','.join('?' for _ in columns)+')',
                                 tuple(row[k] for k in columns))


def imported_identity(store, ledger):
    selected = {}
    for table, columns in TABLES.items():
        if table == 'events':
            seqs = [r['seq'] for r in ledger['rows'][table]]
            rows = store.rows('SELECT '+','.join(columns)+' FROM events WHERE seq IN ('+','.join('?' for _ in seqs)+') ORDER BY seq', seqs) if seqs else []
            expected = sorted(ledger['rows'][table], key=lambda r: r['seq'])
        else:
            rows = store.rows('SELECT '+','.join(columns)+' FROM '+table+' ORDER BY rowid')
            expected = ledger['rows'][table]
        require(rows == expected, 'imported_execution_changed', 'FAIL', table)
        selected[table] = rows
    for key, value in ledger['state'].items():
        require(store.get(key) == value, 'imported_state_changed', 'FAIL', key)
    for key, present in ledger['optional_state'].items():
        require(bool(store.rows('SELECT key FROM state WHERE key=?', (key,))) == present, 'optional_state_changed', 'FAIL')
    return digest(selected)


def custody_checks(p, inventory):
    actual = inventory['custody_reconciliation']
    require(not actual['issues'], 'custody_issues', 'FAIL')
    want = p.expected['custody']
    require(type(want) is list and want, 'missing_expected_custody', 'INCOMPLETE')
    key = lambda r: tuple(r[k] for k in ('client_id', 'order_id', 'symbol', 'book'))
    for r in want:
        shape(r, 'client_id order_id symbol book quantity linked_confirmed_fee_quantity additional_debit_quantity classification checkpoints', 'custody')
        require(r['classification'] == 'confirmed-fee' and dec(r['additional_debit_quantity']) == 0, 'expected_custody_not_confirmed', 'INCOMPLETE')
        require(type(r['checkpoints']) is list and r['checkpoints'], 'missing_expected_window', 'INCOMPLETE')
        for c in r['checkpoints']:
            shape(c, 'before after before_at after_at before_quantity gross_buy_quantity after_quantity reduction_quantity', 'custody_window')
            require(dec(c['before_quantity']) + dec(c['gross_buy_quantity']) - dec(c['after_quantity']) == dec(c['reduction_quantity'])
                    == dec(r['quantity']) == dec(r['linked_confirmed_fee_quantity']), 'custody_equation', 'FAIL')
            require(0 < instant(c['after_at']) - instant(c['before_at']) <= 60, 'custody_window_duration', 'FAIL')
    require(len({key(r) for r in want}) == len(want), 'duplicate_custody_expectation')
    required = {key(item) for item in p.expected['economics'].values() if item['treatment'] == 'asset-debit'}
    missing = required - {key(r) for r in want}
    require(not missing, 'missing_required_custody', 'INCOMPLETE', sorted(missing))
    have = {key(r): r for r in actual['reductions']}
    require(set(have) == {key(r) for r in want}, 'custody_membership', 'FAIL')
    for r in want:
        a = have[key(r)]
        require(a['classification'] == 'confirmed-fee' and dec(a['additional_debit_quantity']) == 0, 'ambiguous_custody', 'FAIL')
        for k in ('quantity', 'linked_confirmed_fee_quantity', 'additional_debit_quantity'):
            require(dec(str(a[k])) == dec(r[k]), 'custody_value', 'FAIL')
        require(len(a['checkpoints']) == len(r['checkpoints']), 'custody_checkpoint_mismatch', 'FAIL')
        for got, sealed in zip(a['checkpoints'], r['checkpoints']):
            require(got['before'] == sealed['before'] and got['after'] == sealed['after'], 'custody_checkpoint_identity', 'FAIL')
            for k in ('before_at', 'after_at'):
                require(instant(got[k]) == instant(sealed[k]), 'custody_checkpoint_time', 'FAIL')
            for k in ('before_quantity', 'gross_buy_quantity', 'after_quantity', 'reduction_quantity'):
                require(dec(str(got[k])) == dec(sealed[k]), 'custody_checkpoint_quantity', 'FAIL')
    return json.loads(json.dumps(actual, default=str))


def replay(p, checks):
    from .store import Store
    from .activity_validation import import_capture
    from .activity_feed import accounting_read
    from .inventory import attribute
    verify_time_precision(p)
    independent = economic_checks(p)
    for name in ('provenance', 'history', 'membership', 'mapping', 'movements', 'fills'):
        checks[name] = 'PASS'
    results = []
    for round_number in range(2):
        store = Store(p.database, 'alpaca')
        failures = []
        try:
            if round_number == 0:
                import_ledger(store, p.ledger)
            imported_identity(store, p.ledger)
            projection = import_capture(store, p.capture, p.raw[p.roles['raw']], p.mapping, now=p.cutoff)
            require(not projection['issues'], 'projection_issues', 'FAIL', projection['issues'])
            with accounting_read(store, cutoff=p.cutoff) as context:
                inventory = attribute(store, store.get('account_snapshot'), read_context=context)
            require(not inventory['errors'], 'inventory_errors', 'FAIL')
            custody = custody_checks(p, inventory)
            require(books_equal(inventory['gross_books'], independent['gross_books'])
                    and books_equal(inventory['books'], independent['net_books'])
                    and books_equal(projection['net_books'], independent['net_books'])
                    and dec(projection['cash_reconciliation']['cash']) == dec(independent['cash']), 'projected_books_mismatch', 'FAIL')
            results.append({'independent': independent, 'custody': custody, 'execution_sha256': imported_identity(store, p.ledger)})
        except BaseException as exc:
            failures.append(exc)
        finally:
            try:
                store.close()
            except BaseException as exc:
                failures.append(exc)
            if failures:
                raise BaseExceptionGroup('Replay and cleanup failures', failures)
    require(results[0] == results[1], 'duplicate_reopen_changed_economics', 'FAIL')
    for name in ('custody', 'books', 'projection', 'reopen', 'execution_preserved'):
        checks[name] = 'PASS'
    p.preserve(); checks['inputs_preserved'] = 'PASS'
    return results[0]


class RecordingStream(httpx.AsyncByteStream):
    def __init__(self, owner, stream, record, path):
        self.owner, self.stream, self.record, self.path = owner, stream, record, path

    async def __aiter__(self):
        h = hashlib.sha256()
        try:
            fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'wb') as out:
                async for chunk in self.stream:
                    remaining = min(self.owner.per_response - self.record['bytes'], self.owner.total_limit - self.owner.total)
                    retained = chunk[:max(0, remaining)]
                    out.write(retained); out.flush(); os.fsync(out.fileno())
                    h.update(retained)
                    self.record['bytes'] += len(retained); self.owner.total += len(retained)
                    if len(retained) != len(chunk):
                        raise QualificationError('response_byte_limit', 'INCOMPLETE')
                    yield chunk
                self.record['complete'] = True
        except BaseException:
            self.owner.failed = True
            raise
        finally:
            self.record['sha256'] = h.hexdigest()
            self.record['ended_at'] = datetime.now(timezone.utc).isoformat()

    async def aclose(self):
        await self.stream.aclose()
        if not self.record['complete']:
            self.owner.failed = True


class RecordingTransport(httpx.AsyncBaseTransport):
    def __init__(self, package, inner=None):
        self.package, self.inner = package, inner or httpx.AsyncHTTPTransport(retries=0, trust_env=False)
        self.records, self.failed, self.total = [], False, 0
        self.per_response = package.request['limits']['response_bytes']
        self.total_limit = package.request['limits']['total_response_bytes']

    async def handle_async_request(self, request):
        i = len(self.records)
        require(not self.failed and i < COMPARE_MAX_GETS, 'transport_stopped', 'INCOMPLETE')
        require(request.method == 'GET' and request.url.scheme == 'https' and request.url.host == 'paper-api.alpaca.markets'
                and request.url.port in (None, 443) and not request.url.username and not request.url.password
                and request.url.path == ROUTES[i], 'transport_route')
        query = list(request.url.params.multi_items())
        if i == 3:
            require(sorted(query) == [('limit', '500'), ('status', 'all')], 'transport_query')
        elif i == 5:
            require(len(query) == 2 and {k for k, _ in query} == {'since', 'until'}, 'transport_query')
            require(instant(request.url.params['since']) < instant(request.url.params['until']), 'transport_interval')
        else:
            require(not query, 'transport_query')
        record = {'method': 'GET', 'host': PAPER_URL, 'path': request.url.path, 'query': query,
                  'started_at': datetime.now(timezone.utc).isoformat(), 'ended_at': None,
                  'status': None, 'content_type': None, 'content_encoding': None,
                  'bytes': 0, 'sha256': None, 'complete': False, 'body': f'response-{i + 1:02d}.raw'}
        # Persist dispatch before any request. Failure prevents dispatch.
        exclusive(self.package.output / f'dispatch-{i + 1:02d}.json', canonical(record).encode())
        self.records.append(record)
        try:
            response = await self.inner.handle_async_request(request)
            record.update(status=response.status_code, content_type=response.headers.get('content-type'),
                          content_encoding=response.headers.get('content-encoding'))
            return httpx.Response(response.status_code, headers=response.headers,
                                  stream=RecordingStream(self, response.stream, record, self.package.output / record['body']),
                                  extensions=response.extensions)
        except BaseException:
            self.failed = True
            raise

    async def aclose(self):
        await self.inner.aclose()


def validate_prior(p):
    receipt = parse(p.raw[p.roles['replay_receipt']])
    shape(receipt, 'schema version status attempt account claim_scope request_sha256 source environment inputs expectations_sha256 mapping_sha256 mapping_digest cutoff historical_clock started ended checks result workload transport outputs primary_failure secondary_failures missing_evidence cleanup', 'replay_receipt')
    require(sha(p.raw[p.roles['replay_receipt']]) == hexsha(p.args.replay_receipt_sha256), 'accepted_replay_digest', 'FAIL')
    require(receipt.get('schema') == 'g3-v2-replay' and type(receipt.get('version')) is int and receipt.get('version') == 1 and receipt.get('status') == 'PASS'
            and receipt.get('checks') == {k: 'PASS' for k in CHECKS} and receipt.get('cleanup') == 'closed'
            and receipt.get('primary_failure') is None and receipt.get('secondary_failures') == [], 'accepted_replay_not_pass')
    for field, value in (('account', p.request['account']), ('source', p.request['source']), ('environment', p.request['environment']),
                         ('expectations_sha256', sha(p.raw[p.roles['expectations']])), ('mapping_sha256', sha(p.raw[p.roles['mapping']])),
                         ('mapping_digest', digest(p.mapping)), ('cutoff', p.cutoff)):
        require(receipt.get(field) == value, 'accepted_replay_binding', 'FAIL', field)
    require(receipt.get('inputs') == [e for e in p.request['inputs'] if e['role'] != 'replay_receipt'], 'accepted_replay_inputs', 'FAIL')
    return receipt


async def compare(p, offline, prior, checks, records, *, settings_loader=None, transport=None):
    from .broker import AlpacaPaper
    from .config import Settings
    from .store import Store
    from .activity_feed import collect_batch, publish_projection
    require(prior['result'] == offline, 'fresh_offline_mismatch', 'FAIL')
    checks['accepted_replay'] = checks['fresh_offline'] = 'PASS'
    p.preserve()
    # No credential mechanism or broker exists before the full repeated replay.
    settings = (settings_loader or Settings.from_env)()
    require(settings.mode == 'alpaca' and settings.configured and all(getattr(settings, k) is False for k in CONTROLS), 'effective_controls')
    checks['controls'] = 'PASS'
    store = Store(p.database, 'alpaca')
    recorder = RecordingTransport(p, transport)
    records.append(recorder.records)
    broker = None
    failures = []
    try:
        broker = AlpacaPaper(settings, store, transport=recorder)
        initial = await broker.snapshot()
        check_balances(p, initial)
        orders = await broker.request('GET', '/v2/orders', params={'status': 'all', 'limit': 500}, critical=True)
        require(type(orders) is list and len(orders) < 500, 'order_coverage', 'INCOMPLETE')
        indexed = {}
        for order in orders:
            require(order['id'] not in indexed, 'duplicate_current_order', 'FAIL')
            require(order['status'] in ('filled', 'canceled', 'expired', 'rejected', 'replaced'), 'current_unsettled_order', 'INCOMPLETE')
            indexed[order['id']] = order
        expected = {o['order_id']: o for o in p.expected['orders'].values() if o['order_id']}
        require(set(indexed) == set(expected), 'current_order_membership', 'FAIL')
        for oid, want in expected.items():
            have = indexed[oid]
            require(have['client_order_id'] == want['client_id'] and symbol(have['symbol']) == want['symbol']
                    and have['side'] == want['side'] and have['status'] == want['status']
                    and dec(have['filled_qty']) == dec(want['filled_qty']), 'current_order_mismatch', 'FAIL')
            if want['filled_avg_price'] is not None:
                require(dec(have['filled_avg_price']) == dec(want['filled_avg_price']), 'current_order_price', 'FAIL')
        checks['current_orders'] = 'PASS'
        # The historical snapshot and cutoff remain untouched in this disposable
        # ledger. The fresh bracket is retained separately, never relabeled.
        batch, acquisition = await collect_batch(broker, store)
        for account in (acquisition.get('before'), acquisition.get('after')):
            if isinstance(account, dict) and account.get('id') is not None:
                require(account['id'] == p.request['account'], 'account_mismatch', 'FAIL')
        fresh = {}
        sealed = offline['independent']['movement_hashes']
        for event in acquisition['events']:
            require(event.get('account_id', p.request['account']) == p.request['account'], 'account_mismatch', 'FAIL')
            ref, h = event['ref_id'], digest(event)
            require(ref not in fresh or fresh[ref] == h, 'current_conflict', 'FAIL')
            fresh[ref] = h
        require(all(h == sealed[r] for r, h in fresh.items() if r in sealed), 'current_disappearance_or_revision', 'FAIL')
        require(acquisition.get('complete') is True, 'current_acquisition_incomplete', 'INCOMPLETE')
        require(all(r in fresh and fresh[r] == h for r, h in sealed.items()), 'current_disappearance_or_revision', 'FAIL')
        require(fresh == sealed, 'sealed_history_stale', 'INCOMPLETE')
        # Exact hashes bind every already independently checked fresh movement.
        projection = publish_projection(store, batch, p.mapping)
        require(not projection['issues'] and books_equal(projection['net_books'], offline['independent']['net_books'])
                and dec(projection['cash_reconciliation']['cash']) == dec(offline['independent']['cash']), 'fresh_projection_mismatch', 'FAIL')
        checks['current_history'] = 'PASS'
        for account in (acquisition['before'], acquisition['after']):
            check_balances(p, {'account': account, 'positions': acquisition['after_positions']})
        final = await broker.snapshot()
        check_balances(p, final)
        checks['current_balances'] = 'PASS'
        require(len(recorder.records) == COMPARE_MAX_GETS and not recorder.failed
                and all(r['complete'] and r['status'] == 200 for r in recorder.records), 'transport_evidence', 'INCOMPLETE')
        checks['transport'] = 'PASS'
        imported_identity(store, p.ledger)
        return {'historical': offline, 'initial': initial, 'final': final,
                'fresh_workload': {'bytes': len(acquisition['raw']), 'deliveries': len(acquisition['events']), 'references': len(fresh)},
                'actual_interval': {'since': acquisition['since'], 'until': acquisition['until']},
                'claim': 'Stable observed bracket; not an atomic provider snapshot or exclusive ownership.'}
    except BaseException as exc:
        failures.append(exc)
    finally:
        try:
            if broker is not None:
                await broker.close()
            else:
                await recorder.aclose()
        except BaseException as exc:
            failures.append(exc)
        try:
            store.close()
        except BaseException as exc:
            failures.append(exc)
        if failures:
            raise BaseExceptionGroup('Comparison and cleanup failures', failures)


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise QualificationError('arguments')


def arguments(argv):
    parser = Parser(add_help=False, allow_abbrev=False)
    parser.add_argument('operation', choices=('replay', 'compare'))
    for flag in ('request-file', 'request-sha256', 'expectations-file', 'mapping-file', 'ledger-capture',
                 'activity-capture', 'raw-stream', 'database', 'output-dir'):
        parser.add_argument('--'+flag, required=True)
    parser.add_argument('--replay-receipt')
    parser.add_argument('--replay-receipt-sha256')
    require(len([x for x in argv if x.startswith('--')]) == len(set(x for x in argv if x.startswith('--'))), 'duplicate_argument')
    return parser.parse_args(argv)


def run(argv, *, settings_loader=None, transport=None):
    """Public CLI orchestration; injectable transports are for controlled tests."""
    outcome = {'schema': 'g3-v2-outcome', 'version': 1, 'operation': None, 'attempt': None, 'status': 'PASS',
               'exit_code': 0, 'request_sha256': None, 'receipt': None, 'receipt_sha256': None,
               'primary_failure': None, 'secondary_failures': [], 'missing_evidence': [], 'cleanup': 'not-started'}
    p, result, created = None, None, False
    checks, records = {}, []
    started, ended = None, None

    def failure(exc):
        if isinstance(exc, BaseExceptionGroup):
            for cause in exc.exceptions:
                failure(cause)
            return
        if isinstance(exc, QualificationError):
            item = {'reason': exc.reason, 'status': exc.status, 'detail': exc.detail}
        elif isinstance(exc, DecimalException):
            item = {'reason': 'unsupported_arithmetic', 'status': 'INCOMPLETE', 'detail': type(exc).__name__}
        elif isinstance(exc, (KeyboardInterrupt, asyncio.CancelledError, TimeoutError)):
            item = {'reason': 'interrupted_or_exhausted', 'status': 'INCOMPLETE', 'detail': None}
        elif isinstance(exc, (ValueError, TypeError, KeyError)) and not created:
            item = {'reason': 'invalid_document', 'status': 'REJECTED', 'detail': type(exc).__name__}
        else:
            item = {'reason': 'unexpected_failure', 'status': 'ERROR', 'detail': type(exc).__name__}
        if outcome['primary_failure'] is None or PRIORITY[item['status']] > PRIORITY[outcome['status']]:
            if outcome['primary_failure'] is not None:
                outcome['secondary_failures'].append(outcome['primary_failure'])
            outcome['primary_failure'], outcome['status'] = item, item['status']
        else:
            outcome['secondary_failures'].append(item)
        if item['status'] == 'INCOMPLETE':
            outcome['missing_evidence'].append(item['reason'])

    try:
        started = clocks()
        args = arguments(list(argv)); outcome['operation'] = args.operation
        with arithmetic():
            p = Package(args, list(argv))
            outcome.update(attempt=p.request['attempt'], request_sha256=p.request_sha)
            checks = {name: 'NOT_RUN' for name in (COMPARE_CHECKS if args.operation == 'compare' else CHECKS)}
            prior = validate_prior(p) if args.operation == 'compare' else None
            p.output.mkdir(mode=0o700); created = True; outcome['cleanup'] = 'unknown'
            # Ensure SQLite sidecars and any exclusively created artifacts remain private.
            previous_umask = os.umask(0o077)
            try:
                result = replay(p, checks)
                if args.operation == 'compare':
                    result = asyncio.run(compare(p, result, prior, checks, records,
                                                 settings_loader=settings_loader, transport=transport))
                outcome['cleanup'] = 'closed'
            finally:
                os.umask(previous_umask)
    except BaseException as exc:
        failure(exc)
    finally:
        if p is not None:
            try:
                p.preserve()
            except BaseException as exc:
                failure(exc)
        try:
            ended = clocks()
            if p is not None and started is not None:
                require(ended['monotonic'] - started['monotonic'] <= p.request['limits']['whole_seconds'], 'whole_call_exhausted', 'INCOMPLETE')
        except BaseException as exc:
            failure(exc)
        if outcome['status'] == 'PASS' and (not checks or any(v != 'PASS' for v in checks.values())):
            failure(QualificationError('mandatory_checks_missing', 'INCOMPLETE'))
        if created:
            try:
                outputs = {}
                for f in sorted(p.output.iterdir()):
                    require(f.is_file() and not f.is_symlink(), 'unexpected_output', 'FAIL')
                    raw, _ = read_bytes(f, DATA_BYTES)
                    outputs[f.name] = {'sha256': sha(raw), 'bytes': len(raw)}
                receipt = {'schema': 'g3-v2-'+outcome['operation'], 'version': 1, 'status': outcome['status'],
                           'attempt': outcome['attempt'], 'account': p.request['account'],
                           'claim_scope': 'Prospective G3 qualification only; original case unresolved; no runtime or order authority.',
                           'request_sha256': p.request_sha, 'source': p.request['source'], 'environment': p.request['environment'],
                           'inputs': p.request['inputs'], 'expectations_sha256': sha(p.raw[p.roles['expectations']]),
                           'mapping_sha256': sha(p.raw[p.roles['mapping']]), 'mapping_digest': digest(p.mapping),
                           'cutoff': p.cutoff, 'historical_clock': 'Evaluation metadata, not actual invocation time.',
                           'started': started, 'ended': ended, 'checks': checks, 'result': result,
                           'workload': {'raw_bytes': len(p.raw[p.roles['raw']]), 'deliveries': p.capture['delivered_count'], 'references': p.capture['distinct_count']},
                           'transport': records[0] if records else [], 'outputs': outputs,
                           'primary_failure': outcome['primary_failure'], 'secondary_failures': outcome['secondary_failures'],
                           'missing_evidence': outcome['missing_evidence'], 'cleanup': outcome['cleanup']}
                raw = canonical(receipt).encode()
                exclusive(p.output/'receipt.json', raw)
                outcome.update(receipt=str(p.output/'receipt.json'), receipt_sha256=sha(raw))
            except BaseException as exc:
                failure(exc)
    outcome['exit_code'] = EXIT[outcome['status']]
    return outcome


def main():
    outcome = run(sys.argv[1:])
    print(canonical(outcome), flush=True)
    return outcome['exit_code']


if __name__ == '__main__':
    raise SystemExit(main())
