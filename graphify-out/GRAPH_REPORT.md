# Graph Report - astral-trading  (2026-10-26)

## Corpus Check
- 197 files · ~69,648 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1308 nodes · 3870 edges · 56 communities (49 shown, 7 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 135 edges (avg confidence: 0.64)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `2fc61b8d`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_event_sources.py
- BrokerFailure
- run
- test_accounting_engine.py
- test_health_engine.py
- D
- ui.ts
- test_learning_engine.py
- Engine
- test_quantconnect_validation.py
- scripts
- useDashboard
- Settings
- compilerOptions
- contracts.ts
- support.cjs
- test_state_contract.py
- timestamp
- motion.tsx
- health-page.tsx
- liquidity_runner.py
- relay.ts
- replay_runner.py
- test_execution_pilot.py
- test_experiment.py
- HealthMonitor
- test_review_repairs.py
- test_stage2_validation.py
- devDependencies
- engine.py
- utcnow
- overview-page.tsx
- Source
- intelligence.py
- quantconnect/__init__.py
- decide
- validate_pr_body.cjs
- datetime
- Connection
- overnight_watch.py
- Store
- HealthEngine
- experiment.py
- StatusHeading
- boundaries.test.ts
- check-skills.cjs
- navigation.tsx
- commitlint.config.cjs
- packet-dialog.tsx
- proxy.ts
- next.config.ts
- prepare-standalone.mjs
- test_trade_history.py

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

## Communities (56 total, 7 thin omitted)

### Community 0 - "test_event_sources.py"
Cohesion: 0.09
Nodes (32): Retain scoped official calendar catalogs; never certify missing categories., Maintenance needs two current publisher lists. NY Fed remains partial BLS., retain_additional_scopes(), retain_scopes(), catalog(), Cells, event(), maintenance() (+24 more)

### Community 1 - "BrokerFailure"
Cohesion: 0.16
Nodes (9): AlpacaPaper, BrokerFailure, Limiter, Exception, book(), quote(), test_exact_same_venue_depth_contract_and_capacity(), test_quote_adapter_preserves_prices_and_units_unknown_if_book_fails() (+1 more)

### Community 2 - "run"
Cohesion: 0.12
Nodes (40): Failure scenarios and adversarial selection cases; all trades are synthetic., test_ambiguous_fee_is_not_assigned_to_a_strategy(), test_intraday_exit_cannot_liquidate_swing_inventory(), test_late_confirmed_asset_fee_is_idempotent_and_reconciles(), test_local_exit_survives_restart_and_unknown_response(), test_quantity_and_shared_risk_boundaries(), test_readback_422_after_accepted_order_never_releases_reservation(), test_repeated_identical_exit_veto_is_journaled_once() (+32 more)

### Community 3 - "test_accounting_engine.py"
Cohesion: 0.09
Nodes (59): at(), canonical(), cost_report(), digest(), evaluate(), main(), number(), precise() (+51 more)

### Community 4 - "test_health_engine.py"
Cohesion: 0.25
Nodes (13): parse_report(), observations(), Providers, parametrize, Health contracts: temporary ledgers and HTTP fixtures; never models/brokers., report(), test_engine_health_is_separate_from_model_enablement_and_market_closure(), test_event_driven_execution_worker_is_judged_by_status_not_age() (+5 more)

### Community 5 - "D"
Cohesion: 0.14
Nodes (38): D(), Assumptions, Portfolio, replay(), stress_suite(), synthetic_events(), floor_step(), at() (+30 more)

### Community 6 - "ui.ts"
Cohesion: 0.13
Nodes (22): StrategiesView(), StrategyCounts(), AccountingBoundaries(), AccountingCosts(), AccountingGross(), AccountingRecords(), AccountingSummary(), amounts() (+14 more)

### Community 7 - "test_learning_engine.py"
Cohesion: 0.15
Nodes (39): digest(), encode(), evaluate(), main(), markdown(), packet_checks(), protected(), protected_windows() (+31 more)

### Community 8 - "Engine"
Cohesion: 0.16
Nodes (4): age(), Engine, symbol_for(), book_for()

### Community 9 - "test_quantconnect_validation.py"
Cohesion: 0.11
Nodes (31): price_signal(), Pure OHLC hypothesis; caller validates provenance and time separately., QCAlgorithm, AstralBtcSignalParity, Compare both implementations in cloud memory; export aggregate diagnostics only., bundle(), compare(), main() (+23 more)

### Community 10 - "scripts"
Cohesion: 0.05
Nodes (37): @commitlint/cli, @commitlint/config-conventional, @commitlint/lint, @commitlint/load, husky, devDependencies, @commitlint/cli, @commitlint/config-conventional (+29 more)

### Community 11 - "useDashboard"
Cohesion: 0.21
Nodes (17): OverviewFooter(), Context, useDashboard(), PacketDialog(), ResearchExperiments(), ResearchGates(), ResearchLab(), ResearchPackets() (+9 more)

### Community 12 - "Settings"
Cohesion: 0.17
Nodes (19): create_app(), ExitPlan, Halt, Intent, ResearchBar, RiskCandidate, Settings, Exception (+11 more)

### Community 13 - "compilerOptions"
Cohesion: 0.07
Nodes (29): compilerOptions, allowJs, checkJs, esModuleInterop, incremental, isolatedModules, jsx, lib (+21 more)

### Community 14 - "contracts.ts"
Cohesion: 0.06
Nodes (40): dynamic, metadata, RootLayout(), Provider(), AppFrame(), api(), errorMessage(), empty (+32 more)

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

### Community 16 - "test_state_contract.py"
Cohesion: 0.08
Nodes (52): CodexReviewer, command(), material_hash(), Bounded Codex CLI reviewer. Broker credentials and tools are not inherited., observe(), Point-in-time evidence screening; language models cannot override vetoes., screen(), validate_review() (+44 more)

### Community 17 - "timestamp"
Cohesion: 0.22
Nodes (18): evaluate(), floor(), Quote-only liquidity experiment. No orders, fills, positions, P&L or promotion., turnover(), walk(), Same-venue REST book/quote validation. Visible depth never guarantees a fill., _validate(), validate_book() (+10 more)

### Community 18 - "motion.tsx"
Cohesion: 0.11
Nodes (17): AnimationProvider(), initialMode(), initialSystem(), LoadingPanel(), Mode, readMode(), readSystem(), Reveal() (+9 more)

### Community 19 - "health-page.tsx"
Cohesion: 0.10
Nodes (26): metadata, HealthDetails(), HealthFooterStatus(), HealthMap(), HealthPage(), HealthSummary(), attention, inTopic() (+18 more)

### Community 20 - "liquidity_runner.py"
Cohesion: 0.23
Nodes (21): digest(), intelligence(), Policy, binding(), get(), get_inventory_status(), hashes(), load() (+13 more)

### Community 21 - "relay.ts"
Cohesion: 0.07
Nodes (31): dynamic, metadata, Page(), Context, dynamic, GET(), POST(), runtime (+23 more)

### Community 22 - "replay_runner.py"
Cohesion: 0.33
Nodes (10): build_report(), code_hashes(), connect_readonly(), export_events(), Read-only ledger export, fixed future window and offline stress receipts. No…, register_holdout(), report_state(), summary() (+2 more)

### Community 23 - "test_execution_pilot.py"
Cohesion: 0.24
Nodes (9): ExecutionPilot, pilot(), parametrize, test_crash_after_entry_resumes_exit_without_new_entry(), test_final_pilot_boundary_blocks_wrong_or_oversize_requests(), test_pilot_and_strategy_workers_cannot_share_authority(), test_pilot_recovers_lost_accepted_entry_without_duplicate(), test_pilot_refuses_existing_positions() (+1 more)

### Community 24 - "test_experiment.py"
Cohesion: 0.11
Nodes (26): Meetings, parse_fomc(), HTMLParser, Official FOMC meeting dates, scoped context only; no complete macro calendar., propose(), ATR14 + trend/breakout candidate and fixed fractional loss-budget sizing. All…, context(), fomc_html() (+18 more)

### Community 25 - "HealthMonitor"
Cohesion: 0.22
Nodes (7): Independent assessments from telemetry observations; no trading authority., health_inputs(), effective(), HealthMonitor, moment(), Public provider reports, separate from account/model connectivity and risk. No…, test_local_revalidation_time_is_distinct_from_provider_update_time()

### Community 26 - "test_review_repairs.py"
Cohesion: 0.14
Nodes (21): read_context(), daily_history(), fee(), fixture, parametrize, Locked review regressions. Synthetic brokers, patched models and tmp ledgers…, research_engine(), test_all_vetoed_cycle_never_calls_model() (+13 more)

### Community 27 - "test_stage2_validation.py"
Cohesion: 0.20
Nodes (13): audit_crypto(), Read-only reconciliation analysis. Hypotheses cannot become ledger entries., Compare authoritative gross executions and positions; explain, never waive. Fee…, parametrize, Synthetic decision-path and fault tests; none are broker-paper executions., reconciliation_fixture(), test_confirmed_fee_matches_and_duplicate_activity_is_not_counted_twice(), test_downstream_candidate_is_visible_but_inventory_still_vetoes() (+5 more)

### Community 28 - "devDependencies"
Cohesion: 0.04
Nodes (48): eslint, eslint-config-next, @fontsource-variable/dm-sans, @fontsource-variable/space-grotesk, dependencies, @fontsource-variable/dm-sans, @fontsource-variable/space-grotesk, motion (+40 more)

### Community 29 - "engine.py"
Cohesion: 0.22
Nodes (8): Fixed-host Alpaca paper adapter and a separately labelled durable simulator., attribute(), canonical_symbol(), Inventory attribution is evidence, not a substitute for broker availability., One explicitly authorized execution experiment; never an alpha strategy. Uses…, Credential-free local feed read; headlines remain untrusted scoped context., Explicit, bounded PAPER-only CLI. No web API can enable this pilot., One bounded GET-only research cycle on the existing paper ledger. No model.

### Community 30 - "utcnow"
Cohesion: 0.11
Nodes (10): No remote API. Fills are synthetic and do not model queueing/market impact., Simulator, utcnow(), isolate_experiment_workers(), lab_path(), main(), Bounded, GET-only Alpaca dogfood session using a private copied ledger., main() (+2 more)

### Community 31 - "overview-page.tsx"
Cohesion: 0.13
Nodes (22): HealthChanges(), OrderDialog(), AssetBar(), EquityChart(), ExecutionStream(), ModeBadge(), OverviewPage(), views (+14 more)

### Community 33 - "intelligence.py"
Cohesion: 0.17
Nodes (12): ASTRAL paper-only service., clean(), date(), named(), parse(), Independent public intelligence collector. No broker, credentials or order…, safe_url(), Source (+4 more)

### Community 35 - "decide"
Cohesion: 0.27
Nodes (13): Isolated deterministic portfolio execution model. No broker or Store imports.…, decide(), Deterministic timing hypotheses. Produces candidates, never orders or fills., One-unit synthetic quote replay, with fills strictly AFTER decisions. Quote-…, replay(), event(), parametrize, test_entry_cancels_if_research_expires_during_latency() (+5 more)

### Community 37 - "validate_pr_body.cjs"
Cohesion: 0.23
Nodes (11): fs, main(), readableText(), REQUIRED_CHECKS, REQUIRED_SECTIONS, sections(), validatePullRequestBody(), withoutComments() (+3 more)

### Community 38 - "datetime"
Cohesion: 0.13
Nodes (18): parse_bea(), HTMLParser, Scoped BEA schedule; a date is retained without inventing an unspecified…, Schedule, view(), datetime, bea_html(), fee() (+10 more)

### Community 40 - "overnight_watch.py"
Cohesion: 0.25
Nodes (9): audit(), now(), Bounded overnight observation of the existing GET-only localhost paper lab., safety(), watch(), write_summary(), parametrize, test_observer_counts_lost_write_and_http_failure() (+1 more)

### Community 41 - "Store"
Cohesion: 0.14
Nodes (14): collect(), lifespan(), Local-only companion: independent DB and lifecycle preserve the shadow pilot., Collector, Store, test_maintenance_empty_snapshot_304_extends_inspection_not_publication(), parametrize, test_collection_loop_delays_after_failure_continues_and_propagates_cancel() (+6 more)

### Community 42 - "HealthEngine"
Cohesion: 0.26
Nodes (5): lifespan(), Standalone health service, separate process and ledger from telemetry/trading., state(), fresh(), HealthEngine

### Community 44 - "experiment.py"
Cohesion: 0.27
Nodes (10): contract(), diagnose(), Frozen research contract and append-only observations. No execution interface., Retrospective price-only prefixes. Never pretend these were known earlier., register(), source_hashes(), state(), main() (+2 more)

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

### Community 53 - "packet-dialog.tsx"
Cohesion: 0.21
Nodes (9): Dialog(), IntelligenceFeed(), SourceDialog(), ViewDialog(), Detail, EvidenceDialog(), Evidence(), SourceLink() (+1 more)

### Community 63 - "test_trade_history.py"
Cohesion: 0.30
Nodes (10): aggregate_daily(), Build daily candles exclusively from documented execution records., aggregate(), batch(), parametrize, test_bad_trade_records_fail_closed(), test_history_shares_completed_days_and_reconstructs_each_immutable_batch(), test_missing_trade_day_is_not_filled_from_quotes() (+2 more)

## Knowledge Gaps
- **154 isolated node(s):** `Source`, `metadata`, `dynamic`, `runtime`, `dynamic` (+149 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Store` connect `Store` to `test_event_sources.py`, `BrokerFailure`, `run`, `test_accounting_engine.py`, `test_health_engine.py`, `D`, `datetime`, `test_learning_engine.py`, `HealthEngine`, `Settings`, `experiment.py`, `test_state_contract.py`, `timestamp`, `test_experiment.py`, `test_review_repairs.py`, `engine.py`, `utcnow`, `test_trade_history.py`?**
  _High betweenness centrality (0.042) - this node is a cross-community bridge._
- **Why does `utcnow()` connect `utcnow` to `test_event_sources.py`, `BrokerFailure`, `intelligence.py`, `test_accounting_engine.py`, `run`, `test_health_engine.py`, `datetime`, `Engine`, `Store`, `HealthEngine`, `Settings`, `experiment.py`, `test_state_contract.py`, `test_execution_pilot.py`, `HealthMonitor`, `test_review_repairs.py`, `engine.py`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **Why does `Engine` connect `Engine` to `BrokerFailure`, `run`, `D`, `Settings`, `experiment.py`, `test_state_contract.py`, `test_execution_pilot.py`, `test_experiment.py`, `test_review_repairs.py`, `test_stage2_validation.py`, `engine.py`, `utcnow`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `Store` (e.g. with `ExitPlan` and `Halt`) actually correct?**
  _`Store` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `Engine` (e.g. with `ExitPlan` and `Halt`) actually correct?**
  _`Engine` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 30 inferred relationships involving `D()` (e.g. with `diagnose()` and `validate_activity()`) actually correct?**
  _`D()` has 30 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Source`, `metadata`, `dynamic` to the rest of the system?**
  _154 weakly-connected nodes found - possible documentation gaps or missing edges._