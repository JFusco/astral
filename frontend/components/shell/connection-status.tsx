"use client";
import { useDashboard } from "../provider";
export function ConnectionStatus() {
  const { snapshot } = useDashboard();
  const state = snapshot.state;
  return (
    <span
      role="status"
      className={
        snapshot.connected ? "text-status-healthy" : "text-status-unknown"
      }
    >
      {snapshot.connected
        ? state?.mode === "simulator"
          ? "SIMULATOR / SERVER STREAM"
          : state?.connected
            ? "ALPACA / PAPER STREAM"
            : "ALPACA / NOT CONNECTED"
        : snapshot.seeded
          ? "SERVER SNAPSHOT / CONNECTING"
          : state
            ? "BACKEND DISCONNECTED"
            : snapshot.error
              ? "SERVICE UNAVAILABLE"
              : "CONNECTING TO SERVICE"}
    </span>
  );
}
