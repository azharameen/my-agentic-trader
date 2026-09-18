# Tasks

This is the live implementation ledger. Status values are `backlog`, `todo`,
`active`, `inreview`, and `done`. Agents must update status while working,
checklist items as work completes, and update the relevant docs before moving a
task to `done`. Completed tasks are removed after merge; durable decisions stay
in `architecture-decisions.md`.

## Execution Plan

Work proceeds in dependency order. Do not start a later phase until the prior
phase's data contracts and tests are complete.

1. T-002: establish normalized data contracts, freshness, provenance, and
   validation rules, including the single evidence-snapshot schema and
   attribution fields needed later by T-007.
2. T-003: resolve source authority and access constraints, then ingest corporate
   evidence using the T-002 contracts.
3. T-004: add market regime and risk context after T-002; add event-dependent
   vetoes only after T-003.
4. T-005: build the research-agent workflow over the validated evidence layer.
5. T-007: evaluate outcomes and operational quality using frozen research
   snapshots.
6. T-006: add Groww read-only context after its supported capabilities and terms
   are verified; it must not block the research workflow.
7. T-008: remains deferred unless the paper-only invariant is deliberately
   reconsidered.

## Definition Of Done

- Tests cover the new behavior and source failure paths.
- Relevant architecture, PRD, reference, and ADR documents are updated.
- Provenance and freshness are persisted for external evidence.
- No LLM-generated numeric risk values enter deterministic state.
- The chat agent remains read/trigger-only.
- No live buy, sell, or order-modification path is introduced.
- The task reaches `inreview` before `done`.

## Readiness Matrix

| Task | Readiness | Main blocker or decision |
| --- | --- | --- |
| T-002 | In review | Contracts, snapshots, provenance, attribution, and tests implemented; numeric validation thresholds remain for ADR-011 |
| T-003 | Research-ready; implementation-blocked | Decide official-source access/terms and concrete collection method |
| T-004 | Partially ready | Regime work can start after T-002; event vetoes wait for T-003; thresholds need ADR-011 |
| T-005 | Not ready | Needs T-002 snapshot/evidence contracts and T-003/T-004 validated inputs |
| T-006 | Capability-check only | Groww read-only endpoints, terms, quotas, and credential scope are unknown |
| T-007 | Partially ready | Needs snapshot schema, attribution fields, baseline, metric formulas, and sample-size policy |
| T-008 | Deferred by scope | Only starts if the paper-only invariant is intentionally reconsidered |

## active

No tasks currently active.

## inreview

### T-010 Agentic Trader Modernization

- Status: inreview
- Scope note: safe modernization is active. Parallel `Send` fan-out, richer
  research inputs, async lifecycle hardening, SQLite-backed persistence, and
  paper friction modeling are in scope. Live Groww/Zerodha GTT/order routing is
  not authorized and remains behind T-008 plus a new accepted ADR.
- Milestone: CI and lifecycle hardening
  - [x] Reproduce current CI lint/type/test results locally
  - [x] Fix repository lint/type failures without weakening checks
  - [ ] Add external-network mocks for yfinance, Telegram, and broker adapters
  - [ ] Add async lifecycle tests only where async code is introduced
- Milestone: graph modernization
  - [x] Define reducer-safe state fields without changing existing proposal behavior
  - [ ] Evaluate dynamic `Send` fan-out against current universe-scan orchestration
  - [ ] Keep native `interrupt()` and approval resume fail-closed
  - [x] Keep SQLite as the only supported checkpoint persistence system
- Milestone: market context
  - [x] Define India VIX and NIFTY trend data contracts
  - [x] Define corporate event and earnings blackout data contracts
  - [ ] Define FII/DII flow data contract and source authority
- Milestone: analyst workflow
  - [ ] Split qualitative research into bullish, risk-critic, and synthesis roles
  - [ ] Preserve deterministic ownership of prices, risk, and order fields
  - [ ] Add structured regression fixtures for claims and citations
- Milestone: paper execution safety
  - [x] Add circuit/ASM/GSM inputs as deterministic rejection context
  - [x] Add realistic paper transaction-cost accounting
  - [ ] Keep broker order methods fail-closed and unavailable to research agents
- Milestone: verification
  - [ ] Run the full test suite and CI-equivalent checks
  - [ ] Update architecture, PRD, reference, and ADR documents
  - [ ] Move this task to `inreview` before completion

## todo

### T-002 Source and Data Inventory

- Status: inreview
- Milestone: current data contract
  - [x] Document schemas for universe, OHLCV, news, assessment, proposal, and audit
  - [x] Record source timestamps and freshness requirements
  - [x] Define symbol, ISIN, company, and sector identity rules
  - [x] Define immutable evidence-snapshot schema shared by reports and evaluations
  - [x] Define proposal attribution fields: strategy, regime, catalyst type, and source set
- Milestone: source validation
  - [ ] Define retry, timeout, cache, and fallback policy per source
  - [ ] Define cross-source price and event conflict handling
  - [ ] Accept numeric freshness thresholds per source class
  - [ ] Accept numeric disagreement tolerances and authority rules
- Milestone: persistence contract
  - [x] Add source/provenance records to the audit schema
  - [x] Store content hash and parser status for research artifacts
  - [x] Add freshness and validation status to pipeline state
- Milestone: verification
  - [x] Add fixture-based tests for valid, stale, missing, and conflicting data
  - [x] Update `docs/architecture.md` and `docs/reference.md`
- Milestone: decision gate
  - [x] Resolve proposed ADR-009
  - [ ] Resolve proposed ADR-011 thresholds that apply to data validation

### T-003 Corporate Research Inputs

- Status: inreview
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

- Status: todo
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

- Status: todo
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

### T-006 Read-Only Groww Context

- Status: backlog
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

### T-007 Evaluation and Reporting

- Status: backlog
- Milestone: outcomes
  - [ ] Capture frozen proposal evidence and later paper outcomes
  - [ ] Calculate expectancy, drawdown, hit rate, and attribution
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
  - [ ] Reuse T-002 evidence snapshots and attribution fields
  - [ ] Approve baseline and metric definitions before reporting implementation

## done

### T-001 Documentation Contract

- Status: done
- Milestone: canonical docs
  - [x] Create `docs/architecture.md`
  - [x] Create `docs/prd.md`
  - [x] Create `docs/reference.md`
  - [x] Create `docs/architecture-decisions.md`
  - [x] Create `docs/tasks.md`
- Milestone: enforcement
  - [x] Update `AGENTS.md` with docs-first rules
  - [x] Replace duplicate root architecture content with canonical link
  - [x] Verify links and terminology

### T-009 Architecture Deepening

- Status: done
- Milestone: market data
  - [x] Centralize OHLCV loading
  - [x] Preserve source and fetch timestamp
  - [x] Cover single-symbol and universe paths
- Milestone: persistence
  - [x] Centralize checkpointer construction
  - [x] Preserve SQLite thread-index behavior
  - [x] Reset shared state in tests
- Milestone: proposal contract
  - [x] Add validated `ProposalCard`
  - [x] Preserve existing graph and Telegram key access
- Milestone: universe locality
  - [x] Reuse resolved universe rows
  - [x] Add explicit cache reset for refresh/tests
- Milestone: deliberate deferral
  - [x] Keep Telegram split deferred until a second notification adapter exists
- Milestone: verification
  - [x] Add focused architecture tests
  - [x] Run full test suite

## backlog

### T-008 Future Execution Review

- Status: backlog
- Milestone: safety review
  - [ ] Define explicit approval criteria for any future execution work
  - [ ] Require independent paper/live reconciliation review
  - [ ] Require a new ADR before changing the paper-only invariant
