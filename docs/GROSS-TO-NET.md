# Reconcile gross fills with net crypto custody

ASTRAL preserves gross traded quantity separately from the crypto quantity received. A broker custody checkpoint can establish a reduction without establishing its fee classification. Unclassified or ambiguous reductions continue to block strategy execution.

## How the calculation works

`backend/custody.py` compares two account-bound custody checkpoints with the gross buy fills between them. It calculates the observed reduction as starting custody plus gross buys minus ending custody. It uses no fee rate or assumed rounding rule.

The calculation accepts a single local buy order and one strategy owner for each asset interval. It requires consistent order identities, complete recorded cumulative quantities and checkpoints at most 60 seconds apart. The opening checkpoint precedes submission; the ending checkpoint follows terminal completion and receipt of every cumulative fill and terminal order update. Cumulative REST receipt timestamps cannot establish when each partial fill executed: an intermediate position may already include part of a later delta. Without a complete order window, attribution is declined. Each checkpoint must be recorded within 15 seconds of its snapshot. Another working order, overlapping order, external owner, conflicting checkpoint or missing execution prevents automatic attribution. Nonzero starting custody remains part of the calculation.

A checkpoint received more than 15 seconds late is excluded from arithmetic and retains a review issue, even when other valid intervals establish reductions. Account conflicts and negative receipt lag still invalidate the evidence. Terminal orders overlap until their status-specific completion, cancellation or expiry timestamp; missing terminal timestamps remain open-ended. A terminal state effective or recorded after the accounting cutoff retains a review issue and cannot establish a historical reduction.

A fill timestamp outside its order's terminal window declines attribution for that order and retains an order-specific review issue. The order and fill still participate in overlap checks; unrelated valid reductions remain available. Order identity, side and symbol conflicts still invalidate the evidence.

Legacy approved order observations already contain account snapshots. New paper-service reconciliations append a `custody_snapshot` event when position quantities or order fill states change. These events survive restart, retain the original snapshots and do not rewrite fills. The same transaction saves the last signature and checkpoint sequence IDs in `custody_checkpoint` state. Live reads use these primary keys instead of scanning quote history, and unchanged polls do not append duplicate checkpoints. No schema migration or historical adjustment is required.

Inventory exposes gross books, net books and the checkpoint references behind each observed reduction. Accounting reports expose gross quantities, net quantities, the remaining unexplained difference and the classification status. A zero unexplained quantity does not establish complete fee accounting, net profit or tax basis.

## Handle delayed fees without double-counting

An executed negative CFEE record with an explicit matching broker order ID replaces the corresponding measured reduction up to its confirmed amount. The calculation deducts only the remaining unclassified amount. An exact linked fee can classify the reduction; a partial linked fee leaves the remainder unclassified.

Provider fee dates are interpreted as midnight UTC without changing the stored activity. Accounting exports retain the original date and identify day precision; they do not imply an intraday receipt timestamp. A historical cutoff before the next UTC midnight retains a review issue for that date-only fee. Inventory applies one read-time cutoff to both fees and reduction classification, including fees received after the last custody snapshot. A future-dated fee is excluded from current arithmetic and retains a review issue. Accounting reports retain their explicit historical cutoff.

An unlinked fee cannot safely establish overlap by amount alone. For that asset, the calculation applies recorded fees and suppresses additional measured debits while preserving a review issue. An excessive linked fee also requires review. These cases can leave an unexplained quantity, but they cannot silently charge the same observed reduction twice.

A same-asset fee linked to another order can also overlap a measured interval. If that fee is not fully covered by its own unambiguous measured reduction, an overlapping timestamp or UTC date makes allocation ambiguous. Ambiguous reductions cannot establish coverage for their linked fees, so overlap propagates through affected intervals before additional debits are calculated. Independent, unambiguous reductions retain their coverage. Each affected interval retains its measured evidence and review issue, with no additional debit or reassignment of the fee.

Gross fill rows and provider activity rows remain unchanged. No synthetic CFEE record is created. The existing inventory errors, readiness checks and server vetoes remain effective. Paper execution, model use and strategy promotion are not enabled by this change.

## Validate without changing the existing ledger

The custody analyzer and accounting source reader accept read-only SQLite connections. Inspect the existing ledger through `mode=ro` and `query_only=ON`; write any new report to a separate output directory. Do not instantiate the application Store or Engine against retained evidence for an audit.

The regression suite uses disposable synthetic ledgers. It covers gross buys followed by net sells, partial fills, nonzero starting custody, linked and unlinked fees, conflicting evidence, cutoff isolation, restart and repeated reads. Connected account evidence remains separate from those synthetic results.

The [Alpaca crypto fee documentation](https://docs.alpaca.markets/us/docs/crypto-fees) describes fees in the received asset. Its [trade-update contract](https://docs.alpaca.markets/us/docs/websocket-streaming) distinguishes execution quantity from total post-event position quantity. This implementation uses retained REST custody checkpoints; it does not introduce a trade-update stream or claim complete execution-event coverage.
