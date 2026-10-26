# Graph Report - astral-trading  (2026-10-26)

## Corpus Check
- 197 files · ~69,688 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1309 nodes · 3873 edges · 59 communities (50 shown, 9 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 135 edges (avg confidence: 0.64)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a0811cb2`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- datetime
- AlpacaPaper
- run
- test_accounting_engine.py
- HealthEngine
- D
- ui.ts
- test_learning_engine.py
- test_state_contract.py
- Engine
- scripts
- useDashboard
- connection.test.ts
- compilerOptions
- contracts.ts
- support.cjs
- screen
- test_quantconnect_validation.py
- motion.tsx
- health-page.tsx
- timestamp
- relay.ts
- overview-page.tsx
- intelligence.py
- test_experiment.py
- test_health_engine.py
- seed.ts
- read.ts
- devDependencies
- BrokerFailure
- utcnow
- order.tsx
- test_review_repairs.py
- Store
- Settings
- HealthMonitor
- accounting/page.tsx
- validate_pr_body.cjs
- test_readiness_gates.py
- Connection
- overnight_watch.py
- engine.py
- test_stage2_validation.py
- StatusHeading
- Meetings
- Source
- read.test.ts
- boundaries.test.ts
- quantconnect/__init__.py
- check-skills.cjs
- navigation.tsx
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
- `FixedDateTime` --uses--> `RuleViolation`  [INFERRED]
  tests/test_state_contract.py → backend/engine.py
- `Stream` --uses--> `RuleViolation`  [INFERRED]
  tests/test_state_contract.py → backend/engine.py

## Import Cycles
- None detected.

## Communities (59 total, 9 thin omitted)

### Community 0 - "datetime"
Cohesion: 0.08
Nodes (36): Retain scoped official calendar catalogs; never certify missing categories., Maintenance needs two current publisher lists. NY Fed remains partial BLS., retain_additional_scopes(), retain_scopes(), catalog(), Cells, event(), maintenance() (+28 more)

### Community 1 - "AlpacaPaper"
Cohesion: 0.12
Nodes (12): AlpacaPaper, Limiter, aggregate_daily(), Build daily candles exclusively from documented execution records., aggregate(), batch(), parametrize, test_bad_trade_records_fail_closed() (+4 more)

### Community 2 - "run"
Cohesion: 0.14
Nodes (36): Failure scenarios and adversarial selection cases; all trades are synthetic., test_ambiguous_fee_is_not_assigned_to_a_strategy(), test_intraday_exit_cannot_liquidate_swing_inventory(), test_late_confirmed_asset_fee_is_idempotent_and_reconciles(), test_local_exit_survives_restart_and_unknown_response(), test_quantity_and_shared_risk_boundaries(), test_readback_422_after_accepted_order_never_releases_reservation(), test_repeated_identical_exit_veto_is_journaled_once() (+28 more)

### Community 3 - "test_accounting_engine.py"
Cohesion: 0.11
Nodes (52): at(), canonical(), cost_report(), digest(), evaluate(), main(), number(), precise() (+44 more)

### Community 4 - "HealthEngine"
Cohesion: 0.19
Nodes (8): lifespan(), Standalone health service, separate process and ledger from telemetry/trading., state(), fresh(), HealthEngine, Independent assessments from telemetry observations; no trading authority., moment(), Public provider reports, separate from account/model connectivity and risk. No…

### Community 5 - "D"
Cohesion: 0.11
Nodes (48): D(), Assumptions, Portfolio, replay(), build_report(), code_hashes(), connect_readonly(), export_events() (+40 more)

### Community 6 - "ui.ts"
Cohesion: 0.16
Nodes (19): AccountingBoundaries(), AccountingCosts(), AccountingGross(), AccountingRecords(), AccountingSummary(), amounts(), LearningBoundaries(), LearningInventory() (+11 more)

### Community 7 - "test_learning_engine.py"
Cohesion: 0.12
Nodes (46): digest(), encode(), evaluate(), main(), markdown(), packet_checks(), protected(), protected_windows() (+38 more)

### Community 8 - "test_state_contract.py"
Cohesion: 0.18
Nodes (23): at(), build_state(), buy(), free_port(), normalize(), pin_clock(), parametrize, Dashboard read-path contract: fixed Store-seeded ledgers and a pinned clock.… (+15 more)

### Community 9 - "Engine"
Cohesion: 0.15
Nodes (6): age(), Engine, symbol_for(), dumps(), test_late_fee_window_still_includes_original_fill_after_three_days(), test_adapter_hashes_are_cached_local_and_covered_by_packet_hash()

### Community 10 - "scripts"
Cohesion: 0.05
Nodes (37): @commitlint/cli, @commitlint/config-conventional, @commitlint/lint, @commitlint/load, husky, devDependencies, @commitlint/cli, @commitlint/config-conventional (+29 more)

### Community 11 - "useDashboard"
Cohesion: 0.16
Nodes (21): ModeBadge(), Context, useDashboard(), Detail, EvidenceDialog(), PacketDialog(), ResearchExperiments(), ResearchGates() (+13 more)

### Community 12 - "connection.test.ts"
Cohesion: 0.31
Nodes (5): seed(), dashboard(), health(), now, services()

### Community 13 - "compilerOptions"
Cohesion: 0.07
Nodes (29): compilerOptions, allowJs, checkJs, esModuleInterop, incremental, isolatedModules, jsx, lib (+21 more)

### Community 14 - "contracts.ts"
Cohesion: 0.08
Nodes (25): SystemView(), api(), errorMessage(), empty, Snapshot, accountingSchema, amount, counts (+17 more)

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
Cohesion: 0.13
Nodes (27): CodexReviewer, command(), material_hash(), Bounded Codex CLI reviewer. Broker credentials and tools are not inherited., evidence_for(), Point-in-time evidence screening; language models cannot override vetoes., screen(), validate_review() (+19 more)

### Community 17 - "test_quantconnect_validation.py"
Cohesion: 0.12
Nodes (28): QCAlgorithm, AstralBtcSignalParity, bundle(), compare(), main(), new_output(), pinned_sources(), Package an in-cloud comparison or validate its aggregate-only diagnostic log. (+20 more)

### Community 18 - "motion.tsx"
Cohesion: 0.11
Nodes (19): HealthSummary(), Heartbeat(), AnimationProvider(), initialMode(), initialSystem(), LoadingPanel(), Mode, readMode() (+11 more)

### Community 19 - "health-page.tsx"
Cohesion: 0.11
Nodes (24): metadata, HealthChanges(), HealthDetails(), HealthFooterStatus(), HealthMap(), HealthPage(), attention, inTopic() (+16 more)

### Community 20 - "timestamp"
Cohesion: 0.07
Nodes (63): contract(), diagnose(), digest(), observe(), Frozen research contract and append-only observations. No execution interface., Retrospective price-only prefixes. Never pretend these were known earlier., register(), source_hashes() (+55 more)

### Community 21 - "relay.ts"
Cohesion: 0.17
Nodes (12): Context, dynamic, GET(), POST(), runtime, acceptsGzip(), compress, getPaths (+4 more)

### Community 22 - "overview-page.tsx"
Cohesion: 0.17
Nodes (10): ConnectionBanner(), EquityChart(), OverviewFooter(), OverviewPage(), views, StrategiesView(), StrategyCounts(), Shown (+2 more)

### Community 23 - "intelligence.py"
Cohesion: 0.15
Nodes (14): ASTRAL paper-only service., clean(), date(), named(), parse(), Independent public intelligence collector. No broker, credentials or order…, safe_url(), Source (+6 more)

### Community 24 - "test_experiment.py"
Cohesion: 0.14
Nodes (25): parse_fomc(), Official FOMC meeting dates, scoped context only; no complete macro calendar., propose(), ATR14 + trend/breakout candidate and fixed fractional loss-budget sizing. All…, context(), fomc_html(), history(), parametrize (+17 more)

### Community 25 - "test_health_engine.py"
Cohesion: 0.27
Nodes (12): observations(), Providers, parametrize, Health contracts: temporary ledgers and HTTP fixtures; never models/brokers., report(), test_engine_health_is_separate_from_model_enablement_and_market_closure(), test_event_driven_execution_worker_is_judged_by_status_not_age(), test_local_observation_failures_do_not_reuse_healthy_state() (+4 more)

### Community 26 - "seed.ts"
Cohesion: 0.21
Nodes (10): dynamic, metadata, RootLayout(), Provider(), AppFrame(), Seed, healthSchema, loadSeed() (+2 more)

### Community 27 - "read.ts"
Cohesion: 0.24
Nodes (8): ApiError, parseResponse(), ReadResult, allowedHost(), originDefaults, originVariables, Service, serviceUrl()

### Community 28 - "devDependencies"
Cohesion: 0.04
Nodes (48): eslint, eslint-config-next, @fontsource-variable/dm-sans, @fontsource-variable/space-grotesk, dependencies, @fontsource-variable/dm-sans, @fontsource-variable/space-grotesk, motion (+40 more)

### Community 29 - "BrokerFailure"
Cohesion: 0.14
Nodes (22): ExitPlan, Halt, Intent, ResearchBar, RiskCandidate, BrokerFailure, Exception, Exception (+14 more)

### Community 30 - "utcnow"
Cohesion: 0.17
Nodes (5): No remote API. Fills are synthetic and do not model queueing/market impact., Simulator, read_context(), utcnow(), test_valid_context_shape_remains_available()

### Community 31 - "order.tsx"
Cohesion: 0.22
Nodes (13): OrderDialog(), AssetBar(), ExecutionStream(), PositionsPanel(), Context, Selection, SelectionState(), useSelection() (+5 more)

### Community 32 - "test_review_repairs.py"
Cohesion: 0.18
Nodes (17): daily_history(), fee(), parametrize, Locked review regressions. Synthetic brokers, patched models and tmp ledgers…, test_all_vetoed_cycle_never_calls_model(), test_diagnostic_failure_still_journals_prospective_veto(), test_disabled_model_keeps_deterministic_arm_in_new_observations(), test_distinct_lab_still_copies_or_reuses() (+9 more)

### Community 33 - "Store"
Cohesion: 0.14
Nodes (14): collect(), health_inputs(), intelligence(), lifespan(), Local-only companion: independent DB and lifecycle preserve the shadow pilot., Collector, Store, test_maintenance_empty_snapshot_304_extends_inspection_not_publication() (+6 more)

### Community 34 - "Settings"
Cohesion: 0.16
Nodes (14): create_app(), Settings, test_api_shadow_does_not_enable_orders_and_rejects_bypass_fields(), test_read_only_adapter_blocks_post_and_delete_before_transport(), test_shadow_cannot_submit_even_with_repeated_approvals(), test_local_health_inputs_are_small_read_only_and_do_not_export_account_data(), test_replay_report_is_visible_only_in_the_book_that_records_its_receipt(), fixture (+6 more)

### Community 35 - "HealthMonitor"
Cohesion: 0.33
Nodes (4): effective(), HealthMonitor, parse_report(), test_local_revalidation_time_is_distinct_from_provider_update_time()

### Community 36 - "accounting/page.tsx"
Cohesion: 0.19
Nodes (11): dynamic, metadata, Page(), dynamic, metadata, Page(), AccountingContent(), LearningContent() (+3 more)

### Community 37 - "validate_pr_body.cjs"
Cohesion: 0.23
Nodes (11): fs, main(), readableText(), REQUIRED_CHECKS, REQUIRED_SECTIONS, sections(), validatePullRequestBody(), withoutComments() (+3 more)

### Community 38 - "test_readiness_gates.py"
Cohesion: 0.11
Nodes (22): parse_bea(), HTMLParser, Scoped BEA schedule; a date is retained without inventing an unspecified…, Schedule, Validate provider fee records without estimating missing fees or rewriting…, record_fee(), validate_activity(), view() (+14 more)

### Community 40 - "overnight_watch.py"
Cohesion: 0.25
Nodes (9): audit(), now(), Bounded overnight observation of the existing GET-only localhost paper lab., safety(), watch(), write_summary(), parametrize, test_observer_counts_lost_write_and_http_failure() (+1 more)

### Community 41 - "engine.py"
Cohesion: 0.17
Nodes (12): Fixed-host Alpaca paper adapter and a separately labelled durable simulator., attribute(), book_for(), canonical_symbol(), Inventory attribution is evidence, not a substitute for broker availability., isolate_experiment_workers(), lab_path(), main() (+4 more)

### Community 42 - "test_stage2_validation.py"
Cohesion: 0.20
Nodes (13): audit_crypto(), Read-only reconciliation analysis. Hypotheses cannot become ledger entries., Compare authoritative gross executions and positions; explain, never waive. Fee…, parametrize, Synthetic decision-path and fault tests; none are broker-paper executions., reconciliation_fixture(), test_confirmed_fee_matches_and_duplicate_activity_is_not_counted_twice(), test_downstream_candidate_is_visible_but_inventory_still_vetoes() (+5 more)

### Community 47 - "boundaries.test.ts"
Cohesion: 0.32
Nodes (6): allowlist, files, isClient(), lines(), root, text()

### Community 49 - "check-skills.cjs"
Cohesion: 0.33
Nodes (6): checkSkills(), crypto, fs, hashSkillFolder(), path, ROOT

### Community 50 - "navigation.tsx"
Cohesion: 0.40
Nodes (3): NavLink(), Navigation(), pages

### Community 52 - "commitlint.config.cjs"
Cohesion: 0.83
Nodes (3): bodyMaxLineLength(), footerMaxLineLength(), maxLineLength()

### Community 53 - "intelligence-feed.tsx"
Cohesion: 0.23
Nodes (7): Dialog(), IntelligenceFeed(), SourceDialog(), ViewDialog(), IntelligenceView(), SourceLink(), News

## Knowledge Gaps
- **154 isolated node(s):** `Source`, `metadata`, `dynamic`, `runtime`, `dynamic` (+149 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Store` connect `Store` to `datetime`, `test_review_repairs.py`, `Settings`, `test_accounting_engine.py`, `HealthEngine`, `run`, `D`, `test_learning_engine.py`, `test_readiness_gates.py`, `engine.py`, `test_state_contract.py`, `AlpacaPaper`, `screen`, `timestamp`, `intelligence.py`, `test_experiment.py`, `test_health_engine.py`, `BrokerFailure`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._
- **Why does `utcnow()` connect `utcnow` to `datetime`, `AlpacaPaper`, `Settings`, `HealthMonitor`, `HealthEngine`, `Store`, `test_readiness_gates.py`, `run`, `test_review_repairs.py`, `engine.py`, `Engine`, `screen`, `timestamp`, `intelligence.py`, `test_health_engine.py`, `BrokerFailure`?**
  _High betweenness centrality (0.035) - this node is a cross-community bridge._
- **Why does `Engine` connect `Engine` to `test_review_repairs.py`, `AlpacaPaper`, `Settings`, `run`, `datetime`, `D`, `test_readiness_gates.py`, `test_state_contract.py`, `engine.py`, `test_stage2_validation.py`, `screen`, `timestamp`, `test_experiment.py`, `BrokerFailure`, `utcnow`?**
  _High betweenness centrality (0.023) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `Store` (e.g. with `ExitPlan` and `Halt`) actually correct?**
  _`Store` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `Engine` (e.g. with `ExitPlan` and `Halt`) actually correct?**
  _`Engine` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 30 inferred relationships involving `D()` (e.g. with `diagnose()` and `validate_activity()`) actually correct?**
  _`D()` has 30 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Source`, `metadata`, `dynamic` to the rest of the system?**
  _154 weakly-connected nodes found - possible documentation gaps or missing edges._