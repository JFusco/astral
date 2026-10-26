"use client";
import { ui } from "@/lib/ui";
import { useDashboard } from "../../provider";
import { Counts } from "../../ui/counts";
import { SourceLink } from "../../ui/source-link";
export function IntelligenceView() {
  const { snapshot } = useDashboard();
  const state = snapshot.state;
  return (
    <>
      <p>
        Feed freshness describes retrieval, not complete news or calendar
        coverage.
      </p>
      <Counts
        values={{
          alpaca_readback:
            snapshot.connected && state?.connected
              ? "Connected"
              : "Unavailable",
          alpaca_news: state?.workers.find((w) => w.name === "news")?.status,
          retained_headlines: state?.news.length,
        }}
      />
      {snapshot.intelligence?.sources.map((source) => (
        <div key={source.id} className="border-b border-line py-4 text-caption">
          <SourceLink url={source.url}>{source.name} ↗</SourceLink>
          <p>
            {source.category} · poll {source.interval_seconds}s · HTTP{" "}
            {source.http_status ?? "—"}
          </p>
          <p>
            Checked {source.last_success_at ?? "Never"} ·{" "}
            {source.last_item_count ?? "Unknown"} records
          </p>
          <p>
            {snapshot.intelligenceConnected
              ? source.status
              : "Collector offline"}{" "}
            {snapshot.intelligenceConnected && source.fresh
              ? " / fresh"
              : " / cached or stale"}
          </p>
          <p>{source.detail}</p>
        </div>
      ))}
      <p className={ui.notice}>
        Extracted company financials, ETF holdings, on-chain analytics and
        complete verified calendars remain distinct coverage gaps. Metadata does
        not clear a trading veto.
      </p>
    </>
  );
}
