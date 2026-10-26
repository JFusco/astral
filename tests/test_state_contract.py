"""Dashboard read-path contract: fixed Store-seeded ledgers and a pinned clock.

The golden file was captured from the pre-optimization implementation. Never
regenerate it from changed code to make this test pass.
"""
from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from backend.config import Settings
from backend.engine import Engine
from backend.store import Store, dumps

FIXTURE = Path(__file__).with_name("fixtures")/"state_contract.json"
FIXED = datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc)
# Keys deliberately removed from state() after the golden capture (P1d only).
REMOVED = set()


class FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return FIXED if tz else FIXED.replace(tzinfo=None)


def pin_clock(mp):
    mp.setattr("backend.engine.datetime", FixedDateTime)
    mp.setattr("backend.engine.utcnow", lambda: FIXED.isoformat())


def at(seconds_before):
    return datetime.fromtimestamp(FIXED.timestamp()-seconds_before, timezone.utc).isoformat()


def seed(store):
    order = lambda cid, side, qty, status, raw: (cid, dumps({"intent": {"client_order_id": cid, "symbol": "BTC", "side": side, "notional": 100.0,
                                                  "execution": "bounded", "ttl_seconds": 60, "strategy_id": "manual"},
                                                  "payload": {"client_order_id": cid, "symbol": "BTC/USD", "qty": qty, "side": side,
                                                              "type": "limit", "time_in_force": "ioc", "limit_price": "67600"}}),
                                                 dumps(raw), status, 0, FIXED.timestamp()+60, at(300), at(290))
    with store.transaction():
        store.put("assets", {s: {"symbol": s, "broker_symbol": b, "type": k, "tradable": True, "increment": "0.000001" if k == "crypto" else "1",
                                 "minimum": "0.000001" if k == "crypto" else "1", "price_increment": "0.01", "source": "simulator", "at": at(600)}
                             for s, b, k in (("BTC", "BTC/USD", "crypto"), ("SPY", "SPY", "etf"))})
        store.put("quotes", {"BTC": {"bid": "67500", "ask": "67510", "at": at(5), "received_at": at(4), "source": "synthetic"},
                             "SPY": {"bid": "580.1", "ask": "580.2", "at": at(40), "received_at": at(39), "source": "synthetic"}})
        store.put("account_snapshot", {"account": {"id": "persistent-simulator", "cash": "99900.5", "equity": "100001.25", "status": "ACTIVE",
                                                   "trading_blocked": False, "realized": "-0.25", "fees": "0.25"},
                                       "positions": [{"symbol": "BTC/USD", "qty": "0.0015", "cost_basis": "100.75", "market_value": "101.25",
                                                      "current_price": "67505", "unrealized_pl": "0.5"}],
                                       "clock": {"is_open": True, "source": "simulator-not-an-exchange-calendar"}, "at": at(8)})
        store.put("baseline_equity", "100000")
        store.put("halted", False)
        store.put("research_packets", [{"symbol": "BTC", "as_of": at(100), "expires_at": at(-200), "eligible": False,
                                        "facts": {"signal": "hold"}, "vetoes": ["Fixture veto"], "evidence": [], "input_hash": "0"*64}])
        store.put("research_review", {"status": "disabled", "execution_enabled": False})
        store.put("exit_plans", {})
        rows = [order("astral-fixture-buy1", "buy", "0.0015", "filled",
                      {"id": "sim-1", "client_order_id": "astral-fixture-buy1", "symbol": "BTC/USD", "side": "buy", "qty": "0.0015",
                       "status": "filled", "filled_qty": "0.0015", "filled_avg_price": "67166.66", "filled_at": at(295), "fee": "0.25"}),
                order("astral-fixture-open", "buy", "0.001", "new",
                      {"id": "sim-2", "client_order_id": "astral-fixture-open", "symbol": "BTC/USD", "side": "buy", "qty": "0.001",
                       "status": "new", "filled_qty": "0"})]
        store.db.executemany("INSERT INTO orders VALUES(?,?,?,?,?,?,?,?)", rows)
        store.db.execute("INSERT INTO fills VALUES(?,?,?,?)", ("astral-fixture-buy1:0.0015", "astral-fixture-buy1", at(295),
                         dumps({"id": "astral-fixture-buy1:0.0015", "client_id": "astral-fixture-buy1", "symbol": "BTC", "side": "buy",
                                "quantity": "0.0015", "price": "67166.66", "value": "100.74999", "fee": "0.25", "at": at(295), "source": "simulator"})))
        store.db.executemany("INSERT INTO equity(at,value) VALUES(?,?)", [(at(120-30*i), str(100000+i)) for i in range(4)])
        store.db.executemany("INSERT INTO events(at,type,payload) VALUES(?,?,?)",
                             [(at(300), "service_started", dumps({"mode": "simulator", "paper_only": True})),
                              (at(295), "fill", dumps({"client_id": "astral-fixture-buy1"}))])
        store.db.execute("INSERT INTO news VALUES(?,?,?)", ("n1", at(900), dumps({"id": "n1", "headline": "Fixture headline", "source": "fixture",
                         "symbols": ["BTCUSD"], "url": None, "created_at": at(900), "updated_at": at(900), "first_seen_at": at(850)})))
        store.db.execute("INSERT INTO activities VALUES(?,?,?,?)", ("fee-1", "CFEE", at(280), dumps({"id": "fee-1", "activity_type": "CFEE",
                         "status": "executed", "symbol": "BTCUSD", "qty": "-0.000001"})))
        store.db.execute("INSERT INTO shadow(at,intent,result,context,input_hash) VALUES(?,?,?,?,?)",
                         (at(60), dumps({"symbol": "BTC"}), dumps({"decision": "veto", "reason": "Fixture"}), "{}", "1"*64))
        store.db.execute("INSERT INTO timing(at,symbol,strategy,result,context) VALUES(?,?,?,?,?)",
                         (at(60), "BTC", "swing", dumps({"action": "wait", "reason": "Fixture"}), "{}"))
        store.db.execute("INSERT INTO observations(at,request,outcome,context) VALUES(?,?,?,?)", (at(300), "{}", "approved", "{}"))


def build_state(directory, mp):
    pin_clock(mp)
    cfg = Settings(mode="simulator", db_path=Path(directory)/"contract.sqlite", enable_orders=True)
    store = Store(cfg.db_path, cfg.mode)
    try:
        seed(store)
        e = Engine(cfg, store)
        e.connected = True
        e.workers = {"quotes": {"name": "quotes", "status": "healthy", "detail": "Synthetic", "at": at(3), "duration_ms": 4},
                     "execution": {"name": "execution", "status": "healthy", "detail": "Intent submitted once and read back",
                                   "at": at(290), "duration_ms": None}}
        return e.state()
    finally:
        store.close()


def normalize(state):
    # Only generated clock/elapsed values vary between runs. Check their
    # presence and type first so a missing field cannot hide in the normalizer.
    state = json.loads(json.dumps(state))
    assert isinstance(state["server_time"], str) and type(state["uptime_seconds"]) is int
    state["server_time"], state["uptime_seconds"] = "<server_time>", "<uptime_seconds>"
    for worker in state["workers"]:
        assert isinstance(worker["at"], str) and (worker["duration_ms"] is None or type(worker["duration_ms"]) is int)
        worker["at"] = "<worker_at>"
        if worker["duration_ms"] is not None: worker["duration_ms"] = "<duration_ms>"
    return state


def test_state_matches_base_contract(tmp_path, monkeypatch):
    expected = json.loads(FIXTURE.read_text())
    for key in REMOVED: expected.pop(key)
    assert json.dumps(normalize(build_state(tmp_path, monkeypatch)), sort_keys=True) == json.dumps(expected, sort_keys=True)


# --- /api/health: same predicate and fields as before, without state() -----

from contextlib import contextmanager
from datetime import timedelta
from decimal import Decimal
import socket
import threading
import time

import httpx
import uvicorn
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.broker import D
from backend.engine import RuleViolation


@pytest.mark.parametrize("case", ["fresh", "boundary", "stale", "future", "missing", "disconnected", "unconfigured"])
def test_health_matches_state_readiness_without_building_state(tmp_path, monkeypatch, case):
    pin_clock(monkeypatch)
    cfg = Settings(mode="alpaca" if case == "unconfigured" else "simulator", db_path=tmp_path/"health.sqlite")
    app = create_app(cfg, background=False)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        e = app.state.engine
        snap = e.store.get("account_snapshot")
        offsets = {"fresh": 5, "boundary": cfg.max_snapshot_age, "stale": cfg.max_snapshot_age+0.001, "future": -60}
        if case in offsets: e.store.put("account_snapshot", {**snap, "at": at(offsets[case])})
        if case == "missing": e.store.db.execute("DELETE FROM state WHERE key='account_snapshot'")
        if case == "disconnected": e.connected = False
        expected = e.state()
        original, calls = e.state, []
        e.state = lambda: calls.append(1) or original()
        body = client.get("/api/health").json()
        assert not calls
        assert set(body) == {"service_version", "alive", "paper_only", "mode", "configured", "broker_ready", "orders_enabled", "uptime_seconds"}
        assert body["broker_ready"] is expected["connected"]
        assert abs(body["uptime_seconds"]-expected["uptime_seconds"]) <= 1
        assert (body["mode"], body["configured"], body["orders_enabled"]) == (expected["mode"], expected["configured"], expected["orders_enabled"])
        assert body["broker_ready"] is (case in ("fresh", "boundary", "future"))


# --- SSE: framing, replay, shared frame lifetime, failure and isolation ----

def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0));return s.getsockname()[1]


@contextmanager
def serving(app):
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=free_port(), log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True);thread.start()
    deadline = time.monotonic()+15
    while not server.started:
        assert time.monotonic() < deadline and thread.is_alive(), "server did not start"
        time.sleep(.02)
    try:
        yield f"http://127.0.0.1:{server.config.port}"
    finally:
        server.should_exit = True;thread.join(15)
        assert not thread.is_alive(), "a stream kept the server from shutting down"


class Stream:
    """Bounded SSE reader yielding (id, event, data) blocks."""
    def __init__(self, base, after=None, last_id=None):
        headers = {"last-event-id": str(last_id)} if last_id is not None else {}
        self.client = httpx.Client(base_url=base, timeout=httpx.Timeout(5, read=8), trust_env=False)
        self.cm = self.client.stream("GET", "/api/events"+(f"?after={after}" if after is not None else ""), headers=headers)
        self.lines = self.cm.__enter__().iter_lines()
    def next(self, event=None, limit=8):
        block, deadline = {}, time.monotonic()+limit
        for line in self.lines:
            assert time.monotonic() < deadline, "timed out waiting for "+str(event)
            if line == "":
                if "event" in block and (event is None or block["event"] == event): return block
                block = {}
            elif not line.startswith(":"):
                key, _, value = line.partition(": ");block[key] = value
        raise AssertionError("stream ended")
    def close(self):
        self.cm.__exit__(None, None, None);self.client.close()


def stream_app(tmp_path, name="sse"):
    return create_app(Settings(mode="simulator", db_path=tmp_path/(name+".sqlite"), enable_orders=True), background=False)


def test_sse_framing_replay_and_disconnect_are_per_client(tmp_path):
    app = stream_app(tmp_path)
    with serving(app) as base:
        store = app.state.engine.store
        for i in range(3): store.event("fixture", {"n": i})
        last = store.rows("SELECT MAX(seq) n FROM events")[0]["n"]
        a, b = Stream(base, after=0), Stream(base, last_id=last-1)
        seen = []
        while not seen or seen[-1] < last:
            block = a.next("ledger");seen.append(int(block["id"]))
            assert json.loads(block["data"])["seq"] == seen[-1]
        assert seen == sorted(seen) and len(seen) == len(set(seen)) and seen[0] == 1
        assert int(b.next("ledger")["id"]) == last
        a.close()
        store.event("after-disconnect", {})
        assert json.loads(b.next("ledger")["data"])["type"] == "after-disconnect"
        assert json.loads(b.next("state")["data"])["service_version"] == "0.2"
        b.close()


def test_sse_streams_share_one_frame_that_expires(tmp_path):
    app = stream_app(tmp_path)
    with serving(app) as base:
        e = app.state.engine;original, calls = e.state, []
        e.state = lambda: calls.append(1) or original()
        a = Stream(base);first = a.next("state")["data"]
        started = time.monotonic();b = Stream(base);second = b.next("state", limit=1.5)["data"]
        assert time.monotonic()-started < 1.5, "a new client must get its first frame immediately"
        assert first == second and len(calls) == 1
        e.store.put("halted", True)
        deadline = time.monotonic()+4.5
        while not json.loads(a.next("state", limit=4.5)["data"])["halted"]:
            assert time.monotonic() < deadline, "mutation not visible after frame expiry"
        assert len(calls) >= 2
        a.close();b.close()


def test_failed_rebuild_never_delivers_the_expired_frame(tmp_path):
    app = stream_app(tmp_path)
    with serving(app) as base:
        e = app.state.engine;original = e.state
        a = Stream(base);old = a.next("state")["data"];a.close()
        app.state.state_frame["at"] -= 3
        def broken(): raise RuntimeError("fixture state failure")
        e.state = broken
        b = Stream(base);blocks = [];deadline = time.monotonic()+6
        try:
            while time.monotonic() < deadline:
                try: blocks.append(b.next("state", limit=min(3, deadline-time.monotonic())))
                except (AssertionError, httpx.HTTPError): break
            else: pytest.fail("state stream did not fail within the overall deadline")
            assert not blocks, "failed rebuild delivered a state frame"
        finally:
            b.close()
        assert app.state.state_frame["body"] is None
        e.state = original;e.store.put("halted", True)
        c = Stream(base);fresh = c.next("state")["data"];c.close()
        assert fresh != old and json.loads(fresh)["halted"] is True


def test_separate_apps_never_share_frames(tmp_path):
    first, second = stream_app(tmp_path, "one"), stream_app(tmp_path, "two")
    with serving(first) as one, serving(second) as two:
        first.state.engine.store.put("halted", True)
        a, b = Stream(one), Stream(two)
        assert json.loads(a.next("state")["data"])["halted"] is True
        assert json.loads(b.next("state")["data"])["halted"] is False
        assert first.state.state_frame is not second.state.state_frame
        a.close();b.close()


# --- S4: execution enforcement matches the matching planning semantics -----
# Protected modules are called, never edited. risk.propose's ATR loss-budget
# fraction is a different quantity and is deliberately not compared here.

from backend.readiness import view as readiness_view
from backend.research import screen
from test_dogfood import selection_fixture


def risk_engine(tmp_path, as_of, *, positions=(), quotes=None, clock_open=True):
    cfg = Settings(mode="simulator", db_path=tmp_path/"risk.sqlite", enable_orders=True)
    store = Store(cfg.db_path, cfg.mode)
    store.put("assets", {"BTC": {"symbol": "BTC", "broker_symbol": "BTC/USD", "type": "crypto", "tradable": True, "increment": "0.000001",
                                 "minimum": "0.000001", "price_increment": "0.01", "source": "fixture", "at": as_of},
                         "SPY": {"symbol": "SPY", "broker_symbol": "SPY", "type": "etf", "tradable": True, "increment": "1",
                                 "minimum": "1", "price_increment": "0.01", "source": "fixture", "at": as_of}})
    store.put("quotes", quotes or {"BTC": {"bid": "169.99", "ask": "170", "at": as_of}, "SPY": {"bid": "99.99", "ask": "100", "at": as_of}})
    store.put("account_snapshot", {"account": {"id": "fixture", "equity": "100000", "cash": "100000", "status": "ACTIVE"},
                                   "positions": list(positions), "clock": {"is_open": clock_open}, "at": as_of})
    e = Engine(cfg, store);e.connected = True
    return e, store


def buy(symbol, notional, strategy="manual"):
    return {"client_order_id": "astral-parity-0001", "symbol": symbol, "side": "buy", "notional": notional,
            "execution": "bounded", "ttl_seconds": 60, "strategy_id": strategy}


def test_swing_full_value_cap_matches_research_proposal_boundary(tmp_path):
    data = selection_fixture();data["quote"].update(bid="169.99", ask="170")
    facts = screen(**data)["facts"]
    qty, step = D(facts["proposed_quantity"]), D("0.000001")
    entry = D("170")*D("1.001")  # research entry; tick-aligned, so equal to the execution limit
    cap = D("100000")*D("0.0025")/D("1.003")
    assert qty*entry <= cap < (qty+step)*entry, "research cap must bind for this probe"
    e, store = risk_engine(tmp_path, data["as_of"])
    try:
        payload = e.risk_payload(buy("BTC", str(qty*entry), "swing"), shadow=True, as_of=data["as_of"])
        assert D(payload["qty"]) == qty and D(payload["limit_price"]) == entry
        with pytest.raises(RuleViolation, match="Strategy unprotected loss budget"):
            e.risk_payload(buy("BTC", str((qty+step)*entry), "swing"), shadow=True, as_of=data["as_of"])
    finally:
        store.close()


def test_quote_freshness_boundary_matches_across_research_readiness_and_execution(tmp_path, monkeypatch):
    limit = Settings().max_quote_age
    assert limit == 15
    data = selection_fixture();now = datetime.fromisoformat(data["as_of"])
    stamp = lambda seconds: (now-timedelta(seconds=seconds)).isoformat()
    for seconds, fresh in ((limit, True), (limit+0.001, False)):
        data["quote"]["at"] = stamp(seconds)
        assert ("Quote is stale or future-dated" in screen(**data)["vetoes"]) is not fresh
        e, store = risk_engine(tmp_path/str(seconds), data["as_of"], quotes={"BTC": {"bid": "169.99", "ask": "170", "at": stamp(seconds)}})
        try:
            if fresh: e.risk_payload(buy("BTC", "100"), shadow=True, as_of=data["as_of"])
            else:
                with pytest.raises(RuleViolation, match="Quote is missing, stale"):
                    e.risk_payload(buy("BTC", "100"), shadow=True, as_of=data["as_of"])
            monkeypatch.setattr("backend.readiness.utcnow", lambda: data["as_of"])
            store.put("quotes", {"BTC": {"bid": "169.99", "ask": "170", "at": stamp(seconds), "size_unit": "base_asset",
                                         "depth": {"status": "validated", "at": data["as_of"]}}})
            assert readiness_view(store)["symbols"][0]["depth"]["passed"] is fresh
        finally:
            store.close()


@pytest.mark.parametrize("symbol,held,over,under", [("BTC", "4800", "250", "150"), ("SPY", "9800", "300", "150")])
def test_advertised_concentration_fraction_is_the_enforced_boundary(tmp_path, symbol, held, over, under):
    as_of = "2026-10-24T00:00:00+00:00"
    broker = "BTC/USD" if symbol == "BTC" else "SPY"
    position = {"symbol": broker, "qty": "1", "market_value": held, "cost_basis": held, "unrealized_pl": "0", "current_price": held}
    e, store = risk_engine(tmp_path, as_of, positions=[position])
    try:
        fraction = D(e.risk_policy()["crypto_fraction" if symbol == "BTC" else "etf_fraction"])
        cap = D("100000")*fraction
        worst = D("170.17") if symbol == "BTC" else D("100.10")
        increment = D("0.000001") if symbol == "BTC" else D("1")
        for notional, expected in ((over, "Instrument concentration cap"), (under, "Shared unprotected full-value loss budget")):
            filled = (D(notional)/worst/increment).to_integral_value(rounding="ROUND_DOWN")*increment*worst
            assert (D(held)+filled > cap) is (expected.startswith("Instrument"))
            # Below the advertised fraction, the tighter 0.5% unprotected full-value budget is the binding veto.
            with pytest.raises(RuleViolation, match=expected):
                e.risk_payload(buy(symbol, notional), shadow=True, as_of=as_of)
    finally:
        store.close()
