# Agreed engine boundaries

User direction, October 25, 2026: combine offline data/outcome evaluation and
model-research evaluation, and agree on boundaries before implementation.
The user approved this contract on October 25, 2026. It does not enable a worker or authorize
model calls, orders, strategy promotion, subscriptions or tax filings.

## Responsibilities

| Engine | Owns | Does not own | Current implementation |
| --- | --- | --- | --- |
| Risk | Deterministic eligibility, sizing, exposure, loss limits and entry vetoes | Model judgment, automatic policy changes, a guarantee of fill/exit prices | Existing rules in `backend/risk.py`, with enforcement and broker guards in `backend/engine.py` |
| Health | Assess availability, freshness, incidents and recovery from observations; maintain its own heartbeat | Performance/cost accounting, order authority, enabling workers after recovery | Separate `backend/health_engine.py` process and ledger |
| Telemetry | Record operational measurements: worker activity, durations, attempts, tokens, usage, errors and data lineage | Decide profitability, infer invoices from token counts, change trading behavior | Existing events, worker observations and usage receipts; not yet a separate complete subsystem |
| Accounting | Reconcile fills, fees, custody and cash flows; calculate realized/unrealized P&L and platform costs; retain lot, invoice and export records | Invent missing fees, declare expenses deductible, delay protective exits or alter risk rules | On-demand gross/custody/fee proof in `backend/accounting_engine.py` (see ACCOUNTING-ENGINE.md); no complete net P&L, basis completeness or tax-ready export |
| Learning | Offline outcome evaluation and model-research evaluation with explicit evidence limitations | Live strategy changes, risk overrides, automatic promotion, broker execution or unscheduled model calls | Decision/evidence recording plus the on-demand offline audit in `backend/learning_engine.py`; no training or promotion |

The `experiments/gate-data-adapters-v1.json` and `-v2.json` manifests record
adapter source hashes at registration only. No code enforces them, and they do
not describe later versions of those files.

These are responsibility boundaries, not a requirement to build five services.
Keep each proof as small as it needs to be. Strategy, research and broker
execution continue to use their existing deterministic enforcement paths.

## Learning: two separate evaluations

### 1. Data and outcomes

- Read retained source data through SQLite `mode=ro` and a consistent read
  transaction. Write only to a separate local evaluation directory/ledger.
- Register the dataset identity, venue, strategy/horizon, explicit evaluation
  cutoff, evaluator/source hashes and outcome definition before evaluating.
- Keep intraday and swing cohorts separate. Compare only the same venue and
  compatible decision/execution assumptions. Preserve rejects, nonfills,
  abstentions, missing observations and unresolved inventory.
- Respect known-at times and require a resolved outcome to exist by the cutoff.
  Approval is an execution/risk decision, not a profitable outcome. A later
  price change is a diagnostic markout, not an actual trade return.
- Broker-backed paper outcomes, hypothetical replay results and price-only
  diagnostics must stay in separate cohorts. Use accounting-backed reconciled
  records for net P&L labels. Missing costs mean unknown net results.
- Protect both registered November 8 forward windows from learning/tuning.
  Report only their registration/count metadata, not evaluation outcomes. Window
  completion alone does not release the holdout or permit reuse as training data.
- Missing labels or too little comparable evidence produce an explicit
  insufficient-evidence result. Do not create synthetic wins/losses to fill gaps.

### 2. Model research quality

- Evaluate existing model receipts only. Disabled, skipped, failed, cached and
  completed runs have distinct counts; cache reuse is not an independent trial.
- Start with deterministic checks: citations refer to supplied evidence;
  numerical claims match; picks respect vetoes; decision and picks agree; a
  rationale, counter-case and invalidation are present; evidence existed at the
  decision time. Passing those checks does not prove the factual truth or
  predictive value of the narrative.
- Separately assess usefulness using matched no-model decisions, comparable
  horizons, equal risk/cost assumptions and resolved outcomes. Do not compare
  different exposure or retrospective evidence as though it measured model skill.
- Report abstentions, unavailable outcomes and costs alongside completed picks.
  Do not manufacture a benefit score or causal claim from a small sample.
- Keep subjective reasoning review and any additional model-based judging out
  of the first proof. Those would need a separately specified rubric and budget.

## Authority and first acceptance check

The first implementation should be an on-demand offline report, not training
or an autonomous decision loop. It cannot write to trading/intelligence ledgers,
change frozen files, fetch new market data, launch a model, call a broker, loosen
limits or deploy/promote a strategy. This first proof needs no QuantConnect or
LEAN entitlement. It does not clear research-driven paper execution gates.

Acceptance: a reproducible report shows input identity/cutoff, protected windows,
usable and excluded evidence with reason counts, data/outcome readiness, model
contract quality and model-usefulness readiness. Tests should prove look-ahead
and holdout exclusion, cache/skip handling, rejected false labels and source
read-only behavior. A report with no evaluable model/outcome pairs is a valid
readiness finding, not a learning-success or profitability claim.

The eventual training/evaluation split, purge/embargo rules, challenger search,
drift criteria and human promotion/rollback process are separate milestones.
No self-promotion or numerical risk-limit changes will be delegated to learning.

## Non-LEAN work after agreement

1. Build the bounded offline learning report described above.
2. Define accounting inputs and a small reconciliation/cost proof; keep the
   existing 0.000001555 BTC difference unresolved until authoritative evidence
   explains it. Preserve all existing ledgers and cost assumptions.
3. Complete BLS/scheduled-protocol coverage and validate research dispatch/exit
   supervision before applicable paper execution is enabled.
4. Continue the existing prospective windows; resolve fee/custody and liquidity
   gates independently. Do not retune the frozen strategy to create eligibility.
5. Retain health release/deprecation surveillance, external alerting and local
   recovery as follow-ups. Production cleanup, broad performance optimization
   and wiki setup stay deferred as requested.
