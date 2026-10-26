from decimal import Decimal, localcontext
import json
import sqlite3

import pytest

from backend.accounting_engine import at, cost_report, digest, evaluate, readonly, run, source_snapshot
from backend.store import Store

KNOWN = '2026-01-02T12:00:00+00:00'
CUTOFF = at(KNOWN)


def source():
    return {'orders': [], 'fills': [], 'activities': [], 'equity': [], 'issues': {},
            'state': {'mode': 'simulator', 'account_snapshot': {'at': KNOWN, 'positions': [], 'account': {'currency': 'USD'}}}}


def fill(data, identity, side, qty, price, book='swing', symbol='BTC', when=KNOWN):
    data['orders'].append({'client_id': identity, 'request': json.dumps({'intent': {'strategy_id': book}}), 'external': 0, 'created_at': when})
    data['fills'].append({'id': identity, 'client_id': identity, 'at': when, 'payload': json.dumps({
        'id': identity, 'client_id': identity, 'at': when, 'side': side, 'quantity': qty, 'price': price,
        'value': str(Decimal(qty)*Decimal(price)), 'symbol': symbol, 'source': 'simulator', 'fee': None})})


def activity(data, identity, kind='CFEE', **fields):
    payload = {'id': identity, 'activity_type': kind, 'status': 'executed', **fields}
    data['activities'].append({'id': identity, 'type': kind, 'at': KNOWN, 'payload': json.dumps(payload)})


def costs():
    return {'version': 1, 'charge_coverage_complete': False, 'subscription_coverage_complete': False, 'charges': [], 'subscriptions': []}


def charge(identity='invoice', **fields):
    return {'id': identity, 'provider': 'fixture', 'status': 'confirmed', 'currency': 'USD', 'amount': '10',
            'known_at': KNOWN, 'incurred_at': KNOWN, 'source_ref': identity, **fields}


def plan(identity='plan', **fields):
    return {'id': identity, 'provider': 'fixture', 'status': 'active', 'billing_interval': 'monthly',
            'billing_amount': '10', 'currency': 'USD', 'known_at': KNOWN, 'source_ref': 'user-confirmation', **fields}


@pytest.mark.parametrize('url', [
    'javascript:alert(1)', 'http://mail.google.com/mail/u/0/#all/0123456789abcdef',
    'https://example.com/mail/u/0/#all/0123456789abcdef',
    'https://mail.google.com@evil.example/mail/u/0/#all/0123456789abcdef',
    'https://user:secret@mail.google.com/mail/u/0/#all/0123456789abcdef',
    'https://mail.google.com/mail/u/0/?redirect=https://evil.example#all/0123456789abcdef',
    'file:///private/receipt.pdf',
])
def test_untrusted_receipt_destinations_are_rejected(url):
    doc = costs();doc['charges'] = [charge(receipt_url=url)]
    with pytest.raises(ValueError):cost_report(doc, CUTOFF)


@pytest.mark.parametrize('status', ['estimated', 'unknown'])
def test_unconfirmed_expense_cannot_publish_a_receipt_link(status):
    doc = costs();doc['charges'] = [charge(status=status, receipt_url='https://mail.google.com/mail/u/0/#all/0123456789abcdef')]
    with pytest.raises(ValueError, match='confirmed ordinary'):cost_report(doc, CUTOFF)


def test_fifo_partial_sales_and_horizons_remain_separate():
    data = source()
    fill(data, 'a', 'buy', '2', '100', when='2026-01-01T12:00:00+00:00')
    fill(data, 'b', 'buy', '1', '200', when='2026-01-01T13:00:00+00:00')
    fill(data, 'c', 'buy', '1', '1000', 'intraday', when='2026-01-01T14:00:00+00:00')
    fill(data, 'd', 'sell', '2.5', '300')
    fill(data, 'e', 'sell', '1', '900', 'intraday')
    data['state']['account_snapshot']['positions'] = [{'symbol': 'BTCUSD', 'qty': '0.5'}]
    report = evaluate(data, None, CUTOFF)
    assert report['custody']['status'] == 'matched_quantities_only'
    gross = report['gross_fifo_diagnostics']
    assert gross['status'] == 'retained_gross_records_only'
    assert {x['book']: Decimal(x['gross_realized_usd']) for x in gross['by_book']} == {'swing': Decimal('450'), 'intraday': Decimal('-100')}
    assert [Decimal(x['quantity']) for x in gross['matches']] == [Decimal('2'), Decimal('0.5'), Decimal('1')]
    assert report['money_results']['realized_net_pnl_usd'] is None
    assert report['learning_outcomes'] == []
    assert not any(report['authority'].values())


def test_sale_cannot_borrow_another_books_lot():
    data = source();fill(data, 'a', 'buy', '1', '100', 'swing');fill(data, 'b', 'sell', '1', '110', 'intraday')
    report = evaluate(data, None, CUTOFF)
    assert report['issues']['sell_exceeds_same_book_lots'] == 1
    assert report['gross_fifo_diagnostics']['status'] == 'incomplete'
    assert not report['gross_fifo_diagnostics']['matches']
    assert report['custody']['status'] == 'needs_review'


def test_retained_execution_pilot_uses_manual_book_and_preserves_strategy_identity():
    data = source();fill(data, 'a', 'buy', '1', '100', 'lifecycle_test');fill(data, 'b', 'sell', '1', '101', 'lifecycle_test')
    report = evaluate(data, None, CUTOFF)
    assert report['gross_fifo_diagnostics']['by_book'] == [{'symbol': 'BTC', 'book': 'manual', 'gross_realized_usd': '1'}]
    assert all(f['strategy_id'] == 'lifecycle_test' for f in report['_fill_export'])
    assert 'unknown_fill_owner' not in report['issues']


def test_missing_fee_is_not_an_invented_adjustment():
    data = source();fill(data, 'a', 'buy', '1', '100');fill(data, 'b', 'sell', '0.999998445', '101')
    report = evaluate(data, None, CUTOFF)
    assert Decimal(report['custody']['differences'][0]['unexplained_quantity']) == Decimal('-0.000001555')
    assert report['issues']['unreconciled_custody'] == 1
    assert report['fees']['known_cash_fee_debits_by_currency'] == {}
    assert report['money_results']['realized_net_pnl_usd'] is None


def test_confirmed_asset_fee_and_cash_fee_are_not_counted_twice():
    data = source();fill(data, 'a', 'buy', '1', '100');fill(data, 'b', 'sell', '0.99', '101')
    activity(data, 'asset-fee', symbol='BTC/USD', qty='-0.01')
    activity(data, 'cash-fee', 'FEE', currency='USD', net_amount='-0.25')
    report = evaluate(data, None, CUTOFF)
    assert report['custody']['status'] == 'matched_quantities_only'
    assert Decimal(report['custody']['differences'][0]['unexplained_quantity']) == 0
    assert report['fees']['known_cash_fee_debits_by_currency'] == {'USD': '0.25'}
    assert report['money_results']['realized_net_pnl_usd'] is None


@pytest.mark.parametrize('change,issue', [({'status': 'pending'}, 'pending_fee_confirmation'),
    ({'qty': '0.01'}, 'invalid_fee_record'), ({'qty': 'NaN'}, 'invalid_fee_record'),
    ({'date': '2026-01-03'}, 'invalid_fee_record')])
def test_unconfirmed_invalid_or_future_fee_cannot_change_custody(change, issue):
    data = source();fill(data, 'a', 'buy', '0.01', '100')
    activity(data, 'fee', symbol='BTCUSD', qty='-0.01', **{k: v for k,v in change.items() if k != 'qty'})
    if 'qty' in change:
        p = json.loads(data['activities'][0]['payload']);p.update(change);data['activities'][0]['payload'] = json.dumps(p)
    report = evaluate(data, None, CUTOFF)
    assert report['issues'][issue] == 1
    assert Decimal(report['custody']['differences'][0]['unexplained_quantity']) == Decimal('-0.01')


@pytest.mark.parametrize('when', ['2026-01-02T11:58:59+00:00', '2026-01-02T12:00:01+00:00'])
def test_stale_or_future_snapshot_cannot_reconcile(when):
    data = source();data['state']['account_snapshot']['at'] = when
    report = evaluate(data, None, CUTOFF)
    assert not report['custody']['snapshot_current']
    assert report['custody']['differences'] == []
    assert report['issues']['custody_snapshot_missing_stale_or_after_cutoff'] == 1


def test_nonusd_unknown_source_invalid_fill_and_cash_flow_stay_visible():
    data = source();fill(data, 'bad', 'buy', '1', '100', symbol='BTCEUR');fill(data, 'owner', 'buy', '1', '100')
    data['orders'].pop()
    p = json.loads(data['fills'][1]['payload']);p['source'] = 'unknown';data['fills'][1]['payload'] = json.dumps(p)
    activity(data, 'deposit', 'CSD', net_amount='1000')
    data['state']['account_snapshot']['account']['currency'] = 'EUR'
    report = evaluate(data, None, CUTOFF)
    assert report['issues'] == {'invalid_fill_record': 1, 'unknown_fill_owner': 1, 'unverified_fill_source': 1,
        'account_currency_unverified': 1, 'unsupported_cash_flow_activity': 1, 'custody_snapshot_missing_stale_or_after_cutoff': 1}
    assert report['gross_fifo_diagnostics']['status'] == 'incomplete'


def test_equity_change_is_not_trading_profit():
    data = source();data['equity'] = [{'at': '2026-01-01T00:00:00+00:00', 'value': '10000'}, {'at': KNOWN, 'value': '11000'}]
    results = evaluate(data, None, CUTOFF)['money_results']
    assert results['observed_equity_change_usd'] == '1000'
    assert results['cash_flow_adjusted_pnl_usd'] is None


def test_employer_reimbursed_subscription_keeps_gross_but_no_personal_budget():
    doc = costs();doc['subscriptions'] = [plan(provider='OpenAI/Codex', billing_amount='500', personal_fraction='0', funding_note='Employer reimbursed per user')]
    report = cost_report(doc, CUTOFF)
    assert report['gross_monthly_subscription_budget_by_currency'] == {'USD': '500'}
    assert report['monthly_personal_budget_by_currency'] == {'USD': '0'}
    assert report['monthly_astral_personal_budget_by_currency'] == {'USD': '0'}
    assert report['actual_total_by_currency'] is None
    assert not report['monthly_budget_complete']
    assert not report['charges']


def test_invoice_dedup_bundle_allocation_and_estimate_separation():
    doc = costs();doc['charges'] = [charge(), charge(), charge('portion', amount='4', role='included_allocation', parent_charge_id='invoice'),
                                    charge('estimate', amount='2', status='estimated'), charge('euro', currency='EUR', amount='3')]
    doc['charge_coverage_complete'] = True
    report = cost_report(doc, CUTOFF)
    assert report['recorded_confirmed_charges_by_currency'] == {'EUR': '3', 'USD': '10'}
    assert report['estimated_charges_by_currency'] == {'USD': '2'}
    assert report['actual_total_by_currency'] is None
    assert len(report['charges']) == 4
    doc['charges'] = [charge()];report = cost_report(doc, CUTOFF)
    assert report['actual_total_by_currency'] == {'USD': '10'}


@pytest.mark.parametrize('extra', [charge(amount='11'), charge('duplicate', source_ref='invoice'),
    charge('portion', amount='11', role='included_allocation', parent_charge_id='invoice')])
def test_conflicts_duplicate_receipts_and_excess_allocations_fail(extra):
    doc = costs();doc['charges'] = [charge(), extra]
    with pytest.raises(ValueError):cost_report(doc, CUTOFF)


@pytest.mark.parametrize('amount', ['NaN', 'Infinity', '-1', 1.5, True])
def test_invalid_cost_amount_is_rejected(amount):
    doc = costs();doc['charges'] = [charge(amount=amount)]
    with pytest.raises((ValueError, ArithmeticError)):cost_report(doc, CUTOFF)


def test_annual_allocated_mixed_currency_and_unknown_plans_do_not_guess_total():
    doc = costs();doc['subscription_coverage_complete'] = True
    doc['subscriptions'] = [plan(billing_interval='annual', billing_amount='120', personal_fraction='0.5', astral_fraction='0.25'),
                            plan('eur', billing_amount='12', currency='EUR'), plan('unknown', billing_amount=None)]
    report = cost_report(doc, CUTOFF)
    assert report['monthly_personal_budget_by_currency'] == {'EUR': '12', 'USD': '5.0'}
    assert report['monthly_astral_personal_budget_by_currency'] == {'EUR': '12', 'USD': '1.250'}
    assert not report['monthly_budget_complete']
    assert report['exclusions']['unknown_active_subscriptions'] == 1


def test_future_costs_are_excluded_and_decimal_precision_is_fixed():
    doc = costs();doc['charges'] = [charge(known_at='2026-01-03T00:00:00+00:00')]
    doc['subscriptions'] = [plan(billing_interval='annual', billing_amount='1')]
    with localcontext() as ctx:
        ctx.prec = 4;a = cost_report(doc, CUTOFF)
        ctx.prec = 60;b = cost_report(doc, CUTOFF)
    assert a == b
    assert a['recorded_confirmed_charges_by_currency'] == {}
    assert a['exclusions']['after_cutoff_charges'] == 1


def test_readonly_cutoff_contract_and_private_exports(tmp_path):
    path = tmp_path/'source.sqlite';store = Store(path, 'simulator')
    store.put('account_snapshot', source()['state']['account_snapshot']);store.close()
    data = source();fill(data, 'a', 'buy', '1', '100')
    with sqlite3.connect(path) as db:
        for r in data['orders']:
            db.execute('INSERT INTO orders VALUES(?,?,?,?,?,?,?,?)', (r['client_id'], r['request'], '{}', 'filled', 0, 0, KNOWN, KNOWN))
        r = data['fills'][0];db.execute('INSERT INTO fills VALUES(?,?,?,?)', (r['id'], r['client_id'], KNOWN, r['payload']))
        db.execute('INSERT INTO fills VALUES(?,?,?,?)', ('future', 'future', '2026-01-03T00:00:00+00:00', 'DO NOT PARSE'))
    before = path.read_bytes()
    with readonly(path) as db:
        with pytest.raises(sqlite3.OperationalError):db.execute('DELETE FROM fills')
    assert source_snapshot(path, CUTOFF)['issues'] == {'after_cutoff_fills': 1}
    a, r1 = run(path, KNOWN, tmp_path/'out');b, r2 = run(path, KNOWN, tmp_path/'out')
    assert a != b and r1 == r2 and path.read_bytes() == before
    contract = json.loads((a/'contract.json').read_text());assert r1['contract_sha256'] == digest(contract)
    assert 'simulator' in (a/'fills.csv').read_text()
    assert 'DO NOT PARSE' not in (a/'fills.csv').read_text()
    assert all(p.stat().st_mode & 0o077 == 0 for p in a.iterdir())
    with pytest.raises(FileNotFoundError):source_snapshot(tmp_path/'absent.sqlite', CUTOFF)
    assert not (tmp_path/'absent.sqlite').exists()
    with pytest.raises(ValueError):run(path, '2999-01-01T00:00:00+00:00', tmp_path/'out')
