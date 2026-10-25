# First frozen strategy and prospective research journal

Current experiment: `btc-daily-swing-v1`. The experiment is a research-only BTC
baseline at Alpaca US; ETH/SOL/ETF screens remain diagnostic candidates outside
this frozen single-symbol experiment. A proposal cap is not order authorization.

## Contract and observations

The manifest in `experiments/btc-daily-swing-v1.json` fixes SMA20/SMA50,
prior-20-high breakout and Wilder ATR14. Planning uses a 2 ATR stop reference,
2 times stop-distance target, ten-day maximum hold, 25bps/side assumed fees,
10bps adverse round-trip slippage and 2% crypto gap stress. Sizing is the minimum
of ATR loss budget, own cash, full-value risk cap, verified depth cap if available,
and the experiment's $25 notional cap; quantity rounds down. The manifest/code
hashes are checked, and code drift adds a hard veto. Confirmed broker fees are
still unavailable, so fee assumptions are explicitly unverified.

`backend/experiment.py` records an append-only SQLite `experiment_observations`
row keyed by manifest and research-packet hash. Each includes the packet, source
revisions and arrival times, exact numerical sizing, context, underlying timing
and final inventory veto. Duplicate packets do not add observations. Packets
created before registration or without the matching experiment identity are not
enrolled. No historical timestamp is rewritten to create a prospective record.
Code drift is retained visibly; it cannot authorize a trade. No model is run.

New timing observations include `deterministic_arm` action/reason from packet
eligibility, alongside the existing model-gated result and inventory diagnostic.
A model pick is an additional gate for the model-assisted arm only. Recording
the deterministic arm changes no final action, inventory veto or permission;
past observations are not rewritten. Adapter provenance includes cached local
source file hashes, not an attestation of the separate collector's loaded code.

This journal does not simulate positions, reserve hypothetical cash, calculate
P&L or certify exits. Its 14-day minimum is an observation requirement, not a
statistical edge threshold. A separate portfolio mechanics replay now exists, with a fixed future window;
real queue/impact/fee validity and adequate forward coverage remain explicit gates. No automatic promotion is available.

## Historical diagnostic

The retained 100-day BTC execution dataset yielded 50 price-only prefixes after
50 warmup bars: 46 hold, one entry candidate, three exit-review. Each prefix
uses at most 90 bars, exactly like the live price calculation. Altering a future
bar cannot change prior prefix results. Missing, unordered, invalid or unfinished
bars are rejected. The data had already been inspected; it is not an untouched
holdout. Actual observation time remains attached, and no historical point-in-time
news, quote, queue, cost or fill availability is assumed.

Private receipt: `runtime/btc-daily-swing-v1-history-diagnostic.json`.
`runtime/frozen-research-latest.json` contains the connected check; unique
`runtime/research-cycle-*.json` files retain each manual check without replacement.
Raw history batches and live research packets remain in the existing stage-2 DB.

## Local operation

The dashboard runs at `http://127.0.0.1:8766/`, the public collector at port 8768.
The current dashboard process runs deterministic research every 900 seconds;
orders, exits, model calls and continuous shadow probes are disabled. History
reuse requires complete executed-trade provenance, age under 25 minutes and an
end timestamp covering today's UTC boundary. It never refreshes the batch's
known-at timestamp. Quotes/account readback refresh after history retrieval so
slow history downloads cannot silently reuse pre-download executable prices.

If doing a manual bounded check, stop the dashboard cleanly first, then run:

```sh
ASTRAL_MODE=alpaca ASTRAL_DB_PATH=runtime/astral-stage2.sqlite \
ASTRAL_ENABLE_PAPER_ORDERS=false ASTRAL_ENABLE_EXIT_MONITOR=false \
ASTRAL_ENABLE_SHADOW=false ASTRAL_ENABLE_RESEARCH=false \
ASTRAL_ENABLE_CODEX_RESEARCH=false .venv/bin/python scripts/research_once.py
```

That command acquires the same exclusive database lock, snapshots the ledger,
blocks broker submit/cancel methods, performs GET-only evidence/fee readback,
and records order/fill counts before and after. It never runs a model, starts
background workers or changes credentials/risk settings. Restart the dashboard
with the explicit read-only flags after it finishes. Do not run a second executor
against the same ledger.

The Mac must stay awake/online. Startup/recovery service, external missed-heartbeat
alert, verified backups/restore and full forward portfolio remain outstanding.
The old overnight observer and chat polling automation remain stopped.

## Current trade vetoes

The frozen v1 screen requires a top-level verified calendar. Per-category proofs
cannot qualify v1, even when every category passes readiness checks. Its unknown
calendar veto remains. The follow-up is a separately registered v2 with a new
manifest and source hashes, a new prospective window, and a screen consuming
`readiness.calendar_coverage`. That successor is neither implemented nor approved;
it must never relabel v1 results or reuse its window as untouched future evidence.

First connected packet at 11:09:59 UTC on October 25, 2026:

- BTC signal: exit review, no entry candidate.
- Same-venue observed 20-day mean dollar volume about $205,875; below the unchanged
  $1m research threshold. Other venues' liquidity cannot clear an Alpaca order.
- Crypto quote-size units/depth unverified.
- Upcoming financial/protocol/macro coverage incomplete. FOMC is scoped only;
  BLS calendar returned HTTP 403 and no access workaround was attempted.
- Gross ledger BTC balance 0.000001555 versus broker zero; no authoritative
  CFEE/FEE rows yet. No synthetic adjustment or new baseline was applied.

The recorded proposal was about $25 because the experiment cap bound sizing.
A proposed amount with a veto is not a recommendation, approval or executed trade.

See [PORTFOLIO-REPLAY.md](PORTFOLIO-REPLAY.md) for the separate hypothetical execution model, fixed evaluation window and retained data gaps. The original BTC manifest and source hashes remain unchanged.
