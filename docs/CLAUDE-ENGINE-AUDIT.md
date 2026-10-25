# ASTRAL engine audit handoff for Claude

Prepared October 25, 2026 from the implementation accompanying the Next.js
cutover. Pin `git rev-parse HEAD` and `git rev-parse origin/main` before starting
the audit; the delivery message identifies the integrated commit. This document
describes source and test evidence, not the current configuration of a running
broker session. Private runtime data and environment files were not inspected.

## Requested outcome

Audit how the engines work individually and together. Identify concrete
correctness defects, unnecessary work, unclear ownership, coupling, cleanup
opportunities and justified file splits. Produce an evidence-backed improvement
plan before changing engine code. Each engine should have a clear responsibility;
that does not require one deployment or class per engine.

Prioritize reliable behavior and maintainable boundaries. Preserve the paper-only
execution contract, decimal arithmetic, evidence provenance, durable order intent,
unknown results and protected experiments. Do not use a cleanup to enable trading,
training, promotion, a paid model worker or new provider requests.

## Current topology and ownership

| Process or module | Responsibility | Main sources |
| --- | --- | --- |
| Next.js, port 3000 | Four screens, interaction, loading/error states, same-origin API relay and persistent browser connection | `frontend/app/`, `frontend/components/`, `frontend/lib/` |
| Python application, port 8766 | Single execution owner, market/account readback, deterministic gates, research orchestration, ledger and SSE | `backend/app.py`, `backend/engine.py`, `backend/broker.py`, `backend/store.py` |
| Intelligence, port 8768 | Bounded collection of public evidence and source-health observations in its own ledger | `backend/intelligence_app.py`, `backend/intelligence.py` |
| Health, port 8769 | Independent assessment of availability/freshness and its own heartbeat/incident transitions | `backend/health_app.py`, `backend/health_engine.py`, `backend/service_health.py` |
| Accounting CLI | On-demand audit of retained money/custody records and supplied costs | `backend/accounting_engine.py`, `backend/accounting_view.py` |
| Learning CLI | On-demand offline evidence/outcome-readiness and model-contract audit | `backend/learning_engine.py`, `backend/learning_view.py` |
| Deterministic research/risk/timing modules | Evidence qualification, candidate calculations, vetoes and timing hypotheses | `backend/research.py`, `backend/risk.py`, `backend/timing.py` |
| Experiment/replay/liquidity modules | Registered research evidence, hypothetical execution modeling and independent quote/cost observations | `backend/experiment.py`, `backend/portfolio_replay.py`, `backend/replay_runner.py`, `backend/liquidity.py`, `backend/liquidity_runner.py` |
| Telemetry | Operational observations, durations, attempts, usage and lineage distributed across existing records | `Engine.worker`, `events`, research/worker receipts and source fetch records |

The browser calls only the Next.js origin. Node Route Handlers relay explicitly
allowed paths to fixed server-configured Python services. They preserve validated
Host/Origin, paper-intent headers, payloads, status codes, order IDs and SSE framing.
Private reads use no-store. The relay is transport, not financial authority.
Docker defines four services and publishes only the frontend on loopback. Runtime
Docker execution has not been verified because Docker is unavailable locally.

## Engines in detail

### Application orchestration and execution

`backend/app.py` owns the FastAPI lifecycle, request schemas, local trust boundary,
API routes and SSE transport. Its lifespan takes an exclusive lock for the ledger
and creates one Store and Engine. Multiple executor workers on the same ledger
are rejected. It exposes saved accounting/learning reports through read adapters;
those GET routes do not launch evaluators.

`backend/engine.py` currently coordinates several concerns in one 832-line class:
worker scheduling, quotes, account/order reconciliation, fee/news ingestion,
execution gating, order submission/cancel, research, timing, exit monitoring,
experiment/replay/liquidity receipts and dashboard state assembly. This is a useful
audit target, not proof that every method needs a new abstraction.

`Engine.place()` serializes execution, checks existing client IDs, evaluates risk
and durably records the intent before the broker call. Reusing an ID for a
different intent is rejected. Unknown submission outcomes remain blocked and are
queried/reconciled, never automatically submitted again. Startup converts
interrupted `submitting` rows to `unknown`. Cancellation retains uncertainty and
reservations until readback. Locally armed exits reuse this execution path;
they are not broker-native stop protection and depend on the process remaining
available. Automated Alpaca swing/intraday placement is explicitly blocked in
the current execution path.

`backend/broker.py` supplies the fixed-host Alpaca paper adapter and persistent
Simulator. The simulator uses a separate execution mode/ledger, synthetic quotes
and a simplified fill/fee model. It is useful for integration behavior, not real
liquidity or execution-quality evidence. Browser-only synthetic demo code has
been removed; the Python simulator remains.

### Deterministic risk and inventory

`backend/risk.py` computes research-only ATR/trend/breakout candidates and decimal
position-sizing scenarios. It validates raw bar identity, chronology, known-at
times, freshness and instrument constraints. Stop/target values are planning
references and confer no execution authority or loss guarantee.

The final execution checks are currently in `Engine.risk_payload()` and related
methods, not entirely inside risk.py. Review how fresh account/quote state,
halt/loss latches, uncertain orders, cash, exposure, reservations and supported
instrument rules combine. Preserve a single authoritative decision before a
broker write. `backend/inventory.py` attributes holdings to manual, swing,
intraday, external or unknown books; one strategy must not sell another book's
inventory. `backend/reconciliation.py` and `backend/fee_evidence.py` support
retained quantity/fee evidence. Operational account reconciliation and the offline
accounting audit are distinct responsibilities.

### Research, model review and timing

`backend/research.py` builds source-backed screening packets and validates model
responses. `Engine.research_cycle()` obtains history, refreshes account/quotes
after potentially slow downloads, assembles public context, runs deterministic
screens and shadow vetoes, optionally invokes the bounded model reviewer, and
records packets/results/usage. Research has its own lock and pending flag.

`backend/codex_worker.py` is an evidence-only reviewer, currently pinned in source
to gpt-6.1-sol/high. It receives eligible packets, validates citations/numerical
claims, caches by material hash and limits actual launches to four per UTC day,
45 KB input and 180 seconds. Failed/time-out launches consume attempts. Results
always declare execution disabled; the model cannot override deterministic vetoes.
Usage is not an invoice, and actual USD attribution can be unknown. Source flags
default the model off; no running environment was inspected for this handoff.

`backend/timing.py` produces wait/hold/buy-candidate/sell-candidate hypotheses
using position state, closed bars, subsequent fresh quotes, research validity,
session/halt/cooldown and exit references. Timing decisions explicitly do not
assume fills or place orders. Audit the interfaces between screening, risk,
timing, execution and exits without moving broker authority into research.

### Public intelligence and event qualification

The separate Collector owns public-source fetching, parsing, revisions and
source-health observations. It uses fixed endpoints, bounded concurrency,
timeouts/size caps, conditional requests and backoff. It retains revisions,
first-seen times, content hashes and current pointers in its own SQLite ledger.
Its API is GET-only and it does not load broker credentials or run models.

`backend/event_sources.py`, `backend/bea_calendar.py`,
`backend/calendar_context.py`, `backend/calendar_evidence.py` and
`backend/public_context.py` normalize and select scoped evidence. Public context
can add a conservative veto; a partial source cannot certify complete coverage or
clear unrelated risk gates. Publication, source update, arrival and known-at
times have different meanings. Historical source-access denials remain denials.
The trading service retains its own bounded context observations for research;
it does not take ownership of the collector database.

### Health and telemetry

The HealthEngine reads allowlisted `/api/health-inputs` observations from the
application and collector, evaluates availability/freshness and writes transitions
to its separate health ledger. Local cycles run after the previous bounded cycle;
public provider-status requests run independently so they cannot stall local
assessment. Health owns an independent heartbeat. It does not place orders,
restart workers, clear gates, train, promote or call a paid model as a canary.

Telemetry records what happened: worker status/timestamps/durations, errors,
source requests, model attempts/tokens and provenance. Health judges those
observations. Accounting assigns money only with explicit evidence. Learning
evaluates retained records offline. Telemetry is not yet a complete standalone
subsystem; do not describe it as an already isolated service.

### Accounting

`accounting_engine.py` opens the source SQLite database read-only in a consistent
transaction at an explicit cutoff. It writes a separate private evaluation
directory containing a contract, source hashes, report and exports. It performs
book-isolated FIFO gross lot matching, custody comparisons and explicit fee/cost
checks. Missing/disputed data stays visible. Estimates, confirmed charges,
subscriptions and included allocations are distinct; currencies are not silently
converted or costs counted twice.

The first proof does not establish complete basis, transfers/cash flows, net
realized/unrealized profit or tax-ready results. It exports no financial learning
labels. `accounting_view.py` validates and summarizes the latest saved report
bound to the application ledger/mode. Refreshing Accounting only rereads it.

### Learning

`learning_engine.py` is an offline audit, not a training loop. It registers source
identity, hashes, cutoff and limitations, then inventories usable/excluded data,
checks existing model research contracts and reports outcome/usefulness readiness.
It distinguishes skipped, disabled, failed, cached and completed model receipts.
It does not launch a model to evaluate another model.

Protected forward windows are hash-checked and excluded; window completion does
not release them. Approvals/fills/price markouts do not become profitability
labels. Reconciled accounting-backed outcome labels and matched no-model cohorts
are not implemented. No policy training, automatic promotion or risk-limit changes
occur. `learning_view.py` serves a sanitized verified saved report; the UI refresh
does not evaluate, train or promote.

### Experiments, replay and liquidity

`experiment.py` and retained manifests define frozen research contracts.
`portfolio_replay.py` models hypothetical portfolio/execution behavior;
`replay_runner.py` supplies retained-event export, synthetic stress scenarios and
registered-window reports. Hypothetical fills are never paper-broker fills.
`liquidity_runner.py` reads observations through a read-only source connection and
writes separate quote/cost experiment outputs; it cannot create orders or fills.
`market_depth.py`, `trade_history.py`, `liquidity.py` and `readiness.py` support
quote-size/depth semantics, cost assumptions and explicit readiness gates. Audit
these contracts separately from strategy performance and financial reconciliation.

## How information flows

1. Broker/collector observations retain their own timestamps and evidence identity.
2. The application reconciles account/orders, retains fills and attributes inventory.
3. Deterministic research/risk/timing reads qualified evidence and records decisions;
   optional model review can explain eligible evidence but cannot authorize execution.
4. Only the single execution path can commit an intent and call the broker adapter.
   Readback produces ledger events; browser SSE presents those observations.
5. Telemetry supplies health observations; Health assesses them independently.
6. Accounting and Learning consume retained evidence at explicit cutoffs, writing
   separate artifacts. Their pages read saved reports. No accounting-to-learning
   net-outcome adapter exists yet.

## Audit questions and requested evidence

- Map every write owner, lock, transaction, task and side effect before proposing
  splits. Which engine methods are orchestration versus domain decisions? Which
  extractions reduce real coupling while retaining one execution owner?
- Measure event-loop delay and time spent in `Engine.state()`, inventory/readiness
  assembly, synchronous SQLite calls, JSON serialization and per-client SSE work.
  Check repeated ledger scans and report-file discovery before adding caching.
  Any cache needs explicit invalidation and private-data/freshness boundaries.
- Trace cancellation/shutdown, overlapping worker cycles, request timeouts and
  error backoff. Check HTTP-client ownership, abandoned tasks, executor locks and
  SQLite transaction duration. Do not infer a leak from file size or complexity.
- Review direct SQL outside Store transactions/locks, common Store schema reuse by
  companion services, database-mode isolation and report identity checks. Propose
  narrower repositories only where a concrete ownership or consistency issue exists.
- Check repeated public-context collection/history downloads and whether validated
  reuse can save requests without changing known-at evidence or frozen inputs.
- Compare pure risk calculations with runtime execution enforcement for drift.
  Verify invariant tests around books, reservations, halt versus protective exits,
  idempotent intent identity, uncertain submissions and partial fills.
- Check state/DTO contracts and duplicated report-reader utilities. Large files
  worth examining include engine.py, frontend/components/overview.tsx and
  reports.tsx. Split by cohesive responsibility, not arbitrary line limits.
- Audit unknown-versus-zero semantics in every layer, especially cost/telemetry
  summaries. Distinguish application display metrics from complete accounting.
- Reconcile documentation with source: ENGINE-BOUNDARIES.md is an agreed contract
  whose implementation column predates the completed accounting proof. Preserve
  historical decisions and update living implementation descriptions separately.
- Motion uses LazyMotion and shared loading/dialog preferences. A live application
  setting is tested; OS preference toggling remains a separate version-specific
  check because installed hook source differs from the current official promise.
  See NEXTJS-CUTOVER.md and the pending Brain capture; reproduce before changing it.

For each finding provide severity, exact source location, concrete trigger and
effect, reproduction or measurement, smallest correction, proposed file ownership,
acceptance test and residual risk. Separate confirmed defects, measured performance
opportunities and optional structural suggestions. A proposed file tree must name
what moves, dependencies and public interfaces; avoid generic service layers or
new frameworks without evidence. Suggest small ordered changes with rollback points.

## Verified migration baseline and limits

Lint, TypeScript, 14 frontend unit tests, the Webpack standalone build and 355 Python
tests passed after source repairs. Eight real-Chrome cases then passed on production
frontend output and a disposable simulator: routing/resource cleanup, live Health
motion, loading/reduced motion/mobile, uncertain buy/reconcile and actual sell,
relay guards, SSE replay/cancel, saved-report navigation/read-only refresh and
malformed-state recovery. Each buy/sell was submitted once with a distinct retained
intent, and readback verified orders, a sell fill and lower holdings.

The migration review repaired six source defects and one browser assertion race;
final independent verification completed with no findings. Details, versions,
review lineage and evidence limitations are in NEXTJS-CUTOVER.md. This establishes
local integration behavior, not provider/broker acceptance, profitability or broad
engine-architecture correctness. Docker runtime was not tested. Existing services,
broker settings, private data and frozen experiments were not restarted or altered.

## Starting prompt

> Audit the ASTRAL implementation at the pinned main commit using this handoff and
> actual source. First verify current Git state, then map engine ownership and
> call/data/side-effect boundaries. Review correctness, efficiency, cleanup, file
> splitting and cooperation between engines. Preserve all trading, evidence and
> holdout invariants. Do not modify code, secrets, runtime data, broker flags,
> experiments or running processes; do not launch provider/model calls. Return
> prioritized evidence-backed findings and a surgical phased plan, with exact files,
> proposed responsibilities, acceptance checks and measured benefits where available.
> Distinguish built functionality from partial proofs and planned capabilities.
