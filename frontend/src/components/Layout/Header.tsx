import React from 'react';
import { RefreshCw, Play, Search, Database } from 'lucide-react';
import { OverviewData } from '../../types/api';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '../ui/tooltip';

interface HeaderProps {
  overview: OverviewData | null;
  onRefresh: () => void;
  onOpenScanModal: () => void;
  onOpenRunModal: () => void;
  onRefreshUniverse: () => void;
  isRefreshing: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  overview,
  onRefresh,
  onOpenScanModal,
  onOpenRunModal,
  onRefreshUniverse,
  isRefreshing,
}) => {
  return (
    <TooltipProvider>
      <header className="h-16 border-b border-border bg-card/80 backdrop-blur px-6 flex items-center justify-between sticky top-0 z-30">
        <div className="flex items-center space-x-3">
          <span className="text-sm font-semibold text-foreground">
            NIFTY 100 Intelligent Trading Cockpit
          </span>
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
                onClick={onOpenRunModal}
                className="h-8 gap-1.5 text-xs font-medium"
              >
                <Search className="w-3.5 h-3.5 text-primary" />
                <span>Analyze Symbol</span>
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>Launch on-demand qualitative Bear/Bull debate and risk checks for any single NIFTY 100 stock</p>
            </TooltipContent>
          </Tooltip>

          {/* Run Universe Scan Button */}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="default"
                size="sm"
                onClick={onOpenScanModal}
                className="h-8 gap-1.5 text-xs font-semibold"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Run Universe Scan</span>
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
        </div>
      </header>
    </TooltipProvider>
  );
};
