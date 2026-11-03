"""Public offline evidence interpretation, copy safety and process isolation."""
import asyncio
from contextlib import closing, asynccontextmanager
from copy import deepcopy
from datetime import datetime, timedelta
from decimal import Decimal, getcontext
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
from types import SimpleNamespace

import httpx
import pytest

from test_activity_rollout import NOW, legacy_summary_fixture, mock_engine, rollout, seed_legacy_lifecycle  # noqa: F401
from backend.activity_gap_report import PRODUCER, SUPPORTED_PRODUCER_SHA256, S5_PRODUCER_SHA256, build_report, main
from backend.evidence_codec import pack_text, unpack_text, REFERENCE

PROJECT = Path(__file__).resolve().parents[1]


class Clock:
    def __init__(self):
        self.elapsed, self.offset, self.step = 0, 0, .0001

    def mono(self):
        self.elapsed += self.step
        return self.elapsed

    def wall(self):
        return (datetime.fromisoformat(NOW)+timedelta(seconds=self.elapsed+self.offset)).isoformat()


def seal(path, synthetic=True, producer=None, capture_id='disposable-producer-fixture'):
    value = {'schema_version': 1, 'method': 'sqlite-backup', 'complete': True,
             'capture_id': capture_id, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
             'size_bytes': path.stat().st_size, 'synthetic': synthetic,
             'producer_sha256': dict(SUPPORTED_PRODUCER_SHA256) if producer is None else producer}
    if not synthetic:
        value.update(capture_provenance_ref='synthetic-non-operational-test', authorization_ref='synthetic-non-operational-test')
    manifest = path.parent/'copy.json'; manifest.write_text(json.dumps(value))
    return manifest


def policy(path, **changes):
    value = {'schema_version': 1, 'synthetic': True, 'tau_seconds': .1, 'tau_c_seconds': .1,
             'allow_indeterminate_e4': True, 'provenance_ref': 'synthetic-test-only'}
    value.update(changes); path.write_text(json.dumps(value)); return path


def change(path, fn):
    with closing(sqlite3.connect(path)) as db:
        with db:fn(db)
    return seal(path)


def event_change(db, kind, fn):
    for seq, payload in db.execute('SELECT seq,payload FROM events WHERE type=? ORDER BY seq', (kind,)).fetchall():
        value = json.loads(payload); fn(value)
        db.execute('UPDATE events SET payload=? WHERE seq=?', (json.dumps(value), seq))


def generated(rollout, monkeypatch, tmp_path, mode='success', cycles=2, jump=None):
    engine, calls, _ = mock_engine(rollout)
    observation, store, clock = engine.activity_observation, engine.store, Clock()
    observation.clock, observation.wall_clock = clock.mono, clock.wall
    if mode=='short-final':clock.step=1e-9
    slept, jumped = [0], [False]
    original_event = store.event
    monkeypatch.setattr(observation, 'budget_ok', lambda: slept[0] < cycles)
    # Reset controlled capacity between fixture sleeps; production capacity is unchanged.
    probe=[]
    if mode=='loop-lag':
        start_probe=observation.start_lag_probe
        class Loop:
            def time(self):return clock.elapsed
            def call_later(self,_delay,callback,*args):probe.append((callback,args));return SimpleNamespace(cancel=lambda:None)
        monkeypatch.setattr(observation,'start_lag_probe',lambda _loop:start_probe(Loop()))
    original_sleep = asyncio.sleep
    async def sleep(delay):
        if jump in {'sleep','backward-sleep','opposing','divergence'} and not jumped[0]:clock.offset += -3600 if jump=='backward-sleep' else 1 if jump=='divergence' else 3600; jumped[0] = True
        if mode == 'interrupted-sleep':
            clock.elapsed += 7
            raise asyncio.CancelledError()
        initial=clock.elapsed
        if mode=='loop-lag':
            for increment in (11,1.1):
                clock.elapsed+=increment;callback,args=probe.pop(0);callback(*args)
            clock.elapsed=initial
        if mode=='short-final' and slept[0]==0:clock.elapsed=86400-10+.0000006
        else:clock.elapsed += delay
        slept[0] += 1
        engine.broker.trading.calls.clear()
        await original_sleep(0)
    monkeypatch.setattr('backend.activity_observation.asyncio.sleep', sleep)
    if jump == 'residual' or mode == 'residual-delay':
        def event(kind, value):
            result = original_event(kind, value)
            if kind == 'activity_attempt_finished' and not jumped[0]:
                if mode=='residual-delay':clock.elapsed+=10
                else:clock.offset+=3600
                jumped[0]=True
            return result
        monkeypatch.setattr(store, 'event', event)
    handler = engine.broker.http._transport.handler
    reversed_step=[False]
    def transport(request):
        if jump=='opposing' and observation.cycles==2 and request.url.path=='/v2beta1/events/activities' and not reversed_step[0]:
            clock.offset-=3600;reversed_step[0]=True
        if jump == 'request' and not jumped[0] and request.url.path == '/v2beta1/events/activities':
            clock.offset += 3600; jumped[0] = True
        if mode == 'failed-between' and observation.cycles == 2:raise httpx.ReadTimeout('private-canary')
        if mode == 'provider-status':return httpx.Response(503, json={'private-canary': 'hidden'})
        if mode == 'transport-before':raise httpx.ReadTimeout('private-canary')
        if mode == 'collection-cancel':raise asyncio.CancelledError()
        if mode == 'transport-after':
            class Broken(httpx.AsyncByteStream):
                async def __aiter__(self):
                    yield b'{'
                    raise httpx.ReadError('private-canary')
            return httpx.Response(200,stream=Broken())
        return handler(request)
    monkeypatch.setattr(engine.broker.http._transport, 'handler', transport)
    if mode in {'pre-batch', 'pre-lock'}:
        async def reject(*_args, **_kwargs):raise ValueError('private-canary')
        monkeypatch.setattr('backend.activity_observation.collect_batch' if mode == 'pre-batch' else 'backend.engine.Engine.refresh_activity_feed', reject)
    if mode == 'pre-admission':monkeypatch.setattr(observation, 'budget_ok', lambda: False)
    if mode == 'budget-stop':
        decisions = iter([True, False]); monkeypatch.setattr(observation, 'budget_ok', lambda: next(decisions))
    if mode == 'inactive-after-retention':
        from backend.activity_observation import collect_batch
        async def expire(*args, **kwargs):
            result = await collect_batch(*args, **kwargs); clock.elapsed = 86401; return result
        monkeypatch.setattr('backend.activity_observation.collect_batch', expire)
    if mode == 'snapshot-storage':
        put = store.put
        def put_fault(key, value):
            if key == 'snapshot_epoch':raise OSError('private-canary')
            return put(key, value)
        monkeypatch.setattr(store, 'put', put_fault)
    if mode == 'publication-failure':
        def fail(*_args, **_kwargs):raise ValueError('private-canary')
        monkeypatch.setattr('backend.activity_observation.publish_projection', fail)
    if mode == 'sample-failure':
        coverage = observation.coverage
        def fail(*args, **kwargs):
            if kwargs.get('record') is False:raise ValueError('private-canary')
            return coverage(*args, **kwargs)
        monkeypatch.setattr(observation, 'coverage', fail)
    if mode == 'local-budget':engine.broker.trading.normal = 0
    if mode == 'local-cooldown':engine.broker.cooldown['trading'] = time.monotonic()+10000
    if mode in {'acquired-inactive','slow-lock'}:
        lock=engine.lock
        @asynccontextmanager
        async def acquisition_lock():
            async with lock:
                if mode=='acquired-inactive':clock.elapsed=86401
                elif observation.cycles==2:clock.elapsed+=61
                yield
        class Lock:
            def __aenter__(self):self.context=acquisition_lock();return self.context.__aenter__()
            def __aexit__(self,*args):return self.context.__aexit__(*args)
        engine.lock=Lock()
    if mode == 'storage-latch':
        def fail(kind, value):
            if kind == 'activity_attempt_finished':raise sqlite3.OperationalError('private-canary')
            return original_event(kind, value)
        monkeypatch.setattr(store, 'event', fail)
    async def scenario():
        try:
            if mode in {'lock-cancel', 'lock-deadline'}:
                await engine.lock.acquire()
                entered = asyncio.Event(); refresh = engine.refresh_activity_feed
                async def gated():entered.set(); return await refresh()
                monkeypatch.setattr(engine, 'refresh_activity_feed', gated)
                if mode == 'lock-deadline':
                    timeout = asyncio.timeout; monkeypatch.setattr('backend.activity_observation.asyncio.timeout', lambda _: timeout(0))
                task = asyncio.create_task(observation.run(engine)); await entered.wait()
                if mode == 'lock-cancel':task.cancel()
                try:await task
                except asyncio.CancelledError:pass
                engine.lock.release()
            else:
                try:await observation.run(engine)
                except asyncio.CancelledError:pass
        finally:await engine.broker.close()
    asyncio.run(scenario())
    target_dir = tmp_path/'evidence';target_dir.mkdir(exist_ok=True);target = target_dir/'copy.sqlite'
    with closing(sqlite3.connect(target)) as destination:
        store.db.backup(destination)
        assert destination.execute('PRAGMA journal_mode=DELETE').fetchone()[0] == 'delete'
        destination.commit()
    assert target.read_bytes()[18:20] == b'\x01\x01'
    assert not Path(str(target)+'-wal').exists()
    # Only fixture preparation removes an orphan index after completed conversion/close.
    Path(str(target)+'-shm').unlink(missing_ok=True)
    manifest, rules = seal(target), policy(tmp_path/'policy.json')
    return SimpleNamespace(ledger=target, manifest=manifest, policy=rules, run=observation.run_id,
                           observation=observation, calls=calls, clock=clock)


@pytest.fixture
def evidence(rollout, monkeypatch, tmp_path):
    return generated(rollout, monkeypatch, tmp_path)


def report(evidence, rules=True):
    return build_report(evidence.ledger, evidence.manifest, evidence.run, evidence.policy if rules else None)


def snapshot(directory):
    return {p.name: (p.stat().st_ino, p.stat().st_size, p.stat().st_mtime_ns, p.read_bytes())
            for p in directory.iterdir() if p.is_file()}


def test_producer_contract_drift_requires_reviewed_update():
    assert tuple(SUPPORTED_PRODUCER_SHA256) == PRODUCER
    expected_s5 = dict(zip(PRODUCER, (
        'b12dc0518704fa6c40924d09fc8943d015a9e240e7f0ad08ea624235b14a2ab9',
        'cf8601d99d0c26c40dc37a8bd31cc70a4c85f3028c6392f27cb6cb1e74ce0f7d',
        '014c3413ae3815be69239d40d0b13e89601a4681dd5fd377ca203fafcb792b8c',
        '3f508b9166c504578bee54223a3cab094b17b60771a41ba405e7a94858246f42',
        '1f42c772817777c62524485c7171eeca1bfe7d555756a95db060bce823da6d61')))
    assert S5_PRODUCER_SHA256 == expected_s5
    for name, expected in SUPPORTED_PRODUCER_SHA256.items():
        assert hashlib.sha256((PROJECT/name).read_bytes()).hexdigest() == expected
        if name != 'backend/activity_feed.py':assert expected == expected_s5[name]
    assert SUPPORTED_PRODUCER_SHA256['backend/activity_feed.py'] != expected_s5['backend/activity_feed.py']


def test_complete_producer_run_has_bound_counters_distinct_populations_and_no_writes(evidence):
    before = snapshot(evidence.ledger.parent); value = report(evidence)
    assert value['E1'] == 'satisfied', value['issues']
    assert value['exit_code'] == 0, value
    assert value['counters'] == {'cycles': 2, 'complete_acquisitions': 2, 'ratio_requirement': 'satisfied'}
    assert value['populations']['matched_publications'] == 2
    assert value['populations']['latency']['publication']['samples'] == 2
    assert value['populations']['availability_samples'] == {'current': 2}
    assert value['populations']['latency']['state']['samples'] == 0
    assert value['operational_acceptance'] == 'not-assessed'
    assert snapshot(evidence.ledger.parent) == before
    assert any(Decimal(p['monotonic_seconds']) > 0 for i in value['intervals']
               for p in i['contributions'] if p['category'] == 'diagnostic-write-overhead')


@pytest.mark.parametrize('mode,complete,e1', [
    ('pre-admission', 0, 'satisfied'), ('pre-lock', 0, 'satisfied'), ('pre-batch', 0, 'satisfied'),
    ('lock-cancel', 0, 'satisfied'), ('lock-deadline', 0, 'satisfied'),
    ('budget-stop', 0, 'satisfied'), ('inactive-after-retention', 0, 'satisfied'),
    ('snapshot-storage', 0, 'satisfied'), ('publication-failure', 1, 'satisfied'),
    ('sample-failure', 1, 'satisfied'), ('interrupted-sleep', 1, 'satisfied'),
    ('collection-cancel',0,'satisfied'),('acquired-inactive',0,'satisfied'),
    ('storage-latch', None, 'unknown'),
])
def test_real_terminal_paths_preserve_counting_and_expected_missing_boundaries(rollout, monkeypatch, tmp_path, mode, complete, e1):
    item = generated(rollout, monkeypatch, tmp_path, mode, cycles=1); value = report(item)
    assert value['E1'] == e1, value['issues']
    assert value['counters']['complete_acquisitions'] == complete
    if complete == 0:assert value['exit_code'] == 1
    if mode == 'budget-stop':
        assert value['counters']['cycles'] == 1
        assert Decimal(value['intervals'][-1]['end']['monotonic_seconds']) < Decimal(str(item.observation.latest_diagnostics['cycle']['boundaries']['attempt_finish']['monotonic_seconds']))


@pytest.mark.parametrize('kind', ['activity_attempt_started', 'activity_attempt_finished',
                                'activity_observation_sleep_started', 'activity_observation_sleep_finished',
                                'activity_rollout_started', 'activity_rollout_stopped'])
def test_missing_required_lifecycle_record_stays_unknown(evidence, kind):
    change(evidence.ledger, lambda db: db.execute('DELETE FROM events WHERE seq=(SELECT MIN(seq) FROM events WHERE type=?)', (kind,)))
    value = report(evidence)
    assert value['E1'] == 'unknown'
    assert value['exit_code'] == 3


@pytest.mark.parametrize('damage', ['outcome', 'duplicate', 'start-clock', 'sequence', 'abandoned', 'success-publication-end',
                                  'foreign-summary', 'nonfinite', 'duplicate-key', 'deep', 'precision', 'reference', 'compressed'])
def test_malformed_conflicting_or_incomplete_evidence_cannot_pass(evidence, damage):
    def alter(db):
        if damage == 'outcome':db.execute("DELETE FROM activity_batches WHERE phase='outcome'")
        elif damage == 'duplicate':db.execute("INSERT INTO events(at,type,payload) SELECT at,type,payload FROM events WHERE type='activity_attempt_started' LIMIT 1")
        elif damage == 'abandoned':
            db.execute("UPDATE events SET type='activity_attempt_abandoned' WHERE type='activity_attempt_finished'")
        elif damage == 'foreign-summary':
            db.execute("DELETE FROM events WHERE type='activity_rollout_stopped'")
            for key, raw in db.execute("SELECT key,value FROM state WHERE key='activity_rollout_observation'"):
                v=json.loads(raw);v['clock_diagnostics']['run_id']='f'*32;db.execute('UPDATE state SET value=? WHERE key=?',(json.dumps(v),key))
        elif damage in {'reference','compressed'}:
            raw = REFERENCE+b'0'*32 if damage == 'reference' else b'\x89ASTRALZ1\x00broken'
            db.execute("UPDATE activity_batches SET payload=? WHERE phase='outcome'", (raw,))
        elif damage in {'nonfinite','duplicate-key','deep','precision'}:
            raw = {'nonfinite':'{"run_id":NaN}', 'duplicate-key':'{"run_id":1,"run_id":2}',
                   'deep':'['*2000+'0'+']'*2000,
                   'precision':'{"monotonic_seconds":0.'+'1'*100+'}'}[damage]
            db.execute("UPDATE events SET payload=? WHERE type='activity_attempt_finished'",(raw,))
        else:
            def modify(v):
                if damage=='start-clock':v['clock']['monotonic_seconds']+=1
                elif damage=='sequence':v['sequence']+=1
                else:v['boundaries']['publication_end']=None
            event_change(db, 'activity_attempt_started' if damage in {'start-clock','sequence'} else 'activity_attempt_finished', modify)
    change(evidence.ledger, alter);value=report(evidence)
    assert value['E1']=='unknown', value
    assert value['exit_code']==3
    if damage == 'foreign-summary':assert value['counters']['cycles'] is None
    assert 'private-canary' not in json.dumps(value)


def test_missing_and_changed_producer_hashes_do_not_interpret_records(evidence):
    for name in PRODUCER:
        for replacement in (None, '0'*64, 'not-a-digest', [], {}):
            declared=dict(SUPPORTED_PRODUCER_SHA256)
            if replacement is None:declared.pop(name)
            else:declared[name]=replacement
            seal(evidence.ledger,producer=declared);value=report(evidence)
            assert value['exit_code']==3 and value['counters'] is None
            assert all(value[k]=='unknown' for k in ('E1','E2','E3','E4_policy'))


@pytest.mark.parametrize('copy_synthetic,policy_synthetic', [(True,False),(False,True),(False,False)])
def test_non_synthetic_policy_combinations_remain_unknown(evidence, copy_synthetic, policy_synthetic):
    seal(evidence.ledger,synthetic=copy_synthetic);policy(evidence.policy,synthetic=policy_synthetic)
    value=report(evidence);assert value['exit_code']==3 and value['policy_evaluation']=='unknown'


def test_absent_policy_and_missing_run_do_not_gain_defaults(evidence):
    value = report(evidence,False)
    assert value['exit_code']==3
    assert value['E3']==value['E4_policy']=='unknown'
    assert all(i['E3']==i['E4_policy']=='unknown' for i in value['intervals'])
    assert build_report(evidence.ledger,evidence.manifest,'f'*32,evidence.policy)['exit_code']==3


def test_internal_failure_has_its_own_sanitized_exit_without_output(evidence,monkeypatch,capsys):
    def fail(*_a,**_k):raise RuntimeError('private-canary')
    monkeypatch.setattr('backend.activity_gap_report.analyze',fail)
    assert main(['--ledger',str(evidence.ledger),'--copy-manifest',str(evidence.manifest),'--run-id',evidence.run])==4
    output=capsys.readouterr();assert output.out=='' and 'Traceback' not in output.err and 'private-canary' not in output.err


def test_ambient_decimal_precision_does_not_change_verdicts(evidence):
    expected=report(evidence);previous=getcontext().prec
    try:getcontext().prec=3;assert report(evidence)==expected
    finally:getcontext().prec=previous


@pytest.mark.parametrize('mode,locus', [('provider-status','observed-provider-status'),
    ('transport-before','transport-before-observed-headers'),('transport-after','transport-after-headers'),
    ('local-budget','local-budget/cooldown'),('local-cooldown','local-budget/cooldown'),
    ('snapshot-storage','storage'),('slow-lock','lock-wait')])
def test_supported_loci_use_recorded_evidence_without_claiming_network_root(rollout,monkeypatch,tmp_path,mode,locus):
    item=generated(rollout,monkeypatch,tmp_path,mode,cycles=3)
    value=report(item);assert value['E1']=='satisfied',value['issues']
    assert locus in {label for i in value['intervals'] for label in i.get('loci',[])}
    assert all(i['root_cause'] not in {'provider','network'} for i in value['intervals'])
    assert 'private-canary' not in json.dumps(value)


def test_failed_attempt_between_successes_preserves_ratio_and_candidate(rollout,monkeypatch,tmp_path):
    value=report(generated(rollout,monkeypatch,tmp_path,'failed-between',cycles=3))
    assert value['counters']['cycles']==3 and value['counters']['complete_acquisitions']==2
    assert value['exit_code']==1 and value['E1']=='satisfied'
    assert any(i['candidate'] and Decimal(i['monotonic_seconds'])>120 for i in value['intervals'])


@pytest.mark.parametrize('jump',['sleep','residual','request'])
def test_wall_only_step_is_clock_evidence_and_does_not_inflate_monotonic_delay(rollout,monkeypatch,tmp_path,jump):
    value=report(generated(rollout,monkeypatch,tmp_path,jump=jump))
    assert value['E1']=='satisfied',value['issues']
    assert value['E2']=='satisfied'
    assert any('clock-discontinuity' in i['loci'] for i in value['intervals'])
    assert sum(Decimal(p['monotonic_seconds']) for i in value['intervals'] for p in i['contributions'] if p['category']=='wake-delay')<1
    assert any(abs(Decimal(i['wall_seconds'])-Decimal(i['monotonic_seconds']))>3000 for i in value['intervals'])


def test_indeterminate_root_policy_is_explicit_and_cannot_fill_missing_evidence(rollout,monkeypatch,tmp_path):
    item=generated(rollout,monkeypatch,tmp_path,'slow-lock',cycles=2)
    value=report(item);assert any(i['candidate'] for i in value['intervals'])
    assert value['E4_policy']=='satisfied'
    policy(item.policy,allow_indeterminate_e4=False);value=report(item)
    assert value['exit_code']==1 and value['E4_policy']=='not-satisfied'
    change(item.ledger,lambda db:db.execute("DELETE FROM events WHERE type='activity_attempt_finished'"))
    assert report(item)['E1']=='unknown'


def test_residual_is_not_relabelled_as_overhead_and_nested_spans_are_not_added(evidence):
    original=report(evidence)
    for interval in original['intervals']:
        allocated=sum(Decimal(p['monotonic_seconds']) for p in interval['contributions'])
        assert allocated+Decimal(interval['residual_monotonic_seconds'])==Decimal(interval['monotonic_seconds'])
    maximum=max(Decimal(i['residual_monotonic_seconds']) for i in original['intervals'])
    policy(evidence.policy,tau_seconds=float(maximum))
    assert report(evidence)['E2']=='satisfied'
    policy(evidence.policy,tau_seconds=float(maximum-Decimal('0.000001')))
    assert report(evidence)['E2']=='not-satisfied'
    assert any(Decimal(i['residual_monotonic_seconds'])>0 for i in original['intervals'])


def test_missing_final_sleep_pair_and_conflicting_summary_cannot_pass(evidence):
    change(evidence.ledger,lambda db:db.execute("DELETE FROM events WHERE type LIKE 'activity_observation_sleep_%' AND json_extract(payload,'$.sequence')=2"))
    assert report(evidence)['E1']=='unknown'


def test_corrupt_outcome_does_not_hide_reliable_failing_counters(rollout,monkeypatch,tmp_path):
    item=generated(rollout,monkeypatch,tmp_path,'transport-before',cycles=1)
    change(item.ledger,lambda db:db.execute("UPDATE activity_batches SET payload='broken' WHERE phase='outcome'"))
    value=report(item);assert value['E1']=='unknown' and value['exit_code']==1
    assert value['counters']['ratio_requirement']=='not-satisfied'


@pytest.mark.parametrize('fault',['wal-header','raw-main','sidecar','digest','header','view','hard-link','symlink','runtime'])
def test_unusable_containers_emit_no_report_and_preserve_input(evidence,tmp_path,capsys,fault):
    ledger=evidence.ledger
    if fault=='wal-header':
        with closing(sqlite3.connect(ledger)) as db:assert db.execute('PRAGMA journal_mode=WAL').fetchone()[0]=='wal'
        seal(ledger)
    elif fault=='raw-main':
        source=tmp_path/'wal-source.sqlite'
        with closing(sqlite3.connect(source)) as db:
            db.execute('PRAGMA journal_mode=WAL');db.execute('CREATE TABLE t(x)');db.commit()
            ledger.write_bytes(source.read_bytes())
        seal(ledger)
    elif fault=='sidecar':Path(str(ledger)+'-wal').write_bytes(b'fixture')
    elif fault=='digest':ledger.write_bytes(ledger.read_bytes()+b'changed')
    elif fault=='header':ledger.write_bytes(b'bad header'+ledger.read_bytes()[10:]);seal(ledger)
    elif fault=='view':
        change(ledger,lambda db:db.executescript('DROP TABLE events; CREATE VIEW events AS SELECT 1 AS seq,1 AS at,1 AS type,1 AS payload'))
    elif fault=='hard-link':os.link(ledger,tmp_path/'alias.sqlite')
    elif fault=='symlink':
        alias=tmp_path/'alias.sqlite';alias.symlink_to(ledger);ledger=alias
    else:
        folder=tmp_path/'runtime';folder.mkdir();target=folder/'copy.sqlite';target.write_bytes(ledger.read_bytes());ledger=target
    before=snapshot(evidence.ledger.parent)
    assert main(['--ledger',str(ledger),'--copy-manifest',str(evidence.manifest),'--run-id',evidence.run,'--format','json'])==2
    output=capsys.readouterr();assert output.out=='' and 'Traceback' not in output.err
    assert snapshot(evidence.ledger.parent)==before


@pytest.mark.parametrize('container', ['standalone', 'wal-header'])
def test_fresh_cli_process_audits_imports_network_read_only_uri_and_header_order(evidence,tmp_path,container):
    if container == 'wal-header':
        with closing(sqlite3.connect(evidence.ledger)) as db:
            assert db.execute('PRAGMA journal_mode=WAL').fetchone()[0]=='wal'
        seal(evidence.ledger)
    program=r'''
import sys,runpy,os,json
sys.dont_write_bytecode=True
project,ledger,manifest,run,policy,audit_path=sys.argv[1:]
sys.path.insert(0,project)
forbidden=('backend.store','backend.engine','backend.config','backend.broker','backend.app','backend.activity_observation','backend.activity_feed','backend.activity_diagnostics','httpx')
assert not any(n in sys.modules for n in forbidden)
observations={'connections':[],'header_open':False,'violations':[]}
def audit(event,args):
    bad=False
    if event=='import' and any(args[0]==n or args[0].startswith(n+'.') for n in forbidden):bad=True
    if event.startswith('socket.'):bad=True
    if event=='open':
        name,mode,flags=args
        if isinstance(name,str) and os.path.abspath(name)==ledger and not (flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC)):observations['header_open']=True
        if isinstance(name,str) and os.path.commonpath([os.path.abspath(name),os.path.dirname(ledger)])==os.path.dirname(ledger) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC):bad=True
    if event=='sqlite3.connect':
        observations['connections'].append(args[0])
        if not observations['header_open'] or not args[0].startswith('file:') or '?mode=ro' not in args[0]:bad=True
    if bad:
        observations['violations'].append(event)
        raise RuntimeError('isolation violation')
sys.addaudithook(audit)
sys.argv=['astral-gap-report','--ledger',ledger,'--copy-manifest',manifest,'--run-id',run,'--policy',policy,'--format','json']
try:runpy.run_module('backend.activity_gap_report',run_name='__main__')
except SystemExit as exc:code=exc.code
with open(audit_path,'w') as stream:json.dump(observations,stream)
raise SystemExit(code)
'''
    audit_path=tmp_path/'audit.json';before=snapshot(evidence.ledger.parent)
    p=subprocess.run([sys.executable,'-I','-B','-c',program,str(PROJECT),str(evidence.ledger.resolve()),str(evidence.manifest),evidence.run,str(evidence.policy),str(audit_path)],capture_output=True,text=True)
    audit=json.loads(audit_path.read_text());assert not audit['violations']
    if container == 'wal-header':
        assert p.returncode==2 and p.stdout==''
        assert audit['connections']==[]
    else:
        assert p.returncode==0,p.stderr
        value=json.loads(p.stdout);assert value['operational_acceptance']=='not-assessed'
        assert audit['connections']==[evidence.ledger.resolve().as_uri()+'?mode=ro']
    assert snapshot(evidence.ledger.parent)==before


def test_report_does_not_initialize_store_engine_or_load_settings(evidence,monkeypatch):
    def forbidden(*_a,**_k):raise AssertionError('forbidden initialization')
    monkeypatch.setattr('backend.store.Store.__init__',forbidden)
    monkeypatch.setattr('backend.engine.Engine.__init__',forbidden)
    monkeypatch.setattr('backend.config.Settings.from_env',forbidden)
    assert report(evidence)['exit_code']==0


def test_clock_step_placement_preserves_monotonic_accounting(rollout,monkeypatch,tmp_path):
    results=[]
    for jump in ('sleep','residual','request'):
        value=report(generated(rollout,monkeypatch,tmp_path,jump=jump))
        results.append([(i['monotonic_seconds'],i['residual_monotonic_seconds'],
                         [(p['category'],p['monotonic_seconds']) for p in i['contributions']]) for i in value['intervals']])
    assert results[0]==results[1]==results[2]


@pytest.mark.parametrize('jump',['backward-sleep','opposing'])
def test_backward_and_offsetting_wall_steps_remain_visible(rollout,monkeypatch,tmp_path,jump):
    value=report(generated(rollout,monkeypatch,tmp_path,jump=jump))
    assert value['E1']=='satisfied' and value['E2']=='satisfied'
    discrepancies=[Decimal(p['clock_discrepancy_seconds']) for i in value['intervals'] for p in i['clock_discrepancies']]
    assert any(v < -3000 for v in discrepancies)
    if jump=='opposing':assert any(v > 3000 for v in discrepancies)


@pytest.mark.parametrize('cycles,expected',[(100,'satisfied'),(99,'not-satisfied')])
def test_exact_frozen_ratio_does_not_round_a_failure_up(rollout,monkeypatch,tmp_path,cycles,expected):
    item=generated(rollout,monkeypatch,tmp_path,'failed-between',cycles=cycles)
    value=report(item)
    assert value['E1']=='satisfied',value['issues']
    assert value['counters']=={'cycles':cycles,'complete_acquisitions':cycles-1,'ratio_requirement':expected}


def translate_clocks(db,cut,delta):
    def translate(value):
        if isinstance(value,list):
            for item in value:translate(item)
        if not isinstance(value,dict):return
        if 'monotonic_seconds' in value and 'wall_at' in value:
            if Decimal(str(value['monotonic_seconds']))>=cut:
                value['monotonic_seconds']=float(Decimal(str(value['monotonic_seconds']))+delta)
                value['wall_at']=(datetime.fromisoformat(value['wall_at'])+timedelta(seconds=float(delta))).isoformat()
        else:
            for item in value.values():translate(item)
            if isinstance(value.get('started_clock'),dict):value['started_at']=value['started_clock']['wall_at']
            if isinstance(value.get('ended_clock'),dict):value['ended_at']=value['ended_clock']['wall_at']
    from backend.evidence_codec import unpack_text
    for table,column,key in [('events','payload','seq'),('state','value','key'),('activity_batches','payload','rowid')]:
        for row_id,raw in db.execute('SELECT '+key+','+column+' FROM '+table).fetchall():
            try:value=json.loads(unpack_text(raw))
            except ValueError:continue
            translate(value)
            db.execute('UPDATE '+table+' SET '+column+'=? WHERE '+key+'=?',(pack_text(json.dumps(value)),row_id))


@pytest.mark.parametrize('excess,candidate',[(Decimal('0'),False),(Decimal('0.000001'),True)])
def test_completion_interval_exact_120_boundary_uses_decimal_arithmetic(evidence,excess,candidate):
    first=report(evidence);one=Decimal(first['intervals'][0]['end']['monotonic_seconds'])
    def move_first(db):
        payload=db.execute("SELECT payload FROM events WHERE type='activity_attempt_finished' ORDER BY seq LIMIT 1").fetchone()[0]
        cut=Decimal(str(json.loads(unpack_text(payload))['boundaries']['lock_acquired']['monotonic_seconds']))
        translate_clocks(db,cut,Decimal('60.3')-one)
    change(evidence.ledger,move_first)
    second=report(evidence);two=Decimal(second['intervals'][1]['end']['monotonic_seconds'])
    def move_second(db):
        payload=db.execute("SELECT payload FROM events WHERE type='activity_attempt_finished' ORDER BY seq LIMIT 1 OFFSET 1").fetchone()[0]
        cut=Decimal(str(json.loads(unpack_text(payload))['boundaries']['lock_acquired']['monotonic_seconds']))
        translate_clocks(db,cut,Decimal('180.3')+excess-two)
    change(evidence.ledger,move_second);value=report(evidence)
    interval=value['intervals'][1]
    assert value['E1']=='satisfied',value['issues']
    assert Decimal(interval['start']['monotonic_seconds'])==Decimal('60.3')
    assert Decimal(interval['end']['monotonic_seconds'])==Decimal('180.3')+excess
    assert interval['candidate'] is candidate


def test_clock_divergence_threshold_equality_and_exceedance(rollout,monkeypatch,tmp_path):
    item=generated(rollout,monkeypatch,tmp_path,jump='divergence')
    value=report(item)
    divergence=max(abs(Decimal(i['clock_discrepancy_seconds'])) for i in value['intervals'])
    assert divergence==Decimal(1)
    policy(item.policy,tau_c_seconds=float(divergence))
    assert not any(i['candidate'] for i in report(item)['intervals'])
    policy(item.policy,tau_c_seconds=float(divergence-Decimal('0.000001')))
    assert any(i['candidate'] for i in report(item)['intervals'])


def test_post_close_change_withholds_buffered_stdout(evidence,monkeypatch,capsys):
    from backend.activity_gap_report import analyze
    def changed(*args,**kwargs):
        value=analyze(*args,**kwargs)
        with evidence.ledger.open('ab') as stream:stream.write(b'concurrent-change')
        return value
    monkeypatch.setattr('backend.activity_gap_report.analyze',changed)
    assert main(['--ledger',str(evidence.ledger),'--copy-manifest',str(evidence.manifest),'--run-id',evidence.run])==2
    assert capsys.readouterr().out==''


def test_short_final_sleep_can_wake_before_unrounded_target_without_conflict(rollout,monkeypatch,tmp_path):
    item=generated(rollout,monkeypatch,tmp_path,'short-final',cycles=10)
    with closing(sqlite3.connect(item.ledger)) as db:
        sleeps=[json.loads(p) for p, in db.execute("SELECT payload FROM events WHERE type='activity_observation_sleep_finished'")]
    assert any(v['result']=='woke' and v['wake']['monotonic_seconds']<v['scheduled_wake']['monotonic_seconds'] for v in sleeps)
    value=report(item);assert value['E1']=='satisfied',value['issues']


def test_loop_lag_maximum_does_not_move_to_latest_probe_or_enter_timing_totals(rollout,monkeypatch,tmp_path):
    item=generated(rollout,monkeypatch,tmp_path,'loop-lag',cycles=1);value=report(item)
    lag=next(v for v in value['loop_lag'] if v['samples']==2)
    latest=lag['latest_probe'];elapsed=Decimal(latest['observed']['monotonic_seconds'])-Decimal(latest['scheduled']['monotonic_seconds'])
    assert Decimal(lag['max_ms'])>5000 and elapsed<2
    assert lag['maximum_probe_interval']=='unknown' and not lag['included_in_interval_totals']
    for i in value['intervals']:
        assert sum(Decimal(p['monotonic_seconds']) for p in i['contributions'])+Decimal(i['residual_monotonic_seconds'])==Decimal(i['monotonic_seconds'])


def test_actual_over_precision_clock_is_unknown_without_rounding(evidence):
    import re
    def alter(db):
        seq,raw=db.execute("SELECT seq,payload FROM events WHERE type='activity_attempt_started' LIMIT 1").fetchone()
        raw=re.sub(r'"monotonic_seconds":\s*[0-9.e+-]+','"monotonic_seconds":0.'+'1'*100,raw,count=1)
        db.execute('UPDATE events SET payload=? WHERE seq=?',(raw,seq))
    change(evidence.ledger,alter);value=report(evidence)
    assert value['E1']=='unknown' and value['exit_code']==3


def test_corrupt_btree_fails_container_validation_without_report(evidence,capsys):
    raw=bytearray(evidence.ledger.read_bytes());raw[100]=255;evidence.ledger.write_bytes(raw);seal(evidence.ledger)
    assert main(['--ledger',str(evidence.ledger),'--copy-manifest',str(evidence.manifest),'--run-id',evidence.run])==2
    assert capsys.readouterr().out==''


def test_nullable_policy_fields_and_invalid_numeric_policy_are_distinct(evidence,capsys):
    policy(evidence.policy,tau_seconds=None,tau_c_seconds=None,allow_indeterminate_e4=None)
    assert report(evidence)['policy_evaluation']=='unknown'
    policy(evidence.policy,tau_seconds=True)
    assert main(['--ledger',str(evidence.ledger),'--copy-manifest',str(evidence.manifest),'--run-id',evidence.run,'--policy',str(evidence.policy)])==2
    assert capsys.readouterr().out==''


def test_unmarked_persistence_time_remains_residual(rollout,monkeypatch,tmp_path):
    value=report(generated(rollout,monkeypatch,tmp_path,'residual-delay'))
    assert value['E1']=='satisfied' and value['E2']=='not-satisfied'
    assert max(Decimal(i['residual_monotonic_seconds']) for i in value['intervals'])>=10
    assert sum(Decimal(p['monotonic_seconds']) for i in value['intervals'] for p in i['contributions'] if p['category']=='diagnostic-write-overhead')<1


def test_nested_observed_phases_do_not_change_parent_allocation(evidence):
    before=report(evidence)
    def alter(db):
        def trace(v):
            acquisition=v.get('acquisition') or v.get('diagnostics')
            if not acquisition:return
            for request in acquisition['requests']:
                request['phases']['http11.receive_response_body']={'state':'complete','count':1,
                    'started':request['started_clock'],'ended':request['ended_clock']}
        event_change(db,'activity_attempt_finished',trace)
        for rowid,raw in db.execute("SELECT rowid,payload FROM activity_batches WHERE phase='outcome'").fetchall():
            value=json.loads(unpack_text(raw));trace(value)
            db.execute('UPDATE activity_batches SET payload=? WHERE rowid=?',(pack_text(json.dumps(value)),rowid))
    change(evidence.ledger,alter);after=report(evidence)
    assert after['E1']=='satisfied'
    for old,new in zip(before['intervals'],after['intervals']):
        assert old['contributions']==new['contributions']
        assert old['residual_monotonic_seconds']==new['residual_monotonic_seconds']


def test_record_sequence_cannot_be_repaired_by_payload_timestamps(evidence):
    def alter(db):
        a=db.execute("SELECT MIN(seq) FROM events WHERE type='activity_attempt_started'").fetchone()[0]
        b=db.execute("SELECT MIN(seq) FROM events WHERE type='activity_attempt_finished'").fetchone()[0]
        db.execute('UPDATE events SET seq=-1 WHERE seq=?',(a,));db.execute('UPDATE events SET seq=? WHERE seq=?',(a,b));db.execute('UPDATE events SET seq=? WHERE seq=-1',(b,))
    change(evidence.ledger,alter);assert report(evidence)['E1']=='unknown'


def test_huge_counter_is_reconciled_without_allocating_its_claimed_population(evidence):
    def alter(db):
        def counters(v):v['cycles']=2**62
        event_change(db,'activity_rollout_stopped',counters)
        raw=db.execute("SELECT value FROM state WHERE key='activity_rollout_observation'").fetchone()[0]
        value=json.loads(raw);counters(value);db.execute("UPDATE state SET value=? WHERE key='activity_rollout_observation'",(json.dumps(value),))
    change(evidence.ledger,alter);value=report(evidence)
    assert value['E1']=='unknown' and value['exit_code']==1


def test_denied_snapshot_preserves_budget_charges_separately_from_sent_requests(rollout,monkeypatch,tmp_path):
    item=generated(rollout,monkeypatch,tmp_path,'local-budget',cycles=1);value=report(item)
    assert not item.calls
    assert value['populations']['request_budget_units']==3
    assert value['counters']['cycles']==1 and value['counters']['complete_acquisitions']==0


def test_phase_completion_labels_without_measurements_remain_unknown(evidence):
    def alter(db):
        def trace(value):
            acquisition=value.get('acquisition') or value.get('diagnostics')
            if acquisition:
                for request in acquisition['requests']:
                    for phase in request['phases'].values():phase.update(state='complete',count=1,started=None,ended=None)
        event_change(db,'activity_attempt_finished',trace)
        for rowid,raw in db.execute("SELECT rowid,payload FROM activity_batches WHERE phase='outcome'").fetchall():
            value=json.loads(unpack_text(raw));trace(value)
            db.execute('UPDATE activity_batches SET payload=? WHERE rowid=?',(pack_text(json.dumps(value)),rowid))
    change(evidence.ledger,alter);value=report(evidence)
    assert value['cycles']
    assert all(request['phase_attribution']=='unknown' for cycle in value['cycles'] for request in cycle['requests'])


def test_indeterminate_e4_cannot_pass_when_residual_requirement_fails(rollout,monkeypatch,tmp_path):
    item=generated(rollout,monkeypatch,tmp_path,'slow-lock',cycles=2)
    policy(item.policy,tau_seconds=0)
    value=report(item)
    candidates=[i for i in value['intervals'] if i['candidate'] and i['root_cause']=='indeterminate']
    assert candidates
    assert all(i['E2']=='not-satisfied' and i['E4_policy']=='unknown' for i in candidates)
    assert value['exit_code']==1


@pytest.mark.parametrize('case', ['failed-between','unsupported-producer','malformed-row','missing-counters'])
def test_text_cli_explains_verdict_identity_and_audit_evidence(rollout,monkeypatch,tmp_path,capsys,case):
    item=generated(rollout,monkeypatch,tmp_path,'failed-between' if case=='failed-between' else 'success',cycles=3)
    expected=1 if case=='failed-between' else 3
    if case=='unsupported-producer':
        declared=dict(SUPPORTED_PRODUCER_SHA256);declared[PRODUCER[-1]]='0'*64
        seal(item.ledger,producer=declared)
    elif case=='malformed-row':
        with closing(sqlite3.connect(item.ledger)) as db:
            seq=db.execute("SELECT MIN(seq) FROM events WHERE type='activity_attempt_finished'").fetchone()[0]
        change(item.ledger,lambda db:db.execute('UPDATE events SET payload=? WHERE seq=?',('broken',seq)))
    elif case=='missing-counters':
        def remove(db):
            db.execute("DELETE FROM events WHERE type='activity_rollout_stopped'")
            db.execute("DELETE FROM state WHERE key='activity_rollout_observation'")
        change(item.ledger,remove)
    assert main(['--ledger',str(item.ledger),'--copy-manifest',str(item.manifest),
                 '--run-id',item.run,'--policy',str(item.policy)])==expected
    output=capsys.readouterr();text=output.out
    assert output.err=='' and 'None' not in text and 'private-canary' not in text
    assert 'Run ID: '+item.run in text and str(item.ledger) not in text
    assert 'Policy evaluation: ' in text and 'Eligible synthetic policy: ' in text
    for name in ('backend/activity_gap_report.py','backend/activity_gap_analysis.py','backend/evidence_codec.py'):
        assert 'Implementation SHA-256 '+name+': ' in text
    if case=='failed-between':
        assert 'Process ID: '+str(os.getpid()) in text
        assert 'Ratio requirement: not-satisfied' in text
        assert 'Population matched_publications: ' in text and 'Histogram state: 0 samples' in text
        assert 'Population availability_samples: ' in text and 'Population publication_availability_samples: ' in text
    elif case=='unsupported-producer':
        assert 'Producer contract: unsupported' in text and PRODUCER[-1]+': different' in text
        assert 'supported SHA-256: '+SUPPORTED_PRODUCER_SHA256[PRODUCER[-1]] in text
        assert 'declared SHA-256: '+'0'*64 in text
    elif case=='malformed-row':
        assert 'Evidence: malformed-record (table=events, seq='+str(seq)+')' in text
    else:
        assert 'Acquisitions: unknown / unknown' in text


def test_help_is_an_invalid_non_report_invocation(capsys):
    assert main(['--help'])==2
    output=capsys.readouterr()
    assert output.out=='' and output.err=='Offline gap report input could not be verified.\n'


def test_readable_tables_with_corrupt_unused_index_fail_integrity_gate(evidence,capsys):
    with closing(sqlite3.connect(evidence.ledger)) as db:
        db.execute('CREATE INDEX integrity_probe ON activity_batches(at)');db.commit()
        page=db.execute("SELECT rootpage FROM sqlite_schema WHERE name='integrity_probe'").fetchone()[0]
        page_size=db.execute('PRAGMA page_size').fetchone()[0]
    raw=bytearray(evidence.ledger.read_bytes());offset=(page-1)*page_size
    assert raw[offset]==10  # Leaf index page; the schema and table records stay intact.
    cells=int.from_bytes(raw[offset+3:offset+5],'big');assert cells>0
    raw[offset+3:offset+5]=(cells-1).to_bytes(2,'big')
    evidence.ledger.write_bytes(raw);seal(evidence.ledger)
    with closing(sqlite3.connect(evidence.ledger.as_uri()+'?mode=ro',uri=True)) as db:
        assert db.execute('SELECT name FROM sqlite_schema').fetchall()
        assert [r[0] for r in db.execute('PRAGMA integrity_check')]!=['ok']
        for query in ("SELECT key,value FROM state WHERE key='activity_rollout_observation'",
                      'SELECT seq,type,payload FROM events ORDER BY seq',
                      'SELECT rowid,phase,account,payload FROM activity_batches ORDER BY rowid'):
            assert db.execute(query).fetchall()
    before=snapshot(evidence.ledger.parent)
    assert main(['--ledger',str(evidence.ledger),'--copy-manifest',str(evidence.manifest),'--run-id',evidence.run])==2
    assert capsys.readouterr().out==''
    assert snapshot(evidence.ledger.parent)==before


def test_sequential_observations_bind_own_cycles_and_archived_terminal_counters(rollout,monkeypatch,tmp_path):
    with monkeypatch.context() as patch:first=generated(rollout,patch,tmp_path,cycles=1)
    with monkeypatch.context() as patch:second=generated(rollout,patch,tmp_path,cycles=3)
    assert first.run!=second.run
    with closing(sqlite3.connect(second.ledger)) as db:
        archived=[json.loads(raw) for raw, in db.execute("SELECT payload FROM events WHERE type='activity_rollout_previous'")]
        assert any(v['clock_diagnostics']['run_id']==first.run and v['cycles']==1 for v in archived)
        owned={run: {json.loads(raw)['attempt_id'] for raw, in db.execute(
            "SELECT payload FROM events WHERE type='activity_attempt_finished'") if json.loads(raw)['run_id']==run}
            for run in (first.run,second.run)}
    for item,count in ((first,1),(second,3)):
        value=report(item)
        assert value['E1']=='satisfied',value['issues']
        assert value['counters']=={'cycles':count,'complete_acquisitions':count,'ratio_requirement':'satisfied'}
        assert [v['sequence'] for v in value['cycles']]==list(range(1,count+1))
        with closing(sqlite3.connect(item.ledger)) as db:
            ids={json.loads(db.execute('SELECT payload FROM events WHERE seq=?',(v['reference']['seq'],)).fetchone()[0])['attempt_id']
                 for v in value['cycles']}
        assert ids==owned[item.run]
        assert len(value['intervals'])==count+1
        assert Decimal(value['intervals'][0]['start']['monotonic_seconds'])==0
    change(first.ledger,lambda db:db.execute(
        "DELETE FROM events WHERE type='activity_rollout_stopped' AND json_extract(payload,'$.run_id')=?",(first.run,)))
    value=report(first)
    assert value['E1']=='unknown' and value['counters']['cycles']==value['counters']['complete_acquisitions']==1


def test_attempt_from_another_process_cannot_complete_selected_run(evidence):
    def alter(v):
        if v['sequence']==1:v['process_id']+=1
    change(evidence.ledger,lambda db:event_change(db,'activity_attempt_finished',alter))
    value=report(evidence)
    assert value['E1']=='unknown' and value['exit_code']==3


def test_corrupt_outcome_issue_order_is_stable_across_hash_seeds(evidence):
    def alter(db):
        originals=[r[0] for r in db.execute("SELECT id FROM activity_batches WHERE phase='start' ORDER BY rowid")]
        ids={old:str(n)*32 for n,old in enumerate(originals,1)}
        for old,new in ids.items():db.execute('UPDATE activity_batches SET id=? WHERE id=?',(new,old))
        def bind(v):v['attempt_id']=ids[v['attempt_id']]
        for kind in ('activity_attempt_started','activity_attempt_finished'):event_change(db,kind,bind)
        db.execute("UPDATE activity_batches SET payload='broken' WHERE phase='outcome'")
    change(evidence.ledger,alter)
    outputs=[]
    # These IDs have opposite set iteration order under the two seeds.
    for seed in ('1','3'):
        env=os.environ.copy();env['PYTHONHASHSEED']=seed
        result=subprocess.run([sys.executable,'-B','-m','backend.activity_gap_report','--ledger',str(evidence.ledger),
            '--copy-manifest',str(evidence.manifest),'--run-id',evidence.run,'--policy',str(evidence.policy),'--format','json'],
            cwd=PROJECT,env=env,capture_output=True,text=True)
        assert result.returncode==3 and result.stderr==''
        value=json.loads(result.stdout)
        assert len([i for i in value['issues'] if i['reason']=='malformed-record' and i['reference']['table']=='activity_batches'])==2
        outputs.append(result.stdout)
    assert outputs[0]==outputs[1]


def test_boundary_json_key_order_cannot_hide_backward_completion(evidence):
    def alter(db):
        seq,raw=db.execute("SELECT seq,payload FROM events WHERE type='activity_attempt_finished' ORDER BY seq DESC LIMIT 1").fetchone()
        value=json.loads(raw);marks=value['boundaries'];completion=deepcopy(marks['completion'])
        completion['monotonic_seconds']=float(Decimal(str(marks['collection_end']['monotonic_seconds']))-Decimal('0.000001'))
        reordered={}
        for name,sample in marks.items():
            if name=='collection_end':reordered['completion']=completion
            if name!='completion':reordered[name]=sample
        value['boundaries']=reordered
        db.execute('UPDATE events SET payload=? WHERE seq=?',(json.dumps(value),seq))
        def terminal(v):v['clock_diagnostics']['last_completion']=completion
        event_change(db,'activity_rollout_stopped',terminal)
        raw=db.execute("SELECT value FROM state WHERE key='activity_rollout_observation'").fetchone()[0]
        value=json.loads(raw);terminal(value)
        db.execute("UPDATE state SET value=? WHERE key='activity_rollout_observation'",(json.dumps(value),))
    change(evidence.ledger,alter);value=report(evidence)
    assert value['E1']=='unknown' and value['exit_code']==3


@pytest.mark.parametrize('mode', ['publication-failure','sample-failure','pre-lock'])
def test_unclassified_failed_operations_remain_unknown_despite_generous_residual_policy(rollout,monkeypatch,tmp_path,mode):
    item=generated(rollout,monkeypatch,tmp_path,mode,cycles=3 if mode=='pre-lock' else 1)
    if mode!='pre-lock':
        def delay(db):
            raw=db.execute("SELECT payload FROM events WHERE type='activity_attempt_finished'").fetchone()[0]
            cut=Decimal(str(json.loads(raw)['boundaries']['lock_released']['monotonic_seconds']))
            translate_clocks(db,cut,Decimal(90))
        change(item.ledger,delay)
    policy(item.policy,tau_seconds=1000)
    value=report(item);candidates=[i for i in value['intervals'] if i['candidate']]
    assert value['E1']=='satisfied',value['issues']
    assert candidates and all(i['E3']=='unknown' and i['root_cause']=='indeterminate' for i in candidates)
    assert value['E3']=='unknown'
    assert value['exit_code']==(1 if mode=='pre-lock' else 3)
    if mode!='pre-lock':
        assert value['E2']=='satisfied'
        assert max(Decimal(i['residual_monotonic_seconds']) for i in candidates)>=90
        partial='publication' if mode=='publication-failure' else 'immediate-sample'
        assert not any(p['category']==partial for i in candidates for p in i['contributions'])


@pytest.mark.parametrize('sequence', [[],{},True,0,2**63],ids=['list','object','boolean','zero','out-of-range'])
@pytest.mark.parametrize('mode,expected', [('success',3),('transport-before',1)])
def test_malformed_finish_sequence_is_row_unknown_with_known_counter_precedence(rollout,monkeypatch,tmp_path,capsys,sequence,mode,expected):
    item=generated(rollout,monkeypatch,tmp_path,mode,cycles=1)
    with closing(sqlite3.connect(item.ledger)) as db:
        seq=db.execute("SELECT seq FROM events WHERE type='activity_attempt_finished'").fetchone()[0]
    change(item.ledger,lambda db:event_change(db,'activity_attempt_finished',lambda v:v.update(sequence=sequence)))
    assert main(['--ledger',str(item.ledger),'--copy-manifest',str(item.manifest),'--run-id',item.run,
                 '--policy',str(item.policy),'--format','json'])==expected
    output=capsys.readouterr();assert output.err==''
    value=json.loads(output.out)
    assert value['E1']=='unknown'
    assert {'reason':'invalid-attempt-sequence','reference':{'table':'events','seq':seq}} in value['issues']
    assert value['counters']['ratio_requirement']==('satisfied' if mode=='success' else 'not-satisfied')


@pytest.mark.parametrize('boundary,delta,expected', [
    ('scheduled',-0.0001,'unknown'),('scheduled',0,'satisfied'),
    ('wake',0.0001,'unknown'),('wake',0,'satisfied')])
def test_sleep_clocks_follow_adjacent_attempts_allowing_equal_boundaries(evidence,boundary,delta,expected):
    def alter(db):
        seq,raw=db.execute("SELECT seq,payload FROM events WHERE type='activity_observation_sleep_finished' ORDER BY seq LIMIT 1").fetchone()
        value=json.loads(raw)
        kind='activity_attempt_finished' if boundary=='scheduled' else 'activity_attempt_started'
        offset=0 if boundary=='scheduled' else 1
        raw=db.execute('SELECT payload FROM events WHERE type=? ORDER BY seq LIMIT 1 OFFSET ?',(kind,offset)).fetchone()[0]
        attempt=json.loads(raw)
        edge=attempt['boundaries']['attempt_finish'] if boundary=='scheduled' else attempt['clock']
        sample=deepcopy(edge);sample['monotonic_seconds']+=delta
        sample['wall_at']=(datetime.fromisoformat(edge['wall_at'])+timedelta(seconds=delta)).isoformat()
        value[boundary]=sample
        db.execute('UPDATE events SET payload=? WHERE seq=?',(json.dumps(value),seq))
        if boundary=='scheduled':
            def started(v):
                if v['sequence']==1:
                    v['clock']=sample
                    v['scheduled_wake']={'monotonic_seconds':sample['monotonic_seconds']+v['intended_seconds'],
                        'wall_at':(datetime.fromisoformat(sample['wall_at'])+timedelta(seconds=v['intended_seconds'])).isoformat()}
            event_change(db,'activity_observation_sleep_started',started)
    change(evidence.ledger,alter);value=report(evidence)
    assert value['E1']==expected,value['issues']
    if expected=='unknown':
        with closing(sqlite3.connect(evidence.ledger)) as db:
            start_seq=db.execute("SELECT MIN(seq) FROM events WHERE type='activity_observation_sleep_started'").fetchone()[0]
        assert {'reason':'invalid-sleep','reference':{'table':'events','seq':start_seq}} in value['issues']


@pytest.mark.parametrize('contract', ['s5','s6','unsupported'])
def test_report_identifies_whole_reviewed_contract_without_relabeling_input(evidence, capsys, contract):
    # Legacy stamping here tests selection only; external frozen-S5 captures prove compatibility.
    declared = dict(S5_PRODUCER_SHA256 if contract == 's5' else SUPPORTED_PRODUCER_SHA256)
    if contract == 'unsupported':declared['backend/store.py'] = '0'*64
    seal(evidence.ledger, producer=declared, capture_id='synthetic-contract-selection-only-'+contract)
    before = snapshot(evidence.ledger.parent)
    value = report(evidence)
    expected = S5_PRODUCER_SHA256 if contract == 's5' else SUPPORTED_PRODUCER_SHA256
    assert value['schema_version'] == 1
    assert value['provenance']['matched_producer_contract'] == (None if contract == 'unsupported' else contract)
    assert value['provenance']['producer_contract_supported'] is (contract != 'unsupported')
    assert value['provenance']['supported_producer_sha256'] == expected
    assert value['provenance']['declared_producer_sha256'] == declared
    assert value['operational_acceptance'] == 'not-assessed'
    if contract == 'unsupported':
        assert value['exit_code'] == 3 and value['counters'] is None
    else:
        assert value['exit_code'] == 0 and value['counters']['cycles'] == 2
    assert main(['--ledger',str(evidence.ledger),'--copy-manifest',str(evidence.manifest),
                 '--run-id',evidence.run,'--policy',str(evidence.policy)]) == value['exit_code']
    text = capsys.readouterr().out
    assert 'Matched producer contract: '+('unknown' if contract == 'unsupported' else contract) in text
    assert 'None' not in text
    assert snapshot(evidence.ledger.parent) == before


@pytest.mark.parametrize('status', ['prepared', 'observing', 'expired', 'stopped', 'failed'])
def test_legacy_archive_preserves_selected_report_and_input_bytes(rollout, monkeypatch, tmp_path, status):
    """Old archives must not suppress or contribute to a complete selected run."""
    summary = legacy_summary_fixture(status)
    rollout[1].put('activity_rollout_observation', summary)
    seed_legacy_lifecycle(rollout[1], summary, rollout[3])
    item = generated(rollout, monkeypatch, tmp_path)
    before = snapshot(item.ledger.parent)
    value = report(item)
    selected = item.observation.summary()
    assert value['E1'] == 'satisfied', value['issues']
    assert value['exit_code'] == 0
    assert value['counters'] == {'cycles': 2, 'complete_acquisitions': 2, 'ratio_requirement': 'satisfied'}
    assert value['populations'] == {key: selected[key] for key in (
        'matched_publications', 'received_bytes', 'request_budget_units', 'latency',
        'availability_samples', 'publication_availability_samples')}
    assert len(value['intervals']) == 3
    assert value['operational_acceptance'] == 'not-assessed'
    assert snapshot(item.ledger.parent) == before


@pytest.mark.parametrize('damage', [
    'extra-field', 'clock-diagnostics', 'malformed-id', 'selected-id', 'nested-id',
    'recovery-id', 'boolean-counter', 'nonfinite-counter', 'duplicate-key', 'state-summary', 'stopped-event',
])
def test_legacy_looking_records_outside_exception_remain_unknown(evidence, damage):
    """Malformed, selected and current summaries must not gain the historical exception."""
    summary = legacy_summary_fixture()
    if damage == 'extra-field':summary['extra'] = 0
    elif damage == 'clock-diagnostics':summary['clock_diagnostics'] = {}
    elif damage == 'malformed-id':summary['run_id'] = True
    elif damage == 'selected-id':summary['run_id'] = evidence.run
    elif damage == 'nested-id':summary['blocked_reasons']['run_id'] = 0
    elif damage == 'recovery-id':summary['recovered_by'] = evidence.run
    elif damage == 'boolean-counter':summary['cycles'] = True
    elif damage == 'nonfinite-counter':summary['cycles'] = float('inf')
    raw = json.dumps(summary)
    if damage == 'duplicate-key':raw = '{"cycles":3,'+raw[1:]
    def alter(db):
        if damage == 'state-summary':
            db.execute("UPDATE state SET value=? WHERE key='activity_rollout_observation'", (raw,))
        else:
            kind = 'activity_rollout_stopped' if damage == 'stopped-event' else 'activity_rollout_previous'
            db.execute('INSERT INTO events(at,type,payload) VALUES(?,?,?)', (NOW, kind, raw))
    change(evidence.ledger, alter)
    before = snapshot(evidence.ledger.parent)
    value = report(evidence)
    assert value['E1'] == 'unknown'
    assert value['exit_code'] == 3
    expected = ('malformed-record' if damage in {'nonfinite-counter', 'duplicate-key'} else
                'invalid-summary' if damage == 'selected-id' else 'unassignable-record')
    assert expected in {issue['reason'] for issue in value['issues']}
    assert value['operational_acceptance'] == 'not-assessed'
    assert snapshot(evidence.ledger.parent) == before


def test_legacy_shaped_foreign_archive_cannot_replace_selected_terminal(evidence):
    """Valid foreign IDs remain isolated, and neither archive form supplies missing evidence."""
    def seed(db):
        for extra in ({}, {'run_id': 'd'*32}):
            db.execute('INSERT INTO events(at,type,payload) VALUES(?,?,?)',
                       (NOW, 'activity_rollout_previous', json.dumps({**legacy_summary_fixture(), **extra})))
    change(evidence.ledger, seed)
    before = snapshot(evidence.ledger.parent)
    value = report(evidence)
    assert value['E1'] == 'satisfied' and value['exit_code'] == 0
    assert value['counters']['cycles'] == 2
    assert snapshot(evidence.ledger.parent) == before
    def remove_selected(db):
        db.execute("DELETE FROM state WHERE key='activity_rollout_observation'")
        db.execute("DELETE FROM events WHERE type='activity_rollout_stopped'")
    change(evidence.ledger, remove_selected)
    before = snapshot(evidence.ledger.parent)
    value = report(evidence)
    assert value['E1'] == 'unknown' and value['exit_code'] == 3
    assert value['counters']['cycles'] is value['counters']['complete_acquisitions'] is None
    assert value['populations'] is None
    assert value['operational_acceptance'] == 'not-assessed'
    assert snapshot(evidence.ledger.parent) == before
