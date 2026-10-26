"""Synthetic custody receipts: net ownership never certifies unknown fees."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import sqlite3

import pytest

from backend.accounting_engine import at, evaluate, source_snapshot
from backend.config import Settings
from backend.custody import analyze, retained
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


def fee(store, cid, qty, identity='fee-a'):
    payload = {'id':identity,'activity_type':'CFEE','symbol':'BTCUSD','qty':qty,'status':'executed'}
    if cid:payload['order_id']='broker-'+cid
    store.db.execute('INSERT INTO activities VALUES(?,?,?,?)', (identity,'CFEE',clock(50),dumps(payload)))


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


def test_recorded_checkpoints_recover_net_custody_without_legacy_observations(ledger):
    for row in retained(ledger)['observations']:
        ctx=json.loads(row['context']);payload={'snapshot':ctx['snapshot'],'working_orders':[]}
        ledger.db.execute('INSERT INTO events(at,type,payload) VALUES(?,?,?)',(row['at'],'custody_snapshot',dumps(payload)))
    ledger.db.execute('DELETE FROM observations')
    path=ledger.db.execute('PRAGMA database_list').fetchone()['file']
    before=source_snapshot(path,at(clock(59)))
    report=evaluate(before,None,at(clock(59)))
    assert not before['observations'] and report['custody']['gross_to_net']['reductions']
    assert Decimal(report['custody']['differences'][0]['recorded_net_quantity'])==0
    readonly=sqlite3.connect('file:'+path+'?mode=ro',uri=True)
    readonly.row_factory=sqlite3.Row;readonly.execute('PRAGMA query_only=ON')
    try:
        class View:
            def rows(self,q,args=()):return [dict(r) for r in readonly.execute(q,args)]
            def get(self,k,default=None):
                r=readonly.execute('SELECT value FROM state WHERE key=?',(k,)).fetchone();return json.loads(r[0]) if r else default
        assert attribute(View(),ledger.get('account_snapshot'))==attribute(ledger,ledger.get('account_snapshot'))
    finally:readonly.close()


def test_partial_fill_checkpoints_measure_each_increment_once(ledger):
    data=retained(ledger)
    part=data['fills'][1];payload=json.loads(part['payload']);payload['at']=clock(3)
    part.update(at=clock(3.1),payload=dumps(payload))
    raw=json.loads(data['orders'][0]['raw']);raw['filled_at']=clock(3);data['orders'][0]['raw']=dumps(raw)
    data['checkpoints']=[{'id':1,'at':clock(2.3),'payload':dumps({'snapshot':snapshot(2.2,'0.00012349'),'working_orders':['buy-a']})}]
    result=analysis(ledger,**data)
    assert Decimal(result['reductions'][0]['quantity'])==Decimal('.000000774')
    assert [Decimal(p['reduction_quantity']) for p in result['reductions'][0]['checkpoints']]==[Decimal('.000000310'),Decimal('.000000464')]
    assert Decimal(result['additional_debits']['BTC']['manual'])==Decimal('.000001555')
