import asyncio
from dataclasses import replace
from datetime import datetime,timezone,timedelta
import pytest

from backend.broker import BrokerFailure
from backend.engine import Engine,RuleViolation
from backend.pilot import ExecutionPilot
from test_service import engine,run


def pilot(engine,run_id='testpilot-0001'):
    engine.settings=replace(engine.settings,enable_research=False,enable_codex_research=False,enable_shadow=False,enable_exit_monitor=False)
    return ExecutionPilot(engine,run_id,hold_seconds=0)


def test_synthetic_round_trip_and_completed_resume_do_not_buy_twice(engine):
    p=pilot(engine);r=run(p.run())
    assert r['phase']=='completed' and r['outcome']=='round-trip-flat-confirmed'
    assert r['entry_permits']==1 and r['exit_permits']==1
    assert len(engine.state()['fills'])==2 and not any(a['quantity'] for a in engine.state()['assets'])
    assert run(p.run())['phase']=='completed' and len(engine.state()['fills'])==2
    with pytest.raises(RuleViolation,match='already consumed'):ExecutionPilot(engine,'testpilot-0002',hold_seconds=0)


@pytest.mark.parametrize('bad',['symbol','market','gtc','oversize','expired','unscoped-id'])
def test_final_pilot_boundary_blocks_wrong_or_oversize_requests(engine,bad):
    p=pilot(engine)
    q=engine.store.get('quotes')['BTC'];a=float(q['ask'])
    payload={'client_order_id':p.cid('buy'),'symbol':'BTC/USD','side':'buy','type':'limit','time_in_force':'ioc','qty':str(10/a),'limit_price':str(a)}
    if bad=='symbol':payload['symbol']='ETH/USD'
    if bad=='market':payload['type']='market'
    if bad=='gtc':payload['time_in_force']='gtc'
    if bad=='oversize':payload['qty']='1'
    if bad=='expired':p.state['entry_deadline']=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()
    if bad=='unscoped-id':payload['client_order_id']='astral-unscoped0001'
    with pytest.raises(BrokerFailure):run(p.submit(payload))
    assert not engine.state()['fills'] and not p.state['entry_permits']


def test_pilot_recovers_lost_accepted_entry_without_duplicate(engine):
    original=engine.broker.submit;calls=[]
    async def lost(payload):
        calls.append(payload)
        raw=await original(payload)
        if payload['side']=='buy':raise BrokerFailure('Accepted response lost')
        return raw
    engine.broker.submit=lost
    p=pilot(engine);r=run(p.run())
    assert r['outcome']=='round-trip-flat-confirmed'
    assert len(calls)==2 and len(engine.state()['fills'])==2


def test_crash_after_entry_resumes_exit_without_new_entry(engine):
    p=pilot(engine)
    async def interrupted(cid):raise RuntimeError('Simulated process interruption')
    original=p.terminal;p.terminal=interrupted
    with pytest.raises(RuntimeError):run(p.run())
    assert p.state['entry_permits']==1 and len(engine.state()['fills'])==1
    reopened=Engine(engine.settings,engine.store)
    resumed=ExecutionPilot(reopened,p.run_id,hold_seconds=0)
    assert run(resumed.run())['outcome']=='round-trip-flat-confirmed'
    assert len(engine.state()['fills'])==2


def test_pilot_refuses_existing_positions(engine):
    from test_service import intent
    run(engine.place(intent(notional=25)))
    p=pilot(engine)
    with pytest.raises(RuleViolation,match='stable flat'):run(p.run())
    assert p.state['entry_permits']==0


def test_pilot_and_strategy_workers_cannot_share_authority(engine):
    engine.settings=replace(engine.settings,enable_research=True)
    with pytest.raises(ValueError,match='sole order authority'):ExecutionPilot(engine,'testpilot-0001')
