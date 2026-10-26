"""Read a saved local accounting proof for the application, without running it."""
import json
from datetime import datetime, timezone
from pathlib import Path

from .accounting_engine import VERSION, at, digest
from .accounting_receipts import receipt_links


def latest_report(directory, source, mode):
    files = sorted(Path(directory).glob('run-*/report.json'), key=lambda p: p.stat().st_mtime, reverse=True)
    for path in files:
        try:
            contract = json.loads((path.parent/'contract.json').read_text())
            if Path(contract['source_ledger']).resolve() != Path(source).resolve():
                continue
            report = json.loads(path.read_text())
            saved_hash = report.pop('report_sha256')
            if (saved_hash != digest(report) or report['contract_sha256'] != digest(contract)
                    or report['version'] != VERSION or report['source_mode'] != mode
                    or at(report['as_of']) > datetime.now(timezone.utc)):
                raise ValueError('Invalid saved accounting proof')
            costs = report['operating_costs']
            public_costs = {k: costs.get(k) for k in ('status', 'monthly_personal_budget_by_currency',
                'monthly_astral_personal_budget_by_currency', 'monthly_budget_complete', 'actual_total_by_currency',
                'recorded_confirmed_charges_by_currency', 'estimated_charges_by_currency')}
            public_costs['receipt_links'] = receipt_links(costs.get('charges', []))
            # Keep raw invoices, references, private funding notes and lot IDs
            # out of this summary. Export files remain in private runtime/.
            return {'status': 'saved_report', 'as_of': report['as_of'], 'source_mode': report['source_mode'],
                    'fill_rows': report['fill_rows'], 'custody': report['custody'], 'fees': report['fees'],
                    'money_results': report['money_results'], 'issues': report['issues'],
                    'gross_fifo_diagnostics': {k: report['gross_fifo_diagnostics'][k] for k in ('status', 'by_book', 'basis')},
                    'operating_costs': public_costs,
                    'tax_export_status': report['tax_export_status'], 'authority': report['authority']}
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            return {'status': 'unavailable', 'reason': 'Saved accounting report could not be verified'}
    return {'status': 'unavailable', 'reason': 'No saved accounting report for this application ledger'}
