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
| **T-027** | `backlog` | High | ADR-003 | Type safety, typed models in `app/models.py`, and Pydantic `SecretStr` credentials |
| **T-028** | `backlog` | High | ADR-024 | Multi-strategy simultaneous screening (Breakout, Pullback, Mean Reversion) |
| **T-029** | `backlog` | High | ADR-022 | Sequential multi-agent research subgraph (Bear Critic $\rightarrow$ Bull $\rightarrow$ Synth) with early exit |
| **T-030** | `backlog` | Medium | ADR-019 | Concurrency hardening, bounded thread pools in Telegram bot, and tenacity retries |
| **T-031** | `backlog` | Medium | ADR-012 | Event-driven walk-forward backtesting framework reusing production pipeline |
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

*(Currently 0 active tasks. Next candidates from `todo`: T-004, T-007.)*

---

## 4. Tasks Ready for Implementation (`todo`)

*(Currently 0 tasks in todo. Ready to promote from backlog: T-027, T-028, T-029.)*

---

## 5. Backlog Tasks (`backlog`)

### T-027 Type Safety, Typed Models & SecretStr Hardening
- Status: `backlog`
- Priority: `High`
- Related ADRs: [ADR-001](architecture-decisions.md#adr-001-documentation-is-canonical), [ADR-003](architecture-decisions.md#adr-003-deterministic-numeric-risk)
- Goal: Eliminate untyped dictionaries between pipeline stages and secure secrets with Pydantic `SecretStr`.

#### Sub-Task 27.1: Typed Domain Transfer Models (`app/models.py`)
- Goal: Standardize Pydantic data schemas across screener, pipeline, and execution.
##### Milestone 27.1.1: Core Data Models
- [ ] Define `TechnicalSnapshot` model (ticker, close, EMA 200, RSI 14, ATR 14, volume, avg volume)
- [ ] Define `ExecutionResult` model (trade_id, fill_price, slippage, fill_timestamp, status)
- [ ] Define `TradeRecord` model (full typed audit row representation)
- [ ] Define `ScanResult` model (aggregate scan metrics, candidate count, proposal count)
##### Milestone 27.1.2: Model Consumption Refactor
- [ ] Update `screener.get_symbol_snapshot()` to return `TechnicalSnapshot`
- [ ] Update `executor.record_open_trade()` to return `ExecutionResult`
- [ ] Replace non-deterministic `str({...})` cache key in `screener.py` with `evidence.content_hash()`

#### Sub-Task 27.2: SecretStr Credential Isolation
- Goal: Prevent secret leakage in logs, stack traces, and serialization dumps.
##### Milestone 27.2.1: Pydantic Settings Migration
- [ ] Convert `OPENAI_API_KEY`, `TELEGRAM_BOT_TOKEN`, `LANGSMITH_API_KEY`, `ANTHROPIC_API_KEY`, `GROQ_API_KEY`, `GOOGLE_API_KEY` to `SecretStr`
- [ ] Update call sites to safely access `.get_secret_value()` only at client construction boundaries

#### Acceptance Criteria
1. Zero raw dictionaries flow across major module boundaries (`screener` $\rightarrow$ `pipeline` $\rightarrow$ `graph`).
2. Printing or dumping `get_settings()` masks all API keys and tokens (`**********`).
3. Full test suite passes without regression.

---

### T-028 Multi-Strategy Simultaneous Screening & Priority Engine
- Status: `backlog`
- Priority: `High`
- Related ADRs: [ADR-024](architecture-decisions.md#adr-024-multi-strategy-simultaneous-screening-with-deterministic-priority)
- Goal: Implement simultaneous evaluation of Breakout, Pullback, and Mean Reversion setups with deterministic priority.

#### Sub-Task 28.1: Strategy Implementations (`app/strategies.py`)
- Goal: Build pluggable setup strategies implementing the `SetupStrategy` Protocol.
##### Milestone 28.1.1: Concrete Strategy Classes
- [ ] `PullbackInUptrendStrategy`: Price > EMA 200, RSI 14 < 42, Volume > 0.5 * 20-day avg
- [ ] `BreakoutMomentumStrategy`: Price > 20-day High, Price > EMA 50, Volume > 1.5 * 20-day avg
- [ ] `BollingerMeanReversionStrategy`: Price <= Lower Band (20, 2.0), RSI 14 < 30, Price > EMA 200
##### Milestone 28.1.2: Screener Indicator Extensions
- [ ] Extend `screener._compute_indicators` to calculate Bollinger Bands and Donchian channels in pandas

#### Sub-Task 28.2: Priority Resolution & Strategy-Specific Risk
- Goal: Prevent duplicate proposals for the same symbol and apply strategy-appropriate stops.
##### Milestone 28.2.1: Priority Resolver
- [ ] Implement deterministic priority hierarchy: `BREAKOUT` > `PULLBACK` > `MEAN_REVERSION`
- [ ] Tag secondary qualifying setups in proposal audit logs
##### Milestone 28.2.2: Strategy Risk Profiles (`app/risk.py`)
- [ ] Configure Breakout risk profile: 1.0 ATR soft / 2.0 ATR hard / 3.0 R:R
- [ ] Configure Pullback risk profile: 1.5 ATR soft / 2.5 ATR hard / 2.0 R:R
- [ ] Configure Mean Reversion risk profile: 1.2 ATR soft / 2.0 ATR hard / Target at Middle Bollinger Band

#### Acceptance Criteria
1. Screener evaluates universe against all three strategies simultaneously.
2. If a ticker triggers multiple setups, exactly one proposal is generated based on priority.
3. Risk engine applies strategy-specific ATR stop multipliers and target ratios.

---

### T-029 Sequential Multi-Agent Research Subgraph with Early Exit
- Status: `backlog`
- Priority: `High`
- Related ADRs: [ADR-022](architecture-decisions.md#adr-022-multi-agent-qualitative-research-architecture-sequential-bear-first-with-early-exit)
- Goal: Replace single catalyst analyst prompt with a sequential multi-agent debate subgraph (Bear Critic $\rightarrow$ Bull Analyst $\rightarrow$ Synthesis Arbiter).

#### Sub-Task 29.1: Agent Models & Personas (`app/agents/`)
- Goal: Create specialized qualitative analysis agents with structured Pydantic outputs.
##### Milestone 29.1.1: Structured Output Schemas (`app/agents/models.py`)
- [ ] `BearAssessment`: red_flags, structural_risks, governance_score, confidence (0.0–1.0)
- [ ] `BullAssessment`: momentum_thesis, volume_quality, sector_tailwinds, confidence (0.0–1.0)
- [ ] `ResearchVerdict`: composite_confidence (0–100), verdict (BUY/PASS/WAIT), invalidation_criteria, citations
##### Milestone 29.1.2: Agent Implementations
- [ ] `BearRiskCritic`: Stress-tests setup for promoter pledging, litigation, debt, and overhead supply
- [ ] `BullMomentumAnalyst`: Evaluates breakout strength, accumulation, and catalyst drivers
- [ ] `SynthesisArbiter`: Balances arguments and produces final research thesis

#### Sub-Task 29.2: Subgraph Construction & Early Exit Routing
- Goal: Wire sequential execution with early exit into LangGraph.
##### Milestone 29.2.1: Early Exit Logic
- [ ] If Bear Critic scores `STRUCTURAL_DAMAGE` with `confidence >= 0.70`, terminate immediately without invoking Bull Analyst
- [ ] If Bear Critic does not veto, invoke Bull Analyst, then Synthesis Arbiter
- [ ] Require Synthesis Arbiter confidence $\ge 0.60$ to proceed to risk engine
##### Milestone 29.2.2: LangGraph Integration
- [ ] Wire multi-agent subgraph into `app.graph` replacing `_analyze_catalyst`
- [ ] Persist full debate reasoning and citations to PostgreSQL evidence snapshot

#### Acceptance Criteria
1. Bear Critic vetoes structural damage candidates early, saving ~60% LLM cost.
2. Only setups passing Bear Critic and scoring $\ge 0.60$ in Synthesis reach the risk engine.
3. Hard invariant maintained: agents only classify; prices and quantities remain 100% deterministic.

---

### T-030 Concurrency Hardening, Thread Pools & Tenacity Retries
- Status: `backlog`
- Priority: `Medium`
- Related ADRs: [ADR-019](architecture-decisions.md#adr-019-langgraph-platform-modernization-stays-local-first)
- Goal: Eliminate unbounded daemon thread spawning in Telegram bot and add resilient exponential backoff.

#### Sub-Task 30.1: Bounded Worker Pool in Telegram Bot
- Goal: Prevent OS thread exhaustion under high message or command volume.
##### Milestone 30.1.1: ThreadPoolExecutor Integration
- [ ] Replace `threading.Thread(...).start()` in `telegram_bot.py` with a module-level `ThreadPoolExecutor(max_workers=3)`
- [ ] Add command rate-limiting decorator
- [ ] Add graceful thread pool shutdown on bot termination

#### Sub-Task 30.2: Centralized Network Retries (`app/retry.py`)
- Goal: Handle transient network hiccups gracefully without crashing scheduled scans.
##### Milestone 30.2.1: Tenacity Decorators
- [ ] Implement `network_retry` with exponential backoff (1s to 10s, max 3 attempts)
- [ ] Apply retry decorators to `news.fetch_headlines`, `universe._fetch_live`, and corporate event ingestion

#### Acceptance Criteria
1. Telegram bot processes concurrent commands through a bounded pool without spawning unbounded threads.
2. Transient network errors on RSS feeds or universe downloads retry automatically with backoff.

---

### T-031 Walk-Forward Backtesting Framework
- Status: `backlog`
- Priority: `Medium`
- Related ADRs: [ADR-012](architecture-decisions.md#adr-012-modernization-preserves-paper-only-execution)
- Goal: Provide an event-driven backtesting engine reusing exact production screener, risk, and cost logic.

#### Sub-Task 31.1: Backtest Engine Core (`app/backtester.py`)
- Goal: Simulate historical performance bar-by-bar with zero lookahead bias.
##### Milestone 31.1.1: Event Simulation Loop
- [ ] Iterate through historical OHLCV candles bar-by-bar
- [ ] Execute `SetupStrategy.qualifies()` and `calculate_risk()` at each simulated bar
- [ ] Simulate fills with realistic slippage and turnover transaction costs
- [ ] Auto-close positions on stop-loss or profit-target breach
##### Milestone 31.1.2: Performance Reporting & CLI
- [ ] Calculate equity curve, Sharpe ratio, Max Drawdown, and monthly returns matrix
- [ ] Expose CLI: `python -m app.main backtest SYMBOL --start YYYY-MM-DD --end YYYY-MM-DD`

#### Acceptance Criteria
1. Backtest engine uses the exact production risk and strategy code without duplication.
2. Produces accurate equity curve, Sharpe ratio, and drawdown reports without lookahead bias.

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
