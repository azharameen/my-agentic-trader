# Tasks

This is the live implementation ledger. Status values are `backlog`, `todo`,
`active`, `inreview`, and `done`. Agents must update status while working,
checklist items as work completes, and update the relevant docs before moving a
task to `done`. Completed tasks are removed after merge; durable decisions stay
in `architecture-decisions.md`.

## active

No tasks currently active.

## inreview

### T-001 Documentation Contract

- Status: inreview
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

## todo

### T-002 Source and Data Inventory

- Status: todo
- Milestone: current data contract
  - [ ] Document schemas for universe, OHLCV, news, assessment, proposal, and audit
  - [ ] Record source timestamps and freshness requirements
  - [ ] Define symbol, ISIN, company, and sector identity rules
- Milestone: source validation
  - [ ] Define retry, timeout, cache, and fallback policy per source
  - [ ] Define cross-source price and event conflict handling

### T-003 Corporate Research Inputs

- Status: todo
- Milestone: events
  - [ ] Add NSE/BSE announcements
  - [ ] Add results and earnings calendar
  - [ ] Add dividends, splits, bonuses, and pledge events
- Milestone: evidence
  - [ ] Store URLs, publication times, hashes, and parser status
  - [ ] Deduplicate events deterministically

### T-004 Market Context

- Status: todo
- Milestone: regime
  - [ ] Add index trend and volatility context
  - [ ] Add breadth and sector-relative strength
  - [ ] Add event-risk and liquidity filters
- Milestone: fallback
  - [ ] Evaluate an alternate free OHLCV provider
  - [ ] Add stale and disagreement detection

### T-005 Agentic Research Workflow

- Status: todo
- Milestone: agents
  - [ ] Define planner, collector, validator, analyst, and report-writer tools
  - [ ] Enforce read/trigger-only chat boundaries
  - [ ] Add source citations to every report
- Milestone: evaluation
  - [ ] Build deterministic tool-call regression tests
  - [ ] Store research snapshots for reproducibility

### T-006 Read-Only Groww Context

- Status: backlog
- Milestone: capability check
  - [ ] Confirm supported read-only Groww endpoints and authentication flow
  - [ ] Confirm terms, quotas, token expiry, and account-data scope
- Milestone: isolated adapter
  - [ ] Import holdings, positions, orders, and P&L only if supported
  - [ ] Prevent order methods from entering agent tool registries
  - [ ] Add reconciliation tests

### T-007 Evaluation and Reporting

- Status: backlog
- Milestone: outcomes
  - [ ] Capture frozen proposal evidence and later paper outcomes
  - [ ] Calculate expectancy, drawdown, hit rate, and attribution
- Milestone: operations
  - [ ] Add source freshness metrics
  - [ ] Add pipeline quality and failure summaries
  - [ ] Add weekly research report export

## done

No tasks currently complete.

## backlog

### T-008 Future Execution Review

- Status: backlog
- Milestone: safety review
  - [ ] Define explicit approval criteria for any future execution work
  - [ ] Require independent paper/live reconciliation review
  - [ ] Require a new ADR before changing the paper-only invariant
