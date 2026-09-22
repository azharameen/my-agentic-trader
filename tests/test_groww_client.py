"""Unit tests for Groww read-only client and safety invariants (ADR-002, ADR-035)."""

from unittest.mock import MagicMock, patch

import pytest

from app import groww_client
from config.settings import get_settings


@pytest.fixture(autouse=True)
def clean_groww_client():
    """Reset Groww client and settings cache between tests."""
    groww_client._groww_client = None
    get_settings.cache_clear()
    yield
    groww_client._groww_client = None
    get_settings.cache_clear()


def test_groww_client_not_configured_by_default(monkeypatch):
    """Ensure client reports NOT_CONFIGURED when disabled."""
    monkeypatch.setenv("GROWW_ENABLED", "false")
    get_settings.cache_clear()

    client = groww_client.GrowwClient()
    assert not client.is_configured()
    status = client.get_connection_status()
    assert status.status == "NOT_CONFIGURED"
    assert status.configured is False


def test_groww_client_configured_with_access_token(monkeypatch):
    """Ensure direct access token is recognized."""
    monkeypatch.setenv("GROWW_ENABLED", "true")
    monkeypatch.setenv("GROWW_ACCESS_TOKEN", "test_access_token_123")
    get_settings.cache_clear()

    client = groww_client.GrowwClient()
    assert client.is_configured()
    assert client.get_auth_token() == "test_access_token_123"


def test_groww_client_totp_token_exchange(monkeypatch):
    """Test TOTP generation and token caching."""
    monkeypatch.setenv("GROWW_ENABLED", "true")
    monkeypatch.setenv("GROWW_API_KEY", "test_api_key")
    # Base32 secret for pyotp
    monkeypatch.setenv("GROWW_API_SECRET", "JBSWY3DPEHPK3PXP")
    monkeypatch.delenv("GROWW_ACCESS_TOKEN", raising=False)
    get_settings.cache_clear()

    client = groww_client.GrowwClient()
    assert client.is_configured()

    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"token": "generated_jwt_token_abc"}
        mock_post.return_value = mock_resp

        token = client.get_auth_token()
        assert token == "generated_jwt_token_abc"
        mock_post.assert_called_once()


def test_groww_get_user_margin(monkeypatch):
    """Test parsing of user margin and available cash."""
    monkeypatch.setenv("GROWW_ENABLED", "true")
    monkeypatch.setenv("GROWW_ACCESS_TOKEN", "valid_token")
    get_settings.cache_clear()

    client = groww_client.GrowwClient()

    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "equity": {
                "available_cash": 45000.50,
                "collateral": 10000.0,
                "used_margin": 5000.0,
                "total_margin": 50000.50,
            }
        }
        mock_get.return_value = mock_resp

        balance = client.get_user_margin()
        assert balance.available_cash == 45000.50
        assert balance.collateral_margin == 10000.0
        assert balance.total_margin == 50000.50


def test_groww_get_holdings(monkeypatch):
    """Test normalization of Demat equity holdings."""
    monkeypatch.setenv("GROWW_ENABLED", "true")
    monkeypatch.setenv("GROWW_ACCESS_TOKEN", "valid_token")
    get_settings.cache_clear()

    client = groww_client.GrowwClient()

    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "holdings": [
                {
                    "trading_symbol": "INFY.NS",
                    "company_name": "Infosys Ltd",
                    "isin": "INE009A01021",
                    "quantity": 10,
                    "average_price": 1800.0,
                    "ltp": 1890.0,
                    "pnl": 900.0,
                    "pnl_percentage": 5.0,
                }
            ]
        }
        mock_get.return_value = mock_resp

        holdings = client.get_holdings()
        assert len(holdings) == 1
        assert holdings[0].symbol == "INFY"
        assert holdings[0].quantity == 10
        assert holdings[0].avg_price == 1800.0
        assert holdings[0].current_price == 1890.0
        assert holdings[0].pnl == 900.0


def test_groww_order_execution_is_strictly_blocked():
    """HARD INVARIANT: Live order placement/modification/cancellation must raise RuntimeError."""
    client = groww_client.GrowwClient()

    with pytest.raises(RuntimeError, match="strictly prohibited"):
        client.place_order(symbol="TCS", qty=10, side="BUY")

    with pytest.raises(RuntimeError, match="strictly prohibited"):
        client.modify_order(order_id="123", qty=5)

    with pytest.raises(RuntimeError, match="strictly prohibited"):
        client.cancel_order(order_id="123")


def test_groww_sync_to_portfolio_tracker(monkeypatch):
    """Test syncing Demat holdings into portfolio manager positions."""
    monkeypatch.setenv("GROWW_ENABLED", "true")
    monkeypatch.setenv("GROWW_ACCESS_TOKEN", "valid_token")
    get_settings.cache_clear()

    client = groww_client.GrowwClient()

    with patch.object(
        client,
        "get_holdings",
        return_value=[
            groww_client.GrowwHolding(
                symbol="ITC",
                company_name="ITC Ltd",
                quantity=20,
                avg_price=450.0,
                current_price=465.0,
                invested_amount=9000.0,
                current_value=9300.0,
                pnl=300.0,
                pnl_pct=3.33,
            )
        ],
    ), patch("app.portfolio_manager.get_user_portfolio", return_value=None), patch(
        "app.db.execute"
    ) as mock_db_exec:

        res = client.sync_to_portfolio_tracker()
        assert res["synced_count"] == 1
        assert res["holdings_found"] == 1
        assert mock_db_exec.called


# --------------------------------------------------------------------------- #
# ADR-036: Read-only live data, historical data, margin & instruments
# --------------------------------------------------------------------------- #
def test_groww_get_available_margin_details(monkeypatch):
    monkeypatch.setenv("GROWW_ENABLED", "true")
    monkeypatch.setenv("GROWW_ACCESS_TOKEN", "valid_token")
    get_settings.cache_clear()

    client = groww_client.GrowwClient()
    mock_sdk = MagicMock()
    mock_sdk.get_available_margin_details.return_value = {
        "clear_cash": 96.21,
        "net_margin_used": 1.8,
        "equity_margin_details": {"cnc_balance_available": 94.41},
    }
    with patch.object(client, "_get_sdk_client", return_value=mock_sdk):
        details = client.get_available_margin_details()
        assert details["clear_cash"] == 96.21


def test_groww_get_order_margin_details(monkeypatch):
    monkeypatch.setenv("GROWW_ENABLED", "true")
    monkeypatch.setenv("GROWW_ACCESS_TOKEN", "valid_token")
    get_settings.cache_clear()

    client = groww_client.GrowwClient()
    mock_sdk = MagicMock()
    mock_sdk.get_order_margin_details.return_value = {"total_requirement": 2505.0}
    with patch.object(client, "_get_sdk_client", return_value=mock_sdk):
        estimate = client.get_order_margin_details("RELIANCE", quantity=1, price=2500.0)
        assert estimate["total_requirement"] == 2505.0
        mock_sdk.get_order_margin_details.assert_called_once()


def test_groww_get_quote_ltp_ohlc(monkeypatch):
    monkeypatch.setenv("GROWW_ENABLED", "true")
    monkeypatch.setenv("GROWW_ACCESS_TOKEN", "valid_token")
    get_settings.cache_clear()

    client = groww_client.GrowwClient()
    mock_sdk = MagicMock()
    mock_sdk.get_quote.return_value = {"last_price": 149.5}
    mock_sdk.get_ltp.return_value = {"NSE_RELIANCE": 2500.5}
    mock_sdk.get_ohlc.return_value = {"NSE_RELIANCE": {"open": 2490.0, "high": 2510.0, "low": 2480.0, "close": 2500.5}}

    with patch.object(client, "_get_sdk_client", return_value=mock_sdk):
        quote = client.get_quote("RELIANCE")
        assert quote["last_price"] == 149.5

        ltp = client.get_ltp(["RELIANCE"])
        assert ltp["NSE_RELIANCE"] == 2500.5

        ohlc = client.get_ohlc(["RELIANCE"])
        assert ohlc["NSE_RELIANCE"]["close"] == 2500.5


def test_groww_get_ltp_batches_over_50_symbols(monkeypatch):
    monkeypatch.setenv("GROWW_ENABLED", "true")
    monkeypatch.setenv("GROWW_ACCESS_TOKEN", "valid_token")
    get_settings.cache_clear()

    client = groww_client.GrowwClient()
    mock_sdk = MagicMock()
    call_sizes = []

    def fake_get_ltp(segment, exchange_trading_symbols):
        call_sizes.append(len(exchange_trading_symbols))
        return {sym: 100.0 for sym in exchange_trading_symbols}

    mock_sdk.get_ltp.side_effect = fake_get_ltp
    symbols = [f"SYM{i}" for i in range(75)]

    with patch.object(client, "_get_sdk_client", return_value=mock_sdk):
        result = client.get_ltp(symbols)
        assert call_sizes == [50, 25]
        assert len(result) == 75


def test_groww_get_historical_candle_data(monkeypatch):
    monkeypatch.setenv("GROWW_ENABLED", "true")
    monkeypatch.setenv("GROWW_ACCESS_TOKEN", "valid_token")
    get_settings.cache_clear()

    client = groww_client.GrowwClient()
    mock_sdk = MagicMock()
    mock_sdk.get_historical_candle_data.return_value = {
        "candles": [[1633072800, 150, 155, 145, 152, 10000]],
    }
    with patch.object(client, "_get_sdk_client", return_value=mock_sdk):
        response = client.get_historical_candle_data("RELIANCE", "2025-01-01 00:00:00", "2025-01-02 00:00:00")
        assert response["candles"][0][4] == 152


def test_groww_margin_and_livedata_methods_fail_closed_when_not_configured(monkeypatch):
    """All new ADR-036 methods must safely return empty when Groww isn't configured."""
    monkeypatch.setenv("GROWW_ENABLED", "false")
    monkeypatch.delenv("GROWW_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("GROWW_API_KEY", raising=False)
    get_settings.cache_clear()

    client = groww_client.GrowwClient()
    assert client.get_available_margin_details() == {}
    assert client.get_order_margin_details("RELIANCE", quantity=1) == {}
    assert client.get_quote("RELIANCE") == {}
    assert client.get_ltp(["RELIANCE"]) == {}
    assert client.get_ohlc(["RELIANCE"]) == {}
    assert client.get_historical_candle_data("RELIANCE", "2025-01-01", "2025-01-02") == {}
    assert client.get_instrument_by_groww_symbol("NSE-RELIANCE") == {}

