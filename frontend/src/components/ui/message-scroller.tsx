import * as React from 'react';
import { ArrowDown } from 'lucide-react';
import { cn } from '../../lib/utils';
import { Button } from './button';

/**
 * Pragmatic stand-in for shadcn's `MessageScroller` primitive (the full
 * version ships turn-anchoring, prepend-preserving scroll, and virtualization
 * via a separate `@shadcn/react` package we don't depend on). This keeps the
 * behavior that matters for a single-thread agent chat: stick to the bottom
 * while streaming, stop following the instant the reader scrolls up, and a
 * "scroll to latest" button to jump back in.
 */
interface MessageScrollerContextValue {
  viewportRef: React.RefObject<HTMLDivElement>;
  isAtBottom: boolean;
  scrollToEnd: (behavior?: ScrollBehavior) => void;
}

const MessageScrollerContext = React.createContext<MessageScrollerContextValue | null>(null);

export function useMessageScroller(): MessageScrollerContextValue {
  const ctx = React.useContext(MessageScrollerContext);
  if (!ctx) throw new Error('useMessageScroller must be used within a MessageScrollerProvider');
  return ctx;
}

const BOTTOM_THRESHOLD_PX = 48;

export const MessageScrollerProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const viewportRef = React.useRef<HTMLDivElement>(null);
  const [isAtBottom, setIsAtBottom] = React.useState(true);

  const scrollToEnd = React.useCallback((behavior: ScrollBehavior = 'smooth') => {
    const el = viewportRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior });
  }, []);

  const handleScroll = React.useCallback(() => {
    const el = viewportRef.current;
    if (!el) return;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    setIsAtBottom(distanceFromBottom < BOTTOM_THRESHOLD_PX);
  }, []);

  React.useEffect(() => {
    const el = viewportRef.current;
    if (!el) return;
    el.addEventListener('scroll', handleScroll, { passive: true });
    return () => el.removeEventListener('scroll', handleScroll);
  }, [handleScroll]);

  return (
    <MessageScrollerContext.Provider value={{ viewportRef, isAtBottom, scrollToEnd }}>
      {children}
    </MessageScrollerContext.Provider>
  );
};

export const MessageScroller = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, children, ...props }, ref) => (
    <div ref={ref} className={cn('relative flex flex-1 flex-col min-h-0', className)} {...props}>
      {children}
    </div>
  )
);
MessageScroller.displayName = 'MessageScroller';

export const MessageScrollerViewport = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, children, ...props }, ref) => {
    const { viewportRef } = useMessageScroller();
    return (
      <div
        ref={(node) => {
          (viewportRef as React.MutableRefObject<HTMLDivElement | null>).current = node;
          if (typeof ref === 'function') ref(node);
          else if (ref) (ref as React.MutableRefObject<HTMLDivElement | null>).current = node;
        }}
        role="region"
        aria-label="Messages"
        tabIndex={0}
        className={cn('flex-1 overflow-y-auto', className)}
        {...props}
      >
        {children}
      </div>
    );
  }
);
MessageScrollerViewport.displayName = 'MessageScrollerViewport';

export const MessageScrollerContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} role="log" aria-relevant="additions" className={cn('flex flex-col gap-4 p-4', className)} {...props} />
  )
);
MessageScrollerContent.displayName = 'MessageScrollerContent';

export const MessageScrollerItem = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & { messageId?: string; scrollAnchor?: boolean }
>(({ className, messageId, scrollAnchor: _scrollAnchor, ...props }, ref) => (
  <div ref={ref} data-message-id={messageId} className={cn(className)} {...props} />
));
MessageScrollerItem.displayName = 'MessageScrollerItem';

export const MessageScrollerButton: React.FC<{ className?: string }> = ({ className }) => {
  const { isAtBottom, scrollToEnd } = useMessageScroller();
  if (isAtBottom) return null;
  return (
    <Button
      size="sm"
      variant="secondary"
      onClick={() => scrollToEnd()}
      className={cn('absolute bottom-3 left-1/2 -translate-x-1/2 shadow-lg gap-1.5 h-8 text-xs z-10', className)}
    >
      <ArrowDown className="w-3.5 h-3.5" /> Scroll to latest
    </Button>
  );
};

/** Auto-follows new content while the reader is already at (or near) the bottom. */
export function useAutoScrollOnChange(dep: unknown) {
  const { isAtBottom, scrollToEnd } = useMessageScroller();
  React.useEffect(() => {
    if (isAtBottom) scrollToEnd('auto');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dep]);
}
