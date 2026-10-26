"use client";
import Link from "next/link";
import { useState } from "react";
import type { News } from "@/lib/contracts";
import { useDashboard } from "../provider";
import { Panel } from "../ui/panel";
import { Empty } from "../ui/empty";
import { SourceDialog } from "./source-dialog";
export function IntelligenceFeed() {
  const { snapshot } = useDashboard();
  const [filter, setFilter] = useState("all");
  const [story, setStory] = useState<News | null>(null);
  const sourceItems = snapshot.intelligence?.items ?? [];
  const feeds = snapshot.intelligence?.sources ?? [];
  const upcoming = sourceItems
    .filter(
      (n) =>
        n.event_start && Date.parse(n.event_end_exclusive ?? "") > snapshot.now,
    )
    .sort((a, b) => Date.parse(a.event_start!) - Date.parse(b.event_start!))
    .slice(0, 2);
  const all = [
    ...(snapshot.state?.news ?? []),
    ...upcoming,
    ...sourceItems.filter((n) => !n.event_start),
  ].sort(
    (a, b) =>
      (Date.parse(b.created_at ?? b.updated_at ?? b.first_seen_at ?? "") || 0) -
      (Date.parse(a.created_at ?? a.updated_at ?? a.first_seen_at ?? "") || 0),
  );
  const items = all.filter(
    (n) =>
      filter === "all" ||
      (n.category === "crypto" ||
        (n.symbols ?? []).some((s) =>
          ["BTC", "ETH", "SOL", "BTCUSD", "ETHUSD", "SOLUSD"].includes(s),
        )) ===
        (filter === "crypto"),
  );
  return (
    <>
      <Panel
        title="Intelligence feed"
        subtitle={`${feeds.filter((s) => snapshot.intelligenceConnected && s.status === "connected" && s.fresh).length}/${feeds.length} public feeds fresh${snapshot.intelligenceConnected ? "" : " · collector unavailable"}`}
        action={
          <Link className="text-caption text-cyan" href="/?view=intelligence">
            Sources ↗
          </Link>
        }
      >
        <div
          className="flex gap-2 border-b border-line px-5 py-3"
          aria-label="News category"
        >
          {[
            ["all", "All signals"],
            ["markets", "Markets"],
            ["crypto", "Crypto"],
          ].map(([value, title]) => (
            <button
              key={value}
              className={`rounded px-2 py-1 text-xxs ${filter === value ? "bg-cyan/10 text-cyan" : "text-muted"}`}
              aria-pressed={filter === value}
              onClick={() => setFilter(value)}
            >
              {title}
            </button>
          ))}
        </div>
        <div className="max-h-96 overflow-y-auto">
          {items.slice(0, 20).map((n, i) => (
            <button
              key={`${n.source}-${n.id}-${i}`}
              className="block w-full border-b border-line px-5 py-4 text-left hover:bg-surface-raised"
              onClick={() => setStory(n)}
            >
              <span className="text-xxs text-faint">
                {n.source} ·{" "}
                {n.event_start
                  ? `Scheduled ${n.event_start.slice(0, 10)}`
                  : (n.created_at ?? "Publication unknown")}
                {n.source_id &&
                (!snapshot.intelligenceConnected ||
                  !feeds.find((s) => s.id === n.source_id)?.fresh)
                  ? " · CACHED / SOURCE UNAVAILABLE"
                  : ""}
              </span>
              <span className="my-2 block text-body font-medium text-ink">
                {n.headline}
              </span>
              <span className="text-xxs text-cyan">
                {n.symbols?.join(" · ") || n.category || "markets"}
              </span>
            </button>
          ))}
          {!items.length ? (
            <Empty>
              No connected news items. Missing feeds do not imply complete event
              coverage.
            </Empty>
          ) : null}
        </div>
      </Panel>
      {story ? (
        <SourceDialog story={story} onClose={() => setStory(null)} />
      ) : null}
    </>
  );
}
