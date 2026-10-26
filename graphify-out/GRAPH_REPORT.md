# Graph Report - astral-trading  (2026-10-26)

## Corpus Check
- 197 files · ~70,018 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1314 nodes · 3889 edges · 55 communities (47 shown, 8 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 135 edges (avg confidence: 0.64)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f22fbd7e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- event_sources.py
- BrokerFailure
- run
- test_accounting_engine.py
- test_health_engine.py
- test_portfolio_replay.py
- contracts.ts
- test_learning_engine.py
- Store
- Portfolio
- scripts
- useDashboard
- connection.test.ts
- compilerOptions
- provider.tsx
- support.cjs
- dumps
- parse_bea
- motion.tsx
- health-page.tsx
- liquidity_runner.py
- relay.ts
- app.spec.ts
- Source
- Meetings
- test_risk.py
- quantconnect/__init__.py
- datetime
- devDependencies
- Collector
- Engine
- overview-page.tsx
- test_review_repairs.py
- intelligence.py
- replay
- accounting/page.tsx
- validate_pr_body.cjs
- test_readiness_gates.py
- overnight_watch.py
- test_event_sources.py
- audit_crypto
- timestamp
- Connection
- boundaries.test.ts
- navigation.tsx
- check-skills.cjs
- commitlint.config.cjs
- proxy.ts
- next.config.ts
- test_quantconnect_validation.py
- prepare-standalone.mjs
- read.ts

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

## Communities (55 total, 8 thin omitted)

### Community 0 - "event_sources.py"
Cohesion: 0.16
Nodes (13): catalog(), Cells, event(), maintenance(), nyfed(), parse_events(), protocol(), HTMLParser (+5 more)

### Community 1 - "BrokerFailure"
Cohesion: 0.14
Nodes (13): AlpacaPaper, BrokerFailure, Limiter, Exception, aggregate_daily(), aggregate(), batch(), parametrize (+5 more)

### Community 2 - "run"
Cohesion: 0.09
Nodes (56): D(), Settings, Failure scenarios and adversarial selection cases; all trades are synthetic., test_ambiguous_fee_is_not_assigned_to_a_strategy(), test_api_shadow_does_not_enable_orders_and_rejects_bypass_fields(), test_intraday_exit_cannot_liquidate_swing_inventory(), test_late_confirmed_asset_fee_is_idempotent_and_reconciles(), test_local_exit_survives_restart_and_unknown_response() (+48 more)

### Community 3 - "test_accounting_engine.py"
Cohesion: 0.11
Nodes (52): at(), canonical(), cost_report(), digest(), evaluate(), main(), number(), precise() (+44 more)

### Community 4 - "test_health_engine.py"
Cohesion: 0.08
Nodes (28): lifespan(), Standalone health service, separate process and ledger from telemetry/trading., state(), fresh(), HealthEngine, Independent assessments from telemetry observations; no trading authority., effective(), HealthMonitor (+20 more)

### Community 5 - "test_portfolio_replay.py"
Cohesion: 0.14
Nodes (45): Assumptions, replay(), build_report(), code_hashes(), connect_readonly(), export_events(), Read-only ledger export, fixed future window and offline stress receipts. No…, register_holdout() (+37 more)

### Community 6 - "contracts.ts"
Cohesion: 0.11
Nodes (31): AccountingBoundaries(), AccountingCosts(), AccountingGross(), AccountingRecords(), AccountingSummary(), amounts(), LearningBoundaries(), LearningInventory() (+23 more)

### Community 7 - "test_learning_engine.py"
Cohesion: 0.13
Nodes (43): digest(), encode(), evaluate(), main(), markdown(), packet_checks(), protected(), protected_windows() (+35 more)

### Community 8 - "Store"
Cohesion: 0.06
Nodes (49): create_app(), ExitPlan, Halt, Intent, ResearchBar, RiskCandidate, Exception, RuleViolation (+41 more)

### Community 10 - "scripts"
Cohesion: 0.05
Nodes (37): @commitlint/cli, @commitlint/config-conventional, @commitlint/lint, @commitlint/load, husky, devDependencies, @commitlint/cli, @commitlint/config-conventional (+29 more)

### Community 11 - "useDashboard"
Cohesion: 0.23
Nodes (16): useDashboard(), Detail, EvidenceDialog(), PacketDialog(), ResearchExperiments(), ResearchGates(), ResearchLab(), ResearchPackets() (+8 more)

### Community 12 - "connection.test.ts"
Cohesion: 0.27
Nodes (6): Health, seed(), dashboard(), health(), now, services()

### Community 13 - "compilerOptions"
Cohesion: 0.07
Nodes (29): compilerOptions, allowJs, checkJs, esModuleInterop, incremental, isolatedModules, jsx, lib (+21 more)

### Community 14 - "provider.tsx"
Cohesion: 0.10
Nodes (21): dynamic, metadata, Context, Provider(), AppFrame(), Clock(), ConnectionStatus(), HaltButton() (+13 more)

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
Cohesion: 0.11
Nodes (35): parse_fomc(), Official FOMC meeting dates, scoped context only; no complete macro calendar., CodexReviewer, command(), material_hash(), evidence_for(), Point-in-time evidence screening; language models cannot override vetoes., screen() (+27 more)

### Community 17 - "parse_bea"
Cohesion: 0.20
Nodes (6): parse_bea(), HTMLParser, Scoped BEA schedule; a date is retained without inventing an unspecified…, Schedule, bea_html(), test_bea_dates_preserve_clock_text_without_inventing_release_timezone()

### Community 18 - "motion.tsx"
Cohesion: 0.11
Nodes (18): Dialog(), AnimationProvider(), initialMode(), initialSystem(), LoadingPanel(), Mode, readMode(), readSystem() (+10 more)

### Community 19 - "health-page.tsx"
Cohesion: 0.10
Nodes (25): metadata, HealthDetails(), HealthFooterStatus(), HealthMap(), HealthPage(), HealthSummary(), attention, inTopic() (+17 more)

### Community 20 - "liquidity_runner.py"
Cohesion: 0.13
Nodes (37): contract(), digest(), observe(), register(), state(), evaluate(), floor(), Policy (+29 more)

### Community 21 - "relay.ts"
Cohesion: 0.13
Nodes (17): Context, dynamic, GET(), POST(), runtime, acceptsGzip(), compress, getPaths (+9 more)

### Community 22 - "app.spec.ts"
Cohesion: 0.18
Nodes (3): Dashboard, OrderIntent, diagnostics

### Community 25 - "test_risk.py"
Cohesion: 0.24
Nodes (15): propose(), ATR14 + trend/breakout candidate and fixed fractional loss-budget sizing. All…, history(), parametrize, test_diagnostic_rejects_bad_history(), test_prefix_diagnostic_reuses_live_math_and_never_assumes_fills(), inputs(), parametrize (+7 more)

### Community 27 - "datetime"
Cohesion: 0.15
Nodes (15): Fixed-host Alpaca paper adapter and a separately labelled durable simulator., Bounded Codex CLI reviewer. Broker credentials and tools are not inherited., Frozen research contract and append-only observations. No execution interface., source_hashes(), attribute(), canonical_symbol(), Inventory attribution is evidence, not a substitute for broker availability., One explicitly authorized execution experiment; never an alpha strategy. Uses… (+7 more)

### Community 28 - "devDependencies"
Cohesion: 0.04
Nodes (48): eslint, eslint-config-next, @fontsource-variable/dm-sans, @fontsource-variable/space-grotesk, dependencies, @fontsource-variable/dm-sans, @fontsource-variable/space-grotesk, motion (+40 more)

### Community 29 - "Collector"
Cohesion: 0.16
Nodes (13): collect(), health_inputs(), intelligence(), lifespan(), Local-only companion: independent DB and lifecycle preserve the shadow pilot., Collector, date(), test_collection_loop_delays_after_failure_continues_and_propagates_cancel() (+5 more)

### Community 30 - "Engine"
Cohesion: 0.07
Nodes (20): No remote API. Fills are synthetic and do not model queueing/market impact., Simulator, age(), Engine, symbol_for(), Validate provider fee records without estimating missing fees or rewriting…, record_fee(), validate_activity() (+12 more)

### Community 31 - "overview-page.tsx"
Cohesion: 0.09
Nodes (29): HealthChanges(), OrderDialog(), AssetBar(), EquityChart(), ExecutionStream(), IntelligenceFeed(), ModeBadge(), OverviewFooter() (+21 more)

### Community 32 - "test_review_repairs.py"
Cohesion: 0.18
Nodes (18): read_context(), daily_history(), fee(), parametrize, Locked review regressions. Synthetic brokers, patched models and tmp ledgers…, test_all_vetoed_cycle_never_calls_model(), test_diagnostic_failure_still_journals_prospective_veto(), test_disabled_model_keeps_deterministic_arm_in_new_observations() (+10 more)

### Community 33 - "intelligence.py"
Cohesion: 0.22
Nodes (11): ASTRAL paper-only service., clean(), named(), parse(), Independent public intelligence collector. No broker, credentials or order…, safe_url(), Source, value() (+3 more)

### Community 35 - "replay"
Cohesion: 0.38
Nodes (10): One-unit synthetic quote replay, with fills strictly AFTER decisions. Quote-…, replay(), event(), parametrize, test_entry_cancels_if_research_expires_during_latency(), test_entry_timing_fail_closed(), test_exit_rules_work_without_entry_permission(), test_future_data_append_does_not_change_prior_decision() (+2 more)

### Community 36 - "accounting/page.tsx"
Cohesion: 0.14
Nodes (12): dynamic, metadata, Page(), dynamic, metadata, Page(), AccountingContent(), LearningContent() (+4 more)

### Community 37 - "validate_pr_body.cjs"
Cohesion: 0.23
Nodes (11): fs, main(), readableText(), REQUIRED_CHECKS, REQUIRED_SECTIONS, sections(), validatePullRequestBody(), withoutComments() (+3 more)

### Community 38 - "test_readiness_gates.py"
Cohesion: 0.26
Nodes (13): calendar_coverage(), All scoped categories need retained, current, forward-covering evidence.…, view(), book(), quote(), test_adequate_daily_volume_cannot_override_a_subminimum_depth_cap(), test_book_normalization_fails_closed(), test_calendar_flags_and_hash_strings_alone_cannot_certify_coverage() (+5 more)

### Community 40 - "overnight_watch.py"
Cohesion: 0.25
Nodes (9): audit(), now(), Bounded overnight observation of the existing GET-only localhost paper lab., safety(), watch(), write_summary(), parametrize, test_observer_counts_lost_write_and_http_failure() (+1 more)

### Community 42 - "test_event_sources.py"
Cohesion: 0.18
Nodes (16): Retain scoped official calendar catalogs; never certify missing categories., Maintenance needs two current publisher lists. NY Fed remains partial BLS., retain_additional_scopes(), retain_scopes(), calendar_html(), context(), maintenance_body(), parametrize (+8 more)

### Community 43 - "audit_crypto"
Cohesion: 0.32
Nodes (7): audit_crypto(), Read-only reconciliation analysis. Hypotheses cannot become ledger entries., Compare authoritative gross executions and positions; explain, never waive. Fee…, reconciliation_fixture(), test_confirmed_fee_matches_and_duplicate_activity_is_not_counted_twice(), test_exact_fee_hypothesis_never_clears_an_unconfirmed_difference(), test_incomplete_or_conflicting_execution_evidence_cannot_match()

### Community 44 - "timestamp"
Cohesion: 0.21
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

### Community 52 - "commitlint.config.cjs"
Cohesion: 0.83
Nodes (3): bodyMaxLineLength(), footerMaxLineLength(), maxLineLength()

### Community 58 - "test_quantconnect_validation.py"
Cohesion: 0.11
Nodes (35): price_signal(), Pure OHLC hypothesis; caller validates provenance and time separately., QCAlgorithm, as_utc(), AstralBtcSignalParity, Compare both implementations in cloud memory; export aggregate diagnostics only., bundle(), compare() (+27 more)

### Community 63 - "read.ts"
Cohesion: 0.29
Nodes (7): RootLayout(), Seed, healthSchema, ReadResult, loadSeed(), seedScope(), upstreamFetch()

## Knowledge Gaps
- **154 isolated node(s):** `Source`, `metadata`, `dynamic`, `runtime`, `dynamic` (+149 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Store` connect `Store` to `test_review_repairs.py`, `BrokerFailure`, `run`, `test_accounting_engine.py`, `test_health_engine.py`, `test_portfolio_replay.py`, `test_readiness_gates.py`, `test_learning_engine.py`, `test_event_sources.py`, `dumps`, `liquidity_runner.py`, `datetime`, `Collector`, `Engine`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._
- **Why does `utcnow()` connect `Engine` to `test_review_repairs.py`, `BrokerFailure`, `intelligence.py`, `run`, `test_health_engine.py`, `test_readiness_gates.py`, `Store`, `test_event_sources.py`, `dumps`, `liquidity_runner.py`, `datetime`, `Collector`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **Why does `Engine` connect `Engine` to `test_review_repairs.py`, `BrokerFailure`, `run`, `test_portfolio_replay.py`, `Store`, `dumps`, `liquidity_runner.py`, `datetime`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `Store` (e.g. with `ExitPlan` and `Halt`) actually correct?**
  _`Store` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `Engine` (e.g. with `ExitPlan` and `Halt`) actually correct?**
  _`Engine` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 30 inferred relationships involving `D()` (e.g. with `diagnose()` and `validate_activity()`) actually correct?**
  _`D()` has 30 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Source`, `metadata`, `dynamic` to the rest of the system?**
  _154 weakly-connected nodes found - possible documentation gaps or missing edges._