import * as React from 'react';
import { cn } from '../../lib/utils';

const Marker = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        'flex items-center gap-2 rounded-full border border-border bg-muted/50 px-3 py-1.5 text-xs text-muted-foreground w-fit',
        className
      )}
      {...props}
    />
  )
);
Marker.displayName = 'Marker';

const MarkerIcon = React.forwardRef<HTMLSpanElement, React.HTMLAttributes<HTMLSpanElement>>(
  ({ className, ...props }, ref) => (
    <span ref={ref} className={cn('flex items-center justify-center shrink-0', className)} {...props} />
  )
);
MarkerIcon.displayName = 'MarkerIcon';

const MarkerContent = React.forwardRef<HTMLSpanElement, React.HTMLAttributes<HTMLSpanElement>>(
  ({ className, ...props }, ref) => <span ref={ref} className={cn('shimmer-text', className)} {...props} />
);
MarkerContent.displayName = 'MarkerContent';

export { Marker, MarkerIcon, MarkerContent };
