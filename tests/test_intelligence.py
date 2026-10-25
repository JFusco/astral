import asyncio
from datetime import datetime, timezone, timedelta
import json

import httpx
import pytest

from backend.intelligence import Collector, SOURCES, MAX_BYTES, parse
from backend.store import Store


RSS = b'''<rss><channel><item><guid>one</guid><title>Bitcoin &amp; context</title><link>https://example.com/a</link><pubDate>Sat, 24 Oct 2026 12:00:00 GMT</pubDate></item></channel></rss>'''


def test_untrusted_xml_and_unsafe_links():
    for body in (b'<!DOCTYPE rss [<!ENTITY e "boom">]><rss/>', b'<!DOCTYPE rss><rss/>'.decode().encode('utf-16'), b'<html/>', b'x'*(MAX_BYTES+1)):
        with pytest.raises(ValueError): parse(SOURCES[0], body)
    with pytest.raises(ValueError):
        parse(SOURCES[0], RSS.replace(b'https://example.com/a', b'javascript:alert(1)'))
    assert parse(SOURCES[0], RSS)[0]['headline'] == 'Bitcoin & context'


def test_atom_missing_dates_never_become_now():
    body = b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>x</id><title>Notice</title><link href="https://example.com/x"/><updated>2026-10-25T01:00:00Z</updated></entry></feed>'
    item = parse(SOURCES[0], body)[0]
    assert item['created_at'] is None
    assert item['updated_at'] == '2026-10-25T01:00:00+00:00'


def test_status_keeps_component_failure_and_maintenance():
    body = json.dumps({'status':{'description':'Degraded','indicator':'minor'}, 'page':{},
                       'components':[{'name':'Trading','status':'major_outage'}],
                       'scheduled_maintenances':[{'id':'m','name':'Upgrade','scheduled_for':'2026-10-26T01:00:00Z'}]}).encode()
    rows = parse(next(s for s in SOURCES if s.kind == 'status'), body)
    assert rows[0]['created_at'] is None
    assert rows[0]['components'][0]['status'] == 'major_outage'
    assert rows[1]['scheduled_for'] == '2026-10-26T01:00:00+00:00'


def test_dedup_revisions_conditionals_backoff_and_stale(tmp_path):
    store = Store(tmp_path/'intel.sqlite', 'public-intelligence')
    source = SOURCES[0]
    calls = []
    bodies = [RSS, RSS, RSS.replace(b'Bitcoin &amp; context', b'Revised headline')]
    def transport(request):
        calls.append(request)
        if len(calls) <= 3: return httpx.Response(200, content=bodies[len(calls)-1], headers={'etag':'abc'})
        if len(calls) == 4: return httpx.Response(304)
        return httpx.Response(429, headers={'retry-after':'3600'})
    async def exercise():
        c = Collector(store, httpx.AsyncClient(transport=httpx.MockTransport(transport)), sources=(source,))
        await c.poll(force=True)
        first = c.state()['items'][0]
        await c.poll(force=True)
        assert c.state()['items'][0]['first_seen_at'] == first['first_seen_at']
        assert len(store.rows('SELECT * FROM intelligence')) == 1
        await c.poll(force=True)
        assert len(store.rows('SELECT * FROM intelligence')) == 2
        assert c.state()['items'][0]['headline'] == 'Revised headline'
        assert calls[-1].headers['if-none-match'] == 'abc'
        await c.poll(force=True)
        assert c.state()['sources'][0]['status'] == 'connected'
        await c.poll(force=True)
        health = store.get('source:fed')
        assert health['next_attempt_epoch'] >= datetime.now(timezone.utc).timestamp()+3590
        assert c.state()['sources'][0]['status'] == 'error'
        await c.poll()
        assert len(calls) == 5
        assert c.state()['items'][0]['headline'] == 'Revised headline'
        health.update(status='connected',last_success_at=(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat())
        store.put('source:fed',health)
        assert c.state()['sources'][0]['status'] == 'stale'
        assert c.state()['execution_enabled'] is False
        await c.close()
    asyncio.run(exercise())
    store.close()


def test_contact_and_access_denial_do_not_leak_or_retry(tmp_path):
    store = Store(tmp_path/'intel.sqlite', 'public-intelligence')
    source = next(s for s in SOURCES if s.requires_contact)
    calls = []
    def transport(request):
        calls.append(request)
        return httpx.Response(403)
    async def exercise():
        c = Collector(store,httpx.AsyncClient(transport=httpx.MockTransport(transport)),sources=(source,))
        await c.poll()
        assert not calls
        assert c.state()['sources'][0]['status'] == 'needs-contact'
        c.contact = 'contact@example.com'
        await c.poll()
        await c.poll()
        assert len(calls) == 1
        assert 'contact@example.com' in calls[0].headers['user-agent']
        assert 'contact@example.com' not in json.dumps(c.state())
        assert c.state()['sources'][0]['http_status'] == 403
        await c.close()
    asyncio.run(exercise())
    store.close()


def test_oversized_response_and_redirect_stay_failed(tmp_path):
    store = Store(tmp_path/'intel.sqlite', 'public-intelligence')
    async def exercise():
        for response in (httpx.Response(200,content=b'x'*(MAX_BYTES+1)),httpx.Response(302,headers={'location':'http://127.0.0.1/private'})):
            c = Collector(store,httpx.AsyncClient(transport=httpx.MockTransport(lambda _:response)),sources=(SOURCES[0],))
            await c.poll(force=True)
            assert c.state()['sources'][0]['status'] == 'error'
            assert not c.state()['items']
            await c.close()
    asyncio.run(exercise())
    store.close()


def test_publisher_reversion_restores_current_content(tmp_path):
    store = Store(tmp_path/'intel.sqlite', 'public-intelligence')
    responses = iter([RSS, RSS.replace(b'Bitcoin &amp; context',b'Revised'), RSS])
    async def exercise():
        c = Collector(store,httpx.AsyncClient(transport=httpx.MockTransport(lambda _:httpx.Response(200,content=next(responses)))),sources=(SOURCES[0],))
        await c.poll(force=True)
        await c.poll(force=True)
        assert c.state()['items'][0]['headline'] == 'Revised'
        await c.poll(force=True)
        assert c.state()['items'][0]['headline'] == 'Bitcoin & context'
        assert len(store.rows('SELECT * FROM intelligence')) == 2
        await c.close()
    asyncio.run(exercise())
    store.close()


@pytest.mark.parametrize('failure', ['parser','write','error-write'])
def test_unexpected_source_failure_keeps_other_feed_alive_and_recovers(tmp_path, monkeypatch, failure):
    import sqlite3
    import backend.intelligence as module
    store=Store(tmp_path/'resilient.sqlite','public-intelligence')
    sources=(SOURCES[0],SOURCES[2]);bad=sources[0]
    calls=[];fail=[False]
    def handler(request):
        calls.append(request)
        return httpx.Response(200,content=RSS)
    original_parse=module.parse;original_put=store.put
    def parse(source,body):
        if fail[0] and source.id==bad.id and failure=='parser':raise AttributeError('Fixture malformed parser field')
        return original_parse(source,body)
    def put(key,value):
        if fail[0] and key=='source:'+bad.id:
            if failure=='error-write' or (failure=='write' and value.get('status')=='connected'):
                raise sqlite3.OperationalError('Fixture locked disk')
        return original_put(key,value)
    monkeypatch.setattr(module,'parse',parse);monkeypatch.setattr(store,'put',put)
    async def exercise():
        c=Collector(store,httpx.AsyncClient(transport=httpx.MockTransport(handler)),sources=sources)
        await c.poll(force=True)
        previous=store.get('source:'+bad.id)['last_success_at']
        fail[0]=True;await c.poll(force=True)
        by_id={s['id']:s for s in c.state()['sources']}
        assert by_id[sources[1].id]['status']=='connected'
        assert by_id[bad.id]['status']=='error'
        assert by_id[bad.id]['next_attempt_epoch']>datetime.now(timezone.utc).timestamp()
        assert by_id[bad.id]['last_success_at']==previous
        if failure=='error-write':
            assert by_id[bad.id]['health_persisted'] is False
            assert store.get('source:'+bad.id)['last_success_at']==previous
        else:assert store.get('source:'+bad.id)['status']=='error'
        before=len(calls);await c.poll();assert len(calls)==before
        fail[0]=False;await c.poll(force=True)
        assert len(calls)==before+2
        assert all(s['status']=='connected' for s in c.state()['sources'])
        assert not c.unsaved_health
        await c.close()
    asyncio.run(exercise());store.close()


def test_collection_loop_delays_after_failure_continues_and_propagates_cancel(monkeypatch):
    from backend.intelligence_app import collect
    events=[]
    class FixtureCollector:
        async def poll(self):
            events.append('poll')
            if events.count('poll')==1:raise RuntimeError('Fixture poll failure')
    async def sleep(delay):
        events.append(delay)
        if events.count('poll')==2:raise asyncio.CancelledError()
    monkeypatch.setattr('backend.intelligence_app.asyncio.sleep',sleep)
    with pytest.raises(asyncio.CancelledError):asyncio.run(collect(FixtureCollector()))
    assert events==['poll',30,'poll',30]


def test_collector_fetch_propagates_cancellation(tmp_path):
    store=Store(tmp_path/'cancel.sqlite','public-intelligence')
    async def handler(request):raise asyncio.CancelledError()
    async def exercise():
        c=Collector(store,httpx.AsyncClient(transport=httpx.MockTransport(handler)),sources=(SOURCES[0],))
        with pytest.raises(asyncio.CancelledError):await c.poll(force=True)
        assert not store.get('source:'+SOURCES[0].id)
        await c.close()
    asyncio.run(exercise());store.close()
