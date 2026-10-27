# Graph Report - astral-trading  (2026-10-26)

## Corpus Check
- 201 files · ~74,501 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1393 nodes · 4241 edges · 66 communities (59 shown, 7 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 143 edges (avg confidence: 0.63)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e8f4365a`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_event_sources.py
- broker.py
- run
- dumps
- utcnow
- D
- ui.ts
- test_learning_engine.py
- Settings
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
- strategies-view.tsx
- test_experiment.py
- datetime
- quantconnect/__init__.py
- experiment.py
- devDependencies
- Store
- Engine
- overview-page.tsx
- test_review_repairs.py
- intelligence.py
- decide
- connection.test.ts
- read.ts
- validate_pr_body.cjs
- test_risk.py
- test_trade_history.py
- overnight_watch.py
- test_executor_ownership.py
- test_health_engine.py
- test_stage2_validation.py
- price_signal
- Connection
- RuleViolation
- boundaries.test.ts
- seed.ts
- check-skills.cjs
- HealthEngine
- intelligence-feed.tsx
- commitlint.config.cjs
- app.spec.ts
- intelligence_app.py
- proxy.ts
- next.config.ts
- HealthMonitor
- test_quantconnect_validation.py
- prepare-standalone.mjs
- navigation.tsx
- dogfood_session.py
- read.test.ts

## God Nodes (most connected - your core abstractions)
1. `Store` - 95 edges
2. `run()` - 91 edges
3. `Engine` - 83 edges
4. `utcnow()` - 80 edges
5. `D()` - 66 edges
6. `Settings` - 60 edges
7. `dumps()` - 58 edges
8. `useDashboard()` - 53 edges
9. `BrokerFailure` - 47 edges
10. `intent()` - 45 edges

## Surprising Connections (you probably didn't know these)
- `Providers` --uses--> `Settings`  [INFERRED]
  tests/test_health_engine.py → backend/config.py
- `FixedDateTime` --uses--> `Settings`  [INFERRED]
  tests/test_state_contract.py → backend/config.py
- `Stream` --uses--> `RuleViolation`  [INFERRED]
  tests/test_state_contract.py → backend/engine.py
- `FixedDateTime` --uses--> `Engine`  [INFERRED]
  tests/test_state_contract.py → backend/engine.py
- `Stream` --uses--> `Engine`  [INFERRED]
  tests/test_state_contract.py → backend/engine.py

## Import Cycles
- None detected.

## Communities (66 total, 7 thin omitted)

### Community 0 - "test_event_sources.py"
Cohesion: 0.12
Nodes (25): catalog(), Cells, event(), maintenance(), nyfed(), parse_events(), protocol(), HTMLParser (+17 more)

### Community 1 - "broker.py"
Cohesion: 0.24
Nodes (8): Limiter, Fixed-host Alpaca paper adapter and a separately labelled durable simulator., account_identity(), AccountLease, OwnershipError, private_owned(), Exception, Cooperative paper-account ownership for one OS user on one host.

### Community 2 - "run"
Cohesion: 0.11
Nodes (43): Failure scenarios and adversarial selection cases; all trades are synthetic., test_ambiguous_fee_is_not_assigned_to_a_strategy(), test_intraday_exit_cannot_liquidate_swing_inventory(), test_late_confirmed_asset_fee_is_idempotent_and_reconciles(), test_local_exit_survives_restart_and_unknown_response(), test_quantity_and_shared_risk_boundaries(), test_read_only_adapter_blocks_post_and_delete_before_transport(), test_readback_422_after_accepted_order_never_releases_reservation() (+35 more)

### Community 3 - "dumps"
Cohesion: 0.07
Nodes (102): at(), canonical(), cost_report(), digest(), evaluate(), main(), number(), precise() (+94 more)

### Community 4 - "utcnow"
Cohesion: 0.12
Nodes (7): No remote API. Fills are synthetic and do not model queueing/market impact., Simulator, read_context(), utcnow(), fixture, research_engine(), test_valid_context_shape_remains_available()

### Community 5 - "D"
Cohesion: 0.15
Nodes (37): D(), Assumptions, Portfolio, replay(), stress_suite(), synthetic_events(), at(), clock() (+29 more)

### Community 6 - "ui.ts"
Cohesion: 0.15
Nodes (20): AccountingBoundaries(), AccountingCosts(), AccountingGross(), AccountingRecords(), AccountingSummary(), amounts(), LearningBoundaries(), LearningInventory() (+12 more)

### Community 7 - "test_learning_engine.py"
Cohesion: 0.12
Nodes (46): digest(), encode(), evaluate(), main(), markdown(), packet_checks(), protected(), protected_windows() (+38 more)

### Community 8 - "Settings"
Cohesion: 0.12
Nodes (32): create_app(), Settings, test_api_shadow_does_not_enable_orders_and_rejects_bypass_fields(), test_local_health_inputs_are_small_read_only_and_do_not_export_account_data(), test_replay_report_is_visible_only_in_the_book_that_records_its_receipt(), test_api_boundary_validation_and_persistence(), test_live_host_configuration_rejected(), test_only_one_executor_can_own_database() (+24 more)

### Community 9 - "test_execution_pilot.py"
Cohesion: 0.17
Nodes (12): ExecutionPilot, One explicitly authorized execution experiment; never an alpha strategy. Uses…, main(), Explicit, bounded PAPER-only CLI. No web API can enable this pilot., pilot(), parametrize, test_crash_after_entry_resumes_exit_without_new_entry(), test_final_pilot_boundary_blocks_wrong_or_oversize_requests() (+4 more)

### Community 10 - "scripts"
Cohesion: 0.05
Nodes (37): @commitlint/cli, @commitlint/config-conventional, @commitlint/lint, @commitlint/load, husky, devDependencies, @commitlint/cli, @commitlint/config-conventional (+29 more)

### Community 11 - "useDashboard"
Cohesion: 0.15
Nodes (22): HealthFooterStatus(), ModeBadge(), Context, useDashboard(), Detail, EvidenceDialog(), PacketDialog(), ResearchExperiments() (+14 more)

### Community 12 - "timestamp"
Cohesion: 0.17
Nodes (18): evaluate(), floor(), Quote-only liquidity experiment. No orders, fills, positions, P&L or promotion., turnover(), walk(), Same-venue REST book/quote validation. Visible depth never guarantees a fill., _validate(), Isolated deterministic portfolio execution model. No broker or Store imports.… (+10 more)

### Community 13 - "compilerOptions"
Cohesion: 0.07
Nodes (29): compilerOptions, allowJs, checkJs, esModuleInterop, incremental, isolatedModules, jsx, lib (+21 more)

### Community 14 - "contracts.ts"
Cohesion: 0.11
Nodes (24): PortfolioCards(), SystemView(), api(), errorMessage(), empty, healthIsLive(), Snapshot, accountingSchema (+16 more)

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
Cohesion: 0.16
Nodes (23): CodexReviewer, command(), material_hash(), screen(), validate_review(), discover_crypto(), parametrize, selection_fixture() (+15 more)

### Community 17 - "test_readiness_gates.py"
Cohesion: 0.11
Nodes (25): parse_bea(), HTMLParser, Scoped BEA schedule; a date is retained without inventing an unspecified…, Schedule, Validate provider fee records without estimating missing fees or rewriting…, record_fee(), validate_activity(), validate_book() (+17 more)

### Community 18 - "motion.tsx"
Cohesion: 0.10
Nodes (18): Dialog(), AnimationProvider(), initialMode(), initialSystem(), LoadingPanel(), Mode, readMode(), readSystem() (+10 more)

### Community 19 - "health-page.tsx"
Cohesion: 0.11
Nodes (24): metadata, HealthChanges(), HealthDetails(), HealthMap(), HealthPage(), HealthSummary(), attention, inTopic() (+16 more)

### Community 20 - "liquidity_runner.py"
Cohesion: 0.18
Nodes (25): Policy, binding(), get(), get_inventory_status(), hashes(), load(), now(), observe() (+17 more)

### Community 21 - "relay.ts"
Cohesion: 0.17
Nodes (12): Context, dynamic, GET(), POST(), runtime, acceptsGzip(), compress, getPaths (+4 more)

### Community 22 - "BrokerFailure"
Cohesion: 0.26
Nodes (4): AlpacaPaper, BrokerFailure, Exception, quote()

### Community 24 - "test_experiment.py"
Cohesion: 0.16
Nodes (13): Meetings, parse_fomc(), HTMLParser, Official FOMC meeting dates, scoped context only; no complete macro calendar., context(), fomc_html(), history(), parametrize (+5 more)

### Community 25 - "datetime"
Cohesion: 0.20
Nodes (10): Retain scoped official calendar catalogs; never certify missing categories., Maintenance needs two current publisher lists. NY Fed remains partial BLS., retain_additional_scopes(), retain_scopes(), Bounded Codex CLI reviewer. Broker credentials and tools are not inherited., Credential-free local feed read; headlines remain untrusted scoped context., Point-in-time evidence screening; language models cannot override vetoes., datetime (+2 more)

### Community 27 - "experiment.py"
Cohesion: 0.15
Nodes (24): contract(), diagnose(), digest(), observe(), Frozen research contract and append-only observations. No execution interface., Retrospective price-only prefixes. Never pretend these were known earlier., register(), source_hashes() (+16 more)

### Community 28 - "devDependencies"
Cohesion: 0.04
Nodes (48): eslint, eslint-config-next, @fontsource-variable/dm-sans, @fontsource-variable/space-grotesk, dependencies, @fontsource-variable/dm-sans, @fontsource-variable/space-grotesk, motion (+40 more)

### Community 29 - "Store"
Cohesion: 0.23
Nodes (3): Store, main(), test_maintenance_empty_snapshot_304_extends_inspection_not_publication()

### Community 30 - "Engine"
Cohesion: 0.16
Nodes (4): age(), Engine, symbol_for(), book_for()

### Community 31 - "overview-page.tsx"
Cohesion: 0.16
Nodes (18): OrderDialog(), AssetBar(), ConnectionBanner(), EquityChart(), ExecutionStream(), OverviewFooter(), OverviewPage(), views (+10 more)

### Community 32 - "test_review_repairs.py"
Cohesion: 0.19
Nodes (16): daily_history(), fee(), parametrize, Locked review regressions. Synthetic brokers, patched models and tmp ledgers…, test_all_vetoed_cycle_never_calls_model(), test_diagnostic_failure_still_journals_prospective_veto(), test_distinct_lab_still_copies_or_reuses(), test_global_fee_latch_blocks_strategy_sell_with_rule_violation() (+8 more)

### Community 33 - "intelligence.py"
Cohesion: 0.12
Nodes (21): ASTRAL paper-only service., clean(), Collector, date(), named(), parse(), Independent public intelligence collector. No broker, credentials or order…, safe_url() (+13 more)

### Community 34 - "decide"
Cohesion: 0.33
Nodes (12): decide(), One-unit synthetic quote replay, with fills strictly AFTER decisions. Quote-…, replay(), test_disabled_model_keeps_deterministic_arm_in_new_observations(), event(), parametrize, test_entry_cancels_if_research_expires_during_latency(), test_entry_timing_fail_closed() (+4 more)

### Community 35 - "connection.test.ts"
Cohesion: 0.17
Nodes (8): Seed, Health, seed(), Source, dashboard(), health(), now, services()

### Community 36 - "read.ts"
Cohesion: 0.12
Nodes (19): dynamic, metadata, Page(), dynamic, metadata, Page(), AccountingContent(), LearningContent() (+11 more)

### Community 37 - "validate_pr_body.cjs"
Cohesion: 0.23
Nodes (11): fs, main(), readableText(), REQUIRED_CHECKS, REQUIRED_SECTIONS, sections(), validatePullRequestBody(), withoutComments() (+3 more)

### Community 38 - "test_risk.py"
Cohesion: 0.27
Nodes (11): inputs(), parametrize, test_account_restrictions_block(), test_bad_bars_abstain(), test_cost_hurdle_prevents_an_uneconomic_candidate(), test_exact_wilder_atr_and_repeatable_sizing(), test_intraday_budget_costs_minimum_and_cash(), test_missing_crypto_bar_rejected() (+3 more)

### Community 39 - "test_trade_history.py"
Cohesion: 0.38
Nodes (9): aggregate_daily(), aggregate(), batch(), parametrize, test_bad_trade_records_fail_closed(), test_history_shares_completed_days_and_reconstructs_each_immutable_batch(), test_missing_trade_day_is_not_filled_from_quotes(), test_provider_pagination_must_finish_before_history_is_accepted() (+1 more)

### Community 40 - "overnight_watch.py"
Cohesion: 0.25
Nodes (9): audit(), now(), Bounded overnight observation of the existing GET-only localhost paper lab., safety(), watch(), write_summary(), parametrize, test_observer_counts_lost_write_and_http_failure() (+1 more)

### Community 41 - "test_executor_ownership.py"
Cohesion: 0.22
Nodes (16): adapters(), fixture, parametrize, Account ownership through public broker methods; no real provider writes., test_changed_identity_latches_writes_even_if_the_original_identity_returns(), test_close_keeps_ownership_until_the_inflight_write_finishes(), test_closed_adapter_cannot_reacquire_authority_and_market_data_cannot_mutate(), test_different_accounts_can_write_and_read_only_observers_do_not_contend() (+8 more)

### Community 42 - "test_health_engine.py"
Cohesion: 0.25
Nodes (13): observations(), Providers, parametrize, Health contracts: temporary ledgers and HTTP fixtures; never models/brokers., report(), test_engine_health_is_separate_from_model_enablement_and_market_closure(), test_event_driven_execution_worker_is_judged_by_status_not_age(), test_local_observation_failures_do_not_reuse_healthy_state() (+5 more)

### Community 43 - "test_stage2_validation.py"
Cohesion: 0.27
Nodes (10): audit_crypto(), Read-only reconciliation analysis. Hypotheses cannot become ledger entries., Compare authoritative gross executions and positions; explain, never waive. Fee…, parametrize, Synthetic decision-path and fault tests; none are broker-paper executions., reconciliation_fixture(), test_confirmed_fee_matches_and_duplicate_activity_is_not_counted_twice(), test_duplicate_and_out_of_order_partial_readbacks_preserve_quantity() (+2 more)

### Community 44 - "price_signal"
Cohesion: 0.21
Nodes (8): price_signal(), Pure OHLC hypothesis; caller validates provenance and time separately., QCAlgorithm, as_utc(), AstralBtcSignalParity, Compare both implementations in cloud memory; export aggregate diagnostics only., Independent port of the registered BTC price hypothesis, for comparison only., validate_bar()

### Community 46 - "RuleViolation"
Cohesion: 0.35
Nodes (9): ExitPlan, Halt, Intent, ResearchBar, RiskCandidate, Exception, RuleViolation, BaseModel (+1 more)

### Community 47 - "boundaries.test.ts"
Cohesion: 0.32
Nodes (6): allowlist, files, isClient(), lines(), root, text()

### Community 48 - "seed.ts"
Cohesion: 0.23
Nodes (9): dynamic, metadata, RootLayout(), Provider(), AppFrame(), healthSchema, loadSeed(), seedScope() (+1 more)

### Community 49 - "check-skills.cjs"
Cohesion: 0.33
Nodes (6): checkSkills(), crypto, fs, hashSkillFolder(), path, ROOT

### Community 50 - "HealthEngine"
Cohesion: 0.23
Nodes (6): lifespan(), Standalone health service, separate process and ledger from telemetry/trading., state(), fresh(), HealthEngine, test_adapter_hashes_are_cached_local_and_covered_by_packet_hash()

### Community 51 - "intelligence-feed.tsx"
Cohesion: 0.27
Nodes (6): IntelligenceFeed(), SourceDialog(), IntelligenceView(), Empty(), SourceLink(), News

### Community 52 - "commitlint.config.cjs"
Cohesion: 0.83
Nodes (3): bodyMaxLineLength(), footerMaxLineLength(), maxLineLength()

### Community 53 - "app.spec.ts"
Cohesion: 0.18
Nodes (3): Dashboard, OrderIntent, diagnostics

### Community 54 - "intelligence_app.py"
Cohesion: 0.33
Nodes (6): collect(), health_inputs(), intelligence(), lifespan(), Local-only companion: independent DB and lifecycle preserve the shadow pilot., test_collection_loop_delays_after_failure_continues_and_propagates_cancel()

### Community 57 - "HealthMonitor"
Cohesion: 0.15
Nodes (9): Independent assessments from telemetry observations; no trading authority., effective(), HealthMonitor, moment(), parse_report(), HTMLParser, Public provider reports, separate from account/model connectivity and risk. No…, StatusHeading (+1 more)

### Community 58 - "test_quantconnect_validation.py"
Cohesion: 0.17
Nodes (27): bundle(), compare(), main(), new_output(), pinned_sources(), Package an in-cloud comparison or validate its aggregate-only diagnostic log., sha(), evaluate() (+19 more)

### Community 63 - "navigation.tsx"
Cohesion: 0.40
Nodes (3): NavLink(), Navigation(), pages

### Community 64 - "dogfood_session.py"
Cohesion: 0.60
Nodes (4): isolate_experiment_workers(), lab_path(), main(), Bounded, GET-only Alpaca dogfood session using a private copied ledger.

## Knowledge Gaps
- **154 isolated node(s):** `Source`, `metadata`, `dynamic`, `runtime`, `dynamic` (+149 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Store` connect `Store` to `test_event_sources.py`, `run`, `dumps`, `utcnow`, `D`, `test_learning_engine.py`, `Settings`, `test_execution_pilot.py`, `screen`, `test_readiness_gates.py`, `liquidity_runner.py`, `test_experiment.py`, `datetime`, `experiment.py`, `test_review_repairs.py`, `intelligence.py`, `test_risk.py`, `test_trade_history.py`, `test_executor_ownership.py`, `test_health_engine.py`, `RuleViolation`, `HealthEngine`, `intelligence_app.py`, `dogfood_session.py`?**
  _High betweenness centrality (0.050) - this node is a cross-community bridge._
- **Why does `utcnow()` connect `utcnow` to `test_event_sources.py`, `broker.py`, `run`, `dumps`, `Settings`, `test_execution_pilot.py`, `timestamp`, `screen`, `test_readiness_gates.py`, `BrokerFailure`, `datetime`, `experiment.py`, `Store`, `Engine`, `test_review_repairs.py`, `intelligence.py`, `test_health_engine.py`, `RuleViolation`, `HealthEngine`, `HealthMonitor`, `dogfood_session.py`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Why does `Engine` connect `Engine` to `dogfood_session.py`, `test_review_repairs.py`, `run`, `dumps`, `utcnow`, `D`, `test_risk.py`, `Settings`, `test_execution_pilot.py`, `test_stage2_validation.py`, `RuleViolation`, `screen`, `HealthEngine`, `BrokerFailure`, `test_experiment.py`, `datetime`, `experiment.py`?**
  _High betweenness centrality (0.023) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `Store` (e.g. with `ExitPlan` and `Halt`) actually correct?**
  _`Store` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `Engine` (e.g. with `ExitPlan` and `Halt`) actually correct?**
  _`Engine` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 30 inferred relationships involving `D()` (e.g. with `diagnose()` and `validate_activity()`) actually correct?**
  _`D()` has 30 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Source`, `metadata`, `dynamic` to the rest of the system?**
  _154 weakly-connected nodes found - possible documentation gaps or missing edges._