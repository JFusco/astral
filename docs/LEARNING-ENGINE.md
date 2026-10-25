# Offline learning proof

The first learning engine is an on-demand audit of retained evidence and model
research. It does not train a policy or improve a trading strategy automatically.
The [agreed engine boundaries](ENGINE-BOUNDARIES.md) separate it from risk,
health, telemetry, accounting and broker execution.

Run from the project root with an explicit UTC cutoff:

```sh
.venv/bin/python -m backend.learning_engine \
  --source-ledger runtime/astral-stage2.sqlite \
  --as-of 2026-10-25T18:30:00+00:00
```

Choose an actual cutoff at or before the current time. The command creates a
unique `runtime/learning-evaluation/run-<id>/` with `contract.json`, `report.json`
and `report.md`. Files are private local artifacts, never broker ledger rows.
No `.env`, credential, model, broker or network interface is loaded. Existing
SQLite sources are opened with URI `mode=ro`, `query_only` and a read transaction.

## What the report evaluates

1. **Data and outcomes:** inventory available, late, malformed and protected
   records; classify execution approvals, vetoes and research-only observations.
   A risk approval or fill is not a profit/loss label. Net P&L labels require a
   reconciled accounting adapter, which this first proof does not implement.
2. **Model research contracts:** distinguish completed, skipped, failed, cached
   and duplicate receipts. Recheck supplied citation IDs, copied numerical
   claims, vetoes, thesis fields and decision/pick consistency. Report temporal
   problems separately from contract conformance. A quote source timestamp alone
   is not an explicit receipt/known-at timestamp.
3. **Model usefulness readiness:** report the absence of matched, reconciled
   model-versus-no-model outcomes. Do not assign a return, win rate, predictive
   skill score or causal benefit from an abstention or a small sample.

The first proof intentionally produces no training rows or financial outcome
labels. It reports readiness and missing evidence; it does not silently choose
an outcome horizon, cost assumptions, retrospective labels or a comparison arm.
Valid model contracts can still lack complete time evidence, comparable outcomes
or known cost. Those are independent findings.

Recorded token usage and any explicit actual USD amounts are summarized only
for evaluated, deduplicated receipts. Cached input tokens are reported separately
as a subset, not added to total input tokens. Unknown USD attribution remains
unknown; this is not the platform's subscription accounting or an invoice.

## Protected evidence and reproducibility

Both registered forward manifests are hash-checked. Their time windows remain
reserved even after November 8; the audit has no release/override flag. Exclusion
is deliberately conservative across all symbols and horizons. Only identity,
time and count metadata is inspected for protected rows; their payload bodies
are not selected for evaluation. Model completions after cutoff or inside a
protected window cannot be scored.

The source selection fingerprint binds admitted records and excluded metadata
up to the cutoff. The contract records that fingerprint, cutoff, source mode,
evaluator/dependency hashes, holdout hashes and the outcome-definition limitation
before evaluation. The report has its own content hash. Future-row counts are
snapshot inventory metadata; they may increase on a later run while the selected
input fingerprint stays unchanged. No raw prompts, headlines, account balances
or model rationales are copied into the output.

The audit is not a strategy holdout result, paper execution acceptance test,
financial reconciliation, production acceptance or profitability claim.

## Next learning work

After accounting supplies a separately specified reconciled outcome contract,
register a horizon/cohort and equal-risk, comparable no-model baseline. Keep
paper, hypothetical and price-only diagnostics separate. Chronological splitting,
purge/embargo rules, challenger evaluation, drift checks and human promotion/
rollback remain separate milestones. No automatic promotion or risk changes are
part of this engine.
