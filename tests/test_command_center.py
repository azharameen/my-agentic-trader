"""Unit tests for app.command_center: manual stock/F&O/mutual-fund CRUD and the
aggregated Command Center overview (holdings + signals + suggestions).
"""

from __future__ import annotations

import pytest

from app import command_center, db, groww_client


class _FakeGrowwClient:
    """Deterministic stand-in for GrowwClient — no live network calls."""

    def is_configured(self) -> bool:
        return False

    def get_holdings(self):
        return []

    def get_ltp(self, symbols):
        return {}

    def get_user_margin(self):
        raise AssertionError("get_user_margin should not be called when not configured")


@pytest.fixture(autouse=True)
def _fake_groww(monkeypatch):
    monkeypatch.setattr(groww_client, "get_groww_client", lambda: _FakeGrowwClient())


def test_manual_stock_lifecycle():
    position_id = command_center.add_manual_stock(
        user_id="test_user",
        symbol="RELIANCE",
        shares=10,
        entry_price=2500.0,
    )
    row = db.fetchone("SELECT * FROM user_positions WHERE position_id = %s;", (position_id,))
    assert row is not None
    assert row["source"] == "MANUAL"
    assert row["symbol"] == "RELIANCE"
    # Default risk envelope applied when stop/target omitted.
    assert row["stop_loss_price"] < row["entry_price"]
    assert row["target_price"] > row["entry_price"]

    command_center.update_manual_stock(position_id, shares=15, entry_price=2600.0)
    updated = db.fetchone("SELECT * FROM user_positions WHERE position_id = %s;", (position_id,))
    assert updated["shares"] == 15
    assert updated["entry_price"] == 2600.0

    command_center.delete_manual_stock(position_id)
    assert (
        db.fetchone("SELECT * FROM user_positions WHERE position_id = %s;", (position_id,)) is None
    )


def test_manual_fno_lifecycle():
    position_id = command_center.add_fno_position(
        user_id="test_user",
        symbol="NIFTY",
        instrument_type="CE",
        quantity=2,
        entry_price=150.0,
        lot_size=50,
        strike_price=22000,
        expiry_date="2026-01-29",
    )
    row = db.fetchone("SELECT * FROM user_fno_positions WHERE position_id = %s;", (position_id,))
    assert row is not None
    assert row["instrument_type"] == "CE"
    assert row["lot_size"] == 50

    command_center.update_fno_position(position_id, current_price=180.0)
    updated = db.fetchone(
        "SELECT * FROM user_fno_positions WHERE position_id = %s;", (position_id,)
    )
    assert updated["current_price"] == 180.0

    command_center.delete_fno_position(position_id)
    assert (
        db.fetchone("SELECT * FROM user_fno_positions WHERE position_id = %s;", (position_id,))
        is None
    )


def test_manual_mutual_fund_lifecycle():
    folio_id = command_center.add_mutual_fund(
        user_id="test_user",
        scheme_name="Test Flexi Cap Fund",
        units=100.0,
        nav=50.0,
        invested_amount=4500.0,
    )
    row = db.fetchone("SELECT * FROM user_mutual_funds WHERE folio_id = %s;", (folio_id,))
    assert row is not None
    assert row["current_value"] == 5000.0
    assert row["pnl"] == pytest.approx(500.0)

    command_center.update_mutual_fund(folio_id, nav=45.0)
    updated = db.fetchone("SELECT * FROM user_mutual_funds WHERE folio_id = %s;", (folio_id,))
    assert updated["current_value"] == 4500.0
    assert updated["pnl"] == pytest.approx(0.0)

    command_center.delete_mutual_fund(folio_id)
    assert db.fetchone("SELECT * FROM user_mutual_funds WHERE folio_id = %s;", (folio_id,)) is None


def test_overview_aggregates_manual_holdings_and_totals(monkeypatch):
    monkeypatch.setattr(command_center.screener, "get_symbol_snapshot", lambda symbol: None)
    command_center.add_manual_stock(
        user_id="test_user",
        symbol="TCS",
        shares=5,
        entry_price=3000.0,
        stop_loss_price=2800.0,
        target_price=3300.0,
    )
    command_center.add_mutual_fund(
        user_id="test_user",
        scheme_name="Test Index Fund",
        units=10.0,
        nav=200.0,
        invested_amount=1800.0,
    )

    overview = command_center.get_overview(user_id="test_user")

    assert overview["groww_connected"] is False
    assert len(overview["stocks"]) == 1
    stock = overview["stocks"][0]
    assert stock["symbol"] == "TCS"
    assert stock["source"] == "MANUAL"
    assert stock["signal"]["action"] == "HOLD"  # price == entry, no snapshot available

    assert len(overview["mutual_funds"]) == 1
    totals = overview["totals"]
    # invested = 5*3000 (stock) + 1800 (MF) = 16800; current = same (no live price movement mocked)
    assert totals["capital_invested"] == pytest.approx(16800.0)
    assert totals["unrealized_earnings"] == pytest.approx(200.0)
    assert totals["realized_earnings"] == pytest.approx(0.0)
    assert totals["total_earnings"] == pytest.approx(200.0)
    assert totals["cash_available"] == 0.0


def test_overview_exposes_stock_provenance_and_plan_status(monkeypatch):
    monkeypatch.setattr(command_center.screener, "get_symbol_snapshot", lambda symbol: None)
    command_center.add_manual_stock(
        user_id="test_user",
        symbol="INFY",
        shares=2,
        entry_price=1500.0,
    )

    overview = command_center.get_overview(user_id="test_user")

    stock = overview["stocks"][0]
    assert stock["investment_source"] == "MANUAL"
    assert stock["plan_status"] == "NONE"
    assert stock["status"] == "ACTIVE"


def test_overview_includes_groww_synced_rows(monkeypatch):
    monkeypatch.setattr(command_center.screener, "get_symbol_snapshot", lambda symbol: None)
    db.execute(
        "INSERT INTO user_portfolios (portfolio_id, user_id, created_at, initial_capital, allocated_capital, cash_balance, risk_vibe, status) "
        "VALUES (%s, %s, %s, 0, 0, 0, 'BALANCED', 'ACTIVE')",
        ("groww-sync-test_user", "test_user", "2026-09-24T00:00:00+00:00"),
    )
    db.execute(
        "INSERT INTO user_positions (position_id, portfolio_id, user_id, symbol, shares, suggested_price, entry_price, "
        "target_price, stop_loss_price, status, created_at, source, synced_current_price, synced_invested_amount, synced_current_value) "
        "VALUES (%s, %s, %s, %s, 3, 100, 100, 108, 94, 'ACTIVE', %s, 'GROWW_SYNC', 110, 300, 330)",
        ("groww-test", "groww-sync-test_user", "test_user", "INFY", "2026-09-24T00:00:00+00:00"),
    )

    overview = command_center.get_overview("test_user")

    assert [stock["symbol"] for stock in overview["stocks"]] == ["INFY"]
    assert overview["totals"]["current_value"] == 330


def test_signal_sell_when_stop_breached():
    signal = command_center._compute_signal(
        current_price=90.0,
        entry_price=100.0,
        stop_loss_price=95.0,
        target_price=120.0,
        symbol="XYZ",
    )
    assert signal["action"] == "SELL"


def test_signal_trim_when_target_reached():
    signal = command_center._compute_signal(
        current_price=125.0,
        entry_price=100.0,
        stop_loss_price=90.0,
        target_price=120.0,
        symbol="XYZ",
    )
    assert signal["action"] == "TRIM"


def test_signal_includes_analytics_payload(monkeypatch):
    monkeypatch.setattr(command_center.screener, "get_symbol_snapshot", lambda symbol: None)
    signal = command_center._compute_signal(
        current_price=100.0,
        entry_price=100.0,
        stop_loss_price=90.0,
        target_price=120.0,
        symbol="XYZ",
    )
    assert "analytics" in signal
    assert signal["analytics"]["qualifies"] is False
    assert signal["analytics"]["secondary_strategies"] == []


def test_deep_dive_returns_none_for_symbol_never_analyzed():
    assert command_center.get_deep_dive("NEVERRUN") is None


def test_basket_confirmed_positions_are_tagged_and_surfaced(monkeypatch):
    """Positions confirmed via the Smart Investment Plan flow (portfolio_manager)
    must land with source='BASKET' and show up in the unified Command Center
    stocks list — not just Groww-synced or explicitly-manual entries."""
    from app.basket_generator import generate_strategy_basket
    from app.models_basket import BatchExecutionRequest, ExecutionConfirmationItem, RiskVibe
    from app.portfolio_manager import confirm_batch_execution, create_user_portfolio_from_basket

    monkeypatch.setattr(command_center.screener, "get_symbol_snapshot", lambda symbol: None)

    basket = generate_strategy_basket(capital=60000.0, risk_vibe=RiskVibe.BALANCED, max_stocks=2)
    portfolio_id = create_user_portfolio_from_basket(basket, user_id="test_user")
    confirm_batch_execution(
        BatchExecutionRequest(
            basket_id=portfolio_id,
            user_id="test_user",
            confirmations=[
                ExecutionConfirmationItem(
                    symbol=a.symbol,
                    shares=a.shares,
                    executed_price=a.suggested_entry_price,
                    broker_name="Zerodha",
                )
                for a in basket.allocations
            ],
        )
    )

    rows = db.fetchall("SELECT * FROM user_positions WHERE portfolio_id = %s;", (portfolio_id,))
    assert all(r["source"] == "BASKET" for r in rows)

    overview = command_center.get_overview(user_id="test_user")
    symbols_in_overview = {s["symbol"] for s in overview["stocks"]}
    assert symbols_in_overview == {a.symbol for a in basket.allocations}
    assert all(s["source"] == "BASKET" and s["editable"] is False for s in overview["stocks"])
