"""Credential-free local feed read; headlines remain untrusted scoped context."""
import json
from datetime import timedelta
import httpx
from .risk import timestamp
from .store import utcnow


async def read_context():
    try:
        async with httpx.AsyncClient(timeout=5, trust_env=False, follow_redirects=False) as client:
            async with client.stream("GET", "http://127.0.0.1:8768/api/intelligence") as response:
                response.raise_for_status();body=bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body)>2_000_000:raise ValueError("Public context byte limit")
                data=json.loads(body)
        if not isinstance(data,dict):raise ValueError("Invalid public context")
        for key in ("sources","items","calendar_catalogs"):
            rows=data.get(key)
            if not isinstance(rows,list) or any(not isinstance(row,dict) for row in rows):raise ValueError("Invalid public context")
        if len(data["items"])>420:raise ValueError("Invalid public context")
        return {"status":"available", "received_at":utcnow(), "calendar_catalogs":data.get("calendar_catalogs",[]), **{k:data[k] for k in ("as_of","sources","items")}}
    except (httpx.HTTPError,ValueError,KeyError,TypeError):
        return {"status":"unavailable", "received_at":utcnow(), "sources":[], "items":[]}


def evidence_for(symbol, data, as_of):
    now=timestamp(as_of);sources={s["id"]:s for s in data.get("sources",[])};evidence=[];vetoes=[]
    try:
        if data.get("status")!="available" or not 0 <= (now-timestamp(data["as_of"])).total_seconds() <= 120:
            return [], [], "unavailable or stale"
    except (KeyError,TypeError,ValueError):return [], [], "invalid context timestamp"
    for item in data.get("items",[]):
        source=sources.get(item.get("source_id"),{})
        if source.get("status")!="connected" or not source.get("fresh"):continue
        if item.get("category") not in {"macro","macro-calendar","crypto","operations","protocol"}:continue
        if item.get("symbols") and symbol not in item["symbols"]:continue
        try:
            known=timestamp(item["first_seen_at"])
            if known > now:continue
            if item.get("updated_at") and timestamp(item["updated_at"])>now:continue
            if item.get("event_start"):
                start,end=timestamp(item["event_start"]),timestamp(item["event_end_exclusive"])
                dedicated_maintenance=item.get("source_id") in {"alpaca-maint-upcoming","alpaca-maint-active"}
                if not dedicated_maintenance and item.get("maintenance_status") in {"in_progress","verifying"}:
                    vetoes.append("Alpaca maintenance is active; its scheduled end does not establish recovery")
                if end<=now:continue
                if not dedicated_maintenance and start <= now+timedelta(hours=24) and end>now-timedelta(minutes=30):
                    vetoes.append("Scheduled "+item.get("calendar_scope", "macro event")+" overlaps the next 24 hours; conservative date interval")
                kind="calendar-context"
            else:
                if item.get("created_at"):
                    published=timestamp(item["created_at"])
                    if published>now or (now-published).total_seconds()>86400:continue
                elif item.get("category") not in {"operations","protocol"}:continue
                kind="public-context"
        except (KeyError,TypeError,ValueError):continue
        evidence.append({"id":"public:"+item["id"]+":"+item["revision"], "kind":kind,
                         "source":item["source"], "headline":item["headline"][:500], "url":item.get("url"),
                         "known_at":item["first_seen_at"], "published_at":item.get("created_at"),
                         "source_checked_at":source.get("last_success_at"), "revision":item["revision"],
                         "event_start":item.get("event_start"), "event_end_exclusive":item.get("event_end_exclusive"),
                         "calendar_scope":item.get("calendar_scope"), "precision":item.get("precision"),
                         "evidence_role":"context-only; no inferred ticker mapping or complete calendar coverage"})
    # Reserve room for the next two dated calendar events independently of news.
    calendar=sorted([e for e in evidence if e["kind"]=="calendar-context"], key=lambda e:e["event_start"])[:2]
    context=[e for e in evidence if e["kind"]!="calendar-context"][:12]
    # Headline samples are capped. Inspect complete retained catalogs for vetoes.
    from .event_sources import NYFED,MAINTENANCE
    from .calendar_context import FOMC_URL
    from .bea_calendar import URL as BEA_URL
    allowed={"nyfed-bls":NYFED,"alpaca-maint-upcoming":MAINTENANCE+"upcoming.json","alpaca-maint-active":MAINTENANCE+"active.json",
             "fomc-calendar":FOMC_URL,"bea-calendar":BEA_URL}
    for c in data.get("calendar_catalogs",[]):
        s=sources.get(c.get("source_id"),{})
        if c.get("source_url")!=allowed.get(c.get("source_id")) or s.get("status")!="connected" or not s.get("fresh"):continue
        try:
            for e in c["events"]:
                start,end=timestamp(e["event_start"]),timestamp(e["event_end_exclusive"])
                if e.get("maintenance_status") in {"in_progress","verifying"}:
                    vetoes.append("Alpaca maintenance is active; its scheduled end does not establish recovery")
                elif start<=now+timedelta(hours=24) and end>=now-timedelta(minutes=30):
                    vetoes.append("Published event overlaps the research exclusion window: "+e["headline"][:150])
                elif e.get("maintenance_status")=="scheduled" and end<now:
                    vetoes.append("Alpaca maintenance schedule is overdue without a terminal state")
        except (KeyError,TypeError,ValueError):vetoes.append("Published event catalog is invalid; review required")
    return calendar+context, list(dict.fromkeys(vetoes)), "scoped context only"
