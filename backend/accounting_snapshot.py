"""Validated snapshot/version commits. No custody, risk or execution effects."""
from copy import deepcopy
from decimal import Decimal
import json

from .activity_projection import instant
from .evidence_codec import unpack_text
from .executor_ownership import OwnershipError, account_identity


class SnapshotCommitError(ValueError):
    pass


def snapshot_identity(snapshot):
    try:
        return account_identity(snapshot['account'])
    except (ValueError, KeyError, TypeError, OwnershipError) as exc:
        raise SnapshotCommitError('Accounting snapshot identity unavailable') from exc


def validate_snapshot(snapshot, binding):
    """Use reconciliation's finite-decimal formats; retain no account values."""
    try:
        if not isinstance(snapshot, dict) or not isinstance(snapshot['clock'], dict):
            raise ValueError('Snapshot object required')
        if snapshot_identity(snapshot) != binding:
            raise ValueError('Snapshot account differs')
        instant(snapshot['at'])
        if not isinstance(snapshot['positions'], list):
            raise ValueError('Position list required')
        values = [snapshot['account'][key] for key in ('equity', 'cash')]
        for position in snapshot['positions']:
            values.extend(position[key] for key in ('qty', 'market_value', 'cost_basis', 'unrealized_pl'))
        if any(not Decimal(str(value)).is_finite() for value in values):
            raise ValueError('Finite financial values required')
    except (ValueError, KeyError, TypeError, ArithmeticError, OwnershipError) as exc:
        raise SnapshotCommitError('Accounting snapshot validation failed') from exc


def valid_epoch(value):
    return type(value) is int and value > 0


def bound_epoch(store, snapshot):
    """Caller holds store.lock while capturing the snapshot and counter pair."""
    try:
        counter = store.get('snapshot_epoch')
        embedded = snapshot.get('snapshot_epoch') if isinstance(snapshot, dict) else None
        return counter if valid_epoch(counter) and valid_epoch(embedded) and embedded == counter else None
    except (ValueError, TypeError):
        return None


def _require_unversioned_history(store):
    for table, phase in [('activity_batches', " WHERE phase='outcome'"), ('activity_projections', '')]:
        if not store.rows("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)):
            continue
        for row in store.db.execute('SELECT payload FROM '+table+phase):
            record = json.loads(unpack_text(row[0], store.db))
            epoch = record.get('snapshot_epoch') if table == 'activity_batches' else record.get('coverage', {}).get('snapshot_epoch')
            if epoch is not None:
                raise ValueError('Previously initialized epoch unavailable')


def commit_snapshot(store, snapshot):
    """Caller owns one Store.transaction. A return is provisional until commit."""
    with store.lock:
        if not store.db.in_transaction:
            raise SnapshotCommitError('Accounting snapshot transaction required')
        validate_snapshot(snapshot, store.get('account_binding'))
        missing = object()
        try:
            previous = store.get('snapshot_epoch', missing)
            retained = store.get('account_snapshot')
            if previous is missing:
                if isinstance(retained, dict) and 'snapshot_epoch' in retained:
                    raise ValueError('Previously initialized epoch unavailable')
                _require_unversioned_history(store)
                epoch = 1
            elif not valid_epoch(previous):
                raise ValueError('Invalid stored epoch')
            else:
                embedded = retained.get('snapshot_epoch') if isinstance(retained, dict) else None
                if isinstance(retained, dict) and 'snapshot_epoch' in retained and not (valid_epoch(embedded) and embedded <= previous):
                    raise ValueError('Stored epoch regressed')
                epoch = previous+1
        except (ValueError, TypeError, AttributeError, KeyError) as exc:
            raise SnapshotCommitError('Accounting snapshot epoch unavailable') from exc
        stored = deepcopy(snapshot)
        stored['snapshot_epoch'] = epoch
        store.put('account_snapshot', stored)
        store.put('snapshot_epoch', epoch)
        return epoch
