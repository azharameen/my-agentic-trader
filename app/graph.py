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
from typing import Any, Optional

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from app import (
    analyst,
    broker,
    cache,
    checkpoint,
    corporate_events,
    evidence,
    executor,
    observability,
    risk,
    screener,
    store,
)
from app.llm import provider_metadata
from app.state import ProposalCard, TradeProposal, TradingState
from config.settings import get_settings

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
        "source_set": [row.get("data_source", "unknown")],
    }


def _analyze_catalyst(state: TradingState) -> dict:
    """LLM qualitative filter: classify the nature of the price drop."""
    symbol = state["symbol"]
    headlines = state.get("news_headlines", [])
    assessment = analyst.analyze_catalyst(symbol, headlines)
    return {
        "catalyst_assessment": assessment.model_dump(mode="json"),
        "llm_metadata": provider_metadata(),
    }


def _calculate_risk(state: TradingState) -> dict:
    """Deterministic risk engine: build the TradeProposal (or reject)."""
    symbol = state["symbol"]
    event_reason = corporate_events.blackout_reason(
        [corporate_events.CorporateEvent.model_validate(item) for item in state.get("corporate_events", [])],
        symbol,
        holding_days=get_settings().CORPORATE_EVENT_BLACKOUT_DAYS,
    )
    if event_reason:
        return {"human_decision": event_reason}
    proposal = risk.calculate_risk(
        symbol=symbol,
        entry_price=state["daily_close"],
        atr=state["atr"],
        portfolio_capital=executor.get_current_capital(),
    )
    if proposal is None:
        return {"human_decision": "REJECTED_RISK", "rejection_reason": "POSITION_SIZE_OR_RISK"}
    return {"order_proposal": proposal.model_dump(mode="json")}


def _human_approval(state: TradingState) -> dict:
    """HITL gate: pause the graph and wait for a Telegram approval signal.

    `interrupt()` suspends execution and returns the proposal to the caller.
    When the graph is resumed with `Command(resume="APPROVED")` or
    `Command(resume="REJECTED")`, `interrupt()` returns that value.
    """
    proposal = TradeProposal.model_validate(state["order_proposal"])
    assessment_data = state.get("catalyst_assessment")
    assessment = analyst.CatalystAssessment.model_validate(assessment_data) if assessment_data else None
    card = ProposalCard(
        symbol=proposal.symbol,
        entry_price=proposal.entry_price,
        soft_stop=proposal.soft_stop,
        hard_stop=proposal.hard_stop,
        target_price=proposal.target_price,
        quantity=proposal.quantity,
        risk_amount=proposal.risk_amount,
        risk_to_reward=proposal.risk_to_reward,
        thesis=assessment.thesis_rationale if assessment else "",
        catalyst_type=assessment.catalyst_type if assessment else "UNKNOWN",
        proposed_at=datetime.now(timezone.utc),
    )
    decision = interrupt(card.model_dump(mode="json"))
    return {"human_decision": decision, "proposal_card": card.model_dump(mode="json")}


def _proposal_is_stale(card: ProposalCard | dict, symbol: str, entry_price: float) -> bool:
    """True if the proposal is old enough AND the price has drifted meaningfully.

    A stale-but-still-near-entry approval is allowed through (the setup is
    still valid); a stale AND price-moved approval is rejected so the human
    doesn't execute at outdated levels — they should re-run the symbol.
    """
    settings = get_settings()
    proposed_at = card.get("proposed_at") if isinstance(card, dict) else card.proposed_at
    if not proposed_at:
        return False
    try:
        proposed_dt = datetime.fromisoformat(proposed_at) if isinstance(proposed_at, str) else proposed_at
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

    proposal = TradeProposal.model_validate(state["order_proposal"])
    card = state.get("proposal_card") or {}
    if _proposal_is_stale(card, proposal.symbol, proposal.entry_price):
        logger.warning("Rejecting stale approval for %s (proposed_at=%s).",
                       proposal.symbol, card.get("proposed_at"))
        return {
            "human_decision": "REJECTED_STALE",
            "execution_details": {"status": "REJECTED_STALE", "reason": "Price moved since proposal; re-run the symbol."},
        }

    assessment_data = state.get("catalyst_assessment")
    assessment = analyst.CatalystAssessment.model_validate(assessment_data) if assessment_data else None
    trade_broker = broker.get_broker(get_settings().TRADING_MODE)
    details = trade_broker.open_trade(
        proposal=proposal,
        rsi=state["rsi"],
        ema_200=state["ema_200"],
        atr=state["atr"],
        thesis=assessment.thesis_rationale if assessment else "",
        human_decision="APPROVED",
        news_headlines=state.get("news_headlines") or [],
        evidence_snapshot_id=state.get("evidence_snapshot_id"),
        strategy_name=state.get("strategy_name"),
        market_regime=state.get("market_regime"),
        catalyst_type=assessment.catalyst_type if assessment else None,
        source_set=state.get("source_set") or [],
        llm_provider=(state.get("llm_metadata") or {}).get("provider"),
        llm_model=(state.get("llm_metadata") or {}).get("model"),
        cache_hits=state.get("cache_hits") or [],
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
    data = state.get("catalyst_assessment")
    assessment = analyst.CatalystAssessment.model_validate(data) if data else None
    if assessment is not None and not assessment.is_temporary_pullback:
        # Structural damage / non-pullback -> reject without a human prompt.
        return "rejected"
    if assessment is not None and assessment.catalyst_type == "GENERAL_MARKET":
        if state.get("market_regime") in {None, "UNASSESSED"}:
            logger.warning(
                "Rejecting %s: GENERAL_MARKET classification has no validated regime evidence.",
                state["symbol"],
            )
            return "rejected"
    return "calculate_risk"


def _rejected(state: TradingState) -> dict:
    """Persist a reason for every terminal rejection."""
    reason = state.get("rejection_reason")
    if reason is None:
        assessment = state.get("catalyst_assessment")
        if assessment and assessment.get("confidence_score") == 0.0:
            reason = "ANALYST_UNAVAILABLE"
        elif assessment and assessment.get("catalyst_type") == "STRUCTURAL_DAMAGE":
            reason = "STRUCTURAL_DAMAGE"
        elif assessment and assessment.get("catalyst_type") == "GENERAL_MARKET":
            reason = "MISSING_MARKET_REGIME_EVIDENCE"
        elif state.get("human_decision") == "REJECTED_RISK":
            reason = "RISK_GATE"
        elif str(state.get("human_decision", "")).startswith("CORPORATE_EVENT_BLACKOUT"):
            reason = "CORPORATE_EVENT_BLACKOUT"
        else:
            reason = "REJECTED"
    return {"rejection_reason": reason, "execution_details": {"status": "REJECTED", "reason": reason}}


def _route_after_risk(state: TradingState) -> str:
    if state.get("human_decision") == "REJECTED_RISK" or str(state.get("human_decision", "")).startswith("CORPORATE_EVENT_BLACKOUT"):
        return "rejected"
    return "human_approval"


def _route_after_approval(state: TradingState) -> str:
    if state.get("human_decision") == "APPROVED":
        return "paper_execute"
    return "rejected"


# --------------------------------------------------------------------------- #
# Graph construction
# --------------------------------------------------------------------------- #
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
    saver = checkpoint.get_checkpointer()
    connection = checkpoint.current_connection()
    if connection is not None:
        connection.executescript(_THREAD_INDEX_SCHEMA)
    return saver


def _record_thread(thread_id: str, symbol: str) -> None:
    """Track active trade threads in our own table instead of checkpoint internals."""
    _get_checkpointer()
    connection = checkpoint.current_connection()
    if connection is None:
        return
    try:
        connection.execute(
            """
            INSERT INTO graph_threads (thread_id, symbol, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(thread_id) DO UPDATE SET
                symbol = excluded.symbol,
                updated_at = excluded.updated_at
            """,
            (thread_id, symbol, datetime.now(timezone.utc).isoformat()),
        )
        connection.commit()
    except Exception as exc:  # noqa: BLE001 - checkpoint index is best effort
        logger.warning("Could not record graph thread %s: %s", thread_id, exc)


def _backfill_thread_index() -> None:
    """Best-effort migration from checkpoint internals to the public thread index."""
    _get_checkpointer()
    connection = checkpoint.current_connection()
    if connection is None:
        return
    try:
        indexed = connection.execute("SELECT COUNT(*) FROM graph_threads").fetchone()
        if indexed and indexed[0]:
            return
        cur = connection.execute(
            "SELECT DISTINCT thread_id FROM checkpoints WHERE thread_id LIKE ?",
            ("trade-%",),
        )
        rows = [row[0] for row in cur.fetchall()]
        if not rows:
            return
        now = datetime.now(timezone.utc).isoformat()
        connection.executemany(
            "INSERT OR IGNORE INTO graph_threads (thread_id, symbol, updated_at) VALUES (?, ?, ?)",
            [(thread_id, thread_id.split("-", 2)[1] if "-" in thread_id else thread_id, now) for thread_id in rows],
        )
        connection.commit()
    except Exception:  # noqa: BLE001 - checkpoint migration is best effort
        return


def _all_thread_ids(prefix: str = "trade-") -> list[str]:
    """Distinct thread ids recorded in the checkpoint DB, matching a prefix.

    Queries the checkpointer's own SQLite connection directly (rather than
    LangGraph's generic `list()` API) so we can filter server-side and avoid
    depending on undocumented listing semantics.
    """
    _backfill_thread_index()
    connection = checkpoint.current_connection()
    if connection is None:
        return []
    try:
        cur = connection.execute(
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
            value = snap.interrupts[0].value
            pending.append(value.model_dump() if isinstance(value, ProposalCard) else dict(value))
    return pending


def symbol_history(symbol: str, limit: Optional[int] = None) -> list[dict]:
    """Full checkpoint (time-travel) history for the most recent thread of a symbol.

    Returns one entry per super-step, newest first, using LangGraph's native
    `get_state_history()` — see
    https://docs.langchain.com/oss/python/langgraph/use-time-travel. Each
    entry summarizes what changed, which node runs next, and whether that
    step paused at a human-approval interrupt. Useful for auditing exactly
    why a symbol was rejected or approved without re-running the pipeline.
    """
    thread_id = latest_thread_id_for(symbol)
    if thread_id is None:
        return []
    g = build_graph()
    config = {"configurable": {"thread_id": thread_id}}
    history = []
    for snapshot in g.get_state_history(config, limit=limit):
        history.append({
            "next": list(snapshot.next),
            "values": {
                key: value for key, value in (snapshot.values or {}).items()
                if key != "news_headlines"
            },
            "created_at": snapshot.created_at,
            "paused_for_approval": bool(snapshot.interrupts),
        })
    return history


def build_graph(checkpointer: Optional[SqliteSaver] = None) -> Any:
    """Compile the trading StateGraph with a SQLite checkpointer and store.

    Parameters
    ----------
    checkpointer:
        Optional pre-built `SqliteSaver`. If omitted, the process-wide saver
        backed by `CHECKPOINT_DB_PATH` is used.

    The compiled graph also carries the shared long-term `SqliteStore`
    (`app.store`) so future nodes/tools can read or write namespaced,
    cross-thread memory (e.g. the operator profile) via LangGraph's native
    store API without introducing a second persistence mechanism.

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
    graph.add_node("rejected", _rejected)

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

    return graph.compile(checkpointer=checkpointer, store=store.get_store())


def _trace_metadata(symbol: str, decision: Optional[str]) -> dict:
    """Structured metadata attached to every LangGraph invocation so traces
    in LangSmith can be filtered/searched by symbol, strategy, and outcome
    (see ADR-021 — these are non-secret tags, never credentials).
    """
    return {
        "symbol": symbol,
        "strategy": get_settings().SETUP_STRATEGY,
        "trader": "nifty100-swing",
        "decision": decision or "pending",
    }


def run_symbol(
    symbol: str,
    news_headlines: Optional[list[str]] = None,
    snapshot: Optional[dict] = None,
    events: Optional[list[corporate_events.CorporateEvent]] = None,
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
        "strategy_name": get_settings().SETUP_STRATEGY,
        "market_regime": "UNASSESSED",
        "corporate_events": [event.model_dump(mode="json") for event in events or []],
    }
    if snapshot is not None:
        initial_state.update({
            "daily_close": snapshot["daily_close"],
            "rsi": snapshot["rsi"],
            "ema_200": snapshot["ema_200"],
            "atr": snapshot["atr"],
        })
        if snapshot.get("cache_hit"):
            initial_state["cache_hits"] = ["technical"]
    items = []
    if all(key in initial_state for key in ("daily_close", "rsi", "ema_200", "atr")):
        items.append(
            evidence.EvidenceItem(
                kind="MARKET",
                symbol=symbol,
                payload={key: initial_state[key] for key in ("daily_close", "rsi", "ema_200", "atr")},
                provenance=evidence.Provenance(source="screener", fetched_at=datetime.now(timezone.utc)),
            )
        )
    items.extend(
        evidence.EvidenceItem(
            kind="NEWS",
            symbol=symbol,
            payload={"headline": headline},
            provenance=evidence.Provenance(source="rss", fetched_at=datetime.now(timezone.utc)),
        )
        for headline in news_headlines or []
    )
    items.extend(corporate_events.to_evidence_items(events or []))
    if items:
        stored_snapshot = evidence.EvidenceSnapshot(symbol=symbol, items=items)
        evidence.validate_snapshot(stored_snapshot)
        snapshot_key = evidence.content_hash(
            [
                {
                    **item.model_dump(mode="json"),
                    "provenance": {
                        key: value
                        for key, value in item.provenance.model_dump(mode="json").items()
                        if key not in {"fetched_at", "freshness_seconds"}
                    },
                }
                for item in stored_snapshot.items
            ]
        )
        cached_snapshot_id = cache.get_value("evidence_snapshot", snapshot_key)
        if cached_snapshot_id:
            cached_snapshot = evidence.load_snapshot(cached_snapshot_id)
            evidence.validate_snapshot(cached_snapshot)
            initial_state["evidence_snapshot_id"] = cached_snapshot_id
            initial_state["cache_hits"] = [*initial_state.get("cache_hits", []), "evidence"]
        else:
            snapshot_id = evidence.save_snapshot(stored_snapshot)
            cache.set_value(
                "evidence_snapshot", snapshot_key, snapshot_id,
                get_settings().EVIDENCE_CACHE_MINUTES,
            )
            initial_state["evidence_snapshot_id"] = snapshot_id
        initial_state["source_set"] = stored_snapshot.source_set
    with observability.span("graph.run_symbol", symbol=symbol):
        # durability="sync": every checkpoint (screener -> catalyst -> risk ->
        # interrupt) is persisted before the next node starts. A paper-trading
        # approval pipeline must survive a process crash mid-run without ever
        # silently losing a proposal or re-running risk math from a stale
        # state. See https://docs.langchain.com/oss/python/langgraph/checkpointers#durability-modes.
        return graph.invoke(
            initial_state, config,
            durability="sync",
            metadata=_trace_metadata(symbol, decision=None),
        )


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
        return graph.invoke(
            Command(resume=decision), config,
            durability="sync",
            metadata=_trace_metadata(symbol, decision=decision),
        )
