# Architecture Decisions

This file records decisions that constrain implementation. New architectural
choices require a new ADR or an explicit superseding decision.

## ADR-001: Documentation Is Canonical

- Status: accepted
- Context: Architecture and operational rules were duplicated at repository
  root and were difficult for agents to discover consistently.
- Decision: Canonical product and engineering documentation lives under
  `docs/`. Root documents may link to or summarize canonical docs but must not
  diverge from them.
- Consequence: Documentation changes are part of feature work and review.

## ADR-002: Paper-Only Execution

- Status: accepted
- Context: The system is for research and controlled learning, not unattended
  brokerage activity.
- Decision: Live buy/sell remains blocked. Groww integration, if added, is
  read-only and isolated from the execution interface.
- Consequence: No order-capable tool is available to research agents.

## ADR-003: Deterministic Numeric Risk

- Status: accepted
- Context: LLM output is probabilistic and must not control financial numbers.
- Decision: Prices, stops, targets, quantities, exposure, and risk gates are
  computed by deterministic code from validated inputs.
- Consequence: LLM schemas cannot contain order or risk fields.

## ADR-004: Fail Closed on Critical Evidence

- Status: accepted
- Context: Stale or incomplete evidence can create a false research signal.
- Decision: Missing critical data, source conflicts, stale prices, and failed
  validation prevent proposal generation. Research-only reports may still be
  produced with explicit uncertainty.
- Consequence: Availability is less important than auditability and safety.

## ADR-005: Source Provenance Is First-Class

- Status: accepted
- Context: Deep research needs reproducible evidence rather than opaque model
  summaries.
- Decision: Store source, URL or identifier, fetch time, publication time,
  content hash, freshness, parser status, and citation references.
- Consequence: New adapters must implement provenance before being used by an
  agent or scheduled scan.

## ADR-006: Local-First Storage

- Status: superseded by ADR-023
- Context: The project initially used local SQLite storage.
- Decision: Replaced by unified PostgreSQL 16 sidecar persistence under ADR-023.
- Consequence: Eliminates file locking and concurrency bottlenecks.

## ADR-007: Agent Tools Are Read/Trigger-Only

- Status: accepted
- Context: Natural-language interfaces must not bypass explicit human gates.
- Decision: Agents may collect, analyze, report, and trigger research runs, but
  cannot approve, reject, execute, or mutate risk settings.
- Consequence: Telegram approval controls remain separate from chat tools.

## ADR-008: Deepen Existing Seams Before Splitting Transport

- Status: accepted
- Context: The architecture review found real locality problems in market data,
  checkpoint construction, proposal payloads, and universe resolution. It also
  found that splitting Telegram without a second notification adapter would
  only move complexity.
- Decision: Implement the four concrete deepening seams first. Keep Telegram as
  one module until a second notification adapter creates a real seam through the
  existing outbox.
- Consequence: The code gains testable locality without speculative transport
  modules. Telegram restructuring requires a future task and ADR update when
  the second adapter becomes real.

## ADR-009: One Evidence Snapshot For Research And Evaluation

- Status: accepted
- Context: T-005 requires reproducible research snapshots and T-007 requires
  frozen proposal evidence. Treating these as separate stores would create two
  competing histories.
- Decision: Use one immutable evidence snapshot per research run. Reports,
  proposals, evaluations, and citations reference that snapshot by id.
- Consequence: Agent reports and evaluation records must reference the snapshot
  rather than copying evidence into separate stores.

## ADR-010: Official-Source Authority And Public-Web Collection

- Status: proposed
- Context: NSE/BSE and NSE Indices are the strongest authorities, but their
  public web/session access is not a stable API contract and may have terms or
  licensing constraints for automation.
- Decision: Official sources remain authoritative when valid evidence is
  available. Automated collection must be rate-limited, cached, disableable,
  and reviewed against current terms. No scheduled feature may silently depend
  on an unstable or unauthorized source.
- Consequence: T-003 must complete a source-access decision before production
  ingestion. Secondary aggregators may support discovery but cannot silently
  override official evidence.

## ADR-011: Thresholds Require Explicit Safety Decisions

- Status: accepted
- Context: T-002, T-004, and T-005 contain safety-relevant thresholds for
  freshness, source disagreement, regime vetoes, event blackouts, exposure, and
  citation completeness, but previously lacked accepted numeric values.
- Decision:
  1. Market Regime Gates (sourced automatically via Yahoo Finance `^NSEI` and `^INDIAVIX`):
     - India VIX > 24.0: Market anxiety/crisis; completely block new swing trade entries (`allow_new_entries = False`, `risk_multiplier = 0.0`).
     - India VIX in [19.0, 24.0]: Elevated volatility; permit new entries but halve risk budget (`allow_new_entries = True`, `risk_multiplier = 0.5`).
     - NIFTY 50 close < 50-day EMA: Intermediate downtrend; block all long pullback entries (`allow_new_entries = False`).
  2. Multi-Agent Qualitative Thresholds:
     - Bear Risk Critic structural damage confidence >= 0.70 triggers immediate early veto, halting further LLM analysis.
     - Research Synthesis Arbiter composite confidence score >= 0.60 required to pass to deterministic risk engine.
  3. Evaluation Sample Size:
     - Minimum 30 closed trades required before statistical validity is claimed for Sharpe, Profit Factor, or win-rate metrics.
  4. Stale Proposal Horizon:
     - 240 minutes proposal age and > 2.0% price drift invalidate paused proposals upon resume.
- Consequence: T-004 and T-007 are unblocked with calibrated, operator-accepted thresholds. All thresholds remain configurable in `config/settings.py` with these agreed baseline defaults.

## ADR-012: Modernization Preserves Paper-Only Execution

- Status: accepted
- Context: The modernization request includes dynamic fan-out, richer research
  agents, and Groww/Zerodha GTT execution. The current product scope explicitly
  forbids live buy/sell automation.
- Decision: Implement safe orchestration, data, research, and paper-execution
  improvements without enabling live orders. Persistence is unified under
  PostgreSQL 16 (ADR-023). Any broker GTT or live order path requires T-008,
  independent reconciliation review, and a new accepted ADR.
- Consequence: No research agent receives order-capable tools, and no external
  database deployment is part of the product scope.

## ADR-014: Native Multi-Provider LLM Routing via Active Provider

- Status: accepted
- Context: The analyst and chat agent currently use one OpenAI-compatible
  endpoint from `OPENAI_API_KEY`/`OPENAI_BASE_URL`/`OPENAI_MODEL`. The operator
  wants direct OpenAI, Gemini, Anthropic, and Groq support, not an emulated
  OpenAI URL for every provider.
- Decision: Introduce an `LLM_PROVIDER` active switch and explicit native
  LangChain adapters: `ChatOpenAI`, `ChatGoogleGenerativeAI`, `ChatAnthropic`,
  and `ChatGroq`. Keep one explicit `openai_compatible` adapter for Siemens and
  other compatible gateways. Select only at process startup from environment
  configuration; agents cannot switch provider. Unknown, missing, or unsupported
  configuration fails closed: analyst returns conservative rejection and chat
  agent is disabled.
- Consequence: Provider-specific packages and credentials are required only for
  supported providers. Each adapter must pass structured-output and tool-calling
  tests before being accepted. All secrets stay in `.env`/secret storage; never
  logged or persisted. Deterministic risk invariant is unchanged (LLM never
  yields numeric risk values).

## ADR-015: Agentic Platform First, User-Supplied Preferences Second

- Status: accepted
- Context: The operator wants TrAId to remain an agentic research platform, not
  a basket of specialty stock filters. Preference lists should be user-provided
  and explicit, and specialty screens such as Shariah should not be introduced
  before the core workflow is proven.
- Decision: TrAId prioritizes the agentic research, approval, memory, and
  evidence loop. User-supplied include/exclude lists are supported as
  deterministic policy inputs when implemented. Specialty filters and universe
  expansion remain low priority and must be separately reviewed before coding.
- Consequence: The platform stays focused on research, evidence, and human
  control. Preference logic is explicit configuration, not inferred behavior.

## ADR-016: Provider Selection Is Startup-Only

- Status: accepted
- Context: Provider changes affect structured output, tool calling, latency,
  cost, and attribution. Runtime model switching by an agent would make a
  research run difficult to reproduce.
- Decision: `LLM_PROVIDER` and provider-specific model settings are read when
  the process builds its LLM client. Agents cannot change provider, model,
  credentials, or retry policy. The selected provider and model are recorded as
  non-secret metadata in graph/audit context.
- Consequence: Changing providers requires configuration and a process restart;
  each run remains attributable to one configured model.

## ADR-017: NIFTY 100 Is The Next-Release Universe

- Status: accepted
- Context: Broader NSE/BSE universe support requires source authority, symbol
  identity, licensing, liquidity, and freshness decisions that are not yet
  resolved.
- Decision: The next release remains NIFTY 100 only, using the existing NSE
  Indices universe resolver and fallback chain. Broader NSE/BSE coverage is
  deferred until the Phase 2 source-policy discussion is complete.
- Consequence: No new exchange, full-security-master, or custom-universe
  ingestion is added to the next release.

## ADR-013: Paper Transaction Costs Are Net-P&L Data

- Status: accepted
- Context: Gross paper fills overstate delivery results and make evaluation
  misleading.
- Decision: Paper closes calculate and persist gross P&L, delivery transaction
  costs, and net realized P&L. The cost model remains deterministic and
  configurable only through reviewed code/configuration.
- Consequence: Evaluation must use net P&L by default while retaining gross P&L
  for attribution.

## ADR-018: External-Policy Tasks Close as Deferred

- Status: accepted
- Context: T-002, T-003, T-004, T-005, T-006, T-007, T-008, T-016, T-019, and
  T-022 contain work that requires operator-approved thresholds, exchange or
  broker access, or a deliberate product-scope decision not available in the
  current local-first release.
- Decision: Close those tasks as `deferred`, retain their implemented safe
  foundations, and do not claim source ingestion, live market-context wiring,
  full agentic orchestration, cloud migration, or live execution. A future
  implementation must first supersede this decision with the required source,
  threshold, or execution ADR.
- Consequence: The ledger has no misleading open tasks, while deferred work
  remains traceable and fail-closed behavior is preserved.

## ADR-019: LangGraph Platform Modernization Stays Local-First

- Status: accepted
- Context: LangGraph's persistence, store, fault-tolerance, streaming,
  interrupt, time-travel, subgraph, testing, and observability APIs have
  matured since this graph was first built. A review of
  `docs.langchain.com/oss/python/langgraph/*` found genuine, low-risk
  improvements the current single-operator, paper-only product can adopt
  without new infrastructure, alongside platform features (Agent Server
  deploy, Studio, LangSmith-hosted tracing) that require external services
  and are explicitly out of scope until a separate ADR authorizes them.
- Decision:
  1. Adopt LangGraph's native store abstraction (modernized to `PostgresStore` under ADR-023)
     as the long-term-memory backend for the operator profile and cross-thread notes.
     The store is compiled into the graph via `compile(store=...)`.
  2. Set `durability="sync"` explicitly on `graph.invoke()` for `run_symbol`
     and `resume_symbol` so every super-step (screener, catalyst, risk,
     interrupt, execute) is durably checkpointed before the next step starts.
     A paper-trading approval pipeline must not lose a proposal or replay risk
     math from a stale checkpoint after a crash.
  3. Add a read-only time-travel capability (`graph.symbol_history`, the
     `history` CLI command, and the `get_symbol_history` chat-agent tool)
     using `get_state_history()` so the operator and support/debugging work
     can see exactly which node produced a rejection or approval without
     re-running the pipeline or guessing from logs.
  4. Evaluate (do not yet require) event-streaming progress updates to
     Telegram during long `/scan` runs, node-level `RetryPolicy` where a node
     is allowed to raise (most current nodes already fail closed internally
     and therefore do not benefit from graph-level retries), and subgraph-based
     specialist analyst roles for T-005, as separate follow-up tasks.
  5. Explicitly defer LangGraph Agent Server deployment, Studio, and
     LangSmith-hosted tracing: they require new external services or
     credentials and are not authorized by ADR-006/ADR-012's local-first,
     no-new-infrastructure constraint. Optional local-only LangSmith tracing
     may be evaluated later behind an explicit opt-in environment variable
     that never logs secrets or full prompts.
- Consequence: Long-term memory, durability, and auditability improve using
  capabilities already present in the installed LangGraph packages. No new
  infrastructure, deployment target, or paid service is introduced. Deferred
  items require their own task/ADR before implementation.

## ADR-020: Chat Agent Adopts `create_agent` And Built-In Safety Middleware

- Status: accepted
- Context: `langgraph.prebuilt.create_react_agent`, used by `app.chat_agent`,
  is deprecated in LangGraph v1 in favor of `langchain.agents.create_agent`,
  which adds a middleware system. The `langchain` package (already required
  transitively by `langchain-openai`/`langchain-google-genai`/
  `langchain-anthropic`/`langchain-groq`) is installed at v1.4.1 and already
  provides `create_agent` plus built-in middleware (PII redaction, tool-call
  limits, summarization, model fallback, human-in-the-loop, context editing,
  todo lists) with no new dependency. A review of
  `docs.langchain.com/oss/python/integrations/{middleware,tools,chat,
  checkpointers,long-term-memory,splitters,document_loaders}` found this
  migration and three of its middleware genuinely applicable now.
- Decision:
  1. Migrate `app.chat_agent._build_agent()` from `create_react_agent` to
     `create_agent`, keeping the same tools, `system_prompt`, and
     checkpointer, and additionally wiring the T-023 long-term `store`.
  2. Add `PIIMiddleware` (redact emails, mask credit-card numbers on input)
     so operator chat text is sanitized before reaching the LLM or logs.
  3. Add `ToolCallLimitMiddleware` (`run_limit=8`, `exit_behavior="end"`) so
     a confused model cannot loop tool calls indefinitely within one turn.
  4. Add `SummarizationMiddleware` (trigger at ~4000 tokens, keep the most
     recent 20 messages) to bound per-chat conversation memory, closing the
     T-015 "bounded memory/summary policy" checklist item without inventing
     a custom summarizer.
  5. Explicitly do not adopt: `ModelFallbackMiddleware` (would let the agent
     switch providers/models at runtime, conflicting with ADR-016's
     startup-only provider selection), `HumanInTheLoopMiddleware` (no chat
     tool mutates risk/approval/execution state, so there is nothing to
     gate — approval stays exclusively in Telegram's inline buttons per
     ADR-007), and `ContextEditingMiddleware` (overlaps with
     `SummarizationMiddleware`; do not stack two context strategies without
     a measured need).
  6. Do not add new tool integrations, document loaders, or text splitters
     from the reviewed integration pages. Web-search/filing-retrieval tools
     and long-document chunking are real future capabilities but require
     either a new external source (blocked by the Phase 2 source-policy gate
     and ADR-010) or a new dependency; neither is authorized by this ADR.
- Consequence: The chat agent's read/trigger-only boundary (ADR-007) and
  provider startup-only selection (ADR-016) are unchanged and unweakened.
  Bounded memory and basic PII hygiene are implemented using packages already
  present in the environment. `requirements.txt` now pins `langchain>=1.0.0`
  (previously an unenforced `>=0.2.0` floor that predates `create_agent`).

## ADR-021: Optional, Explicit-Opt-In LangSmith Tracing

- Status: accepted
- Context: ADR-019 and ADR-020 deferred LangSmith tracing until it could be
  opt-in and never log secrets or full prompts. The `langsmith` SDK is
  already installed as a transitive dependency of `langchain-core` — no new
  package is required. The operator asked how to connect this project to
  LangSmith.
- Decision:
  1. Add `LANGSMITH_TRACING_ENABLED` (default `false`), `LANGSMITH_API_KEY`,
     `LANGSMITH_PROJECT` (default `traid-nifty100`), and `LANGSMITH_ENDPOINT`
     (optional, for self-hosted LangSmith) to `config/settings.py`.
  2. `app.observability.configure()` calls `_apply_langsmith_env()`, which
     sets the standard `LANGSMITH_TRACING`/`LANGSMITH_API_KEY`/
     `LANGSMITH_PROJECT`/`LANGSMITH_ENDPOINT` process environment variables
     the LangSmith SDK reads directly — but only when
     `LANGSMITH_TRACING_ENABLED=true` **and** `LANGSMITH_API_KEY` is set.
     Enabling the flag without a key logs a warning and stays disabled
     (fail closed); the API key value itself is never logged.
  3. No code changes are required in `app.graph` or `app.chat_agent` — once
     the environment variables are set, LangChain/LangGraph runs are traced
     automatically by the SDK's global callback. To make those traces
     filterable, `app.graph._trace_metadata` attaches non-secret tags
     (`symbol`, `strategy`, `trader`, `decision`) to every `run_symbol` and
     `resume_symbol` invocation via the graph `metadata=` argument.
  4. This is off by default in `.env.example`. Turning it on is an explicit
     operator decision, since it sends run/trace metadata to LangSmith's
     servers (or a self-hosted `LANGSMITH_ENDPOINT`).
- Consequence: Tracing remains fully optional and local-first by default.
  When enabled, the operator is knowingly sending trace data to LangSmith;
  no secret value is ever written to application logs.

## ADR-022: Multi-Agent Qualitative Research Architecture (Sequential Bear-First with Early Exit)

- Status: accepted
- Context: The single-analyst LLM prompt in `analyst.py` is vulnerable to
  confirmation bias and lacks adversarial stress-testing. Evaluating screened
  candidates with a multi-agent debate improves research quality, but parallel
  fan-out triples LLM API consumption on every screened ticker.
- Decision:
  1. Implement a hierarchical multi-agent research subgraph with sequential early
     exit:
     - **Bear Risk Critic Agent**: Runs first. Evaluates governance red flags,
       promoter pledge spikes, litigation, accounting flags, and overhead chart
       resistance. If it classifies the setup as `STRUCTURAL_DAMAGE` with
       `confidence >= 0.70`, it triggers an immediate early veto, halting further
       LLM analysis and saving ~60% downstream API cost.
     - **Bull Momentum Analyst Agent**: Invoked only if the Bear Critic does not
       veto. Evaluates volume breakout quality, sector rotation tailwinds, and
       continuation drivers.
     - **Synthesis Arbiter Agent**: Weighs both arguments, sets explicit
       invalidation criteria, and calculates a composite confidence score (0–100).
       Only candidates scoring `>= 0.60` pass to the deterministic risk engine.
  2. Hard Invariant: All agents emit strictly qualitative classifications via
     Pydantic schemas; agents never emit or mutate prices, stop losses, position
     quantities, or order instructions.
- Consequence: Eliminates confirmation bias while keeping LLM costs controlled.
  Every research verdict persists full reasoning and citation lists to the audit
  snapshot.

## ADR-023: PostgreSQL as Unified Relational, Checkpoint, and Store Persistence Layer

- Status: accepted
- Context: TrAId is evolving from a single-process script into a multi-component
  containerized architecture (scheduler, Telegram interface, pipeline worker).
  SQLite persistence creates file-locking and concurrency bottlenecks across
  multiple processes and lacks native connection pooling and transactional
  migrations.
- Decision:
  1. Adopt PostgreSQL 16 (`postgres:16-alpine`) as the unified persistence engine
     running as a Docker sidecar service in `docker-compose.yml`.
  2. This decision supersedes ADR-006 (Local-First SQLite), the SQLite-only
     constraint in ADR-012, and the SQLite checkpointer constraint in ADR-019.
  3. LangGraph checkpoints and durable interrupts are persisted using
     `langgraph-checkpoint-postgres` (`PostgresSaver`) backed by a synchronous
     `psycopg_pool.ConnectionPool`.
  4. LangGraph long-term memory (operator profile and cross-thread state) is
     persisted using `langgraph.store.postgres.PostgresStore`.
  5. Relational data (`trade_audit_log`, `notification_outbox`, `research_cache`,
     `evidence_snapshots`, `graph_threads`) are unified into the PostgreSQL
     database with B-tree indexes on `status`, `timestamp`, and `symbol`.
  6. All legacy SQLite database files, dependencies, and code branches are completely
     removed in favor of pure PostgreSQL persistence.
  7. Paper-only execution invariant (ADR-002) remains strictly preserved: live
     order execution remains blocked.
- Consequence: Docker Compose requires a PostgreSQL service. State transitions and
  checkpoints survive container restarts with high multi-client concurrency.

## ADR-024: Multi-Strategy Simultaneous Screening with Deterministic Priority

- Status: accepted
- Context: The original screener supported only a single strategy
  (`pullback_in_uptrend`). Operators require diverse setups (e.g. Momentum
  Breakout, Mean Reversion) without running separate disjoint scans.
- Decision:
  1. The screener evaluates universe candidates simultaneously against all
     active setup strategies:
     - `PullbackInUptrendStrategy`: Price > EMA 200, RSI 14 < 42, Volume > 0.5 * 20-day avg.
     - `BreakoutMomentumStrategy`: Price > 20-day High, Price > EMA 50, Volume > 1.5 * 20-day avg.
     - `BollingerMeanReversionStrategy`: Price <= Lower Band (20, 2.0), RSI 14 < 30, Price > EMA 200.
  2. Deterministic Priority Resolution: When a single symbol qualifies under
     multiple strategies on the same day, the system selects the primary strategy
     based on priority (`BREAKOUT` > `PULLBACK` > `MEAN_REVERSION`) and logs
     secondary matches as supporting tags, ensuring exactly one proposal card
     per ticker per calendar day.
  3. Deterministic Risk Engine uses strategy-specific risk parameters (e.g.
     Breakout uses 1.0 ATR soft / 2.0 ATR hard / 3.0 R:R; Pullback uses 1.5 ATR
     soft / 2.5 ATR hard / 2.0 R:R).
- Consequence: Expands candidate generation while preventing duplicate simultaneous
  proposals or operator choice paralysis.
