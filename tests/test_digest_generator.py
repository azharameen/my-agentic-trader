from app.basket_generator import generate_strategy_basket
from app.digest_generator import (
    format_digest_for_telegram,
    generate_evening_health_digest,
    generate_morning_mood_digest,
)
from app.models_basket import BatchExecutionRequest, ExecutionConfirmationItem, RiskVibe
from app.portfolio_manager import confirm_batch_execution, create_user_portfolio_from_basket


def test_morning_and_evening_digests():
    # Create active test portfolio
    basket = generate_strategy_basket(capital=50000.0, risk_vibe=RiskVibe.BALANCED, max_stocks=2)
    pid = create_user_portfolio_from_basket(basket, user_id="digest_user")

    confirmations = [
        ExecutionConfirmationItem(
            symbol=alloc.symbol,
            shares=alloc.shares,
            executed_price=alloc.suggested_entry_price,
            broker_name="Groww",
        )
        for alloc in basket.allocations
    ]
    confirm_batch_execution(
        BatchExecutionRequest(basket_id=pid, user_id="digest_user", confirmations=confirmations)
    )

    # 1. Morning Digest
    am_digest = generate_morning_mood_digest(user_id="digest_user")
    assert am_digest.digest_type == "MORNING_MOOD"
    assert len(am_digest.greeting) > 0
    assert len(am_digest.market_mood) > 0
    assert len(am_digest.positions) == 2

    am_telegram = format_digest_for_telegram(am_digest)
    assert "Morning Market Brief" in am_telegram
    assert am_digest.positions[0].symbol in am_telegram

    # 2. Evening Digest
    pm_digest = generate_evening_health_digest(user_id="digest_user")
    assert pm_digest.digest_type == "EVENING_HEALTH"
    assert "Evening" in pm_digest.greeting
    assert len(pm_digest.portfolio_summary_text) > 0

    pm_telegram = format_digest_for_telegram(pm_digest)
    assert "Evening Portfolio Health" in pm_telegram
