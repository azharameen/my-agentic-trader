import pytest
from app.basket_generator import generate_strategy_basket
from app.models_basket import RiskVibe


def test_generate_basket_balanced_sizing():
    capital = 100000.0
    basket = generate_strategy_basket(capital=capital, risk_vibe=RiskVibe.BALANCED, max_stocks=4)

    assert basket.total_capital == 100000.0
    assert basket.allocated_capital <= basket.total_capital
    assert basket.cash_reserve >= 0.0
    assert abs((basket.allocated_capital + basket.cash_reserve) - basket.total_capital) < 1.0
    assert len(basket.allocations) >= 1

    for alloc in basket.allocations:
        assert alloc.shares >= 1
        assert alloc.suggested_entry_price > 0
        assert alloc.target_price > alloc.suggested_entry_price
        assert alloc.stop_loss_price < alloc.suggested_entry_price
        assert alloc.expected_gain_pct > 0
        assert alloc.max_risk_pct > 0
        assert len(alloc.layman_rationale) > 10


def test_generate_basket_conservative_vs_momentum():
    capital = 50000.0
    cons_basket = generate_strategy_basket(capital=capital, risk_vibe=RiskVibe.CONSERVATIVE, max_stocks=3)
    mom_basket = generate_strategy_basket(capital=capital, risk_vibe=RiskVibe.MOMENTUM, max_stocks=3)

    assert cons_basket.risk_vibe == RiskVibe.CONSERVATIVE
    assert mom_basket.risk_vibe == RiskVibe.MOMENTUM

    for alloc in cons_basket.allocations:
        assert alloc.holding_period == "4 to 8 Weeks"

    for alloc in mom_basket.allocations:
        assert alloc.holding_period == "1 to 2 Weeks"


def test_generate_basket_invalid_capital():
    with pytest.raises(ValueError, match="Capital must be greater than zero"):
        generate_strategy_basket(capital=0.0)

    with pytest.raises(ValueError, match="Capital must be greater than zero"):
        generate_strategy_basket(capital=-1000.0)


def test_generate_basket_custom_candidates():
    custom_pool = [
        {"symbol": "INFY", "price": 1800.0, "atr": 30.0, "strategy": "Breakout Momentum", "sector": "IT"},
        {"symbol": "ICICIBANK", "price": 1200.0, "atr": 20.0, "strategy": "Pullback in Uptrend", "sector": "BANKING"},
    ]
    basket = generate_strategy_basket(capital=50000.0, candidates=custom_pool, max_stocks=2)
    assert len(basket.allocations) == 2
    symbols = {a.symbol for a in basket.allocations}
    assert "INFY" in symbols
    assert "ICICIBANK" in symbols


def test_generate_basket_with_goal_and_affordability():
    from app.models_basket import InvestmentGoal

    # Small capital (< 30,000) should activate affordability filter
    basket = generate_strategy_basket(
        capital=20000.0,
        risk_vibe=RiskVibe.BALANCED,
        goal=InvestmentGoal.VACATION_FUND,
        max_stocks=3,
    )
    assert basket.goal == InvestmentGoal.VACATION_FUND
    assert basket.peace_of_mind_score >= 80
    assert basket.scenario_best_case > 0
    assert basket.scenario_worst_case < 0

    for alloc in basket.allocations:
        assert alloc.suggested_entry_price <= 1500.0  # Affordable price band
        assert alloc.target1_price > alloc.suggested_entry_price
        assert alloc.target2_price > alloc.target1_price
        assert alloc.gtt_stop_trigger > 0
        assert alloc.gtt_target1_trigger > 0
        assert alloc.gtt_target2_trigger > 0

