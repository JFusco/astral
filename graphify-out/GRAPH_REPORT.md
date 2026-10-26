# Graph Report - astral-trading  (2026-10-26)

## Corpus Check
- 192 files · ~67,464 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1270 nodes · 3786 edges · 58 communities (49 shown, 9 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 135 edges (avg confidence: 0.64)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `19c3d760`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_event_sources.py
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
- connection.test.ts
- compilerOptions
- contracts.ts
- support.cjs
- engine.py
- datetime
- motion.tsx
- health-page.tsx
- liquidity_runner.py
- relay.ts
- experiment.py
- BrokerFailure
- test_experiment.py
- test_risk.py
- seed.ts
- test_liquidity_experiment.py
- devDependencies
- strategies-view.tsx
- Simulator
- overview-page.tsx
- Source
- intelligence.py
- HealthEngine
- decide
- accounting/page.tsx
- validate_pr_body.cjs
- utcnow
- Connection
- overnight_watch.py
- Store
- parse_bea
- read.ts
- boundaries.test.ts
- check-skills.cjs
- navigation.tsx
- commitlint.config.cjs
- packet-dialog.tsx
- StatusHeading
- proxy.ts
- next.config.ts
- prepare-standalone.mjs
- test_trade_history.py
- dogfood_session.py

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
- `FixedDateTime` --uses--> `Engine`  [INFERRED]
  tests/test_state_contract.py → backend/engine.py

## Import Cycles
- None detected.

## Communities (58 total, 9 thin omitted)

### Community 0 - "test_event_sources.py"
Cohesion: 0.11
Nodes (24): catalog(), Cells, event(), maintenance(), nyfed(), parse_events(), protocol(), HTMLParser (+16 more)

### Community 2 - "run"
Cohesion: 0.05
Nodes (92): create_app(), Settings, read_context(), audit_crypto(), Read-only reconciliation analysis. Hypotheses cannot become ledger entries., Compare authoritative gross executions and positions; explain, never waive. Fee…, Failure scenarios and adversarial selection cases; all trades are synthetic., test_ambiguous_fee_is_not_assigned_to_a_strategy() (+84 more)

### Community 3 - "test_accounting_engine.py"
Cohesion: 0.11
Nodes (50): at(), canonical(), cost_report(), digest(), evaluate(), main(), number(), precise() (+42 more)

### Community 4 - "test_health_engine.py"
Cohesion: 0.16
Nodes (17): effective(), HealthMonitor, parse_report(), Public provider reports, separate from account/model connectivity and risk. No…, observations(), Providers, parametrize, Health contracts: temporary ledgers and HTTP fixtures; never models/brokers. (+9 more)

### Community 5 - "D"
Cohesion: 0.11
Nodes (49): D(), Assumptions, Portfolio, Isolated deterministic portfolio execution model. No broker or Store imports.…, replay(), build_report(), code_hashes(), connect_readonly() (+41 more)

### Community 6 - "ui.ts"
Cohesion: 0.15
Nodes (20): AccountingBoundaries(), AccountingCosts(), AccountingGross(), AccountingRecords(), AccountingSummary(), amounts(), LearningBoundaries(), LearningInventory() (+12 more)

### Community 7 - "test_learning_engine.py"
Cohesion: 0.13
Nodes (43): digest(), encode(), evaluate(), main(), markdown(), packet_checks(), protected(), protected_windows() (+35 more)

### Community 8 - "test_state_contract.py"
Cohesion: 0.18
Nodes (23): at(), build_state(), buy(), free_port(), normalize(), pin_clock(), parametrize, Dashboard read-path contract: fixed Store-seeded ledgers and a pinned clock.… (+15 more)

### Community 9 - "Engine"
Cohesion: 0.15
Nodes (6): age(), Engine, symbol_for(), book_for(), dumps(), test_adapter_hashes_are_cached_local_and_covered_by_packet_hash()

### Community 10 - "scripts"
Cohesion: 0.05
Nodes (37): @commitlint/cli, @commitlint/config-conventional, @commitlint/lint, @commitlint/load, husky, devDependencies, @commitlint/cli, @commitlint/config-conventional (+29 more)

### Community 11 - "useDashboard"
Cohesion: 0.15
Nodes (22): HealthFooterStatus(), ConnectionBanner(), EquityChart(), ModeBadge(), OverviewFooter(), Context, useDashboard(), PacketDialog() (+14 more)

### Community 12 - "connection.test.ts"
Cohesion: 0.24
Nodes (7): Seed, Health, seed(), dashboard(), health(), now, services()

### Community 13 - "compilerOptions"
Cohesion: 0.07
Nodes (29): compilerOptions, allowJs, checkJs, esModuleInterop, incremental, isolatedModules, jsx, lib (+21 more)

### Community 14 - "contracts.ts"
Cohesion: 0.09
Nodes (24): SystemView(), api(), errorMessage(), empty, Snapshot, accountingSchema, amount, counts (+16 more)

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

### Community 16 - "engine.py"
Cohesion: 0.12
Nodes (18): Fixed-host Alpaca paper adapter and a separately labelled durable simulator., CodexReviewer, command(), material_hash(), Bounded Codex CLI reviewer. Broker credentials and tools are not inherited., attribute(), canonical_symbol(), Inventory attribution is evidence, not a substitute for broker availability. (+10 more)

### Community 17 - "datetime"
Cohesion: 0.16
Nodes (21): Retain scoped official calendar catalogs; never certify missing categories., Maintenance needs two current publisher lists. NY Fed remains partial BLS., retain_additional_scopes(), retain_scopes(), evaluate(), floor(), Quote-only liquidity experiment. No orders, fills, positions, P&L or promotion., turnover() (+13 more)

### Community 18 - "motion.tsx"
Cohesion: 0.12
Nodes (16): HealthSummary(), Heartbeat(), AnimationProvider(), initialMode(), initialSystem(), LoadingPanel(), Mode, readMode() (+8 more)

### Community 19 - "health-page.tsx"
Cohesion: 0.10
Nodes (25): metadata, HealthChanges(), HealthDetails(), HealthMap(), HealthPage(), attention, inTopic(), reportedNodes() (+17 more)

### Community 20 - "liquidity_runner.py"
Cohesion: 0.22
Nodes (22): digest(), Policy, binding(), get(), get_inventory_status(), hashes(), load(), now() (+14 more)

### Community 21 - "relay.ts"
Cohesion: 0.16
Nodes (13): Context, dynamic, GET(), POST(), runtime, acceptsGzip(), compress, getPaths (+5 more)

### Community 22 - "experiment.py"
Cohesion: 0.22
Nodes (14): contract(), diagnose(), observe(), Frozen research contract and append-only observations. No execution interface., Retrospective price-only prefixes. Never pretend these were known earlier., register(), source_hashes(), state() (+6 more)

### Community 23 - "BrokerFailure"
Cohesion: 0.17
Nodes (15): ExitPlan, Halt, Intent, ResearchBar, RiskCandidate, BrokerFailure, Exception, Exception (+7 more)

### Community 24 - "test_experiment.py"
Cohesion: 0.12
Nodes (24): Meetings, parse_fomc(), HTMLParser, Official FOMC meeting dates, scoped context only; no complete macro calendar., evidence_for(), Credential-free local feed read; headlines remain untrusted scoped context., Point-in-time evidence screening; language models cannot override vetoes., screen() (+16 more)

### Community 25 - "test_risk.py"
Cohesion: 0.22
Nodes (16): propose(), ATR14 + trend/breakout candidate and fixed fractional loss-budget sizing. All…, history(), parametrize, test_connected_research_refreshes_after_history_and_never_writes_orders(), test_diagnostic_rejects_bad_history(), test_prefix_diagnostic_reuses_live_math_and_never_assumes_fills(), inputs() (+8 more)

### Community 26 - "seed.ts"
Cohesion: 0.23
Nodes (9): dynamic, metadata, RootLayout(), Provider(), AppFrame(), healthSchema, loadSeed(), seedScope() (+1 more)

### Community 27 - "test_liquidity_experiment.py"
Cohesion: 0.43
Nodes (7): append(), inputs(), parametrize, seed(), test_baseline_rejects_while_separate_half_depth_model_can_cover_25(), test_corrupt_stale_and_unverified_evidence_does_not_become_liquidity_pass(), test_daily_turnover_cap_and_fee_reduced_exit_minimum_are_binding()

### Community 28 - "devDependencies"
Cohesion: 0.04
Nodes (48): eslint, eslint-config-next, @fontsource-variable/dm-sans, @fontsource-variable/space-grotesk, dependencies, @fontsource-variable/dm-sans, @fontsource-variable/space-grotesk, motion (+40 more)

### Community 31 - "overview-page.tsx"
Cohesion: 0.17
Nodes (17): OrderDialog(), AssetBar(), ExecutionStream(), OverviewPage(), views, PortfolioCards(), PositionsPanel(), Context (+9 more)

### Community 33 - "intelligence.py"
Cohesion: 0.16
Nodes (13): ASTRAL paper-only service., clean(), date(), named(), parse(), Independent public intelligence collector. No broker, credentials or order…, safe_url(), Source (+5 more)

### Community 34 - "HealthEngine"
Cohesion: 0.22
Nodes (7): lifespan(), Standalone health service, separate process and ledger from telemetry/trading., state(), fresh(), HealthEngine, Independent assessments from telemetry observations; no trading authority., moment()

### Community 35 - "decide"
Cohesion: 0.29
Nodes (13): decide(), Deterministic timing hypotheses. Produces candidates, never orders or fills., One-unit synthetic quote replay, with fills strictly AFTER decisions. Quote-…, replay(), test_disabled_model_keeps_deterministic_arm_in_new_observations(), event(), parametrize, test_entry_cancels_if_research_expires_during_latency() (+5 more)

### Community 36 - "accounting/page.tsx"
Cohesion: 0.17
Nodes (10): dynamic, metadata, Page(), dynamic, metadata, Page(), AccountingContent(), LearningContent() (+2 more)

### Community 37 - "validate_pr_body.cjs"
Cohesion: 0.23
Nodes (11): fs, main(), readableText(), REQUIRED_CHECKS, REQUIRED_SECTIONS, sections(), validatePullRequestBody(), withoutComments() (+3 more)

### Community 38 - "utcnow"
Cohesion: 0.19
Nodes (20): Validate provider fee records without estimating missing fees or rewriting…, record_fee(), validate_activity(), validate_book(), view(), utcnow(), bea_html(), book() (+12 more)

### Community 40 - "overnight_watch.py"
Cohesion: 0.25
Nodes (9): audit(), now(), Bounded overnight observation of the existing GET-only localhost paper lab., safety(), watch(), write_summary(), parametrize, test_observer_counts_lost_write_and_http_failure() (+1 more)

### Community 41 - "Store"
Cohesion: 0.13
Nodes (16): collect(), health_inputs(), intelligence(), lifespan(), Local-only companion: independent DB and lifecycle preserve the shadow pilot., Collector, Store, test_maintenance_empty_snapshot_304_extends_inspection_not_publication() (+8 more)

### Community 43 - "parse_bea"
Cohesion: 0.25
Nodes (4): parse_bea(), HTMLParser, Scoped BEA schedule; a date is retained without inventing an unspecified…, Schedule

### Community 45 - "read.ts"
Cohesion: 0.18
Nodes (9): ApiError, parseResponse(), read(), ReadResult, allowedHost(), originDefaults, originVariables, Service (+1 more)

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
Cohesion: 0.18
Nodes (10): Dialog(), IntelligenceFeed(), SourceDialog(), ViewDialog(), IntelligenceView(), Detail, EvidenceDialog(), Evidence() (+2 more)

### Community 63 - "test_trade_history.py"
Cohesion: 0.44
Nodes (8): aggregate_daily(), aggregate(), batch(), parametrize, test_bad_trade_records_fail_closed(), test_history_shares_completed_days_and_reconstructs_each_immutable_batch(), test_missing_trade_day_is_not_filled_from_quotes(), test_trade_only_bars_deduplicate_and_exclude_incomplete_day()

### Community 64 - "dogfood_session.py"
Cohesion: 0.32
Nodes (6): isolate_experiment_workers(), lab_path(), main(), Bounded, GET-only Alpaca dogfood session using a private copied ledger., main(), test_live_host_configuration_rejected()

## Knowledge Gaps
- **154 isolated node(s):** `items`, `name`, `private`, `version`, `type` (+149 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Store` connect `Store` to `dogfood_session.py`, `test_event_sources.py`, `run`, `HealthEngine`, `test_accounting_engine.py`, `test_health_engine.py`, `D`, `test_learning_engine.py`, `utcnow`, `test_state_contract.py`, `engine.py`, `experiment.py`, `BrokerFailure`, `test_experiment.py`, `test_risk.py`, `test_liquidity_experiment.py`, `test_trade_history.py`?**
  _High betweenness centrality (0.042) - this node is a cross-community bridge._
- **Why does `D()` connect `D` to `run`, `decide`, `utcnow`, `test_state_contract.py`, `Engine`, `engine.py`, `datetime`, `experiment.py`, `BrokerFailure`, `test_experiment.py`, `Simulator`, `test_trade_history.py`?**
  _High betweenness centrality (0.032) - this node is a cross-community bridge._
- **Why does `utcnow()` connect `utcnow` to `dogfood_session.py`, `AlpacaPaper`, `run`, `HealthEngine`, `intelligence.py`, `test_health_engine.py`, `test_event_sources.py`, `Engine`, `Store`, `engine.py`, `datetime`, `experiment.py`, `BrokerFailure`, `test_experiment.py`, `Simulator`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `Store` (e.g. with `ExitPlan` and `Halt`) actually correct?**
  _`Store` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `Engine` (e.g. with `ExitPlan` and `Halt`) actually correct?**
  _`Engine` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 30 inferred relationships involving `D()` (e.g. with `diagnose()` and `validate_activity()`) actually correct?**
  _`D()` has 30 INFERRED edges - model-reasoned connections that need verification._
- **What connects `items`, `name`, `private` to the rest of the system?**
  _154 weakly-connected nodes found - possible documentation gaps or missing edges._