import React from 'react';
import { 
  LayoutDashboard, 
  Bot, 
  CandlestickChart, 
  TrendingUp, 
  FlaskConical, 
  ShieldCheck, 
  Zap,
  Globe,
  Sparkles,
} from 'lucide-react';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '../ui/tooltip';
import { Wallet } from 'lucide-react';

export type TabType = 'invest' | 'demat' | 'cockpit' | 'copilot' | 'charts' | 'universe' | 'performance' | 'backtest' | 'health';

interface SidebarProps {
  activeTab: TabType;
  setActiveTab: (tab: TabType) => void;
  pendingCount: number;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, setActiveTab, pendingCount }) => {
  const navItems: Array<{ id: TabType; label: string; icon: React.ReactNode; badge?: number; description: string }> = [
    {
      id: 'invest',
      label: 'Smart Investing',
      icon: <Sparkles className="w-4 h-4 text-blue-400" />,
      description: 'Beginner-first portfolio planner, manual broker guidance, and 24/7 AI health monitoring',
    },
    {
      id: 'demat',
      label: 'Demat & Groww Hub',
      icon: <Wallet className="w-4 h-4 text-emerald-400" />,
      description: 'Unified Demat portfolio, Groww equities & mutual funds folios, and AI health review',
    },
    {
      id: 'cockpit',
      label: 'Command Cockpit',
      icon: <LayoutDashboard className="w-4 h-4" />,
      badge: pendingCount,
      description: 'Review pending trade proposals and manage open paper positions',
    },
    {
      id: 'copilot',
      label: 'AI Copilot Chat',
      icon: <Bot className="w-4 h-4" />,
      description: 'Conversational research assistant with read & trigger capabilities',
    },
    {
      id: 'charts',
      label: 'Candlestick Explorer',
      icon: <CandlestickChart className="w-4 h-4" />,
      description: 'Live interactive TradingView candlestick charts for all constituents',
    },
    {
      id: 'universe',
      label: 'NIFTY 100 Universe',
      icon: <Globe className="w-4 h-4" />,
      description: 'View full 100 constituents list, sectors, ISIN codes, and direct analysis',
    },
    {
      id: 'performance',
      label: 'Audit & Alpha',
      icon: <TrendingUp className="w-4 h-4" />,
      description: 'Benchmark alpha metrics and full PostgreSQL historical trade log',
    },
    {
      id: 'backtest',
      label: 'Backtest Studio',
      icon: <FlaskConical className="w-4 h-4" />,
      description: 'Event-driven walk-forward simulation with realistic transaction friction',
    },
    {
      id: 'health',
      label: 'Health & Regime',
      icon: <ShieldCheck className="w-4 h-4" />,
      description: 'Operational telemetry, India VIX regime gates, and deterministic risk bounds',
    },
  ];

  return (
    <TooltipProvider>
      <aside className="w-64 bg-card border-r border-border flex flex-col justify-between flex-shrink-0 min-h-screen">
        <div>
          {/* Brand */}
          <div className="h-16 flex items-center px-6 border-b border-border">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center font-bold text-primary-foreground shadow-md shadow-primary/30 mr-3">
              <Zap className="w-4 h-4" />
            </div>
            <div>
              <h1 className="font-bold text-sm tracking-tight text-foreground flex items-center gap-1.5">
                TrAId <Badge variant="secondary" className="text-[10px] font-mono px-1.5 py-0">v2.0</Badge>
              </h1>
              <p className="text-[11px] text-muted-foreground font-mono">NIFTY 100 Cockpit</p>
            </div>
          </div>

          {/* Navigation */}
          <nav className="p-4 space-y-1">
            {navItems.map((item) => {
              const isActive = activeTab === item.id;
              return (
                <Tooltip key={item.id}>
                  <TooltipTrigger asChild>
                    <Button
                      variant={isActive ? 'default' : 'ghost'}
                      size="sm"
                      onClick={() => setActiveTab(item.id)}
                      className={`w-full justify-between font-medium ${
                        isActive ? 'shadow-md font-semibold' : 'text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      <div className="flex items-center space-x-3">
                        <span>{item.icon}</span>
                        <span>{item.label}</span>
                      </div>
                      {item.badge !== undefined && item.badge > 0 && (
                        <Badge variant="outline" className="ml-auto font-mono text-[10px] bg-amber-500/10 text-amber-400 border-amber-500/30">
                          {item.badge}
                        </Badge>
                      )}
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="right">
                    <p>{item.description}</p>
                  </TooltipContent>
                </Tooltip>
              );
            })}
          </nav>
        </div>

        {/* Footer Info */}
        <div className="p-4 border-t border-border bg-muted/30 text-xs text-muted-foreground space-y-1">
          <div className="flex items-center justify-between font-mono text-[11px]">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              ENGINE LIVE
            </span>
            <span className="text-muted-foreground">PAPER MODE</span>
          </div>
          <div className="text-[11px] text-muted-foreground pt-1">
            PostgreSQL 16 Sidecar Active
          </div>
        </div>
      </aside>
    </TooltipProvider>
  );
};
