import type { Accounting } from "@/lib/contracts";
import { ui } from "@/lib/ui";
import { Card } from "../primitives";
import { amounts } from "./amounts";
export function AccountingSummary({ r }: { r: Accounting }) {
  const c = r.operating_costs;
  return (
    <section className={ui.summaryGrid} aria-label="Accounting summary">
      <Card
        label="PERSONAL MONTHLY BUDGET"
        value={amounts(c.monthly_astral_personal_budget_by_currency)}
        note="Known subscription inputs; coverage may be incomplete"
        tone="text-accent"
      />
      <Card
        label="RECORDED ACTUAL CHARGES"
        value={amounts(c.actual_total_by_currency)}
        note="Confirmed records; budgets are not invoices"
      />
      <Card
        label="NET TRADING P&L"
        value={
          r.money_results.realized_net_pnl_usd === null
            ? "Unknown"
            : `USD ${r.money_results.realized_net_pnl_usd}`
        }
        note="Requires reconciled fees, basis and cash flows"
      />
      <Card
        label="CUSTODY RECONCILIATION"
        value={
          r.custody.status === "needs_review"
            ? "Needs review"
            : "Quantities matched"
        }
        note={`${r.fill_rows} retained fill rows · fee coverage unverified`}
        tone={r.custody.status === "needs_review" ? "text-status-down" : ""}
      />
    </section>
  );
}
