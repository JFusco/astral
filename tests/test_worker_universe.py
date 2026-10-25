import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from backend.codex_worker import CodexReviewer, material_hash
from backend.research import screen, validate_review
from backend.store import Store, dumps
from backend.universe import discover_crypto
from test_dogfood import selection_fixture
from test_service import engine, intent, run
from backend.broker import D


def test_slow_worker_keeps_configured_interval(engine,monkeypatch):
    delays=[]
    async def sleep(delay):
        delays.append(delay)
        raise asyncio.CancelledError()
    async def action():raise AssertionError('No cycle before its configured interval')
    monkeypatch.setattr('backend.engine.asyncio.sleep',sleep)
    with pytest.raises(asyncio.CancelledError):run(engine.loop('research',action,900))
    assert delays==[900]


def test_pending_sells_reserve_their_own_sleeve(engine):
    run(engine.place(intent('astral-swing0001', notional=200, strategy_id='swing')))
    run(engine.place(intent('astral-intra0001', notional=90, strategy_id='intraday')))
    own = D(engine.inventory()['books']['BTC']['intraday'])
    pending = run(engine.place(intent('astral-intrapend', notional=70, side='sell', strategy_id='intraday', execution='patient')))
    assert pending['status'] == 'new'
    payload = engine.risk_payload(intent('astral-intraexit', notional=1000, side='sell', strategy_id='intraday'))
    assert D(payload['qty'])+D(pending['request']['payload']['qty']) <= own


def test_discovery_includes_meme_pairs_without_authorizing_trades():
    asset = {'id':'venue-doge','class':'crypto','symbol':'DOGE/USD','status':'active','tradable':True,
             'min_trade_increment':'1','min_order_size':'1','price_increment':'.00001'}
    result = discover_crypto([asset], '2026-10-25T00:00:00Z')
    row = result['assets'][0]
    assert row['metadata_eligible'] and row['pair']=='DOGE/USD'
    assert not row['execution_enabled'] and not row['execution_allowlisted'] and not row['research_ready']
    for field, value in [('id',None),('price_increment','NaN'),('min_order_size','0'),('status','inactive'),('symbol','DOGE/USDT')]:
        changed = {**asset,field:value}
        assert not discover_crypto([changed],result['as_of'])['assets'][0]['metadata_eligible']
    assert all(not r['metadata_eligible'] for r in discover_crypto([asset,asset],result['as_of'])['assets'])
    assert result == discover_crypto([asset], result['as_of'])


def test_duplicate_model_picks_are_rejected():
    packet = screen(**selection_fixture());facts=packet['facts']
    pick={'symbol':'BTC','why_now':'Fixture','counter_case':'Failure','invalidation':'Expiry','evidence_ids':['quote:BTC'],
          **{k:facts[k] for k in ('spread_bps','avg_daily_dollar_volume_20','proposed_notional')}}
    with pytest.raises(ValueError,match='Duplicate'):
        validate_review({'decision':'propose','summary':'Fixture','picks':[pick,pick]},[packet])


@pytest.mark.parametrize('change',['fact','calendar','news-revision'])
def test_changed_evidence_invalidates_cached_rationale(change):
    packet=screen(**selection_fixture());changed=deepcopy(packet)
    if change=='fact':changed['facts']['proposed_notional']='1'
    if change=='calendar':changed['evidence'][-1]['coverage_until']='2026-10-27T00:00:00Z'
    if change=='news-revision':changed['evidence'][-2]['known_at']='2026-10-24T06:00:00Z'
    assert material_hash([packet]) != material_hash([changed])


def test_cli_worker_isolated_environment_usage_cache_and_budget(tmp_path, monkeypatch):
    store=Store(tmp_path/'worker.sqlite','simulator');worker=CodexReviewer(store)
    packet=screen(**selection_fixture());calls=[]
    monkeypatch.setenv('ALPACA_PAPER_SECRET_KEY','must-not-be-inherited')
    monkeypatch.setattr('backend.codex_worker.shutil.which',lambda _: '/fixture/codex')
    class Process:
        returncode=0
        async def communicate(self,prompt):
            assert b'untrusted evidence' in prompt
            return b'{"type":"turn.completed","usage":{"input_tokens":123,"output_tokens":45}}\n',None
    async def spawn(*args,**kwargs):
        calls.append(args)
        assert 'ALPACA_PAPER_SECRET_KEY' not in kwargs['env']
        assert '--ignore-user-config' in args and 'mcp_servers={}' in args and 'web_search="disabled"' in args
        Path(args[args.index('--output-last-message')+1]).write_text(dumps({'decision':'abstain','summary':'No supported thesis','picks':[]}))
        return Process()
    monkeypatch.setattr('backend.codex_worker.asyncio.create_subprocess_exec',spawn)
    first=run(worker.review([packet]));second=run(worker.review([packet]))
    assert first['status']=='reviewed' and first['usage']['input_tokens']==123 and first['actual_usd'] is None
    assert second['cached'] and len(calls)==1
    for _ in range(3): run(worker.review([packet],force=True))
    assert run(worker.review([packet],force=True))['status']=='budget-exhausted' and len(calls)==4
    store.close()


@pytest.mark.parametrize('mode',['tool','timeout','invalid-json'])
def test_cli_failures_never_accept_picks_and_consume_attempt(tmp_path,monkeypatch,mode):
    store=Store(tmp_path/'worker.sqlite','simulator');worker=CodexReviewer(store)
    monkeypatch.setattr('backend.codex_worker.shutil.which',lambda _: '/fixture/codex')
    class Process:
        returncode=None
        killed=False
        async def communicate(self,prompt):
            if mode=='timeout': raise asyncio.TimeoutError()
            return (b'not json' if mode=='invalid-json' else b'{"type":"item.completed","item":{"type":"command_execution"}}\n'),None
        def kill(self):self.killed=True;self.returncode=-9
        async def wait(self):return self.returncode
    process=Process()
    async def spawn(*args,**kwargs):return process
    monkeypatch.setattr('backend.codex_worker.asyncio.create_subprocess_exec',spawn)
    result=run(worker.review([screen(**selection_fixture())]))
    assert result['status']=='failed' and result['review'] is None and not result['execution_enabled']
    assert process.killed and store.get('codex_budget')['attempts']==1
    store.close()
