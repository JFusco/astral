"""Pure, evidence-bound accounting for the paper activity feed. No write authority."""
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, Inexact, localcontext
import hashlib
import json
import re

from .config import SYMBOLS


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def number(value):
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError('Exact decimal required')
    result = Decimal(value)
    if not result.is_finite():
        raise ValueError('Finite decimal required')
    return result


def instant(value):
    """Compare RFC3339 clocks without truncating provider nanoseconds."""
    if not isinstance(value, str):
        raise ValueError('Timestamp required')
    match = re.fullmatch(r'(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(\.\d{1,18})?(Z|[+-]\d\d:\d\d)', value)
    if not match:
        raise ValueError('RFC3339 timestamp required')
    whole, fraction, zone = match.groups()
    at = datetime.fromisoformat(whole+zone.replace('Z', '+00:00'))
    seconds = (at-datetime(1970, 1, 1, tzinfo=timezone.utc)).total_seconds()
    return Decimal(int(seconds))+Decimal(fraction or '0')


def symbol(value):
    return next((s for s, (pair, _) in SYMBOLS.items() if value in (s, pair, pair.replace('/', ''))), None)


def load_mapping(document):
    """Mappings describe reviewed evidence; they cannot enable any trading action."""
    if not isinstance(document, dict) or type(document.get('version')) is not int or document['version'] != 1:
        raise ValueError('Unsupported association version')
    if document.get('kind') not in ('reviewed-provider', 'sanitized-fixture', 'synthetic-fixture'):
        raise ValueError('Association provenance required')
    if not isinstance(document.get('account_id'), str) or not document['account_id']:
        raise ValueError('Association account required')
    instant(document['known_at'])
    for key in ('source_files', 'expected_events', 'trade_contracts', 'journal_contracts'):
        if not isinstance(document.get(key), dict):
            raise ValueError('Association evidence required')
    if not document['source_files'] or any(not re.fullmatch('[0-9a-f]{64}', h) for h in document['source_files'].values()):
        raise ValueError('Source hashes required')
    if not isinstance(document.get('fee_associations'), list):
        raise ValueError('Fee associations required')
    ids = [item['id'] for item in document['fee_associations']]
    refs = [item['fee_ref_id'] for item in document['fee_associations']]
    if len(set(ids)) != len(ids) or len(set(refs)) != len(refs):
        raise ValueError('Ambiguous association identities')
    canonical(document)
    return document


def ledger_source(store):
    """The caller holds a read transaction or the Store lock across this snapshot."""
    return {'orders': store.rows('SELECT * FROM orders'), 'fills': store.rows('SELECT * FROM fills'),
            'activities': store.rows('SELECT * FROM activities'),
            'state': {key: store.get(key) for key in ('mode', 'account_binding', 'account_snapshot', 'fee_reconciliation_required')}}


def input_digest(source):
    # Quote/equity mark changes do not establish a different quantity/cash history.
    snap = source['state'].get('account_snapshot') or {}
    order_fields = ('client_id', 'request', 'raw', 'status', 'external', 'created_at', 'updated_at')
    return digest({'orders': [{k: r[k] for k in order_fields} for r in source['orders']], 'fills': source['fills'], 'activities': source['activities'],
                   'account': source['state'].get('account_binding'),
                   'positions': sorted((p.get('symbol'), p.get('qty')) for p in snap.get('positions', [])), 'cash': snap.get('account', {}).get('cash'),
                   'legacy_conflict': source['state'].get('fee_reconciliation_required')})


def balances_match(snapshot, after):
    quantities = lambda s: sorted((p['symbol'], p['qty']) for p in s['positions'])
    return (snapshot['account']['id'] == after['account']['id']
            and snapshot['account']['cash'] == after['account']['cash']
            and quantities(snapshot) == quantities(after))


def project(source, events, mapping, coverage, *, knowledge_cutoff, balance_at=None):
    """Return one shared effect set; failure never fabricates a fee or opening cash."""
    with localcontext() as context:
        context.prec = 50
        context.traps[Inexact] = True
        try:
            return _project(source, events, load_mapping(mapping), coverage, knowledge_cutoff, balance_at)
        except (ValueError, KeyError, TypeError, ArithmeticError, AttributeError):
            return {'effects': [], 'issues': ['invalid_activity_evidence'], 'by_symbol': {},
                    'cash_reconciliation': {'status': 'unknown', 'cash': None}, 'net_books': {},
                    'mapping_sha256': None, 'input_sha256': input_digest(source),
                    'fixture': not isinstance(mapping, dict) or mapping.get('kind') != 'reviewed-provider',
                    'association_count': 0, 'activity_count': 0}


def _project(source, events, mapping, coverage, cutoff, balance_at):
    end = instant(cutoff)
    issues, effects = [], []
    snap = source['state'].get('account_snapshot') or {}
    account = snap.get('account', {})
    identity = source['state'].get('account_binding')
    if not identity or identity != account.get('id') or identity != mapping['account_id']:
        issues.append('activity_account_mismatch')
    if account.get('currency') != 'USD':
        issues.append('account_currency_unverified')
    if instant(mapping['known_at']) > end or instant(coverage['received_at']) > end:
        issues.append('evidence_not_yet_known')
    if not coverage.get('complete') or coverage.get('account_id') != identity:
        issues.append('incomplete_activity_coverage')
    if instant(coverage['until']) > instant(coverage['received_at']):
        issues.append('coverage_not_yet_acquired')
    if source['state'].get('fee_reconciliation_required'):
        issues.append('legacy_fee_conflict')
    unique, deliveries = {}, {}
    for event in events:
        ref, delivery, kind = event['ref_id'], event['event_id'], event['activity_type']
        if not all(isinstance(v, str) and v for v in (ref, delivery, kind)):
            raise ValueError('Activity identity required')
        sha = digest(event)
        if delivery in deliveries and deliveries[delivery] != sha:
            issues.append('conflicting_delivery')
        deliveries[delivery] = sha
        if ref in unique and digest(unique[ref]) != sha:
            issues.append('revised_activity')
        unique[ref] = event
        if event.get('account_id', identity) != identity:
            issues.append('activity_account_mismatch')
        if event['status'] != 'executed' or event.get('previous_id') or event.get('details', {}).get('previous_id'):
            issues.append('unreviewed_activity_revision')
        if not instant(coverage['since']) <= instant(event['at']) <= instant(coverage['until']):
            issues.append('activity_outside_interval')
        if instant(event['executed_at']) > instant(coverage['until']):
            issues.append('execution_after_interval')
        for field in ('qty', 'price', 'net_amount'):
            number(event[field])
    expected = mapping['expected_events']
    if any(ref not in unique or digest(unique[ref]) != sha for ref, sha in expected.items()):
        issues.append('missing_or_changed_reviewed_activity')
    if source['activities']:
        # Legacy quantities remain readable, but combining unknown overlapping
        # histories cannot establish a second independent economic charge.
        issues.append('legacy_activity_overlap_unverified')
    orders, by_order, gross, books = {}, defaultdict(list), defaultdict(Decimal), defaultdict(lambda: defaultdict(Decimal))
    for row in source['orders']:
        raw, request = json.loads(row['raw']), json.loads(row['request'])
        if not raw and row['status'] == 'rejected':
            continue
        if raw['id'] in orders or raw['client_order_id'] != row['client_id']:
            raise ValueError('Conflicting order')
        strategy = request.get('intent', {}).get('strategy_id', 'manual')
        book = 'external' if row['external'] else 'manual' if strategy in ('manual', 'lifecycle_test') else strategy
        if book not in ('manual', 'swing', 'intraday', 'external'):
            raise ValueError('Unknown owner')
        orders[raw['id']] = {'raw': raw, 'row': row, 'book': book, 'symbol': symbol(raw['symbol'])}
    for row in source['fills']:
        fill = json.loads(row['payload'])
        order = next((o for o in orders.values() if o['row']['client_id'] == row['client_id']), None)
        if not order or fill['client_id'] != row['client_id'] or symbol(fill['symbol']) != order['symbol']:
            raise ValueError('Fill identity mismatch')
        if fill['source'] != 'alpaca-cumulative-order-readback' or fill['side'] != order['raw']['side']:
            raise ValueError('Fill provenance mismatch')
        if instant(row['at']) > end or instant(fill['at']) > end:
            issues.append('fill_not_yet_known')
        qty = number(fill['quantity'])
        if qty <= 0 or number(fill['value']) <= 0 or number(fill['price']) <= 0:
            raise ValueError('Positive fill required')
        gross[order['raw']['id']] += qty
        books[order['symbol']][order['book']] += qty if fill['side'] == 'buy' else -qty
    cash, included = Decimal(0), Decimal(0)
    reviewed_symbols = set()
    for ref, event in unique.items():
        kind, detail = event['activity_type'], event['details']
        if kind == 'TRD':
            contract = mapping['trade_contracts'].get(ref)
            order = orders.get(detail['order_id'])
            if not contract or contract['sha256'] != digest(event) or not order:
                issues.append('unreviewed_trade'); continue
            if (detail['client_order_id'] != order['row']['client_id'] or symbol(detail['symbol']) != order['symbol']
                    or detail['side'] != order['raw']['side'] or contract['symbol'] != order['symbol']
                    or contract['book'] != order['book'] or contract['currency'] != 'USD'
                    or contract['cash_treatment'] != 'provider-net' or account.get('currency') != 'USD'):
                issues.append('trade_contract_mismatch'); continue
            qty, amount = number(event['qty']), number(event['net_amount'])
            if qty <= 0 or number(event['price']) <= 0 or (detail['side'] == 'buy' and amount > 0) or (detail['side'] == 'sell' and amount < 0):
                raise ValueError('Invalid execution amounts')
            by_order[detail['order_id']].append(event)
            reviewed_symbols.add(order['symbol'])
            cash += amount
        elif kind == 'JNLC':
            contract = mapping['journal_contracts'].get(ref)
            if (not contract or contract['sha256'] != digest(event) or contract['currency'] != 'USD'
                    or event['currency'] != 'USD' or number(event['qty']) != 0):
                issues.append('unreviewed_cash_flow'); continue
            cash += number(event['net_amount'])
        elif kind not in ('CFEE', 'FEE'):
            issues.append('unsupported_activity_type')
    for oid, order in orders.items():
        total = sum((number(e['qty']) for e in by_order[oid]), Decimal(0))
        if total != gross[oid] or total != number(order['raw'].get('filled_qty', '0')):
            issues.append('execution_fill_mismatch')
    associated, associated_trades = set(), set()
    for association in mapping['fee_associations']:
        fee, trade = unique.get(association['fee_ref_id']), unique.get(association.get('trade_ref_id'))
        if not fee or digest(fee) != association['fee_sha256'] or fee['activity_type'] not in ('CFEE', 'FEE'):
            issues.append('unverified_fee_association'); continue
        treatment = association['treatment']
        if treatment == 'standalone-usd':
            # Separate reviewed evidence binds a standalone fee to its asset/book.
            if not association.get('standalone_evidence_sha256'):
                issues.append('unverified_standalone_fee'); continue
            owner = {'symbol': association['symbol'], 'book': association['book']}
        else:
            if not trade or digest(trade) != association['trade_sha256'] or trade['ref_id'] not in mapping['trade_contracts']:
                issues.append('missing_associated_trade'); continue
            owner = orders.get(association['order_id'])
            if (not owner or trade['details']['order_id'] != association['order_id']
                    or owner['row']['client_id'] != association['client_id'] or owner['symbol'] != association['symbol']
                    or owner['book'] != association['book']):
                issues.append('ambiguous_fee_owner'); continue
            if fee['details'].get('parent_id') not in (None, trade['ref_id']):
                issues.append('conflicting_fee_parent'); continue
            if fee['details'].get('order_id') not in (None, association['order_id']):
                issues.append('conflicting_fee_order'); continue
        qty, amount = number(fee['qty']), number(fee['net_amount'])
        if treatment == 'asset-debit' and owner['symbol'] in ('BTC', 'ETH', 'SOL') and qty < 0 and amount == 0:
            books[owner['symbol']][owner['book']] += qty
        elif treatment == 'included-usd' and qty == 0 and amount < 0 and fee['currency'] == 'USD':
            included -= amount
        elif treatment == 'standalone-usd' and qty == 0 and amount < 0 and fee['currency'] == 'USD':
            cash += amount
        else:
            issues.append('unsupported_fee_treatment'); continue
        associated.add(fee['ref_id'])
        if trade and treatment != 'standalone-usd':associated_trades.add(trade['ref_id'])
        effects.append({'association_id': association['id'], 'ref_id': fee['ref_id'], 'client_id': association.get('client_id'),
                        'order_id': association.get('order_id'), 'symbol': owner['symbol'], 'book': owner['book'],
                        'quantity': str(qty if treatment == 'asset-debit' else 0), 'treatment': treatment,
                        'executed_at': fee['executed_at'], 'source_sha256': digest(fee)})
    if any(e['activity_type'] in ('CFEE', 'FEE') and ref not in associated for ref, e in unique.items()):
        issues.append('unassigned_fee')
    if any(e['activity_type'] == 'TRD' and ref not in associated_trades for ref, e in unique.items()):
        issues.append('trade_fee_coverage_unverified')
    actual = defaultdict(Decimal)
    for position in snap['positions']:
        name = symbol(position['symbol'])
        if not name or name in actual or number(position['qty']) < 0:
            raise ValueError('Invalid position')
        actual[name] = number(position['qty'])
    quantity_matches = {s: sum(books[s].values(), Decimal(0)) == actual[s] for s in set(books)|set(actual)}
    if not all(quantity_matches.values()):
        issues.append('unreconciled_asset_quantity')
    if any(q < 0 for book in books.values() for q in book.values()):
        issues.append('negative_owner_inventory')
    if not account.get('created_at') or instant(coverage['since']) > instant(account['created_at']):
        issues.append('cash_history_incomplete')
    if number(account['cash']) != cash:
        issues.append('unreconciled_cash')
    comparison = balance_at or snap['at']
    if comparison != snap['at'] or instant(comparison) > instant(coverage['until']):
        issues.append('balance_outside_coverage')
    issues = sorted(set(issues))
    return {'effects': effects if not issues else [], 'issues': issues,
            'net_books': {s: {b: str(q) for b, q in v.items()} for s, v in books.items()},
            'by_symbol': {s: {'passed': not issues and s in reviewed_symbols and quantity_matches.get(s, False),
                              'status': 'reviewed-history' if not issues and s in reviewed_symbols else 'unverified'} for s in SYMBOLS},
            'cash_reconciliation': {'status': 'matched-historical' if not issues else 'unknown',
                                    'cash': str(cash) if not issues else None, 'included_fee_usd': str(included),
                                    'balance_at': comparison, 'knowledge_cutoff': cutoff},
            'mapping_sha256': digest(mapping), 'input_sha256': input_digest(source),
            'association_count': len(associated), 'activity_count': len(unique), 'fixture': mapping['kind'] != 'reviewed-provider'}
