from copy import deepcopy
import json
from pathlib import Path
import sqlite3

import pytest

from backend.learning_engine import snapshot, evaluate, run, readonly, protected_windows, digest
from backend.store import Store

AT = '2026-01-01T12:00:00+00:00'
END = '2026-01-01T12:05:00+00:00'
AS_OF = '2026-01-02T00:00:00+00:00'


def packet():
    return {'symbol': 'BTC', 'horizon': 'swing', 'as_of': AT, 'expires_at': END,
            'eligible': True, 'vetoes': [], 'facts': {'spread_bps': '2', 'avg_daily_dollar_volume_20': '2000000', 'proposed_notional': '25'},
            'evidence': [{'id': 'quote:BTC', 'kind': 'quote', 'at': AT, 'known_at': AT}]}


def review(decision='propose'):
    p = packet()
    picks = [{'symbol': 'BTC', 'why_now': 'Reason', 'counter_case': 'Counter', 'invalidation': 'Invalidation',
              'evidence_ids': ['quote:BTC'], **p['facts']}] if decision == 'propose' else []
    return {'status': 'reviewed', 'at': '2026-01-01T12:01:00+00:00', 'model': 'fixture-model', 'material_hash': 'fixture',
            'review': {'decision': decision, 'summary': 'Fixture', 'picks': picks},
            'usage': {'input_tokens': 100, 'output_tokens': 20}, 'actual_usd': None}


def ledger(tmp_path):
    path = tmp_path/'source.sqlite'
    store = Store(path, 'simulator')
    store.close()
    return path


def add(path, result=None, packets=None, at=AT, raw_packet=None):
    with sqlite3.connect(path) as db:
        db.execute('INSERT INTO research(at,packet,result,usage) VALUES(?,?,?,?)',
                   (at, raw_packet if raw_packet is not None else json.dumps(packets if packets is not None else [packet()]), json.dumps(result or review()), '{}'))


def report(path, windows=None):
    windows = windows or []
    data = snapshot(path, AS_OF, windows)
    return evaluate(data, {'protected_windows': windows})


def test_source_is_read_only_and_approval_is_never_a_profit_label(tmp_path):
    path = ledger(tmp_path)
    with sqlite3.connect(path) as db:
        db.execute('INSERT INTO observations(at,request,outcome,context) VALUES(?,?,?,?)', (AT, '{}', 'approved', '{}'))
        db.execute('INSERT INTO fills VALUES(?,?,?,?)', ('f', 'o', AT, '{}'))
    before = path.read_bytes()
    with readonly(path) as db:
        with pytest.raises(sqlite3.OperationalError):
            db.execute("DELETE FROM fills")
    r = report(path)
    assert r['data_and_outcomes']['decision_categories'] == {'risk_approved': 1}
    assert r['data_and_outcomes']['resolved_net_pnl_labels'] == 0
    assert r['model_research']['usefulness']['incremental_return'] is None
    assert not any(r['authority'].values())
    assert path.read_bytes() == before
    with pytest.raises(FileNotFoundError):
        snapshot(tmp_path/'absent.sqlite', AS_OF, [])
    assert not (tmp_path/'absent.sqlite').exists()


def test_holdouts_exclude_bodies_and_stay_reserved_after_end(tmp_path):
    path = ledger(tmp_path)
    add(path, at='2026-01-01T13:00:00+00:00', raw_packet='DO NOT PARSE')
    w = [{'id': 'reserved', 'starts_at': AT, 'ends_at': '2026-01-01T14:00:00+00:00'}]
    data = snapshot(path, AS_OF, w)
    assert data['metadata']['research']['protected_window'] == 1
    assert data['records']['research'] == []
    assert not report(path, w)['issues']


def test_late_record_and_future_evidence_cannot_become_usable(tmp_path):
    path = ledger(tmp_path)
    add(path, at='2026-01-03T00:00:00+00:00', raw_packet='DO NOT PARSE')
    p = packet();p['evidence'][0]['known_at'] = '2026-01-01T12:01:00+00:00'
    add(path, packets=[p])
    r = report(path)
    assert r['inventory']['research']['after_cutoff'] == 1
    assert r['model_research']['contract_checks']['temporal_incomplete'] == 1
    assert 'future_evidence' in r['model_research']['records'][0]['temporal_issues']


def test_completed_after_cutoff_or_inside_holdout_is_not_scored(tmp_path):
    path = ledger(tmp_path)
    late = review();late['at'] = '2026-01-03T00:00:00+00:00';add(path, late)
    held = review();held['at'] = '2026-01-01T13:00:00+00:00';add(path, held)
    w = [{'id': 'reserved', 'starts_at': '2026-01-01T12:30:00+00:00', 'ends_at': '2026-01-01T14:00:00+00:00'}]
    r = report(path, w)
    assert not r['model_research']['contract_checks']
    assert r['issues'] == {'model_completed_after_cutoff': 1, 'model_completed_in_protected_window': 1}
    assert all(not x['scored'] for x in r['model_research']['records'])


def test_cache_disabled_failure_and_duplicates_are_distinct_not_new_trials(tmp_path):
    path = ledger(tmp_path)
    add(path);add(path)
    cached = review();cached['cached'] = True;add(path, cached)
    add(path, {'status': 'disabled'});add(path, {'status': 'failed'})
    r = report(path)['model_research']
    assert r['receipt_categories'] == {'completed': 2, 'duplicate_completed_receipt': 1, 'cached': 1, 'skipped': 1, 'failed': 1}
    assert r['contract_checks']['contract_passed'] == 1
    assert r['recorded_usage'] == {'input_tokens': 100, 'output_tokens': 20}
    assert r['costs']['unknown_cost_receipts'] == 1
    assert r['costs']['total_actual_usd'] is None


def test_malformed_packet_expiry_keeps_contract_and_temporal_results_separate(tmp_path):
    path = ledger(tmp_path)
    p = packet()
    p['expires_at'] = 'bad'
    add(path, packets=[p])
    r = report(path)
    models = r['model_research']
    receipt = models['records'][0]
    assert receipt['status'] == 'evaluated'
    assert receipt['scored'] is True
    assert receipt['contract'] == 'passed'
    assert receipt['picks_checked'] == 1
    assert receipt['temporal_issues'] == ['malformed_packet']
    assert 'malformed_research_record' not in r['issues']
    assert models['contract_checks']['contract_passed'] == sum(
        x['status'] == 'evaluated' and x.get('contract') == 'passed' for x in models['records'])
    assert models['contract_checks']['temporal_incomplete'] == 1


def test_stale_cached_review_is_skipped(tmp_path):
    path = ledger(tmp_path)
    add(path, {'status': 'stale-review', 'cached': True, 'execution_enabled': False})
    models = report(path)['model_research']
    assert models['receipt_categories'] == {'skipped': 1}
    assert models['records'][0]['status'] == 'skipped'
    assert models['records'][0]['scored'] is False
    assert not models['contract_checks']
    assert not models['recorded_usage']


@pytest.mark.parametrize('bad', ['citation', 'numeric', 'veto', 'rationale', 'contradiction'])
def test_model_contract_rejects_unsupported_claims_and_picks(tmp_path, bad):
    path = ledger(tmp_path);v = review();p = packet();pick = v['review']['picks'][0]
    if bad == 'citation':pick['evidence_ids'] = ['invented']
    if bad == 'numeric':pick['proposed_notional'] = '2500'
    if bad == 'veto':p['eligible'] = False;p['vetoes'] = ['risk gate']
    if bad == 'rationale':pick['counter_case'] = '   '
    if bad == 'contradiction':v['review']['decision'] = 'abstain'
    add(path, v, [p]);r = report(path)
    assert r['model_research']['contract_checks']['contract_failed'] == 1
    assert r['model_research']['usefulness']['status'] == 'insufficient_evidence'


def test_abstention_and_unknown_quote_arrival_do_not_claim_profit_or_full_timing(tmp_path):
    path = ledger(tmp_path);p = packet();p['eligible'] = False;p['vetoes'] = ['risk gate'];p['evidence'][0].pop('known_at')
    add(path, review('abstain'), [p]);r = report(path)['model_research']
    assert r['decisions'] == {'abstain': 1}
    assert r['contract_checks']['contract_passed'] == 1
    assert r['contract_checks']['picks_checked'] == 0
    assert r['records'][0]['temporal_issues'] == ['quote_arrival_not_explicit']
    assert r['usefulness']['matched_resolved_pairs'] == 0


def test_bad_json_and_naive_dates_are_retained_as_exclusions(tmp_path):
    path = ledger(tmp_path);add(path, raw_packet='{')
    add(path, at='2026-01-01T12:00:00')
    r = report(path)
    assert r['inventory']['research']['invalid_timestamp'] == 1
    assert r['issues']['malformed_research_record'] == 1


def test_registered_run_is_reproducible_and_keeps_raw_prompts_private(tmp_path):
    path = ledger(tmp_path);v = review('abstain');v['review']['summary'] = 'PRIVATE_TEST_RATIONALE';add(path, v)
    out = tmp_path/'results'
    a, r1 = run(path, AS_OF, out);b, r2 = run(path, AS_OF, out)
    assert a != b and r1 == r2
    contract = json.loads((a/'contract.json').read_text())
    assert r1['contract_sha256'] == digest(contract)
    assert contract['source_sha256']['backend/learning_engine.py']
    assert all('PRIVATE_TEST_RATIONALE' not in p.read_text() for p in a.iterdir())
    assert (a/'report.json').stat().st_mode & 0o077 == 0
    with pytest.raises(ValueError):run(path, '2999-01-01T00:00:00+00:00', out)


def test_changed_protected_manifest_is_rejected(tmp_path):
    windows = protected_windows()
    assert len(windows) == 2
    root = Path(__file__).resolve().parents[1]
    for relative in ('experiments/btc-forward-holdout-v1.json', 'experiments/btc-liquidity-depth-v1.json'):
        target = tmp_path/relative;target.parent.mkdir(exist_ok=True)
        target.write_text((root/relative).read_text())
    target.write_text(target.read_text().replace('2026-11-08', '2026-11-09'))
    with pytest.raises(ValueError):protected_windows(tmp_path)
