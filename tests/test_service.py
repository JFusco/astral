import asyncio
import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.broker import AlpacaPaper, BrokerFailure, Simulator, D
from backend.config import Settings
from backend.engine import Engine, RuleViolation
from backend.store import Store


def run(coro):
    return asyncio.run(coro)


def intent(cid="astral-12345678", **kwargs):
    return {"client_order_id": cid, "symbol": "BTC", "side": "buy", "notional": 250.0,
            "execution": "bounded", "ttl_seconds": 60, "strategy_id": "lifecycle_test", **kwargs}


@pytest.fixture
def engine(tmp_path):
    cfg = Settings(mode="simulator", db_path=tmp_path/"state.sqlite", enable_orders=True)
    store = Store(cfg.db_path, cfg.mode)
    e = Engine(cfg, store)
    run(e.refresh_quotes());run(e.reconcile())
    yield e
    store.close()


def test_persistent_trade_accounting_and_restart(engine):
    e = engine
    first = run(e.place(intent()))
    assert first["status"] == "filled"
    s = e.state();assert s["account"]["cash"] < 100000
    assert s["account"]["net"] == pytest.approx(s["account"]["realized"]+s["account"]["unrealized"])
    assert len(s["fills"]) == 1
    reopened = Engine(e.settings, e.store)
    run(reopened.reconcile())
    assert reopened.state()["account"]["equity"] == s["account"]["equity"]
    assert len(reopened.state()["fills"]) == 1
    sale = run(reopened.place(intent("astral-sell1234", side="sell")))
    assert sale["status"] == "filled"
    s = reopened.state()
    assert s["account"]["net"] == pytest.approx(s["account"]["realized"]+s["account"]["unrealized"])


def test_concurrent_duplicate_intent_submits_once(engine):
    calls = []
    original = engine.broker.submit
    async def submit(payload):
        calls.append(payload);return await original(payload)
    engine.broker.submit = submit
    async def both():
        return await asyncio.gather(engine.place(intent()), engine.place(intent()))
    a, b = run(both())
    assert a["client_id"] == b["client_id"]
    assert len(calls) == 1
    assert len(engine.state()["fills"]) == 1
    with pytest.raises(RuleViolation, match="different intent"):
        run(engine.place(intent(notional=200)))


def test_accepted_timeout_recovered_without_second_post(engine):
    calls = []
    original = engine.broker.submit
    async def timeout_after_accept(payload):
        calls.append(payload);await original(payload)
        raise BrokerFailure("Timeout")
    engine.broker.submit = timeout_after_accept
    assert run(engine.place(intent()))["status"] == "unknown"
    assert not engine.connected
    assert run(engine.place(intent()))["status"] == "unknown"
    reopened = Engine(engine.settings, engine.store)
    run(reopened.reconcile())
    assert reopened.store.order(intent()["client_order_id"])["status"] == "filled"
    assert len(reopened.state()["fills"]) == 1
    assert len(calls) == 1


def test_unknown_404_is_not_permission_to_resubmit(engine):
    async def timeout(payload): raise BrokerFailure("Timeout before response")
    engine.broker.submit = timeout
    assert run(engine.place(intent()))["status"] == "unknown"
    run(engine.reconcile())
    with pytest.raises(RuleViolation, match="Uncertain orders"):
        run(engine.place(intent("astral-second123")))
    assert engine.store.order(intent()["client_order_id"])["status"] == "unknown"


def test_halt_blocks_buy_but_allows_sell_and_survives_restart(engine):
    run(engine.place(intent()))
    engine.store.put("halted", True)
    with pytest.raises(RuleViolation, match="halted"):
        run(engine.place(intent("astral-block123")))
    assert run(engine.place(intent("astral-exit1234", side="sell")))["status"] == "filled"
    assert Engine(engine.settings, engine.store).state()["halted"]
    assert engine.state()["learning"]["observations"] == 3


@pytest.mark.parametrize("offset", [-100, 100])
def test_stale_or_future_quote_blocks_orders(engine, offset):
    quotes = engine.store.get("quotes")
    quotes["BTC"]["at"] = (datetime.now(timezone.utc)+timedelta(seconds=offset)).isoformat()
    engine.store.put("quotes", quotes)
    with pytest.raises(RuleViolation, match="Quote"):
        run(engine.place(intent()))
    assert not engine.store.rows("SELECT * FROM orders")


def test_stale_account_and_closed_etf_session(engine):
    snap = engine.store.get("account_snapshot")
    snap["at"] = (datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat()
    engine.store.put("account_snapshot", snap)
    with pytest.raises(RuleViolation, match="snapshot"):
        run(engine.place(intent()))
    run(engine.reconcile());snap = engine.store.get("account_snapshot")
    snap["clock"]["is_open"] = False;engine.store.put("account_snapshot", snap)
    with pytest.raises(RuleViolation, match="session is closed"):
        run(engine.place(intent(symbol="SPY", notional=700)))


def test_pending_cash_reservation_and_short_prevention(engine):
    assert run(engine.place(intent(execution="patient", notional=1000)))["status"] == "new"
    snap = engine.store.get("account_snapshot");snap["account"]["cash"] = "1100"
    engine.store.put("account_snapshot", snap)
    with pytest.raises(RuleViolation, match="unreserved cash"):
        run(engine.place(intent("astral-next1234", notional=250)))
    with pytest.raises(RuleViolation, match="position quantity"):
        run(engine.place(intent("astral-sell1234", side="sell")))


def test_loss_guard_and_total_exposure_include_working_orders(engine):
    run(engine.place(intent(execution="patient", notional=1000)))
    snap = engine.store.get("account_snapshot")
    snap["positions"] = [{"symbol": "TLT", "qty": "530", "market_value": "49000", "cost_basis": "49000", "unrealized_pl": "0"}]
    engine.store.put("account_snapshot", snap)
    with pytest.raises(RuleViolation, match="Aggregate exposure"):
        run(engine.place(intent("astral-cap12345")))
    snap["positions"] = [];snap["account"]["equity"] = "98000";engine.store.put("account_snapshot", snap)
    with pytest.raises(RuleViolation, match="circuit breaker"):
        run(engine.place(intent("astral-loss1234")))


def test_partial_fills_deduplicated_and_incremental_price(engine):
    row = run(engine.place(intent(execution="patient")))
    raw = row["broker"]
    raw.update(status="partially_filled", filled_qty="0.001", filled_avg_price="67500")
    engine.ingest(raw);engine.ingest(raw)
    raw.update(filled_qty="0.002", filled_avg_price="67510")
    engine.ingest(raw);engine.ingest(raw)
    fills = engine.state()["fills"]
    assert len(fills) == 2
    assert sum(D(f["quantity"]) for f in fills) == D(".002")
    assert D(fills[0]["price"]) == D("67520")


def test_fill_during_cancel_is_not_lost(engine):
    run(engine.place(intent(execution="patient")))
    original = engine.broker.cancel
    async def racing_cancel(broker_id):
        with engine.store.transaction():
            state = engine.store.get("simulator")
            raw = state["orders"][intent()["client_order_id"]]
            raw["type"] = "market";engine.broker.match(state, raw)
            engine.store.put("simulator", state)
        return await original(broker_id)
    engine.broker.cancel = racing_cancel
    result = run(engine.cancel(intent()["client_order_id"]))
    assert result["status"] == "filled"
    assert len(engine.state()["fills"]) == 1
    assert engine.state()["account"]["cash"] < 100000


def test_expiry_keeps_reservation_until_canceled_readback(engine):
    run(engine.place(intent(execution="patient")))
    engine.store.db.execute("UPDATE orders SET deadline=0")
    run(engine.reconcile())
    assert engine.store.order(intent()["client_order_id"])["status"] == "pending_cancel"
    run(engine.reconcile())
    assert engine.store.order(intent()["client_order_id"])["status"] == "canceled"


def test_mode_and_account_binding(engine):
    with pytest.raises(ValueError, match="another execution mode"):
        Store(engine.settings.db_path, "alpaca")
    engine.store.put("account_binding", "different-paper-account")
    other = Engine(engine.settings, engine.store)
    with pytest.raises(BrokerFailure, match="different paper account"):
        run(other.reconcile())


def test_api_boundary_validation_and_persistence(tmp_path):
    cfg = Settings(mode="simulator", db_path=tmp_path/"api.sqlite", enable_orders=True)
    headers = {"X-Astral-Intent": "paper-only"}
    with TestClient(create_app(cfg, background=False), base_url="http://localhost") as client:
        assert client.get("/api/health").json()["broker_ready"]
        assert client.post("/api/orders", json=intent()).status_code == 403
        assert client.post("/api/orders", json=intent(), headers={**headers,"Origin":"https://evil.example"}).status_code == 403
        assert client.post("/api/orders", json=intent(notional=-1), headers=headers).status_code == 422
        assert client.post("/api/orders", json=intent(), headers=headers).json()["status"] == "filled"
        assert client.post("/api/halt", json={"halted":True}, headers=headers).status_code == 200
        assert client.get("/api/state", headers={"Host":"evil.example"}).status_code == 400
        first = client.get("/api/state").json()
    with TestClient(create_app(cfg, background=False), base_url="http://localhost") as client:
        recovered = client.get("/api/state").json()
        assert recovered["halted"] and len(recovered["fills"]) == 1
        assert recovered["account"]["cash"] == first["account"]["cash"]


def test_unconfigured_alpaca_never_falls_back_to_simulator(tmp_path):
    cfg = Settings(db_path=tmp_path/"paper.sqlite")
    with TestClient(create_app(cfg), base_url="http://localhost") as client:
        s = client.get("/api/state").json()
        assert s["mode"] == "alpaca" and not s["configured"] and not s["connected"]
        assert s["account"]["equity"] is None and not s["fills"]
        assert all(a["price"] is None for a in s["assets"])
        assert "100000" not in json.dumps(s)


def test_live_host_configuration_rejected(monkeypatch):
    monkeypatch.setenv("APCA_API_BASE_URL", "https://api.alpaca.markets")
    with pytest.raises(ValueError, match="paper host"):
        Settings.from_env()


def test_adapter_fixed_hosts_no_post_retries_and_cooldown(tmp_path):
    cfg = Settings(mode="alpaca", db_path=tmp_path/"adapter.sqlite", api_key="secret-key", secret_key="secret-value")
    store = Store(cfg.db_path, cfg.mode);seen = []
    def handle(request):
        seen.append((request.method, request.url.host))
        if request.method == "POST": raise httpx.ReadTimeout("Uncertain", request=request)
        return httpx.Response(429, headers={"Retry-After":"60"})
    adapter = AlpacaPaper(cfg, store, httpx.MockTransport(handle))
    async def scenario():
        with pytest.raises(BrokerFailure): await adapter.submit({"client_order_id":"astral-mock1234"})
        with pytest.raises(BrokerFailure): await adapter.get_order("astral-mock1234")
        with pytest.raises(BrokerFailure, match="cooldown"): await adapter.get_order("astral-mock1234")
        await adapter.close()
    run(scenario())
    assert seen == [("POST","paper-api.alpaca.markets"),("GET","paper-api.alpaca.markets")]
    assert "secret-key" not in json.dumps(store.get("last_api_call"))
    store.close()


def test_definitive_provider_rejection_not_an_uncertain_order(engine):
    async def rejected(payload): raise BrokerFailure("HTTP 422", 422)
    engine.broker.submit = rejected
    assert run(engine.place(intent()))["status"] == "rejected"
    assert not engine.state()["fills"]


def test_expired_metadata_is_reloaded(engine):
    metadata = engine.store.get("assets")
    for a in metadata.values(): a["at"] = "2020-01-01T00:00:00+00:00"
    engine.store.put("assets", metadata)
    run(engine.refresh_quotes())
    assert engine.store.get("assets")["BTC"]["at"] != "2020-01-01T00:00:00+00:00"


def test_event_replay_is_ordered_and_does_not_repeat_consumed_rows(engine):
    before = engine.state()["sequence"]
    run(engine.place(intent()))
    rows = engine.store.events_after(before)
    assert any(r["type"] == "fill" for r in rows)
    assert [r["seq"] for r in rows] == sorted(r["seq"] for r in rows)
    assert not engine.store.events_after(rows[-1]["seq"])


def test_only_one_executor_can_own_database(tmp_path):
    cfg = Settings(mode="simulator", db_path=tmp_path/"locked.sqlite")
    with TestClient(create_app(cfg, background=False), base_url="http://localhost"):
        with pytest.raises(RuntimeError, match="Another ASTRAL executor"):
            with TestClient(create_app(cfg, background=False), base_url="http://localhost"):
                pass
