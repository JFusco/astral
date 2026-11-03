"""Read-only accounting witnesses. They never grant execution authority."""
from datetime import datetime, timezone

from .activity_feed import FeedError, current_accounting
from .activity_projection import digest, instant, number
from .accounting_snapshot import valid_epoch
from .store import utcnow


def capture(store, symbol, *, enabled=False, now=None, max_snapshot_age=30):
    now = now or utcnow()
    with store.lock:
        try:
            max_snapshot_age = min(number('30'), number(str(max_snapshot_age)))
            if max_snapshot_age <= 0:
                raise ValueError('Positive snapshot age required')
        except ValueError as exc:
            raise FeedError('Valid snapshot age required') from exc
        view = current_accounting(store, enabled=enabled, now=now, max_snapshot_age=max_snapshot_age)
        if not view['accounting_by_symbol'].get(symbol, {}).get('passed'):
            raise FeedError('Current covered accounting required; abstain until an eligible cycle')
        evidence = view['accounting_evidence']
        expires = min(instant(evidence['snapshot_at'])+max_snapshot_age, instant(evidence['acquired_at'])+90)
        return {'symbol': symbol, 'snapshot_epoch': evidence['snapshot_epoch'],
                'snapshot_at': evidence['snapshot_at'], 'batch': evidence['batch'],
                'input_sha256': evidence['input_sha256'], 'mapping_sha256': evidence['mapping_sha256'],
                'coverage_until': evidence['coverage_until'], 'acquired_at': evidence['acquired_at'],
                'expires_at': datetime.fromtimestamp(float(expires), timezone.utc).isoformat(),
                'execution_authorized': False}


def recheck(store, witness, *, enabled=False, now=None, max_snapshot_age=30):
    """Caller holds its execution/reconciliation lock through any later decision.

    This only rechecks accounting. Browser acceptance, owner permit, other
    readiness gates and the existing strategy execution denial remain separate.
    """
    if not isinstance(witness, dict) or not isinstance(witness.get('symbol'), str):
        raise FeedError('Accounting witness required')
    if not valid_epoch(witness.get('snapshot_epoch')):
        raise FeedError('Valid accounting witness snapshot epoch required')
    current = capture(store, witness['symbol'], enabled=enabled, now=now, max_snapshot_age=max_snapshot_age)
    if digest(current) != digest(witness):
        raise FeedError('Accounting window changed; abstain until revalidated')
    return current
