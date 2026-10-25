# ASTRAL trading command

The independent [health engine and live 3D health universe](docs/HEALTH-ENGINE.md)
assess application services, workers, market feeds, provider reports and model
state separately from telemetry and trading. Open the **System Heartbeat** card
in the local dashboard to inspect it. Unknown/disabled capabilities stay explicit.
**App health**, **Accounting** and **Learning** are child pages in the same ASTRAL application,
with shared branding, sidebar and main navigation. The [Tailwind 4 UI foundation](frontend/README.md) owns shared tokens, local fonts and utility recipes.

The [offline learning proof](docs/LEARNING-ENGINE.md) audits outcome readiness
and retained model research, with no training or promotion. Its scoped independent
implementation review is complete. The separate [accounting proof](docs/ACCOUNTING-ENGINE.md)
reports retained gross lot matches, unresolved custody/fee evidence and private
operating-cost records. Net P&L and tax-ready results remain unavailable.

ASTRAL now includes a Python service, durable SQLite records, a paper-only Alpaca adapter, a separate persistent simulator, and a dashboard connected through server-sent events.

**Current milestone:** the capped $25 BTC execution round trip is complete; a frozen BTC daily strategy now records read-only research evidence every 15 minutes. An isolated portfolio replay now exercises 16 synthetic execution scenarios and a fixed future evaluation window. The first research-driven trade remains blocked. See [the current experiment](docs/FROZEN-STRATEGY.md) and [roadmap](docs/ROADMAP.md). Authenticated Alpaca paper readback and a small BTC buy/exit were verified on October 24, 2026 EDT (October 25 UTC); both orders filled and the final account had no positions or working orders. Automated swing/intraday execution and trained learning remain disabled. Public news/filing metadata and scoped FOMC dates are connected; extracted financials, issuer holdings, complete event coverage and a cloud backend remain outstanding.

## Next.js frontend

The sole frontend is the Next.js App Router application in `frontend/`, with
Overview, App health, Accounting and Learning at `/`, `/health`, `/accounting`
and `/learning`. Python serves APIs only. The legacy static frontend, browser
simulation and preview build have been removed.

Use Node.js 22 or later (Node 24 was verified), then run from this directory:

```sh
npm ci --ignore-scripts
npm run dev
```

Open **http://127.0.0.1:3000**. Start the Python service on port 8766 using one of
the mode-specific commands below. Start the [intelligence collector](docs/INTELLIGENCE.md)
on 8768 and [health engine](docs/HEALTH-ENGINE.md) on 8769 in separate terminals.
Do not start duplicate executors for an existing ledger. Missing services are
shown as unavailable; the frontend never substitutes sample account data.

For a production frontend:

```sh
npm run build
npm start
```

The build prepares Next.js standalone output with local fonts and public assets.
Webpack is selected explicitly because Turbopack's CSS worker could not bind its
local port in the verification environment. No private API is called at build time.
Browser requests use one origin; server-only upstream addresses may be configured
as shown in `frontend/.env.example`. Broker keys remain in the root ignored `.env`,
never in the frontend workspace or `NEXT_PUBLIC_*` variables.

Motion 14.6.0 is the standard UI animation library. Route and data loading states,
dialog transitions and connection notices respect system reduced-motion preferences
and the browser display setting. Canvas/Three.js scenes keep their existing drawing
algorithms and release resources on navigation. See [frontend ownership and verification](frontend/README.md).

## Persistent simulator

From this directory:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
ASTRAL_MODE=simulator ASTRAL_ENABLE_PAPER_ORDERS=true .venv/bin/uvicorn backend.app:app --host 127.0.0.1 --port 8766 --workers 1 --timeout-graceful-shutdown 5
```

Open **http://127.0.0.1:3000** after starting the Next.js frontend below. This mode never contacts Alpaca. It begins with $100,000 synthetic cash and zero positions. Quotes are synthetic; fills use a simple bid/ask model and a simulated 25-bps cash fee for crypto. It does not model real liquidity, partial-fill probability, queue priority or exchange calendars. Use Local buy/sell for controlled tests; there are no automatic random backend trades.

The book survives browser reloads and process restarts. Recording continues without an open browser. Use one process: a database lock prevents two executors sharing a book. Separate databases are enforced for Alpaca and simulator modes.

## Alpaca paper connection

Create your own [Paper Only account](https://docs.alpaca.markets/us/docs/paper-trading) and generate its separate paper credentials from **Home → API Keys → Generate New Keys**. Confirm the displayed endpoint is the paper endpoint. Keep keys in the local ignored `.env`, out of chat, screenshots, browser application forms and source code. Skip file creation if `.env` already exists; never overwrite configured credentials.

```sh
test -e .env || install -m 600 .env.example .env
```

Edit `.env` locally: set `ALPACA_PAPER_API_KEY` and `ALPACA_PAPER_SECRET_KEY`; leave `ASTRAL_MODE=alpaca` and `ASTRAL_ENABLE_PAPER_ORDERS=false`. Run:

```sh
.venv/bin/uvicorn backend.app:app --host 127.0.0.1 --port 8766 --workers 1 --timeout-graceful-shutdown 5
```

Confirm account equity/cash, positions, session, assets, quote freshness and reconciled orders before restarting with `ASTRAL_ENABLE_PAPER_ORDERS=true` for a controlled paper lifecycle. There is no live mode, arbitrary execution URL or funds-transfer route. Execution is fixed at `https://paper-api.alpaca.markets`; generic legacy keys are not silently reused.

Execution allowlist: BTC/USD, ETH/USD, SOL/USD; SPY, QQQ, GLD, TLT, IWM. This is engineering scope, not instrument advice. The active crypto Assets API also populates a separate discovery catalog, including other supported pairs; discovery never authorizes an order. Each is checked against venue metadata. Equity orders use whole shares and the regular session. Crypto uses venue increments, market/limit and GTC/IOC. Missing crypto precision disables that instrument. Equity IOC, fractional shares, brackets, stops and extended hours are not assumed.

The adapter polls REST: quotes every 5 seconds, reconciliation every 10 seconds, with bounded backoff, separate quotas, recovery capacity, API outcome records and 429 cooldown. These are application budgets, not provider entitlements. Verify IEX/SIP and account limits. Full broker WebSocket ingestion remains a later improvement. Sources: [order state](https://docs.alpaca.markets/us/docs/orders-at-alpaca), [client-ID lookup](https://docs.alpaca.markets/us/reference/getorderbyclientorderid), [equity quotes](https://docs.alpaca.markets/us/reference/stocklatestquotes-1), [crypto quotes](https://docs.alpaca.markets/us/reference/cryptolatestquotes-1).

## Risk and recovery

- Intent/client ID commits before POST. Repeating the same ID returns its state; changing its intent is rejected. An uncertain POST is never blindly resubmitted. A 404 lookup after a timeout leaves it uncertain and blocks new buys.
- Startup verifies account identity and reads orders/positions before new risk. The database binds to the first paper account observed. External working orders reserve exposure; this service does not cancel them.
- Observed partial fills deduplicate from cumulative order readback. Incremental prices derive from cumulative notional; these are not exchange execution IDs. Unknown fees remain unknown. Cancel requests retain reservations until terminal readback, including fills during cancellation. Limit expiry requests cancellation after 60 seconds by default.
- Orders need fresh quotes (15 seconds), recent account readback (30 seconds), valid metadata/session, sensible spread and available quantity. Future-dated quotes fail. Entry halt persists; sells remain subject to their own safety checks.
- First-release paper limits: $1,000 planned order notional ($100 for market orders); 50% gross exposure; 10% ETF/5% crypto per instrument; 25% economic group; four working orders before more buys are blocked. At a 1% UTC-day equity decline or 5% high-water drawdown, a persisted circuit latches and blocks new buys. A rebound, restart, midnight or the entry switch cannot clear it. Reviewed reset tooling remains future work; preserve the ledger. Cash-flow-adjusted performance is not available, so transfers can conservatively trigger a halt. These are illustrative controls, not guaranteed loss caps. Market fills can exceed sizing references. Shared unprotected full-value risk is capped at 0.5% of equity, swing at 0.25% and intraday at 0.10%, including holdings, pending buys and a cost reserve. These stricter budgets usually bind first. A local conditional exit monitor is available only by explicit server flag; it is not a native stop, cannot guarantee a fill and is disabled in shadow mode. Autonomous Alpaca strategy entries/exits remain disabled.
- Account restriction flags and crypto status must permit the order. New buys must fit local unreserved own cash and broker buying power. Broker buying power already includes its reservations, so only the new order is compared against it. Missing values block entries. Rounded limits stay inside their configured price collar.
- Alpaca equity change is labelled separately from profit: cash flows and complete historical fees are not reconciled yet. Broker valuation marks and execution quotes have distinct timestamps.

## Deterministic research algorithms

`backend/risk.py` is a pure Decimal calculator with fixed arithmetic precision and an explicit decision time. It has no network, clock, random or submission side effects. ATR14 uses the mean of the first 14 true ranges, then Wilder smoothing. Swing uses daily SMA20/SMA50; intraday uses five-minute SMA10/SMA30. A long candidate needs close above both ordered averages and above the previous 20 highs. Otherwise it returns hold or exit-review. These are research hypotheses, not validated trading edges.

Sizing divides a planned-loss budget (0.25% swing / 0.10% intraday equity) by ATR stop distance plus round-trip fees, adverse slippage and gap stress. Defaults assume crypto fees of 25bps per side, 10bps adverse slippage and an extra 1% ETF / 2% crypto gap. Cash and $1,000 notional caps further constrain quantity, which floors to venue increments. A candidate also needs positive modeled net target reward and net reward/stressed loss of at least 1. These arbitrary paper defaults are not optimality claims or loss guarantees.

`POST /api/risk/plan` accepts `{symbol, horizon, bars}` and records a research result with a version, input SHA-256, intermediate values and current execution-gate result. Every bar requires decimal-string OHLC/volume, symbol/source/feed/`adjustment:"raw"`, `at`, `closed_at`, and `known_at` timestamps. Swing needs at least 51 bars, intraday 31. Reject malformed, nonfinite, stale, future, unordered, mixed-source and zero-volume evidence. Intraday missing intervals are rejected for crypto and within an ETF session date. ETF daily bars allow a positive duration up to 24 hours; a full exchange-calendar adapter is still needed.

The planner endpoint accepts caller-supplied, unverified bars. The research worker additionally retrieves bounded daily history directly from Alpaca; automated intraday history is not connected. IEX volume is labeled exchange-only, not consolidated. Crypto daily history now derives exclusively from fully paginated Alpaca US executions, with exact price-times-size volume and immutable raw batches. The former mixed trade/midpoint candle veto is cleared for these verified batches. Crypto quote-size units now normalize only when a fresh same-venue orderbook matches the quote; stale/missing/mismatched books remain unverified. Exact raw snapshots and unit provenance are retained. The endpoint additionally requires a fresh connected account and quote. It never submits, even when a candidate passes. Stop/target references are **not protective orders**. Strategy inventory attribution and shared full-value risk budgets now apply. Realized fees must reconcile before strategy risk or timing can proceed; complete native protection and strategy validation remain outstanding. Learning promotions remain disabled.

Sources: [CME sizing](https://www.cmegroup.com/education/courses/trade-and-risk-management/proper-position-size), [Fidelity ATR](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/atr), [FINRA stop risks](https://www.finra.org/investors/insights/stop-orders-factors-consider-during-volatile-markets), [Alpaca account](https://docs.alpaca.markets/us/docs/account-plans), [paper assumptions](https://docs.alpaca.markets/us/docs/paper-trading).

Alpaca's [official MCP](https://alpaca.markets/mcp-server) can support interactive agent inspection/research. The official hosted paper endpoint is `https://paper-api.alpaca.markets/mcp`. It is not connected here. Enabling a separate MCP trading tool would bypass this application's risk authority; keep execution in the engine. Codex MCP OAuth does not automatically authenticate this Python REST adapter.

## Records, news, learning and cost

Private ignored `runtime/` databases use SQLite WAL/full synchronization and restricted permissions. For online backup, use SQLite's backup API rather than copying only the main database file:

```sh
.venv/bin/python - <<'PY'
import sqlite3
with sqlite3.connect('runtime/astral-alpaca.sqlite') as source:
    with sqlite3.connect('runtime/astral-alpaca-backup.sqlite') as target:
        source.backup(target)
PY
```

The ledger retains quotes/source/arrival times, equity snapshots, intents, risk vetoes with exact input snapshots, order states, observed fills, API outcomes and service errors. SSE reconnect replays event IDs; historical fills do not trigger fresh visual bursts.

News is off by default. After entitlement verification, `ASTRAL_ENABLE_NEWS=true` enables Alpaca metadata ingestion with IDs, source URLs, symbols, publication/update/first-seen times and revision history. Full-text rights are not assumed. Connected backend mode shows no fictional articles. SEC/issuer/macro/project adapters remain planned.

Learning records a decision dataset and provides an on-demand offline readiness/model-contract audit. No reconciled financial labels, trained policy, autonomous strategy changes or promotions are claimed. An opt-in evidence-only worker uses the signed-in local Codex CLI, `gpt-6.1-sol` with high effort, at most four attempts per UTC day per database and six-hour reuse only for identical evidence. It receives a minimal environment with no broker keys, tools disabled, a structured schema, timeout and output budgets. Source text cannot change execution authority. The actual connected abstention used 23,192 input / 406 output tokens; per-run subscription USD attribution is unknown. Private accounting inputs keep subscription budgets, employer funding and actual billing transactions separate. Direct model API calls remain $0; CLI usage is not asserted to be free or unlimited. Hosting/data charges remain unknown. See `reports/Paper trading bot architecture.md` for the broader design and conditional budget.

## Local API and deployment

`GET /api/health` distinguishes process liveness from broker readiness. `GET /api/state` supplies the dashboard; `/api/events` streams ledger IDs/state with `Last-Event-ID` recovery. POST controls: `/api/orders`, `/api/orders/{client_id}/cancel`, `/api/halt`, `/api/reconcile`, `/api/risk/shadow`, `/api/research/run` and `/api/exits`. Shadow mode forces broker writes off; an API field cannot override that setting. They require the same origin and `X-Astral-Intent: paper-only`.

Bind to loopback. Host/origin checks and no wildcard CORS are not multi-user authentication. Do not expose the API directly to the internet. A remote deployment needs authenticated ingress, secrets, backups and external monitoring. Supabase is unnecessary for this single-process milestone; managed Postgres can be considered when deployment/concurrency requires it.

`Dockerfile`, `frontend/Dockerfile` and `compose.yaml` provide separate Python application, intelligence, health and Next.js services. Only the frontend publishes a loopback port (3000); the Python services share the retained private runtime volume. Credentials go only to the application service:

```sh
docker compose up --build -d
```

The Compose environment comes from ignored `.env`. Docker deployment was not executed here. A laptop can sleep; local success does not prove 24/7 availability. An always-on host, authenticated remote ingress and external alerting have not been provisioned.

## Verification

```sh
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
npm run lint
npm run typecheck
npm test
npm run build
npm run test:e2e
```

This machine's macOS Python 3.13 readline extension crashes pytest before collection. The verified process-local workaround changes neither the application nor machine configuration:

```sh
.venv/bin/python - <<'PY'
import sys
sys.modules['readline'] = None
import pytest
raise SystemExit(pytest.main(['-q']))
PY
```

The test suite covers persistence/accounting, concurrent idempotency, lost responses, unknown lookups, halt/sell, stale/future data, cash/exposure/loss checks, partial fills, cancel races/expiry, account/mode binding, local API boundaries, missing credentials, fixed hosts, 429 cooldown, provider rejection, metadata refresh, event replay, exclusive executor ownership, exact ATR arithmetic, reproducibility under changed ambient precision, bad bars, cost hurdles, lot sizing, account restrictions, buying-power reservations and circuit latching. Use the final review check receipt for the tested target, exact test count and result. One dependency deprecation warning remains in Starlette's httpx test client.

`evidence/verification.json` distinguishes local tests/crash recovery from the separately completed broker-paper lifecycle. Alpaca paper omits market impact, queue priority and latency slippage; its fills do not validate profitability. Docker/remote deployment, protective orders, autonomous strategy profitability and automated learning remain unverified.

## Research and stress laboratory

`ASTRAL_ENABLE_SHADOW=true` requires paper orders disabled and records independent risk probes plus deterministic timing decisions; it does not reserve a simulated portfolio or submit trades. `ASTRAL_ENABLE_RESEARCH=true` enables daily-history/news evidence packets; `ASTRAL_ENABLE_CODEX_RESEARCH=true` separately opts into the bounded CLI reviewer. Verified upcoming event calendars are not connected: unknown coverage vetoes every live selection rather than being interpreted as no event. News metadata alone is insufficient. Each proposal records observed spread/volume, planned amount, sizing explanation, sources, decision time, expiry and vetoes. The UI exposes these packets, timing outcomes, inventory differences, the discovery catalog and token usage.

See [the dogfood procedure and failure matrix](docs/DOGFOOD.md) for the bounded connected experiment, model limits, realistic cost tests, no-model baselines and release gates. New suites cover ownership/reservations, delayed fees, readonly adapters, malformed/injected model output, evidence cache invalidation, crypto bar semantics/depth, and no-hindsight timing. The first 90-second connected session was entirely read-only and every candidate abstained. It found a retained 0.000000774 BTC quantity difference, with the broker flat and no confirming fee activity yet; it remains unresolved. No paper performance is presented as proof of edge.

An eight-hour live-data shadow observation can be run against the existing local lab with `scripts/overnight_watch.py --hours 8 --interval 60`. It checks read-only permissions each minute, audits broker request outcomes and new local intents, records quote health, vetoes and timing decisions, and writes private hash-linked checkpoints plus `runtime/overnight-latest.json`. On macOS, a bounded `caffeinate -i -t 28800` wrapper prevents idle sleep. This does not survive a closed lid, power loss or network outage; the receipt exposes gaps and does not claim fills or profit.

The Next.js dashboard merges Alpaca/Benzinga news with the independent public intelligence collector on port 8768 through same-origin Route Handlers. Sources shows HTTP status, freshness and poll intervals for 21 public feeds. Filing metadata and official project announcements are connected; extracted financials, issuer holdings, on-chain data and complete calendars remain unconnected. See [local intelligence setup and boundaries](docs/INTELLIGENCE.md).

The first overnight baseline was ended early at the user's request, with 335 verified hash-linked checkpoints and no observed gaps or broker writes. Its database is frozen privately. A separate one-minute connected shadow run recorded 71 broker GETs and no writes; diagnostic timing now retains the pre-inventory-gate decision while keeping the final veto. See [stage 2 results and pilot readiness](docs/STAGE2-READINESS.md).

See [the delivery and experiment roadmap](docs/ROADMAP.md) for the retained follow-ups: historical data, one frozen forward-tested strategy, research-driven paper testing, the second horizon, learning, tax/cost accounting, local reliability and eventual real-money gates.

The user-authorized [$25 automated execution experiment](docs/EXECUTION-PILOT.md) completed one broker-paper BTC round trip on October 25, 2026. This separate lifecycle test does not waive research strategy gates; its observed equity change was -$0.17 with fees still unclassified. The research-driven trade is the next distinct experiment, not claimed as executed.

Portfolio execution mechanics, read-only replay operations and remaining validity limits: [PORTFOLIO-REPLAY.md](docs/PORTFOLIO-REPLAY.md). Modeled fills never enter the Alpaca fill ledger.

Current fee, depth, liquidity and event evidence: [READINESS-GATES.md](docs/READINESS-GATES.md). The dashboard exposes each gate without overriding the frozen strategy.
# Event and liquidity follow-up

See [the separate liquidity experiment](docs/LIQUIDITY-EXPERIMENT.md) for
versioned quote-only comparison, new public event sources, remaining coverage
gaps and the distinction between model feasibility and trade authorization.
