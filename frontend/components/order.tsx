"use client";
import { useRef, useState, type FormEvent } from "react";
import { z } from "zod";
import { api, ApiError, errorMessage } from "@/lib/api";
import { quoteIsFresh } from "@/lib/connection";
import type { OrderIntent } from "@/lib/contracts";
import { ui } from "@/lib/ui";
import { useDashboard } from "./provider";
import { Dialog } from "./dialog";
export function OrderDialog({
  symbol,
  side,
  onClose,
}: {
  symbol: string;
  side: "buy" | "sell";
  onClose: () => void;
}) {
  const { snapshot, connection } = useDashboard();
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const cached = useRef<OrderIntent | null>(null);
  const busy = useRef(false);
  const [intentId, setIntentId] = useState("");
  const [amount, setAmount] = useState("250");
  const [execution, setExecution] =
    useState<OrderIntent["execution"]>("bounded");
  const fresh = quoteIsFresh(
    snapshot.state,
    symbol,
    snapshot.connected,
    snapshot.now,
  );
  const allowed =
    fresh &&
    snapshot.state?.orders_enabled &&
    !snapshot.uncertainIntent &&
    (side === "sell" || !snapshot.state.halted);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy.current || submitted || !allowed) return;
    busy.current = true;
    setPending(true);
    setSubmitted(true);
    setMessage("Submitting one intent. Do not repeat this action.");
    cached.current ??= {
      client_order_id: "astral-" + crypto.randomUUID(),
      symbol,
      side,
      notional: Number(amount),
      execution,
      ttl_seconds: 60,
      strategy_id: "manual",
    };
    setIntentId(cached.current.client_order_id);
    connection.setUncertainIntent(cached.current);
    try {
      const order = await api("/api/orders", z.object({ status: z.string() }), {
        body: cached.current,
      });
      if (!["unknown", "submitting"].includes(order.status))
        connection.setUncertainIntent(null);
      setMessage(
        `Order ${order.status}. Fill effects follow confirmed readback.`,
      );
      await connection.refresh();
    } catch (e) {
      if (
        e instanceof ApiError &&
        e.kind === "rejected" &&
        e.status &&
        e.status < 500
      )
        connection.setUncertainIntent(null);
      setMessage(
        `${errorMessage(e)} No replacement intent will be submitted. Use System telemetry to reconcile.`,
      );
    } finally {
      busy.current = false;
      setPending(false);
    }
  }
  return (
    <Dialog
      title={`${side === "buy" ? "Buy" : "Sell"} ${symbol}`}
      eyebrow={
        snapshot.state?.mode === "simulator"
          ? "PERSISTENT SIMULATOR / SYNTHETIC FILL"
          : "ALPACA PAPER / NO LIVE MONEY"
      }
      onClose={onClose}
    >
      <p>
        The server checks quote freshness, session, cash, working orders and
        portfolio limits before submission.
      </p>
      <form onSubmit={submit} className="space-y-4">
        <label className="block text-caption">
          Maximum order amount (USD)
          <input
            className="mt-2 w-full rounded-lg border border-line bg-surface-raised px-4 py-3 text-body text-ink"
            type="number"
            min="1"
            max="1000"
            step="0.01"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            required
            disabled={submitted}
          />
        </label>
        <label className="block text-caption">
          Execution policy
          <select
            className="mt-2 w-full rounded-lg border border-line bg-surface-raised px-4 py-3 text-body text-ink"
            value={execution}
            onChange={(e) =>
              setExecution(e.target.value as OrderIntent["execution"])
            }
            disabled={submitted}
          >
            <option value="bounded">Marketable limit — bounded price</option>
            <option value="patient">Passive limit — wait, then expire</option>
            <option value="market">Market — price can move</option>
          </select>
        </label>
        <p className={ui.notice}>
          Quantity rounds down to the instrument increment. Limit orders expire
          after 60 seconds; cancellation must be confirmed.
        </p>
        <button
          type="submit"
          className={`${ui.button} w-full text-accent`}
          disabled={!allowed || pending || submitted}
        >
          {pending
            ? "Submitting…"
            : submitted
              ? "Intent submitted — check readback"
              : `Submit ${snapshot.state?.mode === "simulator" ? "simulated" : "paper"} ${side}`}
        </button>
        <p role="status" className="text-caption text-status-unknown">
          {message ||
            (!allowed
              ? "Fresh readback and server order access are required."
              : "")}
        </p>
        {intentId ? (
          <p className="break-all text-xxs text-faint">Intent {intentId}</p>
        ) : null}
      </form>
    </Dialog>
  );
}
