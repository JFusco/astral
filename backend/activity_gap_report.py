"""Offline diagnostic report for a separately authorized, sealed observation copy."""
import argparse
from contextlib import closing
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import sys

from .activity_gap_analysis import DEFECTS, UNKNOWN, analyze, exact, identity, number
from .evidence_codec import MAX_BYTES, unpack_text

PRODUCER = ('backend/activity_observation.py', 'backend/activity_diagnostics.py',
            'backend/activity_feed.py', 'backend/store.py', 'backend/broker.py')
S5_PRODUCER_SHA256 = dict(zip(PRODUCER, (
    'b12dc0518704fa6c40924d09fc8943d015a9e240e7f0ad08ea624235b14a2ab9',
    'cf8601d99d0c26c40dc37a8bd31cc70a4c85f3028c6392f27cb6cb1e74ce0f7d',
    '014c3413ae3815be69239d40d0b13e89601a4681dd5fd377ca203fafcb792b8c',
    '3f508b9166c504578bee54223a3cab094b17b60771a41ba405e7a94858246f42',
    '1f42c772817777c62524485c7171eeca1bfe7d555756a95db060bce823da6d61')))
SUPPORTED_PRODUCER_SHA256 = {**S5_PRODUCER_SHA256,
    'backend/activity_feed.py': 'd51d4408f4dc81866b97c4d60e6d73ec1d528b2c52f96ccb7cf08b2909212020'}
PRODUCER_CONTRACTS = {'s5': S5_PRODUCER_SHA256, 's6': SUPPORTED_PRODUCER_SHA256}

EVENTS = ('activity_rollout_started', 'activity_rollout_stopped', 'activity_rollout_previous',
          'activity_rollout_failed', 'activity_attempt_started', 'activity_attempt_finished',
          'activity_attempt_abandoned', 'activity_observation_sleep_started',
          'activity_observation_sleep_finished')
COLUMNS = {'state': {'key', 'value'}, 'events': {'seq', 'at', 'type', 'payload'},
           'activity_batches': {'id', 'phase', 'account', 'at', 'payload'}}


class InputError(ValueError):
    """Unusable container or configuration; messages never contain input data."""


def sha256(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            result.update(chunk)
    return result.hexdigest()


def digest_string(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate-key')
        result[key] = value
    return result


def invalid_constant(_):
    raise ValueError('nonfinite-number')


def decode(value):
    text = unpack_text(value)
    if len(text) > MAX_BYTES:
        raise ValueError('unsupported-size')
    result = json.loads(text, parse_float=Decimal, parse_constant=invalid_constant,
                        object_pairs_hook=unique_object)
    if not isinstance(result, dict):
        raise ValueError('unsupported-record')
    return result


def safe_path(value):
    path = Path(value)
    if path.is_symlink():
        raise InputError('unsafe-path')
    resolved = path.resolve(strict=True)
    if 'runtime' in resolved.parts:
        raise InputError('unsafe-path')
    return resolved


def config(path):
    try:
        raw = safe_path(path).read_bytes()
        value = decode(raw.decode('utf-8'))
        value['_file_sha256'] = hashlib.sha256(raw).hexdigest()
        if type(value.get('schema_version')) is not int or value['schema_version'] != 1:
            raise ValueError('unsupported-schema')
        return value
    except (OSError, *DEFECTS) as exc:
        raise InputError('invalid-configuration') from exc


def policy_file(path):
    if path is None:
        return None
    value = config(path)
    try:
        if type(value.get('synthetic')) is not bool or not isinstance(value.get('provenance_ref'), str) or not value['provenance_ref']:
            raise ValueError('invalid-policy')
        with exact():
            result = {'schema_version': 1, 'synthetic': value['synthetic'], '_file_sha256': value['_file_sha256']}
            for key in ('tau_seconds', 'tau_c_seconds'):
                raw = value.get(key)
                result[key] = number(raw) if raw is not None else None
                if result[key] is not None and result[key] < 0:
                    raise ValueError('invalid-policy')
            allow = value.get('allow_indeterminate_e4')
            if allow is not None and type(allow) is not bool:
                raise ValueError('invalid-policy')
            result['allow_indeterminate_e4'] = allow
            return result
    except DEFECTS as exc:
        raise InputError('invalid-policy') from exc


def manifest_file(path):
    value = config(path)
    if (value.get('method') != 'sqlite-backup' or value.get('complete') is not True
            or type(value.get('synthetic')) is not bool or not digest_string(value.get('sha256'))
            or type(value.get('size_bytes')) is not int or value['size_bytes'] <= 0
            or not isinstance(value.get('capture_id'), str) or not value['capture_id']
            or not isinstance(value.get('producer_sha256', {}), dict)):
        raise InputError('invalid-copy-manifest')
    if not value['synthetic'] and not all(isinstance(value.get(k), str) and value[k] for k in (
            'capture_provenance_ref', 'authorization_ref')):
        raise InputError('missing-copy-provenance')
    return value


def fingerprint(path):
    if any(Path(str(path)+suffix).exists() or Path(str(path)+suffix).is_symlink()
           for suffix in ('-wal', '-shm', '-journal')):
        raise InputError('sidecar-present')
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise InputError('unsafe-ledger')
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns, sha256(path))


def header(path, size):
    with path.open('rb') as stream:
        value = stream.read(100)
    page = int.from_bytes(value[16:18], 'big') if len(value) == 100 else 0
    page = 65536 if page == 1 else page
    if (len(value) != 100 or value[:16] != b'SQLite format 3\x00' or value[18:20] != b'\x01\x01'
            or not (512 <= page <= 65536 and page & (page-1) == 0) or size % page):
        raise InputError('invalid-standalone-header')


def schema(db):
    for name, required in COLUMNS.items():
        row = db.execute('SELECT type,sql FROM sqlite_schema WHERE name=?', (name,)).fetchone()
        if row is None or row[0] != 'table' or not row[1].lstrip().upper().startswith('CREATE TABLE'):
            raise InputError('unsupported-schema')
        columns = {row[1] for row in db.execute('PRAGMA table_info('+name+')')}
        if not required <= columns:
            raise InputError('unsupported-schema')
    if [row[0] for row in db.execute('PRAGMA integrity_check')] != ['ok']:
        raise InputError('integrity-check-failed')


def read_guard(action, first, _second, database, _source):
    if action == sqlite3.SQLITE_READ and (first not in COLUMNS or database != 'main'):
        return sqlite3.SQLITE_DENY
    if action in {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_TRANSACTION}:
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def record(kind, reference, raw, **metadata):
    try:
        value = decode(raw)
    except DEFECTS:
        value = None
    return {'kind': kind, 'reference': reference, 'value': value, **metadata}


def records(db, run_id):
    result, batches = [], {}
    for key, value in db.execute("SELECT key,value FROM state WHERE key='activity_rollout_observation'"):
        result.append(record('summary', {'table': 'state', 'key': key}, value))
    placeholders = ','.join('?' for _ in EVENTS)
    for seq, kind, payload in db.execute('SELECT seq,type,payload FROM events WHERE type IN ('+placeholders+') ORDER BY seq', EVENTS):
        item = record('event', {'table': 'events', 'seq': seq}, payload, type=kind)
        result.append(item)
        value = item['value']
        if (value is not None and value.get('run_id') == run_id
                and kind in {'activity_attempt_started', 'activity_attempt_finished'}
                and identity(value.get('attempt_id'))):
            batches.setdefault(value['attempt_id'])
    for batch in batches:
        for rowid, phase, account, payload in db.execute(
                'SELECT rowid,phase,account,payload FROM activity_batches WHERE id=? ORDER BY rowid', (batch,)):
            result.append(record('batch', {'table': 'activity_batches', 'rowid': rowid}, payload,
                                 id=batch, phase=phase, account=account))
    return result


def unknown_report(run_id):
    return {'run_id': run_id, 'process_id': None, 'counters': None, 'cycles': [], 'populations': None,
            'E1': UNKNOWN, 'E2': UNKNOWN, 'E3': UNKNOWN, 'E4_policy': UNKNOWN,
            'policy_evaluation': UNKNOWN, 'synthetic_policy': False, 'intervals': [], 'loop_lag': [],
            'issues': [{'reason': 'unsupported-producer', 'reference': {'input': 'copy-manifest'}}], 'exit_code': 3}


def build_report(ledger, copy_manifest, run_id, policy=None):
    """Read one sealed copy, returning only sanitized diagnostic/audit fields."""
    if not identity(run_id):
        raise InputError('invalid-run-id')
    manifest, rules = manifest_file(copy_manifest), policy_file(policy)
    path = safe_path(ledger)
    before = fingerprint(path)
    if (before[2], before[-1]) != (manifest['size_bytes'], manifest['sha256']):
        raise InputError('copy-digest-mismatch')
    declared = manifest.get('producer_sha256', {})
    matched = next((name for name, hashes in PRODUCER_CONTRACTS.items()
                    if all(declared.get(k) == v for k, v in hashes.items())), None)
    supported = matched is not None
    expected = PRODUCER_CONTRACTS[matched] if supported else SUPPORTED_PRODUCER_SHA256
    try:
        header(path, before[2])
        with closing(sqlite3.connect(path.as_uri()+'?mode=ro', uri=True, timeout=0)) as db:
            db.execute('PRAGMA query_only=ON')
            db.execute('PRAGMA trusted_schema=OFF')
            db.execute('BEGIN')
            schema(db)
            db.set_authorizer(read_guard)
            report = analyze(run_id, records(db, run_id), rules, manifest['synthetic']) if supported else unknown_report(run_id)
    except sqlite3.Error as exc:
        raise InputError('unusable-sqlite-copy') from exc
    finally:
        if fingerprint(path) != before:
            raise InputError('evidence-changed')
    project = Path(__file__).resolve().parents[1]
    implementation = ('backend/activity_gap_report.py', 'backend/activity_gap_analysis.py', 'backend/evidence_codec.py')
    report.update(schema_version=1, operational_acceptance='not-assessed',
        policy={'schema_version': 1, 'eligible_synthetic': report['synthetic_policy'],
                'tau_seconds': format(rules['tau_seconds'], 'f') if rules and rules['tau_seconds'] is not None else None,
                'tau_c_seconds': format(rules['tau_c_seconds'], 'f') if rules and rules['tau_c_seconds'] is not None else None,
                'allow_indeterminate_e4': rules['allow_indeterminate_e4'] if rules else None,
                'operational_approval': 'not-verified'},
        provenance={'input_sha256': before[-1], 'input_size_bytes': before[2],
                    'copy_manifest_sha256': manifest['_file_sha256'],
                    'policy_sha256': rules['_file_sha256'] if rules else None,
                    'synthetic_copy': manifest['synthetic'], 'producer_contract_supported': supported,
                    'matched_producer_contract': matched,
                    'supported_producer_sha256': expected,
                    'declared_producer_sha256': {k: declared.get(k) if digest_string(declared.get(k)) else None for k in PRODUCER},
                    'implementation_sha256': {k: sha256(project/k) for k in implementation}})
    return report


def render(report, format_name):
    if format_name == 'json':
        return json.dumps(report, sort_keys=True, indent=2, allow_nan=False)+'\n'
    def display(value):
        return str(value) if value is not None else 'unknown'
    counts = report['counters'] or {}
    provenance, policy = report['provenance'], report['policy']
    lines = ['Offline observation gap report', 'Operational acceptance: not assessed',
             'Run ID: '+report['run_id'], 'Process ID: '+display(report['process_id']),
             'Policy: synthetic fixture only' if report['synthetic_policy'] else 'Policy: unknown or unset',
             'Policy evaluation: '+report['policy_evaluation'],
             'Eligible synthetic policy: '+str(policy['eligible_synthetic']),
             'Acquisitions: '+display(counts.get('complete_acquisitions'))+' / '+display(counts.get('cycles')),
             'Ratio requirement: '+counts.get('ratio_requirement', UNKNOWN)]
    lines.extend('Policy '+key+': '+display(policy[key]) for key in (
        'tau_seconds', 'tau_c_seconds', 'allow_indeterminate_e4', 'operational_approval'))
    lines.extend(['Input SHA-256: '+provenance['input_sha256'],
                  'Copy manifest SHA-256: '+provenance['copy_manifest_sha256'],
                  'Policy SHA-256: '+(provenance['policy_sha256'] or 'unset'),
                  'Producer contract: '+('supported' if provenance['producer_contract_supported'] else 'unsupported'),
                  'Matched producer contract: '+(provenance['matched_producer_contract'] or 'unknown')])
    for name, supported in provenance['supported_producer_sha256'].items():
        declared = provenance['declared_producer_sha256'][name]
        state = 'missing' if declared is None else 'supported' if declared == supported else 'different'
        lines.append('  '+name+': '+state+'; supported SHA-256: '+supported+'; declared SHA-256: '+(declared or 'missing'))
    lines.extend('Implementation SHA-256 '+name+': '+value for name, value in provenance['implementation_sha256'].items())
    lines.extend(key+': '+report[key] for key in ('E1', 'E2', 'E3', 'E4_policy'))
    populations = report['populations']
    if populations is None:
        lines.append('Populations: unknown')
    else:
        lines.extend('Population '+key+': '+str(populations[key]) for key in (
            'matched_publications', 'received_bytes', 'request_budget_units'))
        for name, value in populations['latency'].items():
            lines.append('Histogram '+name+': '+str(value['samples'])+' samples; p95 upper ms: '+
                         display(value['p95_upper_ms'])+'; over 5000 ms: '+str(value['over_5000_ms']))
        for name in ('availability_samples', 'publication_availability_samples'):
            lines.append('Population '+name+': '+(', '.join(k+'='+str(v) for k, v in populations[name].items()) or 'no samples'))
    for interval in report['intervals']:
        lines.append('Interval '+str(interval['index'])+': '+
                     (interval.get('monotonic_seconds', 'unknown'))+' seconds monotonic; '+
                     interval.get('wall_seconds', 'unknown')+' seconds wall; '+
                     ('candidate status unknown' if interval['candidate'] is None else 'candidate' if interval['candidate'] else 'no fixed-threshold candidate'))
        lines.append('  Root cause: '+interval['root_cause'])
        lines.append('  Residual: '+interval.get('residual_monotonic_seconds','unknown')+' seconds monotonic; '+interval.get('residual_wall_seconds','unknown')+' seconds wall')
        if interval.get('loci'):lines.append('  Observed locations: '+', '.join(interval['loci']))
        for piece in interval.get('contributions',[]):
            lines.append('  '+piece['category']+': '+piece['monotonic_seconds']+' seconds monotonic')
    lines.extend('Evidence: '+issue['reason']+' ('+', '.join(k+'='+display(v) for k, v in issue['reference'].items())+')'
                 for issue in report['issues'])
    return '\n'.join(lines)+'\n'


class Parser(argparse.ArgumentParser):
    def error(self, _message):
        raise InputError('invalid-arguments')


def main(argv=None):
    try:
        parser = Parser(prog='astral-gap-report', description=__doc__, add_help=False)
        parser.add_argument('--ledger', required=True, type=Path)
        parser.add_argument('--copy-manifest', required=True, type=Path)
        parser.add_argument('--run-id', required=True)
        parser.add_argument('--policy', type=Path)
        parser.add_argument('--format', choices=('text', 'json'), default='text')
        args = parser.parse_args(argv)
        report = build_report(args.ledger, args.copy_manifest, args.run_id, args.policy)
        output = render(report, args.format)
        sys.stdout.write(output)
        return report['exit_code']
    except (InputError, OSError):
        sys.stderr.write('Offline gap report input could not be verified.\n')
        return 2
    except Exception:
        sys.stderr.write('Offline gap report failed internally.\n')
        return 4


if __name__ == '__main__':
    raise SystemExit(main())
