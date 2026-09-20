# Tasks

This is the live implementation ledger. Status values are `backlog`, `inreview`,
`done`, and `deferred`. `deferred` means the scope is intentionally closed
outside the current release, with the reason recorded. No task is closed as
`done` unless its implementation, tests, and documentation are complete.
Agents must update status while working,
checklist items as work completes, and update the relevant docs before moving a
task to `done`. Completed tasks are removed after merge; durable decisions stay
in `architecture-decisions.md`.

## Execution Plan

Implementation proceeds in dependency order. A phase may start only after its
entry criteria are met and its tests pass.

### Phase 1: Safe Runtime Foundation (completed)

1. T-015: bounded conversation memory and operator profile.
2. T-018: evidence, market-data, RSS, catalyst, and snapshot reuse.
3. T-017: local retention and persistence seams; no cloud migration yet.

Entry criteria: current paper-only flow, SQLite checkpointing, and Telegram
lifecycle hardening are stable. Exit criteria: provider selection, Telegram
authorization, cache reuse, and persistence behavior are covered by tests and
documented.

### Phase 2: Evidence Quality Foundation and Source Policy Discussion (deferred)

1. T-002: finish freshness, retry, fallback, and disagreement policies.
2. T-003: connect only an approved corporate-event source.
3. T-004: add deterministic market-regime, liquidity, and event gates whose
   thresholds have been explicitly accepted.

Entry criteria: source authority and thresholds are resolved through the Phase 2
discussion gate. Exit criteria:
critical evidence is validated, provenance is persisted, and proposal gates
fail closed on stale or conflicting inputs.

### Phase 3: Agentic Research Workflow (deferred)

1. T-005: planner, collector, validator, specialist analysts, and report writer.
2. T-010: measured graph fan-out and research orchestration modernization.

Entry criteria: Phase 2 evidence contracts are stable. Exit criteria: agents
use approved read-only tools, cite immutable snapshots, and cannot change risk,
approval, or execution state.

### Phase 4: Evaluation And Operations (completed foundation; reporting extensions deferred)

1. T-007: paper outcome evaluation, attribution, and reporting.
2. Extend operational health, freshness, cache-hit, and decision metrics.

Entry criteria: evidence snapshots and paper outcomes are complete. Exit
criteria: results are reproducible and strategy changes require reviewed data.

### Phase 5: LangGraph Platform Modernization (in progress)

1. T-023: long-term memory store, durability tuning, and time-travel
   auditability (foundation complete).
2. T-023 follow-ups: event-streaming scan progress, subgraph-based specialist
   analysts, and node-level retry policy evaluation.

Entry criteria: none — these adopt existing installed LangGraph capabilities
without new infrastructure. Exit criteria: every adopted capability has tests,
docs, and an explicit decision recorded in ADR-019; deployment-requiring
capabilities (Agent Server, Studio, hosted tracing) stay deferred until a new
ADR authorizes external services.

### Deferred Discussion

- T-016: user preference lists and custom universe input.
- T-019: full NSE/BSE security-master scope and authority.
- T-006: Groww read-only context.
- T-008: any live execution or broker order capability.

## Definition Of Done

- Tests cover the new behavior and source failure paths.
- Relevant architecture, PRD, reference, and ADR documents are updated.
- Provenance and freshness are persisted for external evidence.
- No LLM-generated numeric risk values enter deterministic state.
- The chat agent remains read/trigger-only.
- No live buy, sell, or order-modification path is introduced.
- Tasks are removed from this live ledger when complete; durable decisions stay
  in the ADR log.

## Closure Matrix

| Task | Readiness | Main blocker or decision |
| --- | --- | --- |
| T-002 | deferred | Source-specific thresholds and authority require operator-approved ADR-011 values |
| T-003 | deferred | Official NSE/BSE access terms and endpoint are not approved |
| T-004 | deferred | Market-context source and numeric thresholds are not approved; deterministic evaluator remains tested |
| T-005 | deferred | Full multi-agent workflow and citation policy require a reviewed scope decision |
| T-015 | done | Authorization, checkpointed chat history, and allowlisted operator profile foundation are implemented and tested |
| T-017 | done | Local integrity checks and native backups are implemented; cloud migration is explicitly out of scope |
| T-018 | done | TTL caches, stable evidence reuse, invalidation, and technical cache attribution are implemented and tested |
| T-019 | deferred | Full NSE/BSE security-master authority is unresolved by ADR-017 |
| T-006 | deferred | Groww capability, terms, quotas, and credentials are unknown |
| T-007 | deferred | Core metrics exist; baseline, sample-size policy, and report export require approval |
| T-008 | deferred | Live execution is prohibited by ADR-002 and ADR-012 |
| T-023 | inreview | Store/durability/time-travel foundation complete; streaming, subgraphs, and retry-policy follow-ups remain |
| T-024 | inreview | Migrated chat agent to `create_agent` + PII/tool-limit/summarization middleware; fallback and HITL middleware deliberately not adopted |
| T-025 | done | Optional LangSmith tracing (ADR-021); off by default, fails closed without an API key, never logs the key |

### T-010 Agentic Trader Modernization

- Status: deferred
- Scope note: safe modernization is active. Parallel `Send` fan-out, richer
  research inputs, async lifecycle hardening, SQLite-backed persistence, and
  paper friction modeling are in scope. Live Groww/Zerodha GTT/order routing is
  not authorized and remains behind T-008 plus a new accepted ADR.
- Milestone: CI and lifecycle hardening
  - [x] Reproduce current CI lint/type/test results locally
  - [x] Fix repository lint/type failures without weakening checks
  - [x] Add external-network mocks for yfinance, Telegram, and broker adapters
  - [x] Add async lifecycle tests only where async code is introduced
- Milestone: graph modernization
  - [x] Define reducer-safe state fields without changing existing proposal behavior
  - [ ] Evaluate dynamic `Send` fan-out against current universe-scan orchestration
  - [x] Keep native `interrupt()` and approval resume fail-closed
  - [x] Keep SQLite as the only supported checkpoint persistence system
- Milestone: market context
  - [x] Define India VIX and NIFTY trend data contracts
  - [x] Define corporate event and earnings blackout data contracts
  - [x] Define FII/DII flow data contract and source authority
- Milestone: analyst workflow
  - [ ] Split qualitative research into bullish, risk-critic, and synthesis roles
  - [ ] Preserve deterministic ownership of prices, risk, and order fields
  - [ ] Add structured regression fixtures for claims and citations
- Milestone: paper execution safety
  - [x] Add circuit/ASM/GSM inputs as deterministic rejection context
  - [x] Add realistic paper transaction-cost accounting
  - [x] Keep broker order methods fail-closed and unavailable to research agents
- Milestone: verification
  - [x] Run the full test suite and CI-equivalent checks
  - [x] Update architecture, PRD, reference, and ADR documents
  - [x] Keep unresolved fan-out and analyst-workflow decisions in the deferred
        scope rather than inventing unsupported behavior

## Closed With Deferred Scope

### T-002 Source and Data Inventory

 - Status: deferred
- Milestone: current data contract
  - [x] Document schemas for universe, OHLCV, news, assessment, proposal, and audit
  - [x] Record source timestamps and freshness requirements
  - [x] Define symbol, ISIN, company, and sector identity rules
  - [x] Define immutable evidence-snapshot schema shared by reports and evaluations
  - [x] Define proposal attribution fields: strategy, regime, catalyst type, and source set
- Milestone: source validation
  - [x] Define retry, timeout, cache, and fallback policy per current source
  - [ ] Define cross-source price and event conflict handling
  - [x] Accept configurable global evidence freshness enforcement
  - [ ] Accept numeric freshness thresholds per source class
  - [ ] Accept numeric disagreement tolerances and authority rules
- Milestone: persistence contract
  - [x] Add source/provenance records to the audit schema
  - [x] Store content hash and parser status for research artifacts
  - [x] Add freshness and validation status to pipeline state
- Milestone: verification
  - [x] Add fixture-based tests for valid, stale, missing, and conflicting data
  - [x] Update `docs/architecture.md` and `docs/reference.md`
  - [x] Validate required OHLCV columns, numeric values, and non-negative volume
- Milestone: decision gate
  - [x] Resolve proposed ADR-009
  - [ ] Resolve proposed ADR-011 thresholds that apply to data validation
- Review boundary
  - `EVIDENCE_MAX_AGE_SECONDS=0` keeps the global age gate disabled by default;
    enabling it is an operator/configuration decision.
  - Source-specific freshness and disagreement tolerances remain blocked on
    ADR-011 and are not invented here.

### T-003 Corporate Research Inputs

- Status: deferred
- Milestone: events
  - [x] Add normalized corporate-event contract
  - [x] Add results/earnings and board-meeting blackout policy
  - [x] Add dividends, splits, bonuses, rights, and pledge event types
  - [x] Add configurable normalized event source adapter
  - [x] Add results and earnings calendar ingestion path
  - [ ] Connect an approved NSE/BSE source endpoint
- Milestone: evidence
  - [x] Store URLs, publication times, hashes, and parser status in provenance contracts
  - [x] Deduplicate events deterministically
- Milestone: source order
  - [ ] Implement official NSE/BSE source adapter after access approval
  - [ ] Add company investor-relations fallback
  - [ ] Mark aggregator evidence as secondary
  - [x] Complete source disable switch and cache-first behavior
  - [x] Add malformed-source isolation
- Milestone: verification
  - [x] Test duplicate events and blackout boundaries
  - [x] Test one malformed source without aborting a scan
  - [ ] Test duplicate announcements and repeated headlines
  - [x] Test symbol/ISIN/company identity matching
- Milestone: decision gate
  - [ ] Resolve proposed ADR-010 for official-source access and authority
  - [ ] Record concrete endpoints and operational limits in `docs/reference.md`

### T-004 Market Context

- Status: deferred
- Milestone: regime
  - [ ] Add index trend and volatility context
  - [ ] Add breadth and sector-relative strength
  - [ ] Add liquidity and abnormal-volume filters
- Milestone: event-dependent gates
  - [ ] Add event-risk filters after T-003 corporate events are available
- Milestone: fallback
  - [ ] Evaluate an alternate free OHLCV provider
  - [ ] Add stale and disagreement detection
- Milestone: deterministic policy gates
  - [ ] Define market-regime veto rules
  - [ ] Define sector concentration and relative-strength rules
  - [ ] Define earnings/corporate-event blackout rules
  - [ ] Define liquidity and abnormal-volume rules
  - [ ] Accept numeric regime, blackout, concentration, and liquidity thresholds
- Milestone: verification
  - [ ] Test regime pass and veto cases
  - [ ] Test event-risk and stale-data rejection
  - [ ] Test source disagreement fails closed
- Milestone: decision gate
  - [ ] Resolve proposed ADR-011 for all market-context thresholds

### T-005 Agentic Research Workflow

- Status: deferred
- Milestone: agents
  - [ ] Define planner, collector, validator, analyst, and report-writer tools
  - [ ] Enforce read/trigger-only chat boundaries
  - [ ] Add source citations to every report
- Milestone: evaluation
  - [ ] Build deterministic tool-call regression tests
  - [ ] Reference the immutable T-002 evidence snapshot rather than creating a second store
- Milestone: graph workflow
  - [ ] Add planner state with explicit evidence requirements
  - [ ] Add collector tools restricted to approved source adapters
  - [ ] Add validator step before analyst invocation
  - [ ] Add report writer with source citations and uncertainty
- Milestone: safety
  - [ ] Keep approval/rejection outside chat-agent tools
  - [ ] Prevent agents from mutating risk settings
  - [ ] Reject reports with missing critical citations
  - [ ] Define citation completeness threshold before implementation
- Milestone: verification
  - [ ] Add tool allowlist tests
  - [ ] Add prompt-injection and unsupported-claim fixtures
  - [ ] Add deterministic report snapshot tests
- Milestone: decision gate
  - [x] Resolve ADR-009 snapshot ownership
  - [ ] Resolve citation completeness and tool allowlist policy

### T-015 Single-Operator Telegram Control And Conversation Memory

- Status: deferred
- Goal: make `TrAId` a private, single-operator Telegram control plane with
  durable conversation context and no accidental action by another chat.
- Milestone: authorization
  - [x] Bootstrap the first direct chat through `/start` only when
        `TELEGRAM_CHAT_ID` is empty
  - [x] Reject every command, callback, and free-text update whose effective
        chat id differs from `TELEGRAM_CHAT_ID`
  - [x] Document BotFather profile, command-menu, and private-DM configuration
- Review boundary
  - Authorization is complete and tested.
  - T-023 added the store-backed `app.profile` allowlisted-field persistence
    layer (namespaced LangGraph `SqliteStore`). T-024 added
    `SummarizationMiddleware`-based bounded chat memory. A Telegram command
    to let the operator view/edit their own profile remains deferred until
    the field list is agreed.
- Milestone: conversational memory
  - [x] Retain the existing checkpointed per-chat message history
  - [ ] Add an explicit, user-editable operator profile for investment horizon,
        capital, exclusions, risk preference, and notification preferences
        (storage layer exists in `app.profile`/`app.store`; a Telegram
        command to read/write it is not yet implemented)
  - [x] Add a bounded memory/summary policy; never treat unverified chat text
        as market evidence or risk settings (`SummarizationMiddleware`
        condenses older turns past a token budget — see T-024). A
        human-reviewable factual-memory audit path remains open.
- Milestone: pending decisions
  - [ ] Evaluate proactive reminder, expiry, and decision-summary notifications
        in addition to `/pending`
  - [ ] Require the operator to retain approve/reject control
- Discuss before implementing
  - [ ] Agree the required operator profile fields for TrAId v1 (capital,
        horizon, max risk per trade, sector exclusions, notification
        preference) before building the profile store
  - [ ] Agree whether `/run` allows any NSE symbol with a visible warning or is
        restricted to the configured universe

## Deferred

### T-016 Investor Preferences And Universe Selection

 - Status: deferred
- Goal: keep preference handling user-driven and low priority until the TrAId
  agentic platform is proven.
- Milestone: user preferences
  - [ ] Accept user-supplied include/exclude lists for symbols, sectors,
        industries, and other categories
  - [ ] Keep these rules deterministic and explicit; never infer them from free
        text without confirmation
  - [ ] Do not build Shariah or similar domain-specific screening logic until a
        reviewed source and product need are explicit
- Milestone: universe choice
  - [ ] Decide whether TrAId v1 stays NIFTY 100-only or accepts a user-provided
        custom list
  - [ ] Define how the operator supplies the list (manual paste, CSV import,
        config file, or Telegram command)
- Discuss before implementing
  - [ ] Decide the default universe: NIFTY 100, broader NSE, or a
        user-provided list
  - [ ] Decide whether BSE is in-scope for v1 or deferred

### T-017 Storage Portability And Historical Retention

- Status: deferred
- Goal: keep local SQLite now while preparing an evidence-preserving migration
  to PostgreSQL or hosted PostgreSQL (including Supabase) after product flow is
  proven.
- Milestone: local retention
  - [x] Define the local backup and integrity-check command boundary
  - [x] Implement SQLite integrity checks for audit and checkpoint databases
  - [x] Implement timestamped SQLite backups using the native backup API
  - [ ] Define retention and archive policy for audit,
        checkpoint, evidence, and outbox data
  - [ ] Separate active operational data from immutable historical archives
- Milestone: migration readiness
  - [ ] Inventory SQLite-specific SQL and isolate application persistence behind
        tested storage modules before choosing a database package
  - [ ] Define migration, rollback, and reconciliation requirements
  - [ ] Evaluate PostgreSQL with SQLAlchemy/Alembic and LangGraph's PostgreSQL
        checkpointer only when the cloud migration is authorized
- Review boundary
  - Local maintenance is complete for this slice.
  - Cloud migration, retention deletion, and archive policy remain deferred.

### T-018 Data Reuse And Research Caching

- Status: done
- Goal: store scan and research outputs so repeat runs reuse evidence instead of
  burning LLM/API calls.
- Milestone: market-data cache
  - [x] Cache derived technical snapshots with freshness metadata
  - [x] Reuse the latest validated technical snapshot within a freshness window
- Milestone: research cache
  - [x] Cache RSS headline sets keyed by symbol/feed configuration
  - [x] Cache catalyst assessments keyed by provider/model version + symbol +
        headline hash
  - [x] Cache evidence snapshots and reuse them when inputs are unchanged
- Milestone: audit reuse
   - [x] Record technical cache reuse in the trade/evidence record
  - [x] Keep deterministic invalidation on source/model/config changes
- Review boundary
  - Cache storage uses the existing audit SQLite database and configurable TTLs.
  - RSS/catalyst cache-hit attribution and raw OHLCV frames remain follow-up
    work.

### T-019 Universe And Security Master Sourcing

 - Status: deferred
- Goal: choose authoritative sources for full stock symbol lists, security
  master data, and exchange coverage.
- Questions
  - [ ] Why NIFTY 100 only vs NSE+BSE vs all listed equities?
  - [ ] Which official or licensed source should provide the full symbol list
        and metadata?
  - [ ] How often should the master list refresh and what are the freshness
        rules?
  - [ ] Which fields are required (symbol, ISIN, company, exchange, series,
        lot size, tick size, industry, etc.)?

### T-006 Read-Only Groww Context

 - Status: deferred
- Milestone: capability check
  - [ ] Confirm supported read-only Groww endpoints and authentication flow
  - [ ] Confirm terms, quotas, token expiry, and account-data scope
  - [ ] Confirm whether the available credentials expose holdings and positions
  - [ ] Confirm whether order-history reads are available without order writes
- Milestone: isolated adapter
  - [ ] Import holdings, positions, orders, and P&L only if supported
  - [ ] Prevent order methods from entering agent tool registries
  - [ ] Add reconciliation tests
- Milestone: safety
  - [ ] Store credentials only in environment/secret storage
  - [ ] Redact account identifiers from reports and logs
  - [ ] Add an ADR before expanding beyond read-only context

## Closed With Deferred Scope

### T-007 Evaluation and Reporting

 - Status: deferred
- Milestone: outcomes
  - [ ] Capture frozen proposal evidence and later paper outcomes
   - [x] Calculate expectancy, drawdown, hit rate, and attribution
- Milestone: operations
  - [ ] Add source freshness metrics
  - [ ] Add pipeline quality and failure summaries
  - [ ] Add weekly research report export
- Milestone: attribution
  - [ ] Attribute outcomes to strategy, regime, catalyst class, and source set
  - [ ] Track missing-data and human-decision reasons
  - [ ] Compare paper outcomes against a documented baseline
  - [ ] Define baseline: NIFTY 100 buy-and-hold or another approved comparator
  - [ ] Define metric formulas and minimum sample-size interpretation
- Milestone: verification
  - [ ] Add deterministic metric tests
  - [ ] Add report export snapshot tests
  - [ ] Document evaluation limitations and sample-size requirements
- Milestone: decision gate
   - [x] Reuse T-002 evidence snapshots and attribution fields
  - [ ] Approve baseline and metric definitions before reporting implementation

### T-022 Measured Graph Fan-Out

 - Status: deferred
- Goal: evaluate parallel per-symbol research without creating a second pipeline.
- Milestone: design
  - [x] Add timing instrumentation for current sequential `scan -> process_symbol` behavior
  - [ ] Define reducer-safe result aggregation and concurrency limits
   - [x] Preserve one shared per-symbol pipeline for `/run` and `/scan`
- Milestone: safety
   - [x] Prevent duplicate proposals and overlapping scans
  - [ ] Add deterministic fan-out tests before enabling it by default

### T-023 LangGraph Platform Modernization

- Status: inreview
- Goal: adopt current LangGraph persistence, store, durability, and
  time-travel capabilities that improve auditability and safety without new
  infrastructure, per ADR-019. Research source:
  `docs.langchain.com/oss/python/langgraph/*` (persistence, checkpointers,
  stores, fault-tolerance, event-streaming, streaming, interrupts,
  time-travel, add-memory, subgraphs, application-structure, test,
  backward-compatibility, studio, ui, deploy, observability).
- Milestone: long-term memory store
  - [x] Add `app.store`: a shared `SqliteStore` (`langgraph.store.sqlite`,
        already bundled with the installed `langgraph-checkpoint-sqlite`
        package) mirroring `app.checkpoint`'s connection lifecycle
  - [x] Compile the trading graph with `store=` so nodes/tools can use
        namespaced long-term memory through the native LangGraph API
  - [x] Migrate `app.profile` from an ad hoc table to the store, keeping the
        same `load()`/`save()` contract and allowlisted fields
  - [x] Add round-trip and reset tests for `app.store` and `app.profile`
- Milestone: durability
  - [x] Set `durability="sync"` explicitly on `run_symbol` and `resume_symbol`
        so every super-step of a paper-trading approval is durably persisted
        before the next node starts
  - [ ] Decide whether scheduled/background scans should use a different
        durability mode for throughput once measured
- Milestone: time travel and auditability
  - [x] Add `graph.symbol_history()` using `get_state_history()` — read-only,
        newest-first, one entry per super-step with next-node and
        paused-for-approval status
  - [x] Expose it via `python -m app.main history SYMBOL`
  - [x] Expose it via the chat agent's `get_symbol_history` read-only tool
  - [x] Add regression tests for both the graph function and the chat tool
- Milestone: follow-ups (not yet implemented)
  - [ ] Evaluate `stream_events`/`stream_mode="updates"` to push scan-progress
        messages to Telegram during long `/scan` runs
  - [ ] Evaluate subgraph-based specialist analyst roles (fundamental,
        technical, catalyst) as per-invocation subgraphs for T-005, keeping
        deterministic risk/order ownership unchanged
  - [ ] Evaluate node-level `RetryPolicy` only where a node is allowed to
        raise; most current nodes already fail closed internally, so this is
        not a default requirement
  - [ ] Evaluate optional local-only LangSmith tracing behind an explicit
        opt-in environment variable, never logging secrets or full prompts
- Milestone: explicitly deferred
  - [ ] LangGraph Agent Server deployment (requires a new ADR and external
        service; conflicts with ADR-006/ADR-012 until authorized)
  - [ ] LangGraph Studio (local visual debugging only; evaluate only as a
        developer tool, never a production dependency)
  - [ ] Hosted LangSmith tracing (requires external credentials; local-only
        alternative is the only currently considered option)
- Milestone: verification
  - [x] Run the full test suite, ruff, and mypy after each slice
  - [x] Update architecture, reference, and ADR documents to describe only
        what is actually wired

### T-024 LangChain Agent Middleware Modernization

- Status: inreview
- Goal: adopt current LangChain agent-construction and middleware
  capabilities for the read/trigger-only chat agent, per ADR-020. Research
  source: `docs.langchain.com/oss/python/integrations/{middleware,tools,chat,
  checkpointers,long-term-memory,splitters,document_loaders}`.
- Milestone: migrate off the deprecated prebuilt
  - [x] Replace `langgraph.prebuilt.create_react_agent` (deprecated in
        LangGraph v1) with `langchain.agents.create_agent` in
        `app.chat_agent`, keeping the same tool set, checkpointer, and
        read/trigger-only boundary
  - [x] Wire the shared long-term `store` (T-023) into the chat agent via
        `create_agent(..., store=...)`
  - [x] Add a regression test asserting the compiled graph carries the
        expected middleware nodes
- Milestone: safety middleware (built into the already-installed `langchain`
  package — no new dependency)
  - [x] `PIIMiddleware`: redact emails and mask credit-card numbers the
        operator pastes into chat before they reach the LLM or logs
  - [x] `ToolCallLimitMiddleware`: cap tool calls per run so a confused model
        cannot loop indefinitely (e.g. repeatedly re-triggering `run_symbol`)
  - [x] `SummarizationMiddleware`: bound conversation memory by condensing
        older turns past a token budget — closes the T-015 bounded-memory
        checklist item without a custom summarizer
- Milestone: evaluated and explicitly not adopted (documented reasons)
  - [ ] `ModelFallbackMiddleware` — would let the agent silently switch
        providers/models at runtime, conflicting with ADR-016 (provider
        selection is startup-only)
  - [ ] `HumanInTheLoopMiddleware` — the chat agent has no tool that mutates
        risk, approval, or execution state, so there is nothing for it to
        gate; adding it would be unused scaffolding
  - [ ] `ContextEditingMiddleware` — overlaps with `SummarizationMiddleware`;
        do not stack two context-management strategies without a measured
        need
  - [ ] New tool/document-loader/text-splitter integrations (e.g. web
        search, Tavily, filing-document loaders) — all require either a new
        external source (blocked by the Phase 2 source-policy gate/ADR-010)
        or a new dependency; none are adopted without that decision
- Milestone: verification
  - [x] Run the full test suite, ruff, and mypy after the migration
  - [x] Pin `langchain>=1.0.0` in `requirements.txt` (previously an
        unenforced `>=0.2.0` floor that predates `create_agent`)
  - [x] Update architecture, reference, and ADR documents

### T-025 Optional LangSmith Tracing

- Status: done
- Goal: let the operator connect this project to LangSmith for trace
  visibility, opt-in only, per ADR-021.
- Milestone: configuration
  - [x] Add `LANGSMITH_TRACING_ENABLED`, `LANGSMITH_API_KEY`,
        `LANGSMITH_PROJECT`, `LANGSMITH_ENDPOINT` to `config/settings.py`
  - [x] Document all four in `.env.example`, off by default
- Milestone: implementation
  - [x] `app.observability._apply_langsmith_env()` sets the standard
        `LANGSMITH_TRACING`/`LANGSMITH_API_KEY`/`LANGSMITH_PROJECT`/
        `LANGSMITH_ENDPOINT` process environment variables the already-
        installed `langsmith` SDK reads directly, only when explicitly
        enabled and only when an API key is present
  - [x] Fail closed: enabling tracing without an API key logs a warning and
        stays disabled rather than raising
  - [x] Never log the API key value
  - [x] Tag every `run_symbol`/`resume_symbol` trace with non-secret metadata
        (`symbol`, `strategy`, `trader`, `decision`) via `graph._trace_metadata`
        so traces are filterable in the LangSmith UI
- Milestone: verification
  - [x] Add regression tests for disabled-by-default, enabled-without-key,
        and enabled-with-key (asserting the key never appears in log output)
  - [x] Document setup steps in `docs/reference.md`
  - [x] Run the full test suite, ruff, and mypy

## Deferred

### T-008 Future Execution Review

 - Status: deferred
- Milestone: safety review
  - [ ] Define explicit approval criteria for any future execution work
  - [ ] Require independent paper/live reconciliation review
  - [ ] Require a new ADR before changing the paper-only invariant
