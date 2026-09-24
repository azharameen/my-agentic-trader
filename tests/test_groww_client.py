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


def _response(status_code: int, payload: object) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload
    response.text = ""
    response.raise_for_status.return_value = None
    return response


def test_groww_client_not_configured_by_default(monkeypatch):
    monkeypatch.setenv("GROWW_ENABLED", "false")
    get_settings.cache_clear()

    client = groww_client.GrowwClient()
    assert not client.is_configured()
    status = client.get_connection_status()
    assert status.status == "NOT_CONFIGURED"
    assert status.configured is False


def test_groww_client_configured_with_access_token(monkeypatch):
    monkeypatch.setenv("GROWW_ENABLED", "true")
    monkeypatch.setenv("GROWW_ACCESS_TOKEN", "test_access_token_123")
    get_settings.cache_clear()

    client = groww_client.GrowwClient()
    assert client.is_configured()
    assert client.get_auth_token() == "test_access_token_123"


def test_groww_client_approval_exchange_uses_api_key_bearer(monkeypatch):
    monkeypatch.setenv("GROWW_ENABLED", "true")
    monkeypatch.setenv("GROWW_API_KEY", "approval_key_123")
    monkeypatch.setenv("GROWW_API_SECRET", "JBSWY3DPEHPK3PXP")
    monkeypatch.delenv("GROWW_ACCESS_TOKEN", raising=False)
    get_settings.cache_clear()

    client = groww_client.GrowwClient()

    with patch("requests.request") as mock_request:
        mock_request.return_value = _response(
            200,
            {"status": "SUCCESS", "payload": {"token": "access_token_from_approval"}},
        )

        token = client.get_auth_token()

    assert token == "access_token_from_approval"
    first_call = mock_request.call_args_list[0]
    assert first_call.args[1].endswith("/token/api/access")
    assert first_call.kwargs["headers"]["Authorization"] == "Bearer approval_key_123"


def test_groww_client_totp_token_exchange(monkeypatch):
    monkeypatch.setenv("GROWW_ENABLED", "true")
    monkeypatch.setenv("GROWW_API_KEY", "test_api_key")
    monkeypatch.setenv("GROWW_API_SECRET", "JBSWY3DPEHPK3PXP")
    monkeypatch.delenv("GROWW_ACCESS_TOKEN", raising=False)
    get_settings.cache_clear()

    client = groww_client.GrowwClient()
    assert client.is_configured()

    with patch("requests.request") as mock_request:
        mock_request.return_value = _response(
            200,
            {"status": "SUCCESS", "payload": {"token": "generated_jwt_token_abc"}},
        )

        token = client.get_auth_token()

    assert token == "generated_jwt_token_abc"
    assert mock_request.call_count == 1


def test_groww_get_user_margin(monkeypatch):
    monkeypatch.setenv("GROWW_ENABLED", "true")
    monkeypatch.setenv("GROWW_ACCESS_TOKEN", "valid_token")
    get_settings.cache_clear()

    client = groww_client.GrowwClient()

    with patch("requests.request") as mock_request:
        mock_request.return_value = _response(
            200,
            {
                "status": "SUCCESS",
                "payload": {
                    "clear_cash": 45000.50,
                    "collateral_available": 10000.0,
                    "net_margin_used": 5000.0,
                    "adhoc_margin": 0.0,
                },
            },
        )

        balance = client.get_user_margin()

    assert balance.available_cash == 45000.50
    assert balance.collateral_margin == 10000.0
    assert balance.total_margin == 55000.5


def test_groww_get_holdings(monkeypatch):
    monkeypatch.setenv("GROWW_ENABLED", "true")
    monkeypatch.setenv("GROWW_ACCESS_TOKEN", "valid_token")
    get_settings.cache_clear()

    client = groww_client.GrowwClient()

    with patch("requests.request") as mock_request:
        mock_request.return_value = _response(
            200,
            {
                "status": "SUCCESS",
                "payload": {
                    "holdings": [
                        {
                            "trading_symbol": "INFY",
                            "isin": "INE009A01021",
                            "quantity": 10.0,
                            "average_price": 1800.0,
                        }
                    ]
                },
            },
        )

        holdings = client.get_holdings()

    assert len(holdings) == 1
    assert holdings[0].symbol == "INFY"
    assert holdings[0].quantity == 10
    assert holdings[0].avg_price == 1800.0
    assert holdings[0].current_price == 1800.0
    assert holdings[0].pnl == 0.0


def test_groww_holdings_records_permission_error(monkeypatch):
    monkeypatch.setenv("GROWW_ENABLED", "true")
    monkeypatch.setenv("GROWW_ACCESS_TOKEN", "valid_token")
    get_settings.cache_clear()

    client = groww_client.GrowwClient()

    with patch("requests.request") as mock_request:
        mock_request.return_value = _response(
            403, {"status": "FAILURE", "error": {"message": "Access forbidden for this request"}}
        )
        assert client.get_holdings() == []

    assert "forbidden" in client.portfolio_access_error.lower()


def test_groww_get_holdings_unwraps_documented_response(monkeypatch):
    monkeypatch.setenv("GROWW_ENABLED", "true")
    monkeypatch.setenv("GROWW_ACCESS_TOKEN", "valid_token")
    get_settings.cache_clear()

    client = groww_client.GrowwClient()

    with patch("requests.request") as mock_request:
        mock_request.return_value = _response(
            200,
            {
                "status": "SUCCESS",
                "payload": {
                    "holdings": [
                        {
                            "trading_symbol": "TCS",
                            "quantity": 2,
                            "average_price": 3000.0,
                            "ltp": 3100.0,
                        }
                    ]
                },
            },
        )

        holdings = client.get_holdings()

    assert len(holdings) == 1
    assert holdings[0].symbol == "TCS"
    assert holdings[0].quantity == 2


def test_groww_get_orders_uses_documented_order_list(monkeypatch):
    monkeypatch.setenv("GROWW_ENABLED", "true")
    monkeypatch.setenv("GROWW_ACCESS_TOKEN", "valid_token")
    get_settings.cache_clear()

    client = groww_client.GrowwClient()

    with patch("requests.request") as mock_request:
        mock_request.return_value = _response(
            200,
            {
                "status": "SUCCESS",
                "payload": {"order_list": [{"trading_symbol": "INFY", "order_status": "EXECUTED"}]},
            },
        )

        orders = client.get_orders()

    assert orders == [{"trading_symbol": "INFY", "order_status": "EXECUTED"}]
    assert mock_request.call_count == 1


def test_groww_order_execution_is_strictly_blocked():
    client = groww_client.GrowwClient()

    with pytest.raises(RuntimeError, match="strictly prohibited"):
        client.place_order(symbol="TCS", qty=10, side="BUY")

    with pytest.raises(RuntimeError, match="strictly prohibited"):
        client.modify_order(order_id="123", qty=5)

    with pytest.raises(RuntimeError, match="strictly prohibited"):
        client.cancel_order(order_id="123")


def test_groww_sync_to_portfolio_tracker(monkeypatch):
    monkeypatch.setenv("GROWW_ENABLED", "true")
    monkeypatch.setenv("GROWW_ACCESS_TOKEN", "valid_token")
    get_settings.cache_clear()

    client = groww_client.GrowwClient()

    with patch(
        "app.groww_sync.sync_groww_portfolio",
        return_value={
            "status": "OK",
            "holdings_found": 1,
            "synced_count": 1,
            "updated_count": 0,
            "closed_count": 0,
        },
    ) as mock_sync:
        res = client.sync_to_portfolio_tracker()

    assert res["synced_count"] == 1
    assert res["holdings_found"] == 1
    mock_sync.assert_called_once()


def test_groww_get_available_margin_details(monkeypatch):
    monkeypatch.setenv("GROWW_ENABLED", "true")
    monkeypatch.setenv("GROWW_ACCESS_TOKEN", "valid_token")
    get_settings.cache_clear()

    client = groww_client.GrowwClient()

    with patch("requests.request") as mock_request:
        mock_request.return_value = _response(
            200,
            {
                "status": "SUCCESS",
                "payload": {
                    "clear_cash": 96.21,
                    "net_margin_used": 1.8,
                    "equity_margin_details": {"cnc_balance_available": 94.41},
                },
            },
        )
        details = client.get_available_margin_details()

    assert details["clear_cash"] == 96.21


def test_groww_get_order_margin_details(monkeypatch):
    monkeypatch.setenv("GROWW_ENABLED", "true")
    monkeypatch.setenv("GROWW_ACCESS_TOKEN", "valid_token")
    get_settings.cache_clear()

    client = groww_client.GrowwClient()

    with patch("requests.request") as mock_request:
        mock_request.return_value = _response(
            200, {"status": "SUCCESS", "payload": {"total_requirement": 2505.0}}
        )
        estimate = client.get_order_margin_details("RELIANCE", quantity=1, price=2500.0)

    assert estimate["total_requirement"] == 2505.0
    assert mock_request.call_count == 1


def test_groww_get_quote_ltp_ohlc(monkeypatch):
    monkeypatch.setenv("GROWW_ENABLED", "true")
    monkeypatch.setenv("GROWW_ACCESS_TOKEN", "valid_token")
    get_settings.cache_clear()

    client = groww_client.GrowwClient()

    def fake_request(method, url, headers=None, params=None, json=None, timeout=None):
        response = MagicMock()
        response.status_code = 200
        if url.endswith("/live-data/quote"):
            response.json.return_value = {"status": "SUCCESS", "payload": {"last_price": 149.5}}
        elif url.endswith("/live-data/ltp"):
            response.json.return_value = {"status": "SUCCESS", "payload": {"NSE_RELIANCE": 2500.5}}
        else:
            response.json.return_value = {
                "status": "SUCCESS",
                "payload": {
                    "NSE_RELIANCE": {"open": 2490.0, "high": 2510.0, "low": 2480.0, "close": 2500.5}
                },
            }
        response.text = ""
        return response

    with patch("requests.request", side_effect=fake_request):
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
    call_sizes = []

    def fake_request(method, url, headers=None, params=None, json=None, timeout=None):
        response = MagicMock()
        response.status_code = 200
        symbols = (params or {}).get("exchange_symbols", "")
        call_sizes.append(len(symbols.split(",")) if symbols else 0)
        response.json.return_value = {
            "status": "SUCCESS",
            "payload": {symbol: 100.0 for symbol in symbols.split(",") if symbol},
        }
        response.text = ""
        return response

    symbols = [f"SYM{i}" for i in range(75)]

    with patch("requests.request", side_effect=fake_request):
        result = client.get_ltp(symbols)

    assert call_sizes == [50, 25]
    assert len(result) == 75


def test_groww_get_historical_candle_data(monkeypatch):
    monkeypatch.setenv("GROWW_ENABLED", "true")
    monkeypatch.setenv("GROWW_ACCESS_TOKEN", "valid_token")
    get_settings.cache_clear()

    client = groww_client.GrowwClient()

    with (
        patch("requests.request") as mock_request,
        patch.object(
            client,
            "get_all_instruments",
            return_value=[{"trading_symbol": "RELIANCE", "groww_symbol": "NSE-RELIANCE"}],
        ),
    ):
        mock_request.return_value = _response(
            200,
            {
                "status": "SUCCESS",
                "payload": {
                    "candles": [["2025-01-01 09:15:00", 150, 155, 145, 152, 10000]],
                    "closing_price": 152,
                },
            },
        )
        response = client.get_historical_candle_data(
            "RELIANCE", "2025-01-01 00:00:00", "2025-01-02 00:00:00"
        )

    assert response["candles"][0][4] == 152


def test_groww_margin_and_livedata_methods_fail_closed_when_not_configured(monkeypatch):
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
    with patch.object(client, "get_all_instruments", return_value=[]):
        assert client.get_historical_candle_data("RELIANCE", "2025-01-01", "2025-01-02") == {}
        assert client.get_instrument_by_groww_symbol("NSE-RELIANCE") == {}
