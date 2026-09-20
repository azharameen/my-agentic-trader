# Documentation Governance — docs/AGENTS.md

This directory is the **canonical source of truth** for product scope,
system architecture, external references, architectural decisions, and task
status. Code, configuration, and agent behaviors must strictly conform to the
contracts defined here.

## Core Rules for Documentation Changes

1. **Source of Truth Rule:**
   Never implement code changes that contradict the documentation in this
   directory. If requirements change, update `docs/` first before touching code.
2. **ADR Mandate:**
   Any change affecting data storage, risk rules, agent boundaries, network
   dependencies, or execution authority must have an accepted Architecture
   Decision Record (ADR) in `docs/architecture-decisions.md`.
3. **No Phantom Capabilities:**
   In `docs/architecture.md`, maintain a strict distinction between:
   - **Current State Architecture (As-Is)**: What actually runs in the repo today.
   - **Target Modernized Architecture (To-Be)**: What is planned in active/backlog ADRs.
4. **SDLC Compliance:**
   Follow the status definitions, gate transition criteria, and nested hierarchy
   defined in [`docs/sdlc-process.md`](sdlc-process.md).
5. **Task Ledger Integrity:**
   - Every task in `docs/tasks.md` must follow the Task $\rightarrow$ Sub-Tasks
     $\rightarrow$ Milestones $\rightarrow$ Checklists nested hierarchy.
   - Never mark a task `done` until all checklists are ticked, automated tests
     pass, and related doc files (`prd.md`, `architecture.md`, `reference.md`)
     are fully synchronized.
6. **Zero Duplication:**
   Do not copy whole sections between `prd.md`, `architecture.md`, and
   `reference.md`. Keep boundaries clean:
   - `prd.md`: Product scope, user persona, problem statement, acceptance metrics.
   - `architecture.md`: Data flow, state graphs, system topology, component contracts.
   - `reference.md`: External endpoints, source quotas, environment keys, technical tables.
   - `architecture-decisions.md`: Context, decisions, and consequences log (ADR).
   - `tasks.md`: Operational task backlog and active checklist ledger.
   - `sdlc-process.md`: Workflow standards, gate criteria, and multi-agent roles.
