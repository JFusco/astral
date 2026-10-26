"use client";
import { basisPoints, display, money } from "@/lib/format";
import { useDashboard } from "../provider";
export function ResearchPackets({
  onSelect: setPacket,
}: {
  onSelect: (symbol: string) => void;
}) {
  const s = useDashboard().snapshot.state;
  return (
    <div>
      <h3 className="mb-3 text-body font-medium text-ink">
        Why this ticker, now?
      </h3>
      <div className="max-h-72 overflow-y-auto">
        {s?.research.packets.length ? (
          s.research.packets.map((p) => (
            <button
              key={p.symbol}
              onClick={() => setPacket(p.symbol)}
              className="grid w-full grid-cols-2 gap-3 border-b border-line py-4 text-left text-caption text-muted hover:bg-surface-raised sm:grid-cols-4"
            >
              <strong className="text-body text-ink">
                {p.symbol}
                <small className="mt-1 block text-xxs font-normal text-muted">
                  {display(p.facts.history_source)}
                </small>
              </strong>
              <span>
                {basisPoints(p.facts.spread_bps)} bps
                <small className="block text-xxs">spread</small>
              </span>
              <span>
                {money(p.facts.avg_daily_dollar_volume_20)}
                <small className="block text-xxs">
                  20-day observed $ volume
                </small>
              </span>
              <span
                className={
                  p.eligible ? "text-status-healthy" : "text-status-down"
                }
              >
                {p.eligible ? "RESEARCH ELIGIBLE" : `${p.vetoes.length} VETOES`}{" "}
                ↗
              </span>
            </button>
          ))
        ) : (
          <p className="py-4 text-caption text-muted">
            No evidence packets recorded. Server configuration controls
            research.
          </p>
        )}
      </div>
    </div>
  );
}
