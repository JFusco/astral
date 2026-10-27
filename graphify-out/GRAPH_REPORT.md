# Graph Report - astral-trading  (2026-10-27)

## Corpus Check
- 208 files · ~83,828 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1552 nodes · 4899 edges · 60 communities (52 shown, 8 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 249 edges (avg confidence: 0.7)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `2d420690`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_event_sources.py
- utcnow
- run
- dumps
- experiment.py
- D
- ui.ts
- test_learning_engine.py
- Settings
- BrokerFailure
- scripts
- useDashboard
- broker.py
- compilerOptions
- contracts.ts
- support.cjs
- test_review_repairs.py
- test_readiness_gates.py
- motion.tsx
- health-page.tsx
- replay_runner.py
- relay.ts
- test_activity_feed.py
- liquidity_runner.py
- datetime
- Simulator
- quantconnect/__init__.py
- audit_crypto
- devDependencies
- Store
- AlpacaPaper
- overview-page.tsx
- .run
- app-frame.tsx
- test_activity_rollout.py
- ValueError
- parse_bea
- validate_pr_body.cjs
- intelligence.py
- app.spec.ts
- overnight_watch.py
- decide
- test_health_engine.py
- navigation.tsx
- Cells
- activity_feed.py
- timestamp
- boundaries.test.ts
- Observation
- check-skills.cjs
- Source
- commitlint.config.cjs
- proxy.ts
- next.config.ts
- test_quantconnect_validation.py
- prepare-standalone.mjs
- Connection

## God Nodes (most connected - your core abstractions)
1. `Store` - 103 edges
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
- `test_nanosecond_cutoffs_and_decimal_input_contracts()` --calls--> `instant()`  [EXTRACTED]
  tests/test_activity_feed.py → backend/activity_projection.py
- `Providers` --uses--> `Settings`  [INFERRED]
  tests/test_health_engine.py → backend/config.py
- `FixedDateTime` --uses--> `RuleViolation`  [INFERRED]
  tests/test_state_contract.py → backend/engine.py
- `Stream` --uses--> `RuleViolation`  [INFERRED]
  tests/test_state_contract.py → backend/engine.py
- `FixedDateTime` --uses--> `Engine`  [INFERRED]
  tests/test_state_contract.py → backend/engine.py

## Import Cycles
- None detected.

## Communities (60 total, 8 thin omitted)

### Community 0 - "test_event_sources.py"
Cohesion: 0.16
Nodes (21): catalog(), event(), maintenance(), nyfed(), parse_events(), protocol(), Fixed public event sources. Published context is distinct from complete…, Watch authoritative documents without interpreting proposals as activations. (+13 more)

### Community 1 - "utcnow"
Cohesion: 0.13
Nodes (9): age(), Engine, symbol_for(), record_fee(), book_for(), utcnow(), main(), One bounded GET-only research cycle on the existing paper ledger. No model. (+1 more)

### Community 2 - "run"
Cohesion: 0.10
Nodes (49): Failure scenarios and adversarial selection cases; all trades are synthetic., test_ambiguous_fee_is_not_assigned_to_a_strategy(), test_api_shadow_does_not_enable_orders_and_rejects_bypass_fields(), test_intraday_exit_cannot_liquidate_swing_inventory(), test_late_confirmed_asset_fee_is_idempotent_and_reconciles(), test_local_exit_survives_restart_and_unknown_response(), test_quantity_and_shared_risk_boundaries(), test_read_only_adapter_blocks_post_and_delete_before_transport() (+41 more)

### Community 3 - "dumps"
Cohesion: 0.06
Nodes (109): at(), canonical(), cost_report(), digest(), evaluate(), main(), number(), precise() (+101 more)

### Community 4 - "experiment.py"
Cohesion: 0.24
Nodes (11): contract(), observe(), Frozen research contract and append-only observations. No execution interface., register(), source_hashes(), state(), main(), Register once; run offline diagnostic from an existing read-only history DB.… (+3 more)

### Community 5 - "D"
Cohesion: 0.20
Nodes (36): D(), Assumptions, replay(), stress_suite(), synthetic_events(), at(), clock(), pick() (+28 more)

### Community 6 - "ui.ts"
Cohesion: 0.14
Nodes (22): StrategiesView(), StrategyCounts(), AccountingBoundaries(), AccountingCosts(), AccountingGross(), AccountingRecords(), AccountingSummary(), amounts() (+14 more)

### Community 7 - "test_learning_engine.py"
Cohesion: 0.11
Nodes (48): digest(), encode(), evaluate(), main(), markdown(), packet_checks(), protected(), protected_windows() (+40 more)

### Community 8 - "Settings"
Cohesion: 0.12
Nodes (32): create_app(), Settings, test_cancelled_acquisition_retains_partial_stream_and_propagates_cancellation(), test_identity_change_after_complete_stream_retains_quarantined_raw_evidence(), test_local_health_inputs_are_small_read_only_and_do_not_export_account_data(), test_replay_report_is_visible_only_in_the_book_that_records_its_receipt(), test_only_one_executor_can_own_database(), test_unconfigured_alpaca_never_falls_back_to_simulator() (+24 more)

### Community 9 - "BrokerFailure"
Cohesion: 0.17
Nodes (19): ExitPlan, Halt, Intent, ResearchBar, RiskCandidate, BrokerFailure, Exception, Exception (+11 more)

### Community 10 - "scripts"
Cohesion: 0.05
Nodes (37): @commitlint/cli, @commitlint/config-conventional, @commitlint/lint, @commitlint/load, husky, devDependencies, @commitlint/cli, @commitlint/config-conventional (+29 more)

### Community 11 - "useDashboard"
Cohesion: 0.17
Nodes (21): HealthFooterStatus(), EquityChart(), OverviewFooter(), Context, useDashboard(), Detail, EvidenceDialog(), PacketDialog() (+13 more)

### Community 12 - "broker.py"
Cohesion: 0.09
Nodes (28): Fixed-host Alpaca paper adapter and a separately labelled durable simulator., discover_crypto(), Read-only venue discovery. A listing is never execution authorization., isolate_experiment_workers(), lab_path(), main(), Bounded, GET-only Alpaca dogfood session using a private copied ledger., main() (+20 more)

### Community 13 - "compilerOptions"
Cohesion: 0.07
Nodes (29): compilerOptions, allowJs, checkJs, esModuleInterop, incremental, isolatedModules, jsx, lib (+21 more)

### Community 14 - "contracts.ts"
Cohesion: 0.07
Nodes (38): dynamic, metadata, RootLayout(), Provider(), AppFrame(), api(), errorMessage(), empty (+30 more)

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

### Community 16 - "test_review_repairs.py"
Cohesion: 0.09
Nodes (42): CodexReviewer, command(), material_hash(), Bounded Codex CLI reviewer. Broker credentials and tools are not inherited., evidence_for(), read_context(), Point-in-time evidence screening; language models cannot override vetoes., screen() (+34 more)

### Community 17 - "test_readiness_gates.py"
Cohesion: 0.17
Nodes (19): retain_scopes(), calendar_coverage(), All scoped categories need retained, current, forward-covering evidence.…, view(), test_active_to_empty_maintenance_snapshot_survives_restart_and_304(), bea_html(), book(), fee() (+11 more)

### Community 18 - "motion.tsx"
Cohesion: 0.13
Nodes (16): AnimationProvider(), initialMode(), initialSystem(), LoadingPanel(), Mode, readMode(), readSystem(), Reveal() (+8 more)

### Community 19 - "health-page.tsx"
Cohesion: 0.11
Nodes (24): metadata, HealthChanges(), HealthDetails(), HealthMap(), HealthPage(), HealthSummary(), attention, inTopic() (+16 more)

### Community 20 - "replay_runner.py"
Cohesion: 0.33
Nodes (10): build_report(), code_hashes(), connect_readonly(), export_events(), Read-only ledger export, fixed future window and offline stress receipts. No…, register_holdout(), report_state(), summary() (+2 more)

### Community 21 - "relay.ts"
Cohesion: 0.07
Nodes (33): dynamic, metadata, Page(), Context, dynamic, GET(), POST(), runtime (+25 more)

### Community 22 - "test_activity_feed.py"
Cohesion: 0.11
Nodes (41): current_accounting(), parse_sse(), start_batch(), ledger_source(), The caller holds a read transaction or the Store lock across this snapshot., controlled_current(), pure(), parametrize (+33 more)

### Community 23 - "liquidity_runner.py"
Cohesion: 0.29
Nodes (18): digest(), intelligence(), Policy, binding(), get(), get_inventory_status(), hashes(), load() (+10 more)

### Community 24 - "datetime"
Cohesion: 0.10
Nodes (28): Meetings, parse_fomc(), HTMLParser, Official FOMC meeting dates, scoped context only; no complete macro calendar., One explicitly authorized execution experiment; never an alpha strategy. Uses…, Credential-free local feed read; headlines remain untrusted scoped context., propose(), ATR14 + trend/breakout candidate and fixed fractional loss-budget sizing. All… (+20 more)

### Community 25 - "Simulator"
Cohesion: 0.13
Nodes (4): No remote API. Fills are synthetic and do not model queueing/market impact., Simulator, fixture, research_engine()

### Community 27 - "audit_crypto"
Cohesion: 0.32
Nodes (7): audit_crypto(), Read-only reconciliation analysis. Hypotheses cannot become ledger entries., Compare authoritative gross executions and positions; explain, never waive. Fee…, reconciliation_fixture(), test_confirmed_fee_matches_and_duplicate_activity_is_not_counted_twice(), test_exact_fee_hypothesis_never_clears_an_unconfirmed_difference(), test_incomplete_or_conflicting_execution_evidence_cannot_match()

### Community 28 - "devDependencies"
Cohesion: 0.04
Nodes (48): eslint, eslint-config-next, @fontsource-variable/dm-sans, @fontsource-variable/space-grotesk, dependencies, @fontsource-variable/dm-sans, @fontsource-variable/space-grotesk, motion (+40 more)

### Community 29 - "Store"
Cohesion: 0.16
Nodes (13): collect(), lifespan(), Local-only companion: independent DB and lifecycle preserve the shadow pilot., Collector, Store, parametrize, test_collection_loop_delays_after_failure_continues_and_propagates_cancel(), test_collector_fetch_propagates_cancellation() (+5 more)

### Community 30 - "AlpacaPaper"
Cohesion: 0.10
Nodes (17): AlpacaPaper, Limiter, account_identity(), AccountLease, OwnershipError, private_owned(), Exception, Cooperative paper-account ownership for one OS user on one host. (+9 more)

### Community 31 - "overview-page.tsx"
Cohesion: 0.10
Nodes (26): Dialog(), OrderDialog(), AssetBar(), ExecutionStream(), IntelligenceFeed(), ModeBadge(), OverviewPage(), views (+18 more)

### Community 33 - "app-frame.tsx"
Cohesion: 0.29
Nodes (4): Clock(), ConnectionStatus(), HaltButton(), OpeningPanels()

### Community 34 - "test_activity_rollout.py"
Cohesion: 0.12
Nodes (31): Bounded observation of existing accounting, independent of trading readiness., activated_settings(), check_ledger(), ledger_bytes(), main(), prepare(), PreparedRollout, Read-only rollout preflight; activation requires a separate explicit invocation. (+23 more)

### Community 35 - "ValueError"
Cohesion: 0.17
Nodes (22): main(), number(), acceptance(), connected(), destinations(), import_capture(), import_ledger(), main() (+14 more)

### Community 36 - "parse_bea"
Cohesion: 0.25
Nodes (4): parse_bea(), HTMLParser, Scoped BEA schedule; a date is retained without inventing an unspecified…, Schedule

### Community 37 - "validate_pr_body.cjs"
Cohesion: 0.23
Nodes (11): fs, main(), readableText(), REQUIRED_CHECKS, REQUIRED_SECTIONS, sections(), validatePullRequestBody(), withoutComments() (+3 more)

### Community 38 - "intelligence.py"
Cohesion: 0.16
Nodes (13): ASTRAL paper-only service., clean(), date(), named(), parse(), Independent public intelligence collector. No broker, credentials or order…, safe_url(), Source (+5 more)

### Community 40 - "overnight_watch.py"
Cohesion: 0.25
Nodes (9): audit(), now(), Bounded overnight observation of the existing GET-only localhost paper lab., safety(), watch(), write_summary(), parametrize, test_observer_counts_lost_write_and_http_failure() (+1 more)

### Community 41 - "decide"
Cohesion: 0.32
Nodes (12): decide(), Deterministic timing hypotheses. Produces candidates, never orders or fills., One-unit synthetic quote replay, with fills strictly AFTER decisions. Quote-…, replay(), event(), parametrize, test_entry_cancels_if_research_expires_during_latency(), test_entry_timing_fail_closed() (+4 more)

### Community 42 - "test_health_engine.py"
Cohesion: 0.08
Nodes (30): lifespan(), Standalone health service, separate process and ledger from telemetry/trading., state(), fresh(), HealthEngine, Independent assessments from telemetry observations; no trading authority., health_inputs(), effective() (+22 more)

### Community 43 - "navigation.tsx"
Cohesion: 0.40
Nodes (3): NavLink(), Navigation(), pages

### Community 44 - "Cells"
Cohesion: 0.29
Nodes (3): Cells, HTMLParser, Retain cells in a selected table, including links and their following text.

### Community 45 - "activity_feed.py"
Cohesion: 0.15
Nodes (26): activity_identifier(), collect_batch(), FeedError, publish_projection(), Bounded paper activity acquisition and immutable evidence publication., Use the adapter's authentication, process boundary and request budget., Commit even rejected records before publishing or raising their failure., Incremental SSE framing; raw acquisition bytes are retained separately. (+18 more)

### Community 46 - "timestamp"
Cohesion: 0.12
Nodes (28): Retain scoped official calendar catalogs; never certify missing categories., Maintenance needs two current publisher lists. NY Fed remains partial BLS., retain_additional_scopes(), diagnose(), Retrospective price-only prefixes. Never pretend these were known earlier., evaluate(), floor(), Quote-only liquidity experiment. No orders, fills, positions, P&L or promotion. (+20 more)

### Community 47 - "boundaries.test.ts"
Cohesion: 0.32
Nodes (6): allowlist, files, isClient(), lines(), root, text()

### Community 48 - "Observation"
Cohesion: 0.20
Nodes (4): Latency, Observation, Fixed-size histogram retains every observation without per-request rows., Sample current availability without treating it as collection success.

### Community 49 - "check-skills.cjs"
Cohesion: 0.33
Nodes (6): checkSkills(), crypto, fs, hashSkillFolder(), path, ROOT

### Community 52 - "commitlint.config.cjs"
Cohesion: 0.83
Nodes (3): bodyMaxLineLength(), footerMaxLineLength(), maxLineLength()

### Community 58 - "test_quantconnect_validation.py"
Cohesion: 0.11
Nodes (35): price_signal(), Pure OHLC hypothesis; caller validates provenance and time separately., QCAlgorithm, as_utc(), AstralBtcSignalParity, Compare both implementations in cloud memory; export aggregate diagnostics only., bundle(), compare() (+27 more)

## Knowledge Gaps
- **154 isolated node(s):** `Source`, `metadata`, `dynamic`, `runtime`, `dynamic` (+149 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Store` connect `Store` to `test_event_sources.py`, `utcnow`, `run`, `dumps`, `experiment.py`, `D`, `test_learning_engine.py`, `Settings`, `BrokerFailure`, `broker.py`, `test_review_repairs.py`, `test_readiness_gates.py`, `test_activity_feed.py`, `datetime`, `Simulator`, `AlpacaPaper`, `test_activity_rollout.py`, `ValueError`, `test_health_engine.py`, `timestamp`?**
  _High betweenness centrality (0.075) - this node is a cross-community bridge._
- **Why does `utcnow()` connect `utcnow` to `test_event_sources.py`, `run`, `dumps`, `experiment.py`, `Settings`, `BrokerFailure`, `broker.py`, `test_review_repairs.py`, `test_readiness_gates.py`, `test_activity_feed.py`, `datetime`, `Simulator`, `AlpacaPaper`, `test_activity_rollout.py`, `ValueError`, `intelligence.py`, `test_health_engine.py`, `activity_feed.py`, `timestamp`, `Observation`?**
  _High betweenness centrality (0.032) - this node is a cross-community bridge._
- **Why does `Engine` connect `utcnow` to `test_activity_rollout.py`, `dumps`, `run`, `D`, `Settings`, `BrokerFailure`, `broker.py`, `activity_feed.py`, `test_review_repairs.py`, `test_activity_feed.py`, `datetime`, `Simulator`, `AlpacaPaper`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `Store` (e.g. with `ExitPlan` and `Halt`) actually correct?**
  _`Store` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 97 inferred relationships involving `ValueError` (e.g. with `at()` and `cost_report()`) actually correct?**
  _`ValueError` has 97 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `Engine` (e.g. with `ExitPlan` and `Halt`) actually correct?**
  _`Engine` has 12 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Source`, `metadata`, `dynamic` to the rest of the system?**
  _154 weakly-connected nodes found - possible documentation gaps or missing edges._