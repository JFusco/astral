import asyncio
import json
import time
import hashlib
from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_DOWN, ROUND_UP

from .broker import AlpacaPaper, Simulator, BrokerFailure, TERMINAL, D
from .config import SYMBOLS
from .store import dumps, utcnow
from .risk import VERSION, propose
from .inventory import attribute, book_for
from .research import screen
from .codex_worker import CodexReviewer
from .timing import decide as timing_decision


class RuleViolation(Exception):
    pass


def age(timestamp, now=None):
    try:
        moment = datetime.fromisoformat(now.replace("Z", "+00:00")) if now else datetime.now(timezone.utc)
        return (moment-datetime.fromisoformat(timestamp.replace("Z", "+00:00"))).total_seconds()
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
        self.reviewer = CodexReviewer(store)
        self.research_lock = asyncio.Lock()

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
        if self.settings.mode == "alpaca":
            self.tasks.append(asyncio.create_task(self.loop("fees", self.refresh_fees, 60)))
        self.worker("shadow", "waiting" if self.settings.enable_shadow else "disabled", "Risk probes only; no strategy or broker orders")
        if self.settings.enable_shadow:
            self.tasks.append(asyncio.create_task(self.loop("shadow", self.shadow_cycle, self.settings.shadow_interval)))
        self.worker("exit_monitor", "waiting" if self.settings.enable_exit_monitor else "disabled", "Local conditional exits; not broker-native stops")
        if self.settings.enable_exit_monitor:
            self.tasks.append(asyncio.create_task(self.loop("exit_monitor", self.exit_cycle, 2)))
        self.worker("research", "waiting" if self.settings.enable_research else "disabled", "Source-backed screening; missing calendars veto picks")
        if self.settings.enable_research and self.settings.mode == "alpaca":
            self.tasks.append(asyncio.create_task(self.loop("research", self.research_cycle, 900)))

    async def stop(self):
        for task in self.tasks: task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.store.event("service_stopped", {"mode": self.settings.mode})
        await self.broker.close()

    async def loop(self, name, action, interval):
        failures = 0
        while True:
            await asyncio.sleep(min(interval*2**min(failures, 4), max(interval, 120)))
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
        if not self.store.get("assets") or (self.settings.mode == "alpaca" and not self.store.get("crypto_universe")) or any(age(a["at"]) > 3500 for a in self.store.get("assets", {}).values()):
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

    def risk_payload(self, intent, *, shadow=False, as_of=None):
        cfg = self.settings
        if not shadow and not cfg.enable_orders: raise RuleViolation("Paper orders are disabled by server configuration")
        if not self.connected: raise RuleViolation("Broker readback is not healthy")
        snap = self.store.get("account_snapshot")
        if not snap or not 0 <= age(snap["at"], as_of) <= cfg.max_snapshot_age: raise RuleViolation("Account snapshot is stale")
        symbol, side = intent["symbol"], intent["side"]
        metadata = self.store.get("assets", {}).get(symbol)
        if not metadata or not metadata["tradable"]: raise RuleViolation("Instrument is not approved and tradable")
        # Metadata is deliberately reloaded each hour; no stale precision/status assumptions.
        if not 0 <= age(metadata["at"], as_of) <= 3600: raise RuleViolation("Instrument metadata expired or future-dated")
        quote = self.store.get("quotes", {}).get(symbol)
        if not quote or not 0 <= age(quote["at"], as_of) <= cfg.max_quote_age: raise RuleViolation("Quote is missing, stale or future-dated")
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
        reservations, pending_sells, pending_sell_books = [], D(0), {}
        for row in active:
            raw = json.loads(row["raw"]);request = json.loads(row["request"])
            payload = request.get("payload") or raw
            s = symbol_for(payload.get("symbol", ""))
            if s is None and side == "buy": raise RuleViolation("Unapproved working order requires review")
            remaining = max(D(0), D(payload.get("qty") or 0)-D(raw.get("filled_qty") or 0))
            if payload.get("side") == "sell" and s == symbol:
                pending_sells += remaining
                owner = "external" if row["external"] else book_for(request.get("intent", {}))
                pending_sell_books[owner] = pending_sell_books.get(owner, D(0))+remaining
            if payload.get("side") == "buy":
                if side == "buy" and (D(payload.get("qty") or 0) <= 0 or payload.get("type") != "limit" or not payload.get("limit_price")):
                    raise RuleViolation("Unbounded or unquantified working buy requires reconciliation")
                q = self.store.get("quotes", {}).get(s, {})
                reference = max(D(payload.get("limit_price") or 0), D(q.get("ask") or 0))
                if reference <= 0 and side == "buy": raise RuleViolation("Cannot value pending-order exposure")
                reservations.append((s, remaining*reference))
        if side == "sell":
            available = D(positions.get(symbol, {}).get("qty") or 0)-pending_sells
            attribution = self.inventory()
            book = book_for(intent)
            own = D(attribution["books"].get(symbol, {}).get(book, "0"))
            if book in {"swing", "intraday"}:
                if any(d["symbol"] == symbol for d in attribution["differences"]+attribution["errors"]):
                    raise RuleViolation("Strategy inventory differs from broker; reconcile fees or external activity")
                available = min(available, max(D(0), own-pending_sell_books.get(book, D(0))-pending_sell_books.get("external", D(0))))
            else:
                # An operator's manual order cannot consume another sleeve.
                protected = sum((max(D(0), D(attribution["books"].get(symbol, {}).get(b, "0"))) for b in ("swing", "intraday")), D(0))
                available = min(available, max(D(0), D(positions.get(symbol, {}).get("qty") or 0)-protected-pending_sell_books.get("manual", D(0))-pending_sell_books.get("external", D(0))))
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
            # No broker-native stop is verified in this release. Reserve full
            # value of holdings/pending buys, never a hypothetical stop distance.
            full_value = sum((max(abs(D(p["market_value"])), abs(D(p["cost_basis"]))) for p in snap["positions"]), D(0))
            if (full_value+reserve+notional)*D("1.003") > equity*cfg.max_unprotected_risk:
                raise RuleViolation("Shared unprotected full-value loss budget exceeded")
            book = book_for(intent)
            if book in {"swing", "intraday"}:
                inv = self.inventory()
                if inv["differences"] or inv["errors"]:
                    raise RuleViolation("Strategy inventory reconciliation required")
                sleeve = D(0)
                for s, buckets in inv["books"].items():
                    q = self.store.get("quotes", {}).get(s, {})
                    p = positions.get(s, {})
                    per_unit = max(D(q.get("ask") or 0), abs(D(p.get("cost_basis") or 0))/D(p["qty"]) if D(p.get("qty") or 0) > 0 else D(0))
                    if D(buckets[book]) > 0 and per_unit <= 0: raise RuleViolation("Cannot value strategy inventory")
                    sleeve += max(D(0), D(buckets[book]))*per_unit
                for row in active:
                    request, raw = json.loads(row["request"]), json.loads(row["raw"])
                    if book_for(request.get("intent", {})) == book and raw.get("side", request.get("payload", {}).get("side")) == "buy":
                        payload = request.get("payload") or raw
                        sleeve += max(D(0), D(payload.get("qty") or 0)-D(raw.get("filled_qty") or 0))*D(payload.get("limit_price") or 0)
                fraction = D("0.0025") if book == "swing" else D("0.001")
                if (sleeve+notional)*D("1.003") > equity*fraction:
                    raise RuleViolation("Strategy unprotected loss budget exceeded")
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
            if self.settings.mode == "alpaca" and book_for(intent) in {"swing", "intraday"}:
                raise RuleViolation("Strategy execution is shadow-only until protective and research gates are validated")
            context = self.decision_context()
            try:
                payload = self.risk_payload(intent, as_of=context["decision_at"])
            except RuleViolation as exc:
                self.store.db.execute("INSERT INTO observations(at,request,outcome,context) VALUES(?,?,?,?)", (utcnow(), dumps(intent), "blocked: "+str(exc), dumps(context)))
                self.store.event("risk_veto", {"client_id": intent["client_order_id"], "reason": str(exc)})
                raise
            with self.store.transaction():
                self.store.db.execute("INSERT INTO orders VALUES(?,?,?,?,?,?,?,?)", (intent["client_order_id"], dumps({"intent": intent,"payload": payload}), dumps({}), "submitting", 0, time.time()+intent["ttl_seconds"], utcnow(), utcnow()))
                self.store.db.execute("INSERT INTO observations(at,request,outcome,context) VALUES(?,?,?,?)", (utcnow(), dumps(intent), "approved", dumps(context)))
                self.store.event("intent_committed", {"client_id": intent["client_order_id"], "payload": payload})
            accepted = False
            try:
                raw = await self.broker.submit(payload)
                if not raw or raw.get("client_order_id") != intent["client_order_id"]: raise BrokerFailure("Submission identity not confirmed")
                accepted = True
                self.ingest(raw)
                await self._reconcile()
                self.worker("execution", "healthy", "Intent submitted once and read back")
            except Exception as exc:
                # Retain any confirmed terminal state; unknown submission/reconciliation blocks new risk.
                row = self.store.order(intent["client_order_id"])
                definitive_rejection = not accepted and isinstance(exc, BrokerFailure) and exc.status in {400, 401, 403, 422}
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
        self.store.put("news_coverage", {"status": "available", "at": utcnow(), "scope": "Latest 20 metadata records; not exhaustive news coverage"})

    async def refresh_fees(self):
        after = (datetime.now(timezone.utc)-timedelta(days=3)).isoformat()
        items = await self.broker.fee_activities(after)
        with self.store.transaction():
            for item in items:
                if not item.get("id") or item.get("activity_type") not in {"CFEE", "FEE"}:
                    raise BrokerFailure("Unrecognized fee activity")
                self.store.db.execute("INSERT INTO activities VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET type=excluded.type,at=excluded.at,payload=excluded.payload",
                                      (item["id"], item["activity_type"], item.get("transaction_time") or item.get("date") or utcnow(), dumps(item)))
            self.store.put("fee_coverage", {"after": after, "at": utcnow(), "status": "window-fetched", "late_fees_possible": True})
            self.store.event("fee_readback", {"records": len(items), "after": after})

    def inventory(self):
        return attribute(self.store, self.store.get("account_snapshot", {}))

    def decision_context(self):
        return {"snapshot": self.store.get("account_snapshot"), "quotes": self.store.get("quotes"),
                "assets": self.store.get("assets"), "policy": self.risk_policy(), "inventory": self.inventory(),
                "working_orders": self.store.rows("SELECT * FROM orders WHERE status NOT IN ('filled','canceled','expired','rejected','replaced')"),
                "risk_marks": self.store.get("risk_marks"), "halted": self.store.get("halted", False),
                "connected": self.connected, "decision_at": utcnow()}

    async def shadow(self, intent):
        async with self.lock:
            context = self.decision_context()
            try:
                payload = self.risk_payload(intent, shadow=True, as_of=context["decision_at"])
                result = {"decision": "would-approve", "reason": "Pretrade rules passed", "payload": payload}
            except (RuleViolation, ValueError) as exc:
                result = {"decision": "veto", "reason": str(exc)}
            result.update(execution_enabled=False, scope="Independent risk probe; no hypothetical cash reservation or strategy signal", version=VERSION)
            digest = hashlib.sha256(json.dumps({"intent": intent, "context": context}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            with self.store.transaction():
                self.store.db.execute("INSERT INTO shadow(at,intent,result,context,input_hash) VALUES(?,?,?,?,?)",
                                      (context["decision_at"], dumps(intent), dumps(result), dumps(context), digest))
                self.store.event("shadow_decision", {"symbol": intent["symbol"], "strategy_id": intent["strategy_id"], **result, "input_hash": digest})
            return {**result, "input_hash": digest}

    async def shadow_cycle(self):
        for strategy in ("swing", "intraday"):
            for symbol in ("BTC", "ETH", "SPY", "TLT"):
                await self.shadow({"client_order_id": "astral-shadow-"+strategy+"-"+symbol, "symbol": symbol,
                                   "side": "buy", "notional": 25 if SYMBOLS[symbol][1] == "crypto" else 1000,
                                   "execution": "bounded", "ttl_seconds": 60, "strategy_id": strategy})
        self.timing_cycle()

    def timing_cycle(self):
        now = utcnow();inventory = self.inventory();snap = self.store.get("account_snapshot", {})
        packets = {p["symbol"]: p for p in self.store.get("research_packets", [])}
        review = self.store.get("research_review", {})
        picks = {p["symbol"] for p in (review.get("review") or {}).get("picks", [])} if review.get("status") == "reviewed" else set()
        active = [r for r in self.store.rows("SELECT * FROM orders") if r["status"] not in TERMINAL]
        rows = []
        for horizon in ("swing", "intraday"):
            for symbol, (_, kind) in SYMBOLS.items():
                packet = packets.get(symbol, {})
                plan = next((p["request"] for p in self.store.get("exit_plans", {}).values()
                             if p["request"]["symbol"] == symbol and book_for(p["request"]) == horizon and p["state"] in {"armed", "triggered"}), {})
                context = {"as_of": now, "horizon": horizon, "kind": kind,
                           "quote": self.store.get("quotes", {}).get(symbol, {}), "session_open": snap.get("clock", {}).get("is_open", False),
                           "signal": packet.get("facts", {}).get("signal", "hold") if horizon == "swing" else "hold",
                           "latest_closed_at": packet.get("facts", {}).get("latest_closed_daily_bar") if horizon == "swing" else None,
                           "research_qualified": symbol in picks and packet.get("eligible", False), "research_expires_at": packet.get("expires_at"),
                           "quantity": inventory["books"].get(symbol, {}).get(horizon, "0"),
                           "entry_at": inventory["entry_times"].get(symbol, {}).get(horizon),
                           "stop_price": plan.get("stop_price"), "target_price": plan.get("target_price"),
                           "entries_halted": self.store.get("halted", False) or bool(self.store.get("risk_latch")),
                           "pending_order": any(symbol_for(json.loads(r["raw"]).get("symbol", json.loads(r["request"]).get("payload", {}).get("symbol", ""))) == symbol for r in active)}
                result = timing_decision(**context)
                if inventory["differences"] or inventory["errors"]:
                    result.update(action="wait", reason="Inventory reconciliation required before strategy timing")
                self.store.db.execute("INSERT INTO timing(at,symbol,strategy,result,context) VALUES(?,?,?,?,?)", (now, symbol, horizon, dumps(result), dumps(context)))
                rows.append({"symbol": symbol, "strategy": horizon, **result})
        self.store.event("timing_shadow", {"decisions": len(rows), "execution_enabled": False})
        return rows

    async def research_cycle(self):
        if not self.settings.enable_research or self.settings.mode != "alpaca":
            raise RuleViolation("Connected Alpaca research is disabled")
        if self.research_lock.locked(): raise RuleViolation("A research cycle is already running")
        async with self.research_lock:
            history = {}
            for symbol in SYMBOLS:
                try: history[symbol] = await self.broker.research_bars(symbol)
                except BrokerFailure: history[symbol] = None
            snap = self.store.get("account_snapshot", {})
            quotes = self.store.get("quotes", {})
            metadata = self.store.get("assets", {})
            latest = self.store.rows("SELECT payload FROM news n WHERE revision=(SELECT MAX(revision) FROM news WHERE id=n.id) ORDER BY revision DESC LIMIT 100")
            items = [json.loads(r["payload"]) for r in latest]
            now = utcnow();packets = []
            for symbol in SYMBOLS:
                packet = screen(symbol, quotes.get(symbol, {}), history[symbol], items, self.store.get("news_coverage"),
                                self.store.get("event_calendars", {}).get(symbol), metadata.get(symbol, {}), snap.get("account", {}), now)
                result = await self.shadow({"client_order_id": "astral-research-"+symbol, "symbol": symbol, "side": "buy",
                                           "notional": packet["facts"].get("proposed_notional", "25"), "execution": "bounded",
                                           "ttl_seconds": 60, "strategy_id": "swing"})
                if result["decision"] == "veto": packet["vetoes"].append("Risk engine: "+result["reason"])
                packet["eligible"] = not packet["vetoes"]
                packet["input_hash"] = hashlib.sha256(dumps(packet).encode()).hexdigest()
                packets.append(packet)
            review = await self.reviewer.review(packets) if self.settings.enable_codex_research else {"status": "disabled", "execution_enabled": False}
            with self.store.transaction():
                self.store.put("research_packets", packets)
                self.store.put("research_review", review)
                self.store.db.execute("INSERT INTO research(at,packet,result,usage) VALUES(?,?,?,?)", (now, dumps(packets), dumps(review), dumps(review.get("usage", {}))))
                self.store.event("research_cycle", {"symbols": len(packets), "eligible": sum(p["eligible"] for p in packets), "review_status": review["status"]})
            self.worker("research", "healthy", "Evidence screens recorded; agent cannot override vetoes")
            return {"packets": packets, "review": review}

    def start_research(self):
        if not self.settings.enable_research: raise RuleViolation("Research is disabled by server configuration")
        if self.research_lock.locked() or getattr(self, "research_pending", False): return {"status": "already-running"}
        self.research_pending = True
        self.worker("research", "running", "Collecting source evidence and a bounded CLI review")
        async def job():
            try: await self.research_cycle()
            except asyncio.CancelledError: raise
            except Exception:
                self.worker("research", "error", "Research failed; no picks accepted")
                self.store.event("research_failed", {"execution_enabled": False})
            finally: self.research_pending = False
        self.tasks = [t for t in self.tasks if not t.done()]
        self.tasks.append(asyncio.create_task(job()))
        return {"status": "started", "execution_enabled": False}

    async def arm_exit(self, plan):
        async with self.lock:
            if not self.settings.enable_exit_monitor: raise RuleViolation("Local exit monitor is disabled")
            plans = self.store.get("exit_plans", {})
            if plan["id"] in plans:
                if plans[plan["id"]]["request"] != plan: raise RuleViolation("Exit ID belongs to another plan")
                return plans[plan["id"]]
            if any(p["request"]["symbol"] == plan["symbol"] and p["state"] in {"armed", "triggered"} for p in plans.values()):
                raise RuleViolation("An exit plan already reserves this symbol")
            quote = self.store.get("quotes", {}).get(plan["symbol"], {})
            if not self.connected or not 0 <= age(quote.get("at")) <= self.settings.max_quote_age:
                raise RuleViolation("Fresh connected quote required to arm an exit")
            # Validate current sell availability and all account/session checks.
            intent = {"client_order_id": "astral-exit-"+plan["id"], "symbol": plan["symbol"], "side": "sell",
                      "notional": float(self.settings.max_order), "execution": "bounded", "ttl_seconds": 60, "strategy_id": plan["strategy_id"]}
            self.risk_payload(intent)
            bid = D(quote["bid"])
            if not 0 < D(plan["stop_price"]) < bid or (plan.get("target_price") is not None and D(plan["target_price"]) <= bid):
                raise RuleViolation("Stop must be below bid; target must be above bid")
            value = {"request": plan, "state": "armed", "at": utcnow(), "intent": intent, "broker_native": False}
            plans[plan["id"]] = value
            with self.store.transaction():
                self.store.put("exit_plans", plans);self.store.event("exit_armed", value)
            return value

    async def exit_cycle(self):
        for key, plan in self.store.get("exit_plans", {}).items():
            if plan["state"] not in {"armed", "triggered"}: continue
            if plan["state"] == "armed":
                q = self.store.get("quotes", {}).get(plan["request"]["symbol"], {})
                if not 0 <= age(q.get("at")) <= self.settings.max_quote_age: continue
                bid = D(q["bid"])
                if bid > D(plan["request"]["stop_price"]) and (plan["request"].get("target_price") is None or bid < D(plan["request"]["target_price"])): continue
                plan.update(state="triggered", triggered_at=utcnow())
                with self.store.transaction():
                    plans = self.store.get("exit_plans");plans[key] = plan
                    self.store.put("exit_plans", plans);self.store.event("exit_triggered", plan)
            try:
                result = await self.place(plan["intent"])
            except RuleViolation as exc:
                plan["last_error"] = str(exc)
            else:
                plan["order_status"] = result["status"]
                if result["status"] in TERMINAL:
                    plan["state"] = "completed" if result["status"] == "filled" else "attention"
                    # Never claim a flat position from a partial/order fill alone.
                    snap = self.store.get("account_snapshot", {})
                    remaining = next((D(p["qty"]) for p in snap.get("positions", []) if symbol_for(p["symbol"]) == plan["request"]["symbol"]), D(0))
                    plan["remaining_broker_qty"] = str(remaining)
                    own = D(self.inventory()["books"].get(plan["request"]["symbol"], {}).get(book_for(plan["request"]), "0"))
                    if own > D(self.store.get("assets")[plan["request"]["symbol"]]["increment"]): plan["state"] = "attention"
            plans = self.store.get("exit_plans");plans[key] = plan;self.store.put("exit_plans", plans)

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
                "unprotected_full_value_fraction": str(self.settings.max_unprotected_risk),
                "local_exit_monitor": self.settings.enable_exit_monitor,
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
            self.risk_payload(intent, shadow=True)
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
                "inventory": self.inventory(), "exit_plans": list(self.store.get("exit_plans", {}).values()),
                "shadow": {"enabled": self.settings.enable_shadow, "counts": self.store.rows("SELECT json_extract(result,'$.decision') decision,COUNT(*) count FROM shadow GROUP BY decision"),
                           "recent": [{"at": r["at"], "intent": json.loads(r["intent"]), "result": json.loads(r["result"]), "input_hash": r["input_hash"]} for r in self.store.rows("SELECT * FROM shadow ORDER BY id DESC LIMIT 16")]},
                "fee_coverage": self.store.get("fee_coverage"),
                "fee_activities": [json.loads(r["payload"]) for r in self.store.rows("SELECT payload FROM activities ORDER BY at DESC LIMIT 30")],
                "research": {"enabled": self.settings.enable_research, "model_enabled": self.settings.enable_codex_research,
                             "packets": self.store.get("research_packets", []), "review": self.store.get("research_review"),
                             "last_model_review": self.store.get("codex_review"), "budget": self.store.get("codex_budget")},
                "crypto_universe": self.store.get("crypto_universe"),
                "timing": [{"symbol": r["symbol"], "strategy": r["strategy"], **json.loads(r["result"])} for r in self.store.rows("SELECT * FROM timing ORDER BY id DESC LIMIT 16")],
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
                "costs": {"actual_model_api_usd": 0, "model_workers_enabled": self.settings.enable_codex_research, "hosting_and_data_usd": None,
                          "cli_usage": self.store.get("codex_review", {}).get("usage"), "cli_actual_usd": None},
                "uptime_seconds": round(time.monotonic()-self.started)}
