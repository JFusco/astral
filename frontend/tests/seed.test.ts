import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { loadSeed } from "../lib/server/seed";
import { dashboard, health } from "./fixtures";
vi.mock("next/headers", () => ({
  headers: async () => new Headers({ host: "127.0.0.1:3000" }),
}));
const now = Date.parse("2026-10-26T12:00:00.000Z");
const at = (offset: number) => new Date(now + offset).toISOString();
const intelligence = { sources: [], items: [] };
/** Routes by service path; `healthAsOf` sets the health response's as_of. */
const services = (healthAsOf: string, failing: string[] = []) =>
  vi.fn<typeof fetch>(async (input) => {
    const path = new URL(String(input)).pathname;
    if (failing.includes(path)) throw new Error("ECONNREFUSED");
    return Response.json(
      path === "/api/state"
        ? dashboard()
        : path === "/api/health/state"
          ? health(healthAsOf)
          : intelligence,
    );
  });
beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(now);
});
afterEach(() => vi.useRealTimers());
describe("server seed", () => {
  it("reads all three services with the captured server time", async () => {
    const fetcher = services(at(0));
    const seed = await loadSeed(fetcher);
    expect(seed.now).toBe(now);
    expect(seed.state?.mode).toBe("simulator");
    expect(seed.health?.as_of).toBe(at(0));
    expect(seed.intelligence).toEqual(intelligence);
    expect(fetcher).toHaveBeenCalledTimes(3);
  });
  it("keeps the services that answered when another fails", async () => {
    const seed = await loadSeed(services(at(0), ["/api/state"]));
    expect(seed.state).toBeNull();
    expect(seed.health).not.toBeNull();
    expect(seed.intelligence).not.toBeNull();
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
  it("resolves with three empty fields when every service fails", async () => {
    await expect(
      loadSeed(
        services(at(0), [
          "/api/state",
          "/api/health/state",
          "/api/intelligence",
        ]),
      ),
    ).resolves.toEqual({ now, state: null, health: null, intelligence: null });
  });
});
