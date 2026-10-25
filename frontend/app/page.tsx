import { Overview } from "@/components/overview";
export default async function Page({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const query = await searchParams;
  return <Overview view={typeof query.view === "string" ? query.view : null} />;
}
