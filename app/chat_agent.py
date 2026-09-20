"""
Conversational research agent.

A small LangChain agent (``create_agent``) that answers free-text questions
from the operator over Telegram. It is **read/trigger-only**:

* It can inspect technical snapshots, audit-log trades, and paused proposal
  threads, and it can *trigger* the pipeline for a symbol.
* It can NEVER approve, reject, or otherwise resume a paused thread — that
  remains exclusively the human's job via the inline buttons.
* It never emits prices, sizes, or orders of its own; every number it reports
  comes from the deterministic screener / risk / audit layers.

The agent reuses the same provider selected for the catalyst analyst through
``LLM_PROVIDER`` and its provider-specific credentials/model settings.

Safety middleware (all built into the already-installed ``langchain`` package,
no new dependency — see ADR-020):

* ``PIIMiddleware`` redacts/masks emails and credit-card numbers the operator
  might paste into chat before they reach the LLM or logs.
* ``ToolCallLimitMiddleware`` caps tool calls per run so a confused model
  cannot loop indefinitely (e.g. repeatedly re-triggering ``run_symbol``).
* ``SummarizationMiddleware`` bounds conversation memory by condensing older
  turns once the thread grows past a token budget, closing the T-015 "bounded
  memory/summary policy" checklist item without inventing a custom summarizer.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from langchain.agents import create_agent
from langchain.agents.middleware import (
    AgentMiddleware,
    PIIMiddleware,
    SummarizationMiddleware,
    ToolCallLimitMiddleware,
)
from langgraph.checkpoint.sqlite import SqliteSaver

from app import checkpoint, executor, graph, pipeline, screener, store
from app.llm import build_chat_model, is_configured

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are the research assistant for a NIFTY 100 swing-trading desk. The
operator talks to you in plain language over Telegram.

You have tools to:
- get_symbol_snapshot(symbol): latest RSI/EMA200/ATR/price and whether the
  symbol currently qualifies for the pullback setup.
- list_trades(): the paper-trading audit log (open and closed).
- get_thread_status(symbol): whether a proposal for the symbol is paused at
  human approval, with the LLM thesis and deterministic price levels.
- run_symbol(symbol): run the symbol through the full pipeline (screener ->
  LLM catalyst analysis -> risk). If it qualifies, a proposal card is pushed
  to the operator's Telegram for approval. This can take a minute or two.
- get_symbol_history(symbol): the full step-by-step decision trail for the
  symbol's most recent run (every node transition and why it stopped). Use
  this when the operator asks "why was X rejected/approved" instead of
  guessing.

Rules:
1. You are READ/trigger-only. You can NEVER approve, reject, or kill a
   proposal — only the operator can do that via the Telegram buttons. If
   asked, explain that they must tap the button on the proposal card.
2. Never invent prices, quantities, or indicators. Only report numbers your
   tools returned. If a tool returns no data, say so.
3. Be concise — answers render in a phone chat. Use short lines, no tables.
4. When the operator asks you to "run" or "scan" a symbol, call run_symbol
   and then briefly report what happened (qualified / rejected / proposal
   sent for approval).
"""


# --------------------------------------------------------------------------- #
# Tools (all deterministic — no LLM math)
# --------------------------------------------------------------------------- #
def get_symbol_snapshot(symbol: str) -> str:
    """Latest technical snapshot (RSI, EMA200, ATR, close) for one NSE symbol."""
    snap = screener.get_symbol_snapshot(symbol.upper())
    if snap is None:
        return f"No data available for {symbol.upper()}."
    return json.dumps(snap, indent=2)


def list_trades() -> str:
    """The paper-trading audit log: open and closed trades with fills and P&L."""
    trades = executor.fetch_all_trades()
    if not trades:
        return "No trades in the audit log yet."
    return json.dumps(trades[:20], indent=2, default=str)


def get_thread_status(symbol: str) -> str:
    """Status of the LangGraph thread for a symbol (paused proposal, decision, etc.)."""
    g = graph.build_graph()
    thread_id = graph.latest_thread_id_for(symbol.upper())
    if thread_id is None:
        return f"No pipeline run recorded for {symbol.upper()} yet."
    config = {"configurable": {"thread_id": thread_id}}
    try:
        snap = g.get_state(config)
    except Exception as exc:  # noqa: BLE001
        return f"Could not read thread state for {symbol.upper()}: {exc}"

    if snap.values is None or not snap.values:
        return f"No pipeline run recorded for {symbol.upper()} yet."

    info: dict = {
        "next_nodes": list(snap.next),
        "values": {k: v for k, v in snap.values.items() if k != "news_headlines"},
    }
    if snap.interrupts:
        info["paused_at"] = "human_approval"
        info["proposal"] = snap.interrupts[0].value
    return json.dumps(info, indent=2, default=str)


def run_symbol(symbol: str) -> str:
    """Run one symbol through the full pipeline (may take a minute or two)."""
    state = pipeline.process_symbol(symbol.upper())
    if isinstance(state, dict) and state.get("__interrupt__"):
        return (
            f"{symbol.upper()} qualified and a proposal card was pushed to "
            "Telegram for approval. The operator must tap Approve/Reject."
        )
    details = state.get("execution_details") if isinstance(state, dict) else None
    return f"{symbol.upper()} finished: {details}"


def get_symbol_history(symbol: str) -> str:
    """Full step-by-step checkpoint history for a symbol's most recent run.

    Read-only time-travel over LangGraph checkpoints: shows every node
    transition, whether it paused for human approval, and the state at each
    step, so the operator can ask "why did X get rejected/approved" without
    re-running the pipeline.
    """
    history = graph.symbol_history(symbol.upper())
    if not history:
        return f"No pipeline run recorded for {symbol.upper()} yet."
    return json.dumps(history, indent=2, default=str)


def _get_checkpointer() -> SqliteSaver:
    """Return the shared long-lived checkpointer."""
    return checkpoint.get_checkpointer()


def _build_agent() -> Any:
    """Build the LangChain agent from the configured provider, with safety middleware."""
    llm = build_chat_model()
    middleware: list[AgentMiddleware[Any, Any]] = [
        PIIMiddleware("email", strategy="redact", apply_to_input=True),
        PIIMiddleware("credit_card", strategy="mask", apply_to_input=True),
        ToolCallLimitMiddleware(run_limit=8, exit_behavior="end"),
        SummarizationMiddleware(model=llm, trigger=[("tokens", 4000)], keep=("messages", 20)),
    ]
    return create_agent(
        llm,
        [get_symbol_snapshot, list_trades, get_thread_status, run_symbol, get_symbol_history],
        system_prompt=_SYSTEM_PROMPT,
        checkpointer=_get_checkpointer(),
        store=store.get_store(),
        middleware=middleware,
    )


_agent = None


def _get_agent() -> Any:
    """Lazily build (and cache) the agent."""
    global _agent
    if _agent is None:
        _agent = _build_agent()
    return _agent


def ask(question: str, thread_id: Optional[str] = None) -> str:
    """Run a free-text question through the conversational agent.

    Blocking — call from a worker thread, never the bot's event loop.
    Returns the agent's final text answer.
    """
    if not is_configured():
        return "⚠️ Configured LLM provider is unavailable; chat agent unavailable."

    try:
        agent = _get_agent()
        config = {"configurable": {"thread_id": thread_id or "chat-agent-default"}}
        result = agent.invoke({"messages": [("user", question)]}, config=config)
        answer = result["messages"][-1].content
        logger.info("CHAT AGENT answered (%d chars): %s", len(answer), answer[:120])
        return answer
    except Exception as exc:  # noqa: BLE001
        logger.exception("Chat agent failed")
        return f"⚠️ Chat agent error: {exc}"
