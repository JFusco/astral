import asyncio
import json
import time
from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_DOWN, ROUND_UP

from .broker import AlpacaPaper, Simulator, BrokerFailure, TERMINAL, D
from .config import SYMBOLS
from .store import dumps, utcnow
from .risk import VERSION, propose


class RuleViolation(Exception):
    pass


def age(timestamp):
    try:
        return (datetime.now(timezone.utc)-datetime.fromisoformat(timestamp.replace("Z", "+00:00"))).total_seconds()
    except (ValueError, TypeError, AttributeError):
        return float("inf")


def symbol_for(raw):
    return next((s for s, (b, _) in SYMBOLS.items() if b.replace("/", "") == raw.replace("/", "")), None)


class Engine:
    def __init__(self, settings, store, broker=None):
        self.settings, self.store = settings, store
        self.broker = broker or (Simulator(settings, store) if settings.mode == "simulator" else AlpacaPaper(settings, store))
        self.lock = asyncio.Lock()
        self.connected = False
        self.workers = {}
        self.tasks = []
        self.last_equity_record = 0
        self.started = time.monotonic()
        self.identity_checked = False

    def worker(self, name, status, detail="", started=None):
        self.workers[name] = {"name": name, "status": status, "detail": detail, "at": utcnow(),
                              "duration_ms": round((time.monotonic()-started)*1000) if started else None}

    async def start(self):
        # A crash after intent commit or broker POST must never cause another POST.
        with self.store.transaction():
            self.store.db.execute("UPDATE orders SET status='unknown' WHERE status='submitting'")
            self.store.event("service_started", {"mode": self.settings.mode, "paper_only": True})
        if self.settings.configured:
            try:
                await self.refresh_quotes()
                await self.reconcile()
            except (BrokerFailure, RuleViolation, ValueError, KeyError):
                self.connected = False
                self.worker("reconciliation", "error", "Initial readback failed; new orders blocked")
        else:
            self.worker("reconciliation", "waiting", "Set Alpaca paper credentials on the server")
            self.worker("quotes", "waiting", "No authenticated market feed")
        self.worker("ledger", "healthy", "SQLite WAL; durable intent, fill and event records")
        self.worker("strategy", "disabled", "Manual lifecycle milestone; automated strategies not enabled")
        self.worker("learning", "recording", "Decision dataset only; no trained policy or promotion")
        self.worker("news", "waiting" if self.settings.enable_news else "disabled", "Entitlement-dependent; no fictional backend news")
        self.tasks = [asyncio.create_task(self.loop("quotes", self.refresh_quotes, self.settings.quote_interval)),
                      asyncio.create_task(self.loop("reconciliation", self.reconcile, self.settings.reconcile_interval))]
        if self.settings.enable_news and self.settings.mode == "alpaca":
            self.tasks.append(asyncio.create_task(self.loop("news", self.refresh_news, 60)))

    async def stop(self):
        for task in self.tasks: task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.store.event("service_stopped", {"mode": self.settings.mode})
        await self.broker.close()

    async def loop(self, name, action, interval):
        failures = 0
        while True:
            await asyncio.sleep(min(interval*2**min(failures, 4), 120))
            if not self.settings.configured: continue
            started = time.monotonic()
            try:
                await action();failures = 0
                self.worker(name, "healthy", "Latest cycle completed", started)
            except asyncio.CancelledError:
                raise
            except Exception:
                failures += 1
                if name == "reconciliation": self.connected = False
                self.worker(name, "error", "Cycle failed; stale data blocks dependent orders", started)
                self.store.event("worker_error", {"worker": name, "consecutive_failures": failures})

    async def refresh_quotes(self):
        if not self.store.get("assets") or any(age(a["at"]) > 3500 for a in self.store.get("assets", {}).values()):
            assets = await self.broker.load_assets()
            if set(assets) != set(SYMBOLS): raise BrokerFailure("Approved instrument metadata is incomplete")
            self.store.put("assets", assets)
        quotes = await self.broker.quotes()
        if not quotes: raise BrokerFailure("No quotes returned")
        for q in quotes.values():
            if D(q["bid"]) <= 0 or D(q["ask"]) < D(q["bid"]):
                raise BrokerFailure("Invalid quote batch; previous timestamps retained")
        # Merge partial updates without refreshing timestamps for missing symbols.
        with self.store.transaction():
            self.store.put("quotes", {**self.store.get("quotes", {}), **quotes})
            self.store.event("quotes", quotes)
        self.worker("quotes", "healthy", "Synthetic" if self.settings.mode == "simulator" else "Alpaca REST quotes; source timestamps retained")

    async def reconcile(self):
        async with self.lock:
            await self._reconcile()

    async def _reconcile(self):
        bound = self.store.get("account_binding")
        if not self.identity_checked:
            identity = (await self.broker.snapshot())["account"]["id"]
            if bound and bound != identity:
                self.connected = False
                raise BrokerFailure("Database is bound to a different paper account")
            self.store.put("account_binding", identity)
            self.identity_checked = True
        opens = await self.broker.open_orders()
        seen = set()
        for raw in opens:
            cid = raw.get("client_order_id")
            if not cid: raise BrokerFailure("Open order has no client identifier")
            self.ingest(raw);seen.add(cid)
        for row in self.store.rows("SELECT client_id,status FROM orders"):
            if row["status"] in TERMINAL or row["client_id"] in seen: continue
            raw = await self.broker.get_order(row["client_id"])
            if raw:
                self.ingest(raw)
            elif row["status"] not in TERMINAL:
                self.store.db.execute("UPDATE orders SET status='unknown',updated_at=? WHERE client_id=?", (utcnow(), row["client_id"]))
        # Read positions AFTER order states; pending exposure may be double counted
        # briefly, but a newly confirmed fill must not disappear from reservations.
        snapshot = await self.broker.snapshot()
        account = snapshot["account"]
        D(account["equity"]);D(account["cash"])
        for p in snapshot["positions"]:
            for name in ("qty", "market_value", "cost_basis", "unrealized_pl"):
                D(p[name])
        if account["id"] != self.store.get("account_binding"):
            self.connected = False
            raise BrokerFailure("Paper account identity changed")
        with self.store.transaction():
            self.store.put("account_snapshot", snapshot)
            if self.store.get("baseline_equity") is None:
                self.store.put("baseline_equity", account["equity"])
            risk = self.store.get("risk_marks", {})
            today = datetime.now(timezone.utc).date().isoformat()
            if risk.get("day") != today:
                risk = {"day": today, "day_equity": account["equity"], "highwater": risk.get("highwater", account["equity"])}
            risk["highwater"] = str(max(D(risk["highwater"]), D(account["equity"])))
            self.store.put("risk_marks", risk)
            reason = self.loss_breach(account, risk)
            if reason and not self.store.get("risk_latch"):
                self.store.put("risk_latch", {"reason": reason, "at": utcnow(), "equity": account["equity"], "marks": risk})
                self.store.event("risk_circuit_latched", self.store.get("risk_latch"))
            if time.monotonic()-self.last_equity_record >= 30:
                self.store.db.execute("INSERT INTO equity(at,value) VALUES(?,?)", (snapshot["at"], str(account["equity"])))
                self.last_equity_record = time.monotonic()
        self.connected = True
        self.worker("reconciliation", "healthy", "Balances, positions, open and unresolved orders read back")
        # Expiry only requests cancellation. Reservation remains until terminal readback.
        for row in self.store.rows("SELECT * FROM orders WHERE external=0 AND deadline<?", (time.time(),)):
            if row["status"] in TERMINAL or row["status"] in {"unknown", "pending_cancel", "submitting"}: continue
            raw = json.loads(row["raw"])
            if raw.get("id"):
                try:
                    await self.broker.cancel(raw["id"])
                    self.store.db.execute("UPDATE orders SET status='pending_cancel' WHERE client_id=?", (row["client_id"],))
                    self.store.event("cancel_requested", {"client_id": row["client_id"], "reason": "expiry"})
                except BrokerFailure:
                    self.worker("execution", "error", "Cancellation uncertain; reservation retained")

    def ingest(self, raw):
        cid = raw["client_order_id"]
        with self.store.transaction():
            row = self.store.order(cid)
            old = json.loads(row["raw"]) if row else {}
            old_qty, new_qty = D(old.get("filled_qty") or 0), D(raw.get("filled_qty") or 0)
            if new_qty < old_qty: raise BrokerFailure("Order fill quantity regressed; reconciliation required")
            # Once terminal, do not let a delayed open-state message release/recreate risk.
            if row and row["status"] in TERMINAL and raw["status"] not in TERMINAL:
                return
            if not row:
                self.store.db.execute("INSERT INTO orders VALUES(?,?,?,?,?,?,?,?)", (cid, dumps({"external": True}), dumps({}), raw["status"], 1, 0, utcnow(), utcnow()))
            status = "pending_cancel" if row and row["status"] == "pending_cancel" and raw["status"] not in TERMINAL else raw["status"]
            self.store.db.execute("UPDATE orders SET raw=?,status=?,updated_at=? WHERE client_id=?", (dumps(raw), status, utcnow(), cid))
            if new_qty > old_qty:
                if not raw.get("filled_avg_price"): raise BrokerFailure("Filled order missing average price")
                delta = new_qty-old_qty
                total = new_qty*D(raw["filled_avg_price"])
                previous = old_qty*D(old.get("filled_avg_price") or 0)
                price = (total-previous)/delta
                if price <= 0: raise BrokerFailure("Invalid incremental fill price")
                payload = {"id": cid+":"+str(new_qty), "client_id": cid, "symbol": symbol_for(raw["symbol"]) or raw["symbol"],
                           "side": raw["side"], "quantity": str(delta), "price": str(price), "value": str(delta*price),
                           "fee": str(D(raw["fee"])-D(old.get("fee") or 0)) if raw.get("fee") is not None else None,
                           "at": raw.get("filled_at") or utcnow(), "source": "simulator" if self.settings.mode == "simulator" else "alpaca-cumulative-order-readback"}
                cur = self.store.db.execute("INSERT OR IGNORE INTO fills VALUES(?,?,?,?)", (payload["id"], cid, utcnow(), dumps(payload)))
                if cur.rowcount: self.store.event("fill", payload)
            if not old or old.get("status") != raw["status"]:
                self.store.event("order_state", {"client_id": cid, "status": raw["status"], "external": not bool(row)})

    @staticmethod
    def loss_breach(account, marks):
        equity = D(account["equity"])
        if equity <= 0: return "Account equity is nonpositive"
        if equity <= D(marks.get("day_equity", equity))*D("0.99"):
            return "1% UTC-day equity loss circuit breaker"
        if equity <= D(marks.get("highwater", equity))*D("0.95"):
            return "5% high-water drawdown circuit breaker"
        return None

    def risk_payload(self, intent):
        cfg = self.settings
        if not cfg.enable_orders: raise RuleViolation("Paper orders are disabled by server configuration")
        if not self.connected: raise RuleViolation("Broker readback is not healthy")
        snap = self.store.get("account_snapshot")
        if not snap or not 0 <= age(snap["at"]) <= cfg.max_snapshot_age: raise RuleViolation("Account snapshot is stale")
        symbol, side = intent["symbol"], intent["side"]
        metadata = self.store.get("assets", {}).get(symbol)
        if not metadata or not metadata["tradable"]: raise RuleViolation("Instrument is not approved and tradable")
        # Metadata is deliberately reloaded each hour; no stale precision/status assumptions.
        if not 0 <= age(metadata["at"]) <= 3600: raise RuleViolation("Instrument metadata expired or future-dated")
        quote = self.store.get("quotes", {}).get(symbol)
        if not quote or not 0 <= age(quote["at"]) <= cfg.max_quote_age: raise RuleViolation("Quote is missing, stale or future-dated")
        bid, ask = D(quote["bid"]), D(quote["ask"])
        if bid <= 0 or ask < bid or (ask-bid)/((ask+bid)/2) > D("0.005"): raise RuleViolation("Quote spread is invalid or too wide")
        if metadata["type"] == "etf" and snap["clock"].get("is_open") is not True: raise RuleViolation("ETF regular session is closed")
        account = snap["account"]
        if any(account.get(k) for k in ("trading_blocked", "account_blocked", "trade_suspended_by_user")) or account.get("status") != "ACTIVE":
            raise RuleViolation("Paper account is not enabled for trading")
        if cfg.mode == "alpaca" and metadata["type"] == "crypto" and account.get("crypto_status") != "ACTIVE":
            raise RuleViolation("Paper crypto account is not active")
        active = [r for r in self.store.rows("SELECT * FROM orders") if r["status"] not in TERMINAL]
        if side == "buy" and len(active) >= 4: raise RuleViolation("Four working orders already occupy the first-release request budget")
        if side == "buy":
            if self.store.get("halted", False): raise RuleViolation("New entries are halted")
            if self.store.get("risk_latch"): raise RuleViolation("Loss circuit breaker is latched; operator review required")
            if any(r["status"] in {"unknown", "submitting"} for r in active): raise RuleViolation("Uncertain orders must be reconciled before new risk")
            marks = self.store.get("risk_marks", {})
            equity = D(account["equity"])
            if equity <= 0: raise RuleViolation("Account equity is nonpositive")
            reason = self.loss_breach(account, marks)
            if reason: raise RuleViolation(reason)
            if any(symbol_for(p["symbol"]) is None or D(p["qty"]) < 0 for p in snap["positions"]):
                raise RuleViolation("Unapproved or short holdings require operator review")
        increment, minimum, tick = D(metadata["increment"]), D(metadata["minimum"]), D(metadata["price_increment"])
        if increment <= 0 or minimum <= 0 or tick <= 0: raise RuleViolation("Invalid instrument precision")
        style = intent["execution"]
        if style == "market" and D(intent["notional"]) > D("100"):
            raise RuleViolation("Market orders are limited to $100 planned notional; execution price is unbounded")
        if style == "patient": price = bid if side == "buy" else ask
        else: price = ask*D("1.001") if side == "buy" else bid*D("0.999")
        # Keep the rounded limit INSIDE the chosen price bound.
        price = (price/tick).to_integral_value(rounding=ROUND_DOWN if side == "buy" else ROUND_UP)*tick
        if price <= 0: raise RuleViolation("Limit price is below the instrument tick")
        worst_price = max(ask, price)
        qty = (D(intent["notional"])/worst_price/increment).to_integral_value(rounding=ROUND_DOWN)*increment
        if qty < minimum: raise RuleViolation("Order amount is below the minimum tradable quantity")
        notional = qty*worst_price
        if notional > cfg.max_order: raise RuleViolation("Order exceeds the paper per-order cap")
        positions = {symbol_for(p["symbol"]) or p["symbol"]: p for p in snap["positions"]}
        reservations, pending_sells = [], D(0)
        for row in active:
            raw = json.loads(row["raw"]);request = json.loads(row["request"])
            payload = request.get("payload") or raw
            s = symbol_for(payload.get("symbol", ""))
            if s is None and side == "buy": raise RuleViolation("Unapproved working order requires review")
            remaining = max(D(0), D(payload.get("qty") or 0)-D(raw.get("filled_qty") or 0))
            if payload.get("side") == "sell" and s == symbol: pending_sells += remaining
            if payload.get("side") == "buy":
                q = self.store.get("quotes", {}).get(s, {})
                reference = max(D(payload.get("limit_price") or 0), D(q.get("ask") or 0))
                if reference <= 0 and side == "buy": raise RuleViolation("Cannot value pending-order exposure")
                reservations.append((s, remaining*reference))
        if side == "sell":
            available = D(positions.get(symbol, {}).get("qty") or 0)-pending_sells
            qty = min(qty, (available/increment).to_integral_value(rounding=ROUND_DOWN)*increment)
            if qty < minimum: raise RuleViolation("No unreserved position quantity to sell")
        else:
            equity = D(account["equity"]);reserve = sum((v for _, v in reservations), D(0))
            gross = sum((abs(D(p["market_value"])) for p in snap["positions"]), D(0))
            if (reserve+notional)*D("1.003") > D(account["cash"]): raise RuleViolation("Insufficient unreserved cash")
            if cfg.mode == "alpaca":
                field = "non_marginable_buying_power" if metadata["type"] == "crypto" else "buying_power"
                # Provider buying power already reserves provider open orders.
                # Compare only this NEW order here; local cash check above
                # separately reserves all known pending purchases.
                available_power = account.get(field)
                if available_power is None or notional*D("1.003") > max(D(0), D(available_power)):
                    raise RuleViolation("Insufficient or unavailable broker buying power")
            if gross+reserve+notional > equity*cfg.max_exposure: raise RuleViolation("Aggregate exposure cap")
            held = abs(D(positions.get(symbol, {}).get("market_value") or 0))
            cap = D("0.05") if metadata["type"] == "crypto" else D("0.10")
            if held+sum((v for s, v in reservations if s == symbol), D(0))+notional > equity*cap: raise RuleViolation("Instrument concentration cap")
            def group(s): return "crypto" if s in {"BTC","ETH","SOL"} else "equity" if s in {"SPY","QQQ","IWM"} else s
            grouped = sum((abs(D(p["market_value"])) for s, p in positions.items() if group(s) == group(symbol)), D(0))
            grouped += sum((v for s, v in reservations if group(s) == group(symbol)), D(0))
            if grouped+notional > equity*cfg.max_group: raise RuleViolation("Economic exposure group cap")
        payload = {"client_order_id": intent["client_order_id"], "symbol": metadata["broker_symbol"], "qty": str(qty), "side": side,
                   "type": "market" if style == "market" else "limit", "time_in_force": "ioc" if metadata["type"] == "crypto" and style != "patient" else "gtc" if metadata["type"] == "crypto" else "day"}
        if payload["type"] == "limit": payload["limit_price"] = str(price)
        return payload

    async def place(self, intent):
        async with self.lock:
            existing = self.store.order(intent["client_order_id"])
            if existing:
                if json.loads(existing["request"]).get("intent") != intent: raise RuleViolation("Client order ID already belongs to a different intent")
                return self.order_view(existing)
            context = {"snapshot": self.store.get("account_snapshot"), "quotes": self.store.get("quotes"),
                       "assets": self.store.get("assets"), "risk_marks": self.store.get("risk_marks"),
                       "risk_latch": self.store.get("risk_latch"), "halted": self.store.get("halted", False),
                       "working_orders": self.store.rows("SELECT * FROM orders WHERE status NOT IN ('filled','canceled','expired','rejected','replaced')"),
                       "config_version": VERSION, "policy": self.risk_policy()}
            try:
                payload = self.risk_payload(intent)
            except RuleViolation as exc:
                self.store.db.execute("INSERT INTO observations(at,request,outcome,context) VALUES(?,?,?,?)", (utcnow(), dumps(intent), "blocked: "+str(exc), dumps(context)))
                self.store.event("risk_veto", {"client_id": intent["client_order_id"], "reason": str(exc)})
                raise
            with self.store.transaction():
                self.store.db.execute("INSERT INTO orders VALUES(?,?,?,?,?,?,?,?)", (intent["client_order_id"], dumps({"intent": intent,"payload": payload}), dumps({}), "submitting", 0, time.time()+intent["ttl_seconds"], utcnow(), utcnow()))
                self.store.db.execute("INSERT INTO observations(at,request,outcome,context) VALUES(?,?,?,?)", (utcnow(), dumps(intent), "approved", dumps(context)))
                self.store.event("intent_committed", {"client_id": intent["client_order_id"], "payload": payload})
            try:
                raw = await self.broker.submit(payload)
                if not raw or raw.get("client_order_id") != intent["client_order_id"]: raise BrokerFailure("Submission identity not confirmed")
                self.ingest(raw)
                await self._reconcile()
                self.worker("execution", "healthy", "Intent submitted once and read back")
            except Exception as exc:
                # Retain any confirmed terminal state; unknown submission/reconciliation blocks new risk.
                row = self.store.order(intent["client_order_id"])
                definitive_rejection = isinstance(exc, BrokerFailure) and exc.status in {400, 401, 403, 422}
                if row["status"] not in TERMINAL:
                    status = "rejected" if definitive_rejection else "unknown"
                    self.store.db.execute("UPDATE orders SET status=? WHERE client_id=?", (status, intent["client_order_id"]))
                self.connected = False
                self.store.event("submission_rejected" if definitive_rejection else "submission_uncertain", {"client_id": intent["client_order_id"], "action": "query-and-reconcile-only"})
                self.worker("execution", "error", "Readback required; no automatic resubmission")
            return self.order_view(self.store.order(intent["client_order_id"]))

    async def cancel(self, client_id):
        async with self.lock:
            row = self.store.order(client_id)
            if not row or row["external"]: raise RuleViolation("Only locally recorded paper orders may be canceled here")
            if row["status"] in TERMINAL: return self.order_view(row)
            raw = json.loads(row["raw"])
            if not raw.get("id"): raise RuleViolation("Broker order identity is unknown; reconcile first")
            try:
                await self.broker.cancel(raw["id"])
                self.store.db.execute("UPDATE orders SET status='pending_cancel' WHERE client_id=?", (client_id,))
                self.store.event("cancel_requested", {"client_id": client_id, "reason": "operator"})
                await self._reconcile()
            except BrokerFailure:
                self.connected = False
                self.worker("execution", "error", "Cancel outcome uncertain; reservation retained")
            return self.order_view(self.store.order(client_id))

    async def refresh_news(self):
        raw = await self.broker.news()
        for item in (raw or {}).get("news", []):
            safe = {k: item.get(k) for k in ("id", "headline", "source", "symbols", "url", "created_at", "updated_at")}
            safe["first_seen_at"] = utcnow()
            cur = self.store.db.execute("INSERT OR IGNORE INTO news VALUES(?,?,?)", (str(item["id"]), item.get("updated_at") or item["created_at"], dumps(safe)))
            if cur.rowcount: self.store.event("news", safe)

    @staticmethod
    def order_view(row):
        return {"client_id": row["client_id"], "status": row["status"], "external": bool(row["external"]), "request": json.loads(row["request"]), "broker": json.loads(row["raw"]), "updated_at": row["updated_at"]}

    def risk_policy(self):
        return {"version": VERSION, "max_order_usd": str(self.settings.max_order),
                "max_market_order_usd": "100", "max_gross_fraction": str(self.settings.max_exposure),
                "max_group_fraction": str(self.settings.max_group), "etf_fraction": "0.10", "crypto_fraction": "0.05",
                "daily_loss_fraction": "0.01", "highwater_loss_fraction": "0.05",
                "quote_max_age_seconds": self.settings.max_quote_age, "snapshot_max_age_seconds": self.settings.max_snapshot_age,
                "latched": self.store.get("risk_latch"), "automatic_stops": False,
                "automatic_entries": False, "planner": "ATR14 Wilder + trend/breakout; research only"}

    def plan(self, candidate):
        symbol = candidate["symbol"]
        metadata = self.store.get("assets", {}).get(symbol)
        quote = self.store.get("quotes", {}).get(symbol)
        snap = self.store.get("account_snapshot")
        if not metadata or not quote or not snap or not self.connected:
            raise RuleViolation("Connected account, quotes and instrument metadata required for planning")
        if any(b["symbol"] != symbol for b in candidate["bars"]):
            raise RuleViolation("Historical bars do not match the selected symbol")
        as_of = utcnow()
        if not 0 <= age(quote["at"]) <= self.settings.max_quote_age or not 0 <= age(snap["at"]) <= self.settings.max_snapshot_age:
            raise RuleViolation("Fresh quote and account snapshot required for planning")
        try:
            entry = (D(quote["ask"])*D("1.001")/D(metadata["price_increment"])).to_integral_value(rounding=ROUND_DOWN)*D(metadata["price_increment"])
            result = propose(bars=candidate["bars"], horizon=candidate["horizon"], kind=metadata["type"],
                             as_of=as_of, entry=str(entry), equity=snap["account"]["equity"],
                             cash_cap=snap["account"]["cash"], notional_cap=str(self.settings.max_order),
                             increment=metadata["increment"], minimum=metadata["minimum"], tick=metadata["price_increment"])
        except (ValueError, KeyError) as exc:
            raise RuleViolation(str(exc)) from exc
        # A proposal must pass the same current execution gate, but never submits.
        intent = {"client_order_id": "astral-research-only", "symbol": symbol, "side": "buy", "execution": "bounded",
                  "notional": float(D(result["notional"])), "ttl_seconds": 60, "strategy_id": "manual"}
        try:
            if D(result["quantity"]) <= 0: raise RuleViolation("Proposed quantity is below venue minimum")
            self.risk_payload(intent)
            result["current_gate"] = "passed" if result["signal"] == "entry_candidate" else "no-entry-signal"
        except RuleViolation as exc:
            result["current_gate"] = "blocked"
            result["gate_reason"] = str(exc)
        context = {"snapshot": snap, "quote": quote, "metadata": metadata, "policy": self.risk_policy(),
                   "historical_bars": candidate["bars"], "result": result}
        self.store.db.execute("INSERT INTO observations(at,request,outcome,context) VALUES(?,?,?,?)",
                              (as_of, dumps(candidate), "research-only", dumps(context)))
        self.store.event("risk_plan", {"input_sha256": result["input_sha256"], "symbol": symbol, "horizon": candidate["horizon"], "signal": result["signal"]})
        return result

    def state(self):
        snap = self.store.get("account_snapshot", {})
        a = snap.get("account", {});quotes = self.store.get("quotes", {})
        positions = {symbol_for(p["symbol"]) or p["symbol"]: p for p in snap.get("positions", [])}
        assets = []
        for symbol, (_, kind) in SYMBOLS.items():
            q, p = quotes.get(symbol, {}), positions.get(symbol, {})
            price = (D(q["ask"])+D(q["bid"]))/2 if q else D(p.get("current_price") or 0)
            assets.append({"symbol": symbol, "type": kind, "price": float(price) if price else None,
                           "market_value": float(D(p.get("market_value") or 0)),
                           "quantity": float(D(p.get("qty") or 0)), "basis": float(D(p.get("cost_basis") or 0)),
                           "unrealized": float(D(p.get("unrealized_pl") or 0)), "quote": q,
                           "quote_fresh": bool(q) and 0 <= age(q.get("at")) <= self.settings.max_quote_age})
        equity = float(D(a["equity"])) if a.get("equity") is not None else None
        baseline = self.store.get("baseline_equity")
        cash = float(D(a["cash"])) if a.get("cash") is not None else None
        fills = [json.loads(r["payload"]) for r in self.store.rows("SELECT payload FROM fills ORDER BY rowid DESC LIMIT 30")]
        orders = [self.order_view(r) for r in self.store.rows("SELECT * FROM orders ORDER BY created_at DESC LIMIT 50")]
        last_seq = self.store.rows("SELECT COALESCE(MAX(seq),0) n FROM events")[0]["n"]
        latest_news = self.store.rows("SELECT payload FROM news n WHERE revision=(SELECT MAX(revision) FROM news WHERE id=n.id) ORDER BY revision DESC LIMIT 20")
        healthy = self.connected and bool(snap) and age(snap["at"]) <= self.settings.max_snapshot_age
        return {"service_version": "0.2", "mode": self.settings.mode, "paper_only": True, "configured": self.settings.configured,
                "connected": healthy, "as_of": snap.get("at"), "server_time": utcnow(), "halted": self.store.get("halted", False) or bool(self.store.get("risk_latch")),
                "risk_policy": self.risk_policy(),
                "orders_enabled": self.settings.enable_orders, "assets": assets,
                "account": {"equity": equity, "cash": cash, "opening_equity": 100000 if self.settings.mode == "simulator" else baseline,
                            "deployed": sum(float(D(p["market_value"])) for p in snap.get("positions", [])),
                            "realized": float(D(a["realized"])) if a.get("realized") is not None else None,
                            "unrealized": sum(float(D(p.get("unrealized_pl") or 0)) for p in snap.get("positions", [])),
                            "net": equity-100000 if equity is not None and self.settings.mode == "simulator" else None,
                            "equity_change": equity-float(D(baseline)) if equity is not None and baseline is not None else None,
                            "profit_scope": "simulated-net-trading-pnl" if self.settings.mode == "simulator" else "equity-change-since-connection-cash-flows-not-reconciled"},
                "fills": fills, "orders": orders, "workers": list(self.workers.values()), "sequence": last_seq,
                "untracked_positions": [{"symbol": p["symbol"], "quantity": p["qty"], "market_value": p["market_value"]} for p in snap.get("positions", []) if symbol_for(p["symbol"]) is None],
                "equity_history": self.store.rows("SELECT at,value FROM (SELECT * FROM equity ORDER BY id DESC LIMIT 5000) ORDER BY id"),
                "news": [json.loads(r["payload"]) for r in latest_news], "last_api_call": self.store.get("last_api_call"),
                "learning": {"status": "dataset-only", "observations": self.store.rows("SELECT COUNT(*) n FROM observations")[0]["n"], "promotions": 0},
                "costs": {"actual_model_api_usd": 0, "model_workers_enabled": False, "hosting_and_data_usd": None},
                "uptime_seconds": round(time.monotonic()-self.started)}
