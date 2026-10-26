# Graph Report - astral-trading  (2026-10-26)

## Corpus Check
- 191 files · ~69,151 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1266 nodes · 3761 edges · 66 communities (55 shown, 11 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 135 edges (avg confidence: 0.64)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b87a15e1`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_event_sources.py
- BrokerFailure
- run
- test_accounting_engine.py
- test_health_engine.py
- test_portfolio_replay.py
- ui.ts
- test_learning_engine.py
- test_state_contract.py
- Engine
- scripts
- useDashboard
- test_execution_pilot.py
- compilerOptions
- contracts.ts
- support.cjs
- datetime
- timestamp
- motion.tsx
- health-page.tsx
- liquidity_runner.py
- relay.ts
- strategies-view.tsx
- Store
- parse_fomc
- test_experiment.py
- test_review_repairs.py
- asset-bar.tsx
- devDependencies
- dependencies
- Simulator
- overview-page.tsx
- connection.test.ts
- intelligence.py
- Portfolio
- decide
- accounting/page.tsx
- validate_pr_body.cjs
- test_readiness_gates.py
- Connection
- overnight_watch.py
- Collector
- retain_scopes
- parse_bea
- Cells
- read.ts
- scripts
- boundaries.test.ts
- health-galaxy.js
- check-skills.cjs
- navigation.tsx
- frontend/package.json
- commitlint.config.cjs
- test_liquidity_experiment.py
- read.test.ts
- proxy.ts
- next.config.ts
- tailwindcss
- typescript
- prepare-standalone.mjs
- test_trade_history.py
- test_unexpected_source_failure_keeps_other_feed_alive_and_recovers
- controlled_reads

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
- `test_cancel_keeps_reservation_and_models_fill_race_until_ack()` --calls--> `D()`  [INFERRED]
  tests/test_portfolio_replay.py → backend/broker.py
- `test_cash_exhaustion_and_pending_orders_never_double_spend()` --calls--> `D()`  [INFERRED]
  tests/test_portfolio_replay.py → backend/broker.py
- `test_cash_is_reserved_before_fill_and_price_collar_bounds_purchase()` --calls--> `D()`  [INFERRED]
  tests/test_portfolio_replay.py → backend/broker.py
- `test_disconnect_and_unliquidated_position_remain_visible()` --calls--> `D()`  [INFERRED]
  tests/test_portfolio_replay.py → backend/broker.py
- `test_exit_attempt_limit_preserves_unliquidated_quantity()` --calls--> `D()`  [INFERRED]
  tests/test_portfolio_replay.py → backend/broker.py

## Import Cycles
- None detected.

## Communities (66 total, 11 thin omitted)

### Community 0 - "test_event_sources.py"
Cohesion: 0.22
Nodes (16): catalog(), event(), maintenance(), nyfed(), parse_events(), protocol(), Fixed public event sources. Published context is distinct from complete…, Watch authoritative documents without interpreting proposals as activations. (+8 more)

### Community 1 - "BrokerFailure"
Cohesion: 0.21
Nodes (4): AlpacaPaper, BrokerFailure, Limiter, Exception

### Community 2 - "run"
Cohesion: 0.11
Nodes (46): D(), Failure scenarios and adversarial selection cases; all trades are synthetic., test_ambiguous_fee_is_not_assigned_to_a_strategy(), test_api_shadow_does_not_enable_orders_and_rejects_bypass_fields(), test_intraday_exit_cannot_liquidate_swing_inventory(), test_late_confirmed_asset_fee_is_idempotent_and_reconciles(), test_local_exit_survives_restart_and_unknown_response(), test_quantity_and_shared_risk_boundaries() (+38 more)

### Community 3 - "test_accounting_engine.py"
Cohesion: 0.09
Nodes (56): at(), canonical(), cost_report(), digest(), evaluate(), main(), number(), precise() (+48 more)

### Community 4 - "test_health_engine.py"
Cohesion: 0.08
Nodes (27): lifespan(), Standalone health service, separate process and ledger from telemetry/trading., state(), fresh(), HealthEngine, Independent assessments from telemetry observations; no trading authority., health_inputs(), effective() (+19 more)

### Community 5 - "test_portfolio_replay.py"
Cohesion: 0.14
Nodes (45): Assumptions, replay(), build_report(), code_hashes(), connect_readonly(), export_events(), Read-only ledger export, fixed future window and offline stress receipts. No…, register_holdout() (+37 more)

### Community 6 - "ui.ts"
Cohesion: 0.15
Nodes (20): AccountingBoundaries(), AccountingCosts(), AccountingGross(), AccountingRecords(), AccountingSummary(), amounts(), LearningBoundaries(), LearningInventory() (+12 more)

### Community 7 - "test_learning_engine.py"
Cohesion: 0.15
Nodes (39): digest(), encode(), evaluate(), main(), markdown(), packet_checks(), protected(), protected_windows() (+31 more)

### Community 8 - "test_state_contract.py"
Cohesion: 0.15
Nodes (23): at(), build_state(), buy(), free_port(), normalize(), pin_clock(), parametrize, Dashboard read-path contract: fixed Store-seeded ledgers and a pinned clock.… (+15 more)

### Community 9 - "Engine"
Cohesion: 0.16
Nodes (5): age(), Engine, symbol_for(), book_for(), utcnow()

### Community 10 - "scripts"
Cohesion: 0.05
Nodes (37): @commitlint/cli, @commitlint/config-conventional, @commitlint/lint, @commitlint/load, husky, devDependencies, @commitlint/cli, @commitlint/config-conventional (+29 more)

### Community 11 - "useDashboard"
Cohesion: 0.14
Nodes (23): HealthFooterStatus(), EquityChart(), ModeBadge(), OverviewFooter(), Context, useDashboard(), Detail, EvidenceDialog() (+15 more)

### Community 12 - "test_execution_pilot.py"
Cohesion: 0.21
Nodes (10): ExecutionPilot, One explicitly authorized execution experiment; never an alpha strategy. Uses…, pilot(), parametrize, test_crash_after_entry_resumes_exit_without_new_entry(), test_final_pilot_boundary_blocks_wrong_or_oversize_requests(), test_pilot_and_strategy_workers_cannot_share_authority(), test_pilot_recovers_lost_accepted_entry_without_duplicate() (+2 more)

### Community 13 - "compilerOptions"
Cohesion: 0.07
Nodes (29): compilerOptions, allowJs, checkJs, esModuleInterop, incremental, isolatedModules, jsx, lib (+21 more)

### Community 14 - "contracts.ts"
Cohesion: 0.08
Nodes (25): api(), errorMessage(), empty, Snapshot, amount, counts, Dashboard, dashboardSchema (+17 more)

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

### Community 16 - "datetime"
Cohesion: 0.11
Nodes (33): Fixed-host Alpaca paper adapter and a separately labelled durable simulator., CodexReviewer, command(), material_hash(), Bounded Codex CLI reviewer. Broker credentials and tools are not inherited., attribute(), canonical_symbol(), Inventory attribution is evidence, not a substitute for broker availability. (+25 more)

### Community 17 - "timestamp"
Cohesion: 0.21
Nodes (16): evaluate(), floor(), Quote-only liquidity experiment. No orders, fills, positions, P&L or promotion., turnover(), walk(), Same-venue REST book/quote validation. Visible depth never guarantees a fill., _validate(), validate_book() (+8 more)

### Community 18 - "motion.tsx"
Cohesion: 0.11
Nodes (17): AnimationProvider(), initialMode(), initialSystem(), LoadingPanel(), Mode, readMode(), readSystem(), Reveal() (+9 more)

### Community 19 - "health-page.tsx"
Cohesion: 0.14
Nodes (20): metadata, HealthChanges(), HealthDetails(), HealthMap(), HealthPage(), HealthSummary(), attention, inTopic() (+12 more)

### Community 20 - "liquidity_runner.py"
Cohesion: 0.24
Nodes (22): contract(), digest(), source_hashes(), Policy, binding(), get(), get_inventory_status(), hashes() (+14 more)

### Community 21 - "relay.ts"
Cohesion: 0.13
Nodes (17): Context, dynamic, GET(), POST(), runtime, acceptsGzip(), compress, getPaths (+9 more)

### Community 23 - "Store"
Cohesion: 0.09
Nodes (36): create_app(), ExitPlan, Halt, Intent, ResearchBar, RiskCandidate, Settings, Exception (+28 more)

### Community 24 - "parse_fomc"
Cohesion: 0.25
Nodes (4): Meetings, parse_fomc(), HTMLParser, Official FOMC meeting dates, scoped context only; no complete macro calendar.

### Community 25 - "test_experiment.py"
Cohesion: 0.15
Nodes (25): diagnose(), Retrospective price-only prefixes. Never pretend these were known earlier., price_signal(), propose(), ATR14 + trend/breakout candidate and fixed fractional loss-budget sizing. All…, Pure OHLC hypothesis; caller validates provenance and time separately., context(), fomc_html() (+17 more)

### Community 26 - "test_review_repairs.py"
Cohesion: 0.12
Nodes (24): observe(), Frozen research contract and append-only observations. No execution interface., register(), state(), read_context(), Register once; run offline diagnostic from an existing read-only history DB.…, test_observations_deduplicate_and_do_not_create_trades(), daily_history() (+16 more)

### Community 27 - "asset-bar.tsx"
Cohesion: 0.26
Nodes (10): MarketUniverse(), OrderDialog(), AssetBar(), Context, Selection, useSelection(), UniverseSection(), createMarketUniverse() (+2 more)

### Community 28 - "devDependencies"
Cohesion: 0.12
Nodes (17): eslint, eslint-config-next, devDependencies, eslint, eslint-config-next, @playwright/test, @tailwindcss/postcss, @types/node (+9 more)

### Community 29 - "dependencies"
Cohesion: 0.12
Nodes (17): @fontsource-variable/dm-sans, @fontsource-variable/space-grotesk, dependencies, @fontsource-variable/dm-sans, @fontsource-variable/space-grotesk, motion, next, react (+9 more)

### Community 31 - "overview-page.tsx"
Cohesion: 0.13
Nodes (18): Dialog(), ExecutionStream(), IntelligenceFeed(), OverviewPage(), views, PortfolioCards(), PositionsPanel(), SelectionState() (+10 more)

### Community 32 - "connection.test.ts"
Cohesion: 0.17
Nodes (7): Seed, seed(), Source, dashboard(), health(), now, services()

### Community 33 - "intelligence.py"
Cohesion: 0.17
Nodes (12): ASTRAL paper-only service., clean(), date(), named(), parse(), Independent public intelligence collector. No broker, credentials or order…, safe_url(), Source (+4 more)

### Community 35 - "decide"
Cohesion: 0.32
Nodes (12): decide(), Deterministic timing hypotheses. Produces candidates, never orders or fills., One-unit synthetic quote replay, with fills strictly AFTER decisions. Quote-…, replay(), event(), parametrize, test_entry_cancels_if_research_expires_during_latency(), test_entry_timing_fail_closed() (+4 more)

### Community 36 - "accounting/page.tsx"
Cohesion: 0.18
Nodes (12): dynamic, metadata, Page(), dynamic, metadata, Page(), AccountingContent(), LearningContent() (+4 more)

### Community 37 - "validate_pr_body.cjs"
Cohesion: 0.23
Nodes (11): fs, main(), readableText(), REQUIRED_CHECKS, REQUIRED_SECTIONS, sections(), validatePullRequestBody(), withoutComments() (+3 more)

### Community 38 - "test_readiness_gates.py"
Cohesion: 0.16
Nodes (21): Validate provider fee records without estimating missing fees or rewriting…, record_fee(), validate_activity(), calendar_coverage(), Evidence-by-evidence readiness. No threshold changes or execution capability., All scoped categories need retained, current, forward-covering evidence.…, view(), book() (+13 more)

### Community 40 - "overnight_watch.py"
Cohesion: 0.25
Nodes (9): audit(), now(), Bounded overnight observation of the existing GET-only localhost paper lab., safety(), watch(), write_summary(), parametrize, test_observer_counts_lost_write_and_http_failure() (+1 more)

### Community 41 - "Collector"
Cohesion: 0.22
Nodes (11): collect(), intelligence(), lifespan(), Local-only companion: independent DB and lifecycle preserve the shadow pilot., Collector, test_collection_loop_delays_after_failure_continues_and_propagates_cancel(), test_collector_fetch_propagates_cancellation(), test_contact_and_access_denial_do_not_leak_or_retry() (+3 more)

### Community 42 - "retain_scopes"
Cohesion: 0.21
Nodes (11): Retain scoped official calendar catalogs; never certify missing categories., Maintenance needs two current publisher lists. NY Fed remains partial BLS., retain_additional_scopes(), retain_scopes(), evidence_for(), context(), parametrize, test_active_overrun_and_catalog_event_hidden_by_ui_cap_still_veto() (+3 more)

### Community 43 - "parse_bea"
Cohesion: 0.20
Nodes (6): parse_bea(), HTMLParser, Scoped BEA schedule; a date is retained without inventing an unspecified…, Schedule, bea_html(), test_bea_dates_preserve_clock_text_without_inventing_release_timezone()

### Community 44 - "Cells"
Cohesion: 0.29
Nodes (3): Cells, HTMLParser, Retain cells in a selected table, including links and their following text.

### Community 45 - "read.ts"
Cohesion: 0.21
Nodes (10): dynamic, metadata, RootLayout(), Provider(), AppFrame(), healthSchema, ReadResult, loadSeed() (+2 more)

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

### Community 53 - "test_liquidity_experiment.py"
Cohesion: 0.48
Nodes (6): append(), inputs(), parametrize, test_baseline_rejects_while_separate_half_depth_model_can_cover_25(), test_corrupt_stale_and_unverified_evidence_does_not_become_liquidity_pass(), test_daily_turnover_cap_and_fee_reduced_exit_minimum_are_binding()

### Community 63 - "test_trade_history.py"
Cohesion: 0.57
Nodes (6): aggregate(), batch(), parametrize, test_bad_trade_records_fail_closed(), test_missing_trade_day_is_not_filled_from_quotes(), test_trade_only_bars_deduplicate_and_exclude_incomplete_day()

### Community 65 - "controlled_reads"
Cohesion: 0.67
Nodes (3): controlled_reads(), middleware, Request

## Knowledge Gaps
- **155 isolated node(s):** `Source`, `metadata`, `dynamic`, `runtime`, `dynamic` (+150 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Store` connect `Store` to `test_unexpected_source_failure_keeps_other_feed_alive_and_recovers`, `test_event_sources.py`, `run`, `test_accounting_engine.py`, `test_health_engine.py`, `test_portfolio_replay.py`, `test_readiness_gates.py`, `test_learning_engine.py`, `test_state_contract.py`, `Collector`, `retain_scopes`, `datetime`, `liquidity_runner.py`, `test_liquidity_experiment.py`, `test_experiment.py`, `test_review_repairs.py`, `test_trade_history.py`?**
  _High betweenness centrality (0.054) - this node is a cross-community bridge._
- **Why does `utcnow()` connect `Engine` to `test_event_sources.py`, `BrokerFailure`, `intelligence.py`, `run`, `test_health_engine.py`, `test_readiness_gates.py`, `retain_scopes`, `test_execution_pilot.py`, `datetime`, `Store`, `test_review_repairs.py`, `Simulator`?**
  _High betweenness centrality (0.033) - this node is a cross-community bridge._
- **Why does `D()` connect `run` to `Portfolio`, `decide`, `test_portfolio_replay.py`, `test_readiness_gates.py`, `test_state_contract.py`, `Engine`, `test_execution_pilot.py`, `datetime`, `timestamp`, `test_experiment.py`, `Simulator`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `Store` (e.g. with `ExitPlan` and `Halt`) actually correct?**
  _`Store` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `Engine` (e.g. with `ExitPlan` and `Halt`) actually correct?**
  _`Engine` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 30 inferred relationships involving `D()` (e.g. with `diagnose()` and `validate_activity()`) actually correct?**
  _`D()` has 30 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Source`, `metadata`, `dynamic` to the rest of the system?**
  _155 weakly-connected nodes found - possible documentation gaps or missing edges._