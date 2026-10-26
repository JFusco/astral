# Graph Report - astral-trading  (2026-10-26)

## Corpus Check
- 192 files · ~69,749 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1274 nodes · 3790 edges · 69 communities (58 shown, 11 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 135 edges (avg confidence: 0.64)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `79b7f8bf`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- datetime
- AlpacaPaper
- run
- test_accounting_engine.py
- test_health_engine.py
- D
- ui.ts
- test_learning_engine.py
- test_state_contract.py
- Engine
- scripts
- useDashboard
- test_execution_pilot.py
- compilerOptions
- contracts.ts
- support.cjs
- screen
- timestamp
- motion.tsx
- health-page.tsx
- liquidity_runner.py
- relay.ts
- engine.py
- Settings
- test_experiment.py
- test_risk.py
- test_review_repairs.py
- test_stage2_validation.py
- devDependencies
- dependencies
- utcnow
- overview-page.tsx
- Source
- intelligence.py
- HealthEngine
- decide
- accounting/page.tsx
- validate_pr_body.cjs
- test_readiness_gates.py
- Connection
- overnight_watch.py
- Store
- HealthMonitor
- parse_bea
- Cells
- read.ts
- scripts
- boundaries.test.ts
- health-galaxy.js
- check-skills.cjs
- navigation.tsx
- frontend/package.json
- commitlint.config.cjs
- intelligence-feed.tsx
- StatusHeading
- proxy.ts
- next.config.ts
- tailwindcss
- typescript
- prepare-standalone.mjs
- test_trade_history.py
- dogfood_session.py
- ExecutionPilot
- app.spec.ts
- route.ts
- read.test.ts

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
- `Stream` --uses--> `Settings`  [INFERRED]
  tests/test_state_contract.py → backend/config.py
- `Stream` --uses--> `RuleViolation`  [INFERRED]
  tests/test_state_contract.py → backend/engine.py
- `FixedDateTime` --uses--> `Engine`  [INFERRED]
  tests/test_state_contract.py → backend/engine.py
- `Stream` --uses--> `Engine`  [INFERRED]
  tests/test_state_contract.py → backend/engine.py

## Import Cycles
- None detected.

## Communities (69 total, 11 thin omitted)

### Community 0 - "datetime"
Cohesion: 0.12
Nodes (30): Retain scoped official calendar catalogs; never certify missing categories., Maintenance needs two current publisher lists. NY Fed remains partial BLS., retain_additional_scopes(), retain_scopes(), catalog(), event(), maintenance(), nyfed() (+22 more)

### Community 1 - "AlpacaPaper"
Cohesion: 0.19
Nodes (3): AlpacaPaper, Limiter, quote()

### Community 2 - "run"
Cohesion: 0.12
Nodes (41): Failure scenarios and adversarial selection cases; all trades are synthetic., test_ambiguous_fee_is_not_assigned_to_a_strategy(), test_api_shadow_does_not_enable_orders_and_rejects_bypass_fields(), test_intraday_exit_cannot_liquidate_swing_inventory(), test_late_confirmed_asset_fee_is_idempotent_and_reconciles(), test_local_exit_survives_restart_and_unknown_response(), test_quantity_and_shared_risk_boundaries(), test_read_only_adapter_blocks_post_and_delete_before_transport() (+33 more)

### Community 3 - "test_accounting_engine.py"
Cohesion: 0.10
Nodes (56): at(), canonical(), cost_report(), digest(), evaluate(), main(), number(), precise() (+48 more)

### Community 4 - "test_health_engine.py"
Cohesion: 0.23
Nodes (12): effective(), parse_report(), Public provider reports, separate from account/model connectivity and risk. No…, observations(), parametrize, Health contracts: temporary ledgers and HTTP fixtures; never models/brokers., report(), test_engine_health_is_separate_from_model_enablement_and_market_closure() (+4 more)

### Community 5 - "D"
Cohesion: 0.11
Nodes (47): D(), Assumptions, Portfolio, replay(), build_report(), code_hashes(), connect_readonly(), export_events() (+39 more)

### Community 6 - "ui.ts"
Cohesion: 0.14
Nodes (21): StrategiesView(), StrategyCounts(), AccountingBoundaries(), AccountingCosts(), AccountingGross(), AccountingRecords(), AccountingSummary(), amounts() (+13 more)

### Community 7 - "test_learning_engine.py"
Cohesion: 0.15
Nodes (39): digest(), encode(), evaluate(), main(), markdown(), packet_checks(), protected(), protected_windows() (+31 more)

### Community 8 - "test_state_contract.py"
Cohesion: 0.18
Nodes (23): at(), build_state(), buy(), free_port(), normalize(), pin_clock(), parametrize, Dashboard read-path contract: fixed Store-seeded ledgers and a pinned clock.… (+15 more)

### Community 9 - "Engine"
Cohesion: 0.16
Nodes (5): age(), Engine, symbol_for(), book_for(), dumps()

### Community 10 - "scripts"
Cohesion: 0.05
Nodes (37): @commitlint/cli, @commitlint/config-conventional, @commitlint/lint, @commitlint/load, husky, devDependencies, @commitlint/cli, @commitlint/config-conventional (+29 more)

### Community 11 - "useDashboard"
Cohesion: 0.14
Nodes (21): HealthFooterStatus(), Context, useDashboard(), Detail, EvidenceDialog(), PacketDialog(), ResearchExperiments(), ResearchGates() (+13 more)

### Community 12 - "test_execution_pilot.py"
Cohesion: 0.27
Nodes (10): pilot(), parametrize, test_crash_after_entry_resumes_exit_without_new_entry(), test_final_pilot_boundary_blocks_wrong_or_oversize_requests(), test_pilot_and_strategy_workers_cannot_share_authority(), test_pilot_recovers_lost_accepted_entry_without_duplicate(), test_pilot_refuses_existing_positions(), test_synthetic_round_trip_and_completed_resume_do_not_buy_twice() (+2 more)

### Community 13 - "compilerOptions"
Cohesion: 0.07
Nodes (29): compilerOptions, allowJs, checkJs, esModuleInterop, incremental, isolatedModules, jsx, lib (+21 more)

### Community 14 - "contracts.ts"
Cohesion: 0.08
Nodes (37): dynamic, metadata, RootLayout(), Provider(), AppFrame(), api(), errorMessage(), empty (+29 more)

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
Nodes (24): CodexReviewer, command(), material_hash(), Bounded Codex CLI reviewer. Broker credentials and tools are not inherited., Point-in-time evidence screening; language models cannot override vetoes., screen(), validate_review(), parametrize (+16 more)

### Community 17 - "timestamp"
Cohesion: 0.23
Nodes (11): Same-venue REST book/quote validation. Visible depth never guarantees a fill., _validate(), Isolated deterministic portfolio execution model. No broker or Store imports.…, floor_step(), number(), Reproducible research proposals. No network, randomness, or order side effects., timestamp(), Deterministic timing hypotheses. Produces candidates, never orders or fills. (+3 more)

### Community 18 - "motion.tsx"
Cohesion: 0.11
Nodes (19): Heartbeat(), MarketUniverse(), AnimationProvider(), initialMode(), initialSystem(), LoadingPanel(), Mode, readMode() (+11 more)

### Community 19 - "health-page.tsx"
Cohesion: 0.13
Nodes (20): metadata, HealthChanges(), HealthDetails(), HealthMap(), HealthPage(), attention, inTopic(), reportedNodes() (+12 more)

### Community 20 - "liquidity_runner.py"
Cohesion: 0.11
Nodes (42): contract(), digest(), observe(), register(), source_hashes(), state(), evaluate(), floor() (+34 more)

### Community 21 - "relay.ts"
Cohesion: 0.18
Nodes (12): acceptsGzip(), compress, getPaths, postPaths, reject(), relay(), responseHeaders, allowedHost() (+4 more)

### Community 22 - "engine.py"
Cohesion: 0.18
Nodes (11): Fixed-host Alpaca paper adapter and a separately labelled durable simulator., Frozen research contract and append-only observations. No execution interface., attribute(), canonical_symbol(), Inventory attribution is evidence, not a substitute for broker availability., One explicitly authorized execution experiment; never an alpha strategy. Uses…, Evidence-by-evidence readiness. No threshold changes or execution capability., view() (+3 more)

### Community 23 - "Settings"
Cohesion: 0.20
Nodes (18): create_app(), ExitPlan, Halt, Intent, ResearchBar, RiskCandidate, BrokerFailure, Exception (+10 more)

### Community 24 - "test_experiment.py"
Cohesion: 0.18
Nodes (11): Meetings, parse_fomc(), HTMLParser, Official FOMC meeting dates, scoped context only; no complete macro calendar., evidence_for(), Credential-free local feed read; headlines remain untrusted scoped context., context(), fomc_html() (+3 more)

### Community 25 - "test_risk.py"
Cohesion: 0.18
Nodes (19): diagnose(), Retrospective price-only prefixes. Never pretend these were known earlier., price_signal(), propose(), ATR14 + trend/breakout candidate and fixed fractional loss-budget sizing. All…, Pure OHLC hypothesis; caller validates provenance and time separately., history(), parametrize (+11 more)

### Community 26 - "test_review_repairs.py"
Cohesion: 0.18
Nodes (17): daily_history(), fee(), parametrize, Locked review regressions. Synthetic brokers, patched models and tmp ledgers…, test_adapter_hashes_are_cached_local_and_covered_by_packet_hash(), test_all_vetoed_cycle_never_calls_model(), test_diagnostic_failure_still_journals_prospective_veto(), test_distinct_lab_still_copies_or_reuses() (+9 more)

### Community 27 - "test_stage2_validation.py"
Cohesion: 0.20
Nodes (13): audit_crypto(), Read-only reconciliation analysis. Hypotheses cannot become ledger entries., Compare authoritative gross executions and positions; explain, never waive. Fee…, parametrize, Synthetic decision-path and fault tests; none are broker-paper executions., reconciliation_fixture(), test_confirmed_fee_matches_and_duplicate_activity_is_not_counted_twice(), test_downstream_candidate_is_visible_but_inventory_still_vetoes() (+5 more)

### Community 28 - "devDependencies"
Cohesion: 0.12
Nodes (17): eslint, eslint-config-next, devDependencies, eslint, eslint-config-next, @playwright/test, @tailwindcss/postcss, @types/node (+9 more)

### Community 29 - "dependencies"
Cohesion: 0.12
Nodes (17): @fontsource-variable/dm-sans, @fontsource-variable/space-grotesk, dependencies, @fontsource-variable/dm-sans, @fontsource-variable/space-grotesk, motion, next, react (+9 more)

### Community 30 - "utcnow"
Cohesion: 0.13
Nodes (7): No remote API. Fills are synthetic and do not model queueing/market impact., Simulator, read_context(), utcnow(), fixture, research_engine(), test_valid_context_shape_remains_available()

### Community 31 - "overview-page.tsx"
Cohesion: 0.13
Nodes (22): HealthSummary(), OrderDialog(), AssetBar(), EquityChart(), ExecutionStream(), ModeBadge(), OverviewFooter(), OverviewPage() (+14 more)

### Community 33 - "intelligence.py"
Cohesion: 0.19
Nodes (12): ASTRAL paper-only service., clean(), date(), named(), parse(), Independent public intelligence collector. No broker, credentials or order…, safe_url(), Source (+4 more)

### Community 34 - "HealthEngine"
Cohesion: 0.24
Nodes (7): lifespan(), Standalone health service, separate process and ledger from telemetry/trading., state(), fresh(), HealthEngine, Independent assessments from telemetry observations; no trading authority., moment()

### Community 35 - "decide"
Cohesion: 0.38
Nodes (11): decide(), One-unit synthetic quote replay, with fills strictly AFTER decisions. Quote-…, replay(), event(), parametrize, test_entry_cancels_if_research_expires_during_latency(), test_entry_timing_fail_closed(), test_exit_rules_work_without_entry_permission() (+3 more)

### Community 36 - "accounting/page.tsx"
Cohesion: 0.19
Nodes (11): dynamic, metadata, Page(), dynamic, metadata, Page(), AccountingContent(), LearningContent() (+3 more)

### Community 37 - "validate_pr_body.cjs"
Cohesion: 0.23
Nodes (11): fs, main(), readableText(), REQUIRED_CHECKS, REQUIRED_SECTIONS, sections(), validatePullRequestBody(), withoutComments() (+3 more)

### Community 38 - "test_readiness_gates.py"
Cohesion: 0.16
Nodes (16): Validate provider fee records without estimating missing fees or rewriting…, record_fee(), validate_activity(), validate_book(), book(), fee(), parametrize, test_adequate_daily_volume_cannot_override_a_subminimum_depth_cap() (+8 more)

### Community 40 - "overnight_watch.py"
Cohesion: 0.25
Nodes (9): audit(), now(), Bounded overnight observation of the existing GET-only localhost paper lab., safety(), watch(), write_summary(), parametrize, test_observer_counts_lost_write_and_http_failure() (+1 more)

### Community 41 - "Store"
Cohesion: 0.13
Nodes (16): collect(), health_inputs(), intelligence(), lifespan(), Local-only companion: independent DB and lifecycle preserve the shadow pilot., Collector, Store, test_maintenance_empty_snapshot_304_extends_inspection_not_publication() (+8 more)

### Community 42 - "HealthMonitor"
Cohesion: 0.27
Nodes (5): HealthMonitor, Providers, test_missing_heartbeat_invalidates_all_cached_green_nodes(), test_provider_failure_backoff_cached_evidence_and_recovery_deduplicate(), test_unchanged_incident_with_new_source_timestamp_does_not_alert_again()

### Community 43 - "parse_bea"
Cohesion: 0.20
Nodes (6): parse_bea(), HTMLParser, Scoped BEA schedule; a date is retained without inventing an unspecified…, Schedule, bea_html(), test_bea_dates_preserve_clock_text_without_inventing_release_timezone()

### Community 44 - "Cells"
Cohesion: 0.29
Nodes (3): Cells, HTMLParser, Retain cells in a selected table, including links and their following text.

### Community 45 - "read.ts"
Cohesion: 0.36
Nodes (4): ApiError, parseResponse(), ReadResult, upstreamFetch()

### Community 46 - "scripts"
Cohesion: 0.25
Nodes (8): scripts, build, dev, lint, start, test, test:e2e, typecheck

### Community 47 - "boundaries.test.ts"
Cohesion: 0.32
Nodes (6): allowlist, files, isClient(), lines(), root, text()

### Community 48 - "health-galaxy.js"
Cohesion: 0.47
Nodes (3): createHealthGalaxy(), glowTexture(), random()

### Community 49 - "check-skills.cjs"
Cohesion: 0.33
Nodes (6): checkSkills(), crypto, fs, hashSkillFolder(), path, ROOT

### Community 50 - "navigation.tsx"
Cohesion: 0.40
Nodes (3): NavLink(), Navigation(), pages

### Community 51 - "frontend/package.json"
Cohesion: 0.40
Nodes (4): name, private, type, version

### Community 52 - "commitlint.config.cjs"
Cohesion: 0.83
Nodes (3): bodyMaxLineLength(), footerMaxLineLength(), maxLineLength()

### Community 53 - "intelligence-feed.tsx"
Cohesion: 0.23
Nodes (7): Dialog(), IntelligenceFeed(), SourceDialog(), ViewDialog(), IntelligenceView(), SourceLink(), News

### Community 63 - "test_trade_history.py"
Cohesion: 0.35
Nodes (9): aggregate_daily(), Build daily candles exclusively from documented execution records., aggregate(), batch(), parametrize, test_bad_trade_records_fail_closed(), test_history_shares_completed_days_and_reconstructs_each_immutable_batch(), test_missing_trade_day_is_not_filled_from_quotes() (+1 more)

### Community 64 - "dogfood_session.py"
Cohesion: 0.28
Nodes (7): isolate_experiment_workers(), lab_path(), main(), Bounded, GET-only Alpaca dogfood session using a private copied ledger., main(), main(), test_live_host_configuration_rejected()

### Community 67 - "route.ts"
Cohesion: 0.33
Nodes (5): Context, dynamic, GET(), POST(), runtime

## Knowledge Gaps
- **155 isolated node(s):** `Source`, `metadata`, `dynamic`, `runtime`, `dynamic` (+150 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Store` connect `Store` to `datetime`, `run`, `test_accounting_engine.py`, `test_health_engine.py`, `D`, `test_learning_engine.py`, `test_state_contract.py`, `test_execution_pilot.py`, `screen`, `timestamp`, `liquidity_runner.py`, `engine.py`, `Settings`, `test_experiment.py`, `test_review_repairs.py`, `utcnow`, `HealthEngine`, `test_readiness_gates.py`, `HealthMonitor`, `test_trade_history.py`, `dogfood_session.py`?**
  _High betweenness centrality (0.055) - this node is a cross-community bridge._
- **Why does `utcnow()` connect `utcnow` to `datetime`, `AlpacaPaper`, `HealthEngine`, `intelligence.py`, `ExecutionPilot`, `test_health_engine.py`, `test_readiness_gates.py`, `dogfood_session.py`, `run`, `Engine`, `HealthMonitor`, `screen`, `liquidity_runner.py`, `engine.py`, `Settings`, `test_experiment.py`, `test_review_repairs.py`?**
  _High betweenness centrality (0.039) - this node is a cross-community bridge._
- **Why does `Engine` connect `Engine` to `dogfood_session.py`, `AlpacaPaper`, `run`, `D`, `test_readiness_gates.py`, `test_state_contract.py`, `test_execution_pilot.py`, `screen`, `timestamp`, `liquidity_runner.py`, `engine.py`, `Settings`, `test_experiment.py`, `test_review_repairs.py`, `test_stage2_validation.py`, `utcnow`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `Store` (e.g. with `ExitPlan` and `Halt`) actually correct?**
  _`Store` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `Engine` (e.g. with `ExitPlan` and `Halt`) actually correct?**
  _`Engine` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 30 inferred relationships involving `D()` (e.g. with `diagnose()` and `validate_activity()`) actually correct?**
  _`D()` has 30 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Source`, `metadata`, `dynamic` to the rest of the system?**
  _155 weakly-connected nodes found - possible documentation gaps or missing edges._