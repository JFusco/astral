"use client";
import { useDashboard } from "../provider";
export function HealthFooterStatus() {
  const state = useDashboard().snapshot.health;
  return (
    <span>
      {state ? `Last checked ${state.checked_at}` : "Waiting for health data"}
    </span>
  );
}
