"""Explicit, disposable replay/GET-only validation. Never migrate a source ledger."""
import argparse
import asyncio
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path

from .activity_projection import balances_match, digest, load_mapping, number
from .config import ROOT, Settings
from .store import Store, dumps, utcnow


def verify_inputs(mapping_file, *, allow_fixture=False):
    path = Path(mapping_file).resolve(strict=True)
    mapping = load_mapping(json.loads(path.read_text()))
    if mapping['kind'] != 'reviewed-provider' and not allow_fixture:
        raise ValueError('Private original acceptance requires a reviewed-provider mapping')
    if mapping['kind'] == 'reviewed-provider' and path.is_relative_to(ROOT):
        raise ValueError('Real-ID mapping must remain outside the repository')
    for name, expected in mapping['source_files'].items():
        source = Path(name)
        source = source if source.is_absolute() else path.parent/source
        if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            raise ValueError('Source evidence hash mismatch')
    return mapping


def verify_argument(mapping, path, role):
    hashes = [sha for name, sha in mapping['source_files'].items() if Path(name).name == role]
    if len(hashes) != 1 or hashlib.sha256(Path(path).read_bytes()).hexdigest() != hashes[0]:
        raise ValueError('Selected input is not the reviewed source for its role')


def import_ledger(store, ledger):
    """Copy captured rows into a new disposable Store, leaving source bytes alone."""
    if ledger['state']['mode'] != 'alpaca':
        raise ValueError('Paper capture required')
    with store.transaction():
        for key, value in ledger['state'].items():
            store.put(key, value)
        for table in ('orders', 'fills', 'activities', 'observations'):
            for row in ledger['rows'][table]:
                columns = list(row)
                # Table/columns come from this fixed schema, never interpolated
                # from arbitrary input keys.
                allowed = {r['name'] for r in store.rows('PRAGMA table_info('+table+')')}
                if set(columns) != allowed:
                    raise ValueError('Capture columns differ from retained schema')
                store.db.execute('INSERT INTO '+table+' VALUES('+','.join('?' for _ in columns)+')', tuple(row.values()))


def import_capture(store, capture, raw, mapping, *, now=None):
    from .activity_feed import parse_sse, start_batch, retain_batch, publish_projection
    if not capture.get('stream_closed') or capture.get('parse_errors') or capture.get('limit_or_error'):
        raise ValueError('Complete original capture required')
    events = parse_sse(raw)
    if digest(events) != digest(capture['events']):
        raise ValueError('Raw and parsed capture disagree')
    request = capture['request']
    if (request['method'] != 'GET' or request['host'] != 'https://paper-api.alpaca.markets'
            or request['path'] != '/v2beta1/events/activities' or request['status'] != 200):
        raise ValueError('Paper acquisition provenance required')
    binding = store.get('account_binding')
    batch = start_batch(store, binding, request['params']['since'], request['params']['until'])
    coverage = {'complete': True, 'account_id': binding, 'events': events, 'raw': raw,
                'since': request['params']['since'], 'until': request['params']['until'],
                'received_at': request['received_at'], 'historical_import': True, 'imported_at': now or utcnow()}
    retain_batch(store, batch, binding, coverage)
    return publish_projection(store, batch, mapping, now=now)


def acceptance(result, store):
    from .inventory import attribute
    from .activity_projection import canonical
    inventory = attribute(store, store.get('account_snapshot'))
    reductions = inventory['custody_reconciliation']['reductions']
    checks = {'no_issues': not result['issues'], 'activity_count': result.get('activity_count') == 19,
              'association_count': result.get('association_count') == 8,
              'cumulative_fills_unchanged': len(store.rows('SELECT id FROM fills')) == 4,
              'btc_flat': sum((number(q) for q in result['net_books'].get('BTC', {}).values()), number('0')) == 0,
              'inventory_btc_flat': sum((number(q) for q in inventory['books'].get('BTC', {}).values()), number('0')) == 0,
              'cash_exact': result['cash_reconciliation']['cash'] is not None and number(result['cash_reconciliation']['cash']) == number('99999.70'),
              'fee_included': number(result['cash_reconciliation'].get('included_fee_usd', '0')) == number('.14'),
              'both_reductions_classified': len(reductions) == 2 and all(r['classification'] == 'confirmed-fee' for r in reductions),
              'no_second_custody_debit': all(number(r['additional_debit_quantity']) == 0 for r in reductions)}
    return checks, canonical(inventory)


def destinations(database, output, inputs):
    database, output = Path(database), Path(output)
    if database.exists() or database.is_symlink() or output.exists() or output.is_symlink():
        raise ValueError('Validation needs new disposable destinations')
    database, output = database.resolve(), output.resolve()
    runtime = (ROOT/'runtime').resolve()
    if database.is_relative_to(runtime) or output.is_relative_to(runtime) or database.parent != output:
        raise ValueError('Database must be inside the new output directory outside runtime')
    for path in inputs:
        source = Path(path).resolve(strict=True)
        if source in (database, output) or source.is_relative_to(output):
            raise ValueError('Source and destination overlap')
    output.mkdir(parents=True, mode=0o700)
    os.chmod(output, 0o700)
    return database, output


async def connected(store, mapping, settings):
    from .broker import AlpacaPaper
    from .activity_feed import collect_batch, publish_projection
    if mapping['kind'] != 'reviewed-provider' or settings.enable_orders:
        raise ValueError('Read-only paper settings and real reviewed mapping required')
    settings = replace(settings, db_path=Path('unused'), enable_orders=False, enable_shadow=False,
                       enable_research=False, enable_codex_research=False, enable_exit_monitor=False, enable_news=False)
    broker = AlpacaPaper(settings, store)
    try:
        snap = await broker.snapshot()
        if snap['account']['id'] != store.get('account_binding'):
            raise ValueError('Captured and connected account differ')
        current_orders = await broker.request('GET', '/v2/orders', params={'status': 'all', 'limit': 500}, critical=True)
        if not isinstance(current_orders, list) or len(current_orders) >= 500:
            raise ValueError('Order coverage unavailable')
        store.put('account_snapshot', snap)
        batch, receipt = await collect_batch(broker, store)
        after = await broker.snapshot()
        if not balances_match(snap, after):
            raise ValueError('Broker balances moved during accounting comparison')
        retained = {json.loads(o['raw'])['id']: json.loads(o['raw']) for o in store.rows('SELECT raw FROM orders')}
        current = {o['id']: o for o in current_orders if number(o.get('filled_qty', '0')) > 0}
        if set(current) != set(retained) or any(current[k]['filled_qty'] != retained[k]['filled_qty'] for k in current):
            raise ValueError('Connected orders differ from retained history')
        result = publish_projection(store, batch, mapping)
        return result, {'acquisition': {k: v for k, v in receipt.items() if k not in ('raw', 'events')},
                        'account_after': after, 'order_count': len(current_orders), 'broker_writes': 0}
    finally:
        await broker.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mapping-file', type=Path, required=True)
    parser.add_argument('--ledger-capture', type=Path, required=True)
    parser.add_argument('--activity-capture', type=Path, required=True)
    parser.add_argument('--raw-stream', type=Path, required=True)
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--connected', action='store_true')
    args = parser.parse_args()
    try:
        mapping = verify_inputs(args.mapping_file)
        verify_argument(mapping, args.ledger_capture, 'ledger-selected-readonly.json')
        verify_argument(mapping, args.activity_capture, 'activity-sse.json')
        verify_argument(mapping, args.raw_stream, 'activity-sse.raw')
        inputs = [args.mapping_file, args.ledger_capture, args.activity_capture, args.raw_stream]
        originals = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
        database, output = destinations(args.database, args.output_dir, inputs)
        ledger, capture = json.loads(args.ledger_capture.read_text()), json.loads(args.activity_capture.read_text())
        store = Store(database, 'alpaca')
        try:
            import_ledger(store, ledger)
            result = import_capture(store, capture, args.raw_stream.read_bytes(), mapping)
            checks, inventory = acceptance(result, store)
            # Reopen the durable database and replay a duplicate through the same path.
            store.close();store = Store(database, 'alpaca')
            repeated = import_capture(store, capture, args.raw_stream.read_bytes(), mapping)
            repeated_checks, _ = acceptance(repeated, store)
            checks['restart_duplicate_invariant'] = all(repeated_checks.values())
            connected_receipt = None
            if args.connected:
                result, connected_receipt = asyncio.run(connected(store, mapping, Settings.from_env()))
                checks['connected_accounting'] = not result['issues']
            checks['originals_unchanged'] = all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == sha for p, sha in originals.items())
            receipt = {'kind': 'private-original-acceptance', 'at': utcnow(), 'checks': checks, 'projection': result,
                       'inventory': json.loads(inventory), 'connected': connected_receipt, 'source_files': originals,
                       'mapping_sha256': digest(mapping), 'implementation_sha256': {
                           p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('activity_*.py')},
                       'orders_enabled': False, 'ledger_adjustments': False}
            path = output/'receipt.json';path.write_text(json.dumps(receipt, indent=2)+'\n');path.chmod(0o600)
        finally:
            store.close()
        print(json.dumps({'status': 'passed' if all(checks.values()) else 'failed', 'checks': checks, 'receipt': str(path)}))
        if not all(checks.values()): raise SystemExit(1)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.exit(1, f'Activity validation failed: {type(exc).__name__}; no source-ledger writes\n')
