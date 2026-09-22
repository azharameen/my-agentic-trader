import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  ShieldCheck,
  TrendingUp,
  Zap,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Wallet,
  PieChart,
  Sun,
  Moon,
  Clock,
  ExternalLink,
  DollarSign,
  Info,
  Copy,
  Check,
  Target,
  Smile,
  Receipt,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Input } from '../ui/input';
import {
  StrategyBasket,
  StockAllocation,
  PortfolioSummary,
  DailyDigest,
  RiskVibe,
  InvestmentGoal,
  ReinvestmentSuggestion,
  GrowwStatus,
  GrowwBalance,
} from '../../types/api';
import {
  generateBasket,
  confirmBatchExecutions,
  fetchActivePortfolioHealth,
  exitPosition,
  fetchMorningDigest,
  fetchEveningDigest,
  fetchGrowwStatus,
  fetchGrowwBalance,
  syncGrowwPortfolio,
} from '../../lib/api';

interface BeginnerInvestWizardProps {
  onShowToast: (msg: string) => void;
}

export const BeginnerInvestWizard: React.FC<BeginnerInvestWizardProps> = ({ onShowToast }) => {
  // Navigation & Step State
  const [currentStep, setCurrentStep] = useState<1 | 2 | 3 | 4>(1);
  const [loading, setLoading] = useState(false);

  // Step 1: Input State
  const [capitalInput, setCapitalInput] = useState<string>('50000');
  const [riskVibe, setRiskVibe] = useState<RiskVibe>('BALANCED');
  const [goal, setGoal] = useState<InvestmentGoal>('SAFE_GROWTH');

  // Groww Integration State
  const [growwStatus, setGrowwStatus] = useState<GrowwStatus | null>(null);
  const [growwBalance, setGrowwBalance] = useState<GrowwBalance | null>(null);
  const [growwSyncing, setGrowwSyncing] = useState<boolean>(false);

  // Step 2: Basket State
  const [basket, setBasket] = useState<StrategyBasket | null>(null);
  const [expandedDeepDives, setExpandedDeepDives] = useState<Record<string, boolean>>({});

  // Step 3: Execution Checklist State
  const [executionPrices, setExecutionPrices] = useState<Record<string, number>>({});
  const [executionChecked, setExecutionChecked] = useState<Record<string, boolean>>({});
  const [copiedSymbolGTT, setCopiedSymbolGTT] = useState<string | null>(null);

  // Step 4: Active Portfolio & Digests State
  const [portfolio, setPortfolio] = useState<PortfolioSummary | null>(null);
  const [morningDigest, setMorningDigest] = useState<DailyDigest | null>(null);
  const [eveningDigest, setEveningDigest] = useState<DailyDigest | null>(null);
  const [activeDigestTab, setActiveDigestTab] = useState<'morning' | 'evening'>('morning');
  const [reinvestmentModal, setReinvestmentModal] = useState<ReinvestmentSuggestion | null>(null);
  const [showTaxBreakdown, setShowTaxBreakdown] = useState<Record<string, boolean>>({});

  // Load existing active portfolio on mount if available
  useEffect(() => {
    loadPortfolioData();
  }, []);

  const loadPortfolioData = async () => {
    try {
      const p = await fetchActivePortfolioHealth();
      if (p && p.active_positions.length > 0) {
        setPortfolio(p);
        setCurrentStep(4);
      }
      const [am, pm] = await Promise.all([
        fetchMorningDigest().catch(() => null),
        fetchEveningDigest().catch(() => null),
      ]);
      setMorningDigest(am);
      setEveningDigest(pm);

      // Fetch Groww Status
      fetchGrowwStatus()
        .then((st) => {
          setGrowwStatus(st);
          if (st.authenticated) {
            fetchGrowwBalance()
              .then((bal) => setGrowwBalance(bal))
              .catch(() => null);
          }
        })
        .catch(() => null);
    } catch (err) {
      console.debug('No active portfolio found or backend starting up', err);
    }
  };

  const handleSyncGrowwHoldings = async () => {
    setGrowwSyncing(true);
    try {
      const res = await syncGrowwPortfolio();
      onShowToast(res.message);
      await loadPortfolioData();
    } catch (err: any) {
      onShowToast(err.message || 'Failed to sync Groww portfolio');
    } finally {
      setGrowwSyncing(false);
    }
  };

  // Step 1 -> Step 2: Generate Basket
  const handleGeneratePlan = async () => {
    const amount = parseFloat(capitalInput);
    if (isNaN(amount) || amount < 5000) {
      onShowToast('Please enter an investment amount of at least ₹5,000.');
      return;
    }

    setLoading(true);
    try {
      const plan = await generateBasket(amount, riskVibe, goal, 4);
      setBasket(plan);

      // Pre-fill execution inputs
      const initialPrices: Record<string, number> = {};
      const initialChecks: Record<string, boolean> = {};
      plan.allocations.forEach((a: StockAllocation) => {
        initialPrices[a.symbol] = a.suggested_entry_price;
        initialChecks[a.symbol] = true;
      });
      setExecutionPrices(initialPrices);
      setExecutionChecked(initialChecks);

      setCurrentStep(2);
      onShowToast('✨ Your personalized investment plan is ready!');
    } catch (err: any) {
      onShowToast(err.message || 'Failed to generate plan.');
    } finally {
      setLoading(false);
    }
  };

  // Step 2 -> Step 3: Proceed to Execution
  const handleProceedToExecution = () => {
    setCurrentStep(3);
  };

  // Step 3 -> Step 4: Confirm Executions on Broker
  const handleConfirmBrokerExecutions = async () => {
    if (!basket) return;

    const confirmations = basket.allocations
      .filter((a: StockAllocation) => executionChecked[a.symbol])
      .map((a: StockAllocation) => ({
        symbol: a.symbol,
        shares: a.shares,
        executed_price: executionPrices[a.symbol] || a.suggested_entry_price,
        broker_name: 'External Broker',
      }));

    if (confirmations.length === 0) {
      onShowToast('Please confirm at least one executed stock purchase.');
      return;
    }

    setLoading(true);
    try {
      const summary = await confirmBatchExecutions({
        basket_id: basket.basket_id,
        confirmations,
      });
      setPortfolio(summary);
      setCurrentStep(4);
      onShowToast('🎉 Portfolio active! AI agents are now monitoring your stocks 24/7.');
    } catch (err: any) {
      onShowToast(err.message || 'Failed to confirm execution.');
    } finally {
      setLoading(false);
    }
  };

  // Handle manual full or partial exit on broker
  const handleExitPosition = async (
    posId: string,
    exitPrice: number,
    symbol: string,
    sharesToExit?: number
  ) => {
    try {
      const result = await exitPosition(posId, exitPrice, sharesToExit);
      setReinvestmentModal(result);
      onShowToast(`✅ Recorded exit for ${symbol}. Realized profit: ₹${result.realized_pnl}`);
      await loadPortfolioData();
    } catch (err: any) {
      onShowToast(err.message || 'Failed to record exit.');
    }
  };

  const copyGTTToClipboard = (alloc: StockAllocation) => {
    const text = `GTT Order for ${alloc.symbol} (${alloc.shares} shares):\n• Stop-Loss Trigger: ₹${alloc.gtt_stop_trigger} (Limit: ₹${alloc.gtt_stop_limit})\n• Target 1 (50%): ₹${alloc.gtt_target1_trigger}\n• Target 2 (50%): ₹${alloc.gtt_target2_trigger}`;
    navigator.clipboard.writeText(text);
    setCopiedSymbolGTT(alloc.symbol);
    onShowToast(`📋 Copied GTT parameters for ${alloc.symbol}!`);
    setTimeout(() => setCopiedSymbolGTT(null), 2500);
  };

  const toggleDeepDive = (symbol: string) => {
    setExpandedDeepDives((prev) => ({ ...prev, [symbol]: !prev[symbol] }));
  };

  const toggleTax = (posId: string) => {
    setShowTaxBreakdown((prev) => ({ ...prev, [posId]: !prev[posId] }));
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      {/* Header Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-blue-900/40 via-indigo-950/50 to-purple-900/30 border border-blue-500/20 p-6 sm:p-8 backdrop-blur-md">
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-400/20 text-blue-400 text-xs font-semibold uppercase tracking-wider mb-3">
              <Sparkles className="w-3.5 h-3.5" />
              Beginner-Friendly Wealth Copilot
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Smart Stock Investing, Made Simple
            </h1>
            <p className="text-sm sm:text-base text-zinc-300 max-w-2xl mt-1">
              Zero finance experience required. Tell us how much you want to invest — our autonomous AI agents
              craft a diversified blue-chip plan, generate 1-click GTT orders, and monitor exits 24/7.
            </p>
          </div>
          <div className="flex items-center gap-2">
            {growwStatus && (
              <Badge
                variant="outline"
                className={`text-xs py-1 px-2.5 flex items-center gap-1.5 ${
                  growwStatus.authenticated
                    ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300'
                    : 'border-zinc-700 bg-zinc-900/60 text-zinc-400'
                }`}
              >
                <div
                  className={`w-2 h-2 rounded-full ${
                    growwStatus.authenticated ? 'bg-emerald-400 animate-pulse' : 'bg-zinc-500'
                  }`}
                />
                {growwStatus.authenticated ? 'Groww API Connected' : 'Groww API Ready'}
              </Badge>
            )}
            {currentStep === 4 && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentStep(1)}
                className="border-zinc-700 bg-zinc-900/80 hover:bg-zinc-800 text-xs text-zinc-200"
              >
                <Sparkles className="w-3.5 h-3.5 mr-1.5 text-blue-400" />
                Invest More Capital
              </Button>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={loadPortfolioData}
              className="border-zinc-700 bg-zinc-900/80 hover:bg-zinc-800 text-xs text-zinc-300"
            >
              <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
              Refresh
            </Button>
          </div>
        </div>

        {/* Stepper Indicator */}
        <div className="grid grid-cols-4 gap-2 mt-6 pt-6 border-t border-white/10">
          {[
            { num: 1, label: 'Capital & Goal' },
            { num: 2, label: 'Strategy Plan' },
            { num: 3, label: 'GTT & Broker Buy' },
            { num: 4, label: 'Live Monitoring' },
          ].map((s) => (
            <div
              key={s.num}
              onClick={() => {
                if (s.num < currentStep || (s.num === 4 && portfolio)) {
                  setCurrentStep(s.num as any);
                }
              }}
              className={`flex items-center gap-2 p-2 rounded-lg cursor-pointer transition-all ${
                currentStep === s.num
                  ? 'bg-blue-600/20 border border-blue-500/40 text-blue-300 font-semibold'
                  : currentStep > s.num
                  ? 'text-emerald-400 opacity-90'
                  : 'text-zinc-500 opacity-60'
              }`}
            >
              <div
                className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                  currentStep === s.num
                    ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/30'
                    : currentStep > s.num
                    ? 'bg-emerald-500 text-black'
                    : 'bg-zinc-800 text-zinc-400'
                }`}
              >
                {currentStep > s.num ? '✓' : s.num}
              </div>
              <span className="text-xs hidden sm:inline">{s.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* STEP 1: CAPITAL, GOAL & RISK VIBE SELECTION */}
      {currentStep === 1 && (
        <Card className="bg-zinc-950/80 border-zinc-800 backdrop-blur-sm shadow-xl">
          <CardHeader>
            <CardTitle className="text-xl text-zinc-100 flex items-center gap-2">
              <Wallet className="w-5 h-5 text-blue-400" />
              Step 1: What is your investment budget &amp; goal?
            </CardTitle>
            <CardDescription className="text-zinc-400">
              TrAId will allocate whole shares across safe, high-quality NIFTY 100 stocks with affordability filters.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Quick Amount Chips */}
            <div className="space-y-2">
              <label className="text-xs font-medium text-zinc-300">Select or Enter Investment Budget:</label>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {[
                  { label: '₹15,000 (Affordable)', val: '15000' },
                  { label: '₹30,000', val: '30000' },
                  { label: '₹50,000', val: '50000' },
                  { label: '₹1,00,000', val: '100000' },
                ].map((preset) => (
                  <button
                    key={preset.val}
                    type="button"
                    onClick={() => setCapitalInput(preset.val)}
                    className={`py-3 px-4 rounded-xl text-center border font-bold text-sm transition-all ${
                      capitalInput === preset.val
                        ? 'bg-blue-600/30 border-blue-500 text-blue-300 shadow-md shadow-blue-600/20'
                        : 'bg-zinc-900/60 border-zinc-800 text-zinc-300 hover:border-zinc-700 hover:bg-zinc-900'
                    }`}
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Custom Amount Input */}
            <div className="space-y-2">
              <div className="relative">
                <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-500 font-bold">₹</span>
                <Input
                  type="number"
                  value={capitalInput}
                  onChange={(e) => setCapitalInput(e.target.value)}
                  placeholder="e.g. 50000"
                  className="pl-8 bg-zinc-900/90 border-zinc-700 text-lg font-bold text-white h-12 rounded-xl focus:border-blue-500"
                />
              </div>

              {/* Groww Balance Auto-fill Banner */}
              {growwStatus?.authenticated && growwBalance && growwBalance.available_cash > 0 && (
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between p-3 rounded-xl bg-emerald-950/30 border border-emerald-500/30 gap-2">
                  <div className="flex items-center gap-2 text-xs text-emerald-300">
                    <Zap className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>
                      Groww Demat Cash: <strong>₹{growwBalance.available_cash.toLocaleString('en-IN')}</strong> (Margin: ₹{growwBalance.total_margin.toLocaleString('en-IN')})
                    </span>
                  </div>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => setCapitalInput(Math.floor(growwBalance.available_cash).toString())}
                    className="h-7 text-xs border-emerald-500/50 text-emerald-300 hover:bg-emerald-600/20"
                  >
                    Auto-fill from Groww
                  </Button>
                </div>
              )}

              {parseFloat(capitalInput) < 30000 && (
                <p className="text-[11px] text-blue-400 flex items-center gap-1">
                  <Info className="w-3.5 h-3.5" />
                  Affordability Mode Enabled: We will pick quality stocks under ₹1,500 so you get multiple whole shares.
                </p>
              )}
            </div>

            {/* Goal Selection */}
            <div className="space-y-3 pt-2">
              <label className="text-xs font-medium text-zinc-300">Select Your Investment Goal:</label>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {[
                  {
                    id: 'SAFE_GROWTH' as InvestmentGoal,
                    icon: '🛡️',
                    label: 'Safe Growth',
                    desc: 'Index-like stability & steady capital defense',
                  },
                  {
                    id: 'VACATION_FUND' as InvestmentGoal,
                    icon: '✈️',
                    label: 'Vacation Fund',
                    desc: '3-6 months swing target for short goals',
                  },
                  {
                    id: 'WEALTH_COMPOUNDING' as InvestmentGoal,
                    icon: '🚀',
                    label: 'Wealth Alpha',
                    desc: 'Ride strong momentum breakouts for compounding',
                  },
                  {
                    id: 'LEARNING' as InvestmentGoal,
                    icon: '🎓',
                    label: 'Learn the Ropes',
                    desc: 'Ultra-safe educational setups for newcomers',
                  },
                ].map((g) => (
                  <div
                    key={g.id}
                    onClick={() => setGoal(g.id)}
                    className={`p-3 rounded-xl border cursor-pointer transition-all flex flex-col justify-between ${
                      goal === g.id
                        ? 'border-blue-500 bg-blue-950/30 text-blue-200'
                        : 'border-zinc-800 bg-zinc-900/40 text-zinc-400 hover:border-zinc-700'
                    }`}
                  >
                    <div className="text-lg mb-1">{g.icon}</div>
                    <div className="font-bold text-xs text-white mb-0.5">{g.label}</div>
                    <div className="text-[10px] text-zinc-400">{g.desc}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Risk Vibe Selection */}
            <div className="space-y-3 pt-2">
              <label className="text-xs font-medium text-zinc-300">Choose Your Strategy Vibe:</label>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {[
                  {
                    id: 'CONSERVATIVE' as RiskVibe,
                    icon: <ShieldCheck className="w-5 h-5 text-emerald-400" />,
                    title: 'Conservative & Steady',
                    subtitle: 'Large-cap anchors with low drawdowns',
                    gain: '+6% to +10% target',
                    duration: '4 to 8 Weeks',
                    color: 'hover:border-emerald-500/50',
                    activeColor: 'border-emerald-500 bg-emerald-950/20',
                  },
                  {
                    id: 'BALANCED' as RiskVibe,
                    icon: <TrendingUp className="w-5 h-5 text-blue-400" />,
                    title: 'Balanced Swing (Recommended)',
                    subtitle: 'Optimal swing trends & strong pullbacks',
                    gain: '+8% to +14% target',
                    duration: '2 to 4 Weeks',
                    color: 'hover:border-blue-500/50',
                    activeColor: 'border-blue-500 bg-blue-950/30',
                  },
                  {
                    id: 'MOMENTUM' as RiskVibe,
                    icon: <Zap className="w-5 h-5 text-amber-400" />,
                    title: 'High Momentum Breakouts',
                    subtitle: 'High volume breakouts for active swing gains',
                    gain: '+12% to +22% target',
                    duration: '1 to 2 Weeks',
                    color: 'hover:border-amber-500/50',
                    activeColor: 'border-amber-500 bg-amber-950/20',
                  },
                ].map((v) => (
                  <div
                    key={v.id}
                    onClick={() => setRiskVibe(v.id)}
                    className={`p-4 rounded-xl border cursor-pointer transition-all flex flex-col justify-between ${
                      riskVibe === v.id ? v.activeColor : 'border-zinc-800 bg-zinc-900/40 ' + v.color
                    }`}
                  >
                    <div>
                      <div className="flex items-center gap-2 mb-2">
                        {v.icon}
                        <h4 className="font-bold text-sm text-zinc-100">{v.title}</h4>
                      </div>
                      <p className="text-xs text-zinc-400 mb-3">{v.subtitle}</p>
                    </div>
                    <div className="pt-3 border-t border-zinc-800/80 flex items-center justify-between text-xs font-semibold">
                      <span className="text-emerald-400">{v.gain}</span>
                      <span className="text-zinc-500">{v.duration}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* CTA Button */}
            <div className="pt-4 flex justify-end">
              <Button
                onClick={handleGeneratePlan}
                disabled={loading}
                className="w-full sm:w-auto px-8 py-6 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-base shadow-lg shadow-blue-600/30 transition-all flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Screening Universe & Sizing 2-Tranche Allocations...
                  </>
                ) : (
                  <>
                    Generate My Investment Plan
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* STEP 2: STRATEGY BASKET REVIEW & SCENARIOS */}
      {currentStep === 2 && basket && (
        <div className="space-y-6">
          {/* Peace of Mind & Allocation Summary Box */}
          <Card className="bg-zinc-950/80 border-zinc-800">
            <CardHeader className="pb-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                  <div className="flex items-center gap-3">
                    <CardTitle className="text-xl text-white flex items-center gap-2">
                      <PieChart className="w-5 h-5 text-blue-400" />
                      Your Smart Portfolio Allocation
                    </CardTitle>
                    <Badge className="bg-emerald-500/20 text-emerald-300 border-emerald-500/40 text-xs px-2.5 py-0.5">
                      Peace of Mind Score: {basket.peace_of_mind_score || 92}/100 🧘
                    </Badge>
                  </div>
                  <CardDescription className="text-zinc-400 mt-1">
                    {basket.overall_thesis}
                  </CardDescription>
                </div>
                <Badge className="bg-blue-600/20 text-blue-300 border-blue-500/30 text-xs px-3 py-1 self-start sm:self-auto">
                  {basket.risk_vibe} • {basket.allocations.length} Stocks
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Capital Breakdown */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 rounded-xl bg-zinc-900/60 border border-zinc-800">
                <div>
                  <span className="text-xs text-zinc-400">Total Capital</span>
                  <div className="text-lg font-bold text-white">₹{basket.total_capital.toLocaleString()}</div>
                </div>
                <div>
                  <span className="text-xs text-zinc-400">Allocated to Stocks</span>
                  <div className="text-lg font-bold text-emerald-400">₹{basket.allocated_capital.toLocaleString()}</div>
                </div>
                <div>
                  <span className="text-xs text-zinc-400">Cash Cushion</span>
                  <div className="text-lg font-bold text-zinc-300">₹{basket.cash_reserve.toLocaleString()}</div>
                </div>
                <div>
                  <span className="text-xs text-zinc-400">Market Environment</span>
                  <div className="text-lg font-bold text-blue-400">{basket.market_regime}</div>
                </div>
              </div>

              {/* Scenario Projections */}
              <div className="p-4 rounded-xl bg-gradient-to-r from-blue-950/20 via-indigo-950/30 to-purple-950/20 border border-blue-500/20">
                <span className="text-xs font-bold text-blue-300 block mb-2">📊 Projected Outcome Scenarios:</span>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                  <div className="p-3 rounded-lg bg-zinc-900/80 border border-emerald-500/30">
                    <span className="text-emerald-400 font-bold block">🟢 Best Case (Full Targets)</span>
                    <span className="text-base font-extrabold text-white">
                      +₹{(basket.scenario_best_case || 0).toLocaleString()}
                    </span>
                    <span className="text-[10px] text-zinc-400 block mt-0.5">Tranche 1 &amp; Runner targets hit</span>
                  </div>
                  <div className="p-3 rounded-lg bg-zinc-900/80 border border-blue-500/30">
                    <span className="text-blue-400 font-bold block">🔵 Expected Case (Swing)</span>
                    <span className="text-base font-extrabold text-white">
                      +₹{(basket.scenario_normal || 0).toLocaleString()}
                    </span>
                    <span className="text-[10px] text-zinc-400 block mt-0.5">60% of target swing momentum</span>
                  </div>
                  <div className="p-3 rounded-lg bg-zinc-900/80 border border-rose-500/30">
                    <span className="text-rose-400 font-bold block">🟠 Max Bounded Drawdown</span>
                    <span className="text-base font-extrabold text-rose-300">
                      -₹{Math.abs(basket.scenario_worst_case || 0).toLocaleString()}
                    </span>
                    <span className="text-[10px] text-zinc-400 block mt-0.5">Strictly limited by hard stop-losses</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Stock Allocation Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {basket.allocations.map((alloc) => {
              const isExpanded = !!expandedDeepDives[alloc.symbol];
              return (
                <Card
                  key={alloc.symbol}
                  className="bg-zinc-950/90 border-zinc-800 hover:border-zinc-700 transition-all shadow-md flex flex-col justify-between"
                >
                  <CardContent className="p-5 space-y-4">
                    {/* Top Row: Symbol & Sector */}
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="text-lg font-extrabold text-white tracking-tight">{alloc.symbol}</h3>
                          <Badge variant="outline" className="text-xs text-zinc-400 border-zinc-700">
                            {alloc.sector}
                          </Badge>
                        </div>
                        <p className="text-xs text-zinc-400">{alloc.company_name}</p>
                      </div>
                      <div className="text-right">
                        <span className="text-xs text-zinc-400 font-medium">Allocation</span>
                        <div className="text-base font-bold text-blue-400">
                          ₹{alloc.total_cost.toLocaleString()}{' '}
                          <span className="text-xs text-zinc-500 font-normal">({alloc.shares} shares)</span>
                        </div>
                      </div>
                    </div>

                    {/* 2-Tranche Metrics Grid */}
                    <div className="grid grid-cols-3 gap-2 p-3 rounded-lg bg-zinc-900/80 border border-zinc-800/80 text-center text-xs">
                      <div>
                        <span className="text-zinc-500 block text-[11px]">Buy At</span>
                        <span className="font-bold text-zinc-200">₹{alloc.suggested_entry_price.toLocaleString()}</span>
                      </div>
                      <div>
                        <span className="text-emerald-500 block text-[11px]">Target 1 ({alloc.target1_shares} sh)</span>
                        <span className="font-bold text-emerald-400">₹{(alloc.target1_price || alloc.target_price).toLocaleString()}</span>
                      </div>
                      <div>
                        <span className="text-indigo-400 block text-[11px]">Target 2 ({alloc.target2_shares} sh)</span>
                        <span className="font-bold text-indigo-300">₹{(alloc.target2_price || alloc.target_price * 1.08).toLocaleString()}</span>
                      </div>
                    </div>

                    {/* Layman Rationale */}
                    <div className="p-3 rounded-lg bg-blue-950/20 border border-blue-900/30 text-xs text-blue-200/90 leading-relaxed">
                      <span className="font-bold text-blue-400 block mb-1">💡 Why this stock:</span>
                      {alloc.layman_rationale}
                    </div>

                    {/* Expandable Deep Dive */}
                    {alloc.deep_dive_summary && (
                      <div>
                        <button
                          type="button"
                          onClick={() => toggleDeepDive(alloc.symbol)}
                          className="text-xs text-zinc-400 hover:text-zinc-200 flex items-center gap-1 font-medium transition-colors"
                        >
                          {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                          {isExpanded ? 'Hide Technical Deep-Dive' : 'View Analyst Deep-Dive & Metrics'}
                        </button>
                        {isExpanded && (
                          <div className="mt-2 p-3 rounded bg-black/50 border border-zinc-800 text-[11px] font-mono text-zinc-400">
                            {alloc.deep_dive_summary}
                          </div>
                        )}
                      </div>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>

          {/* Action Bar */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 rounded-xl bg-zinc-900/70 border border-zinc-800">
            <Button
              variant="outline"
              onClick={() => setCurrentStep(1)}
              className="border-zinc-700 text-zinc-300 hover:bg-zinc-800 w-full sm:w-auto"
            >
              ← Modify Capital &amp; Goal
            </Button>
            <Button
              onClick={handleProceedToExecution}
              className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold px-8 py-5 rounded-xl shadow-lg shadow-emerald-600/20 w-full sm:w-auto flex items-center justify-center gap-2"
            >
              Approve Plan &amp; View GTT Orders
              <ArrowRight className="w-4 h-4" />
            </Button>
          </div>
        </div>
      )}

      {/* STEP 3: GTT HELPER & BROKER BUY CHECKLIST */}
      {currentStep === 3 && basket && (
        <Card className="bg-zinc-950/90 border-zinc-800 shadow-xl">
          <CardHeader>
            <CardTitle className="text-xl text-white flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              Step 3: Buy on Broker &amp; Set 1-Click GTT Orders
            </CardTitle>
            <CardDescription className="text-zinc-400">
              Open Zerodha Kite, Groww, or AngelOne. Buy the delivery shares, set GTT triggers for peace of mind, and acknowledge fills below.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* GTT & Slippage Explanation */}
            <div className="p-4 rounded-xl bg-gradient-to-r from-blue-950/40 to-indigo-950/40 border border-blue-500/20 text-xs sm:text-sm text-zinc-300 space-y-2">
              <div className="font-bold text-blue-300 flex items-center gap-1.5">
                <Info className="w-4 h-4" />
                GTT (Good Till Triggered) Order Guide:
              </div>
              <ul className="list-disc list-inside space-y-1 text-zinc-300 text-xs pl-2">
                <li><b>Buy Delivery (CNC):</b> Place normal market/limit buy for the specified shares.</li>
                <li><b>Create GTT Stop &amp; Target:</b> In your broker app, click "Create GTT" and copy the trigger numbers below.</li>
                <li><b>No Chart Watching Needed:</b> Once GTT is placed, your exit is automated even if you are asleep.</li>
              </ul>
            </div>

            {/* Checklist & GTT Copy Cards */}
            <div className="space-y-4">
              {basket.allocations.map((alloc) => {
                const isChecked = !!executionChecked[alloc.symbol];
                const currentEnteredPrice = executionPrices[alloc.symbol] || alloc.suggested_entry_price;
                const driftPct = ((currentEnteredPrice - alloc.suggested_entry_price) / alloc.suggested_entry_price) * 100;
                const absDrift = Math.abs(driftPct);

                return (
                  <div
                    key={alloc.symbol}
                    className={`p-4 rounded-xl border transition-all ${
                      isChecked
                        ? 'bg-zinc-900/60 border-emerald-500/40'
                        : 'bg-zinc-900/30 border-zinc-800 opacity-60'
                    }`}
                  >
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-3">
                      {/* Left: Checkbox & Symbol */}
                      <div className="flex items-center gap-3">
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={(e) =>
                            setExecutionChecked((prev) => ({
                              ...prev,
                              [alloc.symbol]: e.target.checked,
                            }))
                          }
                          className="w-5 h-5 rounded border-zinc-700 bg-zinc-900 text-emerald-500 focus:ring-emerald-500 cursor-pointer"
                        />
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-extrabold text-base text-white">{alloc.symbol}</span>
                            <Badge variant="outline" className="text-[11px] text-zinc-400">
                              Buy {alloc.shares} Shares (Delivery)
                            </Badge>
                          </div>
                          <span className="text-xs text-zinc-400">Suggested Entry: ₹{alloc.suggested_entry_price.toLocaleString()}</span>
                        </div>
                      </div>

                      {/* Right: Actual Fill Price Editor & Traffic Light */}
                      <div className="flex items-center gap-3 pl-8 md:pl-0">
                        <div className="text-right">
                          <label className="text-[11px] text-zinc-400 block">Actual Filled Price (₹):</label>
                          <div className="flex items-center gap-1.5">
                            <Input
                              type="number"
                              step="0.05"
                              value={currentEnteredPrice}
                              onChange={(e) =>
                                setExecutionPrices((prev) => ({
                                  ...prev,
                                  [alloc.symbol]: parseFloat(e.target.value) || alloc.suggested_entry_price,
                                }))
                              }
                              className="w-28 h-9 text-xs font-bold text-white bg-zinc-950 border-zinc-700 text-right"
                            />
                          </div>
                        </div>

                        {/* Slippage Traffic Light */}
                        {absDrift <= 0.5 ? (
                          <Badge className="bg-emerald-500/10 border-emerald-500/30 text-emerald-400 text-[10px]">
                            🟢 Perfect Fill
                          </Badge>
                        ) : absDrift <= 1.5 ? (
                          <Badge className="bg-amber-500/10 border-amber-500/30 text-amber-300 text-[10px]">
                            🟡 {driftPct > 0 ? `+${driftPct.toFixed(1)}%` : `${driftPct.toFixed(1)}%`} Safe Slippage
                          </Badge>
                        ) : (
                          <Badge className="bg-rose-500/10 border-rose-500/30 text-rose-400 text-[10px]">
                            🔴 {driftPct > 0 ? `+${driftPct.toFixed(1)}%` : `${driftPct.toFixed(1)}%`} High Drift
                          </Badge>
                        )}
                      </div>
                    </div>

                    {/* GTT Helper Bar */}
                    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 p-2.5 rounded-lg bg-black/40 border border-zinc-800 text-[11px]">
                      <div className="flex flex-wrap items-center gap-3 text-zinc-300">
                        <span><b>Stop GTT:</b> ₹{alloc.gtt_stop_trigger || alloc.stop_loss_price}</span>
                        <span><b>Target 1 GTT (50%):</b> ₹{alloc.gtt_target1_trigger || alloc.target_price}</span>
                        <span><b>Target 2 GTT (50%):</b> ₹{alloc.gtt_target2_trigger || alloc.target2_price}</span>
                      </div>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => copyGTTToClipboard(alloc)}
                        className="border-zinc-700 bg-zinc-900 text-[10px] h-7 px-2.5 text-zinc-300 flex items-center gap-1"
                      >
                        {copiedSymbolGTT === alloc.symbol ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                        {copiedSymbolGTT === alloc.symbol ? 'Copied GTT' : 'Copy GTT Numbers'}
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Action Bar */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-zinc-800">
              <Button
                variant="outline"
                onClick={() => setCurrentStep(2)}
                className="border-zinc-700 text-zinc-300 hover:bg-zinc-800 w-full sm:w-auto"
              >
                ← Back to Strategy Plan
              </Button>
              <Button
                onClick={handleConfirmBrokerExecutions}
                disabled={loading}
                className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold px-8 py-5 rounded-xl shadow-lg shadow-emerald-600/30 w-full sm:w-auto flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Activating 24/7 Agent Monitoring...
                  </>
                ) : (
                  <>
                    Confirm Fills &amp; Start 24/7 Monitoring
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* STEP 4: ACTIVE PORTFOLIO MONITORING, 2-TRANCHE PROGRESS & ZEN BANNER */}
      {currentStep === 4 && portfolio && (
        <div className="space-y-6">
          {/* Zen Affirmation Banner if active */}
          {(morningDigest?.zen_mode || eveningDigest?.zen_mode) && (
            <div className="p-4 rounded-2xl bg-gradient-to-r from-emerald-950/40 via-teal-950/30 to-blue-950/40 border border-emerald-500/30 shadow-lg flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-emerald-500/20 flex items-center justify-center text-xl shrink-0">
                🧘
              </div>
              <div>
                <span className="font-extrabold text-emerald-300 text-sm block">Zen Status Active</span>
                <p className="text-xs text-zinc-300">
                  {morningDigest?.zen_message || eveningDigest?.zen_message || 'All positions are in healthy bounds. 0 manual interventions needed today.'}
                </p>
              </div>
            </div>
          )}

          {/* Real-time Portfolio Health Banner */}
          <Card className="bg-zinc-950/80 border-zinc-800 shadow-xl">
            <CardHeader className="pb-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                  <CardTitle className="text-xl text-white flex items-center gap-2">
                    <ShieldCheck className="w-5 h-5 text-emerald-400" />
                    Live Portfolio Health &amp; Agent Monitoring
                  </CardTitle>
                  <CardDescription className="text-zinc-400">
                    TrAId agents are actively evaluating price action, trailing stops, and 2-tranche target milestones.
                  </CardDescription>
                </div>
                <Badge className="bg-emerald-500/10 text-emerald-300 border-emerald-500/20 text-xs px-3 py-1 self-start sm:self-auto">
                  ● ACTIVE MONITORING
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 rounded-xl bg-zinc-900/60 border border-zinc-800">
                <div>
                  <span className="text-xs text-zinc-400">Current Portfolio Value</span>
                  <div className="text-lg font-extrabold text-white">
                    ₹{portfolio.current_value.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </div>
                </div>
                <div>
                  <span className="text-xs text-zinc-400">Total Invested</span>
                  <div className="text-lg font-bold text-zinc-300">₹{portfolio.invested_capital.toLocaleString()}</div>
                </div>
                <div>
                  <span className="text-xs text-zinc-400">Unrealized P&amp;L</span>
                  <div
                    className={`text-lg font-extrabold ${
                      portfolio.unrealized_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'
                    }`}
                  >
                    {portfolio.unrealized_pnl >= 0 ? '+' : ''}₹{portfolio.unrealized_pnl.toLocaleString()} (
                    {portfolio.unrealized_pnl_pct}%)
                  </div>
                </div>
                <div>
                  <span className="text-xs text-zinc-400">Net Profit (Post Tax &amp; STT)</span>
                  <div className="text-lg font-extrabold text-emerald-400">
                    ₹{(portfolio.total_net_pnl || portfolio.unrealized_pnl * 0.8).toLocaleString()}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* High Priority Action Banners */}
          {portfolio.active_positions.some((p) => p.action_required) && (
            <div className="space-y-3">
              {portfolio.active_positions
                .filter((p) => p.action_required)
                .map((pos) => (
                  <div
                    key={pos.position_id}
                    className="p-4 rounded-xl bg-gradient-to-r from-amber-950/60 via-orange-950/50 to-red-950/40 border border-amber-500/50 shadow-lg flex flex-col sm:flex-row sm:items-center justify-between gap-4"
                  >
                    <div className="flex items-start gap-3">
                      <div className="w-9 h-9 rounded-full bg-amber-500/20 flex items-center justify-center shrink-0">
                        <AlertTriangle className="w-5 h-5 text-amber-400" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-extrabold text-white text-base">🚨 Action Alert: {pos.symbol}</span>
                          <Badge className="bg-amber-500 text-black font-bold text-[10px]">{pos.status}</Badge>
                        </div>
                        <p className="text-xs text-zinc-200 mt-0.5">{pos.recommended_action}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {pos.target1_shares && pos.target1_shares < pos.shares && !pos.tranche1_exited && (
                        <Button
                          onClick={() => handleExitPosition(pos.position_id, pos.current_price, pos.symbol, pos.target1_shares)}
                          className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs px-4 py-2 rounded-lg shadow-md"
                        >
                          Book 50% ({pos.target1_shares} sh)
                        </Button>
                      )}
                      <Button
                        onClick={() => handleExitPosition(pos.position_id, pos.current_price, pos.symbol)}
                        className="bg-amber-500 hover:bg-amber-400 text-black font-extrabold text-xs px-4 py-2 rounded-lg shadow-md"
                      >
                        Confirm Full Exit
                      </Button>
                    </div>
                  </div>
                ))}
            </div>
          )}

          {/* Active Holdings Progress List with 2-Tranche Visualizer */}
          <div className="space-y-4">
            <div className="flex items-center justify-between flex-wrap gap-3">
              <h3 className="text-lg font-bold text-zinc-100 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-blue-400" />
                Active Holdings &amp; 2-Tranche Target Progress
              </h3>
              {growwStatus?.configured && (
                <Button
                  size="sm"
                  variant="outline"
                  disabled={growwSyncing}
                  onClick={handleSyncGrowwHoldings}
                  className="border-emerald-500/40 bg-emerald-950/20 text-emerald-300 hover:bg-emerald-900/40 text-xs flex items-center gap-1.5"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${growwSyncing ? 'animate-spin' : ''}`} />
                  {growwSyncing ? 'Syncing...' : 'Sync Groww Demat Holdings'}
                </Button>
              )}
            </div>

            <div className="grid grid-cols-1 gap-4">
              {portfolio.active_positions.map((pos) => {
                const isProfitable = pos.pnl_amount >= 0;
                const isTaxOpen = !!showTaxBreakdown[pos.position_id];

                return (
                  <Card key={pos.position_id} className="bg-zinc-950/90 border-zinc-800">
                    <CardContent className="p-5 space-y-4">
                      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-lg font-black text-white">{pos.symbol}</span>
                            <Badge variant="outline" className="text-xs text-zinc-400 border-zinc-700">
                              {pos.shares} Shares
                            </Badge>
                            {pos.breakeven_locked && (
                              <Badge className="bg-blue-500/20 text-blue-300 border-blue-500/30 text-[10px]">
                                🔒 Break-Even Protected
                              </Badge>
                            )}
                            <span className="text-xs text-zinc-500">({pos.holding_period})</span>
                          </div>
                          <div className="text-xs text-zinc-400 mt-1">
                            Bought at ₹{pos.entry_price.toLocaleString()} • Current: ₹{pos.current_price.toLocaleString()}
                          </div>
                        </div>

                        <div className="flex items-center gap-4">
                          <div className="text-right">
                            <span className="text-xs text-zinc-400">Position P&amp;L</span>
                            <div
                              className={`text-base font-extrabold ${
                                isProfitable ? 'text-emerald-400' : 'text-rose-400'
                              }`}
                            >
                              {isProfitable ? '+' : ''}₹{pos.pnl_amount.toLocaleString()} ({pos.pnl_pct}%)
                            </div>
                          </div>

                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => toggleTax(pos.position_id)}
                            className="border-zinc-800 text-xs text-zinc-400 hover:text-white"
                          >
                            <Receipt className="w-3.5 h-3.5 mr-1" />
                            Tax Net
                          </Button>

                          {pos.shares > 1 && !pos.tranche1_exited && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleExitPosition(pos.position_id, pos.current_price, pos.symbol, pos.target1_shares || Math.floor(pos.shares / 2))}
                              className="border-emerald-700/50 text-emerald-400 hover:bg-emerald-950/30 text-xs"
                            >
                              Exit 50%
                            </Button>
                          )}

                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleExitPosition(pos.position_id, pos.current_price, pos.symbol)}
                            className="border-zinc-700 text-xs text-zinc-300 hover:bg-zinc-800"
                          >
                            Full Exit
                          </Button>
                        </div>
                      </div>

                      {/* Tax Breakdown Sub-card */}
                      {isTaxOpen && (
                        <div className="p-3 rounded-lg bg-zinc-900/90 border border-zinc-800 text-xs space-y-1 text-zinc-300">
                          <div className="font-bold text-white mb-1 flex items-center justify-between">
                            <span>True Net In-Pocket Estimate:</span>
                            <span className="text-emerald-400 font-extrabold">₹{(pos.estimated_net_pnl || 0).toLocaleString()}</span>
                          </div>
                          <div className="grid grid-cols-3 gap-2 text-[11px] text-zinc-400 pt-1 border-t border-zinc-800">
                            <div>Gross Gain: ₹{pos.pnl_amount.toLocaleString()}</div>
                            <div>STT &amp; Brokerage: -₹{(pos.estimated_charges || 0).toLocaleString()}</div>
                            <div>20% STCG Tax: -₹{(pos.estimated_stcg_tax || 0).toLocaleString()}</div>
                          </div>
                        </div>
                      )}

                      {/* 2-Tranche Visualizer Progress Bar */}
                      <div className="space-y-1.5">
                        <div className="flex items-center justify-between text-xs text-zinc-400">
                          <span className="text-rose-400">Stop Loss: ₹{pos.stop_loss_price.toLocaleString()}</span>
                          <span className="font-semibold text-zinc-300">
                            Target 1 (50%): ₹{(pos.target1_price || pos.target_price).toLocaleString()} ({pos.target_progress_pct}%)
                          </span>
                          <span className="text-indigo-400 font-semibold">
                            Runner Target 2: ₹{(pos.target2_price || pos.target_price * 1.08).toLocaleString()}
                          </span>
                        </div>
                        <div className="w-full h-2.5 rounded-full bg-zinc-800 overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-blue-500 via-emerald-500 to-indigo-500 rounded-full transition-all duration-500"
                            style={{ width: `${Math.max(5, pos.target_progress_pct)}%` }}
                          />
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </div>

          {/* Daily Digests Section */}
          <Card className="bg-zinc-950/80 border-zinc-800">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg text-white flex items-center gap-2">
                  <Clock className="w-4 h-4 text-blue-400" />
                  Daily AI Market Evaluations &amp; Digests
                </CardTitle>
                <div className="flex items-center gap-1 bg-zinc-900 p-1 rounded-lg border border-zinc-800">
                  <button
                    type="button"
                    onClick={() => setActiveDigestTab('morning')}
                    className={`px-3 py-1 rounded text-xs font-semibold transition-all flex items-center gap-1.5 ${
                      activeDigestTab === 'morning'
                        ? 'bg-blue-600 text-white shadow'
                        : 'text-zinc-400 hover:text-zinc-200'
                    }`}
                  >
                    <Sun className="w-3.5 h-3.5" />
                    Morning Mood (8:45 AM)
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveDigestTab('evening')}
                    className={`px-3 py-1 rounded text-xs font-semibold transition-all flex items-center gap-1.5 ${
                      activeDigestTab === 'evening'
                        ? 'bg-blue-600 text-white shadow'
                        : 'text-zinc-400 hover:text-zinc-200'
                    }`}
                  >
                    <Moon className="w-3.5 h-3.5" />
                    Evening Wrap (4:00 PM)
                  </button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {activeDigestTab === 'morning' && morningDigest && (
                <div className="p-4 rounded-xl bg-zinc-900/50 border border-zinc-800 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-sm text-amber-300 flex items-center gap-1.5">
                      <Sun className="w-4 h-4" /> {morningDigest.greeting}
                    </span>
                    <span className="text-xs text-zinc-500">{morningDigest.date_str}</span>
                  </div>
                  <p className="text-xs sm:text-sm text-zinc-300 leading-relaxed">{morningDigest.market_mood}</p>
                  <div className="p-3 rounded-lg bg-blue-950/20 border border-blue-900/30 text-xs text-blue-300 font-medium">
                    {morningDigest.portfolio_summary_text}
                  </div>
                </div>
              )}

              {activeDigestTab === 'evening' && eveningDigest && (
                <div className="p-4 rounded-xl bg-zinc-900/50 border border-zinc-800 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-sm text-indigo-300 flex items-center gap-1.5">
                      <Moon className="w-4 h-4" /> {eveningDigest.greeting}
                    </span>
                    <span className="text-xs text-zinc-500">{eveningDigest.date_str}</span>
                  </div>
                  <p className="text-xs sm:text-sm text-zinc-300 leading-relaxed">{eveningDigest.market_mood}</p>
                  <div className="p-3 rounded-lg bg-indigo-950/20 border border-indigo-900/30 text-xs text-indigo-300 font-medium">
                    {eveningDigest.portfolio_summary_text}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Capital Reinvestment Modal */}
      {reinvestmentModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <Card className="bg-zinc-950 border-emerald-500/40 max-w-lg w-full shadow-2xl">
            <CardHeader>
              <CardTitle className="text-xl text-emerald-400 flex items-center gap-2">
                <Sparkles className="w-5 h-5" />
                Capital Freed! Ready to Reinvest?
              </CardTitle>
              <CardDescription className="text-zinc-300">
                You successfully exited <b>{reinvestmentModal.exited_symbol}</b> with{' '}
                <span className="text-emerald-400 font-bold">
                  {reinvestmentModal.realized_pnl >= 0 ? '+' : ''}₹{reinvestmentModal.realized_pnl.toLocaleString()}
                </span>{' '}
                profit (Net in-pocket: ₹{(reinvestmentModal.estimated_net_pnl || reinvestmentModal.realized_pnl * 0.8).toLocaleString()}). ₹{reinvestmentModal.freed_capital.toLocaleString()} is now ready to compound!
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="text-xs font-semibold text-zinc-300">Top Fresh Opportunities for Freed Capital:</div>
              <div className="space-y-2">
                {reinvestmentModal.new_opportunities.map((opp) => (
                  <div key={opp.symbol} className="p-3 rounded-lg bg-zinc-900 border border-zinc-800 text-xs">
                    <div className="flex items-center justify-between font-bold text-white mb-1">
                      <span>
                        {opp.symbol} ({opp.shares} shares @ ₹{opp.suggested_entry_price.toLocaleString()})
                      </span>
                      <span className="text-emerald-400">Target: +{opp.expected_gain_pct}%</span>
                    </div>
                    <p className="text-[11px] text-zinc-400">{opp.layman_rationale}</p>
                  </div>
                ))}
              </div>
              <div className="flex items-center justify-end gap-3 pt-4 border-t border-zinc-800">
                <Button
                  variant="outline"
                  onClick={() => setReinvestmentModal(null)}
                  className="border-zinc-700 text-xs text-zinc-300"
                >
                  Hold as Cash for Now
                </Button>
                <Button
                  onClick={() => {
                    setCapitalInput(reinvestmentModal.freed_capital.toString());
                    setReinvestmentModal(null);
                    setCurrentStep(1);
                  }}
                  className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs"
                >
                  Deploy into New Basket →
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
};
