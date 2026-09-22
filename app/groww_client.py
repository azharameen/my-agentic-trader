"""Groww Broker API Read-Only Client (ADR-002, ADR-035).

Provides strict read-only access to Groww Trading/Cloud APIs for:
1. Fetching available Demat cash/collateral balance.
2. Fetching live Demat equity holdings and open positions.
3. Inspecting order history and GTT execution states.
4. Auto-synchronizing real-world holdings into TrAId's portfolio monitor.

HARD INVARIANT: Live order placement, modification, and cancellation are
strictly blocked with explicit runtime exceptions.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import requests
from pydantic import BaseModel, Field

from config.settings import get_settings

logger = logging.getLogger(__name__)

GROWW_BASE_URL = "https://api.groww.in/v1"


class GrowwBalance(BaseModel):
    """Normalized Groww margin and cash balances."""

    available_cash: float = 0.0
    collateral_margin: float = 0.0
    used_margin: float = 0.0
    total_margin: float = 0.0
    currency: str = "INR"
    raw: dict[str, Any] = Field(default_factory=dict)


class GrowwHolding(BaseModel):
    """Normalized Groww Demat holding."""

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
    """Normalized Groww open position."""

    symbol: str
    quantity: int = 0
    buy_price: float = 0.0
    sell_price: float = 0.0
    current_price: float = 0.0
    pnl: float = 0.0
    segment: str = "CASH"
    product_type: str = "CNC"


class GrowwMutualFund(BaseModel):
    """Normalized Mutual Fund folio asset."""

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
    """Aggregated multi-asset Net Worth overview for Demat & Mutual Funds."""

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
    """Diagnostic status for Groww API connection."""

    configured: bool = False
    authenticated: bool = False
    status: str = "NOT_CONFIGURED"  # CONNECTED | NOT_CONFIGURED | ERROR
    message: str = ""
    last_synced_at: str = ""
    ucc: str = ""


class GrowwClient:
    """Read-only client for Groww Trading/Cloud API."""

    def __init__(self) -> None:
        self._cached_token: str | None = None
        self._token_expiry_epoch: float = 0.0
        self._last_error_message: str = ""
        self._scope_warning: str = ""
        self._instruments_cache: Any = None
        self._instruments_cache_expiry: float = 0.0

    def is_configured(self) -> bool:
        """Check if minimum Groww credentials are provided in settings."""
        settings = get_settings()
        has_token = bool(settings.GROWW_ACCESS_TOKEN and settings.GROWW_ACCESS_TOKEN.get_secret_value().strip())
        has_key_secret = bool(
            settings.GROWW_API_KEY
            and settings.GROWW_API_KEY.get_secret_value().strip()
        )
        return settings.GROWW_ENABLED and (has_token or has_key_secret)

    def get_auth_token(self) -> str | None:
        """Retrieve or generate valid Groww access token.

        Supports direct token override, direct JWT key, approval checksum,
        or dynamic TOTP generation.
        """
        settings = get_settings()
        if not self.is_configured():
            return None

        # 1. Direct access token override
        if settings.GROWW_ACCESS_TOKEN and settings.GROWW_ACCESS_TOKEN.get_secret_value().strip():
            return settings.GROWW_ACCESS_TOKEN.get_secret_value().strip()

        # 2. Cached in-memory token validity check
        now_ts = datetime.now(timezone.utc).timestamp()
        if self._cached_token and now_ts < self._token_expiry_epoch:
            return self._cached_token

        api_key = settings.GROWW_API_KEY.get_secret_value().strip() if settings.GROWW_API_KEY else ""
        secret = settings.GROWW_API_SECRET.get_secret_value().strip() if settings.GROWW_API_SECRET else ""

        if not api_key:
            return None

        # 3. If API Key itself is a valid JWT access token
        if api_key.startswith("eyJ") and len(api_key) > 100:
            return api_key

        # 4. Try Groww Approval Key / Secret exchange
        if secret:
            try:
                from growwapi import GrowwAPI

                token = GrowwAPI.get_access_token(api_key=api_key, secret=secret)
                if token:
                    self._cached_token = str(token)
                    self._token_expiry_epoch = now_ts + (12 * 3600)
                    self._last_error_message = ""
                    logger.info("Successfully generated Groww access token via approval secret.")
                    return self._cached_token
            except Exception as exc:  # noqa: BLE001
                err_str = str(exc)
                logger.warning("Groww approval token exchange failed: %s", err_str)
                if "Session approval required" in err_str or "403" in err_str:
                    self._last_error_message = (
                        "Session approval required: please approve the authorization request in your "
                        "Groww mobile app, or provide GROWW_ACCESS_TOKEN directly in .env."
                    )
                else:
                    self._last_error_message = f"Approval token exchange failed: {err_str}"

            # 5. Try TOTP exchange if secret is a base32 TOTP secret or 6-digit OTP
            try:
                from growwapi import GrowwAPI

                current_otp = ""
                if len(secret) == 6 and secret.isdigit():
                    current_otp = secret
                else:
                    import pyotp

                    totp = pyotp.TOTP(secret)
                    current_otp = totp.now()

                if current_otp:
                    token = GrowwAPI.get_access_token(api_key=api_key, totp=current_otp)
                    if token:
                        self._cached_token = str(token)
                        self._token_expiry_epoch = now_ts + (12 * 3600)
                        self._last_error_message = ""
                        logger.info("Successfully generated Groww access token via TOTP.")
                        return self._cached_token
            except Exception as exc:  # noqa: BLE001
                logger.debug("Groww TOTP exchange attempted and failed: %s", exc)

        return None

    def _get_headers(self) -> dict[str, str] | None:
        token = self.get_auth_token()
        if not token:
            return None
        import uuid

        return {
            "x-request-id": str(uuid.uuid4()),
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "x-client-id": "growwapi",
            "x-client-platform": "growwapi-python-client",
            "x-client-platform-version": "1.5.0",
            "x-api-version": "1.0",
        }

    def get_connection_status(self) -> GrowwStatus:
        """Return diagnostic health check of the Groww API connection."""
        if not self.is_configured():
            return GrowwStatus(
                configured=False,
                authenticated=False,
                status="NOT_CONFIGURED",
                message="Groww API is disabled or credentials are missing in configuration.",
            )

        token = self.get_auth_token()
        if not token:
            msg = (
                self._last_error_message
                or "Failed to generate authentication token with configured API key/secret."
            )
            return GrowwStatus(
                configured=True,
                authenticated=False,
                status="ERROR",
                message=msg,
            )

        # Verify token by fetching profile or margin details
        try:
            headers = self._get_headers()
            resp = requests.get(f"{GROWW_BASE_URL}/user/profile", headers=headers, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                ucc = ""
                if isinstance(data, dict):
                    success_data = data.get("success", {}).get("data", {}) if isinstance(data.get("success"), dict) else {}
                    ucc = success_data.get("ucc") or data.get("ucc") or ""

                ucc_str = f" (UCC: {ucc})" if ucc else ""
                return GrowwStatus(
                    configured=True,
                    authenticated=True,
                    status="CONNECTED",
                    message=f"Successfully authenticated and connected to Groww Cloud API{ucc_str}.",
                    last_synced_at=datetime.now(timezone.utc).isoformat(),
                )

            # Fallback check
            resp = requests.get(f"{GROWW_BASE_URL}/margins/detail/user", headers=headers, timeout=8)
            if resp.status_code == 200:
                return GrowwStatus(
                    configured=True,
                    authenticated=True,
                    status="CONNECTED",
                    message="Successfully authenticated and connected to Groww Cloud API.",
                    last_synced_at=datetime.now(timezone.utc).isoformat(),
                )
            return GrowwStatus(
                configured=True,
                authenticated=False,
                status="ERROR",
                message=f"Groww API returned HTTP {resp.status_code}: {resp.text[:120]}",
            )
        except Exception as exc:  # noqa: BLE001
            return GrowwStatus(
                configured=True,
                authenticated=False,
                status="ERROR",
                message=f"Connection error reaching Groww API: {exc}",
            )

    def get_user_margin(self) -> GrowwBalance:
        """Fetch real-time available cash and margin balances from Groww."""
        headers = self._get_headers()
        if not headers:
            return GrowwBalance()

        try:
            resp = requests.get(f"{GROWW_BASE_URL}/margins/detail/user", headers=headers, timeout=10)
            if resp.status_code != 200:
                resp = requests.get(f"{GROWW_BASE_URL}/margins/user", headers=headers, timeout=10)

            if resp.status_code == 200:
                data = resp.json()
                # Parse standard Groww margin structure
                equity_margin = data.get("equity") or data.get("cash") or data
                avail = float(
                    equity_margin.get("available_cash")
                    or equity_margin.get("net_margin_available")
                    or equity_margin.get("available_balance")
                    or 0.0
                )
                collateral = float(equity_margin.get("collateral") or equity_margin.get("pledge_margin") or 0.0)
                used = float(equity_margin.get("used_margin") or equity_margin.get("utilised_margin") or 0.0)
                total = float(equity_margin.get("total_margin") or (avail + used))

                return GrowwBalance(
                    available_cash=round(avail, 2),
                    collateral_margin=round(collateral, 2),
                    used_margin=round(used, 2),
                    total_margin=round(total, 2),
                    raw=data,
                )
            logger.warning("Failed to fetch Groww margin. Status: %d", resp.status_code)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Error fetching Groww user margin: %s", exc)

        return GrowwBalance()

    # ------------------------------------------------------------------ #
    # Read-Only Live Data, Historical Data, Margin & Instruments (ADR-036)
    # ------------------------------------------------------------------ #
    def _get_sdk_client(self) -> Any:
        """Lazily build a `growwapi.GrowwAPI` SDK instance from the current token.

        Used for the newer read-only endpoints (quotes, LTP, OHLC, historical
        candles, structured margin, instruments) where the official SDK is the
        most reliable way to hit the correct endpoint/schema.
        """
        token = self.get_auth_token()
        if not token:
            return None
        try:
            from growwapi import GrowwAPI

            return GrowwAPI(token)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Could not build Groww SDK client: %s", exc)
            return None

    def get_available_margin_details(self) -> dict[str, Any]:
        """Fetch structured available margin (clear cash, CNC/F&O balances)."""
        sdk = self._get_sdk_client()
        if not sdk:
            return {}
        try:
            return dict(sdk.get_available_margin_details() or {})
        except Exception as exc:  # noqa: BLE001
            logger.warning("Error fetching Groww available margin details: %s", exc)
            return {}

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
        """Estimate margin/fund requirement for a single proposed order (informational only).

        This never places an order; it is purely a read-only fund-requirement
        estimate surfaced to the human approver alongside a trade proposal.
        """
        sdk = self._get_sdk_client()
        if not sdk:
            return {}
        try:
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
            return dict(
                sdk.get_order_margin_details(segment=segment, orders=[order]) or {}
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Error fetching Groww order margin estimate for %s: %s", trading_symbol, exc)
            return {}

    def get_quote(self, trading_symbol: str, exchange: str = "NSE", segment: str = "CASH") -> dict[str, Any]:
        """Fetch a full real-time quote (LTP, OHLC, depth, circuit limits) for one instrument."""
        sdk = self._get_sdk_client()
        if not sdk:
            return {}
        try:
            return dict(
                sdk.get_quote(exchange=exchange, segment=segment, trading_symbol=trading_symbol) or {}
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Error fetching Groww quote for %s: %s", trading_symbol, exc)
            return {}

    def get_ltp(self, symbols: list[str], exchange: str = "NSE", segment: str = "CASH") -> dict[str, float]:
        """Fetch last traded price for up to 50 instruments per call, batching if needed."""
        sdk = self._get_sdk_client()
        if not sdk or not symbols:
            return {}
        results: dict[str, float] = {}
        batch_size = 50
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i : i + batch_size]
            tickers = tuple(f"{exchange}_{sym}" for sym in batch)
            try:
                resp = sdk.get_ltp(segment=segment, exchange_trading_symbols=tickers)
                if isinstance(resp, dict):
                    results.update({k: float(v) for k, v in resp.items()})
            except Exception as exc:  # noqa: BLE001
                logger.warning("Error fetching Groww LTP batch (%d symbols): %s", len(batch), exc)
        return results

    def get_ohlc(self, symbols: list[str], exchange: str = "NSE", segment: str = "CASH") -> dict[str, dict[str, float]]:
        """Fetch real-time OHLC snapshot for up to 50 instruments per call, batching if needed."""
        sdk = self._get_sdk_client()
        if not sdk or not symbols:
            return {}
        results: dict[str, dict[str, float]] = {}
        batch_size = 50
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i : i + batch_size]
            tickers = tuple(f"{exchange}_{sym}" for sym in batch)
            try:
                resp = sdk.get_ohlc(segment=segment, exchange_trading_symbols=tickers)
                if isinstance(resp, dict):
                    results.update(resp)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Error fetching Groww OHLC batch (%d symbols): %s", len(batch), exc)
        return results

    def get_historical_candle_data(
        self,
        trading_symbol: str,
        start_time: str,
        end_time: str,
        interval_in_minutes: int = 1440,
        exchange: str = "NSE",
        segment: str = "CASH",
    ) -> dict[str, Any]:
        """Fetch historical OHLCV candles for one instrument (daily bars by default).

        ponytail: uses the legacy `get_historical_candle_data` (V1) endpoint on
        purpose — it supports up to 1080 days per request, which the cold-start
        full-history fetch in `market_data.load_history` needs for 1y/2y EMA-200
        indicators. The newer `get_historical_candles` (V2) caps at 180 days per
        request, so switching over requires a pagination loop. Migrate + paginate
        when the SDK actually removes the V1 endpoint.
        """
        sdk = self._get_sdk_client()
        if not sdk:
            return {}
        try:
            return dict(
                sdk.get_historical_candle_data(
                    trading_symbol=trading_symbol,
                    exchange=exchange,
                    segment=segment,
                    start_time=start_time,
                    end_time=end_time,
                    interval_in_minutes=interval_in_minutes,
                )
                or {}
            )
        except Exception as exc:  # noqa: BLE001
            logger.info("Groww historical candles unavailable for %s: %s", trading_symbol, exc)
            return {}

    def get_all_instruments(self) -> Any:
        """Fetch the full instruments master (cached in-memory for 24h)."""
        now_ts = datetime.now(timezone.utc).timestamp()
        if self._instruments_cache is not None and now_ts < self._instruments_cache_expiry:
            return self._instruments_cache
        sdk = self._get_sdk_client()
        if not sdk:
            return None
        try:
            df = sdk.get_all_instruments()
            self._instruments_cache = df
            self._instruments_cache_expiry = now_ts + (24 * 3600)
            return df
        except Exception as exc:  # noqa: BLE001
            logger.warning("Error fetching Groww instruments master: %s", exc)
            return self._instruments_cache

    def get_instrument_by_groww_symbol(self, groww_symbol: str) -> dict[str, Any]:
        """Look up a single instrument's lot size / tick size / ISIN by its Groww symbol."""
        sdk = self._get_sdk_client()
        if not sdk:
            return {}
        try:
            return dict(sdk.get_instrument_by_groww_symbol(groww_symbol=groww_symbol) or {})
        except Exception as exc:  # noqa: BLE001
            logger.debug("Could not resolve Groww instrument %s: %s", groww_symbol, exc)
            return {}

    def get_holdings(self) -> list[GrowwHolding]:
        """Fetch user's Demat equity holdings normalized to standard symbols."""
        headers = self._get_headers()
        if not headers:
            return []

        try:
            resp = requests.get(f"{GROWW_BASE_URL}/holdings/user", headers=headers, timeout=10)
            if resp.status_code == 200:
                raw_holdings = resp.json()
                if isinstance(raw_holdings, dict):
                    raw_holdings = raw_holdings.get("holdings") or raw_holdings.get("results") or []

                holdings: list[GrowwHolding] = []
                for item in raw_holdings:
                    if not isinstance(item, dict):
                        continue
                    sym = (
                        item.get("trading_symbol")
                        or item.get("symbol")
                        or item.get("nse_symbol")
                        or item.get("scrip_code")
                        or ""
                    )
                    sym = sym.replace(".NS", "").strip().upper()
                    if not sym:
                        continue

                    qty = int(item.get("quantity") or item.get("net_quantity") or item.get("total_qty") or 0)
                    if qty <= 0:
                        continue

                    avg_p = float(item.get("average_price") or item.get("avg_cost_price") or item.get("avg_price") or 0.0)
                    cur_p = float(item.get("ltp") or item.get("close_price") or item.get("current_price") or avg_p)
                    inv = float(item.get("invested_amount") or (qty * avg_p))
                    val = float(item.get("current_value") or (qty * cur_p))
                    pnl = float(item.get("pnl") or (val - inv))
                    pnl_pct = float(item.get("pnl_percentage") or ((pnl / inv * 100) if inv > 0 else 0.0))

                    holdings.append(
                        GrowwHolding(
                            symbol=sym,
                            company_name=str(item.get("company_name") or item.get("scrip_name") or sym),
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
            if resp.status_code == 403:
                self._scope_warning = (
                    "Groww API returned 403 Forbidden for Demat holdings. "
                    "Please ensure the 'Read Holdings' permission scope is enabled in your Groww Developer Console."
                )
            logger.warning("Failed to fetch Groww holdings. Status: %d", resp.status_code)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Error fetching Groww holdings: %s", exc)

        return []

    def get_positions(self) -> list[GrowwPosition]:
        """Fetch user's open positions from Groww."""
        headers = self._get_headers()
        if not headers:
            return []

        try:
            resp = requests.get(f"{GROWW_BASE_URL}/positions/user", headers=headers, timeout=10)
            if resp.status_code == 200:
                raw_positions = resp.json()
                if isinstance(raw_positions, dict):
                    raw_positions = raw_positions.get("positions") or raw_positions.get("results") or []

                positions: list[GrowwPosition] = []
                for item in raw_positions:
                    if not isinstance(item, dict):
                        continue
                    sym = (
                        item.get("trading_symbol")
                        or item.get("symbol")
                        or item.get("nse_symbol")
                        or ""
                    )
                    sym = sym.replace(".NS", "").strip().upper()
                    if not sym:
                        continue

                    qty = int(item.get("quantity") or item.get("net_quantity") or 0)
                    buy_p = float(item.get("buy_price") or item.get("average_price") or 0.0)
                    sell_p = float(item.get("sell_price") or 0.0)
                    cur_p = float(item.get("ltp") or item.get("current_price") or buy_p)
                    pnl = float(item.get("pnl") or item.get("unrealised_pnl") or 0.0)

                    positions.append(
                        GrowwPosition(
                            symbol=sym,
                            quantity=qty,
                            buy_price=round(buy_p, 2),
                            sell_price=round(sell_p, 2),
                            current_price=round(cur_p, 2),
                            pnl=round(pnl, 2),
                            segment=str(item.get("segment") or "CASH"),
                            product_type=str(item.get("product_type") or "CNC"),
                        )
                    )
                return positions
        except Exception as exc:  # noqa: BLE001
            logger.warning("Error fetching Groww positions: %s", exc)

        return []

    def get_orders(self) -> list[dict[str, Any]]:
        """Fetch user's order book / history from Groww."""
        headers = self._get_headers()
        if not headers:
            return []

        try:
            resp = requests.get(f"{GROWW_BASE_URL}/orders/user", headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    return data
                if isinstance(data, dict):
                    return list(data.get("orders") or data.get("results") or [])
        except Exception as exc:  # noqa: BLE001
            logger.warning("Error fetching Groww orders: %s", exc)

        return []

    def sync_to_portfolio_tracker(self, user_id: str = "default_user") -> dict[str, Any]:
        """Sync Groww Demat holdings into TrAId active user positions.

        Adds any untracked Groww holdings to TrAId's portfolio monitor
        with automated break-even and 2-tranche profit targets.
        """
        import uuid
        from app import db, portfolio_manager

        holdings = self.get_holdings()
        if not holdings:
            return {
                "synced_count": 0,
                "holdings_found": 0,
                "message": "No Demat holdings found in Groww or Groww API not connected.",
            }

        db.init_all_tables()
        existing_summary = portfolio_manager.get_user_portfolio(user_id=user_id)
        existing_symbols = {pos.symbol for pos in existing_summary.active_positions} if existing_summary else set()

        portfolio_id = existing_summary.portfolio_id if existing_summary else f"groww-sync-{uuid.uuid4().hex[:8]}"
        now_utc = datetime.now(timezone.utc).isoformat()

        if not existing_summary:
            db.execute(
                """
                INSERT INTO user_portfolios (
                    portfolio_id, user_id, created_at, initial_capital,
                    allocated_capital, cash_balance, risk_vibe, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (portfolio_id) DO NOTHING;
                """,
                (portfolio_id, user_id, now_utc, 100000.0, 0.0, 100000.0, "BALANCED", "ACTIVE"),
            )

        synced_count = 0
        for h in holdings:
            if h.symbol in existing_symbols:
                continue  # Already being tracked

            entry_p = h.avg_price if h.avg_price > 0 else h.current_price
            stop_loss = round(entry_p * 0.94, 2)  # -6% default safety stop
            t1 = round(entry_p * 1.08, 2)
            t2 = round(entry_p * 1.16, 2)
            t1_shares = h.quantity // 2
            t2_shares = h.quantity - t1_shares
            pos_id = f"pos-{uuid.uuid4().hex[:8]}"

            db.execute(
                """
                INSERT INTO user_positions (
                    position_id, portfolio_id, user_id, symbol, company_name,
                    shares, suggested_price, entry_price, current_price,
                    stop_loss_price, target_price, target2_price, target1_shares,
                    target2_shares, status, filled_at, highest_price, trailing_stop,
                    broker_name, sector, tranche1_exited, breakeven_locked
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                """,
                (
                    pos_id,
                    portfolio_id,
                    user_id,
                    h.symbol,
                    h.company_name,
                    h.quantity,
                    entry_p,
                    entry_p,
                    h.current_price or entry_p,
                    stop_loss,
                    t1,
                    t2,
                    t1_shares,
                    t2_shares,
                    "ACTIVE",
                    now_utc,
                    h.current_price or entry_p,
                    stop_loss,
                    "Groww",
                    "Diversified",
                    False,
                    False,
                ),
            )
            synced_count += 1

        return {
            "synced_count": synced_count,
            "holdings_found": len(holdings),
            "message": f"Successfully synced {synced_count} new holdings from Groww Demat into TrAId portfolio monitor.",
        }

    def get_mutual_funds(self, user_id: str = "default_user") -> list[GrowwMutualFund]:
        """Fetch user's mutual fund folios from database and Groww sync."""
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
        if rows:
            return [GrowwMutualFund(**row) for row in rows]
        return []

    def get_portfolio_overview(self, user_id: str = "default_user") -> GrowwPortfolioOverview:
        """Aggregate Demat equities, mutual funds, and cash balances into complete Net Worth."""
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
            ucc=status.ucc or "9541339548",
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
        """Safe non-blocking auto-sync for background jobs and boot initialization."""
        if not self.is_configured():
            return {"status": "SKIPPED", "reason": "Not configured"}
        try:
            return self.sync_to_portfolio_tracker(user_id=user_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Auto-sync background job encountered an issue: %s", exc)
            return {"status": "ERROR", "reason": str(exc)}

    # ------------------------------------------------------------------ #
    # Strict Fail-Closed Live Order Invariants (ADR-002, ADR-035)
    # ------------------------------------------------------------------ #
    def place_order(self, *args: Any, **kwargs: Any) -> None:
        """Prohibited: Live order placement via Groww is strictly disabled."""
        raise RuntimeError(
            "Order execution via Groww API is strictly prohibited by platform policy (ADR-002, ADR-035). "
            "TrAId is a decision-support system. Use 1-click GTT parameters in Zerodha/Groww manually."
        )

    def modify_order(self, *args: Any, **kwargs: Any) -> None:
        """Prohibited: Live order modification via Groww is strictly disabled."""
        raise RuntimeError("Order modification via Groww API is strictly prohibited by platform policy.")

    def cancel_order(self, *args: Any, **kwargs: Any) -> None:
        """Prohibited: Live order cancellation via Groww is strictly disabled."""
        raise RuntimeError("Order cancellation via Groww API is strictly prohibited by platform policy.")


_groww_client: GrowwClient | None = None


def get_groww_client() -> GrowwClient:
    """Return the singleton GrowwClient instance."""
    global _groww_client
    if _groww_client is None:
        _groww_client = GrowwClient()
    return _groww_client
