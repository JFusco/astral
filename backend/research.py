"""Point-in-time evidence screening; language models cannot override vetoes."""
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import hashlib
import json

from .risk import number as D, timestamp, propose
from .config import SYMBOLS

RESEARCH_VERSION = "research-evidence-v1"


def screen(symbol, quote, history, news, news_coverage, calendar, metadata, account, as_of):
    now = timestamp(as_of)
    vetoes, facts, bars = [], {}, []
    kind = SYMBOLS[symbol][1]
    evidence = [{"id": "quote:"+symbol, "source": quote.get("source"), "at": quote.get("at"), "kind": "quote"}]
    try:
        bid, ask = D(quote["bid"]), D(quote["ask"])
        if bid <= 0 or ask < bid: raise ValueError("Invalid quote")
        quote_age = (now-timestamp(quote["at"])).total_seconds()
        if not 0 <= quote_age <= 15: vetoes.append("Quote is stale or future-dated")
        spread = (ask-bid)/((ask+bid)/2)*10000
        facts.update(spread_bps=str(spread), bid=str(bid), ask=str(ask))
        if spread > (20 if kind == "etf" else 35): vetoes.append("Spread exceeds research threshold")
        depth_cap = None
        if kind == "crypto":
            facts["size_unit"] = quote.get("size_unit", "unverified")
            if quote.get("size_unit") != "base_asset":
                vetoes.append("Crypto quote-size units unverified; depth-based sizing is unavailable")
            else:
                bid_size, ask_size = D(quote.get("bid_size")), D(quote.get("ask_size"))
                if min(bid_size, ask_size) <= 0: raise ValueError("Crypto quote depth is missing or nonpositive")
                depth_cap = min(bid_size*bid, ask_size*ask)*D("0.01")
                facts["top_of_book_one_percent_cap"] = str(depth_cap)
        if not history or not 0 <= (now-timestamp(history["received_at"])).total_seconds() <= 1800:
            raise ValueError("Historical source is unavailable or stale")
        facts["bar_semantics"] = history.get("bar_semantics", "unknown")
        if kind == "crypto" and history.get("bar_semantics") != "executed-trades-only":
            vetoes.append("Crypto OHLC may contain quote midpoints; trade-based breakout requires verified executed-trade bars")
        # Daily ETF timestamp commonly begins at local midnight. End at the
        # next midnight conservatively; this is not an exchange-calendar claim.
        for raw in history["rows"]:
            start = timestamp(raw["t"]);end = start+timedelta(days=1)
            if end > now: continue
            bars.append({"symbol": symbol, "source": "alpaca", "feed": history["source"], "adjustment": "raw",
                         "at": start.isoformat(), "closed_at": end.isoformat(), "known_at": history["received_at"],
                         **{k: str(raw[r]) for k, r in (("open","o"),("high","h"),("low","l"),("close","c"),("volume","v"))}})
        bars = bars[-90:]
        if len(bars) < 51: raise ValueError("Insufficient completed daily history")
        dollar_volumes = [D(b["volume"])*D(b["close"]) for b in bars[-21:]]
        avg = sum(dollar_volumes[:-1], Decimal(0))/20
        if avg <= 0: raise ValueError("Invalid dollar volume")
        facts.update(avg_daily_dollar_volume_20=str(avg), latest_daily_dollar_volume=str(dollar_volumes[-1]),
                     relative_dollar_volume=str(dollar_volumes[-1]/avg), volume_scope=history["coverage"],
                     history_source=history["source"], latest_closed_daily_bar=bars[-1]["closed_at"])
        if avg < 1000000: vetoes.append("Observed average daily dollar volume below $1m research threshold")
        full_value_cap = min(D("1000"), D(account["equity"])*D("0.0025")/D("1.003"))
        if depth_cap is not None: full_value_cap = min(full_value_cap, depth_cap)
        planner = propose(bars=bars, horizon="swing", kind=kind, as_of=as_of, entry=str(ask*D("1.001")),
                          equity=account["equity"], cash_cap=account["cash"], notional_cap=str(full_value_cap),
                          increment=metadata["increment"], minimum=metadata["minimum"], tick=metadata["price_increment"])
        facts.update(atr14=planner["atr14_wilder"], signal=planner["signal"], planned_stop=planner["stop_reference"],
                     target=planner["target_reference"], cost_hurdle=planner["cost_hurdle_passed"],
                     proposed_quantity=planner["quantity"], proposed_notional=planner["notional"],
                     planned_loss_budget=planner["planned_loss_budget"], planned_stress_loss=planner["planned_stress_loss"],
                     sizing_reason="Minimum of ATR loss budget, own cash and unprotected swing full-value cap; quantity rounded down. Current portfolio gate can veto.")
        if planner["signal"] != "entry_candidate": vetoes.append("Frozen price/volatility hypothesis has no entry candidate")
        evidence.append({"id": "history:"+symbol, "source": history["source"], "at": history["received_at"], "kind": "daily-bars"})
    except (ValueError, KeyError, TypeError) as exc:
        vetoes.append(str(exc))
    news_fresh = news_coverage and news_coverage.get("status") == "available" and 0 <= (now-timestamp(news_coverage["at"])).total_seconds() <= 300
    if not news_fresh: vetoes.append("News source unavailable or stale")
    relevant = []
    for item in news:
        symbols = {s.replace("/", "") for s in item.get("symbols", [])}
        if symbol not in symbols and SYMBOLS[symbol][0].replace("/", "") not in symbols: continue
        try:
            published, known, updated = (timestamp(item[k]) for k in ("created_at", "first_seen_at", "updated_at"))
            if published > now or known > now or updated > now: continue
            if (now-published).total_seconds() > 86400: continue
        except (KeyError, ValueError, TypeError): continue
        relevant.append({"id": "news:"+str(item["id"]), "headline": item["headline"][:300], "url": item.get("url"),
                         "published_at": item["created_at"], "known_at": item["first_seen_at"], "source": item.get("source")})
    evidence.extend(relevant[:5])
    if not relevant: vetoes.append("No recent symbol-specific news evidence; absence of articles is not proof of no catalyst")
    # Corporate earnings, ETF distribution/rebalance/holdings events and crypto
    # upgrades/unlocks differ. No calendar integration means UNKNOWN, never none.
    calendar_valid = False
    if calendar:
        try:
            calendar_valid = calendar["symbol"] == symbol and calendar["status"] == "verified" and timestamp(calendar["known_at"]) <= now <= timestamp(calendar["coverage_until"]) and now-timestamp(calendar["known_at"]) <= timedelta(hours=6) and bool(calendar["source_url"].startswith("https://"))
            if calendar_valid:
                evidence.append({"id": "calendar:"+symbol, "source": calendar["source_url"], "at": calendar["known_at"], "kind": "event-calendar",
                                 "coverage_until": calendar["coverage_until"], "events": calendar["events"]})
                for event in calendar["events"]:
                    when = timestamp(event["at"])
                    if now-timedelta(minutes=30) <= when <= now+timedelta(hours=24): vetoes.append("Scheduled event falls inside the 24-hour research exclusion window")
        except (KeyError, ValueError, TypeError): calendar_valid = False
    if not calendar_valid: vetoes.append("Upcoming financial/protocol/macro events are unknown; verified calendar coverage required")
    facts["event_calendar_status"] = "verified" if calendar_valid else "unknown"
    facts["event_types_required"] = "Fund distributions/rebalances, major holdings and macro releases" if kind == "etf" else "Protocol upgrades, supply unlocks, exchange/security and macro events"
    packet = {"version": RESEARCH_VERSION, "symbol": symbol, "kind": kind, "horizon": "swing", "as_of": as_of,
              "expires_at": (now+timedelta(minutes=5)).isoformat(), "facts": facts, "evidence": evidence,
              "vetoes": list(dict.fromkeys(vetoes)), "eligible": not vetoes, "execution_enabled": False}
    packet["input_hash"] = hashlib.sha256(json.dumps(packet,sort_keys=True,separators=(",", ":")).encode()).hexdigest()
    return packet


def validate_review(review, packets):
    by_symbol = {p["symbol"]: p for p in packets}
    checked = []
    if review.get("decision") not in {"abstain", "propose"}: raise ValueError("Invalid agent decision")
    if len(review.get("picks", [])) > 3: raise ValueError("Too many agent picks")
    for pick in review.get("picks", []):
        if any(p["symbol"] == pick["symbol"] for p in checked): raise ValueError("Duplicate agent symbol")
        packet = by_symbol.get(pick["symbol"])
        if not packet or not packet["eligible"]: raise ValueError("Agent selected an unknown or vetoed symbol")
        ids = {e["id"] for e in packet["evidence"]}
        if not pick["evidence_ids"] or not set(pick["evidence_ids"]).issubset(ids): raise ValueError("Agent cited missing evidence")
        if not pick["why_now"] or not pick["invalidation"] or not pick["counter_case"]: raise ValueError("Incomplete trade thesis")
        for field in ("spread_bps", "avg_daily_dollar_volume_20", "proposed_notional"):
            if D(pick[field]) != D(packet["facts"][field]): raise ValueError("Agent numerical claim differs from evidence")
        checked.append(pick)
    if (review["decision"] == "propose") != bool(checked): raise ValueError("Decision and picks disagree")
    return {**review, "picks": checked, "execution_enabled": False, "validation": "evidence-ids-and-hard-vetoes-passed"}
