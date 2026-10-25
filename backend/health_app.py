"""Standalone health service, separate process and ledger from telemetry/trading."""
import asyncio
from contextlib import asynccontextmanager
import fcntl

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .config import ROOT
from .health_engine import HealthEngine
from .store import Store


@asynccontextmanager
async def lifespan(app):
    directory = ROOT/'runtime'
    directory.mkdir(exist_ok=True)
    lock = open(directory/'health.lock','a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    store = Store(directory/'astral-health.sqlite','health')
    engine = HealthEngine(store)
    app.state.health = engine
    tasks = [asyncio.create_task(engine.run()),asyncio.create_task(engine.providers.run())]
    try:
        yield
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks,return_exceptions=True)
        await engine.close()
        store.close()
        lock.close()


app = FastAPI(title='ASTRAL health engine',lifespan=lifespan,docs_url=None,redoc_url=None,openapi_url=None)
app.add_middleware(TrustedHostMiddleware,allowed_hosts=['127.0.0.1','localhost'])
app.add_middleware(CORSMiddleware,allow_origins=['http://127.0.0.1:8766','http://localhost:8766',
                                              'http://127.0.0.1:8765','http://localhost:8765'],allow_methods=['GET'])


@app.get('/api/health/state')
async def state():
    return JSONResponse(app.state.health.state(),headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})
