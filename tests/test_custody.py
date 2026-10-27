"""Synthetic custody receipts: net ownership never certifies unknown fees."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import sqlite3

import pytest

from backend.accounting_engine import at, evaluate, source_snapshot
from backend.config import Settings
from backend.custody import analyze, retain_checkpoint, retained
from backend.engine import Engine
from backend.inventory import attribute
from backend.store import Store, dumps
from test_service import run

START = datetime(2026, 1, 2, 12, tzinfo=timezone.utc)


def clock(seconds):
    return (START+timedelta(seconds=seconds)).isoformat()


def snapshot(seconds, qty='0'):
    return {'at': clock(seconds), 'account': {'id': 'paper-fixture', 'currency': 'USD', 'cash': '100000', 'equity': '100000'},
            'positions': [] if Decimal(qty)==0 else [{'symbol': 'BTCUSD', 'qty': qty, 'qty_available': qty,
                'market_value': '25', 'cost_basis': '25', 'unrealized_pl': '0'}],
            'clock': {'is_open': True}}


@pytest.fixture
def ledger(tmp_path):
    store = Store(tmp_path/'paper.sqlite', 'alpaca')
    store.put('account_binding', 'paper-fixture');store.put('account_snapshot', snapshot(59))
    for cid, side, qty, second in [('buy-a','buy','0.000309121',2), ('sell-a','sell','0.000308347',6),
                                  ('buy-b','buy','0.000311568',32), ('sell-b','sell','0.000310787',36)]:
        raw = {'id': 'broker-'+cid, 'client_order_id': cid, 'symbol': 'BTC/USD', 'side': side,
               'status': 'filled', 'filled_qty': qty, 'submitted_at': clock(second-1), 'filled_at': clock(second)}
        request = {'intent': {'strategy_id': 'manual', 'client_order_id': cid}}
        store.db.execute('INSERT INTO orders VALUES(?,?,?,?,?,?,?,?)', (cid,dumps(request),dumps(raw),'filled',0,0,clock(second-1),clock(second+.1)))
        # Two cumulative deltas for the first buy protect partial-fill summation.
        parts = ['0.0001238','0.000185321'] if cid=='buy-a' else [qty]
        for i, part in enumerate(parts):
            payload = {'id': cid+str(i), 'client_id': cid, 'symbol': 'BTC', 'side': side, 'quantity': part,
                       'price': '80000', 'value': str(Decimal(part)*80000), 'fee': None,
                       'at': clock(second), 'source': 'alpaca-cumulative-order-readback'}
            store.db.execute('INSERT INTO fills VALUES(?,?,?,?)', (payload['id'],cid,clock(second+.1),dumps(payload)))
    for second, qty in [(0,'0'), (4,'0.000308347'), (30,'0'), (34,'0.000310787')]:
        store.db.execute('INSERT INTO observations(at,request,outcome,context) VALUES(?,?,?,?)',
                         (clock(second+.2),'{}','approved',dumps({'snapshot':snapshot(second,qty),'working_orders':[]})))
    yield store
    store.close()


def analysis(store, **changes):
    data = dict(**retained(store), snapshot=store.get('account_snapshot'), account_id=store.get('account_binding'), mode='alpaca')
    data.update(changes)
    return analyze(**data)


def fee(store, cid, qty, identity='fee-a', when=None):
    payload = {'id':identity,'activity_type':'CFEE','symbol':'BTCUSD','qty':qty,'status':'executed'}
    if cid:payload['order_id']='broker-'+cid
    store.db.execute('INSERT INTO activities VALUES(?,?,?,?)', (identity,'CFEE',when or clock(50),dumps(payload)))


def test_roundtrip_uses_observed_net_custody_and_keeps_unknown_fees_blocked(ledger):
    before = retained(ledger)
    inv = attribute(ledger, ledger.get('account_snapshot'))
    assert Decimal(inv['gross_books']['BTC']['manual']) == Decimal('0.000001555')
    assert Decimal(inv['books']['BTC']['manual']) == 0
    assert inv['differences'] == [] and inv['status'] == 'needs-review'
    assert {r['classification'] for r in inv['custody_reconciliation']['reductions']} == {'unclassified'}
    assert [Decimal(r['quantity']) for r in inv['custody_reconciliation']['reductions']] == [Decimal('.000000774'),Decimal('.000000781')]
    assert inv['errors'] and retained(ledger) == before
    data = source_snapshot(ledger.db.execute('PRAGMA database_list').fetchone()['file'], at(clock(59)))
    report = evaluate(data, None, at(clock(59)))
    assert Decimal(report['custody']['differences'][0]['recorded_net_quantity']) == 0
    assert Decimal(report['custody']['differences'][0]['gross_quantity']) == Decimal('.000001555')
    assert report['custody']['status'] == 'needs_review'
    assert report['issues']['custody_debit_requires_review'] == 1
    assert report['money_results']['realized_net_pnl_usd'] is None
    assert not any(report['authority'].values())


def test_linked_late_fee_replaces_observed_debit_without_charging_twice(ledger):
    fee(ledger,'buy-a','-0.000000774')
    mixed = attribute(ledger,ledger.get('account_snapshot'))
    assert Decimal(mixed['books']['BTC']['manual']) == 0 and mixed['status']=='needs-review'
    assert Decimal(mixed['custody_reconciliation']['additional_debits']['BTC']['manual']) == Decimal('.000000781')
    fee(ledger,'buy-b','-0.000000781','fee-b')
    inv = attribute(ledger,ledger.get('account_snapshot'))
    assert Decimal(inv['books']['BTC']['manual']) == 0 and inv['status']=='matched'
    assert {r['classification'] for r in inv['custody_reconciliation']['reductions']} == {'confirmed-fee'}
    before=retained(ledger)
    assert attribute(ledger,ledger.get('account_snapshot'))==inv and retained(ledger)==before
    report = evaluate(source_snapshot(ledger.db.execute('PRAGMA database_list').fetchone()['file'],at(clock(59))),None,at(clock(59)))
    assert Decimal(report['custody']['differences'][0]['recorded_net_quantity'])==0
    assert report['custody']['status']=='matched_quantities_only'
    assert report['money_results']['realized_net_pnl_usd'] is None


@pytest.mark.parametrize('cutoff_seconds', [59,43200,43201], ids=['intraday','next-utc-midnight','after-utc-midnight'])
def test_date_only_linked_fees_preserve_precision_and_require_review_until_day_ends(ledger,cutoff_seconds):
    fee(ledger,'buy-a','-0.000000774',when='2026-01-02')
    fee(ledger,'buy-b','-0.000000781','fee-b',when='2026-01-02')
    ledger.put('account_snapshot',snapshot(cutoff_seconds))
    inv=attribute(ledger,ledger.get('account_snapshot'))
    assert Decimal(inv['books']['BTC']['manual'])==0 and inv['status']=='matched'
    assert len(inv['custody_reconciliation']['reductions'])==2
    assert {r['classification'] for r in inv['custody_reconciliation']['reductions']}=={'confirmed-fee'}
    assert inv['errors']==[]
    source=source_snapshot(ledger.db.execute('PRAGMA database_list').fetchone()['file'],at(clock(cutoff_seconds)))
    report=evaluate(source,None,at(clock(cutoff_seconds)))
    assert report['fees']['recorded_rows']==2
    assert report['custody']['status']==('needs_review' if cutoff_seconds<43200 else 'matched_quantities_only')
    assert report['issues'].get('day_precision_fee_on_cutoff_date',0)==(2 if cutoff_seconds<43200 else 0)
    assert Decimal(report['custody']['differences'][0]['recorded_net_quantity'])==0
    assert {r['time_precision'] for r in report['_fee_export']}=={'day'}
    assert {r['known_at'] for r in report['_fee_export']}=={'2026-01-02'}
    assert {r['at'] for r in source['activities']}=={'2026-01-02'}
    assert report['money_results']['realized_net_pnl_usd'] is None


@pytest.mark.parametrize('evidence', ['snapshot','execution'])
def test_date_only_custody_or_execution_timestamps_remain_invalid(ledger,evidence):
    data=retained(ledger)
    row=data['observations'][0] if evidence=='snapshot' else data['fills'][0]
    field='context' if evidence=='snapshot' else 'payload'
    payload=json.loads(row[field])
    if evidence=='snapshot':payload['snapshot']['at']='2026-01-02'
    else:payload['at']='2026-01-02'
    row[field]=dumps(payload)
    result=analysis(ledger,**data)
    assert not result['reductions'] and result['issues']


def test_local_rejection_without_broker_evidence_does_not_discard_valid_reductions(ledger):
    baseline=analysis(ledger);data=retained(ledger)
    rejected={**data['orders'][0],'client_id':'rejected','status':'rejected','raw':'{}'}
    data['orders'].append(rejected)
    assert analysis(ledger,**data)==baseline


@pytest.mark.parametrize('status,has_fill,external', [
    ('unknown',False,0),('submitting',False,0),('filled',False,0),
    ('canceled',False,0),('expired',False,0),('replaced',False,0),
    ('rejected',True,0),('rejected',False,1),
], ids=['unknown','submitting','filled','canceled','expired','replaced','rejected-with-fill','external-rejection'])
def test_missing_broker_evidence_is_only_ignored_for_local_unfilled_rejections(ledger,status,has_fill,external):
    data=retained(ledger)
    row={**data['orders'][0],'client_id':'missing-broker','status':status,'raw':'{}','external':external}
    data['orders'].append(row)
    if has_fill:
        fill=deepcopy(data['fills'][0]);payload=json.loads(fill['payload'])
        payload.update(id='rejected-fill',client_id=row['client_id'])
        fill.update(id=payload['id'],client_id=row['client_id'],payload=dumps(payload));data['fills'].append(fill)
    result=analysis(ledger,**data)
    assert not result['reductions'] and not result['additional_debits'] and result['issues']


@pytest.mark.parametrize('working', [[],['unrecorded']], ids=['no-working-order','unresolved-working-order'])
def test_stale_observation_is_excluded_without_losing_valid_reductions_or_review(ledger,working):
    baseline=analysis(ledger)
    ledger.db.execute('INSERT INTO observations(at,request,outcome,context) VALUES(?,?,?,?)',
                     (clock(23),'{}','approved',dumps({'snapshot':snapshot(3,'1'),'working_orders':working})))
    result=analysis(ledger)
    assert result['reductions']==baseline['reductions'] and result['additional_debits']==baseline['additional_debits']
    assert any('Stale custody checkpoint' in i['reason'] for i in result['issues'])
    assert not any('Invalid custody evidence' in i['reason'] for i in result['issues'])
    fee(ledger,'buy-a','-0.000000774');fee(ledger,'buy-b','-0.000000781','fee-b')
    inv=attribute(ledger,ledger.get('account_snapshot'))
    assert Decimal(inv['books']['BTC']['manual'])==0 and inv['status']=='needs-review'
    assert any('Stale custody checkpoint' in i['reason'] for i in inv['errors'])


@pytest.mark.parametrize('condition', ['negative-lag','wrong-account','wrong-currency'])
def test_invalid_observation_identity_or_negative_lag_still_blocks_all_reductions(ledger,condition):
    snap=snapshot(3,'1')
    if condition=='wrong-account':snap['account']['id']='another-account'
    if condition=='wrong-currency':snap['account']['currency']='EUR'
    ledger.db.execute('INSERT INTO observations(at,request,outcome,context) VALUES(?,?,?,?)',
                     (clock(2 if condition=='negative-lag' else 23),'{}','approved',dumps({'snapshot':snap,'working_orders':[]})))
    result=analysis(ledger)
    assert not result['reductions'] and not result['additional_debits'] and result['issues']


@pytest.mark.parametrize('status,terminal_field', [
    ('canceled','canceled_at'),('expired','expired_at'),('rejected','failed_at'),('replaced','replaced_at'),
])
def test_unfilled_order_terminated_before_checkpoints_does_not_overlap_later_buys(ledger,status,terminal_field):
    baseline=analysis(ledger);data=retained(ledger)
    other={**data['orders'][0],'client_id':'earlier','status':status}
    raw=json.loads(other['raw']);raw.update(id='broker-earlier',client_order_id='earlier',status=status,
        submitted_at=clock(-10),filled_qty='0',filled_at=None)
    raw[terminal_field]=clock(-1);other['raw']=dumps(raw);data['orders'].append(other)
    assert analysis(ledger,**data)==baseline


@pytest.mark.parametrize('status,terminal_field', [('canceled','canceled_at'),('expired','expired_at')])
@pytest.mark.parametrize('termination', ['before','overlapping','missing','nonterminal'])
def test_partial_fill_time_cannot_end_an_order_before_cancellation_or_expiry(ledger,status,terminal_field,termination):
    baseline=analysis(ledger);data=retained(ledger)
    other={**data['orders'][0],'client_id':'earlier','status':'unknown' if termination=='nonterminal' else status}
    raw=json.loads(other['raw']);raw.update(id='broker-earlier',client_order_id='earlier',status=other['status'],
        submitted_at=clock(-10),filled_qty='0.001',filled_at=clock(-5))
    if termination!='missing':raw[terminal_field]=clock(40 if termination=='overlapping' else -1)
    other['raw']=dumps(raw);data['orders'].append(other)
    result=analysis(ledger,**data)
    if termination=='before':assert result==baseline
    else:assert not result['reductions'] and not result['additional_debits']


@pytest.mark.parametrize('overlaps', [False,True], ids=['isolated-order','overlapping-order'])
def test_canceled_partial_fill_with_ingest_time_only_preserves_unrelated_reductions_and_review(ledger,monkeypatch,overlaps):
    fee(ledger,'buy-a','-0.000000774');fee(ledger,'buy-b','-0.000000781','fee-b')
    baseline=analysis(ledger)
    assert attribute(ledger,ledger.get('account_snapshot'))['status']=='matched'
    submitted,canceled,received=(1.5,2.5,3) if overlaps else (44,45,46)
    cid='canceled-partial'
    request={'intent':{'strategy_id':'manual','client_order_id':cid}}
    ledger.db.execute('INSERT INTO orders VALUES(?,?,?,?,?,?,?,?)',
        (cid,dumps(request),'{}','submitting',0,0,clock(submitted),clock(submitted)))
    raw={'id':'broker-'+cid,'client_order_id':cid,'symbol':'BTC/USD','side':'buy','status':'canceled',
         'qty':'0.002','filled_qty':'0.001','filled_avg_price':'80000','submitted_at':clock(submitted),
         'canceled_at':clock(canceled),'filled_at':None}
    monkeypatch.setattr('backend.engine.utcnow',lambda:clock(received))
    Engine(Settings(mode='alpaca'),ledger,object()).ingest(raw)
    ledger.put('account_snapshot',snapshot(59,'0.001'))
    assert json.loads(ledger.rows('SELECT payload FROM fills WHERE client_id=?',(cid,))[0]['payload'])['at']==clock(received)
    result=analysis(ledger)
    expected=[r for r in baseline['reductions'] if not overlaps or r['client_id']=='buy-b']
    assert result['reductions']==expected
    assert any(i.get('client_id')==cid and 'execution time outside terminal window' in i['reason'] for i in result['issues'])
    inv=attribute(ledger,ledger.get('account_snapshot'))
    assert Decimal(inv['books']['BTC']['manual'])==Decimal('0.001')
    assert inv['differences']==[] and inv['status']=='needs-review'


@pytest.mark.parametrize('conflict', ['side','symbol','identity'])
def test_fill_side_symbol_and_order_identity_conflicts_still_invalidate_all_custody_evidence(ledger,conflict):
    data=retained(ledger)
    if conflict=='identity':
        raw=json.loads(data['orders'][0]['raw']);raw['client_order_id']='another-client'
        data['orders'][0]['raw']=dumps(raw)
    else:
        fill=json.loads(data['fills'][0]['payload']);fill[conflict]='sell' if conflict=='side' else 'ETH'
        data['fills'][0]['payload']=dumps(fill)
    result=analysis(ledger,**data)
    assert result['reductions']==[] and result['additional_debits']=={}
    assert any('Invalid custody evidence' in i['reason'] for i in result['issues'])


def test_linked_fees_after_last_snapshot_share_inventory_cutoff_without_double_debits(ledger,monkeypatch):
    fee(ledger,'buy-a','-0.000000774',when=clock(60))
    monkeypatch.setattr('backend.inventory.utcnow',lambda:clock(59.5))
    before=attribute(ledger,ledger.get('account_snapshot'))
    assert Decimal(before['books']['BTC']['manual'])==0
    assert Decimal(before['custody_reconciliation']['additional_debits']['BTC']['manual'])==Decimal('.000001555')
    monkeypatch.setattr('backend.inventory.utcnow',lambda:clock(60))
    mixed=attribute(ledger,ledger.get('account_snapshot'))
    assert Decimal(mixed['books']['BTC']['manual'])==0 and mixed['status']=='needs-review'
    assert Decimal(mixed['custody_reconciliation']['additional_debits']['BTC']['manual'])==Decimal('.000000781')
    fee(ledger,'buy-b','-0.000000781','fee-b',when=clock(60))
    inv=attribute(ledger,ledger.get('account_snapshot'))
    assert Decimal(inv['books']['BTC']['manual'])==0 and inv['status']=='matched'
    assert Decimal(inv['custody_reconciliation']['additional_debits']['BTC']['manual'])==0
    # Historical accounting still excludes fees after its explicit cutoff.
    report=evaluate(source_snapshot(ledger.db.execute('PRAGMA database_list').fetchone()['file'],at(clock(59))),None,at(clock(59)))
    assert {r['classification'] for r in report['custody']['gross_to_net']['reductions']}=={'unclassified'}
    assert Decimal(report['custody']['differences'][0]['recorded_net_quantity'])==0
    ledger.put('account_snapshot',snapshot(61));monkeypatch.setattr('backend.inventory.utcnow',lambda:clock(61))
    advanced=attribute(ledger,ledger.get('account_snapshot'))
    assert advanced['books']==inv['books'] and advanced['status']=='matched'


def test_invalid_fee_timestamp_keeps_inventory_reviewable_and_blocked(ledger):
    fee(ledger,'buy-a','-0.000000774',when='invalid')
    inv=attribute(ledger,ledger.get('account_snapshot'))
    assert inv['status']=='needs-review' and inv['errors']
    assert not inv['custody_reconciliation']['reductions']


@pytest.mark.parametrize('linked,amount', [(None,'-0.000001555'),('buy-a','-0.000002')], ids=['unlinked-overlap','excess-linked-fee'])
def test_ambiguous_or_conflicting_fee_cannot_clear_review_or_double_charge(ledger,linked,amount):
    fee(ledger,linked,amount)
    inv = attribute(ledger,ledger.get('account_snapshot'))
    assert inv['status']=='needs-review' and inv['errors']
    # Unlinked overlap suppresses all measured adjustments; an excess linked
    # fee suppresses that order's adjustment. Neither fee is charged twice.
    for r in inv['custody_reconciliation']['reductions']:
        if linked is None or r['client_id']==linked:
            assert r['classification']=='ambiguous' and Decimal(r['additional_debit_quantity'])==0


@pytest.mark.parametrize('fee_at,first_debit,ambiguous', [
    (clock(32),'0',True),('2026-01-02','0',True),(clock(50),'0',False),(clock(32),'0.0001',False),
], ids=['cross-order-overlap','cross-order-day-precision','outside-window','covered-by-own-reduction'])
def test_cross_order_fee_overlap_never_charges_the_same_custody_debit_twice(ledger,fee_at,first_debit,ambiguous):
    ledger.db.execute("DELETE FROM orders WHERE client_id LIKE 'sell-%'")
    ledger.db.execute("DELETE FROM fills WHERE client_id LIKE 'sell-%' OR id='buy-a1'")
    for row in retained(ledger)['orders']:
        raw=json.loads(row['raw']);raw['filled_qty']='0.01'
        ledger.db.execute('UPDATE orders SET raw=? WHERE client_id=?',(dumps(raw),row['client_id']))
    for row in retained(ledger)['fills']:
        fill=json.loads(row['payload']);fill.update(quantity='0.01',value='800')
        ledger.db.execute('UPDATE fills SET payload=? WHERE id=?',(dumps(fill),row['id']))
    first_net=Decimal('0.01')-Decimal(first_debit)
    second_net=first_net+Decimal('0.0099')
    ledger.db.execute('DELETE FROM observations')
    for second,qty in [(0,'0'),(4,str(first_net)),(30,str(first_net)),(34,str(second_net))]:
        ledger.db.execute('INSERT INTO observations(at,request,outcome,context) VALUES(?,?,?,?)',
            (clock(second+.1),'{}','approved',dumps({'snapshot':snapshot(second,qty),'working_orders':[]})))
    # A fee outside the measured window is a separate later custody debit.
    expected=second_net-(Decimal('0.0001') if fee_at==clock(50) else Decimal(0))
    ledger.put('account_snapshot',snapshot(59,str(expected)))
    fee(ledger,'buy-a','-0.0001',when=fee_at)
    before=retained(ledger)
    inv=attribute(ledger,ledger.get('account_snapshot'))
    second=next(r for r in inv['custody_reconciliation']['reductions'] if r['client_id']=='buy-b')
    assert Decimal(second['quantity'])==Decimal('0.0001')
    assert second['classification']==('ambiguous' if ambiguous else 'unclassified')
    assert Decimal(second['additional_debit_quantity'])==(Decimal(0) if ambiguous else Decimal('0.0001'))
    assert Decimal(inv['books']['BTC']['manual'])==expected
    assert inv['differences']==[] and inv['status']=='needs-review' and inv['errors']
    source=source_snapshot(ledger.db.execute('PRAGMA database_list').fetchone()['file'],at(clock(59)))
    report=evaluate(source,None,at(clock(59)))
    assert Decimal(report['custody']['differences'][0]['recorded_net_quantity'])==expected
    assert Decimal(report['custody']['differences'][0]['unexplained_quantity'])==0
    assert report['custody']['status']=='needs_review' and report['fees']['recorded_rows']==1
    assert report['money_results']['realized_net_pnl_usd'] is None
    assert attribute(ledger,ledger.get('account_snapshot'))==inv and retained(ledger)==before


@pytest.mark.parametrize('reverse', [False,True], ids=['chronological-inputs','reversed-inputs'])
def test_chained_cross_order_fees_preserve_net_custody_and_ambiguity(tmp_path,monkeypatch,reverse):
    store=Store(tmp_path/'chain.sqlite','alpaca')
    try:
        store.put('account_binding','paper-fixture');store.put('account_snapshot',snapshot(69,'0.0298'))
        buys=[('buy-a',2),('buy-b',32),('buy-c',62)]
        for cid,second in reversed(buys) if reverse else buys:
            raw={'id':'broker-'+cid,'client_order_id':cid,'symbol':'BTC/USD','side':'buy',
                 'status':'filled','filled_qty':'0.01','submitted_at':clock(second-1),'filled_at':clock(second)}
            request={'intent':{'strategy_id':'manual','client_order_id':cid}}
            store.db.execute('INSERT INTO orders VALUES(?,?,?,?,?,?,?,?)',
                (cid,dumps(request),dumps(raw),'filled',0,0,clock(second-1),clock(second+.1)))
            fill={'id':cid,'client_id':cid,'symbol':'BTC','side':'buy','quantity':'0.01',
                  'price':'80000','value':'800','fee':None,'at':clock(second),'source':'alpaca-cumulative-order-readback'}
            store.db.execute('INSERT INTO fills VALUES(?,?,?,?)',(cid,cid,clock(second+.1),dumps(fill)))
        samples=[(0,'0'),(4,'0.01'),(30,'0.01'),(34,'0.0199'),(60,'0.0199'),(64,'0.0298')]
        for second,qty in reversed(samples) if reverse else samples:
            store.db.execute('INSERT INTO observations(at,request,outcome,context) VALUES(?,?,?,?)',
                (clock(second+.1),'{}','approved',dumps({'snapshot':snapshot(second,qty),'working_orders':[]})))
        fees=[('buy-a',32),('buy-b',62)]
        for cid,second in reversed(fees) if reverse else fees:
            fee(store,cid,'-0.0001','fee-'+cid,clock(second))
        monkeypatch.setattr('backend.inventory.utcnow',lambda:clock(69))
        before=retained(store)
        inv=attribute(store,store.get('account_snapshot'))
        assert Decimal(inv['gross_books']['BTC']['manual'])==Decimal('0.03')
        assert Decimal(inv['books']['BTC']['manual'])==Decimal('0.0298')
        assert inv['differences']==[] and inv['status']=='needs-review' and inv['errors']
        source=source_snapshot(tmp_path/'chain.sqlite',at(clock(69)))
        report=evaluate(source,None,at(clock(69)))
        difference=report['custody']['differences'][0]
        assert Decimal(difference['gross_quantity'])==Decimal('0.03')
        assert Decimal(difference['recorded_net_quantity'])==Decimal('0.0298')
        assert Decimal(difference['unexplained_quantity'])==0
        assert report['custody']['status']=='needs_review'
        for result in (inv['custody_reconciliation'],report['custody']['gross_to_net']):
            assert Decimal(result['additional_debits']['BTC']['manual'])==0
            reductions={r['client_id']:r for r in result['reductions']}
            assert set(reductions)=={'buy-b','buy-c'}
            assert all(r['classification']=='ambiguous' and Decimal(r['additional_debit_quantity'])==0
                       and Decimal(r['quantity'])==Decimal('0.0001') for r in reductions.values())
            assert len(result['issues'])==2
        assert report['money_results']['realized_net_pnl_usd'] is None
        assert retained(store)==before
    finally:store.close()


@pytest.mark.parametrize('condition', ['missing','stale','future','wrong-account','conflicting','unknown-working-order','different-owner','unrecorded-order','incomplete-fill'])
def test_incomplete_or_ambiguous_evidence_cannot_explain_a_debit(ledger,condition):
    data = retained(ledger)
    if condition=='missing':data['observations']=[]
    elif condition in {'stale','future','wrong-account','unknown-working-order'}:
        for row in data['observations']:
            ctx=json.loads(row['context'])
            if condition=='stale':row['at']=clock(1000)
            if condition=='future':ctx['snapshot']['at']=clock(1000)
            if condition=='wrong-account':ctx['snapshot']['account']['id']='another-paper-account'
            if condition=='unknown-working-order':ctx['working_orders']=['unrecorded']
            row['context']=dumps(ctx)
    elif condition=='conflicting':
        row=deepcopy(data['observations'][1]);ctx=json.loads(row['context']);ctx['snapshot']['positions'][0]['qty']='1';row['context']=dumps(ctx);data['observations'].append(row)
    elif condition=='different-owner':
        for row in data['orders'][2:]:row['request']=dumps({'intent':{'strategy_id':'intraday'}})
    elif condition=='unrecorded-order':
        other=deepcopy(data['orders'][0]);other.update(client_id='unrecorded',status='unknown')
        raw=json.loads(other['raw']);raw.update(id='broker-unrecorded',client_order_id='unrecorded',filled_at=None,filled_qty='0')
        other['raw']=dumps(raw);data['orders'].append(other)
    else:data['fills']=[r for r in data['fills'] if json.loads(r['payload'])['side']=='sell']
    result=analysis(ledger,**data)
    assert not result['additional_debits']
    # The unchanged gross inventory difference still vetoes cases without a
    # usable checkpoint; malformed/conflicting data adds a separate issue.
    assert not result['reductions']


def test_duplicate_reordered_checkpoints_and_low_decimal_precision_are_idempotent(ledger):
    from decimal import localcontext
    expected=analysis(ledger);data=retained(ledger)
    data['observations']=list(reversed(data['observations']))+[data['observations'][1]]
    data['fills'].reverse()
    with localcontext() as ctx:
        ctx.prec=4
        assert analysis(ledger,**data)==expected


def test_nonzero_starting_custody_is_not_misclassified_as_a_new_fee(ledger):
    data=retained(ledger)
    for row in data['observations']:
        ctx=json.loads(row['context']);snap=ctx['snapshot'];qty=sum((Decimal(p['qty']) for p in snap['positions']),Decimal(0))+1
        ctx['snapshot']=snapshot((at(snap['at'])-START).total_seconds(),str(qty));row['context']=dumps(ctx)
    result=analysis(ledger,**data)
    assert Decimal(result['additional_debits']['BTC']['manual'])==Decimal('.000001555')


def test_custody_checkpoint_lookups_use_primary_keys_amid_quote_history(ledger,monkeypatch):
    baseline=attribute(ledger,ledger.get('account_snapshot'))
    for second,qty in [(0,'0'),(4,'0.000308347')]:
        monkeypatch.setattr('backend.store.utcnow',lambda second=second:clock(second+.1))
        with ledger.transaction():
            retain_checkpoint(ledger,snapshot(second,qty))
            ledger.db.executemany('INSERT INTO events(at,type,payload) VALUES(?,?,?)',
                [(clock(second+.1),'quotes','{}')]*10000)
    assert len(retained(ledger)['checkpoints'])==2
    plans=[];read_rows=ledger.rows
    def capture_event_queries(sql,args=()):
        if 'FROM events' in sql:
            plans.extend(r['detail'] for r in ledger.db.execute('EXPLAIN QUERY PLAN '+sql,args))
        return read_rows(sql,args)
    monkeypatch.setattr(ledger,'rows',capture_event_queries)
    assert attribute(ledger,ledger.get('account_snapshot'))==baseline
    with ledger.transaction():retain_checkpoint(ledger,snapshot(4,'0.000308347'))
    assert plans and all('SEARCH events USING INTEGER PRIMARY KEY' in p and 'SCAN' not in p for p in plans)
    assert len(retained(ledger)['checkpoints'])==2


def test_rolled_back_checkpoint_can_be_retained_again_without_losing_evidence(ledger,monkeypatch):
    monkeypatch.setattr('backend.store.utcnow',lambda:clock(.1))
    with pytest.raises(RuntimeError,match='reconciliation failed'):
        with ledger.transaction():
            retain_checkpoint(ledger,snapshot(0))
            raise RuntimeError('reconciliation failed')
    assert retained(ledger)['checkpoints']==[]
    assert ledger.rows("SELECT seq FROM events WHERE type='custody_snapshot'")==[]
    with ledger.transaction():retain_checkpoint(ledger,snapshot(0))
    checkpoints=retained(ledger)['checkpoints']
    assert len(checkpoints)==1 and json.loads(checkpoints[0]['payload'])['snapshot']==snapshot(0)


def test_future_reconciliation_retains_custody_across_restart_without_duplicate_events(tmp_path,monkeypatch):
    path=tmp_path/'new.sqlite';store=Store(path,'alpaca');cfg=Settings(mode='alpaca',db_path=path)
    class Observer:
        async def snapshot(self):return snapshot(0)
        async def open_orders(self):return []
    monkeypatch.setattr('backend.store.utcnow',lambda:clock(.1))
    e=Engine(cfg,store,Observer());run(e.reconcile());run(e.reconcile())
    assert len(retained(store)['checkpoints'])==1
    store.close();store=Store(path,'alpaca')
    try:
        restarted=Engine(cfg,store,Observer());run(restarted.reconcile())
        assert len(retained(store)['checkpoints'])==1
        snap=snapshot(10,'0.01')
        async def changed():return snap
        restarted.broker.snapshot=changed
        monkeypatch.setattr('backend.store.utcnow',lambda:clock(10.1))
        run(restarted.reconcile())
        assert len(retained(store)['checkpoints'])==2
        assert store.rows('SELECT * FROM fills')==[]
        assert not analysis(store)['reductions']
    finally:store.close()


def test_recorded_checkpoints_recover_net_custody_without_legacy_observations(ledger,monkeypatch):
    for row in retained(ledger)['observations']:
        ctx=json.loads(row['context'])
        monkeypatch.setattr('backend.store.utcnow',lambda received=row['at']:received)
        with ledger.transaction():retain_checkpoint(ledger,ctx['snapshot'])
    ledger.db.execute('DELETE FROM observations')
    path=ledger.db.execute('PRAGMA database_list').fetchone()['file']
    before=source_snapshot(path,at(clock(59)))
    report=evaluate(before,None,at(clock(59)))
    assert not before['observations'] and report['custody']['gross_to_net']['reductions']
    assert Decimal(report['custody']['differences'][0]['recorded_net_quantity'])==0
    inv=attribute(ledger,ledger.get('account_snapshot'))
    assert Decimal(inv['books']['BTC']['manual'])==0 and inv['differences']==[] and inv['status']=='needs-review'
    readonly=sqlite3.connect('file:'+path+'?mode=ro',uri=True)
    readonly.row_factory=sqlite3.Row;readonly.execute('PRAGMA query_only=ON')
    try:
        class View:
            def rows(self,q,args=()):return [dict(r) for r in readonly.execute(q,args)]
            def get(self,k,default=None):
                r=readonly.execute('SELECT value FROM state WHERE key=?',(k,)).fetchone();return json.loads(r[0]) if r else default
        assert attribute(View(),ledger.get('account_snapshot'))==inv
    finally:readonly.close()


def test_partial_fill_checkpoints_preserve_complete_order_reduction(ledger):
    data=retained(ledger)
    part=data['fills'][1];payload=json.loads(part['payload']);payload['at']=clock(3)
    part.update(at=clock(3.1),payload=dumps(payload))
    raw=json.loads(data['orders'][0]['raw']);raw['filled_at']=clock(3);data['orders'][0]['raw']=dumps(raw)
    data['checkpoints']=[{'id':1,'at':clock(2.3),'payload':dumps({'snapshot':snapshot(2.2,'0.00012349'),'working_orders':['buy-a']})}]
    result=analysis(ledger,**data)
    assert Decimal(result['reductions'][0]['quantity'])==Decimal('.000000774')
    assert Decimal(result['additional_debits']['BTC']['manual'])==Decimal('.000001555')


@pytest.mark.parametrize('baseline', [True,False], ids=['complete-window','missing-pre-submission-baseline'])
def test_delayed_cumulative_fill_does_not_charge_position_already_seen_mid_order(ledger,baseline):
    data=retained(ledger);data['orders']=data['orders'][:1]
    raw=json.loads(data['orders'][0]['raw']);raw.update(filled_qty='0.01',submitted_at=clock(1),filled_at=clock(10))
    data['orders'][0].update(raw=dumps(raw),updated_at=clock(10.1))
    payload=json.loads(data['fills'][0]['payload']);payload.update(quantity='0.01',value='800',at=clock(10))
    data['fills']=[{**data['fills'][0],'payload':dumps(payload),'at':clock(10.1)}]
    data['observations']=[]
    samples=[(0,'0',[]),(3,'0.004',['buy-a']),(11,'0.00995',[])]
    data['checkpoints']=[{'id':i,'at':clock(t+.1),'payload':dumps({'snapshot':snapshot(t,q),'working_orders':working})}
        for i,(t,q,working) in enumerate(samples if baseline else samples[1:])]
    result=analysis(ledger,**data,snapshot=snapshot(12,'0.00995'))
    assert [Decimal(r['quantity']) for r in result['reductions']]==([Decimal('.00005')] if baseline else [])
    if baseline:assert Decimal(result['additional_debits']['BTC']['manual'])==Decimal('.00005')
    else:assert result['additional_debits']=={}


@pytest.mark.parametrize('effective,known', [(70,70.1),(3,70.1)], ids=['future-cancellation','late-known-cancellation'])
def test_historical_report_cannot_clear_review_using_terminal_state_known_after_cutoff(ledger,effective,known):
    row=ledger.order('buy-a');raw=json.loads(row['raw']);raw.update(status='canceled',canceled_at=clock(effective),qty='0.001')
    ledger.db.execute('UPDATE orders SET status=?,raw=?,updated_at=? WHERE client_id=?',('canceled',dumps(raw),clock(known),'buy-a'))
    fee(ledger,'buy-a','-0.000000774');fee(ledger,'buy-b','-0.000000781','fee-b')
    source=source_snapshot(ledger.db.execute('PRAGMA database_list').fetchone()['file'],at(clock(59)))
    report=evaluate(source,None,at(clock(59)))
    assert report['custody']['status']=='needs_review'
    assert any('Terminal order evidence unavailable' in i['reason'] for i in report['custody']['gross_to_net']['issues'])


def test_future_dated_fee_cannot_clear_live_review_when_gross_custody_matches(ledger,monkeypatch):
    ledger.db.execute('DELETE FROM observations')
    ledger.put('account_snapshot',snapshot(59,'0.000001555'))
    fee(ledger,'buy-a','-0.000000774',when=clock(60))
    monkeypatch.setattr('backend.inventory.utcnow',lambda:clock(59))
    inv=attribute(ledger,ledger.get('account_snapshot'))
    assert inv['differences']==[] and inv['status']=='needs-review'
    assert any('Fee timestamp is after accounting read' in i['reason'] for i in inv['errors'])
