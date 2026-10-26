# Graph Report - astral-trading  (2026-10-26)

## Corpus Check
- 196 files · ~71,223 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1306 nodes · 3854 edges · 64 communities (53 shown, 11 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 135 edges (avg confidence: 0.64)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `80515691`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_event_sources.py
- BrokerFailure
- run
- test_accounting_engine.py
- HealthMonitor
- D
- ui.ts
- test_learning_engine.py
- test_state_contract.py
- Engine
- scripts
- research-lab.tsx
- test_quantconnect_validation.py
- compilerOptions
- contracts.ts
- support.cjs
- dumps
- timestamp
- motion.tsx
- health-page.tsx
- liquidity_runner.py
- relay.ts
- experiment.py
- utcnow
- test_health_engine.py
- test_experiment.py
- test_review_repairs.py
- overview-page.tsx
- devDependencies
- dependencies
- test_stage2_validation.py
- intelligence-feed.tsx
- Source
- intelligence.py
- Settings
- decide
- HealthEngine
- validate_pr_body.cjs
- datetime
- Connection
- overnight_watch.py
- intelligence_app.py
- app.spec.ts
- Schedule
- StatusHeading
- useDashboard
- scripts
- boundaries.test.ts
- health-galaxy.js
- check-skills.cjs
- navigation.tsx
- frontend/package.json
- commitlint.config.cjs
- quantconnect/__init__.py
- proxy.ts
- next.config.ts
- tailwindcss
- typescript
- prepare-standalone.mjs
- test_trade_history.py
- Store

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
- `Stream` --uses--> `RuleViolation`  [INFERRED]
  tests/test_state_contract.py → backend/engine.py
- `Stream` --uses--> `Engine`  [INFERRED]
  tests/test_state_contract.py → backend/engine.py

## Import Cycles
- None detected.

## Communities (64 total, 11 thin omitted)

### Community 0 - "test_event_sources.py"
Cohesion: 0.12
Nodes (23): catalog(), Cells, event(), maintenance(), nyfed(), parse_events(), protocol(), HTMLParser (+15 more)

### Community 1 - "BrokerFailure"
Cohesion: 0.21
Nodes (4): AlpacaPaper, BrokerFailure, Limiter, Exception

### Community 2 - "run"
Cohesion: 0.11
Nodes (43): Failure scenarios and adversarial selection cases; all trades are synthetic., test_ambiguous_fee_is_not_assigned_to_a_strategy(), test_intraday_exit_cannot_liquidate_swing_inventory(), test_late_confirmed_asset_fee_is_idempotent_and_reconciles(), test_local_exit_survives_restart_and_unknown_response(), test_quantity_and_shared_risk_boundaries(), test_read_only_adapter_blocks_post_and_delete_before_transport(), test_readback_422_after_accepted_order_never_releases_reservation() (+35 more)

### Community 3 - "test_accounting_engine.py"
Cohesion: 0.11
Nodes (47): at(), canonical(), cost_report(), digest(), evaluate(), main(), number(), precise() (+39 more)

### Community 4 - "HealthMonitor"
Cohesion: 0.22
Nodes (7): Independent assessments from telemetry observations; no trading authority., health_inputs(), effective(), HealthMonitor, moment(), Public provider reports, separate from account/model connectivity and risk. No…, test_local_revalidation_time_is_distinct_from_provider_update_time()

### Community 5 - "D"
Cohesion: 0.10
Nodes (39): D(), No remote API. Fills are synthetic and do not model queueing/market impact., Simulator, Assumptions, Portfolio, replay(), stress_suite(), synthetic_events() (+31 more)

### Community 6 - "ui.ts"
Cohesion: 0.15
Nodes (20): AccountingBoundaries(), AccountingCosts(), AccountingGross(), AccountingRecords(), AccountingSummary(), amounts(), LearningBoundaries(), LearningInventory() (+12 more)

### Community 7 - "test_learning_engine.py"
Cohesion: 0.15
Nodes (39): digest(), encode(), evaluate(), main(), markdown(), packet_checks(), protected(), protected_windows() (+31 more)

### Community 8 - "test_state_contract.py"
Cohesion: 0.18
Nodes (23): at(), build_state(), buy(), free_port(), normalize(), pin_clock(), parametrize, Dashboard read-path contract: fixed Store-seeded ledgers and a pinned clock.… (+15 more)

### Community 9 - "Engine"
Cohesion: 0.09
Nodes (22): ExitPlan, Halt, Intent, ResearchBar, RiskCandidate, age(), Engine, Exception (+14 more)

### Community 10 - "scripts"
Cohesion: 0.05
Nodes (37): @commitlint/cli, @commitlint/config-conventional, @commitlint/lint, @commitlint/load, husky, devDependencies, @commitlint/cli, @commitlint/config-conventional (+29 more)

### Community 11 - "research-lab.tsx"
Cohesion: 0.23
Nodes (13): Detail, EvidenceDialog(), PacketDialog(), ResearchExperiments(), ResearchGates(), ResearchPackets(), ResearchStatus(), ShadowDecisions() (+5 more)

### Community 12 - "test_quantconnect_validation.py"
Cohesion: 0.12
Nodes (30): QCAlgorithm, AstralBtcSignalParity, Cloud entry point; package with compare prepare before uploading main.py., bundle(), compare(), main(), new_output(), pinned_sources() (+22 more)

### Community 13 - "compilerOptions"
Cohesion: 0.07
Nodes (29): compilerOptions, allowJs, checkJs, esModuleInterop, incremental, isolatedModules, jsx, lib (+21 more)

### Community 14 - "contracts.ts"
Cohesion: 0.09
Nodes (30): RootLayout(), empty, Seed, Snapshot, amount, counts, Dashboard, dashboardSchema (+22 more)

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

### Community 16 - "dumps"
Cohesion: 0.16
Nodes (24): CodexReviewer, command(), material_hash(), Bounded Codex CLI reviewer. Broker credentials and tools are not inherited., screen(), validate_review(), dumps(), parametrize (+16 more)

### Community 17 - "timestamp"
Cohesion: 0.18
Nodes (14): Validate provider fee records without estimating missing fees or rewriting…, validate_activity(), Same-venue REST book/quote validation. Visible depth never guarantees a fill., _validate(), validate_book(), Isolated deterministic portfolio execution model. No broker or Store imports.…, Evidence-by-evidence readiness. No threshold changes or execution capability., floor_step() (+6 more)

### Community 18 - "motion.tsx"
Cohesion: 0.10
Nodes (19): MarketUniverse(), AnimationProvider(), initialMode(), initialSystem(), LoadingPanel(), Mode, readMode(), readSystem() (+11 more)

### Community 19 - "health-page.tsx"
Cohesion: 0.14
Nodes (18): metadata, HealthDetails(), HealthMap(), HealthPage(), HealthSummary(), attention, inTopic(), reportedNodes() (+10 more)

### Community 20 - "liquidity_runner.py"
Cohesion: 0.13
Nodes (34): intelligence(), evaluate(), floor(), Policy, Quote-only liquidity experiment. No orders, fills, positions, P&L or promotion., binding(), get(), get_inventory_status() (+26 more)

### Community 21 - "relay.ts"
Cohesion: 0.07
Nodes (34): dynamic, metadata, Page(), Context, dynamic, GET(), POST(), runtime (+26 more)

### Community 22 - "experiment.py"
Cohesion: 0.14
Nodes (26): contract(), diagnose(), digest(), observe(), Frozen research contract and append-only observations. No execution interface., Retrospective price-only prefixes. Never pretend these were known earlier., register(), source_hashes() (+18 more)

### Community 23 - "utcnow"
Cohesion: 0.12
Nodes (21): Fixed-host Alpaca paper adapter and a separately labelled durable simulator., Retain scoped official calendar catalogs; never certify missing categories., record_fee(), attribute(), canonical_symbol(), Inventory attribution is evidence, not a substitute for broker availability., One explicitly authorized execution experiment; never an alpha strategy. Uses…, Credential-free local feed read; headlines remain untrusted scoped context. (+13 more)

### Community 24 - "test_health_engine.py"
Cohesion: 0.25
Nodes (13): parse_report(), observations(), Providers, parametrize, Health contracts: temporary ledgers and HTTP fixtures; never models/brokers., report(), test_engine_health_is_separate_from_model_enablement_and_market_closure(), test_event_driven_execution_worker_is_judged_by_status_not_age() (+5 more)

### Community 25 - "test_experiment.py"
Cohesion: 0.11
Nodes (27): Meetings, parse_fomc(), HTMLParser, Official FOMC meeting dates, scoped context only; no complete macro calendar., evidence_for(), Point-in-time evidence screening; language models cannot override vetoes., propose(), ATR14 + trend/breakout candidate and fixed fractional loss-budget sizing. All… (+19 more)

### Community 26 - "test_review_repairs.py"
Cohesion: 0.21
Nodes (15): daily_history(), fee(), parametrize, Locked review regressions. Synthetic brokers, patched models and tmp ledgers…, test_all_vetoed_cycle_never_calls_model(), test_diagnostic_failure_still_journals_prospective_veto(), test_distinct_lab_still_copies_or_reuses(), test_identical_fee_duplicates_and_later_execution_are_idempotent() (+7 more)

### Community 27 - "overview-page.tsx"
Cohesion: 0.14
Nodes (21): HealthChanges(), OrderDialog(), AssetBar(), EquityChart(), ExecutionStream(), OverviewFooter(), OverviewPage(), views (+13 more)

### Community 28 - "devDependencies"
Cohesion: 0.12
Nodes (17): eslint, eslint-config-next, devDependencies, eslint, eslint-config-next, @playwright/test, @tailwindcss/postcss, @types/node (+9 more)

### Community 29 - "dependencies"
Cohesion: 0.12
Nodes (17): @fontsource-variable/dm-sans, @fontsource-variable/space-grotesk, dependencies, @fontsource-variable/dm-sans, @fontsource-variable/space-grotesk, motion, next, react (+9 more)

### Community 30 - "test_stage2_validation.py"
Cohesion: 0.20
Nodes (13): audit_crypto(), Read-only reconciliation analysis. Hypotheses cannot become ledger entries., Compare authoritative gross executions and positions; explain, never waive. Fee…, engine(), fixture, parametrize, Synthetic decision-path and fault tests; none are broker-paper executions., reconciliation_fixture() (+5 more)

### Community 31 - "intelligence-feed.tsx"
Cohesion: 0.20
Nodes (8): Dialog(), IntelligenceFeed(), SourceDialog(), ViewDialog(), IntelligenceView(), Empty(), SourceLink(), News

### Community 33 - "intelligence.py"
Cohesion: 0.13
Nodes (19): ASTRAL paper-only service., clean(), Collector, date(), named(), parse(), Independent public intelligence collector. No broker, credentials or order…, safe_url() (+11 more)

### Community 34 - "Settings"
Cohesion: 0.21
Nodes (11): create_app(), Settings, test_api_shadow_does_not_enable_orders_and_rejects_bypass_fields(), test_local_health_inputs_are_small_read_only_and_do_not_export_account_data(), test_quote_adapter_preserves_prices_and_units_unknown_if_book_fails(), test_quote_adapter_retains_raw_book_and_versions_new_normalization(), fixture, research_engine() (+3 more)

### Community 35 - "decide"
Cohesion: 0.29
Nodes (13): decide(), Deterministic timing hypotheses. Produces candidates, never orders or fills., One-unit synthetic quote replay, with fills strictly AFTER decisions. Quote-…, replay(), test_disabled_model_keeps_deterministic_arm_in_new_observations(), event(), parametrize, test_entry_cancels_if_research_expires_during_latency() (+5 more)

### Community 36 - "HealthEngine"
Cohesion: 0.26
Nodes (5): lifespan(), Standalone health service, separate process and ledger from telemetry/trading., state(), fresh(), HealthEngine

### Community 37 - "validate_pr_body.cjs"
Cohesion: 0.23
Nodes (11): fs, main(), readableText(), REQUIRED_CHECKS, REQUIRED_SECTIONS, sections(), validatePullRequestBody(), withoutComments() (+3 more)

### Community 38 - "datetime"
Cohesion: 0.14
Nodes (24): parse_bea(), Scoped BEA schedule; a date is retained without inventing an unspecified…, Maintenance needs two current publisher lists. NY Fed remains partial BLS., retain_additional_scopes(), retain_scopes(), calendar_coverage(), All scoped categories need retained, current, forward-covering evidence.…, view() (+16 more)

### Community 40 - "overnight_watch.py"
Cohesion: 0.25
Nodes (9): audit(), now(), Bounded overnight observation of the existing GET-only localhost paper lab., safety(), watch(), write_summary(), parametrize, test_observer_counts_lost_write_and_http_failure() (+1 more)

### Community 41 - "intelligence_app.py"
Cohesion: 0.50
Nodes (4): collect(), lifespan(), Local-only companion: independent DB and lifecycle preserve the shadow pilot., test_collection_loop_delays_after_failure_continues_and_propagates_cancel()

### Community 45 - "useDashboard"
Cohesion: 0.14
Nodes (17): dynamic, metadata, HealthFooterStatus(), ModeBadge(), StrategiesView(), StrategyCounts(), SystemView(), Context (+9 more)

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

### Community 63 - "test_trade_history.py"
Cohesion: 0.38
Nodes (9): aggregate_daily(), aggregate(), batch(), parametrize, test_bad_trade_records_fail_closed(), test_history_shares_completed_days_and_reconstructs_each_immutable_batch(), test_missing_trade_day_is_not_filled_from_quotes(), test_provider_pagination_must_finish_before_history_is_accepted() (+1 more)

### Community 64 - "Store"
Cohesion: 0.23
Nodes (4): Store, parametrize, test_unexpected_source_failure_keeps_other_feed_alive_and_recovers(), test_replay_report_is_visible_only_in_the_book_that_records_its_receipt()

## Knowledge Gaps
- **155 isolated node(s):** `Source`, `metadata`, `dynamic`, `runtime`, `dynamic` (+150 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Store` connect `Store` to `test_event_sources.py`, `run`, `test_accounting_engine.py`, `D`, `test_learning_engine.py`, `test_state_contract.py`, `Engine`, `dumps`, `liquidity_runner.py`, `experiment.py`, `utcnow`, `test_health_engine.py`, `test_experiment.py`, `test_review_repairs.py`, `test_stage2_validation.py`, `intelligence.py`, `Settings`, `HealthEngine`, `datetime`, `intelligence_app.py`, `test_trade_history.py`?**
  _High betweenness centrality (0.035) - this node is a cross-community bridge._
- **Why does `utcnow()` connect `utcnow` to `Store`, `BrokerFailure`, `Settings`, `intelligence.py`, `HealthMonitor`, `D`, `HealthEngine`, `datetime`, `run`, `Engine`, `test_event_sources.py`, `dumps`, `timestamp`, `experiment.py`, `test_health_engine.py`, `test_review_repairs.py`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Why does `Engine` connect `Engine` to `Store`, `BrokerFailure`, `Settings`, `run`, `D`, `test_state_contract.py`, `dumps`, `experiment.py`, `utcnow`, `test_experiment.py`, `test_review_repairs.py`, `test_stage2_validation.py`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `Store` (e.g. with `ExitPlan` and `Halt`) actually correct?**
  _`Store` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `Engine` (e.g. with `ExitPlan` and `Halt`) actually correct?**
  _`Engine` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 30 inferred relationships involving `D()` (e.g. with `diagnose()` and `validate_activity()`) actually correct?**
  _`D()` has 30 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Source`, `metadata`, `dynamic` to the rest of the system?**
  _155 weakly-connected nodes found - possible documentation gaps or missing edges._