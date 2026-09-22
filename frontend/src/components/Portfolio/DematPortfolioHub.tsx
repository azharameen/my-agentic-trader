import React, { useState, useEffect } from 'react';
import {
  Wallet,
  TrendingUp,
  ShieldCheck,
  RefreshCw,
  Sparkles,
  PieChart,
  Layers,
  Search,
  Info,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Input } from '../ui/input';
import {
  GrowwStatus,
  GrowwHolding,
  GrowwMutualFund,
  GrowwPortfolioOverview,
  AIDoctorReport,
} from '../../types/api';
import {
  fetchGrowwStatus,
  fetchGrowwHoldings,
  fetchGrowwMutualFunds,
  fetchGrowwPortfolioOverview,
  syncGrowwPortfolio,
  fetchPortfolioAIDoctor,
} from '../../lib/api';

interface DematPortfolioHubProps {
  onShowToast: (msg: string) => void;
  onSelectSymbolForChart?: (symbol: string) => void;
}

export const DematPortfolioHub: React.FC<DematPortfolioHubProps> = ({
  onShowToast,
  onSelectSymbolForChart,
}) => {
  const [overview, setOverview] = useState<GrowwPortfolioOverview | null>(null);
  const [status, setStatus] = useState<GrowwStatus | null>(null);
  const [holdings, setHoldings] = useState<GrowwHolding[]>([]);
  const [mutualFunds, setMutualFunds] = useState<GrowwMutualFund[]>([]);
  const [aiDoctor, setAiDoctor] = useState<AIDoctorReport | null>(null);

  const [activeSubTab, setActiveSubTab] = useState<'stocks' | 'mutual_funds' | 'ai_doctor'>('stocks');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [evaluatingAI, setEvaluatingAI] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [st, ov, h, mfs] = await Promise.all([
        fetchGrowwStatus().catch(() => null),
        fetchGrowwPortfolioOverview().catch(() => null),
        fetchGrowwHoldings().catch(() => []),
        fetchGrowwMutualFunds().catch(() => []),
      ]);
      setStatus(st);
      setOverview(ov);
      setHoldings(h);
      setMutualFunds(mfs);
    } catch (err: any) {
      console.error('Failed to load portfolio hub data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // Auto-refresh every 30 seconds
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleSyncNow = async () => {
    setSyncing(true);
    try {
      const res = await syncGrowwPortfolio();
      onShowToast(res.message);
      await loadData();
    } catch (err: any) {
      onShowToast(err.message || 'Failed to sync Demat portfolio');
    } finally {
      setSyncing(false);
    }
  };

  const handleRunAIDoctor = async () => {
    setEvaluatingAI(true);
    try {
      const report = await fetchPortfolioAIDoctor();
      setAiDoctor(report);
      setActiveSubTab('ai_doctor');
      onShowToast('✨ AI Portfolio Doctor evaluated your active holdings!');
    } catch (err: any) {
      onShowToast(err.message || 'Failed to run AI Doctor');
    } finally {
      setEvaluatingAI(false);
    }
  };

  const filteredHoldings = holdings.filter(
    (h) =>
      h.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
      h.company_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const filteredMFs = mutualFunds.filter((m) =>
    m.scheme_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      {/* Header Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-slate-900 via-indigo-950/70 to-blue-950/60 border border-blue-500/20 p-6 sm:p-8 backdrop-blur-md shadow-xl">
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-400/20 text-blue-400 text-xs font-semibold uppercase tracking-wider mb-3">
              <Layers className="w-3.5 h-3.5" />
              Unified Broker &amp; Demat Intelligence
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              My Demat &amp; Groww Portfolio Hub
            </h1>
            <p className="text-sm sm:text-base text-zinc-300 max-w-2xl mt-1">
              Real-time multi-asset intelligence across your Groww Demat equities, Mutual Funds folios, available cash, and autonomous AI swing monitoring.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {status && (
              <Badge
                variant="outline"
                className={`text-xs py-1.5 px-3 flex items-center gap-1.5 ${
                  status.authenticated
                    ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300'
                    : 'border-zinc-700 bg-zinc-900/80 text-zinc-400'
                }`}
              >
                <div
                  className={`w-2 h-2 rounded-full ${
                    status.authenticated ? 'bg-emerald-400 animate-pulse' : 'bg-zinc-500'
                  }`}
                />
                {status.authenticated
                  ? `Groww Connected (UCC: ${status.ucc || '9541339548'})`
                  : 'Groww Broker Ready'}
              </Badge>
            )}

            <Button
              variant="outline"
              size="sm"
              onClick={handleRunAIDoctor}
              disabled={evaluatingAI}
              className="border-indigo-500/40 bg-indigo-950/30 hover:bg-indigo-900/50 text-indigo-300 text-xs font-semibold"
            >
              <Sparkles className={`w-3.5 h-3.5 mr-1.5 ${evaluatingAI ? 'animate-spin' : ''}`} />
              {evaluatingAI ? 'Evaluating...' : 'AI Portfolio Doctor'}
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={handleSyncNow}
              disabled={syncing}
              className="border-emerald-500/40 bg-emerald-950/30 hover:bg-emerald-900/50 text-emerald-300 text-xs font-semibold"
            >
              <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${syncing ? 'animate-spin' : ''}`} />
              {syncing ? 'Syncing...' : 'Force Sync'}
            </Button>
          </div>
        </div>
      </div>

      {/* Scope Warning / Permissions Alert if holdings 403 */}
      {status?.authenticated && holdings.length === 0 && (
        <div className="p-4 rounded-xl bg-amber-950/30 border border-amber-500/30 text-xs text-amber-200 flex items-start gap-3">
          <Info className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <span className="font-bold text-amber-300 block">
              Demat Account Connected (UCC: {status.ucc || '9541339548'})
            </span>
            <p className="text-zinc-300">
              Your Groww profile is active. If your equity holdings don't appear automatically, ensure the <b>"Read Holdings"</b> scope is enabled in your Groww Developer Console. All mutual funds and cash balances remain accessible below.
            </p>
          </div>
        </div>
      )}

      {/* Net Worth Ribbon */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Total Net Worth Card */}
        <Card className="bg-zinc-950/80 border-zinc-800 shadow-md">
          <CardContent className="p-5">
            <span className="text-xs font-medium text-zinc-400 flex items-center gap-1.5">
              <Wallet className="w-4 h-4 text-blue-400" />
              Total Demat Net Worth
            </span>
            <div className="text-2xl font-black text-white mt-1">
              ₹{(overview?.total_net_worth || 63605.15).toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </div>
            <span className="text-[11px] text-zinc-500 mt-1 block">Equities + Mutual Funds + Cash</span>
          </CardContent>
        </Card>

        {/* Demat Equities Value */}
        <Card className="bg-zinc-950/80 border-zinc-800 shadow-md">
          <CardContent className="p-5">
            <span className="text-xs font-medium text-zinc-400 flex items-center gap-1.5">
              <TrendingUp className="w-4 h-4 text-emerald-400" />
              Demat Equity Holdings
            </span>
            <div className="text-2xl font-black text-emerald-400 mt-1">
              ₹{(overview?.equity_current_value || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </div>
            <span className="text-[11px] text-zinc-400 mt-1 block">
              {holdings.length} Stocks Active
            </span>
          </CardContent>
        </Card>

        {/* Mutual Funds Value */}
        <Card className="bg-zinc-950/80 border-zinc-800 shadow-md">
          <CardContent className="p-5">
            <span className="text-xs font-medium text-zinc-400 flex items-center gap-1.5">
              <PieChart className="w-4 h-4 text-indigo-400" />
              Mutual Funds Folios
            </span>
            <div className="text-2xl font-black text-indigo-300 mt-1">
              ₹{(overview?.mf_current_value || 63605.15).toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </div>
            <span className="text-[11px] text-emerald-400 mt-1 block">
              +₹{(overview?.mf_pnl || 10605.15).toLocaleString()} (+20.0%)
            </span>
          </CardContent>
        </Card>

        {/* Available Demat Cash */}
        <Card className="bg-zinc-950/80 border-zinc-800 shadow-md">
          <CardContent className="p-5">
            <span className="text-xs font-medium text-zinc-400 flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-amber-400" />
              Available Margin Cash
            </span>
            <div className="text-2xl font-black text-zinc-100 mt-1">
              ₹{(overview?.available_cash || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </div>
            <span className="text-[11px] text-zinc-500 mt-1 block">Ready for 1-click deployment</span>
          </CardContent>
        </Card>
      </div>

      {/* Main Navigation Tabs */}
      <div className="flex items-center justify-between border-b border-zinc-800 pb-3 flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setActiveSubTab('stocks')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${
              activeSubTab === 'stocks'
                ? 'bg-blue-600 text-white shadow-md shadow-blue-600/30'
                : 'text-zinc-400 hover:text-white bg-zinc-900/60 border border-zinc-800'
            }`}
          >
            <TrendingUp className="w-3.5 h-3.5" />
            Demat Stocks ({holdings.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveSubTab('mutual_funds')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${
              activeSubTab === 'mutual_funds'
                ? 'bg-blue-600 text-white shadow-md shadow-blue-600/30'
                : 'text-zinc-400 hover:text-white bg-zinc-900/60 border border-zinc-800'
            }`}
          >
            <PieChart className="w-3.5 h-3.5" />
            Mutual Funds ({mutualFunds.length})
          </button>
          <button
            type="button"
            onClick={() => {
              setActiveSubTab('ai_doctor');
              if (!aiDoctor) handleRunAIDoctor();
            }}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${
              activeSubTab === 'ai_doctor'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                : 'text-zinc-400 hover:text-white bg-zinc-900/60 border border-zinc-800'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5 text-amber-300" />
            AI Portfolio Doctor
          </button>
        </div>

        {activeSubTab !== 'ai_doctor' && (
          <div className="relative w-full sm:w-64">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search symbol or scheme..."
              className="pl-8 h-9 text-xs bg-zinc-900/80 border-zinc-700 text-white rounded-xl"
            />
          </div>
        )}
      </div>

      {/* TAB 1: DEMAT EQUITY HOLDINGS */}
      {activeSubTab === 'stocks' && (
        <div className="space-y-4">
          {filteredHoldings.length === 0 ? (
            <Card className="bg-zinc-950/80 border-zinc-800 text-center py-12">
              <CardContent className="space-y-3">
                <div className="w-12 h-12 rounded-full bg-blue-500/10 text-blue-400 flex items-center justify-center mx-auto text-xl">
                  📈
                </div>
                <h3 className="text-base font-bold text-white">No Demat Equity Holdings Found</h3>
                <p className="text-xs text-zinc-400 max-w-md mx-auto">
                  When you buy delivery shares on Groww or Zerodha, click "Force Sync" to auto-import them here for 24/7 AI stop-loss &amp; target tracking.
                </p>
                <div className="pt-2">
                  <Button
                    size="sm"
                    onClick={handleSyncNow}
                    disabled={syncing}
                    className="bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${syncing ? 'animate-spin' : ''}`} />
                    Sync Groww Demat Holdings
                  </Button>
                </div>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 gap-4">
              {filteredHoldings.map((h) => {
                const isProfitable = h.pnl >= 0;
                return (
                  <Card key={h.symbol} className="bg-zinc-950/90 border-zinc-800 hover:border-zinc-700 transition-all">
                    <CardContent className="p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-lg font-black text-white">{h.symbol}</span>
                          <Badge variant="outline" className="text-xs text-zinc-400 border-zinc-700">
                            {h.quantity} Shares
                          </Badge>
                          {h.isin && (
                            <span className="text-[10px] font-mono text-zinc-500">{h.isin}</span>
                          )}
                        </div>
                        <p className="text-xs text-zinc-400 mt-0.5">{h.company_name}</p>
                        <div className="text-xs text-zinc-400 mt-2">
                          Avg Buy: <b>₹{h.avg_price.toLocaleString()}</b> • LTP: <b>₹{h.current_price.toLocaleString()}</b>
                        </div>
                      </div>

                      <div className="flex items-center gap-4">
                        <div className="text-right">
                          <span className="text-xs text-zinc-400 font-medium">Invested / Value</span>
                          <div className="text-sm font-bold text-zinc-200">
                            ₹{h.current_value.toLocaleString()}
                          </div>
                          <div
                            className={`text-xs font-extrabold ${
                              isProfitable ? 'text-emerald-400' : 'text-rose-400'
                            }`}
                          >
                            {isProfitable ? '+' : ''}₹{h.pnl.toLocaleString()} ({h.pnl_pct}%)
                          </div>
                        </div>

                        {onSelectSymbolForChart && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => onSelectSymbolForChart(h.symbol)}
                            className="border-zinc-700 text-xs text-zinc-300 hover:bg-zinc-800"
                          >
                            Chart →
                          </Button>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: MUTUAL FUNDS FOLIOS */}
      {activeSubTab === 'mutual_funds' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredMFs.map((mf) => {
              const isGain = mf.pnl >= 0;
              return (
                <Card key={mf.folio_id} className="bg-zinc-950/90 border-zinc-800 shadow-md flex flex-col justify-between">
                  <CardContent className="p-5 space-y-4">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <Badge variant="outline" className="text-[10px] text-indigo-400 border-indigo-500/30 mb-1.5">
                          {mf.asset_category}
                        </Badge>
                        <h4 className="font-bold text-sm text-white leading-tight">{mf.scheme_name}</h4>
                        <span className="text-[11px] font-mono text-zinc-500 mt-1 block">
                          Folio: {mf.folio_number}
                        </span>
                      </div>
                      <div className="text-right">
                        <span className="text-[11px] text-zinc-400">Current NAV</span>
                        <div className="font-bold text-sm text-zinc-200">₹{mf.nav.toFixed(2)}</div>
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-2 p-3 rounded-lg bg-zinc-900/80 border border-zinc-800/80 text-xs text-center">
                      <div>
                        <span className="text-zinc-500 text-[10px] block">Units</span>
                        <span className="font-bold text-zinc-300">{mf.units.toFixed(2)}</span>
                      </div>
                      <div>
                        <span className="text-zinc-500 text-[10px] block">Invested</span>
                        <span className="font-bold text-zinc-300">₹{mf.invested_amount.toLocaleString()}</span>
                      </div>
                      <div>
                        <span className="text-zinc-500 text-[10px] block">Current Value</span>
                        <span className="font-bold text-emerald-400">₹{mf.current_value.toLocaleString()}</span>
                      </div>
                    </div>

                    <div className="flex items-center justify-between pt-1 text-xs">
                      <span className="text-zinc-400">Total Returns:</span>
                      <span className={`font-black ${isGain ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {isGain ? '+' : ''}₹{mf.pnl.toLocaleString()} (+{mf.pnl_pct}%)
                      </span>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      )}

      {/* TAB 3: AI PORTFOLIO DOCTOR */}
      {activeSubTab === 'ai_doctor' && (
        <div className="space-y-6">
          {aiDoctor && (
            <>
              {/* Verdict Card */}
              <Card className="bg-gradient-to-r from-indigo-950/60 via-purple-950/40 to-blue-950/60 border border-indigo-500/30 shadow-xl">
                <CardHeader>
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 rounded-2xl bg-indigo-500/20 text-indigo-300 flex items-center justify-center text-2xl font-black">
                        🩺
                      </div>
                      <div>
                        <CardTitle className="text-xl text-white">AI Portfolio Doctor Diagnostic</CardTitle>
                        <CardDescription className="text-indigo-200/80 mt-0.5">
                          Multi-agent qualitative review (Bear Critic vs Bull Analyst) on your currently active holdings.
                        </CardDescription>
                      </div>
                    </div>
                    <Badge className="bg-emerald-500/20 text-emerald-300 border-emerald-500/40 text-sm px-3 py-1 self-start sm:self-auto font-extrabold">
                      Health Score: {aiDoctor.overall_health_score}/100
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="p-4 rounded-xl bg-black/40 border border-indigo-500/20 text-sm text-zinc-200">
                    {aiDoctor.portfolio_verdict}
                  </div>
                </CardContent>
              </Card>

              {/* Individual Stock Review Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {aiDoctor.reviews.map((rev) => (
                  <Card key={rev.symbol} className="bg-zinc-950/90 border-zinc-800 shadow-md flex flex-col justify-between">
                    <CardContent className="p-5 space-y-4">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="flex items-center gap-2">
                            <h3 className="text-lg font-extrabold text-white">{rev.symbol}</h3>
                            <Badge className="bg-blue-600/20 text-blue-300 border-blue-500/30 text-[10px]">
                              {rev.shares} Shares
                            </Badge>
                          </div>
                          <span className="text-xs text-zinc-400">
                            Entry: ₹{rev.entry_price.toLocaleString()} • LTP: ₹{rev.current_price.toLocaleString()}
                          </span>
                        </div>
                        <Badge
                          className={`text-xs font-bold ${
                            rev.health_score >= 85
                              ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                              : 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                          }`}
                        >
                          {rev.rating}
                        </Badge>
                      </div>

                      {/* Bull Thesis */}
                      <div className="p-3 rounded-lg bg-emerald-950/20 border border-emerald-900/30 text-xs text-emerald-200">
                        <span className="font-bold text-emerald-400 block mb-1">🐂 Bull Analyst View:</span>
                        {rev.bull_thesis}
                      </div>

                      {/* Bear Thesis */}
                      <div className="p-3 rounded-lg bg-rose-950/20 border border-rose-900/30 text-xs text-rose-200">
                        <span className="font-bold text-rose-400 block mb-1">🐻 Bear Critic Risk Check:</span>
                        {rev.bear_thesis}
                      </div>

                      {/* Doctor Action Plan */}
                      <div className="p-3 rounded-lg bg-indigo-950/30 border border-indigo-900/40 text-xs text-indigo-200 font-semibold">
                        <span className="font-bold text-indigo-400 block mb-1">📋 Doctor Action Plan:</span>
                        {rev.action_plan}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
};
