# Graph Report - astral-trading  (2026-10-26)

## Corpus Check
- 199 files · ~71,331 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1342 nodes · 3976 edges · 64 communities (55 shown, 9 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 143 edges (avg confidence: 0.63)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d857c6f2`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- datetime
- broker.py
- run
- test_accounting_engine.py
- HealthMonitor
- D
- ui.ts
- test_learning_engine.py
- test_state_contract.py
- BrokerFailure
- scripts
- useDashboard
- connection.test.ts
- compilerOptions
- contracts.ts
- support.cjs
- screen
- test_readiness_gates.py
- motion.tsx
- health-page.tsx
- experiment.py
- relay.ts
- AlpacaPaper
- intelligence-feed.tsx
- test_experiment.py
- read.ts
- quantconnect/__init__.py
- engine.py
- devDependencies
- Store
- Engine
- overview-page.tsx
- test_review_repairs.py
- intelligence.py
- utcnow
- decide
- accounting/page.tsx
- validate_pr_body.cjs
- Settings
- replay_runner.py
- overnight_watch.py
- test_executor_ownership.py
- test_health_engine.py
- test_stage2_validation.py
- timestamp
- Connection
- Portfolio
- boundaries.test.ts
- navigation.tsx
- check-skills.cjs
- store.py
- test_trade_history.py
- commitlint.config.cjs
- intelligence_app.py
- app-frame.tsx
- proxy.ts
- next.config.ts
- StatusHeading
- test_quantconnect_validation.py
- prepare-standalone.mjs
- seed.ts

## God Nodes (most connected - your core abstractions)
1. `Store` - 91 edges
2. `run()` - 88 edges
3. `Engine` - 80 edges
4. `utcnow()` - 78 edges
5. `D()` - 66 edges
6. `Settings` - 57 edges
7. `useDashboard()` - 53 edges
8. `BrokerFailure` - 47 edges
9. `intent()` - 45 edges
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

## Communities (64 total, 9 thin omitted)

### Community 0 - "datetime"
Cohesion: 0.09
Nodes (34): Retain scoped official calendar catalogs; never certify missing categories., Maintenance needs two current publisher lists. NY Fed remains partial BLS., retain_additional_scopes(), retain_scopes(), catalog(), Cells, event(), maintenance() (+26 more)

### Community 1 - "broker.py"
Cohesion: 0.14
Nodes (12): Limiter, Fixed-host Alpaca paper adapter and a separately labelled durable simulator., account_identity(), AccountLease, OwnershipError, private_owned(), Exception, Cooperative paper-account ownership for one OS user on one host. (+4 more)

### Community 2 - "run"
Cohesion: 0.14
Nodes (36): Failure scenarios and adversarial selection cases; all trades are synthetic., test_ambiguous_fee_is_not_assigned_to_a_strategy(), test_api_shadow_does_not_enable_orders_and_rejects_bypass_fields(), test_intraday_exit_cannot_liquidate_swing_inventory(), test_late_confirmed_asset_fee_is_idempotent_and_reconciles(), test_local_exit_survives_restart_and_unknown_response(), test_quantity_and_shared_risk_boundaries(), test_readback_422_after_accepted_order_never_releases_reservation() (+28 more)

### Community 3 - "test_accounting_engine.py"
Cohesion: 0.10
Nodes (53): at(), canonical(), cost_report(), digest(), evaluate(), main(), number(), precise() (+45 more)

### Community 5 - "D"
Cohesion: 0.20
Nodes (36): D(), Assumptions, replay(), stress_suite(), synthetic_events(), at(), clock(), pick() (+28 more)

### Community 6 - "ui.ts"
Cohesion: 0.13
Nodes (22): StrategiesView(), StrategyCounts(), AccountingBoundaries(), AccountingCosts(), AccountingGross(), AccountingRecords(), AccountingSummary(), amounts() (+14 more)

### Community 7 - "test_learning_engine.py"
Cohesion: 0.11
Nodes (47): digest(), encode(), evaluate(), main(), markdown(), packet_checks(), protected(), protected_windows() (+39 more)

### Community 8 - "test_state_contract.py"
Cohesion: 0.18
Nodes (23): at(), build_state(), buy(), free_port(), normalize(), pin_clock(), parametrize, Dashboard read-path contract: fixed Store-seeded ledgers and a pinned clock.… (+15 more)

### Community 9 - "BrokerFailure"
Cohesion: 0.13
Nodes (23): ExitPlan, Halt, Intent, ResearchBar, RiskCandidate, BrokerFailure, Exception, Exception (+15 more)

### Community 10 - "scripts"
Cohesion: 0.05
Nodes (37): @commitlint/cli, @commitlint/config-conventional, @commitlint/lint, @commitlint/load, husky, devDependencies, @commitlint/cli, @commitlint/config-conventional (+29 more)

### Community 11 - "useDashboard"
Cohesion: 0.16
Nodes (21): HealthFooterStatus(), EquityChart(), ModeBadge(), Context, useDashboard(), Detail, EvidenceDialog(), PacketDialog() (+13 more)

### Community 12 - "connection.test.ts"
Cohesion: 0.17
Nodes (7): Seed, seed(), Source, dashboard(), health(), now, services()

### Community 13 - "compilerOptions"
Cohesion: 0.07
Nodes (29): compilerOptions, allowJs, checkJs, esModuleInterop, incremental, isolatedModules, jsx, lib (+21 more)

### Community 14 - "contracts.ts"
Cohesion: 0.08
Nodes (28): SystemView(), api(), errorMessage(), empty, Snapshot, accountingSchema, amount, counts (+20 more)

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
Nodes (24): CodexReviewer, command(), material_hash(), Bounded Codex CLI reviewer. Broker credentials and tools are not inherited., evidence_for(), Point-in-time evidence screening; language models cannot override vetoes., screen(), validate_review() (+16 more)

### Community 17 - "test_readiness_gates.py"
Cohesion: 0.12
Nodes (18): parse_bea(), HTMLParser, Scoped BEA schedule; a date is retained without inventing an unspecified…, Schedule, record_fee(), bea_html(), book(), fee() (+10 more)

### Community 18 - "motion.tsx"
Cohesion: 0.13
Nodes (16): AnimationProvider(), initialMode(), initialSystem(), LoadingPanel(), Mode, readMode(), readSystem(), Reveal() (+8 more)

### Community 19 - "health-page.tsx"
Cohesion: 0.11
Nodes (25): metadata, HealthDetails(), HealthMap(), HealthPage(), HealthSummary(), attention, inTopic(), reportedNodes() (+17 more)

### Community 20 - "experiment.py"
Cohesion: 0.11
Nodes (40): contract(), digest(), observe(), Frozen research contract and append-only observations. No execution interface., register(), source_hashes(), state(), evaluate() (+32 more)

### Community 21 - "relay.ts"
Cohesion: 0.17
Nodes (12): Context, dynamic, GET(), POST(), runtime, acceptsGzip(), compress, getPaths (+4 more)

### Community 23 - "intelligence-feed.tsx"
Cohesion: 0.23
Nodes (7): Dialog(), IntelligenceFeed(), SourceDialog(), ViewDialog(), IntelligenceView(), SourceLink(), News

### Community 24 - "test_experiment.py"
Cohesion: 0.11
Nodes (26): Meetings, parse_fomc(), HTMLParser, Official FOMC meeting dates, scoped context only; no complete macro calendar., propose(), ATR14 + trend/breakout candidate and fixed fractional loss-budget sizing. All…, context(), fomc_html() (+18 more)

### Community 25 - "read.ts"
Cohesion: 0.23
Nodes (8): read(), ReadResult, allowedHost(), originDefaults, originVariables, Service, serviceUrl(), schema

### Community 27 - "engine.py"
Cohesion: 0.43
Nodes (5): attribute(), canonical_symbol(), Inventory attribution is evidence, not a substitute for broker availability., Evidence-by-evidence readiness. No threshold changes or execution capability., view()

### Community 28 - "devDependencies"
Cohesion: 0.04
Nodes (48): eslint, eslint-config-next, @fontsource-variable/dm-sans, @fontsource-variable/space-grotesk, dependencies, @fontsource-variable/dm-sans, @fontsource-variable/space-grotesk, motion (+40 more)

### Community 29 - "Store"
Cohesion: 0.27
Nodes (3): Store, test_maintenance_empty_snapshot_304_extends_inspection_not_publication(), test_replay_report_is_visible_only_in_the_book_that_records_its_receipt()

### Community 30 - "Engine"
Cohesion: 0.16
Nodes (6): age(), Engine, symbol_for(), book_for(), dumps(), test_adapter_hashes_are_cached_local_and_covered_by_packet_hash()

### Community 31 - "overview-page.tsx"
Cohesion: 0.15
Nodes (19): HealthChanges(), OrderDialog(), AssetBar(), ExecutionStream(), OverviewFooter(), OverviewPage(), views, PortfolioCards() (+11 more)

### Community 32 - "test_review_repairs.py"
Cohesion: 0.19
Nodes (16): daily_history(), fee(), parametrize, Locked review regressions. Synthetic brokers, patched models and tmp ledgers…, test_all_vetoed_cycle_never_calls_model(), test_diagnostic_failure_still_journals_prospective_veto(), test_distinct_lab_still_copies_or_reuses(), test_global_fee_latch_blocks_strategy_sell_with_rule_violation() (+8 more)

### Community 33 - "intelligence.py"
Cohesion: 0.12
Nodes (21): ASTRAL paper-only service., clean(), Collector, date(), named(), parse(), Independent public intelligence collector. No broker, credentials or order…, safe_url() (+13 more)

### Community 34 - "utcnow"
Cohesion: 0.11
Nodes (12): No remote API. Fills are synthetic and do not model queueing/market impact., Simulator, read_context(), utcnow(), isolate_experiment_workers(), lab_path(), main(), Bounded, GET-only Alpaca dogfood session using a private copied ledger. (+4 more)

### Community 35 - "decide"
Cohesion: 0.32
Nodes (12): decide(), Deterministic timing hypotheses. Produces candidates, never orders or fills., One-unit synthetic quote replay, with fills strictly AFTER decisions. Quote-…, replay(), event(), parametrize, test_entry_cancels_if_research_expires_during_latency(), test_entry_timing_fail_closed() (+4 more)

### Community 36 - "accounting/page.tsx"
Cohesion: 0.17
Nodes (10): dynamic, metadata, Page(), dynamic, metadata, Page(), AccountingContent(), LearningContent() (+2 more)

### Community 37 - "validate_pr_body.cjs"
Cohesion: 0.23
Nodes (11): fs, main(), readableText(), REQUIRED_CHECKS, REQUIRED_SECTIONS, sections(), validatePullRequestBody(), withoutComments() (+3 more)

### Community 38 - "Settings"
Cohesion: 0.19
Nodes (11): create_app(), Settings, test_read_only_adapter_blocks_post_and_delete_before_transport(), test_shadow_cannot_submit_even_with_repeated_approvals(), test_local_health_inputs_are_small_read_only_and_do_not_export_account_data(), engine(), fixture, test_api_boundary_validation_and_persistence() (+3 more)

### Community 39 - "replay_runner.py"
Cohesion: 0.33
Nodes (10): build_report(), code_hashes(), connect_readonly(), export_events(), Read-only ledger export, fixed future window and offline stress receipts. No…, register_holdout(), report_state(), summary() (+2 more)

### Community 40 - "overnight_watch.py"
Cohesion: 0.25
Nodes (9): audit(), now(), Bounded overnight observation of the existing GET-only localhost paper lab., safety(), watch(), write_summary(), parametrize, test_observer_counts_lost_write_and_http_failure() (+1 more)

### Community 41 - "test_executor_ownership.py"
Cohesion: 0.23
Nodes (15): adapters(), fixture, parametrize, Account ownership through public broker methods; no real provider writes., test_account_writer_is_exclusive_between_processes_and_recovers_after_sigkill(), test_changed_identity_latches_writes_even_if_the_original_identity_returns(), test_close_keeps_ownership_until_the_inflight_write_finishes(), test_closed_adapter_cannot_reacquire_authority_and_market_data_cannot_mutate() (+7 more)

### Community 42 - "test_health_engine.py"
Cohesion: 0.24
Nodes (14): parse_report(), observations(), Providers, parametrize, Health contracts: temporary ledgers and HTTP fixtures; never models/brokers., report(), test_engine_health_is_separate_from_model_enablement_and_market_closure(), test_event_driven_execution_worker_is_judged_by_status_not_age() (+6 more)

### Community 43 - "test_stage2_validation.py"
Cohesion: 0.20
Nodes (13): audit_crypto(), Read-only reconciliation analysis. Hypotheses cannot become ledger entries., Compare authoritative gross executions and positions; explain, never waive. Fee…, parametrize, Synthetic decision-path and fault tests; none are broker-paper executions., reconciliation_fixture(), test_confirmed_fee_matches_and_duplicate_activity_is_not_counted_twice(), test_downstream_candidate_is_visible_but_inventory_still_vetoes() (+5 more)

### Community 44 - "timestamp"
Cohesion: 0.22
Nodes (14): diagnose(), Retrospective price-only prefixes. Never pretend these were known earlier., Quote-only liquidity experiment. No orders, fills, positions, P&L or promotion., turnover(), walk(), Same-venue REST book/quote validation. Visible depth never guarantees a fill., _validate(), Isolated deterministic portfolio execution model. No broker or Store imports.… (+6 more)

### Community 47 - "boundaries.test.ts"
Cohesion: 0.32
Nodes (6): allowlist, files, isClient(), lines(), root, text()

### Community 48 - "navigation.tsx"
Cohesion: 0.40
Nodes (3): NavLink(), Navigation(), pages

### Community 49 - "check-skills.cjs"
Cohesion: 0.33
Nodes (6): checkSkills(), crypto, fs, hashSkillFolder(), path, ROOT

### Community 50 - "store.py"
Cohesion: 0.17
Nodes (10): lifespan(), Standalone health service, separate process and ledger from telemetry/trading., state(), fresh(), HealthEngine, Independent assessments from telemetry observations; no trading authority., effective(), moment() (+2 more)

### Community 51 - "test_trade_history.py"
Cohesion: 0.39
Nodes (8): aggregate(), batch(), parametrize, test_bad_trade_records_fail_closed(), test_history_shares_completed_days_and_reconstructs_each_immutable_batch(), test_missing_trade_day_is_not_filled_from_quotes(), test_provider_pagination_must_finish_before_history_is_accepted(), test_trade_only_bars_deduplicate_and_exclude_incomplete_day()

### Community 52 - "commitlint.config.cjs"
Cohesion: 0.83
Nodes (3): bodyMaxLineLength(), footerMaxLineLength(), maxLineLength()

### Community 53 - "intelligence_app.py"
Cohesion: 0.29
Nodes (6): collect(), health_inputs(), intelligence(), lifespan(), Local-only companion: independent DB and lifecycle preserve the shadow pilot., test_collection_loop_delays_after_failure_continues_and_propagates_cancel()

### Community 54 - "app-frame.tsx"
Cohesion: 0.36
Nodes (3): Clock(), HaltButton(), OpeningPanels()

### Community 58 - "test_quantconnect_validation.py"
Cohesion: 0.11
Nodes (35): price_signal(), Pure OHLC hypothesis; caller validates provenance and time separately., QCAlgorithm, as_utc(), AstralBtcSignalParity, Compare both implementations in cloud memory; export aggregate diagnostics only., bundle(), compare() (+27 more)

### Community 63 - "seed.ts"
Cohesion: 0.25
Nodes (8): dynamic, metadata, RootLayout(), Provider(), AppFrame(), loadSeed(), seedScope(), upstreamFetch()

## Knowledge Gaps
- **154 isolated node(s):** `Source`, `metadata`, `dynamic`, `runtime`, `dynamic` (+149 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Store` connect `Store` to `datetime`, `broker.py`, `run`, `test_accounting_engine.py`, `D`, `test_learning_engine.py`, `test_state_contract.py`, `BrokerFailure`, `screen`, `test_readiness_gates.py`, `experiment.py`, `test_experiment.py`, `test_review_repairs.py`, `intelligence.py`, `utcnow`, `Settings`, `test_executor_ownership.py`, `test_health_engine.py`, `store.py`, `test_trade_history.py`, `intelligence_app.py`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Why does `utcnow()` connect `utcnow` to `datetime`, `broker.py`, `intelligence.py`, `test_accounting_engine.py`, `HealthMonitor`, `run`, `Settings`, `test_review_repairs.py`, `BrokerFailure`, `test_health_engine.py`, `screen`, `test_readiness_gates.py`, `store.py`, `experiment.py`, `AlpacaPaper`, `engine.py`, `Engine`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Why does `Engine` connect `Engine` to `test_review_repairs.py`, `utcnow`, `run`, `D`, `Settings`, `test_state_contract.py`, `BrokerFailure`, `test_stage2_validation.py`, `screen`, `test_readiness_gates.py`, `experiment.py`, `AlpacaPaper`, `test_experiment.py`, `engine.py`, `Store`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `Store` (e.g. with `ExitPlan` and `Halt`) actually correct?**
  _`Store` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `Engine` (e.g. with `ExitPlan` and `Halt`) actually correct?**
  _`Engine` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 30 inferred relationships involving `D()` (e.g. with `diagnose()` and `validate_activity()`) actually correct?**
  _`D()` has 30 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Source`, `metadata`, `dynamic` to the rest of the system?**
  _154 weakly-connected nodes found - possible documentation gaps or missing edges._