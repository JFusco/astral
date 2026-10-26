"use client";
import { ui } from "@/lib/ui";
import { utc } from "@/lib/format";
import { Panel } from "../ui/panel";
import { useHealthView } from "./health-view-state";
export function HealthChanges() {
  const { state, nodes } = useHealthView();
  return (
    <Panel title="Recent status changes">
      <div className={ui.panelBody}>
        {state?.changes.length ? (
          state.changes.slice(0, 4).map((change, i) => (
            <div key={i} className="flex justify-between gap-3 text-caption">
              <span>
                {nodes.find((n) => n.id === change.payload.id)?.name ??
                  change.payload.id}
                : {change.payload.previous ?? "unknown"} →{" "}
                {change.payload.status ?? "unknown"}
              </span>
              <span>{utc(change.at)}</span>
            </div>
          ))
        ) : (
          <p>No health checks received.</p>
        )}
      </div>
    </Panel>
  );
}
