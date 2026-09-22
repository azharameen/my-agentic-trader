import React, { useState, useEffect } from 'react';
import { Play, Loader2, AlertTriangle, FlaskConical, Dices } from 'lucide-react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip as ChartTooltip,
  Legend,
  Filler,
} from 'chart.js';
import { fetchUniverse, runBacktest } from '../../lib/api';
import { BacktestResult } from '../../types/api';
import { formatINR, formatPct, formatNumber } from '../../lib/utils';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '../ui/tooltip';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, ChartTooltip, Legend, Filler);

export const BacktestStudio: React.FC = () => {
  const [universeSymbols, setUniverseSymbols] = useState<string[]>([]);
  const [symbol, setSymbol] = useState('RELIANCE');
  const [startDate, setStartDate] = useState('2024-01-01');
  const [endDate, setEndDate] = useState(new Date().toISOString().slice(0, 10));
  const [initialCapital, setInitialCapital] = useState(100000);
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchUniverse()
      .then((data) => setUniverseSymbols(data.symbols))
      .catch((err) => console.error(err));
  }, []);

  const handleRunBacktest = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    try {
      const data = await runBacktest({
        symbols: [symbol],
        startDate,
        endDate,
        initialCapital,
      });
      setResult(data);
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Backtest execution failed');
    } finally {
      setIsLoading(false);
    }
  };

  const chartData = result
    ? {
        labels: result.equity_curve.map((pt) => pt.time),
        datasets: [
          {
            label: 'Strategy Equity (₹)',
            data: result.equity_curve.map((pt) => pt.equity),
            borderColor: '#3B82F6',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            fill: true,
            tension: 0.1,
            pointRadius: 0,
            borderWidth: 2,
          },
        ],
      }
    : null;

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        mode: 'index' as const,
        intersect: false,
      },
    },
    scales: {
      x: {
        grid: { color: 'rgba(51, 65, 85, 0.4)' },
        ticks: { color: '#64748B', maxTicksLimit: 10 },
      },
      y: {
        grid: { color: 'rgba(51, 65, 85, 0.4)' },
        ticks: { color: '#64748B' },
      },
    },
  };

  return (
    <TooltipProvider>
      <div className="space-y-6">
        {/* Parameter Selection Card */}
        <Card className="shadow-2xl">
          <CardHeader className="border-b border-border pb-4">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center font-bold">
                <FlaskConical className="w-4 h-4" />
              </div>
              <div>
                <CardTitle className="text-base font-bold text-foreground">Walk-Forward Backtesting Studio</CardTitle>
                <CardDescription className="text-xs text-muted-foreground mt-0.5">
                  Event-driven simulation with zero lookahead bias and realistic delivery transaction costs (ADR-025)
                </CardDescription>
              </div>
            </div>
          </CardHeader>

          <CardContent className="p-6">
            <form onSubmit={handleRunBacktest} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 items-end">
              <div>
                <label className="text-xs font-semibold text-foreground block mb-1.5">Symbol</label>
                <select
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value)}
                  className="w-full bg-muted border border-border rounded-lg px-3.5 h-9 text-foreground font-mono text-xs focus:outline-none focus:ring-1 focus:ring-ring transition"
                >
                  {universeSymbols.length > 0 ? (
                    universeSymbols.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))
                  ) : (
                    <option value={symbol}>{symbol}</option>
                  )}
                </select>
              </div>

              <div>
                <label className="text-xs font-semibold text-foreground block mb-1.5">Start Date</label>
                <Input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="h-9 text-xs font-mono"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-foreground block mb-1.5">End Date</label>
                <Input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="h-9 text-xs font-mono"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-foreground block mb-1.5">Initial Capital (₹)</label>
                <Input
                  type="number"
                  value={initialCapital}
                  onChange={(e) => setInitialCapital(Number(e.target.value))}
                  className="h-9 text-xs font-mono"
                />
              </div>

              <div>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      type="submit"
                      disabled={isLoading}
                      className="w-full h-9 text-xs font-semibold gap-2 shadow-lg shadow-primary/20"
                    >
                      {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />}
                      <span>{isLoading ? 'Simulating...' : 'Run Backtest'}</span>
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Run event-driven walk-forward backtest on historical data with 0.1% STT slippage</p>
                  </TooltipContent>
                </Tooltip>
              </div>
            </form>

            {error && (
              <div className="mt-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Results View */}
        {result && (
          <div className="space-y-6">
            {/* Summary Scorecard Ribbon */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3.5">
              <Card className="shadow-sm">
                <CardContent className="p-3.5">
                  <span className="text-xs text-muted-foreground block mb-1">Final Equity</span>
                  <div className="text-lg font-bold font-mono text-foreground">
                    ₹{formatINR(result.summary.final_equity)}
                  </div>
                  <span className={`text-[10px] ${result.summary.total_return_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {formatPct(result.summary.total_return_pct)}
                  </span>
                </CardContent>
              </Card>

              <Card className="shadow-sm">
                <CardContent className="p-3.5">
                  <span className="text-xs text-muted-foreground block mb-1">Sharpe Ratio</span>
                  <div className="text-lg font-bold font-mono text-primary">
                    {formatNumber(result.summary.sharpe_ratio, 2)}
                  </div>
                  <span className="text-[10px] text-muted-foreground/70">Risk-Adjusted</span>
                </CardContent>
              </Card>

              <Card className="shadow-sm">
                <CardContent className="p-3.5">
                  <span className="text-xs text-muted-foreground block mb-1">Max Drawdown</span>
                  <div className="text-lg font-bold font-mono text-rose-400">
                    {result.summary.max_drawdown_pct.toFixed(2)}%
                  </div>
                  <span className="text-[10px] text-muted-foreground/70">Peak-to-Trough</span>
                </CardContent>
              </Card>

              <Card className="shadow-sm">
                <CardContent className="p-3.5">
                  <span className="text-xs text-muted-foreground block mb-1">Win Rate</span>
                  <div className="text-lg font-bold font-mono text-foreground">
                    {(result.summary.win_rate * 100).toFixed(1)}%
                  </div>
                  <span className="text-[10px] text-muted-foreground/70">{result.summary.winning_trades}W / {result.summary.losing_trades}L</span>
                </CardContent>
              </Card>

              <Card className="shadow-sm">
                <CardContent className="p-3.5">
                  <span className="text-xs text-muted-foreground block mb-1">Profit Factor</span>
                  <div className="text-lg font-bold font-mono text-purple-400">
                    {formatNumber(result.summary.profit_factor, 2)}
                  </div>
                  <span className="text-[10px] text-muted-foreground/70">Gross W/L</span>
                </CardContent>
              </Card>

              <Card className="shadow-sm">
                <CardContent className="p-3.5">
                  <span className="text-xs text-muted-foreground block mb-1">Average R</span>
                  <div className="text-lg font-bold font-mono text-emerald-400">
                    {formatNumber(result.summary.average_r, 2)}R
                  </div>
                  <span className="text-[10px] text-muted-foreground/70">{result.summary.total_trades} Total Trades</span>
                </CardContent>
              </Card>
            </div>

            {/* Equity Curve Chart */}
            {chartData && (
              <Card className="shadow-2xl">
                <CardHeader className="border-b border-border pb-3">
                  <CardTitle className="text-sm font-bold text-foreground">Simulated Equity Curve</CardTitle>
                </CardHeader>
                <CardContent className="p-6">
                  <div className="h-72 w-full">
                    <Line data={chartData} options={chartOptions} />
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Monte Carlo Bootstrap Risk Simulator (ADR-033) */}
            {result.monte_carlo && result.monte_carlo.iterations > 0 && (
              <Card className="shadow-2xl border-primary/20">
                <CardHeader className="border-b border-border pb-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <Dices className="w-4 h-4 text-primary" />
                      <CardTitle className="text-sm font-bold text-foreground">
                        Monte Carlo Bootstrap Risk Assessment ({result.monte_carlo.iterations.toLocaleString()} Iterations)
                      </CardTitle>
                    </div>
                    <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                      ADR-033 Resampling
                    </span>
                  </div>
                  <CardDescription className="text-xs text-muted-foreground mt-0.5">
                    1,000 i.i.d. trade order resamplings with replacement to estimate tail drawdown and probability of ruin
                  </CardDescription>
                </CardHeader>
                <CardContent className="p-6 space-y-6">
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                    <div className="p-3 rounded-lg bg-muted/40 border border-border">
                      <span className="text-xs text-muted-foreground block mb-1">95th %ile Max DD</span>
                      <div className="text-lg font-bold font-mono text-rose-400">
                        {result.monte_carlo.p95_max_drawdown_pct.toFixed(2)}%
                      </div>
                      <span className="text-[10px] text-muted-foreground/70">1-in-20 Tail Risk</span>
                    </div>

                    <div className="p-3 rounded-lg bg-muted/40 border border-border">
                      <span className="text-xs text-muted-foreground block mb-1">99th %ile Max DD</span>
                      <div className="text-lg font-bold font-mono text-rose-500">
                        {result.monte_carlo.p99_max_drawdown_pct.toFixed(2)}%
                      </div>
                      <span className="text-[10px] text-muted-foreground/70">1-in-100 Black Swan</span>
                    </div>

                    <div className="p-3 rounded-lg bg-muted/40 border border-border">
                      <span className="text-xs text-muted-foreground block mb-1">Risk of Ruin (≥50% DD)</span>
                      <div className={`text-lg font-bold font-mono ${result.monte_carlo.ruin_probability_pct === 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {result.monte_carlo.ruin_probability_pct.toFixed(1)}%
                      </div>
                      <span className="text-[10px] text-muted-foreground/70">Terminal Failure Prob</span>
                    </div>

                    <div className="p-3 rounded-lg bg-muted/40 border border-border">
                      <span className="text-xs text-muted-foreground block mb-1">90% Equity Range</span>
                      <div className="text-sm font-bold font-mono text-foreground mt-1">
                        ₹{formatINR(result.monte_carlo.p05_final_equity)} - ₹{formatINR(result.monte_carlo.p95_final_equity)}
                      </div>
                      <span className="text-[10px] text-muted-foreground/70">5th to 95th Percentile</span>
                    </div>
                  </div>

                  {result.monte_carlo.drawdown_distribution.length > 0 && (
                    <div className="space-y-2">
                      <div className="flex justify-between items-center text-xs text-muted-foreground">
                        <span>Max Drawdown Distribution Histogram (10 Bins)</span>
                        <span>Mean DD: {result.monte_carlo.mean_drawdown_pct.toFixed(2)}%</span>
                      </div>
                      <div className="grid grid-cols-10 gap-1.5 h-20 items-end bg-muted/20 p-2.5 rounded-lg border border-border">
                        {result.monte_carlo.drawdown_distribution.map((count, idx) => {
                          const maxCount = Math.max(...result.monte_carlo!.drawdown_distribution, 1);
                          const heightPct = Math.max(8, (count / maxCount) * 100);
                          return (
                            <div key={idx} className="flex flex-col items-center h-full justify-end group relative">
                              <div
                                style={{ height: `${heightPct}%` }}
                                className="w-full bg-primary/70 hover:bg-primary rounded-t transition-all"
                              />
                              <div className="opacity-0 group-hover:opacity-100 absolute -top-7 bg-popover text-popover-foreground text-[10px] px-1.5 py-0.5 rounded shadow whitespace-nowrap z-10 pointer-events-none">
                                {count} iterations
                              </div>
                            </div>
                          );
                        })}
                      </div>
                      <div className="flex justify-between text-[10px] text-muted-foreground font-mono px-1">
                        <span>0%</span>
                        <span>Estimated Max Drawdown Severity</span>
                        <span>{result.monte_carlo.p99_max_drawdown_pct.toFixed(0)}%+</span>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Simulated Trades Table */}
            <Card className="shadow-2xl space-y-4">
              <CardHeader className="border-b border-border pb-3">
                <CardTitle className="text-sm font-bold text-foreground">Simulated Trade Executions</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <Table>
                  <TableHeader className="bg-muted/50">
                    <TableRow>
                      <TableHead className="text-[11px] font-semibold uppercase tracking-wider">Entry Date</TableHead>
                      <TableHead className="text-[11px] font-semibold uppercase tracking-wider">Exit Date</TableHead>
                      <TableHead className="text-[11px] font-semibold uppercase tracking-wider">Entry Fill</TableHead>
                      <TableHead className="text-[11px] font-semibold uppercase tracking-wider">Exit Fill</TableHead>
                      <TableHead className="text-[11px] font-semibold uppercase tracking-wider">Quantity</TableHead>
                      <TableHead className="text-[11px] font-semibold uppercase tracking-wider">R-Multiple</TableHead>
                      <TableHead className="text-[11px] font-semibold uppercase tracking-wider">Exit Reason</TableHead>
                      <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-right">Net P&L</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody className="font-mono">
                    {result.trades.map((tr) => {
                      const isWin = tr.net_pnl >= 0;
                      return (
                        <TableRow key={tr.trade_id} className="hover:bg-muted/40 transition">
                          <TableCell className="text-muted-foreground">{tr.entry_date}</TableCell>
                          <TableCell className="text-muted-foreground">{tr.exit_date}</TableCell>
                          <TableCell className="text-foreground">₹{formatINR(tr.entry_price)}</TableCell>
                          <TableCell className="text-foreground">₹{formatINR(tr.exit_price)}</TableCell>
                          <TableCell className="text-foreground">{tr.quantity}</TableCell>
                          <TableCell className={`font-bold ${isWin ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {tr.r_multiple > 0 ? '+' : ''}{tr.r_multiple.toFixed(2)}R
                          </TableCell>
                          <TableCell className="font-sans text-muted-foreground">{tr.exit_reason}</TableCell>
                          <TableCell className={`text-right font-bold ${isWin ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {isWin ? '+' : ''}₹{formatINR(tr.net_pnl)}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </TooltipProvider>
  );
};
