"""Local-only companion: independent DB and lifecycle preserve the shadow pilot."""
import asyncio
from contextlib import asynccontextmanager
import fcntl
import json

from fastapi import FastAPI
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .config import ROOT
from .intelligence import Collector
from .store import Store
from .service_health import HealthMonitor


async def collect(collector):
    while True:
        try:
            await collector.poll()
        except Exception:
            # Source health carries fetch failures; a failed poll must not end
            # collection or bypass the normal retry delay. Cancellation escapes.
            pass
        await asyncio.sleep(30)


@asynccontextmanager
async def lifespan(app):
    directory = ROOT / "runtime"
    directory.mkdir(exist_ok=True)
    lock = open(directory / "intelligence.lock", "a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    # This file is private and ignored. Never load or inherit broker .env keys.
    config_path = directory / "intelligence-config.json"
    config = json.loads(config_path.read_text()) if config_path.exists() else {}
    store = Store(directory / "astral-intelligence.sqlite", "public-intelligence")
    collector = Collector(store, contact=config.get("sec_contact", ""))
    app.state.collector = collector
    task = asyncio.create_task(collect(collector))
    try:
        yield
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        await collector.close()
        store.close()
        lock.close()


app = FastAPI(title="ASTRAL public intelligence", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "intelligence"])


@app.get("/api/intelligence")
async def intelligence():
    from fastapi.responses import JSONResponse
    return JSONResponse(app.state.collector.state(), headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


@app.get("/api/health-inputs")
async def health_inputs():
    from fastapi.responses import JSONResponse
    state = app.state.collector.state()
    sources = [{k:s.get(k) for k in ('id','name','url','category','status','fresh','interval_seconds','last_success_at','last_attempt_at','http_status')}
               for s in state['sources']]
    return JSONResponse({'as_of':state['as_of'], 'sources':sources,
                         'alpaca':HealthMonitor.alpaca_state(app.state.collector.store)},
                        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})
