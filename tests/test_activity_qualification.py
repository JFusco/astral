"""New consumer boundaries: synthetic evidence only, never an account fixture."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

import httpx
import pytest

from backend import activity_qualification as q
from backend.config import Settings


def at(second):
    return f'2026-01-01T00:00:{second:02d}+00:00'


def encode(value):
    return json.dumps(value, separators=(',', ':')).encode()


def write(path, value):
    path.write_bytes(value if isinstance(value, bytes) else encode(value))
    path.chmod(0o600)
    return str(path)


def synthetic():
    account = {'id': '00000000-0000-4000-8000-000000000001', 'currency': 'USD', 'created_at': at(0), 'cash': '989'}
    def snapshot(t, qty, cash='989'):
        return {'at': at(t), 'account': {**account, 'cash': cash}, 'positions': [{'symbol': 'BTCUSD', 'qty': qty}], 'clock': {}}
    orders, fills = [], []
    for cid, side, qty, submitted, execution, known, value in [('buy', 'buy', '1', 1, 3, 4, '100'), ('sell', 'sell', '0.9', 10, 11, 12, '90')]:
        raw = {'id': 'o-'+cid, 'client_order_id': cid, 'symbol': 'BTC/USD', 'side': side,
               'status': 'filled', 'submitted_at': at(submitted), 'filled_at': at(execution),
               'filled_qty': qty, 'filled_avg_price': '100'}
        orders.append({'client_id': cid, 'request': json.dumps({'intent': {'strategy_id': 'manual'}}), 'raw': json.dumps(raw),
                       'status': 'filled', 'external': 0, 'deadline': 0.0, 'created_at': at(submitted), 'updated_at': at(known)})
        f = {'client_id': cid, 'source': 'alpaca-cumulative-order-readback', 'symbol': 'BTC/USD', 'side': side,
             'at': at(execution), 'quantity': qty, 'price': '100', 'value': value}
        fills.append({'id': 'fill-'+cid, 'client_id': cid, 'at': at(known), 'payload': json.dumps(f)})
    points = [{'seq': 1, 'at': at(0), 'type': 'custody_snapshot', 'payload': json.dumps({'snapshot': snapshot(0, '0', '0'), 'working_orders': []})},
              {'seq': 2, 'at': at(5), 'type': 'custody_snapshot', 'payload': json.dumps({'snapshot': snapshot(5, '0.9', '900'), 'working_orders': []})}]
    ledger = {'schema': 'g3-v2-selected-ledger', 'version': 1, 'capture_id': 'synthetic-case', 'account': account['id'],
              'ledger_id': 'synthetic-ledger', 'captured_at': at(20), 'selection': {k: list(v) for k, v in q.TABLES.items()}, 'producer_refs': [],
              'state': {'mode': 'alpaca', 'account_binding': account['id'], 'account_snapshot': snapshot(15, '0'),
                        'custody_checkpoint': {'seqs': [1, 2]}},
              'optional_state': {k: k == 'custody_checkpoint' for k in q.OPTIONAL_STATE},
              'rows': {'orders': orders, 'fills': fills, 'activities': [], 'observations': [], 'events': points}}
    def event(ref, kind, t, qty, net, currency='USD', details=None, price='0'):
        return {'ref_id': ref, 'event_id': 'event-'+ref, 'account_id': account['id'], 'activity_type': kind,
                'at': at(t), 'executed_at': at(t), 'status': 'executed', 'qty': qty, 'price': price,
                'net_amount': net, 'currency': currency, 'details': details or {}}
    events = [event('fund', 'JNLC', 0, '0', '1000'),
              event('buy', 'TRD', 3, '1', '-100', details={'order_id': 'o-buy', 'client_order_id': 'buy', 'symbol': 'BTC/USD', 'side': 'buy'}, price='100'),
              event('asset-fee', 'CFEE', 3, '-0.1', '0', 'BTC', {'order_id': 'o-buy', 'parent_id': 'buy'}),
              event('sell', 'TRD', 11, '0.9', '89', details={'order_id': 'o-sell', 'client_order_id': 'sell', 'symbol': 'BTC/USD', 'side': 'sell'}, price='100'),
              event('usd-fee', 'FEE', 11, '0', '-1', details={'order_id': 'o-sell', 'parent_id': 'sell'})]
    mapping = {'version': 1, 'kind': 'reviewed-provider', 'account_id': account['id'], 'known_at': at(25), 'source_files': {},
               'expected_events': {e['ref_id']: q.digest(e) for e in events},
               'trade_contracts': {e['ref_id']: {'sha256': q.digest(e), 'symbol': 'BTC', 'book': 'manual', 'currency': 'USD', 'cash_treatment': 'provider-net'} for e in events if e['activity_type'] == 'TRD'},
               'journal_contracts': {'fund': {'sha256': q.digest(events[0]), 'currency': 'USD'}}, 'fee_associations': []}
    for fee, trade, treatment in [(events[2], events[1], 'asset-debit'), (events[4], events[3], 'included-usd')]:
        mapping['fee_associations'].append({'id': 'association-'+fee['ref_id'], 'fee_ref_id': fee['ref_id'], 'fee_sha256': q.digest(fee),
                                          'trade_ref_id': trade['ref_id'], 'trade_sha256': q.digest(trade), 'order_id': trade['details']['order_id'],
                                          'client_id': trade['details']['client_order_id'], 'symbol': 'BTC', 'book': 'manual', 'treatment': treatment})
    economics = {}
    for e in events:
        ref = e['ref_id']; is_trade = e['activity_type'] == 'TRD'; journal = ref == 'fund'
        cid = None if journal else 'buy' if ref in ('buy', 'asset-fee') else 'sell'
        economics[ref] = {k: e[k] for k in ('qty', 'price', 'net_amount', 'currency')}
        economics[ref].update(symbol=None if journal else 'BTC', book=None if journal else 'manual',
                             client_id=cid, order_id=None if journal else 'o-'+cid,
                             treatment='journal' if journal else 'provider-net' if is_trade else 'asset-debit' if ref == 'asset-fee' else 'included-usd',
                             gross_value=('100' if ref == 'buy' else '90') if is_trade else None,
                             denomination='BTC' if ref == 'asset-fee' else 'USD', evidence_refs=[],
                             equation_evidence={k: {'exactness_evidenced': True, 'evidence_refs': []} for k in ('gross_from_qty_price', 'net_from_gross_and_included_fees')} if is_trade else None)
    custody = [{'client_id': 'buy', 'order_id': 'o-buy', 'symbol': 'BTC', 'book': 'manual', 'quantity': '0.1',
                'linked_confirmed_fee_quantity': '0.1', 'additional_debit_quantity': '0', 'classification': 'confirmed-fee',
                'checkpoints': [{'before': 'checkpoint:1', 'after': 'checkpoint:2', 'before_at': at(0), 'after_at': at(5),
                                 'before_quantity': '0', 'gross_buy_quantity': '1', 'after_quantity': '0.9', 'reduction_quantity': '0.1'}]}]
    return ledger, events, mapping, economics, custody


class Case:
    def __init__(self, root):
        self.root = root.resolve(); self.root.chmod(0o700)
        self.inputs = self.root/'inputs'; self.inputs.mkdir(mode=0o700)
        self.requests = self.root/'requests'; self.requests.mkdir(mode=0o700)
        self.ledger, self.events, self.mapping, self.economics, self.custody = synthetic()
        self.source = q.source_identity()
        self.serial = 0
        self.mutate_expected = lambda e: None

    def prepare(self, operation='replay', receipt=None):
        self.serial += 1
        support = write(self.inputs/'interpretation.json', {'synthetic': True, 'basis': 'Independent exact fixture equations; no operational claim.'})
        self.ledger['producer_refs'] = [support]
        raw = b''.join(b'data: '+encode(e)+b'\n\n' for e in self.events)
        cap = {'schema': 'g3-v2-activity-capture', 'version': 1, 'capture_id': 'synthetic-case', 'account': self.ledger['account'],
               'request': {'method': 'GET', 'host': q.PAPER_URL, 'path': q.ROUTES[5], 'status': 200,
                           'params': {'since': at(0), 'until': at(16)}, 'received_at': at(18)},
               'content_type': 'text/event-stream', 'stream_closed': True, 'parse_errors': [], 'limit_or_error': None,
               'termination': 'normal-finite', 'raw_sha256': q.sha(raw), 'raw_bytes': len(raw), 'decoding_layer': 'HTTP content-decoded body',
               'sent_at': at(16), 'ended_at': at(17), 'delivered_count': len(self.events), 'distinct_count': len({e['ref_id'] for e in self.events}),
               'observation_refs': [support], 'producer_refs': [support], 'events': self.events}
        paths = {'ledger': write(self.inputs/'ledger-selected-readonly.json', self.ledger), 'capture': write(self.inputs/'activity-sse.json', cap),
                 'raw': write(self.inputs/'activity-sse.raw', raw), 'support': support}
        def entry(role, path):
            b = Path(path).read_bytes()
            return {'role': role, 'path': path, 'sha256': q.sha(b), 'bytes': len(b)}
        self.mapping['source_files'] = {p: q.sha(Path(p).read_bytes()) for p in paths.values()}
        self.mapping['expected_events'] = {e['ref_id']: q.digest(e) for e in self.events}
        for e in self.events:
            if e['ref_id'] in self.mapping['trade_contracts']:
                self.mapping['trade_contracts'][e['ref_id']]['sha256'] = q.digest(e)
        for a in self.mapping['fee_associations']:
            a['fee_sha256'] = self.mapping['expected_events'][a['fee_ref_id']]
            a['trade_sha256'] = self.mapping['expected_events'][a['trade_ref_id']]
        paths['mapping'] = write(self.inputs/'mapping.json', self.mapping)
        economics = deepcopy(self.economics)
        for item in economics.values():
            item['evidence_refs'] = [support]
            for eq in (item['equation_evidence'] or {}).values():
                eq['evidence_refs'] = [support]
        exp = {'schema': 'g3-v2-reviewed-expectations', 'version': 1, 'account': self.ledger['account'], 'environment': 'paper',
               'amendment_sha256': 'a'*64, 'capture_id': 'synthetic-case', 'inputs': [entry(r, p) for r, p in paths.items() if r != 'mapping'],
               'mapping_sha256': q.sha(Path(paths['mapping']).read_bytes()), 'mapping_digest': q.digest(self.mapping), 'source': self.source,
               'evaluator': {'identity': 'Synthetic evaluator', 'method': 'Hand-calculated test schedule', 'sealed_at': at(28),
                             'derivation_refs': [support], 'limitations': ['Synthetic only'], 'independent': True},
               'history': {'since': at(0), 'until': at(16), 'balance_at': at(15), 'knowledge_cutoff': at(30),
                           'created_at': at(0), 'zero_origin': True, 'evidence_refs': [support]},
               'deliveries': [{'event_id': e['event_id'], 'ref_id': e['ref_id'], 'sha256': q.digest(e)} for e in self.events],
               'movements': {e['ref_id']: {'type': e['activity_type'], 'sha256': q.digest(e), 'at': e['at'], 'executed_at': e['executed_at']} for e in self.events},
               'orders': {r['client_id']: q.order_description(r) for r in self.ledger['rows']['orders']}, 'fills': {},
               'economics': economics, 'custody': self.custody,
               'coverage': {'included_usd': ['usd-fee'], 'asset_debit': ['asset-fee'], 'no_second_debit': [support]},
               'closing': {'cash': '989', 'included_fee_usd': '1', 'gross_books': {'BTC': {'manual': '0.1'}},
                           'net_books': {'BTC': {'manual': '0'}}, 'positions': {'BTC': '0'}}}
        for row in self.ledger['rows']['fills']:
            f = json.loads(row['payload'])
            exp['fills'][row['id']] = {k: f[k] for k in ('client_id', 'source', 'at', 'quantity', 'price', 'value')}
            exp['fills'][row['id']].update(row_sha256=q.digest(row), known_at=row['at'], trade_refs=[f['client_id']], evidence_refs=[support])
        self.mutate_expected(exp)
        paths['expectations'] = write(self.inputs/'expectations.json', exp)
        if receipt:
            # Accepted receipts are copied to an input location, preserving bytes.
            paths['replay_receipt'] = write(self.inputs/'accepted-replay.json', Path(receipt).read_bytes())
        output = self.root/f'output-{self.serial}'
        request_path = str(self.requests/f'request-{self.serial}.json')
        args = [operation, '--request-file', request_path, '--request-sha256', '0'*64,
                '--expectations-file', paths['expectations'], '--mapping-file', paths['mapping'], '--ledger-capture', paths['ledger'],
                '--activity-capture', paths['capture'], '--raw-stream', paths['raw'], '--database', str(output/'database.sqlite'), '--output-dir', str(output)]
        receipt_binding = None
        if receipt:
            receipt_binding = {'path': paths['replay_receipt'], 'sha256': q.sha(Path(paths['replay_receipt']).read_bytes())}
            args += ['--replay-receipt', receipt_binding['path'], '--replay-receipt-sha256', receipt_binding['sha256']]
        now = datetime.now(timezone.utc)
        request = {'schema': 'g3-v2-operation-request', 'version': 1, 'operation': operation, 'attempt': f'synthetic-{self.serial}', 'account': self.ledger['account'],
                   'invocation': {'executable': sys.executable, 'module': 'backend.activity_qualification', 'arguments': q.invocation_arguments(args)},
                   'inputs': [entry(r, p) for r, p in paths.items()], 'source': self.source, 'environment': q.environment(),
                   'destinations': {'database': str(output/'database.sqlite'), 'output_dir': str(output)}, 'controls': {k: False for k in q.CONTROLS},
                   'limits': {'input_bytes': 4*q.DATA_BYTES, 'response_bytes': q.RAW_BYTES, 'total_response_bytes': q.DATA_BYTES, 'whole_seconds': 60},
                   'start_window': {'not_before': (now-timedelta(minutes=1)).isoformat(), 'before': (now+timedelta(minutes=5)).isoformat()},
                   'supervision': {'request_sha256': 'b'*64, 'method_sha256': 'c'*64, 'stop_procedure': 'Owned synthetic test caller', 'qualified': True},
                   'attestation': {'operator': 'Synthetic operator', 'approved_at': now.isoformat(), 'accepted': True},
                   'replay_receipt': receipt_binding,
                   'compare': {'method': 'GET', 'host': q.PAPER_URL, 'routes': q.ROUTES, 'max_gets': 11, 'credential_mechanism': 'Settings.from_env'} if receipt else None}
        write(Path(request_path), request)
        args[args.index('--request-sha256')+1] = q.sha(Path(request_path).read_bytes())
        return args


@pytest.fixture
def case(tmp_path):
    return Case(tmp_path)


def assert_outcome(out, status, reason=None):
    assert out['status'] == status, out
    assert out['exit_code'] == q.EXIT[status]
    if reason:
        assert out['primary_failure']['reason'] == reason, out


def test_complete_evidence_replays_and_reopens_without_second_effect(case, monkeypatch):
    monkeypatch.setattr(Settings, 'from_env', lambda: pytest.fail('Offline must not load credentials'))
    args = case.prepare()
    before = {p: p.read_bytes() for p in case.inputs.iterdir()}
    out = q.run(args)
    assert_outcome(out, 'PASS')
    receipt = json.loads(Path(out['receipt']).read_bytes())
    assert receipt['checks'] == dict.fromkeys(q.CHECKS, 'PASS')
    assert receipt['result']['independent']['cash'] == '989'
    assert receipt['result']['custody']['reductions'][0]['additional_debit_quantity'] == '0.0'
    assert all(p.read_bytes() == b for p, b in before.items())
    assert receipt['cutoff'] == at(30)


@pytest.mark.parametrize('supported,residual,status', [(True, True, 'FAIL'), (False, True, 'INCOMPLETE'), (False, False, 'INCOMPLETE')])
def test_exactness_evidence_determines_equation_verdict(case, supported, residual, status):
    if residual:
        # Opposing differences leave closing cash unchanged.
        case.events[1]['net_amount'] = '-99'
        case.events[3]['net_amount'] = '88'
        case.economics['buy']['net_amount'] = '-99'
        case.economics['sell']['net_amount'] = '88'
    for item in case.economics.values():
        for eq in (item['equation_evidence'] or {}).values():
            eq['exactness_evidenced'] = supported
    assert_outcome(q.run(case.prepare()), status, 'execution_equation_mismatch' if supported else 'unsupported_rounding_semantics')


def test_supported_failure_survives_an_unsupported_relation(case):
    case.economics['buy']['gross_value'] = '101'
    case.economics['sell']['equation_evidence']['gross_from_qty_price']['exactness_evidenced'] = False
    assert_outcome(q.run(case.prepare()), 'FAIL', 'execution_equation_mismatch')


@pytest.mark.parametrize('change,reason', [
    (lambda e: e['history'].update(zero_origin=False), 'unsupported_opening'),
    (lambda e: e['coverage'].update(included_usd=[]), 'missing_real_fee_coverage'),
    (lambda e: e['custody'].clear(), 'missing_expected_custody'),
    (lambda e: e['economics']['buy']['evidence_refs'].append('/unapproved/evidence'), 'unapproved_reference'),
])
def test_missing_or_unapproved_evidence_cannot_qualify(case, change, reason):
    case.mutate_expected = change
    out = q.run(case.prepare())
    assert out['status'] != 'PASS'
    assert out['primary_failure']['reason'] == reason


def test_checkpoint_reference_closure_and_column_order(case):
    for rows in case.ledger['rows'].values():
        for i, row in enumerate(rows):
            rows[i] = dict(reversed(list(row.items())))
    assert_outcome(q.run(case.prepare()), 'PASS')
    case.ledger['rows']['events'].pop()
    assert_outcome(q.run(case.prepare()), 'INCOMPLETE', 'checkpoint_reference_closure')


def test_duplicate_checkpoint_sequences_are_rejected(case):
    case.ledger['state']['custody_checkpoint']['seqs'] = [1, 1]
    assert_outcome(q.run(case.prepare()), 'REJECTED', 'checkpoint_sequences')


def test_timestamp_truncation_cannot_change_presubmission_decision(case):
    row = case.ledger['rows']['orders'][0]
    raw = json.loads(row['raw']); raw['submitted_at'] = '2026-01-01T00:00:00.000000001+00:00'
    row['raw'] = json.dumps(raw)
    assert_outcome(q.run(case.prepare()), 'INCOMPLETE', 'unsupported_timestamp_precision')


@pytest.mark.parametrize('value', ['NaN', True, 1, ' 1', '0.'+'1'*51, '1e101'])
def test_noncontract_decimal_never_qualifies(case, value):
    case.economics['buy']['gross_value'] = value
    assert q.run(case.prepare())['status'] != 'PASS'


def test_existing_output_and_tampered_input_denied(case):
    args = case.prepare()
    Path(args[args.index('--output-dir')+1]).mkdir()
    assert_outcome(q.run(args), 'REJECTED', 'new_destination_required')
    args = case.prepare()
    with (case.inputs/'activity-sse.raw').open('ab') as f:
        f.write(b' ')
    assert q.run(args)['status'] != 'PASS'


def handler_for(case, calls, change=None):
    def handler(request):
        calls.append((request.method, request.url.path))
        if change:
            override = change(request, len(calls))
            if override:
                return override
        if request.url.path == '/v2/account':
            return httpx.Response(200, json=case.ledger['state']['account_snapshot']['account'])
        if request.url.path == '/v2/positions':
            return httpx.Response(200, json=case.ledger['state']['account_snapshot']['positions'])
        if request.url.path == '/v2/clock':
            return httpx.Response(200, json={})
        if request.url.path == '/v2/orders':
            return httpx.Response(200, json=[json.loads(r['raw']) for r in case.ledger['rows']['orders']])
        return httpx.Response(200, headers={'content-type': 'text/event-stream'}, content=(case.inputs/'activity-sse.raw').read_bytes())
    return handler


def test_comparison_has_eleven_gets_after_full_offline_replay(case):
    first = q.run(case.prepare()); assert_outcome(first, 'PASS')
    args = case.prepare('compare', first['receipt'])
    calls = []
    out = q.run(args, settings_loader=lambda: Settings(api_key='synthetic', secret_key='synthetic'),
                transport=httpx.MockTransport(handler_for(case, calls)))
    assert_outcome(out, 'PASS')
    assert calls == [('GET', route) for route in q.ROUTES]
    receipt = json.loads(Path(out['receipt']).read_bytes())
    assert len(receipt['transport']) == 11
    assert all(r['complete'] for r in receipt['transport'])


def test_failed_offline_phase_never_loads_credentials_or_calls_transport(case):
    first = q.run(case.prepare()); assert_outcome(first, 'PASS')
    case.mutate_expected = lambda e: e['closing'].update(cash='988')
    calls = []
    out = q.run(case.prepare('compare', first['receipt']), settings_loader=lambda: pytest.fail('credentials before valid offline replay'),
                transport=httpx.MockTransport(handler_for(case, calls)))
    assert out['status'] != 'PASS' and calls == []


@pytest.mark.parametrize('attack', ['orders-cap', 'cash', 'new-history', 'redirect'])
def test_current_evidence_failures_stop_comparison(case, attack):
    first = q.run(case.prepare()); assert_outcome(first, 'PASS')
    def change(request, count):
        if attack == 'orders-cap' and count == 4:
            return httpx.Response(200, json=[{}]*500)
        if attack == 'cash' and count == 1:
            return httpx.Response(200, json={**case.ledger['state']['account_snapshot']['account'], 'cash': '988'})
        if attack == 'redirect' and count == 1:
            return httpx.Response(302, headers={'location': 'https://example.com/'})
        if attack == 'new-history' and count == 6:
            e = deepcopy(case.events[0]); e.update(ref_id='new', event_id='new')
            return httpx.Response(200, headers={'content-type': 'text/event-stream'}, content=(case.inputs/'activity-sse.raw').read_bytes()+b'data: '+encode(e)+b'\n\n')
    calls = []
    out = q.run(case.prepare('compare', first['receipt']), settings_loader=lambda: Settings(api_key='synthetic', secret_key='synthetic'),
                transport=httpx.MockTransport(handler_for(case, calls, change)))
    assert out['status'] != 'PASS'
    assert len(calls) <= 8 and all(m == 'GET' for m, _ in calls)


def test_cli_argument_failure_emits_one_machine_readable_outcome():
    proc = subprocess.run([sys.executable, '-m', 'backend.activity_qualification', 'replay'], capture_output=True, text=True)
    assert proc.returncode == 2
    assert json.loads(proc.stdout)['primary_failure']['reason'] == 'arguments'
    assert proc.stderr == ''


def test_receipt_storage_failure_preserves_established_mismatch(case, monkeypatch):
    case.economics['buy']['gross_value'] = '101'
    original = q.exclusive
    def fail_receipt(path, raw):
        if path.name == 'receipt.json':
            raise OSError('synthetic write failure')
        original(path, raw)
    monkeypatch.setattr(q, 'exclusive', fail_receipt)
    out = q.run(case.prepare())
    assert_outcome(out, 'FAIL', 'execution_equation_mismatch')
    assert out['receipt'] is None
    assert out['secondary_failures'][0]['reason'] == 'unexpected_failure'


@pytest.mark.parametrize('link', ['symbolic', 'hard'])
def test_linked_inputs_are_denied_before_store_creation(case, link):
    args = case.prepare()
    path = case.inputs/'activity-sse.raw'
    saved = case.inputs/'unapproved.raw'
    path.rename(saved)
    if link == 'symbolic':
        path.symlink_to(saved)
    else:
        os.link(saved, path)
    out = q.run(args)
    assert out['status'] != 'PASS'
    assert not Path(args[args.index('--database')+1]).exists()


def test_ambiguous_custody_and_missing_window_do_not_pass(case):
    # A late checkpoint cannot cover the complete buy interval.
    point = json.loads(case.ledger['rows']['events'][0]['payload'])
    point['working_orders'] = ['buy']
    case.ledger['rows']['events'][0]['payload'] = json.dumps(point)
    assert_outcome(q.run(case.prepare()), 'FAIL', 'custody_membership')


def test_host_clock_cannot_change_historical_inventory(case, monkeypatch):
    monkeypatch.setattr('backend.inventory.utcnow', lambda: '2099-01-01T00:00:00+00:00')
    assert_outcome(q.run(case.prepare()), 'PASS')


def test_evidence_known_after_cutoff_is_incomplete(case):
    case.ledger['rows']['fills'][0]['at'] = at(31)
    assert_outcome(q.run(case.prepare()), 'INCOMPLETE', 'post_cutoff_evidence')


def test_inexact_multiplication_cannot_round_into_a_pass(case):
    for e in case.events:
        if e['ref_id'] == 'buy':
            e.update(qty='1.'+'1'*48, price='1.'+'1'*48)
    case.economics['buy'].update(qty='1.'+'1'*48, price='1.'+'1'*48)
    assert_outcome(q.run(case.prepare()), 'INCOMPLETE', 'unsupported_arithmetic')


def test_omitted_receipt_check_blocks_all_credential_and_network_work(case):
    first = q.run(case.prepare()); assert_outcome(first, 'PASS')
    prior = Path(first['receipt']); doc = json.loads(prior.read_bytes())
    del doc['checks']['custody']; write(prior, doc)
    out = q.run(case.prepare('compare', str(prior)), settings_loader=lambda: pytest.fail('credential loading'))
    assert_outcome(out, 'REJECTED', 'accepted_replay_not_pass')


def test_response_retention_failure_prevents_another_dispatch(case, monkeypatch):
    first = q.run(case.prepare()); assert_outcome(first, 'PASS')
    original = q.os.open
    def storage_failure(path, flags, *args, **kwargs):
        if str(path).endswith('response-01.raw'):
            raise OSError('synthetic storage error')
        return original(path, flags, *args, **kwargs)
    monkeypatch.setattr(q.os, 'open', storage_failure)
    calls = []
    out = q.run(case.prepare('compare', first['receipt']), settings_loader=lambda: Settings(api_key='synthetic', secret_key='synthetic'),
                transport=httpx.MockTransport(handler_for(case, calls)))
    assert out['status'] != 'PASS'
    assert calls == [('GET', '/v2/account')]


def test_enabled_order_control_is_rejected_without_dispatch(case):
    first = q.run(case.prepare()); assert_outcome(first, 'PASS')
    calls = []
    out = q.run(case.prepare('compare', first['receipt']),
                settings_loader=lambda: Settings(api_key='synthetic', secret_key='synthetic', enable_orders=True),
                transport=httpx.MockTransport(handler_for(case, calls)))
    assert_outcome(out, 'REJECTED', 'effective_controls')
    assert calls == []


def test_final_clock_failure_does_not_replace_equation_failure(case, monkeypatch):
    case.economics['buy']['gross_value'] = '101'
    original = q.clocks
    count = 0
    def clock():
        nonlocal count
        count += 1
        if count == 2:
            raise OSError('synthetic clock failure')
        return original()
    monkeypatch.setattr(q, 'clocks', clock)
    out = q.run(case.prepare())
    assert_outcome(out, 'FAIL', 'execution_equation_mismatch')
    assert out['secondary_failures'][0]['reason'] == 'unexpected_failure'


def test_exact_checkpoint_values_allow_equivalent_serialization(case):
    checkpoint = case.custody[0]['checkpoints'][0]
    checkpoint['before_at'] = checkpoint['before_at'].replace('+00:00', 'Z')
    checkpoint['reduction_quantity'] = '0.10'
    assert_outcome(q.run(case.prepare()), 'PASS')


def test_reopen_failure_after_accepted_receipt_still_prevents_credentials(case, monkeypatch):
    from backend import activity_validation
    first = q.run(case.prepare()); assert_outcome(first, 'PASS')
    original = activity_validation.import_capture
    count = 0
    def fail_reopen(*args, **kwargs):
        nonlocal count
        count += 1
        if count == 2:
            raise OSError('synthetic reopen persistence failure')
        return original(*args, **kwargs)
    monkeypatch.setattr(activity_validation, 'import_capture', fail_reopen)
    out = q.run(case.prepare('compare', first['receipt']), settings_loader=lambda: pytest.fail('credentials after failed reopen'))
    assert_outcome(out, 'ERROR', 'unexpected_failure')
    assert count == 2


def test_numeric_json_checkpoint_quantity_is_rejected(case):
    row = case.ledger['rows']['events'][0]
    point = json.loads(row['payload'])
    point['snapshot']['positions'][0]['qty'] = 0
    row['payload'] = json.dumps(point)
    assert_outcome(q.run(case.prepare()), 'REJECTED', 'decimal_schema')
