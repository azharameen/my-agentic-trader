import React, { useState, useEffect, useCallback } from 'react';
import { Info } from 'lucide-react';
import { Sidebar, TabType } from './components/Layout/Sidebar';
import { SidebarProvider, SidebarInset } from './components/ui/sidebar';
import { Header } from './components/Layout/Header';
import { MetricRibbon } from './components/Layout/MetricRibbon';
import { CandlestickChart } from './components/Charts/CandlestickChart';
import { UniverseExplorer } from './components/Universe/UniverseExplorer';
import { Scorecard } from './components/Performance/Scorecard';
import { TradeAuditTable } from './components/Performance/TradeAuditTable';
import { BacktestStudio } from './components/Backtest/BacktestStudio';
import { SystemHealthView } from './components/Health/SystemHealth';
import { CommandCenter } from './components/CommandCenter/CommandCenter';
import { Schedules } from './components/Schedules/Schedules';
import { ChatSidebar } from './components/Layout/ChatSidebar';
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
  fetchCommandCenterOverview,
} from './lib/api';
import {
  OverviewData,
  CommandCenterOverview,
  OpenPosition,
  TradeProposal,
  HistoricalTrade,
  PerformanceScorecard,
} from './types/api';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('command');
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [commandOverview, setCommandOverview] = useState<CommandCenterOverview | null>(null);
  const [positions, setPositions] = useState<OpenPosition[]>([]);
  const [proposals, setProposals] = useState<TradeProposal[]>([]);
  const [trades, setTrades] = useState<HistoricalTrade[]>([]);
  const [performance, setPerformance] = useState<PerformanceScorecard | null>(null);

  const [isScanModalOpen, setIsScanModalOpen] = useState(false);
  const [selectedChartSymbol, setSelectedChartSymbol] = useState('RELIANCE');
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [isCopilotOpen, setIsCopilotOpen] = useState(true);
  const [chatPrompt, setChatPrompt] = useState<string | undefined>();

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
      const commandData = await fetchCommandCenterOverview();
      setOverview(oData);
      setPositions(pData);
      setProposals(propData);
      setTrades(tData);
      setPerformance(perfData);
      setCommandOverview(commandData);
    } catch (err) {
      console.error('Failed to load dashboard data', err);
    } finally {
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadAllData();
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

    eventSource.addEventListener('COMMAND_CENTER_TICK', () => {
      loadAllData();
    });

    eventSource.addEventListener('STOCK_ADDED', () => loadAllData());
    eventSource.addEventListener('STOCK_UPDATED', () => loadAllData());
    eventSource.addEventListener('STOCK_REMOVED', () => loadAllData());
    eventSource.addEventListener('FNO_ADDED', () => loadAllData());
    eventSource.addEventListener('FNO_UPDATED', () => loadAllData());
    eventSource.addEventListener('FNO_REMOVED', () => loadAllData());
    eventSource.addEventListener('MF_ADDED', () => loadAllData());
    eventSource.addEventListener('MF_UPDATED', () => loadAllData());
    eventSource.addEventListener('MF_REMOVED', () => loadAllData());

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

  const handleOpenInvestmentChat = () => {
    setChatPrompt("I want to build a new investment plan. Please ask me whatever you need to know before generating anything. Do not assume my capital, risk appetite, or goal.");
    setIsCopilotOpen(true);
  };

  const handleToggleChat = () => {
    setChatPrompt(undefined);
    setIsCopilotOpen((prev) => !prev);
  };

  return (
    <SidebarProvider defaultOpen={false} className="h-screen overflow-hidden bg-background text-foreground">
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
        setActiveTab={(tab) => tab === 'copilot' ? setIsCopilotOpen(true) : setActiveTab(tab)}
        pendingCount={proposals.length}
      />

      {/* Main Content Area */}
      <SidebarInset className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <Header
          overview={overview}
          commandOverview={commandOverview}
          onRefresh={loadAllData}
          onOpenScanModal={handleRunScan}
          onRunSymbol={handleRunSymbol}
          onRefreshUniverse={handleRefreshUniverse}
          onToggleChat={handleToggleChat}
          isRefreshing={isRefreshing}
        />

        <main className="flex-1 overflow-y-auto p-6">
          {/* Tab: Command Center (unified command surface — everything owned, in one screen) */}
          {activeTab === 'command' && (
            <CommandCenter
              onShowToast={showToast}
              onOpenInvestmentChat={handleOpenInvestmentChat}
              proposals={proposals}
              positions={positions}
              onApprove={handleApprove}
              onReject={handleReject}
              onClosePosition={handleClosePosition}
              onSelectSymbolForChart={handleSelectSymbolForChart}
            />
          )}

          {/* Top Portfolio Ribbon on relevant views */}
          {activeTab === 'performance' && (
            <MetricRibbon overview={overview} />
          )}

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
          {activeTab === 'schedules' && <Schedules onShowToast={showToast} />}

          {/* Tab 8: System Health & Regime */}
          {activeTab === 'health' && <SystemHealthView />}
        </main>
      </SidebarInset>

      {/* Global toggleable right-side AI Copilot chat sidebar */}
      <ChatSidebar
        open={isCopilotOpen}
        onOpenChange={setIsCopilotOpen}
        onShowToast={showToast}
        onPortfolioChanged={loadAllData}
        initialPrompt={chatPrompt}
      />

    </SidebarProvider>
  );
};

export default App;
