import { api, errorMessage } from "./api";
import {
  dashboardSchema,
  fillSchema,
  healthSchema,
  intelligenceSchema,
  type Dashboard,
  type Fill,
  type Health,
  type Intelligence,
  type OrderIntent,
} from "./contracts";

export type Snapshot = {
  state: Dashboard | null;
  health: Health | null;
  intelligence: Intelligence | null;
  connected: boolean;
  healthConnected: boolean;
  healthLoading: boolean;
  intelligenceConnected: boolean;
  error: string | null;
  now: number;
  fill: Fill | null;
  fillAt: number;
  uncertainIntent: OrderIntent | null;
};
const empty: Snapshot = {
  state: null,
  health: null,
  intelligence: null,
  connected: false,
  healthConnected: false,
  healthLoading: true,
  intelligenceConnected: false,
  error: null,
  now: 0,
  fill: null,
  fillAt: 0,
  uncertainIntent: null,
};
export const serverSnapshot = () => empty;

/** One owner per mounted application. All subscriptions, timers and requests stop together. */
export class Connection {
  private snapshot: Snapshot = empty;
  private listeners = new Set<() => void>();
  private source: EventSource | null = null;
  private controller: AbortController | null = null;
  private cursor = 0;
  private bootstrapped = false;
  private seen = new Set<string>();
  private lastMessage = 0;
  private healthReceived = 0;
  private pendingState = false;
  private generation = 0;
  subscribe = (listener: () => void) => {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  };
  getSnapshot = () => this.snapshot;
  setUncertainIntent = (uncertainIntent: OrderIntent | null) =>
    this.update({ uncertainIntent });
  private update(patch: Partial<Snapshot>) {
    this.snapshot = { ...this.snapshot, ...patch };
    this.listeners.forEach((fn) => fn());
  }
  async refresh() {
    if (this.pendingState || !this.controller) return;
    this.pendingState = true;
    const generation = this.generation;
    try {
      const state = await api("/api/state", dashboardSchema, {
        signal: this.controller.signal,
        timeout: 3000,
      });
      if (generation !== this.generation) return;
      if (!this.bootstrapped) {
        this.cursor = state.sequence;
        state.fills.forEach((f) => this.seen.add(f.id));
        this.bootstrapped = true;
      }
      this.accept(state);
      if (!this.source) this.openStream();
    } catch (error) {
      if (generation === this.generation && !this.controller?.signal.aborted)
        this.update({ connected: false, error: errorMessage(error) });
    } finally {
      if (generation === this.generation) this.pendingState = false;
    }
  }
  private accept(state: Dashboard) {
    const current = this.snapshot.state;
    if (current) {
      const time = Date.parse(state.server_time),
        currentTime = Date.parse(current.server_time);
      if (
        time < currentTime ||
        (time === currentTime && state.sequence < current.sequence)
      )
        return;
    }
    this.lastMessage = Date.now();
    this.update({ state, connected: true, error: null });
  }
  private openStream() {
    const source = new EventSource(`/api/events?after=${this.cursor}`);
    this.source = source;
    source.addEventListener("state", (event) => {
      try {
        this.accept(
          dashboardSchema.parse(JSON.parse((event as MessageEvent).data)),
        );
      } catch {
        this.update({
          connected: false,
          error: "Invalid dashboard event received",
        });
      }
    });
    source.addEventListener("ledger", (event) => {
      const message = event as MessageEvent;
      try {
        const row: unknown = JSON.parse(message.data);
        const id = Number(message.lastEventId);
        if (
          !Number.isSafeInteger(id) ||
          id <= 0 ||
          !row ||
          typeof row !== "object" ||
          !("type" in row)
        )
          throw new Error("Invalid ledger event");
        if (id <= this.cursor) return;
        if (row.type === "fill") {
          const fill = fillSchema.parse("payload" in row ? row.payload : null);
          if (!this.seen.has(fill.id)) {
            this.seen.add(fill.id);
            this.update({ fill, fillAt: Date.now() });
          }
        }
        this.cursor = id;
        this.lastMessage = Date.now();
      } catch {
        this.update({
          connected: false,
          error: "Invalid ledger event received",
        });
      }
    });
    source.onerror = () =>
      this.update({
        connected: false,
        error: "Stream disconnected; reconnecting",
      });
  }
  start() {
    this.generation++;
    this.controller = new AbortController();
    const generation = this.generation;
    const signal = this.controller.signal;
    const pollHealth = async () => {
      try {
        const health = await api("/api/health/state", healthSchema, {
          signal,
          timeout: 4000,
        });
        const age = Date.now() - Date.parse(health.as_of);
        if (!Number.isFinite(age) || age < -5000 || age > 15000)
          throw new Error("Stale health response");
        if (generation === this.generation) {
          this.healthReceived = Date.now();
          this.update({ health, healthConnected: true, healthLoading: false });
        }
      } catch {
        if (generation === this.generation && !signal.aborted)
          this.update({ healthConnected: false, healthLoading: false });
      }
    };
    const pollIntelligence = async () => {
      try {
        const intelligence = await api(
          "/api/intelligence",
          intelligenceSchema,
          { signal, timeout: 5000 },
        );
        if (generation === this.generation)
          this.update({ intelligence, intelligenceConnected: true });
      } catch {
        if (generation === this.generation && !signal.aborted)
          this.update({ intelligenceConnected: false });
      }
    };
    // Each poll finishes before another of the same kind starts, including after visibility changes.
    let healthPending = false,
      intelligencePending = false;
    const health = async () => {
      if (healthPending) return;
      healthPending = true;
      try {
        await pollHealth();
      } finally {
        healthPending = false;
      }
    };
    const intelligence = async () => {
      if (intelligencePending) return;
      intelligencePending = true;
      try {
        await pollIntelligence();
      } finally {
        intelligencePending = false;
      }
    };
    void this.refresh();
    void health();
    void intelligence();
    const timers = [
      setInterval(() => void health(), 5000),
      setInterval(() => void intelligence(), 30000),
      setInterval(() => {
        const now = Date.now();
        const patch: Partial<Snapshot> = { now };
        if (now - this.lastMessage > 8000) {
          patch.connected = false;
          if (this.source) {
            this.source.close();
            this.source = null;
          }
          void this.refresh();
        }
        if (now - this.healthReceived > 15000) patch.healthConnected = false;
        this.update(patch);
      }, 1000),
    ];
    const visible = () => {
      if (!document.hidden) {
        void health();
        void intelligence();
        if (!this.snapshot.connected) void this.refresh();
      }
    };
    document.addEventListener("visibilitychange", visible);
    return () => {
      this.generation++;
      timers.forEach(clearInterval);
      document.removeEventListener("visibilitychange", visible);
      this.source?.close();
      this.source = null;
      this.controller?.abort();
      this.controller = null;
      this.pendingState = false;
    };
  }
}
export function healthIsLive(snapshot: Snapshot) {
  const { health, healthConnected, now } = snapshot;
  const age = health ? now - Date.parse(health.checked_at) : Infinity;
  return !!(
    healthConnected &&
    health?.heartbeat_live &&
    age >= -5000 &&
    age <= 30000
  );
}
export function quoteIsFresh(
  state: Dashboard | null,
  symbol: string,
  connected: boolean,
  now: number,
) {
  const asset = state?.assets.find((a) => a.symbol === symbol);
  const age = asset?.quote.at ? now - Date.parse(asset.quote.at) : Infinity;
  return !!(
    connected &&
    state?.connected &&
    asset?.quote_fresh &&
    age >= 0 &&
    age <= 15000
  );
}
