# Graph Report - astral-trading  (2026-10-27)

## Corpus Check
- 210 files · ~85,722 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1581 nodes · 5074 edges · 60 communities (54 shown, 6 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 255 edges (avg confidence: 0.7)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b0562a02`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- timestamp
- Engine
- run
- dumps
- read.ts
- test_portfolio_replay.py
- ui.ts
- test_learning_engine.py
- test_state_contract.py
- test_execution_pilot.py
- scripts
- provider.tsx
- test_executor_ownership.py
- compilerOptions
- contracts.ts
- support.cjs
- screen
- utcnow
- motion.tsx
- health-page.tsx
- replay_runner.py
- relay.ts
- test_activity_feed.py
- liquidity_runner.py
- test_experiment.py
- activity_feed.py
- quantconnect/__init__.py
- test_liquidity_experiment.py
- devDependencies
- intelligence.py
- AlpacaPaper
- useDashboard
- datetime
- app-frame.tsx
- test_activity_rollout.py
- test_review_repairs.py
- Schedule
- validate_pr_body.cjs
- test_evidence_storage.py
- ValueError
- overnight_watch.py
- collect_batch
- test_health_engine.py
- navigation.tsx
- retain_batch
- Store
- number
- boundaries.test.ts
- import_ledger
- check-skills.cjs
- audit_crypto
- commitlint.config.cjs
- proxy.ts
- next.config.ts
- test_quantconnect_validation.py
- prepare-standalone.mjs
- Connection

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
- `test_nanosecond_cutoffs_and_decimal_input_contracts()` --calls--> `instant()`  [EXTRACTED]
  tests/test_activity_feed.py → backend/activity_projection.py
- `test_cancel_keeps_reservation_and_models_fill_race_until_ack()` --calls--> `D()`  [INFERRED]
  tests/test_portfolio_replay.py → backend/broker.py
- `test_cash_exhaustion_and_pending_orders_never_double_spend()` --calls--> `D()`  [INFERRED]
  tests/test_portfolio_replay.py → backend/broker.py
- `test_cash_is_reserved_before_fill_and_price_collar_bounds_purchase()` --calls--> `D()`  [INFERRED]
  tests/test_portfolio_replay.py → backend/broker.py
- `test_disconnect_and_unliquidated_position_remain_visible()` --calls--> `D()`  [INFERRED]
  tests/test_portfolio_replay.py → backend/broker.py

## Import Cycles
- None detected.

## Communities (60 total, 6 thin omitted)

### Community 0 - "timestamp"
Cohesion: 0.11
Nodes (30): Retain scoped official calendar catalogs; never certify missing categories., Maintenance needs two current publisher lists. NY Fed remains partial BLS., retain_additional_scopes(), retain_scopes(), catalog(), Cells, event(), maintenance() (+22 more)

### Community 1 - "Engine"
Cohesion: 0.15
Nodes (4): age(), Engine, symbol_for(), book_for()

### Community 2 - "run"
Cohesion: 0.11
Nodes (49): D(), Failure scenarios and adversarial selection cases; all trades are synthetic., test_ambiguous_fee_is_not_assigned_to_a_strategy(), test_intraday_exit_cannot_liquidate_swing_inventory(), test_late_confirmed_asset_fee_is_idempotent_and_reconciles(), test_local_exit_survives_restart_and_unknown_response(), test_quantity_and_shared_risk_boundaries(), test_read_only_adapter_blocks_post_and_delete_before_transport() (+41 more)

### Community 3 - "dumps"
Cohesion: 0.06
Nodes (112): at(), canonical(), cost_report(), digest(), evaluate(), main(), number(), precise() (+104 more)

### Community 4 - "read.ts"
Cohesion: 0.09
Nodes (24): dynamic, metadata, Page(), dynamic, metadata, RootLayout(), dynamic, metadata (+16 more)

### Community 5 - "test_portfolio_replay.py"
Cohesion: 0.14
Nodes (36): Assumptions, Portfolio, replay(), stress_suite(), synthetic_events(), at(), clock(), pick() (+28 more)

### Community 6 - "ui.ts"
Cohesion: 0.14
Nodes (21): AccountingBoundaries(), AccountingCosts(), AccountingGross(), AccountingRecords(), AccountingSummary(), amounts(), LearningBoundaries(), LearningInventory() (+13 more)

### Community 7 - "test_learning_engine.py"
Cohesion: 0.15
Nodes (39): digest(), encode(), evaluate(), main(), markdown(), packet_checks(), protected(), protected_windows() (+31 more)

### Community 8 - "test_state_contract.py"
Cohesion: 0.18
Nodes (23): at(), build_state(), buy(), free_port(), normalize(), pin_clock(), parametrize, Dashboard read-path contract: fixed Store-seeded ledgers and a pinned clock.… (+15 more)

### Community 9 - "test_execution_pilot.py"
Cohesion: 0.25
Nodes (9): ExecutionPilot, pilot(), parametrize, test_crash_after_entry_resumes_exit_without_new_entry(), test_final_pilot_boundary_blocks_wrong_or_oversize_requests(), test_pilot_and_strategy_workers_cannot_share_authority(), test_pilot_recovers_lost_accepted_entry_without_duplicate(), test_pilot_refuses_existing_positions() (+1 more)

### Community 10 - "scripts"
Cohesion: 0.05
Nodes (37): @commitlint/cli, @commitlint/config-conventional, @commitlint/lint, @commitlint/load, husky, devDependencies, @commitlint/cli, @commitlint/config-conventional (+29 more)

### Community 11 - "provider.tsx"
Cohesion: 0.21
Nodes (15): Context, Detail, EvidenceDialog(), PacketDialog(), ResearchExperiments(), ResearchGates(), ResearchPackets(), ResearchStatus() (+7 more)

### Community 12 - "test_executor_ownership.py"
Cohesion: 0.22
Nodes (16): adapters(), fixture, parametrize, Account ownership through public broker methods; no real provider writes., test_changed_identity_latches_writes_even_if_the_original_identity_returns(), test_close_keeps_ownership_until_the_inflight_write_finishes(), test_closed_adapter_cannot_reacquire_authority_and_market_data_cannot_mutate(), test_different_accounts_can_write_and_read_only_observers_do_not_contend() (+8 more)

### Community 13 - "compilerOptions"
Cohesion: 0.07
Nodes (29): compilerOptions, allowJs, checkJs, esModuleInterop, incremental, isolatedModules, jsx, lib (+21 more)

### Community 14 - "contracts.ts"
Cohesion: 0.06
Nodes (34): api(), errorMessage(), empty, Seed, Snapshot, accountingSchema, amount, counts (+26 more)

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
Cohesion: 0.19
Nodes (19): CodexReviewer, material_hash(), screen(), validate_review(), parametrize, selection_fixture(), test_model_cannot_choose_unlisted_ticker_or_use_news_as_authority(), test_model_cannot_override_veto_or_invent_citations_or_numbers() (+11 more)

### Community 17 - "utcnow"
Cohesion: 0.13
Nodes (26): parse_bea(), Scoped BEA schedule; a date is retained without inventing an unspecified…, Validate provider fee records without estimating missing fees or rewriting…, record_fee(), validate_activity(), calendar_coverage(), Evidence-by-evidence readiness. No threshold changes or execution capability., All scoped categories need retained, current, forward-covering evidence.… (+18 more)

### Community 18 - "motion.tsx"
Cohesion: 0.14
Nodes (15): Dialog(), AnimationProvider(), initialMode(), initialSystem(), LoadingPanel(), Mode, readMode(), readSystem() (+7 more)

### Community 19 - "health-page.tsx"
Cohesion: 0.10
Nodes (26): metadata, HealthChanges(), HealthDetails(), HealthFooterStatus(), HealthMap(), HealthPage(), HealthSummary(), attention (+18 more)

### Community 20 - "replay_runner.py"
Cohesion: 0.19
Nodes (18): contract(), observe(), register(), state(), build_report(), code_hashes(), connect_readonly(), export_events() (+10 more)

### Community 21 - "relay.ts"
Cohesion: 0.13
Nodes (17): Context, dynamic, GET(), POST(), runtime, acceptsGzip(), compress, getPaths (+9 more)

### Community 22 - "test_activity_feed.py"
Cohesion: 0.12
Nodes (30): parse_sse(), ledger_source(), The caller holds a read transaction or the Store lock across this snapshot., destinations(), pure(), parametrize, Behavioral protection for money counted once and unknown evidence staying…, test_absence_of_fee_records_is_never_zero_fee_evidence_even_if_balances_match() (+22 more)

### Community 23 - "liquidity_runner.py"
Cohesion: 0.28
Nodes (19): digest(), Policy, binding(), get(), get_inventory_status(), hashes(), load(), now() (+11 more)

### Community 24 - "test_experiment.py"
Cohesion: 0.12
Nodes (24): Meetings, parse_fomc(), HTMLParser, Official FOMC meeting dates, scoped context only; no complete macro calendar., propose(), ATR14 + trend/breakout candidate and fixed fractional loss-budget sizing. All…, context(), fomc_html() (+16 more)

### Community 25 - "activity_feed.py"
Cohesion: 0.20
Nodes (24): activity_identifier(), batch_events(), main(), publish_projection(), Bounded paper activity acquisition and immutable evidence publication., Validate the selected acquisition, including legacy frame semantics., balances_match(), canonical() (+16 more)

### Community 27 - "test_liquidity_experiment.py"
Cohesion: 0.23
Nodes (15): evaluate(), floor(), Quote-only liquidity experiment. No orders, fills, positions, P&L or promotion., turnover(), walk(), Same-venue REST book/quote validation. Visible depth never guarantees a fill., _validate(), validate_book() (+7 more)

### Community 28 - "devDependencies"
Cohesion: 0.04
Nodes (48): eslint, eslint-config-next, @fontsource-variable/dm-sans, @fontsource-variable/space-grotesk, dependencies, @fontsource-variable/dm-sans, @fontsource-variable/space-grotesk, motion (+40 more)

### Community 29 - "intelligence.py"
Cohesion: 0.08
Nodes (28): ASTRAL paper-only service., collect(), health_inputs(), intelligence(), lifespan(), Local-only companion: independent DB and lifecycle preserve the shadow pilot., clean(), Collector (+20 more)

### Community 30 - "AlpacaPaper"
Cohesion: 0.07
Nodes (17): AlpacaPaper, Limiter, Fixed-host Alpaca paper adapter and a separately labelled durable simulator., No remote API. Fills are synthetic and do not model queueing/market impact., Simulator, account_identity(), AccountLease, OwnershipError (+9 more)

### Community 31 - "useDashboard"
Cohesion: 0.11
Nodes (29): OrderDialog(), AssetBar(), ConnectionBanner(), EquityChart(), ExecutionStream(), IntelligenceFeed(), ModeBadge(), OverviewFooter() (+21 more)

### Community 32 - "datetime"
Cohesion: 0.17
Nodes (12): command(), Bounded Codex CLI reviewer. Broker credentials and tools are not inherited., Frozen research contract and append-only observations. No execution interface., source_hashes(), One explicitly authorized execution experiment; never an alpha strategy. Uses…, Credential-free local feed read; headlines remain untrusted scoped context., Point-in-time evidence screening; language models cannot override vetoes., datetime (+4 more)

### Community 33 - "app-frame.tsx"
Cohesion: 0.29
Nodes (4): Clock(), ConnectionStatus(), HaltButton(), OpeningPanels()

### Community 34 - "test_activity_rollout.py"
Cohesion: 0.09
Nodes (34): Latency, Observation, Fixed-size histogram retains every observation without per-request rows., Sample current availability without treating it as collection success., activated_settings(), check_ledger(), ledger_bytes(), main() (+26 more)

### Community 35 - "test_review_repairs.py"
Cohesion: 0.18
Nodes (18): read_context(), daily_history(), fee(), parametrize, Locked review regressions. Synthetic brokers, patched models and tmp ledgers…, test_adapter_hashes_are_cached_local_and_covered_by_packet_hash(), test_all_vetoed_cycle_never_calls_model(), test_diagnostic_failure_still_journals_prospective_veto() (+10 more)

### Community 37 - "validate_pr_body.cjs"
Cohesion: 0.23
Nodes (11): fs, main(), readableText(), REQUIRED_CHECKS, REQUIRED_SECTIONS, sections(), validatePullRequestBody(), withoutComments() (+3 more)

### Community 38 - "test_evidence_storage.py"
Cohesion: 0.20
Nodes (22): current_accounting(), Read-only compatibility with ledgers predating the new tables., read_projection(), pack_bytes(), pack_text(), Versioned lossless encoding for new bulky evidence; legacy rows stay intact., reference_bytes(), reference_text() (+14 more)

### Community 39 - "ValueError"
Cohesion: 0.18
Nodes (10): diagnose(), Retrospective price-only prefixes. Never pretend these were known earlier., price_signal(), Pure OHLC hypothesis; caller validates provenance and time separately., QCAlgorithm, as_utc(), AstralBtcSignalParity, Compare both implementations in cloud memory; export aggregate diagnostics only. (+2 more)

### Community 40 - "overnight_watch.py"
Cohesion: 0.25
Nodes (9): audit(), now(), Bounded overnight observation of the existing GET-only localhost paper lab., safety(), watch(), write_summary(), parametrize, test_observer_counts_lost_write_and_http_failure() (+1 more)

### Community 41 - "collect_batch"
Cohesion: 0.16
Nodes (13): collect_batch(), FeedError, Use the adapter's authentication, process boundary and request budget., Incremental SSE framing; raw acquisition bytes are retained separately., SSEParser, stream_activities(), unique_object(), Bounded observation of existing accounting, independent of trading readiness. (+5 more)

### Community 42 - "test_health_engine.py"
Cohesion: 0.08
Nodes (27): lifespan(), Standalone health service, separate process and ledger from telemetry/trading., state(), fresh(), HealthEngine, Independent assessments from telemetry observations; no trading authority., effective(), HealthMonitor (+19 more)

### Community 43 - "navigation.tsx"
Cohesion: 0.40
Nodes (3): NavLink(), Navigation(), pages

### Community 44 - "retain_batch"
Cohesion: 0.21
Nodes (16): Commit even rejected records before publishing or raising their failure., retain_batch(), start_batch(), import_capture(), controlled_current(), A mock-provider acceptance, not evidence about another provider account., replay(), test_abandoned_batch_and_publication_failure_do_not_hide_evidence() (+8 more)

### Community 45 - "Store"
Cohesion: 0.10
Nodes (36): create_app(), ExitPlan, Halt, Intent, ResearchBar, RiskCandidate, BrokerFailure, Exception (+28 more)

### Community 46 - "number"
Cohesion: 0.15
Nodes (21): Isolated deterministic portfolio execution model. No broker or Store imports.…, floor_step(), number(), Reproducible research proposals. No network, randomness, or order side effects., decide(), Deterministic timing hypotheses. Produces candidates, never orders or fills., One-unit synthetic quote replay, with fills strictly AFTER decisions. Quote-…, replay() (+13 more)

### Community 47 - "boundaries.test.ts"
Cohesion: 0.32
Nodes (6): allowlist, files, isClient(), lines(), root, text()

### Community 48 - "import_ledger"
Cohesion: 0.17
Nodes (13): import_ledger(), Copy captured rows into a new disposable Store, leaving source bytes alone., verify_inputs(), document(), fixture, setup(), test_fixture_mapping_and_missing_originals_cannot_satisfy_private_acceptance(), test_sanitized_package_replays_without_private_inputs_and_counts_fees_once() (+5 more)

### Community 49 - "check-skills.cjs"
Cohesion: 0.33
Nodes (6): checkSkills(), crypto, fs, hashSkillFolder(), path, ROOT

### Community 50 - "audit_crypto"
Cohesion: 0.32
Nodes (7): audit_crypto(), Read-only reconciliation analysis. Hypotheses cannot become ledger entries., Compare authoritative gross executions and positions; explain, never waive. Fee…, reconciliation_fixture(), test_confirmed_fee_matches_and_duplicate_activity_is_not_counted_twice(), test_exact_fee_hypothesis_never_clears_an_unconfirmed_difference(), test_incomplete_or_conflicting_execution_evidence_cannot_match()

### Community 52 - "commitlint.config.cjs"
Cohesion: 0.83
Nodes (3): bodyMaxLineLength(), footerMaxLineLength(), maxLineLength()

### Community 58 - "test_quantconnect_validation.py"
Cohesion: 0.16
Nodes (28): bundle(), compare(), main(), new_output(), pinned_sources(), Package an in-cloud comparison or validate its aggregate-only diagnostic log., sha(), evaluate() (+20 more)

## Knowledge Gaps
- **154 isolated node(s):** `Source`, `metadata`, `dynamic`, `runtime`, `dynamic` (+149 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Store` connect `Store` to `timestamp`, `run`, `dumps`, `test_portfolio_replay.py`, `test_learning_engine.py`, `test_state_contract.py`, `test_executor_ownership.py`, `screen`, `utcnow`, `replay_runner.py`, `test_activity_feed.py`, `liquidity_runner.py`, `test_experiment.py`, `activity_feed.py`, `test_liquidity_experiment.py`, `intelligence.py`, `AlpacaPaper`, `datetime`, `test_activity_rollout.py`, `test_review_repairs.py`, `test_evidence_storage.py`, `test_health_engine.py`, `retain_batch`, `import_ledger`?**
  _High betweenness centrality (0.070) - this node is a cross-community bridge._
- **Why does `utcnow()` connect `utcnow` to `timestamp`, `Engine`, `run`, `dumps`, `test_execution_pilot.py`, `screen`, `replay_runner.py`, `activity_feed.py`, `intelligence.py`, `AlpacaPaper`, `datetime`, `test_activity_rollout.py`, `test_review_repairs.py`, `test_evidence_storage.py`, `ValueError`, `collect_batch`, `test_health_engine.py`, `retain_batch`, `Store`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._
- **Why does `Engine` connect `Engine` to `datetime`, `test_activity_rollout.py`, `dumps`, `run`, `test_portfolio_replay.py`, `test_review_repairs.py`, `test_state_contract.py`, `collect_batch`, `test_execution_pilot.py`, `Store`, `screen`, `utcnow`, `replay_runner.py`, `test_activity_feed.py`, `test_experiment.py`, `AlpacaPaper`?**
  _High betweenness centrality (0.031) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `Store` (e.g. with `ExitPlan` and `Halt`) actually correct?**
  _`Store` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 102 inferred relationships involving `ValueError` (e.g. with `at()` and `cost_report()`) actually correct?**
  _`ValueError` has 102 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `Engine` (e.g. with `ExitPlan` and `Halt`) actually correct?**
  _`Engine` has 12 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Source`, `metadata`, `dynamic` to the rest of the system?**
  _154 weakly-connected nodes found - possible documentation gaps or missing edges._