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
from pathlib import Path
from typing import Any, Optional

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from config.settings import get_settings
from app.state import TradingState
from app import screener, analyst, risk, executor

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Node implementations
# --------------------------------------------------------------------------- #
def _math_screener(state: TradingState) -> dict:
    """Entry node: pull the technical snapshot for the target symbol.

    In a full daily run the universe scan happens in `main.py`; this node
    re-derives the snapshot for the single symbol the thread is processing so
    the state is self-contained and checkpointable.
    """
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
    }
    decision = interrupt(card)
    return {"human_decision": decision}


def _paper_execute(state: TradingState) -> dict:
    """Simulate the paper fill and record the audit row (only if approved)."""
    if state.get("human_decision") != "APPROVED":
        return {"execution_details": {"status": "NOT_EXECUTED"}}

    proposal = state["order_proposal"]
    assessment = state.get("catalyst_assessment")
    details = executor.record_open_trade(
        proposal=proposal,
        rsi=state["rsi"],
        ema_200=state["ema_200"],
        atr=state["atr"],
        thesis=assessment.thesis_rationale if assessment else "",
        human_decision="APPROVED",
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


def _get_checkpointer() -> SqliteSaver:
    """Return a process-wide `SqliteSaver` backed by a persistent connection.

    `SqliteSaver.from_conn_string()` returns a *context manager*, not a saver,
    so we build the saver from a long-lived `sqlite3` connection instead. The
    connection (and its `data/` directory) is created once and reused, which
    keeps checkpoints durable across `build_graph()` calls.
    """
    global _checkpointer
    if _checkpointer is None:
        settings = get_settings()
        db_path = Path(settings.CHECKPOINT_DB_PATH)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        _checkpointer = SqliteSaver(conn)
    return _checkpointer


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


def run_symbol(symbol: str, news_headlines: Optional[list[str]] = None) -> dict:
    """Run the graph for a single symbol up to (and including) the interrupt.

    Returns the current state. If the graph paused at `human_approval`, the
    returned state will contain `__interrupt__` and the caller should resume
    with `resume_symbol(...)`.
    """
    graph = build_graph()
    config = {"configurable": {"thread_id": f"trade-{symbol}"}}
    initial_state: TradingState = {
        "symbol": symbol,
        "news_headlines": news_headlines or [],
    }
    return graph.invoke(initial_state, config)


def resume_symbol(symbol: str, decision: str) -> dict:
    """Resume a paused thread with a human decision.

    Parameters
    ----------
    symbol:
        The symbol whose thread is paused at `human_approval`.
    decision:
        "APPROVED" or "REJECTED" (or "KILLED" for emergency stop).
    """
    graph = build_graph()
    config = {"configurable": {"thread_id": f"trade-{symbol}"}}
    return graph.invoke(Command(resume=decision), config)
