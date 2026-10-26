import type { Learning } from "@/lib/contracts";
import { ui } from "@/lib/ui";
import { Panel, Counts } from "../primitives";
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
