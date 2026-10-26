"use client";
import { useState } from "react";
import { api, errorMessage } from "@/lib/api";
import { dashboardSchema } from "@/lib/contracts";
import { ui } from "@/lib/ui";
import { useDashboard } from "../../provider";
/** Workers, uncertain intent and the reconcile request. */
export function SystemView() {
  const { snapshot, connection } = useDashboard();
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

  return (
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
        Uptime {state?.uptime_seconds ?? "unknown"}s · Direct model API spend $0
        · Signed-in CLI usage has unknown USD cost · Hosting/data charges
        unknown.
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
  );
}
