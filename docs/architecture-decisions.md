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

- Status: accepted
- Context: The project should remain free or low-cost and easy to operate.
- Decision: SQLite and local cached artifacts remain the default until measured
  requirements justify another store.
- Consequence: Scaling limitations are accepted at single-operator scale and
  must be demonstrated before adding infrastructure.

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

- Status: proposed
- Context: T-002, T-004, and T-005 contain safety-relevant thresholds for
  freshness, source disagreement, regime vetoes, event blackouts, exposure, and
  citation completeness, but currently provide no numeric values.
- Decision: Thresholds must be documented and reviewed before implementation;
  agents may not invent them during coding or runtime.
- Consequence: T-002 and T-004 remain implementation-blocked until the
  threshold table is accepted.

## ADR-012: Modernization Preserves Paper-Only Execution

- Status: accepted
- Context: The modernization request includes dynamic fan-out, richer research
  agents, and Groww/Zerodha GTT execution. The current product scope explicitly
  forbids live buy/sell automation.
- Decision: Implement safe orchestration, data, research, and paper-execution
  improvements without enabling live orders. SQLite remains the only supported
  persistence system. Any broker GTT or live order path requires T-008,
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
  1. Adopt LangGraph's native `SqliteStore` (`langgraph.store.sqlite`, already
     bundled with the installed `langgraph-checkpoint-sqlite` package — no new
     dependency) as the long-term-memory backend for the operator profile and
     any future cross-thread notes, replacing the ad hoc SQLite table. The
     store is compiled into the graph via `compile(store=...)`.
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
