import type { Learning } from "@/lib/contracts";
import { ui } from "@/lib/ui";
import { Panel } from "../ui/panel";
export function LearningProtected({ r }: { r: Learning }) {
  return (
    <Panel title="Protected evidence" subtitle="Reserved forward windows">
      <div className={ui.panelBody}>
        {r.protected_windows.map((w) => (
          <div
            key={w.id}
            className="space-y-2 border-b border-line pb-4 last:border-0"
          >
            <h3 className={ui.sectionTitle}>{w.id}</h3>
            <p>
              {w.starts_at} → {w.ends_at}
            </p>
            <p>{w.policy}</p>
          </div>
        ))}
      </div>
    </Panel>
  );
}
