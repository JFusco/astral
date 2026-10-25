import { test, expect, type Page } from "@playwright/test";
import type { Dashboard, OrderIntent } from "../../lib/contracts";

async function health(page: Page) {
  await page.route("**/api/health/state", (route) =>
    route.fulfill({
      json: {
        as_of: new Date().toISOString(),
        checked_at: new Date().toISOString(),
        heartbeat_live: true,
        sequence: 1,
        duration_ms: 2,
        nodes: [
          {
            id: "application",
            name: "Application API",
            group: "core",
            status: "healthy",
            detail: "Isolated test service",
            checked_at: new Date().toISOString(),
          },
        ],
        changes: [],
      },
    }),
  );
}
test("all four routes render and navigation keeps one stream while graphics release resources", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await health(page);
  await page.addInitScript(() => {
    const active = new Set<EventSource>();
    const Native = window.EventSource;
    window.EventSource = class extends Native {
      constructor(url: string | URL, options?: EventSourceInit) {
        super(url, options);
        active.add(this);
      }
      close() {
        active.delete(this);
        super.close();
      }
    };
    Object.defineProperty(window, "__streams", { get: () => active.size });
    const pending = new Set<number>();
    const request = window.requestAnimationFrame.bind(window),
      cancel = window.cancelAnimationFrame.bind(window);
    window.requestAnimationFrame = (callback) => {
      const id = request((time) => {
        pending.delete(id);
        callback(time);
      });
      pending.add(id);
      return id;
    };
    window.cancelAnimationFrame = (id) => {
      pending.delete(id);
      cancel(id);
    };
    Object.defineProperty(window, "__frames", { get: () => pending.size });
  });
  await page.goto("/");
  await expect(
    page.getByText("SIMULATOR / SERVER STREAM", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Market overview" }),
  ).toBeVisible();
  const baseline = await page.evaluate(
    () => Reflect.get(window, "__frames") as number,
  );
  await page.screenshot({
    path: "test-results/overview-desktop.png",
    fullPage: true,
  });
  for (let i = 0; i < 3; i++) {
    await page
      .getByRole("navigation", { name: "Main navigation" })
      .getByRole("link", { name: "App health" })
      .click();
    await expect(
      page.getByRole("heading", { name: "App health", exact: true }),
    ).toBeVisible();
    await expect
      .poll(() => page.locator('canvas[data-renderer="three-webgl"]').count())
      .toBe(1);
    await expect(
      page.getByRole("button", { name: "Application API healthy" }),
    ).toBeVisible();
    await page
      .getByRole("navigation", { name: "Main navigation" })
      .getByRole("link", { name: "Accounting", exact: true })
      .click();
    await expect(
      page.getByRole("heading", { name: "Accounting", exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText("No verified accounting report is available.", {
        exact: false,
      }),
    ).toBeVisible();
    await page
      .getByRole("navigation", { name: "Main navigation" })
      .getByRole("link", { name: "Learning", exact: true })
      .click();
    await expect(
      page.getByRole("heading", { name: "Learning", exact: true }),
    ).toBeVisible();
    await expect
      .poll(() => page.evaluate(() => Reflect.get(window, "__streams")))
      .toBe(1);
    await expect
      .poll(() =>
        page.evaluate(() => Reflect.get(window, "__frames") as number),
      )
      .toBeLessThanOrEqual(baseline + 2);
    await page
      .getByRole("navigation", { name: "Main navigation" })
      .getByRole("link", { name: "Overview", exact: true })
      .click();
    await expect(
      page.getByRole("heading", { name: "Market overview" }),
    ).toBeVisible();
  }
  expect(errors).toEqual([]);
  await page.goto("/health.html");
  await expect(
    page.getByRole("heading", { name: "Page not found" }),
  ).toBeVisible();
});
test("Health keeps its WebGL canvas while ambient motion stops and resumes", async ({
  page,
}) => {
  test.setTimeout(45000);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await health(page);
  await page.goto("/health");
  const canvas = page.locator('canvas[data-renderer="three-webgl"]');
  await expect(canvas).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Application API healthy" }),
  ).toBeVisible();
  const renderer = await canvas.evaluateHandle((canvas) => {
    const state = { canvas, lost: 0, restored: 0 };
    canvas.addEventListener("webglcontextlost", () => state.lost++);
    canvas.addEventListener("webglcontextrestored", () => state.restored++);
    return state;
  });
  await expect
    .poll(async () => Number(await canvas.getAttribute("data-shooting-stars")), {
      timeout: 15000,
      intervals: [100],
    })
    .toBeGreaterThan(0);
  await page.evaluate(() => {
    localStorage.setItem("astral-motion", "reduced");
    window.dispatchEvent(new Event("astral-motion-change"));
  });
  await expect
    .poll(() => canvas.getAttribute("data-shooting-stars"))
    .toBe("0");
  await page.evaluate(() => {
    localStorage.setItem("astral-motion", "cinematic");
    window.dispatchEvent(new Event("astral-motion-change"));
  });
  await expect
    .poll(async () => Number(await canvas.getAttribute("data-shooting-stars")), {
      timeout: 15000,
      intervals: [100],
    })
    .toBeGreaterThan(0);
  await expect(canvas).toHaveCount(1);
  expect(
    await renderer.evaluate((state) => ({
      sameCanvas:
        state.canvas ===
        document.querySelector('canvas[data-renderer="three-webgl"]'),
      lost: state.lost,
      restored: state.restored,
    })),
  ).toEqual({ sameCanvas: true, lost: 0, restored: 0 });
  await expect(
    page.getByText(/3D view unavailable|3D view paused/),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Application API healthy" }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});
test("loading feedback honors reduced motion and narrow screens remain usable", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setViewportSize({ width: 390, height: 844 });
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/state", async (route) => {
    await gate;
    await route.continue();
  });
  await page.goto("/");
  const loading = page.getByRole("status", {
    name: "Reading account and ledger state",
  });
  await expect(loading).toBeVisible();
  expect(
    await loading.evaluate(
      (el) =>
        el
          .getAnimations({ subtree: true })
          .filter((a) => a.effect?.getTiming().iterations === Infinity).length,
    ),
  ).toBe(0);
  await page.screenshot({
    path: "test-results/loading-mobile.png",
    fullPage: true,
  });
  release();
  await expect(
    page.getByText("SIMULATOR / SERVER STREAM", { exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("link", { name: "Display settings" }).click();
  await expect(
    page.getByRole("dialog", { name: "Display settings" }),
  ).toBeVisible();
  await expect(page.getByText("Reduced motion is active.")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
});
test("simulator order submits once and uncertain outcomes remain blocked across navigation until reconciliation", async ({
  page,
  request,
}) => {
  await page.goto("/");
  const buy = page.getByRole("button", { name: "＋ Local buy", exact: true });
  await expect(buy).toBeEnabled();
  const submissions: OrderIntent[] = [];
  await page.route("**/api/orders", async (route) => {
    submissions.push(route.request().postDataJSON());
    if (submissions.length === 1) {
      await route.fetch();
      await route.abort("failed");
    } else await route.continue();
  });
  await buy.click();
  await page.getByLabel("Maximum order amount (USD)").fill("25");
  await page.getByLabel("Execution policy").selectOption("market");
  await page.getByRole("button", { name: "Submit simulated buy" }).click();
  await expect(
    page.getByText("No replacement intent will be submitted.", {
      exact: false,
    }),
  ).toBeVisible();
  expect(submissions).toHaveLength(1);
  const [buyIntent] = submissions;
  await expect(
    page.getByText(`Intent ${buyIntent.client_order_id}`, { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Intent submitted — check readback" }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "Close dialog" }).click();
  await expect(buy).toBeDisabled();
  await page
    .getByRole("navigation", { name: "Main navigation" })
    .getByRole("link", { name: "Learning", exact: true })
    .click();
  await page
    .getByRole("navigation", { name: "Main navigation" })
    .getByRole("link", { name: "Overview", exact: true })
    .click();
  await expect(buy).toBeDisabled();
  await page.getByRole("link", { name: "System telemetry" }).click();
  await expect(
    page.getByText(`Uncertain intent: ${buyIntent.client_order_id}.`, {
      exact: false,
    }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Reconcile account and orders" })
    .click();
  await expect(
    page.getByText(/Intent filled; confirmed by readback/),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close dialog" }).click();
  await expect(buy).toBeEnabled();
  expect(submissions).toHaveLength(1);
  const postBuyResponse = await request.get("/api/state");
  expect(postBuyResponse.status()).toBe(200);
  const postBuy: Dashboard = await postBuyResponse.json();
  expect(postBuy.orders).toEqual(
    expect.arrayContaining([
      expect.objectContaining({
        client_id: buyIntent.client_order_id,
        status: "filled",
      }),
    ]),
  );
  const quantityAfterBuy = postBuy.assets.find(
    (asset) => asset.symbol === buyIntent.symbol,
  )!.quantity;
  expect(quantityAfterBuy).toBeGreaterThan(0);
  await page.getByRole("button", { name: "◈ Halt entries" }).click();
  await expect(
    page.getByRole("button", { name: "◇ Resume entries" }),
  ).toBeVisible();
  await expect(buy).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "− Local sell" }),
  ).toBeEnabled();
  await page.getByRole("button", { name: "◇ Resume entries" }).click();
  await expect(buy).toBeEnabled();
  await page.getByRole("button", { name: "− Local sell" }).click();
  await page.getByLabel("Maximum order amount (USD)").fill("10");
  await page.getByLabel("Execution policy").selectOption("market");
  await page.getByRole("button", { name: "Submit simulated sell" }).click();
  await expect(page.getByText(/Order (filled|accepted|new)\./)).toBeVisible();
  await expect(
    page.getByText(`Intent ${submissions[1].client_order_id}`, { exact: true }),
  ).toBeVisible();
  expect(submissions.map((intent) => intent.side)).toEqual(["buy", "sell"]);
  expect(submissions[1].symbol).toBe(buyIntent.symbol);
  const intentIds = submissions.map((intent) => intent.client_order_id);
  for (const id of intentIds) expect(id).toMatch(/^astral-/);
  expect(new Set(intentIds).size).toBe(2);
  const postSellResponse = await request.get("/api/state");
  expect(postSellResponse.status()).toBe(200);
  const postSell: Dashboard = await postSellResponse.json();
  expect(postSell.orders).toEqual(
    expect.arrayContaining(
      submissions.map((intent) =>
        expect.objectContaining({
          client_id: intent.client_order_id,
          request: expect.objectContaining({ intent }),
        }),
      ),
    ),
  );
  expect(postSell.fills).toEqual(
    expect.arrayContaining([
      expect.objectContaining({
        client_id: submissions[1].client_order_id,
        side: "sell",
        symbol: buyIntent.symbol,
      }),
    ]),
  );
  expect(
    postSell.assets.find((asset) => asset.symbol === buyIntent.symbol)!.quantity,
  ).toBeLessThan(quantityAfterBuy);
  expect(submissions).toHaveLength(2);
});
test("the production relay enforces same-origin headers", async ({
  request,
}) => {
  const state = await request.get("/api/state");
  expect(state.status()).toBe(200);
  expect(state.headers()["cache-control"]).toBe("no-store");
  expect((await request.get("/api/unknown")).status()).toBe(404);
  expect(
    (
      await request.get("/api/state", {
        headers: {
          host: "evil.example",
          "x-forwarded-host": "127.0.0.1:18730",
        },
      })
    ).status(),
  ).toBe(400);
  expect(
    (await request.post("/api/halt", { data: { halted: true } })).status(),
  ).toBe(403);
  expect(
    (
      await request.post("/api/halt", {
        headers: {
          "X-Astral-Intent": "paper-only",
          origin: "https://evil.example",
        },
        data: { halted: true },
      })
    ).status(),
  ).toBe(403);
  const halt = await request.post("/api/halt", {
    headers: {
      "X-Astral-Intent": "paper-only",
      origin: "http://127.0.0.1:18730",
    },
    data: { halted: true },
  });
  expect(halt.status()).toBe(200);
  await request.post("/api/halt", {
    headers: { "X-Astral-Intent": "paper-only" },
    data: { halted: false },
  });
});
test("SSE preserves Last-Event-ID replay and the cancellation route reaches the simulator", async ({
  page,
  request,
}) => {
  const before = await (await request.get("/api/state")).json();
  const headers = {
    "X-Astral-Intent": "paper-only",
    origin: "http://127.0.0.1:18730",
  };
  await request.post("/api/halt", { headers, data: { halted: true } });
  await page.goto("/");
  const replay = await page.evaluate(async (cursor: number) => {
    const response = await fetch("/api/events?after=99999999", {
      headers: { "Last-Event-ID": String(cursor) },
      signal: AbortSignal.timeout(4000),
    });
    const reader = response.body!.getReader();
    const decoder = new TextDecoder();
    let body = "";
    try {
      while (!/id: \d+\nevent: ledger/.test(body)) {
        const next = await reader.read();
        if (next.done) break;
        body += decoder.decode(next.value, { stream: true });
      }
      return body;
    } finally {
      await reader.cancel();
    }
  }, before.sequence);
  expect(replay).toContain("event: ledger");
  expect(replay).toContain("entry_halt");
  await request.post("/api/halt", { headers, data: { halted: false } });
  const id = `astral-cancel-e2e-${Date.now()}`;
  const order = await request.post("/api/orders", {
    headers,
    data: {
      client_order_id: id,
      symbol: "BTC",
      side: "buy",
      notional: 25,
      execution: "patient",
      ttl_seconds: 60,
      strategy_id: "manual",
    },
  });
  expect(order.status()).toBe(202);
  const cancel = await request.post(`/api/orders/${id}/cancel`, {
    headers,
    data: {},
  });
  expect(cancel.status()).toBe(200);
  expect(["pending_cancel", "canceled", "filled"]).toContain(
    (await cancel.json()).status,
  );
});
test("saved reports preserve unknown results and stale figures; refreshing never starts an evaluation", async ({
  page,
  request,
}) => {
  const accounting = await (
    await request.get("http://127.0.0.1:18766/__test/accounting")
  ).json();
  const learning = await (
    await request.get("http://127.0.0.1:18766/__test/learning")
  ).json();
  expect(accounting.status).toBe("saved_report");
  expect(learning.status).toBe("saved_report");
  await page.addInitScript(() => {
    const signals: AbortSignal[] = [];
    const fetcher = window.fetch.bind(window);
    window.fetch = (input, options) => {
      if (input === "/api/accounting/report" && options?.signal)
        signals.push(options.signal);
      return fetcher(input, options);
    };
    Object.defineProperty(window, "__reportAborts", {
      get: () => signals.map((signal) => signal.aborted ? signal.reason?.name : null),
    });
  });
  let release!: () => void;
  const delayedRefresh = new Promise<void>((resolve) => {
    release = resolve;
  });
  let reads = 0,
    mutations = 0;
  page.on("request", (req) => {
    if (req.method() === "POST") mutations++;
  });
  await page.route("**/api/accounting/report", async (route) => {
    reads++;
    if (reads === 3) await delayedRefresh;
    await route.fulfill({
      json:
        reads === 2
          ? { status: "unavailable", reason: "Fixture report unavailable" }
          : accounting,
    });
  });
  await page.route("**/api/learning/report", (route) =>
    route.fulfill({ json: learning }),
  );
  await page.goto("/accounting");
  await expect(page.getByText(/Saved 2026-01-02/)).toBeVisible();
  await expect(
    page
      .getByText("NET TRADING P&L", { exact: true })
      .locator("..")
      .getByText("Unknown", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Refresh report" }).click();
  await expect(
    page.getByText(/Displayed figures are retained from the previous response/),
  ).toBeVisible();
  await expect(
    page
      .getByText("NET TRADING P&L", { exact: true })
      .locator("..")
      .getByText("Unknown", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Refresh report" }).click();
  await expect
    .poll(() => page.evaluate(() => Reflect.get(window, "__reportAborts").slice(2)))
    .toEqual([null]);
  await page
    .getByRole("navigation", { name: "Main navigation" })
    .getByRole("link", { name: "Learning", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Protected evidence" }),
  ).toBeVisible();
  await expect
    .poll(() => page.evaluate(() => Reflect.get(window, "__reportAborts").slice(2)), {
      timeout: 1000,
    })
    .toEqual(["AbortError"]);
  release();
  await expect(
    page.getByText(/saved offline audit cannot train/),
  ).toBeVisible();
  await page
    .getByRole("navigation", { name: "Main navigation" })
    .getByRole("link", { name: "Accounting", exact: true })
    .click();
  const accountingHeading = page.getByRole("heading", {
    name: "Accounting",
    exact: true,
  });
  await expect(accountingHeading).toBeVisible();
  await expect(
    page.getByRole("region", { name: "Accounting summary" }),
  ).toBeVisible();
  await expect(page.getByText(/Saved 2026-01-02/)).toBeVisible();
  await expect.poll(() => reads).toBe(4);
  await expect(
    accountingHeading
      .locator("../..")
      .getByRole("button", { name: "Refresh report" }),
  ).toBeEnabled();
  expect(mutations).toBe(0);
});
test("a failed state contract stays unavailable and recovers without synthetic balances", async ({
  page,
}) => {
  let malformed = true;
  await page.route("**/api/state", async (route) => {
    if (malformed)
      await route.fulfill({
        json: { service_version: "0.2", account: { equity: 999999 } },
      });
    else await route.continue();
  });
  await page.goto("/");
  await expect(
    page.getByText("Local service unavailable", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "＋ Paper buy" }),
  ).toBeDisabled();
  await expect(page.getByText("$999,999.00", { exact: true })).toHaveCount(0);
  await expect(
    page.getByRole("status", { name: "Reading account and ledger state" }),
  ).toHaveCount(0);
  malformed = false;
  await expect(
    page.getByText("SIMULATOR / SERVER STREAM", { exact: true }),
  ).toBeVisible({ timeout: 12000 });
  await expect(
    page.getByRole("button", { name: "＋ Local buy" }),
  ).toBeEnabled();
});
