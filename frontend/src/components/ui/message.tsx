import * as React from 'react';
import { cn } from '../../lib/utils';

type Align = 'start' | 'end';

export interface MessageProps extends React.HTMLAttributes<HTMLDivElement> {
  align?: Align;
}

const Message = React.forwardRef<HTMLDivElement, MessageProps>(
  ({ className, align = 'start', children, ...props }, ref) => (
    <div
      ref={ref}
      data-align={align}
      className={cn('flex w-full items-end gap-2.5', align === 'end' && 'flex-row-reverse', className)}
      {...props}
    >
      {children}
    </div>
  )
);
Message.displayName = 'Message';

const MessageGroup = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => <div ref={ref} className={cn('flex flex-col gap-1.5', className)} {...props} />
);
MessageGroup.displayName = 'MessageGroup';

const MessageAvatar = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('shrink-0', className)} {...props} />
  )
);
MessageAvatar.displayName = 'MessageAvatar';

const MessageContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('flex min-w-0 flex-1 flex-col gap-1', className)} {...props} />
  )
);
MessageContent.displayName = 'MessageContent';

const MessageHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('text-[11px] font-medium text-muted-foreground px-1', className)} {...props} />
  )
);
MessageHeader.displayName = 'MessageHeader';

const MessageFooter = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('flex items-center gap-1.5 text-[10px] text-muted-foreground px-1', className)} {...props} />
  )
);
MessageFooter.displayName = 'MessageFooter';

export { Message, MessageGroup, MessageAvatar, MessageContent, MessageHeader, MessageFooter };
