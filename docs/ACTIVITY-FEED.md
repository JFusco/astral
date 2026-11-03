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

## Distinguish a fresh snapshot from retained history

Fresh snapshots receive a locally assigned version, `snapshot_epoch`. Current accounting requires the same positive integer in the stored snapshot, its state counter and the acquisition receipt. Equal balances or a backward wall clock cannot preserve authority after replacement. Existing identity, input, cutoff, freshness, mapping, conflict and reader checks still apply.

`accounting_snapshot.commit_snapshot` validates identity and finite financial values inside the caller's existing transaction. It stores the snapshot and counter atomically and opens no nested transaction. Reconciliation, refreshing collection and the disposable connected validator use this helper. Reconciliation alone retains custody checkpoints, risk marks, baseline equity and equity history.

Refreshing collection records the helper's returned epoch only after commit succeeds. Default collection captures the existing snapshot and counter together when choosing the actual stream cutoff. It adds no snapshot refresh, request or commit. Publication preserves the captured epoch; it never fills a missing version from current state.

Historical imports keep their original receipts and remain epochless. They can explain past cash and custody without establishing current authority. A connected validation run commits a genuinely fresh snapshot before collection, preserving its eleven GETs, input hashes and before/after balance and order checks. Its implementation manifest includes the shared snapshot helper.

Current reads always see the newest retained attempt by insertion order, including pending attempts with future or invalid timestamps. Historical projection reads retain their cutoff semantics. Unknown versions, failed transactions and unbound snapshots block current accounting; they do not erase historical evidence. A compatible older writer leaves no embedded epoch, so rolling forward cannot reuse a surviving counter alone.

Malformed counters require the separately approved [evidence-preserving recovery procedure](ACCOUNTING-ROLLOUT.md#recover-a-damaged-snapshot-counter). There is no automatic reset or repair.

## Keep timing diagnostics separate from accounting

Observation cycles have bounded start, finish, abandonment and sleep events. Their attempt identity becomes the batch ID only if collection starts. Standalone collection still allocates its own batch ID and retains its existing lifecycle; diagnostic events never become accounting attempts.

Outcomes retain acquisition-time request diagnostics with at most seven spans and fixed transport-phase summaries. Later retention, publication and sampling boundaries belong to the observer envelope. Each clock offset identifies its run/process; absent phases remain unknown. No diagnostic retains headers, bodies, query identifiers or arbitrary exception messages.

A diagnostic or retention storage failure disables the active observer in memory and skips later writes. Preserve any committed start/outcome/projection and report missing operational evidence. Recovery annotations never supply an outcome, successful completion or current authority. Historical imports, snapshot-version binding and every existing current-accounting gate retain their meaning.

## Rehearse old readers and new writers separately

Use only the pinned compatible predecessor from the reviewed rehearsal package. It can decode retained binary evidence and body references. An older reader without that codec is not a rollback candidate.

Rehearse rollback with the reader and execution controls disabled, retaining activity records, diagnostics, conflicts, epochs, receipts, projections and frozen manifests. Read historical evidence and explicitly reconcile only through a synthetic GET-only transport. Record expected snapshot, custody, equity, risk and request-evidence changes separately from preserved execution records.

On roll-forward, inspect current accounting before startup or reconciliation can replace the predecessor-written snapshot. A surviving counter cannot bind an epochless snapshot. Equal balances, equal timestamps and backward wall time cannot restore the old acquisition or witness. A genuinely fresh snapshot and a new qualifying nonhistorical acquisition remain necessary; persistent conflicts stay blocked.

Disposable fixtures establish compatibility mechanics only. Actual ledger-copy access, private original replay and a fresh GET-only broker comparison each need separate authorization. None of them activates the reader, approves an observation, enables orders or replaces the fixed [operational gates and owner decisions](ACCOUNTING-ROLLOUT.md#record-the-remaining-owner-decisions).

## Bind a future observation to prospective approval

The [observation approval procedure](ACCOUNTING-ROLLOUT.md#bind-approval-before-starting-a-run) allocates a run ID before operator approval. Launch requires the immutable record and its explicitly supplied byte digest, matching source/account/ledger/mapping/policy/controls and a prospective start window. The locked recheck occurs before Store/Engine startup. Research/news values must be explicit and match the approved policy.

Approval time is operator-attested, not independently timestamped. Existing run identities, including embedded summary and recovery IDs, cannot be reused. Unknown identity evidence blocks startup. No collector, real E1–E4 verifier or operational acceptance is added. Private replay, fresh GET-only comparison, activation and orders keep their separate authorization gates.
