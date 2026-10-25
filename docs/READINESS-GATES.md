# Evidence needed for the first research-driven paper trade

Observed October 25, 2026. The four gates are now visible in the dashboard's
**BTC / FIRST RESEARCH TRADE → Gate evidence** dialog. No broker orders or model
calls were enabled. A green component does not authorize a trade.

Subsequent work: [LIQUIDITY-EXPERIMENT.md](LIQUIDITY-EXPERIMENT.md) adds NY Fed
key BLS context, explicit Alpaca maintenance coverage and official protocol
watches, plus a separate liquidity hypothesis. This report's initial connected
readback below is preserved; it does not represent the newer source count.

| Gate | Implemented work | Connected result | What remains |
| --- | --- | --- | --- |
| Fees/custody | Old-fill-anchored fee retrieval, provider record validation, immutable revisions and a conflict latch | Eight execution activities match four orders; broker flat; no CFEE/FEE rows; gross BTC residual 0.000001555 | Authoritative fee/debit evidence; no synthetic adjustment or tolerance change |
| Quote/depth units | Same-venue book/quote validation, unit contract, source hashes and raw snapshots | BTC/ETH/SOL book tops and quote sizes match; fresh matching snapshots normalize to underlying-asset quantities | Every subsequent snapshot must revalidate; mismatches/staleness revert to unverified |
| Liquidity | Exact executed-trade volume, top-level participation and nearby-price depth diagnostics; venue minimum check | BTC mean daily observed value about $205,875 versus frozen $1m minimum; top-level 1% cap about $0.80, below current venue minimum | Original policy does not qualify this venue/size; changing policy requires a separate, versioned experiment |
| Events | Scoped FOMC/BEA source catalogs with retained bodies and evidence hashes | Published FOMC and BEA categories can validate independently; BEA has 13 scheduled releases | BLS automated calendar denied HTTP 403; complete scheduled-protocol and venue-maintenance coverage remain unavailable |

BTC's current closed-bar signal is **exit review**, not an entry candidate. The
new depth evidence makes the sizing cap binding: the proposal rounds to zero
under current minimum order metadata. This is not fixed by enabling orders.
The separate fee/inventory mismatch also remains active even if another veto is
reported first. No extra trade is used to manufacture a successful test.

## Fee reconciliation

Alpaca documents fees in the received asset/currency and potentially delayed
end-of-day posting. The current same-day empty queries do not establish zero
fees. Both the general activity endpoint and specific CFEE/FEE endpoints were
checked. Gross fills agree with their order quantities and values. A 0.25%
per-buy-execution upward-rounding hypothesis numerically explains the BTC
residual, but it remains an unconfirmed hypothesis.

`refresh_fees` retains the earliest recorded fill in its lookup window instead
of losing old unresolved fees after three days. The bounded five-page request
budget is unchanged; incomplete traversal fails rather than claiming coverage.
Confirmed debits must identify a supported pair and negative finite quantity.
Pending records cannot change inventory. Previously confirmed records cannot be
overwritten silently: revisions are retained before a conflict triggers a review
latch. Existing strategy-owner ambiguity checks still apply. No fill, quantity,
account baseline or fee row has been synthesized.

A posting-time guarantee and provider rounding rule have not been established
for this account. The existing local fee poll will read new records when
available while the service/Mac remain running. Nothing was sent to support;
a prepared question is in `docs/ALPACA-FEE-QUESTIONS.md`.

## Depth validation and unit provenance

The adapter requests `/v1beta3/crypto/us/latest/orderbooks` on the same fixed US
venue as the crypto quotes and execution-history data. It validates both source
ages (15 seconds), rejects future timestamps, requires book/quote times within
one second, sorted unique nonnegative levels, uncrossed prices, and exact top
price/size agreement. It applies no stock round-lot or currency conversion.

The unit contract derives from Alpaca's description of level-2 sizes as
quantities of the underlying asset, checked against its current REST p/s schema
and matching quote fields. It is a documented adapter interpretation supported
by connected consistency checks, not a new provider warranty. Every normalized
quote carries `size_unit_version`, source links, book timestamp and content hash.
The exact raw book is retained in `depth_snapshots`. Failed/forbidden/missing,
changed or stale books leave units unverified. Displayed depth can disappear;
normalization is not evidence of fill probability or queue priority.

This adds one data GET per quote refresh, about 12 requests/minute at the current
5-second interval. Existing quote polling adds 24 data requests/minute; metadata,
news and bounded history share the existing 100/minute local normal data budget.
No paid tier or new subscription was purchased. Snapshot storage grows with unique
books; no automatic deletion was added. Observe disk growth before extending
unattended retention indefinitely.

Trade-history retention now shares insert-only raw UTC-day records in
`market_trade_days`; partial-day tails retain each distinct content version.
An immutable `market_batch_maps` entry for every full `symbol:input_sha256`
lists ordered day keys and the original start/end/known-at bounds. Concatenating
those records and rerunning `aggregate_daily` with those bounds reproduces the
input hash and daily bars. Existing full `market_batches` rows remain untouched.
The under-1500-second reuse rule and 12-page limit are unchanged; a larger trade
window still fails closed at that limit. Monitor disk growth and page headroom.

## Liquidity policy distinction

The unchanged frozen strategy applies a $1m observed average daily-volume floor
and a 1% **top-level** dollar cap. The new diagnostic also sums 1% participation
across visible levels inside a 10bps buy/sell collar. At one BTC readback this
nearby-price capacity was approximately $2,698 each way, while the top-level cap
was only about $0.80. These are different measurements, not conflicting data.
Neither another venue's volume nor nearby-price depth clears the frozen rules.

A future liquidity experiment can evaluate order-size/turnover participation,
both-side book-walk cost, spread/fee shocks, depth disappearance, quantity minima
and exit feasibility. It must register changed rules separately before evaluating
future results. The existing daily strategy and November 8 evaluation cutoff
remain unchanged. Historical low-volume rejection remains a retained result.

## Event coverage

The collector retains the full official HTML body and hash for FOMC and BEA
catalogs, plus each parsed event. Source revalidation updates freshness without
inventing publication dates. Main-ledger category proofs bind symbol, source,
checked time, coverage bounds and retained evidence hash. Arbitrary flags/hash
strings cannot certify a category; the dashboard loads and checks the referenced
proof. Complete categories need current evidence covering at least the next 24
hours. BTC earnings/ETF distributions are not applicable; unannounced security
incidents require operational monitoring and cannot be certified absent.

FOMC dates use whole Eastern meeting intervals. BEA's schedule does not specify
a clock timezone on the page, so the parser retains the printed time and uses a
conservative whole Eastern date for exclusion. It does not invent an exact
release timestamp. The two catalogs remain **partial overall coverage**; the
collector does not turn them into a complete financial/protocol calendar.
BLS release RSS remains distinct from the denied upcoming-calendar endpoint.
No identity switch, access workaround or repeating BLS ICS poll was added.

## Remaining acceptance sequence

1. Obtain actual posted CFEE/FEE evidence (or a provider-confirmed accounting
   contract) and match custody without an invented adjustment.
2. Retain fresh matching same-venue depth and an executable quantity. The current
   frozen liquidity policy still fails; evaluate an explicitly versioned
   challenger if a different policy is desired.
3. Supply verified BLS, scheduled-protocol and venue-maintenance categories from
   permitted sources. Protocol/unlock requirements differ across assets. This
   cannot qualify v1: its frozen screen requires a top-level verified calendar
   and cannot consume per-category proofs, even if all categories pass.
   The follow-up is a separately registered v2 with a new manifest and source
   hashes, a new prospective window, and a screen consuming
   `readiness.calendar_coverage`. It is neither implemented nor approved and
   must never relabel v1 results or reuse its window as untouched future evidence.
4. Require a fresh qualified entry, cost/size/risk checks and validated research
   execution/exit supervision before the bounded research PAPER pilot.

Real queue/impact behavior, adequate forward strategy evidence and offline
learning promotion remain separate roadmap work. A successful mechanical test
or passing depth component is not a profitable strategy result.

Official references:
- [Crypto fees](https://docs.alpaca.markets/us/docs/crypto-fees)
- [Account activities](https://docs.alpaca.markets/us/docs/account-activities)
- [Current crypto data fields and venue locations](https://docs.alpaca.markets/us/docs/real-time-crypto-pricing-data)
- [Alpaca's level-2 quantity guide](https://alpaca.markets/learn/visualizing-orderbook-data-with-alpaca-crypto-api)
- [Official API specification](https://github.com/alpacahq/cli/blob/main/api/specs/market-data-api.json)
- [Crypto pair limitations](https://alpaca.markets/support/alpaca-crypto-coin-pair-faq)
- [BEA release schedule](https://www.bea.gov/news/schedule)
- [FOMC calendar](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm)
