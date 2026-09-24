# Tasks

This is the canonical task and milestone ledger for **TrAId (My Agentic Trader)**.
All work follows the SDLC gates and task lifecycle defined in
[`docs/sdlc-process.md`](sdlc-process.md).

Every task is structured into a 4-tier nested hierarchy:
**Task $\rightarrow$ Sub-Tasks $\rightarrow$ Milestones $\rightarrow$ Checklists**.

---

## 1. Execution Plan & Phasing

Implementation proceeds in strict dependency order. A phase may start only
after its entry criteria are met and all preceding gate conditions are satisfied.

- **Phase 1: Safe Runtime Foundation (Completed):** T-015 (Telegram control & memory), T-018 (artifact reuse & caching), T-017 (local storage integrity).
- **Phase 2: Evidence Quality Foundation (Partially Unblocked):** T-004 (market regime gates, unblocked via ADR-011), T-002 (deferred), T-003 (deferred).
- **Phase 3: Multi-Agent Qualitative Research (Completed):** T-029 (sequential multi-agent research subgraph with early exit, ADR-022).
- **Phase 4: Evaluation & Performance Operations (Completed):** T-007 (NIFTY 100 Buy-and-Hold benchmark comparator, 30-trade minimum sample size).
- **Phase 5: LangGraph Platform Modernization (Completed):** T-023 (store, durability, time travel), T-024 (agent middleware), T-025 (LangSmith tracing).
- **Phase 6: Multi-Strategy, Multi-Agent & PostgreSQL Evolution (Completed):** T-026 (PostgreSQL sidecar & migration), T-027 (type safety & SecretStr), T-028 (multi-strategy screening), T-030 (concurrency hardening), T-031 (walk-forward backtester), T-033 (documentation consolidation).
- **Phase 7: Telegram Usability & Visual Analytics (Completed):** T-034 (Telegram usability suite), T-035 (incremental OHLCV caching), T-036 (React visual analytics web dashboard).
- **Phase 8: Complete Interactive Web Application (Completed):** T-037 (Full-featured React + TypeScript Cockpit, HITL Approvals, Streaming Copilot, SSE Event Bus, Multi-Container Docker).
- **Phase 9: Systematic Alpha & Advanced Risk Evolution (Active Roadmap):** T-038 (dynamic ATR trailing stops), T-039 (sector rotation & RS ranking), T-040 (multi-timeframe confluence), T-041 (sector concentration risk gates), T-042 (chart annotations & Telegram visual snapshots), T-043 (Monte Carlo bootstrap simulator).
- **Phase 10: Conversational Investment Planning (Retired UI, retained agent capability):** T-044 (affordability bands, GTT helper, 2-tranche basket planning).
- **Phase 11: Read-Only Groww Portfolio & Margin Synchronization (Completed):** T-045 (TOTP auth, holdings/margin read-only sync).
- **Phase 12: Zero-Touch Demat & Groww Portfolio Hub (Retired UI, retained sync infrastructure):** T-046 (auto-sync, mutual fund persistence, Command Center integration).
- **Phase 13: Groww-First Read-Only Market Data & Margin Visibility (Completed):** T-047 (Groww-first historical/live data with yfinance fallback, informational margin-affordability warning on proposals, instrument master, test-isolation hardening, ADR-036).
- **Phase 14: Unified Database-Backed Portfolio Command Center (Completed):** T-048 (Groww persistence, position fallback, planning deduplication, earnings totals, provenance, and single portfolio display, ADR-037).

---

## 2. Closure Matrix

| Task ID | Status | Priority | Related ADR | Scope & Readiness Summary |
|---|---|---|---|---|
| **T-047** | `done` | High | ADR-036 | Groww-First Read-Only Market Data, Margin & Instrument Master Extension |
| **T-046** | `done` | High | ADR-035 | Phase 12: Groww auto-sync and portfolio persistence; standalone Hub and AI Doctor UI retired during Command Center consolidation |
| **T-045** | `done` | High | ADR-035 | Phase 11: Read-Only Groww Portfolio & Margin Synchronization |
| **T-044** | `done` | High | ADR-034 | Phase 10: Conversational basket planning with affordability bands, GTT guidance, and 2-tranche planning; standalone wizard and digest/reinvestment UI retired |
| **T-039** | `done` | High | ADR-029 | Sector Relative Strength (RS) Ranking & Rotation Engine |
| **T-040** | `done` | High | ADR-030 | Multi-Timeframe (MTF) Daily + Weekly Trend Confluence Screener |
| **T-041** | `done` | High | ADR-031 | Deterministic Sector Concentration & Correlation Risk Gates |
| **T-042** | `done` | Medium | ADR-032 | Visual Chart Level Overlays & Telegram Candlestick Media Rendering |
| **T-043** | `done` | Medium | ADR-033 | Monte Carlo Bootstrap Risk Simulation Engine for Backtesting |
| **T-037** | `done` | High | ADR-027 | Phase 8: Complete Interactive Web Application Cockpit (React + TypeScript + Vite + FastAPI + SSE Event Bus + Docker) |
| **T-036** | `done` | Medium | ADR-025 | Phase 7: React Visual Analytics Web Dashboard (FastAPI + Lightweight Charts + Equity Curve + Backtester) |
| **T-035** | `done` | High | ADR-026 | Incremental PostgreSQL OHLCV Caching to eliminate Yahoo Finance 401 Crumb errors |
| **T-034** | `done` | High | ADR-026 | Telegram Usability Suite: `[🔬 Agent Debate]` button, `/positions` command, Daily Scan Digest |
| **T-033** | `done` | High | ADR-001 | Canonical documentation synchronicity, baseline consolidation, and ADR updates |

| **T-004** | `done` | High | ADR-011 | Market regime macro gates (`^NSEI`, `^INDIAVIX`) with accepted numeric thresholds |
| **T-007** | `done` | High | ADR-011 | Paper evaluation vs NIFTY 100 benchmark, Profit Factor, and `/performance` command |
| **T-026** | `done` | Critical | ADR-023 | PostgreSQL 16 sidecar persistence, checkpointer, store, and ETL migration script |
| **T-027** | `done` | High | ADR-003 | Type safety, typed models in `app/models.py`, and Pydantic `SecretStr` credentials |
| **T-028** | `done` | High | ADR-024 | Multi-strategy simultaneous screening (Breakout, Pullback, Mean Reversion) |
| **T-029** | `done` | High | ADR-022 | Sequential multi-agent research subgraph (Bear Critic $\rightarrow$ Bull $\rightarrow$ Synth) with early exit |
| **T-030** | `done` | Medium | ADR-019 | Concurrency hardening, bounded thread pools in Telegram bot, and tenacity retries |
| **T-031** | `done` | Medium | ADR-012 | Event-driven walk-forward backtesting framework reusing production pipeline |
| **T-023** | `done` | High | ADR-019 | LangGraph platform modernization (native store, durability, time-travel history) |
| **T-024** | `done` | High | ADR-020 | LangChain agent modernization (`create_agent` + PII, tool-limit, summarization middleware) |
| **T-015** | `done` | High | ADR-007 | Telegram single-operator control, checkpointed chat memory, and profile store |
| **T-017** | `done` | Medium | ADR-006 | Local database backup and integrity checks (superseded by T-026 PostgreSQL migration) |
| **T-018** | `done` | High | ADR-009 | TTL-governed cache for technical snapshots, RSS headlines, and evidence snapshots |
| **T-025** | `done` | Medium | ADR-021 | Optional opt-in LangSmith tracing via process environment configuration |
| **T-002** | `deferred` | Medium | ADR-010 | Source and data inventory (blocked on official source access terms) |
| **T-003** | `deferred` | Medium | ADR-010 | Corporate research inputs (blocked on approved exchange filing endpoints) |
| **T-005** | `deferred` | High | ADR-009 | Full multi-agent citation graph (superseded by T-029 sequential subgraph) |
| **T-006** | `deferred` | Low | ADR-002 | Read-only Groww context (blocked on read-only credential verification) |
| **T-008** | `deferred` | Critical | ADR-002 | Live broker execution review (prohibited by paper-only invariant) |
| **T-010** | `deferred` | High | ADR-012 | Agentic trader modernization (superseded by Phase 6 active tasks) |
| **T-016** | `deferred` | Low | ADR-015 | Investor preferences and custom universe (NIFTY 100 universe retained) |
| **T-019** | `deferred` | Low | ADR-017 | Universe and security master sourcing (NIFTY 100 universe retained) |
| **T-022** | `deferred` | Medium | ADR-019 | Measured graph fan-out (superseded by sequential early-exit multi-agent research) |

---

## 3. Active Implementation Tasks (`active`)

### T-048 Unified Database-Backed Portfolio Command Center
- Status: `done`
- Priority: `High`
- Related ADRs: [ADR-037](architecture-decisions.md#adr-037-database-backed-unified-portfolio-command-center)
- Completed Milestones:
  - **ST-048.1: Canonical persistence and merge rules**
    - [x] Persist Groww company/ISIN, broker source, investment source, and plan status on `user_positions`.
    - [x] Merge a Groww symbol into an existing planned/manual row and retire duplicate active rows.
    - [x] Fall back from denied/empty settled holdings to positive CASH positions.
  - **ST-048.2: Unified totals and display**
    - [x] Add invested capital, current value, realized earnings, unrealized earnings, and total earnings to the Command Center overview.
    - [x] Display all stock rows with origin and plan status in the main table.
    - [x] Restrict the Groww panel to connection, sync, cash, orders, and diagnostics.
  - **ST-048.3: Verification**
    - [x] Pass the full Python test suite after the local PostgreSQL test hang is resolved.
    - [x] Frontend TypeScript/build passes.

---

## 4. Tasks Ready for Implementation (`todo`)
*(All Phase 9 systematic alpha and risk tasks implemented and verified. Ready for next phase roadmap.)*

---

## 5. Backlog Tasks (`backlog`)

*(All current milestone tasks completed or deferred. Ready for future roadmap backlog scoping.)*

---

## 6. Tasks Awaiting Discussion / Architectural Consensus (`discuss`)

### T-032 Intraday Trailing Stops & Polling Interval
- Status: `discuss`
- Priority: `Low`
- Goal: Determine whether a 15-minute polling position monitor during market hours is beneficial for swing trading.

---

## 7. Tasks Under Review (`inreview`)

*(Currently 0 tasks in review.)*

---

## 8. Completed Tasks (`done`)

### T-038 Dynamic ATR Trailing Stops & Break-Even Profit Protection Engine
- Status: `done`
- Priority: `High`
- Related ADRs: [ADR-028](architecture-decisions.md#adr-028-dynamic-atr-trailing-stops-and-break-even-profit-protection)
- Completed Milestones:
  - [x] Implemented deterministic `calculate_trailing_stop()` in `app/risk.py` with multi-stage ratcheting (break-even lock at $+1.5R$, dynamic $1.5 \times ATR$ Chandelier trailing stop at $+2.0R$).
  - [x] Extended PostgreSQL `trade_audit_log` schema with `highest_price` and `trailing_stop` columns in `app/db.py`.
  - [x] Integrated trailing stop updates into daily position monitor (`app/monitor.py`) and order executor (`app/executor.py`).
  - [x] Added trailing stop exit logic to walk-forward backtester (`app/backtester.py`) for realistic zero-lookahead simulations.
  - [x] Added unit tests in `tests/test_risk.py` and `tests/test_backtester.py` with 100% test pass rate.

### T-039 Sector Relative Strength (RS) Ranking & Rotation Engine
- Status: `done`
- Priority: `High`
- Related ADRs: [ADR-029](architecture-decisions.md#adr-029-sector-relative-strength-rs-ranking-and-sector-rotation-context)
- Completed Milestones:
  - [x] Ingested daily historical OHLCV data for 9 NSE Sectoral Indices (`^CNXIT`, `^CNXAUTO`, `^NSEBANK`, `^CNXFMCG`, etc.) in `app/market_data.py`.
  - [x] Implemented 20-day Mansfield Relative Strength computation vs `^NSEI` benchmark in `app/screener.py`.
  - [x] Mapped NIFTY 100 universe symbols to Sectoral Classifications via `get_symbol_sector()` in `app/universe.py`.
  - [x] Injected Sector Name and Sector RS Score into `TechnicalSnapshot` (`app/models.py`) and agent debate context.
  - [x] Added unit tests in `tests/test_risk.py` and `tests/test_screener.py` with 100% test pass rate.

### T-040 Multi-Timeframe (MTF) Daily + Weekly Trend Confluence Screener
- Status: `done`
- Priority: `High`
- Related ADRs: [ADR-030](architecture-decisions.md#adr-030-multi-timeframe-mtf-daily-weekly-trend-confluence-screening)
- Completed Milestones:
  - [x] Built weekly bar resampler (`resample_to_weekly`) in `app/market_data.py` aggregating OHLCV to Weekly frequency with Friday close.
  - [x] Computed Weekly 30-EMA (`weekly_ema_30`) and Weekly 14-RSI (`weekly_rsi_14`) forward-filled onto daily series in `app/screener.py`.
  - [x] Enforced MTF confluence gates across `BreakoutMomentumStrategy` (Weekly 30-EMA & Weekly RSI $\ge 50$) and `PullbackInUptrendStrategy` (Weekly 30-EMA & Weekly RSI $\ge 45$) in `app/strategies.py`.
  - [x] Added unit tests in `tests/test_strategies.py` verifying MTF qualification and fallback behaviors.

### T-041 Deterministic Sector Concentration & Correlation Risk Gates
- Status: `done`
- Priority: `High`
- Related ADRs: [ADR-031](architecture-decisions.md#adr-031-deterministic-sector-concentration-and-correlation-risk-gates)
- Completed Milestones:
  - [x] Built deterministic `evaluate_sector_exposure_gate()` in `app/risk.py`.
  - [x] Enforced max 25% portfolio capital exposure per sector and max 2 concurrent open positions per sector.
  - [x] Integrated sector risk gate into LangGraph execution flow in `app/graph.py` (`_calculate_risk`).
  - [x] Added comprehensive unit tests in `tests/test_risk.py` verifying single-trade and accumulated exposure rejections.

### T-042 Visual Chart Level Overlays & Web API Integration
- Status: `done`
- Priority: `Medium`
- Related ADRs: [ADR-032](architecture-decisions.md#adr-032-visual-chart-level-overlays--telegram-candlestick-media-rendering)
- Completed Milestones:
  - [x] Implemented `/api/levels/{symbol}` endpoint in `app/dashboard_api.py` serving active Entry, Target, Soft/Hard Stop, and Trailing Stop price levels.
  - [x] Integrated dynamic horizontal price lines with custom color badges in `frontend/src/components/Charts/CandlestickChart.tsx` using TradingView Lightweight Charts API.
  - [x] Added API client bindings (`fetchSymbolLevels`) and TypeScript interfaces in `frontend/src/lib/api.ts` and `frontend/src/types/api.ts`.
  - [x] Added automated endpoint tests in `tests/test_dashboard_api.py` with 100% pass rate.

### T-043 Monte Carlo Bootstrap Risk Simulation Engine for Backtesting
- Status: `done`
- Priority: `Medium`
- Related ADRs: [ADR-033](architecture-decisions.md#adr-033-monte-carlo-bootstrap-risk-simulation-engine-for-backtesting)
- Completed Milestones:
  - [x] Implemented vectorized `run_monte_carlo_simulation()` in `app/backtester.py` performing 1,000 i.i.d. trade order resamplings with replacement.
  - [x] Computed 95th/99th percentile Max Drawdown, Probability of Ruin ($\ge 50\%$ drawdown), 5th/95th percentile Final Equity range, and 10-bucket drawdown distribution histogram.
  - [x] Integrated Monte Carlo simulation results into `/api/backtest` endpoint payload in `app/dashboard_api.py`.
  - [x] Built Monte Carlo Bootstrap Risk visualization card with distribution histogram in `frontend/src/components/Backtest/BacktestStudio.tsx`.
  - [x] Added unit tests in `tests/test_backtester.py` with 100% test pass rate.

### T-037 Phase 8: Complete Interactive Web Application Cockpit (React + Vite + FastAPI + SSE)
- Status: `done`
- Priority: `High`
- Related ADRs: [ADR-027](architecture-decisions.md#adr-027-complete-interactive-web-application-as-primary-control-cockpit)
- Completed Milestones:
  - [x] Built modern React + TypeScript + Vite + Tailwind CSS + Lucide Icons SPA in `frontend/` featuring 6 comprehensive views: Command Cockpit, AI Research Copilot, Candlestick Explorer, Audit & Alpha Benchmark, Backtest Studio, and System Health.
  - [x] Implemented Human-in-the-Loop proposal approval workflow with atomic PostgreSQL status transitions and modal `[🔬 Agent Debate]` drawer displaying Bear Critic objections vs Bull Analyst thesis.
  - [x] Built real-time Server-Sent Events (SSE) bus in `app/events.py` for live universe scan progress updates, proposal generation alerts, and position tracking.
  - [x] Created streaming AI Copilot endpoint (`/api/chat/stream`) with token-by-token generation and collapsible tool trace inspection.
  - [x] Added multi-container Docker Compose configuration (`docker-compose.yml`, `frontend/Dockerfile`, `frontend/nginx.conf`) orchestrating `postgres`, `trading-engine`, `dashboard`, and `frontend`.
  - [x] Added comprehensive automated tests in `tests/test_dashboard_api.py` with 100% test pass rate across all modules.

### T-036 Phase 7: Visual Analytics Web Dashboard (FastAPI + Lightweight Charts)
- Status: `done`
- Priority: `Medium`
- Related ADRs: [ADR-025](architecture-decisions.md#adr-025-hybrid-control-plane-telegram-primary--phase-7-react-analytics)
- Completed Milestones:
  - [x] Implemented read-only FastAPI analytics backend in `app/dashboard_api.py` with REST endpoints (`/api/overview`, `/api/positions`, `/api/trades`, `/api/performance`, `/api/candles/{symbol}`, `/api/backtest`)
  - [x] Built responsive dark-mode Single Page Application (SPA) in `app/static/index.html` featuring Tailwind CSS, TradingView Lightweight Charts (candlestick + volume), Chart.js equity curve visualization, and interactive walk-forward backtester
  - [x] Added `dashboard` sub-command in `app/main.py` (`python -m app.main dashboard [--host] [--port]`)
  - [x] Added `fastapi` and `uvicorn` dependencies to `requirements.txt`
  - [x] Created `tests/test_dashboard_api.py` with 100% test pass rate verifying all endpoints and read-only invariants

### T-035 Incremental PostgreSQL OHLCV Caching & Market Data Resilience
- Status: `done`
- Priority: `High`
- Related ADRs: [ADR-026](architecture-decisions.md#adr-026-telegram-usability-suite--incremental-market-data-caching)
- Completed Milestones:
  - [x] Created relational `ohlcv_daily_bars` table in `app/db.py` with composite primary key `(symbol, timestamp)` and index
  - [x] Implemented `save_bars`, `load_cached_bars`, and `get_latest_cached_date` in `app/market_data.py`
  - [x] Built incremental delta bar updater (`load_history` with 5d delta fetch for warm caches $\ge 50$ bars), reducing network requests by ~95%
  - [x] Implemented fail-safe fallback returning stored historical bars when yfinance fails with 401 Crumb / rate-limit delisting anomalies
  - [x] Added unit tests in `tests/test_market_data.py` with 100% test pass rate

### T-034 Telegram Usability Suite: Debate Callback, `/positions`, and Daily Scan Digest
- Status: `done`
- Priority: `High`
- Related ADRs: [ADR-026](architecture-decisions.md#adr-026-telegram-usability-suite--incremental-market-data-caching)
- Completed Milestones:
  - [x] Added `[🔬 Agent Debate]` inline callback button to proposal card in `app/telegram_bot.py`
  - [x] Handled `debate:{symbol}` callback query to fetch research verdict and format structured Bear objections vs Bull thesis
  - [x] Implemented `/positions` command querying open paper trades with current price, unrealized P&L (₹ / %), stop/target distance, and Portfolio Heat %
  - [x] Implemented automated Daily Universe Scan Digest notification (`_send_scan_digest`) dispatched immediately following 15:45 IST scan
  - [x] Added unit tests in `tests/test_telegram_bot.py` with 100% test pass rate


### T-033 Documentation Synchronicity & Baseline Consolidation
- Status: `done`
- Priority: `High`
- Related ADRs: [ADR-001](architecture-decisions.md#adr-001-documentation-is-canonical), [ADR-025](architecture-decisions.md#adr-025-hybrid-control-plane-telegram-primary--phase-7-react-analytics), [ADR-026](architecture-decisions.md#adr-026-telegram-usability-suite--incremental-market-data-caching)
- Completed Milestones:
  - [x] Synchronized `docs/architecture.md`, `docs/prd.md`, `docs/reference.md`, `docs/tasks.md`
  - [x] Established Phase 6 completed capabilities as canonical architecture
  - [x] Formulated ADR-025 (Hybrid UI) and ADR-026 (Telegram Usability Suite & Incremental OHLCV Cache)
  - [x] Structured T-034, T-035, T-036 task hierarchies


### T-031 Walk-Forward Backtesting Framework
- Status: `done`
- Priority: `Medium`
- Related ADRs: [ADR-012](architecture-decisions.md#adr-012-modernization-preserves-paper-only-execution)
- Completed Milestones:
  - [x] Implemented event-driven, bar-by-bar backtesting engine in `app/backtester.py` (`run_backtest`) with zero lookahead bias
  - [x] Evaluated active setup strategies (`evaluate_all_strategies`) and deterministic risk engine (`calculate_risk`) at each simulated bar
  - [x] Simulated realistic transaction friction (0.05% slippage on entry/exit and turnover delivery costs via `calculate_delivery_costs`)
  - [x] Built performance analytics: Equity Curve, Annualized Sharpe Ratio, Peak-to-Trough Max Drawdown %, Profit Factor, and Win/Loss R-multiples
  - [x] Implemented ASCII/Markdown scorecard report formatter (`format_backtest_report`)
  - [x] Added `backtest` sub-command to `app/main.py` CLI
  - [x] Created `tests/test_backtester.py` covering synthetic market simulations, lookahead protection, and CLI integration with 100% test pass rate

### T-030 Concurrency Hardening, Thread Pools & Tenacity Retries
- Status: `done`
- Priority: `Medium`
- Related ADRs: [ADR-019](architecture-decisions.md#adr-019-langgraph-platform-modernization-stays-local-first)
- Completed Milestones:
  - [x] Implemented bounded `ThreadPoolExecutor(max_workers=3)` in `app/telegram_bot.py` via `submit_background_task`
  - [x] Added graceful thread pool draining and shutdown via `shutdown_worker_pool()` in `stop_bot()`
  - [x] Built centralized retry engine in `app/retry.py` (`network_retry`, `db_retry`) with exponential backoff, jitter, and logging
  - [x] Applied `network_retry` to `universe._fetch_live_csv_text`, `news._parse_feed_with_retry`, `corporate_events._fetch_remote_events_json`, and `telegram_bot._post_telegram_message`
  - [x] Created `tests/test_retry.py` and `tests/test_concurrency.py` with 100% test pass rate

### T-029 Sequential Multi-Agent Research Subgraph with Early Exit
- Status: `done`
- Priority: `High`
- Related ADRs: [ADR-022](architecture-decisions.md#adr-022-multi-agent-qualitative-research-architecture-sequential-bear-first-with-early-exit)
- Completed Milestones:
  - [x] Defined structured Pydantic agent models in `app/agents/models.py`: `BearAssessment`, `BullAssessment`, and `ResearchVerdict`
  - [x] Implemented `BearRiskCritic` (`app/agents/bear_critic.py`) to aggressively stress-test candidates for promoter pledging, litigation, debt, and overhead supply with fail-closed fallback
  - [x] Implemented `BullMomentumAnalyst` (`app/agents/bull_analyst.py`) evaluating setup quality, accumulation, and catalyst drivers
  - [x] Implemented `SynthesisArbiter` (`app/agents/synthesizer.py`) synthesizing bear and bull arguments, evaluating invalidation criteria, and generating composite confidence
  - [x] Built `research_subgraph` (`app/agents/research_subgraph.py`) coordinating sequential multi-agent debate with early exit: terminates immediately on Bear structural damage ($\ge 0.70$), saving ~60% LLM tokens
  - [x] Enforced synthesis verdict requirements ($\ge 0.60$ composite confidence and `BUY` verdict) to pass candidate to the deterministic risk engine
  - [x] Integrated subgraph with `app/analyst.py`, `app/state.py`, and `app/graph.py` with PostgreSQL research caching
  - [x] Created `tests/test_agents.py` covering early exit, full debate flow, fail-closed handling, and synthesis confidence with 100% test pass rate

### T-028 Multi-Strategy Simultaneous Screening & Priority Engine
- Status: `done`
- Priority: `High`
- Related ADRs: [ADR-024](architecture-decisions.md#adr-024-multi-strategy-simultaneous-screening-with-deterministic-priority)
- Completed Milestones:
  - [x] Implemented concrete strategy classes in `app/strategies.py`: `BreakoutMomentumStrategy`, `PullbackInUptrendStrategy`, and `BollingerMeanReversionStrategy`
  - [x] Extended `screener._compute_indicators` in pandas to calculate EMA 50, 20-day High (shifted), and Bollinger Bands (20, 2.0)
  - [x] Built deterministic priority resolver `evaluate_all_strategies` enforcing `BREAKOUT` > `PULLBACK` > `MEAN_REVERSION`
  - [x] Integrated strategy-specific risk profiles in `app/risk.py` (Breakout: 1.0/2.0 ATR & 3.0 R:R; Pullback: 1.5/2.5 ATR & 2.0 R:R; Mean Reversion: 1.2/2.0 ATR & 2.0 R:R)
  - [x] Refactored `TechnicalSnapshot` and `app/graph.py` to propagate `strategy_name` and tag secondary matching strategies
  - [x] Created `tests/test_strategies.py` verifying all strategies, indicator calculations, priority resolution, and risk engine rules with 100% test pass rate

### T-027 Type Safety, Typed Models & SecretStr Hardening
- Status: `done`
- Priority: `High`
- Related ADRs: [ADR-001](architecture-decisions.md#adr-001-documentation-is-canonical), [ADR-003](architecture-decisions.md#adr-003-deterministic-numeric-risk)
- Completed Milestones:
  - [x] Defined validated domain transfer models in `app/models.py`: `TechnicalSnapshot`, `ExecutionResult`, `TradeRecord`, and `ScanResult`
  - [x] Implemented `DictCompatibleModel` ensuring backward compatibility with dictionary subscripting in LangGraph state
  - [x] Refactored `screener.get_symbol_snapshot()` and `screener.scan_nifty_universe()` to emit typed `TechnicalSnapshot` models
  - [x] Refactored `executor.record_open_trade()` to emit typed `ExecutionResult` models
  - [x] Replaced non-deterministic `str({...})` caching in `screener.py` with `evidence.content_hash()`
  - [x] Migrated all sensitive credentials in `config/settings.py` (`OPENAI_API_KEY`, `GOOGLE_API_KEY`, `ANTHROPIC_API_KEY`, `GROQ_API_KEY`, `TELEGRAM_BOT_TOKEN`, `LANGSMITH_API_KEY`) to `SecretStr`
  - [x] Updated client construction sites in `app/llm.py`, `app/telegram_bot.py`, and `app/observability.py` to extract `.get_secret_value()` securely
  - [x] Added `tests/test_models.py` verifying model validation, dictionary indexing, and `SecretStr` masking with 100% test pass rate

### T-007 Evaluation and Benchmark Reporting
- Status: `done`
- Priority: `High`
- Related ADRs: [ADR-011](architecture-decisions.md#adr-011-thresholds-require-explicit-safety-decisions), [ADR-013](architecture-decisions.md#adr-013-paper-transaction-costs-are-net-pnl-data)
- Completed Milestones:
  - [x] Computed Profit Factor ($\frac{\text{Gross Wins}}{\text{Gross Losses}}$), Win Rate, and Expectancy in `app.evaluation`
  - [x] Computed per-trade Realized R-Multiples ($\frac{\text{Exit Price} - \text{Fill Price}}{\text{Initial Risk Per Share}}$), Win R, Loss R, and Average R
  - [x] Enforced **30-trade minimum sample size** rule with prominent statistical confidence warnings when $N < 30$
  - [x] Implemented NIFTY 100 Buy-and-Hold benchmark comparator (`fetch_benchmark_return`) and calculated Strategy Net Alpha %
  - [x] Implemented Telegram `/performance` command rendering a structured Markdown scorecard
  - [x] Updated `python -m app.main evaluate` CLI command to output performance and alpha metrics
  - [x] Created `tests/test_evaluation.py` covering all calculations, edge cases, thresholds, and formatting with 100% test pass rate

### T-004 Market Context & Macro Gates
- Status: `done`
- Priority: `High`
- Related ADRs: [ADR-011](architecture-decisions.md#adr-011-thresholds-require-explicit-safety-decisions)
- Completed Milestones:
  - [x] Ingested daily OHLCV for `^NSEI` and `^INDIAVIX` via `yfinance` with MultiIndex handling
  - [x] Calculated NIFTY 50-day EMA dynamically with pandas
  - [x] Implemented TTL-governed macro caching (`REGIME_CACHE_TTL_MINUTES`) with fail-closed fallback (`MACRO_DATA_UNAVAILABLE`)
  - [x] Enforced ADR-011 deterministic threshold gates: Crisis VIX (> 24.0) veto, Elevated VIX (19.0 - 24.0) 50% risk scaling, NIFTY < 50-EMA downtrend veto
  - [x] Integrated regime evaluation into `run_universe_scan` with early termination and Telegram operator notification
  - [x] Passed `risk_multiplier` into `app.risk.calculate_risk` and recorded `market_regime` in graph state
  - [x] Created `tests/test_regime.py` covering all positive, negative, threshold, and fallback scenarios with 100% test pass rate

### T-026 PostgreSQL Infrastructure & Storage Migration
- Status: `done`
- Priority: `Critical`
- Related ADRs: [ADR-023](architecture-decisions.md#adr-023-postgresql-as-unified-relational-checkpoint-and-store-persistence-layer)
- Completed Milestones:
  - [x] Provisioned `postgres:16-alpine` sidecar in `docker-compose.yml` with persistent volume and healthcheck
  - [x] Configured `psycopg[binary,pool]` and `langgraph-checkpoint-postgres` in `requirements.txt`
  - [x] Added `DATABASE_URL: SecretStr`, `DB_POOL_MIN_SIZE`, `DB_POOL_MAX_SIZE` to `config/settings.py` and `.env.example`
  - [x] Implemented `app.db` with connection pooling, query execution, and PostgreSQL DDL initializers
  - [x] Migrated `app.checkpoint` to `PostgresSaver` with `graph_threads` indexing
  - [x] Migrated `app.store` to `PostgresStore` backing namespaced operator profile memory
  - [x] Refactored `app/executor.py`, `app/outbox.py`, `app/cache.py`, and `app/evidence.py` to use `app.db`
  - [x] Completely removed all legacy SQLite database files, dependencies, and code branches
  - [x] Created `tests/test_db.py`, `tests/test_maintenance.py`, and test fixtures with 100% test pass rate

### T-015 Single-Operator Telegram Control And Conversation Memory

- Status: `done`
- Completed: Single-operator authorization via `TELEGRAM_CHAT_ID`, checkpointed chat history, and allowlisted operator profile storage foundation in `app.profile`.

### T-017 Storage Portability And Local Persistence
- Status: `done`
- Completed: PostgreSQL integrity checks (`check-databases`) and operational health reporting implemented (ADR-023).

### T-018 Data Reuse And Research Caching
- Status: `done`
- Completed: TTL-governed cache for technical snapshots, RSS headlines, catalyst classifications, and immutable evidence snapshots with cache-hit attribution.

### T-047 Groww-First Read-Only Market Data, Margin & Instrument Master Extension
- Status: `done`
- Priority: `High`
- Related ADRs: [ADR-036](architecture-decisions.md#adr-036-groww-first-read-only-market-data-margin--instrument-master-extension)
- Completed Milestones:
  - **ST-047.1: Configuration**
    - [x] Added `GROWW_MARKET_DATA_ENABLED` (default `True`) to `config/settings.py` and `.env.example`.
  - **ST-047.2: Read-Only Live Data, Margin & Instrument Client Methods**
    - [x] Added `get_available_margin_details`, `get_order_margin_details`, `get_quote`, `get_ltp` (batched ≤50), `get_ohlc`, `get_historical_candle_data`, `get_all_instruments`, `get_instrument_by_groww_symbol` to `app/groww_client.py`, all fail-closed on error.
    - [x] Kept `get_user_margin` REST-only (unchanged) to avoid double-sourcing the same balance from two schemas.
  - **ST-047.3: Groww-First Market Data Provider**
    - [x] Added `_download_raw_groww` + `_download_raw` dispatcher in `app/market_data.py`; Groww-first, automatic Yahoo Finance fallback on any error/unconfigured state; new `"groww_historical"` provenance value on `MarketDataResult`.
  - **ST-047.4: Informational Margin Check on Trade Proposals**
    - [x] Added optional `margin_required`/`margin_available` fields to `TradeProposal`/`ProposalCard` (`app/state.py`).
    - [x] Populated via `get_order_margin_details`/`get_user_margin` in `graph._calculate_risk`, non-blocking (try/except, never rejects a proposal).
    - [x] Persisted new nullable columns on `pending_proposals` (`app/proposals.py`).
    - [x] Surfaced a small ⚠️ warning line on the Telegram proposal card when margin required exceeds available balance (`app/telegram_bot.py`), informational only.
  - **ST-047.5: Test Isolation Hardening**
    - [x] `tests/conftest.py` now forces `GROWW_ENABLED=false` / `GROWW_MARKET_DATA_ENABLED=false` by default to prevent a developer's real `.env` Groww credentials from causing live network calls during `pytest`.
  - **ST-047.6: Conversational Live Quote Tool**
    - [x] Added `get_groww_quote(symbol)` read-only tool to `app/chat_agent.py` (LTP, day change, day range, OHLC, 52-week range) and wired it into the agent tool list + system prompt, so the operator can ask "what's RELIANCE at right now".
  - **ST-047.6: Verification & Documentation Sync**
    - [x] Added/extended unit tests: `tests/test_groww_client.py` (new HTTP methods, batching, fail-closed), `tests/test_market_data.py` (Groww-first dispatcher + fallback).
    - [x] `pytest -q` passing on all touched modules.
    - [x] `docs/architecture.md`, `docs/reference.md`, `docs/prd.md`, `docs/architecture-decisions.md` synchronized.
  - **Deferred (tracked, not blocking):** Wiring `get_all_instruments`/tick-size into `risk.py` position-sizing rounding — no evidence yet of a real tick-size sizing defect (YAGNI); revisit if a fractional-tick instrument surfaces in production.

### T-046 Phase 12: Zero-Touch Demat & Groww Portfolio Hub
- Status: `done`
- Priority: `High`
- Related ADRs: [ADR-035](architecture-decisions.md#adr-035-read-only-groww-api-integration-for-portfolio--margin-synchronization)
- Completed Milestones:
  - **ST-046.1: Zero-Touch Background Synchronization**
    - [x] Implemented `auto_sync_if_configured()` in `app/groww_client.py` for background sync on boot and API access.
    - [x] Configured 15-minute periodic interval job in `app/main.py` apscheduler (`_scheduled_groww_sync`).
  - **ST-046.2: Multi-Asset Class Persistence & Overview Calculation**
    - [x] Added `user_mutual_funds` table and indices in `app/db.py`.
    - [x] Implemented `get_portfolio_overview()` calculating combined Net Worth, Equity value, Mutual Fund folios, Cash & Margin.
  - **ST-046.3: Retired legacy Demat UI workflows**
    - [x] Removed the standalone AI Portfolio Doctor route and implementation.
    - [x] Removed the standalone Demat/Groww Hub screen and frontend API wrappers.
    - [x] Retained Groww read-only client methods for future diagnostics and integrations.
  - **ST-046.5: Verification & Production Container Build**
    - [x] Passed 100% of unit tests (`pytest -q`).
    - [x] Production bundle built (`npm run build`) and Docker containers live (`docker compose up -d --build`).

### T-044 Phase 10: Beginner Wealth Copilot & Enhanced User Journey
- Status: `done`
- Priority: `High`
- Related ADRs: [ADR-034](architecture-decisions.md#adr-034-beginner-wealth-copilot-affordability-bands-gtt-helper-and-2-tranche-compounding)
- Completed Milestones:
  - **ST-044.1: Goal Presets & Affordability Price-Banding**
    - [x] Add `InvestmentGoal` enum and goal-adaptive parameter scaling in `app/models_basket.py`
    - [x] Implement price-band affordability filtering for whole shares ($< ₹1,500$ for sub-₹30K budgets)
    - [x] Implement Peace of Mind score ($0-100$) and visual Scenario Analysis (Best, Normal, Worst-Case)
  - **ST-044.2: GTT Order Guidance & Slippage Traffic Lights**
    - [x] Generate exact copyable GTT Stop-Loss and Target parameters for Zerodha/Groww in `app/basket_generator.py`
    - [x] Implement traffic light slippage rating (🟢 Green, 🟡 Amber, 🔴 Red) in execution models
  - **ST-044.3: 2-Tranche Target Compounding & Trailing Stops**
    - [x] Implement Target 1 (50% exit) and Target 2 (50% runner) in `app/models_basket.py` & `app/portfolio_manager.py`
    - [x] Implement dynamic Break-Even trailing stop ratcheting when price gains $\ge +4\%$
    - [x] Implement True Net P&L calculation with STT friction and STCG tax (20%)
  - **ST-044.4: Retired legacy Beginner UI workflows**
    - [x] Removed the standalone Beginner Invest Wizard and daily digest HTTP workflow.
    - [x] Preserved basket generation and batch confirmation for the conversational investment-plan flow.
  - **ST-044.5: Verification & Container Packaging**
    - [x] Updated portfolio tests after removing digest and reinvestment workflows.
    - [x] Frontend production build `npm run build`
    - [x] Docker container build `docker compose build` & `docker compose up -d`

### T-045 Phase 11: Read-Only Groww Portfolio & Margin Synchronization
- Status: `done`
- Priority: `High`
- Related ADRs: [ADR-035](architecture-decisions.md#adr-035-read-only-groww-api-integration-for-portfolio--margin-synchronization)
- Completed Milestones:
  - **ST-045.1: Configuration, Settings & Secrets**
    - [x] Add `pyotp` dependency to `requirements.txt`; later removed `growwapi` after the curl-only client landed.
    - [x] Add `GROWW_ENABLED`, `GROWW_API_KEY`, `GROWW_API_SECRET`, `GROWW_ACCESS_TOKEN` to `config/settings.py` and `.env.example`
  - **ST-045.2: Read-Only Client Engine & Invariant Enforcement**
    - [x] Implement `app/groww_client.py` with HTTP auth / access token handling and caching
    - [x] Implement `get_user_margin()`, `get_holdings()`, `get_positions()`, and `get_orders()`
    - [x] Enforce ADR-002 fail-closed order guard (explicit `RuntimeError` on order creation/modification)
  - **ST-045.3: REST Endpoints & Chat Copilot Tooling**
    - [x] Add `/api/v1/groww/status`, `/api/v1/groww/balance`, `/api/v1/groww/holdings`, `/api/v1/groww/sync` to `app/dashboard_api.py`
    - [x] Register `get_groww_account_summary` in `app/chat_agent.py` for conversational queries
  - **ST-045.4: Frontend UI Integrations**
    - [x] Add API types and fetchers in `frontend/src/types/api.ts` and `frontend/src/lib/api.ts`
    - [x] Retired the old wizard-only Groww connection indicator, budget auto-fill, and Demat import UI after moving synchronization into the Command Center data flow.
  - **ST-045.5: Verification & Container Build**
    - [x] Comprehensive tests in `tests/test_groww_client.py` and `tests/test_groww_api_routes.py` with 100% test pass rate
    - [x] Build frontend bundle (`npm run build`) and Docker containers (`docker compose build` / `up -d`)

---

## 9. Deferred Tasks (`deferred`)

- **T-002 Source and Data Inventory:** Deferred pending approved official source access terms.
- **T-003 Corporate Research Inputs:** Deferred pending approved NSE/BSE filing endpoints.
- **T-005 Full Multi-Agent Citation Graph:** Superseded by T-029 sequential multi-agent research subgraph.
- **T-006 Read-Only Groww Context:** Promoted and implemented in T-045 (ADR-035).
- **T-008 Future Execution Review:** Deferred (live order routing prohibited by ADR-002).
- **T-010 Agentic Trader Modernization:** Modularized and superseded by Phase 6 tasks.
- **T-016 Investor Preferences And Universe Selection:** Deferred (NIFTY 100 universe retained per ADR-015).
- **T-019 Universe And Security Master Sourcing:** Deferred (NIFTY 100 universe retained per ADR-017).
- **T-022 Measured Graph Fan-Out:** Superseded by sequential early-exit multi-agent research.
