# Graph Report - astral-trading  (2026-10-27)

## Corpus Check
- 205 files · ~80,607 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1493 nodes · 4711 edges · 59 communities (53 shown, 6 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 240 edges (avg confidence: 0.7)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d0ef9fbe`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_event_sources.py
- Engine
- test_service.py
- dumps
- activity_validation.py
- D
- ui.ts
- test_learning_engine.py
- test_state_contract.py
- Settings
- scripts
- useDashboard
- run
- compilerOptions
- contracts.ts
- support.cjs
- screen
- test_readiness_gates.py
- motion.tsx
- health-page.tsx
- ValueError
- relay.ts
- test_activity_feed.py
- activity_feed.py
- test_risk.py
- utcnow
- quantconnect/__init__.py
- test_stage2_validation.py
- devDependencies
- Store
- broker.py
- overview-page.tsx
- test_review_repairs.py
- intelligence.py
- accounting/page.tsx
- Source
- BrokerFailure
- validate_pr_body.cjs
- Collector
- test_execution_pilot.py
- overnight_watch.py
- test_experiment.py
- test_health_engine.py
- parse_bea
- source-dialog.tsx
- ExecutionPilot
- Cells
- boundaries.test.ts
- check-skills.cjs
- test_trade_history.py
- commitlint.config.cjs
- proxy.ts
- next.config.ts
- test_quantconnect_validation.py
- prepare-standalone.mjs
- Connection

## God Nodes (most connected - your core abstractions)
1. `Store` - 101 edges
2. `utcnow()` - 91 edges
3. `run()` - 91 edges
4. `Engine` - 87 edges
5. `D()` - 67 edges
6. `Settings` - 66 edges
7. `dumps()` - 59 edges
8. `useDashboard()` - 53 edges
9. `BrokerFailure` - 51 edges
10. `intent()` - 45 edges

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

## Communities (59 total, 6 thin omitted)

### Community 0 - "test_event_sources.py"
Cohesion: 0.15
Nodes (23): catalog(), event(), maintenance(), nyfed(), parse_events(), protocol(), Fixed public event sources. Published context is distinct from complete…, Watch authoritative documents without interpreting proposals as activations. (+15 more)

### Community 1 - "Engine"
Cohesion: 0.16
Nodes (4): age(), Engine, symbol_for(), book_for()

### Community 2 - "test_service.py"
Cohesion: 0.13
Nodes (26): Failure scenarios and adversarial selection cases; all trades are synthetic., test_ambiguous_fee_is_not_assigned_to_a_strategy(), test_intraday_exit_cannot_liquidate_swing_inventory(), test_late_confirmed_asset_fee_is_idempotent_and_reconciles(), test_quantity_and_shared_risk_boundaries(), test_readback_422_after_accepted_order_never_releases_reservation(), test_shared_pending_and_inventory_budget_across_strategies(), test_stale_exit_quote_cannot_trigger_an_order() (+18 more)

### Community 3 - "dumps"
Cohesion: 0.06
Nodes (111): at(), canonical(), cost_report(), digest(), evaluate(), main(), number(), precise() (+103 more)

### Community 4 - "activity_validation.py"
Cohesion: 0.14
Nodes (31): publish_projection(), start_batch(), balances_match(), canonical(), digest(), input_digest(), instant(), load_mapping() (+23 more)

### Community 5 - "D"
Cohesion: 0.15
Nodes (37): D(), Assumptions, Portfolio, replay(), stress_suite(), synthetic_events(), at(), clock() (+29 more)

### Community 6 - "ui.ts"
Cohesion: 0.15
Nodes (20): AccountingBoundaries(), AccountingCosts(), AccountingGross(), AccountingRecords(), AccountingSummary(), amounts(), LearningBoundaries(), LearningInventory() (+12 more)

### Community 7 - "test_learning_engine.py"
Cohesion: 0.15
Nodes (39): digest(), encode(), evaluate(), main(), markdown(), packet_checks(), protected(), protected_windows() (+31 more)

### Community 8 - "test_state_contract.py"
Cohesion: 0.19
Nodes (21): at(), build_state(), buy(), free_port(), normalize(), pin_clock(), Dashboard read-path contract: fixed Store-seeded ledgers and a pinned clock.…, Bounded SSE reader yielding (id, event, data) blocks. (+13 more)

### Community 9 - "Settings"
Cohesion: 0.20
Nodes (18): create_app(), ExitPlan, Halt, Intent, ResearchBar, RiskCandidate, Settings, Exception (+10 more)

### Community 10 - "scripts"
Cohesion: 0.05
Nodes (37): @commitlint/cli, @commitlint/config-conventional, @commitlint/lint, @commitlint/load, husky, devDependencies, @commitlint/cli, @commitlint/config-conventional (+29 more)

### Community 11 - "useDashboard"
Cohesion: 0.13
Nodes (26): dynamic, metadata, HealthFooterStatus(), ModeBadge(), Context, Provider(), useDashboard(), Detail (+18 more)

### Community 12 - "run"
Cohesion: 0.28
Nodes (17): adapters(), fixture, parametrize, Account ownership through public broker methods; no real provider writes., test_changed_identity_latches_writes_even_if_the_original_identity_returns(), test_close_keeps_ownership_until_the_inflight_write_finishes(), test_closed_adapter_cannot_reacquire_authority_and_market_data_cannot_mutate(), test_different_accounts_can_write_and_read_only_observers_do_not_contend() (+9 more)

### Community 13 - "compilerOptions"
Cohesion: 0.07
Nodes (29): compilerOptions, allowJs, checkJs, esModuleInterop, incremental, isolatedModules, jsx, lib (+21 more)

### Community 14 - "contracts.ts"
Cohesion: 0.07
Nodes (32): SystemView(), api(), errorMessage(), empty, Seed, Snapshot, accountingSchema, amount (+24 more)

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
Nodes (22): CodexReviewer, command(), material_hash(), Bounded Codex CLI reviewer. Broker credentials and tools are not inherited., Point-in-time evidence screening; language models cannot override vetoes., screen(), validate_review(), parametrize (+14 more)

### Community 17 - "test_readiness_gates.py"
Cohesion: 0.14
Nodes (23): Maintenance needs two current publisher lists. NY Fed remains partial BLS., retain_additional_scopes(), retain_scopes(), Validate provider fee records without estimating missing fees or rewriting…, record_fee(), validate_activity(), calendar_coverage(), All scoped categories need retained, current, forward-covering evidence.… (+15 more)

### Community 18 - "motion.tsx"
Cohesion: 0.13
Nodes (15): AnimationProvider(), initialMode(), initialSystem(), LoadingPanel(), Mode, readMode(), readSystem(), Reveal() (+7 more)

### Community 19 - "health-page.tsx"
Cohesion: 0.11
Nodes (25): metadata, HealthChanges(), HealthDetails(), HealthMap(), HealthPage(), HealthSummary(), attention, inTopic() (+17 more)

### Community 20 - "ValueError"
Cohesion: 0.07
Nodes (74): contract(), digest(), observe(), Frozen research contract and append-only observations. No execution interface., register(), source_hashes(), state(), evaluate() (+66 more)

### Community 21 - "relay.ts"
Cohesion: 0.08
Nodes (29): Page(), Context, dynamic, GET(), POST(), runtime, RootLayout(), Page() (+21 more)

### Community 22 - "test_activity_feed.py"
Cohesion: 0.11
Nodes (41): current_accounting(), parse_sse(), Read-only compatibility with ledgers predating the new tables., read_projection(), ledger_source(), The caller holds a read transaction or the Store lock across this snapshot., destinations(), controlled_current() (+33 more)

### Community 23 - "activity_feed.py"
Cohesion: 0.17
Nodes (16): activity_identifier(), collect_batch(), FeedError, main(), Bounded paper activity acquisition and immutable evidence publication., Use the adapter's authentication, process boundary and request budget., Commit even rejected records before publishing or raising their failure., Incremental SSE framing; raw acquisition bytes are retained separately. (+8 more)

### Community 24 - "test_risk.py"
Cohesion: 0.17
Nodes (20): diagnose(), Retrospective price-only prefixes. Never pretend these were known earlier., propose(), ATR14 + trend/breakout candidate and fixed fractional loss-budget sizing. All…, history(), parametrize, test_diagnostic_rejects_bad_history(), test_prefix_diagnostic_reuses_live_math_and_never_assumes_fills() (+12 more)

### Community 25 - "utcnow"
Cohesion: 0.10
Nodes (16): No remote API. Fills are synthetic and do not model queueing/market impact., Simulator, Retain scoped official calendar catalogs; never certify missing categories., Independent assessments from telemetry observations; no trading authority., Inventory attribution is evidence, not a substitute for broker availability., One explicitly authorized execution experiment; never an alpha strategy. Uses…, Credential-free local feed read; headlines remain untrusted scoped context., read_context() (+8 more)

### Community 27 - "test_stage2_validation.py"
Cohesion: 0.22
Nodes (12): audit_crypto(), Read-only reconciliation analysis. Hypotheses cannot become ledger entries., Compare authoritative gross executions and positions; explain, never waive. Fee…, parametrize, Synthetic decision-path and fault tests; none are broker-paper executions., reconciliation_fixture(), test_confirmed_fee_matches_and_duplicate_activity_is_not_counted_twice(), test_downstream_candidate_is_visible_but_inventory_still_vetoes() (+4 more)

### Community 28 - "devDependencies"
Cohesion: 0.04
Nodes (48): eslint, eslint-config-next, @fontsource-variable/dm-sans, @fontsource-variable/space-grotesk, dependencies, @fontsource-variable/dm-sans, @fontsource-variable/space-grotesk, motion (+40 more)

### Community 29 - "Store"
Cohesion: 0.09
Nodes (19): Store, isolate_experiment_workers(), lab_path(), main(), Bounded, GET-only Alpaca dogfood session using a private copied ledger., main(), main(), Explicit, bounded PAPER-only CLI. No web API can enable this pilot. (+11 more)

### Community 30 - "broker.py"
Cohesion: 0.17
Nodes (9): Limiter, Fixed-host Alpaca paper adapter and a separately labelled durable simulator., account_identity(), AccountLease, OwnershipError, private_owned(), Exception, Cooperative paper-account ownership for one OS user on one host. (+1 more)

### Community 31 - "overview-page.tsx"
Cohesion: 0.12
Nodes (23): OrderDialog(), AssetBar(), EquityChart(), ExecutionStream(), IntelligenceFeed(), OverviewFooter(), OverviewPage(), views (+15 more)

### Community 32 - "test_review_repairs.py"
Cohesion: 0.18
Nodes (17): daily_history(), fee(), parametrize, Locked review regressions. Synthetic brokers, patched models and tmp ledgers…, test_adapter_hashes_are_cached_local_and_covered_by_packet_hash(), test_all_vetoed_cycle_never_calls_model(), test_diagnostic_failure_still_journals_prospective_veto(), test_distinct_lab_still_copies_or_reuses() (+9 more)

### Community 33 - "intelligence.py"
Cohesion: 0.16
Nodes (13): ASTRAL paper-only service., clean(), date(), named(), parse(), Independent public intelligence collector. No broker, credentials or order…, safe_url(), Source (+5 more)

### Community 34 - "accounting/page.tsx"
Cohesion: 0.18
Nodes (10): dynamic, metadata, dynamic, metadata, AccountingContent(), LearningContent(), ReportFrame(), Shown (+2 more)

### Community 36 - "BrokerFailure"
Cohesion: 0.14
Nodes (12): AlpacaPaper, BrokerFailure, Exception, test_local_exit_survives_restart_and_unknown_response(), test_read_only_adapter_blocks_post_and_delete_before_transport(), parametrize, test_accepted_timeout_recovered_without_second_post(), test_adapter_fixed_hosts_no_post_retries_and_cooldown() (+4 more)

### Community 37 - "validate_pr_body.cjs"
Cohesion: 0.23
Nodes (11): fs, main(), readableText(), REQUIRED_CHECKS, REQUIRED_SECTIONS, sections(), validatePullRequestBody(), withoutComments() (+3 more)

### Community 38 - "Collector"
Cohesion: 0.20
Nodes (12): collect(), health_inputs(), intelligence(), lifespan(), Local-only companion: independent DB and lifecycle preserve the shadow pilot., Collector, test_collection_loop_delays_after_failure_continues_and_propagates_cancel(), test_collector_fetch_propagates_cancellation() (+4 more)

### Community 39 - "test_execution_pilot.py"
Cohesion: 0.27
Nodes (10): pilot(), parametrize, test_crash_after_entry_resumes_exit_without_new_entry(), test_final_pilot_boundary_blocks_wrong_or_oversize_requests(), test_pilot_and_strategy_workers_cannot_share_authority(), test_pilot_recovers_lost_accepted_entry_without_duplicate(), test_pilot_refuses_existing_positions(), test_synthetic_round_trip_and_completed_resume_do_not_buy_twice() (+2 more)

### Community 40 - "overnight_watch.py"
Cohesion: 0.25
Nodes (9): audit(), now(), Bounded overnight observation of the existing GET-only localhost paper lab., safety(), watch(), write_summary(), parametrize, test_observer_counts_lost_write_and_http_failure() (+1 more)

### Community 41 - "test_experiment.py"
Cohesion: 0.21
Nodes (9): Meetings, parse_fomc(), HTMLParser, Official FOMC meeting dates, scoped context only; no complete macro calendar., context(), fomc_html(), test_fomc_dates_are_conservative_local_intervals_not_invented_release_times(), test_scoped_calendar_context_can_veto_but_never_claim_complete_coverage() (+1 more)

### Community 42 - "test_health_engine.py"
Cohesion: 0.08
Nodes (26): lifespan(), Standalone health service, separate process and ledger from telemetry/trading., state(), fresh(), HealthEngine, effective(), HealthMonitor, parse_report() (+18 more)

### Community 43 - "parse_bea"
Cohesion: 0.25
Nodes (4): parse_bea(), HTMLParser, Scoped BEA schedule; a date is retained without inventing an unspecified…, Schedule

### Community 44 - "source-dialog.tsx"
Cohesion: 0.31
Nodes (5): Dialog(), SourceDialog(), ViewDialog(), SourceLink(), News

### Community 46 - "Cells"
Cohesion: 0.29
Nodes (3): Cells, HTMLParser, Retain cells in a selected table, including links and their following text.

### Community 47 - "boundaries.test.ts"
Cohesion: 0.32
Nodes (6): allowlist, files, isClient(), lines(), root, text()

### Community 49 - "check-skills.cjs"
Cohesion: 0.33
Nodes (6): checkSkills(), crypto, fs, hashSkillFolder(), path, ROOT

### Community 51 - "test_trade_history.py"
Cohesion: 0.44
Nodes (8): aggregate_daily(), aggregate(), batch(), parametrize, test_bad_trade_records_fail_closed(), test_history_shares_completed_days_and_reconstructs_each_immutable_batch(), test_missing_trade_day_is_not_filled_from_quotes(), test_trade_only_bars_deduplicate_and_exclude_incomplete_day()

### Community 52 - "commitlint.config.cjs"
Cohesion: 0.83
Nodes (3): bodyMaxLineLength(), footerMaxLineLength(), maxLineLength()

### Community 58 - "test_quantconnect_validation.py"
Cohesion: 0.11
Nodes (35): price_signal(), Pure OHLC hypothesis; caller validates provenance and time separately., QCAlgorithm, as_utc(), AstralBtcSignalParity, Compare both implementations in cloud memory; export aggregate diagnostics only., bundle(), compare() (+27 more)

### Community 63 - "Connection"
Cohesion: 0.18
Nodes (4): NavLink(), Navigation(), pages, Connection

## Knowledge Gaps
- **154 isolated node(s):** `Source`, `metadata`, `dynamic`, `runtime`, `dynamic` (+149 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Store` connect `Store` to `test_event_sources.py`, `test_service.py`, `dumps`, `activity_validation.py`, `D`, `test_learning_engine.py`, `test_state_contract.py`, `Settings`, `run`, `screen`, `test_readiness_gates.py`, `ValueError`, `test_activity_feed.py`, `utcnow`, `broker.py`, `test_review_repairs.py`, `BrokerFailure`, `Collector`, `test_execution_pilot.py`, `test_experiment.py`, `test_health_engine.py`, `test_trade_history.py`?**
  _High betweenness centrality (0.058) - this node is a cross-community bridge._
- **Why does `Engine` connect `Engine` to `test_review_repairs.py`, `test_service.py`, `dumps`, `BrokerFailure`, `D`, `test_execution_pilot.py`, `test_state_contract.py`, `Settings`, `test_experiment.py`, `screen`, `test_activity_feed.py`, `activity_feed.py`, `utcnow`, `test_stage2_validation.py`, `Store`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._
- **Why does `D()` connect `D` to `Engine`, `test_service.py`, `dumps`, `BrokerFailure`, `test_state_contract.py`, `test_health_engine.py`, `ExecutionPilot`, `screen`, `test_readiness_gates.py`, `test_trade_history.py`, `ValueError`, `test_risk.py`, `utcnow`, `test_stage2_validation.py`, `broker.py`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `Store` (e.g. with `ExitPlan` and `Halt`) actually correct?**
  _`Store` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 91 inferred relationships involving `ValueError` (e.g. with `at()` and `cost_report()`) actually correct?**
  _`ValueError` has 91 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `Engine` (e.g. with `ExitPlan` and `Halt`) actually correct?**
  _`Engine` has 12 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Source`, `metadata`, `dynamic` to the rest of the system?**
  _154 weakly-connected nodes found - possible documentation gaps or missing edges._