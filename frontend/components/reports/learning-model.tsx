import type { Learning } from "@/lib/contracts";
import { ui } from "@/lib/ui";
import { Panel } from "../ui/panel";
import { Counts } from "../ui/counts";
export function LearningModel({ r }: { r: Learning }) {
  const model = r.model_research;
  return (
    <Panel title="Model research quality">
      <div className={ui.panelBody}>
        <h3 className={ui.sectionTitle}>Receipt categories</h3>
        <Counts values={model.receipt_categories} />
        <h3 className={ui.sectionTitle}>Contract and timing checks</h3>
        <Counts values={model.contract_checks} />
        <p>{model.usefulness.reason}</p>
      </div>
    </Panel>
  );
}
