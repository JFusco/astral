# Deterministic sizing, volatility, concentration and learning gates

Research date: 2026-10-24. Scope: transparent proposal algorithms and risk controls for the existing personal, long-only ETF/crypto paper engine. These recommendations are engineering policy choices unless a cited source explicitly states otherwise. Determinism means the same versioned input produces the same result; it does not mean a forecast or future return is accurate.

## What is the smallest defensible sizing algorithm?

### Takeaway

Implement a pure, replayable long-position proposal calculator that budgets a **planned loss**, divides by a conservative loss-per-unit estimate, then rounds quantity down and reapplies cash/exposure limits. Return a proposal and rejection reasons, without submitting an order or suggesting that the stop is an actual maximum loss.

### Cited Findings

- CME explains position sizing in terms of an account risk allowance and the distance to a logically selected stop. Its separate lesson explicitly says that the commonly discussed 2% threshold is arbitrary. The useful principle is the account-loss budget; there is no universally justified percentage for this project. — [CME position size](https://www.cmegroup.com/education/courses/trade-and-risk-management/proper-position-size); [CME 2% rule](https://www.cmegroup.com/education/courses/trade-and-risk-management/the-2-percent-rule)
- FINRA says a triggered stop becomes a market order and may execute substantially away from its trigger; a stop-limit introduces the possibility of no execution. A stop calculation is therefore a planning assumption, not a loss guarantee. — [FINRA stop-order risks](https://www.finra.org/investors/insights/stop-orders-factors-consider-during-volatile-markets)
- Fidelity defines true range as the maximum of high-minus-low, absolute high-minus-previous-close, and absolute low-minus-previous-close. It gives Wilder-style recursive ATR as `(previous_ATR * (n - 1) + TR) / n`; ATR measures volatility, not price direction. Fourteen periods is conventional, not an optimized universal choice. — [Fidelity ATR guide](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/atr)
- Python Decimal supports exact decimal representations from strings, configurable precision, explicit rounding modes, and nonfinite values that callers must reject. `ROUND_DOWN` means toward zero; `ROUND_FLOOR` means toward negative infinity. — [Python 3.13 Decimal](https://docs.python.org/3.13/library/decimal.html)

### Inferences

Recommended v1 interface: `propose_long(inputs, policy) -> {status, reasons, qty, notional, planned_stop, risk_estimate, costs, as_of, version, input_hash}`. All arithmetic uses Decimal values constructed from serialized decimal strings with fixed context precision. No global mutable state, clock reads, random numbers, network calls, LLM calls, or implicit source defaults in this function. Pass decision time explicitly. Quantities/prices serialize as strings. Preserve the inputs, policy and source snapshots alongside the result.

1. Require finite positive equity, executable entry bound, stop distance, quantity increment, minimum order, costs and remaining caps. A zero/negative denominator, nonfinite number, missing fee/slippage assumptions or unsupported broker precision rejects the proposal.
2. For an optional ATR stop, compute TR from complete OHLC bars; seed the first ATR with the arithmetic mean of the first `n` TR observations, then apply the recurrence in chronological order. With a strict previous-close requirement, ATR14 needs at least 15 bars. This is only the mathematical minimum. If a strategy uses SMA50 as well, its independent warm-up is longer. Record initialization, period and bar frequency so replay does not silently change its value.
3. Let `E` be reconciled account equity and `f` the versioned per-proposal planned-loss fraction. Let `R_available` be the lesser of `E*f`, remaining strategy risk, remaining aggregate planned risk, and remaining daily risk allowance. Pending entries consume risk immediately. Do not count unconfirmed cancels or hoped-for sell proceeds as released risk/cash.
4. Define long entry `P`, planned stop `S` with `0 < S < P`, entry/exit fees and adverse slippage estimates per unit, plus an explicit gap stress buffer. Set `L_unit = (P-S) + entry_fee_unit + exit_fee_unit + slippage_unit + gap_buffer_unit`. Do not count the spread twice when `P` is already the ask or worst executable buy limit. An ATR-derived `S = P - k*ATR` is permissible as a documented policy, but neither `k=2` nor any other multiplier is a known optimum.
5. Compute the raw quantity as the minimum of `R_available/L_unit`, cash-affordable quantity including entry costs, the order notional cap, remaining symbol cap, remaining correlation-bucket cap, remaining strategy cap and remaining gross cap. Compute `qty = floor(raw_qty / qty_increment) * qty_increment`. Flooring to a power-of-ten exponent alone is insufficient for increments such as `0.05`.
6. Reject zero/below-minimum size. Recompute all dollar totals from the rounded quantity and recheck every invariant; do not round risk upward to qualify an otherwise invalid order. Venue price-tick rounding is a separate operation with side-specific rules, followed by another validity check.
7. Return `planned_stop_is_submitted: false` unless a real, reconciled protective broker order exists. A pure proposal must not imply protective-order placement. Until broker-stop lifecycle and disconnect recovery are implemented, retain proposal-only semantics.

Illustrative policy, **not research-derived optimal settings**: reserve at most 0.10% equity per proposed trade, cap aggregate planned-loss exposure at 0.50%, keep the existing small notional/gross caps and long-only constraints. Do not silently relax them when performance improves. If existing holdings have unknown stop plans, do not assume zero loss risk: block a new risk-budgeted entry or use a conservative documented full-notional reservation.

### Gaps

- No source establishes a safe universal risk fraction, ATR multiplier, gap buffer, quote age or warm-up count for these ETF/crypto strategies. These must be explicit configurable hypotheses, stress-tested and shown to the user.
- An actual stop can gap, fail, be rejected or not be supported for the asset/order combination. Current proposal arithmetic cannot establish a maximum loss.
- No verified strategy edge or calibrated probability of winning exists yet. ATR sizing does not answer what to buy or when to buy it.

## How should costs, freshness, drawdown and correlated exposures gate proposals?

### Takeaway

The first gate should reject uncertain inputs and unaffordable or concentrated exposure. Use modeled costs and stress scenarios explicitly; do not treat a favorable target/stop ratio, low historical correlation or a profitable paper fill as evidence of positive expected return.

### Cited Findings

- FINRA explains that holdings within the same industry, geography or investment type may move together, and that overlapping ETF holdings can create hidden concentration. Holding multiple funds alone does not eliminate this risk. — [FINRA concentration risk](https://syndication.finra.org/content/concentrate-concentration-risk-0)
- Alpaca says paper trading omits market impact, order-information leakage, latency slippage, queue position, regulatory fees and dividends. It also says simulated fills do not test order quantity against quoted NBBO size. Paper returns cannot validate realistic liquidity/costs on their own. — [Alpaca paper specification](https://docs.alpaca.markets/us/docs/paper-trading)
- Alpaca historical stock bars have explicit feed and adjustment parameters, symbol-as-of mapping, and pagination. A page limit is across symbols rather than per symbol; incomplete pagination can silently leave a symbol without sufficient bars. — [Alpaca historical bars](https://docs.alpaca.markets/us/reference/stockbars)
- A primary empirical study of 103 equity strategies found that volatility-managed variants did not systematically outperform unmanaged variants and that feasible out-of-sample implementations generally disappointed relative to in-sample results. Volatility adjustment is a risk policy, not an established source of profit for this bot. — [Cederburg, O'Doherty, Wang and Yan, 2020](https://www.lehigh.edu/~xuy219/research/COWY.pdf)

### Inferences

Recommended gates in order:

- **Data gate:** bar start/end/received timestamps, symbol, feed, timeframe, currency, adjustment mode and source identity must be explicit and consistent. Only completed bars ending before the decision time can be used. Require strictly increasing unique timestamps and valid OHLC (`0 < low <= min(open,close) <= max(open,close) <= high`), finite nonnegative volume, and adequate coverage of the strategy's specified calendar. An absent zero-trade interval is not automatically a flat-price bar. Distinguish market closures from missing observations. For ETF daily data, use actual session calendars/early closes; for crypto use a defined UTC calendar. Reject future, incomplete or stale bars. Freshness thresholds depend on timeframe and latest expected session close, not one shared wall-clock timeout.
- **Quote/execution gate:** independently require a fresh quote and current reconciled account even when daily bars are valid. A daily signal is not permission to use yesterday's executable price. Freeze entries if any required source is unknown/stale; existing exit handling retains its separate fail-safe policy.
- **Cost hurdle:** enumerate fees, crossing spread, slippage and a conservative liquidity allowance. Require a strictly positive modeled net target reward and a configured minimum net reward-to-planned-loss ratio. Label this an economic feasibility filter. It is not a probability or alpha estimate. If win reward is `W_net>0` and loss magnitude is `L_net>0`, break-even win probability under that simplified two-outcome model is `L_net/(W_net+L_net)`. Without a calibrated out-of-sample probability, expected return is unknown. Trades can have exits other than the assumed stop/target, so report this limitation.
- **Shared account risk:** keep separate swing/intraday books and signals, but allocate cash, pending orders, symbol exposure and losses through one aggregate account ledger. Buying SPY in two strategies must count twice. A second broker does not create a second global capital budget. Make reservation updates transactional with order intent creation.
- **Concentration:** start with conservative static overlapping buckets (e.g., SPY/QQQ/IWM as US equity exposure, all crypto in one crypto bucket), plus instrument/gross caps. Do not assert these are exhaustive correlation estimates. ETF look-through data can refine them later. Historical rolling correlation should be diagnostic first: align observations, state window/sample count, reject missing data, and never let an estimated negative correlation unlock larger exposure. Stress all assets/buckets moving adversely together.
- **Drawdown:** use persisted daily/session opening equity and high-water equity. Define drawdown `max(0,1-equity/high_water)` and day loss from a reconciled baseline, adjusted for external cash flows. Track the account time zone and reset boundary explicitly; a UTC day for crypto and ET session attribution can coexist while the account circuit uses one declared boundary. Latch breaches and require explicit reviewed reset; do not auto-clear a loss halt at midnight without a policy. Missing cash-flow reconciliation means equity change is not trustworthy net trading profit.
- **Stress telemetry:** alongside planned-stop risk, report simple loss under adverse price moves, doubled/tripled slippage and simultaneous bucket declines. These are scenarios, not confidence bounds or VaR estimates. They remain meaningful when correlation/expected returns are unestimated.

### Gaps

- Cost and gap buffers must be calibrated against eventual provider fills and actual fee schedules; current local synthetic fills cannot do this.
- Free IEX quotes/bars represent that source, not consolidated liquidity. A paper fill against NBBO and an IEX-derived signal are distinct inputs that must remain labeled.
- Dynamic covariance optimization, Kelly sizing, leveraged volatility targeting and VaR/expected-shortfall capital allocation need reliable estimates and validation not currently present. Defer them rather than inventing confidence from a small dataset.

## What learning and testing gates are appropriate before automation?

### Takeaway

The learning layer should first collect reproducible point-in-time observations and evaluate frozen candidates offline. A candidate may earn a paper experiment; it should not rewrite risk limits, promote itself or enable autonomous execution because a recent backtest looks good.

### Cited Findings

- Bailey and colleagues show that ordinary hold-out testing fails to account for how many configurations were tried, discuss small-sample weaknesses, and propose estimating backtest-overfitting probability using combinatorially symmetric cross-validation. Their method is not a universal certification of a trading edge. — [Probability of Backtest Overfitting, original paper](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf)
- Bailey and López de Prado's Deflated Sharpe Ratio addresses multiple-testing selection bias and non-normal returns. They argue that reporting only winners while omitting trial counts inflates performance expectations. — [Deflated Sharpe Ratio, original paper](https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf)
- scikit-learn's TimeSeriesSplit uses time-ordered expanding training windows because ordinary cross-validation can train on future observations; its `gap` excludes observations between the training and test sets. Comparable fold metrics require attention to sample spacing. — [TimeSeriesSplit documentation](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html)

### Inferences

Smallest implementation now:

1. Add unit-tested pure ATR, sizing, cost/reward and drawdown functions, with golden examples and adversarial boundary inputs. Test no risk cap is exceeded after rounding, malformed/missing bars reject, wider stops/costs cannot increase allowed quantity under otherwise fixed caps, identical inputs replay identically, and entries cannot bypass pending-order reservations.
2. Store a proposal observation with strategy version, algorithm version, market-data snapshot hash, decision/receive times, parameter set, reason codes, estimated costs and explicit `execution_enabled:false`. Preserve rejected proposals as well as accepted ones. This adds deterministic decision telemetry without an LLM on every tick and fits the small operations budget.
3. Keep each strategy frequency/asset universe fixed for an experiment. Train/calibrate only on older data; evaluate the frozen candidate on later contiguous windows. Purge training labels whose outcome extends into a test period and use a gap at least consistent with the label/holding horizon. Feature normalization/selection and parameter tuning are fit inside training windows only. Archive all attempted configurations, not only winners. A final hold-out repeatedly consulted during redesign becomes part of research, not an untouched test set.
4. Model spread, commissions, adverse slippage, rejects, partial fills, queued limits, halts, outages, stale quotes and corporate actions. Trade at the next admissible observable price after the signal, not the closing price used to calculate it unless an actual implementable close-auction strategy is specified. A bar touching a limit is not proof of a fill. Synthetic chaos tests validate plumbing, not profitability.
5. Compare each candidate after costs with cash/no-trade and an appropriate passive benchmark over identical dates/capital conventions. Report net return, turnover, drawdown, exposure/time in market, per-asset/strategy concentration, cost sensitivity, tail losses and number of independent completed trade episodes. Win rate and Sharpe alone are inadequate.
6. Advance candidate states manually through `draft -> reproducible backtest -> forward paper -> reviewed`. Risk limits remain independently versioned. A model may propose a candidate change; it cannot alter guardrails, delete a losing history or reset the account. Maintain rollback to the prior frozen candidate.

There is no universally justified minimum such as 30 days or 100 trades that proves profitability. Predeclare the observation period, trade-count floor, risk bounds and evaluation metrics; label early results inconclusive when samples are short/dependent. Adding many parameter searches should trigger explicit multiple-testing analysis, not higher confidence. DSR/PBO are later diagnostics once enough candidate/return history exists; implementing them immediately on one short synthetic series would overstate their value.

### Gaps

- No actual historical dataset, point-in-time news/fundamental archive, forward broker-paper run or robust net-return backtest was available in this research task. No strategy profitability claim is warranted.
- The NBER Moreira/Muir source was found, but its full article/PDF returned 403 during this pass. The contradictory later empirical study above was opened and read; no claim of universal performance improvement is made.
- Pure arithmetic accuracy, test coverage and deterministic replay do not establish predictive accuracy. Those require separate evidence and continuing monitoring.
