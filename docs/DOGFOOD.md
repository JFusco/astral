# Paper research and failure testing

This milestone tests operational correctness. It does not establish that the strategy makes money. All autonomous Alpaca strategy orders and learning promotions remain disabled. The local lab uses a backup of the original paper ledger; it never clears the unresolved fee difference or resets performance to improve results.

## Reproduce the bounded connected session

With the existing ignored `.env` configured, run from this project:

```sh
.venv/bin/python scripts/dogfood_session.py --seconds 90 --with-model
```

The script creates `runtime/astral-dogfood.sqlite` through SQLite's backup API if it does not already exist. It will not overwrite an existing lab. Stop any service using that lab first. Credentials stay server-side. The session forces broker orders and exit monitoring off; it asserts zero broker writes and zero new local orders. Omit `--with-model` for deterministic screening alone. The model option uses the signed-in local Codex CLI and shared subscription limits; it is not free or unlimited usage. Its four-attempt UTC-day ceiling is **per database**, not an account-wide spending guarantee. Avoid parallel lab copies to evade that budget.

`runtime/dogfood-latest.json` retains the private receipt. The first actual 90-second run on October 25, 2026 completed 91 GETs, zero writes, zero new local orders, 80 risk probes (all veto), and 144 timing observations (all wait). Its one `gpt-6.1-sol / high` review used 23,192 input and 406 output tokens, including 224 reasoning tokens. Exact subscription USD attribution is unavailable. News metadata was accessible. No candidate qualified. This receipt predates the additional crypto candle/depth guards and catalog discovery; it is not proof of their connected behavior.

The broker was flat, but the retained fill ledger differed by 0.000000774 BTC. No fee activity had yet confirmed the cause. This remains an unresolved reconciliation finding, not a write-off or confirmed fee. Strategy entries and strategy timing wait for reconciliation.

## Three independent decisions

1. **Selection:** correct venue identity; current tradability; quote freshness and spread; observed liquidity; completed, point-in-time history; symbol news; verified upcoming event coverage. Each packet carries its sources, arrival times, proposed amount, sizing reason, vetoes and input hash. Unknown event coverage blocks selection. Crypto quote-size units are currently unverified, and Alpaca's mixed trade/midpoint candles cannot prove the current trade-breakout hypothesis.
2. **Timing:** a frozen deterministic rule evaluates entry, hold or exit using evidence known at the decision time. Entry permission expires. A replay executes only at a subsequent quote and stresses gaps, latency, fees and slippage. Intraday history is not automatically acquired yet; live intraday signals wait. A replay's synthetic fill is never reported as a broker fill.
3. **Size and execution:** Decimal arithmetic rounds down to venue increments. Price, own cash, pending orders, group exposure and strategy ownership are checked again. With no verified native protection, reserve the full value: at most 0.5% shared equity, 0.25% swing and 0.10% intraday, including existing holdings and pending purchases. ATR stop references cannot reduce those budgets. A model cannot raise a budget, remove a veto or place an order.

## Failure scenarios and their proof

| Failure | Required behavior | Current proof |
|---|---|---|
| Timeout after accepted POST; crash before response | Retain uncertain intent; query only; never repeat POST | Synthetic adapter/restart tests |
| Fill during cancel; rejected readback after acceptance | Keep reservation until terminal readback | Synthetic partial/cancel and acceptance tests |
| Two strategies own the same coin | Own-sleeve fills and pending sells cannot consume the other's inventory | Concurrent reservation and sleeve tests |
| Fee arrives late or in the purchased crypto | Idempotent activity import; unresolved/ambiguous differences block strategies | Fixture fee tests; real discrepancy intentionally retained |
| Stale/future/crossed quote or history | Abstain; retain timestamps | Risk, screening and timing tests |
| Midnight, restart or rebound after a loss breach | Persist the loss latch | Circuit/restart tests |
| News contains tool instructions or fabricated evidence | Treat as data; reject unsupported picks/numbers/IDs | Adversarial review tests; tool-disabled CLI |
| Model emits malformed output, calls a tool, times out, duplicates a pick or exceeds budget | No accepted picks; consume bounded attempt | Mock worker and schema tests; one real structured abstention |
| Calendar or evidence changes under cached reasoning | Invalidate review fingerprint | Fact, calendar and revision tests |
| Midpoint high is mistaken for an executed trade | Veto trade-based breakout | Crypto candle-semantics test |
| Quote-size units missing or depth zero | Veto depth-based selection | Units/depth tests; normalized adapter pending |
| New meme listing or duplicate/malformed identity | Discovery only; no expanded execution permission | Catalog tests; full contract/on-chain metadata adapter pending |
| Price gaps through a stop | Execute at later available quote; do not assume stop-price fill | Timing replay tests; native protection unverified |
| Learning sees an outcome from the future | Require resolved-at cutoff and isolated training/test sets | Learning and promotion disabled; future training tests still required |
| Fee/queue/latency optimism produces apparent profits | Report stress results and compare baselines | Quote replay tests only; historical fill model still incomplete |

## Establishing an edge comes next

Freeze crypto day and swing experiments separately: 5m/15m day hypotheses and a 4h swing hypothesis. Capture real trades/quotes/depth and point-in-time news/events prospectively, including inactive/delisted assets. Keep the first research catalog broad; shortlist only pairs with usable venue liquidity and evidence, including meme coins when the same tests pass. Never use later news, revised macro releases or a modern model's future knowledge to explain earlier decisions as though it had known them then.

Compare each strategy with cash, a simple no-model rule and a suitable market benchmark, at equal risk and actual fee assumptions. Count every attempted parameter choice. Use chronological walk-forward folds with purging/embargo for overlapping holdings, then an untouched holdout and forward paper period. Stress maker-to-taker conversion, nonfills, partials, 2x/3x observed spreads and slippage, 5/30/120-second delays, API outages and correlated selloffs. Track net expectancy, drawdown, turnover, capacity, fill quality, tail loss and stability across folds and regimes. A fixed number of days or a high win rate alone is insufficient. Promotion thresholds must be registered before inspecting holdout results; no automatic promotion exists.

Tax analysis remains advisory. A proposed hypothetical tax ledger should show pretax and estimated after-tax wealth, explicit marginal-rate assumptions, known/unknown basis, disposal fees and wash-sale exposure. It must never delay a protective exit. Alpaca lot selection must not be assumed. See the source-linked tax report in the workspace.

## Boundaries

The local conditional exit monitor is opt-in and depends on the running process, fresh data and venue acceptance. An IOC can expire or partially fill, which requires attention; the monitor never promises a stop-price fill or silently resubmits an uncertain exit. It is disabled in shadow sessions. The service on a laptop is not proven 24/7 operation. Always-on hosting, authenticated ingress, external alerts, complete event data, realistic fills, tax-lot accounting and strategy performance remain release gates.

## Overnight observation

The eight-hour watcher reads the existing localhost lab, with no order-control route. Every minute it verifies paper/read-only/shadow configuration, verifies model calls and local exits remain off, audits ledger request outcomes including lost responses, and records feed freshness, inventory, selection vetoes and timing. It writes hash-linked, synchronized checkpoints and an atomic private `runtime/overnight-latest.json`. Missing service or market data produces a degraded sample; unsafe configuration or a new local intent fails the experiment. A stopped watcher is detectable by the last checkpoint timestamp; it cannot alert while the whole host is unavailable.

On macOS, the actual run uses a bounded `caffeinate -i -t 28800` wrapper around `.venv/bin/python scripts/overnight_watch.py --hours 8 --interval 60`. Keep the Mac powered, online and its lid open. The wrapper only prevents idle sleep. The underlying read-only lab continues after the recording window; this is not cloud uptime proof. In the morning inspect status, gaps, request methods, new intents, inventory differences and last checkpoint before judging the run. Shadow probes are independent checks, not an executable strategy or simulated account return.
