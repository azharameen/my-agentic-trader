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
  BatchExecutionRequest,
  PortfolioSummary,
  Schedule,
  ScheduleInput,
} from "../types/api";

const BASE_URL = "/api";

export async function fetchSchedules(): Promise<Schedule[]> {
  const res = await fetch(`${BASE_URL}/schedules`);
  if (!res.ok) throw new Error(`Schedules fetch failed: ${res.statusText}`);
  return res.json();
}

export async function saveSchedule(schedule: ScheduleInput, id?: string): Promise<Schedule> {
  const res = await fetch(`${BASE_URL}/schedules${id ? `/${id}` : ''}`, {
    method: id ? 'PUT' : 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(schedule),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Failed to save schedule');
  }
  return res.json();
}

export async function setScheduleEnabled(id: string, enabled: boolean): Promise<Schedule> {
  const res = await fetch(`${BASE_URL}/schedules/${id}/enabled`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ enabled }),
  });
  if (!res.ok) throw new Error(`Schedule update failed: ${res.statusText}`);
  return res.json();
}

export async function runScheduleNow(id: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/schedules/${id}/run`, { method: 'POST' });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Failed to run schedule');
  }
}

export async function deleteSchedule(id: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/schedules/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(`Schedule delete failed: ${res.statusText}`);
}

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

// --------------------------------------------------------------------------- //
// Groww Broker API Integration (Read-Only, ADR-035)
// --------------------------------------------------------------------------- //

// --------------------------------------------------------------------------- //
// Command Center: unified holdings, manual entries, and agent signals
// --------------------------------------------------------------------------- //
import { CommandCenterOverview } from "../types/api";

export async function fetchCommandCenterOverview(): Promise<CommandCenterOverview> {
  const res = await fetch(`${BASE_URL}/v1/command-center/overview`);
  if (!res.ok) throw new Error(`Command Center overview fetch failed: ${res.statusText}`);
  return res.json();
}

export async function addManualStock(payload: {
  symbol: string;
  shares: number;
  entry_price: number;
  stop_loss_price?: number;
  target_price?: number;
  sector?: string;
}): Promise<{ position_id: string }> {
  const res = await fetch(`${BASE_URL}/v1/command-center/stocks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to add stock");
  }
  return res.json();
}

export async function updateManualStock(
  positionId: string,
  payload: Partial<{ shares: number; entry_price: number; stop_loss_price: number; target_price: number }>
): Promise<void> {
  const res = await fetch(`${BASE_URL}/v1/command-center/stocks/${positionId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to update stock");
  }
}

export async function deleteManualStock(positionId: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/v1/command-center/stocks/${positionId}`, { method: "DELETE" });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to delete stock");
  }
}

export async function addFnoPosition(payload: {
  symbol: string;
  instrument_type: string;
  quantity: number;
  entry_price: number;
  lot_size?: number;
  strike_price?: number;
  expiry_date?: string;
}): Promise<{ position_id: string }> {
  const res = await fetch(`${BASE_URL}/v1/command-center/fno`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to add F&O position");
  }
  return res.json();
}

export async function deleteFnoPosition(positionId: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/v1/command-center/fno/${positionId}`, { method: "DELETE" });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to delete F&O position");
  }
}

export async function addMutualFund(payload: {
  scheme_name: string;
  units: number;
  nav: number;
  invested_amount: number;
  folio_number?: string;
  asset_category?: string;
}): Promise<{ folio_id: string }> {
  const res = await fetch(`${BASE_URL}/v1/command-center/mutual-funds`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to add mutual fund");
  }
  return res.json();
}

export async function deleteMutualFund(folioId: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/v1/command-center/mutual-funds/${folioId}`, { method: "DELETE" });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to delete mutual fund");
  }
}


export async function fetchDeepDive(symbol: string) {
  const res = await fetch(`${BASE_URL}/v1/command-center/deep-dive/${symbol}`);
  if (!res.ok) throw new Error(`Deep dive fetch failed: ${res.statusText}`);
  return res.json() as Promise<import("../types/api").DeepDiveResponse>;
}
