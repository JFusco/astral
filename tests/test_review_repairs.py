"""Locked review regressions. Synthetic brokers, patched models and tmp ledgers only."""
import asyncio
from collections import Counter
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sqlite3

import httpx
import pytest

from backend import experiment
from backend.broker import BrokerFailure, Simulator
from backend.codex_worker import CodexReviewer
from backend.config import Settings
from backend.engine import Engine, RuleViolation
from backend.public_context import read_context
from backend.research import screen
from backend.store import Store, dumps, utcnow
from backend.timing import decide
from scripts import dogfood_session
from test_dogfood import selection_fixture
from test_service import engine, intent, run


@pytest.fixture
def research_engine(tmp_path, monkeypatch):
    cfg = Settings(mode='alpaca', db_path=tmp_path/'research.sqlite', api_key='fixture',
                   secret_key='fixture', enable_research=True)
    store = Store(cfg.db_path, cfg.mode)
    broker = Simulator(cfg, store)
    e = Engine(cfg, store, broker)
    async def unavailable():
        return {'status':'unavailable', 'sources':[], 'items':[]}
    async def missing(symbol):
        raise BrokerFailure('Fixture history unavailable')
    async def forbidden(*args, **kwargs):
        raise AssertionError('Research attempted a broker write')
    broker.research_bars = missing
    broker.submit = broker.cancel = forbidden
    monkeypatch.setattr('backend.engine.read_context', unavailable)
    yield e
    store.close()


@pytest.mark.parametrize('error', [TypeError, sqlite3.OperationalError, asyncio.CancelledError])
def test_startup_replay_failure_is_optional_and_cancellation_escapes(research_engine, monkeypatch, error):
    e = research_engine
    def broken(*args):
        raise error('Fixture replay failure')
    monkeypatch.setattr('backend.engine.build_replay_report', broken)
    scheduled = []
    async def loop(name, action, interval):
        scheduled.append((name, interval))
        await asyncio.Future()
    e.loop = loop
    async def exercise():
        try:
            if error is asyncio.CancelledError:
                with pytest.raises(asyncio.CancelledError):
                    await e.start()
            else:
                await e.start()
                assert e.workers['portfolio_replay']['status'] == 'error'
            await asyncio.sleep(0)
            assert ('liquidity_experiment', 15) in scheduled
            if error is not asyncio.CancelledError:
                assert ('portfolio_replay', 900) in scheduled
            assert e.workers['event_context']['status'] == 'error'
        finally:
            await e.stop()
    run(exercise())


def test_oversized_prompt_costs_no_attempt(tmp_path, monkeypatch):
    store = Store(tmp_path/'worker.sqlite', 'simulator')
    packet = screen(**selection_fixture())
    packet['evidence'].append({'id':'oversized', 'headline':'x'*46000})
    budget = {'day':datetime.now(timezone.utc).date().isoformat(), 'attempts':2}
    store.put('codex_budget', budget)
    monkeypatch.setattr('backend.codex_worker.shutil.which', lambda _: '/fixture/codex')
    async def forbidden(*args, **kwargs):
        raise AssertionError('Oversized input launched a process')
    monkeypatch.setattr('backend.codex_worker.asyncio.create_subprocess_exec', forbidden)
    result = run(CodexReviewer(store).review([packet]))
    assert result['status'] == 'input-budget-exceeded'
    assert store.get('codex_budget') == budget
    store.close()


def test_all_vetoed_cycle_never_calls_model(research_engine, monkeypatch):
    e = research_engine
    e.settings = replace(e.settings, enable_codex_research=True)
    async def forbidden(*args, **kwargs):
        raise AssertionError('All-vetoed cycle called the model')
    monkeypatch.setattr('backend.codex_worker.asyncio.create_subprocess_exec', forbidden)
    e.reviewer.review = forbidden
    result = run(e.research_cycle())
    assert not any(p['eligible'] for p in result['packets'])
    assert result['review']['status'] == 'no-eligible-packets'
    assert e.store.get('codex_budget', {}).get('attempts', 0) == 0
    assert e.store.get('research_review') == result['review']


def test_cycle_sends_only_eligible_packets_to_one_patched_process(research_engine, monkeypatch):
    from backend.research import screen
    e = research_engine
    e.settings = replace(e.settings, enable_codex_research=True)
    qualified = screen(**selection_fixture())
    def fixture_screen(symbol, *args, **kwargs):
        packet = deepcopy(qualified)
        packet['symbol'] = symbol
        if symbol != 'BTC':
            packet.update(eligible=False, vetoes=['Fixture veto'])
        return packet
    async def approved(*args, **kwargs):
        return {'decision':'would-approve'}
    monkeypatch.setattr('backend.engine.screen', fixture_screen)
    e.shadow = approved
    monkeypatch.setattr('backend.codex_worker.shutil.which', lambda _: '/fixture/codex')
    calls = []
    class Process:
        returncode = 0
        async def communicate(self, prompt):
            supplied = json.loads(prompt.split(b'\n', 1)[1])
            assert [p['symbol'] for p in supplied] == ['BTC']
            return b'', None
    async def spawn(*args, **kwargs):
        calls.append(args)
        pick = {'symbol':'BTC', 'why_now':'Fixture', 'counter_case':'Failure', 'invalidation':'Expiry',
                'evidence_ids':['quote:BTC'], **{k:qualified['facts'][k] for k in
                ('spread_bps','avg_daily_dollar_volume_20','proposed_notional')}}
        Path(args[args.index('--output-last-message')+1]).write_text(dumps(
            {'decision':'propose', 'summary':'Synthetic only', 'picks':[pick]}))
        return Process()
    monkeypatch.setattr('backend.codex_worker.asyncio.create_subprocess_exec', spawn)
    result = run(e.research_cycle())
    assert len(calls) == 1 and e.store.get('codex_budget')['attempts'] == 1
    assert result['review']['status'] == 'reviewed'
    assert result['review']['review']['validation'] == 'evidence-ids-and-hard-vetoes-passed'


def test_disabled_model_keeps_deterministic_arm_in_new_observations(engine):
    s = engine.store
    frozen = experiment.register(s)
    now = datetime.now(timezone.utc)
    packet = {'symbol':'BTC', 'eligible':True, 'as_of':now.isoformat(), 'input_hash':'fixture-1',
              'expires_at':(now+timedelta(minutes=5)).isoformat(),
              'facts':{'experiment_manifest':frozen['manifest_sha256'], 'signal':'entry_candidate',
                       'latest_closed_daily_bar':(now-timedelta(minutes=1)).isoformat()}}
    s.put('research_packets', [packet])
    s.put('research_review', {'status':'disabled'})
    result = next(r for r in engine.timing_cycle() if r['symbol']=='BTC' and r['strategy']=='swing')
    assert result['deterministic_arm']['action'] == 'buy_candidate'
    context = json.loads(s.rows("SELECT context FROM timing WHERE symbol='BTC' AND strategy='swing'")[0]['context'])
    unchanged = decide(**context)
    assert result['action'] == unchanged['action'] == 'wait'
    assert result['reason'] == unchanged['reason'] and result['inventory_gate_passed']
    old = s.rows('SELECT * FROM experiment_observations')[0]
    assert json.loads(old['payload'])['timing']['deterministic_arm'] == result['deterministic_arm']
    packet['input_hash'] = 'fixture-2'
    s.put('research_packets', [packet]);engine.timing_cycle()
    assert s.rows('SELECT * FROM experiment_observations WHERE id=?', (old['id'],))[0] == old


def test_global_fee_latch_blocks_strategy_sell_with_rule_violation(engine):
    run(engine.place(intent(notional=100, strategy_id='swing')))
    manual = intent(side='sell', notional=25, strategy_id='manual')
    with pytest.raises(RuleViolation) as before:
        engine.risk_payload(manual, shadow=True)
    engine.store.put('fee_reconciliation_required', {'reason':'Fixture changed fee'})
    with pytest.raises(RuleViolation, match='Strategy inventory differs from broker;'):
        engine.risk_payload(intent(side='sell', notional=25, strategy_id='swing'), shadow=True)
    with pytest.raises(RuleViolation) as after:
        engine.risk_payload(manual, shadow=True)
    assert str(before.value) == str(after.value)
    assert engine.inventory()['status'] == 'needs-review'


def fee(**changes):
    return {'id':'f1', 'activity_type':'CFEE', 'status':'executed', 'symbol':'BTCUSD',
            'qty':'-0.000001', **changes}


@pytest.mark.parametrize('reverse', [False, True])
def test_unequal_first_fee_duplicates_retain_both_and_apply_neither(engine, reverse):
    items = [fee(), fee(qty='-0.000002')]
    if reverse:items.reverse()
    async def fetched(after):return items
    engine.broker.fee_activities = fetched
    with pytest.raises(ValueError, match='Conflicting fee batch'):
        run(engine.refresh_fees())
    assert len(engine.store.rows('SELECT * FROM activity_revisions')) == 2
    assert not engine.store.rows('SELECT * FROM activities')
    assert engine.store.get('fee_reconciliation_required')


def test_identical_fee_duplicates_and_later_execution_are_idempotent(engine):
    items = [fee(status='pending')]*2
    async def fetched(after):return deepcopy(items)
    engine.broker.fee_activities = fetched
    run(engine.refresh_fees())
    assert len(engine.store.rows('SELECT * FROM activities')) == 1
    items[:] = [fee(), fee()]
    run(engine.refresh_fees());run(engine.refresh_fees())
    assert len(engine.store.rows('SELECT * FROM activity_revisions')) == 2
    assert len(engine.store.rows('SELECT * FROM activities')) == 1
    assert json.loads(engine.store.rows('SELECT payload FROM activities')[0]['payload']) == fee()
    assert not engine.store.get('fee_reconciliation_required')


@pytest.mark.parametrize('quantity', ['1', '0', None, 'NaN', float('nan')])
def test_invalid_confirmed_fee_revision_is_retained_and_latched(engine, quantity):
    items = [fee()]
    async def fetched(after):return deepcopy(items)
    engine.broker.fee_activities = fetched
    run(engine.refresh_fees())
    original = engine.store.rows('SELECT * FROM activities')
    items[:] = [fee(qty=quantity)]
    with pytest.raises(ValueError):run(engine.refresh_fees())
    revisions = engine.store.rows('SELECT payload FROM activity_revisions')
    assert len(revisions) == 2
    for row in revisions:
        json.loads(row['payload'], parse_constant=lambda value: pytest.fail('Nonfinite JSON escaped'))
    assert engine.store.rows('SELECT * FROM activities') == original
    assert engine.store.get('fee_reconciliation_required')
    assert engine.inventory()['status'] == 'needs-review'


def test_new_invalid_fee_is_never_applied(engine):
    async def fetched(after):return [fee(qty=None)]
    engine.broker.fee_activities = fetched
    with pytest.raises(ValueError):run(engine.refresh_fees())
    assert not engine.store.rows('SELECT * FROM activities')


def daily_history(count=60):
    now = datetime.now(timezone.utc)
    boundary = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return {'rows':[{'t':(boundary-timedelta(days=count-i)).isoformat(), 'o':'100', 'h':'102',
                     'l':'99', 'c':'101', 'v':'100000', 'dollar_volume':'10100000'} for i in range(count)],
            'received_at':now.isoformat(), 'source':'fixture-executions', 'coverage':'Synthetic only',
            'bar_semantics':'executed-trades-only', 'complete_page_traversal':True, 'input_sha256':'fixture'}


@pytest.mark.parametrize('case', ['short', 'gap', 'valid'])
def test_diagnostic_failure_still_journals_prospective_veto(research_engine, case):
    e = research_engine
    history = daily_history(30 if case=='short' else 60)
    if case=='gap':history['rows'].pop(12)
    async def bars(symbol):return deepcopy(history) if symbol=='BTC' else None
    e.broker.research_bars = bars
    result = run(e.research_cycle())
    assert not result['packets'][0]['eligible']
    diagnostic = e.store.get('experiment_diagnostic')
    if case=='valid':
        assert diagnostic['evaluated_prefixes'] == 10
    else:
        assert diagnostic['status'] == 'unavailable' and diagnostic['reason']
    assert len(e.store.rows('SELECT * FROM experiment_observations')) == 1
    assert not e.store.rows('SELECT * FROM orders') and not e.store.rows('SELECT * FROM fills')


def test_adapter_hashes_are_cached_local_and_covered_by_packet_hash(research_engine, tmp_path, monkeypatch):
    import backend.engine as engine_module
    e = research_engine
    sources = ('public_context','calendar_evidence','event_sources','intelligence','calendar_context',
               'bea_calendar','market_depth','trade_history','broker')
    local = tmp_path/'adapters';local.mkdir()
    for name in sources:
        (local/(name+'.py')).write_bytes(Path(engine_module.__file__).with_name(name+'.py').read_bytes())
    monkeypatch.setattr(engine_module, '__file__', str(local/'engine.py'))
    reads = Counter()
    original_read = Path.read_bytes
    def read(path):
        if path.parent == local:reads[path.name] += 1
        return original_read(path)
    monkeypatch.setattr(Path, 'read_bytes', read)
    original_screen = engine_module.screen
    screen_hashes = {}
    def screen(*args, **kwargs):
        packet = original_screen(*args, **kwargs)
        screen_hashes[packet['symbol']] = packet['input_hash']
        return packet
    monkeypatch.setattr(engine_module, 'screen', screen)
    for _ in range(2):
        result = run(e.research_cycle())
        for packet in result['packets']:
            versions = packet['evidence_adapter_versions']
            assert versions['public_context'] == 'scoped-calendar-context-v4'
            assert len(versions['local_source_file_sha256']) == len(sources)
            before = {**packet, 'input_hash':screen_hashes[packet['symbol']]}
            assert hashlib.sha256(dumps(before).encode()).hexdigest() == packet['input_hash']
    assert reads == Counter({name+'.py':1 for name in sources})
    old = e.adapter_source_hashes()['backend/public_context.py']
    (local/'public_context.py').write_text('# Changed local fixture\n')
    new = Engine(e.settings, e.store, e.broker).adapter_source_hashes()
    assert new['backend/public_context.py'] != old
    assert experiment.contract()['code_matches']


@pytest.mark.parametrize('body', [[], None, {'sources':['bad'], 'items':[]},
                                {'sources':[], 'items':[None]},
                                {'sources':[], 'items':[], 'calendar_catalogs':['bad']},
                                {'as_of':'2026-10-25T12:00:00Z', 'sources':[], 'items':[]}])
def test_malformed_context_returns_unavailable_and_start_survives(research_engine, monkeypatch, body):
    client = httpx.AsyncClient
    monkeypatch.setattr('backend.public_context.httpx.AsyncClient', lambda **kwargs:
                        client(transport=httpx.MockTransport(lambda _: httpx.Response(200, content=json.dumps(body))), **kwargs))
    assert run(read_context())['status'] == 'unavailable'
    monkeypatch.setattr('backend.engine.read_context', read_context)
    monkeypatch.setattr('backend.engine.build_replay_report', lambda _: {
        'receipt':'fixture', 'synthetic_scenarios':0, 'forward':{'status':'fixture'}})
    async def exercise():
        try:
            await research_engine.start()
            assert research_engine.workers['event_context']['status'] == 'error'
        finally:await research_engine.stop()
    run(exercise())


def test_valid_context_shape_remains_available(monkeypatch):
    client = httpx.AsyncClient
    body = {'as_of':utcnow(), 'sources':[], 'items':[], 'calendar_catalogs':[]}
    monkeypatch.setattr('backend.public_context.httpx.AsyncClient', lambda **kwargs:
                        client(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=body)), **kwargs))
    result = run(read_context())
    assert result['status'] == 'available' and result['received_at']
    assert {key:result[key] for key in body} == body


@pytest.mark.parametrize('alias', ['same', 'symlink', 'hardlink', 'relative'])
def test_lab_rejects_primary_alias_before_lock_or_store(tmp_path, monkeypatch, alias):
    monkeypatch.setattr(dogfood_session, 'ROOT', tmp_path)
    monkeypatch.chdir(tmp_path)
    directory = tmp_path/'runtime';directory.mkdir()
    source = directory/'primary.sqlite';source.write_bytes(b'Untouched fixture ledger')
    destination = source
    if alias=='symlink':
        destination = directory/'alias.sqlite';destination.symlink_to(source)
    elif alias=='hardlink':
        import os
        destination = directory/'alias.sqlite';os.link(source, destination)
    cfg = Settings(db_path=Path('runtime/primary.sqlite') if alias=='relative' else source)
    monkeypatch.setattr(Settings, 'from_env', classmethod(lambda cls: cfg))
    def forbidden(*args, **kwargs):raise AssertionError('Constructed writable lab before identity check')
    monkeypatch.setattr(dogfood_session, 'Store', forbidden)
    monkeypatch.setattr(dogfood_session, 'Engine', forbidden)
    with pytest.raises(ValueError, match='must differ'):
        run(dogfood_session.main(0, False, destination.name))
    assert not list(directory.glob('*.lock'))
    assert source.read_bytes() == b'Untouched fixture ledger'


@pytest.mark.parametrize('reuse', [False, True])
def test_distinct_lab_still_copies_or_reuses(tmp_path, monkeypatch, reuse):
    monkeypatch.setattr(dogfood_session, 'ROOT', tmp_path)
    directory = tmp_path/'runtime';directory.mkdir()
    source = directory/'primary.sqlite'
    with sqlite3.connect(source) as db:
        db.execute('CREATE TABLE marker(value TEXT)');db.execute("INSERT INTO marker VALUES('source')")
    destination = directory/'lab.sqlite'
    if reuse:
        with sqlite3.connect(destination) as db:
            db.execute('CREATE TABLE marker(value TEXT)');db.execute("INSERT INTO marker VALUES('existing lab')")
    monkeypatch.setattr(Settings, 'from_env', classmethod(lambda cls: Settings(db_path=source)))
    class StopBeforeEngine(Exception):pass
    def check_copy(path, mode):
        assert path == destination
        with sqlite3.connect(path) as db:
            assert db.execute('SELECT value FROM marker').fetchone()[0] == ('existing lab' if reuse else 'source')
        raise StopBeforeEngine()
    monkeypatch.setattr(dogfood_session, 'Store', check_copy)
    with pytest.raises(StopBeforeEngine):run(dogfood_session.main(0, False, 'lab.sqlite'))
    with sqlite3.connect(source) as db:
        assert db.execute('SELECT value FROM marker').fetchone()[0] == 'source'


def test_lab_start_suppresses_shared_workers(research_engine, monkeypatch):
    e = research_engine
    def forbidden(*args):raise AssertionError('Lab touched a registered output')
    monkeypatch.setattr('backend.engine.build_replay_report', forbidden)
    monkeypatch.setattr('backend.engine.observe_liquidity', forbidden)
    dogfood_session.isolate_experiment_workers(e)
    scheduled = []
    async def loop(name, action, interval):
        scheduled.append(name)
        if name in {'liquidity_experiment','portfolio_replay'}:await action()
        await asyncio.Future()
    e.loop = loop
    async def exercise():
        try:
            await e.start();await asyncio.sleep(0)
            assert {'liquidity_experiment','portfolio_replay'} <= set(scheduled)
            assert not e.store.get('portfolio_replay_receipt')
        finally:await e.stop()
    run(exercise())
