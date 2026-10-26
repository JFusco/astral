"use client";
import { useEffect, useRef, useState, type ReactNode } from "react";
import type { createMarketUniverse } from "@/graphics/market-universe";
import { useMotionSettings } from "./motion";
import { Panel } from "./ui/panel";

export type OrbitItem = {
  symbol: string; name: string; type: string; color: string;
  radius: number; phase: number; label: string; detail: string; tone: string;
};
export function OrbitalUniverse({ title, subtitle, items, selected, onSelect, core, observation, fill = null, fillAt = 0, children }: {
  title: string; subtitle: string; items: OrbitItem[]; selected: string;
  onSelect: (id: string) => void; core: string; observation: string;
  fill?: { side: string; symbol: string } | null; fillAt?: number; children?: ReactNode;
}) {
  const pendingFocus = useRef<string | null>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const labels = useRef(new Map<string, HTMLButtonElement>());
  const renderer = useRef<ReturnType<typeof createMarketUniverse> | null>(null);
  const { mode, reduced } = useMotionSettings();
  const [paused, setPaused] = useState(false);
  const [unavailable, setUnavailable] = useState(false);
  const current = useRef({ selected, paused, motion: reduced ? "reduced" : mode, fill, fillAt, items });
  useEffect(() => {
    if (pendingFocus.current && !labels.current.has(pendingFocus.current)) {
      labels.current.values().next().value?.focus();
    }
    pendingFocus.current = null;
  }, [items]);
  useEffect(() => {
    current.current = { selected, paused, motion: reduced ? "reduced" : mode, fill, fillAt, items };
  }, [selected, paused, mode, reduced, fill, fillAt, items]);
  useEffect(() => {
    let disposed = false;
    void import("@/graphics/market-universe").then(({ createMarketUniverse }) => {
      if (disposed || !canvas.current) return;
      try {
        renderer.current = createMarketUniverse(canvas.current, labels.current, () => current.current.items, () => current.current);
      } catch { setUnavailable(true); }
    }).catch(() => { if (!disposed) setUnavailable(true); });
    return () => { disposed = true; renderer.current?.dispose(); renderer.current = null; };
  }, []);
  return (
    <Panel title={title} subtitle={subtitle} className="xl:col-span-2" action={
      <div className="flex gap-3">
        <button className="text-caption text-cyan" onClick={() => setPaused((v) => !v)} aria-pressed={paused}>
          {paused ? "Resume motion" : "Pause motion"}
        </button>
        <button className="text-caption text-cyan" onClick={() => renderer.current?.reset()}>Reset orbit ↻</button>
      </div>
    }>
      <div className="relative h-orbit touch-pan-y overflow-hidden bg-app">
        <canvas ref={canvas} className="size-full cursor-grab active:cursor-grabbing"
          aria-label={`Interactive 3D ${title.toLowerCase()}. Use the selection buttons to explore.`} />
        <div className="pointer-events-none absolute top-4 left-5 bg-app text-xxs tracking-wider text-muted">ORBITAL VIEW</div>
        <div className="pointer-events-none absolute top-4 right-5 bg-app text-xxs text-muted">{observation}</div>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center" aria-hidden="true">
          <span className="font-display text-3xl text-cyan/50">A</span>
          <span className="mt-1 text-xxs tracking-widest bg-app text-muted">{core}</span>
        </div>
        <div className={unavailable ? "absolute inset-x-5 top-12 bottom-12 grid grid-cols-2 content-center gap-2 overflow-y-auto" : undefined}>
        {items.map((item) => (
          <button key={item.symbol} ref={(element) => {
            if (element) labels.current.set(item.symbol, element); else labels.current.delete(item.symbol);
          }} onClick={() => { pendingFocus.current = item.symbol; onSelect(item.symbol); }} aria-label={`Select ${item.name}`} aria-pressed={selected === item.symbol}
            className={`${unavailable ? "relative" : "absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2"} max-w-44 cursor-pointer rounded-md border bg-surface px-2 py-1 font-display text-caption focus-visible:outline-2 focus-visible:outline-cyan ${selected === item.symbol ? "border-accent/50 text-accent" : `border-line ${item.tone}`}`}>
            {item.label}<span className="mt-0.5 block truncate font-sans text-xxs text-muted">{item.detail}</span>
          </button>
        ))}
        </div>
        {unavailable ? <p role="status" className="absolute bottom-4 left-5 text-caption text-muted">Canvas unavailable · use selection buttons</p> : null}
      </div>
      {children}
    </Panel>
  );
}
