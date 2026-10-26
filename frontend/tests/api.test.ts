import { afterEach, expect, it, vi } from "vitest";
import { z } from "zod";
import { api } from "../lib/api";
import { accountingSchema, dashboardSchema } from "../lib/contracts";
import { dashboard } from "./fixtures";
afterEach(() => vi.unstubAllGlobals());
it("rejects unsafe receipt navigation in an accounting response without throwing", async () => {
  const receipts = accountingSchema.shape.operating_costs.shape.receipt_links;
  for (const url of ["not-a-url", "javascript:alert(1)", "https://evil.example/mail/u/0/#all/0123456789abcdef",
    "https://user:secret@mail.google.com/mail/u/0/#all/0123456789abcdef",
    "https://mail.google.com/mail/u/0/?redirect=https://evil.example#all/0123456789abcdef"]) {
    vi.stubGlobal("fetch", vi.fn<typeof fetch>(async () => Response.json([{ provider: "Fixture vendor", url }])));
    await expect(api("/api/accounting/report", receipts)).rejects.toMatchObject({ kind: "invalid-response" });
  }
});
it("rejects malformed values instead of inventing defaults", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn<typeof fetch>(async () => Response.json({ amount: "not a number" })),
  );
  await expect(
    api("/api/state", z.object({ amount: z.number() })),
  ).rejects.toMatchObject({ kind: "invalid-response" });
});
it("accepts null optional news metadata without changing required fields", () => {
  const news = {
    id: 1,
    headline: "h",
    source: "benzinga",
    symbols: null,
    url: null,
    created_at: null,
    updated_at: null,
    first_seen_at: "2026-01-01T00:00:00Z",
  };
  const state = { ...dashboard(), news: [news] };
  expect(dashboardSchema.parse(state).news).toEqual([news]);
  for (const key of ["id", "headline", "source"])
    expect(
      dashboardSchema.safeParse({ ...state, news: [{ ...news, [key]: null }] })
        .success,
    ).toBe(false);
});
it("performs a mutation once on a lost response", async () => {
  const fetcher = vi.fn<typeof fetch>(async () => {
    throw new TypeError("connection reset");
  });
  vi.stubGlobal("fetch", fetcher);
  await expect(
    api("/api/orders", z.unknown(), {
      body: { client_order_id: "astral-preserved-intent" },
    }),
  ).rejects.toMatchObject({ kind: "unavailable" });
  expect(fetcher).toHaveBeenCalledTimes(1);
  expect(JSON.parse(fetcher.mock.calls[0]?.[1]?.body as string)).toEqual({
    client_order_id: "astral-preserved-intent",
  });
});
it("keeps a missing saved report distinct from a valid report", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn<typeof fetch>(async () =>
      Response.json({ status: "unavailable", reason: "No saved report" }),
    ),
  );
  await expect(api("/api/learning/report", z.unknown())).rejects.toMatchObject({
    kind: "unavailable",
    message: "No saved report",
  });
});
