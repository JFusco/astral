"""Lossless mixed-ledger reads and fail-closed evidence decoding."""
import hashlib
import json
from pathlib import Path
import struct
import zlib

import pytest

from backend.evidence_codec import (MAGIC, NAMESPACE, REFERENCE, MAX_BYTES, pack_bytes, pack_text,
                                    unpack_bytes, unpack_text, reference_bytes)
from backend.store import Store
from backend.activity_projection import digest
from backend.activity_feed import (SSEParser, current_accounting, parse_sse, publish_projection,
                                   read_projection, retain_batch, start_batch)
from backend.activity_validation import import_ledger, import_capture, acceptance
from backend.accounting_engine import source_snapshot, at
from backend.liquidity_runner import readonly, snapshot
from backend.replay_runner import export_events

NOW = '2030-01-01T00:00:00+00:00'
FIXTURE = Path(__file__).parent/'fixtures/activity_feed/btc-sanitized-v1'


@pytest.mark.parametrize('raw', [b'', b'data: {}\n\n', NAMESPACE+b'raw rejected bytes',
                               ('data: '+json.dumps({'note': '€ 測試 '*1000})+'\n\n').encode()])
def test_retained_binary_evidence_returns_exact_original_bytes(raw):
    assert unpack_bytes(pack_bytes(raw)) == raw


@pytest.mark.parametrize('attack', ['version', 'truncated', 'checksum', 'trailing', 'length', 'oversize', 'expansion'])
def test_changed_or_unbounded_payload_is_rejected(attack):
    encoded = pack_text(json.dumps({'source': 'retained-source-'*500}))
    if attack == 'version': encoded = NAMESPACE+b'Z2\0'+encoded[len(MAGIC):]
    if attack == 'truncated': encoded = encoded[:-8]
    if attack == 'checksum': encoded = encoded[:-1]+bytes([encoded[-1]^1])
    if attack == 'trailing': encoded += b'unaccounted'
    if attack == 'length': encoded = MAGIC+struct.pack('>I', 1)+encoded[len(MAGIC)+4:]
    if attack == 'oversize': encoded = MAGIC+struct.pack('>I', MAX_BYTES+1)+encoded[len(MAGIC)+4:]
    if attack == 'expansion': encoded = MAGIC+struct.pack('>I', 16)+zlib.compress(b'a'*100000)
    with pytest.raises(ValueError): unpack_text(encoded)


@pytest.mark.parametrize('encoding', ['legacy', 'encoded'])
def test_reopened_market_evidence_is_identical_for_stream_liquidity_and_replay(tmp_path, encoding):
    path = tmp_path/'market.sqlite'
    store = Store(path, 'alpaca')
    book = {'t': NOW, 'b': [{'p': str(100-i/1000), 's': '1'} for i in range(200)],
            'a': [{'p': str(101+i/1000), 's': '2'} for i in range(200)]}
    quote = {'at': NOW, 'received_at': NOW, 'source': 'alpaca-us', 'bid': '100', 'ask': '101',
             'depth': {'raw_sha256': digest(book), 'unit_sources': ['retained provider evidence']*30}}
    quotes = {'BTC': quote}
    encode = pack_text if encoding == 'encoded' else lambda x:x
    store.db.execute('CREATE TABLE depth_snapshots(id TEXT PRIMARY KEY,at TEXT,symbol TEXT,payload TEXT)')
    store.db.execute('INSERT INTO depth_snapshots VALUES(?,?,?,?)', (digest(book), NOW, 'BTC', encode(json.dumps(book))))
    store.db.execute('INSERT INTO events(at,type,payload) VALUES(?,?,?)', (NOW, 'quotes', encode(json.dumps(quotes))))
    store.db.execute('CREATE TABLE experiment_observations(id TEXT,at TEXT,payload TEXT)')
    store.close()
    reopened = Store(path, 'alpaca')
    try:
        assert reopened.events_after(0)[0]['payload'] == quotes
        with readonly(path) as db:
            retained = snapshot(db)
        assert retained['quote'] == quote and retained['raw_book'] == book
        exported, coverage = export_events(path, starts_at=NOW, ends_at=NOW)
        assert not coverage['issues'] and coverage['quotes'] == 1
        assert exported[0]['quote'] == quote
    finally: reopened.close()


def test_mixed_accounting_rows_keep_raw_streams_and_exact_cash_after_restart(tmp_path, monkeypatch):
    monkeypatch.setattr('backend.inventory.utcnow', lambda:NOW)
    path = tmp_path/'accounting.sqlite'
    store = Store(path, 'alpaca')
    ledger = json.loads((FIXTURE/'ledger-selected-readonly.json').read_text())
    capture = json.loads((FIXTURE/'activity-sse.json').read_text())
    mapping = json.loads((FIXTURE/'mapping.json').read_text())
    raw = (FIXTURE/'activity-sse.raw').read_bytes()
    import_ledger(store, ledger)
    earlier = '2029-12-31T23:59:00+00:00'
    first = import_capture(store, capture, raw, mapping, now=earlier)
    # Recreate pre-codec activity bodies, frames and the cached projection.
    legacy = store.rows('SELECT ordinal,payload,frame FROM activity_events WHERE batch=? ORDER BY ordinal', (first['batch'],))
    for row in legacy:
        store.db.execute('UPDATE activity_events SET payload=?,frame=? WHERE batch=? AND ordinal=?',
                         (row['payload'], row['frame'], first['batch'], row['ordinal']))
    store.db.execute('UPDATE activity_projections SET payload=? WHERE id=(SELECT id FROM activity_projections LIMIT 1)',
                     (json.dumps(first),))
    outcome = store.rows("SELECT payload FROM activity_batches WHERE id=? AND phase='outcome'", (first['batch'],))[0]['payload']
    store.db.execute("UPDATE activity_batches SET payload=? WHERE id=? AND phase='outcome'", (outcome, first['batch']))
    assert store.rows('SELECT payload,frame FROM activity_events WHERE batch=? ORDER BY ordinal', (first['batch'],)) == [
        {'payload': row['payload'], 'frame': row['frame']} for row in legacy]
    old = source_snapshot(path, at(earlier))['activity_projection']
    assert old['batch'] == first['batch'] and not old['issues']
    assert old['cash_reconciliation']['cash'] == '99999.70'
    store.close()
    reopened = Store(path, 'alpaca')
    try:
        repeated = import_capture(reopened, capture, raw, mapping, now=NOW)
        assert all(acceptance(repeated, reopened)[0].values())
        batch = reopened.rows("SELECT payload FROM activity_batches WHERE phase='outcome' ORDER BY rowid DESC LIMIT 1")[0]
        assert bytes.fromhex(json.loads(batch['payload'])['raw_hex']) == raw
        frames = reopened.rows('SELECT frame FROM activity_events WHERE batch=? ORDER BY ordinal', (repeated['batch'],))
        assert [event for row in frames for event in parse_sse(row['frame'])] == capture['events']
        accounting = source_snapshot(path, at(NOW))
        assert accounting['activity_projection']['cash_reconciliation']['cash'] == '99999.70'
    finally: reopened.close()


@pytest.fixture
def retained_accounting(tmp_path, monkeypatch):
    """Synthetic current/reviewed conditions exercise the gate, not private acceptance."""
    monkeypatch.setattr('backend.activity_feed.utcnow', lambda: NOW)
    path = tmp_path/'retained.sqlite'
    store = Store(path, 'alpaca')
    capture = json.loads((FIXTURE/'activity-sse.json').read_text())
    mapping = json.loads((FIXTURE/'mapping.json').read_text())
    raw = (FIXTURE/'activity-sse.raw').read_bytes()
    import_ledger(store, json.loads((FIXTURE/'ledger-selected-readonly.json').read_text()))
    snapshot = store.get('account_snapshot');snapshot['at'] = NOW;store.put('account_snapshot', snapshot)
    capture['request']['params']['until'] = capture['request']['received_at'] = NOW
    mapping['kind'] = 'reviewed-provider'
    result = import_capture(store, capture, raw, mapping, now=NOW)
    try:
        assert not result['issues'] and len(result['effects']) == 8
        assert current_accounting(store, enabled=True, now=NOW)['accounting_by_symbol']['BTC']['passed']
        yield path, store, capture, raw, mapping, result
    finally: store.close()


@pytest.mark.parametrize('column', ['payload', 'frame'])
@pytest.mark.parametrize('attack', ['missing', 'changed'])
def test_corrupt_selected_acquisition_blocks_publication_and_cached_accounting(retained_accounting, column, attack):
    path, store, _, _, mapping, first = retained_accounting
    reference = store.db.execute('SELECT '+column+' FROM activity_events WHERE batch=? ORDER BY ordinal LIMIT 1',
                                 (first['batch'],)).fetchone()[0]
    assert reference.startswith(REFERENCE)
    key = reference[len(REFERENCE):]
    if attack == 'missing': store.db.execute('DELETE FROM evidence_blobs WHERE sha256=?', (key,))
    else: store.db.execute('UPDATE evidence_blobs SET payload=? WHERE sha256=?', (b'changed', key))
    with pytest.raises(ValueError, match='Referenced evidence'):
        publish_projection(store, first['batch'], mapping, now=NOW)
    for result in (read_projection(store, cutoff=NOW), source_snapshot(path, at(NOW))['activity_projection']):
        assert result['issues'] and not result['effects']
        assert result['cash_reconciliation']['cash'] is None
        assert not any(entry['passed'] for entry in result['by_symbol'].values())
    current = current_accounting(store, enabled=True, now=NOW)
    assert current['activity_coverage']['issues']
    assert not any(entry['passed'] for entry in current['accounting_by_symbol'].values())
    assert current['cash_reconciliation']['cash'] is None


@pytest.mark.parametrize('column', ['payload', 'frame'])
@pytest.mark.parametrize('attack', ['marker', 'other_reference'])
def test_damaged_or_misbound_reference_cannot_be_accepted_as_legacy_evidence(retained_accounting, column, attack):
    path, store, _, _, mapping, first = retained_accounting
    rows = store.db.execute('SELECT ordinal,'+column+' FROM activity_events WHERE batch=? ORDER BY ordinal LIMIT 2',
                            (first['batch'],)).fetchall()
    original = rows[0][1]
    changed = bytes([original[0]^0x80])+original[1:] if attack == 'marker' else rows[1][1]
    store.db.execute('UPDATE activity_events SET '+column+'=? WHERE batch=? AND ordinal=?',
                     (changed, first['batch'], rows[0][0]))
    for result in (read_projection(store, cutoff=NOW), source_snapshot(path, at(NOW))['activity_projection']):
        assert result['issues'] and not result['effects']
        assert result['cash_reconciliation']['cash'] is None
    current = current_accounting(store, enabled=True, now=NOW)
    assert not any(entry['passed'] for entry in current['accounting_by_symbol'].values())
    try: publication = publish_projection(store, first['batch'], mapping, now=NOW)
    except ValueError: pass
    else: assert publication['issues'] and not publication['effects']


@pytest.mark.parametrize('loss', ['one_delivery', 'whole_batch'])
def test_missing_selected_delivery_blocks_cached_accounting(retained_accounting, loss):
    path, store, _, _, _, first = retained_accounting
    query = 'DELETE FROM activity_events WHERE batch=?'
    if loss == 'one_delivery': query += ' AND ordinal=0'
    store.db.execute(query, (first['batch'],))
    for result in (read_projection(store, cutoff=NOW), source_snapshot(path, at(NOW))['activity_projection']):
        assert result['issues'] and not result['effects']
        assert result['cash_reconciliation']['cash'] is None
    current = current_accounting(store, enabled=True, now=NOW)
    assert not any(entry['passed'] for entry in current['accounting_by_symbol'].values())


@pytest.mark.parametrize('attack', ['outcome_checksum', 'missing_outcome', 'outcome_account', 'receipt_account',
                                  'incomplete_outcome', 'raw_checksum', 'duplicate_delivery', 'delivery_order',
                                  'delivery_account', 'delivery_identity', 'changed_frame'])
def test_selected_outcome_and_entire_delivery_sequence_are_required_for_accounting(retained_accounting, attack):
    path, store, capture, _, mapping, first = retained_accounting
    # Duplicate deliveries remain evidence, while their money is applied once.
    capture['events'] = [*capture['events'], capture['events'][0]]
    raw = b'\xef\xbb\xbf: heartbeat\r\n\r\n'+b''.join(
        ('data: '+json.dumps(event)+'\r\n\r\n').encode() for event in capture['events'])
    intact = import_capture(store, capture, raw, mapping, now=NOW)
    for result in (intact, read_projection(store, cutoff=NOW), source_snapshot(path, at(NOW))['activity_projection']):
        assert not result['issues'] and result['effects'] == first['effects']
        assert result['cash_reconciliation'] == first['cash_reconciliation']
    assert current_accounting(store, enabled=True, now=NOW)['accounting_by_symbol']['BTC']['passed']
    batch = intact['batch']
    if attack == 'outcome_checksum':
        encoded = store.db.execute("SELECT payload FROM activity_batches WHERE id=? AND phase='outcome'", (batch,)).fetchone()[0]
        assert encoded.startswith(MAGIC)
        changed = encoded[:-1]+bytes([encoded[-1]^1])
        store.db.execute("UPDATE activity_batches SET payload=? WHERE id=? AND phase='outcome'", (changed, batch))
    elif attack == 'missing_outcome':
        store.db.execute("DELETE FROM activity_batches WHERE id=? AND phase='outcome'", (batch,))
    elif attack == 'outcome_account':
        store.db.execute("UPDATE activity_batches SET account=? WHERE id=? AND phase='outcome'", ('another-account', batch))
    elif attack in ('receipt_account', 'incomplete_outcome', 'raw_checksum'):
        receipt = json.loads(store.rows("SELECT payload FROM activity_batches WHERE id=? AND phase='outcome'", (batch,))[0]['payload'])
        if attack == 'receipt_account': receipt['account_id'] = 'another-account'
        if attack == 'incomplete_outcome': receipt['complete'] = False
        if attack == 'raw_checksum': receipt['raw_hex'] = (raw+b': heartbeat\n\n').hex()
        store.db.execute("UPDATE activity_batches SET payload=? WHERE id=? AND phase='outcome'", (pack_text(json.dumps(receipt)), batch))
    elif attack == 'duplicate_delivery':
        store.db.execute('DELETE FROM activity_events WHERE batch=? AND ordinal=?', (batch, len(capture['events'])-1))
    elif attack == 'delivery_order':
        store.db.execute('UPDATE activity_events SET ordinal=-1 WHERE batch=? AND ordinal=0', (batch,))
        store.db.execute('UPDATE activity_events SET ordinal=0 WHERE batch=? AND ordinal=1', (batch,))
        store.db.execute('UPDATE activity_events SET ordinal=1 WHERE batch=? AND ordinal=-1', (batch,))
    elif attack == 'delivery_account':
        store.db.execute('UPDATE activity_events SET account=? WHERE batch=? AND ordinal=0', ('another-account', batch))
    elif attack == 'delivery_identity':
        store.db.execute('UPDATE activity_events SET event_id=? WHERE batch=? AND ordinal=0', ('another-delivery', batch))
    elif attack == 'changed_frame':
        frame = store.rows('SELECT frame FROM activity_events WHERE batch=? AND ordinal=0', (batch,))[0]['frame']
        store.db.execute('UPDATE activity_events SET frame=? WHERE batch=? AND ordinal=0', (pack_bytes(b'id: changed\n'+frame), batch))
    for result in (read_projection(store, cutoff=NOW), source_snapshot(path, at(NOW))['activity_projection']):
        assert result['issues'] and not result['effects']
        assert result['cash_reconciliation']['cash'] is None
        assert not any(entry['passed'] for entry in result['by_symbol'].values())
    current = current_accounting(store, enabled=True, now=NOW)
    assert current['activity_coverage']['issues']
    assert not any(entry['passed'] for entry in current['accounting_by_symbol'].values())
    assert current['cash_reconciliation']['cash'] is None
    try: publication = publish_projection(store, batch, mapping, now=NOW)
    except ValueError: pass
    else:
        assert publication['issues'] and not publication['effects']
        assert publication['cash_reconciliation']['cash'] is None


@pytest.mark.parametrize('attack', ['frame_reference', 'outcome_checksum', 'missing_outcome', 'raw_checksum', 'duplicate_delivery'])
def test_accounting_cutoff_excludes_corrupt_later_acquisition(retained_accounting, monkeypatch, attack):
    path, store, capture, _, mapping, first = retained_accounting
    later = '2030-01-01T00:01:00+00:00'
    monkeypatch.setattr('backend.activity_feed.utcnow', lambda: later)
    # A distinct later frame must not be decoded while reading the earlier batch.
    if attack == 'duplicate_delivery': capture['events'] = [*capture['events'], capture['events'][0]]
    raw = b''.join(('id: later\ndata: '+json.dumps(event)+'\n\n').encode() for event in capture['events'])
    second = import_capture(store, capture, raw, mapping, now=later)
    batch = second['batch']
    if attack == 'frame_reference':
        frame = store.db.execute('SELECT frame FROM activity_events WHERE batch=? LIMIT 1', (batch,)).fetchone()[0]
        store.db.execute('DELETE FROM evidence_blobs WHERE sha256=?', (frame[len(REFERENCE):],))
    elif attack == 'outcome_checksum':
        encoded = store.db.execute("SELECT payload FROM activity_batches WHERE id=? AND phase='outcome'", (batch,)).fetchone()[0]
        store.db.execute("UPDATE activity_batches SET payload=? WHERE id=? AND phase='outcome'",
                         (encoded[:-1]+bytes([encoded[-1]^1]), batch))
    elif attack == 'missing_outcome':
        store.db.execute("DELETE FROM activity_batches WHERE id=? AND phase='outcome'", (batch,))
    elif attack == 'raw_checksum':
        receipt = json.loads(store.rows("SELECT payload FROM activity_batches WHERE id=? AND phase='outcome'", (batch,))[0]['payload'])
        receipt['raw_hex'] = (raw+b': heartbeat\n\n').hex()
        store.db.execute("UPDATE activity_batches SET payload=? WHERE id=? AND phase='outcome'", (pack_text(json.dumps(receipt)), batch))
    else:
        store.db.execute('DELETE FROM activity_events WHERE batch=? AND ordinal=?', (batch, len(capture['events'])-1))
    for result in (read_projection(store, cutoff=NOW), source_snapshot(path, at(NOW))['activity_projection']):
        assert result['batch'] == first['batch'] and not result['issues']
        assert len(result['effects']) == 8 and result['cash_reconciliation']['cash'] == '99999.70'
    assert read_projection(store, cutoff=later)['issues']


@pytest.mark.parametrize('column', ['payload', 'frame'])
@pytest.mark.parametrize('prior_error', [None, 'activity_acquisition_cancelled'])
def test_shared_blob_corruption_retains_rejected_deliveries_and_raw_stream_after_restart(retained_accounting, column, prior_error):
    path, store, capture, raw, mapping, first = retained_accounting
    reference = store.db.execute('SELECT '+column+' FROM activity_events WHERE batch=? ORDER BY ordinal LIMIT 1',
                                 (first['batch'],)).fetchone()[0]
    key = reference[len(REFERENCE):]
    store.db.execute('UPDATE evidence_blobs SET payload=? WHERE sha256=?', (b'changed', key))
    binding = store.get('account_binding')
    batch = start_batch(store, binding, capture['request']['params']['since'], NOW)
    result = {'complete': prior_error is None, 'error': prior_error, 'account_id': binding, 'events': capture['events'], 'raw': raw,
              'received_at': NOW, 'historical_import': True, **capture['request']['params']}
    retain_batch(store, batch, binding, result)
    assert result['complete'] is False and result['error']
    store.close()
    reopened = Store(path, 'alpaca')
    try:
        rows = reopened.rows('SELECT * FROM activity_events WHERE batch=? ORDER BY ordinal', (batch,))
        parser = SSEParser();parser.feed(raw, final=True)
        assert [row['ordinal'] for row in rows] == list(range(len(capture['events'])))
        assert [json.loads(row['payload']) for row in rows] == capture['events']
        assert [row['frame'] for row in rows] == [frame for _, frame in parser.frames]
        assert all(row['account'] == binding and row['at'] == NOW for row in rows)
        assert [row['sha256'] for row in rows] == [digest(event) for event in capture['events']]
        receipt = json.loads(reopened.rows("SELECT payload FROM activity_batches WHERE id=? AND phase='outcome'", (batch,))[0]['payload'])
        assert receipt['complete'] is False and receipt['error'] == (prior_error or 'activity_evidence_integrity_error')
        assert receipt['evidence_integrity_error'] is True
        assert bytes.fromhex(receipt['raw_hex']) == raw
        assert receipt['raw_sha256'] == hashlib.sha256(raw).hexdigest()
        assert reopened.db.execute('SELECT payload FROM evidence_blobs WHERE sha256=?', (key,)).fetchone()[0] == b'changed'
        assert not current_accounting(reopened, enabled=True, now=NOW)['accounting_by_symbol']['BTC']['passed']
        try: publication = publish_projection(reopened, batch, mapping, now=NOW)
        except ValueError: pass  # Corrupt prior payloads also veto a new publication.
        else:
            assert publication['issues'] and not publication['effects']
            assert publication['cash_reconciliation']['cash'] is None
    finally: reopened.close()


def test_corrupt_quote_cannot_become_replay_or_liquidity_evidence(tmp_path):
    path = tmp_path/'corrupt.sqlite'
    store = Store(path, 'alpaca')
    store.db.execute('INSERT INTO events(at,type,payload) VALUES(?,?,?)', (NOW, 'quotes', NAMESPACE+b'unsupported'))
    store.db.execute('CREATE TABLE experiment_observations(id TEXT,at TEXT,payload TEXT)')
    try:
        exported, coverage = export_events(path, starts_at=NOW, ends_at=NOW)
        assert not exported and coverage['issues']
        with readonly(path) as db, pytest.raises(ValueError): snapshot(db)
        with pytest.raises(ValueError): store.events_after(0)
    finally: store.close()


@pytest.mark.parametrize('attack', ['missing', 'changed'])
def test_deduplicated_evidence_requires_its_original_content(tmp_path, attack):
    store = Store(tmp_path/'source.sqlite', 'alpaca')
    try:
        raw = b'data: {"retained":"provider-original"}\n\n'
        first = reference_bytes(store.db, raw)
        assert reference_bytes(store.db, raw) == first
        assert store.db.execute('SELECT count(*) FROM evidence_blobs').fetchone()[0] == 1
        if attack == 'missing': store.db.execute('DELETE FROM evidence_blobs')
        else: store.db.execute('UPDATE evidence_blobs SET payload=?', (b'different',))
        with pytest.raises(ValueError): unpack_bytes(first, store.db)
    finally: store.close()


@pytest.mark.parametrize('encoding', ['legacy', 'encoded'])
def test_offline_learning_reads_admitted_packets_without_parsing_future_rows(tmp_path, encoding):
    from backend.learning_engine import snapshot as learning_snapshot
    store = Store(tmp_path/'learning.sqlite', 'alpaca')
    packets = json.dumps([{'symbol': 'BTC', 'vetoes': ['retained provider evidence']*100}])
    stored = pack_text(packets) if encoding == 'encoded' else packets
    store.db.execute('INSERT INTO research(at,packet,result,usage) VALUES(?,?,?,?)', (NOW, stored, '{}', '{}'))
    store.db.execute('INSERT INTO research(at,packet,result,usage) VALUES(?,?,?,?)',
                     ('2030-01-02T00:00:00+00:00', NAMESPACE+b'unsupported', '{}', '{}'))
    try:
        selected = learning_snapshot(tmp_path/'learning.sqlite', NOW, [])
        assert selected['records']['research'][0]['packet'] == packets
        assert len(selected['records']['research']) == 1
        assert selected['metadata']['research']['after_cutoff'] == 1
    finally: store.close()
