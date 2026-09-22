import React, { useState } from 'react';
import { Search, Sparkles } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '../ui/dialog';
import { Input } from '../ui/input';
import { Button } from '../ui/button';

interface SymbolAnalysisModalProps {
  isOpen: boolean;
  onClose: () => void;
  onRunSymbol: (symbol: string) => void;
}

export const SymbolAnalysisModal: React.FC<SymbolAnalysisModalProps> = ({
  isOpen,
  onClose,
  onRunSymbol,
}) => {
  const [symbol, setSymbol] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const cleanSym = symbol.trim().toUpperCase().replace('.NS', '');
    if (cleanSym) {
      onRunSymbol(cleanSym);
      setSymbol('');
      onClose();
    }
  };

  const sampleSymbols = ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK', 'TATAMOTORS', 'SBIN', 'BHARTIARTL'];

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-md p-0 overflow-hidden">
        <DialogHeader className="px-6 py-4 border-b border-border bg-muted/30">
          <div className="flex items-center space-x-2">
            <Search className="w-5 h-5 text-primary" />
            <DialogTitle className="text-base font-bold text-foreground">Deep Analyze Symbol</DialogTitle>
          </div>
          <DialogDescription className="text-xs text-muted-foreground mt-0.5">
            Run an on-demand qualitative debate graph on any NIFTY 100 constituent.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="text-xs font-semibold text-foreground block mb-1.5">
              NSE Ticker Symbol
            </label>
            <Input
              type="text"
              placeholder="e.g. RELIANCE, TCS, INFY"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              className="font-mono text-sm"
              autoFocus
            />
          </div>

          <div>
            <span className="text-[11px] text-muted-foreground block mb-2">Popular NIFTY 100 Constituents:</span>
            <div className="flex flex-wrap gap-1.5">
              {sampleSymbols.map((sym) => (
                <Button
                  type="button"
                  key={sym}
                  variant="outline"
                  size="sm"
                  onClick={() => setSymbol(sym)}
                  className="h-6 px-2 text-[11px] font-mono text-muted-foreground hover:text-primary"
                >
                  {sym}
                </Button>
              ))}
            </div>
          </div>

          <div className="pt-2">
            <Button
              type="submit"
              disabled={!symbol.trim()}
              className="w-full text-xs font-semibold gap-2 shadow-lg shadow-primary/25"
            >
              <Sparkles className="w-4 h-4" />
              <span>Launch Multi-Agent Research Graph</span>
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};
