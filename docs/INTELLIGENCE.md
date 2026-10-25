# Local intelligence collector

The public collector runs independently on `127.0.0.1:8768`. The trading service
stays on `127.0.0.1:8766`, and the Next.js dashboard at `http://127.0.0.1:3000` merges both GET responses
through same-origin Route Handlers. The original
overnight baseline is frozen. Current research packets receive bounded scoped
context from this collector without broker credentials or execution authority.

Start the collector from this checkout:

```sh
.venv/bin/python -m uvicorn backend.intelligence_app:app --host 127.0.0.1 --port 8768 --workers 1 --timeout-graceful-shutdown 5
```

It runs while this process and the computer remain awake and online. It is not
installed as a login service. The existing overnight awake assertion has a fixed
end; this collector does not extend it or restart the trading service.

| Source | Poll interval | Evidence |
| --- | --- | --- |
| Federal Reserve releases | 5 minutes | Official macro announcements |
| Federal Reserve FOMC calendar | 60 minutes | Official meeting date intervals; exact announcement times unspecified |
| Federal Reserve speeches | 15 minutes | Official policy communications |
| BLS latest releases | 5 minutes | Official economic release metadata |
| SEC current 8-K and 10-Q feeds | 15 minutes each | Latest 40 company filings per feed |
| CoinDesk and Cointelegraph | 5 minutes each | Publisher headline metadata |
| Ethereum Foundation and Bitcoin Core | 15 minutes each | Official project announcements |
| Coinbase, Kraken, Solana and Alpaca status | 2 minutes each | Components, incidents and supplied maintenance notices |

These are public metadata endpoints: no additional paid account or API key was
added. Alpaca/Benzinga remains in the existing service with its own entitlement.
SEC requests use the user-provided identifying contact stored only in ignored,
mode-0600 `runtime/intelligence-config.json` as `sec_contact`. The collector does
not load `.env`, import broker tools, fetch article bodies or run a model.

The Sources dialog shows source-specific HTTP state, poll interval, last
successful check and record count. A fresh fetch does not mean every publication
is recent. Publication time, update time, first-seen time, immutable content hash
and current revision pointer are retained. Unknown publication times remain
unknown. Operational snapshots are labeled separately. Cached records remain
visible after errors. A current pointer handles publisher corrections and
reversions without rewriting historical content. The API returns up to 20
current records per source, at most 420 total; the separate SQLite ledger retains
all observed revisions. This is bounded sampling, not complete news coverage.

Fetches use fixed HTTPS endpoints, three concurrent requests maximum, 20-second
timeouts, a 2 MB decompressed response cap, conditional requests, no redirect
following and exponential error backoff (up to six hours), honoring Retry-After.
Entity declarations are rejected before XML parsing. Requests do not follow
article links. HTTP access failures stay failures; no bypass or alternative
identity is attempted. Responses and request counts are retained locally in
`runtime/astral-intelligence.sqlite`. The API is GET-only, bound to loopback with
exact trusted local/service hosts; browser access goes through the Next.js relay. The collector owns only its own database lock.

## What this enables, and what remains

These sources supply timestamped research context and visible operational
warnings. Project-wide tags are explicit; publisher headlines do not receive
invented ticker mappings. Broad SEC filing metadata does not extract financial
statements or verify ETF holdings. Status maintenance notices do not establish a
complete protocol or macro calendar. A green status page is not an end-to-end
broker execution check. The collector grants no execution authority.

During the original overnight pilot these feeds were display-only. That baseline
is frozen. The BTC v1 research experiment now attaches up to 12 fresh scoped
public context records and the next two FOMC meeting intervals. Source arrival,
revision and validation timestamps remain attached. Future/revised/stale inputs
are excluded. Public context cannot supply missing symbol-specific news or claim
complete event coverage; known FOMC meetings can add a conservative date-window
veto. It cannot clear any existing veto. Complete event calendars, token identities, on-chain analytics,
issuer holdings and extracted financial statements remain separate integrations.
Inventory reconciliation, crypto bar/quote-size semantics and execution readiness
must still pass before automated paper orders are enabled.

Official discovery references:
- https://www.federalreserve.gov/feeds/feeds.htm
- https://www.bls.gov/feed/
- https://www.sec.gov/about/developer-resources
- https://status.coinbase.com/api
- https://status.kraken.com/api
- https://status.solana.com/api

The original overnight baseline has since been stopped and frozen. The collector
and read-only dashboard now run from `/Users/joe.fusco/Projects/astral-trading`;
compatibility links preserve older receipt paths. New historical execution data
and the authorized mechanical paper experiment are documented separately in
`EXECUTION-PILOT.md` and `ROADMAP.md`.

BLS's official ICS calendar was probed separately and returned an explicit HTTP
403 automated-access denial. This is a calendar coverage failure, distinct from
the connected BLS latest-release RSS feed. No bypass, identity switch or repeating
ICS poll was added. FOMC events use America/New_York date intervals, including
DST and cross-month meetings, without inventing a release hour. Only the next
two retained upcoming meetings appear in the news list; calendar archive rows
cannot crowd out all recent news. All 57 parsed dates/revisions are retained in
the collector ledger; the API remains a bounded 20-record-per-source sample.

Official calendar references:
- https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
- https://www.bls.gov/help/hlpiCAL.htm

An earlier October 25, 2026 snapshot had 15 sources after adding the official BEA release schedule hourly; this count is historical. FOMC/BEA full source bodies, hashes and parsed catalogs are retained for scoped category proofs; a missing catalog triggers one bounded bootstrap fetch while later failures retain normal backoff. Full event coverage remains incomplete. See READINESS-GATES.md.
# Event source follow-up

The collector now has 21 sources and returns at most 420 headline records
(20 per source), plus full retained event catalogs. Six new adapters cover NY Fed
key BLS releases, Alpaca upcoming/active maintenance, the Bitcoin BIP index,
Bitcoin Core lifecycle and Ethereum roadmap. See
[LIQUIDITY-EXPERIMENT.md](LIQUIDITY-EXPERIMENT.md) for exact scope and expiry.
Only the paired maintenance lists can clear their corresponding complete
published-list category. Partial BLS and protocol sources remain explicitly
insufficient for complete event qualification.
