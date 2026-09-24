import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { PlusCircle, Trash2, Zap, Clock, Sparkles } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../ui/tooltip';
import { HoverCard, HoverCardContent, HoverCardTrigger } from '../ui/hover-card';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetFooter } from '../ui/sheet';
import { PendingProposals } from './PendingProposals';
import { OpenPositions } from './OpenPositions';
import { AgentDebateModal } from './AgentDebateModal';
import {
  fetchCommandCenterOverview,
  addManualStock,
  deleteManualStock,
  addFnoPosition,
  deleteFnoPosition,
  addMutualFund,
  deleteMutualFund,
  fetchDeepDive,
  triggerRunSymbol,
} from '../../lib/api';
import { CommandCenterOverview, CommandCenterSuggestion, DeepDiveResponse, OpenPosition, StockSignal, TradeProposal } from '../../types/api';

const signalStyles: Record<StockSignal['action'], string> = {
  BUY_MORE: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
  HOLD: 'bg-slate-500/10 text-slate-400 border-slate-500/30',
  TRIM: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
  SELL: 'bg-red-500/10 text-red-400 border-red-500/30',
};

const SignalBadge: React.FC<{ signal: StockSignal }> = ({ signal }) => (
  <HoverCard openDelay={150}>
    <HoverCardTrigger asChild>
      <Badge variant="outline" className={`cursor-help font-mono text-[10px] ${signalStyles[signal.action]}`}>
        {signal.action.replace('_', ' ')}
      </Badge>
    </HoverCardTrigger>
    <HoverCardContent>
      <p className="text-xs font-semibold text-foreground mb-1">{signal.label}</p>
      <p className="text-xs text-muted-foreground mb-2">{signal.rationale}</p>
      {signal.analytics && (
        <div className="text-[11px] font-mono text-muted-foreground space-y-0.5 border-t border-border pt-2">
          {signal.analytics.strategy_name && <div>Strategy: <span className="text-foreground">{signal.analytics.strategy_name}</span></div>}
          {signal.analytics.secondary_strategies.length > 0 && (
            <div>Also matches: {signal.analytics.secondary_strategies.join(', ')}</div>
          )}
          {signal.analytics.rsi !== null && signal.analytics.rsi !== undefined && <div>RSI(14): {signal.analytics.rsi}</div>}
          {signal.analytics.sector_name && (
            <div>
              Sector: {signal.analytics.sector_name}
              {signal.analytics.sector_rs_20d !== null && signal.analytics.sector_rs_20d !== undefined && ` (RS ${signal.analytics.sector_rs_20d.toFixed(2)})`}
            </div>
          )}
        </div>
      )}
    </HoverCardContent>
  </HoverCard>
);

const PnlText: React.FC<{ value: number; pct?: number }> = ({ value, pct }) => {
  const positive = value >= 0;
  return (
    <span className={`font-mono text-sm ${positive ? 'text-emerald-500' : 'text-red-500'}`}>
      {positive ? '+' : ''}₹{value.toFixed(2)} {pct !== undefined && `(${positive ? '+' : ''}${pct.toFixed(2)}%)`}
    </span>
  );
};

interface CommandCenterProps {
  onShowToast: (msg: string) => void;
  onOpenInvestmentChat: () => void;
  proposals: TradeProposal[];
  positions: OpenPosition[];
  onApprove: (proposalId: string) => void;
  onReject: (proposalId: string) => void;
  onClosePosition: (tradeId: string) => void;
  onSelectSymbolForChart: (symbol: string) => void;
}

export const CommandCenter: React.FC<CommandCenterProps> = ({
  onShowToast,
  onOpenInvestmentChat,
  proposals,
  positions,
  onApprove,
  onReject,
  onClosePosition,
  onSelectSymbolForChart,
}) => {
  const [data, setData] = useState<CommandCenterOverview | null>(null);
  const [lastSyncedAt, setLastSyncedAt] = useState<Date | null>(null);
  const [addStockOpen, setAddStockOpen] = useState(false);
  const [addFnoOpen, setAddFnoOpen] = useState(false);
  const [addMfOpen, setAddMfOpen] = useState(false);
  const [buySheetSuggestion, setBuySheetSuggestion] = useState<CommandCenterSuggestion | null>(null);
  const [deepDiveSymbol, setDeepDiveSymbol] = useState<string | null>(null);
  const [selectedProposalForDebate, setSelectedProposalForDebate] = useState<TradeProposal | null>(null);

  const load = useCallback(async () => {
    try {
      const overview = await fetchCommandCenterOverview();
      setData(overview);
      setLastSyncedAt(new Date());
    } catch (err) {
      console.error('Failed to load Command Center overview', err);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Live push updates: broad SCAN/tick events already flow through /api/events (see App.tsx);
  // Command Center listens for its own tick + CRUD confirmations to refresh immediately.
  useEffect(() => {
    const es = new EventSource('/api/events');
    const refresh = () => load();
    const events = [
      'COMMAND_CENTER_TICK', 'STOCK_ADDED', 'STOCK_UPDATED', 'STOCK_REMOVED',
      'FNO_ADDED', 'FNO_UPDATED', 'FNO_REMOVED', 'MF_ADDED', 'MF_UPDATED', 'MF_REMOVED',
      'PROPOSAL_CREATED',
    ];
    events.forEach((evt) => es.addEventListener(evt, refresh));
    return () => es.close();
  }, [load]);

  const secondsSinceSync = useMemo(() => {
    if (!lastSyncedAt) return null;
    return Math.max(0, Math.round((Date.now() - lastSyncedAt.getTime()) / 1000));
  }, [lastSyncedAt, data]);

  if (!data) {
    return <div className="text-sm text-muted-foreground p-6">Loading Command Center...</div>;
  }

  const { totals, stocks, fno, mutual_funds: mutualFunds, suggested, groww_connected: growwConnected } = data;

  return (
    <TooltipProvider>
      <div className="space-y-6">
        {/* Totals ribbon */}
        <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
          <MetricCard label="Capital Invested" value={`₹${totals.capital_invested.toLocaleString('en-IN')}`} tooltip="Sum of your original purchase cost across stocks, F&O, and mutual funds." />
          <MetricCard label="Current Value" value={`₹${totals.current_value.toLocaleString('en-IN')}`} tooltip="Live mark-to-market value of everything you hold right now." />
          <MetricCard label="Total Earned" value={`${totals.total_earnings >= 0 ? '+' : ''}₹${totals.total_earnings.toLocaleString('en-IN')}`} valueClassName={totals.total_earnings >= 0 ? 'text-emerald-500' : 'text-red-500'} tooltip="Realized earnings from closed trades plus unrealized earnings on current holdings." />
          <MetricCard
            label="Unrealized P&L"
            value={`${totals.unrealized_earnings >= 0 ? '+' : ''}₹${totals.unrealized_earnings.toLocaleString('en-IN')}`}
            valueClassName={totals.unrealized_earnings >= 0 ? 'text-emerald-500' : 'text-red-500'}
            tooltip={`${totals.total_pnl_pct.toFixed(2)}% return on the current invested cost basis.`}
          />
          <MetricCard label="Cash Available" value={`₹${totals.cash_available.toLocaleString('en-IN')}`} tooltip="Available cash/margin balance reported by Groww, if connected." />
          <Card>
            <CardContent className="p-4 flex flex-col gap-1">
              <span className="text-xs text-muted-foreground flex items-center gap-1">
                <Clock className="w-3 h-3" /> Last synced
              </span>
              <span className="text-sm font-mono">{secondsSinceSync !== null ? `${secondsSinceSync}s ago` : '—'}</span>
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="text-[10px] text-muted-foreground underline decoration-dotted cursor-help">
                    {growwConnected ? 'Groww connected, SSE invalidates updates' : 'Groww not connected'}
                  </span>
                </TooltipTrigger>
                <TooltipContent>
                  <p className="max-w-xs text-xs">
                    Groww holdings are synced into the database and the screen refreshes from SSE events or explicit actions.
                  </p>
                </TooltipContent>
              </Tooltip>
            </CardContent>
          </Card>
        </div>

        {/* Market regime */}
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <HoverCard openDelay={100}>
            <HoverCardTrigger asChild>
              <Badge
                variant="outline"
                className={`cursor-help text-[11px] ${
                  data.market_regime.allow_new_entries
                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                    : 'bg-red-500/10 text-red-400 border-red-500/30'
                }`}
              >
                Market regime: {data.market_regime.allow_new_entries ? 'RISK-ON' : 'RISK-OFF'}
                {data.market_regime.vix !== null && data.market_regime.vix !== undefined && ` · VIX ${data.market_regime.vix.toFixed(1)}`}
              </Badge>
            </HoverCardTrigger>
            <HoverCardContent>
              <p className="text-xs font-semibold mb-1">Risk multiplier: {data.market_regime.risk_multiplier}x</p>
              {data.market_regime.reasons.length > 0 ? (
                <ul className="text-xs text-muted-foreground list-disc pl-4 space-y-0.5">
                  {data.market_regime.reasons.map((r, i) => <li key={i}>{r}</li>)}
                </ul>
              ) : (
                <p className="text-xs text-muted-foreground">No regime warnings active.</p>
              )}
            </HoverCardContent>
          </HoverCard>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" onClick={onOpenInvestmentChat}>
              <Sparkles className="w-4 h-4 mr-1.5 text-blue-400" /> Smart Investment Plan
            </Button>
          </div>
        </div>

        <section className="space-y-8 border-t border-border pt-6" aria-label="Action queue and paper execution">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-primary">Execution control</p>
            <h2 className="mt-1 text-lg font-bold text-foreground">Action Queue &amp; Paper Execution</h2>
            <p className="mt-1 text-xs text-muted-foreground">
              Review research-qualified proposals and monitor paper trades alongside your real portfolio.
            </p>
          </div>
          <PendingProposals
            proposals={proposals}
            onApprove={onApprove}
            onReject={onReject}
            onViewDebate={setSelectedProposalForDebate}
          />
          <OpenPositions
            positions={positions}
            onClosePosition={onClosePosition}
            onSelectSymbolForChart={onSelectSymbolForChart}
          />
        </section>

        {/* Suggested new opportunities */}
        {suggested.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold mb-2 flex items-center gap-1.5">
              <Zap className="w-4 h-4 text-amber-400 animate-pulse" /> Suggested for you
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {suggested.map((s) => (
                <Card key={s.proposal_id} className="border-amber-500/30 relative overflow-hidden">
                  <div className="absolute top-0 right-0 w-2 h-2 rounded-full bg-amber-400 animate-ping m-3" />
                  <CardContent className="p-4 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-bold">{s.symbol}</span>
                      <Badge variant="outline" className="text-[10px] bg-emerald-500/10 text-emerald-400 border-emerald-500/30">
                        AGENT SUGGESTS BUY
                      </Badge>
                    </div>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <p className="text-xs text-muted-foreground line-clamp-2 cursor-help">{s.thesis}</p>
                      </TooltipTrigger>
                      <TooltipContent><p className="max-w-xs text-xs">{s.thesis}</p></TooltipContent>
                    </Tooltip>
                    <div className="flex justify-between text-xs font-mono">
                      <span>Entry ₹{s.entry_price.toFixed(2)}</span>
                      <span>Target ₹{s.target_price.toFixed(2)}</span>
                      <span>Stop ₹{s.hard_stop.toFixed(2)}</span>
                    </div>
                    <Button size="sm" className="w-full" onClick={() => setBuySheetSuggestion(s)}>
                      Mark as bought
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )}

        {/* Holdings tabs */}
        <Tabs defaultValue="stocks">
          <TabsList>
            <TabsTrigger value="stocks">Stocks ({stocks.length})</TabsTrigger>
            <TabsTrigger value="fno">F&amp;O ({fno.length})</TabsTrigger>
            <TabsTrigger value="mf">Mutual Funds ({mutualFunds.length})</TabsTrigger>
          </TabsList>

          <TabsContent value="stocks" className="space-y-3">
            <div className="flex justify-end">
              <Button size="sm" variant="outline" onClick={() => setAddStockOpen(true)}>
                <PlusCircle className="w-4 h-4 mr-1.5" /> Add stock
              </Button>
            </div>
            <Card>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Symbol</TableHead>
                      <TableHead>Qty</TableHead>
                       <TableHead>Invested</TableHead>
                       <TableHead>Current</TableHead>
                       <TableHead>Value</TableHead>
                       <TableHead>P&amp;L</TableHead>
                       <TableHead>Signal</TableHead>
                       <TableHead>Origin / status</TableHead>
                      <TableHead />
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {stocks.length === 0 && (
                      <TableRow><TableCell colSpan={9} className="text-center text-muted-foreground text-sm py-8">
                        No stocks in the database yet. Groww is synced automatically when configured; planned positions appear here before purchase.
                      </TableCell></TableRow>
                    )}
                    {stocks.map((s) => (
                      <TableRow key={s.position_id}>
                        <TableCell className="font-semibold">
                          <button
                            className="hover:underline decoration-dotted text-left"
                            onClick={() => setDeepDiveSymbol(s.symbol)}
                          >
                            {s.symbol}
                          </button>
                        </TableCell>
                        <TableCell className="font-mono">{s.shares}</TableCell>
                        <TableCell className="font-mono">₹{s.invested_amount.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</TableCell>
                        <TableCell className="font-mono">₹{s.current_price.toFixed(2)}</TableCell>
                        <TableCell className="font-mono">₹{s.current_value.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</TableCell>
                        <TableCell><PnlText value={s.pnl} pct={s.pnl_pct} /></TableCell>
                        <TableCell><SignalBadge signal={s.signal} /></TableCell>
                        <TableCell>
                          <Badge variant="secondary" className="text-[10px]">
                            {s.investment_source === 'PLANNED_THEN_GROWW' ? 'Plan → Groww' : s.investment_source === 'GROWW_DIRECT' ? 'Groww direct' : s.investment_source === 'MANUAL_THEN_GROWW' ? 'Manual → Groww' : s.source === 'BASKET' ? 'Smart Plan' : 'Manual'}
                          </Badge>
                          <span className="block text-[10px] text-muted-foreground">{s.plan_status !== 'NONE' ? s.plan_status : s.status}</span>
                        </TableCell>
                        <TableCell>
                          {s.editable && (
                            <Button size="sm" variant="ghost" onClick={async () => {
                              await deleteManualStock(s.position_id);
                              onShowToast(`Removed ${s.symbol}`);
                              load();
                            }}>
                              <Trash2 className="w-3.5 h-3.5 text-red-400" />
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="fno" className="space-y-3">
            <div className="flex justify-end">
              <Button size="sm" variant="outline" onClick={() => setAddFnoOpen(true)}>
                <PlusCircle className="w-4 h-4 mr-1.5" /> Add F&amp;O position
              </Button>
            </div>
            <Card>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Symbol</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Qty (lots)</TableHead>
                      <TableHead>Entry</TableHead>
                      <TableHead>Current</TableHead>
                      <TableHead>P&amp;L</TableHead>
                      <TableHead />
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {fno.length === 0 && (
                      <TableRow><TableCell colSpan={7} className="text-center text-muted-foreground text-sm py-8">
                        No F&amp;O positions. This tab is manual-entry only — Groww's free API and this
                        platform have no live F&amp;O data source today.
                      </TableCell></TableRow>
                    )}
                    {fno.map((p) => (
                      <TableRow key={p.position_id}>
                        <TableCell className="font-semibold">{p.symbol}</TableCell>
                        <TableCell><Badge variant="outline" className="text-[10px]">{p.instrument_type}</Badge></TableCell>
                        <TableCell className="font-mono">{p.quantity} x {p.lot_size}</TableCell>
                        <TableCell className="font-mono">₹{p.entry_price.toFixed(2)}</TableCell>
                        <TableCell className="font-mono">₹{p.current_price.toFixed(2)}</TableCell>
                        <TableCell><PnlText value={p.pnl} /></TableCell>
                        <TableCell>
                          <Button size="sm" variant="ghost" onClick={async () => {
                            await deleteFnoPosition(p.position_id);
                            onShowToast(`Removed ${p.symbol} ${p.instrument_type}`);
                            load();
                          }}>
                            <Trash2 className="w-3.5 h-3.5 text-red-400" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="mf" className="space-y-3">
            <div className="flex justify-end">
              <Button size="sm" variant="outline" onClick={() => setAddMfOpen(true)}>
                <PlusCircle className="w-4 h-4 mr-1.5" /> Add mutual fund
              </Button>
            </div>
            <Card>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Scheme</TableHead>
                      <TableHead>Units</TableHead>
                      <TableHead>NAV</TableHead>
                      <TableHead>Current Value</TableHead>
                      <TableHead>P&amp;L</TableHead>
                      <TableHead />
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {mutualFunds.length === 0 && (
                      <TableRow><TableCell colSpan={6} className="text-center text-muted-foreground text-sm py-8">
                        No mutual funds tracked. Groww's API has no live MF endpoint — add folios manually.
                      </TableCell></TableRow>
                    )}
                    {mutualFunds.map((m) => (
                      <TableRow key={m.folio_id}>
                        <TableCell className="font-semibold">{m.scheme_name}</TableCell>
                        <TableCell className="font-mono">{m.units}</TableCell>
                        <TableCell className="font-mono">₹{m.nav.toFixed(2)}</TableCell>
                        <TableCell className="font-mono">₹{m.current_value.toFixed(2)}</TableCell>
                        <TableCell><PnlText value={m.pnl} pct={m.pnl_pct} /></TableCell>
                        <TableCell>
                          <Button size="sm" variant="ghost" onClick={async () => {
                            await deleteMutualFund(m.folio_id);
                            onShowToast(`Removed ${m.scheme_name}`);
                            load();
                          }}>
                            <Trash2 className="w-3.5 h-3.5 text-red-400" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      <AddStockSheet open={addStockOpen} onOpenChange={setAddStockOpen} onAdded={() => { load(); onShowToast('Stock added'); }} />
      <AddFnoSheet open={addFnoOpen} onOpenChange={setAddFnoOpen} onAdded={() => { load(); onShowToast('F&O position added'); }} />
      <AddMfSheet open={addMfOpen} onOpenChange={setAddMfOpen} onAdded={() => { load(); onShowToast('Mutual fund added'); }} />
      <BuySheet suggestion={buySheetSuggestion} onClose={() => setBuySheetSuggestion(null)} onAdded={() => { load(); onShowToast('Position recorded'); }} />
      <DeepDiveSheet symbol={deepDiveSymbol} onClose={() => setDeepDiveSymbol(null)} onShowToast={onShowToast} />
      <AgentDebateModal
        proposal={selectedProposalForDebate}
        onClose={() => setSelectedProposalForDebate(null)}
        onApprove={onApprove}
        onReject={onReject}
      />
    </TooltipProvider>
  );
};

const MetricCard: React.FC<{ label: string; value: string; tooltip: string; valueClassName?: string }> = ({ label, value, tooltip, valueClassName }) => (
  <Card>
    <CardContent className="p-4 flex flex-col gap-1">
      <Tooltip>
        <TooltipTrigger asChild>
          <span className="text-xs text-muted-foreground underline decoration-dotted cursor-help w-fit">{label}</span>
        </TooltipTrigger>
        <TooltipContent><p className="max-w-xs text-xs">{tooltip}</p></TooltipContent>
      </Tooltip>
      <span className={`text-lg font-bold font-mono ${valueClassName ?? ''}`}>{value}</span>
    </CardContent>
  </Card>
);

const AddStockSheet: React.FC<{ open: boolean; onOpenChange: (v: boolean) => void; onAdded: () => void }> = ({ open, onOpenChange, onAdded }) => {
  const [symbol, setSymbol] = useState('');
  const [shares, setShares] = useState('');
  const [entryPrice, setEntryPrice] = useState('');
  const [stop, setStop] = useState('');
  const [target, setTarget] = useState('');

  const submit = async () => {
    if (!symbol || !shares || !entryPrice) return;
    await addManualStock({
      symbol, shares: Number(shares), entry_price: Number(entryPrice),
      stop_loss_price: stop ? Number(stop) : undefined,
      target_price: target ? Number(target) : undefined,
    });
    setSymbol(''); setShares(''); setEntryPrice(''); setStop(''); setTarget('');
    onOpenChange(false);
    onAdded();
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent>
        <SheetHeader><SheetTitle>Add a stock you bought</SheetTitle></SheetHeader>
        <div className="space-y-3">
          <Field label="Symbol (NSE)"><Input value={symbol} onChange={(e) => setSymbol(e.target.value.toUpperCase())} placeholder="RELIANCE" /></Field>
          <Field label="Quantity"><Input type="number" value={shares} onChange={(e) => setShares(e.target.value)} /></Field>
          <Field label="Average buy price (₹)"><Input type="number" value={entryPrice} onChange={(e) => setEntryPrice(e.target.value)} /></Field>
          <Field label="Stop-loss (₹, optional)"><Input type="number" value={stop} onChange={(e) => setStop(e.target.value)} /></Field>
          <Field label="Target (₹, optional)"><Input type="number" value={target} onChange={(e) => setTarget(e.target.value)} /></Field>
        </div>
        <SheetFooter><Button onClick={submit}>Save</Button></SheetFooter>
      </SheetContent>
    </Sheet>
  );
};

const AddFnoSheet: React.FC<{ open: boolean; onOpenChange: (v: boolean) => void; onAdded: () => void }> = ({ open, onOpenChange, onAdded }) => {
  const [symbol, setSymbol] = useState('');
  const [instrumentType, setInstrumentType] = useState('FUT');
  const [quantity, setQuantity] = useState('');
  const [lotSize, setLotSize] = useState('1');
  const [entryPrice, setEntryPrice] = useState('');
  const [strike, setStrike] = useState('');
  const [expiry, setExpiry] = useState('');

  const submit = async () => {
    if (!symbol || !quantity || !entryPrice) return;
    await addFnoPosition({
      symbol, instrument_type: instrumentType, quantity: Number(quantity), lot_size: Number(lotSize) || 1,
      entry_price: Number(entryPrice), strike_price: strike ? Number(strike) : undefined, expiry_date: expiry || undefined,
    });
    setSymbol(''); setQuantity(''); setEntryPrice(''); setStrike(''); setExpiry('');
    onOpenChange(false);
    onAdded();
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent>
        <SheetHeader><SheetTitle>Add an F&amp;O position (manual)</SheetTitle></SheetHeader>
        <div className="space-y-3">
          <Field label="Underlying symbol"><Input value={symbol} onChange={(e) => setSymbol(e.target.value.toUpperCase())} placeholder="NIFTY" /></Field>
          <Field label="Instrument type"><Input value={instrumentType} onChange={(e) => setInstrumentType(e.target.value.toUpperCase())} placeholder="FUT / CE / PE" /></Field>
          <Field label="Strike (optional)"><Input type="number" value={strike} onChange={(e) => setStrike(e.target.value)} /></Field>
          <Field label="Expiry (YYYY-MM-DD, optional)"><Input value={expiry} onChange={(e) => setExpiry(e.target.value)} /></Field>
          <Field label="Lot size"><Input type="number" value={lotSize} onChange={(e) => setLotSize(e.target.value)} /></Field>
          <Field label="Quantity (lots)"><Input type="number" value={quantity} onChange={(e) => setQuantity(e.target.value)} /></Field>
          <Field label="Entry price (₹)"><Input type="number" value={entryPrice} onChange={(e) => setEntryPrice(e.target.value)} /></Field>
        </div>
        <SheetFooter><Button onClick={submit}>Save</Button></SheetFooter>
      </SheetContent>
    </Sheet>
  );
};

const AddMfSheet: React.FC<{ open: boolean; onOpenChange: (v: boolean) => void; onAdded: () => void }> = ({ open, onOpenChange, onAdded }) => {
  const [scheme, setScheme] = useState('');
  const [units, setUnits] = useState('');
  const [nav, setNav] = useState('');
  const [invested, setInvested] = useState('');
  const [folio, setFolio] = useState('');

  const submit = async () => {
    if (!scheme || !units || !nav || !invested) return;
    await addMutualFund({ scheme_name: scheme, units: Number(units), nav: Number(nav), invested_amount: Number(invested), folio_number: folio });
    setScheme(''); setUnits(''); setNav(''); setInvested(''); setFolio('');
    onOpenChange(false);
    onAdded();
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent>
        <SheetHeader><SheetTitle>Add a mutual fund folio (manual)</SheetTitle></SheetHeader>
        <div className="space-y-3">
          <Field label="Scheme name"><Input value={scheme} onChange={(e) => setScheme(e.target.value)} placeholder="Parag Parikh Flexi Cap" /></Field>
          <Field label="Folio number (optional)"><Input value={folio} onChange={(e) => setFolio(e.target.value)} /></Field>
          <Field label="Units"><Input type="number" value={units} onChange={(e) => setUnits(e.target.value)} /></Field>
          <Field label="Current NAV (₹)"><Input type="number" value={nav} onChange={(e) => setNav(e.target.value)} /></Field>
          <Field label="Total invested amount (₹)"><Input type="number" value={invested} onChange={(e) => setInvested(e.target.value)} /></Field>
        </div>
        <SheetFooter><Button onClick={submit}>Save</Button></SheetFooter>
      </SheetContent>
    </Sheet>
  );
};

const BuySheet: React.FC<{ suggestion: CommandCenterSuggestion | null; onClose: () => void; onAdded: () => void }> = ({ suggestion, onClose, onAdded }) => {
  const [shares, setShares] = useState('');
  const [entryPrice, setEntryPrice] = useState('');

  useEffect(() => {
    if (suggestion) setEntryPrice(String(suggestion.entry_price));
  }, [suggestion]);

  if (!suggestion) return null;

  const submit = async () => {
    if (!shares || !entryPrice) return;
    await addManualStock({
      symbol: suggestion.symbol, shares: Number(shares), entry_price: Number(entryPrice),
      stop_loss_price: suggestion.hard_stop, target_price: suggestion.target_price,
    });
    setShares('');
    onClose();
    onAdded();
  };

  return (
    <Sheet open={!!suggestion} onOpenChange={(v) => !v && onClose()}>
      <SheetContent>
        <SheetHeader><SheetTitle>Mark {suggestion.symbol} as bought</SheetTitle></SheetHeader>
        <p className="text-xs text-muted-foreground mb-3">{suggestion.thesis}</p>
        <div className="space-y-3">
          <Field label="Quantity bought"><Input type="number" value={shares} onChange={(e) => setShares(e.target.value)} /></Field>
          <Field label="Actual fill price (₹)"><Input type="number" value={entryPrice} onChange={(e) => setEntryPrice(e.target.value)} /></Field>
        </div>
        <SheetFooter><Button onClick={submit}>Confirm purchase</Button></SheetFooter>
      </SheetContent>
    </Sheet>
  );
};

const Field: React.FC<{ label: string; children: React.ReactNode }> = ({ label, children }) => (
  <div className="space-y-1">
    <label className="text-xs text-muted-foreground">{label}</label>
    {children}
  </div>
);

const DeepDiveSheet: React.FC<{ symbol: string | null; onClose: () => void; onShowToast: (msg: string) => void }> = ({ symbol, onClose, onShowToast }) => {
  const [dive, setDive] = useState<DeepDiveResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [triggering, setTriggering] = useState(false);

  const load = useCallback(async () => {
    if (!symbol) return;
    setLoading(true);
    try {
      const result = await fetchDeepDive(symbol);
      setDive(result);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [symbol]);

  useEffect(() => {
    setDive(null);
    if (symbol) load();
  }, [symbol, load]);

  if (!symbol) return null;

  const handleRunAnalysis = async () => {
    setTriggering(true);
    try {
      await triggerRunSymbol(symbol);
      onShowToast(`Deep analysis for ${symbol} launched — this can take a minute`);
      setTimeout(load, 15000);
    } catch (err: any) {
      onShowToast(`Failed to launch analysis: ${err.message}`);
    } finally {
      setTriggering(false);
    }
  };

  const verdict = dive?.research_verdict as any;

  return (
    <Sheet open={!!symbol} onOpenChange={(v) => !v && onClose()}>
      <SheetContent>
        <SheetHeader><SheetTitle>{symbol} — Agent Deep Dive</SheetTitle></SheetHeader>
        {loading && <p className="text-sm text-muted-foreground">Loading...</p>}
        {!loading && dive && !dive.available && (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              No completed agent research found yet for {symbol}. This deterministic signal above is technical-only —
              run the full Bear/Bull/Synthesizer research pass for a qualitative thesis.
            </p>
            <Button onClick={handleRunAnalysis} disabled={triggering}>
              {triggering ? 'Launching...' : 'Run deep analysis'}
            </Button>
          </div>
        )}
        {!loading && dive && dive.available && (
          <div className="space-y-4 text-sm">
            {dive.strategy_name && (
              <div><span className="text-muted-foreground">Matched strategy: </span><Badge variant="outline">{dive.strategy_name}</Badge></div>
            )}
            {dive.market_regime && (
              <div><span className="text-muted-foreground">Regime at analysis time: </span>{dive.market_regime}</div>
            )}
            {verdict && (
              <div className="space-y-2 border-t border-border pt-3">
                {verdict.bear_thesis && <div><p className="text-xs font-semibold text-red-400">Bear Critic</p><p className="text-xs text-muted-foreground">{verdict.bear_thesis}</p></div>}
                {verdict.bull_thesis && <div><p className="text-xs font-semibold text-emerald-400">Bull Analyst</p><p className="text-xs text-muted-foreground">{verdict.bull_thesis}</p></div>}
                {verdict.synthesis && <div><p className="text-xs font-semibold text-foreground">Synthesizer Verdict</p><p className="text-xs text-muted-foreground">{verdict.synthesis}</p></div>}
              </div>
            )}
            <Button size="sm" variant="outline" onClick={handleRunAnalysis} disabled={triggering}>
              {triggering ? 'Launching...' : 'Re-run analysis'}
            </Button>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
};

export default CommandCenter;
