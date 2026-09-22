import React, { useState } from 'react';
import { Bot, User, ChevronDown, ChevronRight, Terminal, Wrench } from 'lucide-react';
import { ChatMessage } from '../../types/api';
import { formatDateTime } from '../../lib/utils';
import { Card } from '../ui/card';

interface MessageItemProps {
  message: ChatMessage;
}

export const MessageItem: React.FC<MessageItemProps> = ({ message }) => {
  const isUser = message.sender === 'user';
  const [showTools, setShowTools] = useState(false);

  return (
    <div className={`flex items-start space-x-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-primary flex-shrink-0 mt-0.5">
          <Bot className="w-4 h-4" />
        </div>
      )}

      <div className={`max-w-2xl space-y-2 ${isUser ? 'items-end' : 'items-start'}`}>
        {/* Tool Call Step Accordion */}
        {!isUser && message.toolCalls && message.toolCalls.length > 0 && (
          <Card className="overflow-hidden text-xs bg-muted/40">
            <button
              onClick={() => setShowTools(!showTools)}
              className="w-full px-3 py-1.5 flex items-center justify-between text-muted-foreground hover:text-foreground transition"
            >
              <div className="flex items-center space-x-1.5">
                <Wrench className="w-3.5 h-3.5 text-primary" />
                <span>Tool Executions ({message.toolCalls.length})</span>
              </div>
              {showTools ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
            </button>

            {showTools && (
              <div className="p-3 bg-background/80 border-t border-border font-mono text-[11px] space-y-2">
                {message.toolCalls.map((tc, idx) => (
                  <div key={idx} className="space-y-1">
                    <div className="flex items-center space-x-1 text-primary">
                      <Terminal className="w-3 h-3" />
                      <span>{tc.name}</span>
                    </div>
                    {tc.input && (
                      <div className="text-muted-foreground pl-4 text-[10px] break-all">
                        Input: {tc.input}
                      </div>
                    )}
                    {tc.output && (
                      <div className="text-emerald-400 pl-4 text-[10px] bg-muted/60 p-1.5 rounded border border-border break-all">
                        Output: {tc.output}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Card>
        )}

        {/* Message Bubble */}
        <div
          className={`p-4 rounded-2xl text-sm leading-relaxed ${
            isUser
              ? 'bg-primary text-primary-foreground rounded-tr-none shadow-md shadow-primary/20 font-medium'
              : 'bg-card border border-border text-card-foreground rounded-tl-none shadow-lg'
          }`}
        >
          <div className="whitespace-pre-wrap font-sans text-xs sm:text-sm">
            {message.text}
          </div>
        </div>

        {/* Timestamp */}
        <div className={`text-[10px] text-muted-foreground px-1 ${isUser ? 'text-right' : 'text-left'}`}>
          {formatDateTime(message.timestamp)}
        </div>
      </div>

      {isUser && (
        <div className="w-8 h-8 rounded-lg bg-muted border border-border flex items-center justify-center text-muted-foreground flex-shrink-0 mt-0.5">
          <User className="w-4 h-4" />
        </div>
      )}
    </div>
  );
};
