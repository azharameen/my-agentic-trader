import * as React from 'react';
import { PanelLeft } from 'lucide-react';
import { cn } from '../../lib/utils';
import { Button } from './button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from './tooltip';

type SidebarState = 'expanded' | 'collapsed';
type SidebarSide = 'left' | 'right';
type SidebarCollapsible = 'offcanvas' | 'icon' | 'none';

interface SidebarContextValue {
  state: SidebarState;
  open: boolean;
  setOpen: (open: boolean) => void;
  toggleSidebar: () => void;
}

const SidebarContext = React.createContext<SidebarContextValue | null>(null);

export const useSidebar = (): SidebarContextValue => {
  const context = React.useContext(SidebarContext);
  if (!context) throw new Error('useSidebar must be used inside SidebarProvider');
  return context;
};

interface SidebarProviderProps extends React.HTMLAttributes<HTMLDivElement> {
  defaultOpen?: boolean;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

export const SidebarProvider = React.forwardRef<HTMLDivElement, SidebarProviderProps>(
  ({ defaultOpen = true, open: controlledOpen, onOpenChange, className, children, ...props }, ref) => {
    const [internalOpen, setInternalOpen] = React.useState(defaultOpen);
    const open = controlledOpen ?? internalOpen;
    const setOpen = React.useCallback((nextOpen: boolean) => {
      if (controlledOpen === undefined) setInternalOpen(nextOpen);
      onOpenChange?.(nextOpen);
    }, [controlledOpen, onOpenChange]);
    const toggleSidebar = React.useCallback(() => setOpen(!open), [open, setOpen]);

    React.useEffect(() => {
      const onKeyDown = (event: KeyboardEvent) => {
        if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'b') {
          event.preventDefault();
          toggleSidebar();
        }
      };
      window.addEventListener('keydown', onKeyDown);
      return () => window.removeEventListener('keydown', onKeyDown);
    }, [toggleSidebar]);

    return (
      <SidebarContext.Provider value={{ state: open ? 'expanded' : 'collapsed', open, setOpen, toggleSidebar }}>
        <TooltipProvider>
          <div ref={ref} data-state={open ? 'expanded' : 'collapsed'} className={cn('group/sidebar-wrapper flex min-h-svh w-full', className)} {...props}>
            {children}
          </div>
        </TooltipProvider>
      </SidebarContext.Provider>
    );
  }
);
SidebarProvider.displayName = 'SidebarProvider';

interface SidebarProps extends React.HTMLAttributes<HTMLElement> {
  side?: SidebarSide;
  collapsible?: SidebarCollapsible;
}

export const Sidebar = React.forwardRef<HTMLElement, SidebarProps>(
  ({ side = 'left', collapsible = 'offcanvas', className, children, ...props }, ref) => {
    const { state } = useSidebar();
    const hidden = collapsible === 'offcanvas' && state === 'collapsed';
    const iconCollapsed = collapsible === 'icon' && state === 'collapsed';
    return (
      <aside
        ref={ref}
        data-side={side}
        data-state={state}
        data-collapsible={collapsible}
        className={cn(
          'relative flex h-svh shrink-0 flex-col border-border bg-card transition-[width,transform] duration-200 ease-linear',
          side === 'left' ? 'border-r' : 'border-l',
          hidden ? 'w-0 overflow-hidden border-0' : iconCollapsed ? 'w-16' : 'w-[var(--sidebar-width,16rem)]',
          className,
        )}
        {...props}
      >
        <div className={cn('flex min-h-0 flex-1 flex-col', iconCollapsed && '[&_[data-sidebar-label]]:hidden')}>
          {children}
        </div>
      </aside>
    );
  }
);
Sidebar.displayName = 'Sidebar';

export const SidebarHeader = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn('flex shrink-0 flex-col border-b border-border p-2', className)} {...props} />
);
export const SidebarContent = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn('flex min-h-0 flex-1 flex-col gap-2 overflow-auto p-2', className)} {...props} />
);
export const SidebarFooter = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn('shrink-0 border-t border-border p-2', className)} {...props} />
);
export const SidebarGroup = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn('relative flex w-full min-w-0 flex-col p-2', className)} {...props} />
);
export const SidebarGroupLabel = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div data-sidebar-label className={cn('px-2 pb-2 text-xs font-medium text-muted-foreground', className)} {...props} />
);
export const SidebarMenu = ({ className, ...props }: React.HTMLAttributes<HTMLUListElement>) => (
  <ul className={cn('flex w-full min-w-0 flex-col gap-1', className)} {...props} />
);
export const SidebarMenuItem = (props: React.LiHTMLAttributes<HTMLLIElement>) => <li className="group/menu-item relative" {...props} />;

interface SidebarMenuButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  isActive?: boolean;
  tooltip?: string;
}

export const SidebarMenuButton = React.forwardRef<HTMLButtonElement, SidebarMenuButtonProps>(
  ({ isActive, tooltip, className, children, ...props }, ref) => {
    const button = <button ref={ref} data-active={isActive} className={cn('flex h-9 w-full items-center gap-2 rounded-md px-2 text-sm text-muted-foreground outline-none transition-colors hover:bg-accent hover:text-accent-foreground data-[active=true]:bg-primary data-[active=true]:font-semibold data-[active=true]:text-primary-foreground', className)} {...props}>{children}</button>;
    if (!tooltip) return button;
    return <Tooltip><TooltipTrigger asChild>{button}</TooltipTrigger><TooltipContent side="right">{tooltip}</TooltipContent></Tooltip>;
  }
);
SidebarMenuButton.displayName = 'SidebarMenuButton';

export const SidebarMenuBadge = ({ className, ...props }: React.HTMLAttributes<HTMLSpanElement>) => (
  <span className={cn('absolute right-2 top-2 rounded border border-amber-500/30 bg-amber-500/10 px-1.5 text-[10px] text-amber-400', className)} {...props} />
);

export const SidebarRail = () => {
  const { toggleSidebar } = useSidebar();
  return <button type="button" aria-label="Toggle navigation" onClick={toggleSidebar} className="absolute inset-y-0 -right-2 z-20 hidden w-4 cursor-ew-resize sm:block" />;
};

export const SidebarTrigger = React.forwardRef<HTMLButtonElement, React.ComponentProps<typeof Button>>(({ className, onClick, ...props }, ref) => {
  const { toggleSidebar } = useSidebar();
  return <Button ref={ref} variant="ghost" size="icon" aria-label="Toggle sidebar" className={cn('h-7 w-7', className)} onClick={(event) => { onClick?.(event); toggleSidebar(); }} {...props}><PanelLeft className="h-4 w-4" /></Button>;
});
SidebarTrigger.displayName = 'SidebarTrigger';

export const SidebarInset = ({ className, ...props }: React.HTMLAttributes<HTMLElement>) => (
  <main className={cn('relative flex min-w-0 flex-1 flex-col bg-background', className)} {...props} />
);
