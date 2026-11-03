---
meta:
  contentType: How-to
---

# Prepare an orders-off accounting observation

Use this runbook to prepare and, after a separate owner decision, observe the existing activity reader for 24 hours. It serves the operator of one Alpaca paper account. Preparation does not activate the reader, restart services or authorize orders. The implementation scope and acceptance plan are recorded in [issue #46](https://github.com/JFusco/astral/issues/46).

## Validate private inputs without activation

Complete the [private historical replay and GET-only comparison](ACTIVITY-FEED.md) against the reviewed code. Keep originals and the reviewed mapping outside the repository. Missing or changed sources fail validation; sanitized fixtures cannot replace them.

Run the default preparation command with the exact operational ledger, account and mapping digest. The digest is SHA-256 of the reviewed mapping file bytes, including whitespace. Replace the descriptive values with your private inputs:

```sh
.venv/bin/python -m backend.activity_rollout \
  --ledger /private/operational/astral.sqlite \
  --mapping-file /private/reviewed/mapping.json \
  --mapping-sha256 reviewed_mapping_file_sha256 \
  --account-id reviewed_paper_account_id
```

This command opens SQLite in read-only mode. It checks paper settings, account identity, mapping/source hashes, unsettled orders and disk space. It makes no broker request and never constructs Store or Engine. A successful result reports `reader_activated: false`.

Normal startup still ignores activity-reader environment variables. Do not add activation fields to `.env`. The rollout entry point rejects enabled orders, shadow, exit monitoring or model use instead of silently changing those controls.

## Obtain the runtime activation decision

Before activation, the owner must approve the exact code revision, ledger/account binding, private mapping digest, 24-hour window, limits, process restart and rollback. That decision must explicitly permit additive activity tables and new accounting evidence in the existing ledger. A prepared command, mapping, source artifact or this document never grants permission.

Require these prerequisites:

1. Affected tests, `npm run verify:push` and full local `npm run verify:ci` pass for the delivered source. Record hosted checks separately.
2. Private original replay and a fresh GET-only comparison pass independently from CI fixtures.
3. A focused implementation review has no unresolved accepted findings.
4. A rehearsal using an isolated disposable database confirms schema addition, duplicate/restart recovery and retained execution rows.
5. Record a consistent private database backup, execution-table hashes, enabled controls, process identity, storage and latency baseline under the approved operational procedure.

Only after that decision, stop the approved executor gracefully and use the approved-record invocation below. `--activate` alone fails before application startup. It serves the existing application on `127.0.0.1:8766` with one worker and the existing database lock. Do not start a second writer or stop unrelated processes. No activation command runs as part of installation, import, delivery or testing.

The activation path rechecks ledger identity and unsettled orders under the application lock before opening Store. The mapping is validated once and pinned in memory. A new reviewed mapping requires another explicit rollout invocation; editing or deleting the original file does not change the pinned contract.

## Bind approval before starting a run

Prepare a private proposal, obtain operator approval and supply its exact byte digest at launch. This procedure supports operator-attested approval. It does not verify a cryptographic signature or an independent trusted timestamp. The approving operator remains the trust boundary; a source artifact or file alone grants no permission.

Resolve every owner decision before approving the record. Keep the ledger, mapping, policy, owner evidence and approval outside the repository. Use the same delivered checkout for preparation and launch. Source identity includes its Git revision, maintained file contents and modes, and symlink target text. Missing Git metadata, changed source or unreadable evidence blocks startup. This identity does not attest installed dependencies or prove delivery.

### Freeze an explicit policy

Create a private UTF-8 JSON policy with exactly these fields. The values shown as placeholders must come from the prospective owner decision; the implementation supplies no operational tolerance or cadence defaults.

```json
{
  "schema_version": 1,
  "tau_seconds": "approved_residual_tolerance",
  "tau_c_seconds": "approved_clock_tolerance",
  "precision_seconds": "approved_positive_precision",
  "overhead_policy": "recorded-sleep-write-only",
  "e4_policy": "allow-indeterminate",
  "research_enabled": false,
  "news_enabled": false,
  "state_poll_seconds": "approved_positive_interval",
  "observation_poll_seconds": "approved_positive_interval",
  "local_post_policy": "prohibit",
  "compute_policy": "quiet-host",
  "owner_decisions_sha256": "approved_owner_record_digest"
}
```

Tolerances are finite nonnegative decimal strings. Precision and polling intervals are finite positive decimal strings. E4 also accepts `require-determined`; POST policy also accepts `emergency-ends-run`; compute policy also accepts `explicit-overlap`. Their detailed choices and permitted actions belong in the immutable owner record referenced by its byte SHA-256. Additional overhead credit requires separate policy design. These examples select no operational values.

The owner record must include backup and independent restore evidence, frozen raw SQL execution hashes, process/executable/invocation ownership, rollback/restart instructions, actor and POST rules, permitted compute, and the remaining G3 evidence. A digest references that evidence; this tool does not verify its contents or availability. Manual operational review remains required. It neither interprets real E1–E4 nor certifies G4.

### Prepare and approve the private proposal

Set `ASTRAL_ENABLE_RESEARCH` and `ASTRAL_ENABLE_NEWS` explicitly to the approved `true` or `false` values in the invoking process. Do this before loading dotenv values. Effective settings must match the policy. Research requires an existing matching frozen registration; preparation and locked startup recheck both reject its absence or mismatch. Preparation never creates registration.

Use the existing preparation arguments with `--policy-file`, `--start-not-before`, `--start-before` and `--proposal-output`. The start-window timestamps use UTC `+00:00` with at most six fractional digits. The output must be a new private file outside the repository. It contains an allocated 32-character lowercase hexadecimal run ID, complete source identity, account/ledger/mapping bindings, effective controls and policy digest. The ledger stays read-only, and no broker request or application startup occurs.

The output starts with null `approved_by` and `approved_at`; it cannot activate. After reviewing the proposal and referenced owner evidence, the named operator fills those two fields. Preserve every proposal field. `approved_at` must be at or after proposal creation and strictly before startup, under the disclosed operator/host-clock trust model. Freeze the record and independently record its exact SHA-256 before launch. A caller who invents or backdates an attestation violates that trust model; this implementation cannot independently prove the human action or clock correctness.

The start window permits startup only. It never replaces or shortens the actual 86,400-second observation. The start timestamp must be inside the window. Approval, policy and source are rechecked before Store/Engine construction under the existing ledger lock. The approved ID is assigned before application creation; every run uses that ID. Malformed, duplicated or unreadable identity evidence blocks. Any retained rollout, attempt, sleep or embedded summary/recovery identity prevents reuse.

### Supply the approved record explicitly

Use `--activate` only with a separate activation authorization and all existing preparation arguments. Add `--policy-file`, `--approval-file` and `--approval-sha256`, with the exact operator-approved digest. Retain explicit research/news process values. Missing, changed, future, late, expired-window or mismatched approval denies startup. Changing policy bytes also denies startup, even when their decoded values are unchanged.

Normal preflight without these options remains read-only and reports the effective research/news booleans. It does not allocate authority or activate the reader. Private proposal files contain account and ledger audit data; standard output does not disclose them. The CLI emits a fixed preflight error rather than raw paths, account data or exception text.

A run identity is considered used when its first durable observation/recovery evidence is retained. An attempt that fails before retaining any identity has no independent consumption receipt. Do not automatically retry an uncertain startup. Preserve the failure and let the operator reconcile it; use a new proposal and approval for a restart. This operator-attested design does not coordinate another host or an administrator who edits evidence.

Keep all fixed budgets, inclusive parser boundaries, counting points and server vetoes. Denied order requests, risk plans, shadow calls and emergency halts can change frozen execution hashes even with orders disabled. Follow the approved POST policy and fail/end the window when required; never exclude those writes after the run.

## Observe collection and accounting separately

Read `GET /api/accounting/observation` for sanitized operational measurements. The endpoint is unavailable as an active observation during ordinary startup. It never returns credentials, private mapping content, account identifiers or ledger paths.

Collection uses the existing parser, immutable retention, projection, inventory, custody and reporting paths. A current broker snapshot and publication share the existing reconciliation lock. The collector verifies account identity before and after the stream and checks post-stream cash/positions. It never copies a historical balance into a current snapshot.

An accepted publication does not certify a later snapshot. A newer snapshot beyond the actual stream cutoff remains blocked even when its balances match. Pending/failed acquisitions, stale snapshots, changed inputs and uncovered activities remain separate failures. The summary reports complete acquisitions, matched publications and sampled current availability separately; sample counts are not a continuous uptime measurement.

Alpaca documents [delayed balance propagation and backfilled activity](https://docs.alpaca.markets/us/docs/activity-sse). Retain mismatches and retry through the bounded next acquisition. Missing fees never mean zero fees. New executions, unassigned fees, unsupported journals and revisions remain blocked until separately reviewed evidence establishes their treatment. The eight historical BTC associations do not cover future trades or another ticker.

## Enforce the observation limits

The observer preserves existing server vetoes and these fixed limits:

| Boundary | Limit or measurement |
| --- | --- |
| Observation | 86,400 seconds of monotonic time |
| Delay between completed attempts | 60 seconds; no overlapping observer acquisitions |
| Acquisition / stream / idle deadline | 60 / 30 / 8 seconds |
| Frames / bytes / frame size | 10,000 / 8 MiB / 64 KiB |
| Accepted acquisition / snapshot age | 90 / 30 seconds |
| Trading request budget | Existing 60 normal calls per minute; preserve 20 recovery slots |
| Observer request charge | At most seven budget units per acquisition, including the snapshot |
| Storage admission | Less than 256 MiB growth of database plus WAL; at least 5 GiB free |
| Publication latency target | Histogram p95 upper bound at most 250 ms |
| `/api/state` latency target | Histogram p95 upper bound at most 2,000 ms, with actual request samples |

The observer uses normal request capacity for every added GET and respects provider cooldowns. Budget units conservatively include all three snapshot requests even when the snapshot fails early; they are not an exact count of requests sent. Existing API request receipts remain the transport evidence. Initial application reads and other workers also consume the shared budget.

The collector admits a cycle only within the storage budget and checks again before publication. An in-flight bounded acquisition can exceed the admission threshold; its raw evidence remains retained, publication stops and no further acquisition starts. Database plus WAL growth is a conservative physical-storage measurement that includes other workers. Do not prune, vacuum or reset evidence to obtain a pass.

The 24-hour deadline cancels an in-flight acquisition and disables the reader gate. Storage failure and interruption also disable it. The application can continue serving GETs; it does not automatically restart the observer or enable trading. Retained projection effects remain historical evidence, while current accounting stays blocked when the reader is disabled.

## Reuse evidence within a state read

Each `Engine.state()` read holds `store.lock` throughout construction. Paper accounting captures one cutoff and shares its ledger inputs and batch-validation results through an explicit local context. Each distinct selected batch is validated once, including a different historical checkpoint batch. Expected validation failures are retained only for that read. Projection results and issues remain private to each caller; current-accounting gates are evaluated independently. Inventory is computed once and supplied to readiness.

The context is cleared before the lock is released, including when construction fails. The next state read validates evidence again and detects changed inputs, epochs or corrupt retained evidence. Historical attribution cannot establish current authority or hide newer attempts. Standalone accounting reads do not retain this context. Snapshot and acquisition freshness, epoch binding, witness rules and all execution vetoes remain unchanged.

Validation counts from controlled fixtures demonstrate read reuse. They do not prove production latency or satisfy observation acceptance. The parser, deadlines, acquisition schedule and GET/SSE measurement populations are unchanged.

## Interpret browser state-read provenance

The browser records `ownReadAt` and the exact `server_time`/sequence identity only when its current-generation GET is adopted. The incoming timestamp and any prior displayed timestamp must parse to finite values. Invalid timestamp parsing preserves display behavior but produces no receipt. Server seeds, rejected responses, failed requests and obsolete generations cannot create or refresh a receipt.

An adopted SSE state clears the receipt, even when timestamp and sequence match. Healthy streaming therefore normally leaves both fields null: stream messages keep the watchdog current without another GET. A later eligible browser GET can issue a new receipt; the next adopted SSE state clears it again. A retained receipt describes only its original displayed response, including during disconnection. It proves neither freshness nor execution eligibility and adds no action consumer or authorization path.

## Decide whether the observation passed

Require an actual 24-hour window, at least 99% complete acquisitions, no unexplained acquisition gap over 120 seconds, the storage/latency limits above and zero broker mutations. Preserve startup, completion, interruption and failure receipts. Every unmatched publication and sampled blocked state needs an explanation; a collection-success count cannot conceal unusable accounting.

Poll `/api/state` and the observation endpoint at the agreed cadence during the approved window to retain current gate status and latency samples. Missing latency samples, acquisition gaps or missing original evidence cannot pass. The observer deliberately reports `owner-review-required`; it does not certify its own operational acceptance. Simulated clocks and disposable provider tests do not establish elapsed real-world observation.

Compare covered current cash and asset quantities exactly, retaining the normal inventory/custody checks. Confirm that shared views apply asset fees once and disclose already-included USD fees without another cash debit. Unsupported symbols remain unverified. Save abstentions and blocked intervals as evidence.

If acquisition coordination cannot produce usable covered publications, fail the rollout and resolve that behavior before another activation. Never move the cutoff, extend freshness or hide an attempted acquisition to manufacture availability. Accounting acceptance does not clear liquidity, events, entry timing, sizing, execution or exit-supervision gates.

## Roll back while retaining evidence

Use the approved procedure to stop the observer and return to ordinary reader-disabled startup, keeping orders disabled. Recheck controls and retained execution rows. Preserve raw streams, association versions, conflicts, acquisition outcomes, projections and observation receipts. Existing projection effects may still explain historical inventory; they cannot establish current readiness.

Use the updated [compatible evidence reader](EVIDENCE-STORAGE.md) for rollback. Older code cannot decode new binary payloads and immutable body references. Preserve the new tables and existing frozen manifests; the authorized replay/liquidity reader changes remain visible as code drift.

Never restore old balances, clear a conflict, reset a baseline or treat an empty legacy fee response as zero fees. Restart recovery starts a new observation window and requires fresh covered acquisition. It never repeats an order or silently counts downtime as observed operation.

## Diagnose blocked accounting without changing the observation

Acquisition receipts retain an allowlisted failure class, stage, dispatch outcome and at most seven request spans. Snapshot requests have their actual account, positions or clock path; a three-unit snapshot charge does not establish three sent requests. Request spans record elapsed time and received HTTP status without exception messages, headers or credentials. Lock wait, scheduled-wake delay and event-loop lag have separate fixed-size histograms. These measurements do not change deadlines, budgets or acceptance thresholds.

An incomplete acquisition retains its raw evidence and blocks current accounting. It does not establish that provider history disappeared or that balances differ. A complete replay that omits previously covered activity still triggers the disappearance veto. Original failed receipts and legacy projections remain unchanged.

`/api/state` includes `accounting` evidence with the latest snapshot time, actual stream cutoff, acquisition time, publication time and latest attempt. The observation endpoint exposes the same boundary evidence. The last verified checkpoint has `historical-only` status and `current_authority: false`. A failed or pending attempt never promotes that checkpoint into current cash. Ledgers without the new checkpoint pointer return no historical checkpoint until another validated publication; they do not invent historical verification.

The existing availability count samples after the scheduled delay. A separate publication-availability count samples immediately after publication. Neither count measures continuous uptime. Keep both populations distinct in acceptance reports.

### Validate a covered window in isolation

`Engine.inspect_accounting_window` captures or rechecks a read-only witness under the reconciliation lock. It issues no broker request and never grants execution authority. Rechecks require the same symbol, snapshot epoch and timestamp, batch, mapping and accounting inputs, with all current coverage and freshness gates still passing. Snapshot replacement invalidates the witness even when balances and timestamps are identical or the wall clock moves backward. A changed input, new accounting attempt or expired window also requires abstention.

The witness's `snapshot_epoch` is the positive integer already validated against the stored snapshot, counter and acquisition. Booleans and other malformed values are rejected with `FeedError`. Legacy witnesses without an epoch are rejected too; never stamp, coerce or repair them. Capture a fresh witness only after current accounting qualifies again. A fresh snapshot commit alone cannot replace the required qualifying acquisition.

Expiry remains the earlier of snapshot time plus the configured age (capped at thirty seconds) and acquisition time plus ninety seconds. Exact equality remains eligible; future evidence is rejected. `expires_at` is display information, and changing it cannot extend authority. Inspection releases the reconciliation lock before returning. A returned witness neither retains that lock nor authorizes a later action; a future consumer must hold its own required locks through recheck and decision. This method does not hold reconciliation waiting for a browser.

Reconciliation runs about every ten seconds; an accounting attempt waits sixty seconds after completion. A newer snapshot invalidates the previous stream cutoff, and snapshots expire after thirty seconds. This design supports intermittent covered windows. It cannot provide continuous current authority under those limits. Do not suppress reconciliation, shorten the acquisition delay, move a cutoff or extend freshness to manufacture a usable window.

The witness is preparation for a separately reviewed qualified paper runner. It does not consume an owner permit, commit an intent or bypass the existing strategy denial. Reader activation still requires orders, shadow, exits and models off. Browser acceptance, future fee associations, event coverage, liquidity, signals, risk and protective-exit requirements remain independent blockers. Fixes need disposable validation, review and a separate activation decision before a new real observation. Never apply them to an observation already in progress.

Use `npm run test:backend` for the Python suite. It applies the documented process-local workaround for this machine's native readline import crash. No system Python setting changes.


### Recover a damaged snapshot counter

A malformed snapshot counter blocks the final reconciliation transaction, including custody, risk and equity updates. Reconciliation reports failure and keeps its existing backoff. Observer refresh retains an incomplete attempt and keeps its normal delay. The connected validation CLI exits through its sanitized error path. Current reads treat missing, malformed or unbound versions as unavailable authority.

Never reset, delete or coerce a damaged counter automatically. Recovery requires separate owner approval; this procedure does not authorize a ledger change or restart. Preserve the original failed observation and its acceptance result.

1. Keep the reader, orders, automatic entries, local exits, shadow and models disabled. Use the approved stop procedure.
2. Preserve a consistent ledger backup, the offending value and every acquisition, projection, conflict and execution row.
3. Inspect an authorized offline copy. Find every retained valid acquisition or projection epoch, stored counter and embedded snapshot epoch. If any recovery evidence is unreadable, stop.
4. Document a recovery high-water mark strictly above every retained valid epoch. Obtain approval for the exact repair package.
5. Apply an approved repair only to the damaged counter. Preserve the stored snapshot and all historical evidence. The counter alone grants no authority.
6. The next ordinary fresh snapshot commit receives the high-water mark plus one. A new qualifying acquisition and every existing veto must pass before current accounting becomes available.

Do not delete the counter to initialize epoch one or recommit an old snapshot. A missing counter beside any retained versioned snapshot, acquisition or projection also blocks. Initialization scans retained version metadata only when the counter is genuinely absent; unreadable history cannot justify epoch one. A counter below the retained snapshot version also blocks. Rollback readers remain compatible with the added metadata; rolling forward rejects an older writer's snapshot without an embedded epoch. Epoch metadata stays outside economic input hashes and custody signatures.

Snapshot and witness version binding change no observation cadence, deadline, freshness, request budget, acceptance threshold or execution permission. S6 removes per-line whole-suffix copying while preserving byte/frame/event limits, deadlines and error semantics; it provides no hard wall-time guarantee. Local fixtures do not prove provider behavior, state latency or another elapsed observation.

## Inspect bounded timing diagnostics

The observer records each admitted cycle before preflight or lock waiting. Its sequence and attempt ID identify any later batch. Diagnostic events use the existing `events` table; accounting batches keep only their original start and immutable outcome phases.

Use `activity_attempt_started` and `activity_attempt_finished` to distinguish pre-batch failure, lock waiting, retained outcomes, counted acquisitions, publication and immediate sampling. The finished envelope records paired boundary clocks, fixed loop-lag summaries and at most seven request spans. Publication and retention-end measurements never alter an outcome.

Observation start, completion, sleep and end samples include wall UTC and monotonic offsets with run/process identity. Compare offsets only within that run. Sleep records distinguish intended delay, diagnostic-write overhead, actual waiting and interruption. The final tail remains visible even when no later acquisition completes. Wall rollback preserves event sequence order. Missing clock boundaries remain unknown.

HTTP tracing records only events exposed by the installed transport. Fixed phase summaries cover connection, TLS, request send, response headers/body and response close. Missing events have unknown duration; they do not prove DNS, pool waiting or connection reuse. Time before the first trace event remains unattributed. Trace callbacks perform no storage work and discard callback payloads. Request classifications retain fixed path templates, observed status and safe failure labels without identifiers, headers, bodies or exception messages. Additional provider-status and local-denial receipts use `api_request_diagnostic`, outside the existing request/error population.

On a diagnostic, batch-start, retention, publication or observer-state storage failure, the reader stops in memory. Broker request-receipt writes during acquisition follow the same rule. The observer skips every later write, including outcome retention after an earlier diagnostic write fails. A committed start without an outcome stays pending. Already committed evidence survives; missing evidence cannot establish successful observation. There is no write retry or salvage loop.

S1 snapshot-transaction failures retain their existing exception: roll back snapshot/counter together, retain an incomplete attempt when storage permits, publish blocked evidence and wait the normal delay. Evidence-integrity rejection remains distinct from storage failure. Cancellation still propagates if cleanup storage also fails.

On restart, recovery appends `activity_attempt_abandoned` for a valid unfinished cycle, without replacing its outcome or changing accounting selection. Repeated recovery adds no duplicate annotation. Malformed diagnostic identity blocks recovery without repair. A crash after publication can leave a valid projection and missing operational completion evidence; abandonment cannot fill that gap. A new run never includes prior downtime.

These diagnostics introduce no gap tolerance, clock veto or revised acceptance rule. Preserve the full observation window, existing counter update points, histogram populations, freshness, request budgets and storage/free-space limits above. All diagnostic storage counts toward growth. Fixture and process-crash tests do not establish provider behavior, runtime latency or operational acceptance.

## Offline gap report (S5)

`backend.activity_gap_report` evaluates recorded diagnostics for one observation run. It does not assess operational acceptance. The report uses only an explicitly supplied, separately authorized ledger copy; synthetic fixtures do not approve a future observation or explain the original failed observation.

Run the report from the repository root:

```sh
python -m backend.activity_gap_report \
  --ledger copy.sqlite --copy-manifest copy.json \
  --run-id 00000000000000000000000000000000 \
  --policy fixture-policy.json --format json
```

Use the actual recorded run ID. Text is the default format; JSON has `schema_version: 1`. Save stdout outside the evidence directory. Errors use fixed messages on stderr. The report buffers its output until SQLite closes and the copy's identity, size, modification time, digest and sidecar checks pass. An unexpected internal failure emits no report or traceback.

The input must already be a completed, closed, standalone SQLite backup in rollback-journal format. Its header read/write version bytes must both be 1, and no `-wal`, `-shm` or `-journal` sidecar may exist. A main-file copy from a WAL database does not establish that committed WAL records were included. The report rejects WAL headers before opening SQLite, uses one `mode=ro` connection and read transaction with `query_only` enabled, and never captures, converts, checkpoints or repairs evidence. Runtime locations, symlink files and hard-linked ledgers are rejected.

The copy manifest contains these fields:

| Field | Required value |
| --- | --- |
| `schema_version` | Integer 1 |
| `method`, `complete` | `sqlite-backup`, boolean true |
| `sha256`, `size_bytes` | Exact sealed destination SHA-256 and positive integer size |
| `capture_id`, `synthetic` | Nonempty capture identity and explicit boolean |
| `producer_sha256` | Captured source hashes for the five files below |
| `capture_provenance_ref`, `authorization_ref` | Nonempty references required for a non-synthetic copy |

The supported producer contract pins `backend/activity_observation.py`, `backend/activity_diagnostics.py`, `backend/activity_feed.py`, `backend/store.py` and `backend/broker.py`. The report embeds reviewed `s5` and `s6` five-file producer tuples and displays the matched tuple's hashes alongside the declared values, or the current `s6` hashes when no tuple matches. All required hashes must match one complete reviewed tuple; missing, malformed or unmatched required hashes produce an unknown `unsupported-producer` report without interpreting records. Record the producer's actual capture provenance; copying supported values into a manifest does not establish that provenance. Drift tests bind the current tuple to source and preserve the frozen legacy `s5` tuple. Future producer changes require review of the report contract and compatibility evidence. Implementation hashes are recorded separately.

Report `schema_version` remains 1. The additive `provenance.matched_producer_contract` is `s5` or `s6` for a match, and null when unsupported. `producer_contract_supported` is true only for a whole-tuple match. `supported_producer_sha256` contains that matched tuple, or the current `s6` expected tuple for unsupported inputs. Text displays the same identifier and expected hashes. S5 captures retain their original declared hashes and manifests; new reports record their own implementation hashes. The legacy contract covers isolated synthetic evidence, not an operational S5 observation. Parser compatibility requires unchanged events, normalized frame bytes, errors and limits, including retained evidence read in both version directions. New captures record the actual producing source. Selection-only test fixtures stamped with a legacy tuple do not establish S5 provenance.

The optional policy has this shape; the numbers below are synthetic test values only:

```json
{
  "schema_version": 1,
  "synthetic": true,
  "tau_seconds": 0.1,
  "tau_c_seconds": 0.1,
  "allow_indeterminate_e4": true,
  "provenance_ref": "synthetic-test-only"
}
```

Missing or null policy fields remain unset. Tolerances must be finite, nonnegative decimal numbers; booleans are not numbers. Arithmetic uses a local 64-digit decimal context with precision-loss traps and integer wall-clock microseconds, without an epsilon. Over-precision record values remain unknown; invalid policy representation is an input error.

Policy verdicts are available only when both the copy and policy are synthetic. A non-synthetic copy cannot reach exit 0 through a manifest declaration or an approval timestamp. Operational tolerances, E4 policy, any additional overhead treatment and prospective approval verification still require separate owner decisions and review.

The report preserves recorded run/process identity, event sequence, original batch evidence and both observation edges. It requires cycle start/finish and necessary sleep/wake records. Abandoned annotations do not supply a missing finish. A retained complete receipt does not reconstruct a counted acquisition: raw `complete_acquisitions / cycles` retains its actual update points, and zero cycles fails. Publication failures do not subtract an acquisition already counted. Matched publications, actual GET latency, acquisition/publication histograms and the two availability populations remain separate.

An interval exceeding 120 seconds in either clock is a candidate. An interval exceeding supplied τc in absolute wall-minus-monotonic divergence is also a candidate. Equality does not exceed a threshold. E2 partitions measured spans without adding nested request, retention or phase durations twice. Only the recorded sleep diagnostic-write span receives overhead credit; unmarked persistence, coverage and control work remains itemized residual. Synthetic τ applies to absolute monotonic residual per interval. Wall residual and component discrepancies are reported separately, so a wall step cannot become extra scheduler, execution or network delay. Opposing steps remain visible even when the interval's net divergence cancels.

E3 identifies supported observed locations separately from E4 root cause. Missing trace phases and pre-trace time remain unknown; they do not establish DNS or pool wait. Loop-lag maximums describe their containing cycle or sleep; the retained scheduled/observed pair describes only the latest probe and may not identify the maximum. Neither is added to interval totals. Provider status and transport errors alone do not prove the entire gap's root cause. An indeterminate root is accepted or rejected only by the explicit eligible synthetic E4 policy, after E1–E3.

Rule states are `satisfied`, `not-satisfied`, `unknown` and `not-evaluated`. The last means demonstrably inapplicable, never missing prerequisites. Malformed, duplicate, conflicting, unsupported or incomplete records remain unknown with row references; they do not suppress independently known counter failures. JSON retains exact decimal seconds as strings and contains evidence/policy/implementation hashes, interval contributions, residuals, discrepancies, classifications and limitations. Private payloads, account details, absolute input paths and exception text are excluded.

| Exit | Meaning |
| --- | --- |
| 0 | All applicable diagnostic requirements satisfied under an eligible synthetic policy |
| 1 | Report emitted with a known failed requirement, even if another result is unknown |
| 2 | Invalid arguments, policy, copy provenance, container, schema, integrity or protected read; no report |
| 3 | Report emitted with required evidence or policy unknown and no known failure |
| 4 | Unexpected internal failure; fixed error, no report |

Report-emitting precedence is 1, then 3, then 0. Every report carries `operational_acceptance: not-assessed`. No exit code unlocks an action, changes a runtime veto or establishes multi-day paper-trading readiness.

## Rehearse compatibility on disposable ledgers

Complete these steps before requesting delivery or an operational observation. Use the reviewed compatible predecessor and accumulated successor identities pinned in the rehearsal package. Keep separate checkouts, dependencies, databases and process receipts; use synthetic inputs and recording GET-only transports.

1. Have the actual predecessor create a clean terminal-history ledger. Seal a consistent SQLite backup after stopping its writer. Verify the backup opens independently without WAL, SHM or journal sidecars.
2. Open a working copy with the successor. Check additive schema compatibility and preservation of old rows. Obtain a fresh mock snapshot, acquire nonhistorical activity and publish. Require current accounting only when every existing gate passes.
3. Repeat deliveries under new batches, stop the owned process and reopen in another process. Require once-only economic effects, retained outcomes and unchanged execution records.
4. Stop the successor and seal its output. Open another working copy with the pinned predecessor, with reader, orders, shadow, exits, research, news and models disabled. Read history and explicitly reconcile through a recording GET-only mock. Start no background workers.
5. Seal that predecessor output and open it with the successor before startup, reconciliation or application lifespan execution. Its predecessor-written snapshot has no embedded epoch. Require unavailable current accounting and rejection of the old witness, even with equal balances and timestamps or backward wall time.
6. Obtain a genuinely fresh mock snapshot. Its new epoch still cannot authorize an earlier acquisition. Require a new qualifying acquisition before the clean lineage recovers.

Repeat rollback and roll-forward with a separately sealed conflict lineage. It must remain blocked. Preserve separately identified legacy-overlap, corrupt-evidence and malformed-counter variants. Never clear a conflict or remove overlapping evidence to recover the positive case. Synthetic counter recovery tests authorize no repair of a real ledger.

For reader-disabled rollback, preserve all preexisting activity tables and schemas, evidence blobs, diagnostics, epochs, conflicts, projections, acquisition receipts, the covered-checkpoint pointer and frozen manifests. Preserve every existing event and terminal execution record. Check logical SQL values rather than SQLite file equality: checkpointing can change the container without changing a row.

Record expected reconciliation changes separately:

| Record | Permitted procedural delta |
| --- | --- |
| Current snapshot | The predecessor replaces it without an embedded epoch; the surviving epoch counter remains unchanged |
| Equity and risk | Equity may append; day/high-water marks may update; an absent baseline may initialize; a safety latch may be added, never cleared |
| Custody | A changed signature may append a checkpoint and update its pointer |
| Request and service evidence | GET receipts and service events may append; the last-call value may update |

Inventory every other change and stop on an unclassified delta. An external order inserted or updated during readback fails execution preservation. Startup tests that intentionally change submitting orders to unknown have separate expected-delta receipts; they cannot satisfy unchanged terminal-ledger acceptance.

Reuse the existing crash, cancellation, storage and integrity tests. New permanent tests use repository inputs only. Actual predecessor behavior belongs to the separate runner, which fails a named prerequisite check when a checkout, interpreter or source inventory is missing or wrong. Ordinary backend and full CI must pass without that runner or a predecessor checkout.

## Freeze the execution comparison before a run

Hash every row, including unsettled rows, using these ordered columns and keys:

| Component | Columns | Order |
| --- | --- | --- |
| Orders | `client_id, request, raw, status, external, deadline, created_at, updated_at` | Binary `client_id` |
| Fills | `id, client_id, at, payload` | Binary `id` |
| Activities | `id, type, at, payload` | Binary `id` |
| Observations | `id, at, request, outcome, context` | Numeric `id` |

Include exact presence and stored values for `mode`, `account_binding`, `halted`, `exit_plans`, `execution_pilot`, `fee_reconciliation_required` and `frozen_experiment`, ordered by state key. Include `events(seq,at,type,payload)` ordered by sequence for `intent_committed`, `submission_rejected`, `submission_uncertain`, `cancel_requested`, `fill`, `order_state`, `exit_armed`, `entry_halt`, `risk_plan` and `risk_veto`.

With research disabled, also hash every shadow, timing and research row in schema-column order and numeric ID order. With news disabled, hash every news row in schema-column order and binary `(id,revision)` order. Freeze this selection prospectively. Research-enabled operation requires an already-present readable experiment registration matching its frozen manifest. An absent registration blocks that option until separately authorized pre-baseline registration and a new baseline. Never rebaseline or change an existing registration to obtain acceptance.

Use raw SQL values without decoding evidence or reformatting payload JSON. Serialize the component name, ordered columns and ordered rows as compact UTF-8 JSON. Tag null, integer decimal strings, real binary64 hexadecimal bytes, text UTF-8 bytes and blob bytes distinctly. Represent missing state keys explicitly. Record each component's SHA-256 and row count, then hash the sorted component manifest. Preserve frozen manifest file digests too.

Hash inequality fails the execution invariant even with zero broker mutations. Expected accounting, custody, request and approved worker changes remain individually inventoried. No post-run exclusion can turn a changed execution record into a pass.

## Record the remaining owner decisions

Before a separately authorized operational run, freeze these decisions and their evidence:

| Decision | Evidence or unresolved choice |
| --- | --- |
| Revision and binding | Delivered inventory, protected hashes, completed review, post-review CI, rehearsal receipts, account/ledger identity and mapping-file digest |
| Private validation | Separately authorized ledger-copy access, original historical replay and fresh GET-only broker comparison |
| Controls and process | Disabled execution controls, executable/invocation, PID and start identity, account/database ownership and one writer |
| Backup and recovery | Consistent backup including committed WAL data, independent restore check, execution hashes, graceful stop, restart and rollback procedure |
| Polling | Fixed state/observation polling cadences and retained actual request samples |
| Research/news | Disabled, or named existing workers and cadence; models remain off; research requires the preexisting frozen registration |
| Compute overlap | Approved concurrent builds/tests/reviews or a quiet-host policy, with deviations recorded |
| Residual tolerance τ | Unset operational nonnegative finite tolerance, precision, rationale and overhead treatment |
| Clock tolerance τc | Unset absolute wall-minus-monotonic divergence tolerance and prospective checks across attempts, sleeps and both observation edges |
| E4 and approval | Unset treatment of indeterminate roots and a source/run/account/mapping-bound approval identity proving approval preceded start |

The existing offline report cannot verify prospective operational approval. Choose manual operational evaluation or separately plan and review a verifier. O2 total GET-readback deadlines, O4 additional runtime clock vetoes and O6 usability targets remain separate decisions. No timeout may silently cover an uncertain broker mutation or its post-mutation reconciliation.

Freeze `complete_acquisitions / cycles` at the implemented update points. Admission creates a cycle before preflight or lock waiting. Admitted failures and cancellations remain cycles. A stop before admission creates none. Count a complete acquisition only after retention and post-retention guards, before publication. Publication failure does not subtract it; a complete receipt retained after stop is not counted. Zero cycles cannot pass.

Retain start-to-first, completion-to-completion and last-to-end intervals in both clocks. An interval over 120 seconds in either clock, or divergence over approved τc, requires the prospectively approved evidence checks. Preserve sequence through backward or opposing clock steps. Monotonic offsets cannot be compared across processes. Explain unmatched publications and blocked samples without changing denominators.

Require actual 86,400 monotonic seconds and report wall elapsed too. Preserve at least 99% complete acquisitions, DB plus WAL growth strictly below 256 MiB, at least 5 GiB free, publication histogram p95 upper bound at most 250 ms, actual eligible GET state histogram p95 upper bound at most 2,000 ms, zero broker mutations and unchanged execution hashes. Missing evidence, shortened windows, restarts and merged metric populations cannot manufacture a pass.

Maximum-budget and retained-history measurements are diagnostics. Record individual samples, source/dependency/runner/input identities, CPU, memory, physical DB/WAL/free space and shared-host overlap. Keep parser, retention, publication, accounting, witness, state and actual HTTP populations separate. Fixture watchdogs are external resource limits, never application deadlines; censored samples are not completed durations. Short storage samples cannot establish 24-hour growth acceptance.

Accounting acceptance leaves execution unavailable. Cooldown wiring, uncertain cancellation, operator-control responsiveness, exit-failure isolation, residual positions and every eligibility/risk veto still require separately authorized planning, implementation and review before a supervised paper round trip or multi-day pilot.
