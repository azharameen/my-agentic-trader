import pytest
from app.basket_generator import generate_strategy_basket
from app.models_basket import BatchExecutionRequest, ExecutionConfirmationItem, RiskVibe
from app.portfolio_manager import (
    confirm_batch_execution,
    create_user_portfolio_from_basket,
    get_user_portfolio,
)


def test_portfolio_lifecycle():
    # 1. Generate basket
    basket = generate_strategy_basket(capital=100000.0, risk_vibe=RiskVibe.BALANCED, max_stocks=3)
    portfolio_id = create_user_portfolio_from_basket(basket, user_id="test_user")

    assert portfolio_id == basket.basket_id

    # 2. Confirm execution on broker with actual prices
    confirmations = [
        ExecutionConfirmationItem(
            symbol=alloc.symbol,
            shares=alloc.shares,
            executed_price=alloc.suggested_entry_price + 2.0,  # Small slippage
            broker_name="Zerodha",
        )
        for alloc in basket.allocations
    ]
    req = BatchExecutionRequest(
        basket_id=portfolio_id,
        user_id="test_user",
        confirmations=confirmations,
    )
    summary = confirm_batch_execution(req)

    assert summary.portfolio_id == portfolio_id
    assert summary.user_id == "test_user"
    assert len(summary.active_positions) == len(basket.allocations)
    assert summary.invested_capital > 0

    # 3. Retrieve portfolio
    fetched = get_user_portfolio(user_id="test_user", portfolio_id=portfolio_id)
    assert fetched is not None
    assert len(fetched.active_positions) == len(basket.allocations)

