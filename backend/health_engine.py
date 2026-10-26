"""Independent assessments from telemetry observations; no trading authority."""
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import time

import httpx

from .service_health import HealthMonitor, moment
from .store import utcnow

LOCAL = {'application':os.getenv('ASTRAL_HEALTH_APPLICATION_ORIGIN', 'http://127.0.0.1:8766').rstrip('/')+'/api/health-inputs',
         'collector':os.getenv('ASTRAL_HEALTH_COLLECTOR_ORIGIN', 'http://127.0.0.1:8768').rstrip('/')+'/api/health-inputs'}
WORKER_TTL = {'quotes':30, 'reconciliation':45, 'fees':300, 'news':600,
              'research':1800, 'portfolio_replay':1800, 'event_context':180,
              'liquidity_experiment':90, 'exit_monitor':30, 'shadow':180}
# Written only when an order/cancel happens; no heartbeat, so age is not a fault.
EVENT_DRIVEN = {'execution'}
SYMBOLS = ('BTC','ETH','SOL','SPY','QQQ','GLD','TLT','IWM')


def fresh(at, seconds, now):
    try:
        return 0 <= (now-moment(at)).total_seconds() <= seconds
    except (ValueError, TypeError, AttributeError):
        return False


class HealthEngine:
    def __init__(self, store, client=None, providers=None):
        self.store = store
        self.client = client or httpx.AsyncClient(timeout=5, follow_redirects=False, trust_env=False)
        self.providers = providers or HealthMonitor(store)
        self.last_error = None
        self.started = time.monotonic()
        self.storage_path = Path(store.db.execute('PRAGMA database_list').fetchone()[2]).parent

    async def close(self):
        await self.client.aclose()
        await self.providers.close()

    async def read(self, url):
        body = bytearray()
        async with self.client.stream('GET', url) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes():
                body.extend(chunk)
                if len(body) > 300_000:
                    raise ValueError('Health inputs exceed budget')
        result = json.loads(body)
        if not isinstance(result, dict):
            raise ValueError('Invalid health inputs')
        if not fresh(result.get('as_of'), 30, datetime.now(timezone.utc)):
            raise ValueError('Health input timestamp is stale or invalid')
        return result

    async def cycle(self):
        start = time.monotonic()
        previous = self.store.get('health-snapshot', {})
        nodes = []
        now = datetime.now(timezone.utc)

        def add(id, name, group, status, detail, checked_at=None, required=True):
            nodes.append({'id':id, 'name':name, 'group':group, 'status':status,
                          'detail':detail, 'checked_at':checked_at or now.isoformat(), 'required':required})

        # Local observations are assessed without importing their engines or DBs.
        results = await asyncio.gather(*(self.read(url) for url in LOCAL.values()), return_exceptions=True)
        app, collector = [r if isinstance(r,dict) else None for r in results]
        add('application','Application API','core','healthy' if app else 'down',
            'Read-only health inputs received' if app else 'Application health inputs unavailable')
        add('collector','Intelligence collector','core','healthy' if collector else 'down',
            'Source health inputs received' if collector else 'Collector health inputs unavailable')
        if app:
            connected = app.get('connected') is True and fresh(app.get('snapshot_at'),45,now)
            add('broker','Paper broker readback','execution','healthy' if connected else 'degraded',
                'Recent account/order readback; no execution test' if connected else 'Account readback missing, stale or disconnected',app.get('snapshot_at'))
            for symbol in SYMBOLS:
                q = app.get('quotes',{}).get(symbol,{})
                closed = symbol not in ('BTC','ETH','SOL') and app.get('session_open') is False
                good = fresh(q.get('at'),30,now) and fresh(q.get('received_at'),30,now)
                add('quote:'+symbol,symbol+' quotes','market','inactive' if closed else 'healthy' if good else 'degraded',
                    'ETF session closed; no fresh quote required' if closed else 'Source and arrival times fresh' if good else 'Quote source or arrival time unavailable/stale',q.get('received_at'),not closed)
            seen_workers = set()
            for w in app.get('workers',[]):
                name = w.get('name')
                if not isinstance(name,str):
                    continue
                seen_workers.add(name)
                status = w.get('status')
                disabled = status == 'disabled'
                ttl = WORKER_TTL.get(name,45)
                observed_at = app.get('ledger_at') if name=='ledger' else w.get('at')
                good = status in ('healthy','recording') and (name in EVENT_DRIVEN or fresh(observed_at,ttl,now))
                assessed = 'inactive' if disabled else 'healthy' if good else 'degraded'
                detail = 'Disabled by server configuration' if disabled else 'Worker observation: '+str(status)
                if name == 'learning' and status == 'recording':
                    assessed = 'inactive'
                    detail = 'Dataset recording only; trained learning and promotion are not enabled'
                if status in ('running','waiting') and fresh(w.get('at'),ttl,now):
                    assessed = 'checking'
                add('worker:'+name,name.replace('_',' ').title(),'workers',assessed,
                    detail,observed_at,assessed!='inactive')
            for name in ('quotes','reconciliation'):
                if name not in seen_workers:
                    add('worker:'+name,name.title(),'workers','unknown','No worker observation received')
            model = app.get('model',{})
            enabled = app.get('model_enabled') is True
            status = 'inactive' if not enabled else 'unknown'
            detail = 'Disabled by server configuration; no paid health probe'
            if enabled:
                recent = fresh(model.get('at'),21600,now)
                status = 'healthy' if recent and model.get('status') == 'reviewed' else 'degraded' if recent else 'unknown'
                detail = 'Last recorded model call: '+str(model.get('status') or 'none')+'; no active model/quota probe'
            add('model','Research model / Codex','models',status,detail,model.get('at'),enabled)
        else:
            for id,name,group in [('broker','Paper broker readback','execution'),('model','Research model / Codex','models'),
                                  *[('quote:'+s,s+' quotes','market') for s in SYMBOLS],
                                  *[('worker:'+w,w.title(),'workers') for w in ('quotes','reconciliation')]]:
                add(id,name,group,'unknown','Application observations unavailable')
            present = {n['id'] for n in nodes}
            for prior in previous.get('nodes',[]):
                if prior['group']=='workers' and prior['id'] not in present:
                    add(prior['id'],prior['name'],'workers','unknown','Application observations unavailable',prior.get('checked_at'))
        if collector:
            sources = collector.get('sources')
            if not isinstance(sources,list) or not sources:
                raise ValueError('Collector supplied no source inventory')
            for source in sources:
                interval = source.get('interval_seconds',300)
                good = source.get('status') == 'connected' and source.get('fresh') is True and fresh(source.get('last_success_at'),max(600,interval*3),now)
                add('source:'+source['id'],source['name'],'sources','healthy' if good else 'degraded',
                    'Published feed fetched / revalidated' if good else 'Feed unavailable, stale or not configured',source.get('last_success_at'))
            alpaca = collector.get('alpaca',{})
            good = alpaca.get('fetch_status') == 'connected' and fresh(alpaca.get('last_success_at'),360,now)
            reported = alpaca.get('report',{}).get('status') if good else 'unknown'
            add('provider:alpaca','Alpaca published status','providers','healthy' if reported=='operational' else 'degraded' if reported=='incident' else 'unknown',
                alpaca.get('report',{}).get('description','Published report unavailable'),alpaca.get('last_success_at'))
        else:
            for prior in previous.get('nodes',[]):
                if prior['group']=='sources':
                    add(prior['id'],prior['name'],'sources','unknown','Collector unavailable; last source observation cannot establish current health')
            add('provider:alpaca','Alpaca published status','providers','unknown','Collector unavailable')
        # Keep provider polling independent of the local heartbeat. It runs in
        # a separate task so a slow public status endpoint cannot stall checks.
        for p in self.providers.state()['providers']:
            reported = p['status']
            add('provider:'+p['id'],p['name']+' published status','providers',
                'healthy' if reported=='operational' else 'degraded' if reported=='incident' else 'unknown',
                (p.get('report',{}).get('description','No validated report') if reported!='unknown' else 'Status report unavailable or stale')+'. '+p['scope'],p.get('last_success_at'))
        add('runtime:docker','Docker runtime','local','unknown','Runtime daemon has not been probed; executable '+('found' if shutil.which('docker') else 'not on service PATH'),required=False)
        add('runtime:lean','Local LEAN evaluation','local','inactive','Separate evaluation; engine/entitlement not verified by this health engine',required=False)
        add('feature:quantconnect-account','QuantConnect account / checkout','providers','unknown',
            'No authenticated payment or entitlement probe; public operational status cannot clear the reported checkout issue',required=False)
        disk = shutil.disk_usage(self.storage_path)
        disk_status = 'down' if disk.free < 1024**3 else 'degraded' if disk.free < 5*1024**3 else 'healthy'
        add('runtime:disk','Local disk capacity','local',disk_status,
            f'{disk.free/1024**3:.1f} GiB available; warns below 5 GiB, critical below 1 GiB')
        add('runtime:storage','Health evidence storage','core','healthy','Snapshot persisted to the separate health ledger')
        current = {n['id']:n for n in nodes}
        old = {n['id']:n for n in previous.get('nodes',[])}
        transitions = [{'id':n['id'],'name':n['name'],'previous':old[n['id']]['status'] if n['id'] in old else 'unseen',
                        'status':n['status']} for n in nodes if old.get(n['id'],{}).get('status') != n['status'] and (n['id'] in old or n['status'] in ('down','degraded'))]
        snapshot = {'checked_at':utcnow(),'sequence':previous.get('sequence',0)+1, 'nodes':list(current.values()),
                    'duration_ms':round((time.monotonic()-start)*1000), 'execution_enabled':False}
        with self.store.transaction():
            self.store.put('health-snapshot',snapshot)
            for change in transitions:
                self.store.event('health_transition',change)
        self.last_error = None

    async def run(self):
        while True:
            try:
                await self.cycle()
            except Exception:
                self.last_error = 'Assessment or storage failed; retained results are not a current healthy check'
            await asyncio.sleep(10)

    def state(self):
        now = datetime.now(timezone.utc)
        snapshot = self.store.get('health-snapshot',{})
        live = not self.last_error and fresh(snapshot.get('checked_at'),30,now)
        nodes = snapshot.get('nodes',[])
        if not live:
            nodes = [{**n,'last_status':n['status'],'status':'unknown','detail':'Health-engine heartbeat missed; retained observation only'} for n in nodes]
        counts = {s:sum(n['status']==s for n in nodes) for s in ('healthy','degraded','down','unknown','inactive','checking')}
        changes = self.store.rows("SELECT seq,at,payload FROM events WHERE type='health_transition' ORDER BY seq DESC LIMIT 20")
        return {**snapshot,'as_of':now.isoformat(),'heartbeat_live':live,'nodes':nodes,'counts':counts,
                'uptime_seconds':int(time.monotonic()-self.started),
                'error':self.last_error,'changes':[{**r,'payload':json.loads(r['payload'])} for r in changes],
                'check_interval_seconds':10,'heartbeat_timeout_seconds':30,'provider_interval_seconds':120,
                'external_notifications_enabled':False,'execution_enabled':False,
                'scope':'Independent health assessments; telemetry is input, health never authorizes trading'}
