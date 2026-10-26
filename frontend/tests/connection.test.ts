import { afterEach, beforeEach, expect, it, vi } from "vitest";
import {
  Connection,
  quoteIsFresh,
  healthIsLive,
  type Seed,
} from "../lib/connection";
import { dashboard, health } from "./fixtures";
class Source extends EventTarget {
  static instances: Source[] = [];
  closed = false;
  onerror: (() => void) | null = null;
  constructor(public url: string) {
    super();
    Source.instances.push(this);
  }
  close() {
    this.closed = true;
  }
  send(type: string, data: unknown, id = "") {
    this.dispatchEvent(
      new MessageEvent(type, { data: JSON.stringify(data), lastEventId: id }),
    );
  }
}
let stop: (() => void) | undefined;
beforeEach(() => {
  vi.useFakeTimers();
  Source.instances = [];
  vi.stubGlobal("EventSource", Source);
  vi.stubGlobal(
    "document",
    Object.assign(new EventTarget(), { hidden: false }),
  );
  vi.stubGlobal(
    "fetch",
    vi.fn<typeof fetch>(async (path) =>
      String(path) === "/api/state"
        ? Response.json(dashboard())
        : Response.json({ detail: "off" }, { status: 503 }),
    ),
  );
});
afterEach(() => {
  stop?.();
  stop = undefined;
  vi.useRealTimers();
  vi.unstubAllGlobals();
});
it("seeds historical fills, deduplicates replay and retains the last ledger cursor across reconnection", async () => {
  const historical = {
    id: "old",
    symbol: "BTC",
    side: "buy" as const,
    quantity: "1",
    price: "100",
    fee: "0",
    at: new Date().toISOString(),
  };
  vi.stubGlobal(
    "fetch",
    vi.fn<typeof fetch>(async (path) =>
      String(path) === "/api/state"
        ? Response.json({ ...dashboard(), fills: [historical] })
        : Response.json({ detail: "off" }, { status: 503 }),
    ),
  );
  const connection = new Connection();
  stop = connection.start();
  await vi.advanceTimersByTimeAsync(1);
  expect(connection.getSnapshot().fill).toBeNull();
  const source = Source.instances[0];
  source.send("ledger", { type: "fill", payload: historical }, "11");
  expect(connection.getSnapshot().fill).toBeNull();
  source.send(
    "ledger",
    { type: "fill", payload: { ...historical, id: "new" } },
    "12",
  );
  expect(connection.getSnapshot().fill?.id).toBe("new");
  const at = connection.getSnapshot().fillAt;
  await vi.advanceTimersByTimeAsync(10);
  source.send(
    "ledger",
    { type: "fill", payload: { ...historical, id: "new" } },
    "13",
  );
  expect(connection.getSnapshot().fillAt).toBe(at);
  await vi.advanceTimersByTimeAsync(9000);
  expect(source.closed).toBe(true);
  expect(Source.instances.at(-1)?.url).toContain("after=13");
});
it("closes streams and removes timers on unmount, including repeated setup", async () => {
  const connection = new Connection();
  stop = connection.start();
  await vi.advanceTimersByTimeAsync(1);
  const first = Source.instances[0];
  stop();
  expect(first.closed).toBe(true);
  expect(vi.getTimerCount()).toBe(0);
  stop = connection.start();
  await vi.advanceTimersByTimeAsync(1);
  expect(Source.instances).toHaveLength(2);
  stop();
  expect(Source.instances.every((s) => s.closed)).toBe(true);
  expect(vi.getTimerCount()).toBe(0);
  stop = undefined;
});
it("retains newer SSE halt state when an older deferred refresh resolves", async () => {
  const connection = new Connection();
  stop = connection.start();
  await vi.advanceTimersByTimeAsync(1);
  const initial = connection.getSnapshot().state!;
  let resolve!: (response: Response) => void;
  const delayed = new Promise<Response>((done) => {
    resolve = done;
  });
  vi.stubGlobal("fetch", vi.fn<typeof fetch>(() => delayed));
  const refresh = connection.refresh();
  Source.instances[0].send("state", {
    ...initial,
    sequence: 12,
    server_time: new Date(Date.parse(initial.server_time) + 2000).toISOString(),
    halted: true,
  });
  const newer = connection.getSnapshot();
  resolve(
    Response.json({
      ...initial,
      sequence: 11,
      server_time: new Date(Date.parse(initial.server_time) + 1000).toISOString(),
      halted: false,
    }),
  );
  await refresh;
  expect(connection.getSnapshot()).toBe(newer);
  expect(connection.getSnapshot().state?.halted).toBe(true);
  expect(connection.getSnapshot().state?.sequence).toBe(12);
});
it("orders timestamp ties by sequence and accepts newer account and quotes with equal sequence", async () => {
  const connection = new Connection();
  stop = connection.start();
  await vi.advanceTimersByTimeAsync(1);
  const initial = connection.getSnapshot().state!;
  const source = Source.instances[0];
  source.send("state", { ...initial, sequence: 12, halted: true });
  const newer = connection.getSnapshot();
  source.send("state", { ...initial, sequence: 11, halted: false });
  expect(connection.getSnapshot()).toBe(newer);
  const time = new Date(Date.parse(initial.server_time) + 1000).toISOString();
  source.send("state", {
    ...newer.state,
    server_time: time,
    account: { ...initial.account, cash: 99000 },
    assets: initial.assets.map((asset) => ({
      ...asset,
      price: 101,
      quote: { ...asset.quote, at: time },
    })),
  });
  expect(connection.getSnapshot().state).toMatchObject({
    sequence: 12,
    server_time: time,
    halted: true,
    account: { cash: 99000 },
    assets: [{ price: 101, quote: { at: time } }],
  });
});
it("requires fresh quotes and a current independent health check", () => {
  const state = dashboard();
  expect(quoteIsFresh(state, "BTC", true, Date.now())).toBe(true);
  expect(quoteIsFresh(state, "BTC", false, Date.now())).toBe(false);
  expect(quoteIsFresh(state, "BTC", true, Date.now() + 16000)).toBe(false);
  const connection = new Connection();
  expect(healthIsLive(connection.getSnapshot())).toBe(false);
});
const seed = (patch: Partial<Seed> = {}): Seed => ({
  now: Date.now(),
  state: dashboard(),
  health: null,
  ...patch,
});
const pending = () => new Promise<Response>(() => {});
it("starts from a display-only seed and keeps a stable initial snapshot", async () => {
  const initial = seed();
  const connection = new Connection(initial);
  const first = connection.getSnapshot();
  expect(first).toMatchObject({
    state: initial.state,
    connected: false,
    seeded: true,
    healthConnected: false,
    healthLoading: true,
    intelligence: null,
    intelligenceConnected: false,
    now: initial.now,
  });
  expect(connection.getInitialSnapshot()).toBe(first);
  stop = connection.start();
  await vi.advanceTimersByTimeAsync(1);
  expect(connection.getSnapshot()).toMatchObject({
    connected: true,
    seeded: false,
  });
  expect(connection.getInitialSnapshot()).toBe(first);
});
it("clears the seed when the browser's state read fails", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn<typeof fetch>(async () =>
      Response.json({ detail: "off" }, { status: 503 }),
    ),
  );
  const connection = new Connection(seed());
  stop = connection.start();
  await vi.advanceTimersByTimeAsync(1);
  expect(connection.getSnapshot()).toMatchObject({
    connected: false,
    seeded: false,
    error: "off",
  });
});
it("keeps the seed while only health and intelligence polls fail", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn<typeof fetch>((path) =>
      String(path) === "/api/state"
        ? pending()
        : Promise.resolve(Response.json({ detail: "off" }, { status: 503 })),
    ),
  );
  const connection = new Connection(seed());
  stop = connection.start();
  await vi.advanceTimersByTimeAsync(100);
  expect(connection.getSnapshot()).toMatchObject({
    seeded: true,
    connected: false,
    healthLoading: false,
    intelligenceConnected: false,
  });
});
it("keeps a newer seed disconnected without a stream until a browser read is accepted", async () => {
  const newer = {
    ...dashboard(),
    sequence: 12,
    server_time: new Date(Date.now() + 2000).toISOString(),
  };
  const connection = new Connection(seed({ state: newer }));
  stop = connection.start();
  await vi.advanceTimersByTimeAsync(1);
  expect(connection.getSnapshot().state).toBe(newer);
  expect(connection.getSnapshot()).toMatchObject({
    connected: false,
    seeded: true,
  });
  expect(Source.instances).toHaveLength(0);
  const accepted = {
    ...newer,
    sequence: 13,
    server_time: new Date(Date.parse(newer.server_time) + 1000).toISOString(),
  };
  vi.mocked(fetch).mockResolvedValueOnce(Response.json(accepted));
  await connection.refresh();
  expect(connection.getSnapshot()).toMatchObject({
    state: accepted,
    connected: true,
    seeded: false,
  });
  expect(Source.instances).toHaveLength(1);
  expect(Source.instances[0].url).toBe("/api/events?after=10");
});
it("runs the stream watchdog from the seed time", async () => {
  vi.stubGlobal("fetch", vi.fn<typeof fetch>(pending));
  const fresh = new Connection(seed());
  stop = fresh.start();
  await vi.advanceTimersByTimeAsync(1000);
  expect(fresh.getSnapshot().seeded).toBe(true);
  stop();
  const old = new Connection(seed({ now: Date.now() - 7500 }));
  stop = old.start();
  await vi.advanceTimersByTimeAsync(1000);
  expect(old.getSnapshot()).toMatchObject({ seeded: false, connected: false });
});
it("expires a seeded health check at the first watchdog tick after 15 s", async () => {
  vi.stubGlobal("fetch", vi.fn<typeof fetch>(pending));
  const now = Date.now();
  const connection = new Connection(
    seed({ now, health: health(new Date(now).toISOString()) }),
  );
  expect(connection.getSnapshot()).toMatchObject({
    healthConnected: true,
    healthLoading: false,
  });
  expect(healthIsLive(connection.getSnapshot())).toBe(true);
  stop = connection.start();
  await vi.advanceTimersByTimeAsync(15001);
  expect(connection.getSnapshot().healthConnected).toBe(true);
  expect(healthIsLive(connection.getSnapshot())).toBe(true);
  await vi.advanceTimersByTimeAsync(999);
  expect(connection.getSnapshot().healthConnected).toBe(false);
  expect(healthIsLive(connection.getSnapshot())).toBe(false);
});
it("keeps today's unseeded behavior without a seed", () => {
  const connection = new Connection();
  expect(connection.getSnapshot()).toMatchObject({
    state: null,
    connected: false,
    seeded: false,
    healthLoading: true,
    now: 0,
  });
  expect(connection.getInitialSnapshot()).toBe(connection.getSnapshot());
});
