"use client";
import { useDashboard } from "../provider";
export function ModeBadge() {
  const { snapshot } = useDashboard();
  const state = snapshot.state;
  return (
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
  );
}
