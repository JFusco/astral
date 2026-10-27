"""Evidence-by-evidence readiness. No threshold changes or execution capability."""
from decimal import Decimal
from datetime import timedelta
import json
import hashlib
import re
from urllib.parse import urlsplit
from .risk import number as D, timestamp
from .store import utcnow


def calendar_coverage(calendar, symbol, now, proofs=None):
    """All scoped categories need retained, current, forward-covering evidence.

    Unannounced incidents remain a separate live operational risk; no calendar
    can certify that a future security incident will not occur.
    """
    required={"fomc", "bea", "bls", "scheduled-protocol", "venue-maintenance"}
    if symbol != "BTC": required.add("supply-unlocks")
    missing=[]; proofs=proofs or {}
    for category in sorted(required):
        try:
            c=calendar["categories"][category]
            proof=proofs.get(c.get("retained_evidence_sha256"),{})
            valid=(calendar["symbol"]==symbol and c["status"]=="verified"
                   and 0 <= (now-timestamp(c["checked_at"])).total_seconds() <= (300 if category=="venue-maintenance" else 21600)
                   and timestamp(c["coverage_from"]) <= now
                   and timestamp(c["coverage_until"]) >= now+timedelta(hours=24)
                   and urlsplit(c["source_url"]).scheme=="https" and bool(urlsplit(c["source_url"]).hostname)
                   and re.fullmatch(r"[0-9a-f]{64}",c["retained_evidence_sha256"]) is not None
                   and proof.get("category")==category and proof.get("symbol")==symbol
                   and proof.get("source_url")==c["source_url"]
                   and all(proof.get(k)==c[k] for k in ("checked_at","coverage_from","coverage_until")))
        except (ValueError, KeyError, TypeError):valid=False
        if not valid:missing.append(category)
    return {"passed":not missing,"required_categories":sorted(required),"missing_categories":missing}


def view(store, *, feed_enabled=False, max_snapshot_age=30):
    from .inventory import attribute
    now = timestamp(utcnow())
    snapshot = store.get("account_snapshot", {})
    inventory = attribute(store, snapshot)
    from .activity_feed import current_accounting
    accounting = current_accounting(store, enabled=feed_enabled, now=now.isoformat(), max_snapshot_age=max_snapshot_age)
    proofs={}; calendars=store.get("event_calendars",{})
    active_hashes={c.get("retained_evidence_sha256") for symbol in ("BTC","ETH","SOL")
                   for key,c in calendars.get(symbol,{}).get("categories",{}).items()
                   if key in {"fomc","bea","bls","scheduled-protocol","venue-maintenance","supply-unlocks"}}
    active_hashes.discard(None)
    if active_hashes and store.rows("SELECT name FROM sqlite_master WHERE name='event_calendar_evidence'"):
        placeholders=",".join("?" for _ in active_hashes)
        for row in store.rows("SELECT sha256,payload FROM event_calendar_evidence WHERE sha256 IN ("+placeholders+")",tuple(active_hashes)):
            if hashlib.sha256(row["payload"].encode()).hexdigest()==row["sha256"]:
                proofs[row["sha256"]]=json.loads(row["payload"])
    quotes = store.get("quotes", {})
    packets = {p["symbol"]: p for p in store.get("research_packets", [])}
    context = store.get("public_research_context", {})
    sources = {}
    for s in context.get("sources", []):
        try:
            fresh = s.get("status")=="connected" and 0 <= (now-timestamp(s["last_success_at"])).total_seconds() <= min(21600, max(600, s["interval_seconds"]*3))
        except (ValueError, KeyError, TypeError): fresh=False
        sources[s["id"]] = {"name":s["name"], "fresh":fresh, "checked_at":s.get("last_success_at"), "url":s["url"]}
    fees = store.rows("SELECT type,payload FROM activities")
    confirmed = sum(json.loads(r["payload"]).get("status")=="executed" for r in fees)
    rows = []
    for symbol in ("BTC", "ETH", "SOL"):
        quote = quotes.get(symbol, {})
        depth = quote.get("depth", {})
        try:
            depth_ok = quote.get("size_unit")=="base_asset" and depth.get("status")=="validated" and 0 <= (now-timestamp(depth["at"])).total_seconds() <= 15 and 0 <= (now-timestamp(quote["at"])).total_seconds() <= 15
        except (ValueError, KeyError, TypeError): depth_ok=False
        packet=packets.get(symbol, {})
        history=store.get("trade_history:"+symbol, {})
        average=None
        try:
            bars=history["rows"][-21:]
            if len(bars)!=21 or history.get("bar_semantics")!="executed-trades-only" or not history.get("complete_page_traversal"):
                raise ValueError("Unverified history")
            if not 0 <= (now-timestamp(history["received_at"])).total_seconds() <= 1800:raise ValueError("Stale history")
            average=sum((D(b["dollar_volume"]) for b in bars[:-1]),Decimal(0))/20
        except (ValueError,KeyError,TypeError):pass
        minimum_notional=None; size_fits=False
        try:
            asset=store.get("assets",{})[symbol]
            minimum_notional=D(asset["minimum"])*D(quote["ask"])*D("1.001")
            size_fits=asset.get("tradable") is True and min(D("25"),D(depth["top_one_percent_cap_usd"]))>=minimum_notional>0
        except (ValueError,KeyError,TypeError):pass
        liquidity_ok=depth_ok and average is not None and average>=1000000 and size_fits
        caps={k:depth.get(k) for k in ("top_one_percent_cap_usd", "buy_one_percent_capacity_usd", "sell_one_percent_capacity_usd")}
        fee_ok=(accounting['accounting_by_symbol'][symbol]['passed']
                and inventory["status"]=="matched" and not store.get("fee_reconciliation_required"))
        source_ids=["fomc-calendar","bea-calendar","nyfed-bls","alpaca-maint-upcoming","alpaca-maint-active"]
        source_ids+= ["bitcoin-bips","bitcoin-lifecycle"] if symbol=="BTC" else ["ethereum-roadmap"] if symbol=="ETH" else []
        coverage={k:sources.get(k,{"fresh":False,"name":k}) for k in source_ids}
        event_result=calendar_coverage(calendars.get(symbol,{}),symbol,now,proofs)
        rows.append({"symbol":symbol,"fees":{"passed":fee_ok,"status":inventory["status"],"confirmed_records":confirmed,
                     "differences":inventory["differences"],"errors":inventory["errors"],"last_check":store.get("fee_coverage")},
                     "depth":{"passed":depth_ok,"status":"validated" if depth_ok else "unverified/stale",
                              "evidence":depth,"fill_guaranteed":False},
                     "liquidity":{"passed":liquidity_ok,"average_daily_dollars":str(average) if average is not None else None,
                                  "required_average_daily_dollars":"1000000","threshold_changed":False,"venue":"alpaca-us",**caps,
                                  "minimum_tradable_notional_usd":str(minimum_notional) if minimum_notional is not None else None,
                                  "top_cap_fits_venue_minimum":size_fits,
                                  "provider_minimum_usd_note":"Alpaca FAQ describes a $1 minimum; verify current instrument metadata before an order"},
                     "events":{**event_result,"status":"verified scoped coverage" if event_result["passed"] else "partial coverage","sources":coverage,
                               "partial_categories":calendars.get(symbol,{}).get("categories",{}),
                               "missing":["NY Fed key BLS releases are scoped context; complete BLS coverage still unknown (original BLS ICS 403 retained)",
                                          "Protocol documents are connected context, not a complete activation/unlock calendar",
                                          "Unannounced security incidents cannot be certified absent by a calendar"],
                               "not_applicable":["Corporate earnings and ETF distributions"] if symbol=="BTC" else []},
                     "signal":packet.get("facts",{}).get("signal","unknown"),"packet_eligible":packet.get("eligible",False),
                     "paper_trade_authorized":False})
    return {"version":"readiness-evidence-v1","as_of":now.isoformat(),"symbols":rows, **accounting,
            "broader_readiness_not_covered":["SPY", "QQQ", "GLD", "TLT", "IWM"],
            "execution_enabled":False,"policy_changed":False,
            "next_requirements":["All evidence gates and a fresh qualifying entry", "Separately validated research execution/exit supervision"]}
