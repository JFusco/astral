import type { Learning } from "@/lib/contracts";
import { ui } from "@/lib/ui";
import { Panel, Counts } from "../primitives";
export function LearningUsage({ r }: { r: Learning }) {
  const model = r.model_research;
  return (
    <Panel title="Recorded usage and costs">
      <div className={ui.panelBody}>
        <Counts values={model.recorded_usage} />
        <p>
          Attributable model cost:{" "}
          {model.costs.total_actual_usd === null
            ? "unknown"
            : `${model.costs.total_actual_usd} USD`}
          .
        </p>
        <p>
          Unknown-cost receipts: {model.costs.unknown_cost_receipts}.{" "}
          {model.costs.scope}.
        </p>
        <p>
          Platform subscriptions and employer reimbursements belong to
          Accounting.
        </p>
      </div>
    </Panel>
  );
}
