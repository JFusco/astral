"use client";
import Link from "next/link";
import { ui } from "@/lib/ui";
import { money } from "@/lib/format";
import { healthIsLive } from "@/lib/connection";
import { useDashboard } from "../provider";
import { Card } from "../ui/card";
import { LoadingPanel } from "../motion";
export function PortfolioCards() {
  const { snapshot } = useDashboard();
  const state = snapshot.state;
  const account = state?.account;
  const liveHealth = healthIsLive(snapshot);
  const healthNodes = snapshot.health?.nodes ?? [];
  return !state && !snapshot.error ? (
    <LoadingPanel label="Reading account and ledger state" cards />
  ) : (
    <section className={ui.summaryGrid} aria-label="Portfolio overview">
      <Card
        label="PORTFOLIO VALUE"
        value={money(account?.equity)}
        note={
          account?.equity === null || !account
            ? "No account readback"
            : `${money(account.net ?? account.equity_change)} since ${state?.mode === "simulator" ? "simulator inception" : "connection"}`
        }
      />
      <Card
        label={
          state?.mode === "simulator" ? "NET TRADING P&L" : "EQUITY CHANGE"
        }
        value={money(account?.net ?? account?.equity_change)}
        note={
          <>
            {account?.realized === null || !account
              ? "Realized P&L not reconciled"
              : `${money(account.realized)} realized`}
            <p>
              {state?.mode === "simulator"
                ? "Synthetic fills · simulated fees included"
                : "Cash flows & fees not fully reconciled"}
            </p>
          </>
        }
        tone="text-accent"
      />
      <Card
        label="CAPITAL AT WORK"
        value={account?.equity == null ? "—" : money(account?.deployed)}
        note={
          <>
            <div className="my-3 h-1 overflow-hidden rounded-full bg-line">
              <span
                className="block h-full bg-cyan"
                style={{
                  width: account?.equity
                    ? `${Math.min(100, (account.deployed / account.equity) * 100)}%`
                    : "0%",
                }}
              />
            </div>
            {money(account?.cash)} cash ·{" "}
            {account?.equity
              ? `${((account.deployed / account.equity) * 100).toFixed(1)}% exposure`
              : "Exposure unknown"}
          </>
        }
      />
      <Link
        href="/health"
        className="block focus-visible:outline-2 focus-visible:outline-cyan"
      >
        <Card
          label="SYSTEM HEARTBEAT"
          value={
            <>
              {liveHealth
                ? healthNodes.filter((n) => n.status === "healthy").length
                : "—"}{" "}
              <span className="font-sans text-caption font-normal text-muted">
                / {healthNodes.length || "—"} assessed
              </span>
            </>
          }
          note={
            <>
              <p>
                {liveHealth
                  ? `${healthNodes.filter((n) => ["down", "degraded", "unknown"].includes(n.status)).length} need attention`
                  : "Health engine unavailable"}
              </p>
              <span className="text-cyan">Health universe ↗</span>
            </>
          }
        />
      </Link>
    </section>
  );
}
