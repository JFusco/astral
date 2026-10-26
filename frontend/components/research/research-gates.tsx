"use client";
import { object, records } from "@/lib/data";
import { display } from "@/lib/format";
import { useDashboard } from "../provider";
/** Discovery listings and BTC readiness gates; `open` shows retained evidence. */
export function ResearchGates({
  open,
}: {
  open: (title: string, value: unknown) => void;
}) {
  const s = useDashboard().snapshot.state;
  const gates = records(s?.readiness?.symbols).find((r) => r.symbol === "BTC");
  return (
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
              {records(s.crypto_universe.assets).length} crypto venue listings
              ↗
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
          {object(gates.depth).passed ? "validated" : "unverified / stale"} ·
          Liquidity {object(gates.liquidity).passed ? "passes" : "BLOCKED"} ·
          Events {display(object(gates.events).status)} ·{" "}
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
  );
}
