# Stage 2 results and automated paper-pilot readiness

Observed October 25, 2026. No real-money trading. No new broker paper orders.

## 1. End and preserve the baseline

The user ended the overnight observer early at 10:22:11 UTC. Its 335 checkpoint
hash chain was recomputed successfully. The saved run includes 16,500 broker GET
requests, zero broker write/order/fill events, zero API/worker errors and zero
observed unavailable or degraded-crypto samples. These are sampled observations,
not proof there were no failures between checkpoints. This is not an eight-hour
completion. The trading service was then stopped, including continuous probes.

Private retained evidence:
- `runtime/baseline-20261025-final.json`
- `runtime/overnight-20261025T044703.jsonl`
- `runtime/baseline-20261025-frozen.sqlite`

The frozen ledger can contain service events after the last observer checkpoint;
its freeze time and the checkpoint timestamps remain distinct. No ledger history
was reset. Intelligence collection continues separately on port 8768.

## 2. Reconcile against broker records and inspect downstream decisions

A fresh GET-only readback retrieved all four execution activities for the two
historical BTC orders: two partial executions on the buy and two on the sell.
Their quantities and execution values agree with cumulative order readback.
There are no broker positions. Both general activity and explicit CFEE/FEE
queries returned no fee rows.

| Quantity | BTC |
| --- | --- |
| Gross buy executions | 0.000309121 |
| Gross sell executions | 0.000308347 |
| Residual gross ledger quantity | 0.000000774 |
| Confirmed asset-fee activity | 0 |
| Current broker position | 0 |

A 0.25% buy fee rounded UP at 0.000000001 BTC separately for each partial execution
would total exactly 0.000000774 BTC. This is an arithmetic hypothesis. The
rounding rule is not independently verified, and it is not a confirmed broker
fee. Do not insert a synthetic CFEE record, relax tolerances, adopt a new baseline
or describe the inventory as matched. Alpaca documents credited-asset fees and
potentially delayed fee posting: https://docs.alpaca.markets/us/docs/crypto-fees.
The absence of fee rows today does not establish zero fees or explain a posting
schedule for this account. The discrepancy remains blocked pending authoritative
fee evidence or a documented, verified accounting contract.

`backend/reconciliation.py` performs this analysis without mutating inputs,
writing adjustments or granting execution authority. Its result is retained in
`runtime/reconciliation-analysis.json`; detailed broker responses remain in
private `runtime/reconciliation-readback.json`.

A new one-minute connected shadow run used a COPY of the frozen database. It
recorded 71 broker GETs, zero writes, zero new local orders, 56 new risk probes,
and 96 timing evaluations. Before the inventory veto, 36 crypto evaluations
waited for a qualified research pick and 60 ETF evaluations rejected stale quotes.
No symbol qualified. The engine now retains that underlying decision alongside
the final inventory veto, so the next barrier is visible without disabling the
first one. No hypothetical successful order or fill is reported as executed.

Private receipt: `runtime/stage2-connected-final.json`.

## 3. Fault and decision-path tests

128 local synthetic tests pass, including 15 new cases. New coverage includes:

- Missing fee confirmation never becomes a reconciled balance; exact arithmetic
  matches are still hypotheses. Confirmed fee and execution IDs deduplicate.
- A synthetic evidence-qualified selection reaches a buy candidate, then reaches
  a stop exit. A real-data eligibility claim is not inferred from that fixture.
- An underlying synthetic buy candidate remains a final WAIT when inventory is
  inconsistent. Diagnostic visibility never overrides a risk veto.
- 24 concurrent same-intent retries after an accepted-but-lost response produce
  one simulated submission and one recorded fill.
- Eight seeded orderings, 48 partial/duplicate readbacks each: cumulative quantity
  never rolls backward, duplicates never add fills, regressed readbacks raise
  reconciliation errors without changing stored state.
- An armed synthetic exit waits through disconnected broker readback, then submits
  exactly once after recovery.

Existing cases also exercise cancel/fill races, stale exits, crash/restart exits,
unknown submissions, fee/slippage/gap costs, look-ahead prevention, expiry,
concentration, strategy ownership and shared risk budgets. This is not a queue,
market-impact, load-capacity or profitable-strategy validation. One existing
Starlette test-client deprecation warning remains.

Per-case receipt: `runtime/stage2-test-results.json`.

## 4. Automated paper-pilot decision: NO-GO

Local fault tests pass. Current connected execution readiness does not.

| Required condition | Current result |
| --- | --- |
| Ledger and broker inventory agree with confirmed adjustments | Blocked: BTC quantity difference |
| Crypto trade-bar semantics verified for breakout strategy | Blocked: current bars may contain quote midpoints |
| Crypto quote sizes normalized to verified asset units | Blocked: units unverified |
| Adequate observed execution-venue liquidity | Current BTC/ETH/SOL screen fails the $1m daily-volume threshold |
| Verified event coverage for the pilot symbol and holding window | Blocked: no complete supported calendar |
| Current qualifying strategy entry | None in the short connected run |
| Production strategy execution and exit supervision validated | Still shadow-only; explicit execution gate remains |

Proposed first pilot AFTER those conditions pass: one BTC/USD long-only spot
position, at most $25 entry value, one open order at a time, bounded limit orders,
one round trip, a 15-minute observation window and a five-minute maximum holding
period. New entries stop on stale data, uncertain order state, reconciliation
failure or the pilot risk cap. Exit behavior requires continued monitoring and
confirmed readback; a local stop cannot guarantee the loss amount or execution
price. No leverage, shorts, meme coins, multiple strategies or unattended
continuation in this initial pilot.

Those pilot-specific caps are a proposed acceptance contract, not enabled or
claimed as implemented controls. Before activation, enforce them server-side,
prove their expiry/restart behavior and verify the final configuration. Existing
paper strategy execution remains hard-blocked. No extra approval is being sought
for a bypass; unresolved evidence must be supplied and checked first.

The local dashboard resumes in read-only observation mode against the separate
stage 2 copy. Continuous shadow probes, research/model workers, exit monitoring
and paper orders are disabled. Account/quote/news/fee readbacks continue. The
completed baseline stays frozen.

## Subsequent user-authorized execution experiment

After this no-go assessment, the user explicitly selected a separate $25 BTC
execution test before a research-qualified trade. That mechanical experiment
completed one confirmed round trip with flat custody and a -$0.17 equity change.
It did not clear research-strategy gates or classify fees. See
[the execution receipt](EXECUTION-PILOT.md) and [the retained roadmap](ROADMAP.md).
The project now resides at `/Users/joe.fusco/Projects/astral-trading`.

## Current research follow-up after the mechanical test

The earlier readiness table is historical. The executed-trade daily-bar adapter
has since been connected and verified, clearing the candle-provenance blocker
for those batches. The BTC daily v1 experiment is frozen and its read-only
prospective journal is recording every 15 minutes. Scoped public context and
FOMC dates now appear in research packets. All eight current symbols remain
ineligible; inventory/fees, quote units, venue liquidity and complete event
coverage remain unresolved. The latest BTC signal is exit review, not entry.

The current paper-order, exit and model flags remain OFF; deterministic research
is ON. This is not a restart of the stopped overnight observer or chat polling.
See [the frozen contract and first result](FROZEN-STRATEGY.md).
