import json

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.config import Settings
from backend.learning_engine import run
from backend.learning_view import latest_report
from backend.store import Store

AS_OF = '2026-01-02T12:00:00+00:00'


def saved(tmp_path):
    ledger = tmp_path/'source.sqlite'
    store = Store(ledger, 'simulator');store.close()
    folder, _ = run(ledger, AS_OF, tmp_path/'reports')
    return ledger, folder


def test_summary_preserves_boundaries_and_excludes_receipt_bodies(tmp_path):
    ledger, folder = saved(tmp_path)
    r = latest_report(folder.parent, ledger, 'simulator')
    assert r['status'] == 'saved_report'
    assert r['data_and_outcomes']['resolved_net_pnl_labels'] == 0
    assert r['model_research']['usefulness']['incremental_return'] is None
    assert len(r['protected_windows']) == 2
    assert 'records' not in r['model_research']
    assert not any(r['authority'].values())
    assert 'source_ledger' not in json.dumps(r)


def test_changed_saved_report_is_not_shown(tmp_path):
    ledger, folder = saved(tmp_path)
    report = json.loads((folder/'report.json').read_text())
    report['data_and_outcomes']['resolved_net_pnl_labels'] = 100
    (folder/'report.json').write_text(json.dumps(report))
    assert latest_report(folder.parent, ledger, 'simulator')['status'] == 'unavailable'


def test_summary_must_match_application_ledger_and_mode(tmp_path):
    ledger, folder = saved(tmp_path)
    assert latest_report(folder.parent, ledger, 'alpaca')['status'] == 'unavailable'
    assert latest_report(folder.parent, tmp_path/'other.sqlite', 'simulator')['status'] == 'unavailable'


def test_endpoint_reads_saved_results_without_launching_an_evaluation(tmp_path, monkeypatch):
    import backend.app as module
    ledger, folder = saved(tmp_path)
    calls = []
    def cached(directory, source, mode):
        calls.append((source, mode))
        return latest_report(folder.parent, source, mode)
    monkeypatch.setattr(module, 'latest_learning_report', cached)
    cfg = Settings(mode='simulator', db_path=ledger)
    with TestClient(create_app(cfg, background=False), base_url='http://127.0.0.1') as client:
        store = client.app.state.engine.store
        before = store.rows('SELECT COUNT(*) n FROM events')[0]['n']
        response = client.get('/api/learning/report')
        assert response.status_code == 200 and response.json()['status'] == 'saved_report'
        assert response.headers['cache-control'] == 'no-store'
        assert store.rows('SELECT COUNT(*) n FROM events')[0]['n'] == before
    assert calls == [(ledger, 'simulator')]
    assert len(list(folder.parent.glob('run-*'))) == 1
