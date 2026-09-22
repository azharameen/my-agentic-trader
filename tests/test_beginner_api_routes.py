from fastapi.testclient import TestClient
from app.dashboard_api import app

client = TestClient(app)


def test_api_generate_basket_and_confirm_lifecycle():
    # 1. Generate basket via API
    res_basket = client.post(
        "/api/v1/strategy/generate-basket",
        json={"capital": 75000.0, "risk_vibe": "BALANCED", "max_stocks": 3},
    )
    assert res_basket.status_code == 200
    basket = res_basket.json()
    assert basket["total_capital"] == 75000.0
    assert len(basket["allocations"]) >= 1

    basket_id = basket["basket_id"]

    # 2. Confirm execution on broker
    confirmations = [
        {
            "symbol": alloc["symbol"],
            "shares": alloc["shares"],
            "executed_price": alloc["suggested_entry_price"],
            "broker_name": "AngelOne",
        }
        for alloc in basket["allocations"]
    ]
    res_confirm = client.post(
        "/api/v1/portfolio/confirm-executions",
        json={
            "basket_id": basket_id,
            "user_id": "api_test_user",
            "confirmations": confirmations,
        },
    )
    assert res_confirm.status_code == 200
    summary = res_confirm.json()
    assert summary["portfolio_id"] == basket_id
    assert len(summary["active_positions"]) == len(basket["allocations"])

    # 3. Fetch active health
    res_health = client.get("/api/v1/portfolio/active-health?user_id=api_test_user")
    assert res_health.status_code == 200
    health_data = res_health.json()
    assert health_data["portfolio_id"] == basket_id

    # 4. Fetch digests
    res_am = client.get("/api/v1/digests/morning?user_id=api_test_user")
    assert res_am.status_code == 200
    assert res_am.json()["digest_type"] == "MORNING_MOOD"

    res_pm = client.get("/api/v1/digests/evening?user_id=api_test_user")
    assert res_pm.status_code == 200
    assert res_pm.json()["digest_type"] == "EVENING_HEALTH"

    # 5. Exit position
    first_pos = health_data["active_positions"][0]
    res_exit = client.post(
        "/api/v1/portfolio/exit-position",
        json={
            "position_id": first_pos["position_id"],
            "exit_price": first_pos["entry_price"] * 1.1,
            "user_id": "api_test_user",
        },
    )
    assert res_exit.status_code == 200
    reinvest = res_exit.json()
    assert reinvest["exited_symbol"] == first_pos["symbol"]
    assert len(reinvest["new_opportunities"]) >= 1
