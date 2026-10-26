"use client";
import { object } from "@/lib/data";
import { display } from "@/lib/format";
import { useDashboard } from "../provider";
/** Registered experiments and replays; `open` shows retained evidence. */
export function ResearchExperiments({
  open,
}: {
  open: (title: string, value: unknown) => void;
}) {
  const s = useDashboard().snapshot.state;
  const experiment = s?.experiment,
    replay = s?.portfolio_replay,
    liquidity = s?.liquidity_experiment;
  return (
    <div className="space-y-4 border-t border-line p-5 text-caption text-muted">
      <p>
        {experiment ? (
          <>
            {display(experiment.id)} ·{" "}
            {experiment.code_matches ? "Code verified" : "CODE DRIFT / BLOCKED"}{" "}
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
            {replay.code_matches ? "Code verified" : "CODE DRIFT / REVIEW"} ·{" "}
            {display(replay.synthetic_scenarios)} synthetic scenarios ·{" "}
            {display(object(replay.observed_coverage).quotes)} quotes /{" "}
            {display(object(replay.observed).fill_count)} hypothetical fills.{" "}
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
            {display(liquidity.status)} · {display(liquidity.samples)} snapshots
            · No orders, fills or profit inferred.{" "}
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
  );
}
