"""Behavioral protection for money counted once and unknown evidence staying blocked.

These fixtures are sanitized or synthetic. Private provider acceptance is a
separate required CLI receipt and never supplied by this suite.
"""
import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import httpx
import pytest

from backend.activity_feed import (SSEParser, parse_sse, collect_batch, current_accounting,
                                   start_batch, retain_batch, publish_projection, read_projection)
from backend.activity_projection import digest, instant, load_mapping, project, ledger_source
from backend.activity_validation import (verify_inputs, import_ledger, import_capture, acceptance,
                                         destinations, connected)
from backend.broker import AlpacaPaper
from backend.config import Settings, SYMBOLS
from backend.store import Store

FIXTURE = Path(__file__).parent/'fixtures/activity_feed/btc-sanitized-v1'
KNOWN = '2030-01-01T00:00:00+00:00'


def document(name):return json.loads((FIXTURE/name).read_text())


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr('backend.inventory.utcnow', lambda: KNOWN)
    store = Store(tmp_path/'ledger.sqlite', 'alpaca')
    import_ledger(store, document('ledger-selected-readonly.json'))
    yield store, document('activity-sse.json'), document('mapping.json')
    store.close()


def replay(setup, capture=None, mapping=None, *, now=KNOWN):
    store, original, reviewed = setup
    capture = deepcopy(capture or original)
    raw = b''.join(('data: '+json.dumps(e)+'\n\n').encode() for e in capture['events'])
    return import_capture(store, capture, raw, mapping or reviewed, now=now)


def pure(setup, capture=None, mapping=None):
    store, original, reviewed = setup
    capture = capture or original
    request = capture['request']
    coverage = {'complete': True, 'account_id': store.get('account_binding'),
                'received_at': request['received_at'], **request['params']}
    return project(ledger_source(store), capture['events'], mapping or reviewed, coverage, knowledge_cutoff=KNOWN)


def test_sanitized_package_replays_without_private_inputs_and_counts_fees_once(setup):
    mapping = verify_inputs(FIXTURE/'mapping.json', allow_fixture=True)
    assert mapping['kind'] == 'sanitized-fixture'
    import hashlib
    for name, sha in document('manifest.json')['files'].items():
        assert hashlib.sha256((FIXTURE/name).read_bytes()).hexdigest() == sha
    result = import_capture(setup[0], setup[1], (FIXTURE/'activity-sse.raw').read_bytes(), mapping, now=KNOWN)
    checks, _ = acceptance(result, setup[0])
    assert all(checks.values()), checks
    assert result['fixture']
    assert result['cash_reconciliation']['cash'] != '99999.56'
    assert len(setup[0].rows('SELECT * FROM fills')) == 4
    assert not setup[0].rows('SELECT * FROM activities')


def test_duplicates_reordering_and_database_restart_do_not_charge_again(setup):
    store, capture, mapping = setup
    first = replay(setup)
    changed = deepcopy(capture);changed['events'] = list(reversed(changed['events']))*2
    again = replay(setup, changed)
    assert first['net_books'] == again['net_books']
    assert first['cash_reconciliation'] == again['cash_reconciliation']
    path = store.db.execute('PRAGMA database_list').fetchone()['file']
    other = Store(path, 'alpaca')
    try:
        third = replay((other, capture, mapping))
        assert all(acceptance(third, other)[0].values())
    finally:other.close()


@pytest.mark.parametrize('kind', ['TRD', 'CFEE', 'JNLC'])
def test_missing_provider_records_block_reconciliation(setup, kind):
    capture = deepcopy(setup[1]);index = next(i for i,e in enumerate(capture['events']) if e['activity_type'] == kind)
    capture['events'].pop(index)
    result = replay(setup, capture)
    assert result['issues'] and not result['effects']
    assert result['cash_reconciliation']['cash'] is None


@pytest.mark.parametrize('ref', [e['ref_id'] for e in document('activity-sse.json')['events'] if e['activity_type']=='JNLC'])
def test_each_cash_journal_is_required_even_when_other_journals_offset(setup, ref):
    capture = deepcopy(setup[1]);capture['events'] = [e for e in capture['events'] if e['ref_id'] != ref]
    assert pure(setup, capture)['cash_reconciliation']['cash'] is None


def test_smallest_btc_fee_cannot_disappear_under_instrument_tolerance(setup):
    capture = deepcopy(setup[1])
    capture['events'] = [e for e in capture['events'] if e['qty'] != '-0.000000001']
    result = pure(setup, capture)
    assert 'unreconciled_asset_quantity' in result['issues']
    assert result['cash_reconciliation']['cash'] is None


@pytest.mark.parametrize('mutation', ['delivery', 'activity', 'correction'])
def test_revised_confirmed_record_stays_blocked_after_restart_and_original_replay(setup, mutation):
    store, capture, _ = setup
    replay(setup)
    changed = deepcopy(capture);fee = next(e for e in changed['events'] if e['activity_type']=='CFEE')
    fee['qty'] = '-0.000001'
    if mutation == 'activity':fee['event_id'] = 'new-delivery'
    if mutation == 'correction':fee['previous_id'] = 'prior-ref'
    assert replay(setup, changed)['issues']
    assert store.rows('SELECT * FROM activity_conflicts')
    again = replay(setup)
    assert 'persistent_activity_conflict' in again['issues']
    assert again['cash_reconciliation']['cash'] is None


@pytest.mark.parametrize('attack', ['mapping', 'owner', 'account', 'local-fill', 'side', 'nan', 'float', 'missing-id', 'future'])
def test_untrusted_evidence_never_produces_financial_effects(setup, attack):
    store, original, reviewed = setup
    capture, mapping = deepcopy(original), deepcopy(reviewed)
    fee = next(e for e in capture['events'] if e['activity_type']=='CFEE')
    if attack=='mapping':mapping['fee_associations'].pop()
    if attack=='owner':mapping['fee_associations'][0]['book']='swing'
    if attack=='account':mapping['account_id']='another-account'
    if attack=='local-fill':store.db.execute('DELETE FROM fills WHERE rowid=(SELECT MIN(rowid) FROM fills)')
    if attack=='side':next(e for e in capture['events'] if e['activity_type']=='TRD')['details']['side']='sell'
    if attack=='nan':fee['qty']='NaN'
    if attack=='float':fee['qty']=-0.1
    if attack=='missing-id':fee.pop('ref_id')
    if attack=='future':fee['executed_at']='2031-01-01T00:00:00Z'
    result=pure(setup,capture,mapping)
    assert result['issues'] and not result['effects']
    assert result['cash_reconciliation']['cash'] is None


@pytest.mark.parametrize('malformed', ['float-quantity', 'missing-ref'])
def test_malformed_capture_publishes_consumable_blocked_accounting(setup, malformed):
    from backend.accounting_engine import at, evaluate, source_snapshot
    store, original, _ = setup
    capture = deepcopy(original)
    fee = next(e for e in capture['events'] if e['activity_type'] == 'CFEE')
    if malformed == 'float-quantity':fee['qty'] = -0.1
    else:fee.pop('ref_id')
    result = replay(setup, capture)
    assert 'invalid_activity_evidence' in result['issues']
    assert result['association_count'] == result['activity_count'] == 0
    for enabled in (True, False):
        current = current_accounting(store, enabled=enabled, now=KNOWN)
        assert 'invalid_activity_evidence' in current['activity_coverage']['issues']
        assert not any(r['passed'] for r in current['accounting_by_symbol'].values())
        assert current['cash_reconciliation']['cash'] is None
    path = Path(store.db.execute('PRAGMA database_list').fetchone()['file'])
    report = evaluate(source_snapshot(path, at(KNOWN)), None, at(KNOWN))
    assert report['fees']['cash_reconciliation']['cash'] is None


@pytest.mark.parametrize('field', ['ref_id', 'event_id', 'activity_type'])
@pytest.mark.parametrize('value', [[], {'unexpected': 'identifier'}], ids=['list', 'object'])
def test_malformed_identifiers_retain_the_entire_batch_and_block_publication(setup, field, value):
    store, original, _ = setup
    replay(setup)
    capture = deepcopy(original)
    capture['events'][-1][field] = value
    result = replay(setup, capture)
    batch = result['batch']
    rows = store.rows('SELECT * FROM activity_events WHERE batch=? ORDER BY ordinal', (batch,))
    assert [json.loads(r['payload']) for r in rows] == capture['events']
    metadata = {'ref_id': 'ref_id', 'event_id': 'event_id', 'activity_type': 'type'}[field]
    assert rows[-1][metadata] is None
    assert parse_sse(rows[-1]['frame']) == [capture['events'][-1]]
    receipt = json.loads(store.rows("SELECT payload FROM activity_batches WHERE id=? AND phase='outcome'", (batch,))[0]['payload'])
    assert parse_sse(bytes.fromhex(receipt['raw_hex'])) == capture['events']
    assert not receipt['complete'] and receipt['error'] == 'invalid_activity_identity'
    assert result['issues'] and not result['effects']
    assert result['cash_reconciliation']['cash'] is None
    current = current_accounting(store, enabled=True, now=KNOWN)
    assert not any(r['passed'] for r in current['accounting_by_symbol'].values())
    assert current['cash_reconciliation']['cash'] is None
    # A subsequent well-formed replay must inspect malformed prior metadata safely.
    assert replay(setup)['cash_reconciliation']['cash'] is None


def test_old_window_unknown_inception_and_legacy_overlap_are_not_cash_proof(setup):
    store, original, _ = setup
    capture=deepcopy(original);capture['request']['params']['since']='2026-10-25T03:24:00Z'
    assert 'cash_history_incomplete' in pure(setup,capture)['issues']
    snap=store.get('account_snapshot');snap['account'].pop('created_at');store.put('account_snapshot',snap)
    assert 'cash_history_incomplete' in pure(setup)['issues']
    store.db.execute('INSERT INTO activities VALUES(?,?,?,?)',('legacy','CFEE',KNOWN,json.dumps({'id':'legacy'})))
    assert 'legacy_activity_overlap_unverified' in pure(setup)['issues']


def test_associations_cannot_become_known_before_their_actual_availability(setup):
    mapping=deepcopy(setup[2]);mapping['known_at']='2031-01-01T00:00:00Z'
    assert 'evidence_not_yet_known' in pure(setup,mapping=mapping)['issues']
    replay(setup)
    assert read_projection(setup[0],cutoff='2029-01-01T00:00:00Z') is None
    current=current_accounting(setup[0],enabled=True,now=KNOWN)
    assert not any(r['passed'] for r in current['accounting_by_symbol'].values())
    assert current['cash_reconciliation']['cash'] is None


@pytest.mark.parametrize('asset', ['ETH','SOL','SPY','QQQ','GLD','TLT','IWM'])
def test_other_tickers_cannot_inherit_btc_accounting_acceptance(setup,asset):
    result=pure(setup)
    assert result['by_symbol']['BTC']['passed']
    assert not result['by_symbol'][asset]['passed']
    capture=deepcopy(setup[1]);extra=deepcopy(next(e for e in capture['events'] if e['activity_type']=='TRD'))
    extra.update(ref_id='unreviewed-'+asset,event_id='delivery-'+asset)
    extra['details']['symbol']=asset+'/USD' if asset in ('ETH','SOL') else asset
    capture['events'].append(extra)
    assert 'unreviewed_trade' in pure(setup,capture)['issues']


def test_simultaneous_mixed_asset_trades_never_get_timestamp_associations(setup):
    capture=deepcopy(setup[1]);trade=deepcopy(next(e for e in capture['events'] if e['activity_type']=='TRD'))
    trade.update(ref_id='eth-ref',event_id='eth-delivery');trade['details']['symbol']='ETH/USD'
    capture['events'].append(trade)
    result=pure(setup,capture)
    assert 'unreviewed_trade' in result['issues'] and not result['effects']


def test_reviewed_fee_never_moves_between_manual_and_swing_books(setup):
    mapping=deepcopy(setup[2]);mapping['fee_associations'][0]['book']='swing'
    assert 'ambiguous_fee_owner' in pure(setup,mapping=mapping)['issues']
    mapping['fee_associations'][0].pop('book')
    assert pure(setup,mapping=mapping)['issues']


def test_unmapped_usd_fee_cannot_be_subtracted_beside_included_fee(setup):
    capture=deepcopy(setup[1]);fee=deepcopy(next(e for e in capture['events'] if e['activity_type']=='CFEE' and e['qty']=='0'))
    fee.update(ref_id='unknown-usd',event_id='unknown-delivery');capture['events'].append(fee)
    result=pure(setup,capture)
    assert 'unassigned_fee' in result['issues'] and result['cash_reconciliation']['cash'] is None


def test_explicitly_reviewed_standalone_usd_fee_is_debited_once(setup):
    store, original, reviewed=setup
    capture,mapping=deepcopy(original),deepcopy(reviewed)
    fee=deepcopy(next(e for e in capture['events'] if e['activity_type']=='CFEE' and e['qty']=='0'))
    fee.update(ref_id='standalone',event_id='standalone-delivery',net_amount='-1.00')
    capture['events'].append(fee);mapping['expected_events']['standalone']=digest(fee)
    mapping['fee_associations'].append({'id':'standalone-association','fee_ref_id':'standalone','fee_sha256':digest(fee),
        'symbol':'BTC','book':'manual','treatment':'standalone-usd','standalone_evidence_sha256':'a'*64})
    snap=store.get('account_snapshot');snap['account']['cash']='99998.70';store.put('account_snapshot',snap)
    result=pure(setup,capture,mapping)
    assert not result['issues']
    assert result['cash_reconciliation']['cash']=='99998.70'
    assert result['cash_reconciliation']['included_fee_usd']=='0.14'


def test_frame_parser_handles_multiline_utf8_and_split_crlf():
    event={'message':'café'};raw=('data: {\r\ndata: "message": "café"}\r\n\r\n').encode()
    parser=SSEParser()
    for byte in raw:parser.feed(bytes([byte]))
    parser.feed(b'',final=True)
    assert [e for e,_ in parser.frames]==[event]


@pytest.mark.parametrize('raw',[b'data: {"a":1}\n',b'data: []\n\n',b'data: {"x":1,"x":2}\n\n',
    b'data: NaN\n\n',b': internal server error\n\n',b': you are reading too slowly, dropped 2 messages\n\n',b'data: \xff\n\n'])
def test_malformed_or_incomplete_stream_is_never_complete(raw):
    with pytest.raises((ValueError,UnicodeError)):parse_sse(raw)


@pytest.mark.parametrize('budget',['MAX_FRAME','MAX_BYTES','MAX_EVENTS'])
def test_resource_limits_fail_closed(monkeypatch,budget):
    monkeypatch.setattr('backend.activity_feed.'+budget,1)
    with pytest.raises(ValueError):parse_sse(b'data: {}\n\ndata: {}\n\n')


def test_nanosecond_cutoffs_and_decimal_input_contracts():
    assert instant('2026-10-25T03:49:34.939799496Z')>instant('2026-10-25T03:49:34.939799Z')
    assert instant('2026-10-25T03:49:34.939799496Z')==instant('2026-10-24T23:49:34.939799496-04:00')


def test_environment_cannot_enable_unactivated_activity_feed(monkeypatch):
    monkeypatch.setattr('dotenv.load_dotenv',lambda *a,**k:None)
    monkeypatch.setenv('ASTRAL_ENABLE_ACTIVITY_FEED','true')
    monkeypatch.setenv('ASTRAL_ACTIVITY_MAPPING_PATH','/private/fixture.json')
    settings=Settings.from_env()
    assert not settings.enable_activity_feed and settings.activity_mapping_path is None


def test_fixture_mapping_and_missing_originals_cannot_satisfy_private_acceptance(tmp_path):
    with pytest.raises(ValueError):verify_inputs(FIXTURE/'mapping.json')
    mapping=document('mapping.json');mapping['kind']='reviewed-provider';mapping['source_files']={'missing.json':'0'*64}
    path=tmp_path/'mapping.json';path.write_text(json.dumps(mapping))
    with pytest.raises(OSError):verify_inputs(path)


def test_validation_refuses_existing_aliases_and_runtime_before_opening_store(tmp_path):
    source=tmp_path/'source.json';source.write_text('{}')
    alias=tmp_path/'alias.sqlite';alias.hardlink_to(source)
    with pytest.raises(ValueError):destinations(alias,tmp_path/'out',[source])
    with pytest.raises(ValueError):destinations(Path('runtime/forbidden/database.sqlite'),Path('runtime/forbidden'),[source])
    assert source.read_text()=='{}'


@pytest.mark.parametrize('failure',['status','content','notice','identity'])
def test_connected_acquisition_retains_failures_without_publishing(setup,failure):
    store,_,_=setup;identity=store.get('account_binding');calls=[]
    def handler(request):
        calls.append(request.method)
        if request.url.path=='/v2/account':return httpx.Response(200,json={'id':'changed' if failure=='identity' else identity,'created_at':'2026-10-25T00:00:00Z'})
        return httpx.Response(403 if failure=='status' else 200,headers={'content-type':'application/json' if failure=='content' else 'text/event-stream'},content=b': internal server error\n\n')
    broker=AlpacaPaper(Settings(api_key='fixture',secret_key='fixture'),store,httpx.MockTransport(handler))
    try:
        batch,result=asyncio.run(collect_batch(broker,store))
        assert not result['complete']
        assert store.rows("SELECT id FROM activity_batches WHERE id=? AND phase='outcome'",(batch,))
        assert not store.rows('SELECT * FROM activity_projections')
        assert set(calls)=={'GET'}
    finally:asyncio.run(broker.close())


def test_abandoned_batch_and_publication_failure_do_not_hide_evidence(setup,monkeypatch):
    store,_,_=setup
    replay(setup)
    abandoned=start_batch(store,store.get('account_binding'),'2026-10-25T00:00:00Z',KNOWN)
    assert 'new_activity_attempt_pending' in current_accounting(store,enabled=True,now=KNOWN)['activity_coverage']['issues']
    assert store.rows('SELECT id FROM activity_batches WHERE id=?',(abandoned,))
    original=store.db.execute('SELECT COUNT(*) FROM activity_projections').fetchone()[0]
    monkeypatch.setattr('backend.activity_feed.project',lambda *a,**k: (_ for _ in ()).throw(RuntimeError('publication interrupted')))
    with pytest.raises(RuntimeError):replay(setup)
    assert store.db.execute('SELECT COUNT(*) FROM activity_projections').fetchone()[0]==original
    assert len(store.rows("SELECT * FROM activity_batches WHERE phase='outcome'"))==2


def controlled_current(setup):
    """A mock-provider acceptance, not evidence about another provider account."""
    store,original,reviewed=setup
    capture,mapping=deepcopy(original),deepcopy(reviewed)
    capture['request']['params']['until']=KNOWN;capture['request']['received_at']=KNOWN
    mapping['kind']='reviewed-provider'
    snapshot=store.get('account_snapshot');snapshot['at']=KNOWN;store.put('account_snapshot',snapshot)
    return replay(setup,capture,mapping)


@pytest.mark.parametrize('age,passed',[(0,True),(90,True),(90.000001,False)])
def test_acquisition_freshness_boundary_and_snapshot_gate_are_independent(setup,age,passed):
    controlled_current(setup)
    now=(datetime.fromisoformat(KNOWN)+timedelta(seconds=age)).isoformat()
    result=current_accounting(setup[0],enabled=True,now=now,max_snapshot_age=120)
    assert result['accounting_by_symbol']['BTC']['passed'] is passed
    assert all(not result['accounting_by_symbol'][s]['passed'] for s in SYMBOLS if s!='BTC')
    assert not current_accounting(setup[0],enabled=False,now=now,max_snapshot_age=120)['accounting_by_symbol']['BTC']['passed']
    if age>30:
        assert not current_accounting(setup[0],enabled=True,now=now)['accounting_by_symbol']['BTC']['passed']


def test_failed_or_running_attempt_invalidates_recent_success_until_validated_recovery(setup):
    controlled_current(setup);store=setup[0]
    assert current_accounting(store,enabled=True,now=KNOWN)['accounting_by_symbol']['BTC']['passed']
    batch=start_batch(store,store.get('account_binding'),'2026-10-25T00:00:00Z',KNOWN)
    assert not current_accounting(store,enabled=True,now=KNOWN)['accounting_by_symbol']['BTC']['passed']
    retain_batch(store,batch,store.get('account_binding'),{'complete':False,'events':[],'raw':b'',
        'received_at':KNOWN,'since':'2026-10-25T00:00:00Z','until':KNOWN})
    assert not current_accounting(store,enabled=True,now=KNOWN)['accounting_by_symbol']['BTC']['passed']
    controlled_current(setup)
    assert current_accounting(store,enabled=True,now=KNOWN)['accounting_by_symbol']['BTC']['passed']


def test_mark_changes_do_not_hide_new_cash_or_quantity_changes(setup):
    controlled_current(setup);store=setup[0]
    snapshot=store.get('account_snapshot');snapshot['account']['cash']='99999.69';store.put('account_snapshot',snapshot)
    result=current_accounting(store,enabled=True,now=KNOWN)
    assert 'accounting_inputs_changed' in result['activity_coverage']['issues']
    assert result['cash_reconciliation']['cash'] is None


def test_saved_report_is_historical_and_cutoff_excludes_later_publication(setup):
    from backend.accounting_engine import source_snapshot,evaluate,at
    store=setup[0];controlled_current(setup)
    path=Path(store.db.execute('PRAGMA database_list').fetchone()['file'])
    cutoff=at(KNOWN)
    source=source_snapshot(path,cutoff)
    result=evaluate(source,None,cutoff)
    assert result['fees']['cash_reconciliation']['cash']=='99999.70'
    assert result['custody']['snapshot_current']
    assert all(not value for value in result['authority'].values())
    before=source_snapshot(path,at('2029-12-31T23:59:59Z'))
    assert before['activity_projection'] is None


@pytest.mark.parametrize('interruption', ['pending', 'failed', 'unpublished', 'revision', 'historical-revision'])
def test_unpublished_evidence_blocks_inventory_and_reports_across_restart_at_its_cutoff(setup, monkeypatch, interruption):
    from backend.accounting_engine import at, evaluate, source_snapshot
    from backend.inventory import attribute
    store, capture, mapping = setup
    monkeypatch.setattr('backend.activity_feed.utcnow', lambda: KNOWN)
    first = controlled_current(setup)
    path = Path(store.db.execute('PRAGMA database_list').fetchone()['file'])
    retained = store.rows('SELECT * FROM activity_projections')
    later = (datetime.fromisoformat(KNOWN)+timedelta(seconds=1)).isoformat()
    monkeypatch.setattr('backend.activity_feed.utcnow', lambda: later)
    batch = start_batch(store, store.get('account_binding'), capture['request']['params']['since'], KNOWN)
    if interruption != 'pending':
        events = deepcopy(capture['events'])
        if interruption.endswith('revision'):
            fee = next(e for e in events if e['activity_type'] == 'CFEE')
            fee.update(event_id='revised-delivery', qty='-0.000001')
        raw = b''.join(('data: '+json.dumps(e)+'\n\n').encode() for e in events)
        receipt = {'events': events, 'raw': raw,
            'complete': interruption != 'failed', 'received_at': later,
            'since': capture['request']['params']['since'], 'until': KNOWN}
        if interruption == 'historical-revision':
            receipt.update(received_at=capture['request']['received_at'], imported_at=later, historical_import=True)
        retain_batch(store, batch, store.get('account_binding'), receipt)
    for reopened in (False, True):
        reader = Store(path, 'alpaca') if reopened else store
        try:
            monkeypatch.setattr('backend.inventory.utcnow', lambda: later)
            inventory = attribute(reader, reader.get('account_snapshot'))
            assert inventory['status'] == 'needs-review'
            assert any(e['reason'] == 'Activity evidence requires reconciliation review' for e in inventory['errors'])
            assert not any(r['classification'] == 'confirmed-fee' for r in inventory['custody_reconciliation']['reductions'])
            report = evaluate(source_snapshot(path, at(later)), None, at(later))
            assert report['fees']['cash_reconciliation']['cash'] is None
            assert 'activity_evidence_requires_review' in report['issues']
            blocked = read_projection(reader, cutoff=later)
            assert not blocked['effects'] and blocked['cash_reconciliation']['cash'] is None
            if interruption.endswith('revision'):assert 'persistent_activity_conflict' in blocked['issues']
            assert reader.rows('SELECT * FROM activity_projections') == retained
            monkeypatch.setattr('backend.inventory.utcnow', lambda: KNOWN)
            assert attribute(reader, reader.get('account_snapshot'))['status'] == 'matched'
            historical = evaluate(source_snapshot(path, at(KNOWN)), None, at(KNOWN))
            assert historical['fees']['cash_reconciliation']['cash'] == '99999.70'
            assert read_projection(reader, cutoff=KNOWN) == first
        finally:
            if reopened:reader.close()
    recovered_at = (datetime.fromisoformat(later)+timedelta(seconds=1)).isoformat()
    monkeypatch.setattr('backend.activity_feed.utcnow', lambda: recovered_at)
    recovery = deepcopy(capture)
    recovery['request']['params']['until'] = recovered_at
    recovery['request']['received_at'] = recovered_at
    mapping = deepcopy(mapping);mapping['kind'] = 'reviewed-provider'
    recovered = replay(setup, recovery, mapping, now=recovered_at)
    if interruption.endswith('revision'):
        assert recovered['cash_reconciliation']['cash'] is None
    else:
        assert not recovered['issues']
        assert read_projection(store, cutoff=recovered_at)['cash_reconciliation']['cash'] == '99999.70'


@pytest.mark.parametrize('readback', ['unchanged', 'cash-moved', 'position-moved', 'positions-unavailable', 'account-unavailable'])
def test_worker_requires_post_stream_balances_before_publishing_usable_accounting(setup, tmp_path, monkeypatch, readback):
    from backend.engine import Engine
    store, _, reviewed = setup
    monkeypatch.setattr('backend.activity_feed.utcnow', lambda: KNOWN)
    snapshot = store.get('account_snapshot');snapshot['at'] = KNOWN
    store.put('account_snapshot', snapshot)
    mapping = deepcopy(reviewed);mapping['kind'] = 'reviewed-provider'
    mapping_path = tmp_path/'controlled-mapping.json';mapping_path.write_text(json.dumps(mapping))
    settings = Settings(api_key='fixture', secret_key='fixture', enable_activity_feed=True, activity_mapping_path=mapping_path)
    calls, account_reads = [], 0
    def handler(request):
        nonlocal account_reads
        calls.append((request.method, request.url.path))
        if request.url.path == '/v2/account':
            account_reads += 1
            if account_reads == 2 and readback == 'account-unavailable':return httpx.Response(503)
            account = deepcopy(snapshot['account'])
            if account_reads == 2 and readback == 'cash-moved':account['cash'] = '99999.69'
            return httpx.Response(200, json=account)
        if request.url.path == '/v2/positions':
            if readback == 'positions-unavailable':return httpx.Response(503)
            return httpx.Response(200, json=[{'symbol': 'BTCUSD', 'qty': '0.000000001'}] if readback == 'position-moved' else [])
        assert request.url.path == '/v2beta1/events/activities'
        return httpx.Response(200, headers={'content-type': 'text/event-stream'}, content=(FIXTURE/'activity-sse.raw').read_bytes())
    broker = AlpacaPaper(settings, store, httpx.MockTransport(handler))
    engine = Engine(settings, store, broker)
    try:
        result = asyncio.run(engine.refresh_activity_feed())
        receipt = json.loads(store.rows("SELECT payload FROM activity_batches WHERE id=? AND phase='outcome'", (result['batch'],))[0]['payload'])
        assert bytes.fromhex(receipt['raw_hex']) == (FIXTURE/'activity-sse.raw').read_bytes()
        assert len(store.rows('SELECT * FROM activity_events')) == 19
        assert all(method == 'GET' for method, _ in calls)
        current = current_accounting(store, enabled=True, now=KNOWN)
        if readback == 'unchanged':
            assert not result['issues']
            assert current['accounting_by_symbol']['BTC']['passed']
            assert current['cash_reconciliation']['cash'] == '99999.70'
        else:
            issue = 'post_stream_balances_changed' if readback.endswith('moved') else 'post_stream_balances_unavailable'
            assert issue in result['issues']
            assert not result['effects'] and result['cash_reconciliation']['cash'] is None
            assert not any(r['passed'] for r in current['accounting_by_symbol'].values())
            assert current['cash_reconciliation']['cash'] is None
        assert store.get('account_snapshot') == snapshot
    finally:asyncio.run(broker.close())


def test_identity_change_after_complete_stream_retains_quarantined_raw_evidence(setup):
    store=setup[0];identity=store.get('account_binding');count=0
    def handler(request):
        nonlocal count
        if request.url.path=='/v2/account':
            count+=1
            return httpx.Response(200,json={'id':identity if count==1 else 'changed','created_at':'2026-10-25T00:00:00Z'})
        return httpx.Response(200,headers={'content-type':'text/event-stream'},content=(FIXTURE/'activity-sse.raw').read_bytes())
    broker=AlpacaPaper(Settings(api_key='fixture',secret_key='fixture'),store,httpx.MockTransport(handler))
    try:
        batch,result=asyncio.run(collect_batch(broker,store))
        assert not result['complete'] and len(result['events'])==19
        row=store.rows("SELECT payload FROM activity_batches WHERE id=? AND phase='outcome'",(batch,))[0]
        assert json.loads(row['payload'])['raw_sha256']
        assert store.get('account_binding')==identity
    finally:asyncio.run(broker.close())


def test_cancelled_acquisition_retains_partial_stream_and_propagates_cancellation(setup):
    store=setup[0];identity=store.get('account_binding')
    class Partial(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b': heartbeat\n\n'
            raise asyncio.CancelledError()
    def handler(request):
        if request.url.path=='/v2/account':return httpx.Response(200,json={'id':identity,'created_at':'2026-10-25T00:00:00Z'})
        return httpx.Response(200,headers={'content-type':'text/event-stream'},stream=Partial())
    broker=AlpacaPaper(Settings(api_key='fixture',secret_key='fixture'),store,httpx.MockTransport(handler))
    try:
        with pytest.raises(asyncio.CancelledError):asyncio.run(collect_batch(broker,store))
        row=store.rows("SELECT payload FROM activity_batches WHERE phase='outcome'")[0]
        receipt=json.loads(row['payload'])
        assert not receipt['complete'] and receipt['raw_hex']
        assert not store.rows('SELECT * FROM activity_projections')
    finally:asyncio.run(broker.close())


def test_two_reviewed_owner_books_receive_only_their_own_fee_effects(setup):
    store,_,reviewed=setup;mapping=deepcopy(reviewed)
    # The second round trip belongs to swing in this explicitly synthetic variant.
    clients=[r['client_id'] for r in store.rows('SELECT client_id FROM orders ORDER BY rowid')][-2:]
    for row in store.rows('SELECT client_id,request FROM orders'):
        if row['client_id'] in clients:
            request=json.loads(row['request']);request['intent']['strategy_id']='swing'
            store.db.execute('UPDATE orders SET request=? WHERE client_id=?',(json.dumps(request),row['client_id']))
    for event in setup[1]['events']:
        if event['activity_type']=='TRD' and event['details']['client_order_id'] in clients:
            mapping['trade_contracts'][event['ref_id']]['book']='swing'
    for entry in mapping['fee_associations']:
        if entry['client_id'] in clients:entry['book']='swing'
    result=pure(setup,mapping=mapping)
    assert not result['issues']
    assert all(float(q)==0 for q in result['net_books']['BTC'].values())
    by_owner={b:[e for e in result['effects'] if e['book']==b] for b in ('manual','swing')}
    assert len(by_owner['manual'])==4 and len(by_owner['swing'])==4
    assert all(e['client_id'] in clients for e in by_owner['swing'])


def test_selected_capture_file_must_match_the_mapping_source_role(tmp_path):
    from backend.activity_validation import verify_argument
    original=FIXTURE/'activity-sse.json';altered=tmp_path/'different.json';altered.write_text('{}')
    mapping=document('mapping.json')
    verify_argument(mapping,original,'activity-sse.json')
    with pytest.raises(ValueError):verify_argument(mapping,altered,'activity-sse.json')


def test_valid_bom_and_welcome_are_not_provider_error_notices():
    assert parse_sse(b'\xef\xbb\xbf: welcome to the Alpaca events\n\ndata: {}\n\n')==[{}]


def test_reviewed_execution_still_requires_verified_currency_and_valid_fill_values(setup):
    store=setup[0];snapshot=store.get('account_snapshot');snapshot['account']['currency']='EUR';store.put('account_snapshot',snapshot)
    assert 'account_currency_unverified' in pure(setup)['issues']
    snapshot['account']['currency']='USD';store.put('account_snapshot',snapshot)
    row=store.rows('SELECT id,payload FROM fills ORDER BY rowid LIMIT 1')[0]
    payload=json.loads(row['payload']);payload['value']='-1.00'
    store.db.execute('UPDATE fills SET payload=? WHERE id=?',(json.dumps(payload),row['id']))
    assert pure(setup)['issues']==['invalid_activity_evidence']


def test_absence_of_fee_records_is_never_zero_fee_evidence_even_if_balances_match(setup):
    store,original,reviewed=setup;capture,mapping=deepcopy(original),deepcopy(reviewed)
    fees=[e for e in capture['events'] if e['activity_type']=='CFEE']
    removed_refs={e['ref_id'] for e in fees};capture['events']=[e for e in capture['events'] if e['ref_id'] not in removed_refs]
    mapping['expected_events']={k:v for k,v in mapping['expected_events'].items() if k not in removed_refs}
    mapping['fee_associations']=[]
    # Gross retained quantity and provider cash agree, but fee coverage is unknown.
    snapshot=store.get('account_snapshot');snapshot['positions']=[{'symbol':'BTC/USD','qty':'0.000001555'}]
    store.put('account_snapshot',snapshot)
    result=pure(setup,capture,mapping)
    assert 'trade_fee_coverage_unverified' in result['issues']
    assert result['cash_reconciliation']['cash'] is None
