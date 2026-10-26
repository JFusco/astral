import { NextResponse, type NextRequest } from "next/server";
/** Root layouts cannot read the pathname; the server seed scope needs it. Overwrites any client value. */
export function proxy(request: NextRequest) {
  const headers = new Headers(request.headers);
  headers.set("x-astral-path", request.nextUrl.pathname);
  return NextResponse.next({ request: { headers } });
}
export const config = {
  matcher: ["/((?!api|_next/static|_next/image|.*\\..*).*)"],
};
