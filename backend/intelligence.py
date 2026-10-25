"""Independent public intelligence collector. No broker, credentials or order tools.

Headlines are untrusted context, never verified calendars or execution authority.
Only fixed public endpoints are fetched; article links are never crawled.
"""
import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
import json
import re
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

import httpx

from .store import dumps, utcnow
from . import event_sources

MAX_BYTES = 2_000_000


@dataclass(frozen=True)
class Source:
    id: str
    name: str
    url: str
    category: str
    kind: str = "rss"
    interval: int = 300
    symbols: tuple = ()
    requires_contact: bool = False


SOURCES = (
    Source("fed", "Federal Reserve releases", "https://www.federalreserve.gov/feeds/press_all.xml", "macro"),
    Source("fomc-calendar", "Federal Reserve FOMC calendar", "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm", "macro-calendar", "fomc", 3600),
    Source("fed-speeches", "Federal Reserve speeches", "https://www.federalreserve.gov/feeds/speeches.xml", "macro", interval=900),
    Source("bls", "BLS economic releases", "https://www.bls.gov/feed/bls_latest.rss", "macro"),
    Source("sec-8k", "SEC current reports (8-K)", "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&owner=exclude&count=40&output=atom", "filings", interval=900, requires_contact=True),
    Source("sec-10q", "SEC quarterly reports (10-Q)", "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=10-Q&owner=exclude&count=40&output=atom", "filings", interval=900, requires_contact=True),
    Source("coindesk", "CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss", "crypto"),
    Source("cointelegraph", "Cointelegraph", "https://cointelegraph.com/rss", "crypto"),
    Source("ethereum", "Ethereum Foundation blog", "https://blog.ethereum.org/en/feed.xml", "crypto", interval=900, symbols=("ETH",)),
    Source("bitcoin-core", "Bitcoin Core announcements", "https://bitcoincore.org/en/rss.xml", "crypto", interval=900, symbols=("BTC",)),
    Source("coinbase-status", "Coinbase status", "https://status.coinbase.com/api/v2/summary.json", "operations", "status", 120),
    Source("kraken-status", "Kraken status", "https://status.kraken.com/api/v2/summary.json", "operations", "status", 120),
    Source("solana-status", "Solana status", "https://status.solana.com/api/v2/summary.json", "operations", "status", 120, ("SOL",)),
    Source("alpaca-status", "Alpaca status", "https://status.alpaca.markets/api/v2/summary.json", "operations", "status", 120),
    Source("bea-calendar", "BEA economic release calendar", "https://www.bea.gov/news/schedule", "macro-calendar", "bea", 3600),
    Source("nyfed-bls", "New York Fed key BLS release calendar", event_sources.NYFED, "macro-calendar", "nyfed", 3600),
    Source("alpaca-maint-upcoming", "Alpaca upcoming maintenance", event_sources.MAINTENANCE+"upcoming.json", "operations", "maintenance-upcoming", 120),
    Source("alpaca-maint-active", "Alpaca active maintenance", event_sources.MAINTENANCE+"active.json", "operations", "maintenance-active", 120),
    Source("bitcoin-bips", "Bitcoin BIP proposal index", event_sources.BIPS, "protocol", "bips", 900, ("BTC",)),
    Source("bitcoin-lifecycle", "Bitcoin Core software lifecycle", event_sources.LIFECYCLE, "protocol", "bitcoin-lifecycle", 3600, ("BTC",)),
    Source("ethereum-roadmap", "Ethereum protocol roadmap", event_sources.ETHEREUM, "protocol", "ethereum-roadmap", 3600, ("ETH",)),
)


def clean(value, limit=500):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]*>", "", str(value or ""))).strip()[:limit]


def date(value):
    if not value:
        return None
    try:
        d = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            d = parsedate_to_datetime(value)
        except (ValueError, TypeError, OverflowError):
            return None
    # Never invent a timezone or a publication timestamp.
    return d.astimezone(timezone.utc).isoformat() if d.tzinfo else None


def safe_url(value):
    try:
        u = urlsplit(value or "")
        return value if u.scheme == "https" and u.hostname and not u.username and not u.password else None
    except ValueError:
        return None


def named(node, name):
    return next((c for c in node if c.tag.rsplit("}", 1)[-1] == name), None)


def value(node, name):
    c = named(node, name)
    return "".join(c.itertext()).strip() if c is not None else ""


def parse(source, body):
    if len(body) > MAX_BYTES:
        raise ValueError("Response exceeds byte limit")
    if source.kind in event_sources.KINDS:
        return event_sources.parse_events(source.kind, body)
    if source.kind == "fomc":
        from .calendar_context import parse_fomc
        return parse_fomc(body)
    if source.kind == "bea":
        from .bea_calendar import parse_bea
        return parse_bea(body)
    if source.kind == "status":
        raw = json.loads(body)
        status = raw["status"]
        # Overall/component status is a snapshot, not a news publication.
        result = [{"key": "current-status", "headline": source.name+": "+clean(status["description"]),
                   "url": source.url.removesuffix("/api/v2/summary.json"), "created_at": None,
                   "updated_at": date(raw.get("page", {}).get("updated_at")),
                   "indicator": clean(status["indicator"], 40),
                   "components": [{"name": clean(c.get("name"), 150), "status": clean(c.get("status"), 40)} for c in raw.get("components", [])[:150]]}]
        for item in (raw.get("incidents", [])+raw.get("scheduled_maintenances", []))[:40]:
            result.append({"key": str(item["id"]), "headline": clean(item.get("name")),
                           "url": safe_url(item.get("shortlink")) or result[0]["url"],
                           "created_at": date(item.get("created_at")), "updated_at": date(item.get("updated_at")),
                           "indicator": clean(item.get("status"), 40), "scheduled_for": date(item.get("scheduled_for")),
                           "scheduled_until": date(item.get("scheduled_until"))})
        return result
    # Reject entities/DTDs, including UTF-16/32 declarations, before stdlib parsing.
    probe = body.replace(b"\x00", b"").upper()
    if b"<!DOCTYPE" in probe or b"<!ENTITY" in probe:
        raise ValueError("XML declarations with entities are not accepted")
    root = ET.fromstring(body)
    if root.tag.rsplit("}", 1)[-1] not in {"rss", "feed", "RDF"}:
        raise ValueError("Response is not an RSS or Atom feed")
    result = []
    for item in (n for n in root.iter() if n.tag.rsplit("}", 1)[-1] in {"item", "entry"}):
        link = named(item, "link")
        url = safe_url(link.get("href") or link.text) if link is not None else None
        headline = clean(value(item, "title"))
        if not headline or not url:
            continue
        result.append({"key": value(item, "guid") or value(item, "id") or url, "headline": headline,
                       "url": url, "created_at": date(value(item, "pubDate") or value(item, "published")),
                       "updated_at": date(value(item, "updated") or value(item, "pubDate") or value(item, "published"))})
        if len(result) >= 40:
            break
    if not result:
        raise ValueError("Feed contains no usable linked headlines")
    return result


class Collector:
    def __init__(self, store, client=None, contact="", sources=SOURCES):
        self.store, self.contact, self.sources = store, contact, sources
        self.client = client or httpx.AsyncClient(timeout=20, follow_redirects=False, trust_env=False)
        self.semaphore = asyncio.Semaphore(3)
        self.lock = asyncio.Lock()
        self.unsaved_health = {}
        store.db.executescript("""
          CREATE TABLE IF NOT EXISTS intelligence(id TEXT NOT NULL,revision TEXT NOT NULL,first_seen_at TEXT NOT NULL,payload TEXT NOT NULL,PRIMARY KEY(id,revision));
          CREATE INDEX IF NOT EXISTS intelligence_id ON intelligence(id,first_seen_at);
          CREATE TABLE IF NOT EXISTS intelligence_current(id TEXT PRIMARY KEY,revision TEXT NOT NULL);
          INSERT OR IGNORE INTO intelligence_current SELECT id,revision FROM intelligence WHERE rowid IN (SELECT MAX(rowid) FROM intelligence GROUP BY id);
        """)

    async def close(self):
        await self.client.aclose()

    async def poll(self, force=False):
        async with self.lock:
            await asyncio.gather(*(self.fetch(s, force) for s in self.sources))

    async def fetch(self, source, force=False):
        health = dict(self.unsaved_health.get(source.id) or self.store.get("source:"+source.id, {}))
        now = datetime.now(timezone.utc).timestamp()
        catalog_kind=source.kind in {"fomc","bea"} | event_sources.KINDS
        needs_catalog=catalog_kind and not self.store.get("calendar_catalog:"+source.id)
        bootstrap=needs_catalog and not health.get("catalog_bootstrap_attempted")
        if not force and not bootstrap and now < health.get("next_attempt_epoch", 0):
            return
        if source.requires_contact and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", self.contact):
            self.store.put("source:"+source.id, {**health, "status": "needs-contact", "detail": "SEC identifying contact required"})
            return
        headers = {"User-Agent": "ASTRAL-Local-Research/0.3"+(" contact "+self.contact if source.requires_contact else " (public-feed-reader)"),
                   "Accept": "application/rss+xml, application/atom+xml, application/xml, application/json, text/xml, text/html"}
        for key, header in (("etag", "If-None-Match"), ("last_modified", "If-Modified-Since")):
            if health.get(key) and not needs_catalog: headers[header] = health[key]
        async with self.semaphore:
            prior_health = dict(health)
            health.pop("health_persisted", None)
            health.update(last_attempt_at=utcnow(), requests=health.get("requests", 0)+1, http_status=None)
            if needs_catalog:health["catalog_bootstrap_attempted"]=True
            try:
                async with self.client.stream("GET", source.url, headers=headers) as response:
                    health["http_status"] = response.status_code
                    if response.status_code == 304:
                        if not health.get("last_success_at"):
                            raise ValueError("304 without a retained successful fetch")
                        health.update(status="connected", last_success_at=utcnow(), failures=0, detail="Unchanged; source revalidated", next_attempt_epoch=now+source.interval)
                        with self.store.transaction():
                            self.store.put("source:"+source.id, health)
                            catalog=self.store.get("calendar_catalog:"+source.id)
                            if catalog:
                                catalog["checked_at"]=health["last_success_at"]
                                if source.kind.startswith("maintenance-"):
                                    catalog["coverage_from"]=health["last_success_at"]
                                    from datetime import timedelta
                                    catalog["coverage_until"]=(datetime.fromisoformat(health["last_success_at"])+timedelta(hours=48)).isoformat()
                                self.store.put("calendar_catalog:"+source.id,catalog)
                        self.unsaved_health.pop(source.id, None)
                        return
                    response.raise_for_status()
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > MAX_BYTES: raise ValueError("Response exceeds byte limit")
                    items = parse(source, bytes(body))
                    seen = utcnow()
                    with self.store.transaction():
                        if catalog_kind:
                            body_hash=hashlib.sha256(body).hexdigest()
                            self.store.db.execute("CREATE TABLE IF NOT EXISTS calendar_source_bodies(sha256 TEXT PRIMARY KEY,at TEXT NOT NULL,url TEXT NOT NULL,body TEXT NOT NULL)")
                            self.store.db.execute("INSERT OR IGNORE INTO calendar_source_bodies VALUES(?,?,?,?)",(body_hash,seen,source.url,body.decode("utf-8")))
                            self.store.put("calendar_catalog:"+source.id,event_sources.catalog(source,bytes(body),items,seen))
                        if not items and source.kind.startswith("maintenance-"):
                            # Valid empty schedule is a retained snapshot, never an executed event.
                            items=[{"key":"empty-published-schedule","headline":source.name+": no published entries in latest response",
                                    "url":source.url,"created_at":None,"updated_at":None,"schedule_empty":True}]
                        for item in items:
                            key = item.pop("key")
                            item.update(id=source.id+":"+hashlib.sha256(key.encode()).hexdigest()[:24],
                                        source=source.name, source_id=source.id, category=source.category,
                                        symbols=list(source.symbols), symbol_scope="source-level context; no inferred ticker mapping",
                                        evidence_role="context-only", source_url=source.url)
                            revision = hashlib.sha256(dumps(item).encode()).hexdigest()
                            item.update(first_seen_at=seen, revision=revision)
                            cur = self.store.db.execute("INSERT OR IGNORE INTO intelligence VALUES(?,?,?,?)", (item["id"], revision, seen, dumps(item)))
                            self.store.db.execute("INSERT INTO intelligence_current VALUES(?,?) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision", (item["id"], revision))
                            if cur.rowcount: self.store.event("intelligence", {"id": item["id"], "source_id": source.id, "revision": revision})
                        health.update(status="connected", last_success_at=seen, failures=0, detail="Metadata only; bounded public source sample",
                                      last_item_count=len(items), etag=response.headers.get("etag"), last_modified=response.headers.get("last-modified"),
                                      bytes=len(body), next_attempt_epoch=now+source.interval)
                        self.store.put("source:"+source.id, health)
                    self.unsaved_health.pop(source.id, None)
            except Exception:
                health = {**prior_health, **{k:health[k] for k in ("last_attempt_at", "requests", "http_status", "catalog_bootstrap_attempted") if k in health}}
                failures = prior_health.get("failures", 0)+1
                delay = min(source.interval*2**min(failures, 5), 21600)
                # Honor numeric Retry-After where supplied, without a rapid retry loop.
                if health.get("http_status") == 429:
                    retry = response.headers.get("retry-after", "")
                    try:
                        delay = max(delay, float(retry))
                    except ValueError:
                        retry_date = date(retry)
                        if retry_date: delay = max(delay, datetime.fromisoformat(retry_date).timestamp()-now)
                health.update(status="error", failures=failures, detail="Fetch or validation failed; cached evidence retained", next_attempt_epoch=now+delay)
                health["last_success_at"] = prior_health.get("last_success_at")
                health.pop("health_persisted", None)
                try:
                    self.store.put("source:"+source.id, health)
                except Exception:
                    health.update(health_persisted=False, detail="Fetch or storage failed; error health could not be persisted")
                    self.unsaved_health[source.id] = health
                else:
                    self.unsaved_health.pop(source.id, None)

    def state(self):
        now = datetime.now(timezone.utc).timestamp()
        sources = []
        for s in self.sources:
            h = self.unsaved_health.get(s.id) or self.store.get("source:"+s.id, {})
            checked = date(h.get("last_success_at"))
            fresh = bool(checked) and 0 <= now-datetime.fromisoformat(checked).timestamp() <= max(600, s.interval*3)
            sources.append({"id": s.id, "name": s.name, "url": s.url, "category": s.category,
                            "interval_seconds": s.interval, **{k:v for k,v in h.items() if k not in {"etag", "last_modified"}},
                            "fresh": fresh, "status": "stale" if h.get("status") == "connected" and not fresh else h.get("status", "waiting")})
        # Keep revisions immutable, but let the current pointer follow a publisher
        # reverting to older content. Balance sources so a busy feed cannot hide
        # every item from a smaller feed in this bounded response.
        items = self.store.rows("""WITH ranked AS (
            SELECT i.payload,COALESCE(json_extract(i.payload,'$.event_start'),json_extract(i.payload,'$.created_at'),json_extract(i.payload,'$.updated_at'),i.first_seen_at) sort_at,
                   ROW_NUMBER() OVER (PARTITION BY json_extract(i.payload,'$.source_id') ORDER BY COALESCE(json_extract(i.payload,'$.event_start'),json_extract(i.payload,'$.created_at'),json_extract(i.payload,'$.updated_at'),i.first_seen_at) DESC,i.rowid DESC) rank
            FROM intelligence i JOIN intelligence_current c ON i.id=c.id AND i.revision=c.revision)
            SELECT payload FROM ranked WHERE rank<=20 ORDER BY sort_at DESC LIMIT 420"""
        )
        catalogs=[]
        for s in sources:
            if s["fresh"] and s["status"]=="connected":
                catalog=self.store.get("calendar_catalog:"+s["id"])
                if catalog:catalogs.append(catalog)
        return {"as_of": utcnow(), "sources": sources, "items": [json.loads(r["payload"]) for r in items], "calendar_catalogs":catalogs,
                "scope": "Public metadata and operational snapshots; context only, no complete event calendar", "execution_enabled": False}
