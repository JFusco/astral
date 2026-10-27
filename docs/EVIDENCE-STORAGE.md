---
meta:
  contentType: Reference
---

# Read losslessly stored evidence

New bulky evidence uses a versioned binary representation to reduce ledger growth. Existing text rows remain unchanged. Collection cadence, source timestamps, content hashes, acquisition associations and execution vetoes remain independent of storage encoding.

## Decode mixed ledgers

`backend/evidence_codec.py` uses zlib compression only when it saves space. The binary header identifies the version and original byte length. Decoding rejects unsupported versions, invalid lengths, truncated streams, checksum failures, trailing bytes and expansion beyond the declared size or 32 MiB decoder limit. Legacy text remains readable without compression.

New quote events, raw order books, research packets, diagnostic contexts, activity outcomes and accounting projections can contain encoded payloads. Decision fields used by SQLite JSON queries remain text. `Store.rows()` restores payload, packet, context and frame values before returning them. Direct SQLite readers must use `unpack_text()` or `unpack_row()` instead of passing encoded values directly to a JSON parser.

## Retain every activity delivery

Repeated activity payloads and frames share immutable content in the additive `evidence_blobs` table. Each acquisition still retains its own batch, ordered delivery rows, provider identities, timestamps, hashes, outcome and complete raw stream. References bind the exact original bytes by SHA-256; a missing or changed body fails decoding. Deduplication never discards an acquisition or treats a missing fee as zero.

`unpack_row(row, db)` resolves these references within the caller's existing SQLite transaction. Keep the body table with the ledger when backing up or exporting data. A plain SQLite inspection exposes encoded values; use the codec for an evidence export. Do not decode by guessing a format or accepting a partial stream.

Publication and cached reads validate the selected batch's decoded event and frame against each delivery's retained hash. Cached reads also check the number of distinct activities. Damaged markers, mismatched references and missing deliveries block accounting. If existing shared content is corrupt, retain the new rejected delivery inline with its outcome and full raw stream; leave the corrupt historical body unchanged.

## Preserve frozen contracts and rollback evidence

The owner approved storage-only changes to the replay and liquidity readers for issue #48. Their source hashes change, and their hash sets now include the codec. Existing frozen manifests remain unchanged and report code drift. This change neither rebaselines an experiment nor certifies its results.

Reader-disabled rollback uses the updated compatible application on the same ledger. Do not launch an older application that cannot decode new evidence. Preserve all encoded records, body references, conflicts and projections; never restore old balances or rewrite historical rows to roll back.

## Measure operational storage

Disposable mixed-ledger, corruption, restart and replay checks establish compatibility. Private workload measurements establish capacity estimates. Neither proves elapsed 24-hour acceptance. The [accounting observation](ACCOUNTING-ROLLOUT.md) retains its fixed 256 MiB database-plus-WAL growth limit, 5 GiB free-space requirement and latency criteria. Activation still requires a fresh broker comparison, consistent backup and the authorized startup package for the exact delivered revision.
