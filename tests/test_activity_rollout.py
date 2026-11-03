"""Rollout authorization, bounded collection and recovery with disposable mock evidence."""
import asyncio
from contextlib import closing, contextmanager
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta
import uuid
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace

import httpx
import pytest

from backend.activity_feed import current_accounting
from backend.activity_observation import Observation
from backend.activity_rollout import DAY, activated_settings, prepare, source_identity as real_source_identity
from backend.activity_validation import import_ledger
from backend.broker import AlpacaPaper
from backend.config import Settings
from backend.engine import Engine
from backend.store import Store

FIXTURE = Path(__file__).parent/'fixtures/activity_feed/btc-sanitized-v1'
NOW = '2030-01-01T00:00:00+00:00'


def legacy_summary_fixture(status='stopped'):
    """Inline a6bf6ca Observation.summary/Latency.view contract; no history lookup."""
    started = status not in {'prepared', 'failed'}
    return {
        'status': status,
        'reason': {'stopped': 'owner_stopped', 'failed': 'ledger_recheck_failed'}.get(status),
        'started_at': '2029-12-31T23:00:00+00:00' if started else None,
        'duration_seconds': 86400,
        'elapsed_seconds': (86400.125 if status == 'expired' else 180.125) if started else 0,
        'cycles': 3 if started else 0, 'complete_acquisitions': 2 if started else 0,
        'matched_publications': 2 if started else 0, 'received_bytes': 1024 if started else 0,
        'request_budget_units': 21 if started else 0,
        'max_acquisition_gap_seconds': 60.25 if started else 0,
        'last_success_at': '2029-12-31T23:02:00.125+00:00' if started else None,
        'blocked_reasons': {'incomplete_activity_coverage': 1} if started else {},
        'latency': {
            'acquisition': {'samples': 3 if started else 0, 'p95_upper_ms': 2000 if started else None, 'over_5000_ms': 0},
            'publication': {'samples': 3 if started else 0, 'p95_upper_ms': 250 if started else None, 'over_5000_ms': 0},
            'state': {'samples': 0, 'p95_upper_ms': None, 'over_5000_ms': 0},
        },
        'availability_samples': {'current': 2, 'incomplete': 1} if started else {},
        'growth_bytes': 2048, 'current_accounting_is_separate': True,
        'operational_acceptance': 'owner-review-required',
        'reader_enabled': status == 'observing', 'orders_enabled': False,
    }


def seed_legacy_lifecycle(store, summary, mapping_sha256):
    """Base lifecycle records retained their own ID even when summaries did not."""
    if summary['status'] not in {'prepared', 'failed'}:
        store.event('activity_rollout_started', {
            'run_id': 'd'*32, 'mapping_sha256': mapping_sha256, 'duration_seconds': 86400})
    if summary['status'] == 'stopped':
        store.event('activity_rollout_stopped', {'run_id': 'd'*32, **summary})
    elif summary['status'] == 'failed':
        store.event('activity_rollout_failed', {'run_id': 'd'*32, 'reason': summary['reason']})


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
    monkeypatch.setattr('backend.activity_rollout.utcnow', lambda: NOW)
    monkeypatch.setattr('backend.activity_rollout.source_identity', lambda: {'revision': '1'*40, 'files': {}})
    monkeypatch.setattr('backend.activity_feed.utcnow', lambda: NOW)
    monkeypatch.setattr('backend.broker.utcnow', lambda: NOW)
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    yield settings, store, path, sha, mapping
    store.close()


def prepared(rollout):
    settings, _, path, sha, mapping = rollout
    return approved_fixture(settings, prepare(settings, path, sha, mapping['account_id']))


def approval_policy():
    """Synthetic values exercise bindings; no operational policy is selected."""
    return {'schema_version': 1, 'tau_seconds': '0.01', 'tau_c_seconds': '0.01',
            'precision_seconds': '0.000001', 'overhead_policy': 'recorded-sleep-write-only',
            'e4_policy': 'allow-indeterminate', 'research_enabled': False, 'news_enabled': False,
            'state_poll_seconds': '5', 'observation_poll_seconds': '60',
            'local_post_policy': 'prohibit', 'compute_policy': 'quiet-host',
            'owner_decisions_sha256': '3'*64}


def approved_fixture(settings, spec, *, change=None, run_id=None, policy_overrides=None):
    from backend import activity_rollout as module
    policy_path = spec.ledger.parent/('policy-'+uuid.uuid4().hex+'.json')
    policy = approval_policy();policy.update(policy_overrides or {})
    policy_path.write_text(json.dumps(policy))
    now = datetime.fromisoformat(module.utcnow())
    proposal = module.propose(settings, spec, policy_path, (now-timedelta(hours=1)).isoformat(),
                              (now+timedelta(hours=1)).isoformat(), run_id=run_id)
    proposal['created_at'] = (now-timedelta(seconds=2)).isoformat()
    record = {'schema_version': 1, 'method': 'operator-attested', 'approved_by': 'synthetic operator',
              'approved_at': (now-timedelta(seconds=1)).isoformat(), 'proposal': proposal}
    if change:
        change(record)
    path = spec.ledger.parent/('approval-'+uuid.uuid4().hex+'.json')
    path.write_text(json.dumps(record))
    return module.authorize(settings, spec, path, hashlib.sha256(path.read_bytes()).hexdigest(), policy_path)


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
    if not spec.approval_path:
        spec = approved_fixture(settings, spec)
    observation = Observation(spec, clock=clock)
    observation.run_id = spec.run_id
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


def test_availability_sample_observes_reconciliation_between_acquisitions(rollout, monkeypatch):
    clock = [0]
    engine, calls, _ = mock_engine(rollout, clock=lambda: clock[0])
    observation = engine.activity_observation
    checks = iter((True, True, False))
    monkeypatch.setattr(observation, 'budget_ok', lambda: next(checks, False))
    now = lambda: (datetime.fromisoformat(NOW)+timedelta(seconds=clock[0])).isoformat()
    monkeypatch.setattr('backend.activity_feed.utcnow', now)

    async def reconciled_during_interval(delay):
        assert delay == 60
        assert observation.summary()['matched_publications'] == 1
        clock[0] += delay
        snapshot = engine.store.get('account_snapshot')
        snapshot['at'] = now()
        engine.store.put('account_snapshot', snapshot)
        current = current_accounting(engine.store, enabled=True)
        assert 'accounting_snapshot_outside_coverage' in current['activity_coverage']['issues']

    monkeypatch.setattr('backend.activity_observation.asyncio.sleep', reconciled_during_interval)
    async def scenario():
        try:
            await observation.run(engine)
            summary = engine.store.get('activity_rollout_observation')
            assert len(calls) == 7
            assert summary['complete_acquisitions'] == summary['matched_publications'] == 1
            assert summary['availability_samples'] == {'incomplete': 1}
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


def test_ledger_recheck_failure_retains_sanitized_receipt_and_disables_reader(rollout):
    engine, calls, _ = mock_engine(rollout)
    observation = engine.activity_observation
    observation.started, observation.status = None, 'prepared'
    engine.store.db.execute("UPDATE orders SET status='unknown'")
    async def scenario():
        try:
            await observation.run(engine)
            assert not calls and not engine.activity_enabled
            summary = observation.summary()
            assert summary['status'] == 'failed' and summary['reason'] == 'ledger_recheck_failed'
            assert engine.workers['fees']['status'] == 'disabled'
            receipts = engine.store.rows("SELECT payload FROM events WHERE type='activity_rollout_failed'")
            assert [json.loads(row['payload']) for row in receipts] == [
                {'run_id': observation.run_id, 'reason': 'ledger_recheck_failed'}]
            assert not engine.store.rows("SELECT seq FROM events WHERE type='activity_rollout_started'")
        finally: await engine.broker.close()
    asyncio.run(scenario())


def test_inflight_storage_limit_retains_scan_and_prevents_publication(rollout, monkeypatch):
    engine, calls, _ = mock_engine(rollout)
    checks = iter((True, False))
    monkeypatch.setattr(engine.activity_observation, 'budget_ok', lambda: next(checks, False))
    async def scenario():
        try:
            await asyncio.wait_for(engine.activity_observation.run(engine), 5)
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
                samples = engine.activity_observation.summary()['availability_samples']
                response = await client.get('/api/accounting/observation')
                view = response.json()
                repeated = await client.get('/api/accounting/observation')
                assert view['availability_samples'] == repeated.json()['availability_samples'] == samples
                assert engine.activity_observation.summary()['availability_samples'] == samples
                assert response.headers['cache-control'] == 'no-store'
                assert view['complete_acquisitions'] == 1 and view['matched_publications'] == 1
                assert 'accounting_snapshot_outside_coverage' in view['activity_coverage']['issues']
                assert not view['accounting_by_symbol']['BTC']['passed']
                assert view['latency']['state']['samples'] == 1
                assert not any(k in response.text for k in ('account_id', 'api_key', 'secret_key', 'mapping_json'))
        finally: await engine.broker.close()
    asyncio.run(scenario())


@pytest.mark.parametrize('boundary', ['prepared', 'stopped', 'deadline', 'start-during-request',
                                     'stop-during-request', 'deadline-during-request', 'replacement-during-request'])
def test_state_latency_excludes_requests_outside_same_active_window(rollout, monkeypatch, boundary):
    from backend.app import create_app
    clock = [0]
    engine, _, _ = mock_engine(rollout, clock=lambda: clock[0])
    observation = engine.activity_observation
    app = create_app(engine.settings, background=False, activity_observation=observation)
    app.state.engine = engine
    monkeypatch.setattr('backend.app.time', SimpleNamespace(monotonic=lambda: clock[0]))
    action = [lambda: None]
    duration = [2.5]
    def state():
        clock[0] += duration[0]
        action[0]()
        return {'orders_enabled': False}
    monkeypatch.setattr(engine, 'state', state)

    def start():
        observation.started, observation.status = clock[0], 'observing'

    def expire():
        clock[0] = observation.started+DAY

    def replace_observation():
        replacement = Observation(observation.prepared, clock=lambda: clock[0])
        replacement.started, replacement.status = clock[0], 'observing'
        engine.activity_observation = replacement

    async def scenario():
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://localhost') as client:
                if boundary in ('prepared', 'start-during-request'):
                    observation.started, observation.status = None, 'prepared'
                else:
                    assert (await client.get('/api/state')).status_code == 200
                    assert observation.summary()['latency']['state'] == {
                        'samples': 1, 'p95_upper_ms': 5000, 'over_5000_ms': 0}
                duration[0] = .001
                if boundary == 'stopped': observation.stop(engine.store, 'owner_stopped')
                if boundary == 'deadline': expire()
                if boundary == 'start-during-request': action[0] = start
                if boundary == 'stop-during-request': action[0] = lambda: observation.stop(engine.store, 'owner_stopped')
                if boundary == 'deadline-during-request': action[0] = expire
                if boundary == 'replacement-during-request': action[0] = replace_observation
                before = observation.summary()['latency']['state']
                response = await client.get('/api/state')
                assert response.status_code == 200 and response.json()['orders_enabled'] is False
                assert response.headers['cache-control'] == 'no-store'
                assert observation.summary()['latency']['state'] == before
                if observation.status == 'stopped':
                    assert engine.store.get('activity_rollout_observation')['latency']['state'] == before
                if boundary == 'replacement-during-request':
                    assert engine.activity_observation.summary()['latency']['state']['samples'] == 0
        finally: await engine.broker.close()
    asyncio.run(scenario())



@pytest.mark.parametrize('failed_path,occurrence,stage', [
    pytest.param('/v2/account', 1, 'initial-snapshot', id='snapshot-account'),
    pytest.param('/v2/positions', 1, 'initial-snapshot', id='snapshot-positions'),
    pytest.param('/v2/clock', 1, 'initial-snapshot', id='snapshot-clock'),
    pytest.param('/v2/account', 2, 'identity-before', id='identity-before'),
    pytest.param('/v2beta1/events/activities', 1, 'activity-stream', id='stream'),
    pytest.param('/v2/account', 3, 'identity-after', id='identity-after'),
    pytest.param('/v2/positions', 2, 'positions-after', id='positions-after'),
])
def test_failed_acquisition_identifies_stage_without_secrets_or_false_missing_history(rollout, failed_path, occurrence, stage):
    from collections import Counter
    from backend.activity_feed import current_accounting
    engine, calls, _ = mock_engine(rollout)
    transport = engine.broker.http._transport
    original = transport.handler
    counts = Counter()
    async def scenario():
        try:
            assert not (await engine.refresh_activity_feed())['issues']
            before = {t:engine.store.rows('SELECT * FROM '+t) for t in ('orders','fills','activities','observations')}
            calls.clear()
            def fail(request):
                path = request.url.path
                counts[path] += 1
                if path == failed_path and counts[path] == occurrence:
                    calls.append((request.method, path))
                    raise httpx.ReadTimeout('sensitive-secret-must-never-be-retained')
                return original(request)
            transport.handler = fail
            result = await engine.refresh_activity_feed()
            assert 'incomplete_activity_coverage' in result['issues']
            assert not {'activity_disappeared_from_replay','unreconciled_cash','unreconciled_asset_quantity'} & set(result['issues'])
            assert not result['effects'] and result['cash_reconciliation']['cash'] is None
            receipt = engine.broker._last_activity_acquisition
            diagnostics = receipt['diagnostics']
            assert diagnostics['failure_stage'] == stage and diagnostics['failure_kind'] == 'ReadTimeout'
            assert len(diagnostics['requests']) == len(calls) <= 7
            failed = next(x for x in diagnostics['requests'] if x['path'] == failed_path and x['failure_kind'] == 'ReadTimeout')
            assert failed['http_status'] is None and failed['dispatch'] == 'started-outcome-unknown'
            assert 'sensitive-secret' not in json.dumps(diagnostics)
            retained = json.loads(engine.store.rows("SELECT payload FROM activity_batches WHERE id=? AND phase='outcome'", (result['batch'],))[0]['payload'])
            assert retained['diagnostics'] == diagnostics
            view = current_accounting(engine.store, enabled=True, now=NOW)
            assert not view['accounting_by_symbol']['BTC']['passed']
            assert view['cash_reconciliation']['cash'] is None
            assert view['accounting_evidence']['historical_checkpoint']['cash'] == '99999.70'
            assert view['accounting_evidence']['historical_checkpoint']['current_authority'] is False
            assert all(engine.store.rows('SELECT * FROM '+t) == rows for t,rows in before.items())
        finally:
            await engine.broker.close()
    asyncio.run(scenario())


def test_complete_replay_omission_still_blocks_after_failure_classification_change(rollout):
    from backend.activity_feed import retain_batch, start_batch, publish_projection
    engine, _, capture = mock_engine(rollout)
    async def scenario():
        try:
            assert not (await engine.refresh_activity_feed())['issues']
            events = capture['events'][:-1]
            batch = start_batch(engine.store, rollout[4]['account_id'], '2026-10-24T00:00:00Z', NOW)
            raw = b''.join(('data: '+json.dumps(e)+'\n\n').encode() for e in events)
            receipt = dict(engine.broker._last_activity_acquisition)
            receipt.update(events=events, raw=raw)
            retain_batch(engine.store, batch, rollout[4]['account_id'], receipt)
            result = publish_projection(engine.store, batch, json.loads(engine.activity_observation.prepared.mapping_json), now=NOW)
            assert 'activity_disappeared_from_replay' in result['issues']
            assert not result['effects'] and result['cash_reconciliation']['cash'] is None
        finally:
            await engine.broker.close()
    asyncio.run(scenario())


def inspection_state(engine, calls):
    # Logical contents include immutable receipts and execution tables; total_changes
    # also catches writes which restore the original values before returning.
    return (tuple(engine.store.db.iterdump()), engine.store.db.total_changes,
            tuple(calls), engine.settings, engine.activity_enabled)


@contextmanager
def unchanged_inspection(engine, calls):
    before = inspection_state(engine, calls)
    try:
        yield
    finally:
        assert inspection_state(engine, calls) == before


@pytest.mark.parametrize('change', ['newer-snapshot', 'stale-snapshot', 'future-snapshot', 'cash',
                                    'pending-attempt', 'disabled', 'forged-witness', 'forged-expiry',
                                    'missing-counter', 'malformed-counter', 'unbound-snapshot'])
def test_accounting_window_recheck_denies_changed_or_expired_opportunities(rollout, change):
    from backend.accounting_window import capture, recheck
    from backend.activity_feed import FeedError, start_batch
    engine, calls, _ = mock_engine(rollout)
    async def scenario():
        try:
            await engine.refresh_activity_feed()
            before_calls = list(calls)
            with unchanged_inspection(engine, calls):
                witness = capture(engine.store, 'BTC', enabled=True, now=NOW)
                assert witness['execution_authorized'] is False
                evidence = current_accounting(engine.store, enabled=True, now=NOW)['accounting_evidence']
                assert witness['snapshot_epoch'] == engine.store.get('account_snapshot')['snapshot_epoch']
                assert witness['snapshot_epoch'] == engine.store.get('snapshot_epoch') == evidence['acquisition_epoch']
                assert recheck(engine.store, witness, enabled=True, now=NOW) == witness
            now, enabled = NOW, True
            if change == 'newer-snapshot':
                snapshot = engine.store.get('account_snapshot');snapshot['at'] = '2030-01-01T00:00:10+00:00'
                engine.store.put('account_snapshot', snapshot);now = snapshot['at']
            elif change == 'stale-snapshot': now = '2030-01-01T00:00:30.000001+00:00'
            elif change == 'future-snapshot': now = '2029-12-31T23:59:59.999999+00:00'
            elif change == 'missing-counter':engine.store.db.execute("DELETE FROM state WHERE key='snapshot_epoch'")
            elif change == 'malformed-counter':engine.store.put('snapshot_epoch', True)
            elif change == 'unbound-snapshot':
                snapshot = engine.store.get('account_snapshot');snapshot['snapshot_epoch'] += 1
                engine.store.put('account_snapshot', snapshot)
            elif change == 'cash':
                snapshot = engine.store.get('account_snapshot');snapshot['account']['cash'] = '99999.69';engine.store.put('account_snapshot', snapshot)
            elif change == 'pending-attempt':start_batch(engine.store, rollout[4]['account_id'], '2026-10-24T00:00:00Z', NOW)
            elif change == 'disabled':enabled = False
            elif change == 'forged-expiry':witness['expires_at'] = '2099-01-01T00:00:00+00:00'
            else:witness['execution_authorized'] = True
            with unchanged_inspection(engine, calls):
                with pytest.raises(FeedError):recheck(engine.store, witness, enabled=enabled, now=now)
            assert calls == before_calls
        finally:
            await engine.broker.close()
    asyncio.run(scenario())


@pytest.mark.parametrize('corruption', ['hash', 'non-json', 'list-id', 'object-id', 'string', 'list-sha'])
def test_historical_checkpoint_cannot_be_forged_into_current_authority(rollout, corruption):
    from backend.accounting_window import capture
    from backend.activity_feed import FeedError, current_accounting
    engine, _, _ = mock_engine(rollout)
    async def scenario():
        try:
            await engine.refresh_activity_feed()
            pointer = engine.store.get('activity_last_covered_projection')
            if corruption == 'hash': pointer['sha256'] = '0'*64
            elif corruption == 'list-id': pointer['id'] = ['x']
            elif corruption == 'object-id': pointer['id'] = {'x': 'y'}
            elif corruption == 'list-sha': pointer['sha256'] = ['x']
            elif corruption == 'string': pointer = 'invalid-pointer'
            if corruption == 'non-json':
                engine.store.db.execute("UPDATE state SET value=? WHERE key='activity_last_covered_projection'", ('not-json',))
            else:
                engine.store.put('activity_last_covered_projection', pointer)
            snapshot = engine.store.get('account_snapshot');snapshot['at'] = '2030-01-01T00:00:10+00:00';engine.store.put('account_snapshot', snapshot)
            view = current_accounting(engine.store, enabled=True, now=snapshot['at'])
            assert view['accounting_evidence']['historical_checkpoint'] is None
            assert view['cash_reconciliation']['cash'] is None
            with pytest.raises(FeedError):capture(engine.store, 'BTC', enabled=True, now=snapshot['at'])
        finally:await engine.broker.close()
    asyncio.run(scenario())


@pytest.mark.parametrize('interruption', ['stream-deadline', 'attempt-deadline', 'cancellation'])
def test_deadlines_and_task_cancellation_retain_distinct_failure_classes(rollout, monkeypatch, interruption):
    engine, calls, _ = mock_engine(rollout)
    original = engine.broker.http._transport.handler
    if interruption == 'stream-deadline': monkeypatch.setattr('backend.activity_feed.STREAM_SECONDS', 0)
    if interruption == 'attempt-deadline': monkeypatch.setattr('backend.activity_feed.ATTEMPT_SECONDS', 0)

    async def scenario():
        entered = asyncio.Event()
        class Stalled(httpx.AsyncByteStream):
            async def __aiter__(self):
                yield b': heartbeat\n\n'
                entered.set()
                await asyncio.Event().wait()
        def handler(request):
            if request.url.path != '/v2beta1/events/activities': return original(request)
            calls.append((request.method, request.url.path))
            return httpx.Response(200, headers={'content-type': 'text/event-stream'}, stream=Stalled())
        engine.broker.http._transport.handler = handler
        try:
            task = asyncio.create_task(engine.refresh_activity_feed())
            await entered.wait()
            if interruption == 'cancellation':
                task.cancel()
                with pytest.raises(asyncio.CancelledError): await task
            else:
                result = await task
                assert 'incomplete_activity_coverage' in result['issues']
                assert result['cash_reconciliation']['cash'] is None
            receipt = engine.broker._last_activity_acquisition
            assert not receipt['complete'] and receipt['raw'] == b': heartbeat\n\n'
            diagnostics = receipt['diagnostics']
            assert diagnostics['failure_kind'] == ('CancelledError' if interruption == 'cancellation' else 'TimeoutError')
            stream = next(r for r in diagnostics['requests'] if r['path'] == '/v2beta1/events/activities')
            assert stream['failure_kind'] == ('TimeoutError' if interruption == 'stream-deadline' else 'CancelledError')
            retained = json.loads(engine.store.rows("SELECT payload FROM activity_batches WHERE phase='outcome'")[0]['payload'])
            assert retained['diagnostics'] == diagnostics
        finally: await engine.broker.close()
    asyncio.run(scenario())


def test_partial_http_body_failure_retains_received_status_without_exception_text(rollout):
    engine, calls, _ = mock_engine(rollout)
    class Partial(httpx.AsyncByteStream):
        closed = False
        async def __aiter__(self):
            yield b'{"id":'
            raise httpx.ReadTimeout('sensitive-secret-must-never-be-retained')
        async def aclose(self):
            self.closed = True
    body = Partial()
    def handler(request):
        calls.append((request.method, request.url.path))
        assert request.url.path == '/v2/account'
        return httpx.Response(200, stream=body)
    engine.broker.http._transport.handler = handler
    async def scenario():
        try:
            result = await engine.refresh_activity_feed()
            assert 'incomplete_activity_coverage' in result['issues']
            assert result['cash_reconciliation']['cash'] is None and not result['effects']
            receipt = engine.broker._last_activity_acquisition
            assert not receipt['complete'] and body.closed
            diagnostics = receipt['diagnostics']
            assert diagnostics['failure_kind'] == 'ReadTimeout'
            assert len(diagnostics['requests']) == len(calls) == 1
            request = diagnostics['requests'][0]
            assert request['http_status'] == 200 and request['dispatch'] == 'response-received'
            assert request['failure_kind'] == 'ReadTimeout'
            assert 'sensitive-secret' not in json.dumps(diagnostics)
            retained = json.loads(engine.store.rows("SELECT payload FROM activity_batches WHERE phase='outcome'")[0]['payload'])
            assert retained['diagnostics'] == diagnostics
        finally: await engine.broker.close()
    asyncio.run(scenario())


def test_state_bounds_evidence_validation_and_rechecks_tampering_on_later_reads(rollout, monkeypatch):
    from backend import activity_feed
    engine, _, _ = mock_engine(rollout)
    monkeypatch.setattr('backend.engine.utcnow', lambda: NOW)
    monkeypatch.setattr('backend.inventory.utcnow', lambda: NOW)
    monkeypatch.setattr('backend.readiness.utcnow', lambda: NOW)
    monkeypatch.setattr('backend.engine.experiment.state', lambda _: None)
    monkeypatch.setattr(engine, 'replay_view', lambda: None)
    async def scenario():
        try:
            projection = await engine.refresh_activity_feed()
            validated = []
            original = activity_feed._validate_batch
            def counted(store, batch):
                validated.append(batch)
                return original(store, batch)
            monkeypatch.setattr(activity_feed, '_validate_batch', counted)
            state = engine.state()
            assert state['accounting']['cash_reconciliation']['cash'] == '99999.70'
            assert state['readiness']['cash_reconciliation']['cash'] == '99999.70'
            assert state['accounting']['accounting_evidence']['historical_checkpoint']['batch'] == projection['batch']
            assert validated == [projection['batch']]
            engine.store.db.execute('UPDATE activity_events SET sha256=? WHERE batch=? AND ordinal=0', ('0'*64, projection['batch']))
            current = engine.state()
            assert validated == [projection['batch'], projection['batch']]
            for view in (current['accounting'], current['readiness']):
                assert view['accounting_evidence']['historical_checkpoint'] is None
                assert view['cash_reconciliation']['cash'] is None
        finally: await engine.broker.close()
    asyncio.run(scenario())


@pytest.fixture
def s3_state(rollout, monkeypatch):
    engine, calls, _ = mock_engine(rollout)
    clock = [NOW]
    for module in ('engine', 'inventory', 'readiness', 'activity_feed', 'broker'):
        monkeypatch.setattr('backend.'+module+'.utcnow', lambda: clock[0])
    monkeypatch.setattr('backend.engine.experiment.state', lambda _: None)
    monkeypatch.setattr(engine, 'replay_view', lambda: None)
    projection = asyncio.run(engine.refresh_activity_feed())
    try:
        yield engine, calls, projection, clock
    finally:
        asyncio.run(engine.broker.close())


@pytest.fixture
def s3_validations(monkeypatch):
    from collections import Counter
    from backend import activity_feed
    counts = Counter()
    original = activity_feed._validate_batch
    def counted(store, batch):
        counts[batch] += 1
        return original(store, batch)
    monkeypatch.setattr(activity_feed, '_validate_batch', counted)
    return counts


def test_s3_standalone_accounting_validates_each_selected_batch_once_per_call(s3_state, s3_validations):
    engine, calls, covered, _ = s3_state
    with unchanged_inspection(engine, calls):
        current = current_accounting(engine.store, enabled=True, now=NOW)
    assert s3_validations == {covered['batch']: 1}
    assert current['activity_coverage']['issues'] == []
    assert current['cash_reconciliation']['cash'] == '99999.70'
    assert current['accounting_evidence']['historical_checkpoint']['batch'] == covered['batch']
    with unchanged_inspection(engine, calls):
        assert current_accounting(engine.store, enabled=True, now=NOW) == current
    assert s3_validations == {covered['batch']: 2}

    engine.broker.trading.normal = 0
    failed = asyncio.run(engine.refresh_activity_feed())
    s3_validations.clear()  # Acquisition and publication are outside the accounting read.
    with unchanged_inspection(engine, calls):
        current = current_accounting(engine.store, enabled=True, now=NOW)
    assert s3_validations == {covered['batch']: 1, failed['batch']: 1}
    assert 'incomplete_activity_coverage' in current['activity_coverage']['issues']
    assert current['cash_reconciliation']['cash'] is None
    history = current['accounting_evidence']['historical_checkpoint']
    assert history['batch'] == covered['batch'] and history['current_authority'] is False
    assert current['accounting_evidence']['latest_attempt']['id'] == failed['batch']


def test_s3_distinct_failed_and_historical_batches_each_validate_once(s3_state, s3_validations):
    engine, calls, covered, _ = s3_state
    engine.broker.trading.normal = 0
    failed = asyncio.run(engine.refresh_activity_feed())
    s3_validations.clear()  # Publication is outside the state read.
    with unchanged_inspection(engine, calls):
        state = engine.state()
    assert s3_validations == {covered['batch']: 1, failed['batch']: 1}
    for view in (state['accounting'], state['readiness']):
        assert view['cash_reconciliation']['cash'] is None
        history = view['accounting_evidence']['historical_checkpoint']
        assert history['batch'] == covered['batch'] and history['current_authority'] is False
        assert view['accounting_evidence']['latest_attempt']['id'] == failed['batch']
    engine.store.db.execute('UPDATE activity_events SET frame=? WHERE batch=? AND ordinal=0', ('corrupt', covered['batch']))
    with unchanged_inspection(engine, calls):
        state = engine.state()
    assert s3_validations == {covered['batch']: 2, failed['batch']: 2}
    assert state['accounting']['accounting_evidence']['historical_checkpoint'] is None


@pytest.mark.parametrize('phase', ['start', 'outcome'])
@pytest.mark.parametrize('future', [False, True], ids=['same-clock', 'backward-clock'])
def test_s3_new_attempt_remains_visible_without_hiding_history(s3_state, s3_validations, phase, future):
    from backend.activity_feed import start_batch, retain_batch
    engine, calls, covered, clock = s3_state
    at = (datetime.fromisoformat(NOW)+timedelta(seconds=int(future))).isoformat()
    clock[0] = at
    batch = start_batch(engine.store, engine.store.get('account_binding'), '2026-10-24T00:00:00Z', at)
    if phase == 'outcome':
        retain_batch(engine.store, batch, engine.store.get('account_binding'),
                     {'complete': False, 'received_at': at, 'raw': b'', 'events': []})
    clock[0] = NOW
    with unchanged_inspection(engine, calls):
        state = engine.state()
    assert s3_validations == {covered['batch']: 1}
    for view in (state['accounting'], state['readiness']):
        assert view['cash_reconciliation']['cash'] is None
        assert 'new_activity_attempt_pending' in view['activity_coverage']['issues']
        assert ('activity_attempt_time_unavailable' in view['activity_coverage']['issues']) is future
        assert view['accounting_evidence']['latest_attempt'] == {
            'id': batch, 'phase': phase, 'at': at, 'status': 'pending' if phase == 'start' else 'unpublished'}
        assert view['accounting_evidence']['historical_checkpoint']['batch'] == covered['batch']


@pytest.mark.parametrize('damage,issue', [
    ('frame', 'activity_evidence_integrity_error'), ('raw', 'activity_evidence_integrity_error'),
    ('outcome-json', 'activity_evidence_integrity_error'), ('inputs', 'accounting_inputs_changed'),
    ('epoch', 'accounting_snapshot_replaced'), ('counter', 'accounting_snapshot_epoch_unavailable'),
])
def test_s3_next_state_rechecks_changed_evidence(s3_state, s3_validations, damage, issue):
    from backend.accounting_snapshot import commit_snapshot
    engine, calls, projection, _ = s3_state
    with unchanged_inspection(engine, calls):
        assert engine.state()['accounting']['cash_reconciliation']['cash'] == '99999.70'
    if damage == 'frame':
        engine.store.db.execute('UPDATE activity_events SET frame=? WHERE batch=? AND ordinal=0', ('corrupt', projection['batch']))
    elif damage in {'raw', 'outcome-json'}:
        outcome = json.loads(engine.store.rows("SELECT payload FROM activity_batches WHERE id=? AND phase='outcome'", (projection['batch'],))[0]['payload'])
        outcome['raw_hex'] = '00'
        engine.store.db.execute("UPDATE activity_batches SET payload=? WHERE id=? AND phase='outcome'",
                                ('{' if damage == 'outcome-json' else json.dumps(outcome), projection['batch']))
    elif damage == 'counter':
        engine.store.put('snapshot_epoch', True)
    else:
        snapshot = engine.store.get('account_snapshot')
        if damage == 'inputs':
            snapshot['account']['cash'] = '99999.69'
            engine.store.put('account_snapshot', snapshot)
        else:
            with engine.store.transaction():
                commit_snapshot(engine.store, snapshot)
    with unchanged_inspection(engine, calls):
        state = engine.state()
    assert s3_validations == {projection['batch']: 2}
    for view in (state['accounting'], state['readiness']):
        assert issue in view['activity_coverage']['issues']
        assert view['cash_reconciliation']['cash'] is None
        assert all(not item['passed'] for item in view['accounting_by_symbol'].values())


@pytest.mark.parametrize('denial', ['disabled', 'snapshot-stale', 'acquisition-stale'])
def test_s3_current_denials_preserve_historical_attribution(s3_state, s3_validations, denial):
    engine, calls, projection, clock = s3_state
    if denial == 'disabled': engine.settings = replace(engine.settings, enable_activity_feed=False)
    else: clock[0] = (datetime.fromisoformat(NOW)+timedelta(seconds=31 if denial == 'snapshot-stale' else 91)).isoformat()
    with unchanged_inspection(engine, calls):
        state = engine.state()
    assert s3_validations == {projection['batch']: 1}
    for view in (state['accounting'], state['readiness']):
        assert view['cash_reconciliation']['cash'] is None
        assert view['accounting_evidence']['historical_checkpoint']['cash'] == '99999.70'
    assert state['inventory']['status'] == 'matched'


def test_s3_reuse_never_shares_caller_issues_or_accounting_gates(s3_state, s3_validations):
    from backend.activity_feed import accounting_read, batch_events, read_projection, FeedError
    engine, calls, projection, _ = s3_state
    with unchanged_inspection(engine, calls), accounting_read(engine.store, cutoff=NOW) as context:
        events, coverage, issues = batch_events(engine.store, projection['batch'], read_context=context)
        events.clear(); coverage.clear(); issues.append('caller-only')
        first = read_projection(engine.store, read_context=context)
        first['issues'].append('caller-only'); first['cash_reconciliation']['cash'] = '0'
        denied = current_accounting(engine.store, enabled=False, read_context=context)
        stale = current_accounting(engine.store, enabled=True, max_snapshot_age=-1, read_context=context)
        passed = current_accounting(engine.store, enabled=True, read_context=context)
        assert denied['activity_coverage']['issues'] == ['activity_reader_disabled']
        assert stale['activity_coverage']['issues'] == ['accounting_snapshot_stale']
        assert passed['activity_coverage']['issues'] == []
        assert passed['cash_reconciliation']['cash'] == '99999.70'
        assert s3_validations == {projection['batch']: 1}
        with pytest.raises(FeedError):
            current_accounting(engine.store, enabled=True, now='2030-01-02T00:00:00Z', read_context=context)
    with pytest.raises(FeedError):
        current_accounting(engine.store, enabled=True, read_context=context)


def test_s3_one_cutoff_survives_clock_change_but_next_read_expires(s3_state, monkeypatch, s3_validations):
    from backend import activity_feed
    engine, calls, projection, clock = s3_state
    original = activity_feed._validate_batch
    def advance(store, batch):
        result = original(store, batch)
        clock[0] = '2030-01-01T00:02:00+00:00'
        return result
    monkeypatch.setattr(activity_feed, '_validate_batch', advance)
    with unchanged_inspection(engine, calls):
        first = engine.state()
        second = engine.state()
    assert first['readiness']['as_of'] == NOW
    for key in ('accounting', 'readiness'):
        assert first[key]['activity_coverage']['issues'] == []
        assert 'activity_acquisition_stale' in second[key]['activity_coverage']['issues']
    assert s3_validations == {projection['batch']: 2}


def test_s3_interrupted_state_is_read_only_and_next_read_recovers(s3_state, monkeypatch):
    from backend import activity_feed
    engine, calls, _, _ = s3_state
    original = activity_feed._validate_batch
    def broken(store, batch):
        raise RuntimeError('fixture read interrupted')
    monkeypatch.setattr(activity_feed, '_validate_batch', broken)
    with unchanged_inspection(engine, calls):
        with pytest.raises(RuntimeError, match='fixture read interrupted'): engine.state()
    monkeypatch.setattr(activity_feed, '_validate_batch', original)
    with unchanged_inspection(engine, calls):
        assert engine.state()['accounting']['activity_coverage']['issues'] == []


@pytest.mark.parametrize('fail', [False, True], ids=['success', 'exception'])
def test_s3_state_serializes_reconciliation_and_releases_context(s3_state, monkeypatch, fail):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from backend import activity_feed
    from backend.accounting_snapshot import commit_snapshot
    engine, calls, projection, _ = s3_state
    snapshot = engine.store.get('account_snapshot')
    go, probed = Event(), Event()
    lock_available, contexts = [], []
    original_validate, original_state = activity_feed._validate_batch, engine._state
    def capture_context(*, read_context=None):
        contexts.append(read_context)
        return original_state(read_context=read_context)
    monkeypatch.setattr(engine, '_state', capture_context)
    def reconcile():
        assert go.wait(5)
        acquired = engine.store.lock.acquire(blocking=False)
        lock_available.append(acquired)
        if acquired: engine.store.lock.release()
        probed.set()
        with engine.store.transaction():
            return commit_snapshot(engine.store, snapshot)
    def gated(store, batch):
        go.set()
        assert probed.wait(5)
        assert lock_available == [False]
        if fail: raise RuntimeError('fixture read interrupted')
        return original_validate(store, batch)
    monkeypatch.setattr(activity_feed, '_validate_batch', gated)
    with ThreadPoolExecutor(max_workers=1) as pool:
        writer = pool.submit(reconcile)
        try:
            if fail:
                with pytest.raises(RuntimeError, match='fixture read interrupted'): engine.state()
            else:
                first = engine.state()
                assert first['accounting']['activity_coverage']['issues'] == []
            assert writer.result(timeout=5) == snapshot['snapshot_epoch']+1
        finally:
            go.set()
    assert all(c.store is None and c.source is None and not c.batches for c in contexts)
    monkeypatch.setattr(activity_feed, '_validate_batch', original_validate)
    with unchanged_inspection(engine, calls):
        second = engine.state()
    assert second['accounting']['activity_coverage']['issues'] == ['accounting_snapshot_replaced']


def test_older_checkpoint_validates_its_own_evidence_after_a_failed_acquisition(rollout):
    engine, _, _ = mock_engine(rollout)
    async def scenario():
        try:
            covered = await engine.refresh_activity_feed()
            engine.broker.trading.normal = 0
            await engine.refresh_activity_feed()
            current = current_accounting(engine.store, enabled=True, now=NOW)
            assert current['accounting_evidence']['historical_checkpoint']['batch'] == covered['batch']
            assert current['cash_reconciliation']['cash'] is None
            engine.store.db.execute('UPDATE activity_events SET sha256=? WHERE batch=? AND ordinal=0', ('0'*64, covered['batch']))
            assert current_accounting(engine.store, enabled=True, now=NOW)['accounting_evidence']['historical_checkpoint'] is None
        finally: await engine.broker.close()
    asyncio.run(scenario())


def test_current_reads_keep_first_attempt_visible_despite_backward_clock(rollout):
    from backend.activity_feed import retain_batch, start_batch
    _, store, _, _, mapping = rollout
    before = (datetime.fromisoformat(NOW)-timedelta(seconds=1)).isoformat()
    later = (datetime.fromisoformat(NOW)+timedelta(seconds=1)).isoformat()
    def evidence(now):
        view = current_accounting(store, enabled=True, now=now)
        assert view['cash_reconciliation']['cash'] is None
        result = view['accounting_evidence']
        assert all(result[k] is None for k in ('coverage_until', 'acquired_at', 'published_at', 'batch', 'input_sha256', 'mapping_sha256'))
        return result
    assert evidence(NOW)['latest_attempt'] is None
    batch = start_batch(store, mapping['account_id'], before, NOW)
    pending = {'id': batch, 'phase': 'start', 'at': NOW, 'status': 'pending'}
    assert evidence(before)['latest_attempt'] == pending
    assert evidence(NOW)['latest_attempt'] == pending
    retain_batch(store, batch, mapping['account_id'], {'complete': False, 'received_at': later, 'raw': b'', 'events': []})
    assert evidence(NOW)['latest_attempt'] == {'id': batch, 'phase': 'outcome', 'at': later, 'status': 'unpublished'}
    assert evidence(later)['latest_attempt'] == {'id': batch, 'phase': 'outcome', 'at': later, 'status': 'unpublished'}


def test_legacy_ledger_without_activity_tables_has_no_latest_attempt(rollout):
    store = rollout[1]
    store.db.execute('DROP TABLE activity_batches')
    store.db.execute('DROP TABLE activity_projections')
    view = current_accounting(store, enabled=True, now=NOW)
    assert view['accounting_evidence']['latest_attempt'] is None
    assert view['accounting_evidence']['historical_checkpoint'] is None
    assert view['cash_reconciliation']['cash'] is None


@pytest.mark.parametrize('step', [0, -1], ids=['identical-time', 'backward-wall'])
def test_read_only_window_inspection_serializes_with_reconciliation(rollout, monkeypatch, step):
    from backend.accounting_snapshot import commit_snapshot
    from backend.activity_feed import FeedError
    engine, calls, _ = mock_engine(rollout)
    clock = [NOW]
    for target in ('backend.accounting_window.utcnow', 'backend.activity_feed.utcnow', 'backend.broker.utcnow'):
        monkeypatch.setattr(target, lambda: clock[0])
    async def scenario():
        queued = None
        try:
            await engine.refresh_activity_feed()
            with unchanged_inspection(engine, calls):
                witness = await engine.inspect_accounting_window('BTC')
            async with engine.lock:
                entered = asyncio.Event()
                async def inspect():
                    entered.set()
                    return await engine.inspect_accounting_window('BTC', expected=witness)
                queued = asyncio.create_task(inspect())
                await entered.wait()
                assert not queued.done()
                clock[0] = (datetime.fromisoformat(NOW)+timedelta(seconds=step)).isoformat()
                snapshot = await engine.broker.snapshot()
                assert snapshot['account'] == engine.store.get('account_snapshot')['account']
                with engine.store.transaction():
                    epoch = commit_snapshot(engine.store, snapshot)
                clock[0] = NOW
                assert epoch == witness['snapshot_epoch']+1
                view = current_accounting(engine.store, enabled=True, now=clock[0])
                assert view['activity_coverage']['issues'] == ['accounting_snapshot_replaced']
                after_reconciliation = inspection_state(engine, calls)
            with pytest.raises(FeedError):await queued
            assert inspection_state(engine, calls) == after_reconciliation
            assert not engine.lock.locked()
            with unchanged_inspection(engine, calls):
                with pytest.raises(FeedError):await engine.inspect_accounting_window('BTC')
            await engine.refresh_activity_feed()
            with unchanged_inspection(engine, calls):
                fresh = await engine.inspect_accounting_window('BTC')
                assert fresh['snapshot_epoch'] > epoch
                assert await engine.inspect_accounting_window('BTC', expected=fresh) == fresh
                with pytest.raises(FeedError):await engine.inspect_accounting_window('BTC', expected=witness)
            assert not engine.lock.locked() and not engine.settings.enable_orders
        finally:
            if queued and not queued.done():
                queued.cancel()
                await asyncio.gather(queued, return_exceptions=True)
            await engine.broker.close()
    asyncio.run(scenario())


@pytest.mark.parametrize('version', [
    pytest.param('missing', id='missing'), pytest.param(None, id='null'),
    pytest.param(2, id='different'), pytest.param(0, id='zero'), pytest.param(-1, id='negative'),
    pytest.param(True, id='boolean'), pytest.param('1', id='string'), pytest.param(1.0, id='float'),
    pytest.param(float('nan'), id='nan'), pytest.param(float('inf'), id='infinity'),
    pytest.param(object(), id='non-serializable'),
])
def test_s2_invalid_witness_version_denies_recheck_without_writes(rollout, monkeypatch, version):
    from backend.activity_feed import FeedError
    engine, calls, _ = mock_engine(rollout)
    monkeypatch.setattr('backend.accounting_window.utcnow', lambda: NOW)
    async def scenario():
        try:
            await engine.refresh_activity_feed()
            with unchanged_inspection(engine, calls):
                witness = await engine.inspect_accounting_window('BTC')
                assert witness['snapshot_epoch'] == 1
                if version == 'missing':witness.pop('snapshot_epoch')
                else:witness['snapshot_epoch'] = version
                with pytest.raises(FeedError):await engine.inspect_accounting_window('BTC', expected=witness)
                fresh = await engine.inspect_accounting_window('BTC')
                assert fresh['snapshot_epoch'] == 1 and fresh['execution_authorized'] is False
            assert not engine.lock.locked()
        finally:await engine.broker.close()
    asyncio.run(scenario())


def test_s2_unversioned_replacement_requires_fresh_snapshot_and_acquisition(rollout, monkeypatch):
    from backend.accounting_snapshot import commit_snapshot
    from backend.activity_feed import FeedError
    engine, calls, _ = mock_engine(rollout)
    store = engine.store
    monkeypatch.setattr('backend.accounting_window.utcnow', lambda: NOW)
    async def scenario():
        try:
            await engine.refresh_activity_feed()
            with unchanged_inspection(engine, calls):
                original = await engine.inspect_accounting_window('BTC')
            # Diagnostic lifecycle records are not actual pending accounting batches.
            store.event('activity_attempt_started', {'run_id': 'diagnostic-only', 'attempt_id': 'diagnostic-only'})
            with unchanged_inspection(engine, calls):
                assert await engine.inspect_accounting_window('BTC', expected=original) == original
            replacement = store.get('account_snapshot');replacement.pop('snapshot_epoch')
            store.put('account_snapshot', replacement)
            assert store.get('snapshot_epoch') == original['snapshot_epoch']
            with unchanged_inspection(engine, calls):
                with pytest.raises(FeedError):await engine.inspect_accounting_window('BTC')
                with pytest.raises(FeedError):await engine.inspect_accounting_window('BTC', expected=original)
            snapshot = await engine.broker.snapshot()
            async with engine.lock:
                with store.transaction():epoch = commit_snapshot(store, snapshot)
            assert epoch == original['snapshot_epoch']+1
            with unchanged_inspection(engine, calls):
                with pytest.raises(FeedError):await engine.inspect_accounting_window('BTC')
            await engine.refresh_activity_feed()
            with unchanged_inspection(engine, calls):
                fresh = await engine.inspect_accounting_window('BTC')
                assert fresh['snapshot_epoch'] == store.get('snapshot_epoch') > epoch
                assert await engine.inspect_accounting_window('BTC', expected=fresh) == fresh
                with pytest.raises(FeedError):await engine.inspect_accounting_window('BTC', expected=original)
        finally:await engine.broker.close()
    asyncio.run(scenario())


@pytest.mark.parametrize('limit,age,allowed', [
    pytest.param(30,30,True,id='default-equality'),
    pytest.param(30,30.000001,False,id='default-expired'),
    pytest.param(10.5,10.5,True,id='stricter-equality'),
    pytest.param(10.5,10.500001,False,id='stricter-expired'),
    pytest.param(120,30,True,id='ceiling-equality'),
    pytest.param(120,30.000001,False,id='ceiling-expired'),
    pytest.param(30,-0.000001,False,id='future-evidence'),
    pytest.param(float('nan'),0,False,id='invalid-limit'),
])
def test_window_preserves_stricter_snapshot_age_and_fixed_thirty_second_ceiling(rollout, limit, age, allowed):
    from backend.accounting_window import capture, recheck
    from backend.activity_feed import FeedError
    engine, calls, _ = mock_engine(rollout)
    async def scenario():
        try:
            await engine.refresh_activity_feed()
            now = (datetime.fromisoformat(NOW)+timedelta(seconds=age)).isoformat()
            with unchanged_inspection(engine, calls):
                if allowed:
                    witness = capture(engine.store, 'BTC', enabled=True, now=NOW, max_snapshot_age=limit)
                    expected_expiry = datetime.fromisoformat(NOW)+timedelta(seconds=min(30,limit))
                    assert witness['expires_at'] == expected_expiry.isoformat()
                    assert recheck(engine.store, witness, enabled=True, now=now, max_snapshot_age=limit) == witness
                    assert witness['execution_authorized'] is False
                else:
                    with pytest.raises(FeedError):capture(engine.store, 'BTC', enabled=True, now=now, max_snapshot_age=limit)
        finally:await engine.broker.close()
    asyncio.run(scenario())



def timing_events(store, kind):
    return [json.loads(row['payload']) for row in store.rows(
        'SELECT payload FROM events WHERE type=? ORDER BY seq', (kind,))]


def one_timing_cycle(engine, monkeypatch, wall_step=0):
    """A shortened fixture window: one attempt and the unchanged 60-second sleep."""
    elapsed, wall_offset = [0], [0]
    observation = engine.activity_observation
    observation.clock = lambda: elapsed[0]
    observation.wall_clock = lambda: (datetime.fromisoformat(NOW)+timedelta(
        seconds=elapsed[0]+wall_offset[0])).isoformat()
    woke = [False]
    monkeypatch.setattr(observation, 'budget_ok', lambda: not woke[0])

    async def sleep(delay):
        assert delay == 60
        elapsed[0] += delay
        wall_offset[0] += wall_step
        woke[0] = True
    monkeypatch.setattr('backend.activity_observation.asyncio.sleep', sleep)
    return elapsed


def test_s0_cycle_diagnostics_bind_identity_without_mutating_outcome(rollout, monkeypatch):
    engine, calls, _ = mock_engine(rollout)
    one_timing_cycle(engine, monkeypatch)
    before = {table: engine.store.rows('SELECT * FROM '+table)
              for table in ('orders', 'fills', 'activities', 'observations', 'equity', 'shadow')}
    async def scenario():
        try:
            await engine.activity_observation.run(engine)
            started, = timing_events(engine.store, 'activity_attempt_started')
            finished, = timing_events(engine.store, 'activity_attempt_finished')
            assert started['attempt_id'] == finished['attempt_id']
            assert started['sequence'] == finished['sequence'] == 1
            assert finished['batch_started'] and finished['outcome_retained'] and finished['acquisition_counted']
            assert finished['publication'] == 'published'
            rows = engine.store.rows('SELECT id,phase,payload FROM activity_batches ORDER BY rowid')
            assert [(r['id'], r['phase']) for r in rows] == [(started['attempt_id'], 'start'), (started['attempt_id'], 'outcome')]
            receipt = json.loads(rows[1]['payload'])
            assert 'publication' not in receipt and 'boundaries' not in receipt
            assert len(receipt['diagnostics']['requests']) == len(calls) == 7
            assert all(p['state'] == 'not-observed' for request in receipt['diagnostics']['requests']
                       for p in request['phases'].values())
            assert finished['boundaries']['retention_end'] is not None
            assert finished['boundaries']['completion'] is not None
            for table, retained in before.items():
                assert engine.store.rows('SELECT * FROM '+table) == retained
        finally:
            await engine.broker.close()
    asyncio.run(scenario())


@pytest.mark.parametrize('jump', [3600, -3600], ids=['forward-wall', 'backward-wall'])
def test_s0_sleep_and_final_tail_preserve_both_clocks(rollout, monkeypatch, jump):
    engine, _, _ = mock_engine(rollout)
    one_timing_cycle(engine, monkeypatch, jump)
    async def scenario():
        try:
            await engine.activity_observation.run(engine)
            slept, = timing_events(engine.store, 'activity_observation_sleep_finished')
            assert slept['intended_seconds'] == 60 and slept['result'] == 'woke'
            assert slept['wait'] == {'monotonic_seconds': 60, 'wall_seconds': 60+jump}
            clocks = engine.activity_observation.summary()['clock_diagnostics']
            assert clocks['tail'] == {'monotonic_seconds': 60, 'wall_seconds': 60+jump}
            assert clocks['wall_elapsed_seconds'] == 60+jump
            assert clocks['end']['monotonic_seconds'] == 60
            events = engine.store.rows("SELECT seq,type FROM events WHERE type LIKE 'activity_%' ORDER BY seq")
            names = [e['type'] for e in events]
            assert names.index('activity_attempt_finished') < names.index('activity_observation_sleep_started')
            assert names.index('activity_observation_sleep_started') < names.index('activity_observation_sleep_finished')
        finally:
            await engine.broker.close()
    asyncio.run(scenario())


@pytest.mark.parametrize('mode,seconds,result,samples,p95', [
    pytest.param('interrupted', 7, 'interrupted', 0, None, id='cancelled-sleep'),
    pytest.param('late', 62, 'woke', 1, 2000, id='late-wake'),
])
def test_s0_sleep_interruption_and_late_wake_preserve_receipts_and_histogram(
        rollout, monkeypatch, mode, seconds, result, samples, p95):
    engine, _, _ = mock_engine(rollout)
    elapsed = one_timing_cycle(engine, monkeypatch)
    observation, normal_sleep = engine.activity_observation, asyncio.sleep
    entered, release = asyncio.Event(), asyncio.Event()
    async def sleep(delay):
        assert delay == 60
        if mode == 'interrupted':
            entered.set()
            await release.wait()
        else:
            await normal_sleep(delay)
            elapsed[0] += 2
    monkeypatch.setattr('backend.activity_observation.asyncio.sleep', sleep)
    async def scenario():
        task = asyncio.create_task(observation.run(engine))
        try:
            if mode == 'interrupted':
                await entered.wait()
                elapsed[0] += seconds
                task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await task
            else:
                await task
            started, = timing_events(engine.store, 'activity_observation_sleep_started')
            finished, = timing_events(engine.store, 'activity_observation_sleep_finished')
            assert started['intended_seconds'] == finished['intended_seconds'] == 60
            assert finished['result'] == result
            assert finished['wait']['monotonic_seconds'] == seconds
            assert observation.summary()['latency']['scheduling_delay'] == {
                'samples': samples, 'p95_upper_ms': p95, 'over_5000_ms': 0}
            assert not observation.storage_failed
            if mode == 'interrupted':
                assert engine.store.get('activity_rollout_observation')['reason'] == 'observation_interrupted'
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
            await engine.broker.close()
    asyncio.run(scenario())


def test_s0_full_window_records_final_short_sleep_without_extra_cycle(rollout, monkeypatch):
    engine, _, _ = mock_engine(rollout)
    observation, elapsed, delays = engine.activity_observation, [0], []
    observation.clock = lambda: elapsed[0]
    observation.wall_clock = lambda: (datetime.fromisoformat(NOW)+timedelta(seconds=elapsed[0])).isoformat()
    async def sleep(delay):
        delays.append(delay)
        elapsed[0] = DAY-10 if len(delays) == 1 else DAY
    monkeypatch.setattr('backend.activity_observation.asyncio.sleep', sleep)
    async def scenario():
        try:
            await observation.run(engine)
            assert delays == [60, 10]
            assert observation.cycles == observation.complete == 2
            assert observation.summary()['elapsed_seconds'] == DAY
            assert observation.summary()['clock_diagnostics']['tail']['monotonic_seconds'] == 10
            assert len(timing_events(engine.store, 'activity_observation_sleep_finished')) == 2
            assert not engine.activity_enabled
        finally:
            await engine.broker.close()
    asyncio.run(scenario())


@pytest.mark.parametrize('deadline', [False, True], ids=['cancelled', 'deadline'])
def test_s0_lock_wait_has_terminal_diagnostics_without_a_batch(rollout, monkeypatch, deadline):
    engine, calls, _ = mock_engine(rollout)
    original = engine.refresh_activity_feed
    entered = asyncio.Event()
    async def refresh():
        entered.set()
        return await original()
    monkeypatch.setattr(engine, 'refresh_activity_feed', refresh)
    if deadline:
        original_timeout = asyncio.timeout
        monkeypatch.setattr('backend.activity_observation.asyncio.timeout', lambda _: original_timeout(0))
    async def scenario():
        await engine.lock.acquire()
        task = asyncio.create_task(engine.activity_observation.run(engine))
        try:
            await entered.wait()
            if not deadline:
                task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await task
            else:
                await task
            finished, = timing_events(engine.store, 'activity_attempt_finished')
            assert finished['terminal'] == ('deadline' if deadline else 'cancelled')
            assert not finished['batch_started'] and not finished['outcome_retained']
            assert finished['boundaries']['lock_wait_start'] is not None
            assert finished['boundaries']['lock_acquired'] is None
            assert not engine.store.rows('SELECT id FROM activity_batches')
            assert engine.activity_observation.cycles == 1 and not calls
            assert not engine.activity_enabled
        finally:
            engine.lock.release()
            await engine.broker.close()
    asyncio.run(scenario())


@pytest.mark.parametrize('point', ['second-write', 'commit'])
def test_s0_snapshot_transaction_failure_retains_incomplete_attempt_with_normal_delay(
        rollout, monkeypatch, point):
    import sqlite3
    engine, _, _ = mock_engine(rollout)
    elapsed = one_timing_cycle(engine, monkeypatch)
    observation, store = engine.activity_observation, engine.store
    before = {key: store.get(key) for key in ('account_snapshot', 'snapshot_epoch')}
    if point == 'second-write':
        put = store.put
        def fail(key, value):
            if key == 'snapshot_epoch':
                raise OSError('controlled snapshot storage fault')
            return put(key, value)
        monkeypatch.setattr(store, 'put', fail)
    else:
        db = store.db
        class CommitFailure:
            fired = False
            def __getattr__(self, name):
                return getattr(db, name)
            def execute(self, sql, *args):
                if sql == 'COMMIT' and not self.fired:
                    self.fired = True
                    raise sqlite3.OperationalError('controlled snapshot commit fault')
                return db.execute(sql, *args)
        monkeypatch.setattr(store, 'db', CommitFailure())
    async def scenario():
        try:
            await observation.run(engine)
            assert not observation.storage_failed and observation.reason != 'diagnostic_storage_failed'
            assert {key: store.get(key) for key in before} == before
            outcome, = store.rows("SELECT payload FROM activity_batches WHERE phase='outcome'")
            receipt = json.loads(outcome['payload'])
            assert receipt['complete'] is False and receipt['snapshot_epoch'] is None
            finished, = timing_events(store, 'activity_attempt_finished')
            assert finished['outcome_retained'] is True and finished['acquisition_counted'] is False
            assert finished['publication'] == 'published' and finished['failure_kind'] == 'storage'
            slept, = timing_events(store, 'activity_observation_sleep_finished')
            assert slept['intended_seconds'] == 60 and slept['result'] == 'woke'
            assert elapsed[0] == 60
            assert not current_accounting(store, enabled=True, now=NOW)['accounting_by_symbol']['BTC']['passed']
        finally:
            await engine.broker.close()
    asyncio.run(scenario())


@pytest.mark.parametrize('point,cycles,outcomes,projections,complete', [
    pytest.param('activity_rollout_started', 0, 0, 0, 0, id='run-start'),
    pytest.param('startup-state', 0, 0, 0, 0, id='initial-persist'),
    pytest.param('activity_attempt_started', 1, 0, 0, 0, id='attempt-start'),
    pytest.param('batch-start', 1, 0, 0, 0, id='batch-start'),
    pytest.param('api_request', 1, 0, 0, 0, id='request-receipt'),
    pytest.param('last_api_call', 1, 0, 0, 0, id='request-state'),
    pytest.param('api_request_failed', 1, 0, 0, 0, id='transport-failure-receipt'),
    pytest.param('api_request_diagnostic', 1, 0, 0, 0, id='denial-receipt'),
    pytest.param('activity_request', 1, 0, 0, 0, id='stream-receipt'),
    pytest.param('retention', 1, 0, 0, 0, id='retention'),
    pytest.param('publication', 1, 1, 0, 1, id='publication'),
    pytest.param('activity_attempt_finished', 1, 1, 1, 1, id='attempt-finish'),
    pytest.param('activity_observation_sleep_started', 1, 1, 1, 1, id='sleep-start'),
    pytest.param('activity_observation_sleep_finished', 1, 1, 1, 1, id='sleep-finish'),
    pytest.param('stop-state', 1, 1, 1, 1, id='final-persist'),
    pytest.param('activity_rollout_stopped', 1, 1, 1, 1, id='run-finish'),
])
def test_s0_storage_failure_disables_in_memory_and_never_salvages_or_retries(
        rollout, monkeypatch, point, cycles, outcomes, projections, complete):
    import sqlite3
    import backend.activity_feed as feed
    import backend.activity_observation as observer
    engine, _, _ = mock_engine(rollout)
    one_timing_cycle(engine, monkeypatch)
    observation, attempts = engine.activity_observation, []
    event, put, db = engine.store.event, engine.store.put, engine.store.db
    failed = [False]
    def record(name):
        assert not failed[0], 'A write followed the storage failure'
        attempts.append(name)
        if name == point:
            failed[0] = True
            raise sqlite3.OperationalError('sensitive-storage-detail')
    def guarded_event(kind, payload):
        record(kind)
        return event(kind, payload)
    def guarded_put(key, value):
        label = key if key != 'activity_rollout_observation' else (
            'startup-state' if observation.cycles == 0 else
            'stop-state' if observation.status == 'stopped' else 'state')
        record(label)
        return put(key, value)
    class DB:
        def __getattr__(self, name):
            return getattr(db, name)
        def execute(self, sql, args=()):
            if sql.startswith('INSERT INTO activity_batches') and args[1] == 'start':
                record('batch-start')
            return db.execute(sql, args)
    monkeypatch.setattr(engine.store, 'event', guarded_event)
    monkeypatch.setattr(engine.store, 'put', guarded_put)
    monkeypatch.setattr(engine.store, 'db', DB())
    if point == 'api_request_failed':
        def unavailable(request):raise httpx.ReadTimeout('sensitive-network-detail')
        engine.broker.http._transport = httpx.MockTransport(unavailable)
    if point == 'api_request_diagnostic':engine.broker.trading.normal = 0
    if point == 'retention':
        def retain(*args):record('retention')
        monkeypatch.setattr(feed, 'retain_batch', retain)
    if point == 'publication':
        def publish(*args):record('publication')
        monkeypatch.setattr(observer, 'publish_projection', publish)
    async def scenario():
        try:
            await observation.run(engine)
            assert failed[0] and attempts[-1] == point and attempts.count(point) == 1
            assert observation.storage_failed and not engine.activity_enabled
            assert observation.reason == 'diagnostic_storage_failed'
            assert observation.cycles == cycles and observation.complete == complete
            assert len(engine.store.rows("SELECT id FROM activity_batches WHERE phase='outcome'")) == outcomes
            assert len(engine.store.rows('SELECT id FROM activity_projections')) == projections
            assert observation.latest_diagnostics['failure_kind'] == 'storage'
            assert 'sensitive-storage-detail' not in json.dumps(observation.latest_diagnostics)
            if point in {'api_request', 'activity_request', 'retention'}:
                pending = current_accounting(engine.store, enabled=True, now=NOW)
                assert pending['accounting_evidence']['latest_attempt']['status'] == 'pending'
        finally:
            await engine.broker.close()
    asyncio.run(scenario())


def test_s0_pre_batch_rejection_has_finish_but_no_invented_accounting_outcome(rollout, monkeypatch):
    from backend.activity_feed import FeedError
    engine, calls, _ = mock_engine(rollout)
    one_timing_cycle(engine, monkeypatch)
    async def reject(*args, **kwargs):
        raise FeedError('sensitive-preflight-detail')
    monkeypatch.setattr('backend.activity_observation.collect_batch', reject)
    async def scenario():
        try:
            await engine.activity_observation.run(engine)
            finished, = timing_events(engine.store, 'activity_attempt_finished')
            assert finished['failure_kind'] == 'FeedError' and finished['terminal'] == 'failed'
            assert not finished['batch_started'] and not finished['outcome_retained']
            assert not engine.store.rows('SELECT id FROM activity_batches') and not calls
            assert 'sensitive-preflight-detail' not in json.dumps(finished)
        finally:
            await engine.broker.close()
    asyncio.run(scenario())


@pytest.mark.parametrize('broken_trace', [False, True], ids=['observed-phases', 'instrumentation-failure'])
def test_s0_httpcore_trace_records_observed_phases_and_reuse(rollout, monkeypatch, broken_trace):
    from httpcore import AsyncMockBackend
    from backend.activity_diagnostics import PHASES
    if broken_trace:
        from backend.activity_diagnostics import trace_extensions
        def extensions(receipt, previous=None):
            def broken_sample():raise RuntimeError('sensitive-trace-detail')
            receipt['_sample'] = broken_sample
            return trace_extensions(receipt, previous)
        monkeypatch.setattr('backend.activity_diagnostics.trace_extensions', extensions)
        monkeypatch.setattr('backend.activity_feed.trace_extensions', extensions)
    engine, _, _ = mock_engine(rollout)
    snapshot = engine.store.get('account_snapshot')
    raw = (FIXTURE/'activity-sse.raw').read_bytes()
    bodies = [json.dumps(snapshot['account']).encode(), json.dumps(snapshot['positions']).encode(),
              json.dumps(snapshot['clock']).encode(), json.dumps(snapshot['account']).encode(), raw,
              json.dumps(snapshot['account']).encode(), json.dumps(snapshot['positions']).encode()]
    responses = [b'HTTP/1.1 200 OK\r\nContent-Length: '+str(len(body)).encode()+
                 (b'\r\nContent-Type: text/event-stream' if index == 4 else b'\r\nContent-Type: application/json')+
                 b'\r\n\r\n'+body for index, body in enumerate(bodies)]
    transport = httpx.AsyncHTTPTransport()
    transport._pool._network_backend = AsyncMockBackend(responses)
    async def scenario():
        await engine.broker.http.aclose()
        engine.broker.http = httpx.AsyncClient(transport=transport, trust_env=False)
        try:
            await engine.refresh_activity_feed()
            requests = engine.broker._last_activity_acquisition['diagnostics']['requests']
            assert len(requests) == 7
            if broken_trace:
                assert all(request['tracing_unavailable'] for request in requests)
                assert 'sensitive-trace-detail' not in json.dumps(requests)
                assert engine.activity_observation.complete == 1
                return
            assert all(phase['state'] == 'complete' for phase in requests[0]['phases'].values())
            assert [requests[0]['phases'][name]['started']['monotonic_seconds'] for name in PHASES] == sorted(
                requests[0]['phases'][name]['started']['monotonic_seconds'] for name in PHASES)
            for request in requests[1:]:
                assert request['phases']['connection.connect_tcp']['state'] == 'not-observed'
                assert request['phases']['connection.start_tls']['started'] is None
                assert request['phases']['http11.receive_response_body']['state'] == 'complete'
                assert request['phases']['http11.response_closed']['state'] == 'complete'
            assert requests[4]['path'] == '/v2beta1/events/activities'
        finally:
            await engine.broker.close()
    asyncio.run(scenario())


def test_s0_corrupt_reference_remains_integrity_denial_with_normal_delay(rollout, monkeypatch):
    engine, _, _ = mock_engine(rollout)
    elapsed = one_timing_cycle(engine, monkeypatch)
    def invalid(*args):raise ValueError('sensitive-corrupt-reference')
    monkeypatch.setattr('backend.activity_feed.reference_bytes', invalid)
    async def scenario():
        try:
            await engine.activity_observation.run(engine)
            finished, = timing_events(engine.store, 'activity_attempt_finished')
            assert finished['outcome_retained'] and finished['publication'] == 'published'
            assert not finished['acquisition_counted'] and not engine.activity_observation.storage_failed
            assert elapsed[0] == 60
            assert current_accounting(engine.store, enabled=True, now=NOW)['activity_coverage']['status'] == 'incomplete'
            assert 'sensitive-corrupt-reference' not in json.dumps(finished)
        finally:
            await engine.broker.close()
    asyncio.run(scenario())


@pytest.mark.parametrize('point', ['retention', 'attempt-finish', 'sleep-finish'])
def test_s0_cancellation_survives_storage_failure_in_cleanup(rollout, monkeypatch, point):
    engine, _, _ = mock_engine(rollout)
    entered = asyncio.Event()
    async def gated(*args, **kwargs):
        entered.set()
        await asyncio.Event().wait()
    event = engine.store.event
    failures = []
    def guarded(kind, payload):
        if kind == {'attempt-finish': 'activity_attempt_finished', 'sleep-finish': 'activity_observation_sleep_finished'}.get(point):
            failures.append(kind)
            raise OSError('sensitive-cleanup-detail')
        return event(kind, payload)
    monkeypatch.setattr(engine.store, 'event', guarded)
    if point == 'retention':
        monkeypatch.setattr(engine.broker, 'stream_activities', gated)
        def fail(*args):
            failures.append('retention')
            raise OSError('sensitive-cleanup-detail')
        monkeypatch.setattr('backend.activity_feed.retain_batch', fail)
    elif point == 'sleep-finish':
        monkeypatch.setattr('backend.activity_observation.asyncio.sleep', gated)
    else:
        original = engine.refresh_activity_feed
        async def refresh():
            entered.set()
            return await original()
        monkeypatch.setattr(engine, 'refresh_activity_feed', refresh)
    async def scenario():
        if point == 'attempt-finish':await engine.lock.acquire()
        task = asyncio.create_task(engine.activity_observation.run(engine))
        try:
            await entered.wait()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):await task
            assert len(failures) == 1 and engine.activity_observation.storage_failed
            assert not engine.activity_enabled
            assert engine.activity_observation.latest_diagnostics['failure_kind'] == 'storage'
            assert 'sensitive-cleanup-detail' not in json.dumps(engine.activity_observation.latest_diagnostics)
        finally:
            if point == 'attempt-finish':engine.lock.release()
            await engine.broker.close()
    asyncio.run(scenario())


def crash_timing_worker(ledger, mapping_path, sha, point, pipe):
    """Test-only child: acknowledge a committed boundary, then wait for SIGKILL."""
    import backend.activity_feed as feed
    import backend.activity_observation as observer
    import backend.broker as broker_module
    settings = Settings(db_path=Path(ledger), api_key='fixture', secret_key='fixture')
    store = Store(settings.db_path, 'alpaca')
    mapping = json.loads(Path(mapping_path).read_text())
    spec = prepare(settings, Path(mapping_path), sha, mapping['account_id'])
    inputs = (settings, store, Path(mapping_path), sha, mapping)
    feed.utcnow = broker_module.utcnow = lambda: NOW
    import backend.activity_rollout as rollout_module
    rollout_module.source_identity = lambda: {'revision': '1'*40, 'files': {}}
    engine, _, _ = mock_engine(inputs, spec=spec)
    def gate():
        pipe.send('committed')
        import threading
        threading.Event().wait()
    if point == 'attempt-start':
        event = store.event
        def marked(kind, payload):
            result = event(kind, payload)
            if kind == 'activity_attempt_started':gate()
            return result
        store.event = marked
    else:
        module, name = {'batch-start': (feed, 'start_batch'), 'outcome': (feed, 'retain_batch'),
                        'publication': (observer, 'publish_projection')}[point]
        operation = getattr(module, name)
        def marked(*args, **kwargs):
            result = operation(*args, **kwargs)
            gate()
            return result
        setattr(module, name, marked)
    asyncio.run(engine.activity_observation.run(engine))


@pytest.mark.parametrize('point,status', [
    ('attempt-start', None), ('batch-start', 'pending'), ('outcome', 'unpublished'), ('publication', 'complete')])
def test_s0_sigkill_leaves_original_crash_evidence_and_annotation_cannot_grant_authority(rollout, point, status):
    import multiprocessing
    import signal
    settings, original_store, path, sha, mapping = rollout
    before = {table: original_store.rows('SELECT * FROM '+table)
              for table in ('orders', 'fills', 'activities', 'observations', 'equity', 'shadow')}
    context = multiprocessing.get_context('spawn')
    parent, child = context.Pipe(duplex=False)
    process = context.Process(target=crash_timing_worker, args=(str(settings.db_path), str(path), sha, point, child))
    process.start()
    child.close()
    try:
        # Bound process readiness and cleanup; no timing assertion on application work.
        assert parent.poll(10), 'Crash fixture did not reach its committed gate'
        assert parent.recv() == 'committed'
        process.kill()
        process.join(10)
        assert process.exitcode == -signal.SIGKILL
        reopened = Store(settings.db_path, 'alpaca')
        try:
            fresh = Observation(prepare(settings, path, sha, mapping['account_id']))
            evidence_before = current_accounting(reopened, enabled=True, now=NOW)
            latest = evidence_before['accounting_evidence']['latest_attempt']
            assert (latest['status'] if latest else None) == status
            outcomes = reopened.rows("SELECT id,payload FROM activity_batches WHERE phase='outcome'")
            fresh.recover(reopened)
            fresh.recover(reopened)
            assert len(timing_events(reopened, 'activity_attempt_abandoned')) == 1
            assert not timing_events(reopened, 'activity_attempt_finished')
            assert reopened.rows("SELECT id,payload FROM activity_batches WHERE phase='outcome'") == outcomes
            assert current_accounting(reopened, enabled=True, now=NOW) == evidence_before
            assert not fresh.active
            assert evidence_before['accounting_by_symbol']['BTC']['passed'] == (point == 'publication')
            for table, retained in before.items():assert reopened.rows('SELECT * FROM '+table) == retained
        finally:
            reopened.close()
    finally:
        if process.is_alive():process.kill()
        process.join(10)
        parent.close()
        process.close()


@pytest.mark.parametrize('invalid', [True, '1', [], 0, 'x'*1000], ids=['boolean', 'string', 'array', 'zero', 'oversized'])
def test_s0_recovery_rejects_malformed_diagnostic_identity_without_repair(rollout, invalid):
    engine, calls, _ = mock_engine(rollout)
    record = {'run_id': '1'*32, 'process_id': 1, 'sequence': invalid, 'attempt_id': '2'*32}
    engine.store.event('activity_attempt_started', record)
    rows = engine.store.rows("SELECT seq,payload FROM events WHERE type='activity_attempt_started'")
    async def scenario():
        try:
            await engine.activity_observation.run(engine)
            assert not calls and not engine.activity_enabled
            assert engine.activity_observation.reason == 'diagnostic_evidence_invalid'
            assert timing_events(engine.store, 'activity_rollout_failed') == [
                {'run_id': engine.activity_observation.run_id, 'reason': 'diagnostic_evidence_invalid'}]
            assert not timing_events(engine.store, 'activity_attempt_abandoned')
            assert not timing_events(engine.store, 'activity_rollout_started')
            assert engine.store.rows("SELECT seq,payload FROM events WHERE type='activity_attempt_started'") == rows
        finally:
            await engine.broker.close()
    asyncio.run(scenario())


def test_s0_httpcore_failure_phase_retains_no_exception_or_callback_payload(rollout):
    import httpcore
    engine, _, _ = mock_engine(rollout)
    class Backend(httpcore.AsyncMockBackend):
        async def connect_tcp(self, *args, **kwargs):
            raise httpcore.ConnectError('sensitive-httpcore-detail')
    transport = httpx.AsyncHTTPTransport()
    transport._pool._network_backend = Backend([])
    async def scenario():
        await engine.broker.http.aclose()
        engine.broker.http = httpx.AsyncClient(transport=transport, trust_env=False)
        try:
            result = await engine.refresh_activity_feed()
            assert result['issues'] and engine.activity_observation.complete == 0
            trace = engine.broker._last_activity_acquisition['diagnostics']
            request, = trace['requests']
            assert trace['failure_kind'] == 'ConnectError'
            assert request['phases']['connection.connect_tcp']['state'] == 'failed'
            assert request['phases']['connection.start_tls']['state'] == 'not-observed'
            assert request['http_status'] is None
            assert 'sensitive-httpcore-detail' not in json.dumps(trace)
        finally:
            await engine.broker.close()
    asyncio.run(scenario())


def test_replaced_prepared_ledger_denies_activation_without_writes(rollout):
    """A same-account replacement at the prepared pathname is another ledger."""
    import sqlite3
    settings, store, *_ = rollout
    spec = prepared(rollout)
    replacement = settings.db_path.with_name('replacement.sqlite')
    with closing(sqlite3.connect(replacement)) as db:store.db.backup(db)
    store.close()
    original = settings.db_path.with_name('original.sqlite')
    settings.db_path.rename(original)
    replacement.rename(settings.db_path)
    before = {p:p.read_bytes() for p in (original,settings.db_path)}
    with pytest.raises(ValueError,match='Prepared ledger was replaced'):
        activated_settings(settings,spec)
    assert {p:p.read_bytes() for p in before} == before


@pytest.mark.parametrize('strategy',['swing','intraday'])
def test_paper_strategy_denial_precedes_intent_and_dispatch(rollout,strategy):
    from backend.engine import RuleViolation
    engine,calls,_ = mock_engine(rollout)
    async def scenario():
        try:
            assert not (await engine.refresh_activity_feed())['issues']
            assert not engine.settings.enable_orders
            with unchanged_inspection(engine,calls):
                with pytest.raises(RuleViolation,match='Strategy execution is shadow-only'):
                    await engine.place({'client_order_id':'astral-rehearsal-'+strategy,'symbol':'BTC',
                        'side':'buy','notional':25,'execution':'bounded','ttl_seconds':60,'strategy_id':strategy})
        finally:await engine.broker.close()
    asyncio.run(scenario())


_ACQUISITION_EDGES = [
    pytest.param(mode,index,path,occurrence,stage,id=mode+'-'+name)
    for mode,indices in [('body',range(1,7)),('status',[1,2,3,5,6]),('cancel',[1,2,3,5,6])]
    for index,name,path,occurrence,stage in [
        (1,'snapshot-positions','/v2/positions',1,'initial-snapshot'),
        (2,'snapshot-clock','/v2/clock',1,'initial-snapshot'),
        (3,'identity-before','/v2/account',2,'identity-before'),
        (4,'stream','/v2beta1/events/activities',1,'activity-stream'),
        (5,'identity-after','/v2/account',3,'identity-after'),
        (6,'positions-after','/v2/positions',2,'positions-after')]
    if index in indices
]


@pytest.mark.parametrize('mode,index,path,occurrence,stage',_ACQUISITION_EDGES)
def test_acquisition_stage_edges_retain_evidence_and_deny_authority(rollout,mode,index,path,occurrence,stage):
    """Header/body/status/cancellation edges must not hide earlier complete streams."""
    from collections import Counter
    engine,calls,_ = mock_engine(rollout)
    transport = engine.broker.http._transport
    original = transport.handler
    counts = Counter()
    async def scenario():
        entered = asyncio.Event()
        class Interrupted(httpx.AsyncByteStream):
            closed = False
            async def __aiter__(self):
                yield b': heartbeat\n\n' if index == 4 else b'{'
                if mode == 'cancel':
                    entered.set();await asyncio.Event().wait()
                raise httpx.ReadTimeout('private-body-canary')
            async def aclose(self):self.closed = True
        body = Interrupted()
        try:
            assert not (await engine.refresh_activity_feed())['issues']
            before = {t:engine.store.rows('SELECT * FROM '+t) for t in ('orders','fills','activities','observations')}
            calls.clear()
            def inject(request):
                counts[request.url.path] += 1
                if request.url.path == path and counts[path] == occurrence:
                    calls.append((request.method,path))
                    return httpx.Response(503,json={}) if mode == 'status' else httpx.Response(
                        200,headers={'content-type':'text/event-stream'} if index == 4 else {},stream=body)
                return original(request)
            transport.handler = inject
            task = asyncio.create_task(engine.refresh_activity_feed())
            if mode == 'cancel':
                await entered.wait();task.cancel()
                with pytest.raises(asyncio.CancelledError):await task
            else:
                result = await task
                assert 'incomplete_activity_coverage' in result['issues']
                assert not {'activity_disappeared_from_replay','unreconciled_cash'} & set(result['issues'])
            receipt = engine.broker._last_activity_acquisition
            assert not receipt['complete']
            diagnostics = receipt['diagnostics']
            expected = {'body':'ReadTimeout','status':'BrokerFailure','cancel':'CancelledError'}[mode]
            assert diagnostics['failure_stage'] == stage and diagnostics['failure_kind'] == expected
            failed = next(r for r in diagnostics['requests'] if r['failure_kind'])
            assert failed['path'] == path and failed['dispatch'] == 'response-received'
            assert failed['http_status'] == (503 if mode == 'status' else 200)
            assert failed['failure_locus'] == {'body':'transport-after-headers','status':'observed-provider-status',
                                                'cancel':'deadline/cancellation'}[mode]
            assert len(diagnostics['requests']) == len(calls) <= 7
            assert all(method == 'GET' for method,_ in calls)
            if mode != 'status':assert body.closed
            if index > 4:
                assert receipt['raw'] == (FIXTURE/'activity-sse.raw').read_bytes()
                assert len(receipt['events']) == 19
            retained = json.loads(engine.store.rows("SELECT payload FROM activity_batches WHERE phase='outcome' ORDER BY rowid DESC LIMIT 1")[0]['payload'])
            assert retained['diagnostics'] == diagnostics
            assert bytes.fromhex(retained['raw_hex']) == receipt['raw']
            assert 'private-body-canary' not in json.dumps(retained)
            view = current_accounting(engine.store,enabled=True,now=NOW)
            assert not view['accounting_by_symbol']['BTC']['passed']
            assert view['cash_reconciliation']['cash'] is None
            assert view['accounting_evidence']['historical_checkpoint']['current_authority'] is False
            assert all(engine.store.rows('SELECT * FROM '+t) == rows for t,rows in before.items())
        finally:await engine.broker.close()
    asyncio.run(scenario())


# These cases fill the startup authorization gap; existing accounting tests keep
# their own fixture approvals and continue to prove the unchanged producer rules.
@pytest.mark.parametrize('attack', ['missing-operator', 'future', 'late', 'account', 'ledger',
                                   'mapping', 'source', 'controls', 'short-window', 'duration', 'policy-digest'])
def test_approval_binding_denies_before_reader_settings_and_leaves_ledger_unchanged(rollout, attack):
    settings, store, path, sha, mapping = rollout
    spec = prepare(settings, path, sha, mapping['account_id'])
    before = source_bytes(settings)
    def change(record):
        proposal = record['proposal']
        if attack == 'missing-operator':record['approved_by'] = ''
        elif attack == 'future':record['approved_at'] = '2031-01-01T00:00:00+00:00'
        elif attack == 'late':record['approved_at'] = NOW
        elif attack == 'account':proposal['account_id'] = 'different account'
        elif attack == 'ledger':proposal['ledger_identity'][1] += 1
        elif attack == 'mapping':proposal['mapping_sha256'] = '0'*64
        elif attack == 'source':proposal['source']['revision'] = '0'*40
        elif attack == 'controls':proposal['controls']['enable_news'] = True
        elif attack == 'short-window':proposal['start_before'] = '2029-01-01T00:00:00+00:00'
        elif attack == 'policy-digest':proposal['policy_sha256'] = None
        else:proposal['duration_seconds'] = 1
    with pytest.raises(ValueError):approved_fixture(settings, spec, change=change)
    assert source_bytes(settings) == before
    assert not settings.enable_activity_feed


@pytest.mark.parametrize('run_id', ['', 'A'*32, 'x'*32, 'a'*31, True])
def test_invalid_run_identity_cannot_be_proposed(rollout, run_id):
    from backend.activity_rollout import propose
    settings, _, path, sha, mapping = rollout
    policy = settings.db_path.parent/'policy.json';policy.write_text(json.dumps(approval_policy()))
    with pytest.raises(ValueError):
        propose(settings, prepare(settings, path, sha, mapping['account_id']), policy,
                '2029-01-01T00:00:00+00:00', '2031-01-01T00:00:00+00:00', run_id=run_id)


@pytest.mark.parametrize('storage,payload', [
    ('event', lambda identity: {'run_id': identity}),
    ('event', lambda identity: {'clock_diagnostics': {'run_id': identity}}),
    ('event', lambda identity: {'recovered_by': identity}),
    pytest.param('state', lambda identity: {'clock_diagnostics': {'run_id': identity}}, id='persisted-summary')])
def test_new_approval_cannot_reuse_a_recorded_run_identity(rollout, storage, payload):
    settings, store, path, sha, mapping = rollout
    identity = 'e'*32
    if storage == 'state':store.put('activity_rollout_observation', payload(identity))
    else:store.event('activity_rollout_previous', payload(identity))
    before = source_bytes(settings)
    with pytest.raises(ValueError):
        approved_fixture(settings, prepare(settings, path, sha, mapping['account_id']), run_id=identity)
    assert source_bytes(settings) == before


def test_unreadable_identity_evidence_blocks_proposal_without_repair(rollout):
    settings, store, path, sha, mapping = rollout
    store.db.execute("INSERT INTO events(at,type,payload) VALUES(?,?,?)", (NOW, 'activity_attempt_started', '{'))
    before = source_bytes(settings)
    with pytest.raises(ValueError):approved_fixture(settings, prepare(settings, path, sha, mapping['account_id']))
    assert source_bytes(settings) == before


@pytest.mark.parametrize('drift', ['approval', 'policy', 'history'])
def test_locked_recheck_denies_changed_evidence_before_store_construction(rollout, monkeypatch, drift):
    from backend import app as module
    from backend.activity_rollout import authorize
    settings, store, *_ = rollout
    spec = prepared(rollout)
    cfg = activated_settings(settings, spec)
    if drift == 'approval':spec.approval_path.write_text(spec.approval_path.read_text()+' ')
    elif drift == 'policy':spec.policy_path.write_text(spec.policy_path.read_text()+' ')
    else:store.event('activity_attempt_finished', {'run_id': spec.run_id})
    before = source_bytes(settings)
    constructed = []
    monkeypatch.setattr(module, 'Store', lambda *_: constructed.append('Store'))
    monkeypatch.setattr(module, 'Engine', lambda *_: constructed.append('Engine'))
    observation = Observation(spec);observation.run_id = spec.run_id
    app = module.create_app(cfg, activity_observation=observation)
    async def scenario():
        with pytest.raises(ValueError):
            async with app.router.lifespan_context(app):pass
    asyncio.run(scenario())
    assert constructed == []
    assert source_bytes(settings) == before


def test_cli_binds_approved_identity_and_explicit_controls_without_starting_services(rollout, monkeypatch):
    from backend import activity_rollout as module
    settings, _, path, sha, mapping = rollout
    spec = prepared(rollout)
    captured = []
    observed = []
    app_token = object()
    def app_factory(cfg, *, activity_observation):
        observed.append((cfg, activity_observation.run_id))
        return app_token
    monkeypatch.setattr('backend.app.create_app', app_factory)
    monkeypatch.setenv('ASTRAL_ENABLE_RESEARCH', 'false');monkeypatch.setenv('ASTRAL_ENABLE_NEWS', 'false')
    monkeypatch.setattr(Settings, 'from_env', lambda: settings)
    monkeypatch.setattr('uvicorn.run', lambda app, **kwargs: captured.append(app))
    monkeypatch.setattr('sys.argv', ['rollout', '--ledger', str(settings.db_path), '--mapping-file', str(path),
        '--mapping-sha256', sha, '--account-id', mapping['account_id'], '--activate',
        '--approval-file', str(spec.approval_path), '--approval-sha256', spec.approval_sha256,
        '--policy-file', str(spec.policy_path)])
    original = module.activated_settings
    bound = []
    def inspected(cfg, prepared):
        bound.append(prepared.run_id)
        return original(cfg, prepared)
    monkeypatch.setattr(module, 'activated_settings', inspected)
    module.main()
    assert captured == [app_token] and bound == [spec.run_id]
    assert observed[0][1] == spec.run_id and observed[0][0].enable_activity_feed
    assert not observed[0][0].enable_orders


def test_environment_controls_override_dotenv_and_policy_mismatch_denies(rollout, monkeypatch, tmp_path):
    from backend import config, activity_rollout as module
    settings, _, path, sha, mapping = rollout
    (tmp_path/'.env').write_text('ASTRAL_ENABLE_RESEARCH=true\nASTRAL_ENABLE_NEWS=true\n')
    monkeypatch.setattr(config, 'ROOT', tmp_path)
    monkeypatch.setenv('ASTRAL_ENABLE_RESEARCH', 'false');monkeypatch.setenv('ASTRAL_ENABLE_NEWS', 'false')
    monkeypatch.setenv('ALPACA_PAPER_API_KEY', 'fixture');monkeypatch.setenv('ALPACA_PAPER_SECRET_KEY', 'fixture')
    actual = Settings.from_env()
    assert not actual.enable_research and not actual.enable_news
    spec = prepare(settings, path, sha, mapping['account_id'])
    with pytest.raises(ValueError):approved_fixture(replace(settings, enable_news=True), spec)


@pytest.mark.parametrize('key,value', [('tau_seconds', None), ('tau_seconds', 'NaN'),
                                     ('tau_c_seconds', '-1'), ('precision_seconds', '0'),
                                     ('e4_policy', None), ('research_enabled', 1)])
def test_unset_or_invalid_policy_cannot_authorize_a_run(rollout, key, value):
    from backend.activity_rollout import propose
    settings, _, path, sha, mapping = rollout
    policy = approval_policy();policy[key] = value
    policy_path = settings.db_path.parent/'bad-policy.json';policy_path.write_text(json.dumps(policy))
    with pytest.raises(ValueError):propose(settings, prepare(settings,path,sha,mapping['account_id']), policy_path,
        '2029-01-01T00:00:00+00:00', '2031-01-01T00:00:00+00:00')


@pytest.mark.parametrize('change', ['content', 'mode', 'symlink'])
def test_source_bytes_modes_and_symlink_targets_are_rechecked_before_activation(rollout, monkeypatch, tmp_path, change):
    from backend import activity_rollout as module
    root = tmp_path/'source';root.mkdir()
    code = root/'module.py';code.write_text('value = 1\n')
    (root/'other.py').write_text('value = 2\n')
    (root/'alias.py').symlink_to('module.py')
    for args in (['git','init','--quiet'],['git','add','.'],
                 ['git','-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','--quiet','-m','fixture']):
        subprocess.run(args,cwd=root,check=True,capture_output=True)
    monkeypatch.setattr(module, 'ROOT', root)
    monkeypatch.setattr(module, 'source_identity', real_source_identity)
    spec = prepared(rollout)
    if change == 'content':code.write_text('value = 3\n')
    elif change == 'mode':code.chmod(0o755)
    else:(root/'alias.py').unlink();(root/'alias.py').symlink_to('other.py')
    before = source_bytes(rollout[0])
    with pytest.raises(ValueError):activated_settings(rollout[0], spec)
    assert source_bytes(rollout[0]) == before


def test_cli_missing_approval_denies_before_settings_or_application_startup(rollout, monkeypatch):
    from backend.activity_rollout import main
    settings, _, path, sha, mapping = rollout
    monkeypatch.setenv('ASTRAL_ENABLE_RESEARCH', 'false');monkeypatch.setenv('ASTRAL_ENABLE_NEWS', 'false')
    def unexpected():raise AssertionError('Settings loaded before approval argument checks')
    monkeypatch.setattr(Settings, 'from_env', unexpected)
    monkeypatch.setattr('sys.argv', ['rollout','--ledger',str(settings.db_path),'--mapping-file',str(path),
        '--mapping-sha256',sha,'--account-id',mapping['account_id'],'--activate'])
    before = source_bytes(settings)
    with pytest.raises(SystemExit) as error:main()
    assert error.value.code == 1 and source_bytes(settings) == before


@pytest.mark.parametrize('payload', [{}, {'run_id': True}, {'clock_diagnostics': {'run_id': 'wrong'}}])
def test_valid_json_with_unreadable_identity_denies_a_new_run(rollout, payload):
    settings, store, path, sha, mapping = rollout
    store.event('activity_rollout_previous', payload)
    before = source_bytes(settings)
    with pytest.raises(ValueError):approved_fixture(settings, prepare(settings,path,sha,mapping['account_id']))
    assert source_bytes(settings) == before


def test_cli_proposal_is_private_unapproved_and_preserves_ledger(rollout, monkeypatch, capsys):
    from backend import activity_rollout as module
    settings, _, path, sha, mapping = rollout
    policy = settings.db_path.parent/'policy.json';policy.write_text(json.dumps(approval_policy()))
    output = settings.db_path.parent/'proposal.json'
    before = source_bytes(settings)
    monkeypatch.setenv('ASTRAL_ENABLE_RESEARCH', 'false');monkeypatch.setenv('ASTRAL_ENABLE_NEWS', 'false')
    monkeypatch.setattr(Settings, 'from_env', lambda: settings)
    monkeypatch.setattr('sys.argv', ['rollout','--ledger',str(settings.db_path),'--mapping-file',str(path),
        '--mapping-sha256',sha,'--account-id',mapping['account_id'],'--policy-file',str(policy),
        '--proposal-output',str(output),'--start-not-before','2029-01-01T00:00:00+00:00',
        '--start-before','2031-01-01T00:00:00+00:00'])
    module.main()
    record = json.loads(output.read_text());receipt = json.loads(capsys.readouterr().out)
    assert record['approved_by'] is None and record['approved_at'] is None
    assert output.stat().st_mode & 0o777 == 0o600
    assert receipt['reader_activated'] is False and receipt['approval'] == 'pending'
    assert mapping['account_id'] not in json.dumps(receipt)
    assert source_bytes(settings) == before
    with pytest.raises(ValueError):module.authorize(settings, prepare(settings,path,sha,mapping['account_id']),
        output, hashlib.sha256(output.read_bytes()).hexdigest(), policy)


@pytest.mark.parametrize('attack', ['missing-digest', 'wrong-digest', 'duplicate-field', 'oversized'])
def test_untrusted_approval_bytes_cannot_authorize(rollout, attack):
    from backend import activity_rollout as module
    settings, *_ = rollout;spec = prepared(rollout)
    digest = spec.approval_sha256
    if attack == 'missing-digest':digest = None
    elif attack == 'wrong-digest':digest = '0'*64
    elif attack == 'duplicate-field':
        raw = spec.approval_path.read_text();spec.approval_path.write_text('{"schema_version":1,'+raw[1:])
        digest = hashlib.sha256(spec.approval_path.read_bytes()).hexdigest()
    else:
        spec.approval_path.write_bytes(b' '* (module.DOCUMENT_BYTES+1))
        digest = hashlib.sha256(spec.approval_path.read_bytes()).hexdigest()
    before = source_bytes(settings)
    with pytest.raises(ValueError):module.authorize(settings,spec,spec.approval_path,digest,spec.policy_path)
    assert source_bytes(settings) == before


def test_research_requires_existing_registration_and_rechecks_it_without_writes(rollout):
    from backend.experiment import contract
    settings, store, path, sha, mapping = rollout
    settings = replace(settings, enable_research=True)
    raw = prepare(settings,path,sha,mapping['account_id'])
    with pytest.raises(ValueError):approved_fixture(settings,raw,policy_overrides={'research_enabled':True})
    manifest = contract()
    registration = {'id':manifest['id'],'manifest_sha256':manifest['manifest_sha256'],'registered_at':NOW}
    store.put('frozen_experiment', registration)
    before = source_bytes(settings)
    spec = approved_fixture(settings,raw,policy_overrides={'research_enabled':True})
    assert activated_settings(settings,spec).enable_research and source_bytes(settings) == before
    store.put('frozen_experiment', {**registration,'manifest_sha256':'0'*64})
    before = source_bytes(settings)
    with pytest.raises(ValueError):activated_settings(settings,spec)
    assert source_bytes(settings) == before


def test_legacy_state_archives_unchanged_and_allows_fresh_observations_only(rollout, monkeypatch):
    """An old saved summary must not make the documented approved restart unusable."""
    settings, store, path, sha, mapping = rollout
    store.put('activity_rollout_observation', legacy_summary_fixture())
    seeded = store.rows("SELECT value FROM state WHERE key='activity_rollout_observation'")[0]['value']
    for run_id in ('e'*32, 'f'*32):
        before = source_bytes(settings)
        spec = approved_fixture(settings, prepare(settings, path, sha, mapping['account_id']), run_id=run_id)
        cfg = activated_settings(settings, spec)
        assert cfg.enable_activity_feed and not cfg.enable_orders
        assert source_bytes(settings) == before
        engine, _, _ = mock_engine(rollout, spec)
        with monkeypatch.context() as patch:
            one_timing_cycle(engine, patch)
            async def scenario():
                try:
                    await engine.activity_observation.run(engine)
                    assert engine.activity_observation.cycles == engine.activity_observation.complete == 1
                    assert engine.activity_observation.status == 'stopped'
                finally:
                    await engine.broker.close()
            asyncio.run(scenario())
        archived = store.rows("SELECT payload FROM events WHERE type='activity_rollout_previous' ORDER BY seq")
        assert archived[0]['payload'].encode() == seeded.encode()
    before = source_bytes(settings)
    for run_id in ('e'*32, 'f'*32):
        with pytest.raises(ValueError):
            approved_fixture(settings, prepare(settings, path, sha, mapping['account_id']), run_id=run_id)
        assert source_bytes(settings) == before


@pytest.mark.parametrize('status', ['prepared', 'observing', 'expired', 'stopped', 'failed'])
def test_existing_legacy_archive_and_lifecycle_allow_fresh_approval_without_writes(rollout, status):
    """Already archived and interrupted base runs must not strand fresh approvals."""
    settings, store, path, sha, mapping = rollout
    summary = legacy_summary_fixture(status)
    seed_legacy_lifecycle(store, summary, sha)
    store.event('activity_rollout_previous', summary)
    before = source_bytes(settings)
    spec = approved_fixture(settings, prepare(settings, path, sha, mapping['account_id']), run_id='e'*32)
    assert activated_settings(settings, spec).enable_activity_feed
    assert source_bytes(settings) == before
    if status != 'prepared':
        with pytest.raises(ValueError):
            approved_fixture(settings, prepare(settings, path, sha, mapping['account_id']), run_id='d'*32)
        assert source_bytes(settings) == before


@pytest.mark.parametrize('damage', [
    pytest.param(lambda v: v.pop('reason'), id='missing-field'),
    pytest.param(lambda v: v.update(extra=0), id='extra-field'),
    pytest.param(lambda v: v.update(clock_diagnostics={}), id='partially-new-summary'),
    pytest.param(lambda v: v.update(status='unknown'), id='unsupported-status'),
    pytest.param(lambda v: v.update(reason=[]), id='non-string-reason'),
    pytest.param(lambda v: v.update(started_at='2029-02-30T00:00:00+00:00'), id='invalid-timestamp'),
    pytest.param(lambda v: v.update(duration_seconds=60), id='short-duration'),
    pytest.param(lambda v: v.update(elapsed_seconds=True), id='boolean-duration'),
    pytest.param(lambda v: v.update(max_acquisition_gap_seconds=-1), id='negative-duration'),
    pytest.param(lambda v: v.update(elapsed_seconds=float('inf')), id='nonfinite-duration'),
    pytest.param(lambda v: v.update(cycles=True), id='boolean-counter'),
    pytest.param(lambda v: v.update(cycles=1.5), id='fractional-counter'),
    pytest.param(lambda v: v.update(cycles=-1), id='negative-counter'),
    pytest.param(lambda v: v.update(cycles=float('nan')), id='nan-counter'),
    pytest.param(lambda v: v.update(cycles=float('inf')), id='infinite-counter'),
    pytest.param(lambda v: v.update(blocked_reasons=[]), id='invalid-counter-dictionary'),
    pytest.param(lambda v: v['blocked_reasons'].update(incomplete_activity_coverage=True), id='boolean-nested-counter'),
    pytest.param(lambda v: v['availability_samples'].update(unknown=1), id='unsupported-availability'),
    pytest.param(lambda v: v['latency'].pop('state'), id='missing-latency-population'),
    pytest.param(lambda v: v['latency'].update(lock_wait={}), id='new-latency-population'),
    pytest.param(lambda v: v['latency']['state'].update(extra=0), id='extra-histogram-field'),
    pytest.param(lambda v: v['latency']['state'].pop('samples'), id='missing-histogram-field'),
    pytest.param(lambda v: v['latency']['state'].update(samples=True), id='boolean-latency-counter'),
    pytest.param(lambda v: v['latency']['state'].update(p95_upper_ms=True), id='boolean-latency-bound'),
    pytest.param(lambda v: v['latency']['state'].update(p95_upper_ms=251), id='unsupported-latency-bound'),
    pytest.param(lambda v: v.update(current_accounting_is_separate=False), id='changed-accounting-marker'),
    pytest.param(lambda v: v.update(operational_acceptance='accepted'), id='changed-acceptance-marker'),
    pytest.param(lambda v: v.update(reader_enabled=1), id='non-boolean-reader'),
    pytest.param(lambda v: v.update(orders_enabled=True), id='enabled-orders'),
    pytest.param(lambda v: v.update(run_id=True), id='malformed-direct-identity'),
    pytest.param(lambda v: v.update(clock_diagnostics={'run_id': 'wrong'}), id='malformed-clock-identity'),
    pytest.param(lambda v: v.update(run_id='e'*32), id='reused-direct-identity'),
    pytest.param(lambda v: v.update(recovered_by='e'*32), id='reused-recovery-identity'),
    pytest.param(lambda v: v['blocked_reasons'].update(run_id=0), id='identity-key-in-counter'),
    pytest.param(lambda v: v['blocked_reasons'].update(run_id='e'*32), id='reused-nested-identity'),
    pytest.param(lambda v: v['blocked_reasons'].update(history=[{'recovered_by': True}]), id='malformed-list-identity'),
    pytest.param(lambda v: v['blocked_reasons'].update(history=[{'recovered_by': 'e'*32}]), id='reused-list-identity'),
])
def test_legacy_looking_corruption_denies_proposal_and_recheck_without_writes(rollout, damage):
    """The compatibility exception must not hide damaged history or identity reuse."""
    settings, store, path, sha, mapping = rollout
    spec = approved_fixture(settings, prepare(settings, path, sha, mapping['account_id']), run_id='e'*32)
    summary = legacy_summary_fixture()
    damage(summary)
    # Raw fixture insertion exercises the decoder's nonfinite rejection as well.
    store.db.execute('INSERT INTO events(at,type,payload) VALUES(?,?,?)',
                     (NOW, 'activity_rollout_previous', json.dumps(summary)))
    before = source_bytes(settings)
    with pytest.raises(ValueError):
        approved_fixture(settings, prepare(settings, path, sha, mapping['account_id']), run_id='e'*32)
    assert source_bytes(settings) == before
    with pytest.raises(ValueError):
        activated_settings(settings, spec)
    assert source_bytes(settings) == before


@pytest.mark.parametrize('kind', ['activity_rollout_started', 'activity_rollout_stopped',
                                'activity_attempt_started', 'activity_observation_sleep_started'])
def test_legacy_summary_under_another_event_type_still_denies(rollout, kind):
    """An old payload cannot excuse missing lifecycle identities outside previous archives."""
    settings, store, path, sha, mapping = rollout
    store.event(kind, legacy_summary_fixture())
    before = source_bytes(settings)
    with pytest.raises(ValueError):
        approved_fixture(settings, prepare(settings, path, sha, mapping['account_id']))
    assert source_bytes(settings) == before


@pytest.mark.parametrize('field', ['run_id', 'recovered_by'])
def test_legacy_looking_foreign_identity_keeps_reuse_checks(rollout, field):
    """Identity-bearing history keeps its existing foreign/reused handling."""
    settings, store, path, sha, mapping = rollout
    store.event('activity_rollout_previous', {**legacy_summary_fixture(), field: 'd'*32})
    before = source_bytes(settings)
    spec = approved_fixture(settings, prepare(settings, path, sha, mapping['account_id']), run_id='e'*32)
    assert activated_settings(settings, spec).enable_activity_feed
    assert source_bytes(settings) == before
    with pytest.raises(ValueError):
        approved_fixture(settings, prepare(settings, path, sha, mapping['account_id']), run_id='d'*32)
    assert source_bytes(settings) == before


def test_duplicate_field_in_legacy_archive_denies_without_repair(rollout):
    """A repeated old field must not be collapsed into an apparently valid archive."""
    settings, store, path, sha, mapping = rollout
    raw = '{"cycles":3,'+json.dumps(legacy_summary_fixture())[1:]
    store.db.execute('INSERT INTO events(at,type,payload) VALUES(?,?,?)',
                     (NOW, 'activity_rollout_previous', raw))
    before = source_bytes(settings)
    with pytest.raises(ValueError):
        approved_fixture(settings, prepare(settings, path, sha, mapping['account_id']))
    assert source_bytes(settings) == before
