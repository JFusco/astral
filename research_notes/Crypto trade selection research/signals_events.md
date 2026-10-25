# Crypto day and swing signals, events, and falsifiable tests

Research completed October 25, 2026. Scope is spot crypto day and swing trading for ASTRAL, starting with Alpaca. Numerical rules below are proposed experimental settings unless explicitly attributed to a source. They are not measured profitable parameters or current trade recommendations. Application status comes from the coordinator: daily-bar SMA/ATR hypothesis, event coverage unknown, shadow decisions only, and full-value unprotected-position budgets. This researcher made no application changes and submitted no orders.

## Which signal families merit testing, and on what horizons?

### Takeaway
Historical evidence supports investigating crypto momentum and market-specific information, but it does not establish an executable five-minute trading edge. Start with a small frozen family of interpretable experiments, use realistic cost hurdles, and permit “no trade” as the normal outcome.

### Cited Findings
- Liu and Tsyvinski report cryptocurrency-specific time-series momentum and investor-attention predictability in their historical study of Bitcoin, Ripple, and Ethereum. This is historical research, not a current trading signal. — [NBER working paper 24877](https://www.nber.org/papers/w24877)
- Borri, Liu, Tsyvinski, and Wu’s March 2026 revision uses weekly portfolios sorted on prior two-week returns, and reports size, momentum, and value factors. Its dataset includes inactive coins to address survivorship bias. It also documents frequent large jumps in crypto using five-minute data. The five-minute observations measure jumps; they do not establish a five-minute momentum strategy. — [Author research, revision 4](https://arxiv.org/html/2510.14435v4)
- Coinbase’s current public spot stream offers five-minute candles updated each second, an order-book snapshot/update channel, trade updates, and separate heartbeat messages. A changing candle is not necessarily a completed candle. — [Coinbase WebSocket endpoints](https://docs.cdp.coinbase.com/coinbase-app/advanced-trade-apis/websocket/websocket-endpoints)

### Inferences
Proposed initial experiment matrix, with all parameters frozen before each forward window:

| Experiment | Decision bars | Regime / eligibility | Entry hypothesis | Exit / holding hypothesis |
|---|---|---|---|---|
| Intraday breakout | 15m primary, 5m separately scored | BTC and asset 1h trend nonnegative; eligible spread, turnover, depth | Closed-bar close exceeds previous 20 completed-bar high; dollar volume above rolling median | ATR-based invalidation, trailing rule or 4h time exit; no adding to losers |
| Intraday pullback continuation | 15m with 1h context | Positive 1h trend, moderate realized volatility, no event exclusion | Pullback then completed-bar recovery above a fixed moving-average threshold | Structural/ATR stop, trend invalidation, or 4h time exit |
| Range reversion challenger | 5m or 15m | Predeclared low-trend regime; not during jumps, launches, or known critical events | Fixed volatility-normalized deviation and confirmed reversal | Mean touch, adverse boundary, or 1h timeout |
| Swing continuation | 4h with 1d context | Positive higher-timeframe trend; sufficient warmup and liquidity | Prior-window breakout or separately registered pullback recovery | ATR/trend exit or 2–5 day maximum hold |
| Catalyst observation | 15m/1h | Verified event/news identity and first-seen timestamps | Record post-release behavior; initially observation-only | No execution until its own forward evidence supports it |

- These are deliberately distinct hypotheses. Do not combine all indicators and choose the most flattering backtest. Compare 5m versus 15m as separate trials; do not let a failed 5m strategy inherit a successful 4h result.
- Historical weekly-factor evidence offers more direct motivation for a swing challenger than for scalping. A negative or unstable intraday result is useful evidence, not a reason to tune endlessly. — [Research motivation](https://arxiv.org/html/2510.14435v4)
- Rank only candidates that pass eligibility. A deterministic score can combine a frozen signal-strength percentile, independently estimated executable liquidity, and a lower confidence bound on out-of-sample net expectancy. Until there is a credible expectancy estimate, show signal strength and cost hurdle separately instead of inventing an expected return.
- The LLM should explain the supplied evidence and countercase. Its adjectives or self-reported confidence should not size positions, choose an unseen indicator threshold, or override a veto.

### Gaps
- No source inspected proves these exact rules profitable on Alpaca’s current venue, fee tier, eligible symbols, or the user’s latency. No current coin recommendation is supported by this research alone.
- Current ASTRAL daily history cannot validate 5m, 15m, or 4h behavior. It needs venue-specific point-in-time histories and a separate forward capture before those hypotheses can be assessed.

## What execution and sizing hurdles must a short-horizon signal clear?

### Takeaway
Fees and executable liquidity can eliminate a visually attractive setup. A limit price controls the worst acceptable price but does not prove maker fees, a fill, or a guaranteed stop loss.

### Cited Findings
- Alpaca’s published first crypto tier, for rolling 30-day volume below $100,000, charges 0.15% maker and 0.25% taker. Marketable limit orders remove liquidity and are taker orders. Fees are charged in the received asset, and CFEE/FEE activity can post at the end of the day. — [Alpaca crypto spot fees](https://docs.alpaca.markets/us/docs/crypto-fees)
- Coinbase’s `ticker_batch` has no best bid/ask; `level2` provides book snapshots and increments. Its documentation also warns that sequence gaps can identify dropped messages. — [Coinbase endpoints](https://docs.cdp.coinbase.com/coinbase-app/advanced-trade-apis/websocket/websocket-endpoints); [sequence numbers](https://docs.cdp.coinbase.com/coinbase-app/advanced-trade-apis/websocket/websocket-overview)
- The SEC’s October 2024 complaints alleged paid wash-trading services that created artificial crypto volume. An allegation is not a finding that a particular current asset’s volume is fraudulent; it demonstrates why reported volume alone cannot establish executable liquidity. — [SEC original enforcement announcement](https://www.sec.gov/newsroom/press-releases/2024-166)

### Inferences
- Fee arithmetic at Alpaca’s first tier is approximately 30 bps maker/maker, 40 bps mixed, and 50 bps taker/taker per round trip, before spread and slippage. Use the observed account tier and actual fill fee classification where available. For planning, assume taker unless a credible queue-aware model supports maker execution. This arithmetic follows the published schedule; it is not an estimate of realized costs. — [Fee basis](https://docs.alpaca.markets/us/docs/crypto-fees)
- Net opportunity gate: `net_edge_bps_lower_bound > entry_fee + exit_fee + entry_implementation_shortfall + exit_implementation_shortfall + uncertainty_buffer`. Do not double count spread if measured shortfall already includes it. Stop/target distance alone does not estimate edge.
- Proposed risk sizing: `q = floor_to_increment(min(risk_dollars / (stop_distance_per_unit + stressed_exit_cost_per_unit), remaining_cash / all_in_entry_price, remaining_full_value_budget / all_in_entry_price, liquidity_capacity_units, symbol_cap_units))`. A local conditional stop cannot justify treating the loss as bounded by stop distance; retain the full-value exposure cap. Emit every binding cap and the resulting planned/stressed loss in the receipt.
- Prototype liquidity guard settings to test, not market facts: quote age ≤2s for intraday / ≤5s for swing order submission; complete historical warmup; execution-venue 24h dollar turnover ≥$1m; planned order ≤0.1% of trailing-minute traded notional; planned size ≤5% of visible executable depth inside the maximum slippage band. If only top-of-book is available, do not infer total depth; use a smaller cap or abstain. The current app’s 15s quote and daily-volume checks are operational starting points, not proof that these tighter checks pass.
- Freeze a maximum spread appropriate to the experiment and reject if expected move cannot cover total costs. A universal “meme coins may use wider spreads” exemption defeats this rule.
- Stress all routes at taker/taker fees, 1×/2×/3× observed spread and slippage, fill delays 0.25s/2s/10s, partial fills, disappearing depth, gaps beyond stops, order-status timeouts, and venue outage during a triggered exit. A deterministic simulator must fill against later executable quotes, not at the desired stop price.
- Volume anomalies, repetitive trade sizes, or cross-venue disagreement can quarantine a candidate; they do not conclusively detect wash trading. No deterministic filter can guarantee the absence of manipulation. — [Risk motivation](https://www.sec.gov/newsroom/press-releases/2024-166)

### Gaps
- This research did not obtain Alpaca full-depth historical data, queue position, or per-symbol capacity measurements. Displayed-book filters remain proposed until the adapter’s units, freshness, and coverage are verified.
- Provisional paper P&L should remain fee-incomplete until delayed asset-denominated debits reconcile. A zero fee-activity response on trade day is not proof of zero fees. — [Alpaca posting behavior](https://docs.alpaca.markets/us/docs/crypto-fees)

## How should news, token events, identity, and meme coins affect decisions?

### Takeaway
Use event and news evidence with explicit identity, timestamp, date precision, and coverage. Treat meme coins as eligible for research under stronger evidence and liquidity requirements; a matching ticker and a high percentage gain are insufficient.

### Cited Findings
- CoinGecko’s official token lookup accepts an asset-platform identifier and contract address and returns platform/contract metadata and market tickers. This is a usable identity cross-check, not proof that the asset is tradable at the connected broker. — [CoinGecko contract endpoint](https://docs.coingecko.com/reference/coins-contract-address)
- Arbitrum’s official supply page distinguishes monthly team/investor unlocks from continuously vesting Foundation tokens; its displayed numerical circulating-supply examples are explicitly dated March 2024. Current retrieval does not make those numbers current. — [Arbitrum supply documentation](https://docs.arbitrum.foundation/token-supply)
- The Arbitrum Foundation’s vesting contract source describes an initial quarter vest and subsequent proportional monthly vesting. A schedule alone does not show whether beneficiaries claimed or sold tokens. — [Original contract source](https://github.com/ArbitrumFoundation/governance/blob/main/src/ArbitrumVestingWallet.sol)
- The February 18, 2026 Ethereum Foundation update targeted Glamsterdam for the first half of 2026; the currently retrieved Ethereum roadmap lists Q4 2026 and explains that plans change. These are conflicting date versions, not a precise execution-time calendar. — [Dated Foundation announcement](https://blog.ethereum.org/2026/02/18/protocol-priorities-update-2026); [current roadmap](https://ethereum.org/roadmap/)
- The Federal Reserve publishes the FOMC calendar, including its October 27–28, 2026 meeting. This is a direct macro-event source, not evidence that a particular coin will rise or fall. — [Federal Reserve calendar](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm)
- SEC staff describe meme coins as speculative and often volatile; the February 2025 statement has no legal force, is not a Commission rule, and explicitly requires facts-and-circumstances analysis. Do not encode “meme coin” as a blanket legal or tax classification. — [SEC staff statement and footnotes](https://www.sec.gov/newsroom/speeches-statements/staff-statement-meme-coins)
- A 2025 author preprint investigates wash trading, liquidity-pool price inflation, concentrated ownership, and rug pulls in meme tokens. Its sample-selected findings must not be treated as the current probability that any particular coin is fraudulent; the retrieved preprint contains unfilled publication-template fields, so use it as a risk taxonomy rather than authoritative current prevalence. — [Original meme ecosystem study](https://arxiv.org/html/2507.01963v1)

### Inferences
- Instrument identity key: `(broker_asset_id, venue_pair, base_asset_id, quote_asset_id, network_id, contract_or_native_asset_id)`. No symbol-only join across news, market data, holdings, or order APIs. A bridge-wrapped version, redenomination, chain migration, or colliding ticker is a separate identity requiring an explicit mapping and effective date.
- A crypto event record should include `source_url`, `source_authority`, `published_at`, `first_seen_at`, `version_hash`, `known_at`, `event_start/end`, `date_precision`, `affected_asset_ids`, `category`, `coverage_until`, and `confidence_basis`. A quarter-only roadmap must stay an interval, not become a fabricated midnight timestamp.
- Keep separate event types: scheduled vesting eligibility, actual vesting claim/transfer, exchange deposit, and market sale. “Unlock equals dump” is an invalid deterministic inference. Recompute unlock size against a denominator dated no later than decision time; quarantine stale or conflicting supply figures. — [Schedule and dated-number motivation](https://docs.arbitrum.foundation/token-supply)
- Required coverage categories should depend on the strategy and asset: protocol upgrades, supply/unlocks, exchange listings/delistings/maintenance, security incidents, governance votes, and designated macro events. Missing optional funding or on-chain features should not fabricate a veto for a rule that does not use them; missing required coverage should abstain. Crypto should not inherit an equity earnings-calendar requirement literally.
- Proposed initial event policy: exclude new intraday risk ±30m around a verified major macro release; exclude new positions near a major token/protocol event when the event interval overlaps the planned holding horizon, unless the experiment is explicitly the catalyst strategy. These windows are conservative trial settings needing forward evaluation. Always permit protective exits.
- News ingestion should deduplicate syndication, retain the original and revised content, preserve first-seen time and provider delay, resolve instrument identity, classify source authority, and expire evidence at a horizon-appropriate age. “No matching headline” must distinguish genuinely checked coverage from unavailable feed, truncated result set, or unrecognized alias. Social popularity is attention evidence, not independently verified positive news.
- For meme candidates add identity verification, listing age/history sufficiency, observed exit liquidity, issuer/admin powers where available, ownership concentration with exchange/pool wallets distinguished, and liquidity removal/transfer restrictions where applicable. Unknown contract risks should keep DEX execution disabled; a centralized-exchange listing does not prove contract safety or replace venue liquidity checks.
- Funding/open interest can be optional externally sourced regime features for spot trading. Label the exact derivatives venue, instrument, timestamp, contract units, funding interval, and forecast-versus-realized rate; do not pretend Alpaca spot provides them or that the user may trade an offshore derivatives venue. Current Coinbase docs distinguish eligible non-US Global Derivatives from US products. — [Coinbase current product scope](https://docs.cdp.coinbase.com/coinbase-app/advanced-trade-apis/overview)

### Gaps
- No verified all-crypto event feed with complete historical first-seen versions was obtained within this research. A calendar adapter and coverage registry still need implementation; a fresh current web search cannot reconstruct past availability.
- No specific meme coin currently satisfies ASTRAL’s guards on evidence gathered here. “Any crypto” should mean broad discovery with capability-based eligibility, not an unconditional execution allowlist.

## How can ASTRAL falsify a supposed edge and solve operational edge cases deterministically?

### Takeaway
Separate operational correctness from profitability. Deterministic gates can prevent known invalid actions; they cannot eliminate market uncertainty or guarantee that a selected strategy makes money.

### Cited Findings
- Bailey and coauthors show why selecting the best of many backtests produces false positives and develop probability-of-backtest-overfitting analysis with combinatorially symmetric cross-validation. — [Original PBO research](https://carmamaths.org/resources/jon/backtest2.pdf)
- Bailey and López de Prado’s Deflated Sharpe Ratio addresses selection bias from multiple testing and non-normal returns. It requires recognizing the search behind the winning result; a high raw Sharpe alone is insufficient. — [Original DSR paper](https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf)
- Scikit-learn’s time-series splitter keeps training before testing and supports a gap, while warning that comparable fold metrics assume equally spaced samples. A fixed gap is not automatically a full interval-aware purge for variable-length holding periods. — [Official TimeSeriesSplit documentation](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html)

### Inferences
Proposed evaluation contract:

1. Freeze the universe snapshot, fee schedule, indicator definitions, strategy version, configuration hash, maximum holding interval, and promotion criterion before each test window. Count every indicator/timeframe/symbol/filter/LLM prompt variant as part of the search log, including discarded failures. — [Multiple-search motivation](https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf)
2. Persist raw append-only quotes/trades/bars and news/event versions with source and receipt times. A replay at `t` may use only evidence received by `t`; the bar must be complete, and simulated execution must occur strictly after decision and assumed routing delay. Test every prefix of a dataset against its full-run decision prefix to detect future leakage.
3. Use chronological walk-forward fitting and testing. Purge training labels whose holding/outcome intervals overlap validation, and impose an embargo where folds reuse neighboring observations. Do not fit volatility scaling, universe filters, or feature normalization on future data. A simple `TimeSeriesSplit(gap=n)` needs explicit verification against the maximum outcome interval. — [Chronological split foundation](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html)
4. Preserve assets that subsequently delisted, failed, migrated, or lost liquidity. A present-day winner list is not the historical universe. Test market regimes, weekends, time zones, trending/range periods, and liquid versus less-liquid groups separately. — [Inactive-asset motivation](https://arxiv.org/html/2510.14435v4)
5. Baselines: cash/no-trade; deterministic same-signal/no-LLM selector; fixed liquidity-first universe; BTC-only signal; and matched-turnover random entries with identical holding and risk rules. Include the real entry and exit cost model for every baseline.
6. Publish net expectancy per fill and per attempted order; exposure and turnover; return and drawdown; loss tails; maximum adverse/favorable excursion; time in market; fill/reject/partial/cancel rates; signal-to-order delay; mark-to-fill shortfall; and cost-adjusted results by regime and symbol. Use day/block resampling rather than pretending overlapping trades are independent. A promotion threshold needs uncertainty intervals and a predeclared minimum effective sample, not an arbitrary universal “100 trades proves it.”
7. Use DSR/PBO as diagnostics after recording the complete experiment search, then reserve an untouched final test and subsequent forward paper period. Reject parameter settings whose returns collapse under modest nearby settings or realistic friction. Neither diagnostic replaces market-realistic fill simulation or forward observations. — [DSR](https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf); [PBO](https://carmamaths.org/resources/jon/backtest2.pdf)
8. Do not let a current LLM retrospectively rank known historical coins and call the result out-of-sample. Its pretrained knowledge may contain later outcomes even with browsing disabled. Prefer prospectively captured reviews; historical LLM comparisons should be labeled potentially contaminated, with deterministic evidence-only baselines retained.

Deterministic regression cases to add or verify (these are required behaviors, not claims they are already implemented):

| Case | Required observable result |
|---|---|
| Ticker collision / wrong network / token migration | Quarantine identity; no order; receipt names conflicting IDs |
| News first seen after signal or revised after replay time | Exclude it from the decision; preserve original version |
| Roadmap changes from H1 to Q4 / date only | Preserve old knowledge; interval stays uncertain; no exact time invented |
| Unlock claim without sale | Mark event type accurately; do not assert selling pressure as fact |
| Candle revised or still forming | Do not enter on incomplete/future close; replay version disclosed |
| Sequence gap / stale quote / crossed market / missing depth | Pause affected entry rule, resnapshot/reconcile, record reason |
| Taker marketable limit mislabeled maker | Fee hurdle uses taker; missing fee classification stays conservative |
| Both stop and target touched in one OHLC bar | Use finer quote sequence or conservative ambiguous outcome; never choose favorable ordering |
| Price jumps below stop; process down during trigger | Fill at later executable bid, include gap loss; flag protection unavailability |
| Partial fill + timeout + restart | Reconcile stable client ID and fills before any retry; no duplicate exposure |
| Two strategy sleeves sell same symbol concurrently | Reserve each sleeve’s quantity; no cross-sleeve liquidation or oversell |
| Late crypto-asset fee / dust / fee pagination | Deduplicate activity and reconcile net holdings; do not silently round away unexplained balances |
| Candidate hype spike after repeated failed searches | Search-budget log includes failed variants; no automatic live promotion |

### Gaps
- These controls can make the system reproducible and fail closed, but cannot guarantee fills, bounded losses during outages, immunity from manipulation, or a profitable edge. Source-backed risk taxonomy must be converted into concrete tests and matched to actual code before claiming a gap solved.
- ASTRAL’s current operational tests, shadow abstentions, and synthetic timing replay are not a validated crypto strategy performance study. The full historical dataset, venue execution calibration, event coverage, forward sample, and promotion decision remain outstanding.
