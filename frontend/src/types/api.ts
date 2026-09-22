export interface MarketRegime {
  vix: number | null;
  nifty_close: number | null;
  nifty_ema_50: number | null;
  allow_new_entries: boolean;
  risk_multiplier: number;
  reasons: string[];
}

export interface OverviewData {
  trading_mode: string;
  base_capital: number;
  current_capital: number;
  total_equity: number;
  total_realized_pnl: number;
  total_unrealized_pnl: number;
  open_positions_count: number;
  pending_proposals_count: number;
  total_trades_count: number;
  portfolio_heat_pct: number;
  max_portfolio_heat_pct: number;
  risk_per_trade_pct: number;
  market_regime: MarketRegime;
  server_time: string;
}

export interface AgentDebate {
  symbol: string;
  research_verdict?: {
    thesis_summary?: string;
    verdict?: string;
    confidence_score?: number;
    bear_objections?: string[];
    bull_catalysts?: string[];
    citations?: string[];
  };
  catalyst_assessment?: {
    catalyst_type?: string;
    catalyst_direction?: string;
    conviction?: string;
    thesis_rationale?: string;
    time_horizon_days?: number;
    primary_risks?: string[];
  };
  strategy_name?: string;
  market_regime?: string;
  citations?: string[];
}

export interface TradeProposal {
  proposal_id: string;
  symbol: string;
  strategy_name: string;
  entry_price: number;
  soft_stop: number;
  hard_stop: number;
  target_price: number;
  quantity: number;
  risk_amount: number;
  risk_to_reward: number;
  thesis: string;
  catalyst_type: string;
  created_at: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'EXPIRED';
  debate?: AgentDebate;
}

export interface OpenPosition {
  trade_id: string;
  symbol: string;
  entry_date: string;
  fill_price: number;
  current_price: number;
  quantity: number;
  soft_stop: number;
  hard_stop: number;
  target_price: number;
  strategy_name: string;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  stop_dist_pct: number;
  target_dist_pct: number;
  risk_amount: number;
  thesis: string;
}

export interface HistoricalTrade {
  trade_id: string;
  timestamp: string;
  symbol: string;
  entry_price: number;
  fill_price?: number;
  exit_price?: number;
  quantity: number;
  status: string;
  realized_pnl?: number;
  gross_pnl?: number;
  strategy_name?: string;
  mistake_category?: string;
  thesis?: string;
}

export interface PerformanceScorecard {
  closed_count: number;
  open_count: number;
  gross_pnl: number;
  total_costs: number;
  net_pnl: number;
  win_rate: number;
  expectancy: number;
  profit_factor: number | null;
  average_win_r: number;
  average_loss_r: number;
  average_r: number;
  max_drawdown_pct: number;
  benchmark_return_pct: number | null;
  strategy_alpha_pct: number | null;
  sample_size_valid: boolean;
  confidence_warning?: string;
}

export interface CandleData {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface BacktestSummary {
  initial_capital: number;
  final_equity: number;
  total_return_pct: number;
  total_net_pnl: number;
  sharpe_ratio: number;
  max_drawdown_pct: number;
  profit_factor: number;
  win_rate: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  average_r: number;
}

export interface MonteCarloStats {
  iterations: number;
  mean_drawdown_pct: number;
  p95_max_drawdown_pct: number;
  p99_max_drawdown_pct: number;
  ruin_probability_pct: number;
  median_final_equity: number;
  p05_final_equity: number;
  p95_final_equity: number;
  drawdown_distribution: number[];
}

export interface BacktestResult {
  summary: BacktestSummary;
  equity_curve: Array<{ time: string; equity: number; drawdown_pct: number }>;
  monte_carlo?: MonteCarloStats;
  trades: Array<{
    trade_id: string;
    symbol: string;
    strategy: string;
    entry_date: string;
    exit_date: string;
    entry_price: number;
    exit_price: number;
    quantity: number;
    net_pnl: number;
    r_multiple: number;
    exit_reason: string;
  }>;
}

export interface SystemHealth {
  status: string;
  trading_mode: string;
  postgres_pool_healthy: boolean;
  active_open_positions: number;
  database_backup_dir: string;
  checkpointer_ready: boolean;
  llm_configured: boolean;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'agent' | 'tool';
  text: string;
  toolCalls?: Array<{ name: string; input?: string; output?: string }>;
  timestamp: string;
}

export interface UniverseConstituent {
  symbol: string;
  company_name: string;
  industry: string;
  series: string;
  isin: string;
}

export interface UniverseResponse {
  count: number;
  symbols: string[];
  constituents?: UniverseConstituent[];
  source?: string;
  timestamp?: string;
}

export type InvestmentGoal = 'SAFE_GROWTH' | 'VACATION_FUND' | 'WEALTH_COMPOUNDING' | 'LEARNING';

export type RiskVibe = 'CONSERVATIVE' | 'BALANCED' | 'MOMENTUM';

export interface StockAllocation {
  symbol: string;
  company_name: string;
  sector: string;
  shares: number;
  suggested_entry_price: number;
  total_cost: number;
  weight_pct: number;
  target_price: number;
  stop_loss_price: number;
  expected_gain_pct: number;
  max_risk_pct: number;
  target1_price?: number;
  target1_shares?: number;
  target2_price?: number;
  target2_shares?: number;
  target2_gain_pct?: number;
  gtt_stop_trigger?: number;
  gtt_stop_limit?: number;
  gtt_target1_trigger?: number;
  gtt_target1_limit?: number;
  gtt_target2_trigger?: number;
  gtt_target2_limit?: number;
  holding_period: string;
  layman_rationale: string;
  deep_dive_summary?: string;
}

export interface StrategyBasket {
  basket_id: string;
  created_at: string;
  total_capital: number;
  allocated_capital: number;
  cash_reserve: number;
  risk_vibe: RiskVibe;
  goal?: InvestmentGoal;
  market_regime: string;
  overall_thesis: string;
  peace_of_mind_score?: number;
  scenario_best_case?: number;
  scenario_normal?: number;
  scenario_worst_case?: number;
  allocations: StockAllocation[];
}

export interface ExecutionConfirmationItem {
  symbol: string;
  shares: number;
  executed_price: number;
  broker_name?: string;
}

export interface BatchExecutionRequest {
  basket_id: string;
  user_id?: string;
  confirmations: ExecutionConfirmationItem[];
}

export interface PositionHealthStatus {
  position_id: string;
  symbol: string;
  shares: number;
  entry_price: number;
  current_price: number;
  pnl_amount: number;
  pnl_pct: number;
  target_price: number;
  stop_loss_price: number;
  target_progress_pct: number;
  status: string;
  action_required: boolean;
  recommended_action: string;
  holding_period: string;
  target1_price?: number;
  target1_shares?: number;
  target2_price?: number;
  target2_shares?: number;
  breakeven_locked?: boolean;
  tranche1_exited?: boolean;
  gtt_stop_trigger?: number;
  gtt_target1_trigger?: number;
  gtt_target2_trigger?: number;
  estimated_charges?: number;
  estimated_stcg_tax?: number;
  estimated_net_pnl?: number;
}

export interface PortfolioSummary {
  portfolio_id: string;
  user_id: string;
  initial_capital: number;
  invested_capital: number;
  current_value: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  cash_balance: number;
  total_net_pnl?: number;
  active_positions: PositionHealthStatus[];
}

export interface DailyDigest {
  digest_id: string;
  digest_type: string;
  date_str: string;
  title: string;
  greeting: string;
  market_mood: string;
  portfolio_summary_text: string;
  total_portfolio_value: number;
  daily_pnl_amount: number;
  daily_pnl_pct: number;
  zen_mode?: boolean;
  zen_message?: string;
  positions: PositionHealthStatus[];
  action_alerts: string[];
  earnings_alerts?: string[];
}

export interface ReinvestmentSuggestion {
  freed_capital: number;
  realized_pnl: number;
  exited_symbol: string;
  estimated_net_pnl?: number;
  stcg_tax_deducted?: number;
  new_opportunities: StockAllocation[];
}

export interface GrowwStatus {
  configured: boolean;
  authenticated: boolean;
  status: 'CONNECTED' | 'NOT_CONFIGURED' | 'ERROR';
  message: string;
  last_synced_at?: string;
  ucc?: string;
}

export interface GrowwBalance {
  available_cash: number;
  collateral_margin: number;
  used_margin: number;
  total_margin: number;
  currency: string;
}

export interface GrowwHolding {
  symbol: string;
  company_name: string;
  isin: string;
  quantity: number;
  avg_price: number;
  current_price: number;
  invested_amount: number;
  current_value: number;
  pnl: number;
  pnl_pct: number;
}

export interface GrowwSyncResponse {
  synced_count: number;
  holdings_found: number;
  message: string;
}

export interface GrowwMutualFund {
  folio_id: string;
  scheme_name: string;
  folio_number: string;
  units: number;
  nav: number;
  invested_amount: number;
  current_value: number;
  pnl: number;
  pnl_pct: number;
  asset_category: string;
  last_updated: string;
}

export interface GrowwPortfolioOverview {
  ucc: string;
  status: string;
  total_net_worth: number;
  equity_invested: number;
  equity_current_value: number;
  equity_pnl: number;
  equity_pnl_pct: number;
  mf_invested: number;
  mf_current_value: number;
  mf_pnl: number;
  available_cash: number;
  total_margin: number;
  holdings_count: number;
  mf_count: number;
  last_synced_at: string;
  is_demo_mode?: boolean;
  scope_warning?: string;
}

export interface AIDoctorReview {
  symbol: string;
  shares: number;
  entry_price: number;
  current_price: number;
  pnl_pct: number;
  rating: string;
  health_score: number;
  bull_thesis: string;
  bear_thesis: string;
  action_plan: string;
  stop_loss: number;
  target1: number;
  target2: number;
}

export interface AIDoctorReport {
  overall_health_score: number;
  portfolio_verdict: string;
  total_positions_reviewed: number;
  reviews: AIDoctorReview[];
}
