# Compare frozen BTC signals inside QuantConnect

This isolated comparison checks the independent LEAN port against ASTRAL's exact
frozen BTC signal function on identical bars inside the cloud process. It exports
aggregate diagnostics only. It evaluates neither profitability nor trading readiness.

## Scope and fixed inputs

Use Coinbase BTCUSD completed daily trade bars, January 1 through June 30, 2025,
in UTC. These historical development inputs are separate from Alpaca evidence
and all registered prospective windows. No runtime database, existing observation,
registration or holdout is read or updated.

The independent port preserves SMA20/SMA50, the strict prior-20-high breakout,
Wilder ATR14, 50 warmup bars and a maximum 90-bar rolling window. ATR restarts
within each window, matching frozen v1. Both implementations run against each
same in-memory window; the frozen function is extracted unchanged after all four
registered source hashes and the manifest identity pass verification.

The algorithm refuses every live deployment, including paper hosts. It has no
order-placement calls and requires zero orders and zero invested holdings before
emitting its completion summary. Calendar, liquidity, custody, sizing and
execution gates remain separate.

## Prepare the cloud file

Run from the repository root using the existing Python environment. Preparation
requires no credentials, network, Docker or running ASTRAL service:

```sh
.venv/bin/python -m scripts.quantconnect.compare prepare \
  --output outputs/quantconnect/prepared-v2-run
```

Each output directory must be new. After provider restrictions have cleared,
replace the isolated project's `main.py` with this generated file and verify the
saved source before running a backtest on the included node. Do not add resources,
purchase local data or deploy live. July 1 is included only to receive the completed
June 30 bar; July 1 bars are excluded.

## Validate a completed aggregate log

Verify the saved backtest's exact source, successful completion and zero orders.
Download its ordinary diagnostic log. Contract v2 emits only a source/header line
and one completion summary: 181 processed bars, 131 evaluated signals, signal
counts, mismatched-signal count and maximum numerical comparison errors.

It exports no raw OHLCV rows, indicator series or raw-data digests. Comparison
happens inside QuantConnect. Local log validation checks the aggregate contract;
it cannot independently recompute cloud results from exported market data.

```sh
.venv/bin/python -m scripts.quantconnect.compare compare \
  --log /absolute/path/to/downloaded-backtest-log.txt \
  --origin quantconnect-cloud-export \
  --output outputs/quantconnect/compared-v2-run
```

The tool saves JSON and Markdown reports. Exit 0 means the complete aggregate
reports agreement; 1 means mismatches; 2 means invalid evidence or refusal.
Signal decisions must match exactly; indicator differences allow `1e-20` absolute
tolerance. Old raw-export logs, missing/duplicated summaries, wrong source identities,
invalid counts and contradictory/non-finite errors cannot pass.

Use `--origin local-fixture` for synthetic checks. Origin labels are supplied by
the operator; they do not authenticate a cloud run. Verify the saved provider result
separately. Generated files, logs, account details and screenshots stay outside Git.
Outputs may use new directories under `outputs/quantconnect/` or system temporary
storage; existing evidence is never overwritten.

## Connected findings on October 26, 2026

The active Researcher seat and receipt confirmed USD 10 monthly. Private Accounting
inputs retain the monthly budget and one confirmed charge separately, with an
email receipt link. Overall cost completeness and net trading results remain unknown.

The existing [cloud project](https://www.quantconnect.com/project/38487956),
**Dancing Light Brown Lion**, remains isolated. Its IDE initially failed with a
QuantConnect extension startup error: `navigator is now a global in nodejs`.
Recycling only its coding session produced another failed environment with a
WebSocket 1006 error. No backtest was launched through the editor.

The official API authenticated successfully using the account's existing emailed
token, without rotating it or saving it in this repository. API readback verified
the saved source, and upload/readback verified the final v1 source exactly.
The compiler then rejected v1's raw OHLCV log export and reported an account
suspension until `2026-10-26 20:33:39` (provider timestamp). That rejection is retained
as a failure; it is not a compilation or historical validation pass.

No further cloud submissions were attempted after that guard. The local v2
correction keeps comparison in cloud memory and exports aggregate diagnostics.
It has not yet been uploaded, compiled or accepted by QuantConnect. The existing
cloud project still has the rejected v1 source; do not rerun it. Resume only with
the corrected bundle after the provider restriction has cleared, and retain any
new rejection without changing identity or trying another export channel.

Local controlled-dependency tests exercise the packaged algorithm, all signal
states, threshold equality, capped-window behavior, drift, invalid/missing bars,
aggregate refusal, output isolation and zero-order/live-mode boundaries. These
checks prove local behavior, not provider acceptance or profitable performance.
