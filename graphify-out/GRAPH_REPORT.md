# Graph Report - astral-trading  (2026-10-27)

## Corpus Check
- 210 files · ~86,302 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1582 nodes · 5087 edges · 59 communities (54 shown, 5 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 255 edges (avg confidence: 0.7)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `28388285`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_event_sources.py
- Engine
- run
- dumps
- accounting-content.tsx
- D
- ui.ts
- test_learning_engine.py
- test_state_contract.py
- app-frame.tsx
- scripts
- useDashboard
- test_executor_ownership.py
- compilerOptions
- contracts.ts
- support.cjs
- screen
- test_readiness_gates.py
- motion.tsx
- health-view-state.tsx
- packet-dialog.tsx
- relay.ts
- test_activity_feed.py
- ValueError
- Meetings
- activity_validation.py
- quantconnect/__init__.py
- datetime
- devDependencies
- intelligence.py
- Settings
- asset-bar.tsx
- utcnow
- test_health_engine.py
- test_activity_rollout.py
- test_risk.py
- HealthEngine
- validate_pr_body.cjs
- test_evidence_storage.py
- Store
- test_trade_history.py
- activity_feed.py
- HealthMonitor
- navigation.tsx
- parametrize
- test_dogfood.py
- decide
- boundaries.test.ts
- overnight_watch.py
- check-skills.cjs
- test_stage2_validation.py
- document
- commitlint.config.cjs
- proxy.ts
- next.config.ts
- prepare-standalone.mjs

## God Nodes (most connected - your core abstractions)
1. `Store` - 111 edges
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
- `FixedDateTime` --uses--> `RuleViolation`  [INFERRED]
  tests/test_state_contract.py → backend/engine.py
- `Stream` --uses--> `RuleViolation`  [INFERRED]
  tests/test_state_contract.py → backend/engine.py

## Import Cycles
- None detected.

## Communities (59 total, 5 thin omitted)

### Community 0 - "test_event_sources.py"
Cohesion: 0.10
Nodes (29): Retain scoped official calendar catalogs; never certify missing categories., Maintenance needs two current publisher lists. NY Fed remains partial BLS., retain_additional_scopes(), retain_scopes(), catalog(), Cells, event(), maintenance() (+21 more)

### Community 1 - "Engine"
Cohesion: 0.05
Nodes (32): ExitPlan, Halt, Intent, ResearchBar, RiskCandidate, AlpacaPaper, BrokerFailure, Limiter (+24 more)

### Community 2 - "run"
Cohesion: 0.14
Nodes (25): test_all_vetoed_cycle_never_calls_model(), test_new_invalid_fee_is_never_applied(), parametrize, run(), test_accepted_timeout_recovered_without_second_post(), test_adapter_fixed_hosts_no_post_retries_and_cooldown(), test_alpaca_state_account_fields_match_dashboard_number_contract(), test_concurrent_duplicate_intent_submits_once() (+17 more)

### Community 3 - "dumps"
Cohesion: 0.06
Nodes (112): at(), canonical(), cost_report(), digest(), evaluate(), main(), number(), precise() (+104 more)

### Community 4 - "accounting-content.tsx"
Cohesion: 0.19
Nodes (12): dynamic, metadata, Page(), AccountingBoundaries(), AccountingContent(), AccountingCosts(), AccountingGross(), AccountingRecords() (+4 more)

### Community 5 - "D"
Cohesion: 0.11
Nodes (47): D(), Assumptions, Portfolio, replay(), build_report(), code_hashes(), connect_readonly(), export_events() (+39 more)

### Community 6 - "ui.ts"
Cohesion: 0.11
Nodes (23): metadata, dynamic, metadata, Page(), HealthChanges(), HealthPage(), LearningBoundaries(), LearningContent() (+15 more)

### Community 7 - "test_learning_engine.py"
Cohesion: 0.15
Nodes (39): digest(), encode(), evaluate(), main(), markdown(), packet_checks(), protected(), protected_windows() (+31 more)

### Community 8 - "test_state_contract.py"
Cohesion: 0.16
Nodes (23): at(), build_state(), buy(), FixedDateTime, free_port(), normalize(), pin_clock(), parametrize (+15 more)

### Community 9 - "app-frame.tsx"
Cohesion: 0.21
Nodes (7): dynamic, metadata, Provider(), AppFrame(), Clock(), HaltButton(), OpeningPanels()

### Community 10 - "scripts"
Cohesion: 0.05
Nodes (37): @commitlint/cli, @commitlint/config-conventional, @commitlint/lint, @commitlint/load, husky, devDependencies, @commitlint/cli, @commitlint/config-conventional (+29 more)

### Community 11 - "useDashboard"
Cohesion: 0.12
Nodes (31): HealthFooterStatus(), EquityChart(), ExecutionStream(), ModeBadge(), OverviewFooter(), OverviewPage(), views, PortfolioCards() (+23 more)

### Community 12 - "test_executor_ownership.py"
Cohesion: 0.22
Nodes (16): adapters(), fixture, parametrize, Account ownership through public broker methods; no real provider writes., test_changed_identity_latches_writes_even_if_the_original_identity_returns(), test_close_keeps_ownership_until_the_inflight_write_finishes(), test_closed_adapter_cannot_reacquire_authority_and_market_data_cannot_mutate(), test_different_accounts_can_write_and_read_only_observers_do_not_contend() (+8 more)

### Community 13 - "compilerOptions"
Cohesion: 0.07
Nodes (29): compilerOptions, allowJs, checkJs, esModuleInterop, incremental, isolatedModules, jsx, lib (+21 more)

### Community 14 - "contracts.ts"
Cohesion: 0.08
Nodes (26): OrderDialog(), SystemView(), api(), errorMessage(), empty, quoteIsFresh(), Snapshot, amount (+18 more)

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
Cohesion: 0.14
Nodes (25): CodexReviewer, command(), material_hash(), Bounded Codex CLI reviewer. Broker credentials and tools are not inherited., screen(), validate_review(), discover_crypto(), Read-only venue discovery. A listing is never execution authorization. (+17 more)

### Community 17 - "test_readiness_gates.py"
Cohesion: 0.12
Nodes (21): parse_bea(), HTMLParser, Scoped BEA schedule; a date is retained without inventing an unspecified…, Schedule, Validate provider fee records without estimating missing fees or rewriting…, record_fee(), validate_activity(), calendar_coverage() (+13 more)

### Community 18 - "motion.tsx"
Cohesion: 0.14
Nodes (16): HealthSummary(), Heartbeat(), AnimationProvider(), initialMode(), initialSystem(), LoadingPanel(), Mode, readMode() (+8 more)

### Community 19 - "health-view-state.tsx"
Cohesion: 0.13
Nodes (21): HealthDetails(), HealthMap(), attention, inTopic(), reportedNodes(), shown(), Context, HealthViewState() (+13 more)

### Community 20 - "packet-dialog.tsx"
Cohesion: 0.20
Nodes (10): Dialog(), IntelligenceFeed(), SourceDialog(), ViewDialog(), Detail, EvidenceDialog(), Evidence(), SourceLink() (+2 more)

### Community 21 - "relay.ts"
Cohesion: 0.05
Nodes (35): Context, dynamic, GET(), POST(), runtime, RootLayout(), Connection, Seed (+27 more)

### Community 22 - "test_activity_feed.py"
Cohesion: 0.10
Nodes (43): parse_sse(), start_batch(), ledger_source(), The caller holds a read transaction or the Store lock across this snapshot., destinations(), controlled_current(), pure(), parametrize (+35 more)

### Community 23 - "ValueError"
Cohesion: 0.05
Nodes (86): contract(), diagnose(), digest(), observe(), Frozen research contract and append-only observations. No execution interface., Retrospective price-only prefixes. Never pretend these were known earlier., register(), source_hashes() (+78 more)

### Community 25 - "activity_validation.py"
Cohesion: 0.18
Nodes (26): publish_projection(), balances_match(), canonical(), digest(), input_digest(), instant(), load_mapping(), number() (+18 more)

### Community 27 - "datetime"
Cohesion: 0.15
Nodes (23): parse_fomc(), Official FOMC meeting dates, scoped context only; no complete macro calendar., Isolated deterministic portfolio execution model. No broker or Store imports.…, Point-in-time evidence screening; language models cannot override vetoes., floor_step(), number(), propose(), Reproducible research proposals. No network, randomness, or order side effects. (+15 more)

### Community 28 - "devDependencies"
Cohesion: 0.04
Nodes (48): eslint, eslint-config-next, @fontsource-variable/dm-sans, @fontsource-variable/space-grotesk, dependencies, @fontsource-variable/dm-sans, @fontsource-variable/space-grotesk, motion (+40 more)

### Community 29 - "intelligence.py"
Cohesion: 0.19
Nodes (12): ASTRAL paper-only service., clean(), date(), named(), parse(), Independent public intelligence collector. No broker, credentials or order…, safe_url(), Source (+4 more)

### Community 30 - "Settings"
Cohesion: 0.18
Nodes (11): Settings, test_read_only_adapter_blocks_post_and_delete_before_transport(), test_shadow_cannot_submit_even_with_repeated_approvals(), book(), test_quote_adapter_preserves_prices_and_units_unknown_if_book_fails(), test_quote_adapter_retains_raw_book_and_versions_new_normalization(), engine(), fixture (+3 more)

### Community 31 - "asset-bar.tsx"
Cohesion: 0.39
Nodes (6): AssetBar(), Context, Selection, SelectionState(), useSelection(), UniverseSection()

### Community 32 - "utcnow"
Cohesion: 0.11
Nodes (20): Fixed-host Alpaca paper adapter and a separately labelled durable simulator., No remote API. Fills are synthetic and do not model queueing/market impact., Simulator, One explicitly authorized execution experiment; never an alpha strategy. Uses…, Credential-free local feed read; headlines remain untrusted scoped context., read_context(), Evidence-by-evidence readiness. No threshold changes or execution capability., utcnow() (+12 more)

### Community 33 - "test_health_engine.py"
Cohesion: 0.21
Nodes (14): observations(), parametrize, Health contracts: temporary ledgers and HTTP fixtures; never models/brokers., report(), test_engine_health_is_separate_from_model_enablement_and_market_closure(), test_event_driven_execution_worker_is_judged_by_status_not_age(), test_local_health_inputs_are_small_read_only_and_do_not_export_account_data(), test_local_observation_failures_do_not_reuse_healthy_state() (+6 more)

### Community 34 - "test_activity_rollout.py"
Cohesion: 0.08
Nodes (37): Latency, Observation, Fixed-size histogram retains every observation without per-request rows., Sample current availability without treating it as collection success., activated_settings(), check_ledger(), ledger_bytes(), main() (+29 more)

### Community 35 - "test_risk.py"
Cohesion: 0.24
Nodes (12): inputs(), parametrize, test_account_restrictions_block(), test_bad_bars_abstain(), test_cost_hurdle_prevents_an_uneconomic_candidate(), test_exact_threshold_latches_across_reconcile_and_restart(), test_exact_wilder_atr_and_repeatable_sizing(), test_intraday_budget_costs_minimum_and_cash() (+4 more)

### Community 36 - "HealthEngine"
Cohesion: 0.26
Nodes (5): lifespan(), Standalone health service, separate process and ledger from telemetry/trading., state(), fresh(), HealthEngine

### Community 37 - "validate_pr_body.cjs"
Cohesion: 0.23
Nodes (11): fs, main(), readableText(), REQUIRED_CHECKS, REQUIRED_SECTIONS, sections(), validatePullRequestBody(), withoutComments() (+3 more)

### Community 38 - "test_evidence_storage.py"
Cohesion: 0.20
Nodes (23): current_accounting(), Read-only compatibility with ledgers predating the new tables., read_projection(), pack_text(), unpack_bytes(), unpack_row(), unpack_text(), fixture (+15 more)

### Community 39 - "Store"
Cohesion: 0.12
Nodes (17): collect(), health_inputs(), intelligence(), lifespan(), Local-only companion: independent DB and lifecycle preserve the shadow pilot., Collector, Store, test_maintenance_empty_snapshot_304_extends_inspection_not_publication() (+9 more)

### Community 40 - "test_trade_history.py"
Cohesion: 0.29
Nodes (10): aggregate_daily(), seed(), aggregate(), batch(), parametrize, test_bad_trade_records_fail_closed(), test_history_shares_completed_days_and_reconstructs_each_immutable_batch(), test_missing_trade_day_is_not_filled_from_quotes() (+2 more)

### Community 41 - "activity_feed.py"
Cohesion: 0.13
Nodes (23): activity_identifier(), batch_events(), collect_batch(), FeedError, main(), Bounded paper activity acquisition and immutable evidence publication., Use the adapter's authentication, process boundary and request budget., Commit even rejected records before publishing or raising their failure. (+15 more)

### Community 42 - "HealthMonitor"
Cohesion: 0.15
Nodes (9): Independent assessments from telemetry observations; no trading authority., effective(), HealthMonitor, moment(), parse_report(), HTMLParser, Public provider reports, separate from account/model connectivity and risk. No…, StatusHeading (+1 more)

### Community 43 - "navigation.tsx"
Cohesion: 0.40
Nodes (3): NavLink(), Navigation(), pages

### Community 44 - "parametrize"
Cohesion: 0.18
Nodes (11): daily_history(), fee(), parametrize, test_diagnostic_failure_still_journals_prospective_veto(), test_distinct_lab_still_copies_or_reuses(), test_identical_fee_duplicates_and_later_execution_are_idempotent(), test_invalid_confirmed_fee_revision_is_retained_and_latched(), test_lab_rejects_primary_alias_before_lock_or_store() (+3 more)

### Community 45 - "test_dogfood.py"
Cohesion: 0.22
Nodes (15): Failure scenarios and adversarial selection cases; all trades are synthetic., test_ambiguous_fee_is_not_assigned_to_a_strategy(), test_api_shadow_does_not_enable_orders_and_rejects_bypass_fields(), test_intraday_exit_cannot_liquidate_swing_inventory(), test_late_confirmed_asset_fee_is_idempotent_and_reconciles(), test_local_exit_survives_restart_and_unknown_response(), test_quantity_and_shared_risk_boundaries(), test_readback_422_after_accepted_order_never_releases_reservation() (+7 more)

### Community 46 - "decide"
Cohesion: 0.33
Nodes (12): decide(), One-unit synthetic quote replay, with fills strictly AFTER decisions. Quote-…, replay(), test_disabled_model_keeps_deterministic_arm_in_new_observations(), event(), parametrize, test_entry_cancels_if_research_expires_during_latency(), test_entry_timing_fail_closed() (+4 more)

### Community 47 - "boundaries.test.ts"
Cohesion: 0.32
Nodes (6): allowlist, files, isClient(), lines(), root, text()

### Community 48 - "overnight_watch.py"
Cohesion: 0.25
Nodes (9): audit(), now(), Bounded overnight observation of the existing GET-only localhost paper lab., safety(), watch(), write_summary(), parametrize, test_observer_counts_lost_write_and_http_failure() (+1 more)

### Community 49 - "check-skills.cjs"
Cohesion: 0.33
Nodes (6): checkSkills(), crypto, fs, hashSkillFolder(), path, ROOT

### Community 50 - "test_stage2_validation.py"
Cohesion: 0.20
Nodes (13): audit_crypto(), Read-only reconciliation analysis. Hypotheses cannot become ledger entries., Compare authoritative gross executions and positions; explain, never waive. Fee…, parametrize, Synthetic decision-path and fault tests; none are broker-paper executions., reconciliation_fixture(), test_confirmed_fee_matches_and_duplicate_activity_is_not_counted_twice(), test_downstream_candidate_is_visible_but_inventory_still_vetoes() (+5 more)

### Community 51 - "document"
Cohesion: 0.40
Nodes (5): document(), fixture, setup(), test_fixture_mapping_and_missing_originals_cannot_satisfy_private_acceptance(), test_selected_capture_file_must_match_the_mapping_source_role()

### Community 52 - "commitlint.config.cjs"
Cohesion: 0.83
Nodes (3): bodyMaxLineLength(), footerMaxLineLength(), maxLineLength()

## Knowledge Gaps
- **154 isolated node(s):** `Source`, `metadata`, `dynamic`, `runtime`, `dynamic` (+149 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Store` connect `Store` to `test_event_sources.py`, `Engine`, `run`, `dumps`, `D`, `test_learning_engine.py`, `test_state_contract.py`, `test_executor_ownership.py`, `screen`, `test_readiness_gates.py`, `test_activity_feed.py`, `ValueError`, `activity_validation.py`, `datetime`, `Settings`, `utcnow`, `test_health_engine.py`, `test_activity_rollout.py`, `HealthEngine`, `test_evidence_storage.py`, `test_trade_history.py`, `HealthMonitor`, `test_dogfood.py`, `document`?**
  _High betweenness centrality (0.076) - this node is a cross-community bridge._
- **Why does `utcnow()` connect `utcnow` to `test_event_sources.py`, `Engine`, `run`, `dumps`, `screen`, `test_readiness_gates.py`, `test_activity_feed.py`, `ValueError`, `activity_validation.py`, `intelligence.py`, `Settings`, `test_health_engine.py`, `test_activity_rollout.py`, `HealthEngine`, `test_evidence_storage.py`, `Store`, `activity_feed.py`, `HealthMonitor`, `test_dogfood.py`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._
- **Why does `Engine` connect `Engine` to `utcnow`, `test_activity_rollout.py`, `dumps`, `run`, `D`, `Store`, `test_state_contract.py`, `activity_feed.py`, `parametrize`, `test_dogfood.py`, `screen`, `test_stage2_validation.py`, `test_activity_feed.py`, `ValueError`, `datetime`, `Settings`?**
  _High betweenness centrality (0.032) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `Store` (e.g. with `ExitPlan` and `Halt`) actually correct?**
  _`Store` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 102 inferred relationships involving `ValueError` (e.g. with `at()` and `cost_report()`) actually correct?**
  _`ValueError` has 102 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `Engine` (e.g. with `ExitPlan` and `Halt`) actually correct?**
  _`Engine` has 12 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Source`, `metadata`, `dynamic` to the rest of the system?**
  _154 weakly-connected nodes found - possible documentation gaps or missing edges._