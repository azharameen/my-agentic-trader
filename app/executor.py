"""
Execution & audit layer.

Handles:
  * SQLite schema initialization for `data/trading_audit.db` (auto-created on
    boot if missing).
  * Paper-trading fill simulation with realistic slippage (0.05%).
  * Appending every decision state to the `trade_audit_log` table for
    post-mortem analysis.

In `PAPER_TRADING` mode fills are simulated locally. In `LIVE` mode this module
refuses to route orders until a real broker adapter is wired in (the mission
requires broker execution to be mocked until proven).
"""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.risk import calculate_delivery_costs
from app.state import TradeProposal
from config.settings import get_settings

logger = logging.getLogger(__name__)

# Realistic slippage applied to paper fills (0.05%).
SLIPPAGE_PCT = 0.0005

_SCHEMA = """
CREATE TABLE IF NOT EXISTS trade_audit_log (
    trade_id        TEXT PRIMARY KEY,
    timestamp       TEXT NOT NULL,
    symbol          TEXT NOT NULL,
    entry_price     REAL NOT NULL,
    soft_stop       REAL NOT NULL,
    hard_stop       REAL NOT NULL,
    target_price    REAL NOT NULL,
    quantity        INTEGER NOT NULL,
    rsi             REAL,
    ema_200         REAL,
    atr             REAL,
    thesis          TEXT,
    headlines_used  TEXT,
    human_decision  TEXT,
    fill_price      REAL,
    status          TEXT NOT NULL DEFAULT 'OPEN_PAPER',
    exit_price      REAL,
    realized_pnl    REAL,
    gross_pnl       REAL,
    transaction_costs TEXT,
    evidence_snapshot_id TEXT,
    strategy_name   TEXT,
    market_regime   TEXT,
    catalyst_type   TEXT,
    source_set      TEXT,
    llm_provider    TEXT,
    llm_model       TEXT,
    cache_hits      TEXT,
    mistake_category TEXT
);
"""


def _ensure_column(conn: sqlite3.Connection, column: str, ddl_type: str) -> None:
    """Add a column to trade_audit_log if it's missing (for pre-existing DBs)."""
    existing = {row[1] for row in conn.execute("PRAGMA table_info(trade_audit_log)").fetchall()}
    if column not in existing:
        conn.execute(f"ALTER TABLE trade_audit_log ADD COLUMN {column} {ddl_type}")


def _db_path() -> Path:
    """Resolve the audit DB path and ensure its parent directory exists."""
    settings = get_settings()
    path = Path(settings.DATABASE_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def init_db() -> None:
    """Create the audit schema if it does not already exist.

    Safe to call repeatedly (idempotent). Called on application boot.
    """
    path = _db_path()
    with sqlite3.connect(path) as conn:
        conn.executescript(_SCHEMA)
    _ensure_column(conn, "headlines_used", "TEXT")
    _ensure_column(conn, "gross_pnl", "REAL")
    _ensure_column(conn, "transaction_costs", "TEXT")
    _ensure_column(conn, "evidence_snapshot_id", "TEXT")
    _ensure_column(conn, "strategy_name", "TEXT")
    _ensure_column(conn, "market_regime", "TEXT")
    _ensure_column(conn, "catalyst_type", "TEXT")
    _ensure_column(conn, "source_set", "TEXT")
    _ensure_column(conn, "llm_provider", "TEXT")
    _ensure_column(conn, "llm_model", "TEXT")
    _ensure_column(conn, "cache_hits", "TEXT")
    from app import outbox

    outbox.init_db()
    from app import cache
    cache.init_db()
    from app import evidence
    evidence.init_db()
    logger.info("Audit database ready at %s", path)


def get_current_capital() -> float:
    """Configured base capital plus realized P&L from closed paper trades.

    Used for position sizing so `RISK_PER_TRADE_PCT` tracks actual equity as
    it accrues, instead of always sizing off the static config baseline.
    """
    settings = get_settings()
    with sqlite3.connect(_db_path()) as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(realized_pnl), 0) FROM trade_audit_log WHERE status = 'CLOSED'"
        ).fetchone()
    realized = row[0] if row else 0.0
    return settings.PORTFOLIO_CAPITAL + realized


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_open_trade(
    proposal: TradeProposal,
    rsi: float,
    ema_200: float,
    atr: float,
    thesis: str,
    human_decision: str,
    news_headlines: Optional[list[str]] = None,
    evidence_snapshot_id: Optional[str] = None,
    strategy_name: Optional[str] = None,
    market_regime: Optional[str] = None,
    catalyst_type: Optional[str] = None,
    source_set: Optional[list[str]] = None,
    llm_provider: Optional[str] = None,
    llm_model: Optional[str] = None,
    cache_hits: Optional[list[str]] = None,
) -> dict:
    """Simulate a paper fill and persist an OPEN_PAPER trade row.

    The fill price applies slippage against the entry (buys fill slightly
    higher than the quoted entry). Returns the full record dict including the
    generated `trade_id` and `fill_price`.
    """
    settings = get_settings()
    if settings.TRADING_MODE == "LIVE":
        raise RuntimeError(
            "LIVE order routing is not implemented. Set TRADING_MODE=PAPER_TRADING."
        )

    trade_id = uuid.uuid4().hex
    fill_price = round(proposal.entry_price * (1.0 + SLIPPAGE_PCT), 2)
    headlines_json = json.dumps(news_headlines or [])

    with sqlite3.connect(_db_path()) as conn:
        conn.execute(
            """
            INSERT INTO trade_audit_log (
                trade_id, timestamp, symbol, entry_price, soft_stop, hard_stop,
                target_price, quantity, rsi, ema_200, atr, thesis, headlines_used,
                human_decision, fill_price, status
                , evidence_snapshot_id, strategy_name, market_regime, catalyst_type, source_set,
                llm_provider, llm_model, cache_hits
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trade_id,
                _now_iso(),
                proposal.symbol,
                proposal.entry_price,
                proposal.soft_stop,
                proposal.hard_stop,
                proposal.target_price,
                proposal.quantity,
                rsi,
                ema_200,
                atr,
                thesis,
                headlines_json,
                human_decision,
                fill_price,
                "OPEN_PAPER",
                evidence_snapshot_id,
                strategy_name,
                market_regime,
                catalyst_type,
                json.dumps(source_set or []),
                llm_provider,
                llm_model,
                json.dumps(cache_hits or []),
            ),
        )
        conn.commit()

    logger.info(
        "PAPER FILL %s %s qty=%d fill=%.2f (slippage %.4f%%)",
        trade_id, proposal.symbol, proposal.quantity, fill_price, SLIPPAGE_PCT * 100,
    )
    return {
        "trade_id": trade_id,
        "symbol": proposal.symbol,
        "fill_price": fill_price,
        "quantity": proposal.quantity,
        "status": "OPEN_PAPER",
        "slippage_pct": SLIPPAGE_PCT * 100,
    }


def close_trade(
    trade_id: str,
    exit_price: float,
    mistake_category: Optional[str] = None,
) -> dict:
    """Close an open paper trade, computing realized P&L.

    Realized P&L = (exit_price - fill_price) * quantity. The row is updated to
    `CLOSED`. Returns the updated record.
    """
    with sqlite3.connect(_db_path()) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT status, fill_price, quantity, exit_price, realized_pnl FROM trade_audit_log WHERE trade_id = ?",
            (trade_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"Unknown trade_id: {trade_id}")

        if row["status"] == "CLOSED":
            return {
                "trade_id": trade_id,
                "exit_price": row["exit_price"],
                "realized_pnl": row["realized_pnl"],
                "status": "CLOSED",
            }

        fill_price = row["fill_price"]
        quantity = row["quantity"]
        gross_pnl = round((exit_price - fill_price) * quantity, 2)
        costs = calculate_delivery_costs(
            buy_value=fill_price * quantity,
            sell_value=exit_price * quantity,
        )
        realized_pnl = round(gross_pnl - costs.total, 2)

        conn.execute(
            """
            UPDATE trade_audit_log
            SET status = 'CLOSED', exit_price = ?, realized_pnl = ?,
                gross_pnl = ?, transaction_costs = ?, mistake_category = ?
            WHERE trade_id = ?
            """,
            (exit_price, realized_pnl, gross_pnl, costs.model_dump_json(), mistake_category, trade_id),
        )
        conn.commit()

    logger.info(
        "CLOSED %s exit=%.2f pnl=%.2f mistake=%s",
        trade_id, exit_price, realized_pnl, mistake_category,
    )
    return {
        "trade_id": trade_id,
        "exit_price": exit_price,
        "realized_pnl": realized_pnl,
        "gross_pnl": gross_pnl,
        "transaction_costs": costs.model_dump(),
        "status": "CLOSED",
    }


def fetch_all_trades() -> list[dict]:
    """Return every audit row as a list of dicts (for the dashboard)."""
    with sqlite3.connect(_db_path()) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM trade_audit_log ORDER BY timestamp DESC"
        ).fetchall()
        return [dict(r) for r in rows]
