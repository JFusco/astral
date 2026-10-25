# News, fundamentals, and automatic refresh inputs

Research date: October 24, 2026. Scope: US Georgia personal ETF/spot-crypto paper bot, separate swing and intraday strategies, $100–$300/month total budget. This is a source and refresh design, not a running service. No account access, subscriptions, or scheduled automation was created.

## Which affordable inputs should feed the bot?

### Takeaway

Use a small, traceable source stack: Alpaca news if the account entitlement permits it, SEC filings for underlying companies, issuer holdings/fund data for ETFs, government macro releases, CoinGecko for broad crypto context, and official project/exchange announcements. Treat this as expanding evidence coverage, not a promise to ingest every article or every relevant event.

### Cited Findings

| Input | Verified capability and useful scope | Price/quota boundary |
|---|---|---|
| Alpaca/Benzinga news | Alpaca documents stock and crypto news history since 2015; it says its news comes from Benzinga and cites an average of 130+ articles/day. A live news WebSocket also exists. [Historical news](https://docs.alpaca.markets/us/docs/historical-news-data), [live news](https://docs.alpaca.markets/us/docs/streaming-real-time-news) | A 2022 launch article described a limited beta free at 200 calls/minute on Free and 10,000 on Unlimited. This is historical pricing evidence, not confirmed current entitlement or quota. [Launch article](https://alpaca.markets/blog/introducing-news-api-for-real-time-fiancial-news/) |
| SEC submissions and Company Facts | Unauthenticated JSON APIs provide filing history and standardized XBRL financial facts. URLs: `https://data.sec.gov/submissions/CIK##########.json` and `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json`. Custom taxonomy facts are outside the aggregated standardized-facts scope. [SEC API guide](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) | No API keys required. SEC allows at most 10 requests/second/user across machines; declare a meaningful User-Agent with contact information. [Developer resources](https://www.sec.gov/about/developer-resources), [SEC FAQ](https://www.sec.gov/about/webmaster-frequently-asked-questions) |
| ETF issuer data | An issuer example, IVV’s iShares page, exposes NAV, expense ratio, fund characteristics, and a downloadable holdings CSV. Different fields have different as-of dates; holding values may use vendor prices different from NAV valuation prices. [IVV official issuer page](https://www.ishares.com/us/products/239726/ishares-core-sp-500-etf) | Issuer-specific download contracts, availability, and reuse terms need checking; no universal ETF holdings API/quota was established. |
| Official macro information | Federal Reserve RSS covers monetary-policy releases, speeches, and economic-statistics updates. BLS RSS covers CPI, employment, PPI, and other releases. Treasury provides daily interest-rate XML feeds with GET requests. [Fed feeds](https://www.federalreserve.gov/feeds/feeds.htm), [BLS feeds](https://www.bls.gov/feed/), [Treasury XML](https://home.treasury.gov/treasury-daily-interest-rate-xml-feed) | Publicly accessible source pages; no paid subscription was needed to read these sources. Their exact automated access quotas were not verified in this pass. |
| CoinGecko broad crypto context | `/coins/markets` returns price, market cap, volume, circulating/total/max supply, and `last_updated`, with ID-based filtering and up to 250 IDs/request. [Endpoint contract](https://docs.coingecko.com/reference/coins-markets) | Current pricing: Demo $0, 10,000 calls/month and 100/minute; Basic $35/month on monthly billing, 100,000/month and 300/minute, or $29/month effective when billed $348/year. Freshness advertised from 60 seconds for Demo and from 10 seconds for Basic. [Current pricing](https://www.coingecko.com/en/api/pricing) |
| Official crypto announcements | Ethereum Foundation’s blog has Protocol Announcements and Security categories. Coinbase’s official blog publishes product, company, and policy announcements. [Ethereum Foundation blog](https://blog.ethereum.org/), [Coinbase blog](https://www.coinbase.com/blog) | These are candidate primary sources for a maintained allowlist; a comprehensive announcement API or universal free feed was not verified. |

- **News update identity.** Alpaca news messages include article ID, source, symbols, URL, `created_at`, and `updated_at`; content can contain HTML. This supports deduplication and article-version handling. It does not establish permission to archive or redistribute unlimited full-text content. [Alpaca live news schema](https://docs.alpaca.markets/us/docs/streaming-real-time-news).
- **SEC update timing.** SEC says submissions JSON typically updates in less than a second and XBRL in under a minute as filings disseminate, with possible longer peak-time delays. Nightly bulk JSON ZIPs are published at approximately 3 a.m. ET. These are service processing expectations, not guaranteed end-to-end delivery to the bot. [SEC API guide](https://www.sec.gov/search-filings/edgar-application-programming-interfaces).
- **SEC request identity.** SEC’s sample identifies an organization plus an administrative email in the User-Agent; it does not prescribe a secret credential. Example for implementation: `PersonalTradingResearch contact@example.com`, replaced with a real monitored contact. The aggregate maximum is 10 requests/second; running more workers does not multiply the allowance. [SEC FAQ](https://www.sec.gov/about/webmaster-frequently-asked-questions), [fair-access scope](https://www.sec.gov/about/developer-resources).
- **Institutional holdings are delayed.** Form 13F filings are normally due within 45 days of quarter end, subject to weekend/holiday adjustments. They describe historical institutional holdings; they are not live order flow or current ETF constituent holdings. [SEC Form 13F FAQ](https://www.sec.gov/rules-regulations/staff-guidance/frequently-asked-questions-about-form-13f).
- **Conflicting CoinGecko documentation.** The current pricing page says Demo 100/minute and Basic 300/minute, while an official troubleshooting article still says Demo 30/minute and Basic 250/minute. Prefer the current pricing page for planning, configure conservatively, and confirm the actual account/dashboard and responses before enabling capacity-dependent behavior. [Pricing](https://www.coingecko.com/en/api/pricing), [conflicting troubleshooting article](https://www.coingecko.com/learn/coingecko-api-troubleshooting-guide-and-solutions).

### Inferences

- For ETFs, use fund mandate, issuer disclosures, holdings weights, fees, distributions, NAV/premium-discount, concentration, and underlying constituent earnings where available. Company Facts is useful for operating-company constituents rather than assigning an ETF an ordinary corporate income statement. Start with a few selected ETF issuers and major constituent exposures, then expand.
- CoinGecko is a market-context source. Use the execution venue’s fresh quote/order book for an order decision; do not substitute broad reference market data for executable prices.
- Official exchange notices can identify maintenance, pair restrictions, listings/delistings, and changes to trading rules. Official project releases/security announcements can identify upgrades and incidents. Build source adapters only for verified official domains and repositories associated with selected assets.
- Treat issuer and project statements as attributed claims, with uncertainty retained. Broad news, analyst commentary, and primary releases are different evidence types; do not count syndicated copies as multiple independent confirmations.
- Start with free inputs and a bounded CoinGecko Demo refresh. If needed, CoinGecko Basic adds $35/month, leaving $166 under a $300 budget after Alpaca’s $99 data plan. The resulting $134/month data estimate excludes unknown current Alpaca news entitlements, taxes, hosting, and AI.

### Gaps

- Current Alpaca news pricing, account entitlement, streaming concurrency, current per-endpoint quota, historical completeness, and guaranteed delivery latency were not established. Confirm these before describing news as included/free today.
- This stack does not provide comprehensive worldwide news, every earnings estimate, an institutional real-time newswire, or a social-media firehose. Model access, Codex CLI, and a Grok subscription do not by themselves establish those data entitlements.
- No paid premium news provider was added. A separately licensed wire could consume most of the budget and should be considered only after proving the benefit of the initial sources.
- No uniform API was established for all ETF issuers, crypto token unlock schedules, or project security disclosures. Token supply fields do not by themselves reveal future unlock events or their certainty.
- Treasury Fiscal Data API documentation returned 403; the independently readable Treasury daily-rate XML documentation supports the source recommendation. No denied endpoint was bypassed.

## How should inputs remain up to date?

### Takeaway

Refresh according to the source’s publication cadence and the strategy’s decision needs. A ten-minute source does not become current intraday evidence just because an agent rereads it every second. Keep ingestion continuously observable and distinguish an old-but-valid daily fact from a stale live quote.

### Cited Findings

- Alpaca supports event-driven news streaming and version timestamps. [News WebSocket](https://docs.alpaca.markets/us/docs/streaming-real-time-news).
- SEC supplies company/latest-filings RSS and JSON updates; latest-filings RSS is its recommended public route for getting close to real-time publication. The SEC warns document publication can lag acceptance and is not guaranteed. [Developer resources](https://www.sec.gov/about/developer-resources), [SEC availability FAQ](https://www.sec.gov/about/webmaster-frequently-asked-questions).
- BLS has an official release calendar and says release pages normally appear within seconds of official release time. The schedule uses Eastern Time; economic series may have preliminary/revised releases. [BLS dissemination policy](https://www.bls.gov/about-bls/dissemination.htm), [2026 calendar](https://www.bls.gov/schedule/2026/home.htm).
- Treasury’s documented feed is daily, with requests selectable by year or month. [Treasury daily XML](https://home.treasury.gov/treasury-daily-interest-rate-xml-feed).

### Inferences

Proposed refresh policy (design choices, not vendor promises):

| Source | Initial policy | Failure behavior |
|---|---|---|
| Broker market quotes and order states | Stream during strategy-active hours; crypto stays active around the clock if its strategy does | Block new order decisions needing a fresh quote when the feed is stale; reconcile open orders after reconnect |
| News | Live stream if entitled; periodic overlapping REST catch-up by article/update time after reconnect | Record gaps and backfill; do not silently relabel late news as known earlier |
| SEC filings | Poll a scoped filing watchlist/RSS with a shared throttle; fetch affected Company Facts when a new relevant filing arrives; nightly reconciliation | Retain previous version and flag missing updates; no random per-worker crawling |
| ETF issuer holdings and fund details | Check once per trading day after normal issuer publication; refresh prospectus/fees on source change | Preserve holdings as-of date and availability time; signal when expected publication is missing |
| Macro releases | Refresh calendar daily; fetch specific releases around their scheduled times and reconcile later revisions | Pause calendar-sensitive rules when a scheduled release is delayed or unavailable |
| Crypto metadata/supply | Start with one batched call every ten minutes; refresh slower-moving project metadata daily | Treat missing values as unknown, not zero; keep provider update time separate from fetch time |
| Official announcements | Poll an allowlist using conditional requests/RSS where supported, initially every 5–15 minutes | Mark source-specific delay and retain last successful cursor |

- One batched CoinGecko request every ten minutes is 4,320 calls in a 30-day month, before retries/backfills/other endpoints. That fits the published 10,000-call Demo allowance while leaving room for bounded overhead. Avoid one request per asset per refresh.
- Use a shared quota allocator per provider/account/IP scope, retry with jitter/backoff, limit reconnect storms, and preserve cursors. Prefer `ETag`/`Last-Modified` conditional requests when a source supports them. These are implementation recommendations, not claims that each source supports every mechanism.
- Run a small source-health worker that emits `last_success`, `source_updated_at`, `latest_available_at`, `expected_next_release`, `lag`, `error_count`, `remaining_quota`, and `monthly_budget_used`. Use separate freshness policies per data type and strategy. An article correction should trigger reanalysis without creating a new independent event.
- Source updates should change evidence and derived features; they must not silently change the risk policy, trade permissions, or strategy code. Each proposed learned change needs versioned evaluation before deployment.

### Gaps

- No source SLA or subsecond news latency has been purchased or demonstrated. Initial refresh times above require measurement and adjustment.
- No infrastructure scheduler was created. The user’s requirement is an architecture requirement for automatic updates, not authorization to activate an external recurring automation now.

## What must the learning layer retain and protect?

### Takeaway

Build a time-aware evidence ledger. Every training example and decision must be reproducible using only information available at that moment, with provider corrections, revisions, late arrivals, and simulated fills labeled explicitly.

### Cited Findings

- SEC Company Facts aggregates disclosures across filings, while its frames API selects the latest-filed fact that fits a period. A current response is therefore not automatically a historical snapshot of what the bot knew on an earlier date. [SEC API data contracts](https://www.sec.gov/search-filings/edgar-application-programming-interfaces).
- Issuer page fields can have different reporting dates, and the issuer notes holdings valuation/vendor-price differences. [IVV issuer disclosures](https://www.ishares.com/us/products/239726/ishares-core-sp-500-etf).
- Article `created_at` and `updated_at` differ, and CoinGecko exposes its own `last_updated`. [Alpaca news schema](https://docs.alpaca.markets/us/docs/streaming-real-time-news), [CoinGecko market schema](https://docs.coingecko.com/reference/coins-markets).
- CoinGecko Demo calls require attribution; paid-plan licensing and overage terms are shown separately. [CoinGecko pricing](https://www.coingecko.com/en/api/pricing).

### Inferences

- Store source/provider ID, canonical URL, asset identifiers, content hash, provider publication/update time, `first_seen_at`, ingestion time, effective/as-of period, revision number, source license/retention policy, parser version, and all derived feature/model versions. For filings retain CIK, accession, form, fiscal period, units, taxonomy tag, filing/acceptance timestamp where available, and the exact fact version used.
- Separate `event_time`, `published_at`, and `available_to_bot_at`. Backtests must enforce `available_to_bot_at <= decision_time`; a quarter-end fiscal period or a 13F holdings date is not an availability timestamp. Never overwrite an as-reported fact with a later restatement in the historical training dataset.
- Keep article IDs and revision chains; cluster duplicate/syndicated stories. Record whether a conclusion is a source fact, extraction, inference, estimate, rumor, or contradiction. NLP outputs need evidence pointers and uncertainty rather than an unsupported buy/sell score.
- Model textual inputs as untrusted data. Articles, HTML, PDFs, and social posts cannot grant instructions or tool permissions. Parse/sanitize outside the execution boundary; the evidence agent emits structured features and citations, while deterministic risk/execution code controls orders.
- Evaluate each added source in a controlled strategy version: compare after-cost outcomes and decision quality against the same strategy without that source. More news can add noise and processing cost. Training labels must avoid counting a paper simulator’s optimistic fills as actual execution skill.
- For private research, prefer URLs, metadata, hashes, extracted facts, and short evidence excerpts; retain full articles only where the provider contract permits it. Apply source-specific cache/retention rules and attribution. Check storage, model-training, redistribution, and dashboard-display rights before expansion; API access alone does not establish all those rights.

### Gaps

- Full-text storage/training/redistribution licenses were not exhaustively reviewed. No statement here grants rights to mirror publisher archives or circumvent paywalls.
- Consensus earnings estimates and economic surprise benchmarks were not sourced. Published actual data alone does not establish the market’s prior expectation.
- No data quality benchmark, measured source lag, model performance improvement, or paper/live trading benefit has yet been demonstrated.
