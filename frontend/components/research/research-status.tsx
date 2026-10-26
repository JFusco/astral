"use client";
import { object, records } from "@/lib/data";
import { display } from "@/lib/format";
import { useDashboard } from "../provider";
export function ResearchStatus() {
  const s = useDashboard().snapshot.state;
  const recorded = object(s?.research.last_model_review ?? s?.research.review),
    usage = object(recorded.usage),
    budget = object(s?.research.budget);
  return (
    <div className="grid grid-cols-1 gap-4 border-b border-line p-5 text-caption text-muted sm:grid-cols-2 lg:grid-cols-4">
      <div>
        <strong className="text-ink">
          {s?.shadow.enabled ? "SHADOW OBSERVING" : "SHADOW OFF"}
        </strong>
        <p>
          {s?.shadow.counts
            .map((c) => `${c.count} ${c.decision}`)
            .join(" · ") || "No shadow probes yet"}
        </p>
      </div>
      <div>
        <strong className="text-ink">INVENTORY</strong>
        <p>
          {display(s?.inventory.status)} ·{" "}
          {records(s?.inventory.differences).length} differences
        </p>
      </div>
      <div>
        <strong className="text-ink">RESEARCH WORKER</strong>
        <p>
          {recorded.model
            ? `${display(recorded.model)} / ${display(recorded.effort)} · recorded`
            : s?.research.model_enabled
              ? "Awaiting first review"
              : "Model disabled"}
        </p>
      </div>
      <div>
        <strong className="text-ink">USAGE</strong>
        <p>
          {display(budget.attempts)} / 4 attempts today ·{" "}
          {display(usage.input_tokens)} in / {display(usage.output_tokens)} out
          · USD unknown
        </p>
      </div>
    </div>
  );
}
