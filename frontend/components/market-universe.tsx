"use client";
import { useEffect, useRef, useState } from "react";
import { assets } from "@/lib/assets";
import type { createMarketUniverse } from "@/graphics/market-universe";
import { useDashboard } from "./provider";
import { useMotionSettings } from "./motion";
import { Panel } from "./ui/panel";
export function MarketUniverse({
  selected,
  onSelect,
  children,
}: {
  selected: string;
  onSelect: (symbol: string) => void;
  children: React.ReactNode;
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const labels = useRef(new Map<string, HTMLButtonElement>());
  const renderer = useRef<ReturnType<typeof createMarketUniverse> | null>(null);
  const { snapshot } = useDashboard();
  const { mode, reduced } = useMotionSettings();
  const [paused, setPaused] = useState(false);
  const [unavailable, setUnavailable] = useState(false);
  const current = useRef({
    selected,
    paused,
    motion: reduced ? "reduced" : mode,
    fill: snapshot.fill,
    fillAt: snapshot.fillAt,
  });
  useEffect(() => {
    current.current = {
      selected,
      paused,
      motion: reduced ? "reduced" : mode,
      fill: snapshot.fill,
      fillAt: snapshot.fillAt,
    };
  }, [selected, paused, mode, reduced, snapshot.fill, snapshot.fillAt]);
  useEffect(() => {
    let disposed = false;
    void import("@/graphics/market-universe")
      .then(({ createMarketUniverse }) => {
        if (disposed || !canvas.current) return;
        try {
          renderer.current = createMarketUniverse(
            canvas.current,
            labels.current,
            assets,
            () => current.current,
          );
        } catch {
          setUnavailable(true);
        }
      })
      .catch(() => {
        if (!disposed) setUnavailable(true);
      });
    return () => {
      disposed = true;
      renderer.current?.dispose();
      renderer.current = null;
    };
  }, []);
  return (
    <Panel
      title="Market universe"
      subtitle="8 tracked assets"
      className="xl:col-span-2"
      action={
        <div className="flex gap-3">
          <button
            className="text-caption text-cyan"
            onClick={() => setPaused((v) => !v)}
            aria-pressed={paused}
          >
            {paused ? "Resume motion" : "Pause motion"}
          </button>
          <button
            className="text-caption text-cyan"
            onClick={() => renderer.current?.reset()}
          >
            Reset orbit ↻
          </button>
        </div>
      }
    >
      <div className="relative h-orbit touch-pan-y overflow-hidden bg-app">
        <canvas
          ref={canvas}
          className="size-full cursor-grab active:cursor-grabbing"
          aria-label="Interactive 3D market universe. Use asset buttons to select a ticker."
        />
        <div className="pointer-events-none absolute top-4 left-5 text-xxs tracking-wider text-faint">
          ORBITAL VIEW
        </div>
        <div className="pointer-events-none absolute top-4 right-5 text-xxs text-faint">
          {snapshot.connected
            ? snapshot.state?.mode === "simulator"
              ? "SYNTHETIC"
              : "OBSERVING"
            : "STANDBY"}
        </div>
        <div
          className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center"
          aria-hidden="true"
        >
          <span className="font-display text-3xl text-cyan/50">A</span>
          <span className="mt-1 text-xxs tracking-widest text-faint">
            PORTFOLIO CORE
          </span>
        </div>
        {assets.map((asset) => (
          <button
            key={asset.symbol}
            ref={(element) => {
              if (element) labels.current.set(asset.symbol, element);
              else labels.current.delete(asset.symbol);
            }}
            onClick={() => onSelect(asset.symbol)}
            aria-label={`Select ${asset.name}`}
            aria-pressed={selected === asset.symbol}
            className={`absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 cursor-pointer rounded-md border bg-surface/90 px-2 py-1 font-display text-caption focus-visible:outline-2 focus-visible:outline-cyan ${selected === asset.symbol ? "border-accent/50 text-accent" : asset.type === "crypto" ? "border-line text-violet" : "border-line text-cyan"}`}
          >
            {asset.symbol}
            <span className="mt-0.5 block font-sans text-xxs text-muted">
              {asset.type === "crypto" ? "CRYPTO" : "ETF"}
            </span>
          </button>
        ))}
        <div
          className="pointer-events-none absolute bottom-14 left-5 rounded-lg border border-line bg-surface/80 px-3 py-2 text-xxs text-muted"
          aria-live="polite"
        >
          {snapshot.fill && snapshot.now - snapshot.fillAt < 6500
            ? `${snapshot.fill.side === "buy" ? "NEBULA" : "SUPERNOVA"} / ${snapshot.fill.symbol} ${snapshot.fill.side.toUpperCase()} FILL`
            : "Every signal has a story."}
        </div>
        <div className="pointer-events-none absolute bottom-4 left-5 text-xxs text-muted">
          ETF · CRYPTO · FILL EVENT
        </div>
        {unavailable ? (
          <p className="absolute top-12 left-5 text-caption text-muted">
            Canvas unavailable · use asset selection buttons
          </p>
        ) : null}
      </div>
      {children}
    </Panel>
  );
}
