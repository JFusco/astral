"""Owned browser-test service: temporary simulator ledger, no broker or model access."""
from pathlib import Path
import asyncio
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.app import create_app
from backend.config import Settings
from backend.store import Store
from backend.accounting_engine import run as accounting_run
from backend.learning_engine import run as learning_run
from backend.accounting_view import latest_report as accounting_report
from backend.learning_view import latest_report as learning_report
from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
import uvicorn

# Server-side reads bypass Playwright's page.route, so tests steer these paths here instead.
REPORT_MODES = {'accounting': {'passthrough', 'fixture', 'unavailable'}, 'learning': {'passthrough', 'fixture'}}

if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='astral-next-simulator-') as directory:
        settings = Settings(mode='simulator', db_path=Path(directory)/'simulator.sqlite', enable_orders=True)
        # Separate empty evidence source and reports, never the operator's runtime directory.
        source = Path(directory)/'report-source.sqlite'
        Store(source, 'simulator').close()
        cutoff = '2026-01-02T12:00:00+00:00'
        accounting_dir = Path(directory)/'accounting'
        learning_dir = Path(directory)/'learning'
        accounting_run(source, cutoff, accounting_dir)
        learning_run(source, cutoff, learning_dir)
        app = create_app(settings)

        @app.get('/__test/accounting')
        def saved_accounting():
            return accounting_report(accounting_dir, source, 'simulator')

        @app.get('/__test/learning')
        def saved_learning():
            return learning_report(learning_dir, source, 'simulator')

        control = {'accounting': 'passthrough', 'learning': 'passthrough'}
        fixtures = {'accounting': saved_accounting, 'learning': saved_learning}

        def valid(name, mode):
            if name == 'accounting' and mode.startswith('delay:'):
                return mode[6:].isdigit()
            return mode in REPORT_MODES.get(name, ())

        @app.post('/__test/control')
        async def set_control(body: dict):
            if not all(isinstance(v, str) and valid(k, v) for k, v in body.items()):
                return JSONResponse({'detail': 'Unknown control'}, status_code=400)
            control.update(body)
            return control

        @app.middleware('http')
        async def controlled_reports(request: Request, call_next):
            name = {'/api/accounting/report': 'accounting', '/api/learning/report': 'learning'}.get(request.url.path)
            mode = control.get(name, 'passthrough')
            if mode == 'passthrough':
                return await call_next(request)
            if mode == 'unavailable':
                return JSONResponse({'status': 'unavailable', 'reason': 'Fixture report unavailable'})
            if mode.startswith('delay:'):
                await asyncio.sleep(int(mode[6:]) / 1000)
            return JSONResponse(jsonable_encoder(fixtures[name]()))

        uvicorn.run(app, host='127.0.0.1', port=18766, workers=1, log_level='warning')
