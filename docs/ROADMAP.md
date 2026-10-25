# ASTRAL delivery and experiment roadmap

This is the working follow-up list, reconciled with the architecture, risk,
crypto, AI-failure and tax reports. The project is local and paper-first. A
successful execution experiment is not strategy or profitability validation.

| Order | Work | Current state | Acceptance evidence |
| --- | --- | --- | --- |
| 1 | One $25 BTC execution experiment | Completed one confirmed $24.9863 entry and exit; flat, equity change -$0.17; fees unclassified | One capped entry, short timed hold, confirmed exit/flat custody, order IDs, latency, costs and recovery receipts |
| 2 | Verified execution history | Connected and verified: BTC 93,735 / ETH 34,350 / SOL 25,611 executed trades, 100 completed daily bars each | Fully paginated same-venue trades, immutable raw batches, source/known-at timestamps, no midpoint candles or fabricated missing bars |
| 3 | Accounting and research eligibility | Fee evidence still pending; fresh same-venue quote/book units validated; FOMC/BEA scoped coverage added; liquidity and complete calendar gates remain closed | Confirmed fee/asset adjustments, verified quote units/depth, venue liquidity, scoped event calendars and usable point-in-time news |
| 4 | Freeze ONE strategy and its experiment | BTC daily swing v1 frozen with code/manifest hashes, $25 proposal cap, no-model baseline and acceptance contract; not forward-validated | Register exact code/data/model versions, symbol universe, fees, sizing, entry/exit rules, window and pass/fail thresholds before evaluation |
| 5 | Backtest and prospective shadow for that frozen strategy | 50 price-only prefixes; isolated portfolio execution model and 16 synthetic stress scenarios implemented; fixed future window collecting. Real queue/impact/fee validity and sufficient forward evidence remain outstanding | Chronological train/validation/untouched holdout, next-observable-quote fills, retained nonfills and rejects, realistic costs and sample/regime coverage |
| 6 | First research-driven PAPER trade | Explicit user objective after execution proof; not enabled | Fresh qualified evidence and sizing explanation, all risk gates, bounded single-position pilot and confirmed exits |
| 7 | Compare decision and execution quality | Comparison contract below; no causal/profitability claim yet | Equal-risk no-model baseline and model-assisted arm; same evidence timestamps and costs; pre-registered analysis |
| 8 | Add the second horizon | Swing and intraday calculators exist separately; connected intraday collection and validation are incomplete | Independent strategy budget, synchronized portfolio accounting, no cross-sleeve liquidation or double spending |
| 9 | Learning layer | Dataset recording only | Resolved-outcome labels, point-in-time cutoff, purged/embargoed splits, offline challenger evaluation, drift checks and reviewed promotion/rollback |
| 10 | Reliable local unattended operation | Live dashboard/feeds work while Mac is awake; durable order state exists | Login/startup service, bounded process recovery, external missed-heartbeat alert, tested disconnect/reboot recovery, backups and restore drill |
| 11 | Tax and cost accounting | Source-linked research and partial telemetry exist | Tax-lot and fee adapters, cash-flow-adjusted P&L, explicit hypothetical tax assumptions, worker token/time/cost budgets and unavailable-cost labels |
| 12 | Broader assets/venues and real money | Discovery catalog exists; no new automatic authorization | Verified token/contract identity, unlock/security and on-chain data, exit feasibility, venue-specific adapters, Georgia/account eligibility and separately authorized capital deployment |

## First frozen strategy

Use the existing daily swing hypothesis as the first reproducible baseline:
ATR14 Wilder, SMA20/SMA50, prior-20-bar breakout, with the existing fee/slippage/gap
hurdle and capped sizing. Do not tune it after seeing a favorable paper result.
Its conservative maximum holding period is ten days; this is a swing experiment,
not a long-term investment claim. Define a shorter pilot holding contract
separately if needed; do not call a 20-second execution test a daily swing test.

The second experiment can use five-minute intraday data and SMA10/SMA30 with
independent registration and validation. The crypto report also proposes 15-minute
and four-hour hypotheses. Those remain separate future experiments, not silent
parameter replacements or a search for whichever chart looks profitable.

## Comparing execution-only and research-driven runs

The user selected the execution test FIRST, then a research-driven paper trade.
The first asks whether the machinery submits once, respects the amount/price
bounds, reconciles partial fills, survives uncertainty and returns flat. The
second additionally asks why this ticker, time and amount qualified and what
would invalidate the thesis.

Record symbol, strategy/experiment version, decision and quote timestamps,
spread/depth and volume scope, evidence revisions, candidate and veto reasons,
requested/filled quantity, order status history, partials/nonfills, submission and
fill latency, exit trigger, realized/unknown fees, cash flows, equity change,
model version/effort/usage and worker time/cost.

Use repeated comparable sessions and an equal-risk deterministic no-model arm to
assess the incremental research layer. Account for market exposure, time of day,
volatility, liquidity, turnover and costs. Comparing one 20-second BTC test with
a later swing trade cannot isolate research skill. Neither a few wins nor a
fixed number of days establishes an edge. Retain abstentions and failed trials.

## Stress work still outstanding

- Portfolio cash/reservation/partial/cancel mechanics now have an isolated replay.
  Venue queue priority, actual replenishment, impact, hidden outage fills and
  verified fee semantics still need validation; independent risk probes are not
  a portfolio experiment.
- Repeated connected recovery exercises, not just synthetic crash/unknown-order
  tests; no live stop-price execution guarantee.
- Liquidity shocks, maker-to-taker conversion, 2x/3x spreads, adverse fees,
  partial fills, gaps, 5/30/120-second delays, rate limits, outages and correlated
  selloffs, with equal-risk baselines and chronological holdouts.
- Evidence/strategy/model drift, forged news, stale/revised calendar notices,
  unsupported symbols, delistings, ambiguous token identities and prompt injection.
- A learning policy may not change numerical risk limits, authorize a ticker,
  promote itself, or delay a protective exit for a tax or narrative preference.

## Additional data follow-ups

The 21 public sources provide bounded metadata and operational context. They are
not comprehensive financial statements, ETF holdings, on-chain analytics,
verified protocol/unlock calendars. Scoped context is now attached to research
packets; remaining adapters and their coverage/freshness contracts remain explicit
work. The broad research reports remain dated evidence, not current provider
acceptance.

## October 25 follow-up: frozen baseline is recording

`experiments/btc-daily-swing-v1.json` fixes the BTC hypothesis, $25 research
proposal cap, code hashes, no-model baseline, assumptions and acceptance
conditions. It was frozen before this diagnostic, but the price dataset had
already been inspected during adapter development. It is development data,
not an untouched holdout. Changing the registered strategy code produces a
visible drift veto; replacing the experiment registration in the same ledger
is rejected. Existing historical packets cannot be enrolled as new prospective
observations.

The first diagnostic covered 100 daily bars with 50 chronological prefixes:
46 holds, one raw entry candidate, three exit-review signals. It uses the same
price-indicator function as live planning. No fills, fees, cash balances,
returns or historical news availability are inferred. This is an implementation
and signal-frequency diagnostic, not the realistic backtest in row 5.

The first connected research journal entry was recorded at 11:09:59 UTC
(07:09:59 Eastern). BTC had an exit-review signal and five vetoes. There were
zero new orders/fills. The fresh fee readback returned zero CFEE/FEE records;
the gross BTC ledger residual is 0.000001555 BTC while the broker is flat.
It remains unresolved. Public context now includes the next FOMC meeting dates,
with source arrival/revision evidence. BLS calendar access returned HTTP 403;
no bypass was attempted. That calendar and remaining event categories remain
unknown.

The local dashboard now enables deterministic read-only research on a 15-minute
interval. Orders, model calls, exits and the old continuous shadow probes remain
disabled. The first 14 days is a minimum observation window, not a profitability
pass or automatic promotion. Only observed decisions are enrolled; no restart
backfill. Running requires this process and Mac to stay awake and online.

### Historical implementation sequence (October 25, 2026, before the replay)

1. Obtain authoritative fee/asset-debit evidence and verify quote depth units;
   preserve unresolved differences until then. Confirm venue-appropriate
   executable liquidity without importing another venue's volume to pass a gate.
2. Complete scoped event adapters and retain coverage failures. FOMC dates alone
   do not establish BLS/BEA/Treasury/protocol/unlock/issuer coverage.
3. Add a standalone portfolio replay using retained executable quotes/trades,
   cash reservations, partial/nonfill rules and fee/spread/latency stress. Keep
   it distinct from this no-fill prospective journal and synthetic harness.
4. Review chronological holdout and prospective evidence; only then permit one
   qualified research PAPER position with validated exit supervision.
5. Compare the equal-risk model-assisted arm, add five-minute intraday separately,
   then implement offline learning/challenger review. Learning cannot promote
   itself, change risk limits or delay exits. Reliability, tax lots, worker
   costs and broader-venue work remain rows 10–12 above.

See [FROZEN-STRATEGY.md](FROZEN-STRATEGY.md) for operations and evidence.

## Portfolio replay follow-up

The offline execution model now covers cash reservation, partial/nonfills,
IOC/GTC outcomes, fee-in-cash/base scenarios, bounded entry/exit retries,
price collars, delays and cancel/fill races. Sixteen synthetic mechanics scenarios
run separately from observed-market replay. The initial recorded-data report
had 224 quote arrivals, two research packets, zero hypothetical orders/fills,
one 55.236-second quote-arrival gap and retained timing/boundary exclusions.
These are infrastructure observations, not profitability evidence.

The forward evaluation window is registered from October 25 at 11:30:31.730361
UTC through November 8 at the same UTC time. Its strategy/model code, baseline
sequence and cutoff cannot slide on restart. Reports refresh locally on startup
and every 15 minutes. Source inputs remain read-only, and modeled trades never
enter the actual fill ledger or animations. See [PORTFOLIO-REPLAY.md](PORTFOLIO-REPLAY.md).

Next acceptance work is authoritative fee and depth evidence, event coverage,
validated venue execution assumptions and adequate prospective/holdout samples.
Current zero-eligibility data cannot establish timing or selection skill. The
second horizon and offline learning remain deferred until the first strategy's
acceptance conditions are satisfied; no automatic promotion is available.

## Gate implementation follow-up

See [READINESS-GATES.md](READINESS-GATES.md) for the connected evidence and exact path to the first research PAPER trade. Fee retrieval now preserves old unresolved fills and confirmed-record revisions. New quote/book validation clears the size-unit veto only for fresh matching snapshots. BEA adds GDP/PCE schedule context and retained scoped category proofs alongside FOMC. The original liquidity thresholds are unchanged and still reject current BTC conditions; the top-level cap also falls below the venue minimum, producing a zero-sized proposal. Fees, missing calendar categories, no qualifying entry and research exit supervision remain explicit gates. No orders or model calls were enabled.

## Event sources and separate liquidity hypothesis

See [LIQUIDITY-EXPERIMENT.md](LIQUIDITY-EXPERIMENT.md). NY Fed key BLS releases,
Alpaca upcoming/active maintenance and official protocol documents now have
explicit adapters. Maintenance can clear its published-list category; scoped BLS
and protocol watches cannot certify complete calendars. The separate BTC
liquidity experiment compares the unchanged baseline with a $25 two-sided-depth
and turnover model, retains seven cost/depth shocks, and records only future
quote observations in its own database. It cannot remove an original veto.

## Remaining gates and next steps

- Obtain authoritative fee/custody evidence and reconcile the residual without
  synthetic adjustments or relaxed tolerances.
- Complete full BLS and scheduled-protocol coverage; maintain fresh paired venue
  maintenance evidence. Partial sources cannot certify complete categories.
- Retain the original-liquidity failure and absent buy signal as PAPER NO-GO
  gates. The separate liquidity hypothesis cannot clear the original thresholds.
- Follow up with a separately registered v2 calendar screen consuming
  `readiness.calendar_coverage`, new source/manifest hashes and a new prospective
  window. It is neither implemented nor approved; v1 results remain v1.
- Profile full-window replay and SSE/REST state paths on a synthetic temporary
  ledger at the expected window size (about 240,000 quote events): record wall
  time, peak RSS, event-loop/quote-worker delay and state response latency during
  replay. Measure before any cadence or architecture change; scheduling stays
  unchanged in this repair.
- Plan a separate LEAN benchmark of the frozen signal and execution assumptions,
  with matched inputs, costs and chronological cutoffs. No installation or
  benchmark result is claimed here.
- Complete independent repair recheck and then review sufficient prospective
  evidence and validated exit supervision before a bounded research PAPER pilot.

These follow-ups clear no product gate and authorize no trades or promotion.

## Connected-service health and provider updates

User requirement added October 25, 2026: check the health of every service ASTRAL
depends on and stay current with provider changes, including QuantConnect,
OpenAI/Codex and Alpaca. This section is planned work, not a claim that new
monitoring, alerts or scheduled checks have been implemented.

Acceptance requirements:

- Maintain an inventory of actual dependencies and the features they support:
  broker/account reconciliation, market data, news/calendars, local services,
  LEAN/Docker, QuantConnect entitlement and optional model research. Distinguish
  connected, not configured and intentionally disabled features. A disabled
  model worker is not an availability failure or a successful connection test.
- Combine official component-level incident/maintenance reports with bounded
  read-only checks of the connection and data ASTRAL actually uses. Display
  provider status and local observations separately, with checked-at and
  last-success times, freshness limits, latency and actionable errors. Missing,
  stale or unavailable status evidence means unknown, never implicitly healthy.
- Start with [QuantConnect status](https://status.quantconnect.com/),
  [OpenAI status](https://status.openai.com/) and
  [Alpaca status](https://status.alpaca.markets/), reusing the existing Alpaca
  status/maintenance collection and worker/source freshness checks. Add new
  dependencies as they are connected; avoid duplicate polling. Respect each
  provider's rate limits and use bounded timeouts/backoff.
- A green aggregate status page cannot overrule a failing local operation.
  QuantConnect's October 25 payment-configuration error is an unresolved user
  checkout failure even while its public status page reports services online;
  that page does not list payment processing separately. A rendered payment
  form alone does not verify payment processing, entitlement or CLI access.
- Surface incidents, maintenance, local failures, stale feeds and recovery in
  the dashboard. Notify for new actionable changes and recovery; deduplicate
  repeated errors and avoid no-change alerts. Clearly label stale retained
  results and collection gaps, including when the Mac sleeps or loses network.
- Track official release notes, API/schema changes, deprecations, model/CLI
  compatibility and pricing/entitlement changes with source links and dates.
  Review their impact on our pinned versions and actual usage. Do not silently
  upgrade software, change providers, purchase extras or alter frozen sources
  and manifests in response to a vendor update.
- Health probes must not place test trades, submit payments, enable disabled
  workers, run paid model calls or expose credentials. Failures must preserve
  existing entry vetoes and inventory/order uncertainty; recovery must not
  automatically enable orders, relax risk limits or promote a strategy. Verify
  exit/reconciliation behavior separately before unattended paper execution.

Define and verify monitoring/notification cadence as part of implementation.
No background monitoring or external notifications were enabled by this note.
