import type { Accounting } from "@/lib/contracts";
import { ui } from "@/lib/ui";
import { Reveal } from "../motion";
import { AccountingSummary } from "./accounting-summary";
import { AccountingRecords } from "./accounting-records";
import { AccountingCosts } from "./accounting-costs";
import { AccountingGross } from "./accounting-gross";
import { AccountingBoundaries } from "./accounting-boundaries";
export function AccountingContent({ r }: { r: Accounting }) {
  return (
    <Reveal>
      <AccountingSummary r={r} />
      <div className={ui.columns}>
        <AccountingRecords r={r} />
        <AccountingCosts r={r} />
      </div>
      <AccountingGross r={r} />
      <AccountingBoundaries r={r} />
    </Reveal>
  );
}
