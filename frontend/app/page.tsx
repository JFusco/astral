import { OverviewPage } from "@/components/overview/overview-page";
export default async function Page({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const query = await searchParams;
  return (
    <OverviewPage view={typeof query.view === "string" ? query.view : null} />
  );
}
