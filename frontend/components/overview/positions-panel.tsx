"use client";
import Link from "next/link";
import { assets } from "@/lib/assets";
import { money, quantity } from "@/lib/format";
import { useDashboard } from "../provider";
import { Panel } from "../ui/panel";
import { Empty } from "../ui/empty";
import { useSelection } from "./selection";
export function PositionsPanel() {
  const { snapshot } = useDashboard();
  const { selected, setSelected } = useSelection();
  const state = snapshot.state;
  const ready = !!(snapshot.connected && state?.connected);
  const positions = state?.assets.filter((a) => a.quantity > 1e-9) ?? [];
  return (
    <Panel
      title="Open positions"
      subtitle={`${state ? positions.length : "—"} positions · ${state?.mode === "simulator" ? "SYNTHETIC" : "PAPER"}`}
    >
      <div className="flex justify-between px-5 py-3 text-xxs text-faint">
        <span>ASSET / QUANTITY</span>
        <span>VALUE / OPEN P&L</span>
      </div>
      {positions.length ? (
        positions.map((p) => (
          <button
            className={`flex w-full items-center justify-between gap-3 border-t border-line px-5 py-4 text-left hover:bg-surface-raised ${selected === p.symbol ? "bg-surface-raised" : ""}`}
            aria-label={`Select ${p.symbol} position`}
            aria-pressed={selected === p.symbol}
            key={p.symbol}
            onClick={() => setSelected(p.symbol)}
          >
            <span className="flex items-center gap-3">
              <span className="grid size-8 place-items-center rounded-full border border-line text-cyan">
                {assets.find((a) => a.symbol === p.symbol)?.icon ?? p.symbol}
              </span>
              <span>
                <strong className="block text-caption">{p.symbol}</strong>
                <small className="text-xxs text-muted">
                  {quantity(p.quantity)}{" "}
                  {p.type === "crypto" ? p.symbol : "shares"}
                </small>
              </span>
            </span>
            <span className="text-right">
              <strong className="block font-display text-body">
                {money(p.market_value)}
              </strong>
              <small
                className={`text-xxs ${p.unrealized < 0 ? "text-status-down" : "text-muted"}`}
              >
                {money(p.unrealized)} (
                {p.basis ? ((p.unrealized / p.basis) * 100).toFixed(2) : "0.00"}
                %)
              </small>
            </span>
          </button>
        ))
      ) : (
        <Empty>
          {state
            ? "No open positions. Unallocated cash is available capital."
            : "No connected account readback."}
        </Empty>
      )}
      <div className="space-y-3 border-t border-line p-5 text-caption text-muted">
        <div className="flex justify-between gap-3">
          <span>Portfolio risk</span>
          <strong className="text-accent">
            {!ready
              ? "READBACK REQUIRED"
              : state?.risk_policy.latched
                ? "LOSS CIRCUIT LATCHED"
                : !state?.orders_enabled
                  ? "READ ONLY"
                  : state.halted
                    ? "ENTRIES HALTED"
                    : state.untracked_positions.length
                      ? "UNTRACKED HOLDINGS"
                      : "SERVER RISK CHECKS"}
          </strong>
        </div>
        <p className="text-xxs text-faint">
          Fresh quotes + server checks required per order
        </p>
        {snapshot.uncertainIntent ? (
          <p className="text-status-unknown">
            Submission outcome uncertain.{" "}
            <Link href="/?view=system" className="text-cyan">
              Reconcile ↗
            </Link>
          </p>
        ) : null}
      </div>
    </Panel>
  );
}
