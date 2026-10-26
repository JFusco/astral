"""Measured gross-to-net custody evidence; never a fee estimate or write-off."""
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, localcontext
import json

from .fee_evidence import validate_activity

PAIRS = {'BTCUSD': 'BTC', 'ETHUSD': 'ETH', 'SOLUSD': 'SOL'}
TERMINAL = {'filled', 'canceled', 'expired', 'rejected', 'replaced'}


def moment(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:raise ValueError('Timezone required')
    return result


def quantity(value):
    if not isinstance(value, (str, int)) or isinstance(value, bool):raise ValueError('Decimal quantity required')
    result = Decimal(value)
    if not result.is_finite():raise ValueError('Finite quantity required')
    return result


def asset(value):
    value = str(value).replace('/', '')
    return PAIRS.get(value, value if value in PAIRS.values() else None)


def retained(store):
    """Read existing rows only, including legacy decision-context snapshots."""
    return {'orders': store.rows('SELECT * FROM orders'), 'fills': store.rows('SELECT * FROM fills'),
            'activities': store.rows('SELECT * FROM activities'),
            'observations': store.rows('SELECT id,at,outcome,context FROM observations WHERE outcome=\'approved\''),
            'checkpoints': store.rows("SELECT seq AS id,at,payload FROM events WHERE type='custody_snapshot'")}


def retain_checkpoint(store, snapshot):
    """Append future custody changes without altering fills or old evidence."""
    orders = store.rows('SELECT client_id,status,raw FROM orders')
    payload = {'snapshot': snapshot, 'working_orders': [o['client_id'] for o in orders if o['status'] not in TERMINAL]}
    # Cash/mark changes are not custody evidence. Retain baseline, position and
    # fill-state transitions, including a fill whose net position stayed flat.
    signature = [snapshot['account']['id'], sorted((p['symbol'], p['qty']) for p in snapshot['positions']),
                 sorted((o['client_id'], o['status'], json.loads(o['raw']).get('filled_qty')) for o in orders)]
    signature = json.loads(json.dumps(signature))
    previous = store.rows("SELECT payload FROM events WHERE type='custody_snapshot' ORDER BY seq DESC LIMIT 1")
    if not previous or json.loads(previous[0]['payload'])['signature'] != signature:
        # JSON round-trip makes comparison independent of tuple/list encoding.
        payload['signature'] = signature
        store.event('custody_snapshot', payload)


def analyze(*, orders, fills, activities, observations=(), checkpoints=(), snapshot,
            account_id=None, mode=None, as_of=None):
    """Explain reductions across fresh, single-owner, single-buy intervals.

    Observed reductions remain unclassified and vetoed. Only explicitly linked
    confirmed fees can classify them. Unlinked fees suppress inferred overlap
    accounting rather than risking a second debit.
    """
    empty = {'reductions': [], 'additional_debits': {}, 'issues': []}
    if mode != 'alpaca' or not account_id:return empty
    try:
        end = moment(as_of or snapshot['at'])
        if snapshot['account']['id'] != account_id:raise ValueError()
        with localcontext() as ctx:
            ctx.prec = 50
            return _analyze(orders, fills, activities, observations, checkpoints, snapshot, account_id, end)
    except (ValueError, KeyError, TypeError, AttributeError, ArithmeticError):
        return {**empty, 'issues': [{'symbol': None, 'reason': 'Invalid custody evidence; review required'}]}


def _analyze(orders, fills, activities, observations, checkpoints, snapshot, account_id, end):
    issues, order_map, owners, broker_ids = [], {}, defaultdict(set), set()
    for row in orders:
        raw = json.loads(row['raw']);request = json.loads(row['request'])
        if raw['id'] in broker_ids or raw['client_order_id'] != row['client_id']:raise ValueError('Conflicting order identity')
        broker_ids.add(raw['id'])
        name = request.get('intent', {}).get('strategy_id', 'manual')
        book = name if name in {'swing', 'intraday'} else 'manual' if name in {'manual', 'lifecycle_test'} else 'unknown'
        if row['external']:book = 'external'
        order_map[row['client_id']] = {**row, 'broker': raw, 'book': book}
        symbol = asset(raw.get('symbol'))
        if symbol:owners[symbol].add(book)
    executions = []
    for row in fills:
        fill = json.loads(row['payload']);known = moment(row['at']);at = moment(fill['at'])
        if known > end:continue
        if at > known or quantity(fill['quantity']) <= 0 or fill['side'] not in {'buy', 'sell'}:raise ValueError()
        if fill.get('source') != 'alpaca-cumulative-order-readback':raise ValueError()
        executions.append({**fill, 'executed': at, 'known': known, 'symbol': asset(fill['symbol'])})
    points = []
    for row in observations:
        if row['outcome'] == 'approved':points.append((f"observation:{row['id']}", row['at'], json.loads(row['context'])))
    for row in checkpoints:points.append((f"checkpoint:{row['id']}", row['at'], json.loads(row['payload'])))
    points.append(('current', snapshot['at'], {'snapshot': snapshot, 'working_orders': [r['client_id'] for r in orders if r['status'] not in TERMINAL]}))
    valid, conflicts = {}, set()
    for ref, received, point in points:
        snap = point['snapshot'];at = moment(snap['at']);received = moment(received)
        if received > end or at > end:continue
        if snap['account']['id'] != account_id or snap['account']['currency'] != 'USD':raise ValueError()
        if not 0 <= (received-at).total_seconds() <= 15:raise ValueError()
        quantities = {}
        for p in snap['positions']:
            symbol = asset(p['symbol'])
            if symbol is None:continue
            if symbol in quantities or quantity(p['qty']) < 0:raise ValueError()
            quantities[symbol] = quantity(p['qty'])
        working = {o['client_id'] if isinstance(o, dict) else o for o in point['working_orders']}
        entry = {'at': at, 'quantities': quantities, 'ref': ref, 'working': working}
        if at in valid and (quantities != valid[at]['quantities'] or entry['working'] != valid[at]['working']):conflicts.add(at)
        valid.setdefault(at, entry)
    if conflicts:raise ValueError('Conflicting checkpoints')
    points = sorted(valid.values(), key=lambda p: p['at'])
    reductions = {}
    for before, after in zip(points, points[1:]):
        if not 0 < (after['at']-before['at']).total_seconds() <= 60:continue
        between = [f for f in executions if before['at'] < f['executed'] <= after['at']]
        for symbol in PAIRS.values():
            trades = [f for f in between if f['symbol'] == symbol]
            if not trades:continue
            clients = {f['client_id'] for f in trades}
            if len(clients) != 1 or any(f['side'] != 'buy' or f['known'] > after['at'] for f in trades):continue
            cid = next(iter(clients));order = order_map[cid];raw = order['broker']
            if (before['working'] | after['working']) - {cid}:continue
            # Never bridge an unrecorded or concurrent order, including a zero
            # fill/uncertain order that a polling gap might otherwise conceal.
            nearby = [o for o in order_map.values() if asset(o['broker'].get('symbol')) == symbol
                      and moment(o['broker']['submitted_at']) <= after['at']
                      and (o['broker'].get('filled_at') is None or moment(o['broker']['filled_at']) > before['at'])]
            if len(nearby) != 1 or nearby[0]['client_id'] != cid or order['status'] not in TERMINAL:continue
            gross = sum((quantity(f['quantity']) for f in trades), Decimal(0))
            all_fills = [f for f in executions if f['client_id'] == cid]
            if sum((quantity(f['quantity']) for f in all_fills), Decimal(0)) != quantity(raw['filled_qty']):continue
            debit = before['quantities'].get(symbol, Decimal(0))+gross-after['quantities'].get(symbol, Decimal(0))
            if not 0 < debit < gross:continue
            if owners[symbol] != {order['book']} or order['book'] in {'external', 'unknown'}:
                issues.append({'symbol': symbol, 'reason': 'Custody reduction has ambiguous strategy ownership'});continue
            item = reductions.setdefault(cid, {'client_id': cid, 'order_id': raw['id'], 'symbol': symbol,
                'book': order['book'], 'quantity': Decimal(0), 'checkpoints': []})
            item['quantity'] += debit
            item['checkpoints'].append({'before': before['ref'], 'after': after['ref'],
                'before_at': before['at'].isoformat(), 'after_at': after['at'].isoformat(),
                'before_quantity': str(before['quantities'].get(symbol, 0)), 'gross_buy_quantity': str(gross),
                'after_quantity': str(after['quantities'].get(symbol, 0)), 'reduction_quantity': str(debit)})
    linked, unlinked, seen = defaultdict(Decimal), set(), {}
    for row in activities:
        fee = json.loads(row['payload'])
        if moment(row['at']) > end or fee.get('activity_type') != 'CFEE' or fee.get('status') != 'executed':continue
        if row['id'] != fee['id'] or row['type'] != 'CFEE':raise ValueError('Conflicting fee identity')
        if fee['id'] in seen:
            if seen[fee['id']] != fee:raise ValueError('Conflicting fees')
            continue
        seen[fee['id']] = fee
        validate_activity(fee);symbol = asset(fee['symbol'])
        cid = next((cid for cid,o in order_map.items() if o['broker'].get('id') == fee.get('order_id') and fee.get('order_id')), None)
        if cid is None:unlinked.add(symbol)
        elif asset(order_map[cid]['broker'].get('symbol')) != symbol:raise ValueError('Fee order symbol differs')
        else:linked[cid] -= quantity(fee['qty'])
    additional, output = defaultdict(Decimal), []
    for cid, item in reductions.items():
        symbol = item['symbol'];debit = item['quantity'];confirmed = linked[cid]
        ambiguous = symbol in unlinked or confirmed > debit
        pending = Decimal(0) if ambiguous else debit-confirmed
        if ambiguous:issues.append({'symbol': symbol, 'reason': 'Confirmed fee overlap with custody reduction requires review'})
        elif pending:issues.append({'symbol': symbol, 'reason': 'Observed custody reduction requires fee classification'})
        additional[(symbol,item['book'])] += pending
        output.append({**item, 'quantity': str(debit), 'linked_confirmed_fee_quantity': str(confirmed),
            'additional_debit_quantity': str(pending), 'classification': 'ambiguous' if ambiguous else 'unclassified' if pending else 'confirmed-fee'})
    return {'reductions': output, 'additional_debits': {s: {b: str(q) for (a,b),q in additional.items() if a == s} for s,_ in additional},
            'issues': issues}
