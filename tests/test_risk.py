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
