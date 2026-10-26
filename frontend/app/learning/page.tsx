import { learningSchema } from "@/lib/contracts";
import { read } from "@/lib/server/read";
import { ReportFrame } from "@/components/reports/report-frame";
import { LearningContent } from "@/components/reports/learning-content";
export const metadata = { title: "Learning" };
export const dynamic = "force-dynamic";
export default async function Page() {
  const report = await read("application", "learning/report", learningSchema, {
    timeout: 5000,
  });
  return (
    <ReportFrame
      title="Learning"
      subtitle="Offline evidence readiness and checks of recorded model research."
      asOf={report.data?.as_of}
      mode={report.data?.source_mode}
      error={report.error ?? null}
      empty="No verified learning report is available. Outcome readiness remains unknown."
    >
      {report.data ? <LearningContent r={report.data} /> : null}
    </ReportFrame>
  );
}
