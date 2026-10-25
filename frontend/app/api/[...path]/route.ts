import { relay } from "@/lib/relay";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
type Context = { params: Promise<{ path: string[] }> };
export async function GET(request: Request, { params }: Context) {
  return relay(request, (await params).path);
}
export async function POST(request: Request, { params }: Context) {
  return relay(request, (await params).path);
}
