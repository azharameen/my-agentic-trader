import * as React from 'react';
import { cn } from '../../lib/utils';

type BubbleVariant = 'default' | 'secondary' | 'muted' | 'tinted' | 'outline' | 'ghost' | 'destructive';
type Align = 'start' | 'end';

const variantClasses: Record<BubbleVariant, string> = {
  default: 'bg-primary text-primary-foreground',
  secondary: 'bg-secondary text-secondary-foreground',
  muted: 'bg-muted text-muted-foreground',
  tinted: 'bg-primary/10 text-foreground',
  outline: 'border border-border bg-transparent text-foreground',
  ghost: 'bg-transparent text-foreground max-w-none px-0',
  destructive: 'bg-destructive/10 text-destructive border border-destructive/30',
};

export interface BubbleProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: BubbleVariant;
  align?: Align;
}

const Bubble = React.forwardRef<HTMLDivElement, BubbleProps>(
  ({ className, variant = 'default', align = 'start', children, ...props }, ref) => (
    <div
      ref={ref}
      data-variant={variant}
      data-align={align}
      className={cn('flex flex-col gap-1', align === 'end' ? 'items-end' : 'items-start', className)}
      {...props}
    >
      {children}
    </div>
  )
);
Bubble.displayName = 'Bubble';

export interface BubbleContentProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: BubbleVariant;
}

/** Rendered inside `Bubble` (as a sibling wrapper prop) or used standalone with an explicit variant. */
const BubbleContent = React.forwardRef<HTMLDivElement, BubbleContentProps>(
  ({ className, variant = 'default', ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        'rounded-2xl px-3.5 py-2 text-sm leading-relaxed break-words',
        variant !== 'ghost' && 'max-w-[80%]',
        variantClasses[variant],
        className
      )}
      {...props}
    />
  )
);
BubbleContent.displayName = 'BubbleContent';

const BubbleGroup = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => <div ref={ref} className={cn('flex flex-col gap-1', className)} {...props} />
);
BubbleGroup.displayName = 'BubbleGroup';

const BubbleReactions = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('flex items-center gap-1 text-xs', className)} {...props} />
  )
);
BubbleReactions.displayName = 'BubbleReactions';

export { Bubble, BubbleContent, BubbleGroup, BubbleReactions };
