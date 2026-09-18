"""
LangGraph trading pipeline.

Builds a `StateGraph(TradingState)` with the following node chain:

    math_screener -> analyze_catalyst -> calculate_risk -> human_approval -> paper_execute

Key LangGraph concepts used here:

* **Checkpoints** — a `SqliteSaver` (from `data/checkpoints.db`) persists the
  full `TradingState` after every super-step. If the process dies mid-run, the
  thread can be resumed from the last checkpoint without re-running completed
  nodes.
* **Human-in-the-Loop** — the `human_approval` node calls LangGraph's native
  `interrupt()`. This *pauses* the graph, persists state, and returns the
  proposal to the caller. The graph only continues when resumed with
  `Command(resume="APPROVED")` or `Command(resume="REJECTED")`.
* **Conditional routing** — after the analyst, structurally-damaged setups are
  routed straight to a terminal `rejected` node (no human prompt needed for an
  obvious no-trade).

The graph is compiled once and cached. Each symbol is run in its own thread
(`thread_id`) so checkpoints stay isolated per trade.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from config.settings import get_settings
from app.state import TradingState
from app import observability, screener, analyst, risk, executor, broker

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Node implementations
# --------------------------------------------------------------------------- #
def _math_screener(state: TradingState) -> dict:
    """Entry node: pull the technical snapshot for the target symbol.

    If the caller already computed the snapshot (e.g. the universe scan
    already ran `scan_nifty_universe` for this symbol), those values are
    pre-seeded into the state and this node is a no-op — avoids downloading
    the same OHLCV history twice per symbol on every `/scan`.
    """
    if all(k in state for k in ("daily_close", "rsi", "ema_200", "atr")):
        return {}

    symbol = state["symbol"]
    snapshot = screener.scan_nifty_universe([symbol])
    if not snapshot:
        # No qualifying setup — terminate cleanly.
        logger.info("math_screener: %s not in qualifying set; ending thread.", symbol)
        return {"human_decision": "NO_SETUP"}
    row = snapshot[0]
    return {
        "daily_close": row["daily_close"],
        "rsi": row["rsi"],
        "ema_200": row["ema_200"],
        "atr": row["atr"],
    }


def _analyze_catalyst(state: TradingState) -> dict:
    """LLM qualitative filter: classify the nature of the price drop."""
    symbol = state["symbol"]
    headlines = state.get("news_headlines", [])
    assessment = analyst.analyze_catalyst(symbol, headlines)
    return {"catalyst_assessment": assessment}


def _calculate_risk(state: TradingState) -> dict:
    """Deterministic risk engine: build the TradeProposal (or reject)."""
    symbol = state["symbol"]
    proposal = risk.calculate_risk(
        symbol=symbol,
        entry_price=state["daily_close"],
        atr=state["atr"],
        portfolio_capital=executor.get_current_capital(),
    )
    if proposal is None:
        return {"human_decision": "REJECTED_RISK"}
    return {"order_proposal": proposal}


def _human_approval(state: TradingState) -> dict:
    """HITL gate: pause the graph and wait for a Telegram approval signal.

    `interrupt()` suspends execution and returns the proposal to the caller.
    When the graph is resumed with `Command(resume="APPROVED")` or
    `Command(resume="REJECTED")`, `interrupt()` returns that value.
    """
    proposal = state["order_proposal"]
    assessment = state.get("catalyst_assessment")
    card = {
        "symbol": proposal.symbol,
        "entry_price": proposal.entry_price,
        "soft_stop": proposal.soft_stop,
        "hard_stop": proposal.hard_stop,
        "target_price": proposal.target_price,
        "quantity": proposal.quantity,
        "risk_amount": proposal.risk_amount,
        "risk_to_reward": proposal.risk_to_reward,
        "thesis": assessment.thesis_rationale if assessment else "",
        "catalyst_type": assessment.catalyst_type if assessment else "UNKNOWN",
        "proposed_at": datetime.now(timezone.utc).isoformat(),
    }
    decision = interrupt(card)
    return {"human_decision": decision, "proposal_card": card}


def _proposal_is_stale(card: dict, symbol: str, entry_price: float) -> bool:
    """True if the proposal is old enough AND the price has drifted meaningfully.

    A stale-but-still-near-entry approval is allowed through (the setup is
    still valid); a stale AND price-moved approval is rejected so the human
    doesn't execute at outdated levels — they should re-run the symbol.
    """
    settings = get_settings()
    proposed_at = card.get("proposed_at")
    if not proposed_at:
        return False
    try:
        proposed_dt = datetime.fromisoformat(proposed_at)
    except ValueError:
        return False

    age_minutes = (datetime.now(timezone.utc) - proposed_dt).total_seconds() / 60
    if age_minutes < settings.STALE_PROPOSAL_MINUTES:
        return False

    snap = screener.get_symbol_snapshot(symbol)
    if snap is None:
        return True  # can't verify current price; be conservative
    move_pct = abs(snap["daily_close"] - entry_price) / entry_price if entry_price else 0.0
    return move_pct > settings.STALE_PROPOSAL_PRICE_MOVE_PCT


def _paper_execute(state: TradingState) -> dict:
    """Simulate the paper fill and record the audit row (only if approved)."""
    if state.get("human_decision") != "APPROVED":
        return {"execution_details": {"status": "NOT_EXECUTED"}}

    proposal = state["order_proposal"]
    card = state.get("proposal_card") or {}
    if _proposal_is_stale(card, proposal.symbol, proposal.entry_price):
        logger.warning("Rejecting stale approval for %s (proposed_at=%s).",
                       proposal.symbol, card.get("proposed_at"))
        return {
            "human_decision": "REJECTED_STALE",
            "execution_details": {"status": "REJECTED_STALE", "reason": "Price moved since proposal; re-run the symbol."},
        }

    assessment = state.get("catalyst_assessment")
    trade_broker = broker.get_broker(get_settings().TRADING_MODE)
    details = trade_broker.open_trade(
        proposal=proposal,
        rsi=state["rsi"],
        ema_200=state["ema_200"],
        atr=state["atr"],
        thesis=assessment.thesis_rationale if assessment else "",
        human_decision="APPROVED",
        news_headlines=state.get("news_headlines") or [],
    )
    return {"execution_details": details}


# --------------------------------------------------------------------------- #
# Routing
# --------------------------------------------------------------------------- #
def _route_after_screener(state: TradingState) -> str:
    if state.get("human_decision") == "NO_SETUP":
        return "end"
    return "analyze_catalyst"


def _route_after_analyst(state: TradingState) -> str:
    assessment = state.get("catalyst_assessment")
    if assessment is not None and not assessment.is_temporary_pullback:
        # Structural damage / non-pullback -> reject without a human prompt.
        return "rejected"
    return "calculate_risk"


def _route_after_risk(state: TradingState) -> str:
    if state.get("human_decision") == "REJECTED_RISK":
        return "rejected"
    return "human_approval"


def _route_after_approval(state: TradingState) -> str:
    if state.get("human_decision") == "APPROVED":
        return "paper_execute"
    return "rejected"


# --------------------------------------------------------------------------- #
# Graph construction
# --------------------------------------------------------------------------- #
_checkpointer: Optional[SqliteSaver] = None
_checkpoint_conn: Optional[sqlite3.Connection] = None

_THREAD_INDEX_SCHEMA = """
CREATE TABLE IF NOT EXISTS graph_threads (
    thread_id   TEXT PRIMARY KEY,
    symbol      TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
"""


def _get_checkpointer() -> SqliteSaver:
    """Return a process-wide `SqliteSaver` backed by a persistent connection.

    `SqliteSaver.from_conn_string()` returns a *context manager*, not a saver,
    so we build the saver from a long-lived `sqlite3` connection instead. The
    connection (and its `data/` directory) is created once and reused, which
    keeps checkpoints durable across `build_graph()` calls.
    """
    global _checkpointer, _checkpoint_conn
    if _checkpointer is None:
        settings = get_settings()
        db_path = Path(settings.CHECKPOINT_DB_PATH)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        conn.executescript(_THREAD_INDEX_SCHEMA)
        _checkpoint_conn = conn
        _checkpointer = SqliteSaver(conn)
    return _checkpointer


def _record_thread(thread_id: str, symbol: str) -> None:
    """Track active trade threads in our own table instead of checkpoint internals."""
    _get_checkpointer()
    if _checkpoint_conn is None:
        return
    try:
        _checkpoint_conn.execute(
            """
            INSERT INTO graph_threads (thread_id, symbol, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(thread_id) DO UPDATE SET
                symbol = excluded.symbol,
                updated_at = excluded.updated_at
            """,
            (thread_id, symbol, datetime.now(timezone.utc).isoformat()),
        )
        _checkpoint_conn.commit()
    except sqlite3.OperationalError as exc:
        logger.warning("Could not record graph thread %s: %s", thread_id, exc)


def _backfill_thread_index() -> None:
    """Best-effort migration from checkpoint internals to the public thread index."""
    _get_checkpointer()
    if _checkpoint_conn is None:
        return
    try:
        indexed = _checkpoint_conn.execute("SELECT COUNT(*) FROM graph_threads").fetchone()
        if indexed and indexed[0]:
            return
        cur = _checkpoint_conn.execute(
            "SELECT DISTINCT thread_id FROM checkpoints WHERE thread_id LIKE ?",
            ("trade-%",),
        )
        rows = [row[0] for row in cur.fetchall()]
        if not rows:
            return
        now = datetime.now(timezone.utc).isoformat()
        _checkpoint_conn.executemany(
            "INSERT OR IGNORE INTO graph_threads (thread_id, symbol, updated_at) VALUES (?, ?, ?)",
            [(thread_id, thread_id.split("-", 2)[1] if "-" in thread_id else thread_id, now) for thread_id in rows],
        )
        _checkpoint_conn.commit()
    except sqlite3.OperationalError:
        return


def _all_thread_ids(prefix: str = "trade-") -> list[str]:
    """Distinct thread ids recorded in the checkpoint DB, matching a prefix.

    Queries the checkpointer's own SQLite connection directly (rather than
    LangGraph's generic `list()` API) so we can filter server-side and avoid
    depending on undocumented listing semantics.
    """
    _backfill_thread_index()
    if _checkpoint_conn is None:
        return []
    try:
        cur = _checkpoint_conn.execute(
            "SELECT thread_id FROM graph_threads WHERE thread_id LIKE ? ORDER BY updated_at",
            (f"{prefix}%",),
        )
        return [row[0] for row in cur.fetchall()]
    except sqlite3.OperationalError as exc:
        logger.warning("Could not list checkpoint thread ids: %s", exc)
        return []


def latest_thread_id_for(symbol: str) -> Optional[str]:
    """Most recent thread id for a symbol (thread ids embed an ISO date suffix)."""
    prefix = f"trade-{symbol}-"
    candidates = [t for t in _all_thread_ids() if t.startswith(prefix)]
    return candidates[-1] if candidates else None


def list_pending_approvals() -> list[dict]:
    """Every proposal card currently paused at `human_approval`, across all threads."""
    g = build_graph()
    pending: list[dict] = []
    for thread_id in _all_thread_ids():
        config = {"configurable": {"thread_id": thread_id}}
        try:
            snap = g.get_state(config)
        except Exception:  # noqa: BLE001 - a corrupt/partial checkpoint must not break the listing
            continue
        if snap.interrupts:
            pending.append(dict(snap.interrupts[0].value))
    return pending


def build_graph(checkpointer: Optional[SqliteSaver] = None) -> Any:
    """Compile the trading StateGraph with a SQLite checkpointer.

    Parameters
    ----------
    checkpointer:
        Optional pre-built `SqliteSaver`. If omitted, the process-wide saver
        backed by `CHECKPOINT_DB_PATH` is used.

    Returns
    -------
    Compiled graph ready for `.invoke()` / `.stream()` with a `thread_id`.
    """
    if checkpointer is None:
        checkpointer = _get_checkpointer()

    graph = StateGraph(TradingState)

    graph.add_node("math_screener", _math_screener)
    graph.add_node("analyze_catalyst", _analyze_catalyst)
    graph.add_node("calculate_risk", _calculate_risk)
    graph.add_node("human_approval", _human_approval)
    graph.add_node("paper_execute", _paper_execute)
    graph.add_node("rejected", lambda s: {"execution_details": {"status": "REJECTED"}})

    graph.add_edge(START, "math_screener")
    graph.add_conditional_edges(
        "math_screener", _route_after_screener,
        {"analyze_catalyst": "analyze_catalyst", "end": END},
    )
    graph.add_conditional_edges(
        "analyze_catalyst", _route_after_analyst,
        {"calculate_risk": "calculate_risk", "rejected": "rejected"},
    )
    graph.add_conditional_edges(
        "calculate_risk", _route_after_risk,
        {"human_approval": "human_approval", "rejected": "rejected"},
    )
    graph.add_conditional_edges(
        "human_approval", _route_after_approval,
        {"paper_execute": "paper_execute", "rejected": "rejected"},
    )
    graph.add_edge("paper_execute", END)
    graph.add_edge("rejected", END)

    return graph.compile(checkpointer=checkpointer)


def run_symbol(
    symbol: str,
    news_headlines: Optional[list[str]] = None,
    snapshot: Optional[dict] = None,
) -> dict:
    """Run the graph for a single symbol up to (and including) the interrupt.

    A fresh `thread_id` is used per calendar day (`trade-<SYMBOL>-<ISO date>`)
    so re-running a symbol on a later date doesn't silently resume a stale
    checkpoint from a previous run.

    Parameters
    ----------
    snapshot:
        Optional pre-computed technical snapshot (`daily_close`/`rsi`/
        `ema_200`/`atr`) from an earlier `screener.scan_nifty_universe` call,
        so `_math_screener` can skip re-downloading the same OHLCV history.

    Returns the current state. If the graph paused at `human_approval`, the
    returned state will contain `__interrupt__` and the caller should resume
    with `resume_symbol(...)`.
    """
    graph = build_graph()
    thread_id = f"trade-{symbol}-{date.today().isoformat()}"
    config = {"configurable": {"thread_id": thread_id}}
    _record_thread(thread_id, symbol)
    initial_state: TradingState = {
        "symbol": symbol,
        "news_headlines": news_headlines or [],
    }
    if snapshot is not None:
        initial_state.update({
            "daily_close": snapshot["daily_close"],
            "rsi": snapshot["rsi"],
            "ema_200": snapshot["ema_200"],
            "atr": snapshot["atr"],
        })
    with observability.span("graph.run_symbol", symbol=symbol):
        return graph.invoke(initial_state, config)


def resume_symbol(symbol: str, decision: str) -> dict:
    """Resume a paused thread with a human decision.

    Resolves the *most recent* thread for the symbol (see
    `latest_thread_id_for`) rather than assuming today's date, so an approval
    tapped after midnight still resumes the thread that actually paused.

    Parameters
    ----------
    symbol:
        The symbol whose thread is paused at `human_approval`.
    decision:
        "APPROVED" or "REJECTED" (or "KILLED" for emergency stop).
    """
    graph = build_graph()
    thread_id = latest_thread_id_for(symbol) or f"trade-{symbol}-{date.today().isoformat()}"
    config = {"configurable": {"thread_id": thread_id}}
    _record_thread(thread_id, symbol)
    with observability.span("graph.resume_symbol", symbol=symbol, decision=decision):
        return graph.invoke(Command(resume=decision), config)
