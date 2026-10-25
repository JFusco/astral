"""Public provider reports, separate from account/model connectivity and risk.

No credential, broker, model, strategy or execution imports. Alpaca reuses the
existing intelligence collector. Only two fixed public GET endpoints are added.
"""
import asyncio
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
import hashlib
from html.parser import HTMLParser
import json
import math
import time

import httpx

from .store import utcnow

INTERVAL = 120
TTL = 360
MAX_BYTES = 1_000_000
PROVIDERS = {
    "quantconnect": {"name":"QuantConnect", "url":"https://status.quantconnect.com/",
                     "scope":"Published aggregate status; checkout, subscription and local LEAN access are not verified"},
    "openai": {"name":"OpenAI / Codex", "url":"https://status.openai.com/api/v2/summary.json",
               "scope":"Published provider/component status; ASTRAL's signed-in CLI, model access and quota are not verified"},
}


def moment(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Timezone required')
    return parsed.astimezone(timezone.utc)


class StatusHeading(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_heading = False
        self.headings = []

    def handle_starttag(self, tag, attrs):
        if tag == 'h1':
            self.in_heading = True
            self.headings.append('')

    def handle_endtag(self, tag):
        if tag == 'h1':
            self.in_heading = False

    def handle_data(self, value):
        if self.in_heading:
            self.headings[-1] += value


def parse_report(provider, body):
    if len(body) > MAX_BYTES:
        raise ValueError('Status response too large')
    if provider == 'quantconnect':
        parser = StatusHeading()
        parser.feed(body.decode('utf-8'))
        headings = [' '.join(h.split()) for h in parser.headings]
        recognized = {'All services are online':'operational',
                      'Some services are down':'incident',
                      'Some services are degraded':'incident',
                      'All services are down':'incident'}
        if len(headings) != 1 or headings[0] not in recognized:
            raise ValueError('Unrecognized QuantConnect status heading')
        return {'status':recognized[headings[0]], 'description':headings[0],
                'components':[], 'incidents':[], 'source_updated_at':None}
    raw = json.loads(body)
    indicator = raw['status']['indicator']
    if indicator not in {'none','minor','major','critical','maintenance'}:
        raise ValueError('Unknown provider status indicator')
    description = raw['status']['description']
    components = raw.get('components')
    if not isinstance(description, str) or not description.strip() or not isinstance(components, list) or not components:
        raise ValueError('Status snapshot lacks component coverage')
    statuses = {'operational','degraded_performance','partial_outage','major_outage','under_maintenance'}
    normalized = []
    for component in components:
        if not isinstance(component, dict) or not isinstance(component.get('name'), str) or component.get('status') not in statuses:
            raise ValueError('Invalid component status')
        normalized.append({'name':component['name'][:150], 'status':component['status']})
    incidents = raw.get('incidents', [])
    if not isinstance(incidents, list):
        raise ValueError('Invalid incident list')
    active = []
    for incident in incidents:
        if not isinstance(incident, dict) or not isinstance(incident.get('status'), str):
            raise ValueError('Invalid incident')
        if incident['status'] not in {'resolved','postmortem'}:
            active.append({'name':str(incident.get('name','Published incident'))[:200], 'status':incident['status'][:40]})
    problem = indicator != 'none' or active or any(c['status'] != 'operational' for c in normalized)
    return {'status':'incident' if problem else 'operational', 'description':description[:300],
            'components':normalized[:150], 'incidents':active[:40],
            'source_updated_at':raw.get('page', {}).get('updated_at')}


def effective(record, now):
    try:
        age = (now-moment(record['last_success_at'])).total_seconds()
        fresh = 0 <= age <= TTL
    except (KeyError, ValueError, TypeError, AttributeError):
        fresh = False
    valid = fresh and record.get('fetch_status') == 'connected'
    return {**record, 'fresh':fresh, 'status':record.get('report',{}).get('status','unknown') if valid else 'unknown'}


class HealthMonitor:
    def __init__(self, store, client=None):
        self.store = store
        self.client = client or httpx.AsyncClient(timeout=10, follow_redirects=False, trust_env=False)
        self.unsaved = {}

    async def close(self):
        await self.client.aclose()

    def record(self, provider):
        return self.unsaved.get(provider) or self.store.get('service-health:'+provider, {})

    def save(self, provider, value):
        prior = self.record(provider)
        now = datetime.now(timezone.utc)
        old = effective(prior, now)['status']
        new = effective(value, now)['status']
        # Checked-at/body hashes change on each fetch; they must not spam alerts.
        material = lambda r: {k:r.get('report',{}).get(k) for k in ('status','description','components','incidents')}
        changed = old != new or (new == 'incident' and material(prior) != material(value))
        try:
            with self.store.transaction():
                self.store.put('service-health:'+provider, value)
                if changed and (prior or new == 'incident'):
                    self.store.event('service_health_change', {'provider':provider, 'previous':old, 'status':new,
                                     'description':value.get('report',{}).get('description') if new != 'unknown' else value.get('error','Status unavailable')})
        except Exception:
            self.unsaved[provider] = {**value, 'persisted':False}
        else:
            self.unsaved.pop(provider, None)

    async def poll(self):
        for provider, source in PROVIDERS.items():
            prior = self.record(provider)
            now = datetime.now(timezone.utc)
            if now.timestamp() < prior.get('next_attempt_epoch', 0):
                continue
            started = time.monotonic()
            value = {**prior, 'checked_at':now.isoformat(), 'http_status':None}
            retry_after = None
            try:
                async with self.client.stream('GET', source['url'], headers={'User-Agent':'ASTRAL-Service-Health/1.0', 'Accept':'application/json,text/html'}) as response:
                    value['http_status'] = response.status_code
                    retry_after = response.headers.get('retry-after')
                    response.raise_for_status()
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > MAX_BYTES:
                            raise ValueError('Status response too large')
                report = parse_report(provider, bytes(body))
                value.update(report=report, body_sha256=hashlib.sha256(body).hexdigest(),
                             last_success_at=utcnow(), fetch_status='connected', error=None, failures=0,
                             next_attempt_epoch=now.timestamp()+INTERVAL)
            except Exception:
                failures = prior.get('failures',0)+1
                delay = min(INTERVAL*2**min(failures,4), 1800)
                if value['http_status'] == 429 and retry_after:
                    try:
                        seconds = float(retry_after)
                    except ValueError:
                        try:
                            seconds = (parsedate_to_datetime(retry_after)-now).total_seconds()
                        except (ValueError, TypeError, OverflowError):
                            seconds = 0
                    if math.isfinite(seconds):
                        delay = max(delay, max(seconds,0))
                value.update(fetch_status='error', error='Public status fetch or validation failed; last report retained as historical evidence',
                             failures=failures, next_attempt_epoch=now.timestamp()+delay)
            value['latency_ms'] = round((time.monotonic()-started)*1000)
            self.save(provider, value)

    async def run(self):
        while True:
            try:
                await self.poll()
            except Exception:
                # A storage fault must not silently terminate the optional worker.
                pass
            await asyncio.sleep(30)

    def state(self):
        now = datetime.now(timezone.utc)
        providers = [{**source, 'id':provider, 'interval_seconds':INTERVAL, 'freshness_seconds':TTL,
                      **effective(self.record(provider), now)} for provider,source in PROVIDERS.items()]
        changes = self.store.rows("SELECT seq,at,payload FROM events WHERE type='service_health_change' ORDER BY seq DESC LIMIT 12")
        return {'as_of':now.isoformat(), 'providers':providers,
                'changes':[{**row,'payload':json.loads(row['payload'])} for row in changes],
                'scope':'Published reports only; no authenticated, model, payment or trading probes',
                'external_notifications_enabled':False, 'execution_enabled':False}

    @staticmethod
    def alpaca_state(store):
        # Runs inside the collector; reuse its retained snapshot and request budget.
        now = datetime.now(timezone.utc)
        health = store.get('source:alpaca-status', {})
        key = 'alpaca-status:'+hashlib.sha256(b'current-status').hexdigest()[:24]
        rows = store.rows('SELECT i.payload FROM intelligence i JOIN intelligence_current c ON i.id=c.id AND i.revision=c.revision WHERE i.id=?', (key,))
        report = None
        try:
            if rows:
                item = json.loads(rows[0]['payload'])
                report = parse_report('alpaca', json.dumps({'status':{'indicator':item['indicator'], 'description':item['headline']},
                                     'components':item['components']}).encode())
        except (ValueError, KeyError, TypeError):
            pass
        return {'id':'alpaca', 'name':'Alpaca', 'url':'https://status.alpaca.markets/',
                          'scope':'Existing public status snapshot; account/data readback is shown separately',
                          'interval_seconds':INTERVAL, 'freshness_seconds':TTL,
                          **effective({'fetch_status':health.get('status'), 'checked_at':health.get('last_attempt_at'),
                                       'last_success_at':health.get('last_success_at'), 'http_status':health.get('http_status'),
                                       'report':report or {}, 'error':health.get('detail')}, now)}
