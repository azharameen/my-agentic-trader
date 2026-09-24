import * as React from 'react';
import { cn } from '../../lib/utils';

const Empty = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('flex flex-col items-center justify-center gap-2 text-center px-6 py-10', className)}
      {...props}
    />
  )
);
Empty.displayName = 'Empty';

const EmptyMedia = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('w-12 h-12 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center text-primary mb-1', className)}
      {...props}
    />
  )
);
EmptyMedia.displayName = 'EmptyMedia';

const EmptyTitle = React.forwardRef<HTMLHeadingElement, React.HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <h3 ref={ref} className={cn('text-sm font-semibold text-foreground', className)} {...props} />
  )
);
EmptyTitle.displayName = 'EmptyTitle';

const EmptyDescription = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLParagraphElement>>(
  ({ className, ...props }, ref) => (
    <p ref={ref} className={cn('text-xs text-muted-foreground max-w-xs', className)} {...props} />
  )
);
EmptyDescription.displayName = 'EmptyDescription';

export { Empty, EmptyMedia, EmptyTitle, EmptyDescription };
