"use client";
import { AnimatePresence } from "motion/react";
import * as m from "motion/react-m";
import { ui } from "@/lib/ui";
import { utc } from "@/lib/format";
import { useDashboard } from "../provider";
import { useMotionSettings } from "../motion";
export function ConnectionBanner() {
  const { snapshot } = useDashboard();
  const state = snapshot.state;
  const { reduced } = useMotionSettings();
  return (
    <AnimatePresence initial={false}>
      {!snapshot.connected ? (
        <m.div
          key="connection"
          initial={{ opacity: reduced ? 1 : 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          role="status"
          className={`${ui.notice} border-status-degraded/30`}
        >
          <strong>
            {state && snapshot.seeded
              ? "Server snapshot · connecting live stream"
              : state
                ? "Service connection lost · retained observation only"
                : snapshot.error
                  ? "Local service unavailable"
                  : "Connecting to local service"}
          </strong>
          <p>
            {state && snapshot.seeded
              ? `Showing server readback from ${utc(state.server_time)}. Actions unlock after the live connection confirms.`
              : (snapshot.error ??
                "Reading account and ledger state. No balances or prices are assumed.")}
          </p>
        </m.div>
      ) : null}
    </AnimatePresence>
  );
}
