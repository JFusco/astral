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

Only after that decision, stop the approved executor gracefully and invoke the same command with `--activate`. It serves the existing application on `127.0.0.1:8766` with one worker and the existing database lock. Do not start a second writer or stop unrelated processes. No activation command runs as part of installation, import, delivery or testing.

The activation path rechecks ledger identity and unsettled orders under the application lock before opening Store. The mapping is validated once and pinned in memory. A new reviewed mapping requires another explicit rollout invocation; editing or deleting the original file does not change the pinned contract.

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

## Decide whether the observation passed

Require an actual 24-hour window, at least 99% complete acquisitions, no unexplained acquisition gap over 120 seconds, the storage/latency limits above and zero broker mutations. Preserve startup, completion, interruption and failure receipts. Every unmatched publication and sampled blocked state needs an explanation; a collection-success count cannot conceal unusable accounting.

Poll `/api/state` and the observation endpoint at the agreed cadence during the approved window to retain current gate status and latency samples. Missing latency samples, acquisition gaps or missing original evidence cannot pass. The observer deliberately reports `owner-review-required`; it does not certify its own operational acceptance. Simulated clocks and disposable provider tests do not establish elapsed real-world observation.

Compare covered current cash and asset quantities exactly, retaining the normal inventory/custody checks. Confirm that shared views apply asset fees once and disclose already-included USD fees without another cash debit. Unsupported symbols remain unverified. Save abstentions and blocked intervals as evidence.

If acquisition coordination cannot produce usable covered publications, fail the rollout and resolve that behavior before another activation. Never move the cutoff, extend freshness or hide an attempted acquisition to manufacture availability. Accounting acceptance does not clear liquidity, events, entry timing, sizing, execution or exit-supervision gates.

## Roll back while retaining evidence

Use the approved procedure to stop the observer and return to ordinary reader-disabled startup, keeping orders disabled. Recheck controls and retained execution rows. Preserve raw streams, association versions, conflicts, acquisition outcomes, projections and observation receipts. Existing projection effects may still explain historical inventory; they cannot establish current readiness.

Use the updated [compatible evidence reader](EVIDENCE-STORAGE.md) for rollback. Older code cannot decode new binary payloads and immutable body references. Preserve the new tables and existing frozen manifests; the authorized replay/liquidity reader changes remain visible as code drift.

Never restore old balances, clear a conflict, reset a baseline or treat an empty legacy fee response as zero fees. Restart recovery starts a new observation window and requires fresh covered acquisition. It never repeats an order or silently counts downtime as observed operation.
