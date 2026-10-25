"""Fixed-host Alpaca paper adapter and a separately labelled durable simulator."""
import asyncio
import math
import time
import uuid
from collections import deque
from decimal import Decimal
from urllib.parse import quote

import httpx

from .config import DATA_URL, PAPER_URL, SYMBOLS
from .store import utcnow

def D(value):
    number = Decimal(str(value))
    if not number.is_finite():
        raise ValueError("Non-finite financial value")
    return number
TERMINAL = {"filled", "canceled", "expired", "rejected", "replaced"}


class BrokerFailure(Exception):
    def __init__(self, message, status=503):
        super().__init__(message)
        self.status = status


class Limiter:
    def __init__(self, normal=60, reserve=20):
        self.normal, self.reserve, self.calls = normal, reserve, deque()

    def take(self, critical=False):
        now = time.monotonic()
        while self.calls and self.calls[0] < now - 60:
            self.calls.popleft()
        if len(self.calls) >= self.normal + (self.reserve if critical else 0):
            raise BrokerFailure("Local request budget reached; capacity reserved for recovery", 429)
        self.calls.append(now)


class AlpacaPaper:
    def __init__(self, settings, store, transport=None):
        self.settings, self.store = settings, store
        self.http = httpx.AsyncClient(headers={"APCA-API-KEY-ID": settings.api_key,
                                              "APCA-API-SECRET-KEY": settings.secret_key},
                                      timeout=8, follow_redirects=False, trust_env=False, transport=transport)
        self.trading, self.data = Limiter(), Limiter(100, 10)
        self.cooldown = {"trading": 0, "data": 0}
        self.metadata = {}

    async def request(self, method, path, *, data=False, critical=False, **kwargs):
        if method != "GET" and not self.settings.enable_orders:
            raise BrokerFailure("Read-only adapter blocks broker writes", 403)
        if not self.settings.configured:
            raise BrokerFailure("Alpaca paper credentials are not configured")
        pool = "data" if data else "trading"
        if time.monotonic() < self.cooldown[pool]:
            raise BrokerFailure("Provider cooldown active", 429)
        (self.data if data else self.trading).take(critical)
        started = time.monotonic()
        try:
            response = await self.http.request(method, (DATA_URL if data else PAPER_URL) + path, **kwargs)
            self.store.put("last_api_call", {"pool": pool, "method": method, "path": path,
                                             "status": response.status_code, "at": utcnow(),
                                             "latency_ms": round((time.monotonic()-started)*1000),
                                             "remaining": response.headers.get("x-ratelimit-remaining")})
            self.store.event("api_request", self.store.get("last_api_call"))
            if response.status_code == 404:
                return None
            if response.status_code == 429:
                try:
                    delay = min(300, max(1, float(response.headers.get("retry-after", "60"))))
                except ValueError:
                    delay = 60
                self.cooldown[pool] = time.monotonic() + delay
            if response.status_code >= 400 or 300 <= response.status_code < 400:
                raise BrokerFailure(f"Alpaca {pool} request returned HTTP {response.status_code}", response.status_code)
            return response.json() if response.content else {}
        except (httpx.HTTPError, ValueError) as exc:
            self.store.event("api_request_failed", {"pool": pool, "method": method, "path": path,
                                                    "at": utcnow(), "latency_ms": round((time.monotonic()-started)*1000), "outcome": "transport-or-response-error"})
            # Never log credentials, request headers, or arbitrary provider response bodies.
            raise BrokerFailure("Alpaca request outcome is unavailable; reconcile before resubmission") from exc

    async def load_assets(self):
        from .universe import discover_crypto
        self.metadata = {}
        cryptos = await self.request("GET", "/v2/assets", params={"asset_class": "crypto", "status": "active"})
        if not isinstance(cryptos, list): raise BrokerFailure("Crypto asset discovery response unavailable")
        self.store.put("crypto_universe", discover_crypto(cryptos, utcnow()))
        by_symbol = {a["symbol"]: a for a in cryptos or []}
        for symbol, (broker_symbol, kind) in SYMBOLS.items():
            raw = by_symbol.get(broker_symbol) if kind == "crypto" else await self.request("GET", "/v2/assets/"+quote(broker_symbol, safe=""))
            if raw:
                self.metadata[symbol] = {"symbol": symbol, "broker_symbol": broker_symbol, "type": kind,
                    "tradable": raw.get("tradable") is True and raw.get("status") == "active" and (kind != "crypto" or all(raw.get(k) is not None for k in ("min_trade_increment", "min_order_size", "price_increment"))),
                    "increment": raw.get("min_trade_increment", "0.000001") if kind == "crypto" else "1",
                    "minimum": raw.get("min_order_size", "0.000001") if kind == "crypto" else "1",
                    "price_increment": raw.get("price_increment", "0.01"), "source": "alpaca", "at": utcnow()}
        return self.metadata

    async def quotes(self):
        result = {}
        groups = [("/v2/stocks/quotes/latest", {"symbols": ",".join(v[0] for v in SYMBOLS.values() if v[1] == "etf"), "feed": self.settings.equity_feed}),
                  ("/v1beta3/crypto/us/latest/quotes", {"symbols": ",".join(v[0] for v in SYMBOLS.values() if v[1] == "crypto")})]
        for path, params in groups:
            raw = await self.request("GET", path, data=True, params=params)
            for broker_symbol, q in (raw or {}).get("quotes", {}).items():
                symbol = next((s for s, v in SYMBOLS.items() if v[0] == broker_symbol), None)
                if symbol:
                    result[symbol] = {"bid": str(q["bp"]), "ask": str(q["ap"]), "at": q["t"],
                                      "bid_size": str(q.get("bs", "")), "ask_size": str(q.get("as", "")),
                                      "size_unit": "unverified",
                                      "received_at": utcnow(), "source": "alpaca-us" if "/crypto/" in path else "alpaca-"+self.settings.equity_feed}
        return result

    async def snapshot(self):
        account = await self.request("GET", "/v2/account", critical=True)
        positions = await self.request("GET", "/v2/positions", critical=True)
        clock = await self.request("GET", "/v2/clock", critical=True)
        if not isinstance(account, dict) or not account.get("id") or not isinstance(positions, list) or not isinstance(clock, dict):
            raise BrokerFailure("Incomplete account, positions, or session response")
        return {"account": account, "positions": positions, "clock": clock, "at": utcnow()}

    async def open_orders(self):
        raw = await self.request("GET", "/v2/orders", critical=True, params={"status": "open", "limit": 500})
        if not isinstance(raw, list) or len(raw) >= 500:
            raise BrokerFailure("Open-order set unavailable or at pagination boundary")
        return raw

    async def get_order(self, client_id):
        return await self.request("GET", "/v2/orders:by_client_order_id", critical=True, params={"client_order_id": client_id})

    async def submit(self, payload):
        # Exactly one POST attempt. An uncertain response is never blindly retried.
        return await self.request("POST", "/v2/orders", json=payload)

    async def cancel(self, broker_id):
        return await self.request("DELETE", "/v2/orders/"+quote(broker_id, safe=""), critical=True)

    async def news(self):
        return await self.request("GET", "/v1beta1/news", data=True,
                                  params={"symbols": ",".join(b.replace("/", "") for b, _ in SYMBOLS.values()), "limit": 20, "include_content": "false", "sort": "desc"})

    async def fee_activities(self, after):
        result, token = [], None
        for _ in range(5):
            params = {"activity_types": "CFEE,FEE", "after": after, "direction": "asc", "page_size": 100}
            if token: params["page_token"] = token
            page = await self.request("GET", "/v2/account/activities", params=params, critical=True)
            if not isinstance(page, list): raise BrokerFailure("Fee activity response unavailable")
            result.extend(page)
            if len(page) < 100: return result
            next_token = page[-1].get("id")
            if not next_token or next_token == token: raise BrokerFailure("Fee activity pagination did not advance")
            token = next_token
        raise BrokerFailure("Fee activity page budget reached; coverage incomplete")

    async def research_bars(self, symbol):
        from datetime import datetime, timezone, timedelta
        broker_symbol, kind = SYMBOLS[symbol]
        end = datetime.now(timezone.utc)-timedelta(minutes=20 if kind == "etf" else 2)
        path = "/v2/stocks/bars" if kind == "etf" else "/v1beta3/crypto/us/bars"
        params = {"symbols": broker_symbol, "timeframe": "1Day", "start": (end-timedelta(days=100)).isoformat(),
                  "end": end.isoformat(), "limit": 1000, "sort": "asc"}
        if kind == "etf": params.update(feed=self.settings.equity_feed, adjustment="raw")
        raw = await self.request("GET", path, data=True, params=params)
        if not isinstance(raw, dict) or raw.get("next_page_token"):
            raise BrokerFailure("Research history incomplete or outside bounded page budget")
        rows = raw.get("bars", {}).get(broker_symbol, [])
        if not rows: raise BrokerFailure("No research history for symbol")
        return {"rows": rows, "source": "alpaca-"+(self.settings.equity_feed if kind == "etf" else "us"),
                "bar_semantics": "executed-trades-only" if kind == "etf" else "trades-and-quote-midpoints",
                "received_at": utcnow(), "coverage": "IEX exchange only; not consolidated volume" if kind == "etf" and self.settings.equity_feed == "iex" else "Selected execution/data venue", "end": end.isoformat()}

    async def close(self):
        await self.http.aclose()


class Simulator:
    """No remote API. Fills are synthetic and do not model queueing/market impact."""
    def __init__(self, settings, store):
        self.settings, self.store = settings, store
        if not store.get("simulator"):
            store.put("simulator", {"cash": "100000", "realized": "0", "fees": "0", "positions": {}, "orders": {}, "tick": 0})

    async def load_assets(self):
        return {s: {"symbol": s, "broker_symbol": b, "type": k, "tradable": True,
                    "increment": "0.000001" if k == "crypto" else "1",
                    "minimum": "0.000001" if k == "crypto" else "1", "price_increment": "0.01", "source": "simulator", "at": utcnow()}
                for s, (b, k) in SYMBOLS.items()}

    async def quotes(self):
        base = [67500, 3400, 156, 580, 490, 244, 92.4, 217.8]
        with self.store.transaction():
            state = self.store.get("simulator");state["tick"] += 1
            result = {}
            for i, symbol in enumerate(SYMBOLS):
                mid = D(base[i]) * (1 + D(str(math.sin(state["tick"]*.13+i)*.001)))
                result[symbol] = {"bid": str(mid*D("0.9996")), "ask": str(mid*D("1.0004")), "at": utcnow(), "received_at": utcnow(), "source": "synthetic"}
            self.store.put("simulator", state)
        return result

    def match(self, state, raw):
        if raw["status"] in TERMINAL:
            return
        symbol = next(s for s, v in SYMBOLS.items() if v[0] == raw["symbol"])
        q = self.store.get("quotes", {}).get(symbol)
        if not q:
            return
        price = D(q["ask"] if raw["side"] == "buy" else q["bid"])
        marketable = raw["type"] == "market" or (price <= D(raw["limit_price"]) if raw["side"] == "buy" else price >= D(raw["limit_price"]))
        if not marketable:
            if raw["time_in_force"] == "ioc":
                raw["status"] = "canceled"
            return
        qty = D(raw["qty"]);value = qty*price;fee = value*D("0.0025") if SYMBOLS[symbol][1] == "crypto" else D(0)
        pos = state["positions"].get(symbol, {"qty": "0", "basis": "0"})
        held, basis, cash = D(pos["qty"]), D(pos["basis"]), D(state["cash"])
        if raw["side"] == "buy":
            if value+fee > cash:
                raw["status"] = "rejected";return
            cash -= value+fee;held += qty;basis += value+fee
        else:
            if qty > held:
                raw["status"] = "rejected";return
            removed = basis*qty/held;cash += value-fee;held -= qty;basis -= removed
            state["realized"] = str(D(state["realized"])+value-fee-removed)
        state["positions"][symbol] = {"qty": str(held), "basis": str(basis)}
        state["cash"] = str(cash);state["fees"] = str(D(state["fees"])+fee)
        raw.update(status="filled", filled_qty=str(qty), filled_avg_price=str(price), filled_at=utcnow(), fee=str(fee))

    async def snapshot(self):
        with self.store.transaction():
            state = self.store.get("simulator")
            for order in state["orders"].values():
                self.match(state, order)
            self.store.put("simulator", state)
        positions = [];equity = D(state["cash"])
        quotes = self.store.get("quotes", {})
        for s, p in state["positions"].items():
            if D(p["qty"]) == 0: continue
            q = quotes.get(s);price = (D(q["bid"])+D(q["ask"]))/2 if q else D(p["basis"])/D(p["qty"])
            value = D(p["qty"])*price;equity += value
            positions.append({"symbol": SYMBOLS[s][0], "qty": p["qty"], "cost_basis": p["basis"], "market_value": str(value), "current_price": str(price), "unrealized_pl": str(value-D(p["basis"]))})
        return {"account": {"id": "persistent-simulator", "cash": state["cash"], "equity": str(equity), "status": "ACTIVE", "trading_blocked": False,
                            "realized": state["realized"], "fees": state["fees"]},
                "positions": positions, "clock": {"is_open": True, "source": "simulator-not-an-exchange-calendar"}, "at": utcnow()}

    async def open_orders(self):
        return [o for o in self.store.get("simulator")["orders"].values() if o["status"] not in TERMINAL]

    async def get_order(self, client_id):
        return self.store.get("simulator")["orders"].get(client_id)

    async def submit(self, payload):
        with self.store.transaction():
            state = self.store.get("simulator")
            if payload["client_order_id"] in state["orders"]:
                return state["orders"][payload["client_order_id"]]
            raw = {**payload, "id": "sim-"+str(uuid.uuid4()), "status": "new", "filled_qty": "0", "filled_avg_price": None, "submitted_at": utcnow()}
            self.match(state, raw);state["orders"][payload["client_order_id"]] = raw;self.store.put("simulator", state)
            return raw

    async def cancel(self, broker_id):
        with self.store.transaction():
            state = self.store.get("simulator")
            for raw in state["orders"].values():
                if raw["id"] == broker_id and raw["status"] not in TERMINAL:
                    raw["status"] = "canceled"
            self.store.put("simulator", state)
        return {}

    async def close(self):
        pass
