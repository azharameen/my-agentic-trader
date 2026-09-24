import React, { useState } from 'react';
import { Layers, LogOut, ArrowUpRight } from 'lucide-react';
import { OpenPosition } from '../../types/api';
import { formatINR, formatPct } from '../../lib/utils';
import { Card } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../ui/table';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '../ui/tooltip';

interface OpenPositionsProps {
  positions: OpenPosition[];
  onClosePosition: (tradeId: string) => void;
  onSelectSymbolForChart: (symbol: string) => void;
}

export const OpenPositions: React.FC<OpenPositionsProps> = ({
  positions,
  onClosePosition,
  onSelectSymbolForChart,
}) => {
  const [confirmingTradeId, setConfirmingTradeId] = useState<string | null>(null);

  if (positions.length === 0) {
    return (
      <Card className="p-8 text-center">
        <div className="w-12 h-12 rounded-full bg-muted border border-border flex items-center justify-center mx-auto mb-3 text-muted-foreground">
          <Layers className="w-6 h-6" />
        </div>
        <h3 className="text-sm font-semibold text-foreground">No Active Open Positions</h3>
        <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
          Approved proposals will execute paper orders and track live stop/target levels here.
        </p>
      </Card>
    );
  }

  return (
    <TooltipProvider>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-foreground flex items-center gap-2">
            <span>Active Paper Positions</span>
            <Badge variant="outline" className="bg-primary/10 text-primary border-primary/30 font-mono">
              {positions.length}
            </Badge>
          </h2>
          <span className="text-xs text-muted-foreground">Position Monitor active during market hours</span>
        </div>

        <Card className="overflow-hidden shadow-lg">
          <Table>
            <TableHeader className="bg-muted/50">
              <TableRow>
                <TableHead className="text-[11px] font-semibold uppercase tracking-wider">Symbol & Strategy</TableHead>
                <TableHead className="text-[11px] font-semibold uppercase tracking-wider">Entry Fill</TableHead>
                <TableHead className="text-[11px] font-semibold uppercase tracking-wider">Current Price</TableHead>
                <TableHead className="text-[11px] font-semibold uppercase tracking-wider">Unrealized P&L</TableHead>
                <TableHead className="text-[11px] font-semibold uppercase tracking-wider">Stop Distance</TableHead>
                <TableHead className="text-[11px] font-semibold uppercase tracking-wider">Target Distance</TableHead>
                <TableHead className="text-[11px] font-semibold uppercase tracking-wider">Risk Stake</TableHead>
                <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody className="font-mono">
              {positions.map((pos) => {
                const isProfitable = pos.unrealized_pnl >= 0;
                return (
                  <TableRow key={pos.trade_id} className="hover:bg-muted/40 transition">
                    {/* Symbol & Strategy */}
                    <TableCell className="font-sans">
                      <div className="flex items-center space-x-2">
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <button
                              onClick={() => onSelectSymbolForChart(pos.symbol)}
                              className="font-bold text-sm text-foreground hover:text-primary flex items-center gap-1 font-mono transition"
                            >
                              <span>{pos.symbol}</span>
                              <ArrowUpRight className="w-3.5 h-3.5 text-muted-foreground" />
                            </button>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>Open live candlestick chart for {pos.symbol}</p>
                          </TooltipContent>
                        </Tooltip>

                        <Badge variant="secondary" className="text-[10px]">
                          {pos.strategy_name}
                        </Badge>
                      </div>
                      <span className="text-[10px] text-muted-foreground block font-mono mt-0.5">
                        Qty: {pos.quantity} shares
                      </span>
                    </TableCell>

                    {/* Entry Fill */}
                    <TableCell className="text-foreground">
                      ₹{formatINR(pos.fill_price)}
                    </TableCell>

                    {/* Current Price */}
                    <TableCell className="font-bold text-foreground">
                      ₹{formatINR(pos.current_price)}
                    </TableCell>

                    {/* Unrealized P&L */}
                    <TableCell>
                      <div className={`font-bold ${isProfitable ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {isProfitable ? '+' : ''}₹{formatINR(pos.unrealized_pnl)}
                      </div>
                      <div className={`text-[10px] ${isProfitable ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {formatPct(pos.unrealized_pnl_pct)}
                      </div>
                    </TableCell>

                    {/* Hard Stop Dist */}
                    <TableCell>
                      <div className="text-foreground">₹{formatINR(pos.hard_stop)}</div>
                      <span className="text-[10px] text-rose-400">
                        {pos.stop_dist_pct.toFixed(1)}% buffer
                      </span>
                    </TableCell>

                    {/* Target Dist */}
                    <TableCell>
                      <div className="text-foreground">₹{formatINR(pos.target_price)}</div>
                      <span className="text-[10px] text-emerald-400">
                        {pos.target_dist_pct.toFixed(1)}% away
                      </span>
                    </TableCell>

                    {/* Capital at Risk */}
                    <TableCell className="text-rose-400">
                      ₹{formatINR(pos.risk_amount)}
                    </TableCell>

                    {/* Exit Button */}
                    <TableCell className="text-right">
                      {confirmingTradeId === pos.trade_id ? (
                        <div className="flex items-center justify-end space-x-1.5 font-sans">
                          <Button
                            size="sm"
                            variant="destructive"
                            onClick={() => {
                              onClosePosition(pos.trade_id);
                              setConfirmingTradeId(null);
                            }}
                            className="h-7 px-2.5 text-xs font-bold"
                          >
                            Confirm Exit
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => setConfirmingTradeId(null)}
                            className="h-7 px-2 text-xs"
                          >
                            Cancel
                          </Button>
                        </div>
                      ) : (
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => setConfirmingTradeId(pos.trade_id)}
                              className="h-7 px-2.5 text-xs text-muted-foreground hover:text-rose-400 hover:border-rose-500/30 gap-1 ml-auto"
                            >
                              <LogOut className="w-3.5 h-3.5" />
                              <span>Exit</span>
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>Manually exit this paper trade position at current market price</p>
                          </TooltipContent>
                        </Tooltip>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </Card>
      </div>
    </TooltipProvider>
  );
};
