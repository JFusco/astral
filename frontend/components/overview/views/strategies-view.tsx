import { ui } from "@/lib/ui";
import { StrategyCounts } from "./strategy-counts";
export function StrategiesView() {
  return (
    <>
      <p>
        ATR14, trend and prior-20-bar breakouts are reproducible research
        hypotheses, not validated trading edges. Automatic entries remain
        disabled.
      </p>
      <StrategyCounts />
      <p className={ui.notice}>
        Stop and target levels are planning references; no protective order is
        placed. Server limits include $1,000 planned order, $100 market order,
        50% gross exposure and a shared 0.5% unprotected full-value risk budget.
        Sizing and every veto remain server decisions. Learning promotion is
        disabled.
      </p>
    </>
  );
}
