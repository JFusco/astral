import {
  test,
  expect,
  type APIRequestContext,
  type Page,
} from "@playwright/test";
import type { Dashboard, OrderIntent } from "../../lib/contracts";

const simulator = "http://127.0.0.1:18766";
// Server-side reads bypass page.route; the disposable simulator is steered directly instead.
async function control(
  request: APIRequestContext,
  modes: Record<string, string>,
) {
  const response = await request.post(`${simulator}/__test/control`, {
    data: modes,
  });
  expect(response.ok()).toBe(true);
}
/** Elements in the complete server response, never script payloads (RSC data would match falsely). */
async function rendered(
  page: Page,
  request: APIRequestContext,
  path: string,
  selector: string,
) {
  const response = await request.get(path);
  expect(response.ok()).toBe(true);
  const html = await response.text();
  return page.evaluate(
    ([html, selector]) => {
      const doc = new DOMParser().parseFromString(html, "text/html");
      doc.querySelectorAll("script, style").forEach((el) => el.remove());
      return [...doc.querySelectorAll(selector)].map(
        (el) => el.textContent ?? "",
      );
    },
    [html, selector] as const,
  );
}
const hydration = /hydrat|Minified React error #(418|423|425)\b/i;
let diagnostics: string[] = [];
test.beforeEach(({ page }) => {
  diagnostics = [];
  page.on("pageerror", (error) => {
    if (hydration.test(error.message))
      diagnostics.push(`pageerror: ${error.message}`);
  });
  page.on("console", (message) => {
    if (message.type() === "error" && hydration.test(message.text()))
      diagnostics.push(`console: ${message.text()}`);
  });
});
test.afterEach(async ({ request }) => {
  await control(request, {
    accounting: "passthrough",
    learning: "passthrough",
    state: "passthrough",
  });
  expect(diagnostics).toEqual([]);
});

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
  request,
}) => {
  // Outlasts the 1.5 s seed timeout once, so the server renders the unseeded frame.
  await control(request, { state: "delay-once:2500" });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setViewportSize({ width: 390, height: 844 });
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  let requested = false;
  await page.route("**/api/state", async (route) => {
    requested = true;
    await gate;
    await route.continue();
  });
  await page.goto("/");
  const loading = page.getByRole("status", {
    name: "Reading account and ledger state",
  });
  await expect(loading).toBeVisible();
  // Server markup is visible before hydration; the Provider effect's read proves hydration.
  await expect.poll(() => requested).toBe(true);
  await expect
    .poll(() =>
      loading.evaluate((el) =>
        el.checkVisibility()
          ? el
              .getAnimations({ subtree: true })
              .filter((a) => a.effect?.getTiming().iterations === Infinity)
              .length
          : -1,
      ),
    )
    .toBe(0);
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
test("saved reports render on the server, preserve unknown results and stale figures; refreshing never starts an evaluation", async ({
  page,
  request,
}) => {
  await control(request, { accounting: "fixture", learning: "fixture" });
  let mutations = 0;
  page.on("request", (req) => {
    if (req.method() === "POST") mutations++;
  });
  const summary = await rendered(
    page,
    request,
    "/accounting",
    'section[aria-label="Accounting summary"]',
  );
  expect(summary).toHaveLength(1);
  expect(summary[0]).toMatch(/NET TRADING P&L\s*Unknown/);
  expect(
    await rendered(page, request, "/accounting", '[role="status"]'),
  ).toEqual(
    expect.arrayContaining([expect.stringMatching(/^Saved 2026-01-02/)]),
  );
  const learningSummary = await rendered(
    page,
    request,
    "/learning",
    'section[aria-label="Learning summary"]',
  );
  expect(learningSummary).toHaveLength(1);
  expect(learningSummary[0]).toContain("OUTCOME READINESS");
  await page.goto("/accounting");
  // Streaming briefly leaves a hidden copy of the report outside <main>.
  const main = page.getByRole("main");
  await expect(main.getByText(/Saved 2026-01-02/)).toBeVisible();
  const netResult = main
    .getByText("NET TRADING P&L", { exact: true })
    .locator("..")
    .getByText("Unknown", { exact: true });
  await expect(netResult).toBeVisible();
  const refresh = page.getByRole("button", { name: "Refresh report" });
  await control(request, { accounting: "unavailable" });
  await refresh.click();
  await expect(
    main.getByText(/Displayed figures are retained from the previous response/),
  ).toBeVisible();
  await expect(netResult).toBeVisible();
  await control(request, { accounting: "delay:3000" });
  const settled = new Promise<void>((resolve) => {
    const done = (req: {
      url(): string;
      headers(): Record<string, string>;
    }) => {
      if (
        req.url().includes("/accounting") &&
        req.headers()["rsc"] === "1" &&
        !req.headers()["next-router-prefetch"]
      )
        resolve();
    };
    page.on("requestfinished", done);
    page.on("requestfailed", done);
  });
  await refresh.click();
  await expect(
    page.getByRole("button", { name: "Reading report…" }),
  ).toBeDisabled();
  await page
    .getByRole("navigation", { name: "Main navigation" })
    .getByRole("link", { name: "Learning", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Protected evidence" }),
  ).toBeVisible();
  await expect(
    page.getByText(/saved offline audit cannot train/),
  ).toBeVisible();
  await settled;
  // A late accounting refresh must never replace the page the user moved to.
  await page.waitForTimeout(500);
  await expect(
    page.getByRole("heading", { name: "Learning", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("region", { name: "Accounting summary" }),
  ).toHaveCount(0);
  await control(request, { accounting: "fixture" });
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
  await expect(main.getByText(/Saved 2026-01-02/)).toBeVisible();
  await expect(
    accountingHeading
      .locator("../..")
      .getByRole("button", { name: "Refresh report" }),
  ).toBeEnabled();
  expect(mutations).toBe(0);
});
test("an unavailable saved report never claims retained figures", async ({
  page,
  request,
}) => {
  await control(request, { accounting: "unavailable" });
  await page.goto("/accounting");
  // Streaming briefly leaves a hidden copy of the report outside <main>.
  const main = page.getByRole("main");
  const notice = main.getByText(
    "Fixture report unavailable. No saved figures are assumed.",
  );
  await expect(notice).toBeVisible();
  await expect(
    main.getByText("No verified accounting report is available.", {
      exact: false,
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Refresh report" }).click();
  await expect(
    page.getByRole("button", { name: "Refresh report" }),
  ).toBeEnabled();
  await expect(notice).toBeVisible();
  await expect(main.getByText(/Displayed figures are retained/)).toHaveCount(0);
});
test("a failed state contract stays unavailable and recovers without synthetic balances", async ({
  page,
  request,
}) => {
  // The server seed drops the malformed state; the browser read gets it too.
  await control(request, { state: "malformed" });
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
  await control(request, { state: "passthrough" });
  malformed = false;
  await expect(
    page.getByText("SIMULATOR / SERVER STREAM", { exact: true }),
  ).toBeVisible({ timeout: 12000 });
  await expect(
    page.getByRole("button", { name: "＋ Local buy" }),
  ).toBeEnabled();
});
test("SSR renders seeded data without enabling actions", async ({
  page,
  request,
}) => {
  const portfolio = await rendered(
    page,
    request,
    "/",
    'section[aria-label="Portfolio overview"]',
  );
  expect(portfolio).toHaveLength(1);
  expect(portfolio[0]).toMatch(/PORTFOLIO VALUE\s*\$[\d,]+\.\d{2}/);
  // Page content streams as a fragment outside <main>, so query the document body.
  const body = (await rendered(page, request, "/", "body")).join(" ");
  expect(body).toContain("PERSISTENT SIMULATOR");
  expect(body).not.toContain("BACKEND REQUIRED");
  expect(await rendered(page, request, "/", '[role="status"]')).toEqual(
    expect.arrayContaining([
      "SERVER SNAPSHOT / CONNECTING",
      expect.stringMatching(/^Server snapshot · connecting live stream/),
    ]),
  );
  expect(
    await rendered(
      page,
      request,
      "/health",
      '[role="status"][aria-label="Connecting to health engine"]',
    ),
  ).toHaveLength(1);
  expect(
    await rendered(
      page,
      request,
      "/health",
      'section[aria-label="Health summary"]',
    ),
  ).toHaveLength(0);
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/state", async (route) => {
    await gate;
    await route.continue();
  });
  await page.goto("/");
  // Before the browser read's 3 s timeout: seeded figures show, every action stays locked.
  const quick = { timeout: 2000 };
  await expect(
    page
      .getByRole("region", { name: "Portfolio overview" })
      .getByText(/^\$[\d,]+\.\d{2}$/)
      .first(),
  ).toBeVisible(quick);
  await expect(
    page.getByText("SERVER SNAPSHOT / CONNECTING", { exact: true }),
  ).toBeVisible(quick);
  const buy = page.getByRole("button", { name: "＋ Local buy", exact: true });
  const halt = page.getByRole("button", { name: "◈ Halt entries" });
  await expect(buy).toBeDisabled(quick);
  await expect(halt).toBeDisabled(quick);
  await expect(
    page.getByRole("button", { name: "Run research review ↗" }),
  ).toBeDisabled(quick);
  release();
  // Up to the 8 s watchdog refresh if the held read already timed out.
  const recovery = { timeout: 12000 };
  await expect(
    page.getByText("SIMULATOR / SERVER STREAM", { exact: true }),
  ).toBeVisible(recovery);
  await expect(buy).toBeEnabled(recovery);
  await expect(halt).toBeEnabled(recovery);
});
test("only the Overview document carries the dashboard seed", async ({
  page,
  request,
}) => {
  // Flight strings escape their quotes inside HTML, so match the bare key; "/" is the positive control.
  const raw = async (path: string) => (await request.get(path)).text();
  expect(await raw("/")).toContain("equity_history");
  for (const path of ["/accounting", "/learning", "/health"]) {
    expect(await raw(path), path).not.toContain("equity_history");
    const status = await rendered(
      page,
      request,
      path,
      'header [role="status"]',
    );
    expect(status.length, path).toBeGreaterThan(0);
    expect(new Set(status), path).toEqual(new Set(["CONNECTING TO SERVICE"]));
  }
  // Capture flight bodies at the network layer: reading them lazily from response
  // events fails once Next aborts or supersedes a streamed RSC fetch.
  const flight: string[] = [];
  await page.route(/[?&]_rsc=/, async (route) => {
    const headers = route.request().headers();
    if (headers["rsc"] !== "1" || headers["next-router-prefetch"])
      return route.fallback();
    const response = await route.fetch();
    const body = await response.text();
    flight.push(body);
    await route.fulfill({ response, body });
  });
  await control(request, { accounting: "fixture" });
  await page.goto("/accounting");
  const refresh = page.getByRole("button", { name: "Refresh report" });
  await refresh.click();
  await expect.poll(() => flight.length).toBeGreaterThan(0);
  await expect(refresh).toBeEnabled();
  await page.goto("/?view=settings");
  await expect(
    page.getByRole("dialog", { name: "Display settings" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close dialog" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(
    page.getByRole("heading", { name: "Market overview" }),
  ).toBeVisible();
  // Client-cache navigations may issue no flight request; any that did must be seed-free.
  for (const body of flight) expect(body).not.toContain("equity_history");
});
test("the strategies view renders on the server inside its dialog", async ({
  page,
  request,
}) => {
  const dialogs = await rendered(page, request, "/?view=strategies", "dialog");
  expect(dialogs).toEqual([
    expect.stringContaining(
      "ATR14, trend and prior-20-bar breakouts are reproducible research hypotheses",
    ),
  ]);
  expect(dialogs[0]).toContain("Deterministic rules. Measured risk.");
  expect(dialogs[0]).toContain("Learning promotion is disabled.");
  for (const view of ["constructor", "hasOwnProperty", "__proto__"])
    expect(
      await rendered(page, request, `/?view=${view}`, "h1, dialog"),
      view,
    ).toEqual(["Market overview"]);
});
// Development React reports attribute and style mismatches that production builds stay silent on.
test.describe("development hydration smoke @dev", () => {
  test.describe.configure({ timeout: 180000 });
  const routes = [
    "/",
    "/health",
    "/accounting",
    "/learning",
    "/?view=settings",
    "/?view=strategies",
  ];
  for (const reducedMotion of ["no-preference", "reduce"] as const)
    test(`direct loads hydrate cleanly with ${reducedMotion} motion`, async ({
      page,
      request,
    }) => {
      await health(page);
      // Saved reports, so the server-rendered report content is hydrated too.
      await control(request, { accounting: "fixture", learning: "fixture" });
      await page.emulateMedia({ reducedMotion });
      for (const path of routes) {
        await page.goto(path);
        // The Provider's first read runs in an effect, so the live status marks hydration.
        await expect(
          page.getByText("SIMULATOR / SERVER STREAM", { exact: true }),
        ).toBeVisible({ timeout: 60000 });
        const report = { "/accounting": "Accounting", "/learning": "Learning" }[
          path
        ];
        if (report)
          await expect(
            page
              .getByRole("main")
              .getByRole("region", { name: `${report} summary` }),
          ).toBeVisible();
        if (path === "/?view=settings" && reducedMotion === "reduce")
          await expect(
            page.getByText("Reduced motion is active."),
          ).toBeVisible();
      }
      if (reducedMotion === "reduce") {
        await page.goto("/");
        await expect(
          page.getByText("SIMULATOR / SERVER STREAM", { exact: true }),
        ).toBeVisible();
        await page.getByRole("link", { name: "Display settings" }).click();
        await expect(page.getByText("Reduced motion is active.")).toBeVisible();
      }
      expect(diagnostics).toEqual([]);
    });
});
