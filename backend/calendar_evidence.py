"""Retain scoped official calendar catalogs; never certify missing categories."""
from datetime import timedelta
import hashlib
import json

from .risk import timestamp
from .store import utcnow
from .event_sources import NYFED, MAINTENANCE

CATALOGS={"fomc-calendar":("fomc","https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"),
          "bea-calendar":("bea","https://www.bea.gov/news/schedule")}


def retain_scopes(store, context, now):
    moment=timestamp(now);calendars=store.get("event_calendars",{})
    health={s.get("id"):s for s in context.get("sources",[])}
    for identity,(category,_) in CATALOGS.items():
        if context.get("status")=="unavailable" or (identity in health and (health[identity].get("status")!="connected" or not health[identity].get("fresh"))):
            for c in calendars.values():
                if category in c.get("categories",{}):c["categories"][category]["status"]="unavailable"
    store.db.execute("CREATE TABLE IF NOT EXISTS event_calendar_evidence(sha256 TEXT PRIMARY KEY,payload TEXT NOT NULL)")
    for catalog in context.get("calendar_catalogs",[]):
        identity=CATALOGS.get(catalog.get("source_id"))
        if not identity or catalog.get("source_url")!=identity[1]:continue
        source=health.get(catalog.get("source_id"))
        if context.get("status")=="unavailable" or (source and (source.get("status")!="connected" or not source.get("fresh"))):continue
        try:
            checked=timestamp(catalog["checked_at"])
            if not 0 <= (moment-checked).total_seconds() <= 21600:continue
            rows=catalog["events"]
            if not rows or len(rows)>200:continue
            future=[r for r in rows if timestamp(r["event_end_exclusive"])>moment]
            end=max(timestamp(r["event_end_exclusive"]) for r in future)
            if end < moment+timedelta(hours=24):continue
            if identity[0]=="fomc" and sum(timestamp(r["event_start"]).year==moment.year for r in rows)<8:continue
            body_hash=catalog["retained_body_sha256"]
            if len(body_hash)!=64 or any(c not in "0123456789abcdef" for c in body_hash):continue
        except (KeyError,TypeError,ValueError):continue
        for symbol in ("BTC","ETH","SOL"):
            proof={"symbol":symbol,"category":identity[0],"source_url":identity[1],"checked_at":catalog["checked_at"],
                   "coverage_from":catalog["checked_at"],"coverage_until":end.isoformat(),
                   "retained_body_sha256":body_hash,"events":future,
                   "scope":"Currently published official schedule only; no unannounced-event guarantee"}
            encoded=json.dumps(proof,sort_keys=True,separators=(",",":"));sha=hashlib.sha256(encoded.encode()).hexdigest()
            store.db.execute("INSERT OR IGNORE INTO event_calendar_evidence VALUES(?,?)",(sha,encoded))
            calendar=calendars.setdefault(symbol,{"symbol":symbol,"status":"partial","categories":{}})
            calendar.setdefault("categories",{})[identity[0]]={"status":"verified",**{k:proof[k] for k in ("source_url","checked_at","coverage_from","coverage_until")},"retained_evidence_sha256":sha}
    store.put("event_calendars",calendars)
    retain_additional_scopes(store,context,moment,calendars)


def retain_additional_scopes(store,context,moment,calendars):
    """Maintenance needs two current publisher lists. NY Fed remains partial BLS."""
    catalogs={c.get("source_id"):c for c in context.get("calendar_catalogs",[])}
    sources={s.get("id"):s for s in context.get("sources",[])}
    def current(identity,url,max_age):
        c=catalogs.get(identity,{});s=sources.get(identity,{})
        try:
            if (context.get("status")!="available" or not 0<=(moment-timestamp(context["as_of"])).total_seconds()<=120
                or s.get("status")!="connected" or s.get("fresh") is not True or c["source_url"]!=url
                or not 0<=(moment-timestamp(c["checked_at"])).total_seconds()<=max_age
                or len(c["retained_body_sha256"])!=64 or any(v not in "0123456789abcdef" for v in c["retained_body_sha256"])):
                return None
            return c
        except (KeyError,TypeError,ValueError):return None
    def save(symbol,category,proof,status):
        encoded=json.dumps(proof,sort_keys=True,separators=(",",":"));sha=hashlib.sha256(encoded.encode()).hexdigest()
        store.db.execute("INSERT OR IGNORE INTO event_calendar_evidence VALUES(?,?)",(sha,encoded))
        c=calendars.setdefault(symbol,{"symbol":symbol,"status":"partial","categories":{}})
        c.setdefault("categories",{})[category]={"status":status,**{k:proof[k] for k in ("source_url","checked_at","coverage_from","coverage_until")},"retained_evidence_sha256":sha}
    upcoming=current("alpaca-maint-upcoming",MAINTENANCE+"upcoming.json",300)
    active=current("alpaca-maint-active",MAINTENANCE+"active.json",300)
    for symbol in ("BTC","ETH","SOL"):
        if upcoming and active:
            proof={"symbol":symbol,"category":"venue-maintenance","source_url":MAINTENANCE+"upcoming.json",
                   "checked_at":min(upcoming["checked_at"],active["checked_at"]),
                   "coverage_from":max(upcoming["coverage_from"],active["coverage_from"]),
                   "coverage_until":min(upcoming["coverage_until"],active["coverage_until"]),
                   "components":[{k:c[k] for k in ("source_url","checked_at","retained_body_sha256")} for c in (upcoming,active)],
                   "events":upcoming["events"]+active["events"],"scope":"Published upcoming AND active Alpaca maintenance snapshot; 48h inspection horizon, 5min evidence expiry; not an outage guarantee"}
            save(symbol,"venue-maintenance",proof,"verified")
        elif "venue-maintenance" in calendars.get(symbol,{}).get("categories",{}):
            calendars[symbol]["categories"]["venue-maintenance"]["status"]="unavailable"
        ny=current("nyfed-bls",NYFED,21600)
        if ny:
            proof={"symbol":symbol,"category":"bls-key-context",**{k:ny[k] for k in ("source_url","checked_at","coverage_from","coverage_until","retained_body_sha256","events","scope")}}
            save(symbol,"bls-key-context",proof,"verified-partial")
        elif "bls-key-context" in calendars.get(symbol,{}).get("categories",{}):
            calendars[symbol]["categories"]["bls-key-context"]["status"]="unavailable"
    store.put("event_calendars",calendars)
