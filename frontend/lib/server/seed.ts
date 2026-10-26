import "server-only";
import {
  dashboardSchema,
  healthSchema,
  intelligenceSchema,
} from "../contracts";
import type { Seed } from "../connection";
import { upstreamFetch } from "../upstream";
import { read } from "./read";

/** Parallel, bounded first-render reads. Service failures become null fields; framework control flow propagates. */
export async function loadSeed(
  fetcher: typeof fetch = upstreamFetch,
): Promise<Seed> {
  const now = Date.now();
  const timeout = { timeout: 1500 };
  const [state, health, intelligence] = await Promise.all([
    read("application", "state", dashboardSchema, timeout, fetcher),
    read("health", "health/state", healthSchema, timeout, fetcher),
    read("intelligence", "intelligence", intelligenceSchema, timeout, fetcher),
  ]);
  // Same acceptance bounds as the browser's health poll, against the captured server clock.
  const age = health.data ? now - Date.parse(health.data.as_of) : NaN;
  const fresh = Number.isFinite(age) && age >= -5000 && age <= 15000;
  return {
    now,
    state: state.data ?? null,
    health: fresh ? (health.data ?? null) : null,
    intelligence: intelligence.data ?? null,
  };
}
