import {
  OverviewData,
  OpenPosition,
  TradeProposal,
  HistoricalTrade,
  PerformanceScorecard,
  CandleData,
  BacktestResult,
  SystemHealth,
  UniverseResponse,
  InvestmentGoal,
  RiskVibe,
  StrategyBasket,
  BatchExecutionRequest,
  PortfolioSummary,
  ReinvestmentSuggestion,
  DailyDigest,
  GrowwStatus,
  GrowwBalance,
  GrowwHolding,
  GrowwSyncResponse,
  GrowwMutualFund,
  GrowwPortfolioOverview,
  AIDoctorReport,
} from "../types/api";

const BASE_URL = "/api";

export async function fetchOverview(): Promise<OverviewData> {
  const res = await fetch(`${BASE_URL}/overview`);
  if (!res.ok) throw new Error(`Overview fetch failed: ${res.statusText}`);
  return res.json();
}

export async function fetchPositions(): Promise<OpenPosition[]> {
  const res = await fetch(`${BASE_URL}/positions`);
  if (!res.ok) throw new Error(`Positions fetch failed: ${res.statusText}`);
  return res.json();
}

export async function closePosition(tradeId: string, exitPrice?: number): Promise<any> {
  const res = await fetch(`${BASE_URL}/positions/${tradeId}/close`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ exit_price: exitPrice }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to close position");
  }
  return res.json();
}

export async function fetchPendingProposals(): Promise<TradeProposal[]> {
  const res = await fetch(`${BASE_URL}/proposals/pending`);
  if (!res.ok) throw new Error(`Pending proposals fetch failed: ${res.statusText}`);
  return res.json();
}

export async function fetchProposalDetails(proposalId: string): Promise<TradeProposal> {
  const res = await fetch(`${BASE_URL}/proposals/${proposalId}`);
  if (!res.ok) throw new Error(`Proposal details fetch failed: ${res.statusText}`);
  return res.json();
}

export async function approveProposal(proposalId: string, notes?: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/proposals/${proposalId}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ notes }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to approve proposal");
  }
  return res.json();
}

export async function rejectProposal(proposalId: string, reason?: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/proposals/${proposalId}/reject`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to reject proposal");
  }
  return res.json();
}

export async function fetchTrades(status?: string): Promise<HistoricalTrade[]> {
  const url = status ? `${BASE_URL}/trades?status=${status}` : `${BASE_URL}/trades`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Trades fetch failed: ${res.statusText}`);
  return res.json();
}

export async function fetchPerformance(): Promise<PerformanceScorecard> {
  const res = await fetch(`${BASE_URL}/performance`);
  if (!res.ok) throw new Error(`Performance fetch failed: ${res.statusText}`);
  return res.json();
}

export async function fetchCandles(symbol: string): Promise<CandleData[]> {
  const res = await fetch(`${BASE_URL}/candles/${symbol}`);
  if (!res.ok) throw new Error(`Candles fetch failed: ${res.statusText}`);
  return res.json();
}

export async function runBacktest(params: {
  symbols?: string[];
  startDate?: string;
  endDate?: string;
  initialCapital?: number;
}): Promise<BacktestResult> {
  const res = await fetch(`${BASE_URL}/backtest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      symbols: params.symbols,
      start_date: params.startDate,
      end_date: params.endDate,
      initial_capital: params.initialCapital,
    }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Backtest failed");
  }
  return res.json();
}

export async function fetchUniverse(): Promise<UniverseResponse> {
  const res = await fetch(`${BASE_URL}/universe`);
  if (!res.ok) throw new Error(`Universe fetch failed: ${res.statusText}`);
  return res.json();
}

export async function refreshUniverse(): Promise<any> {
  const res = await fetch(`${BASE_URL}/universe/refresh`, { method: "POST" });
  if (!res.ok) throw new Error(`Universe refresh failed: ${res.statusText}`);
  return res.json();
}

export async function triggerScan(): Promise<any> {
  const res = await fetch(`${BASE_URL}/scan`, { method: "POST" });
  if (!res.ok) throw new Error(`Scan trigger failed: ${res.statusText}`);
  return res.json();
}

export async function triggerRunSymbol(symbol: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/run/${symbol}`, { method: "POST" });
  if (!res.ok) throw new Error(`Run symbol trigger failed: ${res.statusText}`);
  return res.json();
}

export async function fetchHealth(): Promise<SystemHealth> {
  const res = await fetch(`${BASE_URL}/health`);
  if (!res.ok) throw new Error(`Health fetch failed: ${res.statusText}`);
  return res.json();
}

export interface ChartLevels {
  symbol: string;
  source: 'PROPOSAL' | 'POSITION' | null;
  entry_price: number | null;
  target_price: number | null;
  soft_stop: number | null;
  hard_stop: number | null;
  trailing_stop: number | null;
}

export async function fetchSymbolLevels(symbol: string): Promise<ChartLevels> {
  const res = await fetch(`${BASE_URL}/levels/${symbol}`);
  if (!res.ok) throw new Error(`Levels fetch failed: ${res.statusText}`);
  return res.json();
}

// --------------------------------------------------------------------------- //
// Beginner User Journey API Functions
// --------------------------------------------------------------------------- //

export async function generateBasket(
  capital: number,
  riskVibe: RiskVibe = 'BALANCED',
  goal: InvestmentGoal = 'SAFE_GROWTH',
  maxStocks: number = 4
): Promise<StrategyBasket> {
  const res = await fetch(`${BASE_URL}/v1/strategy/generate-basket`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      capital,
      risk_vibe: riskVibe,
      goal,
      max_stocks: maxStocks,
    }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Failed to generate investment strategy basket');
  }
  return res.json();
}

export async function confirmBatchExecutions(
  request: BatchExecutionRequest
): Promise<PortfolioSummary> {
  const res = await fetch(`${BASE_URL}/v1/portfolio/confirm-executions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Failed to confirm trade executions');
  }
  return res.json();
}

export async function fetchActivePortfolioHealth(
  userId: string = 'default_user'
): Promise<PortfolioSummary | null> {
  const res = await fetch(`${BASE_URL}/v1/portfolio/active-health?user_id=${userId}`);
  if (!res.ok) throw new Error(`Active portfolio fetch failed: ${res.statusText}`);
  return res.json();
}

export async function exitPosition(
  positionId: string,
  exitPrice: number,
  sharesToExit?: number,
  userId: string = 'default_user'
): Promise<ReinvestmentSuggestion> {
  const res = await fetch(`${BASE_URL}/v1/portfolio/exit-position`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      position_id: positionId,
      exit_price: exitPrice,
      shares_to_exit: sharesToExit,
      user_id: userId,
    }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Failed to exit position');
  }
  return res.json();
}

export async function fetchMorningDigest(
  userId: string = 'default_user'
): Promise<DailyDigest> {
  const res = await fetch(`${BASE_URL}/v1/digests/morning?user_id=${userId}`);
  if (!res.ok) throw new Error(`Morning digest fetch failed: ${res.statusText}`);
  return res.json();
}

export async function fetchEveningDigest(
  userId: string = 'default_user'
): Promise<DailyDigest> {
  const res = await fetch(`${BASE_URL}/v1/digests/evening?user_id=${userId}`);
  if (!res.ok) throw new Error(`Evening digest fetch failed: ${res.statusText}`);
  return res.json();
}

// --------------------------------------------------------------------------- //
// Groww Broker API Integration (Read-Only, ADR-035)
// --------------------------------------------------------------------------- //

export async function fetchGrowwStatus(): Promise<GrowwStatus> {
  const res = await fetch(`${BASE_URL}/v1/groww/status`);
  if (!res.ok) throw new Error(`Groww status fetch failed: ${res.statusText}`);
  return res.json();
}

export async function fetchGrowwBalance(): Promise<GrowwBalance> {
  const res = await fetch(`${BASE_URL}/v1/groww/balance`);
  if (!res.ok) throw new Error(`Groww balance fetch failed: ${res.statusText}`);
  return res.json();
}

export async function fetchGrowwHoldings(): Promise<GrowwHolding[]> {
  const res = await fetch(`${BASE_URL}/v1/groww/holdings`);
  if (!res.ok) throw new Error(`Groww holdings fetch failed: ${res.statusText}`);
  return res.json();
}

export async function syncGrowwPortfolio(userId: string = 'default_user'): Promise<GrowwSyncResponse> {
  const res = await fetch(`${BASE_URL}/v1/groww/sync?user_id=${userId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Failed to sync Groww portfolio');
  }
  return res.json();
}

export async function fetchGrowwMutualFunds(userId: string = 'default_user'): Promise<GrowwMutualFund[]> {
  const res = await fetch(`${BASE_URL}/v1/groww/mutual-funds?user_id=${userId}`);
  if (!res.ok) throw new Error(`Groww mutual funds fetch failed: ${res.statusText}`);
  return res.json();
}

export async function fetchGrowwPortfolioOverview(userId: string = 'default_user'): Promise<GrowwPortfolioOverview> {
  const res = await fetch(`${BASE_URL}/v1/groww/portfolio-overview?user_id=${userId}`);
  if (!res.ok) throw new Error(`Groww portfolio overview fetch failed: ${res.statusText}`);
  return res.json();
}

export async function fetchPortfolioAIDoctor(userId: string = 'default_user'): Promise<AIDoctorReport> {
  const res = await fetch(`${BASE_URL}/v1/portfolio/ai-doctor?user_id=${userId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Failed to run AI Doctor portfolio evaluation');
  }
  return res.json();
}


