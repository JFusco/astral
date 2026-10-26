import { promisify } from "node:util";
import { gzip } from "node:zlib";
import { upstreamFetch } from "./upstream";
import { allowedHost, serviceUrl, type Service } from "./server/services";
const getPaths = new Map<string, Service>([
  ["state", "application"],
  ["health", "application"],
  ["health-inputs", "application"],
  ["events", "application"],
  ["accounting/report", "application"],
  ["learning/report", "application"],
  ["health/state", "health"],
  ["intelligence", "intelligence"],
]);
const postPaths = new Set([
  "orders",
  "halt",
  "reconcile",
  "risk/plan",
  "risk/shadow",
  "exits",
  "research/run",
]);
const responseHeaders = {
  "Cache-Control": "no-store",
  "X-Content-Type-Options": "nosniff",
};
const compress = promisify(gzip);
/** Smaller bodies gain little and cost a gzip header plus CPU. */
const compressFrom = 1024;
function acceptsGzip(header: string | null) {
  return (header ?? "").split(",").some((entry) => {
    const [coding, ...params] = entry.trim().toLowerCase().split(";");
    return (
      coding === "gzip" && !params.some((p) => /^\s*q=0(\.0*)?\s*$/.test(p))
    );
  });
}
function reject(detail: string, status: number) {
  return Response.json({ detail }, { status, headers: responseHeaders });
}

export async function relay(
  request: Request,
  segments: string[],
  fetcher: typeof fetch = upstreamFetch,
) {
  const host = request.headers.get("host");
  if (!allowedHost(host)) return reject("Invalid dashboard host", 400);
  const expected = `http://${host}`;
  if (segments.some((s) => !s || s === "." || s === ".." || /[\\/%?#]/.test(s)))
    return reject("Unknown API path", 404);
  const path = segments.join("/");
  let service: Service | undefined;
  if (request.method === "GET") service = getPaths.get(path);
  else if (
    request.method === "POST" &&
    (postPaths.has(path) ||
      /^orders\/astral-[a-zA-Z0-9-]{8,40}\/cancel$/.test(path))
  )
    service = "application";
  if (!service) return reject("Unsupported API path or method", 404);
  if (request.method === "POST") {
    if (
      request.headers.get("x-astral-intent") !== "paper-only" ||
      (request.headers.has("origin") &&
        request.headers.get("origin") !== expected) ||
      request.headers.get("sec-fetch-site") === "cross-site"
    )
      return reject("Same-origin paper intent header required", 403);
    if (!request.headers.get("content-type")?.startsWith("application/json"))
      return reject("JSON required", 415);
  }
  const upstream = serviceUrl(service, path);
  if (!upstream) return reject("Invalid service configuration", 503);
  upstream.search = new URL(request.url).search;
  const headers = new Headers({ host: host });
  for (const key of [
    "origin",
    "sec-fetch-site",
    "x-astral-intent",
    "content-type",
    "last-event-id",
  ]) {
    const value = request.headers.get(key);
    if (value !== null) headers.set(key, value);
  }
  const controller = new AbortController();
  const abort = () => controller.abort();
  request.signal.addEventListener("abort", abort, { once: true });
  if (request.signal.aborted) abort();
  const timer = setTimeout(abort, 15000);
  try {
    const body = request.method === "POST" ? await request.text() : undefined;
    const response = await fetcher(upstream, {
      method: request.method,
      headers,
      body,
      cache: "no-store",
      redirect: "manual",
      signal: controller.signal,
    });
    if (path === "events" && response.ok) {
      clearTimeout(timer); // SSE has an idle watchdog in the browser, not a total request timeout.
      if (
        !response.headers
          .get("content-type")
          ?.startsWith("text/event-stream") ||
        !response.body
      )
        throw new Error("Invalid event stream");
      const reader = response.body.getReader();
      const cleanup = () => {
        clearTimeout(timer);
        request.signal.removeEventListener("abort", abort);
      };
      const stream = new ReadableStream<Uint8Array>({
        async pull(out) {
          try {
            const next = await reader.read();
            if (next.done) {
              cleanup();
              out.close();
            } else out.enqueue(next.value);
          } catch (e) {
            cleanup();
            out.error(e);
          }
        },
        async cancel() {
          abort();
          cleanup();
          await reader.cancel().catch(() => {});
        },
      });
      return new Response(stream, {
        status: response.status,
        headers: {
          ...responseHeaders,
          "Content-Type": "text/event-stream",
          "X-Accel-Buffering": "no",
        },
      });
    }
    const payload = await response.arrayBuffer();
    clearTimeout(timer);
    request.signal.removeEventListener("abort", abort);
    const replyHeaders = new Headers({
      ...responseHeaders,
      "Content-Type":
        response.headers.get("content-type") ?? "application/json",
    });
    // Next compresses pages but not route handlers, and the backend sends JSON uncompressed.
    const gzipped =
      request.method === "GET" &&
      payload.byteLength >= compressFrom &&
      acceptsGzip(request.headers.get("accept-encoding"));
    if (request.method === "GET") replyHeaders.set("Vary", "Accept-Encoding");
    if (gzipped) replyHeaders.set("Content-Encoding", "gzip");
    return new Response(
      gzipped ? new Uint8Array(await compress(payload)) : payload,
      { status: response.status, headers: replyHeaders },
    );
  } catch {
    clearTimeout(timer);
    request.signal.removeEventListener("abort", abort);
    abort();
    return reject(
      request.method === "POST"
        ? "Service unavailable or request timed out; mutation outcome may be uncertain. Reconcile before taking further action."
        : "Service unavailable or request timed out.",
      503,
    );
  }
}
