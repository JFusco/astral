"use client";
import Link from "next/link";
import { useState } from "react";
import { utc } from "@/lib/format";
import { useDashboard } from "../provider";
import { Panel } from "../ui/panel";
export function EquityChart() {
  const { snapshot } = useDashboard();
  const state = snapshot.state,
    now = snapshot.now;
  const [period, setPeriod] = useState("1D");
  const cutoff =
    now -
    ({ "1H": 3600000, "1D": 86400000, "1W": 604800000 }[period] ?? 86400000);
  const values = (state?.equity_history ?? []).filter(
    (p) => Date.parse(p.at) >= cutoff,
  );
  const nums = values.map((p) => Number(p.value));
  const lo = Math.min(...nums),
    hi = Math.max(...nums),
    pad = Math.max((hi - lo) * 0.15, 0.5),
    first = Date.parse(values[0]?.at ?? ""),
    last = Date.parse(values.at(-1)?.at ?? "");
  const points =
    values.length >= 2
      ? values.map((p, i) => [
          ((Date.parse(p.at) - first) / Math.max(last - first, 1)) * 540,
          112 - ((nums[i] - lo + pad) / (hi - lo + 2 * pad)) * 106,
        ])
      : [];
  const line = points
    .map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(2)},${y.toFixed(2)}`)
    .join(" ");
  const point = points.at(-1);
  const pct =
    nums[0] && nums.length >= 2
      ? ((nums.at(-1)! / nums[0] - 1) * 100).toFixed(2)
      : null;
  return (
    <Panel
      title="Recorded account equity"
      action={
        <div
          className="flex gap-1 rounded border border-line p-1"
          aria-label="Chart period"
        >
          {["1H", "1D", "1W"].map((p) => (
            <button
              className={`rounded px-2 py-1 text-xxs ${period === p ? "bg-surface-raised text-ink" : "text-muted"}`}
              key={p}
              aria-pressed={period === p}
              onClick={() => setPeriod(p)}
            >
              {p}
            </button>
          ))}
        </div>
      }
    >
      <div className="flex items-baseline gap-3 px-5 pt-5">
        <strong className="font-display text-2xl text-accent">
          {pct ? `${Number(pct) >= 0 ? "+" : ""}${pct}%` : "Collecting…"}
        </strong>
        <span className="text-xxs text-muted">DURABLE BACKEND SNAPSHOTS</span>
      </div>
      <div className="h-32 px-5 py-3">
        <svg
          className="size-full"
          viewBox="0 0 540 124"
          role="img"
          aria-label="Recorded account equity from server snapshots"
        >
          <defs>
            <linearGradient id="chartFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#b9f47b" stopOpacity=".2" />
              <stop offset="100%" stopColor="#b9f47b" stopOpacity="0" />
            </linearGradient>
          </defs>
          <path
            d="M0 20H540 M0 60H540 M0 100H540"
            className="stroke-line"
            strokeWidth="1"
          />
          {point ? (
            <>
              <path d={`${line} L540,124 L0,124 Z`} fill="url(#chartFill)" />
              <path d={line} fill="none" stroke="#b9f47b" strokeWidth="2" />
              <circle cx={point[0]} cy={point[1]} r="3.5" fill="#d7ffa8" />
            </>
          ) : null}
        </svg>
      </div>
      <div className="flex justify-between px-5 text-xxs text-muted">
        <span>{point ? utc(values[0].at) : "—"}</span>
        <span>
          {point ? utc(values.at(-1)?.at) : "Waiting for observations"}
        </span>
      </div>
      <div className="mt-5 grid grid-cols-2 gap-2 border-t border-line px-5 py-4 text-xxs text-muted">
        <Link href="/?view=strategies">Swing · not enabled</Link>
        <Link href="/?view=strategies">Intraday · not enabled</Link>
      </div>
    </Panel>
  );
}
