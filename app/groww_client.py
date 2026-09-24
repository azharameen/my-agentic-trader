"""Groww Broker API Read-Only Client (curl-only).

Read-only access to Groww Trading API endpoints using direct HTTP calls.
Live order placement, modification, and cancellation remain blocked.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import pyotp
import requests
from pydantic import BaseModel, Field

from config.settings import get_settings

logger = logging.getLogger(__name__)

GROWW_BASE_URL = "https://api.groww.in/v1"
GROWW_INSTRUMENTS_URL = "https://growwapi-assets.groww.in/instruments/instrument.csv"


class GrowwBalance(BaseModel):
    available_cash: float = 0.0
    collateral_margin: float = 0.0
    used_margin: float = 0.0
    total_margin: float = 0.0
    currency: str = "INR"
    raw: dict[str, Any] = Field(default_factory=dict)


class GrowwHolding(BaseModel):
    symbol: str
    company_name: str = ""
    isin: str = ""
    quantity: int = 0
    avg_price: float = 0.0
    current_price: float = 0.0
    invested_amount: float = 0.0
    current_value: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0


class GrowwPosition(BaseModel):
    symbol: str
    quantity: int = 0
    buy_price: float = 0.0
    sell_price: float = 0.0
    current_price: float = 0.0
    pnl: float = 0.0
    segment: str = "CASH"
    product_type: str = "CNC"


class GrowwMutualFund(BaseModel):
    folio_id: str
    scheme_name: str
    folio_number: str = ""
    units: float = 0.0
    nav: float = 0.0
    invested_amount: float = 0.0
    current_value: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    asset_category: str = "EQUITY"
    last_updated: str = ""


class GrowwPortfolioOverview(BaseModel):
    ucc: str = ""
    status: str = "CONNECTED"
    total_net_worth: float = 0.0
    equity_invested: float = 0.0
    equity_current_value: float = 0.0
    equity_pnl: float = 0.0
    equity_pnl_pct: float = 0.0
    mf_invested: float = 0.0
    mf_current_value: float = 0.0
    mf_pnl: float = 0.0
    available_cash: float = 0.0
    total_margin: float = 0.0
    holdings_count: int = 0
    mf_count: int = 0
    last_synced_at: str = ""
    is_demo_mode: bool = False
    scope_warning: str = ""


class GrowwStatus(BaseModel):
    configured: bool = False
    authenticated: bool = False
    status: str = "NOT_CONFIGURED"
    message: str = ""
    last_synced_at: str = ""
    ucc: str = ""
    scope_warning: str = ""


@dataclass(slots=True)
class _HttpResult:
    status_code: int
    data: Any
    error: str = ""


class GrowwClient:
    def __init__(self) -> None:
        self._cached_token: str | None = None
        self._token_expiry_epoch: float = 0.0
        self._last_error_message: str = ""
        self._scope_warning: str = ""
        self._last_portfolio_error: str = ""
        self._instruments_cache: list[dict[str, Any]] | None = None
        self._instruments_cache_expiry: float = 0.0
        self._instrument_lookup: dict[str, dict[str, Any]] = {}

    def is_configured(self) -> bool:
        settings = get_settings()
        has_token = bool(
            settings.GROWW_ACCESS_TOKEN and settings.GROWW_ACCESS_TOKEN.get_secret_value().strip()
        )
        has_key_secret = bool(
            settings.GROWW_API_KEY and settings.GROWW_API_KEY.get_secret_value().strip()
        )
        return settings.GROWW_ENABLED and (has_token or has_key_secret)

    @property
    def portfolio_access_error(self) -> str:
        return self._last_portfolio_error

    def clear_portfolio_access_error(self) -> None:
        self._last_portfolio_error = ""

    def get_auth_token(self) -> str | None:
        settings = get_settings()
        if not self.is_configured():
            return None

        if settings.GROWW_ACCESS_TOKEN and settings.GROWW_ACCESS_TOKEN.get_secret_value().strip():
            return settings.GROWW_ACCESS_TOKEN.get_secret_value().strip()

        now_ts = datetime.now(timezone.utc).timestamp()
        if self._cached_token and now_ts < self._token_expiry_epoch:
            return self._cached_token

        api_key = (
            settings.GROWW_API_KEY.get_secret_value().strip() if settings.GROWW_API_KEY else ""
        )
        secret = (
            settings.GROWW_API_SECRET.get_secret_value().strip()
            if settings.GROWW_API_SECRET
            else ""
        )

        if not api_key:
            return None

        if secret:
            timestamp = str(int(now_ts))
            try:
                checksum = hashlib.sha256(f"{secret}{timestamp}".encode("utf-8")).hexdigest()
                token = self._exchange_access_token(
                    api_key,
                    {"key_type": "approval", "checksum": checksum, "timestamp": timestamp},
                )
                self._cached_token = token
                self._token_expiry_epoch = now_ts + (12 * 3600)
                self._last_error_message = ""
                return token
            except Exception as exc:  # noqa: BLE001
                err_str = str(exc)
                if "Session approval required" in err_str or "403" in err_str:
                    self._last_error_message = (
                        "Session approval required: please approve the authorization request in your "
                        "Groww mobile app, or provide GROWW_ACCESS_TOKEN directly in .env."
                    )
                else:
                    self._last_error_message = f"Approval token exchange failed: {err_str}"

            try:
                current_otp = (
                    secret if len(secret) == 6 and secret.isdigit() else pyotp.TOTP(secret).now()
                )
                token = self._exchange_access_token(
                    api_key, {"key_type": "totp", "totp": current_otp}
                )
                self._cached_token = token
                self._token_expiry_epoch = now_ts + (12 * 3600)
                self._last_error_message = ""
                return token
            except Exception as exc:  # noqa: BLE001
                logger.debug("Groww TOTP exchange attempted and failed: %s", exc)

        return None

    def _exchange_access_token(self, api_key: str, body: dict[str, Any]) -> str:
        result = self._request_json(
            "POST",
            "/token/api/access",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json_body=body,
        )
        if result.status_code == 200:
            token = self._extract_token(self._unwrap_response(result.data))
            if token:
                return token
        raise RuntimeError(
            result.error or f"Groww token exchange failed with HTTP {result.status_code}"
        )

    def _get_headers(self) -> dict[str, str] | None:
        token = self.get_auth_token()
        if not token:
            return None
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "X-API-VERSION": "1.0",
        }

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json_body: Any | None = None,
        timeout: int = 10,
        auth: bool = False,
    ) -> _HttpResult:
        request_headers = dict(headers or {})
        if auth:
            auth_headers = self._get_headers()
            if not auth_headers:
                return _HttpResult(0, {}, "Groww client is not configured")
            request_headers.update(auth_headers)
        try:
            response = requests.request(
                method,
                f"{GROWW_BASE_URL}{path}",
                headers=request_headers,
                params=params,
                json=json_body,
                timeout=timeout,
            )
        except Exception as exc:  # noqa: BLE001
            return _HttpResult(0, {}, str(exc))

        data: Any
        try:
            data = response.json()
        except Exception:  # noqa: BLE001
            data = response.text
        return _HttpResult(response.status_code, data, self._response_error(response, data))

    @staticmethod
    def _unwrap_response(payload: Any) -> Any:
        if not isinstance(payload, dict):
            return payload
        for key in ("payload", "data"):
            value = payload.get(key)
            if value is not None:
                return value
        success = payload.get("success")
        if isinstance(success, dict):
            return success.get("data", payload)
        return payload

    @staticmethod
    def _extract_token(payload: Any) -> str | None:
        if isinstance(payload, dict):
            token = payload.get("token")
            if token:
                return str(token)
            nested = payload.get("success")
            if isinstance(nested, dict) and nested.get("token"):
                return str(nested["token"])
        return None

    @staticmethod
    def _response_error(response: requests.Response, payload: Any) -> str:
        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict):
                message = error.get("message") or error.get("code")
                if message:
                    return str(message)
            message = payload.get("message") or payload.get("status")
            if message and message != "SUCCESS":
                return str(message)
        return response.text[:200]

    @staticmethod
    def _extract_collection(payload: Any, key: str) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if not isinstance(payload, dict):
            return []
        for candidate in (
            payload.get(key),
            payload.get("results"),
            payload.get("data"),
            (payload.get("success") or {}).get("data")
            if isinstance(payload.get("success"), dict)
            else None,
        ):
            result = GrowwClient._extract_collection(candidate, key)
            if result:
                return result
        return []

    def get_connection_status(self) -> GrowwStatus:
        if not self.is_configured():
            return GrowwStatus(
                configured=False,
                authenticated=False,
                status="NOT_CONFIGURED",
                message="Groww API is disabled or credentials are missing in configuration.",
            )

        token = self.get_auth_token()
        if not token:
            return GrowwStatus(
                configured=True,
                authenticated=False,
                status="ERROR",
                message=self._last_error_message or "Failed to generate authentication token.",
            )

        for path in ("/user/detail", "/margins/detail/user"):
            result = self._request_json("GET", path, auth=True, timeout=8)
            if result.status_code == 200:
                payload = self._unwrap_response(result.data)
                ucc = ""
                if isinstance(payload, dict):
                    ucc = str(payload.get("ucc") or payload.get("vendor_user_id") or "")
                return GrowwStatus(
                    configured=True,
                    authenticated=True,
                    status="CONNECTED",
                    message="Successfully authenticated and connected to Groww API.",
                    last_synced_at=datetime.now(timezone.utc).isoformat(),
                    ucc=ucc,
                )
            if result.error:
                self._last_error_message = result.error

        return GrowwStatus(
            configured=True,
            authenticated=False,
            status="ERROR",
            message=self._last_error_message or "Groww API authentication failed.",
        )

    def get_user_margin(self) -> GrowwBalance:
        result = self._request_json("GET", "/margins/detail/user", auth=True, timeout=10)
        if result.status_code != 200:
            self._last_portfolio_error = (
                result.error or f"Groww margin request failed with HTTP {result.status_code}"
            )
            logger.warning("Failed to fetch Groww margin. Status: %s", result.status_code)
            return GrowwBalance()

        payload = self._unwrap_response(result.data)
        if not isinstance(payload, dict):
            return GrowwBalance()

        clear_cash = float(payload.get("clear_cash") or payload.get("available_cash") or 0.0)
        collateral_available = float(payload.get("collateral_available") or 0.0)
        collateral_used = float(payload.get("collateral_used") or 0.0)
        net_margin_used = float(payload.get("net_margin_used") or 0.0)
        adhoc_margin = float(payload.get("adhoc_margin") or 0.0)
        total_margin = clear_cash + collateral_available + adhoc_margin

        self._last_portfolio_error = ""
        return GrowwBalance(
            available_cash=round(clear_cash, 2),
            collateral_margin=round(collateral_available, 2),
            used_margin=round(net_margin_used or collateral_used, 2),
            total_margin=round(total_margin, 2),
            raw=payload,
        )

    def get_available_margin_details(self) -> dict[str, Any]:
        result = self._request_json("GET", "/margins/detail/user", auth=True, timeout=10)
        if result.status_code != 200:
            return {}
        payload = self._unwrap_response(result.data)
        return payload if isinstance(payload, dict) else {}

    def get_order_margin_details(
        self,
        trading_symbol: str,
        quantity: int,
        transaction_type: str = "BUY",
        price: float | None = None,
        exchange: str = "NSE",
        segment: str = "CASH",
        product: str = "CNC",
        order_type: str = "LIMIT",
    ) -> dict[str, Any]:
        order = {
            "trading_symbol": trading_symbol,
            "transaction_type": transaction_type,
            "quantity": int(quantity),
            "order_type": order_type,
            "product": product,
            "exchange": exchange,
        }
        if price is not None:
            order["price"] = float(price)
        result = self._request_json(
            "POST",
            "/margins/detail/orders",
            auth=True,
            params={"segment": segment},
            json_body=[order],
            timeout=10,
        )
        if result.status_code != 200:
            return {}
        payload = self._unwrap_response(result.data)
        return payload if isinstance(payload, dict) else {}

    def get_quote(
        self, trading_symbol: str, exchange: str = "NSE", segment: str = "CASH"
    ) -> dict[str, Any]:
        result = self._request_json(
            "GET",
            "/live-data/quote",
            auth=True,
            params={"exchange": exchange, "segment": segment, "trading_symbol": trading_symbol},
            timeout=10,
        )
        if result.status_code != 200:
            return {}
        payload = self._unwrap_response(result.data)
        return payload if isinstance(payload, dict) else {}

    def get_ltp(
        self, symbols: list[str], exchange: str = "NSE", segment: str = "CASH"
    ) -> dict[str, float]:
        if not symbols:
            return {}
        results: dict[str, float] = {}
        for i in range(0, len(symbols), 50):
            batch = symbols[i : i + 50]
            exchange_symbols = ",".join(f"{exchange}_{sym}" for sym in batch)
            result = self._request_json(
                "GET",
                "/live-data/ltp",
                auth=True,
                params={"segment": segment, "exchange_symbols": exchange_symbols},
                timeout=10,
            )
            if result.status_code != 200:
                continue
            payload = self._unwrap_response(result.data)
            if isinstance(payload, dict):
                for key, value in payload.items():
                    try:
                        results[key] = float(value)
                    except (TypeError, ValueError):
                        continue
        return results

    def get_ohlc(
        self, symbols: list[str], exchange: str = "NSE", segment: str = "CASH"
    ) -> dict[str, dict[str, float]]:
        if not symbols:
            return {}
        results: dict[str, dict[str, float]] = {}
        for i in range(0, len(symbols), 50):
            batch = symbols[i : i + 50]
            exchange_symbols = ",".join(f"{exchange}_{sym}" for sym in batch)
            result = self._request_json(
                "GET",
                "/live-data/ohlc",
                auth=True,
                params={"segment": segment, "exchange_symbols": exchange_symbols},
                timeout=10,
            )
            if result.status_code != 200:
                continue
            payload = self._unwrap_response(result.data)
            if isinstance(payload, dict):
                for key, value in payload.items():
                    parsed = self._parse_ohlc_value(value)
                    if parsed:
                        results[key] = parsed
        return results

    @staticmethod
    def _parse_ohlc_value(value: Any) -> dict[str, float] | None:
        if isinstance(value, dict):
            return {
                k: float(v)
                for k, v in value.items()
                if k in {"open", "high", "low", "close"} and isinstance(v, (int, float, str))
            }
        if isinstance(value, str):
            cleaned = (
                value.strip()
                .strip("{}")
                .replace("open:", '"open":')
                .replace("high:", '"high":')
                .replace("low:", '"low":')
                .replace("close:", '"close":')
            )
            try:
                parsed = json.loads("{" + cleaned + "}")
                return {
                    k: float(v) for k, v in parsed.items() if k in {"open", "high", "low", "close"}
                }
            except Exception:  # noqa: BLE001
                return None
        return None

    def get_historical_candle_data(
        self,
        trading_symbol: str,
        start_time: str,
        end_time: str,
        interval_in_minutes: int = 1440,
        exchange: str = "NSE",
        segment: str = "CASH",
    ) -> dict[str, Any]:
        groww_symbol = self._resolve_groww_symbol(trading_symbol, exchange=exchange)
        result = self._request_json(
            "GET",
            "/historical/candles",
            auth=True,
            params={
                "exchange": exchange,
                "segment": segment,
                "groww_symbol": groww_symbol,
                "start_time": start_time,
                "end_time": end_time,
                "candle_interval": self._minutes_to_interval(interval_in_minutes),
            },
            timeout=15,
        )
        if result.status_code != 200:
            logger.info(
                "Groww historical candles unavailable for %s: %s", trading_symbol, result.error
            )
            return {}
        payload = self._unwrap_response(result.data)
        if not isinstance(payload, dict):
            return {}
        candles = payload.get("candles")
        if isinstance(candles, list):
            payload["candles"] = [
                self._normalize_candle(candle)
                for candle in candles
                if self._normalize_candle(candle)
            ]
        return payload

    @staticmethod
    def _minutes_to_interval(interval_in_minutes: int) -> str:
        mapping = {
            1: "1minute",
            2: "2minute",
            3: "3minute",
            5: "5minute",
            10: "10minute",
            15: "15minute",
            30: "30minute",
            60: "1hour",
            240: "4hour",
            1440: "1day",
            10080: "1week",
            43200: "1month",
        }
        return mapping.get(interval_in_minutes, "1day")

    def get_all_instruments(self) -> list[dict[str, Any]] | None:
        now_ts = datetime.now(timezone.utc).timestamp()
        if self._instruments_cache is not None and now_ts < self._instruments_cache_expiry:
            return self._instruments_cache
        try:
            response = requests.get(GROWW_INSTRUMENTS_URL, timeout=30)
            response.raise_for_status()
            reader = csv.DictReader(io.StringIO(response.text))
            rows = [dict(row) for row in reader]
            self._instruments_cache = rows
            self._instrument_lookup = {}
            for row in rows:
                groww_symbol = str(row.get("groww_symbol") or "").strip()
                trading_symbol = str(row.get("trading_symbol") or "").strip().upper()
                if groww_symbol:
                    self._instrument_lookup[groww_symbol] = row
                if trading_symbol:
                    self._instrument_lookup[trading_symbol] = row
            self._instruments_cache_expiry = now_ts + (24 * 3600)
            return rows
        except Exception as exc:  # noqa: BLE001
            logger.warning("Error fetching Groww instruments master: %s", exc)
            return self._instruments_cache

    def get_instrument_by_groww_symbol(self, groww_symbol: str) -> dict[str, Any]:
        if not self._instrument_lookup:
            self.get_all_instruments()
        row = self._instrument_lookup.get(groww_symbol)
        return dict(row) if row else {}

    def _resolve_groww_symbol(self, trading_symbol: str, exchange: str = "NSE") -> str:
        key = trading_symbol.strip().upper()
        if not self._instrument_lookup:
            self.get_all_instruments()
        row = self._instrument_lookup.get(key)
        if row and row.get("groww_symbol"):
            return str(row["groww_symbol"])
        return f"{exchange}-{key}"

    @staticmethod
    def _normalize_candle(candle: Any) -> list[float] | None:
        if not isinstance(candle, list) or len(candle) < 6:
            return None
        timestamp = candle[0]
        if isinstance(timestamp, str):
            try:
                parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                epoch = int(parsed.timestamp())
            except ValueError:
                try:
                    parsed = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S").replace(
                        tzinfo=timezone.utc
                    )
                    epoch = int(parsed.timestamp())
                except ValueError:
                    return None
        else:
            try:
                epoch = int(float(timestamp))
            except (TypeError, ValueError):
                return None
        try:
            return [
                epoch,
                float(candle[1]),
                float(candle[2]),
                float(candle[3]),
                float(candle[4]),
                float(candle[5]),
            ]
        except (TypeError, ValueError):
            return None

    def _normalise_holdings(self, payload: Any) -> list[GrowwHolding]:
        raw_holdings = self._extract_collection(payload, "holdings")
        holdings: list[GrowwHolding] = []
        for item in raw_holdings:
            sym = (
                str(item.get("trading_symbol") or item.get("symbol") or "")
                .replace(".NS", "")
                .strip()
                .upper()
            )
            qty = int(float(item.get("quantity") or item.get("net_quantity") or 0))
            if not sym or qty <= 0:
                continue
            avg_p = float(item.get("average_price") or item.get("avg_price") or 0.0)
            cur_p = float(item.get("ltp") or item.get("current_price") or avg_p)
            inv = float(item.get("invested_amount") or (qty * avg_p))
            val = float(item.get("current_value") or (qty * cur_p))
            pnl = float(item.get("pnl") or (val - inv))
            pnl_pct = float(item.get("pnl_percentage") or ((pnl / inv * 100) if inv > 0 else 0.0))
            holdings.append(
                GrowwHolding(
                    symbol=sym,
                    company_name=str(item.get("company_name") or item.get("name") or sym),
                    isin=str(item.get("isin") or ""),
                    quantity=qty,
                    avg_price=round(avg_p, 2),
                    current_price=round(cur_p, 2),
                    invested_amount=round(inv, 2),
                    current_value=round(val, 2),
                    pnl=round(pnl, 2),
                    pnl_pct=round(pnl_pct, 2),
                )
            )
        return holdings

    def get_holdings(self) -> list[GrowwHolding]:
        result = self._request_json("GET", "/holdings/user", auth=True, timeout=10)
        if result.status_code != 200:
            self._last_portfolio_error = (
                result.error or f"Groww holdings request failed with HTTP {result.status_code}"
            )
            self._scope_warning = "Groww denied portfolio read access. Verify the active API key's holdings permissions in Groww Developer Console."
            return []

        holdings = self._normalise_holdings(self._unwrap_response(result.data))
        self._scope_warning = (
            ""
            if holdings
            else "Groww returned no current Demat holdings. Orders/positions are separate from settled holdings."
        )
        self._last_portfolio_error = ""
        return holdings

    def get_positions(self) -> list[GrowwPosition]:
        result = self._request_json(
            "GET", "/positions/user", auth=True, params={"segment": "CASH"}, timeout=10
        )
        if result.status_code != 200:
            self._last_portfolio_error = (
                result.error or f"Groww positions request failed with HTTP {result.status_code}"
            )
            return []
        raw_positions = self._extract_collection(self._unwrap_response(result.data), "positions")
        positions: list[GrowwPosition] = []
        for item in raw_positions:
            sym = (
                str(item.get("trading_symbol") or item.get("symbol") or "")
                .replace(".NS", "")
                .strip()
                .upper()
            )
            if not sym:
                continue
            qty = int(float(item.get("quantity") or item.get("net_quantity") or 0))
            buy_p = float(
                item.get("net_price") or item.get("buy_price") or item.get("average_price") or 0.0
            )
            sell_p = float(item.get("sell_price") or 0.0)
            cur_p = float(item.get("ltp") or item.get("current_price") or buy_p)
            pnl = float(
                item.get("realised_pnl") or item.get("unrealised_pnl") or item.get("pnl") or 0.0
            )
            positions.append(
                GrowwPosition(
                    symbol=sym,
                    quantity=qty,
                    buy_price=round(buy_p, 2),
                    sell_price=round(sell_p, 2),
                    current_price=round(cur_p, 2),
                    pnl=round(pnl, 2),
                    segment=str(item.get("segment") or "CASH"),
                    product_type=str(item.get("product") or item.get("product_type") or "CNC"),
                )
            )
        return positions

    def get_orders(self) -> list[dict[str, Any]]:
        result = self._request_json(
            "GET",
            "/order/list",
            auth=True,
            params={"segment": "CASH", "page": 0, "page_size": 100},
            timeout=10,
        )
        if result.status_code != 200:
            self._last_portfolio_error = (
                result.error or f"Groww orders request failed with HTTP {result.status_code}"
            )
            return []
        return self._extract_collection(self._unwrap_response(result.data), "order_list")

    def sync_to_portfolio_tracker(self, user_id: str = "default_user") -> dict[str, Any]:
        from app.groww_sync import sync_groww_portfolio

        return sync_groww_portfolio(user_id=user_id)

    def get_mutual_funds(self, user_id: str = "default_user") -> list[GrowwMutualFund]:
        from app import db

        db.init_all_tables()
        rows = db.fetchall(
            """
            SELECT folio_id, scheme_name, folio_number, units, nav,
                   invested_amount, current_value, pnl, pnl_pct, asset_category, last_updated
            FROM user_mutual_funds
            WHERE user_id = %s
            ORDER BY current_value DESC;
            """,
            (user_id,),
        )
        return [GrowwMutualFund(**row) for row in rows]

    def get_portfolio_overview(self, user_id: str = "default_user") -> GrowwPortfolioOverview:
        status = self.get_connection_status()
        margin = self.get_user_margin()
        holdings = self.get_holdings()
        mfs = self.get_mutual_funds(user_id=user_id)

        equity_inv = sum(h.invested_amount for h in holdings)
        equity_val = sum(h.current_value for h in holdings)
        equity_pnl = equity_val - equity_inv
        equity_pct = round((equity_pnl / equity_inv * 100) if equity_inv > 0 else 0.0, 2)

        mf_inv = sum(mf.invested_amount for mf in mfs)
        mf_val = sum(mf.current_value for mf in mfs)
        mf_pnl = mf_val - mf_inv
        avail_cash = margin.available_cash if margin.available_cash > 0 else 0.0
        total_nw = round(equity_val + mf_val + avail_cash, 2)

        return GrowwPortfolioOverview(
            ucc=status.ucc,
            status=status.status,
            total_net_worth=total_nw,
            equity_invested=round(equity_inv, 2),
            equity_current_value=round(equity_val, 2),
            equity_pnl=round(equity_pnl, 2),
            equity_pnl_pct=equity_pct,
            mf_invested=round(mf_inv, 2),
            mf_current_value=round(mf_val, 2),
            mf_pnl=round(mf_pnl, 2),
            available_cash=round(avail_cash, 2),
            total_margin=round(margin.total_margin, 2),
            holdings_count=len(holdings),
            mf_count=len(mfs),
            last_synced_at=status.last_synced_at or datetime.now(timezone.utc).isoformat(),
            scope_warning=self._scope_warning,
        )

    def auto_sync_if_configured(self, user_id: str = "default_user") -> dict[str, Any]:
        from app.groww_sync import sync_groww_portfolio

        if not self.is_configured():
            return {"status": "SKIPPED", "reason": "Not configured"}
        try:
            return sync_groww_portfolio(user_id=user_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Auto-sync background job encountered an issue: %s", exc)
            return {"status": "ERROR", "reason": str(exc)}

    def place_order(self, *args: Any, **kwargs: Any) -> None:
        raise RuntimeError(
            "Order execution via Groww API is strictly prohibited by platform policy (ADR-002, ADR-035). "
            "TrAId is a decision-support system. Use 1-click GTT parameters in Zerodha/Groww manually."
        )

    def modify_order(self, *args: Any, **kwargs: Any) -> None:
        raise RuntimeError(
            "Order modification via Groww API is strictly prohibited by platform policy."
        )

    def cancel_order(self, *args: Any, **kwargs: Any) -> None:
        raise RuntimeError(
            "Order cancellation via Groww API is strictly prohibited by platform policy."
        )


_groww_client: GrowwClient | None = None


def get_groww_client() -> GrowwClient:
    global _groww_client
    if _groww_client is None:
        _groww_client = GrowwClient()
    return _groww_client
