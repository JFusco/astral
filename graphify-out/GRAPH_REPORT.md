# Graph Report - astral-trading  (2026-10-27)

## Corpus Check
- 205 files · ~81,109 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1497 nodes · 4733 edges · 57 communities (51 shown, 6 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 241 edges (avg confidence: 0.7)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `3c5d7759`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_event_sources.py
- Engine
- run
- dumps
- experiment.py
- test_portfolio_replay.py
- ui.ts
- test_learning_engine.py
- Settings
- BrokerFailure
- scripts
- useDashboard
- test_executor_ownership.py
- compilerOptions
- contracts.ts
- support.cjs
- screen
- datetime
- motion.tsx
- health-page.tsx
- ValueError
- relay.ts
- test_activity_feed.py
- liquidity_runner.py
- test_experiment.py
- Simulator
- quantconnect/__init__.py
- test_stage2_validation.py
- devDependencies
- Store
- OwnershipError
- overview-page.tsx
- test_review_repairs.py
- engine.py
- D
- Source
- utcnow
- validate_pr_body.cjs
- intelligence.py
- test_execution_pilot.py
- overnight_watch.py
- decide
- test_health_engine.py
- navigation.tsx
- panel.tsx
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
6. `Settings` - 67 edges
7. `dumps()` - 59 edges
8. `useDashboard()` - 53 edges
9. `BrokerFailure` - 51 edges
10. `AlpacaPaper` - 45 edges

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

## Communities (57 total, 6 thin omitted)

### Community 0 - "test_event_sources.py"
Cohesion: 0.11
Nodes (24): catalog(), Cells, event(), maintenance(), nyfed(), parse_events(), protocol(), HTMLParser (+16 more)

### Community 1 - "Engine"
Cohesion: 0.16
Nodes (4): age(), Engine, symbol_for(), book_for()

### Community 2 - "run"
Cohesion: 0.14
Nodes (32): test_ambiguous_fee_is_not_assigned_to_a_strategy(), test_readback_422_after_accepted_order_never_releases_reservation(), test_shared_pending_and_inventory_budget_across_strategies(), test_unquantified_external_market_order_blocks_new_risk(), test_global_fee_latch_blocks_strategy_sell_with_rule_violation(), test_exact_threshold_latches_across_reconcile_and_restart(), test_market_cap_and_price_tick_never_weaken_bound(), test_venue_power_is_not_double_reserved() (+24 more)

### Community 3 - "dumps"
Cohesion: 0.06
Nodes (106): at(), canonical(), cost_report(), digest(), evaluate(), main(), number(), precise() (+98 more)

### Community 4 - "experiment.py"
Cohesion: 0.16
Nodes (18): contract(), observe(), Frozen research contract and append-only observations. No execution interface., register(), source_hashes(), state(), main(), Register once; run offline diagnostic from an existing read-only history DB.… (+10 more)

### Community 5 - "test_portfolio_replay.py"
Cohesion: 0.13
Nodes (38): Assumptions, Portfolio, Isolated deterministic portfolio execution model. No broker or Store imports.…, replay(), stress_suite(), synthetic_events(), floor_step(), at() (+30 more)

### Community 6 - "ui.ts"
Cohesion: 0.10
Nodes (26): Dialog(), ViewDialog(), AccountingBoundaries(), AccountingCosts(), AccountingGross(), AccountingRecords(), AccountingSummary(), amounts() (+18 more)

### Community 7 - "test_learning_engine.py"
Cohesion: 0.11
Nodes (48): digest(), encode(), evaluate(), main(), markdown(), packet_checks(), protected(), protected_windows() (+40 more)

### Community 8 - "Settings"
Cohesion: 0.13
Nodes (29): create_app(), Settings, test_local_health_inputs_are_small_read_only_and_do_not_export_account_data(), test_only_one_executor_can_own_database(), test_unconfigured_alpaca_never_falls_back_to_simulator(), at(), build_state(), buy() (+21 more)

### Community 9 - "BrokerFailure"
Cohesion: 0.22
Nodes (12): ExitPlan, Halt, Intent, ResearchBar, RiskCandidate, BrokerFailure, Exception, Exception (+4 more)

### Community 10 - "scripts"
Cohesion: 0.05
Nodes (37): @commitlint/cli, @commitlint/config-conventional, @commitlint/lint, @commitlint/load, husky, devDependencies, @commitlint/cli, @commitlint/config-conventional (+29 more)

### Community 11 - "useDashboard"
Cohesion: 0.19
Nodes (19): HealthFooterStatus(), Context, useDashboard(), PacketDialog(), ResearchExperiments(), ResearchGates(), ResearchLab(), ResearchPackets() (+11 more)

### Community 12 - "test_executor_ownership.py"
Cohesion: 0.22
Nodes (16): adapters(), fixture, parametrize, Account ownership through public broker methods; no real provider writes., test_changed_identity_latches_writes_even_if_the_original_identity_returns(), test_close_keeps_ownership_until_the_inflight_write_finishes(), test_closed_adapter_cannot_reacquire_authority_and_market_data_cannot_mutate(), test_different_accounts_can_write_and_read_only_observers_do_not_contend() (+8 more)

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

### Community 16 - "screen"
Cohesion: 0.20
Nodes (19): CodexReviewer, material_hash(), screen(), validate_review(), parametrize, selection_fixture(), test_model_cannot_choose_unlisted_ticker_or_use_news_as_authority(), test_model_cannot_override_veto_or_invent_citations_or_numbers() (+11 more)

### Community 17 - "datetime"
Cohesion: 0.09
Nodes (31): parse_bea(), HTMLParser, Scoped BEA schedule; a date is retained without inventing an unspecified…, Schedule, Retain scoped official calendar catalogs; never certify missing categories., Maintenance needs two current publisher lists. NY Fed remains partial BLS., retain_additional_scopes(), retain_scopes() (+23 more)

### Community 18 - "motion.tsx"
Cohesion: 0.13
Nodes (15): AnimationProvider(), initialMode(), initialSystem(), LoadingPanel(), Mode, readMode(), readSystem(), Reveal() (+7 more)

### Community 19 - "health-page.tsx"
Cohesion: 0.13
Nodes (19): metadata, HealthChanges(), HealthDetails(), HealthMap(), HealthPage(), HealthSummary(), attention, inTopic() (+11 more)

### Community 20 - "ValueError"
Cohesion: 0.19
Nodes (18): evaluate(), floor(), Quote-only liquidity experiment. No orders, fills, positions, P&L or promotion., turnover(), walk(), Same-venue REST book/quote validation. Visible depth never guarantees a fill., _validate(), validate_book() (+10 more)

### Community 21 - "relay.ts"
Cohesion: 0.07
Nodes (31): dynamic, metadata, Page(), Context, dynamic, GET(), POST(), runtime (+23 more)

### Community 22 - "test_activity_feed.py"
Cohesion: 0.06
Nodes (93): activity_identifier(), collect_batch(), current_accounting(), FeedError, main(), parse_sse(), publish_projection(), Bounded paper activity acquisition and immutable evidence publication. (+85 more)

### Community 23 - "liquidity_runner.py"
Cohesion: 0.32
Nodes (17): digest(), Policy, binding(), get(), get_inventory_status(), hashes(), load(), now() (+9 more)

### Community 24 - "test_experiment.py"
Cohesion: 0.10
Nodes (31): Meetings, parse_fomc(), HTMLParser, Official FOMC meeting dates, scoped context only; no complete macro calendar., diagnose(), Retrospective price-only prefixes. Never pretend these were known earlier., evidence_for(), Credential-free local feed read; headlines remain untrusted scoped context. (+23 more)

### Community 25 - "Simulator"
Cohesion: 0.12
Nodes (5): No remote API. Fills are synthetic and do not model queueing/market impact., Simulator, test_connected_research_refreshes_after_history_and_never_writes_orders(), fixture, research_engine()

### Community 27 - "test_stage2_validation.py"
Cohesion: 0.27
Nodes (10): audit_crypto(), Read-only reconciliation analysis. Hypotheses cannot become ledger entries., Compare authoritative gross executions and positions; explain, never waive. Fee…, parametrize, Synthetic decision-path and fault tests; none are broker-paper executions., reconciliation_fixture(), test_confirmed_fee_matches_and_duplicate_activity_is_not_counted_twice(), test_duplicate_and_out_of_order_partial_readbacks_preserve_quantity() (+2 more)

### Community 28 - "devDependencies"
Cohesion: 0.04
Nodes (48): eslint, eslint-config-next, @fontsource-variable/dm-sans, @fontsource-variable/space-grotesk, dependencies, @fontsource-variable/dm-sans, @fontsource-variable/space-grotesk, motion (+40 more)

### Community 29 - "Store"
Cohesion: 0.15
Nodes (9): Store, isolate_experiment_workers(), lab_path(), main(), Bounded, GET-only Alpaca dogfood session using a private copied ledger., main(), Explicit, bounded PAPER-only CLI. No web API can enable this pilot., test_shadow_cannot_submit_even_with_repeated_approvals() (+1 more)

### Community 30 - "OwnershipError"
Cohesion: 0.23
Nodes (7): Limiter, account_identity(), AccountLease, OwnershipError, private_owned(), Exception, Cooperative paper-account ownership for one OS user on one host.

### Community 31 - "overview-page.tsx"
Cohesion: 0.10
Nodes (21): OrderDialog(), AssetBar(), EquityChart(), IntelligenceFeed(), ModeBadge(), OverviewFooter(), OverviewPage(), views (+13 more)

### Community 32 - "test_review_repairs.py"
Cohesion: 0.18
Nodes (18): read_context(), daily_history(), fee(), parametrize, Locked review regressions. Synthetic brokers, patched models and tmp ledgers…, test_adapter_hashes_are_cached_local_and_covered_by_packet_hash(), test_all_vetoed_cycle_never_calls_model(), test_diagnostic_failure_still_journals_prospective_veto() (+10 more)

### Community 33 - "engine.py"
Cohesion: 0.25
Nodes (11): ASTRAL paper-only service., build_report(), code_hashes(), connect_readonly(), export_events(), Read-only ledger export, fixed future window and offline stress receipts. No…, register_holdout(), report_state() (+3 more)

### Community 34 - "D"
Cohesion: 0.20
Nodes (13): D(), Fixed-host Alpaca paper adapter and a separately labelled durable simulator., Failure scenarios and adversarial selection cases; all trades are synthetic., test_api_shadow_does_not_enable_orders_and_rejects_bypass_fields(), test_intraday_exit_cannot_liquidate_swing_inventory(), test_late_confirmed_asset_fee_is_idempotent_and_reconciles(), test_local_exit_survives_restart_and_unknown_response(), test_quantity_and_shared_risk_boundaries() (+5 more)

### Community 36 - "utcnow"
Cohesion: 0.16
Nodes (10): AlpacaPaper, utcnow(), main(), test_missing_heartbeat_invalidates_all_cached_green_nodes(), test_unchanged_incident_with_new_source_timestamp_does_not_alert_again(), test_quote_adapter_preserves_prices_and_units_unknown_if_book_fails(), test_quote_adapter_retains_raw_book_and_versions_new_normalization(), parametrize (+2 more)

### Community 37 - "validate_pr_body.cjs"
Cohesion: 0.23
Nodes (11): fs, main(), readableText(), REQUIRED_CHECKS, REQUIRED_SECTIONS, sections(), validatePullRequestBody(), withoutComments() (+3 more)

### Community 38 - "intelligence.py"
Cohesion: 0.11
Nodes (25): collect(), health_inputs(), intelligence(), lifespan(), Local-only companion: independent DB and lifecycle preserve the shadow pilot., clean(), Collector, date() (+17 more)

### Community 39 - "test_execution_pilot.py"
Cohesion: 0.27
Nodes (10): pilot(), parametrize, test_crash_after_entry_resumes_exit_without_new_entry(), test_final_pilot_boundary_blocks_wrong_or_oversize_requests(), test_pilot_and_strategy_workers_cannot_share_authority(), test_pilot_recovers_lost_accepted_entry_without_duplicate(), test_pilot_refuses_existing_positions(), test_synthetic_round_trip_and_completed_resume_do_not_buy_twice() (+2 more)

### Community 40 - "overnight_watch.py"
Cohesion: 0.25
Nodes (9): audit(), now(), Bounded overnight observation of the existing GET-only localhost paper lab., safety(), watch(), write_summary(), parametrize, test_observer_counts_lost_write_and_http_failure() (+1 more)

### Community 41 - "decide"
Cohesion: 0.29
Nodes (13): decide(), Deterministic timing hypotheses. Produces candidates, never orders or fills., One-unit synthetic quote replay, with fills strictly AFTER decisions. Quote-…, replay(), test_disabled_model_keeps_deterministic_arm_in_new_observations(), event(), parametrize, test_entry_cancels_if_research_expires_during_latency() (+5 more)

### Community 42 - "test_health_engine.py"
Cohesion: 0.09
Nodes (25): lifespan(), Standalone health service, separate process and ledger from telemetry/trading., state(), fresh(), HealthEngine, Independent assessments from telemetry observations; no trading authority., effective(), HealthMonitor (+17 more)

### Community 43 - "navigation.tsx"
Cohesion: 0.40
Nodes (3): NavLink(), Navigation(), pages

### Community 44 - "panel.tsx"
Cohesion: 0.18
Nodes (15): items, MarketUniverse(), OrbitalUniverse(), OrbitItem, ExecutionStream(), PositionsPanel(), SourceDialog(), Empty() (+7 more)

### Community 47 - "boundaries.test.ts"
Cohesion: 0.32
Nodes (6): allowlist, files, isClient(), lines(), root, text()

### Community 49 - "check-skills.cjs"
Cohesion: 0.33
Nodes (6): checkSkills(), crypto, fs, hashSkillFolder(), path, ROOT

### Community 51 - "test_trade_history.py"
Cohesion: 0.39
Nodes (8): aggregate(), batch(), parametrize, test_bad_trade_records_fail_closed(), test_history_shares_completed_days_and_reconstructs_each_immutable_batch(), test_missing_trade_day_is_not_filled_from_quotes(), test_provider_pagination_must_finish_before_history_is_accepted(), test_trade_only_bars_deduplicate_and_exclude_incomplete_day()

### Community 52 - "commitlint.config.cjs"
Cohesion: 0.83
Nodes (3): bodyMaxLineLength(), footerMaxLineLength(), maxLineLength()

### Community 58 - "test_quantconnect_validation.py"
Cohesion: 0.11
Nodes (33): QCAlgorithm, as_utc(), AstralBtcSignalParity, Compare both implementations in cloud memory; export aggregate diagnostics only., bundle(), compare(), main(), new_output() (+25 more)

## Knowledge Gaps
- **154 isolated node(s):** `Source`, `metadata`, `dynamic`, `runtime`, `dynamic` (+149 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Store` connect `Store` to `test_event_sources.py`, `run`, `dumps`, `experiment.py`, `test_portfolio_replay.py`, `test_learning_engine.py`, `Settings`, `BrokerFailure`, `test_executor_ownership.py`, `screen`, `datetime`, `test_activity_feed.py`, `test_experiment.py`, `Simulator`, `test_review_repairs.py`, `D`, `utcnow`, `intelligence.py`, `test_execution_pilot.py`, `test_health_engine.py`, `test_trade_history.py`?**
  _High betweenness centrality (0.059) - this node is a cross-community bridge._
- **Why does `Engine` connect `Engine` to `test_review_repairs.py`, `engine.py`, `D`, `dumps`, `utcnow`, `experiment.py`, `test_portfolio_replay.py`, `test_execution_pilot.py`, `Settings`, `BrokerFailure`, `run`, `screen`, `test_activity_feed.py`, `test_experiment.py`, `Simulator`, `test_stage2_validation.py`, `Store`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Why does `D()` connect `D` to `Engine`, `engine.py`, `dumps`, `run`, `test_portfolio_replay.py`, `Settings`, `BrokerFailure`, `decide`, `screen`, `datetime`, `ValueError`, `test_experiment.py`, `Simulator`, `test_stage2_validation.py`?**
  _High betweenness centrality (0.035) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `Store` (e.g. with `ExitPlan` and `Halt`) actually correct?**
  _`Store` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 91 inferred relationships involving `ValueError` (e.g. with `at()` and `cost_report()`) actually correct?**
  _`ValueError` has 91 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `Engine` (e.g. with `ExitPlan` and `Halt`) actually correct?**
  _`Engine` has 12 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Source`, `metadata`, `dynamic` to the rest of the system?**
  _154 weakly-connected nodes found - possible documentation gaps or missing edges._