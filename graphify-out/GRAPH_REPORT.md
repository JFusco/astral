# Graph Report - astral-trading  (2026-10-27)

## Corpus Check
- 208 files · ~83,377 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1549 nodes · 4889 edges · 66 communities (58 shown, 8 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 248 edges (avg confidence: 0.7)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e20aaaba`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- timestamp
- Engine
- run
- dumps
- experiment.py
- D
- ui.ts
- test_learning_engine.py
- test_state_contract.py
- Settings
- scripts
- useDashboard
- test_executor_ownership.py
- compilerOptions
- contracts.ts
- support.cjs
- screen
- datetime
- motion.tsx
- health-page.tsx
- ValueError
- relay.ts
- test_activity_feed.py
- liquidity_runner.py
- test_experiment.py
- utcnow
- quantconnect/__init__.py
- test_stage2_validation.py
- devDependencies
- Store
- AlpacaPaper
- overview-page.tsx
- test_review_repairs.py
- engine.py
- test_activity_rollout.py
- activity_validation.py
- test_health_engine.py
- validate_pr_body.cjs
- intelligence.py
- test_execution_pilot.py
- overnight_watch.py
- decide
- HealthEngine
- navigation.tsx
- intelligence-feed.tsx
- activity_feed.py
- test_liquidity_experiment.py
- boundaries.test.ts
- Observation
- check-skills.cjs
- accounting/page.tsx
- test_risk.py
- commitlint.config.cjs
- import_ledger
- ExecutionPilot
- proxy.ts
- next.config.ts
- HealthMonitor
- test_quantconnect_validation.py
- prepare-standalone.mjs
- Connection
- intelligence_app.py
- StatusHeading

## God Nodes (most connected - your core abstractions)
1. `Store` - 103 edges
2. `utcnow()` - 93 edges
3. `run()` - 91 edges
4. `Engine` - 90 edges
5. `Settings` - 71 edges
6. `D()` - 67 edges
7. `dumps()` - 59 edges
8. `useDashboard()` - 53 edges
9. `BrokerFailure` - 51 edges
10. `AlpacaPaper` - 47 edges

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

## Communities (66 total, 8 thin omitted)

### Community 0 - "timestamp"
Cohesion: 0.10
Nodes (29): Retain scoped official calendar catalogs; never certify missing categories., Maintenance needs two current publisher lists. NY Fed remains partial BLS., retain_additional_scopes(), retain_scopes(), catalog(), Cells, event(), maintenance() (+21 more)

### Community 1 - "Engine"
Cohesion: 0.15
Nodes (4): age(), Engine, symbol_for(), book_for()

### Community 2 - "run"
Cohesion: 0.10
Nodes (48): BrokerFailure, Exception, Failure scenarios and adversarial selection cases; all trades are synthetic., test_ambiguous_fee_is_not_assigned_to_a_strategy(), test_api_shadow_does_not_enable_orders_and_rejects_bypass_fields(), test_intraday_exit_cannot_liquidate_swing_inventory(), test_late_confirmed_asset_fee_is_idempotent_and_reconciles(), test_local_exit_survives_restart_and_unknown_response() (+40 more)

### Community 3 - "dumps"
Cohesion: 0.07
Nodes (103): at(), canonical(), cost_report(), digest(), evaluate(), main(), number(), precise() (+95 more)

### Community 4 - "experiment.py"
Cohesion: 0.15
Nodes (24): contract(), diagnose(), digest(), observe(), Frozen research contract and append-only observations. No execution interface., Retrospective price-only prefixes. Never pretend these were known earlier., register(), source_hashes() (+16 more)

### Community 5 - "D"
Cohesion: 0.15
Nodes (37): D(), Assumptions, Portfolio, replay(), stress_suite(), synthetic_events(), at(), clock() (+29 more)

### Community 6 - "ui.ts"
Cohesion: 0.13
Nodes (22): StrategiesView(), StrategyCounts(), AccountingBoundaries(), AccountingCosts(), AccountingGross(), AccountingRecords(), AccountingSummary(), amounts() (+14 more)

### Community 7 - "test_learning_engine.py"
Cohesion: 0.11
Nodes (48): digest(), encode(), evaluate(), main(), markdown(), packet_checks(), protected(), protected_windows() (+40 more)

### Community 8 - "test_state_contract.py"
Cohesion: 0.18
Nodes (23): at(), build_state(), buy(), free_port(), normalize(), pin_clock(), parametrize, Dashboard read-path contract: fixed Store-seeded ledgers and a pinned clock.… (+15 more)

### Community 9 - "Settings"
Cohesion: 0.20
Nodes (16): create_app(), ExitPlan, Halt, Intent, ResearchBar, RiskCandidate, Settings, Exception (+8 more)

### Community 10 - "scripts"
Cohesion: 0.05
Nodes (37): @commitlint/cli, @commitlint/config-conventional, @commitlint/lint, @commitlint/load, husky, devDependencies, @commitlint/cli, @commitlint/config-conventional (+29 more)

### Community 11 - "useDashboard"
Cohesion: 0.14
Nodes (23): HealthFooterStatus(), ModeBadge(), OverviewFooter(), Context, useDashboard(), Detail, EvidenceDialog(), PacketDialog() (+15 more)

### Community 12 - "test_executor_ownership.py"
Cohesion: 0.22
Nodes (16): adapters(), fixture, parametrize, Account ownership through public broker methods; no real provider writes., test_changed_identity_latches_writes_even_if_the_original_identity_returns(), test_close_keeps_ownership_until_the_inflight_write_finishes(), test_closed_adapter_cannot_reacquire_authority_and_market_data_cannot_mutate(), test_different_accounts_can_write_and_read_only_observers_do_not_contend() (+8 more)

### Community 13 - "compilerOptions"
Cohesion: 0.07
Nodes (29): compilerOptions, allowJs, checkJs, esModuleInterop, incremental, isolatedModules, jsx, lib (+21 more)

### Community 14 - "contracts.ts"
Cohesion: 0.08
Nodes (27): PortfolioCards(), api(), errorMessage(), empty, healthIsLive(), Seed, Snapshot, accountingSchema (+19 more)

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

### Community 17 - "datetime"
Cohesion: 0.11
Nodes (25): parse_bea(), HTMLParser, Scoped BEA schedule; a date is retained without inventing an unspecified…, Schedule, calendar_coverage(), All scoped categories need retained, current, forward-covering evidence.…, view(), datetime (+17 more)

### Community 18 - "motion.tsx"
Cohesion: 0.12
Nodes (16): Dialog(), AnimationProvider(), initialMode(), initialSystem(), LoadingPanel(), Mode, readMode(), readSystem() (+8 more)

### Community 19 - "health-page.tsx"
Cohesion: 0.11
Nodes (25): metadata, HealthDetails(), HealthMap(), HealthPage(), HealthSummary(), attention, inTopic(), reportedNodes() (+17 more)

### Community 20 - "ValueError"
Cohesion: 0.17
Nodes (15): Validate provider fee records without estimating missing fees or rewriting…, record_fee(), validate_activity(), Isolated deterministic portfolio execution model. No broker or Store imports.…, Evidence-by-evidence readiness. No threshold changes or execution capability., floor_step(), number(), Reproducible research proposals. No network, randomness, or order side effects. (+7 more)

### Community 21 - "relay.ts"
Cohesion: 0.06
Nodes (36): Context, dynamic, GET(), POST(), runtime, dynamic, metadata, RootLayout() (+28 more)

### Community 22 - "test_activity_feed.py"
Cohesion: 0.11
Nodes (45): current_accounting(), parse_sse(), Read-only compatibility with ledgers predating the new tables., read_projection(), start_batch(), ledger_source(), The caller holds a read transaction or the Store lock across this snapshot., destinations() (+37 more)

### Community 23 - "liquidity_runner.py"
Cohesion: 0.29
Nodes (17): intelligence(), Policy, binding(), get(), get_inventory_status(), hashes(), load(), now() (+9 more)

### Community 24 - "test_experiment.py"
Cohesion: 0.15
Nodes (15): Meetings, parse_fomc(), HTMLParser, Official FOMC meeting dates, scoped context only; no complete macro calendar., evidence_for(), Credential-free local feed read; headlines remain untrusted scoped context., context(), fomc_html() (+7 more)

### Community 25 - "utcnow"
Cohesion: 0.10
Nodes (12): No remote API. Fills are synthetic and do not model queueing/market impact., Simulator, read_context(), utcnow(), isolate_experiment_workers(), lab_path(), main(), Bounded, GET-only Alpaca dogfood session using a private copied ledger. (+4 more)

### Community 27 - "test_stage2_validation.py"
Cohesion: 0.27
Nodes (10): audit_crypto(), Read-only reconciliation analysis. Hypotheses cannot become ledger entries., Compare authoritative gross executions and positions; explain, never waive. Fee…, parametrize, Synthetic decision-path and fault tests; none are broker-paper executions., reconciliation_fixture(), test_confirmed_fee_matches_and_duplicate_activity_is_not_counted_twice(), test_duplicate_and_out_of_order_partial_readbacks_preserve_quantity() (+2 more)

### Community 28 - "devDependencies"
Cohesion: 0.04
Nodes (48): eslint, eslint-config-next, @fontsource-variable/dm-sans, @fontsource-variable/space-grotesk, dependencies, @fontsource-variable/dm-sans, @fontsource-variable/space-grotesk, motion (+40 more)

### Community 29 - "Store"
Cohesion: 0.23
Nodes (4): Store, parametrize, test_unexpected_source_failure_keeps_other_feed_alive_and_recovers(), test_replay_report_is_visible_only_in_the_book_that_records_its_receipt()

### Community 30 - "AlpacaPaper"
Cohesion: 0.10
Nodes (16): AlpacaPaper, Limiter, account_identity(), AccountLease, OwnershipError, private_owned(), Exception, Cooperative paper-account ownership for one OS user on one host. (+8 more)

### Community 31 - "overview-page.tsx"
Cohesion: 0.14
Nodes (20): HealthChanges(), OrderDialog(), AssetBar(), EquityChart(), ExecutionStream(), OverviewPage(), views, PositionsPanel() (+12 more)

### Community 32 - "test_review_repairs.py"
Cohesion: 0.19
Nodes (16): daily_history(), fee(), parametrize, Locked review regressions. Synthetic brokers, patched models and tmp ledgers…, test_adapter_hashes_are_cached_local_and_covered_by_packet_hash(), test_all_vetoed_cycle_never_calls_model(), test_diagnostic_failure_still_journals_prospective_veto(), test_distinct_lab_still_copies_or_reuses() (+8 more)

### Community 33 - "engine.py"
Cohesion: 0.27
Nodes (5): Fixed-host Alpaca paper adapter and a separately labelled durable simulator., One explicitly authorized execution experiment; never an alpha strategy. Uses…, Point-in-time evidence screening; language models cannot override vetoes., Explicit, bounded PAPER-only CLI. No web API can enable this pilot., One bounded GET-only research cycle on the existing paper ledger. No model.

### Community 34 - "test_activity_rollout.py"
Cohesion: 0.14
Nodes (28): Bounded observation of existing accounting, independent of trading readiness., activated_settings(), check_ledger(), ledger_bytes(), main(), prepare(), PreparedRollout, Read-only rollout preflight; activation requires a separate explicit invocation. (+20 more)

### Community 35 - "activity_validation.py"
Cohesion: 0.20
Nodes (23): publish_projection(), balances_match(), canonical(), digest(), input_digest(), instant(), load_mapping(), number() (+15 more)

### Community 36 - "test_health_engine.py"
Cohesion: 0.23
Nodes (13): parse_report(), observations(), parametrize, Health contracts: temporary ledgers and HTTP fixtures; never models/brokers., report(), test_engine_health_is_separate_from_model_enablement_and_market_closure(), test_event_driven_execution_worker_is_judged_by_status_not_age(), test_local_observation_failures_do_not_reuse_healthy_state() (+5 more)

### Community 37 - "validate_pr_body.cjs"
Cohesion: 0.23
Nodes (11): fs, main(), readableText(), REQUIRED_CHECKS, REQUIRED_SECTIONS, sections(), validatePullRequestBody(), withoutComments() (+3 more)

### Community 38 - "intelligence.py"
Cohesion: 0.13
Nodes (19): ASTRAL paper-only service., clean(), Collector, date(), named(), parse(), Independent public intelligence collector. No broker, credentials or order…, safe_url() (+11 more)

### Community 39 - "test_execution_pilot.py"
Cohesion: 0.27
Nodes (10): pilot(), parametrize, test_crash_after_entry_resumes_exit_without_new_entry(), test_final_pilot_boundary_blocks_wrong_or_oversize_requests(), test_pilot_and_strategy_workers_cannot_share_authority(), test_pilot_recovers_lost_accepted_entry_without_duplicate(), test_pilot_refuses_existing_positions(), test_synthetic_round_trip_and_completed_resume_do_not_buy_twice() (+2 more)

### Community 40 - "overnight_watch.py"
Cohesion: 0.25
Nodes (9): audit(), now(), Bounded overnight observation of the existing GET-only localhost paper lab., safety(), watch(), write_summary(), parametrize, test_observer_counts_lost_write_and_http_failure() (+1 more)

### Community 41 - "decide"
Cohesion: 0.33
Nodes (12): decide(), One-unit synthetic quote replay, with fills strictly AFTER decisions. Quote-…, replay(), test_disabled_model_keeps_deterministic_arm_in_new_observations(), event(), parametrize, test_entry_cancels_if_research_expires_during_latency(), test_entry_timing_fail_closed() (+4 more)

### Community 42 - "HealthEngine"
Cohesion: 0.17
Nodes (10): lifespan(), Standalone health service, separate process and ledger from telemetry/trading., state(), fresh(), HealthEngine, Independent assessments from telemetry observations; no trading authority., effective(), moment() (+2 more)

### Community 43 - "navigation.tsx"
Cohesion: 0.40
Nodes (3): NavLink(), Navigation(), pages

### Community 44 - "intelligence-feed.tsx"
Cohesion: 0.33
Nodes (5): IntelligenceFeed(), SourceDialog(), IntelligenceView(), SourceLink(), News

### Community 45 - "activity_feed.py"
Cohesion: 0.16
Nodes (17): activity_identifier(), collect_batch(), FeedError, main(), Bounded paper activity acquisition and immutable evidence publication., Use the adapter's authentication, process boundary and request budget., Commit even rejected records before publishing or raising their failure., Incremental SSE framing; raw acquisition bytes are retained separately. (+9 more)

### Community 46 - "test_liquidity_experiment.py"
Cohesion: 0.23
Nodes (15): evaluate(), floor(), Quote-only liquidity experiment. No orders, fills, positions, P&L or promotion., turnover(), walk(), Same-venue REST book/quote validation. Visible depth never guarantees a fill., _validate(), validate_book() (+7 more)

### Community 47 - "boundaries.test.ts"
Cohesion: 0.32
Nodes (6): allowlist, files, isClient(), lines(), root, text()

### Community 48 - "Observation"
Cohesion: 0.20
Nodes (4): Latency, Observation, Sample current availability without treating it as collection success., Fixed-size histogram retains every observation without per-request rows.

### Community 49 - "check-skills.cjs"
Cohesion: 0.33
Nodes (6): checkSkills(), crypto, fs, hashSkillFolder(), path, ROOT

### Community 50 - "accounting/page.tsx"
Cohesion: 0.15
Nodes (12): dynamic, metadata, Page(), dynamic, metadata, Page(), AccountingContent(), LearningContent() (+4 more)

### Community 51 - "test_risk.py"
Cohesion: 0.32
Nodes (12): propose(), ATR14 + trend/breakout candidate and fixed fractional loss-budget sizing. All…, test_prefix_diagnostic_reuses_live_math_and_never_assumes_fills(), inputs(), parametrize, test_account_restrictions_block(), test_bad_bars_abstain(), test_cost_hurdle_prevents_an_uneconomic_candidate() (+4 more)

### Community 52 - "commitlint.config.cjs"
Cohesion: 0.83
Nodes (3): bodyMaxLineLength(), footerMaxLineLength(), maxLineLength()

### Community 53 - "import_ledger"
Cohesion: 0.22
Nodes (9): import_ledger(), Copy captured rows into a new disposable Store, leaving source bytes alone., document(), fixture, setup(), test_fixture_mapping_and_missing_originals_cannot_satisfy_private_acceptance(), test_selected_capture_file_must_match_the_mapping_source_role(), fixture (+1 more)

### Community 58 - "test_quantconnect_validation.py"
Cohesion: 0.11
Nodes (35): price_signal(), Pure OHLC hypothesis; caller validates provenance and time separately., QCAlgorithm, as_utc(), AstralBtcSignalParity, Compare both implementations in cloud memory; export aggregate diagnostics only., bundle(), compare() (+27 more)

### Community 64 - "intelligence_app.py"
Cohesion: 0.33
Nodes (5): collect(), health_inputs(), lifespan(), Local-only companion: independent DB and lifecycle preserve the shadow pilot., test_collection_loop_delays_after_failure_continues_and_propagates_cancel()

## Knowledge Gaps
- **154 isolated node(s):** `Source`, `metadata`, `dynamic`, `runtime`, `dynamic` (+149 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Store` connect `Store` to `timestamp`, `run`, `dumps`, `experiment.py`, `D`, `test_learning_engine.py`, `test_state_contract.py`, `Settings`, `test_executor_ownership.py`, `screen`, `datetime`, `ValueError`, `test_activity_feed.py`, `test_experiment.py`, `utcnow`, `AlpacaPaper`, `test_review_repairs.py`, `engine.py`, `test_activity_rollout.py`, `activity_validation.py`, `test_health_engine.py`, `intelligence.py`, `test_execution_pilot.py`, `HealthEngine`, `test_liquidity_experiment.py`, `import_ledger`, `HealthMonitor`, `intelligence_app.py`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Why does `utcnow()` connect `utcnow` to `timestamp`, `Engine`, `run`, `dumps`, `experiment.py`, `Settings`, `screen`, `datetime`, `ValueError`, `test_activity_feed.py`, `test_experiment.py`, `Store`, `AlpacaPaper`, `test_review_repairs.py`, `engine.py`, `test_activity_rollout.py`, `activity_validation.py`, `test_health_engine.py`, `intelligence.py`, `HealthEngine`, `activity_feed.py`, `Observation`, `ExecutionPilot`, `HealthMonitor`?**
  _High betweenness centrality (0.033) - this node is a cross-community bridge._
- **Why does `Engine` connect `Engine` to `run`, `dumps`, `experiment.py`, `D`, `test_state_contract.py`, `Settings`, `screen`, `ValueError`, `test_activity_feed.py`, `test_experiment.py`, `utcnow`, `test_stage2_validation.py`, `Store`, `AlpacaPaper`, `test_review_repairs.py`, `engine.py`, `test_activity_rollout.py`, `test_execution_pilot.py`, `activity_feed.py`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `Store` (e.g. with `ExitPlan` and `Halt`) actually correct?**
  _`Store` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 97 inferred relationships involving `ValueError` (e.g. with `at()` and `cost_report()`) actually correct?**
  _`ValueError` has 97 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `Engine` (e.g. with `ExitPlan` and `Halt`) actually correct?**
  _`Engine` has 12 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Source`, `metadata`, `dynamic` to the rest of the system?**
  _154 weakly-connected nodes found - possible documentation gaps or missing edges._