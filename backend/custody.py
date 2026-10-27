"""Measured gross-to-net custody evidence; never a fee estimate or write-off."""
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal, localcontext
import json
import re

from .fee_evidence import validate_activity

PAIRS = {'BTCUSD': 'BTC', 'ETHUSD': 'ETH', 'SOLUSD': 'SOL'}
TERMINAL = {'filled', 'canceled', 'expired', 'rejected', 'replaced'}


def moment(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:raise ValueError('Timezone required')
    return result


def fee_moment(value):
    """Provider activities may carry a UTC date instead of a timestamp."""
    return moment(value+'T00:00:00+00:00' if re.fullmatch(r'\d{4}-\d{2}-\d{2}', value) else value)


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
    seqs = store.get('custody_checkpoint', {}).get('seqs', [])
    return {'orders': store.rows('SELECT * FROM orders'), 'fills': store.rows('SELECT * FROM fills'),
            'activities': store.rows('SELECT * FROM activities'),
            'observations': store.rows('SELECT id,at,outcome,context FROM observations WHERE outcome=\'approved\''),
            'checkpoints': store.rows(f"SELECT seq AS id,at,payload FROM events WHERE seq IN ({','.join('?' for _ in seqs)})", seqs) if seqs else []}


def retain_checkpoint(store, snapshot):
    """Append custody changes inside the caller's reconciliation transaction."""
    orders = store.rows('SELECT client_id,status,raw FROM orders')
    payload = {'snapshot': snapshot, 'working_orders': [o['client_id'] for o in orders if o['status'] not in TERMINAL]}
    # Cash/mark changes are not custody evidence. Retain baseline, position and
    # fill-state transitions, including a fill whose net position stayed flat.
    signature = [snapshot['account']['id'], sorted((p['symbol'], p['qty']) for p in snapshot['positions']),
                 sorted((o['client_id'], o['status'], json.loads(o['raw']).get('filled_qty')) for o in orders)]
    signature = json.loads(json.dumps(signature))
    previous = store.get('custody_checkpoint', {})
    if previous.get('signature') != signature:
        # JSON round-trip makes comparison independent of tuple/list encoding.
        payload['signature'] = signature
        seq = store.event('custody_snapshot', payload)
        store.put('custody_checkpoint', {'signature': signature, 'seqs': previous.get('seqs', [])+[seq]})


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
        if (raw == {} and row['status'] == 'rejected' and not row['external']
                and not any(f['client_id'] == row['client_id'] for f in fills)):continue
        if raw['id'] in broker_ids or raw['client_order_id'] != row['client_id']:raise ValueError('Conflicting order identity')
        broker_ids.add(raw['id'])
        name = request.get('intent', {}).get('strategy_id', 'manual')
        book = name if name in {'swing', 'intraday'} else 'manual' if name in {'manual', 'lifecycle_test'} else 'unknown'
        if row['external']:book = 'external'
        terminal_clock = {'filled': 'filled_at', 'canceled': 'canceled_at', 'expired': 'expired_at',
                          'rejected': 'failed_at', 'replaced': 'replaced_at'}.get(row['status'])
        ended = raw.get(terminal_clock) if terminal_clock else None
        order_map[row['client_id']] = {**row, 'broker': raw, 'book': book, 'ended': moment(ended) if ended else None}
        symbol = asset(raw.get('symbol'))
        if symbol:
            owners[symbol].add(book)
            if row['status'] in TERMINAL and (not ended or moment(ended) > end or moment(row['updated_at']) > end):
                issues.append({'symbol': symbol, 'reason': 'Terminal order evidence unavailable at accounting cutoff'})
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
        lag = (received-at).total_seconds()
        if lag < 0:raise ValueError()
        if lag > 15:
            issues.append({'symbol': None, 'reason': 'Stale custody checkpoint excluded; review required'})
            continue
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
    for cid, order in order_map.items():
        raw = order['broker'];symbol = asset(raw.get('symbol'))
        if raw.get('side') != 'buy' or symbol is None or order['status'] not in TERMINAL:continue
        if order['ended'] is None or order['ended'] > end or moment(order['updated_at']) > end:continue
        trades = [f for f in executions if f['client_id'] == cid]
        gross = sum((quantity(f['quantity']) for f in trades), Decimal(0))
        if not trades or gross != quantity(raw['filled_qty']):continue
        submitted = moment(raw['submitted_at'])
        if any(f['side'] != 'buy' or f['symbol'] != symbol for f in trades):raise ValueError()
        if any(not submitted <= f['executed'] <= order['ended'] for f in trades):
            issues.append({'symbol': symbol, 'client_id': cid, 'reason': 'Order execution time outside terminal window; review required'})
            continue
        # A cumulative REST delta may already be reflected in an intervening
        # position snapshot. Only a complete pre-submission-to-terminal window
        # establishes its gross quantity; receipt time is not execution proof.
        anchors = [p for p in reversed(points) if p['at'] < submitted and not p['working']]
        complete = max(order['ended'], moment(order['updated_at']), *(f['known'] for f in trades))
        endings = [p for p in points if p['at'] >= complete and not p['working']]
        window = next(((a,b) for b in endings for a in anchors if 0 < (b['at']-a['at']).total_seconds() <= 60), None)
        if window is None:continue
        before, after = window
        between = [f for f in executions if f['symbol'] == symbol and before['at'] < f['executed'] <= after['at']]
        if any(f['client_id'] != cid for f in between):continue
        # Never bridge a concurrent or uncertain order, including zero fills.
        nearby = [o for o in order_map.values() if asset(o['broker'].get('symbol')) == symbol
                  and moment(o['broker']['submitted_at']) <= after['at']
                  and (o['ended'] is None or o['ended'] > before['at'])]
        if len(nearby) != 1 or nearby[0]['client_id'] != cid:continue
        debit = before['quantities'].get(symbol, Decimal(0))+gross-after['quantities'].get(symbol, Decimal(0))
        if not 0 < debit < gross:continue
        if owners[symbol] != {order['book']} or order['book'] in {'external', 'unknown'}:
            issues.append({'symbol': symbol, 'reason': 'Custody reduction has ambiguous strategy ownership'});continue
        reductions[cid] = {'client_id': cid, 'order_id': raw['id'], 'symbol': symbol,
            'book': order['book'], 'quantity': debit, 'checkpoints': [{'before': before['ref'], 'after': after['ref'],
            'before_at': before['at'].isoformat(), 'after_at': after['at'].isoformat(),
            'before_quantity': str(before['quantities'].get(symbol, 0)), 'gross_buy_quantity': str(gross),
            'after_quantity': str(after['quantities'].get(symbol, 0)), 'reduction_quantity': str(debit)}]}
    linked, unlinked, seen, fee_windows = defaultdict(Decimal), set(), {}, []
    for row in activities:
        fee = json.loads(row['payload'])
        if fee_moment(row['at']) > end or fee.get('activity_type') != 'CFEE' or fee.get('status') != 'executed':continue
        if row['id'] != fee['id'] or row['type'] != 'CFEE':raise ValueError('Conflicting fee identity')
        if fee['id'] in seen:
            if seen[fee['id']] != fee:raise ValueError('Conflicting fees')
            continue
        seen[fee['id']] = fee
        validate_activity(fee);symbol = asset(fee['symbol'])
        cid = next((cid for cid,o in order_map.items() if o['broker'].get('id') == fee.get('order_id') and fee.get('order_id')), None)
        if cid is None:unlinked.add(symbol)
        elif asset(order_map[cid]['broker'].get('symbol')) != symbol:raise ValueError('Fee order symbol differs')
        else:
            linked[cid] -= quantity(fee['qty'])
            start = fee_moment(row['at'])
            finish = start+timedelta(days=1) if re.fullmatch(r'\d{4}-\d{2}-\d{2}', row['at']) else start
            fee_windows.append((cid, symbol, start, finish))
    # An order ID identifies the charge, not the checkpoint interval that
    # contains its debit. Only unambiguous reductions establish fee coverage;
    # propagate uncovered overlap before calculating any additional debit.
    ambiguous_orders = {cid for cid, item in reductions.items()
                        if item['symbol'] in unlinked or linked[cid] > item['quantity']}
    while True:
        uncovered = [(cid, symbol, start, finish) for cid, symbol, start, finish in fee_windows
                     if cid in ambiguous_orders or linked[cid] > reductions.get(cid, {}).get('quantity', Decimal(0))]
        affected = {cid for cid, item in reductions.items() if cid not in ambiguous_orders
                    and any(other != cid and name == item['symbol']
                            and start <= moment(item['checkpoints'][0]['after_at'])
                            and finish > moment(item['checkpoints'][0]['before_at'])
                            for other, name, start, finish in uncovered)}
        if not affected:break
        ambiguous_orders.update(affected)
    additional, output = defaultdict(Decimal), []
    for cid, item in reductions.items():
        symbol = item['symbol'];debit = item['quantity'];confirmed = linked[cid]
        ambiguous = cid in ambiguous_orders
        pending = Decimal(0) if ambiguous else debit-confirmed
        if ambiguous:issues.append({'symbol': symbol, 'reason': 'Confirmed fee overlap with custody reduction requires review'})
        elif pending:issues.append({'symbol': symbol, 'reason': 'Observed custody reduction requires fee classification'})
        additional[(symbol,item['book'])] += pending
        output.append({**item, 'quantity': str(debit), 'linked_confirmed_fee_quantity': str(confirmed),
            'additional_debit_quantity': str(pending), 'classification': 'ambiguous' if ambiguous else 'unclassified' if pending else 'confirmed-fee'})
    return {'reductions': output, 'additional_debits': {s: {b: str(q) for (a,b),q in additional.items() if a == s} for s,_ in additional},
            'issues': issues}
