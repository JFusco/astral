# AI workers, costs, rate limits, telemetry, and learning

Research verified 2026-10-24. Scope: US Georgia user, paper budget $100–$300/month, daily/swing and intraday strategies kept separate, possibly several venues. These are architecture recommendations and explicit cost illustrations, not evidence of trading edge. No API calls, accounts, trades, or paid generation were executed. Prices USD before taxes. Cite direct official URLs below; ignore search-only Jev lookalike sites, whose pricing conflicted with TypeSafe's actual documentation.

## What should Jev, Codex CLI, Grok Bot, and model APIs do?

### Takeaway

Use ordinary software for the data pipeline, strategy arithmetic, sizing, portfolio risk, routing, order state, and accounting. Add bounded model workers for interpreting text, proposing hypotheses, and reporting; the learning layer should evaluate candidate changes before paper promotion. Agent availability and cheap tokens do not establish predictive skill.

### Cited Findings

- Jev takes state plus typed questions. Choice selects among named options with probabilities; Score rates against ordered descriptive criteria; Noul returns a yes/no probability. These are constrained judgments, not a text-generating analyst. — [Introduction](https://docs.typesafe.ai/introduction), [Choice](https://docs.typesafe.ai/primitives/choice), [Score](https://docs.typesafe.ai/primitives/score), [Noul](https://docs.typesafe.ai/primitives/noul)
- TypeSafe explicitly recommends keeping deterministic rules, control flow, and side effects in code, with atomic model questions and outputs combined in code. — [How to build with TypeSafe](https://docs.typesafe.ai/concepts/how-to-build-with-system-one)
- TypeSafe documents arithmetic, date comparisons, option-order sensitivity, irrelevant-context and adversarial-content weaknesses for **Jev 1.13 specifically**. This is not proof of the exact same defects in 1.14, but is a reason to test every version on the intended workload. — [Jev 1.13 jaggedness](https://docs.typesafe.ai/model-jaggedness/jev-1.13)
- `codex exec --json` emits JSONL lifecycle/tool events and a usage object; `--output-schema` requests a JSON Schema final answer. Default sandbox is read-only. API keys are the documented default for automation. — [Non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode)
- ChatGPT authentication uses subscription access; API-key authentication uses usage-based access and standard API billing. — [Authentication](https://learn.chatgpt.com/docs/auth)
- A separate official **Grok Bot** product now exists: persistent bots use a shared account cloud computer and can run routines. Subscription availability, weekly included usage, and optional model/token on-demand usage differ from the xAI token API. — [Grok Bot overview](https://docs.x.ai/grok-bot/overview), [Grok Bot FAQ](https://docs.x.ai/grok-bot/faq)

### Inferences

Recommended role map (proposal):

| Worker | Responsibility | Suggested implementation | Authority |
| --- | --- | --- | --- |
| Market-data worker | Normalize symbol/venue/calendar, bars/quotes, timestamps and sequence gaps | Python or TypeScript, no LLM | Publish versioned snapshots |
| Strategy workers | Separate ETF swing, ETF intraday, crypto swing, crypto intraday signals | Deterministic, testable functions first | Propose target weights/orders |
| Text classifier | Headline relevance, event type, source credibility category, regime labels from supplied evidence | Optional pinned Jev model | Advisory features; its confidence is not return probability |
| Analyst/proposal worker | Produce constrained explanation/hypothesis from compact data plus approved universe | Optional direct model API | Proposals only; no broker tools/keys |
| Portfolio risk worker | Global/per-strategy/venue exposure, open-order reservations, daily loss/drawdown, correlation and cash | Deterministic central service | Veto; never relaxed by LLM output |
| Execution worker | Price/quantity precision, spread/freshness guards, limit policy, client IDs, cancel/reconcile | Deterministic broker adapter | Sole order writer with paper-only keys |
| Reconciliation/accountant | Broker events, positions/cash, fees, fills, corporate actions, strategy virtual books | Deterministic | Freeze new risk on unresolved mismatch |
| Learning/evaluation worker | Attribution, drift/calibration, candidate scoring and promotion artifacts | Statistics first; optional model retrospective | Write candidate artifacts, not active config |
| Codex CLI/Grok Bot | Build code, inspect replay results, draft experiments/reports, explain incidents | Read-only production snapshots; sandboxed repository tasks | No live broker credentials or runtime risk-policy edits |

Direct APIs are preferable for the bounded runtime worker because token caps, retries, response schema, concurrency and usage accounting can be controlled in one application. Codex CLI and Grok Bot remain useful development/research interfaces. A separate named agent is not required for every logical worker: one process and shared host can run several isolated jobs.

### Gaps

- No verified source establishes profitable ETF/crypto selection or general financial probability calibration for these models.
- User's intended meaning of “Grok Bots” may be the official Grok Bot product or home-built xAI workers; discuss both. Exact subscription Bot spend depends on the user's plan and usage; do not price it with xAI API rates.

## What prices and limits are verified?

### Takeaway

Price the actual model requests and external tools, not a fixed salary per worker. Standard short-prompt API prices verified today support low-cost classification and infrequent analysis, but running a stronger analyst every five minutes can consume the whole budget.

### Cited Findings

| Model / service | Input / 1M | Output / 1M | Cached read / 1M | Source |
| --- | ---: | ---: | ---: | --- |
| Jev `jev-1.14.0` | $0.042 | Free | Not assumed | [TypeSafe Models](https://docs.typesafe.ai/models) |
| OpenAI `gpt-6-luna`, Standard | $0.10 | $0.50 | $0.01 | [API pricing](https://developers.openai.com/api/docs/pricing), [Luna model](https://developers.openai.com/api/docs/models/gpt-6-luna) |
| OpenAI `gpt-6.1-sol`, Standard | $2.00 | $10.00 | $0.10 | [API pricing](https://developers.openai.com/api/docs/pricing) |
| xAI `grok-4.7`, context under 200k | $2.00 | $6.00 | $0.50 | [xAI API pricing](https://docs.x.ai/developers/pricing) |
| OpenAI `gpt-5.3-codex`, Standard, optional development illustration | $1.75 | $14.00 | $0.175 | [API pricing](https://developers.openai.com/api/docs/pricing) |

- OpenAI's pricing distinguishes Standard, Flex/Batch, Fast, Ultrafast and cache writes. All examples below use Standard, uncached input, with no explicit cache-write charges/discounts assumed. Reasoning tokens are billed as output; `max_output_tokens` includes reasoning plus visible output, and incomplete responses can still cost money. — [Pricing](https://developers.openai.com/api/docs/pricing), [Reasoning](https://developers.openai.com/api/docs/guides/reasoning)
- xAI charges $5/1,000 web-search calls. X Search costs **$5/1,000 fetched posts and $10/1,000 fetched profiles**, including parent/quoted posts, rather than one flat search-call price. Reasoning and tool context consume tokens too. — [xAI pricing](https://docs.x.ai/developers/pricing)
- Jev 1.14 was released October 14; default limits are 64k tokens/request and 32k/question. Org-specific request/second and token/second limits are in the console, with `429`/retry handling. Versioned IDs avoid silent alias changes. — [TypeSafe Models](https://docs.typesafe.ai/models)
- OpenAI limits can apply per organization/project and shared model family; they are not independent per worker or key. The current table shows Build tier at 5,000 RPM and 1M TPM for Sol and 2M TPM for Luna. Check the account dashboard and headers before use. — [OpenAI rate limits](https://developers.openai.com/api/docs/guides/rate-limits)
- xAI publishes team/model RPS and TPM tiers. Grok 4.7 Tier 0 currently lists 150 RPS and 50M TPM; actual personalized console values govern. Cached and reasoning tokens also count toward TPM. Exceeding limits returns 429. — [xAI rate limits](https://docs.x.ai/developers/rate-limits)
- Codex subscription usage is separate from API token prices. Local/cloud agent work shares included allowances and weekly limits may apply; task complexity/model/tools/context change consumption. — [Codex pricing](https://learn.chatgpt.com/docs/pricing?codex-pricing-plans=individual)

### Inferences

Pin a model/version plus recorded `price_version=2026-10-24`. Use a per-provider global limiter covering every worker and strategy, plus independent broker/data limiters. Track retries already performed by SDKs to avoid retry multiplication. Prioritize cancellations, fills and position reconciliation above research traffic. Revalidate rates before procurement/implementation.

### Gaps

Jev universal numeric quotas are not public in the fetched docs; account access required. Exact subscription Grok Bot monthly usage/cost and subscription Codex per-worker dollars cannot be inferred from API token rates. Hosting/data subscription prices are separate from these model rates.

## What are reproducible daily versus intraday cost scenarios?

### Takeaway

At bounded context sizes, frequent low-cost proposals can fit the paper budget. Stronger analysis should be scheduled or event-triggered. The cheap classification line is not an equivalent replacement for generative reasoning.

### Cited Findings

All calculations below are **derived illustrations** using the verified [OpenAI](https://developers.openai.com/api/docs/pricing), [xAI](https://docs.x.ai/developers/pricing), and [Jev](https://docs.typesafe.ai/models) rates above. They are not measured bills or quality claims.

### Inferences

Assumptions:

- One compact universe snapshot per strategy run, not one call per asset. Universe must be small/filtered enough that **all prompt/schema/state/questions/tool context across the job** fit the specified budget. Tokenizers vary by provider.
- Generative example: 8,000 total uncached input tokens and 1,500 **total billable output tokens including hidden reasoning** per job. This is a chosen budget, not a prediction that a default reasoning agent naturally stays within it.
- Jev illustration: 8,000 billable input tokens total, typed decisions with free output. It performs a different, narrower job; no generated 1,500-token report assumed.
- Zero retries, zero cache writes/reads, zero tools in this comparison. A successful job may need more than one request; sum all of them. Inference-only totals exclude data, hosting and subscriptions.
- ETF month = 22 regular 6.5-hour sessions: 78 five-minute decision runs/session = 1,716. Crypto month = 30 full days: 288 runs/day = 8,640. Actual exchange calendars differ; these are planning constants.

`job_cost = (input_tokens × input_price + total_billable_output_tokens × output_price) / 1,000,000`

`monthly_cost = sum(all actual job/request/attempt token costs + cache-write/read charges + tool charges)`

| Worker/model | Cost/job | ETF daily, 22 | Crypto daily, 30 | ETF every 5 min, 1,716 | Crypto every 5 min, 8,640 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Jev typed text judgment | $0.000336 | $0.0074 | $0.0101 | $0.58 | $2.90 |
| Luna proposal/extraction | $0.001550 | $0.0341 | $0.0465 | $2.66 | $13.39 |
| Sol analyst | $0.031000 | $0.6820 | $0.9300 | $53.20 | $267.84 |
| Grok 4.7 analyst, no tools | $0.025000 | $0.5500 | $0.7500 | $42.90 | $216.00 |

Concrete lean monthly allocation for both separate intraday strategies (1,716 ETF + 8,640 crypto = **10,356 total runs**) plus daily/swing oversight:

| Logical role | Exact job allocation | Derived model/tool spend |
| --- | --- | ---: |
| Data/signal/risk/execution/reconciliation | Deterministic code on shared host; no LLM | $0 incremental tokens |
| Optional Jev text features | 10,356 × 8k input | $3.48 |
| Luna bounded proposals | 10,356 × (8k input + 1.5k billable output) | $16.05 |
| Sol daily review/swing oversight | 22 ETF + 30 crypto = 52 × same 8k/1.5k budget | $1.61 |
| Learning statistics/replay/drift | Shared-host CPU and storage; no model | $0 incremental tokens |
| Optional Sol learning retrospectives | 4 weeks × 2 strategy-family reports = 8 jobs, each 20k input + 5k billable output | $0.72 |
| Optional Grok research, total job token budget including tool rounds | 60 jobs × 8k/1.5k = $1.50; 120 web calls = $0.60; 600 fetched X posts = $3.00; no profiles | $5.10 |
| **Runtime AI subtotal** | Under all assumptions above | **$26.96** |
| Shared hosting allowance | $15 planning allowance, not a vendor quote | $15.00 |
| Storage/backups/log allowance | $5 planning allowance, not a vendor quote | $5.00 |
| Market data | Parent researcher to substantiate free-tier restrictions or $99 feed | $0 or $99.00 |
| **Expected planning subtotal** | With $0 or $99 data | **$46.96 / $145.96** |
| Optional Codex API development | 20 bounded jobs × (100k input × $1.75/M + 20k billable output × $14/M) = $0.455/job | $9.10 |
| Contingency reserve | Planning reserve, not a charge | $25.00 |
| **Planning envelope** | With above dev example + reserve | **$81.06 / $180.06** |

The free-data envelope does not promise the coverage/fidelity required for serious intraday paper testing. The $99 feed is an input from the parent task and needs the broker/data researcher's current citation. User's $100–$300 is a ceiling envelope, not a spending target. Do not deploy every optional model simply because the illustration fits it. Start with deterministic strategies plus logging, then test whether each AI role improves results after all costs.

Set application-enforced AI daily/monthly hard budgets and per-job max attempts, max tool calls, max tokens, deadline and concurrency. Stop optional model jobs at budget exhaustion; retain data, position tracking, risk exits and cancel/reconcile paths. Larger output/reasoning, searches, retries, cache writes and longer histories can make actual charges much higher. A 10× input/output workload approximately multiplies token spend by 10 before other rate-tier effects.

### Gaps

These are conditional estimates, not forecast invoices or throughput/quality guarantees. Hardware sizing, backup retention, exact feed entitlements, tick storage growth and backtest CPU require measured pilot data. A Jev/model call every five minutes is an upper workload illustration; unchanged or irrelevant text should normally be deduplicated and not reclassified.

## What telemetry is needed to explain a trade and each worker's cost?

### Takeaway

Keep an append-only decision/order/learning ledger that can reconstruct what was known, which code/model proposed what, which guard accepted it and what actually happened. A dashboard without a reproducible ledger will not be enough for incident diagnosis or learning.

### Cited Findings

- OpenTelemetry provides traces, metrics and logs; traces describe a request's path, metrics record runtime measurements, and logs record events. — [OpenTelemetry signals](https://opentelemetry.io/docs/concepts/signals/)
- Codex JSONL has lifecycle/tool events and usage fields including input, cached input, output and reasoning output. — [Codex non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode)
- xAI returns per-request actual billed cost via `usage.cost_in_usd_ticks`; 10^10 ticks = $1. It includes model and server-tool charges/discounts, so do not add your estimated tool charges again. Multi-request conversations require summing each request; streaming cost arrives with final usage. — [xAI cost tracking](https://docs.x.ai/developers/cost-tracking)
- Jev responses return model and input/output usage, and model aliases can move; the resolved version should be logged. — [TypeSafe API](https://docs.typesafe.ai/api/system-one), [TypeSafe Models](https://docs.typesafe.ai/models)

### Inferences

Proposed minimal implementation: structured JSON events plus a transactional SQLite/Postgres ledger and retained snapshots/artifacts; daily backup/export. Add OpenTelemetry spans and Prometheus/Grafana only where useful. One host is sufficient for a first pilot; Kafka/Kubernetes are not initial requirements. Do not put credentials or unnecessary personal data in logs.

Proposed fields, grouped by event family:

| Event family | Minimum evidence/metrics |
| --- | --- |
| Identity/reproducibility | `run_id`, `trace_id`, `parent_run_id`, `strategy_id/version`, `venue`, `account_id`, `paper/live`, code git SHA, config/risk policy versions, model requested/resolved, prompt/schema versions, dataset/snapshot hash, event/receive/process times UTC |
| Data health | Source/feed, exchange timestamp, arrival delay, quote age, sequence gaps/reconnects, missing bars, corporate-action adjustment version, bid/ask/spread, depth if entitled, symbol mapping |
| Decision | Universe/candidate set, features and values, signal/target weights, proposal/hold/reject reason, rationale/evidence links, model probability and confidence separately, deterministic guard outcomes, TTL and price reference |
| Risk/portfolio | Global + strategy + venue cash/exposure, pending-order reservations, gross/net/correlated exposure, concentration, volatility estimate, turnover, realized/unrealized PnL, high-water mark, drawdown, loss limits, limit headroom and risk vetoes |
| Execution lifecycle | Intent/client/broker order IDs, venue, qty/notional, order type/TIF/limit/stop, pretrade quote and expected cost, submitted/acknowledged/accepted/partial/filled/cancel pending/canceled/rejected/expired/unknown states with timestamps, exact broker event IDs/errors |
| Execution quality | End-to-end and broker acknowledgment latency p50/p95/p99, fill ratio, partial-fill dwell time, signed slippage vs arrival midpoint and decision reference, fees/rebates, effective spread, cancels, rejects, price improvement, duplicate prevention, reconciliation mismatches |
| API reliability | Endpoint/provider, limiter pool, 429/retry-after, timeout/5xx, attempts including SDK retries, circuit state, token/request remaining/reset metadata, stale-data stops and recovery evidence |
| AI/worker accounting | Worker/job/attempt/request IDs, provider/model/price version, uncached/read/write input buckets, total output and reasoning subset, tool names/counts and fetched X items, latency, attempts/failures/incomplete status, estimated USD, actual billed USD when supplied, currency, estimated/measured/reconciled status |
| Shared cost | Host/storage/egress/data/subscriptions billed monthly, CPU time/memory/artifact storage per worker, allocation rule, total overhead even with zero trades |
| Learning | Experiment ID, hypothesis, champion/challenger versions, training/validation/paper periods, as-of data versions, objective and benchmark, net cost attribution, drift/calibration results, candidate evaluation, accept/reject reason, reviewer/approval, promotion/rollback timestamp and artifact hashes |

Maintain costs at multiple units: per job, successful job, accepted proposal, submitted order, filled trade, closed round trip, strategy/day, strategy/month, portfolio/month. Count both buys and sells appropriately. Do not report a misleading zero cost when there are no trades: report total dollars and `cost_per_trade = N/A` when count = 0. Avoid allocating the same shared data/host bill independently to every worker.

OpenAI reasoning tokens are a **subset** of total billed output: do not charge output plus reasoning a second time. Likewise avoid double-counting cached-input totals or xAI tool-inclusive actual billed ticks. Aggregate estimated spend live, then reconcile to provider usage/billing and label remaining differences. For multi-venue bots, maintain one global risk and cost ledger plus venue subledgers; independent bot balances can hide aggregate correlated exposure or opposing orders.

No blind order-POST retries after network uncertainty. Persist intent/client ID first, query broker status by ID, and reconcile before any resubmission. Retry policies for read-only model/data calls and trading mutations must be separate.

### Gaps

No universal definition of “all telemetry” is finite. Final event fields, retention, sensitive-data policy and provider idempotency semantics must be tested against the chosen broker adapters. API headers may vary; record missing usage/cost as unknown rather than inventing success or a zero bill.

## How should the learning worker behave and cost be controlled?

### Takeaway

The first learning layer should learn from clean evidence and compare candidate strategy configurations offline. It should not let an LLM rewrite risk limits or silently replace the currently paper-traded policy.

### Cited Findings

- TypeSafe recommends atomic outputs combined in code and explicitly describes using probabilities as features in a downstream classical model; pinned versions protect thresholds from alias movement. — [How to build](https://docs.typesafe.ai/concepts/how-to-build-with-system-one), [Models](https://docs.typesafe.ai/models)
- Optional retrospective inference costs can be computed using published model rates, while total billable output includes reasoning. — [OpenAI pricing](https://developers.openai.com/api/docs/pricing), [Reasoning billing](https://developers.openai.com/api/docs/guides/reasoning)

### Inferences

Proposed staged learning loop:

1. Nightly deterministic attribution: separate signal quality, sizing, execution slippage, fees, borrow/funding if relevant, and worker/data/host expense. Retain rejected/hold proposals as well as trades, with later outcomes labeled at predeclared horizons.
2. Track calibration of any true outcome forecasts against realized labels (reliability bins/Brier score where suitable), signal/feature distributions and market regime changes. Jev confidence about a text classification is not automatically a probability of positive future return.
3. Weekly generate a small, registered set of candidate changes (thresholds, lookbacks, instrument filters, execution parameters within fixed risk rules). Cheap statistics first; optional bounded LLM retrospective proposes hypotheses from the evidence, with $0.72/month illustrative spend above.
4. Evaluate walk-forward/out-of-sample with data available as of each decision; purge/embargo overlapping outcome labels where needed. Keep untouched holdout periods; log all experiments so searching many variants is visible. Report uncertainty/sample size rather than just the winning backtest.
5. Compare paper champion and challenger on the **same** snapshots, broker/paper assumptions, risk budget and benchmark. A challenger may be shadow-only; avoid doubling the real portfolio exposure. Compare net risk-adjusted outcomes, turnover, drawdown, tail loss, cost, reliability and behavior under failure. Win rate alone is inadequate.
6. Write a versioned promotion report with preregistered acceptance criteria, candidate/champion diffs, cost/risk attribution, evidence and rollback. Keep risk limits immutable to automated learning; user-controlled promotion and live enablement remain separate gates.

A first implementation can use ordinary rolling estimates/logistic models or carefully constrained parameter selection; foundation-model fine-tuning is not a prerequisite. Storage/replay CPU belongs in shared measured cost. Budget the learning worker independently so repeated candidate searches cannot exhaust execution resources. Regime drift or weak evidence should trigger reduced confidence/hold/review, never automatic risk expansion or Martingale sizing.

### Gaps

Sample size sufficient for promotion depends on strategy horizon, turnover, dependence and regime coverage. A fixed number of paper days cannot prove live profitability. This scope did not establish an appropriate predictive model or an objective threshold for the user's yet-undefined strategies; choose those before data mining.

## How should continuous news and financial-document ingestion fit the budget?

### Takeaway

Treat “all possible articles” as a coverage objective to bound with selected sources, entitlements, freshness targets and a fixed universe. Fetch incrementally, deduplicate once, cluster related reporting, and summarize changed evidence; do not reread the entire article corpus for every strategy cycle.

### Cited Findings

- At the verified rates, input-heavy Jev classification and bounded Luna summaries can be inexpensive; that does not include news/data licensing or establish comprehensive coverage. — [TypeSafe prices](https://docs.typesafe.ai/models), [OpenAI prices](https://developers.openai.com/api/docs/pricing)
- xAI Web Search bills by call, and X Search bills fetched posts/profiles, including quoted/parent posts; browsing a source through a model has both tool and token expense. — [xAI tool pricing](https://docs.x.ai/developers/pricing)

### Inferences

Proposed feed stages: licensed feed/API/filing ingest → normalize publication/first-seen/update times and source ID → URL/content-hash dedup and revision history → entity/security mapping → relevance filter → event/story clustering → bounded extraction/summary → immutable evidence snapshots. The daily/swing and intraday consumers reference the same stored event IDs. Fetch primary releases, official filings, exchange notices and economic calendars directly where available; news and social evidence remains attributed, not treated as ground truth. Confirm each source's storage, summarization, redistribution and model-processing entitlement during vendor selection.

Proposed extra example, **not a forecast**: 1,000 new items/day, 30 days, each averaging 1,000 total Jev input tokens for relevance/event classification costs `30,000 × 1,000 × $0.042/M = $1.26`. Summarize only 10% (3,000 unique/relevant stories/month), each 2,000 total Luna input plus 500 total billable output tokens: `3,000 × (2,000×$0.10 + 500×$0.50)/M = $1.35`. Thus **$2.61 extra inference**, before feed subscriptions, retrieval/search tools, retries, cache charges and storage. Shared-context reuse is not assumed across these jobs. Each longer article/filing and larger bundle must count its actual tokens. Those averages are chosen caps, not claims about normal article length or adequate summary quality.

If that work is additional to the earlier runtime snapshot budgets, add it once: earlier $180.06 paid-feed envelope becomes **$182.67** under the same assumptions. Do not double count article tokens already included in a snapshot job. Financial statement parsing and ratio arithmetic belong in deterministic code where possible; an LLM can annotate footnotes or explain a supplied filing section. Preserve as-of data and revisions to prevent hindsight leakage.

Add news-source telemetry: source/feed/license tier; cursor/backfill range; publish/update/first-seen/ingest timestamps; revision and content hash; poll/websocket gaps; source-to-ingest lag; staleness/coverage SLAs; 429/errors; unique versus duplicate article counts; event-cluster IDs; symbols/entities; retained raw-source reference and evidence excerpts; classifier confidence; enrichment/summary versions; document token count; queue age; dropped/deferred reason; daily dollars and search/X item consumption. A source outage or missing coverage must be visible in the decision snapshot.

Use separate source API quotas and per-day article/token/search budgets. Reserve capacity for urgent revisions. Expire or revalidate stale summaries by event type; a timeless profile and a breaking halt notice need different TTLs. Social/X sampling from Grok research is one input and should not be described as a comprehensive firehose, comprehensive market coverage, or proof that a rumor is true.

### Gaps

Source availability, licensing, financials update frequency and coverage limits are being researched by the broker/data researcher. No finite paid plan or model can be assumed to cover every article, paywall, private report and social post. Full-text rights and timely first-seen coverage must be verified for each chosen source and channel.
