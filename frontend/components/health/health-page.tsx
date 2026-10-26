import { ui } from "@/lib/ui";
import { Heading } from "../ui/heading";
import { Panel } from "../ui/panel";
import { HealthViewState } from "./health-view-state";
import { HealthSummary } from "./health-summary";
import { HealthMap } from "./health-map";
import { HealthDetails } from "./health-details";
import { HealthChanges } from "./health-changes";
import { HealthFooterStatus } from "./health-footer-status";
export function HealthPage() {
  return (
    <HealthViewState>
      <Heading
        title="App health"
        subtitle="Live checks for the application, data, workers and connected services."
        action={
          <p className="text-caption text-muted">
            Assessments every 10 seconds
          </p>
        }
      />
      <HealthSummary />
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <HealthMap />
        <HealthDetails />
      </div>
      <div className={`${ui.columns} mt-6`}>
        <HealthChanges />
        <Panel title="Check coverage">
          <div className={ui.panelBody}>
            <p>
              Application · broker readback · quotes · workers · public feeds ·
              model state · provider reports
            </p>
            <p>
              Checks every 10s. Provider reports every 120s. A missed heartbeat
              becomes unknown. No test trades, paid model calls, automatic
              upgrades or risk changes.
            </p>
            <p>
              Published provider status does not prove account access, payment
              processing or model availability.
            </p>
          </div>
        </Panel>
      </div>
      <footer className={ui.footer}>
        <span>Health checks do not enable trading</span>
        <HealthFooterStatus />
      </footer>
    </HealthViewState>
  );
}
