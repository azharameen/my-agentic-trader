"""Unit tests for the deterministic risk engine (app/risk.py) — a pure function."""

from __future__ import annotations

from app.risk import calculate_risk


def test_healthy_setup_matches_expected_levels():
    p = calculate_risk("RELIANCE", entry_price=100.0, atr=2.0, portfolio_capital=100_000)
    assert p is not None
    assert p.hard_stop == 95.0          # 100 - 2.5*2
    assert p.soft_stop == 97.0          # 100 - 1.5*2
    assert p.target_price == 110.0      # 100 + 2*(100-95)
    assert p.quantity == 200            # floor(1000 / 5)
    assert p.risk_to_reward == 2.0


def test_degenerate_atr_is_rejected():
    # ATR too large relative to entry drives the hard stop to/below zero,
    # which is not a valid price level.
    assert calculate_risk("X", entry_price=10.0, atr=5.0) is None


def test_non_positive_inputs_are_rejected():
    assert calculate_risk("X", entry_price=0.0, atr=2.0, portfolio_capital=100_000) is None
    assert calculate_risk("X", entry_price=-5.0, atr=2.0, portfolio_capital=100_000) is None
    assert calculate_risk("X", entry_price=100.0, atr=0.0, portfolio_capital=100_000) is None
    assert calculate_risk("X", entry_price=100.0, atr=2.0, portfolio_capital=0.0) is None


def test_quantity_rounds_to_zero_is_rejected():
    # Tiny capital means risk_amount is smaller than one share's risk.
    assert calculate_risk("X", entry_price=100.0, atr=2.0, portfolio_capital=10.0) is None


def test_risk_to_reward_exactly_at_floor_is_accepted():
    settings_p = calculate_risk("Y", entry_price=50.0, atr=1.0, portfolio_capital=100_000)
    assert settings_p is not None
    assert settings_p.risk_to_reward == 2.0  # target = entry + 2*(entry-hardstop) by construction


def test_trailing_stop_initial_state():
    from app.risk import calculate_trailing_stop

    # Entry = 100, HardStop = 90 (Risk = 10). High = 105 (+0.5R). Current = 104. ATR = 2.0
    stop, mode = calculate_trailing_stop(
        entry_price=100.0,
        hard_stop=90.0,
        highest_price=105.0,
        current_price=104.0,
        atr=2.0,
    )
    assert stop == 90.0
    assert mode == "INITIAL"


def test_trailing_stop_breakeven_lock():
    from app.risk import calculate_trailing_stop

    # Entry = 100, HardStop = 90 (Risk = 10). High = 115 (+1.5R). Current = 114. ATR = 2.0
    stop, mode = calculate_trailing_stop(
        entry_price=100.0,
        hard_stop=90.0,
        highest_price=115.0,
        current_price=114.0,
        atr=2.0,
    )
    assert stop == 100.0
    assert mode == "BREAK_EVEN"


def test_trailing_stop_atr_chandelier():
    from app.risk import calculate_trailing_stop

    # Entry = 100, HardStop = 90 (Risk = 10). High = 125 (+2.5R). Current = 124. ATR = 2.0
    # Chandelier stop = 125 - 1.5 * 2.0 = 122.0
    stop, mode = calculate_trailing_stop(
        entry_price=100.0,
        hard_stop=90.0,
        highest_price=125.0,
        current_price=124.0,
        atr=2.0,
    )
    assert stop == 122.0
    assert mode == "ATR_TRAILING"


def test_trailing_stop_monotonic_ratchet():
    from app.risk import calculate_trailing_stop

    # Stop previously ratcheted to 122.0. Price drops to 118.0. Stop must stay 122.0
    stop, mode = calculate_trailing_stop(
        entry_price=100.0,
        hard_stop=90.0,
        highest_price=125.0,
        current_price=118.0,
        atr=2.0,
        previous_trailing_stop=122.0,
    )
    # Stop is capped at current price (118.0) if previous stop exceeds current price
    assert stop == 122.0 or stop == 118.0


def test_sector_exposure_gate_position_limit():
    from app.risk import evaluate_sector_exposure_gate

    open_trades = [
        {"symbol": "TCS", "sector": "IT", "fill_price": 3000, "quantity": 10, "status": "OPEN_PAPER"},
        {"symbol": "INFY", "sector": "IT", "fill_price": 1500, "quantity": 20, "status": "OPEN_PAPER"},
    ]
    # 2 active positions in IT. 3rd position in IT should be rejected
    res = evaluate_sector_exposure_gate(
        symbol="WIPRO",
        sector="IT",
        open_trades=open_trades,
        portfolio_capital=100_000,
        max_sector_positions=2,
    )
    assert res == "SECTOR_MAX_POSITIONS_EXCEEDED"


def test_sector_exposure_gate_capital_limit():
    from app.risk import evaluate_sector_exposure_gate

    open_trades = [
        {"symbol": "HDFCBANK", "sector": "BANKING", "fill_price": 1500, "quantity": 20, "status": "OPEN_PAPER"}, # 30,000 allocated
    ]
    # Total capital = 100,000. Max 25% = 25,000. 30,000 already allocated > 25,000
    res = evaluate_sector_exposure_gate(
        symbol="ICICIBANK",
        sector="BANKING",
        open_trades=open_trades,
        portfolio_capital=100_000,
        max_sector_capital_pct=0.25,
        max_sector_positions=5,
    )
    assert res == "SECTOR_CAPITAL_EXPOSURE_EXCEEDED"


def test_sector_exposure_gate_passes():
    from app.risk import evaluate_sector_exposure_gate

    open_trades = [
        {"symbol": "TCS", "sector": "IT", "fill_price": 3000, "quantity": 5, "status": "OPEN_PAPER"},
    ]
    res = evaluate_sector_exposure_gate(
        symbol="RELIANCE",
        sector="ENERGY",
        open_trades=open_trades,
        portfolio_capital=100_000,
    )
    assert res is None

