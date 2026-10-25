"""Reproducible research proposals. No network, randomness, or order side effects."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from decimal import Decimal, InvalidOperation, ROUND_DOWN, localcontext
import hashlib
import json

VERSION = "deterministic-risk-v3"


def number(value):
    try:
        value = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("Financial inputs must be decimal numbers") from exc
    if not value.is_finite():
        raise ValueError("Financial inputs must be finite")
    return value


def timestamp(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Bar timestamps must include a timezone")
    return result.astimezone(timezone.utc)


def floor_step(value, step):
    value, step = number(value), number(step)
    if step <= 0:
        raise ValueError("Instrument increment must be positive")
    return (value / step).to_integral_value(rounding=ROUND_DOWN) * step


def propose(*, bars, horizon, kind, as_of, entry, equity, cash_cap,
            notional_cap, increment, minimum, tick, fee_bps=None):
    """ATR14 + trend/breakout candidate and fixed fractional loss-budget sizing.

    All prices are raw/unadjusted, one symbol/feed, one bar interval. Caller must
    verify provenance. stop_reference is a planning scenario, NEVER an order.
    """
    with localcontext() as context:
        context.prec = 34
        return _propose(bars=bars, horizon=horizon, kind=kind, as_of=as_of,
                        entry=entry, equity=equity, cash_cap=cash_cap,
                        notional_cap=notional_cap, increment=increment,
                        minimum=minimum, tick=tick, fee_bps=fee_bps)


def _propose(**inputs):
    bars, horizon, kind = inputs["bars"], inputs["horizon"], inputs["kind"]
    if horizon not in {"swing", "intraday"} or kind not in {"etf", "crypto"}:
        raise ValueError("Unsupported horizon or instrument class")
    period = 86400 if horizon == "swing" else 300
    fast, slow = (20, 50) if horizon == "swing" else (10, 30)
    if not slow + 1 <= len(bars) <= 500:
        raise ValueError(f"Require {slow+1} to 500 complete bars")
    now = timestamp(inputs["as_of"])
    provenance = None
    previous_time = None
    previous_end = None
    clean = []
    for bar in bars:
        start, end, known = (timestamp(bar[k]) for k in ("at", "closed_at", "known_at"))
        identity = tuple(bar.get(k) for k in ("symbol", "source", "feed", "adjustment"))
        if not all(identity) or identity[-1] != "raw" or (provenance and identity != provenance):
            raise ValueError("Bars must share symbol, source, feed and raw adjustment")
        provenance = identity
        duration = (end-start).total_seconds()
        valid_duration = 0 < duration <= period if horizon == "swing" and kind == "etf" else duration == period
        if not valid_duration or end > now or known < end or known > now:
            raise ValueError("Only closed bars known at the decision time are permitted")
        if previous_time is not None:
            seconds = (start-previous_time).total_seconds()
            if seconds <= 0 or start < previous_end or (horizon == "intraday" and seconds % period != 0):
                raise ValueError("Bars must be ordered, unique and interval aligned")
            if horizon == "intraday" and kind == "crypto" and seconds != period:
                raise ValueError("Missing crypto intraday bars")
            if horizon == "intraday" and kind == "etf" and seconds != period and start.astimezone(ZoneInfo("America/New_York")).date() == previous_time.astimezone(ZoneInfo("America/New_York")).date():
                raise ValueError("Missing ETF bars within the same session date")
            if horizon == "swing" and kind == "crypto" and seconds != period:
                raise ValueError("Missing crypto daily bars")
        previous_time = start
        previous_end = end
        o, h, l, c, v = (number(bar[k]) for k in ("open", "high", "low", "close", "volume"))
        if min(o, h, l, c) <= 0 or l > min(o, c) or h < max(o, c) or l > h or v <= 0:
            raise ValueError("Invalid OHLC or zero-volume bar")
        clean.append((h, l, c))
    max_age = 4 * 86400 if horizon == "swing" else 600
    if (now-timestamp(bars[-1]["closed_at"])).total_seconds() > max_age:
        raise ValueError("Latest completed bar is stale")
    tr = [max(h-l, abs(h-clean[i-1][2]), abs(l-clean[i-1][2]))
          for i, (h, l, _) in enumerate(clean) if i]
    atr = sum(tr[:14], Decimal(0)) / 14
    for value in tr[14:]:
        atr = (atr*13 + value) / 14
    if atr <= 0:
        raise ValueError("Insufficient positive volatility")
    closes = [b[2] for b in clean]
    fast_mean = sum(closes[-fast:], Decimal(0)) / fast
    slow_mean = sum(closes[-slow:], Decimal(0)) / slow
    breakout = max(b[0] for b in clean[-21:-1])
    signal = "entry_candidate" if closes[-1] > fast_mean > slow_mean and closes[-1] > breakout else "exit_review" if closes[-1] < slow_mean else "hold"
    entry, equity, cash, cap, step, minimum, tick = (number(inputs[k]) for k in
        ("entry", "equity", "cash_cap", "notional_cap", "increment", "minimum", "tick"))
    if min(entry, equity, step, minimum, tick) <= 0 or min(cash, cap) < 0:
        raise ValueError("Invalid account or instrument inputs")
    fee = number(inputs["fee_bps"] if inputs["fee_bps"] is not None else (25 if kind == "crypto" else 0)) / 10000
    if not 0 <= fee <= Decimal("0.02"):
        raise ValueError("Fee assumption outside supported range")
    risk_fraction = Decimal("0.0025") if horizon == "swing" else Decimal("0.001")
    distance = atr * (Decimal(2) if horizon == "swing" else Decimal("1.5"))
    stop = floor_step(entry-distance, tick)
    if stop <= 0 or stop >= entry:
        raise ValueError("ATR stop reference is outside positive prices")
    # Explicit stress assumptions: round-trip fees + 10bp adverse slippage +
    # 1% ETF / 2% crypto gap beyond the reference stop. No loss guarantee.
    buffer = entry * (2*fee + Decimal("0.001") + (Decimal("0.02") if kind == "crypto" else Decimal("0.01")))
    unit_loss = entry-stop+buffer
    net_target_reward = 2*(entry-stop)-entry*(2*fee+Decimal("0.001"))
    reward_ratio = net_target_reward/unit_loss
    cost_viable = net_target_reward > 0 and reward_ratio >= 1
    if signal == "entry_candidate" and not cost_viable:
        signal = "hold"
    budget = equity*risk_fraction
    qty = floor_step(min(budget/unit_loss, cash/(entry*(1+fee)), cap/entry), step)
    if qty < minimum:
        qty = Decimal(0)
    canonical = json.dumps(inputs, sort_keys=True, separators=(",", ":"), default=str, allow_nan=False)
    return {"version": VERSION, "input_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
            "status": "research-only", "execution_enabled": False, "signal": signal,
            "symbol": provenance[0], "source": provenance[1], "feed": provenance[2], "as_of": inputs["as_of"],
            "horizon": horizon, "bars": len(bars), "atr14_wilder": str(atr),
            "fast_sma": str(fast_mean), "slow_sma": str(slow_mean), "breakout_reference": str(breakout),
            "entry_reference": str(entry), "stop_reference": str(stop),
            "target_reference": str(entry+2*(entry-stop)),
            "risk_fraction": str(risk_fraction), "planned_loss_budget": str(budget),
            "stress_loss_per_unit": str(unit_loss), "fee_bps_per_side": str(fee*10000),
            "net_target_reward_per_unit": str(net_target_reward), "reward_to_stress_loss": str(reward_ratio),
            "cost_hurdle_passed": cost_viable,
            "quantity": str(qty), "notional": str(qty*entry), "planned_stress_loss": str(qty*unit_loss),
            "reason": "Target fails the configured net reward/stress-loss hurdle" if not cost_viable else "Trend and prior-20-bar breakout" if signal == "entry_candidate" else "No entry signal; proposed size is for analysis only",
            "limitations": ["User-supplied historical bars require provenance verification",
                "Stop and target are planning references; no protective order is placed",
                "Gap, fees and slippage can exceed these assumptions", "No profitability or predictive accuracy validation"]}
