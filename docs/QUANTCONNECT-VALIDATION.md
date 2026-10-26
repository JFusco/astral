# Compare frozen BTC signals with QuantConnect

Use this isolated comparison to check whether QuantConnect's LEAN backtesting engine reproduces ASTRAL's frozen BTC price hypothesis. It evaluates identical historical bars and reports differences. It does not evaluate profitability or authorize trading.

## Scope and fixed inputs

The comparison uses Coinbase BTCUSD daily trade bars from January 1 through June 30, 2025, in UTC. These are historical development inputs, separate from Alpaca evidence and every registered prospective window. No runtime database, existing observation, experiment registration or holdout is read or updated.

The independent port preserves SMA20/SMA50, a close strictly above the prior 20 highs, Wilder ATR14, 50 initial warmup bars and a maximum 90-bar rolling window. ATR restarts within each window, matching frozen v1. Every eligible day produces an entry candidate, hold or exit-review signal. Those signals are price diagnostics; ASTRAL's calendar, liquidity, inventory, sizing and execution gates still apply separately.

The tool verifies the existing manifest identity and all four registered source hashes before preparing or comparing. It refuses code drift without changing any registration. The algorithm rejects every live deployment, including a broker's paper deployment. It has no order-placement calls and checks zero orders and zero invested holdings before emitting a completion record.

## Prepare the cloud file

Run commands from the repository root with the existing Python environment. Preparation needs no QuantConnect credentials, network connection, Docker installation or running ASTRAL service.

Create a new output directory for each preparation:

```sh
.venv/bin/python -m scripts.quantconnect.compare prepare \
  --output outputs/quantconnect/prepared-run
```

Replace the isolated QuantConnect project's `main.py` with the generated file, save it, and run **Backtest Project**. Use the included backtesting node. Do not deploy live, add resources or purchase local datasets for this comparison. The cloud dates include July 1 only so LEAN can deliver the completed June 30 bar; July 1 bars are excluded.

## Compare a completed cloud export

Check the saved cloud backtest for successful completion, Coinbase BTCUSD input and zero orders. Download its full log. The file needs the comparison header, 181 bars, 131 signals and the completion record. Copied terminal excerpts can omit records and cannot substitute for the complete export.

Compare the downloaded log into a new directory:

```sh
.venv/bin/python -m scripts.quantconnect.compare compare \
  --log /absolute/path/to/downloaded-backtest-log.txt \
  --origin quantconnect-cloud-export \
  --output outputs/quantconnect/compared-run
```

The tool writes `report.json` and `report.md`. Exit status 0 means complete exported signals agree; 1 means a comparison mismatch; 2 means invalid evidence or another refusal. Signals must match exactly. Indicators allow an absolute difference of `1e-20`, independent of displayed rounding.

Use `--origin local-fixture` for synthetic tests. Origin labels are operator-supplied provenance, not provider authentication. A passing fixture report cannot establish cloud acceptance.

Missing days, duplicate or out-of-period bars, invalid prices, absent or misaligned signals, wrong source identities and incomplete exports cannot pass. A digest binds every exported bar and signal. A matching digest establishes export integrity; verify its QuantConnect origin against the saved backtest separately. Reports retain the input log, comparator, bundle and frozen-source hashes, but do not authenticate a pasted log.

Output directories must be new and under `outputs/quantconnect/` or the system temporary directory. Existing output is never overwritten. Keep generated bundles, raw logs, account information and screenshots out of Git.

## Connected setup on October 26, 2026

The signed-in organization showed an active Researcher plan, a $10 estimated bill for October 26 through November 26, one backtesting node, one research node and zero live hosts. A later Gmail receipt and matching invoice confirmed a USD 10 payment on October 26 for that service period.

At the owner's request, private Accounting inputs now record the active USD 10 monthly budget and one receipt-backed USD 10 charge. A new saved report and the running Accounting page show both figures separately. Earlier inputs and saved reports are retained; overall spending coverage and net trading results remain unknown. Receipt identifiers, payment details and account information remain outside Git.

The isolated [QuantConnect project](https://www.quantconnect.com/project/38487956) was created under the generated name **Dancing Light Brown Lion**. Its editor buffer matched the packaged signal-only source after saving. Cloud synchronization remains unverified because the QuantConnect extension host failed to start and Backtest Project produced no run or result. A reload remained on **Loading coding environment**. Browser diagnostics reported a QuantConnect extension startup error, `navigator is now a global in nodejs`, and an extension-host startup timeout.

The cloud comparison is **blocked**, with no backtest result or historical parity claim. Resume with this existing project after its coding environment recovers, or authenticate the official LEAN CLI outside the repository. Verify the saved cloud source matches a freshly prepared bundle before running it. No API token, credential, subscription change, data purchase or live deployment was created.

Local controlled-dependency tests cover all three signal outcomes, exact thresholds, rolling-window behavior, altered results, incomplete or invalid exports, frozen-source drift, protected output paths, zero-order completion and live-mode refusal. These tests do not establish QuantConnect runtime compatibility or provider acceptance.
