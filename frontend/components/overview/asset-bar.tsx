"use client";
import { assets } from "@/lib/assets";
import { quoteIsFresh } from "@/lib/connection";
import { money, utc } from "@/lib/format";
import { ui } from "@/lib/ui";
import { useDashboard } from "../provider";
import { useSelection } from "./selection";
/** Selected asset, its quote freshness and the order entry points. */
export function AssetBar() {
  const { snapshot } = useDashboard();
  const { selected, setOrder } = useSelection();
  const state = snapshot.state;
  const asset = state?.assets.find((a) => a.symbol === selected);
  const identity = assets.find((a) => a.symbol === selected)!;
  const fresh = quoteIsFresh(state, selected, snapshot.connected, snapshot.now);
  const allowed = fresh && state?.orders_enabled && !snapshot.uncertainIntent;
  return (
    <div className="flex flex-wrap items-center justify-between gap-4 border-t border-line px-5 py-4">
      <div className="flex items-center gap-3">
        <span className="grid size-8 place-items-center rounded-full border border-line text-xl text-cyan">
          {identity.icon}
        </span>
        <div>
          <strong className="block text-caption">{identity.name}</strong>
          <span className="text-xxs text-muted">
            {selected} / {identity.type === "crypto" ? "USD" : "ETF"}
          </span>
        </div>
        <div className="ml-4 text-right">
          <strong className="block font-display text-section">
            {money(asset?.price)}
          </strong>
          <span
            className={`text-xxs ${fresh ? "text-accent" : "text-status-unknown"}`}
          >
            {asset?.quote.source
              ? `${asset.quote.source} · ${fresh ? "fresh" : "STALE"} · ${utc(asset.quote.at)}`
              : "No connected quote"}
          </span>
        </div>
      </div>
      <div className="flex gap-2">
        <button
          className={ui.button}
          disabled={!allowed || state?.halted}
          onClick={() => setOrder("buy")}
        >
          ＋ {state?.mode === "simulator" ? "Local" : "Paper"} buy
        </button>
        <button
          className={ui.button}
          disabled={!allowed || !asset || asset.quantity <= 0}
          onClick={() => setOrder("sell")}
        >
          − {state?.mode === "simulator" ? "Local" : "Paper"} sell
        </button>
      </div>
    </div>
  );
}
