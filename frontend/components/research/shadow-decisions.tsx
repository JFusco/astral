"use client";
import { display } from "@/lib/format";
import { useDashboard } from "../provider";
export function ShadowDecisions() {
  const s = useDashboard().snapshot.state;
  return (
    <>
      <h3 className="mb-3 text-body font-medium text-ink">
        Shadow decisions{" "}
        <small className="text-xxs text-muted">NO ORDERS</small>
      </h3>
      <div
        className="max-h-72 overflow-y-auto"
        tabIndex={0}
        role="region"
        aria-label="Recorded shadow decisions"
      >
        {s?.shadow.recent.length ? (
          s.shadow.recent.slice(0, 8).map((row, i) => (
            <div
              key={i}
              className="border-b border-line py-4 text-caption text-muted"
            >
              <strong className="text-ink">
                {display(row.intent.symbol)} · {display(row.intent.strategy_id)}{" "}
                · {display(row.result.decision)}
              </strong>
              <p className="my-2">{display(row.result.reason)}</p>
              <small>
                {row.at} · {row.input_hash.slice(0, 12)}
              </small>
            </div>
          ))
        ) : (
          <p className="text-caption text-muted">
            No independent shadow risk probes recorded.
          </p>
        )}
      </div>
    </>
  );
}
