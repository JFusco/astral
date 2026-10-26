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
        <p>
          Budgets, bills and included allocations are separate. Missing records
          do not mean zero spending. Employer-funded subscriptions can have a $0
          personal budget.
        </p>
      </div>
    </Panel>
  );
}
