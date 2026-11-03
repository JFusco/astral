import { afterEach, beforeEach, expect, it, vi } from "vitest";
import {
  Connection,
  quoteIsFresh,
  healthIsLive,
  type Seed,
  type Snapshot,
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
  vi.restoreAllMocks();
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
  expect(connection.getSnapshot().ownReadAt).toBeNull();
  expect(connection.getSnapshot().ownReadIdentity).toBeNull();
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
    ownReadAt: null,
    ownReadIdentity: null,
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
    ownReadAt: null,
    ownReadIdentity: null,
    now: 0,
  });
  expect(connection.getInitialSnapshot()).toBe(connection.getSnapshot());
});

// These cases protect GET provenance through public reads and stream delivery.
const receiptTime = "2026-10-31T12:34:56.123456+00:00";
const receiptState = () => ({ ...dashboard(), server_time: receiptTime });
function stateFetch(read: (init?: RequestInit) => Promise<Response>) {
  vi.mocked(fetch).mockImplementation((path, init) =>
    String(path) === "/api/state"
      ? read(init)
      : Promise.resolve(Response.json({ detail: "off" }, { status: 503 })),
  );
}
async function liveConnection(state = receiptState()) {
  stateFetch(async () => Response.json(state));
  const connection = new Connection();
  stop = connection.start();
  await vi.advanceTimersByTimeAsync(0);
  return connection;
}
function deferredRead() {
  let resolve!: (response: Response) => void;
  const response = new Promise<Response>((done) => { resolve = done; });
  return { response, resolve };
}
it.each([
  { name: "without a seed", seeded: false },
  { name: "with a display-only seed", seeded: true },
])("records an accepted initial GET $name without changing the initial snapshot", async ({ seeded }) => {
  vi.setSystemTime(new Date(receiptTime));
  const state = receiptState();
  const connection = new Connection(seeded ? seed({ state }) : null);
  const initial = connection.getInitialSnapshot();
  expect(initial).toMatchObject({ ownReadAt: null, ownReadIdentity: null });
  stateFetch(async () => Response.json(state));
  const at = Date.now();
  stop = connection.start();
  await vi.advanceTimersByTimeAsync(0);
  expect(connection.getSnapshot()).toMatchObject({
    state, connected: true, seeded: false, error: null,
    ownReadAt: at, ownReadIdentity: { server_time: receiptTime, sequence: state.sequence },
  });
  expect(Source.instances).toHaveLength(1);
  expect(connection.getInitialSnapshot()).toBe(initial);
  expect(initial).toMatchObject({ ownReadAt: null, ownReadIdentity: null });
});
it("publishes exactly one consistent snapshot per accepted GET, including equal identity", async () => {
  const connection = await liveConnection();
  const first = connection.getSnapshot();
  const next = { ...first.state!, halted: true };
  const notifications: Snapshot[] = [];
  const unsubscribe = connection.subscribe(() => notifications.push(connection.getSnapshot()));
  vi.setSystemTime(Date.now() + 100);
  stateFetch(async () => Response.json(next));
  await connection.refresh();
  unsubscribe();
  expect(notifications).toHaveLength(1);
  expect(notifications[0]).toMatchObject({
    state: next, ownReadAt: Date.now(),
    ownReadIdentity: { server_time: next.server_time, sequence: next.sequence },
  });
  expect(notifications[0].ownReadAt).not.toBe(first.ownReadAt);
});
it.each([
  { name: "an older timestamp", server_time: "2026-10-31T12:34:55+00:00", sequence: 99 },
  { name: "a lower sequence at equal time", server_time: receiptTime, sequence: 9 },
])("rejects $name without refreshing an existing receipt", async ({ server_time, sequence }) => {
  const connection = await liveConnection();
  const accepted = connection.getSnapshot();
  vi.setSystemTime(Date.now() + 100);
  stateFetch(async () => Response.json({ ...accepted.state!, server_time, sequence, halted: true }));
  await connection.refresh();
  expect(connection.getSnapshot()).toBe(accepted);
  expect(Source.instances).toHaveLength(1);
});
it.each([
  { name: "HTTP failure", error: "off", result: () => Promise.resolve(Response.json({ detail: "off" }, { status: 503 })) },
  { name: "transport failure", error: "Service unavailable.", result: () => Promise.reject(new Error("network")) },
  { name: "schema failure", error: "Service response did not match the dashboard contract", result: () => Promise.resolve(Response.json({ service_version: "wrong" })) },
  { name: "timeout", error: "Service request timed out.", result: async () => { throw new Error("aborted"); } },
])("does not create or refresh a receipt after $name", async ({ name, error, result }) => {
  for (const priorRead of [false, true]) {
    const connection = priorRead ? await liveConnection() : new Connection(seed());
    const before = connection.getSnapshot();
    vi.setSystemTime(Date.now() + 100);
    if (name === "timeout") {
      // AbortSignal.timeout uses the runtime clock; provide a controlled deadline.
      const deadline = new AbortController();
      vi.spyOn(AbortSignal, "timeout").mockReturnValue(deadline.signal);
      stateFetch((init) => new Promise<Response>((_resolve, reject) => {
        init!.signal!.addEventListener("abort", () => reject(new Error("aborted")), { once: true });
        queueMicrotask(() => deadline.abort());
      }));
    } else stateFetch(result);
    if (priorRead) await connection.refresh();
    else { stop = connection.start(); await vi.advanceTimersByTimeAsync(0); }
    expect(connection.getSnapshot()).toMatchObject({
      connected: false, seeded: false,
      ownReadAt: before.ownReadAt, ownReadIdentity: before.ownReadIdentity,
    });
    expect(connection.getSnapshot().error).toBe(error);
    stop?.(); stop = undefined;
    vi.restoreAllMocks();
  }
});
it.each([
  { name: "stopped", restarted: false },
  { name: "replaced by a new generation", restarted: true },
])("ignores an old GET that resolves after the connection is $name", async ({ restarted }) => {
  const delayed = deferredRead();
  stateFetch(() => delayed.response);
  const connection = new Connection(seed({ state: receiptState() }));
  stop = connection.start();
  stop(); stop = undefined;
  if (restarted) {
    stateFetch(async () => Response.json({ ...receiptState(), sequence: 11 }));
    stop = connection.start();
    await vi.advanceTimersByTimeAsync(0);
  }
  const current = connection.getSnapshot();
  delayed.resolve(Response.json({ ...receiptState(), sequence: 99 }));
  await vi.advanceTimersByTimeAsync(0);
  expect(connection.getSnapshot()).toBe(current);
  expect(Source.instances).toHaveLength(restarted ? 1 : 0);
});
it.each([
  { name: "invalid incoming time", prior: "finite", incoming: "not-a-time" },
  { name: "invalid prior time", prior: "not-a-time", incoming: receiptTime },
  { name: "invalid initial time", prior: "none", incoming: "not-a-time" },
])("preserves display adoption and stream opening with $name but issues no receipt", async ({ prior, incoming }) => {
  const connection = prior === "finite"
    ? await liveConnection()
    : new Connection(prior === "none" ? null : seed({ state: { ...receiptState(), server_time: prior } }));
  const received = { ...receiptState(), server_time: incoming, halted: true };
  stateFetch(async () => Response.json(received));
  const notifications: Snapshot[] = [];
  if (prior === "finite") {
    const unsubscribe = connection.subscribe(() => notifications.push(connection.getSnapshot()));
    await connection.refresh();
    unsubscribe();
    expect(notifications).toHaveLength(1);
    expect(notifications[0]).toMatchObject({ state: received, ownReadAt: null, ownReadIdentity: null });
  } else {
    stop = connection.start();
    await vi.advanceTimersByTimeAsync(0);
  }
  expect(connection.getSnapshot()).toMatchObject({
    state: received, connected: true, seeded: false, error: null,
    ownReadAt: null, ownReadIdentity: null,
  });
  expect(Source.instances).toHaveLength(1);
});
it.each([
  { name: "finite becomes invalid", before: receiptTime, during: "not-a-time", eligible: false },
  { name: "invalid becomes finite", before: "not-a-time", during: receiptTime, eligible: true },
])("uses the prior state at acceptance when $name during a pending GET", async ({ before, during, eligible }) => {
  const connection = await liveConnection({ ...receiptState(), server_time: before });
  const delayed = deferredRead();
  stateFetch(() => delayed.response);
  const refresh = connection.refresh();
  Source.instances[0].send("state", { ...receiptState(), server_time: during });
  const incoming = { ...receiptState(), server_time: "2026-10-31T12:34:57.123456+00:00", sequence: 12 };
  vi.setSystemTime(Date.now() + 100);
  delayed.resolve(Response.json(incoming));
  await refresh;
  expect(connection.getSnapshot()).toMatchObject({
    state: incoming, connected: true, seeded: false, error: null,
    ownReadAt: eligible ? Date.now() : null,
    ownReadIdentity: eligible ? { server_time: incoming.server_time, sequence: incoming.sequence } : null,
  });
});
it("does not transfer a receipt to adopted SSE state even with identical identity", async () => {
  const connection = await liveConnection();
  const accepted = connection.getSnapshot();
  const source = Source.instances[0];
  source.send("state", { ...accepted.state!, sequence: 9, halted: true });
  expect(connection.getSnapshot()).toBe(accepted);
  source.send("state", { ...accepted.state!, halted: true });
  expect(connection.getSnapshot()).toMatchObject({ state: { halted: true }, ownReadAt: null, ownReadIdentity: null });
});
it("does not resurrect a GET receipt after a subscriber adopts newer SSE state", async () => {
  const connection = await liveConnection();
  const received = { ...receiptState(), sequence: 11 };
  const unsubscribe = connection.subscribe(() => {
    if (connection.getSnapshot().state?.sequence === 11)
      Source.instances[0].send("state", { ...received, sequence: 12 });
  });
  stateFetch(async () => Response.json(received));
  await connection.refresh();
  unsubscribe();
  expect(connection.getSnapshot()).toMatchObject({ state: { sequence: 12 }, ownReadAt: null, ownReadIdentity: null });
});
it("retains null provenance during healthy SSE and issues a new receipt only on watchdog GET recovery", async () => {
  const connection = await liveConnection();
  const first = connection.getSnapshot().ownReadAt;
  expect(first).toBeTypeOf("number");
  const source = Source.instances[0];
  source.send("state", receiptState());
  for (let i = 0; i < 5; i++) {
    await vi.advanceTimersByTimeAsync(2000);
    source.send("state", receiptState());
    expect(connection.getSnapshot()).toMatchObject({ ownReadAt: null, ownReadIdentity: null });
  }
  const stateCalls = () => vi.mocked(fetch).mock.calls.filter(([path]) => String(path) === "/api/state").length;
  expect(stateCalls()).toBe(1);
  await vi.advanceTimersByTimeAsync(8000);
  expect(stateCalls()).toBe(1);
  await vi.advanceTimersByTimeAsync(1000);
  expect(source.closed).toBe(true);
  expect(stateCalls()).toBe(2);
  expect(connection.getSnapshot()).toMatchObject({
    connected: true, ownReadAt: Date.now(),
    ownReadIdentity: { server_time: receiptTime, sequence: 10 },
  });
  Source.instances[1].send("state", receiptState());
  expect(connection.getSnapshot()).toMatchObject({ ownReadAt: null, ownReadIdentity: null });
});
