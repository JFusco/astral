"""Cached learning summaries for the app; never starts or changes an evaluation."""
import json
from datetime import datetime, timezone
from pathlib import Path

from .learning_engine import VERSION, digest, timestamp


def latest_report(directory, source, mode):
    paths = sorted(Path(directory).glob('run-*/report.json'), key=lambda p: p.stat().st_mtime, reverse=True)
    for path in paths:
        try:
            contract = json.loads((path.parent/'contract.json').read_text())
            if Path(contract['source_ledger']).resolve() != Path(source).resolve():
                continue
            report = json.loads(path.read_text())
            saved_hash = report.pop('report_sha256')
            if (saved_hash != digest(report) or report['contract_sha256'] != digest(contract)
                    or report['version'] != VERSION or report['source_mode'] != mode
                    or timestamp(report['as_of']) > datetime.now(timezone.utc)):
                raise ValueError('Invalid saved learning proof')
            models = report['model_research']
            return {'status': 'saved_report', 'as_of': report['as_of'], 'source_mode': report['source_mode'],
                    'inventory': report['inventory'], 'data_and_outcomes': report['data_and_outcomes'],
                    'model_research': {key: models[key] for key in ('receipt_categories', 'decisions', 'contract_checks',
                        'scope', 'usefulness', 'recorded_usage', 'costs')},
                    'issues': report['issues'], 'protected_windows': report['protected_windows'],
                    'authority': report['authority'], 'limitations': report['limitations']}
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            return {'status': 'unavailable', 'reason': 'Saved learning report could not be verified'}
    return {'status': 'unavailable', 'reason': 'No saved learning report for this application ledger'}
