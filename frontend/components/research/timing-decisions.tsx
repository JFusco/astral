"use client";
import { object } from "@/lib/data";
import { display } from "@/lib/format";
import { useDashboard } from "../provider";
export function TimingDecisions() {
  const s = useDashboard().snapshot.state;
  return (
    <>
      <h3 className="my-3 text-body font-medium text-ink">
        Buy / sell timing{" "}
        <small className="text-xxs text-muted">NO ORDERS</small>
      </h3>
      <div
        className="max-h-72 overflow-y-auto"
        tabIndex={0}
        role="region"
        aria-label="Recorded buy and sell timing"
      >
        {s?.timing.length ? (
          s.timing.slice(0, 6).map((row, i) => (
            <div
              key={i}
              className="border-b border-line py-4 text-caption text-muted"
            >
              <strong className="text-ink">
                {display(row.symbol)} · {display(row.strategy)} ·{" "}
                {display(row.action)}
              </strong>
              <p className="my-2">{display(row.reason)}</p>
              {row.before_inventory_gate ? (
                <p>
                  Before inventory check:{" "}
                  {display(object(row.before_inventory_gate).action)} ·{" "}
                  {display(object(row.before_inventory_gate).reason)}
                </p>
              ) : null}
              <small>Execution disabled · fill never assumed</small>
            </div>
          ))
        ) : (
          <p className="text-caption text-muted">
            No timing decisions recorded.
          </p>
        )}
      </div>
    </>
  );
}
