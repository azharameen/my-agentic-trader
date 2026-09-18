# Product Requirements

## Product

NIFTY 100 Research Assistant: a high-quality, evidence-backed, human-controlled
research system for Indian cash-equity swing trading. The product may simulate
paper trades but must not buy or sell securities automatically.

## Goals

- Improve research quality through broader, fresher, cited evidence.
- Keep every numeric market and risk fact deterministic and reproducible.
- Give the operator concise Telegram reports with drill-down evidence.
- Detect stale, missing, contradictory, or low-confidence data.
- Learn from paper outcomes without allowing the LLM to rewrite history.
- Use free/public sources wherever quality is acceptable.

## Non-Goals

- Automated buying, selling, or order modification.
- Intraday or high-frequency execution.
- Investment advice or guaranteed returns.
- Replacing official filings with an LLM summary.
- Adding cloud infrastructure before local evaluation proves the need.

## Users

- **Operator:** reviews evidence and approves or rejects paper proposals.
- **Developer agent:** implements only tasks authorized by this documentation.
- **Research agent:** gathers and explains evidence within tool and policy
  boundaries.

## Core Workflows

### Daily research

1. Resolve the current universe.
2. Fetch and validate market data.
3. Apply deterministic technical and regime filters.
4. Gather news, announcements, events, and fundamentals for candidates.
5. Produce a cited research brief with source timestamps and uncertainty.
6. Apply deterministic risk and exposure gates.
7. Send a paper proposal to Telegram only when all required gates pass.

### Read-only portfolio context

1. Authenticate to Groww only through a dedicated read-only adapter, if its
   supported API permits this.
2. Import holdings, positions, order history, and account metadata.
3. Store fetched data with timestamp and source.
4. Use it for exposure and context only; never submit orders.

### Evaluation

1. Freeze the evidence and technical snapshot used for each proposal.
2. Track approval, rejection, paper fill, exit, return, drawdown, and reason.
3. Compare outcomes by strategy, source coverage, regime, and catalyst class.
4. Change thresholds only through documented tasks and architecture decisions.

## Quality Requirements

- Every report includes source citations, fetched timestamps, and freshness.
- Every numeric value identifies its source and calculation method.
- A single bad symbol or source cannot abort the universe run.
- Incomplete critical evidence cannot generate a proposal.
- Duplicate events and headlines are removed deterministically.
- All external calls have timeout, retry, rate-limit, and cache behavior.
- Research outputs are reproducible from stored snapshots.
- No agent can approve, reject, or execute a paper trade through free text.

## Phased Scope

### Phase 0: Documentation and governance

Canonical docs, source inventory, task workflow, agent boundaries, and ADR
process.

### Phase 1: Data quality foundation

Source adapters, normalized schemas, provenance, freshness checks, caching,
cross-source validation, and corporate event ingestion.

### Phase 2: Deep research

Announcements, results, fundamentals, corporate actions, earnings calendar,
sector context, market regime, and research reports with citations.

### Phase 3: Agentic analysis

Planner, collector, validator, analyst, report writer, and evaluation harness.
Agents remain read-only with deterministic tool outputs.

### Phase 4: Portfolio context and evaluation

Optional Groww read-only synchronization, exposure-aware research, paper-trade
analytics, attribution, and regression datasets.

## Success Metrics

- Percentage of proposals with complete source provenance.
- Percentage of source fetches passing freshness and schema validation.
- Cross-source disagreement rate for prices and events.
- Research report citation coverage.
- False-positive and false-negative rates by strategy and catalyst class.
- Paper-trade expectancy, drawdown, and outcome attribution.
- Zero live orders and zero LLM-generated risk numbers.

## Acceptance Boundary

The product is complete for the current phase when the docs are canonical, the
source matrix is maintained, tasks are traceable, all research outputs are
auditable, and the system remains paper-only.
