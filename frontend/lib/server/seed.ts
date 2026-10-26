import "server-only";
import { headers } from "next/headers";
import { dashboardSchema, healthSchema } from "../contracts";
import type { Seed } from "../connection";
import { upstreamFetch } from "../upstream";
import { read } from "./read";

/** Only the data a route's first render displays; `path` is forwarded by proxy.ts. */
export function seedScope(path: string | null) {
  return { state: path === "/", health: path === "/" || path === "/health" };
}

/** Bounded first-render reads. Service failures become null fields; framework control flow propagates. */
export async function loadSeed(
  fetcher: typeof fetch = upstreamFetch,
): Promise<Seed> {
  const scope = seedScope((await headers()).get("x-astral-path"));
  const now = Date.now();
  const timeout = { timeout: 1500 };
  const [state, health] = await Promise.all([
    scope.state
      ? read("application", "state", dashboardSchema, timeout, fetcher)
      : null,
    scope.health
      ? read("health", "health/state", healthSchema, timeout, fetcher)
      : null,
  ]);
  // Same acceptance bounds as the browser's health poll, against the captured server clock.
  const age = health?.data ? now - Date.parse(health.data.as_of) : NaN;
  const fresh = Number.isFinite(age) && age >= -5000 && age <= 15000;
  return {
    now,
    state: state?.data ?? null,
    health: fresh ? (health?.data ?? null) : null,
  };
}
