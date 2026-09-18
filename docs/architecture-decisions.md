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
