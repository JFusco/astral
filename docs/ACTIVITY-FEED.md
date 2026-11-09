---
meta:
  contentType: How-to
---

# Validate fee accounting without enabling orders

Use this procedure to validate the Alpaca paper activity feed in a disposable database. It covers historical reconciliation and a separate current, GET-only comparison. It does not activate the reader in the running application or authorize orders.

## Qualify a replacement G3 evidence package

Joe accepted prospective G3-v2 evidence on November 8, 2026. This replaces only the dependency on the original BTC recording, including handoff task 1’s source binding and task 2’s historical replay. G3-v1 remains unresolved. Preserve its validator, fixed assertions, private artifacts, failed receipts and sanitized regression. A new capture is never recovered original evidence. Resume the exhausted discovery trail only for a separately authorized concrete lead.

Use the separate `backend.activity_qualification` command for G3-v2. The [engineering issue](https://github.com/JFusco/astral/issues/52) describes its scope. The old CLI below remains available for authenticated originals; its fixed BTC balances and counts do not apply to the replacement case.

Before collecting inputs, qualify a **G3-v2 package acquisition/export method** under a separate reviewed scope. This consumer does not supply that producer. Complete history, required real-provider fee examples, raw capture provenance and independent expectations remain mandatory. Missing or unsupported evidence stops qualification; do not discard records or manufacture trades to fill gaps.

The supported envelope is a USD paper account with evidenced zero cash/assets at inception. Include complete history through the closing snapshot. Supported movements are TRD, quantity-zero USD JNLC, and reviewed asset-debit, included-USD or standalone-USD fees. Every trade needs a non-standalone fee association. Legacy activity overlap, corrections, nonzero openings and unsupported economics are incomplete. Broader projection behavior needs a separate owner scope decision.

### Prepare the private consumer package

Keep every input outside the repository and `runtime/`, in private directories. Use regular, singly linked 0600 files with absolute canonical paths. The output must be a new 0700 directory under an existing private parent, outside every input directory. Its new database must be directly inside it. No source database is opened or migrated.

All JSON control objects reject unknown fields, duplicate keys and nonfinite constants. Raw provider metadata remains intact. Versioned envelopes use `schema` and integer `version: 1`:

| Document | Required fields beyond schema/version |
| --- | --- |
| `g3-v2-selected-ledger` | `capture_id`, `account`, `ledger_id`, `captured_at`, `selection`, `producer_refs`, `state`, `optional_state`, `rows` |
| `g3-v2-activity-capture` | `capture_id`, `account`, `request`, `content_type`, `stream_closed`, `parse_errors`, `limit_or_error`, `termination`, `raw_sha256`, `raw_bytes`, `decoding_layer`, `sent_at`, `ended_at`, `delivered_count`, `distinct_count`, `observation_refs`, `producer_refs`, `events` |
| `g3-v2-reviewed-expectations` | `account`, `environment`, `amendment_sha256`, `capture_id`, `inputs`, `mapping_sha256`, `mapping_digest`, `source`, `evaluator`, `history`, `deliveries`, `movements`, `orders`, `fills`, `economics`, `custody`, `coverage`, `closing` |
| `g3-v2-operation-request` | `operation`, `attempt`, `account`, `invocation`, `inputs`, `source`, `environment`, `destinations`, `controls`, `limits`, `start_window`, `supervision`, `attestation`, `replay_receipt`, `compare` |

`selection` maps each table to its exact ordered Store columns. `rows` contains all rows of orders, fills, activities and observations, preserving source array order without status filtering. Add exactly the custody checkpoint events referenced by `custody_checkpoint.seqs`, preserving `seq,at,type,payload`. Missing references are incomplete; duplicate identities are rejected. Payload/context/request/raw columns contain losslessly decoded JSON text, preserving the text itself. Resolve evidence-blob references in the separately qualified exporter. This semantic export does not replace raw typed SQLite recovery/G4 evidence.

Retain state `mode`, `account_binding` and `account_snapshot`. `optional_state` declares a boolean presence for each of `fee_reconciliation_required`, `custody_checkpoint`, `snapshot_epoch` and `assets`; include the corresponding state value exactly when present. Import no unrelated pointers to omitted tables. Preserve an embedded snapshot epoch, but historical activity imports remain epochless and grant no current authority.

The capture’s `request` contains `method,host,path,status,params,received_at`; `params` contains the actual sent `since,until`. Require HTTP 200 from the fixed paper activity route, `text/event-stream`, `stream_closed:true`, empty `parse_errors`, null `limit_or_error` and `termination:normal-finite`. Preserve original delivered raw bytes and describe their HTTP decoding layer. The parser must reproduce the ordered `events`; bind raw length/hash, delivery count, distinct-reference count, actual dispatch/end/receipt clocks and supporting observation/producer references. Normalized SSE frames are not original raw bytes.

Continue using the version-1 `reviewed-provider` mapping. Bind its exact byte SHA-256 separately from its logical `activity_projection.digest`. Every `source_files` reference must resolve to an explicitly approved input. Every trade, journal and fee has a matching expectation, and vice versa. A standalone-fee evidence hash must resolve to retained derivation bytes. Agreement proves consistency, not authenticity.

### Seal independent expectations

The evaluator derives expectations from retained evidence before running the projector. `evaluator` records `identity,method,sealed_at,derivation_refs,limitations,independent:true`. References are exact paths in the request’s input allowlist. Hashes and attestation bind claims; they cannot authenticate human reasoning or prove provider completeness.

`history` contains `since,until,balance_at,knowledge_cutoff,created_at,zero_origin,evidence_refs`. Require inception-wide coverage, `zero_origin:true`, a microsecond-representable cutoff, and `balance_at <= until <= received_at <= knowledge_cutoff`. Bind the closing snapshot’s timestamp exactly. All retained decision evidence and mapping knowledge must exist by that cutoff. Historical replay, reopen and inventory use the same cutoff; invocation clocks remain separate.

Specify the complete schedules:

- `deliveries`: ordered objects with `event_id,ref_id,sha256`.
- `movements`: every distinct reference mapped to `type,sha256,at,executed_at`.
- `orders`: every local client ID mapped to `client_id,order_id,symbol,side,status,book,filled_qty,filled_avg_price,row_sha256`. Explicitly represent local rejected orders with no provider identity.
- `fills`: every retained fill ID mapped to `row_sha256,client_id,source,at,known_at,quantity,price,value,trade_refs,evidence_refs`. Partition executions exactly once among cumulative-readback deltas.
- `economics`: every movement mapped to `qty,price,net_amount,currency,symbol,book,order_id,client_id,treatment,gross_value,denomination,evidence_refs,equation_evidence`. Use null for fields inapplicable to journals/fees; preserve source values exactly.
- `coverage`: nonempty actual reference lists `included_usd,asset_debit`, plus retained evidence references `no_second_debit`. Empty lists and synthetic examples cannot establish operational coverage.
- `closing`: independently calculated `cash,included_fee_usd,gross_books,net_books,positions`.

For each trade, `equation_evidence` contains `gross_from_qty_price` and `net_from_gross_and_included_fees`. Each declares boolean `exactness_evidenced` and `evidence_refs`. The exact relations are gross value = quantity × price, and signed net cash = signed gross cash + included negative USD charges. A supported nonzero residual fails. Unestablished exactness is incomplete even with zero residual; it cannot erase a separately demonstrated failure. There is no guessed tolerance or quantization.

Closing cash counts trade net cash, journals and standalone USD fees once. Included USD fees are disclosed without a second debit. Asset fees reduce the associated buy’s received base asset once; denomination and ownership need retained evidence. Reconcile each movement, each cumulative fill delta, each order total and only then closing totals. Offsetting errors cannot pass through balance agreement.

`custody` is the complete reduction list keyed by `(client_id,order_id,symbol,book)`. Each object also contains `quantity,linked_confirmed_fee_quantity,additional_debit_quantity,classification,checkpoints`. Each checkpoint contains `before,after,before_at,after_at,before_quantity,gross_buy_quantity,after_quantity,reduction_quantity`. Require an actual confirmed-fee window, exact reduction = before + gross buy − after = linked fee, zero additional debit, no custody issues and complete set equality. An ambiguous zero debit cannot pass. Retain the existing single-owner, nonconcurrent, fresh-checkpoint and 60-second window rules.

Economic numbers must be decimal strings matching `-?(?:0|[1-9][0-9]*)(?:[.][0-9]+)?(?:[eE][+-]?[0-9]{1,3})?`: at most 128 characters, 50 coefficient digits and explicit/effective exponents in [-100,100]. Calculations use precision 50 with inexact/invalid/overflow/underflow traps. Preserve RFC3339 clocks with up to 18 fractional digits. Custody conversion must preserve ordering, ties, cutoff and 0/15/60-second decisions; otherwise precision is unsupported.

### Bind and invoke one operation

The acyclic binding order is captures/support → mapping → expectations → operation request → replay receipt → comparison request → comparison receipt. No file embeds its own byte hash or a downstream digest. `inputs` lists exact `path,role,sha256,bytes` entries. Roles are `ledger,capture,raw,mapping,expectations`, optional `replay_receipt`, and any number of `support` entries. Expectations bind the capture/support entries; mapping identity has separate fields.

`source` is the complete maintained `activity_rollout.source_identity()` value. `environment` records the actual executable, Python, linked SQLite and HTTPX/httpcore/dotenv versions. `invocation` binds `executable,module,arguments`; omit only the external `--request-sha256` pair from `arguments` to avoid a digest cycle. `destinations` binds `database,output_dir`. `controls` explicitly sets every qualification `CONTROLS` field false.

`limits` contains positive integer `input_bytes,response_bytes,total_response_bytes,whole_seconds`. Control documents are capped at 1 MiB, data/expectations at 32 MiB each, raw SSE and each response at 8 MiB, and total response bodies at 32 MiB. The actual request may set stricter limits. Whole-call supervision remains a separate qualified prerequisite, capped by the unchanged 3,720-second contract. `supervision` binds its `request_sha256,method_sha256,stop_procedure,qualified:true`; these are operator declarations, not proof a supervisor is running.

`start_window` contains `not_before,before`. `attestation` contains `operator,approved_at,accepted:true`. Fill actual values only after establishing them and obtaining the exact request-byte approval. Capture stdout, stderr and exit status outside the input/output trees. The following is a command shape, not an executable approval:

```sh
.venv/bin/python -m backend.activity_qualification replay \
  --request-file /private/requests/replay.json \
  --request-sha256 approved_request_byte_sha256 \
  --expectations-file /private/inputs/expectations.json \
  --mapping-file /private/inputs/mapping.json \
  --ledger-capture /private/inputs/ledger-selected-readonly.json \
  --activity-capture /private/inputs/activity-sse.json \
  --raw-stream /private/inputs/activity-sse.raw \
  --database /private/new_attempt/database.sqlite \
  --output-dir /private/new_attempt
```

Replay has null `replay_receipt` and `compare` request fields and never loads credentials. After separately accepting a PASS receipt, a new `compare` request adds `--replay-receipt` and `--replay-receipt-sha256`. It binds that pair in `replay_receipt`. Its `compare` object declares GET, the fixed paper host, the exact `ROUTES` sequence, `max_gets:11` and `credential_mechanism:Settings.from_env`. Comparison repeats the entire offline qualification in fresh destinations before reading credentials. Enabled controls are rejected, not masked.

The maximum successful sequence is account/positions/clock; orders with `status=all,limit=500`; account/activity stream/account/positions; account/positions/clock. There is no pagination, redirect, retry, data-host request or mutation. The existing dynamic interval reaches the earlier of three days ago, earliest fill minus one day, and account creation; `until` is refreshed immediately before dispatch. Record actual sent bounds. New history makes the sealed package incomplete; missing or changed sealed records fail. Retain raw response chunks privately before parser delivery, including bounded partial bodies on failure.

Comparison retains the historical snapshot/custody result separately from the new bracket. Matching observations establish observed stability only, not atomic provider state, delayed-correction absence or exclusive writer ownership. No Engine workers start.

### Interpret the outcome and preserve receipts

Both commands emit one `g3-v2-outcome` JSON object, including pre-output argument failures. It records operation/attempt when known, status/exit code, verified request digest, receipt path/hash or null, primary/secondary failures, missing evidence and cleanup state. Receipts use `g3-v2-replay` or `g3-v2-compare`, with source/environment/input pins, fixed check names, historical cutoff, actual invocation clocks, workload, results and output hashes. The receipt excludes itself from its output inventory and is created exclusively once.

| Exit | Meaning |
| --- | --- |
| 0 | PASS: every mandatory check and finalization passed |
| 1 | FAIL: an established qualification mismatch |
| 2 | REJECTED: invalid arguments, approval or preflight contract |
| 3 | INCOMPLETE: missing/unsupported evidence, interruption or exhausted bounds |
| 4 | ERROR: unexpected internal failure |

Preserve partial outputs and all inputs. A demonstrated failure retains precedence over later unknowns; retain secondary errors too. Forced termination or storage failure can prevent a final receipt. An absent receipt or unknown cleanup never earns a pass. No automatic retry follows.

Qualification engineering is package A only. Acquisition/export qualification, actual evidence capture, independent expectations, replay, backup/restore/current comparison, runtime/observer qualification and final independent G3 acceptance remain distinct approvals. Every G4 threshold and the separate paper-entry/exit/reconciliation gate remain binding.

## Keep the inputs private

Maintain the original activity JSON, raw Server-Sent Events (SSE) capture, retained ledger capture and reviewed association evidence unchanged. Keep the versioned real-ID mapping outside the repository and `runtime/`. Each mapping binds its account, source-file hashes, individual event hashes, order identities, ownership, denomination and cash treatment.

Continuous integration uses `tests/fixtures/activity_feed/btc-sanitized-v1/`. Those derivatives have consistent surrogate identifiers, separate hashes and documented provenance. They cannot satisfy private acceptance or connected validation. Never commit the originals or the substitution table.

## Legacy: replay the original BTC case

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

## Legacy: compare current paper evidence

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

Historical imports keep their original receipts and remain epochless. They can explain past cash and custody without establishing current authority. The legacy connected validator commits a genuinely fresh snapshot before collection. G3-v2 comparison preserves the historical snapshot and records fresh observations separately; neither receipt activates current accounting. Its implementation manifest includes the shared snapshot helper.

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

Disposable fixtures establish compatibility mechanics only. Actual ledger-copy access, the applicable G3-v2 or authenticated-original replay, and a fresh GET-only broker comparison each need separate authorization. None of them activates the reader, approves an observation, enables orders or replaces the fixed [operational gates and owner decisions](ACCOUNTING-ROLLOUT.md#record-the-remaining-owner-decisions).

## Bind a future observation to prospective approval

The [observation approval procedure](ACCOUNTING-ROLLOUT.md#bind-approval-before-starting-a-run) allocates a run ID before operator approval. Launch requires the immutable record and its explicitly supplied byte digest, matching source/account/ledger/mapping/policy/controls and a prospective start window. The locked recheck occurs before Store/Engine startup. Research/news values must be explicit and match the approved policy.

Approval time is operator-attested, not independently timestamped. Existing run identities, including embedded summary and recovery IDs, cannot be reused. Unknown identity evidence blocks startup. No collector, real E1–E4 verifier or operational acceptance is added. Private replay, fresh GET-only comparison, activation and orders keep their separate authorization gates.
