# Deterministic execution and operational trading risk controls

Research checked October 24, 2026. Scope: Joe's own Georgia, US account, ETF and spot crypto, Alpaca first, paper first. Recommendations below are engineering policies to test, not promises of investment performance. All referenced pages were opened, rather than relying on snippets. No account changes or orders were made during this research.

## Which order types control execution risk?

### Takeaway
Default new entries to bounded limit orders using a fresh executable quote. Reserve market orders for an explicitly configured urgency policy, and treat both failed execution and adverse execution as separate risks.

### Cited Findings
- The SEC explains that a market order seeks the available market price without guaranteeing the execution price; different parts of an order may fill at different prices. A limit bounds the price but may not fill. A stop becomes a market order after triggering, while a stop-limit can remain unfilled when the market moves through the limit. — [SEC Trading Basics](https://www.sec.gov/files/trading101basics.pdf)
- Alpaca reserves buying power for opening orders until execution or cancellation; closing orders do not release buying power before execution. Its order API supports client identifiers and lookup by them. It recommends streaming order updates. ETF fractional orders use DAY TIF; equity limit/stop price precision is two decimals at prices at least $1 and four below $1. `pending_cancel` is distinct from `canceled`. — [Alpaca Placing Orders](https://docs.alpaca.markets/us/docs/orders-at-alpaca)
- Alpaca supports crypto `market`, `limit`, and `stop_limit` orders, with `gtc` and `ioc` TIF, and either quantity or notional. Its example prose says a GTC order is good to end of day, contradicting the explicit GTC field: follow the formal type/TIF and broker readback, not that sentence. — [Alpaca Crypto Orders](https://docs.alpaca.markets/us/docs/crypto-orders)

### Inferences
- Deterministic entry policy: reject stale/crossed/nonpositive quotes; calculate midpoint `m=(ask+bid)/2`, spread in basis points `10000*(ask-bid)/m`; reject if spread exceeds asset/strategy ceiling; bound buy to `floor_to_tick(ask*(1+slippage_bps/10000))` and sell to `ceil_to_tick(bid*(1-slippage_bps/10000))`. The allowed slippage is a configured price tolerance, not a prediction of the fill.
- Round quantities down to the valid increment after all cash, position, and risk caps. Never round a buy limit up beyond the authorized price ceiling, or a sell limit down below the authorized floor. Validate the final serialized order again.
- A bounded limit is a default recommendation, not a regulatory requirement. A marketable limit does not guarantee a fill. Repricing must be bounded by maximum attempts, cumulative price tolerance, total order lifetime, and original signal expiry. Never silently turn a rejected limit into market.
- Crypto IOC can reduce resting exposure; fractional ETF DAY orders require explicit expiry monitoring/cancellation in the application. A local expiration timestamp is not broker cancellation proof.
- Stop distance is a sizing input and trigger, not a maximum possible loss. Model gap scenarios where execution is worse, or stop-limit never executes. Do not call a software-only stop protective during a service outage. Crypto lacks the simple stop-market listed for securities in these Alpaca docs.

### Gaps
- Exact fill probability, adverse selection, and slippage distribution require the user's actual venue, quote source, execution logs, size, and market regimes. A fixed tolerance cannot establish them.
- Protective order combinations depend on asset class, fractional eligibility, and broker capabilities. Do not assume stock bracket/OCO semantics apply to crypto.

## Which account, jurisdiction, precision, and session restrictions must be respected?

### Takeaway
Use current broker account/asset readback and fail closed on missing eligibility. In October 2026, Alpaca's old PDT restriction is obsolete; do not encode the historical $25,000/four-trade rule as its current policy.

### Cited Findings
- FINRA's replacement intraday margin standards became effective June 4, 2026; other member firms may phase in until October 20, 2027. The rule replaces day-count/PDT minimum-equity provisions and measures intraday margin exposure. Real-time blocking is permitted, but not mandated for every broker by that notice. — [FINRA Notice 26-10](https://www.finra.org/rules-guidance/notices/26-10)
- Alpaca says it migrated production on June 4, 2026, removed PDT designation and related restrictions, and told direct API users to replace deprecated PDT/daytrade fields with `buying_power`; the former fields were scheduled for complete removal July 6. — [Alpaca migration announcement](https://alpaca.markets/blog/finra-retires-the-pdt-rule-introducing-alpacas-new-intraday-margin-framework/)
- Broker account data includes `status`, `crypto_status`, `trading_blocked`, `account_blocked`, `trade_suspended_by_user`, cash and non-marginable buying power. Cryptocurrencies require cash, cannot be margin collateral, and account ACTIVE status indicates trading eligibility. Alpaca accounts may be margin-enabled even when the user chooses not to borrow. — [Alpaca Trading Account](https://docs.alpaca.markets/us/docs/account-plans)
- Fractional stock orders permit quantity or notional, not both; supported quantity precision is up to nine decimals, with DAY TIF. Check `fractionable` rather than assuming all listed assets qualify. This page still includes obsolete daytrade-count prose, which conflicts with the newer migration notice. — [Alpaca Fractional Trading](https://docs.alpaca.markets/us/docs/fractional-trading)
- Crypto asset metadata exposes `min_order_size`, `min_trade_increment`, and `price_increment`; supported precisions can change. Crypto trades all seven days, but only supported assets/jurisdictions/accounts qualify. — [Alpaca Crypto Spot Trading](https://docs.alpaca.markets/us/docs/crypto-trading)
- Georgia appears in Alpaca's published supported crypto jurisdiction list. The support article is dated May 2023, so it is context rather than proof of a specific account's current approval. — [Alpaca crypto eligibility](https://alpaca.markets/support/alpaca-cryptocurrency)

### Inferences
- Check broker flags before every order, including a closing sell. An entry halt in our application may permit a reducing sell, but cannot override a broker-wide prohibition. Require crypto status separately from securities status.
- Keep the first implementation long-only and unleveraged as an explicit project policy. Compute available new-buy dollars as the minimum of positive locally unreserved cash and current broker buying power, and also non-marginable buying power for crypto. Do not treat a 4x buying-power field as permission to spend 4x cash. Do not double-subtract broker reservations: keep a clear reconciliation contract for which values already include open orders.
- Validate quantity/price with decimal arithmetic. Refresh asset metadata, and disable that symbol if required metadata is absent rather than guessing precision from sample BTC values.
- For ETF intraday MVP, require a fresh official market clock indicating the regular session is open. Crypto's 24/7 schedule does not authorize ETF orders at 2am. Extended ETF sessions are a separate strategy/configuration decision; do not accidentally queue an order for next open.
- Keep broker capability/status handling extensible to multiple platforms: FINRA's phase-in period means another broker's current behavior may differ from Alpaca's. Do not generalize an Alpaca migration statement to every broker.

### Gaps
- No actual account was connected. Account-specific permissions, current flags, precise buying power treatment, current paper crypto enablement, and broker restriction reasons remain unverified.
- The account page contains simplified/possibly older buying-power formula descriptions. Use broker-calculated readback and confirmed rejection reasons; do not reconstruct margin entitlement from this formula.

## How should the engine handle ambiguous submissions, cancellation, and restart?

### Takeaway
An unknown order consumes risk capacity until reconciled. A timeout or cancel acknowledgement is not proof that no fill occurred.

### Cited Findings
- Alpaca explicitly warns that a submission timeout may mean the order reached the market; do not resend it or mark it canceled without confirmation. It directs users to the dashboard/support to establish the outcome. — [Alpaca Working with Orders, timeout FAQ](https://docs.alpaca.markets/us/docs/working-with-orders)
- Alpaca's automated-trading disclosure identifies connectivity, power loss, crashes, and missing/duplicated orders as risks needing continuous monitoring. It warns against overfitting, says the platform is not for HFT, and notes risk-reducing orders can fail to execute as hoped. — [Alpaca Risks of Automated Trading](https://files.alpaca.markets/disclosures/library/RisksAutoTrading.pdf)
- SEC Rule 15c3-5 guidance for broker-dealers with market access calls for preset financial thresholds and pre-entry checks against erroneous size/price and duplicate orders. This is a broker-dealer obligation, not a claim that a personal trader must implement that rule as a member firm. — [SEC market-access FAQ](https://www.sec.gov/rules-regulations/staff-guidance/trading-markets-frequently-asked-questions/divisionsmarketregfaq-0)

### Inferences
- Save immutable intent, risk decision, config version, account/quote IDs, and stable client-order ID before the network POST. Serialize submissions per account; same client ID plus changed body must fail.
- On timeout/transport uncertainty: mark UNKNOWN, retain cash/quantity/exposure reservations, and look up by the original client ID. A temporary 404 alone should not release it or permit a replacement. Keep an unresolved state requiring broker evidence/support if lookup remains inconclusive.
- On restart: recover intents and reservations, bind database to mode/account identity, query open and unresolved orders, import external positions/orders, and refresh account balances before enabling new entries. A flat local database is not a flat broker account.
- On cancel: retain reservations until terminal broker readback. Ingest cumulative partial fills idempotently; reconcile the account after order updates before releasing risk capacity. Protect against late fills, duplicated stream events, reconnects and out-of-order updates.
- Reconcile all brokers through one capital/risk view before simultaneous execution is enabled. Until cross-account reconciliation exists, each broker needs a separately bounded allocation, not full shared buying authority.

### Gaps
- No public REST guarantee that an arbitrary timeout has a bounded eventual 404/visibility window was found. Safe recovery cannot assume one.
- Corporate actions, fills corrected after settlement, external manual trades, and fee activity require more complete ledger reconciliation than simple cumulative order fills.

## How should freshness, liquidity, and 24/7 failure detection work?

### Takeaway
Trading permission should follow data health and account health, while service monitoring continues around the clock. Missing fresh data is a reason to withhold a new entry, not manufacture a quote or silently change data source.

### Cited Findings
- Alpaca stock streams carry exchange/condition/timestamp and bid/ask prices and sizes; stock quote sizes are round lots. It describes streaming as more current than polling historical endpoints. Feeds distinguish IEX, consolidated SIP, delayed SIP, and overnight sources; unavailable subscription feeds fail authentication. — [Alpaca Real-time Stock Data](https://docs.alpaca.markets/us/docs/real-time-stock-pricing-data)
- Crypto quote sizes are asset units. Alpaca documents venue locations, crypto order-book snapshots/updates, and bars containing quote midpoint prices; zero-volume bars may therefore contain prices without trades. Late trades can revise prior minute bars after the half-minute mark. — [Alpaca Real-time Crypto Data](https://docs.alpaca.markets/us/docs/real-time-crypto-pricing-data)
- Alpaca's market-data FAQ confirms crypto zero-volume/trade-count bars can use quote-derived prices and explains subscription-related 403 errors. — [Alpaca Market Data FAQ](https://docs.alpaca.markets/us/docs/market-data-faq)
- FINRA recommends quickly disabling algorithms/platforms, limited-size pilots, versioned code, adverse-market testing, controls/alerts/reconciliation, tracked significant incidents, and outbound-message thresholds for firms' algorithmic trading practices. These are useful design precedents for this personal system, not a claim that adopting a subset satisfies a member firm's obligations. — [FINRA Notice 15-09](https://www.finra.org/rules-guidance/notices/15-09)

### Inferences
- Record exchange event time, ingestion time, source/feed/venue, monotonic arrival age, and clock skew. Use exact data known at the decision time for replay. Evaluate only closed bars and keep bar revisions; never let later revised data leak into prior decisions.
- Check positive finite bid/ask, bid <= ask, nonzero relevant size, spread ceiling, feed entitlement, quote age and account age. Match venue with execution venue. Never compare ETF round-lot sizes with crypto raw units.
- Freshness ceilings such as 15 seconds for quotes and 30 seconds for account state are configurable MVP policy choices, not official safe limits. At a five-second polling cadence this is not a latency-sensitive trading system. Faster strategies need a streaming/data contract and measured latency before activation.
- Use a persisted entry-halt circuit for daily loss, drawdown, unresolved orders, repeated rejects, stale account/feed, abnormal spread/jump, and process health. Separate pause-entry, cancel-working-entry, and reduce-position actions. Halting entries does not cancel resting broker orders automatically or prove a flat account.
- A circuit should latch through restart and require an explicit reviewed reset; do not automatically resume after a brief healthy sample if the cause is unresolved. Reducing orders still need fresh quotes, verified holdings and broker eligibility. If the broker/feed is down, no software promise can make an exit execute.
- Add an independent heartbeat/watchdog and human alert channel for overnight failures; the trading process cannot reliably alert on its own total crash. Restart supervision is an operational function, not trading decision logic.

### Gaps
- Safe spread/liquidity/jump thresholds are not universal. They require asset/strategy-specific calibration and walk-forward/stress validation. No source supplies a threshold guaranteeing safe trading.
- The MVP polling implementation must expose degraded data health; an alive UI is not evidence of a healthy broker/data path or of 24/7 hosted availability.

## How do fees and paper assumptions change risk and profitability gates?

### Takeaway
Evaluate opportunities after conservative transaction costs, and distinguish estimated from settled fees and funding-adjusted profit. Paper fills establish software behavior, not economic profitability.

### Cited Findings
- Alpaca's first crypto fee tier (under $100,000 trailing 30-day volume) is 0.15% maker and 0.25% taker per trade. A marketable limit removes liquidity and is a taker. Fees are taken from the asset received, with CFEE/FEE activity queries available; the page says posting is end-of-day, so same-day queries may omit fees. — [Alpaca Crypto Spot Trading Fees](https://docs.alpaca.markets/us/docs/crypto-fees)
- Alpaca paper excludes market impact, latency slippage, queue position, price improvement, regulatory fees and dividends. It matches marketable orders without checking requested quantity against NBBO size and can produce random partial fills. Paper-only users receive IEX data while paper fills use NBBO. — [Alpaca Paper Trading](https://docs.alpaca.markets/us/docs/paper-trading)

### Inferences
- Tier-one taker/taker crypto round-trip fees alone are roughly 50 basis points, before spread and slippage (the exact compounded return hurdle differs slightly). A strategy seeking tiny gross moves needs to clear those costs before it is a viable candidate.
- Deterministic cost gate: `required_edge_bps = entry_fee_bps + exit_fee_bps + expected_spread_crossing_bps + configured_slippage_bps + uncertainty_buffer_bps`; reject entries with measured strategy edge <= this hurdle. A configured hypothetical target is not an estimated edge, and must not be reported as one.
- Budget fees conservatively as taker unless execution evidence proves maker status. Persist the fee schedule/version. Do not equate LIMIT with maker.
- Track the actual credited crypto quantity and fee currency. Cash-only crypto fee simulation differs from received-asset fee accounting; label the local simulator assumption and reconcile broker holdings against activity before calling net profit accurate.
- Report realized/unrealized P&L, actual fees, provisional fee reserve, spread/slippage estimates, deposits/withdrawals/dividends and service spend separately. Account equity change is not profit when funding or transfers occurred. Until activities are reconciled, label broker profit provisional.
- Use explicit stress fills outside the broker paper model: latency widening, zero liquidity, gap through stop, long outage, partial fill during cancel, stale quote, duplicate event and timeout accepted by broker. Preserve deterministic test fixtures rather than relying on random paper partial fills.

### Gaps
- Actual fee tier, regulatory fee schedule, funding flows and fee activity have not been connected. Paper fee behavior for each asset/order must be observed and reconciled, rather than inferred from the live schedule alone.
- No paper-only result proves a strategy's live fill quality, liquidity capacity, future expectancy, or maximum possible loss.

## Which risk algorithms are justified now?

### Takeaway
Add a deterministic pre-trade veto layer and replayable capital allocation first. Numerical risk budgets are conservative experiment settings; protect them from adaptive/LLM changes.

### Cited Findings
- Preset financial/price/size/duplicate checks are established market-access control patterns; FINRA's algorithmic guidance also emphasizes tracked parameter changes, testing, limited pilots and reconciliation. — [SEC market-access FAQ](https://www.sec.gov/rules-regulations/staff-guidance/trading-markets-frequently-asked-questions/divisionsmarketregfaq-0); [FINRA Notice 15-09](https://www.finra.org/rules-guidance/notices/15-09)

### Inferences
- Implement pure, versioned functions that return reason codes and intermediate arithmetic: quote validation; quantity/price rounding; available-risk calculation; pending-order reservations; portfolio/instrument/group exposure; stale-data veto; day-loss/high-water drawdown; cost hurdle; and order execution policy. Inject event time explicitly, use Decimal for money/quantity, sort inputs, and persist all inputs with the decision.
- Compute quantity from the minimum of authorized order dollars, unreserved cash, instrument/group/portfolio headroom, and configured per-trade risk dollars divided by adverse-price distance plus conservative per-unit costs. Round down. If any cap or required data is unknown, return no new entry. Stop-based risk remains a planned-loss estimate and needs separate gap stress.
- Treat correlated exposures together. SPY/QQQ and BTC/ETH should not be presumed independent simply because ticker strings differ. A fixed group cap is a transparent first approximation; empirical covariance/stress scenarios may refine it after enough aligned data is collected.
- Use cash/risk budgets for each strategy so intraday and swing workers cannot both allocate the same available capital. Aggregate open positions and pending orders across workers before approving either.
- LLMs/news agents can produce timestamped features or hypotheses. The risk engine owns eligibility, sizing and order authorization. Learning may propose a versioned candidate; it cannot lift loss/exposure limits, change active code, or promote itself based on in-sample performance.
- Minimum meaningful invariants: no duplicate submit on timeout/restart; no cash/held-quantity double-spend across simultaneous workers; no exposure above cap after rounding; no stale/future quote entry; no order using obsolete metadata; sell fills after cancel request counted once; unknown outcome retains reservations; identical input snapshot/config yields identical decision.

### Gaps
- This assignment researches operational/execution risk. ATR/volatility sizing, trend/mean-reversion entry rules, out-of-sample statistical validation and strategy selection are adjacent research; deterministic arithmetic alone cannot make market forecasts accurate.
- Personal risk tolerance, intended live capital and acceptable drawdown have not been supplied. Start with small paper-only budgets and version them; do not present a 1% daily or 5% drawdown circuit as a mandated or optimal threshold.
