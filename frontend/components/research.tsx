"use client";
import { useState } from "react";
import { z } from "zod";
import { api, errorMessage } from "@/lib/api";
import { object, records } from "@/lib/data";
import { ui } from "@/lib/ui";
import { useDashboard } from "./provider";
import { Panel } from "./ui/panel";
import { Evidence } from "./ui/evidence";
import { SourceLink } from "./ui/source-link";
import { display, money } from "@/lib/format";
import { Dialog } from "./dialog";
type Detail = { title: string; eyebrow: string; value: unknown };
export function ResearchLab() {
  const { snapshot } = useDashboard();
  const s = snapshot.state;
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState("");
  const [detail, setDetail] = useState<Detail | null>(null);
  const [packet, setPacket] = useState<string | null>(null);
  const running = s?.workers.some(
    (w) => w.name === "research" && w.status === "running",
  );
  async function run() {
    if (pending || running) return;
    setPending(true);
    try {
      const result = await api(
        "/api/research/run",
        z.object({ status: z.string() }),
        { body: {} },
      );
      setMessage(
        `Research ${result.status}. Results arrive through the server stream.`,
      );
    } catch (e) {
      setMessage(errorMessage(e));
    } finally {
      setPending(false);
    }
  }
  const recorded = object(s?.research.last_model_review ?? s?.research.review),
    usage = object(recorded.usage),
    budget = object(s?.research.budget);
  const selected = s?.research.packets.find((p) => p.symbol === packet);
  const gates = records(s?.readiness?.symbols).find((r) => r.symbol === "BTC");
  const experiment = s?.experiment,
    replay = s?.portfolio_replay,
    liquidity = s?.liquidity_experiment;
  const open = (title: string, value: unknown) =>
    setDetail({ title, eyebrow: "RETAINED EVIDENCE / NO EXECUTION", value });
  return (
    <>
      <Panel
        title="Research & risk lab"
        subtitle="Evidence before execution"
        action={
          <button
            className="text-caption text-cyan disabled:text-muted"
            disabled={
              !snapshot.connected || !s?.research.enabled || running || pending
            }
            onClick={() => void run()}
          >
            {running || pending
              ? "Research in progress…"
              : "Run research review ↗"}
          </button>
        }
      >
        <div className="grid grid-cols-1 gap-4 border-b border-line p-5 text-caption text-muted sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <strong className="text-ink">
              {s?.shadow.enabled ? "SHADOW OBSERVING" : "SHADOW OFF"}
            </strong>
            <p>
              {s?.shadow.counts
                .map((c) => `${c.count} ${c.decision}`)
                .join(" · ") || "No shadow probes yet"}
            </p>
          </div>
          <div>
            <strong className="text-ink">INVENTORY</strong>
            <p>
              {display(s?.inventory.status)} ·{" "}
              {records(s?.inventory.differences).length} differences
            </p>
          </div>
          <div>
            <strong className="text-ink">RESEARCH WORKER</strong>
            <p>
              {recorded.model
                ? `${display(recorded.model)} / ${display(recorded.effort)} · recorded`
                : s?.research.model_enabled
                  ? "Awaiting first review"
                  : "Model disabled"}
            </p>
          </div>
          <div>
            <strong className="text-ink">USAGE</strong>
            <p>
              {display(budget.attempts)} / 4 attempts today ·{" "}
              {display(usage.input_tokens)} in / {display(usage.output_tokens)}{" "}
              out · USD unknown
            </p>
          </div>
        </div>
        {message ? (
          <p role="status" className="p-5 text-caption text-cyan">
            {message}
          </p>
        ) : null}
        <div className="space-y-3 border-b border-line p-5 text-caption text-muted">
          <p>
            {s?.crypto_universe ? (
              <>
                <button
                  className="text-cyan"
                  onClick={() =>
                    open("Crypto discovery universe", s.crypto_universe)
                  }
                >
                  {records(s.crypto_universe.assets).length} crypto venue
                  listings ↗
                </button>{" "}
                · Discovery only; listings do not enable orders.
              </>
            ) : (
              "Crypto discovery awaits a connected venue."
            )}
          </p>
          {gates ? (
            <p>
              <strong>BTC / FIRST RESEARCH TRADE</strong> · Fees{" "}
              {object(gates.fees).passed ? "matched" : "BLOCKED"} · Depth{" "}
              {object(gates.depth).passed ? "validated" : "unverified / stale"}{" "}
              · Liquidity{" "}
              {object(gates.liquidity).passed ? "passes" : "BLOCKED"} · Events{" "}
              {display(object(gates.events).status)} ·{" "}
              <button
                className="text-cyan"
                onClick={() => open("BTC: remaining gates", gates)}
              >
                Gate evidence ↗
              </button>
            </p>
          ) : (
            <p>Readiness evidence has not been collected.</p>
          )}
        </div>
        <div className="grid grid-cols-1 gap-6 p-5 lg:grid-cols-2">
          <div>
            <h3 className="mb-3 text-body font-medium text-ink">
              Why this ticker, now?
            </h3>
            <div className="max-h-72 overflow-y-auto">
              {s?.research.packets.length ? (
                s.research.packets.map((p) => (
                  <button
                    key={p.symbol}
                    onClick={() => setPacket(p.symbol)}
                    className="grid w-full grid-cols-2 gap-3 border-b border-line py-4 text-left text-caption text-muted hover:bg-surface-raised sm:grid-cols-4"
                  >
                    <strong className="text-body text-ink">
                      {p.symbol}
                      <small className="mt-1 block text-xxs font-normal text-muted">
                        {display(p.facts.history_source)}
                      </small>
                    </strong>
                    <span>
                      {display(p.facts.spread_bps)} bps
                      <small className="block text-xxs">spread</small>
                    </span>
                    <span>
                      {money(p.facts.avg_daily_dollar_volume_20)}
                      <small className="block text-xxs">
                        20-day observed $ volume
                      </small>
                    </span>
                    <span
                      className={
                        p.eligible ? "text-status-healthy" : "text-status-down"
                      }
                    >
                      {p.eligible
                        ? "RESEARCH ELIGIBLE"
                        : `${p.vetoes.length} VETOES`}{" "}
                      ↗
                    </span>
                  </button>
                ))
              ) : (
                <p className="py-4 text-caption text-muted">
                  No evidence packets recorded. Server configuration controls
                  research.
                </p>
              )}
            </div>
          </div>
          <div>
            <h3 className="mb-3 text-body font-medium text-ink">
              Shadow decisions{" "}
              <small className="text-xxs text-muted">NO ORDERS</small>
            </h3>
            <div
              className="max-h-72 overflow-y-auto"
              tabIndex={0}
              role="region"
              aria-label="Recorded shadow decisions"
            >
              {s?.shadow.recent.length ? (
                s.shadow.recent.slice(0, 8).map((row, i) => (
                  <div
                    key={i}
                    className="border-b border-line py-4 text-caption text-muted"
                  >
                    <strong className="text-ink">
                      {display(row.intent.symbol)} ·{" "}
                      {display(row.intent.strategy_id)} ·{" "}
                      {display(row.result.decision)}
                    </strong>
                    <p className="my-2">{display(row.result.reason)}</p>
                    <small>
                      {row.at} · {row.input_hash.slice(0, 12)}
                    </small>
                  </div>
                ))
              ) : (
                <p className="text-caption text-muted">
                  No independent shadow risk probes recorded.
                </p>
              )}
            </div>
            <h3 className="my-3 text-body font-medium text-ink">
              Buy / sell timing{" "}
              <small className="text-xxs text-muted">NO ORDERS</small>
            </h3>
            <div
              className="max-h-72 overflow-y-auto"
              tabIndex={0}
              role="region"
              aria-label="Recorded buy and sell timing"
            >
              {s?.timing.length ? (
                s.timing.slice(0, 6).map((row, i) => (
                  <div
                    key={i}
                    className="border-b border-line py-4 text-caption text-muted"
                  >
                    <strong className="text-ink">
                      {display(row.symbol)} · {display(row.strategy)} ·{" "}
                      {display(row.action)}
                    </strong>
                    <p className="my-2">{display(row.reason)}</p>
                    {row.before_inventory_gate ? (
                      <p>
                        Before inventory check:{" "}
                        {display(object(row.before_inventory_gate).action)} ·{" "}
                        {display(object(row.before_inventory_gate).reason)}
                      </p>
                    ) : null}
                    <small>Execution disabled · fill never assumed</small>
                  </div>
                ))
              ) : (
                <p className="text-caption text-muted">
                  No timing decisions recorded.
                </p>
              )}
            </div>
          </div>
        </div>
        <div className="space-y-4 border-t border-line p-5 text-caption text-muted">
          <p>
            {experiment ? (
              <>
                {display(experiment.id)} ·{" "}
                {experiment.code_matches
                  ? "Code verified"
                  : "CODE DRIFT / BLOCKED"}{" "}
                · ${display(experiment.notional_cap_usd)} proposal cap ·{" "}
                {display(experiment.observations)} prospective observations ·
                Read-only research every 15 min · Last{" "}
                {display(experiment.last_observation_at)}.{" "}
                <button
                  className="text-cyan"
                  onClick={() => open("Frozen strategy experiment", experiment)}
                >
                  Experiment evidence ↗
                </button>
              </>
            ) : (
              "Frozen strategy experiment has not been registered."
            )}
          </p>
          <p>
            {replay ? (
              <>
                Portfolio replay ·{" "}
                {replay.code_matches ? "Code verified" : "CODE DRIFT / REVIEW"}{" "}
                · {display(replay.synthetic_scenarios)} synthetic scenarios ·{" "}
                {display(object(replay.observed_coverage).quotes)} quotes /{" "}
                {display(object(replay.observed).fill_count)} hypothetical
                fills.{" "}
                <button
                  className="text-cyan"
                  onClick={() => open("Portfolio replay", replay)}
                >
                  Replay evidence ↗
                </button>{" "}
                · All modeled fills are hypothetical; profitability unvalidated.
              </>
            ) : (
              "Portfolio replay report has not been recorded."
            )}
          </p>
          <p>
            {liquidity ? (
              <>
                Separate liquidity experiment · {display(liquidity.id)} ·{" "}
                {display(liquidity.status)} · {display(liquidity.samples)}{" "}
                snapshots · No orders, fills or profit inferred.{" "}
                <button
                  className="text-cyan"
                  onClick={() => open("BTC: liquidity experiment", liquidity)}
                >
                  Liquidity comparison ↗
                </button>
              </>
            ) : (
              "Separate liquidity experiment has not been registered."
            )}
          </p>
          <p>
            {s?.execution_pilot?.phase === "completed"
              ? `Execution test: ${display(s.execution_pilot.outcome)}. Equity change ${display(s.execution_pilot.equity_change_usd)} USD; fees not reconciled. Research strategy gates remain separate.`
              : display(
                  object(object(s?.research.review).review).summary ??
                    "The researcher proposes. The risk engine decides. Unknown sources can veto a candidate.",
                )}
          </p>
        </div>
      </Panel>
      {detail ? (
        <Dialog
          title={detail.title}
          eyebrow={detail.eyebrow}
          onClose={() => setDetail(null)}
        >
          <Evidence value={detail.value} />
          <p className={ui.notice}>
            Retained evidence does not grant order authority or change frozen
            risk rules. Missing values remain unknown.
          </p>
        </Dialog>
      ) : null}
      {selected ? (
        <Dialog
          title={`${selected.symbol}: why now?`}
          eyebrow="RESEARCH EVIDENCE / NO EXECUTION"
          onClose={() => setPacket(null)}
        >
          <p>
            As of {selected.as_of}. Expires {selected.expires_at}.
          </p>
          <Evidence value={selected.facts} />
          <div className={ui.notice}>
            {selected.vetoes.length
              ? selected.vetoes.map((v) => <p key={v}>◇ {v}</p>)
              : "Evidence gate passed; this is still a research proposal."}
          </div>
          {selected.evidence.map((e, i) => (
            <div key={i} className="border-b border-line py-3 text-caption">
              <p>
                {display(e.id)} · {display(e.headline ?? e.source)}
              </p>
              <p>{display(e.at ?? e.published_at)}</p>
              <SourceLink url={e.url ?? e.source} />
            </div>
          ))}
          <p className="break-all text-xxs">
            Input {selected.input_hash}. News is untrusted evidence. No model
            may remove a veto or submit an order. Calendar coverage is
            independent of news coverage.
          </p>
        </Dialog>
      ) : null}
    </>
  );
}
