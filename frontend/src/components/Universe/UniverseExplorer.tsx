import React, { useState, useEffect, useMemo } from 'react';
import {
  Search,
  RefreshCw,
  ArrowDownToLine,
  TrendingUp,
  Sparkles,
  Layers,
  Database,
  ExternalLink,
  ShieldCheck,
} from 'lucide-react';
import { fetchUniverse, refreshUniverse } from '../../lib/api';
import { UniverseConstituent, UniverseResponse } from '../../types/api';
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

interface UniverseExplorerProps {
  onSelectSymbolForChart: (symbol: string) => void;
  onRunSymbol: (symbol: string) => void;
  showToast: (msg: string) => void;
}

export const UniverseExplorer: React.FC<UniverseExplorerProps> = ({
  onSelectSymbolForChart,
  onRunSymbol,
  showToast,
}) => {
  const [universeData, setUniverseData] = useState<UniverseResponse | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedIndustry, setSelectedIndustry] = useState<string>('ALL');
  const [isLoading, setIsLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const loadUniverse = async () => {
    setIsLoading(true);
    try {
      const data = await fetchUniverse();
      setUniverseData(data);
    } catch (err: any) {
      console.error('Failed to load universe', err);
      showToast(`Failed to load universe: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadUniverse();
  }, []);

  const handleForceRefresh = async () => {
    setIsRefreshing(true);
    try {
      const data = await refreshUniverse();
      setUniverseData(data);
      showToast(`Refreshed ${data.count} universe constituents live from NSE.`);
    } catch (err: any) {
      console.error('Failed to refresh universe', err);
      showToast(`Universe refresh failed: ${err.message}`);
    } finally {
      setIsRefreshing(false);
    }
  };

  const constituents = universeData?.constituents || [];

  const industries = useMemo(() => {
    const set = new Set<string>();
    constituents.forEach((c) => {
      if (c.industry) set.add(c.industry);
    });
    return Array.from(set).sort();
  }, [constituents]);

  const filteredConstituents = useMemo(() => {
    return constituents.filter((c) => {
      const matchesSearch =
        c.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
        c.company_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        c.isin.toLowerCase().includes(searchQuery.toLowerCase()) ||
        c.industry.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesIndustry = selectedIndustry === 'ALL' || c.industry === selectedIndustry;
      return matchesSearch && matchesIndustry;
    });
  }, [constituents, searchQuery, selectedIndustry]);

  const exportCSV = () => {
    if (constituents.length === 0) return;
    const headers = ['Symbol', 'Company Name', 'Industry', 'Series', 'ISIN Code'];
    const rows = constituents.map((c) => [
      c.symbol,
      `"${c.company_name}"`,
      `"${c.industry}"`,
      c.series,
      c.isin,
    ]);

    const csvContent =
      'data:text/csv;charset=utf-8,' +
      [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute(
      'download',
      `nifty100_constituents_${new Date().toISOString().slice(0, 10)}.csv`
    );
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <TooltipProvider>
      <div className="space-y-6">
        {/* Top Summary Ribbon */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
          <Card className="shadow-sm">
            <CardContent className="p-3.5">
              <div className="flex items-center justify-between text-muted-foreground mb-1">
                <span className="text-xs font-medium">Constituents Count</span>
                <Layers className="w-4 h-4 text-primary" />
              </div>
              <div className="text-xl font-bold font-mono text-foreground">
                {universeData?.count || constituents.length || 100}
              </div>
              <span className="text-[10px] text-muted-foreground/70">NIFTY 100 Index</span>
            </CardContent>
          </Card>

          <Card className="shadow-sm">
            <CardContent className="p-3.5">
              <div className="flex items-center justify-between text-muted-foreground mb-1">
                <span className="text-xs font-medium">Sectors Represented</span>
                <Database className="w-4 h-4 text-emerald-400" />
              </div>
              <div className="text-xl font-bold font-mono text-foreground">
                {industries.length || 18}
              </div>
              <span className="text-[10px] text-muted-foreground/70">Broad market coverage</span>
            </CardContent>
          </Card>

          <Card className="shadow-sm">
            <CardContent className="p-3.5">
              <div className="flex items-center justify-between text-muted-foreground mb-1">
                <span className="text-xs font-medium">Universe Source</span>
                <ShieldCheck className="w-4 h-4 text-blue-400" />
              </div>
              <div className="text-xl font-bold font-mono text-foreground">
                NSE Indices
              </div>
              <span className="text-[10px] text-muted-foreground/70">Self-refreshing cache</span>
            </CardContent>
          </Card>

          <Card className="shadow-sm">
            <CardContent className="p-3.5">
              <div className="flex items-center justify-between text-muted-foreground mb-1">
                <span className="text-xs font-medium">Filtered Results</span>
                <Search className="w-4 h-4 text-amber-400" />
              </div>
              <div className="text-xl font-bold font-mono text-foreground">
                {filteredConstituents.length}
              </div>
              <span className="text-[10px] text-muted-foreground/70">
                {selectedIndustry === 'ALL' ? 'All industries' : selectedIndustry}
              </span>
            </CardContent>
          </Card>
        </div>

        {/* Main Universe Table Card */}
        <Card className="shadow-2xl space-y-4">
          <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-4 border-b border-border pb-4 space-y-0">
            <div>
              <CardTitle className="text-base font-bold text-foreground flex items-center gap-2">
                <span>NIFTY 100 Constituent Universe</span>
                <Badge variant="outline" className="text-primary border-primary/30 font-mono text-xs">
                  {constituents.length} Stocks
                </Badge>
              </CardTitle>
              <CardDescription className="text-xs text-muted-foreground mt-0.5">
                Official constituent universe screened for asymmetric pullback setups and qualitative agent debate
              </CardDescription>
            </div>

            <div className="flex flex-wrap items-center gap-2.5">
              <div className="relative">
                <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-2.5" />
                <Input
                  type="text"
                  placeholder="Search symbol, company, ISIN..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9 h-8 text-xs w-56 font-mono"
                />
              </div>

              <select
                value={selectedIndustry}
                onChange={(e) => setSelectedIndustry(e.target.value)}
                className="bg-muted border border-border rounded-lg px-3 h-8 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring transition"
              >
                <option value="ALL">All Industries ({industries.length})</option>
                {industries.map((ind) => (
                  <option key={ind} value={ind}>
                    {ind}
                  </option>
                ))}
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
                    <span className="hidden sm:inline">Export CSV</span>
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Download the complete NIFTY 100 constituent list as a CSV file</p>
                </TooltipContent>
              </Tooltip>

              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleForceRefresh}
                    disabled={isRefreshing}
                    className="h-8 text-xs text-primary gap-1.5"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
                    <span>{isRefreshing ? 'Refreshing...' : 'Live Sync NSE'}</span>
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Force download the latest live constituent list from NSE Indices official endpoint</p>
                </TooltipContent>
              </Tooltip>
            </div>
          </CardHeader>

          <CardContent className="p-0">
            <Table>
              <TableHeader className="bg-muted/50">
                <TableRow>
                  <TableHead className="text-[11px] font-semibold uppercase tracking-wider w-24">Symbol</TableHead>
                  <TableHead className="text-[11px] font-semibold uppercase tracking-wider">Company Name</TableHead>
                  <TableHead className="text-[11px] font-semibold uppercase tracking-wider">Industry / Sector</TableHead>
                  <TableHead className="text-[11px] font-semibold uppercase tracking-wider">ISIN Code</TableHead>
                  <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredConstituents.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="py-8 text-center text-muted-foreground text-xs">
                      {isLoading ? 'Loading NIFTY 100 universe...' : 'No constituents match your search criteria.'}
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredConstituents.map((c) => (
                    <TableRow key={c.symbol} className="hover:bg-muted/40 transition">
                      {/* Symbol */}
                      <TableCell className="font-mono font-bold text-foreground">
                        {c.symbol}
                      </TableCell>

                      {/* Company Name */}
                      <TableCell className="text-xs text-foreground font-medium">
                        {c.company_name}
                      </TableCell>

                      {/* Industry */}
                      <TableCell>
                        <Badge variant="secondary" className="text-[10px] font-normal">
                          {c.industry || 'General'}
                        </Badge>
                      </TableCell>

                      {/* ISIN */}
                      <TableCell className="font-mono text-[11px] text-muted-foreground">
                        {c.isin || '-'}
                      </TableCell>

                      {/* Actions */}
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end space-x-1.5">
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => onSelectSymbolForChart(c.symbol)}
                                className="h-7 px-2 text-xs text-muted-foreground hover:text-primary gap-1"
                              >
                                <TrendingUp className="w-3.5 h-3.5" />
                                <span className="hidden md:inline">Chart</span>
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>
                              <p>Open live TradingView lightweight candlestick chart for {c.symbol}</p>
                            </TooltipContent>
                          </Tooltip>

                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button
                                variant="default"
                                size="sm"
                                onClick={() => onRunSymbol(c.symbol)}
                                className="h-7 px-2 text-xs font-semibold gap-1 shadow-sm"
                              >
                                <Sparkles className="w-3.5 h-3.5" />
                                <span className="hidden md:inline">Analyze</span>
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>
                              <p>Launch deep multi-agent qualitative research debate on {c.symbol}</p>
                            </TooltipContent>
                          </Tooltip>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </TooltipProvider>
  );
};
