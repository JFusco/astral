"use client";
import { useRef, useState } from "react";
import { z } from "zod";
import { api, errorMessage } from "@/lib/api";
import { money, quantity, utc } from "@/lib/format";
import { useDashboard } from "../provider";
import { Panel } from "../ui/panel";
import { Empty } from "../ui/empty";
export function ExecutionStream() {
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
