"use client";
import { ui } from "@/lib/ui";
import { utc } from "@/lib/format";
import { Card } from "../ui/card";
import { LoadingPanel, useMotionSettings } from "../motion";
import { Heartbeat } from "./heartbeat";
import { useHealthView } from "./health-view-state";
export function HealthSummary() {
  const { snapshot, state, live, scoped } = useHealthView();
  const { reduced } = useMotionSettings();
  const count = (statuses: string[]) =>
    state
      ? scoped.filter((node) => statuses.includes(node.status)).length
      : "—";
  return !state && snapshot.healthLoading ? (
    <LoadingPanel label="Connecting to health engine" cards />
  ) : (
    <section className={ui.summaryGrid} aria-label="Health summary">
      <Card
        label="HEALTHY"
        value={count(["healthy"])}
        tone="text-status-healthy"
        note="Recent checks passed"
      />
      <Card
        label="NEEDS ATTENTION"
        value={count(["degraded", "down", "unknown"])}
        tone="text-status-degraded"
        note="Degraded, down or unknown"
      />
      <Card
        label="INACTIVE"
        value={count(["inactive"])}
        tone="text-status-inactive"
        note="Explicitly disabled or deferred"
      />
      <div className={ui.card}>
        <span className={ui.label}>ENGINE HEARTBEAT</span>
        <Heartbeat
          sequence={state?.sequence ?? 0}
          live={live}
          reduced={reduced}
        />
        <span className={ui.note}>
          {state
            ? `${live ? "Completed" : "Last recorded"} ${utc(state.checked_at)}`
            : "Waiting for a real check"}
        </span>
      </div>
    </section>
  );
}
