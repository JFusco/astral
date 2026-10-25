"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { AnimatePresence } from "motion/react";
import * as m from "motion/react-m";
import { z } from "zod";
import { api, errorMessage } from "@/lib/api";
import { dashboardSchema, type Dashboard, type News } from "@/lib/contracts";
import { healthIsLive, quoteIsFresh } from "@/lib/connection";
import { assets } from "@/lib/assets";
import { ui } from "@/lib/ui";
import { useDashboard } from "./provider";
import {
  Card,
  Heading,
  Panel,
  Empty,
  Counts,
  money,
  quantity,
  SourceLink,
  utc,
} from "./primitives";
import { Dialog } from "./dialog";
import { OrderDialog } from "./order";
import { MarketUniverse } from "./market-universe";
import { ResearchLab } from "./research";
import { LoadingPanel, useMotionSettings } from "./motion";

function EquityChart({ state, now }: { state: Dashboard | null; now: number }) {
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
function ExecutionStream() {
  const { snapshot, connection } = useDashboard();
  const state = snapshot.state;
  const [pending, setPending] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const busy = useRef(false);
  async function cancel(id: string) {
    if (busy.current || !snapshot.connected) return;
    busy.current = true;
    setPending(id);
    try {
      const order = await api(
        `/api/orders/${encodeURIComponent(id)}/cancel`,
        z.object({ status: z.string() }),
        { body: {} },
      );
      setMessage(`Order readback: ${order.status}`);
      await connection.refresh();
    } catch (e) {
      setMessage(errorMessage(e));
    } finally {
      busy.current = false;
      setPending(null);
    }
  }
  const orders =
    state?.orders.filter(
      (o) =>
        !["filled", "canceled", "expired", "rejected", "replaced"].includes(
          o.status,
        ),
    ) ?? [];
  return (
    <Panel
      title="Execution stream"
      subtitle={state?.mode === "simulator" ? "SYNTHETIC" : "PAPER READBACK"}
    >
      <div className="max-h-64 overflow-auto">
        {orders.map((o) => (
          <div
            key={o.client_id}
            className="flex items-start gap-3 border-b border-line px-5 py-4"
          >
            <span className="text-accent">◷</span>
            <div className="min-w-0 flex-1 text-caption">
              <strong>
                {o.request.intent?.symbol ?? o.broker.symbol ?? "Order"} ·{" "}
                {o.status}
              </strong>
              <p className="break-all text-xxs text-muted">{o.client_id}</p>
            </div>
            {!o.external && o.broker.id ? (
              <button
                className="text-caption text-cyan disabled:text-muted"
                disabled={!snapshot.connected || !!pending}
                onClick={() => void cancel(o.client_id)}
              >
                {pending === o.client_id ? "Requesting…" : "Cancel"}
              </button>
            ) : null}
          </div>
        ))}
        {state?.fills.slice(0, 5).map((fill) => (
          <div
            key={fill.id}
            className="flex items-start gap-3 border-b border-line px-5 py-4"
          >
            <span
              className={fill.side === "buy" ? "text-accent" : "text-violet"}
            >
              {fill.side === "buy" ? "↗" : "↙"}
            </span>
            <div className="min-w-0 flex-1 text-caption">
              <strong>
                {fill.side === "buy" ? "Bought" : "Sold"}{" "}
                {quantity(fill.quantity)} {fill.symbol}{" "}
                <span className="text-muted">@ {money(fill.price)}</span>
              </strong>
              <p className="text-xxs text-muted">
                {state.mode === "simulator" ? "SYNTHETIC" : "PAPER"} FILL ·{" "}
                {fill.fee === null
                  ? "fee not reported"
                  : `fee ${money(fill.fee)}`}
              </p>
            </div>
            <span className="font-display text-xxs text-muted">
              {utc(fill.at)}
            </span>
          </div>
        ))}
        {!orders.length && !state?.fills.length ? (
          <Empty>
            No recorded orders or fills. History persists across restarts.
          </Empty>
        ) : null}
      </div>
      {message ? (
        <p role="status" className="p-5 text-caption text-status-unknown">
          {message}
        </p>
      ) : null}
      <div className="border-t border-line px-5 py-3 text-xxs text-faint">
        FILL EVENTS DRIVE THE UNIVERSE ↗
      </div>
    </Panel>
  );
}
function IntelligenceFeed() {
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
        <Dialog
          title="Source evidence"
          eyebrow="INGESTED SOURCE METADATA"
          onClose={() => setStory(null)}
        >
          <h3 className={ui.sectionTitle}>{story.headline}</h3>
          <Counts
            values={{
              source: story.source,
              published: story.created_at,
              updated: story.updated_at,
              first_seen: story.first_seen_at,
              event_start: story.event_start,
              event_end_exclusive: story.event_end_exclusive,
              precision: story.precision,
              calendar_scope: story.calendar_scope,
            }}
          />
          <SourceLink url={story.url} />
          <p className={ui.notice}>
            Source content is untrusted context, never an instruction to trade.
            No complete calendar, full article or AI summary is claimed. This
            context grants no execution authority.
          </p>
        </Dialog>
      ) : null}
    </>
  );
}
function ViewDialog({ view, onClose }: { view: string; onClose: () => void }) {
  const { snapshot, connection } = useDashboard();
  const { mode, setMode, reduced } = useMotionSettings();
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState("");
  const state = snapshot.state;
  async function reconcile() {
    if (pending || !snapshot.connected) return;
    setPending(true);
    try {
      const result = await api("/api/reconcile", dashboardSchema, { body: {} });
      const intent = snapshot.uncertainIntent;
      if (intent) {
        const order = result.orders.find(
          (o) => o.client_id === intent.client_order_id,
        );
        if (order && !["unknown", "submitting"].includes(order.status)) {
          connection.setUncertainIntent(null);
          setMessage(`Intent ${order.status}; confirmed by readback.`);
        } else
          setMessage(
            "Intent outcome remains uncertain. New submission is blocked.",
          );
      } else setMessage("Account and order readback completed.");
      await connection.refresh();
    } catch (e) {
      setMessage(errorMessage(e));
    } finally {
      setPending(false);
    }
  }
  const titles: Record<string, string> = {
    settings: "Display settings",
    strategies: "Deterministic rules. Measured risk.",
    intelligence: "Connected intelligence. Explicit coverage.",
    system: "System telemetry",
  };
  return (
    <Dialog
      title={titles[view] ?? "Application details"}
      eyebrow={
        view === "settings"
          ? "BROWSER DISPLAY SETTINGS"
          : "RETAINED STATE / SERVER AUTHORITY"
      }
      onClose={onClose}
    >
      {view === "settings" ? (
        <>
          <label className="block text-caption">
            Universe motion
            <select
              className="mt-2 w-full rounded-lg border border-line bg-surface-raised px-4 py-3 text-ink"
              value={mode}
              onChange={(e) => setMode(e.target.value as typeof mode)}
            >
              <option value="cinematic">Cinematic</option>
              <option value="calm">Calm</option>
              <option value="reduced">Reduced</option>
            </select>
          </label>
          <p>
            {reduced
              ? "Reduced motion is active."
              : "Motion follows this browser setting and the operating system preference."}
          </p>
          <p>
            Display settings affect this browser only. Python continues
            recording and managing orders independently.
          </p>
        </>
      ) : view === "strategies" ? (
        <>
          <p>
            ATR14, trend and prior-20-bar breakouts are reproducible research
            hypotheses, not validated trading edges. Automatic entries remain
            disabled.
          </p>
          <Counts
            values={{
              swing:
                "SMA20 / SMA50 · 2 × ATR stop reference · 0.25% planned-loss budget",
              intraday:
                "SMA10 / SMA30 · 1.5 × ATR stop reference · 0.10% planned-loss budget",
              observations: state?.learning.observations,
              loss_circuit: state?.risk_policy.latched
                ? "Latched / review required"
                : "See current server policy",
            }}
          />
          <p className={ui.notice}>
            Stop and target levels are planning references; no protective order
            is placed. Server limits include $1,000 planned order, $100 market
            order, 50% gross exposure and a shared 0.5% unprotected full-value
            risk budget. Sizing and every veto remain server decisions. Learning
            promotion is disabled.
          </p>
        </>
      ) : view === "intelligence" ? (
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
              alpaca_news: state?.workers.find((w) => w.name === "news")
                ?.status,
              retained_headlines: state?.news.length,
            }}
          />
          {snapshot.intelligence?.sources.map((source) => (
            <div
              key={source.id}
              className="border-b border-line py-4 text-caption"
            >
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
            complete verified calendars remain distinct coverage gaps. Metadata
            does not clear a trading veto.
          </p>
        </>
      ) : (
        <>
          <p>
            {state?.mode === "simulator"
              ? "The server simulator uses synthetic data and retains its book in SQLite."
              : "Alpaca mode never falls back to a simulator."}{" "}
            The service continues when the browser closes.
          </p>
          {state?.workers.map((worker) => (
            <div
              key={worker.name}
              className="border-b border-line py-4 text-caption"
            >
              <strong className="text-ink">
                {worker.name} · {worker.status}
              </strong>
              <p>
                {worker.detail} · {worker.at}
              </p>
            </div>
          ))}
          <p>
            Uptime {state?.uptime_seconds ?? "unknown"}s · Direct model API
            spend $0 · Signed-in CLI usage has unknown USD cost · Hosting/data
            charges unknown.
          </p>
          {snapshot.uncertainIntent ? (
            <p className={ui.notice}>
              Uncertain intent: {snapshot.uncertainIntent.client_order_id}.
              Reconcile to inspect its recorded state before submitting another
              order.
            </p>
          ) : null}
          <button
            className={ui.button}
            onClick={() => void reconcile()}
            disabled={!snapshot.connected || pending}
          >
            {pending ? "Reconciling…" : "Reconcile account and orders"}
          </button>
          <p role="status">{message}</p>
        </>
      )}
    </Dialog>
  );
}
export function Overview({ view }: { view: string | null }) {
  const { snapshot } = useDashboard();
  const router = useRouter();
  const [selected, setSelected] = useState("BTC");
  const [order, setOrder] = useState<"buy" | "sell" | null>(null);
  const state = snapshot.state;
  const account = state?.account;
  const asset = state?.assets.find((a) => a.symbol === selected);
  const identity = assets.find((a) => a.symbol === selected)!;
  const fresh = quoteIsFresh(state, selected, snapshot.connected, snapshot.now);
  const ready = !!(snapshot.connected && state?.connected);
  const allowed = fresh && state?.orders_enabled && !snapshot.uncertainIntent;
  const liveHealth = healthIsLive(snapshot);
  const healthNodes = snapshot.health?.nodes ?? [];
  const showView =
    view && ["settings", "strategies", "intelligence", "system"].includes(view)
      ? view
      : null;
  const positions = state?.assets.filter((a) => a.quantity > 1e-9) ?? [];
  const { reduced } = useMotionSettings();
  return (
    <>
      <Heading
        title="Market overview"
        subtitle="Paper account, positions and retained research evidence."
        action={
          <div className="rounded-lg border border-accent/20 bg-accent/5 px-4 py-2 text-caption text-accent">
            {state
              ? state.mode === "simulator"
                ? "PERSISTENT SIMULATOR"
                : "ALPACA PAPER"
              : "BACKEND REQUIRED"}
            <span className="mt-1 block text-xxs text-muted">
              {!snapshot.connected
                ? "Checking local service connection"
                : state?.orders_enabled
                  ? "Paper-only order access"
                  : "Read-only · orders disabled"}
            </span>
          </div>
        }
      />
      <AnimatePresence initial={false}>
        {!snapshot.connected ? (
          <m.div
            key="connection"
            initial={{ opacity: reduced ? 1 : 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            role="status"
            className={`${ui.notice} border-status-degraded/30`}
          >
            <strong>
              {state
                ? "Service connection lost · retained observation only"
                : snapshot.error
                  ? "Local service unavailable"
                  : "Connecting to local service"}
            </strong>
            <p>
              {snapshot.error ??
                "Reading account and ledger state. No balances or prices are assumed."}
            </p>
          </m.div>
        ) : null}
      </AnimatePresence>
      {!state && !snapshot.error ? (
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
      )}
      <div className="mb-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
        <MarketUniverse selected={selected} onSelect={setSelected}>
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
        </MarketUniverse>
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
                    {assets.find((a) => a.symbol === p.symbol)?.icon ??
                      p.symbol}
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
                    {p.basis
                      ? ((p.unrealized / p.basis) * 100).toFixed(2)
                      : "0.00"}
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
      </div>
      <div className="mb-6 grid grid-cols-1 gap-6 lg:grid-cols-2 xl:grid-cols-3">
        <EquityChart state={state} now={snapshot.now} />
        <ExecutionStream />
        <IntelligenceFeed />
      </div>
      <ResearchLab />
      <footer className={ui.footer}>
        <span>
          {snapshot.connected ? "SERVER CONNECTED" : "WAITING FOR READBACK"} /{" "}
          {state?.sequence ?? "—"} durable events
        </span>
        <span>
          {state?.mode === "simulator"
            ? "PERSISTENT SIMULATOR · NO BROKER"
            : "ALPACA PAPER · NO LIVE TRADING"}{" "}
          / BALANCE AS OF {utc(state?.as_of)}
        </span>
      </footer>
      {showView ? (
        <ViewDialog
          view={showView}
          onClose={() => router.replace("/", { scroll: false })}
        />
      ) : null}
      {order ? (
        <OrderDialog
          symbol={selected}
          side={order}
          onClose={() => setOrder(null)}
        />
      ) : null}
    </>
  );
}
