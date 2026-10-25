"""Local-only companion: independent DB and lifecycle preserve the shadow pilot."""
import asyncio
from contextlib import asynccontextmanager
import fcntl
import json

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .config import ROOT
from .intelligence import Collector
from .store import Store


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
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])
app.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:8766", "http://localhost:8766", "http://127.0.0.1:8765", "http://localhost:8765"], allow_methods=["GET"])


@app.get("/api/intelligence")
async def intelligence():
    from fastapi.responses import JSONResponse
    return JSONResponse(app.state.collector.state(), headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})
