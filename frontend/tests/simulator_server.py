"""Owned browser-test service: temporary simulator ledger, no broker or model access."""
from pathlib import Path
import asyncio
import sys
import tempfile
import json

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
REPORT_MODES = {'accounting': {'passthrough', 'fixture', 'unavailable'}, 'learning': {'passthrough', 'fixture'}, 'state': {'passthrough', 'malformed'}}
MALFORMED_STATE = {'service_version': '0.2', 'account': {'equity': 999999}}

if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='astral-next-simulator-') as directory:
        settings = Settings(mode='simulator', db_path=Path(directory)/'simulator.sqlite', enable_orders=True)
        # Separate empty evidence source and reports, never the operator's runtime directory.
        source = Path(directory)/'report-source.sqlite'
        Store(source, 'simulator').close()
        cutoff = '2026-01-02T12:00:00+00:00'
        accounting_dir = Path(directory)/'accounting'
        learning_dir = Path(directory)/'learning'
        costs = Path(directory)/'costs.json'
        costs.write_text(json.dumps({'version': 1, 'subscriptions': [], 'charges': [{
            'id': 'receipt-fixture', 'provider': 'Fixture vendor', 'status': 'confirmed',
            'amount': '10', 'currency': 'USD', 'known_at': cutoff, 'incurred_at': cutoff,
            'source_ref': 'fixture-only', 'receipt_url': 'https://mail.google.com/mail/u/0/#all/0123456789abcdef'}]}))
        accounting_run(source, cutoff, accounting_dir, costs)
        learning_run(source, cutoff, learning_dir)
        app = create_app(settings)

        @app.get('/__test/accounting')
        def saved_accounting():
            return accounting_report(accounting_dir, source, 'simulator')

        @app.get('/__test/learning')
        def saved_learning():
            return learning_report(learning_dir, source, 'simulator')

        control = {'accounting': 'passthrough', 'learning': 'passthrough', 'state': 'passthrough'}
        fixtures = {'accounting': saved_accounting, 'learning': saved_learning}

        def valid(name, mode):
            if name == 'accounting' and mode.startswith('delay:'):
                return mode[6:].isdigit()
            if name == 'state' and mode.startswith('delay-once:'):
                return mode[11:].isdigit()
            return mode in REPORT_MODES.get(name, ())

        @app.post('/__test/control')
        async def set_control(body: dict):
            if not all(isinstance(v, str) and valid(k, v) for k, v in body.items()):
                return JSONResponse({'detail': 'Unknown control'}, status_code=400)
            control.update(body)
            return control

        @app.middleware('http')
        async def controlled_reads(request: Request, call_next):
            name = {'/api/accounting/report': 'accounting', '/api/learning/report': 'learning', '/api/state': 'state'}.get(request.url.path)
            mode = control.get(name, 'passthrough')
            if name == 'state' and mode.startswith('delay-once:'):
                control['state'] = 'passthrough'  # Reset before awaiting: exactly one request is delayed.
                await asyncio.sleep(int(mode[11:]) / 1000)
                return await call_next(request)
            if mode == 'malformed':
                return JSONResponse(MALFORMED_STATE)
            if mode == 'passthrough':
                return await call_next(request)
            if mode == 'unavailable':
                return JSONResponse({'status': 'unavailable', 'reason': 'Fixture report unavailable'})
            if mode.startswith('delay:'):
                await asyncio.sleep(int(mode[6:]) / 1000)
            return JSONResponse(jsonable_encoder(fixtures[name]()))

        uvicorn.run(app, host='127.0.0.1', port=18766, workers=1, log_level='warning')
