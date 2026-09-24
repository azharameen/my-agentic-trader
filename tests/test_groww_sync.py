"""Regression tests for database-backed Groww synchronization and deduplication."""

from __future__ import annotations

from app import db, groww_client, groww_sync


class _FakeGrowwClient:
    def __init__(self, holding: groww_client.GrowwHolding, use_positions: bool = False) -> None:
        self.holding = holding
        self.use_positions = use_positions
        self.portfolio_access_error = ""

    def get_holdings(self) -> list[groww_client.GrowwHolding]:
        return [] if self.use_positions else [self.holding]

    def get_positions(self) -> list[groww_client.GrowwPosition]:
        return [
            groww_client.GrowwPosition(
                symbol=self.holding.symbol,
                quantity=self.holding.quantity,
                buy_price=self.holding.avg_price,
                current_price=self.holding.current_price,
                pnl=self.holding.pnl,
            )
        ]


def test_groww_sync_merges_planned_position_without_duplicate(monkeypatch):
    db.init_all_tables()
    db.execute(
        """
        INSERT INTO user_portfolios (
            portfolio_id, user_id, created_at, initial_capital,
            allocated_capital, cash_balance, risk_vibe, status
        ) VALUES (%s, %s, %s, 0, 0, 0, 'BALANCED', 'ACTIVE');
        """,
        ("plan-test_user", "test_user", "2026-09-24T00:00:00+00:00"),
    )
    db.execute(
        """
        INSERT INTO user_positions (
            position_id, portfolio_id, user_id, symbol, shares,
            suggested_price, entry_price, target_price, stop_loss_price,
            status, created_at, source
        ) VALUES (%s, %s, %s, %s, 2, 100, 100, 108, 94, 'ACTIVE', %s, 'BASKET');
        """,
        (
            "planned-infy",
            "plan-test_user",
            "test_user",
            "INFY",
            "2026-09-24T00:00:00+00:00",
        ),
    )
    fake = _FakeGrowwClient(
        groww_client.GrowwHolding(
            symbol="INFY",
            company_name="Infosys Limited",
            isin="INE009A01021",
            quantity=3,
            avg_price=1200,
            current_price=1250,
            invested_amount=3600,
            current_value=3750,
            pnl=150,
            pnl_pct=4.17,
        )
    )

    result = groww_sync._sync_holdings(fake, user_id="test_user", synced_at="2026-09-24T01:00:00+00:00")

    assert result["updated_count"] == 1
    rows = db.fetchall(
        "SELECT * FROM user_positions WHERE user_id = %s AND symbol = %s AND status = 'ACTIVE';",
        ("test_user", "INFY"),
    )
    assert len(rows) == 1
    row = rows[0]
    assert row["position_id"] == "planned-infy"
    assert row["source"] == "GROWW_SYNC"
    assert row["investment_source"] == "PLANNED_THEN_GROWW"
    assert row["plan_status"] == "BOUGHT"
    assert row["company_name"] == "Infosys Limited"
    assert row["isin"] == "INE009A01021"
    assert row["synced_pnl"] == 150


def test_groww_sync_uses_cash_positions_when_holdings_are_denied(monkeypatch):
    db.init_all_tables()
    fake = _FakeGrowwClient(
        groww_client.GrowwHolding(
            symbol="TCS",
            quantity=4,
            avg_price=3000,
            current_price=3100,
            pnl=400,
        ),
        use_positions=True,
    )

    result = groww_sync._sync_holdings(fake, user_id="test_user", synced_at="2026-09-24T01:00:00+00:00")

    assert result["holdings_found"] == 1
    row = db.fetchone(
        "SELECT * FROM user_positions WHERE user_id = %s AND symbol = %s AND status = 'ACTIVE';",
        ("test_user", "TCS"),
    )
    assert row is not None
    assert row["shares"] == 4
    assert row["synced_current_value"] == 12400
