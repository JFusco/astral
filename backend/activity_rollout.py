"""Read-only rollout preflight; activation requires a separate explicit invocation."""
import argparse
from contextlib import closing
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import os
import re
import subprocess
import uuid
import json
from pathlib import Path
import shutil
import sqlite3

from .activity_gap_analysis import legacy_summary
from .activity_projection import canonical
from .activity_validation import verify_inputs
from .config import ROOT, Settings
from .store import utcnow

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
    approval_path: Path | None = None
    approval_sha256: str | None = None
    policy_path: Path | None = None
    proposal_json: str | None = None
    run_id: str | None = None

    def validate_ledger(self):
        stat = self.ledger.stat()
        if (stat.st_dev, stat.st_ino) != self.identity:
            raise ValueError('Prepared ledger was replaced; repeat preflight')
        check_ledger(self.ledger, self.account)
        if not self.proposal_json or not self.approval_path or not self.approval_sha256 or not self.policy_path:
            raise ValueError('Prospective operator approval required')
        record, _ = read_document(self.approval_path, self.approval_sha256)
        if record.get('proposal') != json.loads(self.proposal_json):
            raise ValueError('Pinned approval differs')
        validate_approval(self, record)


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


# These documents are private audit inputs, never operational acceptance receipts.
DOCUMENT_BYTES = 1024 * 1024
POLICY_KEYS = {'schema_version', 'tau_seconds', 'tau_c_seconds', 'precision_seconds',
               'overhead_policy', 'e4_policy', 'research_enabled', 'news_enabled',
               'state_poll_seconds', 'observation_poll_seconds', 'local_post_policy',
               'compute_policy', 'owner_decisions_sha256'}


def file_sha(path):
    return hashlib.sha256(os.readlink(path).encode() if path.is_symlink() else path.read_bytes()).hexdigest()


def source_identity():
    """Bind complete maintained checkout bytes, modes and symlink target text."""
    names = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'],
                                    cwd=ROOT).decode().split('\0')
    files = {}
    for name in sorted(set(filter(None, names))):
        if name.startswith('graphify-out/'):
            continue
        parts = Path(name).parts
        if any(part in {'runtime', '.git', '.venv', 'node_modules'} or (part.startswith('.env') and part != '.env.example') for part in parts):
            raise ValueError('Private or disposable file in source inventory')
        path = ROOT/name
        files[name] = {'sha256': file_sha(path), 'mode': oct(path.lstat().st_mode & 0o777),
                       'symlink': path.is_symlink()}
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
    return {'revision': revision, 'files': files}


def no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate document field')
        result[key] = value
    return result


def read_document(path, expected_sha256=None):
    with path.open('rb') as stream:
        raw = stream.read(DOCUMENT_BYTES+1)
    if len(raw) > DOCUMENT_BYTES:
        raise ValueError('Approval document exceeds input budget')
    digest = hashlib.sha256(raw).hexdigest()
    if expected_sha256 is not None and (not re.fullmatch('[0-9a-f]{64}', expected_sha256)
                                        or digest != expected_sha256):
        raise ValueError('Document differs from approved bytes')
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=no_duplicates,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Finite document required')))
    if not isinstance(value, dict):
        raise ValueError('Document object required')
    return value, digest


def timestamp(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?\+00:00', value):
        raise ValueError('UTC approval timestamp required')
    return datetime.fromisoformat(value)


def policy_document(path, expected_sha256=None):
    value, sha = read_document(path, expected_sha256)
    if set(value) != POLICY_KEYS or type(value['schema_version']) is not int or value['schema_version'] != 1:
        raise ValueError('Complete versioned operational policy required')
    for key in ('tau_seconds', 'tau_c_seconds', 'precision_seconds', 'state_poll_seconds', 'observation_poll_seconds'):
        raw = value[key]
        if not isinstance(raw, str) or not 0 < len(raw) <= 64:
            raise ValueError('Explicit decimal policy required')
        try:
            number = Decimal(raw)
            if not number.is_finite() or number < 0 or (key not in {'tau_seconds', 'tau_c_seconds'} and number == 0):
                raise ValueError('Finite operational policy required')
        except InvalidOperation as exc:
            raise ValueError('Finite operational policy required') from exc
    choices = {'overhead_policy': {'recorded-sleep-write-only'},
               'e4_policy': {'allow-indeterminate', 'require-determined'},
               'local_post_policy': {'prohibit', 'emergency-ends-run'},
               'compute_policy': {'quiet-host', 'explicit-overlap'}}
    if any(not isinstance(value[key], str) or value[key] not in allowed for key, allowed in choices.items()):
        raise ValueError('Explicit supported policy choice required')
    if any(type(value[key]) is not bool for key in ('research_enabled', 'news_enabled')):
        raise ValueError('Explicit research and news controls required')
    if not isinstance(value['owner_decisions_sha256'], str) or not re.fullmatch('[0-9a-f]{64}', value['owner_decisions_sha256']):
        raise ValueError('Immutable owner decision record reference required')
    return value, sha


def control_identity(settings):
    return {key: getattr(settings, key) for key in ('mode', 'enable_orders', 'enable_shadow',
        'enable_exit_monitor', 'enable_codex_research', 'enable_research', 'enable_news')}


def check_unused_run(path, run_id):
    if not isinstance(run_id, str) or not re.fullmatch('[0-9a-f]{32}', run_id):
        raise ValueError('Valid unused observation identity required')
    def identities(value):
        found = []
        if isinstance(value, dict):
            for key, item in value.items():
                if key in {'run_id', 'recovered_by'}:
                    if not isinstance(item, str) or not re.fullmatch('[0-9a-f]{32}', item):
                        raise ValueError('Unreadable observation identity')
                    found.append(item)
                else:
                    found.extend(identities(item))
        elif isinstance(value, list):
            for item in value:
                found.extend(identities(item))
        return found
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro', uri=True, timeout=3)) as db:
        db.execute('PRAGMA query_only=ON')
        db.execute('BEGIN')
        for kind, raw in db.execute("""SELECT type, payload FROM events WHERE type GLOB 'activity_rollout_*'
            OR type GLOB 'activity_attempt_*' OR type GLOB 'activity_observation_sleep_*'"""):
            record = json.loads(raw, object_pairs_hook=no_duplicates,
                parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Invalid identity evidence')))
            found = identities(record)
            if (not isinstance(record, dict) or run_id in found
                    or (not found and not (kind == 'activity_rollout_previous' and legacy_summary(record)))):
                raise ValueError('Used or unreadable observation identity')
        row = db.execute("SELECT value FROM state WHERE key='activity_rollout_observation'").fetchone()
        if row:
            record = json.loads(row[0], object_pairs_hook=no_duplicates,
                parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Invalid identity evidence')))
            if run_id in identities(record):
                raise ValueError('Used or unreadable observation identity')


def check_research_registration(path, enabled):
    if not enabled:
        return
    from .experiment import contract
    manifest = contract()
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro', uri=True)) as db:
        row = db.execute("SELECT value FROM state WHERE key='frozen_experiment'").fetchone()
    registration = json.loads(row[0], object_pairs_hook=no_duplicates) if row else None
    if (not manifest or not isinstance(registration, dict)
            or registration.get('manifest_sha256') != manifest['manifest_sha256']
            or registration.get('id') != manifest['id'] or not isinstance(registration.get('registered_at'), str)):
        raise ValueError('Existing matching frozen research registration required')


def propose(settings, prepared, policy_path, start_not_before, start_before, *, run_id=None):
    """No ledger writes or application startup; owner fills approval separately."""
    policy, sha = policy_document(policy_path)
    if (policy['research_enabled'], policy['news_enabled']) != (settings.enable_research, settings.enable_news):
        raise ValueError('Effective research/news differs from policy')
    check_research_registration(prepared.ledger, settings.enable_research)
    identity = uuid.uuid4().hex if run_id is None else run_id
    stat = prepared.ledger.stat()
    if (stat.st_dev, stat.st_ino) != prepared.identity:
        raise ValueError('Prepared ledger was replaced')
    check_ledger(prepared.ledger, prepared.account)
    check_unused_run(prepared.ledger, identity)
    if timestamp(start_not_before) >= timestamp(start_before):
        raise ValueError('Prospective start window required')
    return {'schema_version': 1, 'run_id': identity, 'created_at': utcnow(),
            'source': source_identity(), 'account_id': prepared.account,
            'ledger_identity': list(prepared.identity), 'mapping_sha256': prepared.mapping_sha256,
            'policy_sha256': sha, 'controls': control_identity(settings),
            'start_not_before': start_not_before, 'start_before': start_before, 'duration_seconds': DAY}


def validate_approval(prepared, record):
    if set(record) != {'schema_version', 'method', 'approved_by', 'approved_at', 'proposal'}:
        raise ValueError('Complete operator approval required')
    if type(record['schema_version']) is not int or record['schema_version'] != 1 or record['method'] != 'operator-attested':
        raise ValueError('Operator-attested approval required')
    if not isinstance(record['approved_by'], str) or not record['approved_by'].strip() or len(record['approved_by']) > 200:
        raise ValueError('Approving operator required')
    proposal = record['proposal']
    keys = {'schema_version', 'run_id', 'created_at', 'source', 'account_id', 'ledger_identity',
            'mapping_sha256', 'policy_sha256', 'controls', 'start_not_before', 'start_before', 'duration_seconds'}
    if not isinstance(proposal, dict) or set(proposal) != keys or type(proposal['schema_version']) is not int or proposal['schema_version'] != 1:
        raise ValueError('Complete proposal required')
    now = timestamp(utcnow())
    if not (timestamp(proposal['created_at']) <= timestamp(record['approved_at']) < now
            and timestamp(proposal['start_not_before']) <= now < timestamp(proposal['start_before'])):
        raise ValueError('Approval must precede startup within its window')
    if type(proposal['duration_seconds']) is not int or proposal['duration_seconds'] != DAY:
        raise ValueError('Full observation duration required')
    if (proposal['account_id'] != prepared.account or proposal['ledger_identity'] != list(prepared.identity)
            or proposal['mapping_sha256'] != prepared.mapping_sha256 or proposal['source'] != source_identity()
            or proposal['run_id'] != prepared.run_id):
        raise ValueError('Approval binding differs')
    if not isinstance(proposal['policy_sha256'], str) or not re.fullmatch('[0-9a-f]{64}', proposal['policy_sha256']):
        raise ValueError('Approved policy digest required')
    policy, _ = policy_document(prepared.policy_path, proposal['policy_sha256'])
    controls = proposal['controls']
    if (not isinstance(controls, dict) or controls != json.loads(prepared.proposal_json)['controls']
            or controls['mode'] != 'alpaca' or any(controls[key] for key in
                ('enable_orders', 'enable_shadow', 'enable_exit_monitor', 'enable_codex_research'))
            or (controls['enable_research'], controls['enable_news']) != (policy['research_enabled'], policy['news_enabled'])):
        raise ValueError('Approved controls differ')
    if any(type(controls[key]) is not bool for key in controls if key != 'mode'):
        raise ValueError('Boolean controls required')
    if not isinstance(proposal['ledger_identity'], list) or any(type(x) is not int for x in proposal['ledger_identity']):
        raise ValueError('Integer ledger identity required')
    check_research_registration(prepared.ledger, controls['enable_research'])
    check_unused_run(prepared.ledger, prepared.run_id)


def authorize(settings, prepared, approval_path, approval_sha256, policy_path):
    """Trust the operator's explicit digest and time attestation, not file presence."""
    if not isinstance(approval_sha256, str) or not re.fullmatch('[0-9a-f]{64}', approval_sha256):
        raise ValueError('Explicit operator-approved digest required')
    record, _ = read_document(approval_path, approval_sha256)
    proposal = record.get('proposal')
    if not isinstance(proposal, dict) or proposal.get('controls') != control_identity(settings):
        raise ValueError('Effective controls differ from approval')
    result = replace(prepared, approval_path=approval_path.resolve(strict=True), approval_sha256=approval_sha256,
                     policy_path=policy_path.resolve(strict=True), proposal_json=canonical(proposal), run_id=proposal.get('run_id'))
    result.validate_ledger()
    return result


def activated_settings(settings, prepared):
    if not prepared.proposal_json or json.loads(prepared.proposal_json)['controls'] != control_identity(settings):
        raise ValueError('Effective controls differ from approval')
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
    parser.add_argument('--proposal-output', type=Path)
    parser.add_argument('--policy-file', type=Path)
    parser.add_argument('--start-not-before')
    parser.add_argument('--start-before')
    parser.add_argument('--approval-file', type=Path)
    parser.add_argument('--approval-sha256')
    args = parser.parse_args()
    try:
        if args.proposal_output or args.activate:
            if any(os.environ.get(key) not in {'true', 'false'} for key in
                   ('ASTRAL_ENABLE_RESEARCH', 'ASTRAL_ENABLE_NEWS')):
                raise ValueError('Explicit process research/news booleans required')
        if args.proposal_output and args.activate:
            raise ValueError('Preparation and activation are separate invocations')
        if args.activate and (not args.approval_file or not args.approval_sha256 or not args.policy_file):
            raise ValueError('Prospective approval required before startup')
        settings = replace(Settings.from_env(), db_path=args.ledger)
        prepared = prepare(settings, args.mapping_file, args.mapping_sha256, args.account_id)
        if args.proposal_output:
            if not args.policy_file or not args.start_not_before or not args.start_before:
                raise ValueError('Complete prospective policy/window required')
            destination = args.proposal_output.resolve()
            if destination.is_relative_to(ROOT.resolve()):
                raise ValueError('Keep private approval records outside the repository')
            proposal = propose(settings, prepared, args.policy_file, args.start_not_before, args.start_before)
            with destination.open('x', encoding='utf-8') as output:
                os.chmod(destination, 0o600)
                output.write(canonical({'schema_version': 1, 'method': 'operator-attested',
                    'approved_by': None, 'approved_at': None, 'proposal': proposal})+'\n')
        if not args.activate:
            print(json.dumps({'status': 'prepared', 'reader_activated': False, 'broker_requests': 0,
                              'duration_seconds': DAY, 'max_growth_bytes': MAX_GROWTH, 'min_free_bytes': MIN_FREE,
                              'research_enabled': settings.enable_research, 'news_enabled': settings.enable_news,
                              'approval': 'pending' if args.proposal_output else 'required-for-activation'}))
            return
        prepared = authorize(settings, prepared, args.approval_file, args.approval_sha256, args.policy_file)
        from .activity_observation import Observation
        from .app import create_app
        import uvicorn
        observation = Observation(prepared)
        observation.run_id = prepared.run_id
        app = create_app(activated_settings(settings, prepared), activity_observation=observation)
        uvicorn.run(app, host='127.0.0.1', port=8766, workers=1)
    except (ValueError, OSError, sqlite3.Error, KeyError, TypeError, RecursionError, subprocess.SubprocessError):
        parser.exit(1, 'Accounting rollout preflight failed; no activation permitted\n')


if __name__ == '__main__':
    main()
