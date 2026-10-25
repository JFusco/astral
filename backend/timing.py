"""Deterministic timing hypotheses. Produces candidates, never orders or fills."""
from datetime import timedelta

from .risk import number as D, timestamp

VERSION = "timing-v1"


def decide(*, as_of, horizon, kind, quote, session_open, signal, latest_closed_at,
           research_qualified, research_expires_at, quantity="0", entry_at=None,
           stop_price=None, target_price=None, pending_order=False, last_exit_at=None,
           entries_halted=False):
    now = timestamp(as_of)
    def result(action, reason):
        return {"version": VERSION, "action": action, "reason": reason, "as_of": as_of,
                "execution_enabled": False, "fill_assumed": False}
    if horizon not in {"swing", "intraday"} or kind not in {"etf", "crypto"}:
        return result("wait", "Unsupported timing horizon or instrument")
    if pending_order: return result("wait", "Existing or uncertain order must reconcile before another decision")
    held = D(quantity)
    if held < 0: return result("review", "Short inventory is outside this strategy")
    try:
        qtime = timestamp(quote["at"]);bid, ask = D(quote["bid"]), D(quote["ask"])
        if not 0 <= (now-qtime).total_seconds() <= 15 or bid <= 0 or ask < bid:
            return result("wait", "Executable quote is invalid, stale or future-dated")
    except (ValueError, KeyError, TypeError):
        return result("wait", "Executable quote is unavailable")
    if kind == "etf" and not session_open: return result("wait", "ETF session is closed; exit eligibility remains monitored")
    if held > 0:
        # Protective references do not certify protection. Local exits still
        # require the single executor and may miss price during downtime/gaps.
        if stop_price is not None and bid <= D(stop_price): return result("sell_candidate", "Current bid crossed the stop reference")
        if target_price is not None and bid >= D(target_price): return result("sell_candidate", "Current bid reached the target reference")
        if entry_at:
            maximum = timedelta(hours=1) if horizon == "intraday" else timedelta(days=10)
            if now-timestamp(entry_at) >= maximum: return result("sell_candidate", "Maximum holding time reached")
        if signal == "exit_review": return result("sell_candidate", "Closed-bar trend invalidation")
        return result("hold", "Position retained; no current exit condition")
    if entries_halted: return result("wait", "Entry halt is active")
    if last_exit_at and now-timestamp(last_exit_at) < timedelta(minutes=5): return result("wait", "Five-minute re-entry cooldown")
    if not research_qualified: return result("wait", "No qualified, evidence-backed research pick")
    try:
        if not research_expires_at or timestamp(research_expires_at) < now: return result("wait", "Research expired before entry")
        if not latest_closed_at: return result("wait", "Required completed signal bars are unavailable")
        closed = timestamp(latest_closed_at)
        maximum_age = timedelta(days=4) if horizon == "swing" else timedelta(minutes=10)
        if closed > now or now-closed > maximum_age: return result("wait", "Signal bar is future-dated or stale")
        if qtime <= closed: return result("wait", "Entry requires an observable quote after the signal bar closed")
    except (ValueError, TypeError): return result("wait", "Signal or research timestamp is invalid")
    if signal != "entry_candidate": return result("wait", "Frozen signal rules have no entry")
    return result("buy_candidate", "Qualified research and closed-bar signal; fresh subsequent quote")


def replay(events, *, horizon="intraday", fee_bps="25", extra_slippage_bps="0"):
    """One-unit synthetic quote replay, with fills strictly AFTER decisions.

    Quote-level test harness only. No OHLC-touch fills, queue/impact model, or
    inference of real execution probability. Quotes must be chronological.
    """
    held, cash, pending, trades = D(0), D(0), None, []
    entry_at, last_exit = None, None
    previous = None
    for event in events:
        now = timestamp(event["as_of"])
        if previous and now <= previous: raise ValueError("Replay events must be strictly chronological")
        previous = now
        quote = event["quote"]
        fresh = 0 <= (now-timestamp(quote["at"])).total_seconds() <= 15
        if pending and now > pending["at"] and fresh and timestamp(quote["at"]) > pending["at"]:
            slip = D(extra_slippage_bps)/10000;fee = D(fee_bps)/10000
            price = D(quote["ask"])*(1+slip) if pending["side"] == "buy" else D(quote["bid"])*(1-slip)
            # Recheck authorization at fill time; a delayed entry cannot use an
            # expired research packet or trade in a closed/disabled session.
            if pending["side"] == "buy" and (not event["research_qualified"] or timestamp(event["research_expires_at"]) < now or event.get("entries_halted")):
                trades.append({"side":"canceled-entry", "at":event["as_of"]});pending = None
            elif event["kind"] != "etf" or event["session_open"]:
                cash += -price*(1+fee) if pending["side"] == "buy" else price*(1-fee)
                held = D(1) if pending["side"] == "buy" else D(0)
                if held: entry_at=event["as_of"]
                else: last_exit=event["as_of"]
                trades.append({"side":pending["side"], "at":event["as_of"], "price":str(price), "signal_at":pending["at"].isoformat()});pending=None
        decision = decide(**{**event, "horizon":horizon, "quantity":str(held), "entry_at":entry_at,
                             "last_exit_at":last_exit, "pending_order":pending is not None})
        if decision["action"] in {"buy_candidate", "sell_candidate"}:
            pending={"side":"buy" if decision["action"]=="buy_candidate" else "sell", "at":now}
    return {"scope":"synthetic-quote-replay", "trades":trades, "cash_change":str(cash), "open_quantity":str(held),
            "pending":pending["side"] if pending else None, "profitability_validated":False}
