# Application Code Rules — app/AGENTS.md

This directory houses the core application logic, LangGraph state machines,
screener filters, risk engines, and execution layers for TrAId.

## Hard Architectural Invariants — Non-Negotiable

1. **LLM Never Touches Numbers:**
   All financial math (entry, soft stop, hard disaster stop, profit target,
   position quantity, delivery friction, turnover taxes) is calculated exclusively
   in `app/risk.py` via pure, deterministic Python functions.
   - LLMs only classify qualitative catalyst/sentiment context via structured Pydantic models.
   - Never add LLM output fields to `TradeProposal` pricing channels.
2. **Fail-Closed Everywhere:**
   - Missing data, stale prices, network timeouts, or unparseable responses must
     fail safely by rejecting the proposal or returning a conservative fallback.
   - Broad `except Exception as exc:  # noqa: BLE001` markers are intentional for
     pipeline survival and must be preserved where documented.
3. **Live Trading is Strictly Blocked (ADR-002):**
   - `executor.record_open_trade` must raise `RuntimeError` whenever
     `TRADING_MODE == "LIVE"`. Paper trading is the only authorized mode.
   - Never expose live order-routing or mutation tools to agents.
4. **Agent Tools Are Read/Trigger-Only (ADR-007):**
   - The conversational agent in `app/chat_agent.py` can only query history, check
     trades, and trigger research runs.
   - It can **never** approve, reject, cancel, or modify a trade proposal. Human
     approval is exclusively executed via Telegram inline button callbacks.
5. **No `.NS` in Internal State:**
   - Internal state, database records, and proposals use raw NSE tickers (e.g. `RELIANCE`).
   - `.NS` is appended only at the Yahoo Finance query boundary in `app/screener.py`
     and `app/market_data.py`.
6. **Unified Persistence Contract (ADR-023):**
   - All state transitions, LangGraph checkpoints (`PostgresSaver`), operator
     profiles (`PostgresStore`), and audit logs (`trade_audit_log`) must use the
     centralized PostgreSQL connection pool (`app.db.get_connection_pool()`).
7. **Type Safety & Data Transfer Models:**
   - Avoid passing untyped dictionaries between modules. Use the Pydantic models
     defined in `app/models.py` (`TechnicalSnapshot`, `ExecutionResult`, `TradeRecord`).
8. **Deterministic Hashing:**
   - Cache keys and snapshot IDs must be generated via `app.evidence.content_hash()`.
     Never use Python's built-in `str(dict)` for cache keys.
