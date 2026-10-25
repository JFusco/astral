from calendar import monthrange
from copy import deepcopy
from datetime import datetime,timedelta,timezone
import asyncio
import json

import httpx
import pytest

from backend.event_sources import nyfed,maintenance,protocol,MAINTENANCE,NYFED
from backend.intelligence import Collector,SOURCES
from backend.calendar_evidence import retain_scopes
from backend.readiness import calendar_coverage
from backend.public_context import evidence_for
from backend.store import Store

NOW=datetime(2026,10,25,12,tzinfo=timezone.utc)


def calendar_html(month=10,year=2026):
    rows=[]
    for d in range(1,monthrange(year,month)[1]+1):
        if datetime(year,month,d).weekday()>4:continue
        link='<a href="https://www.bls.gov/news.release/cpi.toc.htm">CPI</a><br />(08:30)' if d==(14 if month==10 else 13) else ''
        rows.append(f'<tr><td><div>{d:02d}<br />{link}</div></td></tr>')
    return ('all Eastern Time<td class="ts-data-table-head">'+datetime(year,month,1).strftime('%B %Y')+'</td><table class="research-table-1col">'+''.join(rows)+'</table>').encode()


def test_nyfed_preserves_timezone_and_series_scope_not_full_bls():
    events,scope=nyfed(calendar_html())
    assert events[0]['event_start']=='2026-10-14T08:30:00-04:00'
    events,_=nyfed(calendar_html(11))
    assert events[0]['event_start']=='2026-11-13T08:30:00-05:00'
    assert not scope['complete_category']


def test_nyfed_missing_time_days_or_timezone_fail():
    for body in (calendar_html().replace(b'(08:30)',b'TBD'),calendar_html().replace(b'01<br',b'02<br'),calendar_html().replace(b'all Eastern Time',b'local time')):
        with pytest.raises(ValueError):nyfed(body)
    events,scope=nyfed(calendar_html())
    assert not scope['complete_category'] and scope['coverage_until'].startswith('2026-11-01')
    assert events[0]['originating_url'].startswith('https://www.bls.gov/')


def maintenance_body(items=()):
    return json.dumps({'page':{'id':'bf49n9xp9x2w','url':'https://status.alpaca.markets'},'scheduled_maintenances':list(items)}).encode()


def test_empty_maintenance_is_valid_only_with_full_schema_and_correct_publisher():
    assert maintenance(maintenance_body(),False)==[]
    for body in (b'{}',b'{"page":{},"scheduled_maintenances":[]}',maintenance_body().replace(b'bf49n9xp9x2w',b'other')):
        with pytest.raises((ValueError,KeyError)):maintenance(body,False)
    item={'id':'m','name':'Trade outage','status':'in_progress','scheduled_for':'2026-10-25T10:00:00Z','scheduled_until':'2026-10-25T11:00:00Z'}
    assert maintenance(maintenance_body([item]),True)[0]['maintenance_status']=='in_progress'
    with pytest.raises(ValueError):maintenance(maintenance_body([item]),False)
    with pytest.raises(ValueError):maintenance(maintenance_body([item,item]),True)


def context():
    catalogs=[];sources=[]
    for suffix in ('upcoming','active'):
        identity='alpaca-maint-'+suffix;url=MAINTENANCE+suffix+'.json'
        sources.append({'id':identity,'status':'connected','fresh':True})
        catalogs.append({'source_id':identity,'source_url':url,'checked_at':NOW.isoformat(),'retained_body_sha256':'a'*64,'events':[],
                         'coverage_from':NOW.isoformat(),'coverage_until':(NOW+timedelta(hours=48)).isoformat()})
    return {'status':'available','as_of':NOW.isoformat(),'sources':sources,'calendar_catalogs':catalogs,'items':[]}


def test_two_maintenance_endpoints_required_and_later_failure_revokes_scope(tmp_path):
    store=Store(tmp_path/'calendar.sqlite','public-intelligence');ctx=context()
    retain_scopes(store,ctx,NOW.isoformat())
    saved=store.get('event_calendars')['BTC'];assert saved['categories']['venue-maintenance']['status']=='verified'
    proofs={r['sha256']:json.loads(r['payload']) for r in store.rows('SELECT * FROM event_calendar_evidence')}
    assert 'venue-maintenance' not in calendar_coverage(saved,'BTC',NOW,proofs)['missing_categories']
    assert 'venue-maintenance' in calendar_coverage(saved,'BTC',NOW+timedelta(minutes=6),proofs)['missing_categories']
    ctx['sources'][1]['status']='error';ctx['calendar_catalogs']=ctx['calendar_catalogs'][:1]
    retain_scopes(store,ctx,(NOW+timedelta(minutes=1)).isoformat())
    assert store.get('event_calendars')['BTC']['categories']['venue-maintenance']['status']=='unavailable'
    assert len(store.rows('SELECT * FROM event_calendar_evidence'))==3
    store.close()


def test_active_overrun_and_catalog_event_hidden_by_ui_cap_still_veto():
    ctx=context();ctx['calendar_catalogs'][1]['events']=[{'event_start':'2026-10-25T10:00:00Z','event_end_exclusive':'2026-10-25T11:00:00Z',
        'maintenance_status':'in_progress','headline':'Still active'}]
    _,vetoes,_=evidence_for('BTC',ctx,NOW.isoformat())
    assert any('scheduled end does not establish recovery' in v for v in vetoes)
    ctx['calendar_catalogs'][1]['events'][0].update(maintenance_status='scheduled')
    _,vetoes,_=evidence_for('BTC',ctx,NOW.isoformat())
    assert any('overdue' in v for v in vetoes)


def test_bip_blank_layers_retained_and_status_does_not_create_event_date():
    body=('does not indicate consensus\n{| class="wikitable sortable"\n'+''.join(
        f'|-\n| [[bip-{i:04d}.mediawiki|{i}]]\n|\n| Title {i}\n| Author\n| Specification\n| Draft\n' for i in range(1,101))).encode()
    rows=protocol(body,'bips');assert len(rows[0]['protocol_rows'])==100
    assert not rows[0]['coverage_complete'] and 'event_start' not in rows[0]
    with pytest.raises(ValueError):protocol(body.replace(b'| Draft',b'| Draft\n| extra',1),'bips')


def test_maintenance_empty_snapshot_304_extends_inspection_not_publication(tmp_path):
    s=next(s for s in SOURCES if s.id=='alpaca-maint-upcoming');store=Store(tmp_path/'intel.sqlite','public-intelligence')
    calls=[]
    def handler(request):
        calls.append(request)
        return httpx.Response(200,content=maintenance_body(),headers={'etag':'v1'}) if len(calls)==1 else httpx.Response(304)
    async def exercise():
        c=Collector(store,httpx.AsyncClient(transport=httpx.MockTransport(handler)),sources=(s,))
        await c.poll(force=True);before=store.get('calendar_catalog:'+s.id);first=c.state()['items'][0]
        assert before['events']==[] and first['created_at'] is None and first['schedule_empty']
        await c.poll(force=True);after=store.get('calendar_catalog:'+s.id)
        assert after['checked_at']>=before['checked_at'] and after['coverage_until']>=before['coverage_until']
        assert c.state()['items'][0]['first_seen_at']==first['first_seen_at']
        assert calls[-1].headers['if-none-match']=='v1'
        await c.close()
    asyncio.run(exercise());store.close()


@pytest.mark.parametrize('identity', ['fomc-calendar','bea-calendar'])
@pytest.mark.parametrize('health', ['fresh','stale','error','wrong-url','past'])
def test_complete_official_calendar_vetoes_event_hidden_by_headline_sample(identity, health):
    from backend.calendar_context import FOMC_URL
    from backend.bea_calendar import URL as BEA_URL
    ctx=context();url=FOMC_URL if identity=='fomc-calendar' else BEA_URL
    source={'id':identity,'status':'error' if health=='error' else 'connected','fresh':health!='stale'}
    ctx['sources'].append(source)
    future=(NOW+timedelta(days=10)).isoformat()
    ctx['items']=[{'id':'far-future','revision':'fixture','source':'Official fixture','source_id':identity,
                   'category':'macro-calendar','first_seen_at':NOW.isoformat(),'headline':'Far future sample',
                   'event_start':future,'event_end_exclusive':(NOW+timedelta(days=11)).isoformat()}]
    delta=timedelta(days=-2) if health=='past' else timedelta(hours=2)
    ctx['calendar_catalogs'].append({'source_id':identity,'source_url':url if health!='wrong-url' else 'https://wrong.test',
        'events':[{'event_start':(NOW+delta).isoformat(),'event_end_exclusive':(NOW+delta+timedelta(hours=1)).isoformat(),
                   'headline':'Hidden near-term release'}]})
    _,vetoes,_=evidence_for('BTC',ctx,NOW.isoformat())
    assert any('Hidden near-term release' in v for v in vetoes) == (health=='fresh')


def test_active_to_empty_maintenance_snapshot_survives_restart_and_304(tmp_path):
    from backend.store import utcnow
    sources=tuple(s for s in SOURCES if s.id in {'alpaca-maint-upcoming','alpaca-maint-active'})
    store=Store(tmp_path/'transition.sqlite','public-intelligence')
    now=datetime.now(timezone.utc)
    item={'id':'m','name':'Fixture active overrun','status':'in_progress',
          'scheduled_for':(now-timedelta(hours=2)).isoformat(),
          'scheduled_until':(now-timedelta(hours=1)).isoformat()}
    phase=['active'];requests=[]
    def handler(request):
        requests.append(request)
        if phase[0]=='304':return httpx.Response(304)
        active=phase[0]=='active' and request.url.path.endswith('active.json')
        return httpx.Response(200,content=maintenance_body([item] if active else []),headers={'etag':phase[0]})
    async def exercise():
        c=Collector(store,httpx.AsyncClient(transport=httpx.MockTransport(handler)),sources=sources)
        await c.poll(force=True)
        ctx={'status':'available',**c.state()}
        assert any('scheduled end does not establish recovery' in v for v in evidence_for('BTC',ctx,utcnow())[1])
        phase[0]='empty';await c.poll(force=True)
        ctx={'status':'available',**c.state()}
        assert not evidence_for('BTC',ctx,utcnow())[1]
        assert any(i.get('maintenance_status')=='in_progress' for i in ctx['items'])
        retained=store.rows('SELECT * FROM intelligence')
        await c.close()
        c=Collector(store,httpx.AsyncClient(transport=httpx.MockTransport(handler)),sources=sources)
        phase[0]='304';await c.poll(force=True)
        ctx={'status':'available',**c.state()}
        assert not evidence_for('BTC',ctx,utcnow())[1]
        assert store.rows('SELECT * FROM intelligence') == retained
        assert requests[-1].headers['if-none-match']=='empty'
        retain_scopes(store,ctx,utcnow())
        assert store.get('event_calendars')['BTC']['categories']['venue-maintenance']['status']=='verified'
        for failure in ('stale','error','missing'):
            broken=deepcopy(ctx)
            if failure=='missing':broken['sources']=[]
            elif failure=='stale':broken['sources'][0]['fresh']=False
            else:broken['sources'][0]['status']='error'
            retain_scopes(store,broken,utcnow())
            assert store.get('event_calendars')['BTC']['categories']['venue-maintenance']['status']=='unavailable'
        await c.close()
    asyncio.run(exercise());store.close()
