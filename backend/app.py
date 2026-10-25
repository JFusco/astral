import asyncio
import fcntl
import json
import time
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .config import ROOT, Settings
from .engine import Engine, RuleViolation
from .broker import BrokerFailure
from .store import Store, dumps


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


def create_app(settings=None, broker_factory=None, background=True):
    cfg = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app):
        cfg.db_path.parent.mkdir(parents=True, exist_ok=True)
        lock_file = open(str(cfg.db_path)+".lock", "a")
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            lock_file.close()
            raise RuntimeError("Another ASTRAL executor owns this database; use one worker")
        store = Store(cfg.db_path, cfg.mode)
        engine = Engine(cfg, store, broker_factory(cfg, store) if broker_factory else None)
        app.state.engine = engine
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
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "[::1]"])

    @app.middleware("http")
    async def local_boundary(request: Request, call_next):
        if request.url.path.startswith("/api/") and request.method not in {"GET", "HEAD"}:
            origin = request.headers.get("origin")
            expected = f"{request.url.scheme}://{request.headers.get('host')}"
            if request.headers.get("x-astral-intent") != "paper-only" or (origin and origin != expected) or request.headers.get("sec-fetch-site") == "cross-site":
                return JSONResponse({"detail": "Same-origin paper intent header required"}, status_code=403)
        response = await call_next(request)
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
        e = request.app.state.engine
        state = e.state()
        return {"service_version": "0.2", "alive": True, "paper_only": True, "mode": cfg.mode,
                "configured": cfg.configured, "broker_ready": state["connected"],
                "orders_enabled": cfg.enable_orders, "uptime_seconds": state["uptime_seconds"]}

    @app.get("/api/state")
    async def state(request: Request):
        return request.app.state.engine.state()

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
                    yield f"event: state\ndata: {dumps(e.state())}\n\n"
                    next_state = time.monotonic()+2
                if not rows: yield ": heartbeat\n\n"
                await asyncio.sleep(.5)

        return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    # Same origin as API; credentials never enter browser code. No CORS wildcard.
    app.mount("/", StaticFiles(directory=ROOT / "dist", html=True), name="dashboard")
    return app


app = create_app()
