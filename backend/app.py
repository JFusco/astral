import asyncio
import fcntl
import json
import time
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .config import ROOT, Settings
from .engine import Engine, RuleViolation
from .broker import BrokerFailure
from .store import Store, dumps, utcnow
from .accounting_view import latest_report
from .learning_view import latest_report as latest_learning_report


class Intent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    client_order_id: str = Field(pattern=r"^astral-[a-zA-Z0-9-]{8,40}$")
    symbol: Literal["BTC", "ETH", "SOL", "SPY", "QQQ", "GLD", "TLT", "IWM"]
    side: Literal["buy", "sell"]
    notional: float = Field(gt=0, le=1000, allow_inf_nan=False)
    execution: Literal["patient", "bounded", "market"] = "bounded"
    ttl_seconds: int = Field(default=60, ge=10, le=300)
    strategy_id: Literal["manual", "lifecycle_test", "swing", "intraday"] = "manual"


class ExitPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[a-zA-Z0-9-]{8,25}$")
    symbol: Literal["BTC", "ETH", "SOL", "SPY", "QQQ", "GLD", "TLT", "IWM"]
    strategy_id: Literal["manual", "swing", "intraday"] = "manual"
    stop_price: float = Field(gt=0, allow_inf_nan=False)
    target_price: float | None = Field(default=None, gt=0, allow_inf_nan=False)


class Halt(BaseModel):
    model_config = ConfigDict(extra="forbid")
    halted: bool


class ResearchBar(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symbol: str = Field(min_length=1, max_length=10)
    source: str = Field(min_length=1, max_length=100)
    feed: str = Field(min_length=1, max_length=100)
    adjustment: Literal["raw"] = "raw"
    at: str = Field(max_length=40)
    closed_at: str = Field(max_length=40)
    known_at: str = Field(max_length=40)
    open: str = Field(max_length=40)
    high: str = Field(max_length=40)
    low: str = Field(max_length=40)
    close: str = Field(max_length=40)
    volume: str = Field(max_length=40)


class RiskCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symbol: Literal["BTC", "ETH", "SOL", "SPY", "QQQ", "GLD", "TLT", "IWM"]
    horizon: Literal["swing", "intraday"]
    bars: list[ResearchBar] = Field(min_length=31, max_length=500)


def create_app(settings=None, broker_factory=None, background=True, activity_observation=None):
    cfg = settings or Settings.from_env()
    if activity_observation and (not cfg.enable_activity_feed
                                or cfg.db_path.resolve() != activity_observation.prepared.ledger):
        raise ValueError('Observation requires its prepared ledger and explicit reader settings')

    @asynccontextmanager
    async def lifespan(app):
        cfg.db_path.parent.mkdir(parents=True, exist_ok=True)
        lock_file = open(str(cfg.db_path)+".lock", "a")
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            lock_file.close()
            raise RuntimeError("Another ASTRAL executor owns this database; use one worker")
        if activity_observation:
            try:
                activity_observation.prepared.validate_ledger()
            except BaseException:
                lock_file.close()
                raise
        store = Store(cfg.db_path, cfg.mode)
        engine = Engine(cfg, store, broker_factory(cfg, store) if broker_factory else None, activity_observation)
        app.state.engine = engine
        # One serialized SSE state frame per lifespan/engine; never persisted.
        app.state.state_frame = {"at": 0.0, "body": None}
        try:
            if background:
                await engine.start()
            elif cfg.configured:
                await engine.refresh_quotes();await engine.reconcile()
            yield
        finally:
            await engine.stop()
            store.close()
            fcntl.flock(lock_file, fcntl.LOCK_UN)
            lock_file.close()

    app = FastAPI(title="ASTRAL paper service", version="0.2", lifespan=lifespan)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "[::1]", "application"])

    @app.middleware("http")
    async def local_boundary(request: Request, call_next):
        if request.url.path.startswith("/api/") and request.method not in {"GET", "HEAD"}:
            origin = request.headers.get("origin")
            expected = f"{request.url.scheme}://{request.headers.get('host')}"
            if request.headers.get("x-astral-intent") != "paper-only" or (origin and origin != expected) or request.headers.get("sec-fetch-site") == "cross-site":
                return JSONResponse({"detail": "Same-origin paper intent header required"}, status_code=403)
        started = time.monotonic()
        response = await call_next(request)
        observation = request.app.state.engine.activity_observation
        if observation and request.url.path == '/api/state':
            observation.latencies['state'].add((time.monotonic()-started)*1000)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        return response

    @app.exception_handler(RuleViolation)
    async def rule_error(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=409)

    @app.exception_handler(BrokerFailure)
    async def broker_error(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=503)

    @app.get("/api/health")
    async def health(request: Request):
        # Liveness only; the full dashboard state is never assembled here.
        e = request.app.state.engine
        return {"service_version": "0.2", "alive": True, "paper_only": True, "mode": cfg.mode,
                "configured": cfg.configured, "broker_ready": e.broker_ready(),
                "orders_enabled": cfg.enable_orders, "uptime_seconds": round(time.monotonic()-e.started)}

    @app.get("/api/state")
    async def state(request: Request):
        return request.app.state.engine.state()

    @app.get('/api/accounting/observation')
    async def accounting_observation(request: Request):
        engine = request.app.state.engine
        observation = engine.activity_observation
        if not observation:
            return {'status': 'disabled', 'reader_enabled': False, 'orders_enabled': cfg.enable_orders}
        coverage = observation.coverage(engine.store)
        return {**observation.summary(), **coverage}

    @app.get("/api/health-inputs")
    async def health_inputs(request: Request):
        # Small read-only observations for the independent health engine. No
        # full replay/state scan, account values, prompts, credentials or writes.
        e = request.app.state.engine
        snap = e.store.get('account_snapshot', {})
        model = e.store.get('codex_review', {})
        quotes = e.store.get('quotes', {})
        last_event = e.store.rows('SELECT at FROM events ORDER BY seq DESC LIMIT 1')
        return JSONResponse({'as_of':utcnow(), 'mode':e.settings.mode, 'configured':e.settings.configured,
                             'connected':e.connected, 'snapshot_at':snap.get('at'),
                             'session_open':snap.get('clock',{}).get('is_open'),
                             'orders_enabled':e.settings.enable_orders,
                             'model_enabled':e.settings.enable_codex_research,
                             'ledger_at':last_event[0]['at'] if last_event else None,
                             'model':{k:model.get(k) for k in ('model','at','status')},
                             'workers':[{k:w.get(k) for k in ('name','status','at')} for w in e.workers.values()],
                             'quotes':{s:{k:q.get(k) for k in ('at','received_at','source')} for s,q in quotes.items()}},
                            headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})

    @app.get('/api/accounting/report')
    async def accounting_report():
        return await asyncio.to_thread(latest_report, ROOT/'runtime/accounting-evaluation', cfg.db_path, cfg.mode)

    @app.get('/api/learning/report')
    async def learning_report():
        return await asyncio.to_thread(latest_learning_report, ROOT/'runtime/learning-evaluation', cfg.db_path, cfg.mode)

    @app.post("/api/orders", status_code=202)
    async def submit(body: Intent, request: Request):
        return await request.app.state.engine.place(body.model_dump())

    @app.post("/api/orders/{client_id}/cancel")
    async def cancel(client_id: str, request: Request):
        return await request.app.state.engine.cancel(client_id)

    @app.post("/api/halt")
    async def halt(body: Halt, request: Request):
        e = request.app.state.engine
        async with e.lock:
            if not body.halted and e.store.get("risk_latch"):
                raise RuleViolation("Loss circuit breaker requires operator review; the entry switch cannot clear it")
            with e.store.transaction():
                e.store.put("halted", body.halted)
                e.store.event("entry_halt", {"halted": body.halted})
        return {"halted": body.halted}

    @app.post("/api/risk/plan")
    async def risk_plan(body: RiskCandidate, request: Request):
        e = request.app.state.engine
        async with e.lock:
            return e.plan(body.model_dump())

    @app.post("/api/risk/shadow")
    async def shadow(body: Intent, request: Request):
        return await request.app.state.engine.shadow(body.model_dump())

    @app.post("/api/exits")
    async def exits(body: ExitPlan, request: Request):
        return await request.app.state.engine.arm_exit(body.model_dump())

    @app.post("/api/research/run", status_code=202)
    async def research(request: Request):
        return request.app.state.engine.start_research()

    @app.post("/api/reconcile")
    async def reconcile(request: Request):
        await request.app.state.engine.reconcile()
        return request.app.state.engine.state()

    def state_frame(app):
        # Streams share one frame for at most 2 s. Expiry is checked before
        # delivery, and a failed rebuild leaves nothing stale to reuse.
        frame = app.state.state_frame
        if frame["body"] is None or time.monotonic()-frame["at"] >= 2:
            frame["body"] = None
            frame["body"], frame["at"] = dumps(app.state.engine.state()), time.monotonic()
        return frame["body"]

    @app.get("/api/events")
    async def stream(request: Request, after: int = 0):
        e = request.app.state.engine
        try:
            cursor = max(0, int(request.headers.get("last-event-id", after)))
        except ValueError:
            raise HTTPException(400, "Invalid event cursor")

        async def events():
            nonlocal cursor
            next_state = 0
            while not await request.is_disconnected():
                rows = e.store.events_after(cursor)
                for row in rows:
                    cursor = row["seq"]
                    yield f"id: {cursor}\nevent: ledger\ndata: {dumps(row)}\n\n"
                if time.monotonic() >= next_state:
                    yield f"event: state\ndata: {state_frame(request.app)}\n\n"
                    next_state = time.monotonic()+2
                if not rows: yield ": heartbeat\n\n"
                await asyncio.sleep(.5)

        return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    return app


app = create_app()
