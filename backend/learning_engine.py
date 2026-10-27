"""On-demand offline evidence audit. No model, broker, network or execution API.

Financial outcomes require a future reconciled accounting adapter. This proof
checks readiness and existing model contracts; it never manufactures P&L labels.
"""
import argparse
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sqlite3
import uuid

from .research import validate_review
from .evidence_codec import unpack_row

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'offline-learning-proof-v1'
PROTECTED = ('experiments/btc-forward-holdout-v1.json', 'experiments/btc-liquidity-depth-v1.json')
SOURCES = ('backend/learning_engine.py', 'backend/research.py', 'backend/risk.py', 'backend/config.py', 'backend/evidence_codec.py')
AVAILABILITY = ('known_at', 'source_checked_at', 'at')
SKIPPED = {'disabled', 'no-eligible-packets', 'budget-exhausted', 'cli-unavailable', 'input-budget-exceeded', 'stale-review'}


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError('Timestamp must be an ISO string with a timezone')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Timestamp must include a timezone')
    return result.astimezone(timezone.utc)


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(encode(value).encode()).hexdigest()


def protected_windows(root=ROOT):
    windows = []
    for name in PROTECTED:
        raw = (root/name).read_bytes()
        value = json.loads(raw)
        saved = value.pop('sha256')
        if digest(value) != saved:
            raise ValueError('Protected experiment manifest changed: '+name)
        start, end = timestamp(value['starts_at']), timestamp(value['ends_at'])
        if start > end:
            raise ValueError('Invalid protected window')
        windows.append({'id': value['id'], 'starts_at': start.isoformat(), 'ends_at': end.isoformat(),
                        'manifest_sha256': hashlib.sha256(raw).hexdigest(),
                        'policy': 'Reserved indefinitely; no automatic release when the window ends'})
    return windows


def protected(when, windows):
    return any(timestamp(w['starts_at']) <= when <= timestamp(w['ends_at']) for w in windows)


@contextmanager
def readonly(path):
    path = Path(path).resolve(strict=True)
    db = sqlite3.connect(path.as_uri()+'?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    try:
        db.execute('PRAGMA query_only=ON')
        db.execute('BEGIN')
        yield db
    finally:
        db.close()


def snapshot(path, as_of, windows):
    cutoff = timestamp(as_of)
    selected, issues, metadata = {}, Counter(), {}
    footprint = []
    with readonly(path) as db:
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table in ('observations', 'research', 'orders', 'fills', 'activities', 'experiment_observations'):
            counts = Counter()
            if table not in tables:
                metadata[table] = {'status': 'missing'}
                continue
            id_column, at_column = ('client_id', 'created_at') if table == 'orders' else ('id', 'at')
            admitted = []
            # Only identity/time metadata is selected until cutoff/holdout checks pass.
            for row in db.execute(f'SELECT {id_column} identity,{at_column} recorded_at FROM {table} ORDER BY {id_column}'):
                try:
                    when = timestamp(row['recorded_at'])
                    status = 'after_cutoff' if when > cutoff else 'protected_window' if protected(when, windows) else 'available'
                except (ValueError, TypeError):
                    status = 'invalid_timestamp'
                counts[status] += 1
                # Future row counts are descriptive and excluded from the evaluation fingerprint.
                if status != 'after_cutoff':
                    footprint.append([table, row['identity'], row['recorded_at'], status])
                if status == 'available' and table in ('research', 'observations'):
                    admitted.append(row['identity'])
            metadata[table] = dict(counts)
            selected[table] = []
            for identity in admitted:
                columns = 'id,at,packet,result,usage' if table == 'research' else 'id,at,request,outcome'
                row = unpack_row(db.execute(f'SELECT {columns} FROM {table} WHERE id=?', (identity,)).fetchone(), db)
                footprint.append([table, row])
                selected[table].append(row)
        mode = None
        if 'state' in tables:
            row = db.execute("SELECT value FROM state WHERE key='mode'").fetchone()
            if row:
                try:
                    value = json.loads(row[0])
                    mode = value if value in ('alpaca', 'simulator') else 'unknown'
                except (ValueError, TypeError):
                    mode = 'unknown'
    return {'as_of': cutoff.isoformat(), 'source': str(Path(path).resolve()), 'source_mode': mode or 'unknown',
            'metadata': metadata, 'input_sha256': digest(footprint), 'records': selected}


def packet_checks(packets, recorded_at):
    """Check available timestamps, not scheduled future event dates or forecasts."""
    reasons = set()
    if not isinstance(packets, list) or not packets:
        return {'missing_packets'}
    symbols = set()
    for p in packets:
        try:
            if not isinstance(p, dict) or not isinstance(p.get('symbol'), str) or p['symbol'] in symbols:
                raise ValueError()
            symbols.add(p['symbol'])
            at = timestamp(p['as_of'])
            if at > recorded_at:
                reasons.add('packet_after_recording')
            if timestamp(p['expires_at']) <= at:
                reasons.add('invalid_packet_lifetime')
            if not isinstance(p['eligible'], bool) or not isinstance(p['vetoes'], list):
                raise ValueError()
            if p['eligible'] != (not p['vetoes']):
                reasons.add('eligibility_veto_conflict')
            if not isinstance(p['facts'], dict) or not isinstance(p['evidence'], list):
                raise ValueError()
            if not p['evidence']:
                reasons.add('missing_evidence')
            ids = set()
            for e in p['evidence']:
                if not isinstance(e, dict) or not isinstance(e.get('id'), str) or e['id'] in ids:
                    reasons.add('invalid_evidence_identity')
                    continue
                ids.add(e['id'])
                available = [e[k] for k in AVAILABILITY if e.get(k) is not None]
                if not available:
                    reasons.add('missing_evidence_availability')
                for value in available:
                    if timestamp(value) > at:
                        reasons.add('future_evidence')
                if e.get('published_at') and timestamp(e['published_at']) > at:
                    reasons.add('future_publication')
                # A source timestamp alone does not establish when a quote was received.
                if e.get('kind') == 'quote' and not e.get('known_at'):
                    reasons.add('quote_arrival_not_explicit')
        except (ValueError, TypeError, KeyError, OverflowError):
            reasons.add('malformed_packet')
    return reasons


def evaluate(data, contract):
    issues = Counter()
    decisions = Counter()
    for row in data['records'].get('observations', []):
        outcome = row['outcome']
        label = ('risk_approved' if outcome == 'approved' else 'risk_veto' if isinstance(outcome, str) and outcome.startswith('blocked:')
                 else 'research_only' if outcome == 'research-only' else 'unclassified')
        decisions[label] += 1
    statuses, checks, model_decisions = Counter(), Counter(), Counter()
    dedupe = set()
    receipts = []
    usage = Counter()
    actual_costs = []
    unknown_costs = 0
    packet_count = 0
    packet_issues = Counter()
    for row in data['records'].get('research', []):
        ref = {'research_id': row['id']}
        try:
            packets, result = json.loads(row['packet']), json.loads(row['result'])
            if not isinstance(result, dict):
                raise ValueError()
            status = result.get('status')
            category = 'skipped' if status in SKIPPED else 'cached' if result.get('cached') is True else 'completed' if status == 'reviewed' else 'failed' if status == 'failed' else 'other'
            statuses[category] += 1
            recorded = timestamp(row['at'])
            reasons = packet_checks(packets, recorded)
            packet_count += len(packets) if isinstance(packets, list) else 0
            packet_issues.update(reasons)
            if category in ('cached', 'skipped', 'failed', 'other'):
                receipts.append({**ref, 'status': category, 'scored': False})
                continue
            completed = timestamp(result['at'])
            if completed > timestamp(data['as_of']):
                issues['model_completed_after_cutoff'] += 1
                receipts.append({**ref, 'status': 'unavailable_at_cutoff', 'scored': False})
                continue
            if protected(completed, contract['protected_windows']):
                issues['model_completed_in_protected_window'] += 1
                receipts.append({**ref, 'status': 'protected_completion', 'scored': False})
                continue
            if completed < recorded:
                issues['completion_predates_recording_without_cache_flag'] += 1
                receipts.append({**ref, 'status': 'invalid_completion_time', 'scored': False})
                continue
            review = result.get('review')
            key = digest([result.get('model'), result['at'], result.get('material_hash'), review])
            if key in dedupe:
                statuses['duplicate_completed_receipt'] += 1
                receipts.append({**ref, 'status': 'duplicate', 'scored': False})
                continue
            dedupe.add(key)
            model_decisions['abstain' if isinstance(review, dict) and review.get('decision') == 'abstain' else 'propose' if isinstance(review, dict) and review.get('decision') == 'propose' else 'invalid'] += 1
            # Contract conformance and temporal completeness have independent results.
            try:
                if not isinstance(review, dict) or not isinstance(review.get('picks'), list) or not isinstance(review.get('summary'), str) or not review['summary'].strip():
                    raise ValueError()
                if result.get('execution_enabled') is True:
                    raise ValueError()
                if not isinstance(packets, list) or any(not isinstance(p, dict) for p in packets):
                    raise ValueError()
                effective_packets = [{**p, 'eligible': p.get('eligible') is True and not p.get('vetoes')} for p in packets]
                validated = validate_review(review, effective_packets)
                for pick in validated['picks']:
                    if any(not isinstance(pick[k], str) or not pick[k].strip() for k in ('why_now', 'counter_case', 'invalidation')):
                        raise ValueError()
                checks['contract_passed'] += 1
                pick_count = len(validated['picks'])
                checks['picks_checked'] += pick_count
                contract_status = 'passed'
            except (ValueError, TypeError, KeyError, ArithmeticError):
                checks['contract_failed'] += 1
                contract_status, pick_count = 'failed', 0
            if isinstance(packets, list):
                for p in packets:
                    if isinstance(p, dict) and p.get('eligible') is True:
                        try:
                            expires = timestamp(p['expires_at'])
                        except (ValueError, TypeError, KeyError, OverflowError):
                            continue  # packet_checks already reports malformed_packet.
                        if expires < completed:
                            reasons.add('review_completed_after_evidence_expired')
            checks['temporal_complete' if not reasons else 'temporal_incomplete'] += 1
            for name in ('input_tokens', 'cached_input_tokens', 'output_tokens'):
                amount = result.get('usage', {}).get(name) if isinstance(result.get('usage'), dict) else None
                if isinstance(amount, int) and not isinstance(amount, bool) and amount >= 0:
                    usage[name] += amount
            cost = result.get('actual_usd')
            if isinstance(cost, (str, int, float)) and not isinstance(cost, bool):
                try:
                    cost = Decimal(str(cost))
                    if not cost.is_finite() or cost < 0:
                        raise ValueError()
                    actual_costs.append(cost)
                except (ValueError, ArithmeticError):
                    unknown_costs += 1
            else:
                unknown_costs += 1
            receipts.append({**ref, 'status': 'evaluated', 'scored': True, 'contract': contract_status,
                             'picks_checked': pick_count, 'temporal_issues': sorted(reasons),
                             'outcome': 'unresolved; no reconciled accounting label'})
        except (ValueError, TypeError, KeyError, ArithmeticError):
            issues['malformed_research_record'] += 1
            receipts.append({**ref, 'status': 'malformed', 'scored': False})
    return {'version': VERSION, 'contract_sha256': digest(contract), 'as_of': data['as_of'],
            'source_mode': data['source_mode'], 'input_sha256': data['input_sha256'],
            'inventory': data['metadata'],
            'data_and_outcomes': {'status': 'insufficient_evidence', 'decision_categories': dict(decisions),
                'research_packets_inspected': packet_count, 'packet_issue_counts': dict(packet_issues),
                'resolved_net_pnl_labels': 0, 'training_rows': 0,
                'reason': 'Reconciled accounting outcome adapter is not implemented. Approvals/fills are not net P&L labels.'},
            'model_research': {'receipt_categories': dict(statuses), 'decisions': dict(model_decisions),
                'contract_checks': dict(checks), 'records': receipts,
                'scope': 'Evidence IDs, numerical consistency, hard vetoes, decision/thesis fields and temporal completeness; not narrative truth or predictive skill',
                'usefulness': {'status': 'insufficient_evidence', 'matched_resolved_pairs': 0,
                               'incremental_return': None, 'reason': 'No reconciled, comparable outcome pairs; abstention is not a profitable trade.'},
                'recorded_usage': dict(usage),
                'costs': {'known_actual_usd': str(sum(actual_costs, Decimal(0))) if actual_costs else None,
                          'unknown_cost_receipts': unknown_costs,
                          'total_actual_usd': str(sum(actual_costs, Decimal(0))) if actual_costs and not unknown_costs else None,
                          'scope': 'Deduplicated evaluated receipts only; not total platform subscription cost'}},
            'issues': dict(issues), 'protected_windows': contract['protected_windows'],
            'authority': {k: False for k in ('training_enabled', 'promotion_enabled', 'risk_changes_enabled', 'execution_enabled', 'network_enabled', 'model_calls_enabled')},
            'limitations': ['Holdout windows are conservatively excluded across all symbols and cohorts, even after they end.',
                           'No outcome definition, trained policy or net-return estimate is inferred from this audit.',
                           'Previously inspected development history is not an untouched holdout.']}


def markdown(report):
    models = report['model_research']
    return '\n'.join(['# Offline learning evaluation', '',
        'Cutoff: '+report['as_of'], 'Input fingerprint: '+report['input_sha256'], '',
        '## Data and outcomes', '',
        report['data_and_outcomes']['reason'],
        'Resolved net P&L labels: 0. Training rows: 0.', '',
        '## Model research quality', '',
        'Receipts: '+encode(models['receipt_categories']),
        'Decisions: '+encode(models['decisions']),
        'Contract checks: '+encode(models['contract_checks']),
        'Usefulness: insufficient evidence; no matched reconciled outcomes.',
        'Recorded usage: '+encode(models['recorded_usage']),
        'Total attributable model cost: '+str(models['costs']['total_actual_usd'])+' USD (None means unknown).', '',
        '## Protected evidence', '',
        'Both registered forward windows stay reserved, even after their end dates.',
        'See report.json for excluded counts, issue reasons and receipt-level checks.', '',
        'No training, model calls, trading, risk changes or promotion occurred.', ''])


def run(source, as_of, output, *, root=ROOT):
    cutoff = timestamp(as_of)
    if cutoff > datetime.now(timezone.utc):
        raise ValueError('Evaluation cutoff cannot be in the future')
    windows = protected_windows(root)
    data = snapshot(source, cutoff.isoformat(), windows)
    contract = {'version': VERSION, 'source_ledger': data['source'], 'source_mode': data['source_mode'],
                'as_of': data['as_of'], 'input_sha256': data['input_sha256'], 'protected_windows': windows,
                'source_sha256': {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in SOURCES},
                'outcome_definition': 'No financial labels without a reconciled accounting adapter',
                'evaluation': ['data_and_outcome_readiness', 'deterministic_model_contract_quality', 'model_usefulness_readiness']}
    destination = Path(output).resolve()/('run-'+uuid.uuid4().hex)
    destination.mkdir(parents=True, mode=0o700)
    # Registration precedes evaluation. No raw source bodies, prompts or credentials are exported.
    def save(name, value):
        with (destination/name).open('x', encoding='utf-8') as handle:
            handle.write(value)
        (destination/name).chmod(0o600)
    save('contract.json', json.dumps(contract, indent=2)+'\n')
    report = evaluate(data, contract)
    report['report_sha256'] = digest(report)
    save('report.json', json.dumps(report, indent=2)+'\n')
    save('report.md', markdown(report))
    return destination, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-ledger', type=Path, required=True)
    parser.add_argument('--as-of', required=True, help='Explicit ISO timestamp with timezone')
    parser.add_argument('--output-dir', type=Path, default=ROOT/'runtime/learning-evaluation')
    args = parser.parse_args()
    try:
        destination, report = run(args.source_ledger, args.as_of, args.output_dir)
    except (ValueError, KeyError, OSError, sqlite3.Error) as exc:
        parser.exit(1, f'Offline evaluation failed: {type(exc).__name__}; no execution enabled\n')
    print(json.dumps({'report': str(destination/'report.md'), 'report_sha256': report['report_sha256'],
                      'outcomes': report['data_and_outcomes']['status'],
                      'model_usefulness': report['model_research']['usefulness']['status'], 'execution_enabled': False}))


if __name__ == '__main__':
    main()
