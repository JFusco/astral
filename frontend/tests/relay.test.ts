import { afterEach, describe, expect, it, vi } from "vitest";
import { gunzipSync } from "node:zlib";
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
describe("response compression", () => {
  const large = {
    rows: Array.from({ length: 200 }, (_, i) => ({
      i,
      at: "2026-10-26T00:00:00Z",
    })),
  };
  const upstream = (body: unknown) =>
    vi.fn<typeof fetch>(async () => Response.json(body));
  it("gzips large GET reads the browser accepts and decodes to the same JSON", async () => {
    const response = await relay(
      request("state", "GET", { "accept-encoding": "gzip, deflate, br" }),
      ["state"],
      upstream(large),
    );
    expect(response.headers.get("content-encoding")).toBe("gzip");
    expect(response.headers.get("vary")).toBe("Accept-Encoding");
    expect(response.headers.get("cache-control")).toBe("no-store");
    const body = gunzipSync(Buffer.from(await response.arrayBuffer()));
    expect(JSON.parse(body.toString())).toEqual(large);
  });
  it("sends raw bytes when gzip is not accepted or the body is small", async () => {
    for (const [encoding, body] of [
      [undefined, large],
      ["identity", large],
      ["gzip;q=0, br", large],
      ["gzip", { ok: true }],
    ] as const) {
      const response = await relay(
        request(
          "state",
          "GET",
          encoding ? { "accept-encoding": encoding } : {},
        ),
        ["state"],
        upstream(body),
      );
      expect(response.headers.get("content-encoding"), encoding).toBeNull();
      expect(await response.json(), encoding).toEqual(body);
    }
  });
  it("never compresses the event stream", async () => {
    const bytes = new TextEncoder().encode("x".repeat(4096));
    const fetcher = vi.fn<typeof fetch>(
      async () =>
        new Response(bytes, {
          headers: { "content-type": "text/event-stream" },
        }),
    );
    const response = await relay(
      request("events", "GET", { "accept-encoding": "gzip" }),
      ["events"],
      fetcher,
    );
    expect(response.headers.get("content-encoding")).toBeNull();
    expect(new Uint8Array(await response.arrayBuffer())).toEqual(bytes);
  });
  it("never compresses mutation responses", async () => {
    const response = await relay(
      request("orders", "POST", {
        "x-astral-intent": "paper-only",
        "content-type": "application/json",
        "accept-encoding": "gzip",
      }),
      ["orders"],
      upstream(large),
    );
    expect(response.headers.get("content-encoding")).toBeNull();
    expect(response.headers.get("vary")).toBeNull();
    expect(await response.json()).toEqual(large);
  });
});
describe("upstream transport", () => {
  it("opens a fresh connection per relay request instead of reusing idle sockets", async () => {
    const { createServer } = await import("node:http");
    const { upstreamFetch } = await import("../lib/upstream");
    let connections = 0;
    const headers: (string | undefined)[] = [];
    const server = createServer((req, res) => {
      headers.push(req.headers.connection);
      res.end("{}");
    });
    server.on("connection", () => connections++);
    await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
    const { port } = server.address() as { port: number };
    try {
      for (let i = 0; i < 3; i++)
        await (await upstreamFetch(`http://127.0.0.1:${port}/api/health/state`)).arrayBuffer();
      expect(connections).toBe(3);
      expect(headers).toEqual(["close", "close", "close"]);
    } finally {
      server.closeAllConnections();
      await new Promise((resolve) => server.close(resolve));
    }
  });
});
