# Broker and exchange platforms for a paper-first trading bot

Research date: October 24, 2026. User location is United States, Georgia. User wants separate daily/swing and intraday strategies and can spend $100–$300/month total on paper trading, data, hosting, and AI. No accounts were accessed and no paid services were enabled. Sources below were read live; account-specific availability and entitlements remain unverified.

## Alpaca: the lean starting venue

### Takeaway

Start with Alpaca paper trading for a small allowlist of US ETFs and selected spot crypto. This is a recommendation based on its shared order API and real-time simulator; it does not mean that paper profits establish live profitability. Budget $99/month for consolidated equity data when evaluating intraday execution, leaving $1–$201 of the stated budget for hosting and AI depending on the monthly ceiling. [Alpaca paper trading](https://docs.alpaca.markets/us/docs/paper-trading), [data plans](https://docs.alpaca.markets/us/docs/about-market-data-api).

### Cited Findings

- **Access and isolation.** Email signup is sufficient for a globally available Paper Only account. Paper includes crypto. Paper credentials differ from live credentials, and the paper order base URL is `https://paper-api.alpaca.markets`; the API contract is shared with live. Paper Only accounts receive IEX equity data. [Paper trading](https://docs.alpaca.markets/us/docs/paper-trading); the readable versioned page corroborates these points: [version 1.4.2](https://docs.alpaca.markets/us/v1.4.2/docs/paper-trading).
- **Simulator fidelity.** Alpaca omits order impact, information leakage, latency slippage, queue position, price improvement, regulatory fees, and dividends. Marketable orders use current NBBO, but order size is not checked against displayed NBBO quantity; paper can therefore fill orders larger than available liquidity. Random partial fills occur on 10% of eligible fills. These omissions matter directly to any execution-learning layer. [Paper trading](https://docs.alpaca.markets/us/docs/paper-trading).
- **Actual universe.** `GET /v2/assets` is the master asset list; filter `status=active` and asset class, then inspect the individual asset’s tradability and quantity/price constraints. Default class is `us_equity`; crypto uses `asset_class=crypto`. This is a venue-supported universe rather than every ETF or coin. [Get Assets](https://docs.alpaca.markets/us/reference/get-v2-assets-1), [crypto asset discovery](https://docs.alpaca.markets/us/docs/crypto-trading).
- **Equity order types.** The equity documentation covers market, limit, stop, stop-limit, trailing stops, bracket, OCO, and OTO structures. Support varies with time in force, fractional quantity, and trading session. Extended-hours eligible orders must be limit orders with `day` or `gtc`; overnight eligibility is exposed through asset attributes. Order updates over the streaming interface are recommended for state tracking. [Placing Orders](https://docs.alpaca.markets/us/docs/orders-at-alpaca).
- **Georgia and crypto.** Alpaca’s currently served support article explicitly includes Georgia among supported US crypto jurisdictions, although its article date is May 2023; final account approval still has to establish eligibility. Current crypto docs specify market, limit, and stop-limit, `gtc` or `ioc`, fractional quantity or notional orders, no leverage or shorts, and a $200,000 per-order notional cap. [Alpaca crypto availability](https://alpaca.markets/support/alpaca-cryptocurrency), [Crypto Spot Trading](https://docs.alpaca.markets/us/docs/crypto-trading).
- **Crypto fees.** The current API guide lists base 30-day volume tier $0–$100,000 at **15 basis points maker / 25 basis points taker**; a marketable limit order can be a taker. Higher-volume tiers reduce fees. Do not treat stock commission-free pricing as crypto pricing. [Crypto Spot Trading fees](https://docs.alpaca.markets/us/docs/crypto-trading).
- **Personal Trading API quota.** Official support states **200 requests/minute/account**, with HTTP 429 on overflow. This article is dated December 2022 and should be reconfirmed from account responses/support before capacity planning. This is not the historical data quota. [Trading API usage limit](https://alpaca.markets/support/usage-limit-api-calls).
- **Individual market-data plans.** Basic is free: US stocks/ETFs, IEX real time, 30 equity symbols over WebSocket, history since 2016, restricted access to the latest 15 minutes of historical data, **200 historical calls/minute**. Algo Trader Plus is **$99/month**: all US stock exchanges, unlimited equity stream symbols, history since 2016 without that historical restriction, **10,000 historical calls/minute**. These are personal Trading API data plans; Broker API partner tiers are separate products. [About Market Data API](https://docs.alpaca.markets/us/docs/about-market-data-api).
- **WebSocket connection scope.** Connection count is per user and endpoint and depends on subscription; Alpaca says many subscriptions permit one connection, and most users have one active stream. A second consumer, including a third-party application, can cause error 406. Unlimited symbols does not mean unlimited connections. [WebSocket Stream](https://docs.alpaca.markets/us/docs/streaming-market-data).
- **Crypto feed provenance.** Current crypto stream locations distinguish Alpaca US (`us`), Kraken US (`us-1`), and Kraken EU (`eu-1`); providers can change. Match data provenance to the execution venue rather than assuming every BTC quote represents the same market. [Real-time Crypto Data](https://docs.alpaca.markets/us/docs/real-time-crypto-pricing-data).

### Inferences

- Free IEX data is appropriate for wiring and daily/swing experimentation. For an intraday system that decides market versus limit from spread, quote freshness, or best prices, use consolidated quotes and make feed identity part of every decision record. A strategy fed IEX quotes while the simulator fills from NBBO can otherwise learn from inconsistent information sets. This is an engineering inference from the documented data and fill contracts above.
- Use one market-data ingestion process and fan out internally to the two strategies, risk checks, recorder, and dashboard. Share one account-scoped quota manager across workers; spawning more workers does not increase a personal account’s trading quota.
- Keep paper data credentials/endpoints and the execution adapter explicitly in paper mode. Live mode should require a separate configuration and promotion step.
- For execution learning, retain timestamps from the venue and local receive/decision/send/ack/fill events, feed location, quote age/spread/depth, order/cancel/replace states, rejected requests, and quota usage. Label simulator fills as synthetic and exclude them from claims about actual queue position or market impact.

### Gaps

- The non-versioned paper documentation repeatedly timed out in direct `web.open`; its indexed current content and version 1.4.2 page agreed on the cited core limits. Avoid relying on versioned PDT language or reset-UI instructions as current policy.
- The data-plan table labels its numeric quotas as **historical API calls**. Do not assert those figures apply identically to every latest-data endpoint or crypto endpoint without endpoint-specific documentation or response evidence.
- The Paper Only page says IEX entitlement while the general plan page offers Plus to paper/live users. Confirm whether this user’s exact Paper Only account can purchase Plus or needs a brokerage account before making a paid commitment. No account was accessed.
- No live asset list, approved account permissions, current rate-limit headers, or actual fills have been verified.

## Alternatives: IBKR, Coinbase Advanced Trade, and Kraken

### Takeaway

IBKR is the stronger later ETF adapter when broader markets/order capabilities justify session and data-subscription work. Coinbase Advanced Trade and Kraken are later crypto adapters, but their testing environments require different handling: Coinbase’s public sandbox is mocked; Kraken Spot testing requires qualification/onboarding. [IBKR paper account](https://www.interactivebrokers.com/campus/glossary-terms/paper-trading-account/), [Coinbase sandbox](https://docs.cdp.coinbase.com/coinbase-app/advanced-trade-apis/sandbox), [Kraken testing](https://support.kraken.com/articles/advanced-api-faq).

### Cited Findings

#### Interactive Brokers

- Paper accounts support both Web API and TWS API and use IBKR’s simulator. Paper inherits trading permissions and market-data subscriptions. Fills use top-of-book rather than full depth, and stops/complex orders are simulated; several order types are unavailable. [Paper Trading Account](https://www.interactivebrokers.com/campus/glossary-terms/paper-trading-account/).
- For **Web API**, the official general guide states **10 requests/second/authenticated username**, including CP Gateway access, plus endpoint-specific quotas. Examples: order/trade polling once per 5 seconds, market snapshot 10/second, and history 5 concurrent requests. One username has only one brokerage session across IBKR platforms; subscriptions and permissions attach to the username. [Web API documentation](https://www.interactivebrokers.com/campus/ibkr-api-page/webapi-doc/).
- Newer 2026 changelog documentation additionally caps `/iserver/marketdata/history` at **10 requests/second or 50/minute**. These are history pacing limits; the 5-concurrent requirement from the guide is a different constraint. [September 2026 pacing change](https://www.interactivebrokers.com/docs/web-api/changelog/2026/9/9).
- US Pro stock/ETF commission table: first tier **$0.0035/share, $0.35 minimum/order** with tiered pricing; fixed pricing **$0.005/share, $1 minimum/order**, with fee/cap details. Lite’s advertised $0 stock/ETF tier must not be assumed to apply to this API setup. [US stock commissions](https://www.interactivebrokers.com/en/pricing/commissions-stocks.php).

#### Coinbase Advanced Trade

- REST spot base URL is `https://api.coinbase.com/api/v3/brokerage`. Public product list, order book, candles, and ticker endpoints exist; private methods use JWT. Public responses are cached one second; documentation suggests WebSocket, no-cache, or private market-data methods when live data is needed. [REST endpoints](https://docs.cdp.coinbase.com/coinbase-app/advanced-trade-apis/rest-api).
- The sandbox at `https://api-sandbox.coinbase.com/api/v3/brokerage/{resource}` requires no authentication and returns static predefined mocked responses for accounts/orders. It verifies API integration shape, not strategy fills or P&L against a changing market. [Advanced Trade Sandbox](https://docs.cdp.coinbase.com/coinbase-app/advanced-trade-apis/sandbox).
- The **current** official WebSocket Markdown specifies **8 connections/second/IP** and **8 unauthenticated messages/second/IP**. These are connection/message rates, not concurrent connections, symbol limits, or REST quotas. The HTML page currently omits the body in the rendered extractor; the `.md` page was read directly with Python `urllib`. Do not reuse older 750-connections/second numbers. [WebSocket rate limits](https://docs.cdp.coinbase.com/coinbase-app/advanced-trade-apis/websocket/websocket-rate-limits.md).
- The general Coinbase App API page states **10,000 requests/hour/API key or OAuth user**; it does not clearly distinguish Advanced Trade REST. **Do not present this as a verified Advanced Trade-specific quota**, and do not borrow Coinbase Exchange API limits for Advanced Trade. [Coinbase App rate limits](https://docs.cdp.coinbase.com/coinbase-app/api-architecture/rate-limiting).
- Order configurations include market IOC/FOK, limit GTC/GTD/FOK, stop-limit, and bracket configurations; instrument/venue applicability needs checking rather than assuming every configuration works on every spot pair. [Create Order](https://docs.cdp.coinbase.com/api-reference/advanced-trade-api/rest-api/orders/create-order).
- API keys use `view`, `trade`, and `transfer` scopes. Order creation/cancellation need `trade`, history and market data use `view`, and moving funds uses `transfer`. [Scope & Permissions](https://docs.cdp.coinbase.com/coinbase-app/advanced-trade-apis/rest-scopes).
- Fees depend on product, tier, and maker/taker status. The current public help page directs users to sign in for exact rates and criteria; preview displays the applicable fees. The immediate portion of a partially matched order pays taker fees, while the resting portion can pay maker fees. **Exact user fee tier is unknown without account access.** [Coinbase Advanced fees](https://help.coinbase.com/en/coinbase/trading-and-funding/advanced-trade/advanced-trade-fees).

#### Kraken Spot

- Spot REST/WebSocket/FIX testing is offered to **qualified clients**, with API-team onboarding. Futures has the separate `demo-futures.kraken.com` environment. Spot `validate=true` checks order parameters but returns no order ID; it does not establish a paper portfolio or simulated fills. [Advanced API FAQ](https://support.kraken.com/articles/advanced-api-faq).
- REST private-call limiter uses counters per API key: Starter max **15**, decay **0.33/sec**; Intermediate max **20**, decay **0.5/sec**; Pro max **20**, decay **1/sec**. Ledger/trade history costs two counter units; most other requests one; AddOrder/CancelOrder use another limiter. Master/subaccounts share the master’s trading tier. [REST Rate Limits](https://docs.kraken.com/exchange/guides/rest/ratelimits).
- The matching engine shares per-client/per-pair quotas across REST/WebSocket/FIX. Threshold/decay are **60/1/sec**, **125/2.34/sec**, **180/3.75/sec** for Starter/Intermediate/Pro. AddOrder costs one; rapid cancellation/replacement costs extra (cancel within five seconds costs eight). Open-order limits per pair are **60/80/225** respectively. The rate counter can be observed through order/executions streams. [Spot Trading Limits](https://docs.kraken.com/exchange/guides/general/ratelimits).
- Order types include market, limit, stop-loss, stop-loss-limit, take-profit, take-profit-limit, trailing-stop, trailing-stop-limit, and iceberg. [Spot WebSocket v2 Add Order](https://docs.kraken.com/exchange/api-reference/spot-websocket-v2/add_order).
- Kraken’s currently served restriction page excludes Maine and New York and lists US asset restrictions; Georgia is not in the state exclusions. This supports treating Georgia as a candidate jurisdiction, subject to account approval and pair eligibility. [Where Kraken is licensed](https://support.kraken.com/articles/where-is-kraken-licensed-or-regulated).

### Inferences

- Build adapters after one venue and one operational loop work. A multi-venue design should normalize symbols, capabilities, minimum sizes, tick sizes, time in force, clocks, fees, fills, balances, and errors, while preserving each venue’s raw record.
- Coinbase can be investigated with public market streams and a local fill simulator; its sandbox alone cannot test execution quality. Kraken’s qualified testing option should be checked before deciding to build a Kraken-specific simulator. Neither should be represented as proven equivalent to Alpaca/IBKR paper fills.
- For a later live execution key, request read/trade rights without funds-transfer rights where supported; grant only capabilities needed by that adapter.

### Gaps

- No current Advanced Trade-specific REST limit was conclusively located. Treat it as an onboarding/recheck item and obey 429/backoff rather than filling the gap with an Exchange API quota.
- Coinbase Georgia-specific account/asset eligibility was not separately verified. Kraken has no state exclusion for Georgia in the current page; account-specific entitlements remain unknown for all venues.
- IBKR documentation disagrees on onboarding detail: its current glossary says new clients receive paper accounts automatically, while another official PaperTrader page says approved/funded production account is required. Resolve this during onboarding. [Paper Trading Account](https://www.interactivebrokers.com/campus/glossary-terms/paper-trading-account/), [PaperTrader](https://www.interactivebrokers.com/en/software/paperTrader2.php).
- TWS API message limits were not independently verified in this bounded pass; Web API limits above must not be applied to TWS.
- Exact IBKR market-data fees depend on exchanges, professional/nonprofessional status, and entitlements, so no single monthly price is asserted.
- Kraken now offers stocks/ETFs in its consumer product, but ETF API and paper support were not established here; the Kraken recommendation in this report is specifically for its documented Spot crypto API. [Kraken fee/product page](https://www.kraken.com/features/fee-schedule).

## Costs and the initial venue decision

### Takeaway

Alpaca paper plus one data feed is the best first integration for this budget and two strategy horizons. Keep crypto transaction charges, simulated costs, data subscriptions, cloud costs, and AI worker costs as separate ledger categories; simulated fees are not a real cash charge and real AI/API usage is not simulated trading P&L.

### Cited Findings

Source claim ledger for synthesis:

| Claim to preserve | Primary evidence | Confidence / scope |
|---|---|---|
| Alpaca can paper trade ETFs and selected crypto | [Paper](https://docs.alpaca.markets/us/docs/paper-trading), [assets](https://docs.alpaca.markets/us/reference/get-v2-assets-1) | Documented capability; no account or fill tested |
| Alpaca historical data quota and trading quota are separate | [Data plans](https://docs.alpaca.markets/us/docs/about-market-data-api), [trading quota](https://alpaca.markets/support/usage-limit-api-calls) | Current data page; trading support article is older |
| Coinbase sandbox responses are mocked | [Sandbox](https://docs.cdp.coinbase.com/coinbase-app/advanced-trade-apis/sandbox) | Explicit official contract |
| Kraken Spot test access requires qualification | [API FAQ](https://support.kraken.com/articles/advanced-api-faq) | Explicit official contract; eligibility unknown |
| Exact Coinbase fee tier remains unknown | [Advanced fees](https://help.coinbase.com/en/coinbase/trading-and-funding/advanced-trade/advanced-trade-fees) | Official page requires sign-in |

- **Kraken Pro Spot fee table, verified October 24, 2026.** Scope is the page’s **Spot Crypto** table, which repeats its Cross-platform Fee Tiers table. The highest qualifying spot-volume **or** assets-on-platform condition determines the tier; qualifying twice does not stack benefits. Instant Buy volume does not count toward spot volume. These are maker/taker percentages, not the consumer Instant Buy fee. [Kraken Fee Schedule](https://www.kraken.com/features/fee-schedule).

| Tier | 30-day spot volume USD, at least | Assets on platform USD alternative | Maker | Taker |
|---|---:|---:|---:|---:|
| 1 | 0 | None | 0.40% | 0.80% |
| 2 | 2,500 | None | 0.30% | 0.60% |
| 3 | 10,000 | 20,000 | 0.22% | 0.38% |
| 4 | 25,000 | 50,000 | 0.20% | 0.35% |
| 5 | 50,000 | 100,000 | 0.15% | 0.30% |
| 6 | 100,000 | 200,000 | 0.12% | 0.25% |
| 7 | 250,000 | 400,000 | 0.10% | 0.22% |
| 8 | 500,000 | 600,000 | 0.08% | 0.20% |
| 9 | 1,000,000 | 1,000,000 | 0.06% | 0.18% |
| 10 | 2,500,000 | 2,500,000 | 0.04% | 0.15% |
| 11 | 5,000,000 | 5,000,000 | 0.02% | 0.12% |
| 12 | 10,000,000 | 10,000,000 | 0.00% | 0.10% |
| Pro 1 | 50,000,000 | 20,000,000 | 0.00% | 0.09% |
| Pro 2 | 100,000,000 | 25,000,000 | 0.00% | 0.08% |
| Pro 3 | 250,000,000 | 50,000,000 | 0.00% | 0.07% |
| Pro 4 | 400,000,000 | 80,000,000 | 0.00% | 0.06% |
| Pro 5 | 500,000,000 | 100,000,000 | 0.00% | 0.05% |

### Inferences

Suggested platform comparison (engineering judgment from the cited contracts):

| Platform | Suggested role | Main reason to defer or qualify |
|---|---|---|
| Alpaca | First paper adapter for both strategy horizons | Confirm consolidated-data entitlement and model simulator limitations |
| IBKR | Later ETF adapter for broader brokerage needs | Additional session, permission, and exchange-data work |
| Coinbase Advanced Trade | Later crypto execution adapter | Need a market-driven simulation layer beyond its static sandbox |
| Kraken Spot | Later crypto execution adapter | Check qualified Spot test access and actual account fee tier first |

- Recommendation: free paper integration first; add the $99 Alpaca equity data plan when evaluating intraday quote-sensitive behavior and after entitlement confirmation. With a $300 ceiling, $201 remains for all other real expenses; with a $100 ceiling, only $1 remains, so intraday consolidated data and substantial paid AI do not both fit.
- The current Kraken base Spot table implies about 1.6% fees for a market-in/market-out round trip, before spread/slippage and ignoring notional changes. Alpaca’s cited base crypto taker rate implies about 0.5%. These are arithmetic illustrations rather than personalized fee quotes. A small intraday edge can disappear after transaction costs.
- Do not assume limit means maker: a marketable limit can execute immediately as taker. Simulation and telemetry need realized maker/taker status, venue fees, and both sides of the trade.
- Choose a small supported allowlist first; expand from current asset/product discovery. There is no verified one-platform promise to trade literally every ETF and cryptocurrency.
- Paper testing should teach operational reliability and provide signal evaluation under explicit fill assumptions. Learning execution quality requires separately labeled replay, simulated paper, public-feed shadow, and eventually authorized live evidence. A learning system must not train on paper fills as if they demonstrated actual liquidity or queue priority.

### Gaps

- No current account-specific fee tier, actual statement, data entitlement, professional classification, or negotiated rate was inspected.
- Kraken states fees can be inaccurate when using a VPN; retain the raw account-specific preview/tier at eventual onboarding rather than blindly copying this public table. [Kraken Fee Schedule](https://www.kraken.com/features/fee-schedule).
- Pair-specific schedules, stablecoin schedules, promotions, financing, borrow, transfer/network, and withdrawal fees are not comprehensively modeled here. Select the exact product/pair schedule at runtime; the Spot table above should not be reused for every product.
