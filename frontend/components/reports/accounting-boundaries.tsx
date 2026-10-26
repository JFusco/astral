import type { Accounting } from "@/lib/contracts";
import { ui } from "@/lib/ui";
export function AccountingBoundaries({ r }: { r: Accounting }) {
  return (
    <div className="mt-6 space-y-4 border-t border-line py-6 text-body text-muted">
      <h2 className={ui.sectionTitle}>Evaluation boundaries</h2>
      <p>{r.money_results.reason}</p>
      <p>
        Source CSVs and gross lot matches are preparation records, not certified
        tax lots or a filing. Subscription funding notes do not create payment
        or reimbursement transactions.
      </p>
      <p>
        This page displays an on-demand saved snapshot. Refresh does not run an
        evaluation, change a ledger, call a model or enable trading.
      </p>
    </div>
  );
}
