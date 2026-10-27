"""Rollout authorization, bounded collection and recovery with disposable mock evidence."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import httpx
import pytest

from backend.activity_feed import current_accounting
from backend.activity_observation import Observation
from backend.activity_rollout import DAY, activated_settings, prepare
from backend.activity_validation import import_ledger
from backend.broker import AlpacaPaper
from backend.config import Settings
from backend.engine import Engine
from backend.store import Store

FIXTURE = Path(__file__).parent/'fixtures/activity_feed/btc-sanitized-v1'
NOW = '2030-01-01T00:00:00+00:00'


@pytest.fixture
def rollout(tmp_path, monkeypatch):
    # This synthetic provenance label exercises validation mechanics only.
    private = tmp_path/'controlled-inputs'
    shutil.copytree(FIXTURE, private)
    mapping = json.loads((private/'mapping.json').read_text())
    mapping['kind'] = 'reviewed-provider'
    path = private/'mapping.json'
    path.write_text(json.dumps(mapping))
    store = Store(tmp_path/'disposable.sqlite', 'alpaca')
    import_ledger(store, json.loads((private/'ledger-selected-readonly.json').read_text()))
    settings = Settings(db_path=tmp_path/'disposable.sqlite', api_key='fixture', secret_key='fixture')
    monkeypatch.setattr('backend.activity_rollout.shutil.disk_usage', lambda _: SimpleNamespace(free=10**12))
    monkeypatch.setattr('backend.activity_feed.utcnow', lambda: NOW)
    monkeypatch.setattr('backend.broker.utcnow', lambda: NOW)
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    yield settings, store, path, sha, mapping
    store.close()


def prepared(rollout):
    settings, _, path, sha, mapping = rollout
    return prepare(settings, path, sha, mapping['account_id'])


def source_bytes(settings):
    path = settings.db_path
    return [p.read_bytes() for p in (path, Path(str(path)+'-wal')) if p.exists()]


def test_default_cli_preflight_leaves_ledger_and_reader_untouched(rollout, monkeypatch, capsys):
    from backend.activity_rollout import main
    settings, _, path, sha, mapping = rollout
    before = source_bytes(settings)
    monkeypatch.setattr(Settings, 'from_env', lambda: settings)
    monkeypatch.setattr('sys.argv', ['rollout', '--ledger', str(settings.db_path), '--mapping-file', str(path),
                                   '--mapping-sha256', sha, '--account-id', mapping['account_id']])
    main()
    receipt = json.loads(capsys.readouterr().out)
    assert receipt['reader_activated'] is False and receipt['broker_requests'] == 0
    assert source_bytes(settings) == before
    assert not settings.enable_activity_feed


@pytest.mark.parametrize('control', ['enable_orders', 'enable_shadow', 'enable_exit_monitor',
                                    'enable_codex_research', 'enable_activity_feed'])
def test_enabled_control_denies_preflight_without_ledger_changes(rollout, control):
    settings, _, path, sha, mapping = rollout
    unsafe = {control: True}
    if control == 'enable_exit_monitor': unsafe['enable_orders'] = True
    before = source_bytes(settings)
    with pytest.raises(ValueError):
        prepare(replace(settings, **unsafe), path, sha, mapping['account_id'])
    assert source_bytes(settings) == before


@pytest.mark.parametrize('attack', ['mapping-hash', 'source-hash', 'fixture-label', 'account', 'working-order'])
def test_unreviewed_or_unsettled_inputs_cannot_activate(rollout, attack):
    settings, store, path, sha, mapping = rollout
    account = mapping['account_id']
    if attack == 'mapping-hash': sha = '0'*64
    if attack == 'source-hash': (path.parent/'activity-sse.raw').write_bytes(b'changed')
    if attack == 'fixture-label':
        mapping['kind'] = 'sanitized-fixture';path.write_text(json.dumps(mapping))
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
    if attack == 'account': account = 'another-account'
    if attack == 'working-order': store.db.execute("UPDATE orders SET status='unknown'")
    before = source_bytes(settings)
    with pytest.raises(ValueError): prepare(settings, path, sha, account)
    assert source_bytes(settings) == before


def test_prepared_identity_is_rechecked_before_store_startup(rollout):
    settings, store, *_ = rollout
    spec = prepared(rollout)
    store.put('account_binding', 'replacement-account')
    with pytest.raises(ValueError): activated_settings(settings, spec)


def mock_engine(rollout, spec=None, events=None, clock=None):
    settings, store, _, _, _ = rollout
    spec = spec or prepared(rollout)
    observation = Observation(spec, clock=clock)
    observation.started, observation.status = observation.clock(), 'observing'
    snapshot = store.get('account_snapshot')
    capture = json.loads((FIXTURE/'activity-sse.json').read_text())
    raw = (FIXTURE/'activity-sse.raw').read_bytes() if events is None else b''.join(
        ('data: '+json.dumps(e)+'\n\n').encode() for e in events)
    calls = []
    def handler(request):
        calls.append((request.method, request.url.path))
        assert request.method == 'GET'
        if request.url.path == '/v2/account': return httpx.Response(200, json=snapshot['account'])
        if request.url.path == '/v2/positions': return httpx.Response(200, json=snapshot['positions'])
        if request.url.path == '/v2/clock': return httpx.Response(200, json=snapshot['clock'])
        assert request.url.path == '/v2beta1/events/activities'
        return httpx.Response(200, headers={'content-type':'text/event-stream'}, content=raw)
    broker = AlpacaPaper(activated_settings(settings, spec), store, httpx.MockTransport(handler))
    return Engine(broker.settings, store, broker, observation), calls, capture


def test_pinned_mapping_and_covered_snapshot_reconcile_then_newer_snapshot_blocks(rollout):
    spec = prepared(rollout)
    rollout[2].unlink()
    engine, calls, _ = mock_engine(rollout, spec)
    async def scenario():
        try:
            result = await engine.refresh_activity_feed()
            assert not result['issues']
            assert result['cash_reconciliation']['cash'] == '99999.70'
            assert engine.activity_observation.summary()['request_budget_units'] == 7
            assert len(calls) == 7 and all(method == 'GET' for method, _ in calls)
            assert current_accounting(engine.store, enabled=engine.activity_enabled, now=NOW)['accounting_by_symbol']['BTC']['passed']
            snapshot = engine.store.get('account_snapshot')
            snapshot['at'] = (datetime.fromisoformat(NOW)+timedelta(seconds=10)).isoformat()
            engine.store.put('account_snapshot', snapshot)
            current = current_accounting(engine.store, enabled=True, now=snapshot['at'])
            assert 'accounting_snapshot_outside_coverage' in current['activity_coverage']['issues']
            assert current['cash_reconciliation']['cash'] is None
        finally: await engine.broker.close()
    asyncio.run(scenario())


def test_reconciliation_cannot_replace_snapshot_during_rollout_publication(rollout):
    engine, _, _ = mock_engine(rollout)
    async def scenario():
        entered, release, reconciled = asyncio.Event(), asyncio.Event(), asyncio.Event()
        stream = engine.broker.stream_activities
        async def paused(*args):
            entered.set();await release.wait();return await stream(*args)
        async def competitor():
            await entered.wait()
            assert engine.lock.locked()
            async with engine.lock: reconciled.set()
        engine.broker.stream_activities = paused
        task = asyncio.create_task(engine.refresh_activity_feed())
        other = asyncio.create_task(competitor())
        await entered.wait()
        assert not reconciled.is_set()
        release.set()
        try:
            assert not (await task)['issues']
            await other
            assert reconciled.is_set()
        finally: await engine.broker.close()
    asyncio.run(scenario())


@pytest.mark.parametrize('activity', ['trade', 'late-fee', 'revision'])
def test_uncovered_activity_is_retained_and_blocks_without_guessing(rollout, activity):
    events = json.loads((FIXTURE/'activity-sse.json').read_text())['events']
    extra = deepcopy(next(e for e in events if e['activity_type'] == ('TRD' if activity == 'trade' else 'CFEE')))
    extra['event_id'] = 'new-delivery'
    if activity != 'revision': extra['ref_id'] = 'new-reference'
    else: extra['qty'] = '-0.000000001'
    events.append(extra)
    engine, _, _ = mock_engine(rollout, events=events)
    async def scenario():
        try:
            result = await engine.refresh_activity_feed()
            assert result['issues'] and not result['effects']
            assert result['cash_reconciliation']['cash'] is None
            assert len(engine.store.rows('SELECT ordinal FROM activity_events')) == len(events)
            if activity == 'revision': assert engine.store.rows('SELECT id FROM activity_conflicts')
        finally: await engine.broker.close()
    asyncio.run(scenario())


def test_normal_request_budget_denies_observer_before_using_recovery_reserve(rollout):
    engine, calls, _ = mock_engine(rollout)
    engine.broker.trading.normal = 0
    async def scenario():
        try:
            result = await engine.refresh_activity_feed()
            assert result['issues'] and not calls
            assert engine.broker.trading.reserve == 20
        finally: await engine.broker.close()
    asyncio.run(scenario())


def test_deadline_disables_readiness_even_before_worker_can_finish(rollout):
    clock = [0]
    engine, _, _ = mock_engine(rollout, clock=lambda: clock[0])
    async def scenario():
        try:
            assert not (await engine.refresh_activity_feed())['issues']
            clock[0] = DAY
            assert not engine.activity_enabled
            assert not current_accounting(engine.store, enabled=engine.activity_enabled, now=NOW)['accounting_by_symbol']['BTC']['passed']
            with pytest.raises(ValueError): await engine.refresh_activity_feed()
        finally: await engine.broker.close()
    asyncio.run(scenario())


def test_cancelled_observation_retains_attempt_and_leaves_reader_disabled(rollout):
    engine, _, _ = mock_engine(rollout)
    async def scenario():
        entered = asyncio.Event()
        async def interrupted(*_): entered.set();await asyncio.Event().wait()
        engine.broker.stream_activities = interrupted
        task = asyncio.create_task(engine.activity_observation.run(engine))
        await entered.wait();task.cancel()
        try:
            with pytest.raises(asyncio.CancelledError): await task
            assert not engine.activity_enabled
            outcome = engine.store.rows("SELECT payload FROM activity_batches WHERE phase='outcome'")
            assert json.loads(outcome[-1]['payload'])['error'] == 'activity_acquisition_cancelled'
            assert engine.store.get('activity_rollout_observation')['reason'] == 'observation_interrupted'
        finally: await engine.broker.close()
    asyncio.run(scenario())


def test_storage_limit_stops_collection_without_dropping_evidence(rollout, monkeypatch):
    engine, calls, _ = mock_engine(rollout)
    monkeypatch.setattr(engine.activity_observation, 'budget_ok', lambda: False)
    async def scenario():
        try:
            await engine.activity_observation.run(engine)
            assert not calls and not engine.activity_enabled
            assert engine.store.get('activity_rollout_observation')['reason'] == 'storage_budget_exceeded'
        finally: await engine.broker.close()
    asyncio.run(scenario())


def test_inflight_storage_limit_retains_scan_and_prevents_publication(rollout, monkeypatch):
    engine, calls, _ = mock_engine(rollout)
    checks = iter((True, False))
    monkeypatch.setattr(engine.activity_observation, 'budget_ok', lambda: next(checks, False))
    async def scenario():
        try:
            await engine.activity_observation.run(engine)
            assert len(calls) == 7 and not engine.activity_enabled
            assert len(engine.store.rows('SELECT ordinal FROM activity_events')) == 19
            assert not engine.store.rows('SELECT id FROM activity_projections')
            assert engine.store.get('activity_rollout_observation')['reason'] == 'storage_budget_exceeded'
        finally: await engine.broker.close()
    asyncio.run(scenario())


def test_restart_and_duplicate_scan_preserve_effects_and_execution_rows(rollout):
    engine, _, _ = mock_engine(rollout)
    before = {t:engine.store.rows('SELECT * FROM '+t) for t in ('orders','fills','activities','observations')}
    async def scenario():
        try:
            first = await engine.refresh_activity_feed()
            engine.activity_observation.stop(engine.store, 'owner_stopped')
            restarted = Observation(engine.activity_observation.prepared)
            restarted.started, restarted.status = restarted.clock(), 'observing'
            engine.activity_observation = restarted
            again = await engine.refresh_activity_feed()
            assert again['effects'] == first['effects']
            assert again['cash_reconciliation']['cash'] == first['cash_reconciliation']['cash']
            for table, rows in before.items(): assert engine.store.rows('SELECT * FROM '+table) == rows
            assert len(engine.store.rows('SELECT sha256 FROM activity_associations')) == 1
        finally: await engine.broker.close()
    asyncio.run(scenario())


def test_completed_collection_is_distinct_from_current_accounting_and_api_is_private(rollout, monkeypatch):
    from backend.app import create_app
    engine, _, _ = mock_engine(rollout)
    # Exercise the public diagnostic endpoint, without starting workers or a provider.
    app = create_app(engine.settings, background=False, activity_observation=engine.activity_observation)
    app.state.engine = engine
    monkeypatch.setattr(engine, 'state', lambda: {'orders_enabled': False})
    async def scenario():
        try:
            await engine.refresh_activity_feed()
            snapshot = engine.store.get('account_snapshot');snapshot['at'] = '2030-01-01T00:00:10+00:00'
            engine.store.put('account_snapshot', snapshot)
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://localhost') as client:
                assert (await client.get('/api/state')).json()['orders_enabled'] is False
                response = await client.get('/api/accounting/observation')
                view = response.json()
                assert response.headers['cache-control'] == 'no-store'
                assert view['complete_acquisitions'] == 1 and view['matched_publications'] == 1
                assert 'accounting_snapshot_outside_coverage' in view['activity_coverage']['issues']
                assert not view['accounting_by_symbol']['BTC']['passed']
                assert view['latency']['state']['samples'] == 1
                assert not any(k in response.text for k in ('account_id', 'api_key', 'secret_key', 'mapping_json'))
        finally: await engine.broker.close()
    asyncio.run(scenario())
