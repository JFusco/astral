# Prepared fee-accounting questions for Alpaca

Draft only. Nothing has been sent. Keep keys and account identifiers out of
public messages. Exact private order/activity IDs are retained in
`runtime/gate-investigation-readback.json` if support needs them securely.

Please confirm crypto PAPER fee posting and precision behavior for a same-day
BTC/USD round trip. We observe eight execution activities across four filled
orders on October 25, 2026. Gross quantities/values agree with order readback.
Custody is flat, while gross buy-minus-sell quantity totals 0.000001555 BTC.
The general activities endpoint and specific CFEE/FEE endpoints return no fee
records yet. A 0.25% buy fee rounded upward per partial execution would explain
the amount, but we have not treated that calculation as a confirmed fee.

1. Are crypto paper asset/cash fees posted through CFEE/FEE for this account?
   What posting timezone/window and trade-date versus creation-date filtering
   should we use? Is any newer Trading API endpoint required?
2. What exact asset precision and rounding rule apply per partial execution?
   Does gross order `filled_qty` intentionally exceed received position quantity?
3. Will fee records include order or execution identifiers for strategy/lot
   allocation? How are corrections, refunds and pending/executed states represented?
4. If these paper fees are omitted from activity history, what authoritative
   record or documented accounting contract can reconcile custody and cash?

No reset, dust write-off or inferred fee adjustment has been applied.
