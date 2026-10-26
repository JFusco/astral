import type { Learning } from "@/lib/contracts";
import { ui } from "@/lib/ui";
import { Panel, label } from "../primitives";
export function LearningInventory({ r }: { r: Learning }) {
  return (
    <Panel title="Evidence inventory" subtitle="Counts at the saved cutoff">
      <div className={`${ui.panelBody} overflow-x-auto`}>
        <table className={ui.table}>
          <thead>
            <tr>
              {[
                "SOURCE",
                "AVAILABLE",
                "PROTECTED",
                "AFTER CUTOFF",
                "INVALID TIME",
              ].map((v) => (
                <th key={v}>{v}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {Object.entries(r.inventory).map(([name, v]) => (
              <tr key={name}>
                <td>{label(name)}</td>
                {(
                  [
                    "available",
                    "protected_window",
                    "after_cutoff",
                    "invalid_timestamp",
                  ] as const
                ).map((key) => (
                  <td key={key}>{v[key] ?? "—"}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}
