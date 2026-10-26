"use client";
import { assets } from "@/lib/assets";
import { useDashboard } from "./provider";
import { OrbitalUniverse } from "./orbital-universe";
const items = assets.map((asset) => ({ ...asset, label: asset.symbol,
  detail: asset.type === "crypto" ? "CRYPTO" : "ETF",
  tone: asset.type === "crypto" ? "text-violet" : "text-cyan" }));
export function MarketUniverse({ selected, onSelect, children }: {
  selected: string; onSelect: (symbol: string) => void; children: React.ReactNode;
}) {
  const { snapshot } = useDashboard();
  return (
    <OrbitalUniverse title="Market universe" subtitle="8 tracked assets" items={items}
      selected={selected} onSelect={onSelect} core="PORTFOLIO CORE"
      observation={snapshot.connected ? snapshot.state?.mode === "simulator" ? "SYNTHETIC" : "OBSERVING" : "STANDBY"}
      fill={snapshot.fill} fillAt={snapshot.fillAt}>
      <p className="px-5 py-3 text-caption text-muted" aria-live="polite">
        {snapshot.fill && snapshot.now - snapshot.fillAt < 6500
          ? `${snapshot.fill.side === "buy" ? "NEBULA" : "SUPERNOVA"} / ${snapshot.fill.symbol} ${snapshot.fill.side.toUpperCase()} FILL`
          : "Every signal has a story."}
      </p>
      {children}
    </OrbitalUniverse>
  );
}
