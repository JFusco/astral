import type { Learning } from "@/lib/contracts";
import { ui } from "@/lib/ui";
import { Panel } from "../ui/panel";
import { Counts } from "../ui/counts";
export function LearningOutcomes({ r }: { r: Learning }) {
  const data = r.data_and_outcomes;
  return (
    <Panel title="Data and outcomes">
      <div className={ui.panelBody}>
        <p>{data.reason}</p>
        <Counts values={data.decision_categories} />
        <p>
          Training rows: {data.training_rows}. Research packets inspected:{" "}
          {data.research_packets_inspected}.
        </p>
      </div>
    </Panel>
  );
}
