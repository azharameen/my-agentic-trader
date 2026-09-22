import React from 'react';
import { Wallet, TrendingUp, ShieldAlert, BarChart3, Clock, AlertTriangle } from 'lucide-react';
import { OverviewData } from '../../types/api';
import { formatINR } from '../../lib/utils';
import { Card, CardContent } from '../ui/card';

interface MetricRibbonProps {
  overview: OverviewData | null;
}

export const MetricRibbon: React.FC<MetricRibbonProps> = ({ overview }) => {
  if (!overview) return null;

  const heatPct = overview.portfolio_heat_pct || 0;
  const maxHeat = overview.max_portfolio_heat_pct || 15;
  const isHeatHigh = heatPct > maxHeat * 0.8;

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3.5 mb-6">
      {/* Total Equity */}
      <Card className="shadow-sm">
        <CardContent className="p-3.5">
          <div className="flex items-center justify-between text-muted-foreground mb-1">
            <span className="text-xs font-medium">Total Equity</span>
            <Wallet className="w-4 h-4 text-primary" />
          </div>
          <div className="text-xl font-bold font-mono text-foreground">
            ₹{formatINR(overview.total_equity)}
          </div>
          <div className="text-[11px] text-muted-foreground/70 mt-0.5">
            Base: ₹{formatINR(overview.base_capital)}
          </div>
        </CardContent>
      </Card>

      {/* Unrealized P&L */}
      <Card className="shadow-sm">
        <CardContent className="p-3.5">
          <div className="flex items-center justify-between text-muted-foreground mb-1">
            <span className="text-xs font-medium">Unrealized P&L</span>
            <TrendingUp className="w-4 h-4 text-emerald-400" />
          </div>
          <div
            className={`text-xl font-bold font-mono ${
              overview.total_unrealized_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'
            }`}
          >
            {overview.total_unrealized_pnl >= 0 ? '+' : ''}₹{formatINR(overview.total_unrealized_pnl)}
          </div>
          <div className="text-[11px] text-muted-foreground/70 mt-0.5">
            {overview.open_positions_count} open position(s)
          </div>
        </CardContent>
      </Card>

      {/* Realized P&L */}
      <Card className="shadow-sm">
        <CardContent className="p-3.5">
          <div className="flex items-center justify-between text-muted-foreground mb-1">
            <span className="text-xs font-medium">Realized P&L</span>
            <BarChart3 className="w-4 h-4 text-purple-400" />
          </div>
          <div
            className={`text-xl font-bold font-mono ${
              overview.total_realized_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'
            }`}
          >
            {overview.total_realized_pnl >= 0 ? '+' : ''}₹{formatINR(overview.total_realized_pnl)}
          </div>
          <div className="text-[11px] text-muted-foreground/70 mt-0.5">
            {overview.total_trades_count} total trades
          </div>
        </CardContent>
      </Card>

      {/* Portfolio Heat */}
      <Card className="shadow-sm">
        <CardContent className="p-3.5">
          <div className="flex items-center justify-between text-muted-foreground mb-1">
            <span className="text-xs font-medium">Portfolio Heat</span>
            <ShieldAlert className={`w-4 h-4 ${isHeatHigh ? 'text-amber-400' : 'text-primary'}`} />
          </div>
          <div
            className={`text-xl font-bold font-mono ${
              isHeatHigh ? 'text-amber-400' : 'text-foreground'
            }`}
          >
            {heatPct.toFixed(1)}%
          </div>
          <div className="text-[11px] text-muted-foreground/70 mt-0.5">
            Cap: {maxHeat.toFixed(0)}% (1.0% / trade)
          </div>
        </CardContent>
      </Card>

      {/* Market Regime */}
      <Card className="shadow-sm">
        <CardContent className="p-3.5">
          <div className="flex items-center justify-between text-muted-foreground mb-1">
            <span className="text-xs font-medium">India VIX</span>
            <AlertTriangle className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-xl font-bold font-mono text-foreground">
            {overview.market_regime.vix ? overview.market_regime.vix.toFixed(1) : 'N/A'}
          </div>
          <div className="text-[11px] text-muted-foreground/70 mt-0.5">
            Mult: {overview.market_regime.risk_multiplier * 100}% budget
          </div>
        </CardContent>
      </Card>

      {/* Pending Approvals */}
      <Card className="shadow-sm">
        <CardContent className="p-3.5">
          <div className="flex items-center justify-between text-muted-foreground mb-1">
            <span className="text-xs font-medium">Pending Approvals</span>
            <Clock className="w-4 h-4 text-amber-400" />
          </div>
          <div
            className={`text-xl font-bold font-mono ${
              overview.pending_proposals_count > 0 ? 'text-amber-400 animate-pulse' : 'text-foreground'
            }`}
          >
            {overview.pending_proposals_count}
          </div>
          <div className="text-[11px] text-muted-foreground/70 mt-0.5">
            Action required in Cockpit
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
