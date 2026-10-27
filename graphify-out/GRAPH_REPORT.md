# Graph Report - astral-trading  (2026-10-27)

## Corpus Check
- 210 files · ~84,843 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1571 nodes · 5017 edges · 66 communities (58 shown, 8 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 255 edges (avg confidence: 0.7)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `3248aaa7`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- datetime
- Engine
- run
- dumps
- experiment.py
- D
- ui.ts
- test_learning_engine.py
- test_state_contract.py
- test_execution_pilot.py
- scripts
- research-lab.tsx
- test_executor_ownership.py
- compilerOptions
- contracts.ts
- support.cjs
- screen
- test_readiness_gates.py
- motion.tsx
- health-view-state.tsx
- engine.py
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
- useDashboard
- store.py
- app-frame.tsx
- test_activity_rollout.py
- test_review_repairs.py
- Schedule
- validate_pr_body.cjs
- intelligence.py
- Settings
- overnight_watch.py
- decide
- test_health_engine.py
- navigation.tsx
- Cells
- BrokerFailure
- ValueError
- boundaries.test.ts
- OwnershipError
- check-skills.cjs
- StatusHeading
- HealthEngine
- commitlint.config.cjs
- test_trade_history.py
- Meetings
- proxy.ts
- next.config.ts
- test_liquidity_experiment.py
- test_quantconnect_validation.py
- prepare-standalone.mjs
- Connection
- Source
- source-dialog.tsx

## God Nodes (most connected - your core abstractions)
1. `Store` - 109 edges
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

## Communities (66 total, 8 thin omitted)

### Community 0 - "datetime"
Cohesion: 0.11
Nodes (33): Retain scoped official calendar catalogs; never certify missing categories., Maintenance needs two current publisher lists. NY Fed remains partial BLS., retain_additional_scopes(), retain_scopes(), catalog(), event(), maintenance(), nyfed() (+25 more)

### Community 1 - "Engine"
Cohesion: 0.15
Nodes (4): age(), Engine, symbol_for(), book_for()

### Community 2 - "run"
Cohesion: 0.14
Nodes (36): Failure scenarios and adversarial selection cases; all trades are synthetic., test_ambiguous_fee_is_not_assigned_to_a_strategy(), test_api_shadow_does_not_enable_orders_and_rejects_bypass_fields(), test_intraday_exit_cannot_liquidate_swing_inventory(), test_late_confirmed_asset_fee_is_idempotent_and_reconciles(), test_local_exit_survives_restart_and_unknown_response(), test_quantity_and_shared_risk_boundaries(), test_readback_422_after_accepted_order_never_releases_reservation() (+28 more)

### Community 3 - "dumps"
Cohesion: 0.06
Nodes (106): at(), canonical(), cost_report(), digest(), evaluate(), main(), number(), precise() (+98 more)

### Community 4 - "experiment.py"
Cohesion: 0.27
Nodes (11): contract(), observe(), Frozen research contract and append-only observations. No execution interface., register(), source_hashes(), state(), main(), Register once; run offline diagnostic from an existing read-only history DB.… (+3 more)

### Community 5 - "D"
Cohesion: 0.15
Nodes (37): D(), Assumptions, Portfolio, replay(), stress_suite(), synthetic_events(), at(), clock() (+29 more)

### Community 6 - "ui.ts"
Cohesion: 0.12
Nodes (25): metadata, HealthChanges(), HealthPage(), AccountingBoundaries(), AccountingCosts(), AccountingGross(), AccountingRecords(), AccountingSummary() (+17 more)

### Community 7 - "test_learning_engine.py"
Cohesion: 0.11
Nodes (48): digest(), encode(), evaluate(), main(), markdown(), packet_checks(), protected(), protected_windows() (+40 more)

### Community 8 - "test_state_contract.py"
Cohesion: 0.18
Nodes (23): at(), build_state(), buy(), free_port(), normalize(), pin_clock(), parametrize, Dashboard read-path contract: fixed Store-seeded ledgers and a pinned clock.… (+15 more)

### Community 9 - "test_execution_pilot.py"
Cohesion: 0.24
Nodes (9): ExecutionPilot, pilot(), parametrize, test_crash_after_entry_resumes_exit_without_new_entry(), test_final_pilot_boundary_blocks_wrong_or_oversize_requests(), test_pilot_and_strategy_workers_cannot_share_authority(), test_pilot_recovers_lost_accepted_entry_without_duplicate(), test_pilot_refuses_existing_positions() (+1 more)

### Community 10 - "scripts"
Cohesion: 0.05
Nodes (37): @commitlint/cli, @commitlint/config-conventional, @commitlint/lint, @commitlint/load, husky, devDependencies, @commitlint/cli, @commitlint/config-conventional (+29 more)

### Community 11 - "research-lab.tsx"
Cohesion: 0.25
Nodes (12): Detail, EvidenceDialog(), PacketDialog(), ResearchExperiments(), ResearchGates(), ResearchStatus(), ShadowDecisions(), TimingDecisions() (+4 more)

### Community 12 - "test_executor_ownership.py"
Cohesion: 0.22
Nodes (16): adapters(), fixture, parametrize, Account ownership through public broker methods; no real provider writes., test_changed_identity_latches_writes_even_if_the_original_identity_returns(), test_close_keeps_ownership_until_the_inflight_write_finishes(), test_closed_adapter_cannot_reacquire_authority_and_market_data_cannot_mutate(), test_different_accounts_can_write_and_read_only_observers_do_not_contend() (+8 more)

### Community 13 - "compilerOptions"
Cohesion: 0.07
Nodes (29): compilerOptions, allowJs, checkJs, esModuleInterop, incremental, isolatedModules, jsx, lib (+21 more)

### Community 14 - "contracts.ts"
Cohesion: 0.06
Nodes (41): dynamic, metadata, Page(), RootLayout(), OrderDialog(), AccountingContent(), ReportFrame(), api() (+33 more)

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
Cohesion: 0.23
Nodes (14): bea_html(), book(), fee(), parametrize, quote(), test_adequate_daily_volume_cannot_override_a_subminimum_depth_cap(), test_bea_dates_preserve_clock_text_without_inventing_release_timezone(), test_book_normalization_fails_closed() (+6 more)

### Community 18 - "motion.tsx"
Cohesion: 0.13
Nodes (17): Dialog(), HealthSummary(), Heartbeat(), AnimationProvider(), initialMode(), initialSystem(), LoadingPanel(), Mode (+9 more)

### Community 19 - "health-view-state.tsx"
Cohesion: 0.15
Nodes (19): HealthDetails(), HealthMap(), attention, inTopic(), reportedNodes(), shown(), Context, HealthViewState() (+11 more)

### Community 20 - "engine.py"
Cohesion: 0.32
Nodes (10): build_report(), code_hashes(), connect_readonly(), export_events(), Read-only ledger export, fixed future window and offline stress receipts. No…, register_holdout(), report_state(), summary() (+2 more)

### Community 21 - "relay.ts"
Cohesion: 0.08
Nodes (28): Context, dynamic, GET(), POST(), runtime, dynamic, metadata, Page() (+20 more)

### Community 22 - "test_activity_feed.py"
Cohesion: 0.05
Nodes (108): activity_identifier(), collect_batch(), current_accounting(), FeedError, main(), parse_sse(), publish_projection(), Bounded paper activity acquisition and immutable evidence publication. (+100 more)

### Community 23 - "liquidity_runner.py"
Cohesion: 0.28
Nodes (19): digest(), Policy, binding(), get(), get_inventory_status(), hashes(), load(), now() (+11 more)

### Community 24 - "test_experiment.py"
Cohesion: 0.13
Nodes (26): diagnose(), Retrospective price-only prefixes. Never pretend these were known earlier., propose(), ATR14 + trend/breakout candidate and fixed fractional loss-budget sizing. All…, context(), fomc_html(), history(), parametrize (+18 more)

### Community 25 - "utcnow"
Cohesion: 0.16
Nodes (5): No remote API. Fills are synthetic and do not model queueing/market impact., Simulator, read_context(), utcnow(), test_valid_context_shape_remains_available()

### Community 27 - "test_stage2_validation.py"
Cohesion: 0.20
Nodes (13): audit_crypto(), Read-only reconciliation analysis. Hypotheses cannot become ledger entries., Compare authoritative gross executions and positions; explain, never waive. Fee…, parametrize, Synthetic decision-path and fault tests; none are broker-paper executions., reconciliation_fixture(), test_confirmed_fee_matches_and_duplicate_activity_is_not_counted_twice(), test_downstream_candidate_is_visible_but_inventory_still_vetoes() (+5 more)

### Community 28 - "devDependencies"
Cohesion: 0.04
Nodes (48): eslint, eslint-config-next, @fontsource-variable/dm-sans, @fontsource-variable/space-grotesk, dependencies, @fontsource-variable/dm-sans, @fontsource-variable/space-grotesk, motion (+40 more)

### Community 29 - "Store"
Cohesion: 0.12
Nodes (17): collect(), health_inputs(), intelligence(), lifespan(), Local-only companion: independent DB and lifecycle preserve the shadow pilot., Collector, Store, test_maintenance_empty_snapshot_304_extends_inspection_not_publication() (+9 more)

### Community 31 - "useDashboard"
Cohesion: 0.10
Nodes (33): HealthFooterStatus(), items, MarketUniverse(), AssetBar(), ConnectionBanner(), EquityChart(), ExecutionStream(), IntelligenceFeed() (+25 more)

### Community 32 - "store.py"
Cohesion: 0.13
Nodes (14): Fixed-host Alpaca paper adapter and a separately labelled durable simulator., account_identity(), Cooperative paper-account ownership for one OS user on one host., One explicitly authorized execution experiment; never an alpha strategy. Uses…, isolate_experiment_workers(), lab_path(), main(), Bounded, GET-only Alpaca dogfood session using a private copied ledger. (+6 more)

### Community 33 - "app-frame.tsx"
Cohesion: 0.21
Nodes (7): dynamic, metadata, Provider(), AppFrame(), Clock(), HaltButton(), OpeningPanels()

### Community 34 - "test_activity_rollout.py"
Cohesion: 0.08
Nodes (36): Latency, Observation, Fixed-size histogram retains every observation without per-request rows., Sample current availability without treating it as collection success., activated_settings(), check_ledger(), ledger_bytes(), main() (+28 more)

### Community 35 - "test_review_repairs.py"
Cohesion: 0.19
Nodes (16): daily_history(), fee(), parametrize, Locked review regressions. Synthetic brokers, patched models and tmp ledgers…, test_all_vetoed_cycle_never_calls_model(), test_diagnostic_failure_still_journals_prospective_veto(), test_distinct_lab_still_copies_or_reuses(), test_global_fee_latch_blocks_strategy_sell_with_rule_violation() (+8 more)

### Community 36 - "Schedule"
Cohesion: 0.25
Nodes (3): HTMLParser, Scoped BEA schedule; a date is retained without inventing an unspecified…, Schedule

### Community 37 - "validate_pr_body.cjs"
Cohesion: 0.23
Nodes (11): fs, main(), readableText(), REQUIRED_CHECKS, REQUIRED_SECTIONS, sections(), validatePullRequestBody(), withoutComments() (+3 more)

### Community 38 - "intelligence.py"
Cohesion: 0.16
Nodes (15): parse_bea(), parse_fomc(), ASTRAL paper-only service., clean(), date(), named(), parse(), Independent public intelligence collector. No broker, credentials or order… (+7 more)

### Community 39 - "Settings"
Cohesion: 0.16
Nodes (13): create_app(), Settings, test_read_only_adapter_blocks_post_and_delete_before_transport(), test_shadow_cannot_submit_even_with_repeated_approvals(), test_connected_research_refreshes_after_history_and_never_writes_orders(), test_local_health_inputs_are_small_read_only_and_do_not_export_account_data(), fixture, research_engine() (+5 more)

### Community 40 - "overnight_watch.py"
Cohesion: 0.25
Nodes (9): audit(), now(), Bounded overnight observation of the existing GET-only localhost paper lab., safety(), watch(), write_summary(), parametrize, test_observer_counts_lost_write_and_http_failure() (+1 more)

### Community 41 - "decide"
Cohesion: 0.38
Nodes (11): decide(), One-unit synthetic quote replay, with fills strictly AFTER decisions. Quote-…, replay(), event(), parametrize, test_entry_cancels_if_research_expires_during_latency(), test_entry_timing_fail_closed(), test_exit_rules_work_without_entry_permission() (+3 more)

### Community 42 - "test_health_engine.py"
Cohesion: 0.14
Nodes (20): Independent assessments from telemetry observations; no trading authority., effective(), HealthMonitor, moment(), parse_report(), Public provider reports, separate from account/model connectivity and risk. No…, observations(), Providers (+12 more)

### Community 43 - "navigation.tsx"
Cohesion: 0.40
Nodes (3): NavLink(), Navigation(), pages

### Community 44 - "Cells"
Cohesion: 0.29
Nodes (3): Cells, HTMLParser, Retain cells in a selected table, including links and their following text.

### Community 45 - "BrokerFailure"
Cohesion: 0.35
Nodes (11): ExitPlan, Halt, Intent, ResearchBar, RiskCandidate, BrokerFailure, Exception, Exception (+3 more)

### Community 46 - "ValueError"
Cohesion: 0.18
Nodes (21): evaluate(), floor(), Quote-only liquidity experiment. No orders, fills, positions, P&L or promotion., turnover(), walk(), Same-venue REST book/quote validation. Visible depth never guarantees a fill., _validate(), validate_book() (+13 more)

### Community 47 - "boundaries.test.ts"
Cohesion: 0.32
Nodes (6): allowlist, files, isClient(), lines(), root, text()

### Community 48 - "OwnershipError"
Cohesion: 0.27
Nodes (5): Limiter, AccountLease, OwnershipError, private_owned(), Exception

### Community 49 - "check-skills.cjs"
Cohesion: 0.33
Nodes (6): checkSkills(), crypto, fs, hashSkillFolder(), path, ROOT

### Community 51 - "HealthEngine"
Cohesion: 0.23
Nodes (6): lifespan(), Standalone health service, separate process and ledger from telemetry/trading., state(), fresh(), HealthEngine, test_adapter_hashes_are_cached_local_and_covered_by_packet_hash()

### Community 52 - "commitlint.config.cjs"
Cohesion: 0.83
Nodes (3): bodyMaxLineLength(), footerMaxLineLength(), maxLineLength()

### Community 53 - "test_trade_history.py"
Cohesion: 0.39
Nodes (8): aggregate(), batch(), parametrize, test_bad_trade_records_fail_closed(), test_history_shares_completed_days_and_reconstructs_each_immutable_batch(), test_missing_trade_day_is_not_filled_from_quotes(), test_provider_pagination_must_finish_before_history_is_accepted(), test_trade_only_bars_deduplicate_and_exclude_incomplete_day()

### Community 54 - "Meetings"
Cohesion: 0.25
Nodes (3): Meetings, HTMLParser, Official FOMC meeting dates, scoped context only; no complete macro calendar.

### Community 57 - "test_liquidity_experiment.py"
Cohesion: 0.43
Nodes (7): append(), inputs(), parametrize, seed(), test_baseline_rejects_while_separate_half_depth_model_can_cover_25(), test_corrupt_stale_and_unverified_evidence_does_not_become_liquidity_pass(), test_daily_turnover_cap_and_fee_reduced_exit_minimum_are_binding()

### Community 58 - "test_quantconnect_validation.py"
Cohesion: 0.11
Nodes (35): price_signal(), Pure OHLC hypothesis; caller validates provenance and time separately., QCAlgorithm, as_utc(), AstralBtcSignalParity, Compare both implementations in cloud memory; export aggregate diagnostics only., bundle(), compare() (+27 more)

### Community 65 - "source-dialog.tsx"
Cohesion: 0.47
Nodes (3): SourceDialog(), SourceLink(), News

## Knowledge Gaps
- **154 isolated node(s):** `Source`, `metadata`, `dynamic`, `runtime`, `dynamic` (+149 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Store` connect `Store` to `datetime`, `run`, `dumps`, `experiment.py`, `D`, `test_learning_engine.py`, `test_state_contract.py`, `test_executor_ownership.py`, `screen`, `test_readiness_gates.py`, `test_activity_feed.py`, `liquidity_runner.py`, `test_experiment.py`, `store.py`, `test_activity_rollout.py`, `test_review_repairs.py`, `Settings`, `test_health_engine.py`, `BrokerFailure`, `HealthEngine`, `test_trade_history.py`, `test_liquidity_experiment.py`?**
  _High betweenness centrality (0.077) - this node is a cross-community bridge._
- **Why does `utcnow()` connect `utcnow` to `datetime`, `Engine`, `run`, `dumps`, `experiment.py`, `test_execution_pilot.py`, `screen`, `test_readiness_gates.py`, `engine.py`, `test_activity_feed.py`, `Store`, `AlpacaPaper`, `store.py`, `test_activity_rollout.py`, `test_review_repairs.py`, `intelligence.py`, `Settings`, `test_health_engine.py`, `BrokerFailure`, `ValueError`, `HealthEngine`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Why does `Engine` connect `Engine` to `run`, `dumps`, `experiment.py`, `D`, `test_state_contract.py`, `test_execution_pilot.py`, `screen`, `engine.py`, `test_activity_feed.py`, `test_experiment.py`, `utcnow`, `test_stage2_validation.py`, `Store`, `AlpacaPaper`, `store.py`, `test_activity_rollout.py`, `test_review_repairs.py`, `Settings`, `BrokerFailure`, `HealthEngine`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `Store` (e.g. with `ExitPlan` and `Halt`) actually correct?**
  _`Store` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 102 inferred relationships involving `ValueError` (e.g. with `at()` and `cost_report()`) actually correct?**
  _`ValueError` has 102 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `Engine` (e.g. with `ExitPlan` and `Halt`) actually correct?**
  _`Engine` has 12 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Source`, `metadata`, `dynamic` to the rest of the system?**
  _154 weakly-connected nodes found - possible documentation gaps or missing edges._