---
meta:
  contentType: How-to
---

# Validate fee accounting without enabling orders

Use this procedure to validate the Alpaca paper activity feed in a disposable database. It covers historical reconciliation and a separate current, GET-only comparison. It does not activate the reader in the running application or authorize orders.

## Keep the inputs private

Maintain the original activity JSON, raw Server-Sent Events (SSE) capture, retained ledger capture and reviewed association evidence unchanged. Keep the versioned real-ID mapping outside the repository and `runtime/`. Each mapping binds its account, source-file hashes, individual event hashes, order identities, ownership, denomination and cash treatment.

Continuous integration uses `tests/fixtures/activity_feed/btc-sanitized-v1/`. Those derivatives have consistent surrogate identifiers, separate hashes and documented provenance. They cannot satisfy private acceptance or connected validation. Never commit the originals or the substitution table.

## Run the private historical replay

Choose a new private output directory. The database must be inside that directory; neither destination may already exist. Replace the descriptive paths below with your private input locations, then run from the repository root:

```sh
.venv/bin/python -m backend.activity_feed \
  --mapping-file /private/input_dir/alpaca-paper-fees-v1.json \
  --ledger-capture /private/input_dir/ledger-selected-readonly.json \
  --activity-capture /private/input_dir/activity-sse.json \
  --raw-stream /private/input_dir/activity-sse.raw \
  --database /private/new_output_dir/database.sqlite \
  --output-dir /private/new_output_dir
```

The command verifies the selected inputs against the mapping, copies retained rows into the disposable database and replays the original stream. It reopens the database and repeats the replay. It never opens the source ledger for writes.

Require every check in `receipt.json` to pass. The captured BTC case must retain 19 activities, eight fee associations and four cumulative fill rows. BTC ends at zero, cash equals $99,999.70, both measured reductions are confirmed fees, and additional custody debit equals zero. The $0.14 cash-fee breakout is already included in trade cash. A $99,999.56 cash result double-counts those fees and fails acceptance.

Keep the receipt private. It records source, mapping and implementation hashes, original timestamps, evidence availability, assertions and outcome. A missing input or hash mismatch fails validation; sanitized fixtures never substitute for missing originals.

## Compare current paper evidence

After the private replay passes, repeat the command with fresh disposable destinations and `--connected`. The command uses the existing server-side paper credentials for GET requests. It checks account identity before and after acquisition, compares positions and cash, and checks current orders against retained history. It does not start the Engine worker set or submit orders.

Keep paper orders, automatic entries/exits, shadow and paid model use disabled. A changed account, new execution, missing record or unsupported cash flow blocks reconciliation. New broker activity can make today's balance differ from the historical $99,999.70; never force a historical balance onto a current snapshot.

## Understand blocked results

The reader retains rejected records and partial streams before publication. Changed deliveries, revised activities and uncertain legacy/SSE overlap remain blocked across restart. This release has no automatic conflict-clearing operation; retain the evidence for a separately reviewed resolution.

The reader uses these limits:

| Boundary | Limit |
| --- | --- |
| Acquisition, including identity reads | 60 seconds |
| Stream | 30 seconds |
| Idle read | 8 seconds |
| Event frames | 10,000 |
| Received bytes | 8 MiB |
| Frame | 64 KiB |
| Delay between attempts | 60 seconds |
| Age of accepted acquisition | 90 seconds |

A longer scan can temporarily exceed the conservative freshness limit. Exactly 90 seconds remains eligible; older acquisitions block. Starting a scan does not refresh earlier evidence. Failed attempts block immediately, and recovery requires successful validated publication plus the existing snapshot-freshness checks.

Fee readiness is separate for BTC, ETH, SOL, SPY, QQQ, GLD, TLT and IWM. Only the captured BTC history has reviewed provider associations. Synthetic tests for another asset do not establish its fee contract. Unknown cash effects block dependent account-level cash readiness.

## Preserve activation boundaries

`Settings.enable_activity_feed` defaults to false and `activity_mapping_path` defaults to unset. `Settings.from_env()` does not read either field, even when candidate environment variables exist. The explicit [orders-off rollout entry point](ACCOUNTING-ROLLOUT.md) adds read-only preparation and bounded observation. Runtime activation still requires a separate owner decision; ordinary startup cannot activate the reader.

Before activation, require affected tests, `npm run verify:push`, the full `npm run verify:ci`, the private replay, a controls-off connected comparison and independent implementation review. A passing CI fixture is not private provider acceptance.

Rollback disables the reader while keeping the stricter readiness gate. Preserve raw records, mappings, conflicts, checkpoints and projections. Saved reports remain historical evidence; they cannot enable actions. Net P&L, tax basis, strategy readiness and live-money execution remain uncertified.
