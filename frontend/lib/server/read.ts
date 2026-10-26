import "server-only";
import { headers } from "next/headers";
import { unstable_rethrow } from "next/navigation";
import type { z } from "zod";
import { upstreamFetch } from "../upstream";
import { ApiError, parseResponse } from "../response";
import { allowedHost, serviceUrl, type Service } from "./services";

export type ReadResult<T> =
  | { data: T; error?: undefined }
  | { data?: undefined; error: string };

/** Server-side GET through the relay's service boundary; service failures become results, never throws. */
export async function read<T>(
  service: Service,
  path: string,
  schema: z.ZodType<T>,
  options: { timeout: number },
  fetcher: typeof fetch = upstreamFetch,
): Promise<ReadResult<T>> {
  // Request-time API outside the try: Next's dynamic-rendering signal must propagate.
  const host = (await headers()).get("host");
  if (!allowedHost(host)) return { error: "Invalid dashboard host" };
  const timeout = AbortSignal.timeout(options.timeout);
  try {
    const upstream = serviceUrl(service, path);
    if (!upstream) return { error: "Invalid service configuration" };
    const response = await fetcher(upstream, {
      method: "GET",
      headers: { host },
      cache: "no-store",
      redirect: "manual",
      signal: timeout,
    });
    return { data: await parseResponse(response, schema) };
  } catch (error) {
    unstable_rethrow(error);
    // Checked first: a timeout while reading the body surfaces from the parser as invalid JSON.
    if (timeout.aborted) return { error: "Service request timed out." };
    if (error instanceof ApiError) return { error: error.message };
    // The relay's 503 detail, which the browser displayed before server reads.
    return { error: "Service unavailable or request timed out." };
  }
}
