# BTC fee-classification review: complete

The historical `0.000001555 BTC` custody reduction is confirmed by provider-issued crypto fee records. No percentage, assumed rounding rule or synthetic fee was needed to establish the amount.

## What closed the review

The authenticated Alpaca paper account returned **eight executed CFEE events** through `GET /v2beta1/events/activities`. Alpaca documents [bounded historical replay for this endpoint](https://docs.alpaca.markets/us/reference/subscribetoactivitiessse). The earlier audits and ASTRAL's current collector queried the legacy `/v2/account/activities` endpoints, which still returned zero fee rows in this review.

At 2026-10-27 01:50 UTC, the bounded replay contained 19 events: eight trades, eight crypto fee records and three cash journals. A second replay of the exact same interval returned identical event IDs and payloads, with no parse errors or unfinished stream. Both observations are tied to the same paper account as the retained ledger.

| Reviewed order | Provider asset-fee entries | Total BTC fee |
| --- | --- | ---: |
| First BTC buy | 0.000000310 + 0.000000464 | 0.000000774 |
| Pilot BTC buy | 0.000000001 + 0.000000624 + 0.000000156 | 0.000000781 |
| Total | Five asset-fee records | **0.000001555** |

Those two totals match the independently retained pre-sell custody reductions exactly. Gross buys of `0.000620689 BTC`, minus gross sells of `0.000619134 BTC`, minus the confirmed asset fees leave **zero BTC**, matching broker custody.

The remaining three CFEE events report USD cash-fee amounts of `$0.03`, `$0.04` and `$0.07`, totaling **$0.14**. The earlier per-execution rounding hypothesis happened to match these records; it is no longer the evidence used for classification. A general fee-rate/rounding contract for future executions remains unproven and unnecessary for this historical finding.

## Cash must not be charged twice

In these provider records, each sell trade's `TRD.net_amount` already reflects its associated USD fee. The eight trade net amounts sum to `-$0.30`. The three cash journals net to `$100,000`; two offsetting journal entries contribute zero.

Therefore, the reported trade cash plus journal cash is exactly **$99,999.70**, matching the paper account. Subtracting the CFEE cash breakout again would incorrectly report **$99,999.56**. The fee entries establish the expense breakdown; they must not be blindly added as another cash debit alongside already-net trade amounts.

## Association limits retained

All eight trade `ref_id` values match the retained legacy execution IDs, and their quantities, prices, sides, client IDs and order IDs agree. Each fee has one unique trade candidate at the same execution microsecond; asset-fee prices also agree. The account traded only BTC/USD in the reviewed interval. These checks associate all eight fee records with the two round trips without selecting matches by expected fee amount.

However, the returned CFEE records contain **no explicit parent ID, order ID or instrument symbol**. Their `currency` field says USD even for nonzero asset-quantity fees. BTC quantity denomination is resolved from the isolated matching BTC execution and custody window, not by treating that currency field as the quantity unit. This is an auditable historical review association, not a general automatic allocation contract for concurrent or mixed-asset trading.

The [activity schema guide](https://docs.alpaca.markets/us/docs/activity-sse) describes fee-to-parent linkage, but these actual CFEE responses omit it. Any implementation must retain that absence and fail closed for ambiguous records.

## What remains in the application

The classification question is closed: **provider-confirmed crypto trading fees**, with the historical amounts reconciled. The remaining application work is a data-source integration.

`backend/broker.py:210` polls only the legacy fee endpoint. The running service has not been restarted, and the merged reconciliation code also needs a separately validated consumer for the new feed. Its current legacy CFEE contract cannot directly accept these rows: instrument/link fields are absent, and the same provider type represents both asset and USD cash fee breakouts.

Do not fabricate legacy CFEE rows, inject inferred order IDs, clear the inventory veto, or apply this report as a ledger adjustment. A future adapter should preserve the raw events and acquisition times, distinguish asset quantity from already-net cash, deduplicate and detect revisions, and retain uncertainty when links are missing. Historical execution times do not mean ASTRAL knew these records before this retrieval.

Net P&L, tax basis, learning outcomes and execution authority were not certified or enabled. There is no need to wait for another legacy fee-posting day or ask support to establish these eight historical fee amounts.

## Verification and preserved boundaries

- Both bounded provider replays returned the same 19 events. The first connected audit made 11 GET requests; the verification replay made one additional GET. No broker write or order was submitted.
- A second arithmetic check independently verified the fee totals, cash inclusion and eight unique clock associations using the replayed events.
- The affected custody/accounting/service suites passed **131 tests**; `npm run verify:push` passed. No implementation changed and no new full-CI or independent implementation-review result is claimed for this read-only review.
- Orders, fills, activities and observations remained unchanged. Protected strategy sources and experiment-manifest hashes matched. No Store or Engine was instantiated against runtime; SQLite connections used `mode=ro` and `query_only=ON`.
- Paper orders, automatic entries/exits, shadow and model use remained off. The running inventory veto remains in place. Main remains clean at `d0ef9fbe358bd2cf57b5ddd1354292a21f8936b1`.

Evidence: [classification decision](classification-review.json), [fee/execution associations](associations.json), [identical replay](replay.json), [second arithmetic check](independent-arithmetic-check.json), [affected test output](affected-tests.log), and [verification gate](verify-push.log). Original connected receipts are in the separate `outputs/classification-review-20261027T015027Z` directory; earlier evidence and handoffs were not rewritten.

Next work: implement and independently review the authoritative activity-feed consumer while preserving the ledger, frozen strategy, holdouts and all existing execution vetoes. Controlled activation remains a separate step.
