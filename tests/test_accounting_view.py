import json

from fastapi.testclient import TestClient

from backend.accounting_engine import run
from backend.accounting_view import latest_report
from backend.app import create_app
from backend.config import Settings
from backend.store import Store

AS_OF = '2026-01-02T12:00:00+00:00'


def saved(tmp_path):
    ledger = tmp_path/'source.sqlite';store = Store(ledger, 'simulator');store.close()
    costs = tmp_path/'costs.json'
    costs.write_text(json.dumps({'version': 1, 'charges': [], 'subscriptions': [
        {'id': 'private-id', 'provider': 'fixture', 'status': 'active', 'billing_interval': 'monthly',
         'billing_amount': '500', 'currency': 'USD', 'known_at': AS_OF, 'personal_fraction': '0',
         'source_ref': 'PRIVATE_RECEIPT', 'funding_note': 'PRIVATE_FUNDING_NOTE'}]}))
    folder, _ = run(ledger, AS_OF, tmp_path/'reports', costs)
    return ledger, folder


def test_app_summary_preserves_unknowns_and_excludes_private_source_details(tmp_path):
    ledger, folder = saved(tmp_path)
    report = latest_report(folder.parent, ledger, 'simulator')
    assert report['status'] == 'saved_report'
    assert report['operating_costs']['monthly_astral_personal_budget_by_currency'] == {'USD': '0'}
    assert report['money_results']['realized_net_pnl_usd'] is None
    assert report['operating_costs']['actual_total_by_currency'] is None
    encoded = json.dumps(report)
    assert 'PRIVATE_RECEIPT' not in encoded and 'PRIVATE_FUNDING_NOTE' not in encoded
    assert 'private-id' not in encoded and 'source_ledger' not in encoded
    assert not any(report['authority'].values())


def test_report_tampering_and_wrong_mode_cannot_be_displayed_as_valid(tmp_path):
    ledger, folder = saved(tmp_path)
    assert latest_report(folder.parent, ledger, 'alpaca')['status'] == 'unavailable'
    report = json.loads((folder/'report.json').read_text());report['money_results']['realized_net_pnl_usd'] = '100'
    (folder/'report.json').write_text(json.dumps(report))
    assert latest_report(folder.parent, ledger, 'simulator')['status'] == 'unavailable'


def test_report_for_another_ledger_is_not_the_application_report(tmp_path):
    ledger, folder = saved(tmp_path)
    assert latest_report(folder.parent, tmp_path/'other.sqlite', 'simulator')['status'] == 'unavailable'


def test_read_only_application_endpoint_does_not_start_evaluation(tmp_path, monkeypatch):
    import backend.app as module
    ledger, folder = saved(tmp_path)
    calls = []
    def cached(directory, source, mode):
        calls.append((source, mode))
        return latest_report(folder.parent, source, mode)
    monkeypatch.setattr(module, 'latest_report', cached)
    cfg = Settings(mode='simulator', db_path=ledger)
    with TestClient(create_app(cfg, background=False), base_url='http://127.0.0.1') as client:
        count = client.app.state.engine.store.rows('SELECT COUNT(*) n FROM events')[0]['n']
        response = client.get('/api/accounting/report')
        assert response.status_code == 200 and response.json()['status'] == 'saved_report'
        assert response.headers['cache-control'] == 'no-store'
        assert calls == [(ledger, 'simulator')]
        assert client.app.state.engine.store.rows('SELECT COUNT(*) n FROM events')[0]['n'] == count
    assert len(list(folder.parent.glob('run-*'))) == 1
