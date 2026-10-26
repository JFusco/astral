import type { Learning } from "@/lib/contracts";
import { ui } from "@/lib/ui";
import { Card } from "../ui/card";
import { label } from "@/lib/format";
export function LearningSummary({ r }: { r: Learning }) {
  const data = r.data_and_outcomes,
    model = r.model_research;
  return (
    <section className={ui.summaryGrid} aria-label="Learning summary">
      <Card
        label="OUTCOME READINESS"
        value={label(data.status)}
        note="Reconciled financial labels are required"
        tone="text-status-unknown"
      />
      <Card
        label="RESOLVED NET P&L LABELS"
        value={data.resolved_net_pnl_labels}
        note="Approvals and fills are not profit labels"
      />
      <Card
        label="MODEL CONTRACTS CHECKED"
        value={
          (model.contract_checks.contract_passed ?? 0) +
          (model.contract_checks.contract_failed ?? 0)
        }
        note="Existing receipts only; no new model calls"
      />
      <Card
        label="MODEL USEFULNESS"
        value={label(model.usefulness.status)}
        note="Requires comparable, reconciled outcome pairs"
        tone="text-status-unknown"
      />
    </section>
  );
}
