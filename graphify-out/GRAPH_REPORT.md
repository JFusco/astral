# Graph Report - astral-trading  (2026-10-26)

## Corpus Check
- 201 files · ~73,261 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1372 nodes · 4098 edges · 62 communities (55 shown, 7 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 143 edges (avg confidence: 0.63)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f33a5863`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_event_sources.py
- broker.py
- run
- test_accounting_engine.py
- utcnow
- D
- ui.ts
- test_learning_engine.py
- test_state_contract.py
- test_execution_pilot.py
- scripts
- useDashboard
- timestamp
- compilerOptions
- contracts.ts
- support.cjs
- screen
- test_readiness_gates.py
- motion.tsx
- health-page.tsx
- liquidity_runner.py
- relay.ts
- BrokerFailure
- overview-page.tsx
- datetime
- accounting-content.tsx
- quantconnect/__init__.py
- engine.py
- devDependencies
- Store
- Engine
- panel.tsx
- test_review_repairs.py
- intelligence.py
- decide
- connection.test.ts
- read.ts
- validate_pr_body.cjs
- Settings
- test_trade_history.py
- overnight_watch.py
- test_executor_ownership.py
- test_health_engine.py
- test_stage2_validation.py
- test_liquidity_experiment.py
- Connection
- RuleViolation
- boundaries.test.ts
- seed.ts
- check-skills.cjs
- HealthEngine
- Meetings
- commitlint.config.cjs
- Schedule
- proxy.ts
- next.config.ts
- StatusHeading
- test_quantconnect_validation.py
- prepare-standalone.mjs

## God Nodes (most connected - your core abstractions)
1. `Store` - 94 edges
2. `run()` - 91 edges
3. `Engine` - 82 edges
4. `utcnow()` - 78 edges
5. `D()` - 66 edges
6. `Settings` - 59 edges
7. `useDashboard()` - 53 edges
8. `BrokerFailure` - 47 edges
9. `dumps()` - 47 edges
10. `intent()` - 45 edges

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

## Communities (62 total, 7 thin omitted)

### Community 0 - "test_event_sources.py"
Cohesion: 0.10
Nodes (30): Retain scoped official calendar catalogs; never certify missing categories., Maintenance needs two current publisher lists. NY Fed remains partial BLS., retain_additional_scopes(), retain_scopes(), catalog(), Cells, event(), maintenance() (+22 more)

### Community 1 - "broker.py"
Cohesion: 0.24
Nodes (8): Limiter, Fixed-host Alpaca paper adapter and a separately labelled durable simulator., account_identity(), AccountLease, OwnershipError, private_owned(), Exception, Cooperative paper-account ownership for one OS user on one host.

### Community 2 - "run"
Cohesion: 0.13
Nodes (37): Failure scenarios and adversarial selection cases; all trades are synthetic., test_ambiguous_fee_is_not_assigned_to_a_strategy(), test_intraday_exit_cannot_liquidate_swing_inventory(), test_late_confirmed_asset_fee_is_idempotent_and_reconciles(), test_local_exit_survives_restart_and_unknown_response(), test_quantity_and_shared_risk_boundaries(), test_readback_422_after_accepted_order_never_releases_reservation(), test_repeated_identical_exit_veto_is_journaled_once() (+29 more)

### Community 3 - "test_accounting_engine.py"
Cohesion: 0.06
Nodes (87): at(), canonical(), cost_report(), digest(), evaluate(), main(), number(), precise() (+79 more)

### Community 4 - "utcnow"
Cohesion: 0.14
Nodes (7): No remote API. Fills are synthetic and do not model queueing/market impact., Simulator, record_fee(), read_context(), utcnow(), test_fee_revisions_retained_without_overwriting_confirmed_debit(), test_valid_context_shape_remains_available()

### Community 5 - "D"
Cohesion: 0.11
Nodes (47): D(), Assumptions, Portfolio, replay(), build_report(), code_hashes(), connect_readonly(), export_events() (+39 more)

### Community 6 - "ui.ts"
Cohesion: 0.15
Nodes (17): Dialog(), LearningBoundaries(), LearningInventory(), LearningModel(), LearningOutcomes(), LearningProtected(), LearningSummary(), LearningUsage() (+9 more)

### Community 7 - "test_learning_engine.py"
Cohesion: 0.15
Nodes (39): digest(), encode(), evaluate(), main(), markdown(), packet_checks(), protected(), protected_windows() (+31 more)

### Community 8 - "test_state_contract.py"
Cohesion: 0.18
Nodes (23): at(), build_state(), buy(), free_port(), normalize(), pin_clock(), parametrize, Dashboard read-path contract: fixed Store-seeded ledgers and a pinned clock.… (+15 more)

### Community 9 - "test_execution_pilot.py"
Cohesion: 0.21
Nodes (10): ExecutionPilot, One explicitly authorized execution experiment; never an alpha strategy. Uses…, pilot(), parametrize, test_crash_after_entry_resumes_exit_without_new_entry(), test_final_pilot_boundary_blocks_wrong_or_oversize_requests(), test_pilot_and_strategy_workers_cannot_share_authority(), test_pilot_recovers_lost_accepted_entry_without_duplicate() (+2 more)

### Community 10 - "scripts"
Cohesion: 0.05
Nodes (37): @commitlint/cli, @commitlint/config-conventional, @commitlint/lint, @commitlint/load, husky, devDependencies, @commitlint/cli, @commitlint/config-conventional (+29 more)

### Community 11 - "useDashboard"
Cohesion: 0.19
Nodes (19): HealthFooterStatus(), EquityChart(), OverviewFooter(), Context, useDashboard(), PacketDialog(), ResearchExperiments(), ResearchGates() (+11 more)

### Community 12 - "timestamp"
Cohesion: 0.14
Nodes (18): diagnose(), Retrospective price-only prefixes. Never pretend these were known earlier., Validate provider fee records without estimating missing fees or rewriting…, validate_activity(), turnover(), Same-venue REST book/quote validation. Visible depth never guarantees a fill., _validate(), Isolated deterministic portfolio execution model. No broker or Store imports.… (+10 more)

### Community 13 - "compilerOptions"
Cohesion: 0.07
Nodes (29): compilerOptions, allowJs, checkJs, esModuleInterop, incremental, isolatedModules, jsx, lib (+21 more)

### Community 14 - "contracts.ts"
Cohesion: 0.07
Nodes (28): api(), errorMessage(), empty, Seed, Snapshot, accountingSchema, amount, counts (+20 more)

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
Cohesion: 0.17
Nodes (22): CodexReviewer, command(), material_hash(), Bounded Codex CLI reviewer. Broker credentials and tools are not inherited., screen(), validate_review(), parametrize, selection_fixture() (+14 more)

### Community 17 - "test_readiness_gates.py"
Cohesion: 0.18
Nodes (19): validate_book(), calendar_coverage(), All scoped categories need retained, current, forward-covering evidence.…, view(), bea_html(), book(), fee(), parametrize (+11 more)

### Community 18 - "motion.tsx"
Cohesion: 0.08
Nodes (25): dynamic, metadata, RootLayout(), AnimationProvider(), initialMode(), initialSystem(), LoadingPanel(), Mode (+17 more)

### Community 19 - "health-page.tsx"
Cohesion: 0.17
Nodes (14): metadata, HealthChanges(), HealthDetails(), HealthMap(), HealthPage(), HealthSummary(), inTopic(), reportedNodes() (+6 more)

### Community 20 - "liquidity_runner.py"
Cohesion: 0.24
Nodes (22): contract(), digest(), source_hashes(), Policy, binding(), get(), get_inventory_status(), hashes() (+14 more)

### Community 21 - "relay.ts"
Cohesion: 0.17
Nodes (12): Context, dynamic, GET(), POST(), runtime, acceptsGzip(), compress, getPaths (+4 more)

### Community 22 - "BrokerFailure"
Cohesion: 0.28
Nodes (3): AlpacaPaper, BrokerFailure, Exception

### Community 23 - "overview-page.tsx"
Cohesion: 0.12
Nodes (13): IntelligenceFeed(), ModeBadge(), OverviewPage(), views, PortfolioCards(), ViewDialog(), IntelligenceView(), StrategiesView() (+5 more)

### Community 24 - "datetime"
Cohesion: 0.16
Nodes (24): parse_fomc(), Official FOMC meeting dates, scoped context only; no complete macro calendar., propose(), ATR14 + trend/breakout candidate and fixed fractional loss-budget sizing. All…, datetime, context(), fomc_html(), history() (+16 more)

### Community 25 - "accounting-content.tsx"
Cohesion: 0.31
Nodes (7): AccountingBoundaries(), AccountingCosts(), AccountingGross(), AccountingRecords(), AccountingSummary(), amounts(), Accounting

### Community 27 - "engine.py"
Cohesion: 0.12
Nodes (19): Append future custody changes without altering fills or old evidence., retain_checkpoint(), observe(), Frozen research contract and append-only observations. No execution interface., register(), state(), isolate_experiment_workers(), lab_path() (+11 more)

### Community 28 - "devDependencies"
Cohesion: 0.04
Nodes (48): eslint, eslint-config-next, @fontsource-variable/dm-sans, @fontsource-variable/space-grotesk, dependencies, @fontsource-variable/dm-sans, @fontsource-variable/space-grotesk, motion (+40 more)

### Community 29 - "Store"
Cohesion: 0.26
Nodes (4): Store, parametrize, test_unexpected_source_failure_keeps_other_feed_alive_and_recovers(), test_replay_report_is_visible_only_in_the_book_that_records_its_receipt()

### Community 30 - "Engine"
Cohesion: 0.14
Nodes (6): age(), Engine, symbol_for(), book_for(), dumps(), test_adapter_hashes_are_cached_local_and_covered_by_packet_hash()

### Community 31 - "panel.tsx"
Cohesion: 0.12
Nodes (25): attention, items, MarketUniverse(), OrbitalUniverse(), OrbitItem, OrderDialog(), AssetBar(), ExecutionStream() (+17 more)

### Community 32 - "test_review_repairs.py"
Cohesion: 0.19
Nodes (16): daily_history(), fee(), parametrize, Locked review regressions. Synthetic brokers, patched models and tmp ledgers…, test_all_vetoed_cycle_never_calls_model(), test_diagnostic_failure_still_journals_prospective_veto(), test_distinct_lab_still_copies_or_reuses(), test_global_fee_latch_blocks_strategy_sell_with_rule_violation() (+8 more)

### Community 33 - "intelligence.py"
Cohesion: 0.10
Nodes (27): parse_bea(), ASTRAL paper-only service., collect(), health_inputs(), intelligence(), lifespan(), Local-only companion: independent DB and lifecycle preserve the shadow pilot., clean() (+19 more)

### Community 34 - "decide"
Cohesion: 0.38
Nodes (11): decide(), One-unit synthetic quote replay, with fills strictly AFTER decisions. Quote-…, replay(), event(), parametrize, test_entry_cancels_if_research_expires_during_latency(), test_entry_timing_fail_closed(), test_exit_rules_work_without_entry_permission() (+3 more)

### Community 35 - "connection.test.ts"
Cohesion: 0.23
Nodes (6): Health, seed(), Source, dashboard(), health(), services()

### Community 36 - "read.ts"
Cohesion: 0.12
Nodes (18): dynamic, metadata, Page(), dynamic, metadata, Page(), AccountingContent(), LearningContent() (+10 more)

### Community 37 - "validate_pr_body.cjs"
Cohesion: 0.23
Nodes (11): fs, main(), readableText(), REQUIRED_CHECKS, REQUIRED_SECTIONS, sections(), validatePullRequestBody(), withoutComments() (+3 more)

### Community 38 - "Settings"
Cohesion: 0.17
Nodes (13): create_app(), Settings, test_api_shadow_does_not_enable_orders_and_rejects_bypass_fields(), test_read_only_adapter_blocks_post_and_delete_before_transport(), test_shadow_cannot_submit_even_with_repeated_approvals(), test_local_health_inputs_are_small_read_only_and_do_not_export_account_data(), fixture, research_engine() (+5 more)

### Community 39 - "test_trade_history.py"
Cohesion: 0.30
Nodes (10): aggregate_daily(), Build daily candles exclusively from documented execution records., aggregate(), batch(), parametrize, test_bad_trade_records_fail_closed(), test_history_shares_completed_days_and_reconstructs_each_immutable_batch(), test_missing_trade_day_is_not_filled_from_quotes() (+2 more)

### Community 40 - "overnight_watch.py"
Cohesion: 0.25
Nodes (9): audit(), now(), Bounded overnight observation of the existing GET-only localhost paper lab., safety(), watch(), write_summary(), parametrize, test_observer_counts_lost_write_and_http_failure() (+1 more)

### Community 41 - "test_executor_ownership.py"
Cohesion: 0.22
Nodes (16): adapters(), fixture, parametrize, Account ownership through public broker methods; no real provider writes., test_changed_identity_latches_writes_even_if_the_original_identity_returns(), test_close_keeps_ownership_until_the_inflight_write_finishes(), test_closed_adapter_cannot_reacquire_authority_and_market_data_cannot_mutate(), test_different_accounts_can_write_and_read_only_observers_do_not_contend() (+8 more)

### Community 42 - "test_health_engine.py"
Cohesion: 0.17
Nodes (17): effective(), HealthMonitor, parse_report(), observations(), Providers, parametrize, Health contracts: temporary ledgers and HTTP fixtures; never models/brokers., report() (+9 more)

### Community 43 - "test_stage2_validation.py"
Cohesion: 0.20
Nodes (13): audit_crypto(), Read-only reconciliation analysis. Hypotheses cannot become ledger entries., Compare authoritative gross executions and positions; explain, never waive. Fee…, parametrize, Synthetic decision-path and fault tests; none are broker-paper executions., reconciliation_fixture(), test_confirmed_fee_matches_and_duplicate_activity_is_not_counted_twice(), test_downstream_candidate_is_visible_but_inventory_still_vetoes() (+5 more)

### Community 44 - "test_liquidity_experiment.py"
Cohesion: 0.32
Nodes (10): evaluate(), floor(), Quote-only liquidity experiment. No orders, fills, positions, P&L or promotion., walk(), append(), inputs(), parametrize, test_baseline_rejects_while_separate_half_depth_model_can_cover_25() (+2 more)

### Community 46 - "RuleViolation"
Cohesion: 0.35
Nodes (9): ExitPlan, Halt, Intent, ResearchBar, RiskCandidate, Exception, RuleViolation, BaseModel (+1 more)

### Community 47 - "boundaries.test.ts"
Cohesion: 0.32
Nodes (6): allowlist, files, isClient(), lines(), root, text()

### Community 48 - "seed.ts"
Cohesion: 0.29
Nodes (5): healthSchema, loadSeed(), seedScope(), upstreamFetch(), now

### Community 49 - "check-skills.cjs"
Cohesion: 0.33
Nodes (6): checkSkills(), crypto, fs, hashSkillFolder(), path, ROOT

### Community 50 - "HealthEngine"
Cohesion: 0.19
Nodes (8): lifespan(), Standalone health service, separate process and ledger from telemetry/trading., state(), fresh(), HealthEngine, Independent assessments from telemetry observations; no trading authority., moment(), Public provider reports, separate from account/model connectivity and risk. No…

### Community 52 - "commitlint.config.cjs"
Cohesion: 0.83
Nodes (3): bodyMaxLineLength(), footerMaxLineLength(), maxLineLength()

### Community 53 - "Schedule"
Cohesion: 0.25
Nodes (3): HTMLParser, Scoped BEA schedule; a date is retained without inventing an unspecified…, Schedule

### Community 58 - "test_quantconnect_validation.py"
Cohesion: 0.11
Nodes (35): price_signal(), Pure OHLC hypothesis; caller validates provenance and time separately., QCAlgorithm, as_utc(), AstralBtcSignalParity, Compare both implementations in cloud memory; export aggregate diagnostics only., bundle(), compare() (+27 more)

## Knowledge Gaps
- **154 isolated node(s):** `Source`, `metadata`, `dynamic`, `runtime`, `dynamic` (+149 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Store` connect `Store` to `test_event_sources.py`, `run`, `test_accounting_engine.py`, `D`, `test_learning_engine.py`, `test_state_contract.py`, `screen`, `test_readiness_gates.py`, `liquidity_runner.py`, `datetime`, `engine.py`, `Engine`, `test_review_repairs.py`, `intelligence.py`, `Settings`, `test_trade_history.py`, `test_executor_ownership.py`, `test_health_engine.py`, `test_liquidity_experiment.py`, `RuleViolation`, `HealthEngine`?**
  _High betweenness centrality (0.054) - this node is a cross-community bridge._
- **Why does `utcnow()` connect `utcnow` to `test_event_sources.py`, `broker.py`, `intelligence.py`, `run`, `test_review_repairs.py`, `Settings`, `test_execution_pilot.py`, `test_health_engine.py`, `timestamp`, `RuleViolation`, `screen`, `test_readiness_gates.py`, `HealthEngine`, `BrokerFailure`, `engine.py`, `Engine`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **Why does `Engine` connect `Engine` to `test_review_repairs.py`, `run`, `test_accounting_engine.py`, `utcnow`, `D`, `Settings`, `test_state_contract.py`, `test_execution_pilot.py`, `test_stage2_validation.py`, `RuleViolation`, `screen`, `BrokerFailure`, `datetime`, `engine.py`, `Store`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `Store` (e.g. with `ExitPlan` and `Halt`) actually correct?**
  _`Store` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `Engine` (e.g. with `ExitPlan` and `Halt`) actually correct?**
  _`Engine` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 30 inferred relationships involving `D()` (e.g. with `diagnose()` and `validate_activity()`) actually correct?**
  _`D()` has 30 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Source`, `metadata`, `dynamic` to the rest of the system?**
  _154 weakly-connected nodes found - possible documentation gaps or missing edges._