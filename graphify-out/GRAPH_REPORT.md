# Graph Report - astral-trading  (2026-10-26)

## Corpus Check
- 192 files · ~67,637 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1272 nodes · 3791 edges · 52 communities (49 shown, 3 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 135 edges (avg confidence: 0.64)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d5f5b1c2`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- event_sources.py
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
- Connection
- compilerOptions
- contracts.ts
- support.cjs
- screen
- timestamp
- motion.tsx
- health-page.tsx
- liquidity_runner.py
- relay.ts
- experiment.py
- BrokerFailure
- datetime
- test_risk.py
- test_event_sources.py
- engine.py
- devDependencies
- Collector
- utcnow
- overview-page.tsx
- test_review_repairs.py
- intelligence.py
- parse_bea
- decide
- accounting/page.tsx
- validate_pr_body.cjs
- test_readiness_gates.py
- test_trade_history.py
- overnight_watch.py
- Store
- boundaries.test.ts
- check-skills.cjs
- commitlint.config.cjs
- intelligence-feed.tsx
- proxy.ts
- next.config.ts
- prepare-standalone.mjs

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

## Communities (52 total, 3 thin omitted)

### Community 0 - "event_sources.py"
Cohesion: 0.16
Nodes (13): catalog(), Cells, event(), maintenance(), nyfed(), parse_events(), protocol(), HTMLParser (+5 more)

### Community 1 - "AlpacaPaper"
Cohesion: 0.17
Nodes (3): AlpacaPaper, Limiter, main()

### Community 2 - "run"
Cohesion: 0.06
Nodes (77): create_app(), Settings, audit_crypto(), Read-only reconciliation analysis. Hypotheses cannot become ledger entries., Compare authoritative gross executions and positions; explain, never waive. Fee…, Failure scenarios and adversarial selection cases; all trades are synthetic., test_ambiguous_fee_is_not_assigned_to_a_strategy(), test_api_shadow_does_not_enable_orders_and_rejects_bypass_fields() (+69 more)

### Community 3 - "test_accounting_engine.py"
Cohesion: 0.09
Nodes (58): at(), canonical(), cost_report(), digest(), evaluate(), main(), number(), precise() (+50 more)

### Community 4 - "test_health_engine.py"
Cohesion: 0.08
Nodes (27): lifespan(), Standalone health service, separate process and ledger from telemetry/trading., state(), fresh(), HealthEngine, Independent assessments from telemetry observations; no trading authority., effective(), HealthMonitor (+19 more)

### Community 5 - "D"
Cohesion: 0.11
Nodes (47): D(), Assumptions, Portfolio, replay(), build_report(), code_hashes(), connect_readonly(), export_events() (+39 more)

### Community 6 - "ui.ts"
Cohesion: 0.13
Nodes (22): StrategiesView(), StrategyCounts(), AccountingBoundaries(), AccountingCosts(), AccountingGross(), AccountingRecords(), AccountingSummary(), amounts() (+14 more)

### Community 7 - "test_learning_engine.py"
Cohesion: 0.15
Nodes (39): digest(), encode(), evaluate(), main(), markdown(), packet_checks(), protected(), protected_windows() (+31 more)

### Community 8 - "test_state_contract.py"
Cohesion: 0.18
Nodes (23): at(), build_state(), buy(), free_port(), normalize(), pin_clock(), parametrize, Dashboard read-path contract: fixed Store-seeded ledgers and a pinned clock.… (+15 more)

### Community 9 - "Engine"
Cohesion: 0.16
Nodes (5): age(), Engine, symbol_for(), book_for(), dumps()

### Community 10 - "scripts"
Cohesion: 0.05
Nodes (37): @commitlint/cli, @commitlint/config-conventional, @commitlint/lint, @commitlint/load, husky, devDependencies, @commitlint/cli, @commitlint/config-conventional (+29 more)

### Community 11 - "useDashboard"
Cohesion: 0.19
Nodes (18): HealthFooterStatus(), ModeBadge(), Context, useDashboard(), PacketDialog(), ResearchExperiments(), ResearchGates(), ResearchLab() (+10 more)

### Community 12 - "Connection"
Cohesion: 0.10
Nodes (11): RootLayout(), Connection, Seed, loadSeed(), seedScope(), seed(), Source, dashboard() (+3 more)

### Community 13 - "compilerOptions"
Cohesion: 0.07
Nodes (29): compilerOptions, allowJs, checkJs, esModuleInterop, incremental, isolatedModules, jsx, lib (+21 more)

### Community 14 - "contracts.ts"
Cohesion: 0.08
Nodes (27): api(), errorMessage(), empty, Snapshot, accountingSchema, amount, counts, Dashboard (+19 more)

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
Nodes (24): CodexReviewer, command(), material_hash(), Bounded Codex CLI reviewer. Broker credentials and tools are not inherited., Point-in-time evidence screening; language models cannot override vetoes., screen(), validate_review(), discover_crypto() (+16 more)

### Community 17 - "timestamp"
Cohesion: 0.17
Nodes (22): evaluate(), floor(), Quote-only liquidity experiment. No orders, fills, positions, P&L or promotion., turnover(), walk(), Same-venue REST book/quote validation. Visible depth never guarantees a fill., _validate(), validate_book() (+14 more)

### Community 18 - "motion.tsx"
Cohesion: 0.08
Nodes (23): dynamic, metadata, AnimationProvider(), initialMode(), initialSystem(), LoadingPanel(), Mode, readMode() (+15 more)

### Community 19 - "health-page.tsx"
Cohesion: 0.11
Nodes (26): metadata, HealthChanges(), HealthDetails(), HealthMap(), HealthPage(), HealthSummary(), attention, inTopic() (+18 more)

### Community 20 - "liquidity_runner.py"
Cohesion: 0.25
Nodes (20): digest(), Policy, binding(), get(), get_inventory_status(), hashes(), load(), now() (+12 more)

### Community 21 - "relay.ts"
Cohesion: 0.10
Nodes (21): Context, dynamic, GET(), POST(), runtime, acceptsGzip(), compress, getPaths (+13 more)

### Community 22 - "experiment.py"
Cohesion: 0.22
Nodes (13): contract(), observe(), Frozen research contract and append-only observations. No execution interface., register(), source_hashes(), state(), main(), Register once; run offline diagnostic from an existing read-only history DB.… (+5 more)

### Community 23 - "BrokerFailure"
Cohesion: 0.21
Nodes (13): ExitPlan, Halt, Intent, ResearchBar, RiskCandidate, BrokerFailure, Exception, Exception (+5 more)

### Community 24 - "datetime"
Cohesion: 0.19
Nodes (12): Meetings, parse_fomc(), HTMLParser, Official FOMC meeting dates, scoped context only; no complete macro calendar., evidence_for(), Credential-free local feed read; headlines remain untrusted scoped context., datetime, context() (+4 more)

### Community 25 - "test_risk.py"
Cohesion: 0.18
Nodes (19): diagnose(), Retrospective price-only prefixes. Never pretend these were known earlier., price_signal(), propose(), ATR14 + trend/breakout candidate and fixed fractional loss-budget sizing. All…, Pure OHLC hypothesis; caller validates provenance and time separately., history(), parametrize (+11 more)

### Community 26 - "test_event_sources.py"
Cohesion: 0.18
Nodes (16): Retain scoped official calendar catalogs; never certify missing categories., Maintenance needs two current publisher lists. NY Fed remains partial BLS., retain_additional_scopes(), retain_scopes(), calendar_html(), context(), maintenance_body(), parametrize (+8 more)

### Community 27 - "engine.py"
Cohesion: 0.17
Nodes (12): Fixed-host Alpaca paper adapter and a separately labelled durable simulator., attribute(), canonical_symbol(), Inventory attribution is evidence, not a substitute for broker availability., One explicitly authorized execution experiment; never an alpha strategy. Uses…, Evidence-by-evidence readiness. No threshold changes or execution capability., isolate_experiment_workers(), lab_path() (+4 more)

### Community 28 - "devDependencies"
Cohesion: 0.04
Nodes (48): eslint, eslint-config-next, @fontsource-variable/dm-sans, @fontsource-variable/space-grotesk, dependencies, @fontsource-variable/dm-sans, @fontsource-variable/space-grotesk, motion (+40 more)

### Community 29 - "Collector"
Cohesion: 0.20
Nodes (12): collect(), health_inputs(), intelligence(), lifespan(), Local-only companion: independent DB and lifecycle preserve the shadow pilot., Collector, test_collection_loop_delays_after_failure_continues_and_propagates_cancel(), test_collector_fetch_propagates_cancellation() (+4 more)

### Community 30 - "utcnow"
Cohesion: 0.15
Nodes (7): No remote API. Fills are synthetic and do not model queueing/market impact., Simulator, read_context(), utcnow(), fixture, research_engine(), test_valid_context_shape_remains_available()

### Community 31 - "overview-page.tsx"
Cohesion: 0.14
Nodes (21): OrderDialog(), AssetBar(), ConnectionBanner(), EquityChart(), ExecutionStream(), OverviewFooter(), OverviewPage(), views (+13 more)

### Community 32 - "test_review_repairs.py"
Cohesion: 0.28
Nodes (12): daily_history(), fee(), parametrize, Locked review regressions. Synthetic brokers, patched models and tmp ledgers…, test_diagnostic_failure_still_journals_prospective_veto(), test_distinct_lab_still_copies_or_reuses(), test_identical_fee_duplicates_and_later_execution_are_idempotent(), test_invalid_confirmed_fee_revision_is_retained_and_latched() (+4 more)

### Community 33 - "intelligence.py"
Cohesion: 0.16
Nodes (13): ASTRAL paper-only service., clean(), date(), named(), parse(), Independent public intelligence collector. No broker, credentials or order…, safe_url(), Source (+5 more)

### Community 34 - "parse_bea"
Cohesion: 0.20
Nodes (6): parse_bea(), HTMLParser, Scoped BEA schedule; a date is retained without inventing an unspecified…, Schedule, bea_html(), test_bea_dates_preserve_clock_text_without_inventing_release_timezone()

### Community 35 - "decide"
Cohesion: 0.32
Nodes (12): decide(), Deterministic timing hypotheses. Produces candidates, never orders or fills., One-unit synthetic quote replay, with fills strictly AFTER decisions. Quote-…, replay(), event(), parametrize, test_entry_cancels_if_research_expires_during_latency(), test_entry_timing_fail_closed() (+4 more)

### Community 36 - "accounting/page.tsx"
Cohesion: 0.15
Nodes (12): dynamic, metadata, Page(), dynamic, metadata, Page(), AccountingContent(), LearningContent() (+4 more)

### Community 37 - "validate_pr_body.cjs"
Cohesion: 0.23
Nodes (11): fs, main(), readableText(), REQUIRED_CHECKS, REQUIRED_SECTIONS, sections(), validatePullRequestBody(), withoutComments() (+3 more)

### Community 38 - "test_readiness_gates.py"
Cohesion: 0.18
Nodes (18): record_fee(), calendar_coverage(), All scoped categories need retained, current, forward-covering evidence.…, view(), book(), fee(), parametrize, quote() (+10 more)

### Community 39 - "test_trade_history.py"
Cohesion: 0.38
Nodes (9): aggregate_daily(), aggregate(), batch(), parametrize, test_bad_trade_records_fail_closed(), test_history_shares_completed_days_and_reconstructs_each_immutable_batch(), test_missing_trade_day_is_not_filled_from_quotes(), test_provider_pagination_must_finish_before_history_is_accepted() (+1 more)

### Community 40 - "overnight_watch.py"
Cohesion: 0.25
Nodes (9): audit(), now(), Bounded overnight observation of the existing GET-only localhost paper lab., safety(), watch(), write_summary(), parametrize, test_observer_counts_lost_write_and_http_failure() (+1 more)

### Community 41 - "Store"
Cohesion: 0.29
Nodes (3): Store, parametrize, test_unexpected_source_failure_keeps_other_feed_alive_and_recovers()

### Community 47 - "boundaries.test.ts"
Cohesion: 0.32
Nodes (6): allowlist, files, isClient(), lines(), root, text()

### Community 49 - "check-skills.cjs"
Cohesion: 0.33
Nodes (6): checkSkills(), crypto, fs, hashSkillFolder(), path, ROOT

### Community 52 - "commitlint.config.cjs"
Cohesion: 0.83
Nodes (3): bodyMaxLineLength(), footerMaxLineLength(), maxLineLength()

### Community 53 - "intelligence-feed.tsx"
Cohesion: 0.18
Nodes (9): Dialog(), IntelligenceFeed(), SourceDialog(), ViewDialog(), IntelligenceView(), Detail, EvidenceDialog(), SourceLink() (+1 more)

## Knowledge Gaps
- **154 isolated node(s):** `Source`, `metadata`, `dynamic`, `runtime`, `dynamic` (+149 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Store` connect `Store` to `AlpacaPaper`, `run`, `test_accounting_engine.py`, `test_health_engine.py`, `D`, `test_learning_engine.py`, `test_state_contract.py`, `screen`, `timestamp`, `experiment.py`, `BrokerFailure`, `datetime`, `test_event_sources.py`, `engine.py`, `Collector`, `utcnow`, `test_review_repairs.py`, `test_readiness_gates.py`, `test_trade_history.py`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **Why does `utcnow()` connect `utcnow` to `test_review_repairs.py`, `AlpacaPaper`, `run`, `test_accounting_engine.py`, `test_health_engine.py`, `intelligence.py`, `test_readiness_gates.py`, `Engine`, `screen`, `experiment.py`, `BrokerFailure`, `datetime`, `test_event_sources.py`, `engine.py`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Why does `Engine` connect `Engine` to `test_review_repairs.py`, `AlpacaPaper`, `run`, `D`, `test_readiness_gates.py`, `test_state_contract.py`, `screen`, `timestamp`, `experiment.py`, `BrokerFailure`, `datetime`, `engine.py`, `utcnow`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `Store` (e.g. with `ExitPlan` and `Halt`) actually correct?**
  _`Store` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `Engine` (e.g. with `ExitPlan` and `Halt`) actually correct?**
  _`Engine` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 30 inferred relationships involving `D()` (e.g. with `diagnose()` and `validate_activity()`) actually correct?**
  _`D()` has 30 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Source`, `metadata`, `dynamic` to the rest of the system?**
  _154 weakly-connected nodes found - possible documentation gaps or missing edges._