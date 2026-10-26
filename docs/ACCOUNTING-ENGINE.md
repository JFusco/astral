# Accounting engine: first local proof

Implemented October 25, 2026 in `backend/accounting_engine.py`. This is an
on-demand audit of retained paper/simulator records and explicit cost inputs.
It does not need LEAN or a QuantConnect subscription. It runs separately from
the health engine, operational telemetry and offline learning audit.

Open **Accounting** in ASTRAL's main navigation (`/accounting`). It is a
child page with the same shared logo, sidebar and header as Overview and App
health. `GET /api/accounting/report` reads the latest verified saved report for
the running application's ledger and mode; it never starts an evaluation or
contacts a broker. Private invoice references, funding notes and lot IDs stay
out of the page summary. The page labels the report cutoff and unknown results.
**Refresh report** rereads that saved snapshot; it is not live reconciliation.

Accounting owns money reconciliation. Telemetry supplies usage, attempts,
durations and token receipts; token counts do not establish a subscription bill.
Learning may eventually consume reconciled accounting outcomes through an
explicit adapter. This proof exports no learning labels.

## Run

Provide an explicit cutoff with a timezone, no later than the current time:

```sh
.venv/bin/python -m backend.accounting_engine \
  --source-ledger runtime/astral-stage2.sqlite \
  --as-of '<ISO timestamp with timezone>' \
  --costs-file runtime/accounting-inputs.json
```

The source opens with SQLite URI `mode=ro`, `query_only=ON` and one consistent
read transaction. There is no broker, network, model, subscription or trading
interface. It never loads `.env`. Each run creates a new private directory under
`runtime/accounting-evaluation/`, with an input/source-hash contract saved before
evaluation, JSON/Markdown reports and source CSV exports. Existing runs remain.

## What the report establishes

- Validated positive fills are matched FIFO within each symbol and book:
  manual, swing, intraday, external or unknown. A sale cannot borrow another
  book's lot. Invalid fills, unknown owners/sources and unmatched sells remain
  visible; gross results are incomplete when those occur.
  Retained `lifecycle_test` orders use the manual book, as in current inventory
  attribution; their original strategy ID remains in the fill export.
- Gross lot matches use retained fill values before fees. Alpaca cumulative
  order deltas are identified as order-readback evidence, not individual venue
  execution IDs, certified tax lots or independently reconciled cost basis.
- Custody compares gross fills, confirmed asset fees and measured gross-to-net
  reductions against the current broker snapshot. The snapshot must be USD,
  at/before the cutoff and at most 60 seconds old. Saved order-decision contexts
  and new custody checkpoints retain historical quantity evidence. They do not
  establish complete account history. See [gross-to-net reconciliation](GROSS-TO-NET.md).
- Pending/invalid fees and disputed fee revisions remain issues. Asset debits
  affect quantities only; cash fees are separate. No fee is guessed from a
  residual or deducted twice. Exact unexplained quantities remain in the report.
  Measured reductions retain an unclassified status until linked provider fees
  explain them. The report can show matching net quantities while still requiring
  review. Previously saved version-one reports remain untouched; version two
  requires a fresh read-only report before the application accepts that result.
- Equity change is an observed balance difference. Realized net P&L, unrealized
  P&L and cash-flow-adjusted profit remain unknown in this proof, including when
  quantities match. There is no completeness contract for historical fees,
  deposits/withdrawals, transfers or authoritative basis yet.
- Confirmed expense records, estimates, recurring subscription budgets and
  included allocations are separate. Currency totals stay separate without
  inferred exchange rates. Bundled allocations cannot exceed their parent bill
  and are not added to that bill again. Duplicate/conflicting bill identities
  are rejected. Unknown amounts stay unknown.

## Private operating-cost inputs

`runtime/accounting-inputs.json` is ignored by Git. Keep receipt contents,
account identifiers and credentials out of source files. `source_ref` is a
reference to retained evidence or an explicit user confirmation, not a secret.
This minimal shape records no expenses and makes no completeness assertion:

```json
{
  "version": 1,
  "charge_coverage_complete": false,
  "subscription_coverage_complete": false,
  "charges": [],
  "subscriptions": []
}
```

A subscription record needs `id`, `provider`, `status` (`active`, `proposed`,
`cancelled` or `unverified`), `billing_interval` (`monthly` or `annual`),
`billing_amount` (decimal string or null), `currency`, `known_at` and a
`source_ref` for a known amount. Optional `personal_fraction` and `astral_fraction`
are decimal strings from 0 to 1; both default to 1. Annual budgets divide by 12.
`funding_note` retains reimbursement context. Optional `next_renewal` is an ISO
timestamp. Proposed/unverified plans are not active spending.

Employer-covered subscriptions can use `personal_fraction: "0"` to exclude
that budget from personal ASTRAL costs while retaining gross budget evidence in
the private input/report. A funding assertion is not a paid invoice or an actual
reimbursement transaction. Personal billed amounts and funding notes stay in
ignored local inputs. QuantConnect billing remains unverified unless separately
confirmed; a proposed price is not evidence of a purchase.

A charge needs `id`, `provider`, `status` (`confirmed`, `estimated` or `unknown`),
`amount` (decimal string or null), `currency`, `incurred_at`, `known_at` and a
receipt `source_ref` for confirmed amounts. Optional `role: "included_allocation"`
requires `parent_charge_id` pointing to a confirmed same-provider/currency bill.
Only confirmed parent/ordinary charges enter recorded actual subtotals. Overall
actual totals remain unknown unless the user asserts complete charge coverage,
with no unknowns or estimates. Monthly budget completeness is separately asserted
and requires known active amounts and no unverified subscription entries.

Confirmed ordinary charges can also include an optional `receipt_url` pointing
to a message in Gmail over HTTPS. Accounting shows the provider name and an
**opens Gmail in a new tab** link. Sign in to Gmail to view the source email and
download its receipt or invoice attachments. Local filesystem paths, arbitrary
websites, embedded credentials and redirect URLs are rejected. Raw references,
charge IDs, funding notes and attachment contents remain private. Older saved
reports without receipt links still work. This does not create a tax-ready export.

These assertions cover the supplied input set; they are not independent evidence
that every subscription or expense was discovered. Per-run model USD attribution
is separate from recurring budgets. Employer funding is not a tax deduction
determination. This proof does not assign expenses to tax forms.

## Remaining work

Obtain authoritative fee/custody evidence; add separately validated transfer,
cash-flow, opening-lot and provider execution adapters; reconcile basis and fees
before enabling net results or a learning-label adapter. Add actual invoice,
credit and reimbursement transactions when source evidence exists. Define
complete coverage periods and reporting/export contracts as separate follow-ups.
Source CSVs and gross lot matches are preparation records;
no tax filing or tax-lot certification is implemented.

Verification covers read-only access, cutoff exclusions, book isolation, partial
FIFO matches, unresolved residuals, confirmed/pending asset and cash fees,
unknown net results, budget reimbursement, duplicate/bundled costs, currencies,
invalid amounts, deterministic arithmetic and private reproducible exports.
