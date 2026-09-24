import React from 'react';
import { AgentChatPanel } from '../Copilot/AgentChatPanel';
import { Sidebar as ShadcnSidebar, SidebarContent, SidebarProvider } from '../ui/sidebar';

interface ChatSidebarProps {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  onShowToast: (msg: string) => void;
  onPortfolioChanged: () => void;
  initialPrompt?: string;
}

/**
 * Persistent right-hand chat panel — NOT an overlay/Sheet. When `open`, it
 * takes up real space in the flex layout so the main content is pushed
 * (shrinks), not covered. No backdrop, no click-outside-to-close, no close
 * button: it only toggles via the header's chat icon (same button that
 * opened it) so it behaves like the left navigation rail.
 */
export const ChatSidebar: React.FC<ChatSidebarProps> = ({ open, onOpenChange, onShowToast, onPortfolioChanged, initialPrompt }) => (
  <SidebarProvider open={open} onOpenChange={onOpenChange} defaultOpen={false} className="h-screen w-auto min-w-0 shrink-0 flex-none">
    <ShadcnSidebar
      side="right"
      collapsible="offcanvas"
      style={{ '--sidebar-width': '420px' } as React.CSSProperties}
      className="bg-card/50"
    >
      <SidebarContent className="p-4">
        <AgentChatPanel onShowToast={onShowToast} onPortfolioChanged={onPortfolioChanged} initialPrompt={initialPrompt} />
      </SidebarContent>
    </ShadcnSidebar>
  </SidebarProvider>
);

export default ChatSidebar;
