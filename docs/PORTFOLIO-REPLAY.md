# Offline portfolio replay and fixed forward evaluation

This is an execution model, not a broker execution service. Every modeled fill
is labeled HYPOTHETICAL. No replay fill enters the `fills` table, broker stream,
portfolio balance or universe fill animation. The strategy manifest remains
`btc-daily-swing-v1` with its original hash and rules.

## What is implemented

`backend/portfolio_replay.py` is a deterministic Decimal portfolio calculator.
It owns a separate hypothetical $100,000 starting balance, BTC quantity, order
reservations and position exit references. These balances are scenario inputs,
not the user's Alpaca account balance or earnings.

- A $25 maximum entry fits proposed quantity/notional and unreserved cash. Worst
  bounded buy value plus the assumed cash fee is reserved before any modeled fill.
  Partial fills release only unused reserve; no new buy can double-spend it.
- A fill needs a strictly subsequent, fresh, already-arrived quote, enough modeled
  depth in verified base-asset units, elapsed latency and a price inside the
  order collar. Repeated/out-of-order quotes cannot regenerate fill capacity.
- Each distinct quote supplies at most 1% of displayed side depth by default.
  This is a hypothetical participation ceiling, not executable-volume or queue
  evidence. Fresh quotes with validated `size_unit="base_asset"` can support
  hypothetical replay fills, subject to every other timing, depth and risk gate.
  Missing, stale or mismatched books leave quote units unverified and cannot fill.
- Bounded limits use the fresh ask plus at most 10bps for entry and fresh bid
  minus at most 10bps for exit, rounding inside the collar. IOC/GTC are separate
  scenarios. IOC partial/nonfills terminate the remainder. Default TTL is 60s.
  At most three entry attempts per evidence packet and three exit orders per
  position prevent unbounded retry loops. Remaining inventory stays visible.
- Default modeled latency/cancel latency are 5s each. A cancel request retains
  cash and exposure until its modeled acknowledgment. Fills may race with a
  cancel, including after the evidence expires; expiry cannot undo an order.
- Assumed fees can debit quote cash on both sides, or base asset on a buy and
  quote cash on a sell. These are stress assumptions. They do not resolve the
  missing Alpaca CFEE/FEE evidence or establish the provider's rounding rule.
  Unsellable dust remains inventory; it is never silently written off.
- Position stop/target references remain the original proposal's references;
  later research cannot rewrite them. Exit evaluation uses the frozen timing
  function. A stop crossing triggers an exit decision, then needs a later
  eligible bid inside its limit. It never fills at an unavailable stop price.
- Entry halt, code drift, inventory disagreement, missing/expired evidence,
  pending broker orders and missing signals remain vetoes. Protective exit
  evaluation for hypothetical held inventory does not require a new entry pick.
- Missing observations/disconnects cannot create fills. Final cash, reserve,
  quantity, pending orders, quote freshness and unliquidated exposure are retained.
  Marked equity/drawdown are hypothetical diagnostics, not reconciled realized
  profit or an execution-price guarantee.

The model enforces conservation at every event: cash and inventory never go
negative and reserved cash cannot exceed cash. Full live portfolio risk checks
remain the research packet's qualification prerequisite; this model does not
replace the live risk engine or certify production exit supervision.

## Recorded data and fixed future window

`backend/replay_runner.py` opens the existing trading SQLite ledger using URI
`mode=ro` and `PRAGMA query_only=ON`. It imports recorded BTC quote arrivals and
registered prospective packets, preserving decision, arrival, source and expiry
times plus hashes. It does not load `.env`, broker tools, model workers or a
network client. Unknown/unobservable inputs and gaps are retained in coverage
receipts. Previously inspected history is not reclassified as unseen data.

`experiments/btc-forward-holdout-v1.json` fixes the future window and code hashes:

- Starts October 25, 2026 at 11:30:31.730361 UTC.
- Ends November 8, 2026 at 11:30:31.730361 UTC.
- Original event-sequence boundary is retained. Restarting cannot slide dates,
  silently replace the registered code or backfill unobserved decisions.
- This is a monitored prospective evaluation, not a hidden historical holdout.
  No policy tuning or learning promotion occurs. Fourteen days alone is not
  adequate statistical proof. Trade/regime coverage and costs need review.

The manifest exclusion "Actual crypto depth units remain unverified" is an
immutable historical statement from registration. Later validated base-asset
quotes do not rewrite that exclusion, earlier inputs or the registered contract.

The first report used 224 recorded quote arrivals and two research packets from
the original strategy registration. It produced zero hypothetical orders/fills.
It exposed a 55.236-second collection gap during the earlier service restart,
a boundary quote predating the window and a quote unobservable at arrival.
Those are retained data-quality limits. They are not converted into smooth
backfilled data or a successful trading result.

The separate future window began empty. Its later coverage is measured from
actual arrivals. If the frozen rules never qualify, the correct result is zero
trades and insufficient strategy evidence, not forced entries or weaker limits.

## Stress matrix and tests

Sixteen deterministic synthetic scenarios cover baseline mechanics, 3x/8x fees,
2x/3x spreads, 10bps adverse slippage, 30/120-second delays, IOC partial fills,
zero depth, a base-asset buy fee, disconnect/recovery, a price gap, research expiry,
entry halt and GTC partial/cancel races. Synthetic returns are not market results.
The model does not infer probability of execution from these fixtures.

Tests additionally cover cash exhaustion, duplicate/conflicting events, future
quotes/evidence, stale source timestamps, future-prefix invariance, fixed exit
references, bounded retries, asset-fee dust, code drift, immutable future cutoffs,
and report isolation across ledgers. A test caught a globally loaded replay
report appearing in an unconfigured book; the dashboard now requires its own
ledger's matching report receipt before exposing replay results.

## Local operation and retained receipts

Run a report from the project root:

```sh
.venv/bin/python scripts/portfolio_replay.py
```

The registered window already exists. `--register-holdout` creates it only when
missing and never replaces an existing contract. Reports are serialized with a
separate replay lock; the trading service can continue read-only observation.
Each report writes `runtime/portfolio-replay-<UTC>.json` plus an atomic latest
summary. The ledger remains the input source. Scheduled reports retain compact
ledger totals and the latest 30 hypothetical orders/fills; complete source
inputs, code hashes, input hash, snapshot sequence, coverage and fixed cutoff
permit reproduction. No incomplete result is presented as complete if the
300,000-event safety budget is exceeded.

When deterministic research is enabled, the dashboard refreshes this offline
report on startup and every 15 minutes. Only the owning trading ledger records
the report filename as display metadata; the replay worker itself never writes
the trading DB. No paper-order or model flag is enabled. A stale report retains
its own timestamp; it is not represented as a live calculation.

## Remaining limits before strategy acceptance

Real queue priority, depth replenishment, market impact, hidden fills during
outages and provider fee rounding remain unvalidated. The simulator supplies
hypothetical cancel acknowledgments, not observed exchange acknowledgments.
Depth units require fresh same-venue validation for each quote. No historical full-news/quote archive was
invented, and no complete 100-day executable backtest is claimed. Real-money
and automatic research PAPER execution remain disabled. The broader fee,
liquidity/calendar, exit-supervision, second-horizon, learning, tax and reliability
work remains in [ROADMAP.md](ROADMAP.md).
