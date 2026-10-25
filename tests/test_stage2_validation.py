"""Synthetic decision-path and fault tests; none are broker-paper executions."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import random

import pytest

from backend.broker import BrokerFailure, D
from backend.engine import Engine
from backend.reconciliation import audit_crypto
from backend.research import screen
from backend.timing import decide
from test_dogfood import selection_fixture
from test_service import engine, intent, run


def reconciliation_fixture():
    orders = [{'id':'buy','client_order_id':'fixture-buy','symbol':'BTC/USD','side':'buy','filled_qty':'0.000309121','filled_avg_price':'80789.055333025'},
              {'id':'sell','client_order_id':'fixture-sell','symbol':'BTC/USD','side':'sell','filled_qty':'0.000308347','filled_avg_price':'80785.24'}]
    activities = [dict(id=str(i),activity_type='FILL',symbol='BTC/USD',order_id=o,side=s,qty=q,price=p) for i,(o,s,q,p) in enumerate([
        ('buy','buy','0.0001238','80788.24'),('buy','buy','0.000185321','80789.6'),
        ('sell','sell','0.00012379','80785.24'),('sell','sell','0.000184557','80785.24')])]
    return dict(symbol='BTC/USD',orders=orders,activities=activities,positions=[])


def test_exact_fee_hypothesis_never_clears_an_unconfirmed_difference():
    data = reconciliation_fixture();before = deepcopy(data)
    a = audit_crypto(**data)
    assert all(o['order_quantity_matches'] and o['order_value_matches'] for o in a['orders'])
    assert a['fee_hypothesis']['matches_unexplained_debit']
    assert Decimal(a['unexplained_quantity']) == Decimal('-0.000000774')
    assert a['status'] == 'needs-confirmation'
    assert not a['ledger_adjustment_created'] and not a['execution_authorized']
    assert data == before


def test_confirmed_fee_matches_and_duplicate_activity_is_not_counted_twice():
    data = reconciliation_fixture()
    data['activities'].append(deepcopy(data['activities'][0]))
    fee = dict(id='cf-1',activity_type='CFEE',symbol='BTCUSD',status='executed',qty='-0.000000774')
    data['activities'] += [fee,deepcopy(fee)]
    a = audit_crypto(**data)
    assert a['status'] == 'matched' and a['execution_count'] == 4
    assert not a['execution_authorized']


def test_incomplete_or_conflicting_execution_evidence_cannot_match():
    data = reconciliation_fixture();data['activities'][0]['qty'] = '0.0001237'
    assert audit_crypto(**data)['errors']
    conflict = deepcopy(data['activities'][0]);conflict['qty'] = '999'
    data['activities'].append(conflict)
    with pytest.raises(ValueError,match='Conflicting execution'): audit_crypto(**data)


def test_synthetic_qualified_selection_reaches_entry_and_stop_exit():
    fixture = selection_fixture();p = screen(**fixture)
    assert p['eligible']
    now = datetime.fromisoformat(p['as_of'])+timedelta(seconds=1)
    context = dict(as_of=now.isoformat(),horizon='swing',kind='crypto',quote={**fixture['quote'],'at':now.isoformat()},
                   session_open=True,signal=p['facts']['signal'],latest_closed_at=p['facts']['latest_closed_daily_bar'],
                   research_qualified=p['eligible'],research_expires_at=p['expires_at'],stop_price=p['facts']['planned_stop'],target_price=p['facts']['target'])
    entry = decide(**context)
    assert entry['action'] == 'buy_candidate'
    stop = Decimal(p['facts']['planned_stop'])-Decimal('.01')
    context.update(as_of=(now+timedelta(seconds=2)).isoformat(),quantity=p['facts']['proposed_quantity'],entries_halted=True,research_qualified=False)
    context['quote'] = {'bid':str(stop),'ask':str(stop+Decimal('.01')),'at':context['as_of']}
    exit = decide(**context)
    assert exit['action'] == 'sell_candidate'
    assert not entry['execution_enabled'] and not exit['fill_assumed']


def test_downstream_candidate_is_visible_but_inventory_still_vetoes(engine):
    run(engine.place(intent(notional=25)))
    snap = engine.store.get('account_snapshot');snap['positions']=[];engine.store.put('account_snapshot',snap)
    now = datetime.now(timezone.utc)
    engine.store.put('research_packets',[{'symbol':'BTC','eligible':True,'expires_at':(now+timedelta(minutes=5)).isoformat(),
                                         'facts':{'signal':'entry_candidate','latest_closed_daily_bar':(now-timedelta(seconds=60)).isoformat()}}])
    engine.store.put('research_review',{'status':'reviewed','review':{'picks':[{'symbol':'BTC'}]}})
    result = next(r for r in engine.timing_cycle() if r['symbol']=='BTC' and r['strategy']=='swing')
    assert result['before_inventory_gate']['action'] == 'buy_candidate'
    assert result['action'] == 'wait' and not result['inventory_gate_passed']
    assert not result['execution_enabled']


def test_many_concurrent_retries_after_lost_response_submit_once(engine):
    original = engine.broker.submit;calls=[]
    async def lost(payload):
        calls.append(payload)
        await original(payload)
        raise BrokerFailure('Fixture: accepted response lost')
    engine.broker.submit = lost
    async def scenario():
        return await asyncio.gather(*(engine.place(intent(notional=25)) for _ in range(24)))
    run(scenario())
    resumed = Engine(engine.settings,engine.store)
    run(resumed.reconcile())
    assert len(calls)==1 and len(resumed.state()['fills'])==1
    assert resumed.store.order(intent()['client_order_id'])['status']=='filled'


@pytest.mark.parametrize('seed',range(8))
def test_duplicate_and_out_of_order_partial_readbacks_preserve_quantity(engine,seed):
    row = run(engine.place(intent(notional=25,execution='patient')))
    total = D(row['broker']['qty']);updates=[]
    for fraction in ('0.1','0.4','0.7','1'):
        raw = deepcopy(row['broker']);raw.update(filled_qty=str(total*D(fraction)),filled_avg_price='67500',status='filled' if fraction=='1' else 'partially_filled')
        updates.append(raw)
    observations = [deepcopy(v) for v in updates for _ in range(12)]
    random.Random(seed).shuffle(observations)
    regressions = 0
    for raw in observations:
        before = engine.store.order(intent()['client_order_id'])['raw']
        try:
            engine.ingest(raw)
        except BrokerFailure as exc:
            assert 'regressed' in str(exc)
            assert engine.store.order(intent()['client_order_id'])['raw'] == before
            regressions += 1
    assert regressions > 0
    assert sum(D(f['quantity']) for f in engine.state()['fills']) == total
    assert engine.store.order(intent()['client_order_id'])['status']=='filled'
    assert len({f['id'] for f in engine.state()['fills']}) == len(engine.state()['fills'])


def test_exit_waits_through_readback_disconnect_then_executes_once(engine):
    engine.settings=replace(engine.settings,enable_exit_monitor=True)
    run(engine.place(intent(notional=25)))
    bid=D(engine.store.get('quotes')['BTC']['bid'])
    run(engine.arm_exit({'id':'stage2-exit-0001','symbol':'BTC','strategy_id':'manual','stop_price':str(bid*D('.999')),'target_price':None}))
    original_snapshot=engine.broker.snapshot;original_submit=engine.broker.submit;calls=[]
    async def disconnected(): raise BrokerFailure('Fixture: readback disconnected')
    async def tracked(payload): calls.append(payload);return await original_submit(payload)
    engine.broker.snapshot=disconnected;engine.broker.submit=tracked
    async def observe_disconnect():
        task=asyncio.create_task(engine.loop('reconciliation',engine.reconcile,.001))
        await asyncio.sleep(.02)
        task.cancel();await asyncio.gather(task,return_exceptions=True)
    run(observe_disconnect());assert not engine.connected
    q=engine.store.get('quotes');q['BTC'].update(bid=str(bid*D('.98')),ask=str(bid*D('.9801')));engine.store.put('quotes',q)
    run(engine.exit_cycle());assert not calls
    engine.broker.snapshot=original_snapshot;run(engine.reconcile())
    run(engine.exit_cycle());run(engine.exit_cycle())
    assert len(calls)==1 and engine.store.get('exit_plans')['stage2-exit-0001']['state']=='completed'
