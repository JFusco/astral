# First authorized automated paper execution experiment

The user explicitly chose a $25 BTC execution test before a research-qualified
trade. This is a separate experiment, not a waiver of the research strategy's
accounting, depth, calendar, liquidity or forward-performance requirements.
Those strategy gates remain closed.

## Implemented contract

`backend/pilot.py` runs through the existing durable intent/order engine. The CLI
requires `--execute`, the existing account-bound stage 2 ledger, its exclusive
executor lock, a singleton pilot lock and the fixed Alpaca PAPER configuration.
It exposes no web enable route. The dashboard service is stopped while the
runner owns the ledger. Strategy, research, model and exit workers are disabled.

The final pre-submit boundary permits BTC/USD IOC limit orders only. The entry
must fit $25 at its limit price, use fresh quotes with <=20 bp spread, remain
inside a 10 bp adverse-price bound, start flat with no local or broker working
orders, and fall inside the original two-minute entry deadline. It checks account
identity again. A durable permit is consumed BEFORE each request, including when
a response is lost. One entry is permitted for this experiment; changing the run
ID cannot create another entry in the same ledger. A completed rerun is a no-op.

The configured holding period is 20 seconds, with an earlier exit attempt at a
0.5% price move in either direction. Neither reference guarantees a fill or
maximum loss. Exits are bounded limits, may not sell more than the new gross buy
or current broker custody, and require a terminal entry outcome. One exit phase
allows up to three IOC orders solely to clear a partial residual; no new exit
order follows an unknown prior outcome. A cancellation may be attempted once
per known pilot order. No blind broker POST retry occurs. A crash can be resumed
using the same run ID and retained ledger; uncertain outcomes require readback.
A sustained outage can still require operator intervention and leave up to the
capped spot position exposed. No local process can guarantee availability.

The old unexplained BTC debit is retained. The user-authorized mechanical test
uses fresh flat broker custody and ordinary lifecycle-test risk checks, rather
than inventing a CFEE record or labeling the inventory reconciled. It does not
permit swing/intraday execution. Asset-denominated crypto fees can cause a new
unclassified debit too; fee accounting remains a separate gate before research
strategy execution.

## Confirmed broker-paper result

October 25, 2026:

| Action | Eastern execution time | Quantity BTC | Average price USD | Gross value USD |
| --- | --- | --- | --- | --- |
| Buy | 06:46:02 | 0.000311568 | 80195.191636946 | 24.986255467939991328 |
| Sell | 06:46:22 | 0.000310787 | 80073.58 | 24.88582770746 |

Both orders were reported filled. The buy/sell quantity difference is retained
as unclassified accounting, not a confirmed fee. The runner observed flat broker
custody and no nonterminal local orders afterward. A separate fresh broker GET
check also confirmed zero positions and zero open orders. Account equity changed from
99999.87 to 99999.70, or -0.17 USD. This is equity change for the experiment,
not fully reconciled net trading P&L, and not evidence of a profitable strategy.
No model ran or selected the ticker or entry time.

Private source receipts:
- `runtime/pre-execution-pilot.sqlite`
- `runtime/execution-pilot-final.json`
- `runtime/astral-stage2.sqlite` durable intents, readbacks, fills and permits

The 11 new pilot tests use synthetic brokers. They cover the full round trip,
no repeated completed entry, wrong symbol/type/time-in-force, amount/expiry/ID
bounds, lost accepted response, crash-after-entry recovery, pre-existing
positions and conflicting worker authority. They are separate from the actual
paper receipt. The complete suite passed 146 tests at this checkpoint.

## Next: research-driven experiment

Compare this retained execution baseline with a prospectively registered,
evidence-qualified strategy under equal risk. Record why symbol/time/amount
qualified, all vetoes and abstentions, actual fees and execution conditions.
The historical data adapter now aggregates documented executed trades instead
of using midpoint-contaminated crypto OHLC. Depth unit contracts, actual venue
liquidity, financial/protocol/macro coverage, fee classification and strategy
forward validation still govern research trading. Do not call a mechanical
round trip a qualifying research signal. See `ROADMAP.md` for sequencing and the
second horizon, learning and operational follow-ups.
