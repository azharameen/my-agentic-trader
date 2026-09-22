"""Typed domain models for beginner-friendly strategy baskets, execution confirmations,
portfolio tracking, and daily digests.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class InvestmentGoal(str, Enum):
    SAFE_GROWTH = "SAFE_GROWTH"                    # Capital Preservation & Safe Growth (Index-like stability)
    VACATION_FUND = "VACATION_FUND"                # Short-term Goal / 3-6 Months Swing
    WEALTH_COMPOUNDING = "WEALTH_COMPOUNDING"      # Long-term Alpha & Trend Compounding
    LEARNING = "LEARNING"                          # Low Risk / Small Capital Education


class RiskVibe(str, Enum):
    CONSERVATIVE = "CONSERVATIVE"  # Large-cap leaders, lower volatility, 4-8 week horizon
    BALANCED = "BALANCED"          # Swing & momentum, 2-4 week horizon
    MOMENTUM = "MOMENTUM"          # High-growth breakouts, 1-2 week horizon


class StockAllocation(BaseModel):
    """A single stock allocation inside a beginner's strategy basket."""

    model_config = ConfigDict(extra="ignore")

    symbol: str = Field(description="NSE symbol without exchange suffix.")
    company_name: str = Field(description="Full company name.")
    sector: str = Field(default="Diversified", description="Industry sector.")
    shares: int = Field(description="Exact number of whole shares to buy.")
    suggested_entry_price: float = Field(description="Recommended entry price in INR.")
    total_cost: float = Field(description="Total INR cost = shares * suggested_entry_price.")
    weight_pct: float = Field(description="Percentage allocation of total capital.")
    
    # 2-Tranche targets & Stop-loss
    target_price: float = Field(description="Target 1 profit booking price in INR.")
    stop_loss_price: float = Field(description="Capital protection stop-loss price in INR.")
    expected_gain_pct: float = Field(description="Expected gain percentage to target 1.")
    max_risk_pct: float = Field(description="Max potential loss percentage to stop loss.")
    
    target1_price: float = Field(default=0.0, description="Tranche 1 profit target in INR.")
    target1_shares: int = Field(default=0, description="Number of shares to sell at Tranche 1.")
    target2_price: float = Field(default=0.0, description="Tranche 2 runner target in INR.")
    target2_shares: int = Field(default=0, description="Number of shares to hold for Tranche 2.")
    target2_gain_pct: float = Field(default=0.0, description="Target 2 gain percentage.")

    # GTT (Good Till Triggered) helper coordinates for Zerodha / Groww
    gtt_stop_trigger: float = Field(default=0.0, description="GTT Stop-loss trigger price.")
    gtt_stop_limit: float = Field(default=0.0, description="GTT Stop-loss limit order price.")
    gtt_target1_trigger: float = Field(default=0.0, description="GTT Target 1 trigger price.")
    gtt_target1_limit: float = Field(default=0.0, description="GTT Target 1 limit order price.")
    gtt_target2_trigger: float = Field(default=0.0, description="GTT Target 2 trigger price.")
    gtt_target2_limit: float = Field(default=0.0, description="GTT Target 2 limit order price.")

    holding_period: str = Field(default="2-4 Weeks", description="Expected time horizon in plain English.")
    layman_rationale: str = Field(description="Simple 1-2 sentence explanation of why to buy.")
    deep_dive_summary: Optional[str] = Field(default=None, description="Detailed technical/agent rationale.")


class StrategyBasket(BaseModel):
    """Complete portfolio investment plan for a beginner."""

    model_config = ConfigDict(extra="ignore")

    basket_id: str = Field(description="Unique ID for this basket proposal.")
    created_at: str = Field(description="UTC timestamp of basket generation.")
    total_capital: float = Field(description="User requested investment capital in INR.")
    allocated_capital: float = Field(description="Sum of all stock purchases in INR.")
    cash_reserve: float = Field(description="Unallocated cash buffer in INR.")
    risk_vibe: RiskVibe = Field(default=RiskVibe.BALANCED, description="Risk profile.")
    goal: InvestmentGoal = Field(default=InvestmentGoal.SAFE_GROWTH, description="Selected investment goal.")
    market_regime: str = Field(default="BULLISH", description="Current market environment.")
    overall_thesis: str = Field(description="Plain-English summary of the current market plan.")
    
    # Psychological Peace-of-mind metrics & Scenarios
    peace_of_mind_score: int = Field(default=85, description="Peace of Mind score from 0-100.")
    scenario_best_case: float = Field(default=0.0, description="Estimated INR gain if full targets are met.")
    scenario_normal: float = Field(default=0.0, description="Estimated INR gain in expected market conditions.")
    scenario_worst_case: float = Field(default=0.0, description="Estimated max INR drawdown if all stop-losses hit.")

    allocations: list[StockAllocation] = Field(default_factory=list, description="List of stock allocations.")


class BasketRequest(BaseModel):
    """Incoming request to generate a strategy basket."""

    capital: float = Field(gt=0, description="Total capital in INR to invest.")
    risk_vibe: RiskVibe = Field(default=RiskVibe.BALANCED, description="Selected risk appetite.")
    goal: InvestmentGoal = Field(default=InvestmentGoal.SAFE_GROWTH, description="Selected investment goal.")
    max_stocks: int = Field(default=4, ge=1, le=10, description="Target number of stocks.")
    user_id: Optional[str] = Field(default="default_user", description="User identifier.")


class ExecutionConfirmationItem(BaseModel):
    """Confirmation details for a single executed stock order."""

    symbol: str = Field(description="NSE symbol.")
    shares: int = Field(gt=0, description="Actual shares bought.")
    executed_price: float = Field(gt=0, description="Actual fill price in INR.")
    broker_name: Optional[str] = Field(default="Broker", description="Broker used (e.g. Zerodha, Groww).")


class BatchExecutionRequest(BaseModel):
    """Batch confirmation submitted by user after placing orders on their external broker."""

    basket_id: str = Field(description="ID of the strategy basket being confirmed.")
    user_id: str = Field(default="default_user", description="User identifier.")
    confirmations: list[ExecutionConfirmationItem] = Field(description="List of executed stocks.")


class PositionHealthStatus(BaseModel):
    """Real-time health status of an active holding."""

    position_id: str
    symbol: str
    shares: int
    entry_price: float
    current_price: float
    pnl_amount: float
    pnl_pct: float
    target_price: float
    stop_loss_price: float
    target_progress_pct: float
    status: str = Field(description="ON_TRACK, APPROACHING_TARGET, TARGET_REACHED, STOPPED_OUT")
    action_required: bool = Field(default=False)
    recommended_action: str = Field(default="HOLD")
    holding_period: str = Field(default="2-4 Weeks")

    # 2-Tranche tracking
    target1_price: float = Field(default=0.0)
    target1_shares: int = Field(default=0)
    target2_price: float = Field(default=0.0)
    target2_shares: int = Field(default=0)
    breakeven_locked: bool = Field(default=False, description="True if trailing stop has ratcheted to entry price.")
    tranche1_exited: bool = Field(default=False, description="True if first 50% tranche has been booked.")

    # GTT helper info
    gtt_stop_trigger: float = Field(default=0.0)
    gtt_target1_trigger: float = Field(default=0.0)
    gtt_target2_trigger: float = Field(default=0.0)

    # Net P&L after taxes & charges
    estimated_charges: float = Field(default=0.0, description="Estimated STT + brokerage charges.")
    estimated_stcg_tax: float = Field(default=0.0, description="Estimated 20% STCG tax on gains.")
    estimated_net_pnl: float = Field(default=0.0, description="Net In-Pocket P&L after taxes & charges.")


class PortfolioSummary(BaseModel):
    """Summary of user's active portfolio."""

    portfolio_id: str
    user_id: str
    initial_capital: float
    invested_capital: float
    current_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    cash_balance: float
    total_net_pnl: float = Field(default=0.0, description="Total net profit after estimated taxes and charges.")
    active_positions: list[PositionHealthStatus] = Field(default_factory=list)


class DailyDigest(BaseModel):
    """Structured daily evaluation for the user."""

    digest_id: str
    digest_type: str = Field(description="MORNING_MOOD or EVENING_HEALTH")
    date_str: str
    title: str
    greeting: str
    market_mood: str
    portfolio_summary_text: str
    total_portfolio_value: float
    daily_pnl_amount: float
    daily_pnl_pct: float
    zen_mode: bool = Field(default=False, description="True if portfolio is in peace/zen mode with zero alerts.")
    zen_message: Optional[str] = Field(default=None, description="Reassuring Zen affirmation message.")
    positions: list[PositionHealthStatus] = Field(default_factory=list)
    action_alerts: list[str] = Field(default_factory=list)
    earnings_alerts: list[str] = Field(default_factory=list)


class ReinvestmentSuggestion(BaseModel):
    """Recycled capital opportunity after exiting a profitable trade."""

    freed_capital: float
    realized_pnl: float
    exited_symbol: str
    estimated_net_pnl: float = Field(default=0.0, description="Net realized profit after taxes & charges.")
    stcg_tax_deducted: float = Field(default=0.0, description="20% STCG tax allocated.")
    new_opportunities: list[StockAllocation] = Field(default_factory=list)
