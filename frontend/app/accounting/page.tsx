import { accountingSchema } from "@/lib/contracts";
import { read } from "@/lib/server/read";
import { ReportFrame } from "@/components/reports/report-frame";
import { AccountingContent } from "@/components/reports/accounting-content";
export const metadata = { title: "Accounting" };
export const dynamic = "force-dynamic";
export default async function Page() {
  const report = await read(
    "application",
    "accounting/report",
    accountingSchema,
    { timeout: 5000 },
  );
  return (
    <ReportFrame
      title="Accounting"
      subtitle="Recorded costs, gross trade records and unresolved money evidence."
      asOf={report.data?.as_of}
      mode={report.data?.source_mode}
      error={report.error ?? null}
      empty="No verified accounting report is available. Net results remain unknown."
    >
      {report.data ? <AccountingContent r={report.data} /> : null}
    </ReportFrame>
  );
}
