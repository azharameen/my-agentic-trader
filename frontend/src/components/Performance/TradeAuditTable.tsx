import React, { useState } from 'react';
import { Search, ArrowDownToLine } from 'lucide-react';
import { HistoricalTrade } from '../../types/api';
import { formatINR, formatDateTime } from '../../lib/utils';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '../ui/tooltip';

interface TradeAuditTableProps {
  trades: HistoricalTrade[];
}

export const TradeAuditTable: React.FC<TradeAuditTableProps> = ({ trades }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  const filteredTrades = trades.filter((t) => {
    const matchesSearch =
      t.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (t.thesis && t.thesis.toLowerCase().includes(searchQuery.toLowerCase()));
    const matchesStatus = statusFilter === 'ALL' || t.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const exportCSV = () => {
    if (trades.length === 0) return;
    const headers = ['trade_id', 'timestamp', 'symbol', 'strategy', 'entry_price', 'exit_price', 'quantity', 'status', 'realized_pnl'];
    const rows = trades.map((t) => [
      t.trade_id,
      t.timestamp,
      t.symbol,
      t.strategy_name || 'PULLBACK',
      t.entry_price,
      t.exit_price || '',
      t.quantity,
      t.status,
      t.realized_pnl || '',
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `traid_audit_trades_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <TooltipProvider>
      <Card className="shadow-2xl space-y-4">
        {/* Header & Filters */}
        <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-4 border-b border-border pb-4 space-y-0">
          <div>
            <CardTitle className="text-base font-bold text-foreground">Historical Trade Audit Log</CardTitle>
            <CardDescription className="text-xs text-muted-foreground mt-0.5">
              Complete immutable record of all decisions stored in PostgreSQL (ADR-023)
            </CardDescription>
          </div>

          <div className="flex items-center space-x-3">
            <div className="relative">
              <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-2.5" />
              <Input
                type="text"
                placeholder="Search symbol..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 h-8 text-xs w-48 font-mono"
              />
            </div>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-muted border border-border rounded-lg px-3 h-8 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring transition"
            >
              <option value="ALL">All Statuses</option>
              <option value="CLOSED">CLOSED</option>
              <option value="OPEN_PAPER">OPEN_PAPER</option>
              <option value="REJECTED">REJECTED</option>
            </select>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={exportCSV}
                  className="h-8 text-xs text-muted-foreground hover:text-foreground gap-1.5"
                >
                  <ArrowDownToLine className="w-3.5 h-3.5" />
                  <span>Export CSV</span>
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>Export all historical audit records to a CSV spreadsheet</p>
              </TooltipContent>
            </Tooltip>
          </div>
        </CardHeader>

        {/* Trades Table */}
        <CardContent className="p-0">
          <Table>
            <TableHeader className="bg-muted/50">
              <TableRow>
                <TableHead className="text-[11px] font-semibold uppercase tracking-wider">Timestamp</TableHead>
                <TableHead className="text-[11px] font-semibold uppercase tracking-wider">Symbol</TableHead>
                <TableHead className="text-[11px] font-semibold uppercase tracking-wider">Strategy</TableHead>
                <TableHead className="text-[11px] font-semibold uppercase tracking-wider">Entry Fill</TableHead>
                <TableHead className="text-[11px] font-semibold uppercase tracking-wider">Exit Fill</TableHead>
                <TableHead className="text-[11px] font-semibold uppercase tracking-wider">Quantity</TableHead>
                <TableHead className="text-[11px] font-semibold uppercase tracking-wider">Status</TableHead>
                <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-right">Realized P&L</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody className="font-mono">
              {filteredTrades.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="py-8 text-center text-muted-foreground font-sans">
                    No trades match the current filter criteria.
                  </TableCell>
                </TableRow>
              ) : (
                filteredTrades.map((t) => {
                  const isPnlPositive = (t.realized_pnl || 0) >= 0;
                  return (
                    <TableRow key={t.trade_id} className="hover:bg-muted/40 transition">
                      <TableCell className="text-muted-foreground font-sans text-xs">
                        {formatDateTime(t.timestamp)}
                      </TableCell>
                      <TableCell className="font-bold text-foreground">
                        {t.symbol}
                      </TableCell>
                      <TableCell className="font-sans text-muted-foreground">
                        {t.strategy_name || 'PULLBACK'}
                      </TableCell>
                      <TableCell className="text-foreground">
                        ₹{formatINR(t.fill_price || t.entry_price)}
                      </TableCell>
                      <TableCell className="text-foreground">
                        {t.exit_price ? `₹${formatINR(t.exit_price)}` : '-'}
                      </TableCell>
                      <TableCell className="text-foreground">
                        {t.quantity}
                      </TableCell>
                      <TableCell className="font-sans">
                        <Badge
                          variant="outline"
                          className={`text-[10px] uppercase font-bold ${
                            t.status === 'CLOSED'
                              ? isPnlPositive
                                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                                : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                              : t.status === 'OPEN_PAPER'
                              ? 'bg-primary/10 text-primary border-primary/20'
                              : 'bg-muted text-muted-foreground border-border'
                          }`}
                        >
                          {t.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        {t.realized_pnl !== undefined && t.realized_pnl !== null ? (
                          <span className={`font-bold ${isPnlPositive ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {isPnlPositive ? '+' : ''}₹{formatINR(t.realized_pnl)}
                          </span>
                        ) : (
                          <span className="text-muted-foreground">-</span>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </TooltipProvider>
  );
};
