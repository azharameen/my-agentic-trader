import React, { useState, useEffect, useCallback } from 'react';
import { Info } from 'lucide-react';
import { Sidebar, TabType } from './components/Layout/Sidebar';
import { Header } from './components/Layout/Header';
import { MetricRibbon } from './components/Layout/MetricRibbon';
import { PendingProposals } from './components/Cockpit/PendingProposals';
import { OpenPositions } from './components/Cockpit/OpenPositions';
import { AgentDebateModal } from './components/Cockpit/AgentDebateModal';
import { SymbolAnalysisModal } from './components/Cockpit/SymbolAnalysisModal';
import { FloatingCopilot } from './components/Copilot/FloatingCopilot';
import { ChatContainer } from './components/Copilot/ChatContainer';
import { CandlestickChart } from './components/Charts/CandlestickChart';
import { UniverseExplorer } from './components/Universe/UniverseExplorer';
import { Scorecard } from './components/Performance/Scorecard';
import { TradeAuditTable } from './components/Performance/TradeAuditTable';
import { BacktestStudio } from './components/Backtest/BacktestStudio';
import { SystemHealthView } from './components/Health/SystemHealth';
import { BeginnerInvestWizard } from './components/Beginner/BeginnerInvestWizard';
import { DematPortfolioHub } from './components/Portfolio/DematPortfolioHub';
import {
  fetchOverview,
  fetchPositions,
  fetchPendingProposals,
  fetchTrades,
  fetchPerformance,
  approveProposal,
  rejectProposal,
  closePosition,
  triggerScan,
  triggerRunSymbol,
  refreshUniverse,
} from './lib/api';
import {
  OverviewData,
  OpenPosition,
  TradeProposal,
  HistoricalTrade,
  PerformanceScorecard,
} from './types/api';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('invest');
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [positions, setPositions] = useState<OpenPosition[]>([]);
  const [proposals, setProposals] = useState<TradeProposal[]>([]);
  const [trades, setTrades] = useState<HistoricalTrade[]>([]);
  const [performance, setPerformance] = useState<PerformanceScorecard | null>(null);

  const [selectedProposalForDebate, setSelectedProposalForDebate] = useState<TradeProposal | null>(null);
  const [isScanModalOpen, setIsScanModalOpen] = useState(false);
  const [isRunModalOpen, setIsRunModalOpen] = useState(false);
  const [selectedChartSymbol, setSelectedChartSymbol] = useState('RELIANCE');
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [isCopilotOpen, setIsCopilotOpen] = useState(false);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  const loadAllData = useCallback(async () => {
    setIsRefreshing(true);
    try {
      const [oData, pData, propData, tData, perfData] = await Promise.all([
        fetchOverview(),
        fetchPositions(),
        fetchPendingProposals(),
        fetchTrades(),
        fetchPerformance(),
      ]);
      setOverview(oData);
      setPositions(pData);
      setProposals(propData);
      setTrades(tData);
      setPerformance(perfData);
    } catch (err) {
      console.error('Failed to load dashboard data', err);
    } finally {
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadAllData();
    const interval = setInterval(loadAllData, 10000);
    return () => clearInterval(interval);
  }, [loadAllData]);

  // Connect to SSE event stream for live reactive updates
  useEffect(() => {
    const eventSource = new EventSource('/api/events');

    eventSource.addEventListener('PROPOSAL_CREATED', (e: any) => {
      try {
        const data = JSON.parse(e.data);
        showToast(`New Proposal: ${data.payload.symbol} (${data.payload.strategy})`);
        loadAllData();
      } catch (err) {
        console.error(err);
      }
    });

    eventSource.addEventListener('PROPOSAL_DECIDED', (e: any) => {
      try {
        const data = JSON.parse(e.data);
        showToast(`Decision recorded: ${data.payload.symbol} -> ${data.payload.decision}`);
        loadAllData();
      } catch (err) {
        console.error(err);
      }
    });

    eventSource.addEventListener('POSITION_CLOSED', (e: any) => {
      try {
        const data = JSON.parse(e.data);
        showToast(`Position closed: ${data.payload.symbol} (P&L ₹${data.payload.realized_pnl})`);
        loadAllData();
      } catch (err) {
        console.error(err);
      }
    });

    eventSource.addEventListener('SCAN_PROGRESS', (e: any) => {
      try {
        const data = JSON.parse(e.data);
        if (data.payload.current % 10 === 0 || data.payload.current === data.payload.total) {
          showToast(`Scanning universe: ${data.payload.current}/${data.payload.total}`);
        }
      } catch (err) {
        console.error(err);
      }
    });

    eventSource.addEventListener('SCAN_COMPLETED', (e: any) => {
      try {
        const data = JSON.parse(e.data);
        showToast(`Universe scan completed (${data.payload.proposed_count} proposals found)`);
        loadAllData();
      } catch (err) {
        console.error(err);
      }
    });

    return () => {
      eventSource.close();
    };
  }, [loadAllData]);

  const handleApprove = async (proposalId: string) => {
    try {
      await approveProposal(proposalId);
      showToast('Proposal Approved and Paper Order Executed');
      loadAllData();
    } catch (err: any) {
      showToast(`Approval failed: ${err.message}`);
    }
  };

  const handleReject = async (proposalId: string) => {
    try {
      await rejectProposal(proposalId);
      showToast('Proposal Rejected');
      loadAllData();
    } catch (err: any) {
      showToast(`Rejection failed: ${err.message}`);
    }
  };

  const handleClosePosition = async (tradeId: string) => {
    try {
      await closePosition(tradeId);
      showToast('Position exited at market price');
      loadAllData();
    } catch (err: any) {
      showToast(`Close position failed: ${err.message}`);
    }
  };

  const handleRunScan = async () => {
    try {
      await triggerScan();
      showToast('Universe Scan started in background');
    } catch (err: any) {
      showToast(`Scan trigger failed: ${err.message}`);
    }
  };

  const handleRunSymbol = async (symbol: string) => {
    try {
      await triggerRunSymbol(symbol);
      showToast(`Deep Analysis for ${symbol} launched in background`);
    } catch (err: any) {
      showToast(`Run symbol failed: ${err.message}`);
    }
  };

  const handleRefreshUniverse = async () => {
    try {
      const res = await refreshUniverse();
      showToast(`Refreshed ${res.count} universe constituents from NSE`);
    } catch (err: any) {
      showToast(`Universe refresh failed: ${err.message}`);
    }
  };

  const handleSelectSymbolForChart = (symbol: string) => {
    setSelectedChartSymbol(symbol);
    setActiveTab('charts');
  };

  return (
    <div className="flex h-screen bg-background overflow-hidden text-foreground">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-primary text-primary-foreground font-medium text-xs px-4 py-3 rounded-xl shadow-2xl border border-border flex items-center gap-2">
          <Info className="w-4 h-4 flex-shrink-0" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Sidebar */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={(tab) => {
          if (tab === 'copilot') {
            setIsCopilotOpen(true);
          } else {
            setActiveTab(tab);
          }
        }}
        pendingCount={proposals.length}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Header
          overview={overview}
          onRefresh={loadAllData}
          onOpenScanModal={handleRunScan}
          onOpenRunModal={() => setIsRunModalOpen(true)}
          onRefreshUniverse={handleRefreshUniverse}
          isRefreshing={isRefreshing}
        />

        <main className="flex-1 overflow-y-auto p-6">
          {/* Tab 0: Smart Investing (Beginner Wizard & Portfolio Health) */}
          {activeTab === 'invest' && (
            <BeginnerInvestWizard onShowToast={showToast} />
          )}

          {/* Tab 0.5: Demat & Groww Portfolio Hub */}
          {activeTab === 'demat' && (
            <DematPortfolioHub
              onShowToast={showToast}
              onSelectSymbolForChart={handleSelectSymbolForChart}
            />
          )}

          {/* Top Portfolio Ribbon on relevant views */}
          {(activeTab === 'cockpit' || activeTab === 'performance') && (
            <MetricRibbon overview={overview} />
          )}

          {/* Tab 1: Command Cockpit */}
          {activeTab === 'cockpit' && (
            <div className="space-y-8">
              <PendingProposals
                proposals={proposals}
                onApprove={handleApprove}
                onReject={handleReject}
                onViewDebate={(p) => setSelectedProposalForDebate(p)}
              />
              <OpenPositions
                positions={positions}
                onClosePosition={handleClosePosition}
                onSelectSymbolForChart={handleSelectSymbolForChart}
              />
            </div>
          )}

          {/* Tab 2: AI Copilot Standalone View */}
          {activeTab === 'copilot' && <ChatContainer />}

          {/* Tab 3: Candlestick Explorer */}
          {activeTab === 'charts' && (
            <CandlestickChart initialSymbol={selectedChartSymbol} />
          )}

          {/* Tab 4: NIFTY 100 Universe Explorer */}
          {activeTab === 'universe' && (
            <UniverseExplorer
              onSelectSymbolForChart={handleSelectSymbolForChart}
              onRunSymbol={handleRunSymbol}
              showToast={showToast}
            />
          )}

          {/* Tab 5: Performance & Audit Log */}
          {activeTab === 'performance' && (
            <div className="space-y-8">
              <Scorecard performance={performance} />
              <TradeAuditTable trades={trades} />
            </div>
          )}

          {/* Tab 6: Backtest Studio */}
          {activeTab === 'backtest' && <BacktestStudio />}

          {/* Tab 7: System Health & Regime */}
          {activeTab === 'health' && <SystemHealthView />}
        </main>
      </div>

      {/* Global Floating AI Copilot Popup (Available across all screens) */}
      <FloatingCopilot
        isOpen={isCopilotOpen}
        onToggle={() => setIsCopilotOpen((prev) => !prev)}
      />

      {/* Modals */}
      <AgentDebateModal
        proposal={selectedProposalForDebate}
        onClose={() => setSelectedProposalForDebate(null)}
        onApprove={handleApprove}
        onReject={handleReject}
      />

      <SymbolAnalysisModal
        isOpen={isRunModalOpen}
        onClose={() => setIsRunModalOpen(false)}
        onRunSymbol={handleRunSymbol}
      />
    </div>
  );
};

export default App;
