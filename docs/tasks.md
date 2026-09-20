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
- **Phase 3: Multi-Agent Qualitative Research (Active Blueprint):** T-029 (sequential multi-agent research subgraph with early exit, ADR-022).
- **Phase 4: Evaluation & Performance Operations (Active):** T-007 (NIFTY 100 Buy-and-Hold benchmark comparator, 30-trade minimum sample size).
- **Phase 5: LangGraph Platform Modernization (Completed Foundation):** T-023 (store, durability, time travel), T-024 (agent middleware), T-025 (LangSmith tracing).
- **Phase 6: Multi-Strategy, Multi-Agent & PostgreSQL Evolution (Active):** T-026 (PostgreSQL sidecar & migration), T-027 (type safety & SecretStr), T-028 (multi-strategy screening), T-030 (concurrency hardening), T-031 (walk-forward backtester).

---

## 2. Closure Matrix

| Task ID | Status | Priority | Related ADR | Scope & Readiness Summary |
|---|---|---|---|---|
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

*(Currently 0 active implementation tasks. All Phase 6 development tasks completed.)*

---

## 4. Tasks Ready for Implementation (`todo`)

*(Currently 0 tasks in todo.)*

---

## 5. Backlog Tasks (`backlog`)

*(All current Phase 6 tasks are completed.)*

---

## 6. Tasks Awaiting Discussion / Architectural Consensus (`discuss`)

### T-032 Intraday Trailing Stops & Polling Interval
- Status: `discuss`
- Priority: `Low`
- Goal: Determine whether a 15-minute polling position monitor during market hours is beneficial for swing trading.
- Open Discussion Questions:
  1. Does a 15-minute EOD trailing stop check provide tangible risk reduction for swing trades held across multiple days?
  2. Does polling Yahoo Finance intraday introduce rate-limiting or stale price risks?
  3. Decision gate: Requires an ADR before any intraday polling scheduler is introduced.

---

## 7. Tasks Under Review (`inreview`)

### T-023 LangGraph Platform Modernization
- Status: `inreview`
- Priority: `High`
- Related ADRs: [ADR-019](architecture-decisions.md#adr-019-langgraph-platform-modernization-stays-local-first)
- Completed Milestones:
  - [x] Shared long-term memory store (`compile(store=...)`) backing `app.profile`
  - [x] Set `durability="sync"` explicitly on `run_symbol` and `resume_symbol`
  - [x] Time-travel history exposed via `graph.symbol_history`, `history` CLI, and chat-agent tool
  - [x] Unit and regression tests passing

### T-024 LangChain Agent Middleware Modernization
- Status: `inreview`
- Priority: `High`
- Related ADRs: [ADR-020](architecture-decisions.md#adr-020-chat-agent-adopts-create_agent-and-built-in-safety-middleware)
- Completed Milestones:
  - [x] Migrated from deprecated `create_react_agent` to `langchain.agents.create_agent`
  - [x] `PIIMiddleware` for email and credit card masking
  - [x] `ToolCallLimitMiddleware` (max 8 calls per run)
  - [x] `SummarizationMiddleware` for bounded conversation memory
  - [x] Unit and regression tests passing

---

## 8. Completed Tasks (`done`)

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

### T-025 Optional LangSmith Tracing
- Status: `done`
- Completed: Opt-in LangSmith tracing implemented via `app.observability` (ADR-021), fails closed without API key, tags non-secret metadata.

---

## 9. Deferred Tasks (`deferred`)

- **T-002 Source and Data Inventory:** Deferred pending approved official source access terms.
- **T-003 Corporate Research Inputs:** Deferred pending approved NSE/BSE filing endpoints.
- **T-005 Full Multi-Agent Citation Graph:** Superseded by T-029 sequential multi-agent research subgraph.
- **T-006 Read-Only Groww Context:** Deferred pending verified read-only API credentials.
- **T-008 Future Execution Review:** Deferred (live order routing prohibited by ADR-002).
- **T-010 Agentic Trader Modernization:** Modularized and superseded by Phase 6 tasks.
- **T-016 Investor Preferences And Universe Selection:** Deferred (NIFTY 100 universe retained per ADR-015).
- **T-019 Universe And Security Master Sourcing:** Deferred (NIFTY 100 universe retained per ADR-017).
- **T-022 Measured Graph Fan-Out:** Superseded by sequential early-exit multi-agent research.
