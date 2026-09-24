import React from 'react';
import {
  CandlestickChart, FlaskConical, Globe, LayoutDashboard,
  ShieldCheck, TrendingUp, Zap, CalendarClock,
} from 'lucide-react';
import { Badge } from '../ui/badge';
import {
  Sidebar as ShadcnSidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuBadge,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  SidebarTrigger,
} from '../ui/sidebar';
import { Popover, PopoverContent, PopoverTrigger } from '../ui/popover';

export type TabType = 'command' | 'copilot' | 'charts' | 'universe' | 'performance' | 'backtest' | 'health' | 'schedules';

interface SidebarProps {
  activeTab: TabType;
  setActiveTab: (tab: TabType) => void;
  pendingCount: number;
}

const navItems: Array<{ id: TabType; label: string; icon: React.ElementType; badge?: (count: number) => number; description: string }> = [
  { id: 'command', label: 'Command Center', icon: LayoutDashboard, description: 'Everything you own in one screen: stocks, F&O, mutual funds, capital, returns, and live agent signals' },
  { id: 'charts', label: 'Candlestick Explorer', icon: CandlestickChart, description: 'Interactive price charts and technical levels' },
  { id: 'universe', label: 'NIFTY 100 Universe', icon: Globe, description: 'Constituents, sectors, and direct symbol analysis' },
  { id: 'performance', label: 'Audit & Alpha', icon: TrendingUp, description: 'Benchmark alpha and the historical trade log' },
  { id: 'backtest', label: 'Backtest Studio', icon: FlaskConical, description: 'Walk-forward strategy simulation' },
  { id: 'schedules', label: 'Schedules', icon: CalendarClock, description: 'View and manage automated background jobs' },
  { id: 'health', label: 'Health & Regime', icon: ShieldCheck, description: 'Operational telemetry, macro regime, and risk bounds' },
];

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, setActiveTab, pendingCount }) => (
  <ShadcnSidebar collapsible="icon">
    <SidebarHeader>
      <SidebarMenu>
        <SidebarMenuItem>
          <div className="flex h-10 items-center gap-3 rounded-md px-2 group-data-[state=collapsed]/sidebar-wrapper:justify-center">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-md shadow-primary/30">
              <Zap className="h-4 w-4" />
            </div>
            <div data-sidebar-label className="min-w-0">
              <div className="flex items-center gap-1.5 text-sm font-bold tracking-tight">
                TrAId <Badge variant="secondary" className="px-1.5 py-0 text-[10px] font-mono">v2.0</Badge>
              </div>
              <p className="truncate text-[11px] text-muted-foreground font-mono">NIFTY 100 Command Center</p>
            </div>
          </div>
        </SidebarMenuItem>
      </SidebarMenu>
    </SidebarHeader>
    <SidebarContent>
      <SidebarGroup>
        <SidebarGroupLabel>Navigation</SidebarGroupLabel>
        <SidebarMenu>
          {navItems.map((item) => {
            const Icon = item.icon;
            const badge = item.badge?.(pendingCount) ?? 0;
            return (
              <SidebarMenuItem key={item.id}>
                <SidebarMenuButton
                  isActive={activeTab === item.id}
                  tooltip={item.description}
                  onClick={() => setActiveTab(item.id)}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  <span data-sidebar-label>{item.label}</span>
                </SidebarMenuButton>
                {badge > 0 && <SidebarMenuBadge>{badge}</SidebarMenuBadge>}
              </SidebarMenuItem>
            );
          })}
        </SidebarMenu>
      </SidebarGroup>
    </SidebarContent>
    <SidebarFooter>
      <SidebarMenu>
        <SidebarMenuItem>
          <Popover>
            <PopoverTrigger asChild>
              <SidebarMenuButton tooltip="Open user menu" className="h-11">
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">DU</span>
                <span data-sidebar-label className="grid min-w-0 text-left leading-tight">
                  <span className="truncate text-xs font-semibold">Default User</span>
                  <span className="truncate text-[10px] text-muted-foreground">Local operator</span>
                </span>
              </SidebarMenuButton>
            </PopoverTrigger>
            <PopoverContent side="right" align="end" className="w-56 p-2">
              <div className="border-b border-border px-2 pb-2">
                <p className="text-sm font-semibold">Default User</p>
                <p className="text-xs text-muted-foreground">Local operator account</p>
              </div>
              <div className="pt-1">
                <button type="button" className="flex w-full items-center rounded-sm px-2 py-2 text-left text-sm hover:bg-accent">Settings</button>
                <button type="button" className="flex w-full items-center rounded-sm px-2 py-2 text-left text-sm hover:bg-accent">Help</button>
                <button type="button" className="flex w-full items-center rounded-sm px-2 py-2 text-left text-sm text-destructive hover:bg-destructive/10">Log out</button>
              </div>
            </PopoverContent>
          </Popover>
        </SidebarMenuItem>
      </SidebarMenu>
    </SidebarFooter>
    <SidebarRail />
  </ShadcnSidebar>
);

export const SidebarToggle: React.FC = () => {
  return <SidebarTrigger aria-label="Toggle navigation" />;
};
