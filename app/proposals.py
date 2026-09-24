"""Proposal management and lifecycle operations for TrAId Web Application.

Persists generated trade proposals awaiting human approval into PostgreSQL,
enforces atomic state transitions (PENDING -> APPROVED / REJECTED / EXPIRED),
and coordinates execution with LangGraph and the audit database.
"""

from __future__ import annotations

import json
import logging
from threading import Lock
from datetime import datetime, timezone
from typing import Any, Optional

from app import db, events, graph

logger = logging.getLogger(__name__)
_proposals_table_initialized = False
_proposals_table_lock = Lock()


def init_proposals_table() -> None:
    """Create the pending_proposals table and indexes if not existing."""
    global _proposals_table_initialized
    if _proposals_table_initialized:
        return
    with _proposals_table_lock:
        if _proposals_table_initialized:
            return
        ddl = """
        CREATE TABLE IF NOT EXISTS pending_proposals (
            proposal_id     TEXT PRIMARY KEY,
            symbol          TEXT NOT NULL,
            strategy_name   TEXT NOT NULL,
            entry_price     DOUBLE PRECISION NOT NULL,
            soft_stop       DOUBLE PRECISION NOT NULL,
            hard_stop       DOUBLE PRECISION NOT NULL,
            target_price    DOUBLE PRECISION NOT NULL,
            quantity        INTEGER NOT NULL,
            risk_amount     DOUBLE PRECISION NOT NULL,
            risk_to_reward  DOUBLE PRECISION NOT NULL,
            thesis          TEXT,
            catalyst_type   TEXT,
            margin_required DOUBLE PRECISION,
            margin_available DOUBLE PRECISION,
            raw_card        TEXT NOT NULL,
            created_at      TEXT NOT NULL,
            status          TEXT NOT NULL DEFAULT 'PENDING',
            decided_at      TEXT,
            decision_notes  TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_proposals_status ON pending_proposals(status);
        CREATE INDEX IF NOT EXISTS idx_proposals_symbol ON pending_proposals(symbol);
        CREATE INDEX IF NOT EXISTS idx_proposals_created ON pending_proposals(created_at DESC);
        """
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(ddl)
            # ADR-036: informational Groww margin fields added after initial release.
            cursor.execute(
                "ALTER TABLE pending_proposals ADD COLUMN IF NOT EXISTS margin_required DOUBLE PRECISION;"
            )
            cursor.execute(
                "ALTER TABLE pending_proposals ADD COLUMN IF NOT EXISTS margin_available DOUBLE PRECISION;"
            )
        _proposals_table_initialized = True


def record_proposal(card_data: dict[str, Any], strategy_name: str = "PULLBACK") -> str:
    """Insert or update a trade proposal card into the database."""
    init_proposals_table()
    symbol = card_data["symbol"]
    now_iso = datetime.now(timezone.utc).isoformat()
    proposal_id = f"prop-{symbol}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

    query = """
    INSERT INTO pending_proposals (
        proposal_id, symbol, strategy_name, entry_price, soft_stop, hard_stop,
        target_price, quantity, risk_amount, risk_to_reward, thesis, catalyst_type,
        margin_required, margin_available, raw_card, created_at, status
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'PENDING')
    """
    params = (
        proposal_id,
        symbol,
        strategy_name,
        float(card_data.get("entry_price", 0.0)),
        float(card_data.get("soft_stop", 0.0)),
        float(card_data.get("hard_stop", 0.0)),
        float(card_data.get("target_price", 0.0)),
        int(card_data.get("quantity", 0)),
        float(card_data.get("risk_amount", 0.0)),
        float(card_data.get("risk_to_reward", 0.0)),
        card_data.get("thesis", ""),
        card_data.get("catalyst_type", "UNKNOWN"),
        card_data.get("margin_required"),
        card_data.get("margin_available"),
        json.dumps(card_data),
        now_iso,
    )
    db.execute(query, params)
    logger.info("Recorded pending proposal %s for symbol %s", proposal_id, symbol)

    # Broadcast event to connected Web clients
    events.broadcast_event(
        "PROPOSAL_CREATED",
        {
            "proposal_id": proposal_id,
            "symbol": symbol,
            "strategy": strategy_name,
            "entry_price": card_data.get("entry_price"),
            "target_price": card_data.get("target_price"),
            "hard_stop": card_data.get("hard_stop"),
            "risk_to_reward": card_data.get("risk_to_reward"),
        },
    )
    return proposal_id


def fetch_pending_proposals() -> list[dict[str, Any]]:
    """Retrieve all trade proposals currently awaiting human approval."""
    init_proposals_table()
    query = """
    SELECT * FROM pending_proposals
    WHERE status = 'PENDING'
    ORDER BY created_at DESC
    """
    rows = db.fetchall(query)
    proposals = []
    for r in rows:
        debate = graph.get_symbol_debate(r["symbol"])
        proposals.append(
            {
                "proposal_id": r["proposal_id"],
                "symbol": r["symbol"],
                "strategy_name": r["strategy_name"],
                "entry_price": r["entry_price"],
                "soft_stop": r["soft_stop"],
                "hard_stop": r["hard_stop"],
                "target_price": r["target_price"],
                "quantity": r["quantity"],
                "risk_amount": r["risk_amount"],
                "risk_to_reward": r["risk_to_reward"],
                "thesis": r["thesis"],
                "catalyst_type": r["catalyst_type"],
                "margin_required": r.get("margin_required"),
                "margin_available": r.get("margin_available"),
                "created_at": r["created_at"],
                "status": r["status"],
                "debate": debate,
            }
        )
    return proposals


def fetch_proposal_by_id(proposal_id: str) -> Optional[dict[str, Any]]:
    """Fetch details of a specific proposal by its ID."""
    init_proposals_table()
    query = "SELECT * FROM pending_proposals WHERE proposal_id = %s"
    row = db.fetchone(query, (proposal_id,))
    if not row:
        return None
    row["debate"] = graph.get_symbol_debate(row["symbol"])
    return row


def approve_proposal(proposal_id: str, notes: str = "Approved via Web Cockpit") -> dict[str, Any]:
    """Atomically approve a proposal and resume execution in LangGraph."""
    init_proposals_table()
    row = fetch_proposal_by_id(proposal_id)
    if not row:
        raise ValueError(f"Proposal {proposal_id} not found.")
    if row["status"] != "PENDING":
        raise ValueError(f"Proposal {proposal_id} is already in {row['status']} status.")

    symbol = row["symbol"]
    now_iso = datetime.now(timezone.utc).isoformat()

    # Atomically mark as APPROVED
    update_query = """
    UPDATE pending_proposals
    SET status = 'APPROVED', decided_at = %s, decision_notes = %s
    WHERE proposal_id = %s AND status = 'PENDING'
    """
    db.execute(update_query, (now_iso, notes, proposal_id))

    # Resume graph execution to perform paper execution
    logger.info("Resuming symbol %s with APPROVED decision", symbol)
    result = graph.resume_symbol(symbol, "APPROVED")

    events.broadcast_event(
        "PROPOSAL_DECIDED",
        {"proposal_id": proposal_id, "symbol": symbol, "decision": "APPROVED"},
    )
    return {"status": "APPROVED", "symbol": symbol, "result": result}


def reject_proposal(proposal_id: str, reason: str = "Rejected by operator") -> dict[str, Any]:
    """Atomically reject a proposal and update thread status."""
    init_proposals_table()
    row = fetch_proposal_by_id(proposal_id)
    if not row:
        raise ValueError(f"Proposal {proposal_id} not found.")
    if row["status"] != "PENDING":
        raise ValueError(f"Proposal {proposal_id} is already in {row['status']} status.")

    symbol = row["symbol"]
    now_iso = datetime.now(timezone.utc).isoformat()

    update_query = """
    UPDATE pending_proposals
    SET status = 'REJECTED', decided_at = %s, decision_notes = %s
    WHERE proposal_id = %s AND status = 'PENDING'
    """
    db.execute(update_query, (now_iso, reason, proposal_id))

    logger.info("Resuming symbol %s with REJECTED decision", symbol)
    result = graph.resume_symbol(symbol, "REJECTED")

    events.broadcast_event(
        "PROPOSAL_DECIDED",
        {"proposal_id": proposal_id, "symbol": symbol, "decision": "REJECTED", "reason": reason},
    )
    return {"status": "REJECTED", "symbol": symbol, "result": result}
