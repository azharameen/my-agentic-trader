"""FastAPI Backend for TrAId Full-Featured Interactive Web Application.

Provides comprehensive REST and Server-Sent Events (SSE) endpoints for:
- Command Cockpit (live overview, pending proposals with approvals/rejections, active positions with manual exit)
- AI Research Copilot with real-time token streaming and tool trace inspection
- Candlestick OHLCV data for TradingView Lightweight Charts with technical indicators
- Historical trade audit log and Alpha performance vs NIFTY 100 benchmark
- Event-driven walk-forward backtester simulation
- Universe constituent management and live scan/run workflow triggers
- Real-time SSE event bus for scan progress and proposal updates
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import (
    backtester,
    basket_generator,
    chat_agent,
    db,
    digest_generator,
    evaluation,
    events,
    executor,
    groww_client,
    health,
    market_data,
    models_basket,
    pipeline,
    portfolio_manager,
    proposals,
    regime,
    screener,
    universe,
)
from config.settings import get_settings

logger = logging.getLogger(__name__)

app = FastAPI(
    title="TrAId Web Application API",
    description="Primary Interactive Control Cockpit and AI Research Assistant for NIFTY 100 Swing Trading.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"
FRONTEND_DIST_DIR = Path(__file__).parent.parent / "frontend" / "dist"


# --------------------------------------------------------------------------- #
# Request & Response Models
# --------------------------------------------------------------------------- #
class BacktestRequest(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    initial_capital: Optional[float] = None
    symbols: Optional[list[str]] = None


class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None


class ApproveProposalRequest(BaseModel):
    notes: Optional[str] = "Approved via Web Cockpit"


class RejectProposalRequest(BaseModel):
    reason: Optional[str] = "Rejected by operator via Web Cockpit"


class ClosePositionRequest(BaseModel):
    exit_price: Optional[float] = None
    reason: Optional[str] = "MANUAL_WEB_EXIT"


class RunSymbolRequest(BaseModel):
    symbol: str


# --------------------------------------------------------------------------- #
# System & Overview Endpoints
# --------------------------------------------------------------------------- #
@app.get("/api/health")
def get_health() -> dict[str, Any]:
    """System health, PostgreSQL pool status, and scheduler state."""
    return health.get_summary()


@app.get("/api/overview")
def get_overview() -> dict[str, Any]:
    """Summary overview metrics for the top dashboard ribbon."""
    settings = get_settings()
    trades = executor.fetch_all_trades()
    open_trades = [t for t in trades if t["status"] == "OPEN_PAPER"]
    closed_trades = [t for t in trades if t["status"] == "CLOSED"]

    total_capital = executor.get_current_capital()
    total_realized_pnl = sum(t.get("realized_pnl") or 0.0 for t in closed_trades)

    total_risk_stake = 0.0
    total_unrealized_pnl = 0.0

    for t in open_trades:
        symbol = t["symbol"]
        fill = float(t.get("fill_price") or t.get("entry_price") or 0.0)
        qty = int(t.get("quantity") or 0)
        hard_stop = float(t.get("hard_stop") or 0.0)

        snapshot = screener.get_symbol_snapshot(symbol)
        curr = float(snapshot["daily_close"]) if snapshot else fill

        unrealized = (curr - fill) * qty
        risk_amt = max(0.0, (fill - hard_stop) * qty)

        total_unrealized_pnl += unrealized
        total_risk_stake += risk_amt

    heat_pct = (total_risk_stake / total_capital * 100) if total_capital > 0 else 0.0
    regime_info = regime.get_regime_assessment()
    pending_props = proposals.fetch_pending_proposals()

    return {
        "trading_mode": settings.TRADING_MODE,
        "base_capital": settings.PORTFOLIO_CAPITAL,
        "current_capital": round(total_capital, 2),
        "total_equity": round(total_capital + total_unrealized_pnl, 2),
        "total_realized_pnl": round(total_realized_pnl, 2),
        "total_unrealized_pnl": round(total_unrealized_pnl, 2),
        "open_positions_count": len(open_trades),
        "pending_proposals_count": len(pending_props),
        "total_trades_count": len(trades),
        "portfolio_heat_pct": round(heat_pct, 2),
        "max_portfolio_heat_pct": 15.0,
        "risk_per_trade_pct": settings.RISK_PER_TRADE_PCT * 100,
        "market_regime": {
            "vix": regime_info.vix,
            "nifty_close": regime_info.nifty_close,
            "nifty_ema_50": regime_info.nifty_ema_50,
            "allow_new_entries": regime_info.allow_new_entries,
            "risk_multiplier": regime_info.risk_multiplier,
            "reasons": regime_info.reasons,
        },
        "server_time": datetime.now(timezone.utc).isoformat(),
    }


# --------------------------------------------------------------------------- #
# Pending Proposals & Human-in-the-Loop Approvals
# --------------------------------------------------------------------------- #
@app.get("/api/proposals/pending")
def list_pending_proposals() -> list[dict[str, Any]]:
    """List all trade proposals waiting for operator approval."""
    return proposals.fetch_pending_proposals()


@app.get("/api/proposals/{proposal_id}")
def get_proposal_details(proposal_id: str) -> dict[str, Any]:
    """Retrieve details and qualitative agent debate breakdown for a proposal."""
    prop = proposals.fetch_proposal_by_id(proposal_id)
    if not prop:
        raise HTTPException(status_code=404, detail=f"Proposal {proposal_id} not found.")
    return prop


@app.post("/api/proposals/{proposal_id}/approve")
def approve_proposal_endpoint(proposal_id: str, req: Optional[ApproveProposalRequest] = None) -> dict[str, Any]:
    """Approve a pending trade proposal and execute paper fill."""
    notes = req.notes if req and req.notes else "Approved via Web Cockpit"
    try:
        res = proposals.approve_proposal(proposal_id, notes=notes)
        return res
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to approve proposal %s", proposal_id)
        raise HTTPException(status_code=500, detail=f"Failed to approve proposal: {exc}") from exc


@app.post("/api/proposals/{proposal_id}/reject")
def reject_proposal_endpoint(proposal_id: str, req: Optional[RejectProposalRequest] = None) -> dict[str, Any]:
    """Reject a pending trade proposal with reason."""
    reason = req.reason if req and req.reason else "Rejected by operator"
    try:
        res = proposals.reject_proposal(proposal_id, reason=reason)
        return res
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to reject proposal %s", proposal_id)
        raise HTTPException(status_code=500, detail=f"Failed to reject proposal: {exc}") from exc


# --------------------------------------------------------------------------- #
# Positions & Trade Execution
# --------------------------------------------------------------------------- #
@app.get("/api/positions")
def get_positions() -> list[dict[str, Any]]:
    """List all active open paper positions with live P&L and risk markers."""
    trades = executor.fetch_all_trades()
    open_trades = [t for t in trades if t["status"] == "OPEN_PAPER"]

    results = []
    for t in open_trades:
        symbol = t["symbol"]
        fill = float(t.get("fill_price") or t.get("entry_price") or 0.0)
        qty = int(t.get("quantity") or 0)
        soft_stop = float(t.get("soft_stop") or 0.0)
        hard_stop = float(t.get("hard_stop") or 0.0)
        target = float(t.get("target_price") or 0.0)
        strategy = t.get("strategy_name") or "PULLBACK"

        snapshot = screener.get_symbol_snapshot(symbol)
        curr = float(snapshot["daily_close"]) if snapshot else fill

        unrealized_pnl = round((curr - fill) * qty, 2)
        unrealized_pct = round(((curr - fill) / fill * 100), 2) if fill > 0 else 0.0
        stop_dist_pct = round(((curr - hard_stop) / curr * 100), 2) if curr > 0 else 0.0
        target_dist_pct = round(((target - curr) / curr * 100), 2) if curr > 0 else 0.0
        risk_amt = round(max(0.0, (fill - hard_stop) * qty), 2)

        results.append({
            "trade_id": t["trade_id"],
            "symbol": symbol,
            "entry_date": t["timestamp"],
            "fill_price": fill,
            "current_price": curr,
            "quantity": qty,
            "soft_stop": soft_stop,
            "hard_stop": hard_stop,
            "target_price": target,
            "strategy_name": strategy,
            "unrealized_pnl": unrealized_pnl,
            "unrealized_pnl_pct": unrealized_pct,
            "stop_dist_pct": stop_dist_pct,
            "target_dist_pct": target_dist_pct,
            "risk_amount": risk_amt,
            "thesis": t.get("thesis", ""),
        })

    return results


@app.post("/api/positions/{trade_id}/close")
def close_position_endpoint(trade_id: str, req: Optional[ClosePositionRequest] = None) -> dict[str, Any]:
    """Manually exit/close an open paper trade early at market price."""
    trades = executor.fetch_all_trades()
    trade = next((t for t in trades if t["trade_id"] == trade_id), None)
    if not trade:
        raise HTTPException(status_code=404, detail=f"Trade {trade_id} not found.")

    if trade["status"] != "OPEN_PAPER":
        raise HTTPException(status_code=400, detail=f"Trade {trade_id} is already {trade['status']}.")

    symbol = trade["symbol"]
    snapshot = screener.get_symbol_snapshot(symbol)
    exit_price = req.exit_price if req and req.exit_price else (snapshot["daily_close"] if snapshot else trade["fill_price"])
    reason = req.reason if req and req.reason else "MANUAL_WEB_EXIT"

    try:
        closed = executor.close_trade(trade_id, exit_price=exit_price, mistake_category=reason)
        events.broadcast_event(
            "POSITION_CLOSED",
            {"trade_id": trade_id, "symbol": symbol, "exit_price": exit_price, "realized_pnl": closed["realized_pnl"]},
        )
        return closed
    except Exception as exc:
        logger.exception("Failed to close position %s", trade_id)
        raise HTTPException(status_code=500, detail=f"Failed to close trade: {exc}") from exc


@app.get("/api/trades")
def get_trades(status: Optional[str] = None) -> list[dict[str, Any]]:
    """Historical trade audit log with optional status filtering (OPEN_PAPER, CLOSED)."""
    trades = executor.fetch_all_trades()
    if status:
        trades = [t for t in trades if t["status"].upper() == status.upper()]
    return trades


@app.get("/api/performance")
def get_performance() -> dict[str, Any]:
    """Performance metrics scorecard against NIFTY 100 Buy & Hold benchmark."""
    trades = executor.fetch_all_trades()
    summary = evaluation.summarize_trades(trades)
    return {
        "closed_count": summary.get("closed_trades", 0),
        "open_count": summary.get("open_trades", 0),
        "gross_pnl": summary.get("gross_pnl", 0.0),
        "total_costs": summary.get("transaction_costs", 0.0),
        "net_pnl": summary.get("net_pnl", 0.0),
        "win_rate": summary.get("win_rate", 0.0),
        "expectancy": summary.get("expectancy", 0.0),
        "profit_factor": summary.get("profit_factor"),
        "average_win_r": summary.get("avg_win_r", 0.0),
        "average_loss_r": summary.get("avg_loss_r", 0.0),
        "average_r": summary.get("avg_r_multiple", 0.0),
        "max_drawdown_pct": summary.get("max_drawdown_pct", 0.0),
        "benchmark_return_pct": summary.get("benchmark_return_pct"),
        "strategy_alpha_pct": summary.get("net_alpha_pct"),
        "sample_size_valid": summary.get("sample_size_sufficient", False),
        "confidence_warning": summary.get("sample_size_warning"),
    }


# --------------------------------------------------------------------------- #
# Candlesticks & Technical Data
# --------------------------------------------------------------------------- #
@app.get("/api/candles/{symbol}")
def get_candles(symbol: str) -> list[dict[str, Any]]:
    """Return historical daily OHLCV candles formatted for TradingView Lightweight Charts."""
    clean_sym = symbol.replace(".NS", "").upper()
    try:
        res = market_data.load_history(clean_sym, period="1y", use_cache=True)
        frame = res.frame
        candles = []
        for idx, row in frame.iterrows():
            time_str = str(idx.date() if hasattr(idx, "date") else idx)[:10]
            candles.append({
                "time": time_str,
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
                "volume": int(row["Volume"]),
            })
        return candles
    except Exception as exc:
        logger.exception("Failed to load candles for %s", clean_sym)
        raise HTTPException(status_code=404, detail=f"No candlestick data available for {clean_sym}: {exc}") from exc


@app.get("/api/levels/{symbol}")
def get_symbol_levels(symbol: str) -> dict[str, Any]:
    """Return active price levels (Entry, Target, Soft/Hard Stop, Trailing Stop) for chart overlay (ADR-032)."""
    clean_sym = symbol.replace(".NS", "").upper()
    props = proposals.fetch_pending_proposals()
    prop = next((p for p in props if p["symbol"].upper() == clean_sym), None)

    trades = executor.fetch_all_trades()
    open_trade = next((t for t in trades if t["symbol"].upper() == clean_sym and t["status"] == "OPEN_PAPER"), None)

    if prop:
        return {
            "symbol": clean_sym,
            "source": "PROPOSAL",
            "status": prop.get("status", "PENDING"),
            "entry_price": prop.get("entry_price"),
            "target_price": prop.get("target_price"),
            "soft_stop": prop.get("soft_stop"),
            "hard_stop": prop.get("hard_stop"),
            "trailing_stop": None,
        }
    if open_trade:
        return {
            "symbol": clean_sym,
            "source": "POSITION",
            "status": open_trade.get("status", "OPEN_PAPER"),
            "entry_price": float(open_trade.get("fill_price") or open_trade.get("entry_price") or 0.0),
            "target_price": float(open_trade.get("target_price") or 0.0),
            "soft_stop": float(open_trade.get("soft_stop") or 0.0),
            "hard_stop": float(open_trade.get("hard_stop") or 0.0),
            "trailing_stop": float(open_trade.get("trailing_stop") or 0.0) if open_trade.get("trailing_stop") else None,
        }
    return {
        "symbol": clean_sym,
        "source": None,
        "status": None,
        "entry_price": None,
        "target_price": None,
        "soft_stop": None,
        "hard_stop": None,
        "trailing_stop": None,
    }


# --------------------------------------------------------------------------- #
# Backtest Simulation
# --------------------------------------------------------------------------- #
@app.post("/api/backtest")
def run_backtest_endpoint(req: BacktestRequest) -> dict[str, Any]:
    """Execute event-driven walk-forward backtesting simulation and return equity series."""
    start_date = req.start_date or "2024-01-01"
    end_date = req.end_date or datetime.now().strftime("%Y-%m-%d")
    initial_cap = req.initial_capital or get_settings().PORTFOLIO_CAPITAL
    symbol = req.symbols[0] if req.symbols else "RELIANCE"

    try:
        report = backtester.run_backtest(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_cap,
        )

        return {
            "summary": {
                "initial_capital": report.initial_capital,
                "final_equity": report.final_equity,
                "total_return_pct": report.total_return_pct,
                "total_net_pnl": report.total_net_pnl,
                "sharpe_ratio": report.sharpe_ratio,
                "max_drawdown_pct": report.max_drawdown_pct,
                "profit_factor": report.profit_factor,
                "win_rate": report.win_rate,
                "total_trades": report.total_trades,
                "winning_trades": report.winning_trades,
                "losing_trades": report.losing_trades,
                "average_r": report.average_r,
            },
            "equity_curve": [
                {"time": str(pt.get("date", "")), "equity": pt.get("equity", 0.0), "drawdown_pct": pt.get("drawdown_pct", 0.0)}
                for pt in report.equity_curve
            ],
            "trades": [
                {
                    "trade_id": tr.trade_id,
                    "symbol": tr.symbol,
                    "strategy": tr.strategy_name,
                    "entry_date": tr.entry_date,
                    "exit_date": tr.exit_date,
                    "entry_price": tr.entry_price,
                    "exit_price": tr.exit_price,
                    "quantity": tr.quantity,
                    "net_pnl": tr.net_pnl,
                    "r_multiple": tr.r_multiple,
                    "exit_reason": tr.exit_reason,
                }
                for tr in report.trades
            ],
            "monte_carlo": report.monte_carlo_stats,
        }
    except Exception as exc:
        logger.exception("Backtest execution failed")
        raise HTTPException(status_code=500, detail=f"Backtest failed: {exc}") from exc


# --------------------------------------------------------------------------- #
# Universe & Scan Operations
# --------------------------------------------------------------------------- #
@app.get("/api/universe")
def get_universe_endpoint() -> dict[str, Any]:
    """List active NIFTY 100 universe constituents and cache freshness."""
    symbols = universe.get_universe()
    constituents = universe.get_universe_constituents()
    return {
        "count": len(symbols),
        "symbols": symbols,
        "constituents": constituents,
        "source": "NIFTY_100",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/universe/refresh")
def refresh_universe_endpoint() -> dict[str, Any]:
    """Force a live refresh of NIFTY 100 constituent list from NSE."""
    try:
        symbols = universe.get_universe(force_refresh=True)
        constituents = universe.get_universe_constituents(force_refresh=True)
        return {
            "status": "SUCCESS",
            "count": len(symbols),
            "symbols": symbols,
            "constituents": constituents,
        }
    except Exception as exc:
        logger.exception("Failed to refresh universe")
        raise HTTPException(status_code=500, detail=f"Universe refresh failed: {exc}") from exc


def _run_scan_background() -> None:
    symbols = universe.get_universe()
    try:
        pipeline.run_universe_scan(symbols)
    except Exception:
        logger.exception("Background scan failed")


@app.post("/api/scan")
def trigger_scan_endpoint(background_tasks: BackgroundTasks) -> dict[str, Any]:
    """Trigger a full universe scan across all NIFTY 100 symbols asynchronously."""
    background_tasks.add_task(_run_scan_background)
    return {
        "status": "QUEUED",
        "message": "Universe scan initiated in background. Live progress is streamed via /api/events.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _run_symbol_background(symbol: str) -> None:
    try:
        pipeline.process_symbol(symbol)
    except Exception:
        logger.exception("Background symbol processing failed for %s", symbol)


@app.post("/api/run/{symbol}")
def trigger_run_symbol_endpoint(symbol: str, background_tasks: BackgroundTasks) -> dict[str, Any]:
    """Run a single symbol through the complete multi-agent research pipeline."""
    clean_sym = symbol.replace(".NS", "").upper()
    background_tasks.add_task(_run_symbol_background, clean_sym)
    return {
        "status": "QUEUED",
        "symbol": clean_sym,
        "message": f"Deep analysis for {clean_sym} started. Proposals will appear in Cockpit upon qualification.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# --------------------------------------------------------------------------- #
# Beginner User Journey & Smart Basket Endpoints
# --------------------------------------------------------------------------- #
class ExitPositionRequest(BaseModel):
    position_id: str
    exit_price: float
    shares_to_exit: Optional[int] = None
    user_id: Optional[str] = "default_user"


@app.post("/api/v1/strategy/generate-basket")
def generate_basket_endpoint(req: models_basket.BasketRequest) -> models_basket.StrategyBasket:
    """Generate a risk-diversified, beginner-friendly 3-5 stock investment basket."""
    try:
        basket = basket_generator.generate_strategy_basket(
            capital=req.capital,
            risk_vibe=req.risk_vibe,
            goal=req.goal,
            max_stocks=req.max_stocks,
        )
        portfolio_manager.create_user_portfolio_from_basket(
            basket, user_id=req.user_id or "default_user"
        )
        return basket
    except Exception as exc:
        logger.exception("Failed to generate strategy basket: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/portfolio/confirm-executions")
def confirm_executions_endpoint(req: models_basket.BatchExecutionRequest) -> models_basket.PortfolioSummary:
    """Confirm user execution on broker with actual filled prices and slippage tracking."""
    try:
        summary = portfolio_manager.confirm_batch_execution(req)
        if not summary:
            raise HTTPException(status_code=404, detail="Portfolio not found after execution.")
        return summary
    except Exception as exc:
        logger.exception("Failed to confirm executions: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/v1/portfolio/active-health")
def get_active_portfolio_health_endpoint(user_id: str = "default_user") -> Optional[models_basket.PortfolioSummary]:
    """Fetch active portfolio health, live prices, target progress, and alerts."""
    try:
        return portfolio_manager.get_user_portfolio(user_id=user_id)
    except Exception as exc:
        logger.exception("Failed to fetch active portfolio health: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/v1/portfolio/exit-position")
def exit_position_endpoint(req: ExitPositionRequest) -> models_basket.ReinvestmentSuggestion:
    """Record manual position exit (partial or full), calculate realized P&L, and suggest capital reinvestment."""
    try:
        return portfolio_manager.confirm_position_exit(
            position_id=req.position_id,
            exit_price=req.exit_price,
            shares_to_exit=req.shares_to_exit,
            user_id=req.user_id or "default_user",
        )
    except Exception as exc:
        logger.exception("Failed to exit position: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/v1/digests/morning")
def get_morning_digest_endpoint(user_id: str = "default_user") -> models_basket.DailyDigest:
    """Fetch or generate pre-market morning mood briefing."""
    try:
        return digest_generator.generate_morning_mood_digest(user_id=user_id)
    except Exception as exc:
        logger.exception("Failed to generate morning digest: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/v1/digests/evening")
def get_evening_digest_endpoint(user_id: str = "default_user") -> models_basket.DailyDigest:
    """Fetch or generate post-market evening health report."""
    try:
        return digest_generator.generate_evening_health_digest(user_id=user_id)
    except Exception as exc:
        logger.exception("Failed to generate evening digest: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# --------------------------------------------------------------------------- #
# Groww Broker Integration (Read-Only, ADR-035)
# --------------------------------------------------------------------------- #
@app.get("/api/v1/groww/status")
def get_groww_status_endpoint() -> groww_client.GrowwStatus:
    """Check connectivity and authentication status with Groww Trading/Cloud API."""
    client = groww_client.get_groww_client()
    # Trigger non-blocking auto-sync if configured
    if client.is_configured():
        try:
            client.auto_sync_if_configured()
        except Exception:  # noqa: BLE001
            pass
    return client.get_connection_status()


@app.get("/api/v1/groww/balance")
def get_groww_balance_endpoint() -> groww_client.GrowwBalance:
    """Fetch real-time available cash and margin balance from Groww Demat account."""
    client = groww_client.get_groww_client()
    return client.get_user_margin()


@app.get("/api/v1/groww/holdings")
def get_groww_holdings_endpoint() -> list[groww_client.GrowwHolding]:
    """Fetch live Demat equity holdings normalized to standard symbols."""
    client = groww_client.get_groww_client()
    return client.get_holdings()


@app.get("/api/v1/groww/positions")
def get_groww_positions_endpoint() -> list[groww_client.GrowwPosition]:
    """Fetch open intraday/delivery positions from Groww."""
    client = groww_client.get_groww_client()
    return client.get_positions()


@app.get("/api/v1/groww/mutual-funds")
def get_groww_mutual_funds_endpoint(user_id: str = "default_user") -> list[groww_client.GrowwMutualFund]:
    """Fetch user's mutual fund folios from database and Groww sync."""
    client = groww_client.get_groww_client()
    return client.get_mutual_funds(user_id=user_id)


@app.get("/api/v1/groww/portfolio-overview")
def get_groww_portfolio_overview_endpoint(user_id: str = "default_user") -> groww_client.GrowwPortfolioOverview:
    """Fetch complete multi-asset portfolio overview and Net Worth breakdown."""
    client = groww_client.get_groww_client()
    return client.get_portfolio_overview(user_id=user_id)


@app.post("/api/v1/groww/sync")
def sync_groww_portfolio_endpoint(user_id: str = "default_user") -> dict[str, Any]:
    """Import and synchronize live Groww Demat holdings into TrAId portfolio monitor."""
    client = groww_client.get_groww_client()
    return client.sync_to_portfolio_tracker(user_id=user_id)


@app.post("/api/v1/portfolio/ai-doctor")
def run_portfolio_ai_doctor_endpoint(user_id: str = "default_user") -> dict[str, Any]:
    """Run AI Doctor multi-agent diagnostic across all user's active holdings."""
    return portfolio_manager.evaluate_portfolio_ai_doctor(user_id=user_id)


# --------------------------------------------------------------------------- #
# AI Copilot & Real-Time SSE Streams
# --------------------------------------------------------------------------- #
@app.post("/api/chat/stream")
def chat_stream_endpoint(req: ChatRequest) -> StreamingResponse:
    """Stream AI research copilot responses with token-by-token text and tool traces."""

    def event_generator():
        for event in chat_agent.stream_ask(req.message, thread_id=req.thread_id):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        },
    )


@app.get("/api/events")
async def sse_events_endpoint(request: Request) -> StreamingResponse:
    """Stream live system events (scan progress, proposal alerts, position updates) via SSE."""

    async def event_stream():
        async for msg in events.subscribe():
            if await request.is_disconnected():
                break
            yield f"event: {msg['event']}\ndata: {msg['data']}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        },
    )


# --------------------------------------------------------------------------- #
# Static SPA Serving (React Frontend)
# --------------------------------------------------------------------------- #
if FRONTEND_DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST_DIR / "assets")), name="assets")


@app.get("/")
def serve_dashboard_root() -> Any:
    """Serve the React single-page application."""
    if (FRONTEND_DIST_DIR / "index.html").exists():
        return FileResponse(FRONTEND_DIST_DIR / "index.html")
    return JSONResponse(
        content={
            "service": "TrAId Interactive Web Application API",
            "version": "2.0.0",
            "docs": "/docs",
            "overview": "/api/overview",
            "proposals": "/api/proposals/pending",
            "positions": "/api/positions",
            "performance": "/api/performance",
        }
    )
