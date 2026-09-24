import React, { useState } from 'react';
import { RefreshCw, ScanSearch, Search, Database, Bot, Sparkles } from 'lucide-react';
import { CommandCenterOverview, OverviewData } from '../../types/api';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '../ui/tooltip';
import {
  Command,
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
  CommandShortcut,
} from '../ui/command';
import { SidebarTrigger } from '../ui/sidebar';

interface HeaderProps {
  overview: OverviewData | null;
  commandOverview: CommandCenterOverview | null;
  onRefresh: () => void;
  onOpenScanModal: () => void;
  onRunSymbol: (symbol: string) => void;
  onRefreshUniverse: () => void;
  onToggleChat: () => void;
  isRefreshing: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  overview,
  commandOverview,
  onRefresh,
  onOpenScanModal,
  onRunSymbol,
  onRefreshUniverse,
  onToggleChat,
  isRefreshing,
}) => {
  const [commandOpen, setCommandOpen] = useState(false);
  const [symbol, setSymbol] = useState('');
  const runSymbol = () => {
    const cleanSymbol = symbol.trim().toUpperCase().replace(/\.NS$/, '');
    if (!cleanSymbol) return;
    onRunSymbol(cleanSymbol);
    setSymbol('');
    setCommandOpen(false);
  };
  return (
    <TooltipProvider>
      <header className="h-16 border-b border-border bg-card/80 backdrop-blur px-6 flex items-center justify-between sticky top-0 z-30">
        <div className="flex items-center space-x-3">
          <SidebarTrigger className="-ml-2" />
          <div className="flex items-center gap-4">
            <div className="hidden items-center gap-3 border-l border-border pl-4 md:flex">
              <HeaderMetric label="Invested" value={commandOverview?.totals.capital_invested} />
              <HeaderMetric label="Total return" value={commandOverview?.totals.total_pnl} colored />
            </div>
          </div>
          {overview?.market_regime && (
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="cursor-help">
                  <Badge
                    variant="outline"
                    className={
                      overview.market_regime.allow_new_entries
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                        : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                    }
                  >
                    Regime: {overview.market_regime.allow_new_entries ? 'PERMISSIVE' : 'VETOED'} (VIX: {overview.market_regime.vix ?? 'N/A'})
                  </Badge>
                </div>
              </TooltipTrigger>
              <TooltipContent>
                <p className="max-w-xs">
                  {overview.market_regime.allow_new_entries
                    ? 'Market regime allows new trade entries. India VIX is below crisis thresholds.'
                    : 'Market regime is currently vetoing new trade entries due to elevated market volatility or macro stress.'}
                </p>
              </TooltipContent>
            </Tooltip>
          )}
        </div>

        <div className="flex items-center space-x-2">
          {/* Analyze Symbol Button */}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCommandOpen((open) => !open)}
                className="h-8 gap-1.5 text-xs font-medium"
              >
                <Search className="w-3.5 h-3.5 text-primary" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>Open the command palette to launch agent research for any NSE symbol</p>
            </TooltipContent>
          </Tooltip>

          <CommandDialog open={commandOpen} onOpenChange={setCommandOpen}>
            <Command shouldFilter={false}>
                <CommandInput
                  autoFocus
                  placeholder="Type an NSE symbol or agent command..."
                  value={symbol}
                  onValueChange={setSymbol}
                  onKeyDown={(event) => { if (event.key === 'Enter') runSymbol(); }}
                />
                <CommandList>
                  <CommandEmpty>No agent action found. Enter an NSE symbol to continue.</CommandEmpty>
                  <CommandGroup heading="Agent research">
                    <CommandItem value="research-symbol" disabled={!symbol.trim()} onSelect={runSymbol}>
                      <Sparkles className="mr-2 h-4 w-4 text-primary" />
                      <span>{symbol.trim() ? `Research ${symbol.trim().toUpperCase()}` : 'Research an NSE symbol'}</span>
                      <CommandShortcut>↵</CommandShortcut>
                    </CommandItem>
                  </CommandGroup>
                  <CommandSeparator />
                  <CommandGroup heading="How it works">
                    <CommandItem value="agent-research-help" onSelect={() => setSymbol('') }>
                      <Search className="mr-2 h-4 w-4 text-muted-foreground" />
                      <span>Agents run technical, risk, and qualitative research</span>
                    </CommandItem>
                  </CommandGroup>
                </CommandList>
            </Command>
          </CommandDialog>

          {/* Run Universe Scan Button */}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="default"
                size="sm"
                onClick={onOpenScanModal}
                className="h-8 gap-1.5 text-xs font-semibold"
              >
                <ScanSearch className="w-4 h-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>Screen all NIFTY 100 constituents for technical pullback setups and qualify with multi-agent consensus</p>
            </TooltipContent>
          </Tooltip>

          {/* Force Refresh Universe */}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="outline"
                size="icon"
                onClick={onRefreshUniverse}
                className="h-8 w-8 text-muted-foreground hover:text-foreground"
              >
                <Database className="w-4 h-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>Force refresh NIFTY 100 constituent list from official NSE endpoint</p>
            </TooltipContent>
          </Tooltip>

          {/* Live Data Refresh */}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="outline"
                size="icon"
                onClick={onRefresh}
                className={`h-8 w-8 text-muted-foreground hover:text-foreground ${
                  isRefreshing ? 'animate-spin text-primary' : ''
                }`}
              >
                <RefreshCw className="w-4 h-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>Fetch fresh overview metrics, pending proposals, and position states</p>
            </TooltipContent>
          </Tooltip>

          {/* Toggle AI Copilot chat sidebar */}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="outline"
                size="icon"
                onClick={onToggleChat}
                className="h-8 w-8 text-muted-foreground hover:text-foreground"
              >
                <Bot className="w-4 h-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>Toggle the AI Copilot chat sidebar</p>
            </TooltipContent>
          </Tooltip>
        </div>
      </header>
    </TooltipProvider>
  );
};

const HeaderMetric: React.FC<{ label: string; value?: number; colored?: boolean }> = ({ label, value, colored }) => {
  const amount = value === undefined ? '—' : `₹${value.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
  return (
    <div className="min-w-[92px]">
      <p className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className={`font-mono text-sm font-bold ${colored && value !== undefined ? (value >= 0 ? 'text-emerald-400' : 'text-red-400') : 'text-foreground'}`}>{amount}</p>
    </div>
  );
};
