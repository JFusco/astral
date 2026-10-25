from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal, localcontext

import pytest

from backend.risk import propose
from backend.engine import RuleViolation
from test_service import engine, intent, run


def inputs(horizon="swing", kind="crypto"):
    now = datetime(2026, 10, 24, 0, 0, tzinfo=timezone.utc)
    period = timedelta(days=1) if horizon == "swing" else timedelta(minutes=5)
    bars = []
    for i in range(61):
        end = now-period*(60-i)
        p = 100+i
        bars.append({"symbol": "BTC", "source": "unit-fixture", "feed": "fixture", "adjustment": "raw",
                     "at": (end-period).isoformat(), "closed_at": end.isoformat(), "known_at": end.isoformat(),
                     "open": str(p), "high": str(p+1), "low": str(p-1), "close": str(p), "volume": "10"})
    bars[-1].update(high="172", close="170")
    return dict(bars=bars, horizon=horizon, kind=kind, as_of=now.isoformat(), entry="171",
                equity="100000", cash_cap="100000", notional_cap="1000", increment="0.000001", minimum="0.000001", tick="0.01")


def test_exact_wilder_atr_and_repeatable_sizing():
    data = inputs()
    first = propose(**data)
    # First 59 TRs are 2; final TR=13. Wilder update: (2*13+13)/14.
    assert Decimal(first["atr14_wilder"]) == Decimal("2.785714285714285714285714285714286")
    assert first["signal"] == "entry_candidate"
    assert Decimal(first["planned_stress_loss"]) <= Decimal(first["planned_loss_budget"])
    assert Decimal(first["notional"]) <= 1000
    assert not first["execution_enabled"]
    with localcontext() as context:
        context.prec = 9
        assert propose(**data) == first
    assert data == inputs()  # Calculator did not mutate the original evidence.


@pytest.mark.parametrize("change", ["future", "duplicate", "mixed_feed", "known_early", "zero_volume", "nan", "invalid_ohlc", "stale", "too_few", "malformed"])
def test_bad_bars_abstain(change):
    data = inputs()
    if change == "future": data["bars"][-1]["known_at"] = "2027-01-01T00:00:00Z"
    if change == "duplicate": data["bars"][-1] = deepcopy(data["bars"][-2])
    if change == "mixed_feed": data["bars"][-1]["feed"] = "other"
    if change == "known_early": data["bars"][-1]["known_at"] = data["bars"][-1]["at"]
    if change == "zero_volume": data["bars"][-1]["volume"] = "0"
    if change == "nan": data["bars"][-1]["close"] = "NaN"
    if change == "invalid_ohlc": data["bars"][-1]["low"] = "200"
    if change == "stale": data["as_of"] = "2026-11-01T00:00:00Z"
    if change == "too_few": data["bars"] = data["bars"][-14:]
    if change == "malformed": data["bars"][-1]["close"] = "banana"
    with pytest.raises(ValueError): propose(**data)


def test_intraday_budget_costs_minimum_and_cash():
    data = inputs("intraday")
    first = propose(**data)
    assert first["planned_loss_budget"] == "100.000"
    data.update(cash_cap="5", notional_cap="3", increment="1", minimum="1")
    assert Decimal(propose(**data)["quantity"]) == 0
    base = inputs();base["notional_cap"] = "100000"
    a = propose(**base)
    base["fee_bps"] = 100
    assert Decimal(propose(**base)["quantity"]) < Decimal(a["quantity"])


def test_missing_crypto_bar_rejected():
    data = inputs("intraday")
    del data["bars"][5]
    with pytest.raises(ValueError, match="Missing"): propose(**data)


def test_cost_hurdle_prevents_an_uneconomic_candidate():
    data = inputs();data["fee_bps"] = 200
    result = propose(**data)
    assert not result["cost_hurdle_passed"]
    assert result["signal"] == "hold"


def test_venue_power_is_not_double_reserved(engine):
    from dataclasses import replace
    run(engine.place(intent(execution="patient")))
    engine.settings = replace(engine.settings, mode="alpaca", api_key="fixture", secret_key="fixture")
    snap = engine.store.get("account_snapshot")
    snap["account"].update(crypto_status="ACTIVE", non_marginable_buying_power="260")
    engine.store.put("account_snapshot", snap)
    assert engine.risk_payload(intent("astral-next1234"))["side"] == "buy"
    snap["account"]["non_marginable_buying_power"] = "200"
    engine.store.put("account_snapshot", snap)
    with pytest.raises(RuleViolation, match="buying power"):
        engine.risk_payload(intent("astral-next1234"))


def test_exact_threshold_latches_across_reconcile_and_restart(engine):
    e = engine
    state = e.store.get("simulator");state["cash"] = "99000";e.store.put("simulator", state)
    run(e.reconcile())
    assert e.state()["risk_policy"]["latched"]
    state["cash"] = "100000";e.store.put("simulator", state)
    run(e.reconcile())
    with pytest.raises(RuleViolation, match="latched"):
        run(e.place(intent()))
    assert e.state()["halted"]


@pytest.mark.parametrize("flag", ["account_blocked", "trade_suspended_by_user"])
def test_account_restrictions_block(engine, flag):
    snap = engine.store.get("account_snapshot");snap["account"][flag] = True
    engine.store.put("account_snapshot", snap)
    with pytest.raises(RuleViolation, match="not enabled"): run(engine.place(intent()))


def test_market_cap_and_price_tick_never_weaken_bound(engine):
    with pytest.raises(RuleViolation, match="Market orders"):
        run(engine.place(intent(execution="market")))
    q = engine.store.get("quotes");q["BTC"].update(bid="100.001", ask="100.009")
    engine.store.put("quotes", q)
    payload = engine.risk_payload(intent())
    assert Decimal(payload["limit_price"]) <= Decimal("100.009")*Decimal("1.001")
    passive = engine.risk_payload(intent(execution="patient"))
    assert Decimal(passive["limit_price"]) <= Decimal("100.001")


def test_planner_records_but_cannot_submit(engine):
    data = inputs();candidate = {"symbol": "BTC", "horizon": "swing", "bars": data["bars"]}
    # Anchor the fixture relative to the service decision clock.
    shift = datetime.now(timezone.utc)-datetime.fromisoformat(data["as_of"])-timedelta(seconds=1)
    for b in candidate["bars"]:
        for k in ("at", "closed_at", "known_at"):
            b[k] = (datetime.fromisoformat(b[k])+shift).isoformat()
    before = engine.state()["sequence"]
    plan = engine.plan(candidate)
    assert plan["status"] == "research-only" and not plan["execution_enabled"]
    assert engine.store.events_after(before)[0]["type"] == "risk_plan"
    assert not engine.store.rows("SELECT * FROM orders")
    assert engine.state()["learning"]["observations"] == 1
