"use client";
import { useDashboard } from "../../provider";
import { Counts } from "../../ui/counts";
/** The live parts of the strategies view: observations and the loss circuit. */
export function StrategyCounts() {
  const state = useDashboard().snapshot.state;
  return (
    <Counts
      values={{
        swing:
          "SMA20 / SMA50 · 2 × ATR stop reference · 0.25% planned-loss budget",
        intraday:
          "SMA10 / SMA30 · 1.5 × ATR stop reference · 0.10% planned-loss budget",
        observations: state?.learning.observations,
        loss_circuit: state?.risk_policy.latched
          ? "Latched / review required"
          : "See current server policy",
      }}
    />
  );
}
