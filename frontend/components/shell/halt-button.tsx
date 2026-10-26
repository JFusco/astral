"use client";
import { useState } from "react";
import { z } from "zod";
import { useDashboard } from "../provider";
import { api, errorMessage } from "@/lib/api";
import { ui } from "@/lib/ui";
export function HaltButton() {
  const { snapshot, connection } = useDashboard();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const state = snapshot.state;
  async function halt() {
    if (pending || !state || !snapshot.connected) return;
    setPending(true);
    setError("");
    try {
      await api("/api/halt", z.object({ halted: z.boolean() }), {
        body: { halted: !state.halted },
      });
      await connection.refresh();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setPending(false);
    }
  }
  return (
    <>
      <button
        onClick={halt}
        disabled={!snapshot.connected || pending}
        className={`${ui.button} text-status-degraded`}
      >
        {pending
          ? "Saving…"
          : state?.halted
            ? "◇ Resume entries"
            : "◈ Halt entries"}
      </button>
      {error ? (
        <span role="alert" className="w-full max-w-lg text-status-down">
          {error}
        </span>
      ) : null}
    </>
  );
}
