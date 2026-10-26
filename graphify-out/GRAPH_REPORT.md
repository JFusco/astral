# Graph Report - astral-trading  (2026-10-26)

## Corpus Check
- 192 files · ~67,504 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1271 nodes · 3789 edges · 55 communities (50 shown, 5 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 135 edges (avg confidence: 0.64)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `dd449dc5`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- timestamp
- AlpacaPaper
- run
- test_accounting_engine.py
- test_health_engine.py
- D
- contracts.ts
- test_learning_engine.py
- test_state_contract.py
- Engine
- scripts
- useDashboard
- connection.test.ts
- compilerOptions
- connection.ts
- support.cjs
- screen
- test_liquidity_experiment.py
- motion.tsx
- health-page.tsx
- liquidity_runner.py
- relay.ts
- replay_runner.py
- BrokerFailure
- test_experiment.py
- test_risk.py
- seed.ts
- datetime
- devDependencies
- test_execution_pilot.py
- utcnow
- overview-page.tsx
- test_review_repairs.py
- intelligence.py
- Settings
- decide
- read.ts
- validate_pr_body.cjs
- test_readiness_gates.py
- Connection
- overnight_watch.py
- Store
- test_stage2_validation.py
- app.spec.ts
- boundaries.test.ts
- check-skills.cjs
- provider.tsx
- commitlint.config.cjs
- intelligence-feed.tsx
- proxy.ts
- next.config.ts
- prepare-standalone.mjs

## God Nodes (most connected - your core abstractions)
1. `Store` - 90 edges
2. `Engine` - 80 edges
3. `utcnow()` - 78 edges
4. `run()` - 76 edges
5. `D()` - 66 edges
6. `Settings` - 56 edges
7. `useDashboard()` - 53 edges
8. `intent()` - 45 edges
9. `BrokerFailure` - 44 edges
10. `timestamp()` - 43 edges

## Surprising Connections (you probably didn't know these)
- `Providers` --uses--> `Settings`  [INFERRED]
  tests/test_health_engine.py → backend/config.py
- `FixedDateTime` --uses--> `Settings`  [INFERRED]
  tests/test_state_contract.py → backend/config.py
- `Stream` --uses--> `Settings`  [INFERRED]
  tests/test_state_contract.py → backend/config.py
- `Stream` --uses--> `RuleViolation`  [INFERRED]
  tests/test_state_contract.py → backend/engine.py
- `FixedDateTime` --uses--> `Engine`  [INFERRED]
  tests/test_state_contract.py → backend/engine.py

## Import Cycles
- None detected.

## Communities (55 total, 5 thin omitted)

### Community 0 - "timestamp"
Cohesion: 0.10
Nodes (30): Retain scoped official calendar catalogs; never certify missing categories., Maintenance needs two current publisher lists. NY Fed remains partial BLS., retain_additional_scopes(), retain_scopes(), catalog(), Cells, event(), maintenance() (+22 more)

### Community 2 - "run"
Cohesion: 0.11
Nodes (44): Failure scenarios and adversarial selection cases; all trades are synthetic., test_ambiguous_fee_is_not_assigned_to_a_strategy(), test_intraday_exit_cannot_liquidate_swing_inventory(), test_late_confirmed_asset_fee_is_idempotent_and_reconciles(), test_local_exit_survives_restart_and_unknown_response(), test_quantity_and_shared_risk_boundaries(), test_read_only_adapter_blocks_post_and_delete_before_transport(), test_readback_422_after_accepted_order_never_releases_reservation() (+36 more)

### Community 3 - "test_accounting_engine.py"
Cohesion: 0.11
Nodes (50): at(), canonical(), cost_report(), digest(), evaluate(), main(), number(), precise() (+42 more)

### Community 4 - "test_health_engine.py"
Cohesion: 0.08
Nodes (26): lifespan(), Standalone health service, separate process and ledger from telemetry/trading., state(), fresh(), HealthEngine, Independent assessments from telemetry observations; no trading authority., effective(), HealthMonitor (+18 more)

### Community 5 - "D"
Cohesion: 0.15
Nodes (37): D(), Assumptions, Portfolio, replay(), stress_suite(), synthetic_events(), at(), clock() (+29 more)

### Community 6 - "contracts.ts"
Cohesion: 0.11
Nodes (30): AccountingBoundaries(), AccountingCosts(), AccountingGross(), AccountingRecords(), AccountingSummary(), amounts(), LearningBoundaries(), LearningInventory() (+22 more)

### Community 7 - "test_learning_engine.py"
Cohesion: 0.13
Nodes (43): digest(), encode(), evaluate(), main(), markdown(), packet_checks(), protected(), protected_windows() (+35 more)

### Community 8 - "test_state_contract.py"
Cohesion: 0.18
Nodes (23): at(), build_state(), buy(), free_port(), normalize(), pin_clock(), parametrize, Dashboard read-path contract: fixed Store-seeded ledgers and a pinned clock.… (+15 more)

### Community 9 - "Engine"
Cohesion: 0.16
Nodes (4): age(), Engine, symbol_for(), book_for()

### Community 10 - "scripts"
Cohesion: 0.05
Nodes (37): @commitlint/cli, @commitlint/config-conventional, @commitlint/lint, @commitlint/load, husky, devDependencies, @commitlint/cli, @commitlint/config-conventional (+29 more)

### Community 11 - "useDashboard"
Cohesion: 0.21
Nodes (17): OverviewFooter(), useDashboard(), Detail, EvidenceDialog(), PacketDialog(), ResearchExperiments(), ResearchGates(), ResearchLab() (+9 more)

### Community 12 - "connection.test.ts"
Cohesion: 0.18
Nodes (7): Health, seed(), Source, dashboard(), health(), now, services()

### Community 13 - "compilerOptions"
Cohesion: 0.07
Nodes (29): compilerOptions, allowJs, checkJs, esModuleInterop, incremental, isolatedModules, jsx, lib (+21 more)

### Community 14 - "connection.ts"
Cohesion: 0.23
Nodes (10): api(), errorMessage(), empty, Snapshot, accountingSchema, dashboardSchema, Fill, fillSchema (+2 more)

### Community 15 - "support.cjs"
Cohesion: 0.12
Nodes (26): assert, cli, config, fs, path, {
  ROOT,
  run,
  must,
  write,
  repository,
  fixture,
}, test, assert (+18 more)

### Community 16 - "screen"
Cohesion: 0.15
Nodes (24): CodexReviewer, command(), material_hash(), Bounded Codex CLI reviewer. Broker credentials and tools are not inherited., screen(), validate_review(), discover_crypto(), Read-only venue discovery. A listing is never execution authorization. (+16 more)

### Community 17 - "test_liquidity_experiment.py"
Cohesion: 0.23
Nodes (15): evaluate(), floor(), Quote-only liquidity experiment. No orders, fills, positions, P&L or promotion., turnover(), walk(), Same-venue REST book/quote validation. Visible depth never guarantees a fill., _validate(), validate_book() (+7 more)

### Community 18 - "motion.tsx"
Cohesion: 0.14
Nodes (16): HealthSummary(), Heartbeat(), AnimationProvider(), initialMode(), initialSystem(), LoadingPanel(), Mode, readMode() (+8 more)

### Community 19 - "health-page.tsx"
Cohesion: 0.10
Nodes (25): metadata, HealthDetails(), HealthFooterStatus(), HealthMap(), HealthPage(), attention, inTopic(), reportedNodes() (+17 more)

### Community 20 - "liquidity_runner.py"
Cohesion: 0.22
Nodes (22): digest(), Policy, binding(), get(), get_inventory_status(), hashes(), load(), now() (+14 more)

### Community 21 - "relay.ts"
Cohesion: 0.13
Nodes (17): Context, dynamic, GET(), POST(), runtime, acceptsGzip(), compress, getPaths (+9 more)

### Community 22 - "replay_runner.py"
Cohesion: 0.18
Nodes (19): contract(), observe(), register(), source_hashes(), state(), build_report(), code_hashes(), connect_readonly() (+11 more)

### Community 23 - "BrokerFailure"
Cohesion: 0.28
Nodes (11): ExitPlan, Halt, Intent, ResearchBar, RiskCandidate, BrokerFailure, Exception, Exception (+3 more)

### Community 24 - "test_experiment.py"
Cohesion: 0.13
Nodes (17): Meetings, parse_fomc(), HTMLParser, Official FOMC meeting dates, scoped context only; no complete macro calendar., diagnose(), Retrospective price-only prefixes. Never pretend these were known earlier., context(), fomc_html() (+9 more)

### Community 25 - "test_risk.py"
Cohesion: 0.27
Nodes (11): inputs(), parametrize, test_account_restrictions_block(), test_bad_bars_abstain(), test_cost_hurdle_prevents_an_uneconomic_candidate(), test_exact_wilder_atr_and_repeatable_sizing(), test_intraday_budget_costs_minimum_and_cash(), test_missing_crypto_bar_rejected() (+3 more)

### Community 26 - "seed.ts"
Cohesion: 0.32
Nodes (6): RootLayout(), Seed, healthSchema, loadSeed(), seedScope(), upstreamFetch()

### Community 27 - "datetime"
Cohesion: 0.13
Nodes (20): Frozen research contract and append-only observations. No execution interface., attribute(), canonical_symbol(), Inventory attribution is evidence, not a substitute for broker availability., Isolated deterministic portfolio execution model. No broker or Store imports.…, Evidence-by-evidence readiness. No threshold changes or execution capability., Point-in-time evidence screening; language models cannot override vetoes., floor_step() (+12 more)

### Community 28 - "devDependencies"
Cohesion: 0.04
Nodes (48): eslint, eslint-config-next, @fontsource-variable/dm-sans, @fontsource-variable/space-grotesk, dependencies, @fontsource-variable/dm-sans, @fontsource-variable/space-grotesk, motion (+40 more)

### Community 29 - "test_execution_pilot.py"
Cohesion: 0.21
Nodes (10): ExecutionPilot, One explicitly authorized execution experiment; never an alpha strategy. Uses…, pilot(), parametrize, test_crash_after_entry_resumes_exit_without_new_entry(), test_final_pilot_boundary_blocks_wrong_or_oversize_requests(), test_pilot_and_strategy_workers_cannot_share_authority(), test_pilot_recovers_lost_accepted_entry_without_duplicate() (+2 more)

### Community 30 - "utcnow"
Cohesion: 0.16
Nodes (7): No remote API. Fills are synthetic and do not model queueing/market impact., Simulator, record_fee(), dumps(), utcnow(), test_fee_revisions_retained_without_overwriting_confirmed_debit(), test_adapter_hashes_are_cached_local_and_covered_by_packet_hash()

### Community 31 - "overview-page.tsx"
Cohesion: 0.13
Nodes (22): HealthChanges(), OrderDialog(), AssetBar(), EquityChart(), ExecutionStream(), ModeBadge(), OverviewPage(), views (+14 more)

### Community 32 - "test_review_repairs.py"
Cohesion: 0.19
Nodes (17): read_context(), daily_history(), fee(), parametrize, Locked review regressions. Synthetic brokers, patched models and tmp ledgers…, test_all_vetoed_cycle_never_calls_model(), test_diagnostic_failure_still_journals_prospective_veto(), test_distinct_lab_still_copies_or_reuses() (+9 more)

### Community 33 - "intelligence.py"
Cohesion: 0.10
Nodes (27): ASTRAL paper-only service., collect(), health_inputs(), intelligence(), lifespan(), Local-only companion: independent DB and lifecycle preserve the shadow pilot., clean(), Collector (+19 more)

### Community 34 - "Settings"
Cohesion: 0.23
Nodes (10): create_app(), Settings, test_api_shadow_does_not_enable_orders_and_rejects_bypass_fields(), test_local_health_inputs_are_small_read_only_and_do_not_export_account_data(), test_replay_report_is_visible_only_in_the_book_that_records_its_receipt(), fixture, research_engine(), test_api_boundary_validation_and_persistence() (+2 more)

### Community 35 - "decide"
Cohesion: 0.38
Nodes (11): decide(), One-unit synthetic quote replay, with fills strictly AFTER decisions. Quote-…, replay(), event(), parametrize, test_entry_cancels_if_research_expires_during_latency(), test_entry_timing_fail_closed(), test_exit_rules_work_without_entry_permission() (+3 more)

### Community 36 - "read.ts"
Cohesion: 0.12
Nodes (15): dynamic, metadata, Page(), dynamic, metadata, Page(), AccountingContent(), LearningContent() (+7 more)

### Community 37 - "validate_pr_body.cjs"
Cohesion: 0.23
Nodes (11): fs, main(), readableText(), REQUIRED_CHECKS, REQUIRED_SECTIONS, sections(), validatePullRequestBody(), withoutComments() (+3 more)

### Community 38 - "test_readiness_gates.py"
Cohesion: 0.11
Nodes (24): parse_bea(), HTMLParser, Scoped BEA schedule; a date is retained without inventing an unspecified…, Schedule, Validate provider fee records without estimating missing fees or rewriting…, validate_activity(), calendar_coverage(), All scoped categories need retained, current, forward-covering evidence.… (+16 more)

### Community 40 - "overnight_watch.py"
Cohesion: 0.25
Nodes (9): audit(), now(), Bounded overnight observation of the existing GET-only localhost paper lab., safety(), watch(), write_summary(), parametrize, test_observer_counts_lost_write_and_http_failure() (+1 more)

### Community 41 - "Store"
Cohesion: 0.11
Nodes (20): Fixed-host Alpaca paper adapter and a separately labelled durable simulator., Store, aggregate_daily(), isolate_experiment_workers(), lab_path(), main(), Bounded, GET-only Alpaca dogfood session using a private copied ledger., main() (+12 more)

### Community 42 - "test_stage2_validation.py"
Cohesion: 0.27
Nodes (10): audit_crypto(), Read-only reconciliation analysis. Hypotheses cannot become ledger entries., Compare authoritative gross executions and positions; explain, never waive. Fee…, parametrize, Synthetic decision-path and fault tests; none are broker-paper executions., reconciliation_fixture(), test_confirmed_fee_matches_and_duplicate_activity_is_not_counted_twice(), test_duplicate_and_out_of_order_partial_readbacks_preserve_quantity() (+2 more)

### Community 43 - "app.spec.ts"
Cohesion: 0.18
Nodes (3): Dashboard, OrderIntent, diagnostics

### Community 47 - "boundaries.test.ts"
Cohesion: 0.32
Nodes (6): allowlist, files, isClient(), lines(), root, text()

### Community 49 - "check-skills.cjs"
Cohesion: 0.33
Nodes (6): checkSkills(), crypto, fs, hashSkillFolder(), path, ROOT

### Community 50 - "provider.tsx"
Cohesion: 0.11
Nodes (14): dynamic, metadata, StrategiesView(), StrategyCounts(), Context, Provider(), AppFrame(), Clock() (+6 more)

### Community 52 - "commitlint.config.cjs"
Cohesion: 0.83
Nodes (3): bodyMaxLineLength(), footerMaxLineLength(), maxLineLength()

### Community 53 - "intelligence-feed.tsx"
Cohesion: 0.23
Nodes (7): Dialog(), IntelligenceFeed(), SourceDialog(), ViewDialog(), IntelligenceView(), SourceLink(), News

## Knowledge Gaps
- **154 isolated node(s):** `items`, `name`, `private`, `version`, `type` (+149 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Store` connect `Store` to `timestamp`, `run`, `test_accounting_engine.py`, `test_health_engine.py`, `D`, `test_learning_engine.py`, `test_state_contract.py`, `screen`, `test_liquidity_experiment.py`, `replay_runner.py`, `BrokerFailure`, `test_experiment.py`, `test_risk.py`, `datetime`, `utcnow`, `test_review_repairs.py`, `intelligence.py`, `Settings`, `test_readiness_gates.py`?**
  _High betweenness centrality (0.058) - this node is a cross-community bridge._
- **Why does `Engine` connect `Engine` to `test_review_repairs.py`, `AlpacaPaper`, `Settings`, `run`, `D`, `test_state_contract.py`, `Store`, `test_stage2_validation.py`, `screen`, `replay_runner.py`, `BrokerFailure`, `test_experiment.py`, `test_risk.py`, `datetime`, `test_execution_pilot.py`, `utcnow`?**
  _High betweenness centrality (0.033) - this node is a cross-community bridge._
- **Why does `utcnow()` connect `utcnow` to `timestamp`, `AlpacaPaper`, `Settings`, `intelligence.py`, `test_health_engine.py`, `test_review_repairs.py`, `test_readiness_gates.py`, `run`, `Store`, `Engine`, `screen`, `replay_runner.py`, `BrokerFailure`, `datetime`, `test_execution_pilot.py`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `Store` (e.g. with `ExitPlan` and `Halt`) actually correct?**
  _`Store` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `Engine` (e.g. with `ExitPlan` and `Halt`) actually correct?**
  _`Engine` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 30 inferred relationships involving `D()` (e.g. with `diagnose()` and `validate_activity()`) actually correct?**
  _`D()` has 30 INFERRED edges - model-reasoned connections that need verification._
- **What connects `items`, `name`, `private` to the rest of the system?**
  _154 weakly-connected nodes found - possible documentation gaps or missing edges._