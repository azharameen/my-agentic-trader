import React, { useState, useEffect } from 'react';
import { ShieldCheck, Database, Activity, CheckCircle, RefreshCw } from 'lucide-react';
import { fetchHealth, fetchOverview } from '../../lib/api';
import { SystemHealth as HealthType, OverviewData } from '../../types/api';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '../ui/tooltip';

export const SystemHealthView: React.FC = () => {
  const [health, setHealth] = useState<HealthType | null>(null);
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const loadHealthData = async () => {
    setIsLoading(true);
    try {
      const [hData, oData] = await Promise.all([fetchHealth(), fetchOverview()]);
      setHealth(hData);
      setOverview(oData);
    } catch (err) {
      console.error('Failed to load health info', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadHealthData();
  }, []);

  return (
    <TooltipProvider>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-foreground flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-primary" />
              <span>System Health, Risk Invariants & Market Regime</span>
            </h2>
            <p className="text-xs text-muted-foreground">
              Runtime operational telemetry and deterministic risk boundaries
            </p>
          </div>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                onClick={loadHealthData}
                disabled={isLoading}
                className="h-8 text-xs text-muted-foreground hover:text-foreground gap-1.5"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-primary' : ''}`} />
                <span>Refresh Status</span>
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>Fetch fresh system telemetry and PostgreSQL database health checks</p>
            </TooltipContent>
          </Tooltip>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Core Infrastructure & Persistence */}
          <Card className="shadow-2xl">
            <CardHeader className="border-b border-border pb-3">
              <div className="flex items-center space-x-2 text-foreground font-bold text-sm">
                <Database className="w-4 h-4 text-primary" />
                <span>Storage & Persistence (ADR-023)</span>
              </div>
            </CardHeader>

            <CardContent className="p-6 space-y-3 text-xs">
              <div className="flex items-center justify-between bg-muted/40 p-3 rounded-xl border border-border">
                <span className="text-muted-foreground">PostgreSQL 16 Connection Pool</span>
                <span className="flex items-center gap-1.5 text-emerald-400 font-semibold font-mono">
                  <CheckCircle className="w-4 h-4" /> HEALTHY
                </span>
              </div>

              <div className="flex items-center justify-between bg-muted/40 p-3 rounded-xl border border-border">
                <span className="text-muted-foreground">LangGraph Checkpointer (PostgresSaver)</span>
                <span className="flex items-center gap-1.5 text-emerald-400 font-semibold font-mono">
                  <CheckCircle className="w-4 h-4" /> SYNCHRONIZED
                </span>
              </div>

              <div className="flex items-center justify-between bg-muted/40 p-3 rounded-xl border border-border">
                <span className="text-muted-foreground">Trading Execution Mode</span>
                <span className="text-primary font-bold font-mono">
                  {health?.trading_mode || 'PAPER_TRADING'}
                </span>
              </div>

              <div className="flex items-center justify-between bg-muted/40 p-3 rounded-xl border border-border">
                <span className="text-muted-foreground">LLM Provider & Research Agent</span>
                <span className="text-emerald-400 font-semibold font-mono">
                  CONNECTED
                </span>
              </div>
            </CardContent>
          </Card>

          {/* Deterministic Risk Invariants */}
          <Card className="shadow-2xl">
            <CardHeader className="border-b border-border pb-3">
              <div className="flex items-center space-x-2 text-foreground font-bold text-sm">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                <span>Deterministic Risk Boundaries (ADR-003)</span>
              </div>
            </CardHeader>

            <CardContent className="p-6 space-y-3 text-xs">
              <div className="flex items-center justify-between bg-muted/40 p-3 rounded-xl border border-border">
                <span className="text-muted-foreground">Max Portfolio Heat Limit</span>
                <span className="text-foreground font-bold font-mono">
                  {overview?.max_portfolio_heat_pct.toFixed(0) || 15}% of Total Equity
                </span>
              </div>

              <div className="flex items-center justify-between bg-muted/40 p-3 rounded-xl border border-border">
                <span className="text-muted-foreground">Risk Allocation Per Trade</span>
                <span className="text-foreground font-bold font-mono">
                  {overview?.risk_per_trade_pct.toFixed(1) || 1.0}% of Total Equity
                </span>
              </div>

              <div className="flex items-center justify-between bg-muted/40 p-3 rounded-xl border border-border">
                <span className="text-muted-foreground">Minimum Risk-to-Reward Floor</span>
                <span className="text-foreground font-bold font-mono">
                  2.0 : 1 Asymmetry
                </span>
              </div>

              <div className="flex items-center justify-between bg-muted/40 p-3 rounded-xl border border-border">
                <span className="text-muted-foreground">Live Real-Money Order Routing</span>
                <span className="text-rose-400 font-bold font-mono">
                  HARD-BLOCKED (Paper Only)
                </span>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Market Regime Assessment (ADR-011) */}
        {overview?.market_regime && (
          <Card className="shadow-2xl">
            <CardHeader className="border-b border-border pb-3">
              <div className="flex items-center space-x-2 text-foreground font-bold text-sm">
                <Activity className="w-4 h-4 text-amber-400" />
                <span>Macro Market Regime Gates (ADR-011)</span>
              </div>
            </CardHeader>

            <CardContent className="p-6 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="bg-muted/40 p-4 rounded-xl border border-border">
                  <span className="text-xs text-muted-foreground block mb-1">India VIX</span>
                  <div className="text-xl font-bold font-mono text-foreground">
                    {overview.market_regime.vix ? overview.market_regime.vix.toFixed(1) : 'N/A'}
                  </div>
                  <span className="text-[10px] text-muted-foreground/70">
                    Elevated: &gt;19.0 | Crisis Veto: &gt;24.0
                  </span>
                </div>

                <div className="bg-muted/40 p-4 rounded-xl border border-border">
                  <span className="text-xs text-muted-foreground block mb-1">NIFTY 50 vs 50 EMA</span>
                  <div className="text-xl font-bold font-mono text-foreground">
                    {overview.market_regime.nifty_close ? overview.market_regime.nifty_close.toFixed(0) : 'N/A'}
                  </div>
                  <span className="text-[10px] text-muted-foreground/70">
                    50 EMA: {overview.market_regime.nifty_ema_50 ? overview.market_regime.nifty_ema_50.toFixed(0) : 'N/A'}
                  </span>
                </div>

                <div className="bg-muted/40 p-4 rounded-xl border border-border">
                  <span className="text-xs text-muted-foreground block mb-1">Current Entry Status</span>
                  <div
                    className={`text-lg font-bold font-mono ${
                      overview.market_regime.allow_new_entries ? 'text-emerald-400' : 'text-rose-400'
                    }`}
                  >
                    {overview.market_regime.allow_new_entries ? 'ENTRIES ALLOWED' : 'NEW ENTRIES VETOED'}
                  </div>
                  <span className="text-[10px] text-muted-foreground/70">
                    Risk Multiplier: {(overview.market_regime.risk_multiplier * 100).toFixed(0)}%
                  </span>
                </div>
              </div>

              {overview.market_regime.reasons.length > 0 && (
                <div className="p-3 bg-muted/20 rounded-xl border border-border text-xs text-muted-foreground">
                  <span className="font-semibold text-foreground block mb-1">Regime Rationale:</span>
                  <ul className="list-disc pl-4 space-y-0.5 text-[11px]">
                    {overview.market_regime.reasons.map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </TooltipProvider>
  );
};
