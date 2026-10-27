"""Read-only rollout preflight; activation requires a separate explicit invocation."""
import argparse
from contextlib import closing
from dataclasses import dataclass, replace
import json
from pathlib import Path
import shutil
import sqlite3

from .activity_projection import canonical
from .activity_validation import verify_inputs
from .config import Settings

DAY = 86400
MAX_GROWTH = 256 * 1024 * 1024
MIN_FREE = 5 * 1024 * 1024 * 1024


def ledger_bytes(path):
    return sum(p.stat().st_size for p in (path, Path(str(path)+'-wal')) if p.exists())


@dataclass(frozen=True)
class PreparedRollout:
    ledger: Path
    identity: tuple
    account: str
    mapping_json: str
    mapping_sha256: str
    initial_bytes: int

    def validate_ledger(self):
        stat = self.ledger.stat()
        if (stat.st_dev, stat.st_ino) != self.identity:
            raise ValueError('Prepared ledger was replaced; repeat preflight')
        check_ledger(self.ledger, self.account)


def check_ledger(path, account):
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro', uri=True, timeout=3)) as db:
        db.execute('PRAGMA query_only=ON')
        db.execute('BEGIN')
        values = {k: json.loads(v) for k, v in db.execute(
            "SELECT key,value FROM state WHERE key IN ('mode','account_binding','account_snapshot')")}
        if (values.get('mode') != 'alpaca' or values.get('account_binding') != account
                or values.get('account_snapshot', {}).get('account', {}).get('id') != account):
            raise ValueError('Ledger account binding differs from reviewed rollout')
        if db.execute("SELECT 1 FROM orders WHERE status NOT IN ('filled','canceled','expired','rejected','replaced') LIMIT 1").fetchone():
            raise ValueError('Working or uncertain orders require separate reconciliation')


def prepare(settings, mapping_path, mapping_sha256, account):
    """No Store, Engine, credentials output, broker request or ledger mutation."""
    if settings.mode != 'alpaca' or not settings.configured:
        raise ValueError('Configured paper settings required')
    if any((settings.enable_orders, settings.enable_shadow, settings.enable_exit_monitor,
            settings.enable_codex_research, settings.enable_activity_feed)):
        raise ValueError('Rollout preparation requires all execution controls and reader disabled')
    if not account or len(mapping_sha256) != 64:
        raise ValueError('Expected account and mapping digest required')
    mapping = verify_inputs(mapping_path, expected_sha256=mapping_sha256)
    if mapping['account_id'] != account:
        raise ValueError('Mapping belongs to another account')
    path = settings.db_path.resolve(strict=True)
    stat = path.stat()
    check_ledger(path, account)
    if shutil.disk_usage(path.parent).free < MIN_FREE:
        raise ValueError('Rollout requires at least 5 GiB free disk space')
    return PreparedRollout(path, (stat.st_dev, stat.st_ino), account, canonical(mapping),
                           mapping_sha256, ledger_bytes(path))


def activated_settings(settings, prepared):
    prepared.validate_ledger()
    if settings.db_path.resolve(strict=True) != prepared.ledger:
        raise ValueError('Prepared ledger differs from activation target')
    # replace invokes Settings validation; environment variables still cannot enable it.
    return replace(settings, db_path=prepared.ledger, enable_activity_feed=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledger', type=Path, required=True)
    parser.add_argument('--mapping-file', type=Path, required=True)
    parser.add_argument('--mapping-sha256', required=True)
    parser.add_argument('--account-id', required=True)
    parser.add_argument('--activate', action='store_true', help='Requires a separate owner activation decision')
    args = parser.parse_args()
    try:
        settings = replace(Settings.from_env(), db_path=args.ledger)
        prepared = prepare(settings, args.mapping_file, args.mapping_sha256, args.account_id)
        if not args.activate:
            print(json.dumps({'status': 'prepared', 'reader_activated': False, 'broker_requests': 0,
                              'duration_seconds': DAY, 'max_growth_bytes': MAX_GROWTH, 'min_free_bytes': MIN_FREE}))
            return
        from .activity_observation import Observation
        from .app import create_app
        import uvicorn
        app = create_app(activated_settings(settings, prepared), activity_observation=Observation(prepared))
        uvicorn.run(app, host='127.0.0.1', port=8766, workers=1)
    except (ValueError, OSError, sqlite3.Error, KeyError, TypeError):
        parser.exit(1, 'Accounting rollout preflight failed; no activation permitted\n')


if __name__ == '__main__':
    main()
