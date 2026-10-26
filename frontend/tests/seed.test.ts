import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { loadSeed, seedScope } from "../lib/server/seed";
import { dashboard, health } from "./fixtures";
let path: string | null = "/";
vi.mock("next/headers", () => ({
  headers: async () =>
    new Headers({
      host: "127.0.0.1:3000",
      ...(path === null ? {} : { "x-astral-path": path }),
    }),
}));
const now = Date.parse("2026-10-26T12:00:00.000Z");
const at = (offset: number) => new Date(now + offset).toISOString();
/** Routes by service path; `healthAsOf` sets the health response's as_of. */
const services = (healthAsOf: string, failing: string[] = []) =>
  vi.fn<typeof fetch>(async (input) => {
    const service = new URL(String(input)).pathname;
    if (failing.includes(service)) throw new Error("ECONNREFUSED");
    return Response.json(
      service === "/api/state" ? dashboard() : health(healthAsOf),
    );
  });
const fetched = (fetcher: ReturnType<typeof services>) =>
  fetcher.mock.calls.map(([input]) => new URL(String(input)).pathname).sort();
beforeEach(() => {
  path = "/";
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(now);
});
afterEach(() => vi.useRealTimers());
describe("seed scope", () => {
  it("seeds only the data each route's first render displays", () => {
    expect(seedScope("/")).toEqual({ state: true, health: true });
    expect(seedScope("/health")).toEqual({ state: false, health: true });
    for (const route of ["/accounting", "/learning", "/unknown", null])
      expect(seedScope(route), String(route)).toEqual({
        state: false,
        health: false,
      });
  });
  it("reads state and health for the Overview", async () => {
    const fetcher = services(at(0));
    const seed = await loadSeed(fetcher);
    expect(fetched(fetcher)).toEqual(["/api/health/state", "/api/state"]);
    expect(seed.now).toBe(now);
    expect(seed.state?.mode).toBe("simulator");
    expect(seed.health?.as_of).toBe(at(0));
  });
  it("reads only health for the Health page", async () => {
    path = "/health";
    const fetcher = services(at(0));
    const seed = await loadSeed(fetcher);
    expect(fetched(fetcher)).toEqual(["/api/health/state"]);
    expect(seed.state).toBeNull();
    expect(seed.health).not.toBeNull();
  });
  it("reads nothing for reports, unknown routes or a missing path", async () => {
    for (const route of ["/accounting", "/learning", "/unknown", null]) {
      path = route;
      const fetcher = services(at(0));
      await expect(loadSeed(fetcher), String(route)).resolves.toEqual({
        now,
        state: null,
        health: null,
      });
      expect(fetcher, String(route)).not.toHaveBeenCalled();
    }
  });
});
describe("server seed", () => {
  it("keeps the services that answered when another fails", async () => {
    const seed = await loadSeed(services(at(0), ["/api/state"]));
    expect(seed.state).toBeNull();
    expect(seed.health).not.toBeNull();
  });
  it("drops health outside the browser's -5 s to 15 s age bounds", async () => {
    for (const [offset, kept] of [
      [-16000, false],
      [-15000, true],
      [5000, true],
      [6000, false],
    ] as const)
      expect(
        (await loadSeed(services(at(offset)))).health !== null,
        `as_of ${offset} ms`,
      ).toBe(kept);
    expect((await loadSeed(services("not a time"))).health).toBeNull();
  });
  it("resolves with empty fields when every service fails", async () => {
    await expect(
      loadSeed(services(at(0), ["/api/state", "/api/health/state"])),
    ).resolves.toEqual({ now, state: null, health: null });
  });
});
