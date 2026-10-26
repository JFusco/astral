import type { Accounting } from "@/lib/contracts";
import { ui } from "@/lib/ui";
import { Panel } from "../ui/panel";
import { amounts } from "./amounts";
export function AccountingCosts({ r }: { r: Accounting }) {
  const c = r.operating_costs;
  return (
    <Panel title="Operating costs">
      <div className={ui.panelBody}>
        <p>
          Personal ASTRAL monthly budget:{" "}
          {amounts(c.monthly_astral_personal_budget_by_currency)}
        </p>
        <p>
          Subscription coverage:{" "}
          {c.monthly_budget_complete
            ? "User-asserted complete"
            : "Incomplete / unverified plans remain"}
        </p>
        <p>
          Recorded confirmed charge subtotal:{" "}
          {amounts(c.recorded_confirmed_charges_by_currency)}
        </p>
        <p>Estimated charges: {amounts(c.estimated_charges_by_currency)}</p>
        {c.receipt_links.length ? (
          <div>
            <h3 className="mb-2 font-medium text-ink">Receipt links</h3>
            <p className="mb-3">Open Gmail to view and download the original documents.</p>
            <ul className="space-y-2" aria-label="Expense receipts">
              {c.receipt_links.map((receipt) => (
                <li key={receipt.url}>
                  <a className={`${ui.button} max-w-full break-words text-left`}
                    href={receipt.url} target="_blank" rel="noopener noreferrer">
                    {receipt.provider} receipt (opens Gmail in a new tab)
                  </a>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        <p>
          Budgets, bills and included allocations are separate. Missing records
          do not mean zero spending. Employer-funded subscriptions can have a $0
          personal budget.
        </p>
      </div>
    </Panel>
  );
}
