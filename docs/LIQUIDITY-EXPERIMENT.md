# Separate BTC liquidity experiment

`btc-liquidity-depth-v1` compares liquidity and transaction-cost hypotheses.
It cannot submit an order, infer an executed fill, change custody or claim profit.
The daily swing strategy and its existing November 8 evaluation cutoff stay frozen.

| Rule | Original baseline | Separate challenger |
| --- | --- | --- |
| Venue volume | At least $1m mean observed daily value | Order capped at 2 basis points of the same observed daily value |
| Participation | 1% of top level | 1% per displayed level inside a 10bps collar, on both sides |
| Depth disappearance | No additional sizing haircut | Remove half of displayed size before sizing |
| Order budget | Existing $25 proposal cap | At most $25 |
| Quantity | Venue increment/minimum | Venue increment/minimum, $1 floor, and fee-reduced exit must remain tradable |
| Costs | Existing strategy assumptions | Assume 25bps each side, measure book walk and flooring; modeled round-trip cost capped at 75bps |

These challenger values are test parameters informed by already inspected data,
not proven optimal limits. They do not replace the baseline's liquidity veto or
its independent accounting, event, news, entry-signal and portfolio checks.

The model reserves only 1% of each level after the haircut; it does not assume
access to the whole book. It models a buy limit rounded inside the collar, then
walks both buy and sell participation capacity. Received BTC is reduced by an
assumed buy fee and floored to quantity increments before the sell cost model.
The whole requested target must fit; a reduced size is diagnostic, not a pass.

Seven quote-only scenarios cover half depth, 90%/99% disappearance, doubled fees,
five-times spread, a 2% exit gap, and no exit depth. Every scenario records its
rejection reason and modeled cost. Nothing is appended to the trading fill table.

## Registration and collection

`scripts/liquidity_experiment.py register` creates the manifest exclusively once,
with source hashes, the original strategy identity, a hashed ledger binding,
baseline event sequence, and fixed start/end times 14 days apart. Previously
observed quotes are excluded. Code/contract drift blocks additional observations;
the window is never silently reset or extended.

The local dashboard's research configuration samples every 15 seconds into
`runtime/btc-liquidity-depth-v1.sqlite`. It opens the main paper ledger in SQLite
URI `mode=ro` and `query_only` mode. It makes no network or model requests.
Identical inputs deduplicate. Each observation keeps quote/event identity,
metadata, 21 exact trade-derived bars, raw-book content reference, calculations
and vetoes. The referenced raw book stays in the main ledger's `depth_snapshots`.
Both databases are required to reproduce the observation.

Fresh source quotes/books, exact consistency, current metadata and completed,
contiguous same-venue daily history are required. Invalid samples and collection
gaps over 45 seconds remain visible. Between-sample depth disappearance and
unobserved outages cannot be reconstructed. A stopped Mac means a collection gap.

The dashboard caches a compact summary; sample counters and gap statistics update
incrementally rather than scanning all observations on every server event.
Storage still grows; no old evidence is deleted automatically. The existing raw
depth collector is the larger ongoing storage cost. Disk capacity and retention
need review before an indefinite unattended run.

Fourteen days is an observation window, not a profitability or promotion test.
Queue priority, cancellations, impact, hidden liquidity, adverse selection,
actual fee attribution and reliable protective execution remain unvalidated.
The UI's **Liquidity comparison** dialog separates snapshot feasibility from
research qualification. The original research trade remains disabled.

## Event-source additions

The independent public collector now includes:

- New York Fed's current-month calendar, extracting BLS-origin releases with
  Eastern times and preserving the underlying BLS links without fetching them.
  Its key-series subset does **not** clear complete BLS coverage. Missing days,
  unknown times, missing timezone or changed markup fail validation.
- Alpaca's explicit upcoming **and** active maintenance endpoints. Both must be
  current to verify the published-maintenance category. An empty schema-valid
  list is meaningful; a missing list, error or another publisher is not.
  These catalogs refresh every 120 seconds; category evidence expires after
  five minutes and is checked locally every minute. A 48-hour inspection horizon
  covers the next 24 hours of the currently published list, without guaranteeing
  that newly announced maintenance or incidents cannot occur.
- Bitcoin's canonical BIP index and Bitcoin Core software lifecycle, plus the
  Ethereum roadmap. They retain statuses, TBA and broad schedule text as protocol
  context. A BIP's status or a Core release does not establish network activation;
  an Ethereum quarter/year is not an exact activation timestamp. These watches
  never clear complete protocol coverage or supply-unlock coverage.

Full raw responses and hashes are retained apart from the capped headline sample.
Maintenance overlap/overrun checks inspect the full catalog, so a UI item limit
cannot hide an active event. No access identity was changed and the denied BLS
ICS endpoint was not retried. No subscription was purchased.

References: [NY Fed calendar](https://www.newyorkfed.org/research/calendars/nationalecon_cal.html),
[Alpaca status API](https://status.alpaca.markets/api),
[Bitcoin BIPs](https://github.com/bitcoin/bips),
[Bitcoin Core lifecycle](https://bitcoincore.org/en/lifecycle/),
[Ethereum roadmap](https://ethereum.org/roadmap/).
