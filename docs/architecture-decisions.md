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

## ADR-013: Paper Transaction Costs Are Net-P&L Data

- Status: accepted
- Context: Gross paper fills overstate delivery results and make evaluation
  misleading.
- Decision: Paper closes calculate and persist gross P&L, delivery transaction
  costs, and net realized P&L. The cost model remains deterministic and
  configurable only through reviewed code/configuration.
- Consequence: Evaluation must use net P&L by default while retaining gross P&L
  for attribution.
