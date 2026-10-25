"""Health contracts: temporary ledgers and HTTP fixtures; never models/brokers."""
import asyncio
from datetime import datetime, timedelta, timezone
import json

import httpx
import pytest

from backend.health_engine import HealthEngine
from backend.service_health import HealthMonitor, parse_report, effective, MAX_BYTES
from backend.store import Store, utcnow


def report(status='operational'):
    return {'page':{'updated_at':'2026-01-01T00:00:00Z'},
            'status':{'indicator':'none','description':'All Systems Operational'},
            'components':[{'name':'Responses','status':status}]}


def test_published_green_cannot_hide_component_failure_or_invalid_coverage():
    assert parse_report('openai',json.dumps(report()).encode())['status']=='operational'
    assert parse_report('openai',json.dumps(report('major_outage')).encode())['status']=='incident'
    for raw in [{}, {'status':{'indicator':'none','description':'Fine'},'components':[]},report('new-unknown-status')]:
        with pytest.raises((ValueError,KeyError)):parse_report('openai',json.dumps(raw).encode())
    assert parse_report('quantconnect',b'<h1>All services are online</h1>')['status']=='operational'
    for body in [b'<h1>New layout</h1>',b'<script>All services are online</script>',b'x'*(MAX_BYTES+1)]:
        with pytest.raises(ValueError):parse_report('quantconnect',body)


def test_local_revalidation_time_is_distinct_from_provider_update_time():
    now=datetime.now(timezone.utc)
    value={'last_success_at':now.isoformat(),'fetch_status':'connected','report':{'status':'operational','source_updated_at':'2026-01-01T00:00:00Z'}}
    assert effective(value,now)['status']=='operational'
    assert effective(value,now+timedelta(seconds=361))['status']=='unknown'
    assert effective(value,now-timedelta(seconds=1))['status']=='unknown'
    assert effective({**value,'fetch_status':'error'},now)['status']=='unknown'


def test_provider_failure_backoff_cached_evidence_and_recovery_deduplicate(tmp_path):
    store=Store(tmp_path/'health.sqlite','health');calls=[];fail=False
    def handler(request):
        calls.append(request)
        assert request.method=='GET' and 'authorization' not in request.headers
        if fail:return httpx.Response(429,headers={'Retry-After':'36000'})
        return httpx.Response(200,content=b'<h1>All services are online</h1>' if request.url.host=='status.quantconnect.com' else json.dumps(report()).encode())
    async def exercise():
        nonlocal fail
        monitor=HealthMonitor(store,httpx.AsyncClient(transport=httpx.MockTransport(handler)))
        await monitor.poll();assert len(calls)==2
        assert all(p['status']=='operational' for p in monitor.state()['providers'])
        assert not monitor.state()['changes']
        for key in ('quantconnect','openai'):
            value=monitor.record(key);value['next_attempt_epoch']=0;store.put('service-health:'+key,value)
        fail=True;await monitor.poll();assert len(calls)==4
        assert all(p['status']=='unknown' and p['report']['status']=='operational' for p in monitor.state()['providers'])
        assert len(monitor.state()['changes'])==2
        await monitor.poll();assert len(calls)==4
        assert monitor.record('openai')['next_attempt_epoch']>=datetime.now(timezone.utc).timestamp()+35990
        for key in ('quantconnect','openai'):
            value=monitor.record(key);value['next_attempt_epoch']=0;store.put('service-health:'+key,value)
        await monitor.poll();assert len(monitor.state()['changes'])==2
        for key in ('quantconnect','openai'):
            value=monitor.record(key);value['next_attempt_epoch']=0;store.put('service-health:'+key,value)
        fail=False;await monitor.poll();assert len(monitor.state()['changes'])==4
        await monitor.close()
    asyncio.run(exercise());store.close()


def test_unchanged_incident_with_new_source_timestamp_does_not_alert_again(tmp_path):
    store=Store(tmp_path/'health.sqlite','health');monitor=HealthMonitor(store)
    try:
        value={'last_success_at':utcnow(),'fetch_status':'connected','report':{'status':'incident','description':'Degraded','components':[],'incidents':[],'source_updated_at':'old'}}
        monitor.save('openai',value)
        monitor.save('openai',{**value,'report':{**value['report'],'source_updated_at':'new'}})
        assert len(monitor.state()['changes'])==1
    finally:asyncio.run(monitor.close());store.close()


class Providers:
    def state(self):
        return {'providers':[{'id':'openai','name':'OpenAI','status':'operational','report':{'description':'Published green'},'scope':'Not a model execution probe','last_success_at':utcnow()}]}
    async def close(self):pass


def observations():
    now=utcnow()
    app={'as_of':now,'connected':True,'snapshot_at':now,'session_open':False,'model_enabled':False,'model':{},
         'workers':[{'name':'quotes','status':'healthy','at':now},{'name':'reconciliation','status':'healthy','at':now},{'name':'shadow','status':'disabled','at':now},{'name':'research','status':'waiting','at':now}],
         'quotes':{s:{'at':now,'received_at':now} for s in ('BTC','ETH','SOL')}}
    collector={'as_of':now,'sources':[{'id':'fed','name':'Fed','status':'connected','fresh':True,'last_success_at':now,'interval_seconds':300}],
               'alpaca':{'fetch_status':'connected','last_success_at':now,'report':{'status':'operational','description':'Published green'}}}
    return app,collector


def test_engine_health_is_separate_from_model_enablement_and_market_closure(tmp_path):
    store=Store(tmp_path/'health.sqlite','health');app,collector=observations();calls=[]
    def handler(request):
        calls.append(request)
        assert request.method=='GET' and request.url.host=='127.0.0.1'
        return httpx.Response(200,json=app if request.url.port==8766 else collector)
    async def exercise():
        engine=HealthEngine(store,httpx.AsyncClient(transport=httpx.MockTransport(handler)),Providers())
        await engine.cycle();state=engine.state();nodes={n['id']:n for n in state['nodes']}
        assert state['heartbeat_live'] and not state['execution_enabled']
        assert nodes['model']['status']=='inactive'
        assert nodes['provider:openai']['status']=='healthy'
        assert nodes['quote:BTC']['status']=='healthy' and nodes['quote:SPY']['status']=='inactive'
        assert nodes['worker:shadow']['status']=='inactive'
        assert nodes['worker:research']['status']=='checking'
        assert nodes['runtime:docker']['status']=='unknown'
        first=len(state['changes']);await engine.cycle();assert len(engine.state()['changes'])==first
        assert all(r.url.path=='/api/health-inputs' for r in calls)
        await engine.close()
    asyncio.run(exercise());store.close()


def test_missing_heartbeat_invalidates_all_cached_green_nodes(tmp_path):
    store=Store(tmp_path/'health.sqlite','health')
    engine=HealthEngine(store,providers=Providers())
    try:
        store.put('health-snapshot',{'sequence':4,'checked_at':(datetime.now(timezone.utc)-timedelta(seconds=31)).isoformat(),
                                    'nodes':[{'id':'broker','status':'healthy','name':'Broker','group':'core'}]})
        state=engine.state();assert not state['heartbeat_live']
        assert state['nodes'][0]['status']=='unknown' and state['nodes'][0]['last_status']=='healthy'
        engine.last_error='Fixture storage failure'
        value=store.get('health-snapshot');value['checked_at']=utcnow();store.put('health-snapshot',value)
        assert not engine.state()['heartbeat_live']
    finally:asyncio.run(engine.close());store.close()


@pytest.mark.parametrize('failure',['http','stale','schema'])
def test_local_observation_failures_do_not_reuse_healthy_state(tmp_path,failure):
    store=Store(tmp_path/'health.sqlite','health');app,collector=observations()
    def handler(request):
        if request.url.port==8768:return httpx.Response(200,json=collector)
        if failure=='http':return httpx.Response(503)
        if failure=='schema':return httpx.Response(200,json=[])
        return httpx.Response(200,json={**app,'as_of':'2020-01-01T00:00:00Z'})
    async def exercise():
        engine=HealthEngine(store,httpx.AsyncClient(transport=httpx.MockTransport(handler)),Providers())
        await engine.cycle();nodes={n['id']:n for n in engine.state()['nodes']}
        assert nodes['application']['status']=='down'
        assert nodes['broker']['status']=='unknown' and nodes['model']['status']=='unknown'
        await engine.close()
    asyncio.run(exercise());store.close()


def test_local_health_inputs_are_small_read_only_and_do_not_export_account_data(tmp_path):
    from fastapi.testclient import TestClient
    from backend.app import create_app
    from backend.config import Settings
    cfg=Settings(mode='simulator',db_path=tmp_path/'inputs.sqlite')
    app=create_app(cfg,background=False)
    with TestClient(app,base_url='http://127.0.0.1') as client:
        engine=app.state.engine
        before=engine.store.rows('SELECT COUNT(*) n FROM events')[0]['n']
        response=client.get('/api/health-inputs');assert response.status_code==200
        d=response.json();assert 'workers' in d and 'model_enabled' in d
        assert not any(k in d for k in ('account','cash','equity','api_key','secret_key','orders','fills'))
        assert response.headers['cache-control']=='no-store'
        assert engine.store.rows('SELECT COUNT(*) n FROM events')[0]['n']==before
