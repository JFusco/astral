"""Lossless mixed-ledger reads and fail-closed evidence decoding."""
import json
from pathlib import Path
import struct
import zlib

import pytest

from backend.evidence_codec import (MAGIC, NAMESPACE, MAX_BYTES, pack_bytes, pack_text,
                                    unpack_bytes, unpack_text, reference_bytes)
from backend.store import Store
from backend.activity_projection import digest
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
    first = import_capture(store, capture, raw, mapping, now=NOW)
    # An existing text projection remains valid beside new encoded evidence.
    store.db.execute('UPDATE activity_projections SET payload=? WHERE id=(SELECT id FROM activity_projections LIMIT 1)',
                     (json.dumps(first),))
    store.close()
    reopened = Store(path, 'alpaca')
    try:
        repeated = import_capture(reopened, capture, raw, mapping, now=NOW)
        assert all(acceptance(repeated, reopened)[0].values())
        batch = reopened.rows("SELECT payload FROM activity_batches WHERE phase='outcome' ORDER BY rowid DESC LIMIT 1")[0]
        assert bytes.fromhex(json.loads(batch['payload'])['raw_hex']) == raw
        frames = reopened.rows('SELECT frame FROM activity_events WHERE batch=? ORDER BY ordinal', (repeated['batch'],))
        from backend.activity_feed import parse_sse
        assert [event for row in frames for event in parse_sse(row['frame'])] == capture['events']
        accounting = source_snapshot(path, at(NOW))
        assert accounting['activity_projection']['cash_reconciliation']['cash'] == '99999.70'
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
