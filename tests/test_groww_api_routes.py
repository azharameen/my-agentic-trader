"""Unit tests for Groww FastAPI REST endpoints."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app import groww_client
from app.dashboard_api import app
from config.settings import get_settings


@pytest.fixture(autouse=True)
def clean_env():
    groww_client._groww_client = None
    get_settings.cache_clear()
    yield
    groww_client._groww_client = None
    get_settings.cache_clear()


client = TestClient(app)


def test_groww_status_route_not_configured(monkeypatch):
    """Test /api/v1/groww/status endpoint when disabled."""
    monkeypatch.setenv("GROWW_ENABLED", "false")
    get_settings.cache_clear()
    groww_client._groww_client = None

    response = client.get("/api/v1/groww/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "NOT_CONFIGURED"
    assert data["configured"] is False


def test_groww_balance_route(monkeypatch):
    """Test /api/v1/groww/balance endpoint."""
    monkeypatch.setenv("GROWW_ENABLED", "true")
    monkeypatch.setenv("GROWW_ACCESS_TOKEN", "valid_token")
    get_settings.cache_clear()

    with patch.object(
        groww_client.GrowwClient,
        "get_user_margin",
        return_value=groww_client.GrowwBalance(
            available_cash=25000.0,
            collateral_margin=5000.0,
            used_margin=2000.0,
            total_margin=30000.0,
        ),
    ):
        response = client.get("/api/v1/groww/balance")
        assert response.status_code == 200
        data = response.json()
        assert data["available_cash"] == 25000.0
        assert data["total_margin"] == 30000.0


def test_groww_holdings_route(monkeypatch):
    """Test /api/v1/groww/holdings endpoint."""
    monkeypatch.setenv("GROWW_ENABLED", "true")
    monkeypatch.setenv("GROWW_ACCESS_TOKEN", "valid_token")
    get_settings.cache_clear()

    with patch.object(
        groww_client.GrowwClient,
        "get_holdings",
        return_value=[
            groww_client.GrowwHolding(
                symbol="TCS",
                company_name="Tata Consultancy Services",
                quantity=5,
                avg_price=4000.0,
                current_price=4100.0,
                invested_amount=20000.0,
                current_value=20500.0,
                pnl=500.0,
                pnl_pct=2.5,
            )
        ],
    ):
        response = client.get("/api/v1/groww/holdings")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["symbol"] == "TCS"
        assert data[0]["quantity"] == 5


def test_groww_sync_route(monkeypatch):
    """Test /api/v1/groww/sync endpoint."""
    monkeypatch.setenv("GROWW_ENABLED", "true")
    monkeypatch.setenv("GROWW_ACCESS_TOKEN", "valid_token")
    get_settings.cache_clear()

    with patch(
        "app.groww_sync.sync_groww_portfolio",
        return_value={
            "status": "OK",
            "synced_count": 2,
            "holdings_found": 2,
            "updated_count": 0,
            "closed_count": 0,
        },
    ):
        response = client.post("/api/v1/groww/sync")
        assert response.status_code == 200
        data = response.json()
        assert data["synced_count"] == 2
        assert data["holdings_found"] == 2


def test_groww_orders_route(monkeypatch):
    monkeypatch.setenv("GROWW_ENABLED", "true")
    monkeypatch.setenv("GROWW_ACCESS_TOKEN", "valid_token")
    get_settings.cache_clear()
    with patch.object(
        groww_client.GrowwClient, "get_orders", return_value=[{"trading_symbol": "INFY"}]
    ):
        response = client.get("/api/v1/groww/orders")
    assert response.status_code == 200
    assert response.json() == [{"trading_symbol": "INFY"}]
