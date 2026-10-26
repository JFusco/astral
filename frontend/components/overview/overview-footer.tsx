"use client";
import { ui } from "@/lib/ui";
import { utc } from "@/lib/format";
import { useDashboard } from "../provider";
export function OverviewFooter() {
  const { snapshot } = useDashboard();
  const state = snapshot.state;
  return (
    <footer className={ui.footer}>
      <span>
        {snapshot.connected ? "SERVER CONNECTED" : "WAITING FOR READBACK"} /{" "}
        {state?.sequence ?? "—"} durable events
      </span>
      <span>
        {state?.mode === "simulator"
          ? "PERSISTENT SIMULATOR · NO BROKER"
          : "ALPACA PAPER · NO LIVE TRADING"}{" "}
        / BALANCE AS OF {utc(state?.as_of)}
      </span>
    </footer>
  );
}
