import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { z } from "zod";
import { redirect } from "next/navigation";
import { read } from "../lib/server/read";
let host: string | null = "127.0.0.1:3000";
vi.mock("next/headers", () => ({
  headers: async () => new Headers(host ? { host } : {}),
}));
const schema = z.object({ as_of: z.string() });
const respond = (body: unknown, status = 200) =>
  vi.fn<typeof fetch>(async () => Response.json(body, { status }));
beforeEach(() => {
  host = "127.0.0.1:3000";
});
afterEach(() => vi.unstubAllEnvs());
describe("server read", () => {
  it("reads a validated report through the configured origin with the browser Host", async () => {
    vi.stubEnv("ASTRAL_API_ORIGIN", "http://application:8766");
    const fetcher = respond({ as_of: "2026-01-02" });
    expect(
      await read(
        "application",
        "accounting/report",
        schema,
        { timeout: 1000 },
        fetcher,
      ),
    ).toEqual({ data: { as_of: "2026-01-02" } });
    const [url, init] = fetcher.mock.calls[0];
    expect(String(url)).toBe("http://application:8766/api/accounting/report");
    expect(init).toMatchObject({ method: "GET", cache: "no-store" });
    expect(new Headers(init?.headers).get("host")).toBe("127.0.0.1:3000");
  });
  it("rejects a disallowed Host without contacting a service", async () => {
    host = "evil.example";
    const fetcher = respond({ as_of: "x" });
    expect(
      await read("application", "state", schema, { timeout: 1000 }, fetcher),
    ).toEqual({
      error: "Invalid dashboard host",
    });
    host = null;
    expect(
      await read("application", "state", schema, { timeout: 1000 }, fetcher),
    ).toEqual({
      error: "Invalid dashboard host",
    });
    expect(fetcher).not.toHaveBeenCalled();
  });
  it("rejects an unusable service configuration without contacting a service", async () => {
    vi.stubEnv("ASTRAL_API_ORIGIN", "https://application:8766");
    const fetcher = respond({ as_of: "x" });
    expect(
      await read("application", "state", schema, { timeout: 1000 }, fetcher),
    ).toEqual({
      error: "Invalid service configuration",
    });
    expect(fetcher).not.toHaveBeenCalled();
  });
  it("returns the browser's timeout message when the service does not answer", async () => {
    const fetcher = vi.fn<typeof fetch>(
      (_, init) =>
        new Promise((_, reject) =>
          init?.signal?.addEventListener("abort", () =>
            reject(init.signal?.reason),
          ),
        ),
    );
    expect(
      await read("application", "state", schema, { timeout: 20 }, fetcher),
    ).toEqual({
      error: "Service request timed out.",
    });
  });
  it("reports a timeout while the response body is still arriving as a timeout", async () => {
    const fetcher = vi.fn<typeof fetch>(
      async (_, init) =>
        new Response(
          new ReadableStream({
            start(body) {
              body.enqueue(new TextEncoder().encode('{"as_of":'));
              init?.signal?.addEventListener("abort", () =>
                body.error(init.signal?.reason),
              );
            },
          }),
        ),
    );
    expect(
      await read("application", "state", schema, { timeout: 20 }, fetcher),
    ).toEqual({ error: "Service request timed out." });
  });
  it("keeps service rejection details and falls back to the status", async () => {
    expect(
      await read(
        "application",
        "state",
        schema,
        { timeout: 1000 },
        respond({ detail: "Busy" }, 409),
      ),
    ).toEqual({ error: "Busy" });
    expect(
      await read(
        "application",
        "state",
        schema,
        { timeout: 1000 },
        respond({}, 502),
      ),
    ).toEqual({ error: "Service returned 502" });
  });
  it("returns an unavailable report's reason", async () => {
    expect(
      await read(
        "application",
        "accounting/report",
        schema,
        { timeout: 1000 },
        respond({ status: "unavailable", reason: "No saved report" }),
      ),
    ).toEqual({ error: "No saved report" });
  });
  it("uses the browser's messages for invalid JSON and contract mismatches", async () => {
    const invalid = vi.fn<typeof fetch>(async () => new Response("<html>"));
    expect(
      await read("application", "state", schema, { timeout: 1000 }, invalid),
    ).toEqual({
      error: "Service returned invalid JSON",
    });
    expect(
      await read(
        "application",
        "state",
        schema,
        { timeout: 1000 },
        respond({ as_of: 1 }),
      ),
    ).toEqual({
      error: "Service response did not match the dashboard contract",
    });
  });
  it("turns a transport failure into the relay's unavailable message", async () => {
    const fetcher = vi.fn<typeof fetch>(async () => {
      throw new Error("ECONNREFUSED");
    });
    expect(
      await read("application", "state", schema, { timeout: 1000 }, fetcher),
    ).toEqual({
      error: "Service unavailable or request timed out.",
    });
  });
  it("rethrows framework control flow instead of converting it", async () => {
    const fetcher = vi.fn<typeof fetch>(async () => redirect("/elsewhere"));
    await expect(
      read("application", "state", schema, { timeout: 1000 }, fetcher),
    ).rejects.toMatchObject({
      digest: expect.stringContaining("NEXT_REDIRECT"),
    });
  });
});
