"""Owned browser-test service: temporary simulator ledger, no broker or model access."""
from pathlib import Path
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
import uvicorn

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

        uvicorn.run(app, host='127.0.0.1', port=18766, workers=1, log_level='warning')
