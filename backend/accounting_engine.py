"""Local accounting proof: read-only source audits and explicit cost records.

No broker/model/network interface, tax filing, inferred fee adjustment or trading
write exists here. Gross FIFO diagnostics are not reconciled net P&L or tax lots.
"""
import argparse
from collections import Counter, defaultdict, deque
from contextlib import contextmanager
import csv
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from functools import wraps
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import uuid

from .fee_evidence import validate_activity
from .accounting_receipts import receipt_url
from .custody import analyze as analyze_custody

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'accounting-proof-v2'
USD_SYMBOLS = {'BTC', 'ETH', 'SOL', 'SPY', 'QQQ', 'GLD', 'TLT', 'IWM'}


def precise(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        with localcontext() as context:
            context.prec = 50
            return function(*args, **kwargs)
    return wrapped


def at(value):
    if not isinstance(value, str):
        raise ValueError('Timestamp must be an ISO string')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Timezone required')
    return result.astimezone(timezone.utc)


def number(value):
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError('Amounts must be decimal strings or integers')
    result = Decimal(value)
    if not result.is_finite():
        raise ValueError('Finite amount required')
    return result


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def symbol(value):
    value = str(value).replace('/', '')
    return {'BTCUSD': 'BTC', 'ETHUSD': 'ETH', 'SOLUSD': 'SOL'}.get(value, value)


@contextmanager
def readonly(path):
    db = sqlite3.connect(Path(path).resolve(strict=True).as_uri()+'?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    try:
        db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
        yield db
    finally:
        db.close()


def source_snapshot(path, cutoff):
    selected, issues = {}, Counter()
    with readonly(path) as db:
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        specs = {'fills': ('at', 'id,client_id,at,payload'), 'activities': ('at', 'id,type,at,payload'),
                 'orders': ('created_at', 'client_id,request,raw,status,external,created_at'), 'equity': ('at', 'id,at,value')}
        for table, (clock, columns) in specs.items():
            selected[table] = []
            if table not in tables:
                issues['missing_'+table] += 1;continue
            for row in db.execute(f'SELECT {columns} FROM {table} ORDER BY rowid'):
                try:
                    if at(row[clock]) > cutoff:
                        issues['after_cutoff_'+table] += 1;continue
                    selected[table].append(dict(row))
                except (ValueError, TypeError, AttributeError):
                    issues['invalid_timestamp_'+table] += 1
        selected['observations'] = [dict(r) for r in db.execute("SELECT id,at,outcome,context FROM observations WHERE outcome='approved'")
                                    if at(r['at']) <= cutoff] if 'observations' in tables else []
        selected['checkpoints'] = [dict(r) for r in db.execute("SELECT seq AS id,at,payload FROM events WHERE type='custody_snapshot'")
                                   if at(r['at']) <= cutoff] if 'events' in tables else []
        selected['state'] = {}
        if 'state' in tables:
            for key in ('mode', 'account_snapshot', 'account_binding', 'fee_reconciliation_required'):
                row = db.execute('SELECT value FROM state WHERE key=?', (key,)).fetchone()
                if row:
                    try:selected['state'][key] = json.loads(row[0])
                    except ValueError:issues['invalid_state_'+key] += 1
    selected['issues'] = dict(issues)
    return selected


@precise
def cost_report(document, cutoff):
    if document is None:
        return {'status': 'missing_input', 'actual_total_by_currency': None,
                'monthly_personal_budget_by_currency': None, 'charges': [], 'subscriptions': []}
    if not isinstance(document, dict) or document.get('version') != 1 or not isinstance(document.get('charges'), list) or not isinstance(document.get('subscriptions'), list):
        raise ValueError('Unsupported accounting input contract')
    charges, plans, counts = {}, {}, Counter()
    for collection, key, time_fields in ((charges, 'charges', ('known_at', 'incurred_at')), (plans, 'subscriptions', ('known_at',))):
        for value in document[key]:
            if not isinstance(value, dict) or not isinstance(value.get('id'), str) or not value['id'].strip() or not isinstance(value.get('provider'), str) or not value['provider'].strip():
                raise ValueError('Cost identity/provider required')
            if value['id'] in collection and collection[value['id']] != value:
                raise ValueError('Conflicting cost identity')
            if any(at(value.get(k)) > cutoff for k in time_fields):
                counts['after_cutoff_'+key] += 1;continue
            collection[value['id']] = value
    confirmed, estimates, personal_budget, gross_budget, allocated_budget = (defaultdict(Decimal) for _ in range(5))
    receipt_ids, allocations = {}, defaultdict(Decimal)
    rows, subscriptions = [], []
    for key, v in charges.items():
        status = v.get('status')
        if status not in ('confirmed', 'estimated', 'unknown') or not isinstance(v.get('currency'), str) or not re.fullmatch('[A-Z]{3}', v['currency']):
            raise ValueError('Invalid charge status/currency')
        amount = number(v['amount']) if v.get('amount') is not None else None
        if amount is not None and amount < 0:
            raise ValueError('Negative cost requires a separate credit contract')
        if status != 'unknown' and amount is None:
            raise ValueError('Known charge requires an amount')
        source = v.get('source_ref')
        role = v.get('role', 'charge')
        if role not in ('charge', 'included_allocation'):
            raise ValueError('Invalid billing role')
        link = receipt_url(v.get('receipt_url'))
        if link and (status != 'confirmed' or role != 'charge'):
            raise ValueError('Receipt links require a confirmed ordinary charge')
        if status == 'confirmed' and (not isinstance(source, str) or not source.strip()):
            raise ValueError('Confirmed charge requires a receipt reference')
        if role == 'included_allocation':
            parent = charges.get(v.get('parent_charge_id'))
            if not parent or parent.get('role', 'charge') != 'charge' or parent.get('status') != 'confirmed' or parent['currency'] != v['currency'] or parent['provider'] != v['provider'] or amount is None:
                raise ValueError('Bundled allocation requires a matching confirmed parent charge')
            allocations[parent['id']] += amount
            if allocations[parent['id']] > number(parent['amount']):
                raise ValueError('Allocations exceed the actual bill')
        elif status == 'confirmed':
            receipt_key = (v['provider'].casefold(), source, v['currency'])
            if receipt_key in receipt_ids and receipt_ids[receipt_key] != key:
                raise ValueError('Same receipt appears under multiple charge IDs')
            receipt_ids[receipt_key] = key;confirmed[v['currency']] += amount
        elif status == 'estimated':estimates[v['currency']] += amount
        if status == 'unknown':counts['unknown_charges'] += 1
        rows.append({'id': key, 'provider': v['provider'], 'status': status, 'role': role,
                     'amount': str(amount) if amount is not None else None, 'currency': v['currency'], 'source_ref': source,
                     'known_at': v['known_at'], 'incurred_at': v['incurred_at'], 'receipt_url': link})
    for key, v in plans.items():
        if v.get('status') not in ('active', 'proposed', 'cancelled', 'unverified') or v.get('billing_interval') not in ('monthly', 'annual') or not isinstance(v.get('currency'), str) or not re.fullmatch('[A-Z]{3}', v['currency']):
            raise ValueError('Invalid subscription contract')
        amount = number(v['billing_amount']) if v.get('billing_amount') is not None else None
        personal, allocation = number(v.get('personal_fraction', '1')), number(v.get('astral_fraction', '1'))
        if not 0 <= personal <= 1 or not 0 <= allocation <= 1 or (amount is not None and amount < 0):
            raise ValueError('Invalid subscription amount/allocation')
        if amount is not None and (not isinstance(v.get('source_ref'), str) or not v['source_ref'].strip()):
            raise ValueError('Known subscription amount requires a source reference')
        if v.get('next_renewal') is not None:at(v['next_renewal'])
        monthly = amount/(12 if v['billing_interval'] == 'annual' else 1) if amount is not None else None
        if v['status'] == 'active':
            if monthly is None:counts['unknown_active_subscriptions'] += 1
            else:
                gross_budget[v['currency']] += monthly;personal_budget[v['currency']] += monthly*personal
                allocated_budget[v['currency']] += monthly*personal*allocation
        subscriptions.append({'id': key, 'provider': v['provider'], 'plan': v.get('plan'), 'status': v['status'],
            'billing_amount': str(amount) if amount is not None else None, 'currency': v['currency'],
            'billing_interval': v['billing_interval'], 'monthly_equivalent': str(monthly) if monthly is not None else None,
            'personal_monthly_equivalent': str(monthly*personal) if monthly is not None else None,
            'personal_fraction': str(personal), 'astral_fraction': str(allocation), 'known_at': v['known_at'],
            'source_ref': v.get('source_ref'), 'funding_note': v.get('funding_note'), 'next_renewal': v.get('next_renewal')})
    totals = lambda values: {k: str(v) for k,v in sorted(values.items())}
    complete = document.get('charge_coverage_complete') is True and not counts['unknown_charges'] and not estimates
    return {'status': 'recorded_inputs_only', 'coverage_is_user_asserted': True,
            'recorded_confirmed_charges_by_currency': totals(confirmed), 'estimated_charges_by_currency': totals(estimates),
            'actual_total_by_currency': totals(confirmed) if complete else None,
            'gross_monthly_subscription_budget_by_currency': totals(gross_budget),
            'monthly_personal_budget_by_currency': totals(personal_budget),
            'monthly_astral_personal_budget_by_currency': totals(allocated_budget),
            'monthly_budget_complete': document.get('subscription_coverage_complete') is True and not counts['unknown_active_subscriptions'] and not any(v['status'] == 'unverified' for v in plans.values()),
            'exclusions': dict(counts), 'charges': rows, 'subscriptions': subscriptions,
            'note': 'Budgets are not invoices. Employer coverage and allocation follow user-supplied records; never add budgets to confirmed charges. No FX conversion or deductibility determination.'}


@precise
def evaluate(source, costs, cutoff):
    issues = list(source['issues'])
    orders = {}
    for row in source['orders']:
        try:
            request = json.loads(row['request']);name = request.get('intent', {}).get('strategy_id', 'manual')
            book = 'external' if row['external'] else name if name in ('manual', 'swing', 'intraday') else 'manual' if name == 'lifecycle_test' else 'unknown'
            orders[row['client_id']] = {'book': book, 'strategy_id': name}
        except (ValueError, TypeError, AttributeError):issues.append('invalid_order_metadata')
    fills, fees, equity = [], [], []
    for row in source['fills']:
        try:
            p = json.loads(row['payload']);qty, price, value = (number(p[k]) for k in ('quantity', 'price', 'value'))
            if p['id'] != row['id'] or p['client_id'] != row['client_id'] or qty <= 0 or price <= 0 or value <= 0 or p['side'] not in ('buy', 'sell'):
                raise ValueError()
            if abs(value-qty*price) > max(Decimal('0.000000000001'), value*Decimal('1e-24')) or at(p['at']) > at(row['at']):
                raise ValueError()
            if symbol(p['symbol']) not in USD_SYMBOLS:raise ValueError()
            if p.get('fee') is not None:number(p['fee'])
            owner = orders.get(row['client_id'], {'book': 'unknown', 'strategy_id': None})
            book = owner['book']
            if book == 'unknown':issues.append('unknown_fill_owner')
            expected = {'alpaca': 'alpaca-cumulative-order-readback', 'simulator': 'simulator'}.get(source['state'].get('mode'))
            if not expected or p.get('source') != expected:issues.append('unverified_fill_source')
            fills.append({'id': row['id'], 'symbol': symbol(p['symbol']), 'book': book, 'strategy_id': owner['strategy_id'], 'side': p['side'],
                          'quantity': str(qty), 'price': str(price), 'value': str(value), 'executed_at': p['at'], 'known_at': row['at'],
                          'source': p.get('source', 'unknown'), 'fee': p.get('fee')})
        except (ValueError, TypeError, KeyError, ArithmeticError, AttributeError):issues.append('invalid_fill_record')
    fills.sort(key=lambda f: (at(f['executed_at']), at(f['known_at']), f['id']))
    lots, matched, balances = defaultdict(deque), [], defaultdict(Decimal)
    gross_realized = defaultdict(Decimal)
    for f in fills:
        key = (f['symbol'], f['book']);qty, value = number(f['quantity']), number(f['value'])
        balances[f['symbol']] += qty if f['side'] == 'buy' else -qty
        if f['side'] == 'buy':lots[key].append({'fill': f, 'qty': qty, 'basis': value});continue
        remaining = qty
        while remaining > 0 and lots[key]:
            lot = lots[key][0];take = min(remaining, lot['qty']);basis = lot['basis']*take/lot['qty'];proceeds = value*take/qty
            matched.append({'symbol': f['symbol'], 'book': f['book'], 'buy_fill_id': lot['fill']['id'], 'sell_fill_id': f['id'],
                            'acquired_at': lot['fill']['executed_at'], 'disposed_at': f['executed_at'], 'quantity': str(take),
                            'gross_basis_usd': str(basis), 'gross_proceeds_usd': str(proceeds), 'gross_pnl_usd': str(proceeds-basis)})
            gross_realized[key] += proceeds-basis;remaining -= take;lot['qty'] -= take;lot['basis'] -= basis
            if not lot['qty']:lots[key].popleft()
        if remaining:issues.append('sell_exceeds_same_book_lots')
    snapshot = source['state'].get('account_snapshot', {})
    current = False;actual, cash_fees = defaultdict(Decimal), defaultdict(Decimal)
    try:
        current = isinstance(snapshot, dict) and 0 <= (cutoff-at(snapshot['at'])).total_seconds() <= 60 and isinstance(snapshot.get('positions'), list)
        if current and snapshot.get('account', {}).get('currency') != 'USD':
            current = False;issues.append('account_currency_unverified')
        if current:
            for p in snapshot['positions']:actual[symbol(p['symbol'])] += number(p['qty'])
    except (ValueError, KeyError, TypeError, ArithmeticError, AttributeError):current = False;issues.append('invalid_custody_snapshot')
    gross_balances = dict(balances)
    for row in source['activities']:
        try:
            p = json.loads(row['payload'])
            if p.get('id') != row['id'] or p.get('activity_type') != row['type']:raise ValueError()
            if row['type'] not in ('CFEE', 'FEE'):
                issues.append('unsupported_cash_flow_activity');continue
            for clock in ('transaction_time', 'date'):
                if p.get(clock):
                    event_time = at(p[clock]+'T00:00:00+00:00') if re.fullmatch(r'\d{4}-\d{2}-\d{2}', p[clock]) else at(p[clock])
                    if event_time > at(row['at']):raise ValueError()
            status = validate_activity(p)
            normalized = {'id': row['id'], 'type': row['type'], 'known_at': row['at'], 'status': status,
                          'symbol': symbol(p.get('symbol', '')), 'quantity': p.get('qty'), 'net_amount': p.get('net_amount'), 'currency': p.get('currency')}
            fees.append(normalized)
            if status != 'confirmed-provider-record':issues.append('pending_fee_confirmation');continue
            if row['type'] == 'CFEE':balances[symbol(p['symbol'])] += number(p['qty'])
            else:
                currency = p.get('currency') or snapshot.get('account', {}).get('currency')
                if currency != 'USD':issues.append('fee_currency_unverified');continue
                cash_fees[currency] += -number(p['net_amount'])
        except (ValueError, KeyError, TypeError, ArithmeticError, AttributeError):issues.append('invalid_fee_record')
    if source['state'].get('fee_reconciliation_required'):issues.append('disputed_fee_revision')
    custody = analyze_custody(orders=source['orders'], fills=source['fills'], activities=source['activities'],
        observations=source.get('observations', []), checkpoints=source.get('checkpoints', []), snapshot=snapshot,
        account_id=source['state'].get('account_binding'), mode=source['state'].get('mode'), as_of=cutoff.isoformat())
    if custody['issues']:issues.append('custody_debit_requires_review')
    for s, books in custody['additional_debits'].items():balances[s] -= sum((number(q) for q in books.values()), Decimal(0))
    differences = [{'symbol': s, 'recorded_net_quantity': str(balances[s]), 'broker_quantity': str(actual[s]),
                    'gross_quantity': str(gross_balances.get(s, 0)),
                    'unexplained_quantity': str(actual[s]-balances[s])} for s in sorted(set(actual)|set(balances))] if current else []
    if not current:issues.append('custody_snapshot_missing_stale_or_after_cutoff')
    if any(number(d['unexplained_quantity']) != 0 for d in differences):issues.append('unreconciled_custody')
    for row in source['equity']:
        try:equity.append((at(row['at']), number(row['value'])))
        except (ValueError, TypeError, ArithmeticError):issues.append('invalid_equity_observation')
    equity.sort()
    return {'version': VERSION, 'as_of': cutoff.isoformat(), 'source_mode': source['state'].get('mode', 'unknown'),
            'scope': 'Retained paper/simulator records only; no assertion of complete account history',
            'fill_rows': len(fills), 'fill_sources': dict(Counter(f['source'] for f in fills)),
            'custody': {'status': 'needs_review' if issues else 'matched_quantities_only', 'snapshot_current': current,
                        'differences': differences, 'gross_to_net': custody},
            'gross_fifo_diagnostics': {'by_book': [{'symbol': s, 'book': b, 'gross_realized_usd': str(v)} for (s,b),v in sorted(gross_realized.items())],
                                      'status': 'incomplete' if any(i in issues for i in ('invalid_fill_record', 'unknown_fill_owner', 'unverified_fill_source', 'sell_exceeds_same_book_lots', 'invalid_order_metadata', 'missing_fills', 'missing_orders', 'invalid_timestamp_fills', 'invalid_timestamp_orders')) else 'retained_gross_records_only',
                                      'matches': matched, 'basis': 'Unadjusted retained fill values; cumulative order deltas are not individual execution activities or certified tax lots'},
            'fees': {'recorded_rows': len(fees), 'known_cash_fee_debits_by_currency': {k: str(v) for k,v in cash_fees.items()},
                     'coverage': 'unverified; absence of fee rows is not zero fees'},
            'money_results': {'realized_net_pnl_usd': None, 'unrealized_pnl_usd': None, 'cash_flow_adjusted_pnl_usd': None,
                              'observed_equity_change_usd': str(equity[-1][1]-equity[0][1]) if len(equity) > 1 else None,
                              'equity_window': [equity[0][0].isoformat(), equity[-1][0].isoformat()] if equity else None,
                              'reason': 'Fee/cash-flow completeness and authoritative cost-basis reconciliation are not established. Equity change is not necessarily trading profit.'},
            'operating_costs': cost_report(costs, cutoff), 'issues': dict(Counter(issues)),
            'learning_outcomes': [], 'tax_export_status': 'source_records_only_not_filing_ready',
            'authority': {'orders_enabled': False, 'ledger_adjustments_enabled': False, 'model_calls_enabled': False, 'tax_filing_enabled': False},
            '_fill_export': fills, '_fee_export': fees}


def run(source, as_of, output, costs_file=None):
    cutoff = at(as_of)
    if cutoff > datetime.now(timezone.utc):raise ValueError('Cutoff cannot be in the future')
    data = source_snapshot(source, cutoff)
    costs = json.loads(Path(costs_file).read_text()) if costs_file else None
    folder = Path(output).resolve()/('run-'+uuid.uuid4().hex);folder.mkdir(parents=True, mode=0o700)
    def save(name, value):
        with (folder/name).open('x', encoding='utf-8', newline='') as handle:handle.write(value)
        (folder/name).chmod(0o600)
    contract = {'version': VERSION, 'source_ledger': str(Path(source).resolve()), 'as_of': cutoff.isoformat(),
                'input_sha256': digest(data), 'cost_inputs_sha256': digest(costs),
                'source_sha256': {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ('backend/accounting_engine.py', 'backend/accounting_receipts.py', 'backend/fee_evidence.py', 'backend/custody.py', 'backend/risk.py')},
                'assumptions': 'Gross FIFO diagnostic per book, USD instruments only; no net P&L, synthetic adjustments or filing claims'}
    save('contract.json', json.dumps(contract, indent=2)+'\n')
    report = evaluate(data, costs, cutoff)
    for filename, rows in (('fills.csv', report.pop('_fill_export')), ('fees.csv', report.pop('_fee_export')), ('gross-lot-matches.csv', report['gross_fifo_diagnostics']['matches'])):
        import io
        text = io.StringIO(newline='');fields = list(rows[0]) if rows else ['no_records']
        writer = csv.DictWriter(text, fieldnames=fields);writer.writeheader();writer.writerows(rows);save(filename, text.getvalue())
    report['contract_sha256'] = digest(contract);report['report_sha256'] = digest(report)
    save('report.json', json.dumps(report, indent=2)+'\n')
    save('report.md', '\n'.join(['# Accounting proof', '', 'Cutoff: '+report['as_of'],
        'Source mode: '+str(report['source_mode']), 'Retained fill rows: '+str(report['fill_rows']), '',
        'Custody: '+report['custody']['status'], 'Issues: '+canonical(report['issues']), '',
        'Net P&L: unknown. '+report['money_results']['reason'], '',
        'Monthly personal subscription budget by currency: '+canonical(report['operating_costs'].get('monthly_personal_budget_by_currency')), '',
        'Recurring budgets, confirmed charges and allocations are separate. None means unknown.',
        'Source CSVs and gross lot matches are preparation records, not a tax filing or reconciled learning labels.',
        'No trades, source-ledger writes, subscriptions or adjustments were made.', '']))
    return folder, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-ledger', required=True, type=Path);parser.add_argument('--as-of', required=True)
    parser.add_argument('--costs-file', type=Path);parser.add_argument('--output-dir', type=Path, default=ROOT/'runtime/accounting-evaluation')
    args = parser.parse_args()
    try:folder,r = run(args.source_ledger, args.as_of, args.output_dir, args.costs_file)
    except (ValueError, KeyError, TypeError, ArithmeticError, OSError, sqlite3.Error) as exc:
        parser.exit(1, f'Accounting proof failed: {type(exc).__name__}; no source-ledger writes\n')
    print(json.dumps({'report': str(folder/'report.md'), 'custody': r['custody']['status'], 'net_pnl_usd': None, 'orders_enabled': False}))


if __name__ == '__main__':main()
