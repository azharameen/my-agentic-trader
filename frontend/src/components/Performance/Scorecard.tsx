import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { PerformanceScorecard } from '../../types/api';
import { formatINR, formatPct, formatNumber } from '../../lib/utils';
import { Card, CardContent } from '../ui/card';

interface ScorecardProps {
  performance: PerformanceScorecard | null;
}

export const Scorecard: React.FC<ScorecardProps> = ({ performance }) => {
  if (!performance) return null;

  const winRatePct = (performance.win_rate || 0) * 100;
  const isAlphaPositive = (performance.strategy_alpha_pct || 0) >= 0;

  return (
    <div className="space-y-4">
      {/* Sample Size Warning Banner */}
      {!performance.sample_size_valid && (
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-3.5 flex items-center space-x-3 text-xs text-amber-300">
          <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0" />
          <span>
            {performance.confidence_warning ||
              `Statistical sample size (${performance.closed_count}/30 closed trades) is preliminary. Metric confidence will increase with 30+ trades.`}
          </span>
        </div>
      )}

      {/* Primary KPI Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3.5">
        {/* Net P&L */}
        <Card className="shadow-sm">
          <CardContent className="p-3.5">
            <span className="text-xs text-muted-foreground font-medium block mb-1">Net Realized P&L</span>
            <div
              className={`text-xl font-bold font-mono ${
                performance.net_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'
              }`}
            >
              {performance.net_pnl >= 0 ? '+' : ''}₹{formatINR(performance.net_pnl)}
            </div>
            <span className="text-[10px] text-muted-foreground/70">Gross: ₹{formatINR(performance.gross_pnl)}</span>
          </CardContent>
        </Card>

        {/* Win Rate */}
        <Card className="shadow-sm">
          <CardContent className="p-3.5">
            <span className="text-xs text-muted-foreground font-medium block mb-1">Win Rate</span>
            <div className="text-xl font-bold font-mono text-foreground">
              {winRatePct.toFixed(1)}%
            </div>
            <span className="text-[10px] text-muted-foreground/70">{performance.closed_count} closed trades</span>
          </CardContent>
        </Card>

        {/* Profit Factor */}
        <Card className="shadow-sm">
          <CardContent className="p-3.5">
            <span className="text-xs text-muted-foreground font-medium block mb-1">Profit Factor</span>
            <div className="text-xl font-bold font-mono text-primary">
              {performance.profit_factor !== null ? formatNumber(performance.profit_factor, 2) : 'N/A'}
            </div>
            <span className="text-[10px] text-muted-foreground/70">Gross Win / Gross Loss</span>
          </CardContent>
        </Card>

        {/* Expectancy */}
        <Card className="shadow-sm">
          <CardContent className="p-3.5">
            <span className="text-xs text-muted-foreground font-medium block mb-1">Trade Expectancy</span>
            <div
              className={`text-xl font-bold font-mono ${
                performance.expectancy >= 0 ? 'text-emerald-400' : 'text-rose-400'
              }`}
            >
              {performance.expectancy >= 0 ? '+' : ''}₹{formatINR(performance.expectancy)}
            </div>
            <span className="text-[10px] text-muted-foreground/70">Avg R: {formatNumber(performance.average_r, 2)}R</span>
          </CardContent>
        </Card>

        {/* Max Drawdown */}
        <Card className="shadow-sm">
          <CardContent className="p-3.5">
            <span className="text-xs text-muted-foreground font-medium block mb-1">Max Drawdown</span>
            <div className="text-xl font-bold font-mono text-rose-400">
              {performance.max_drawdown_pct.toFixed(2)}%
            </div>
            <span className="text-[10px] text-muted-foreground/70">Peak-to-trough</span>
          </CardContent>
        </Card>

        {/* Net Alpha vs NIFTY 100 */}
        <Card className="shadow-sm">
          <CardContent className="p-3.5">
            <span className="text-xs text-muted-foreground font-medium block mb-1">Alpha vs NIFTY 100</span>
            <div
              className={`text-xl font-bold font-mono ${
                isAlphaPositive ? 'text-emerald-400' : 'text-rose-400'
              }`}
            >
              {performance.strategy_alpha_pct !== null
                ? formatPct(performance.strategy_alpha_pct)
                : 'N/A'}
            </div>
            <span className="text-[10px] text-muted-foreground/70">Benchmark: {formatPct(performance.benchmark_return_pct)}</span>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
