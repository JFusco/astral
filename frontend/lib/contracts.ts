import { z } from "zod";

const text = z.string();
const number = z.number().finite();
const numeric = z.union([
  number,
  text.refine(
    (v) => v.trim() !== "" && Number.isFinite(Number(v)),
    "Expected numeric string",
  ),
]);
const amount = number.nullable();
const record = z.record(text, z.unknown());
const counts = z.record(text, number);
export const fillSchema = z.object({
  id: text,
  symbol: text,
  side: z.enum(["buy", "sell"]),
  quantity: numeric,
  price: numeric,
  fee: numeric.nullable(),
  at: text,
});
export const newsSchema = z
  .object({
    id: z.union([text, number]),
    headline: text,
    source: text,
    url: text.nullish(),
    category: text.optional(),
    symbols: z.array(text).nullish(),
    created_at: text.nullish(),
    updated_at: text.nullish(),
    first_seen_at: text.optional(),
    event_start: text.optional(),
    event_end_exclusive: text.optional(),
    source_id: text.optional(),
  })
  .passthrough();
export const packetSchema = z.object({
  symbol: text,
  as_of: text,
  expires_at: text,
  eligible: z.boolean(),
  facts: record,
  vetoes: z.array(text),
  evidence: z.array(record),
  input_hash: text,
});
export const dashboardSchema = z.object({
  service_version: z.literal("0.2"),
  mode: z.enum(["alpaca", "simulator"]),
  paper_only: z.literal(true),
  configured: z.boolean(),
  connected: z.boolean(),
  orders_enabled: z.boolean(),
  halted: z.boolean(),
  sequence: number.int().nonnegative(),
  server_time: text,
  as_of: text.nullable(),
  account: z.object({
    equity: amount,
    cash: amount,
    opening_equity: amount,
    deployed: number,
    realized: amount,
    unrealized: number,
    net: amount,
    equity_change: amount,
    profit_scope: text,
  }),
  assets: z.array(
    z.object({
      symbol: text,
      type: z.enum(["crypto", "etf"]),
      price: amount,
      quantity: number,
      basis: number,
      market_value: number,
      unrealized: number,
      quote: z
        .object({ at: text.optional(), source: text.optional() })
        .passthrough(),
      quote_fresh: z.boolean(),
    }),
  ),
  fills: z.array(fillSchema),
  orders: z.array(
    z.object({
      client_id: text,
      status: text,
      external: z.boolean().optional(),
      request: z
        .object({
          intent: z
            .object({ symbol: text.optional() })
            .passthrough()
            .optional(),
        })
        .passthrough(),
      broker: z
        .object({ id: text.optional(), symbol: text.optional() })
        .passthrough(),
    }),
  ),
  workers: z.array(
    z
      .object({
        name: text,
        status: text,
        detail: text.optional(),
        at: text.optional(),
      })
      .passthrough(),
  ),
  equity_history: z.array(z.object({ at: text, value: numeric })),
  news: z.array(newsSchema),
  risk_policy: record,
  inventory: record,
  untracked_positions: z.array(record),
  research: z.object({
    enabled: z.boolean(),
    model_enabled: z.boolean(),
    packets: z.array(packetSchema),
    review: record.nullable(),
    last_model_review: record.nullable(),
    budget: record.nullable(),
  }),
  shadow: z.object({
    enabled: z.boolean(),
    counts: z.array(z.object({ count: number, decision: text })),
    recent: z.array(
      z.object({ at: text, intent: record, result: record, input_hash: text }),
    ),
  }),
  timing: z.array(record),
  learning: z.object({ observations: number }),
  uptime_seconds: number,
  experiment: record.nullable(),
  portfolio_replay: record.nullable(),
  liquidity_experiment: record.nullable(),
  execution_pilot: record.nullable(),
  readiness: record.nullable(),
  crypto_universe: record.nullable(),
});
export const healthNodeSchema = z.object({
  id: text,
  name: text,
  group: text,
  status: z.enum([
    "healthy",
    "degraded",
    "down",
    "unknown",
    "inactive",
    "checking",
  ]),
  detail: text,
  checked_at: text.nullish(),
});
export const healthSchema = z.object({
  as_of: text,
  checked_at: text,
  heartbeat_live: z.boolean(),
  sequence: number,
  duration_ms: number,
  nodes: z.array(healthNodeSchema),
  changes: z.array(
    z
      .object({
        at: text,
        payload: z
          .object({ id: text, previous: text, status: text })
          .passthrough(),
      })
      .passthrough(),
  ),
});
export const intelligenceSchema = z.object({
  sources: z.array(
    z
      .object({
        id: text,
        name: text,
        url: text,
        category: text,
        status: text,
        fresh: z.boolean(),
        interval_seconds: number,
        http_status: number.nullish(),
        last_success_at: text.nullish(),
        detail: text.optional(),
        last_item_count: number.optional(),
      })
      .passthrough(),
  ),
  items: z.array(newsSchema),
});
export const accountingSchema = z.object({
  status: z.literal("saved_report"),
  as_of: text,
  source_mode: text,
  fill_rows: number,
  custody: z.object({
    status: text,
    differences: z.array(
      z.object({
        symbol: text,
        recorded_net_quantity: numeric,
        broker_quantity: numeric,
        unexplained_quantity: numeric,
      }),
    ),
  }),
  money_results: z.object({
    realized_net_pnl_usd: numeric.nullable(),
    reason: text,
  }),
  issues: counts,
  gross_fifo_diagnostics: z.object({
    status: text,
    basis: text,
    by_book: z.array(
      z.object({ symbol: text, book: text, gross_realized_usd: numeric }),
    ),
  }),
  operating_costs: z.object({
    receipt_links: z.array(z.object({
      provider: text,
      url: z.string().max(2048).url().refine((value) => {
        try {
          const u = new URL(value);
          const account = u.searchParams.get("authuser");
          return !/\s/.test(value) && u.origin === "https://mail.google.com" &&
            !u.username && !u.password && /^\/mail\/u\/(?:\d+\/)?$/.test(u.pathname) &&
            /^#(?:all|inbox)\/[A-Za-z0-9_-]{8,100}$/.test(u.hash) &&
            [...u.searchParams.keys()].every((k) => k === "authuser") &&
            u.searchParams.getAll("authuser").length <= 1 &&
            (account === null || /^(?:\d+|[\w.+-]+@[\w.-]+)$/.test(account));
        } catch {
          return false;
        }
      }),
    })).default([]),
    monthly_astral_personal_budget_by_currency: z
      .record(text, numeric)
      .nullable(),
    actual_total_by_currency: z.record(text, numeric).nullable(),
    monthly_budget_complete: z.boolean().nullable(),
    recorded_confirmed_charges_by_currency: z.record(text, numeric).nullable(),
    estimated_charges_by_currency: z.record(text, numeric).nullable(),
  }),
});
export const learningSchema = z.object({
  status: z.literal("saved_report"),
  as_of: text,
  source_mode: text,
  data_and_outcomes: z.object({
    status: text,
    reason: text,
    resolved_net_pnl_labels: number,
    decision_categories: counts,
    training_rows: number,
    research_packets_inspected: number,
  }),
  model_research: z.object({
    receipt_categories: counts,
    contract_checks: counts,
    usefulness: z.object({ status: text, reason: text }),
    recorded_usage: counts,
    costs: z.object({
      total_actual_usd: numeric.nullable(),
      unknown_cost_receipts: number,
      scope: text,
    }),
  }),
  inventory: z.record(
    text,
    z.object({
      available: number.optional(),
      protected_window: number.optional(),
      after_cutoff: number.optional(),
      invalid_timestamp: number.optional(),
      status: text.optional(),
    }),
  ),
  issues: counts,
  protected_windows: z.array(
    z.object({ id: text, starts_at: text, ends_at: text, policy: text }),
  ),
});
export type Dashboard = z.infer<typeof dashboardSchema>;
export type Fill = z.infer<typeof fillSchema>;
export type Health = z.infer<typeof healthSchema>;
export type HealthNode = z.infer<typeof healthNodeSchema>;
export type Intelligence = z.infer<typeof intelligenceSchema>;
export type News = z.infer<typeof newsSchema>;
export type Packet = z.infer<typeof packetSchema>;
export type Accounting = z.infer<typeof accountingSchema>;
export type Learning = z.infer<typeof learningSchema>;
export type OrderIntent = {
  client_order_id: string;
  symbol: string;
  side: "buy" | "sell";
  notional: number;
  execution: "bounded" | "patient" | "market";
  ttl_seconds: 60;
  strategy_id: "manual";
};
