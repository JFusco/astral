"""Snapshot replacement and transaction failures must never create authority."""
import asyncio
from copy import deepcopy
from contextlib import closing
from datetime import datetime, timedelta
import json
from pathlib import Path
import sqlite3

import httpx
import pytest

from backend.accounting_snapshot import SnapshotCommitError, commit_snapshot
from backend.activity_diagnostics import failure_kind
from backend.activity_feed import collect_batch, current_accounting, publish_projection, read_projection, start_batch
from backend.activity_projection import input_digest, ledger_source
from backend.activity_validation import import_ledger
from backend.broker import AlpacaPaper, BrokerFailure
from backend.config import Settings
from backend.engine import Engine
from backend.evidence_codec import NAMESPACE
from backend.store import Store

FIXTURE = Path(__file__).parent/'fixtures/activity_feed/btc-sanitized-v1'
NOW = '2030-01-01T00:00:00+00:00'


@pytest.fixture
def account(tmp_path, monkeypatch):
    store = Store(tmp_path/'disposable.sqlite', 'alpaca')
    import_ledger(store, json.loads((FIXTURE/'ledger-selected-readonly.json').read_text()))
    snapshot = deepcopy(store.get('account_snapshot'));snapshot['at'] = NOW
    mapping = json.loads((FIXTURE/'mapping.json').read_text());mapping['kind'] = 'reviewed-provider'
    clock = {'now': NOW};calls = []
    monkeypatch.setattr('backend.activity_feed.utcnow', lambda: clock['now'])
    monkeypatch.setattr('backend.broker.utcnow', lambda: clock['now'])
    monkeypatch.setattr('backend.inventory.utcnow', lambda: clock['now'])
    def handler(request):
        calls.append((request.method, request.url.path))
        assert request.method == 'GET'
        if request.url.path == '/v2/account':return httpx.Response(200, json=snapshot['account'])
        if request.url.path == '/v2/positions':return httpx.Response(200, json=snapshot['positions'])
        if request.url.path == '/v2/clock':return httpx.Response(200, json=snapshot['clock'])
        assert request.url.path == '/v2beta1/events/activities'
        return httpx.Response(200, headers={'content-type':'text/event-stream'}, content=(FIXTURE/'activity-sse.raw').read_bytes())
    broker = AlpacaPaper(Settings(api_key='fixture', secret_key='fixture'), store, httpx.MockTransport(handler))
    yield store, snapshot, mapping, broker, calls, clock
    asyncio.run(broker.close());store.close()


def publish_current(account, *, refresh=True):
    store, _, mapping, broker, _, clock = account
    batch, receipt = asyncio.run(collect_batch(broker, store, refresh_snapshot=refresh))
    assert receipt['complete']
    result = publish_projection(store, batch, mapping, now=clock['now'])
    assert not result['issues']
    return result


def execution_rows(store):
    return {table:store.rows('SELECT * FROM '+table) for table in ('orders','fills','activities','observations')}


def test_standalone_refresh_commits_bound_epoch_with_same_seven_gets(account):
    store, snapshot, _, _, calls, _ = account
    before = execution_rows(store);original = deepcopy(snapshot)
    result = publish_current(account)
    assert [path for method,path in calls] == ['/v2/account','/v2/positions','/v2/clock',
        '/v2/account','/v2beta1/events/activities','/v2/account','/v2/positions']
    assert all(method == 'GET' for method,_ in calls)
    assert store.get('snapshot_epoch') == store.get('account_snapshot')['snapshot_epoch'] == result['coverage']['snapshot_epoch'] == 1
    assert snapshot == original
    assert execution_rows(store) == before
    assert not store.rows("SELECT * FROM events WHERE type='custody_snapshot'")
    view = current_accounting(store, enabled=True, now=NOW)
    assert view['accounting_by_symbol']['BTC']['passed']
    assert view['accounting_evidence']['snapshot_epoch'] == view['accounting_evidence']['acquisition_epoch'] == 1


@pytest.mark.parametrize('point', ['second-write','commit'])
def test_storage_failure_rolls_back_pair_and_retains_incomplete_attempt(account, monkeypatch, point):
    store, snapshot, _, broker, calls, _ = account
    before = deepcopy(store.get('account_snapshot'));rows = execution_rows(store)
    if point == 'second-write':
        put = store.put
        def fail(key,value):
            if key == 'snapshot_epoch':raise OSError('controlled storage fault')
            return put(key,value)
        monkeypatch.setattr(store,'put',fail)
    else:
        db = store.db
        class CommitFailure:
            fired = False
            def __getattr__(self,name):return getattr(db,name)
            def execute(self,sql,*args):
                if sql == 'COMMIT' and not self.fired:
                    self.fired = True
                    raise sqlite3.OperationalError('controlled commit fault')
                return db.execute(sql,*args)
        monkeypatch.setattr(store,'db',CommitFailure())
    batch,receipt = asyncio.run(collect_batch(broker,store,refresh_snapshot=True))
    assert not receipt['complete']
    assert receipt['snapshot_epoch'] is None
    assert store.get('account_snapshot') == before and store.get('snapshot_epoch') is None
    assert [p for _,p in calls] == ['/v2/account','/v2/positions','/v2/clock']
    assert len(store.rows("SELECT * FROM activity_batches WHERE id=? AND phase='outcome'",(batch,))) == 1
    assert execution_rows(store) == rows
    assert not current_accounting(store,enabled=True,now=NOW)['accounting_by_symbol']['BTC']['passed']


@pytest.mark.parametrize('bad', [None,False,0,-1,1.0,'1',{'epoch':1}], ids=['null','boolean','zero','negative','float','text','object'])
def test_corrupt_counter_denies_fresh_commit_without_reset(account,bad):
    store,snapshot,*_ = account
    with store.transaction():commit_snapshot(store,snapshot)
    store.put('snapshot_epoch',bad)
    before = store.get('account_snapshot')
    with pytest.raises(SnapshotCommitError,match='epoch unavailable'):
        with store.transaction():commit_snapshot(store,snapshot)
    assert store.get('snapshot_epoch') == bad and store.get('account_snapshot') == before
    assert not current_accounting(store,enabled=True,now=NOW)['accounting_by_symbol']['BTC']['passed']


@pytest.mark.parametrize('bad', [True,'1',1.0,0,None], ids=['boolean','text','float','zero','null'])
def test_malformed_retained_epoch_denies_fresh_commit_without_overwriting_evidence(account,bad):
    store,snapshot,*_ = account
    with store.transaction():assert commit_snapshot(store,snapshot) == 1
    store.put('account_snapshot',{**snapshot,'snapshot_epoch':bad})
    before = store.get('account_snapshot')
    with pytest.raises(SnapshotCommitError,match='epoch unavailable'):
        with store.transaction():commit_snapshot(store,snapshot)
    assert store.get('snapshot_epoch') == 1 and store.get('account_snapshot') == before


@pytest.mark.parametrize('invalid', ['number','non-finite','identity','shape'])
def test_invalid_snapshot_is_sanitized_and_commits_neither_value(account,invalid):
    store,snapshot,*_ = account
    changed = deepcopy(snapshot)
    if invalid == 'number':changed['account']['cash'] = 'private-invalid-value'
    elif invalid == 'non-finite':changed['account']['equity'] = 'NaN'
    elif invalid == 'identity':changed['account']['id'] = {'private':'identity'}
    else:changed['positions'] = None
    before = store.get('account_snapshot')
    with pytest.raises(SnapshotCommitError) as caught:
        with store.transaction():commit_snapshot(store,changed)
    assert str(caught.value) == 'Accounting snapshot validation failed'
    assert failure_kind(caught.value) == 'SnapshotCommitError'
    assert store.get('snapshot_epoch') is None and store.get('account_snapshot') == before


def test_helper_requires_transaction_and_cannot_restart_lost_counter(account):
    store,snapshot,*_ = account
    with pytest.raises(SnapshotCommitError,match='transaction required'):commit_snapshot(store,snapshot)
    with store.transaction():commit_snapshot(store,snapshot)
    store.db.execute("DELETE FROM state WHERE key='snapshot_epoch'")
    before = store.get('account_snapshot')
    with pytest.raises(SnapshotCommitError,match='epoch unavailable'):
        with store.transaction():commit_snapshot(store,snapshot)
    assert store.get('snapshot_epoch') is None and store.get('account_snapshot') == before


def test_undecodable_epoch_blocks_current_reads_and_commit_without_repair(account):
    store,snapshot,*_ = account
    publish_current(account)
    store.db.execute("UPDATE state SET value='{' WHERE key='snapshot_epoch'")
    before = store.get('account_snapshot')
    assert 'accounting_snapshot_epoch_unavailable' in current_accounting(store,enabled=True,now=NOW)['activity_coverage']['issues']
    with pytest.raises(SnapshotCommitError,match='epoch unavailable'):
        with store.transaction():commit_snapshot(store,snapshot)
    assert store.db.execute("SELECT value FROM state WHERE key='snapshot_epoch'").fetchone()[0] == '{'
    assert store.get('account_snapshot') == before


def test_missing_counter_after_legacy_replacement_cannot_reuse_historical_epoch(account):
    store,snapshot,*_ = account
    publish_current(account)
    store.put('account_snapshot',deepcopy(snapshot))
    store.db.execute("DELETE FROM state WHERE key='snapshot_epoch'")
    with pytest.raises(SnapshotCommitError,match='epoch unavailable'):
        with store.transaction():commit_snapshot(store,snapshot)
    assert store.get('snapshot_epoch') is None
    assert store.get('account_snapshot') == snapshot


def test_unreadable_history_denies_epoch_initialization_without_changing_snapshot(account):
    store,snapshot,*_ = account
    before = store.get('account_snapshot')
    store.db.execute('INSERT INTO activity_batches VALUES(?,?,?,?,?)',
                     ('unreadable','outcome',store.get('account_binding'),NOW,NAMESPACE+b'unsupported'))
    with pytest.raises(SnapshotCommitError,match='epoch unavailable'):
        with store.transaction():commit_snapshot(store,snapshot)
    assert store.get('snapshot_epoch') is None and store.get('account_snapshot') == before


def test_counter_below_retained_snapshot_version_cannot_be_incremented_back_into_use(account):
    store,snapshot,*_ = account
    with store.transaction():commit_snapshot(store,snapshot)
    with store.transaction():commit_snapshot(store,snapshot)
    store.put('snapshot_epoch',1)
    with pytest.raises(SnapshotCommitError,match='epoch unavailable'):
        with store.transaction():commit_snapshot(store,snapshot)
    assert store.get('snapshot_epoch') == 1 and store.get('account_snapshot')['snapshot_epoch'] == 2


def test_import_only_evidence_stays_historical_without_gaining_epoch(account):
    from backend.activity_validation import import_capture, acceptance
    store,_,mapping,_,_,_ = account
    capture = json.loads((FIXTURE/'activity-sse.json').read_text())
    result = import_capture(store,capture,(FIXTURE/'activity-sse.raw').read_bytes(),mapping,now=NOW)
    assert all(acceptance(result,store)[0].values())
    view = current_accounting(store,enabled=True,now=NOW)
    assert store.get('snapshot_epoch') is None
    assert result['coverage']['snapshot_epoch'] is None
    assert 'activity_snapshot_epoch_unavailable' in view['activity_coverage']['issues']
    assert view['cash_reconciliation']['cash'] is None
    assert read_projection(store,cutoff=NOW)['cash_reconciliation']['cash'] == '99999.70'


@pytest.mark.parametrize('backward', [False,True], ids=['equal-time','backward-clock'])
def test_equal_balance_replacement_invalidates_old_acquisition(account,backward):
    store,snapshot,_,_,_,_ = account
    publish_current(account);digest_before = input_digest(ledger_source(store))
    newer = deepcopy(snapshot)
    if backward:newer['at'] = (datetime.fromisoformat(NOW)-timedelta(seconds=1)).isoformat()
    with store.transaction():assert commit_snapshot(store,newer) == 2
    assert input_digest(ledger_source(store)) == digest_before
    current = current_accounting(store,enabled=True,now=NOW)
    assert 'accounting_snapshot_replaced' in current['activity_coverage']['issues']
    assert current['cash_reconciliation']['cash'] is None


@pytest.mark.parametrize('backward', [False,True], ids=['equal-balances','backward-clock'])
def test_default_collection_keeps_cutoff_epoch_when_reconcile_replaces_snapshot(account,backward):
    store,snapshot,mapping,broker,calls,clock = account
    with store.transaction():commit_snapshot(store,snapshot)
    stream = broker.stream_activities
    async def replace_while_streaming(since,until):
        replacement = deepcopy(snapshot)
        if backward:replacement['at'] = (datetime.fromisoformat(NOW)-timedelta(seconds=1)).isoformat()
        with store.transaction():commit_snapshot(store,replacement)
        return await stream(since,until)
    broker.stream_activities = replace_while_streaming
    batch,receipt = asyncio.run(collect_batch(broker,store))
    result = publish_projection(store,batch,mapping,now=NOW)
    assert receipt['snapshot_epoch'] == result['coverage']['snapshot_epoch'] == 1
    assert store.get('snapshot_epoch') == 2 and len(calls) == 4
    assert 'accounting_snapshot_replaced' in current_accounting(store,enabled=True,now=NOW)['activity_coverage']['issues']


def test_backward_clock_cannot_hide_new_pending_attempt_or_change_historical_cutoff(account):
    store,_,_,_,_,clock = account
    first_at = (datetime.fromisoformat(NOW)-timedelta(seconds=10)).isoformat()
    clock['now'] = first_at
    first = publish_current(account)
    clock['now'] = NOW
    pending = start_batch(store,store.get('account_binding'),first['coverage']['since'],NOW)
    read_at = (datetime.fromisoformat(NOW)-timedelta(seconds=5)).isoformat()
    current = current_accounting(store,enabled=True,now=read_at)
    assert current['accounting_evidence']['latest_attempt']['id'] == pending
    assert current['accounting_evidence']['latest_attempt']['status'] == 'pending'
    assert 'new_activity_attempt_pending' in current['activity_coverage']['issues']
    assert not current['accounting_by_symbol']['BTC']['passed']
    assert read_projection(store,cutoff=read_at) == first


def test_old_writer_replacement_blocks_roll_forward_until_fresh_collection(account):
    store,snapshot,_,_,_,_ = account
    publish_current(account)
    store.put('account_snapshot',deepcopy(snapshot))  # Compatible primary's old writer.
    assert store.get('snapshot_epoch') == 1
    assert 'accounting_snapshot_epoch_unavailable' in current_accounting(store,enabled=True,now=NOW)['activity_coverage']['issues']
    with store.transaction():assert commit_snapshot(store,snapshot) == 2
    assert not current_accounting(store,enabled=True,now=NOW)['accounting_by_symbol']['BTC']['passed']
    publish_current(account,refresh=False)
    assert current_accounting(store,enabled=True,now=NOW)['accounting_by_symbol']['BTC']['passed']


@pytest.mark.parametrize('reject', [False,True], ids=['successful-readback','helper-rejected-after-checkpoint'])
def test_reconciliation_owns_single_transaction_and_rolls_back_its_effects(account,monkeypatch,reject):
    store,snapshot,_,_,_,_ = account
    calls = []
    class Readback:
        async def snapshot(self):calls.append('snapshot');return deepcopy(snapshot)
        async def open_orders(self):calls.append('orders');return []
    engine = Engine(Settings(api_key='fixture',secret_key='fixture'),store,Readback())
    before = {key:store.get(key) for key in ['account_snapshot','snapshot_epoch','custody_checkpoint','baseline_equity','risk_marks','risk_latch']}
    equity = store.rows('SELECT * FROM equity')
    checkpoints = store.rows("SELECT * FROM events WHERE type='custody_snapshot'")
    if reject:
        def fail(store,snapshot):
            assert len(store.rows("SELECT * FROM events WHERE type='custody_snapshot'")) > len(checkpoints)
            raise SnapshotCommitError('Accounting snapshot epoch unavailable')
        monkeypatch.setattr('backend.engine.commit_snapshot',fail)
        engine.connected = True
        with pytest.raises(BrokerFailure):asyncio.run(engine.reconcile())
        assert not engine.connected
        assert {key:store.get(key) for key in before} == before
        assert store.rows('SELECT * FROM equity') == equity
        assert store.rows("SELECT * FROM events WHERE type='custody_snapshot'") == checkpoints
    else:
        asyncio.run(engine.reconcile())
        assert engine.connected and store.get('snapshot_epoch') == 1
    assert calls == ['snapshot','orders','snapshot']


def test_reconciliation_invalid_decimal_uses_existing_safe_failure_boundary(account):
    store,snapshot,*_ = account
    snapshot['account']['cash'] = 'private-invalid-number'
    class Readback:
        async def snapshot(self):return deepcopy(snapshot)
        async def open_orders(self):return []
    engine = Engine(Settings(api_key='fixture',secret_key='fixture'),store,Readback())
    engine.connected = True
    with pytest.raises(BrokerFailure) as caught:asyncio.run(engine.reconcile())
    assert not engine.connected and store.get('snapshot_epoch') is None
    assert 'private' not in str(caught.value)
    assert failure_kind(caught.value) == 'SnapshotCommitError'


def test_counter_high_water_repair_requires_fresh_snapshot_and_acquisition(account, tmp_path):
    """A counter-only repair cannot reuse any pre-repair accounting witness."""
    from backend.accounting_window import capture, recheck
    from backend.activity_feed import FeedError
    from backend.accounting_snapshot import valid_epoch
    store, _, _, broker, _, _ = account
    publish_current(account)
    witness = capture(store, 'BTC', enabled=True, now=NOW)
    rows = execution_rows(store)
    snapshot = deepcopy(store.get('account_snapshot'))
    history = {t:[tuple(row) for row in store.db.execute('SELECT * FROM '+t)] for t in (
        'activity_batches','activity_events','activity_associations','activity_conflicts',
        'activity_projections','evidence_blobs')}
    store.put('snapshot_epoch', 'damaged-counter')
    offending = store.db.execute("SELECT value FROM state WHERE key='snapshot_epoch'").fetchone()[0]
    with closing(sqlite3.connect(tmp_path/'before-repair.sqlite')) as backup:
        store.db.backup(backup)
        assert backup.execute("SELECT value FROM state WHERE key='snapshot_epoch'").fetchone()[0] == offending
    retained = [snapshot['snapshot_epoch']]
    for row in store.rows("SELECT payload FROM activity_batches WHERE phase='outcome'"):
        value = json.loads(row['payload'])['snapshot_epoch']
        assert value is None or valid_epoch(value)
        if value is not None:retained.append(value)
    for row in store.rows('SELECT payload FROM activity_projections'):
        value = json.loads(row['payload'])['coverage']['snapshot_epoch']
        assert value is None or valid_epoch(value)
        if value is not None:retained.append(value)
    high_water = max(retained)+1
    store.put('snapshot_epoch', high_water)
    assert high_water > max(retained)
    assert store.get('account_snapshot') == snapshot
    assert {t:[tuple(row) for row in store.db.execute('SELECT * FROM '+t)] for t in history} == history
    assert execution_rows(store) == rows
    with pytest.raises(FeedError):recheck(store,witness,enabled=True,now=NOW)
    assert not current_accounting(store,enabled=True,now=NOW)['accounting_by_symbol']['BTC']['passed']
    fresh = asyncio.run(broker.snapshot())
    with store.transaction():assert commit_snapshot(store,fresh) == high_water+1
    assert store.get('account_snapshot')['snapshot_epoch'] == high_water+1
    assert not current_accounting(store,enabled=True,now=NOW)['accounting_by_symbol']['BTC']['passed']
    with pytest.raises(FeedError):recheck(store,witness,enabled=True,now=NOW)
    publish_current(account,refresh=False)
    assert current_accounting(store,enabled=True,now=NOW)['accounting_by_symbol']['BTC']['passed']
    assert capture(store,'BTC',enabled=True,now=NOW)['snapshot_epoch'] == high_water+1
    with pytest.raises(FeedError):recheck(store,witness,enabled=True,now=NOW)
    assert execution_rows(store) == rows
