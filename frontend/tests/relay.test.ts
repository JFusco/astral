import { afterEach, describe, expect, it, vi } from "vitest";
import { relay } from "../lib/relay";
const request = (
  path: string,
  method = "GET",
  headers: Record<string, string> = {},
) =>
  new Request(`http://127.0.0.1:3000/api/${path}`, {
    method,
    headers: { host: "127.0.0.1:3000", ...headers },
    ...(method === "POST" ? { body: "{}" } : {}),
  });
afterEach(() => vi.unstubAllEnvs());
describe("local API boundary", () => {
  it("rejects invalid host, foreign origin and missing intent before contacting the backend", async () => {
    const fetcher = vi.fn();
    expect(
      (await relay(request("orders", "POST"), ["orders"], fetcher)).status,
    ).toBe(403);
    expect(
      (
        await relay(
          request("orders", "POST", {
            "x-astral-intent": "paper-only",
            origin: "https://evil.example",
          }),
          ["orders"],
          fetcher,
        )
      ).status,
    ).toBe(403);
    expect(
      (
        await relay(
          request("state", "GET", {
            host: "evil.example",
            "x-forwarded-host": "127.0.0.1:3000",
          }),
          ["state"],
          fetcher,
        )
      ).status,
    ).toBe(400);
    expect(
      (
        await relay(
          request("orders", "POST", {
            "x-astral-intent": "paper-only",
            "sec-fetch-site": "cross-site",
          }),
          ["orders"],
          fetcher,
        )
      ).status,
    ).toBe(403);
    expect(fetcher).not.toHaveBeenCalled();
  });
  it("allows only exact paths and methods", async () => {
    const fetcher = vi.fn();
    for (const path of [
      ["unknown"],
      ["orders", "..", "cancel"],
      ["orders", "x%2fy", "cancel"],
      ["https:", "evil.example"],
    ])
      expect((await relay(request("state"), path, fetcher)).status).toBe(404);
    expect(
      (
        await relay(
          request("health/state", "POST", { "x-astral-intent": "paper-only" }),
          ["health", "state"],
          fetcher,
        )
      ).status,
    ).toBe(404);
    expect(fetcher).not.toHaveBeenCalled();
  });
  it("preserves the browser Host and Origin across a different internal destination and retains backend errors", async () => {
    vi.stubEnv("ASTRAL_API_ORIGIN", "http://application:8766");
    const fetcher = vi.fn<typeof fetch>(async () =>
      Response.json({ detail: "Loss circuit latched" }, { status: 409 }),
    );
    const response = await relay(
      request("orders", "POST", {
        "x-astral-intent": "paper-only",
        "content-type": "application/json",
        origin: "http://127.0.0.1:3000",
      }),
      ["orders"],
      fetcher,
    );
    expect(response.status).toBe(409);
    expect(response.headers.get("cache-control")).toBe("no-store");
    expect(await response.json()).toEqual({ detail: "Loss circuit latched" });
    const [url, options] = fetcher.mock.calls[0] as unknown as [
      URL,
      RequestInit,
    ];
    expect(url.href).toBe("http://application:8766/api/orders");
    expect(new Headers(options.headers).get("host")).toBe("127.0.0.1:3000");
    expect(new Headers(options.headers).get("origin")).toBe(
      "http://127.0.0.1:3000",
    );
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
  it("routes independent services without exposing upstream selection to the caller", async () => {
    const fetcher = vi.fn<typeof fetch>(async () => Response.json({}));
    await relay(request("health/state"), ["health", "state"], fetcher);
    expect(String(fetcher.mock.calls[0][0])).toBe(
      "http://127.0.0.1:8769/api/health/state",
    );
    await relay(request("intelligence"), ["intelligence"], fetcher);
    expect(String(fetcher.mock.calls[1][0])).toBe(
      "http://127.0.0.1:8768/api/intelligence",
    );
  });
  it("streams unchanged SSE bytes and releases the upstream on cancellation", async () => {
    const bytes = new TextEncoder().encode(
      'id: 42\nevent: ledger\ndata: {"type":"fill"}\n\n',
    );
    const cancel = vi.fn();
    const stream = new ReadableStream<Uint8Array>({
      start(c) {
        c.enqueue(bytes);
      },
      cancel,
    });
    const fetcher = vi.fn<typeof fetch>(
      async () =>
        new Response(stream, {
          headers: { "content-type": "text/event-stream" },
        }),
    );
    const response = await relay(
      request("events", "GET", { "last-event-id": "41" }),
      ["events"],
      fetcher,
    );
    const reader = response.body!.getReader();
    expect((await reader.read()).value).toEqual(bytes);
    await reader.cancel();
    expect(cancel).toHaveBeenCalledTimes(1);
    const options = (fetcher.mock.calls[0] as unknown as [URL, RequestInit])[1];
    expect(new Headers(options.headers).get("last-event-id")).toBe("41");
    expect(options.signal?.aborted).toBe(true);
  });
});
