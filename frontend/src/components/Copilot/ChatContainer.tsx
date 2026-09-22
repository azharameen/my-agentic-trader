import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, Trash2, Loader2 } from 'lucide-react';
import { ChatMessage } from '../../types/api';
import { MessageItem } from './MessageItem';
import { PromptPresets } from './PromptPresets';
import { Card } from '../ui/card';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '../ui/tooltip';

export const ChatContainer: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      sender: 'agent',
      text: "Hello! I am TrAId's conversational research assistant.\n\nI can inspect live NIFTY 100 snapshots, explain setup rationale and Bear/Bull debates, report active paper positions, check macro market regime status, or run on-demand graph research for any symbol. How can I help you today?",
      timestamp: new Date().toISOString(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isStreaming]);

  const handleSendMessage = async (textToSend?: string) => {
    const query = (textToSend || input).trim();
    if (!query || isStreaming) return;

    const userMsgId = `user-${Date.now()}`;
    const agentMsgId = `agent-${Date.now()}`;

    const userMsg: ChatMessage = {
      id: userMsgId,
      sender: 'user',
      text: query,
      timestamp: new Date().toISOString(),
    };

    const initialAgentMsg: ChatMessage = {
      id: agentMsgId,
      sender: 'agent',
      text: '',
      toolCalls: [],
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg, initialAgentMsg]);
    setInput('');
    setIsStreaming(true);

    try {
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: query, thread_id: 'web-session-1' }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('ReadableStream not supported');

      const decoder = new TextDecoder();
      let buffer = '';
      let accumulatedText = '';
      let accumulatedToolCalls: Array<{ name: string; input?: string; output?: string }> = [];

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6).trim();
            if (!dataStr) continue;

            try {
              const event = JSON.parse(dataStr);
              if (event.type === 'token') {
                accumulatedText += event.content;
                setMessages((prev) =>
                  prev.map((m) => (m.id === agentMsgId ? { ...m, text: accumulatedText } : m))
                );
              } else if (event.type === 'tool_start') {
                accumulatedToolCalls.push({ name: event.tool, input: event.input });
                setMessages((prev) =>
                  prev.map((m) => (m.id === agentMsgId ? { ...m, toolCalls: [...accumulatedToolCalls] } : m))
                );
              } else if (event.type === 'tool_end') {
                const last = accumulatedToolCalls[accumulatedToolCalls.length - 1];
                if (last && last.name === event.tool) {
                  last.output = event.output;
                  setMessages((prev) =>
                    prev.map((m) => (m.id === agentMsgId ? { ...m, toolCalls: [...accumulatedToolCalls] } : m))
                  );
                }
              } else if (event.type === 'error') {
                accumulatedText += `\n\n[Error: ${event.content}]`;
                setMessages((prev) =>
                  prev.map((m) => (m.id === agentMsgId ? { ...m, text: accumulatedText } : m))
                );
              }
            } catch (err) {
              console.error('Failed to parse SSE line:', line, err);
            }
          }
        }
      }
    } catch (err: any) {
      console.error('Chat error:', err);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === agentMsgId
            ? { ...m, text: `Failed to connect to research agent: ${err.message || 'Unknown error'}` }
            : m
        )
      );
    } finally {
      setIsStreaming(false);
    }
  };

  const handleClearHistory = () => {
    setMessages([
      {
        id: 'welcome',
        sender: 'agent',
        text: "Session cleared. What market research can I help you analyze?",
        timestamp: new Date().toISOString(),
      },
    ]);
  };

  return (
    <TooltipProvider>
      <div className="h-[calc(100vh-140px)] flex flex-col space-y-3">
        {/* Header Info Banner */}
        <div className="flex items-center justify-between px-1">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-primary">
              <Bot className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-foreground flex items-center gap-2">
                <span>TrAId Conversational Market Copilot</span>
                <Badge variant="outline" className="text-[10px] bg-primary/10 text-primary border-primary/20">
                  ReAct Agent
                </Badge>
              </h2>
              <p className="text-xs text-muted-foreground">
                Read/Trigger only (ADR-004) — live database introspection & symbol research triggers
              </p>
            </div>
          </div>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                onClick={handleClearHistory}
                className="text-xs text-muted-foreground hover:text-foreground gap-1.5 h-8"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Clear Chat</span>
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>Clear current conversation history</p>
            </TooltipContent>
          </Tooltip>
        </div>

        {/* Main Chat Log Box */}
        <Card className="flex-1 flex flex-col shadow-xl overflow-hidden">
          {/* Messages Stream Area */}
          <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
            {messages.map((msg) => (
              <MessageItem key={msg.id} message={msg} />
            ))}

            {isStreaming && (
              <div className="flex items-center space-x-2 text-xs text-muted-foreground animate-pulse pl-11">
                <Loader2 className="w-3.5 h-3.5 animate-spin text-primary" />
                <span>Synthesizing agent research thoughts...</span>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input Footer with Presets */}
          <div className="p-4 border-t border-border bg-card/50 space-y-3">
            <PromptPresets onSelectPrompt={(p) => handleSendMessage(p)} />

            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendMessage();
              }}
              className="flex items-center space-x-2"
            >
              <Input
                type="text"
                placeholder="Ask Copilot about any symbol, position, macro regime, or run scans..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={isStreaming}
                className="flex-1 text-xs sm:text-sm h-10"
              />
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    type="submit"
                    disabled={!input.trim() || isStreaming}
                    className="h-10 px-4 font-semibold text-xs gap-1.5 shadow-md shadow-primary/20"
                  >
                    {isStreaming ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <>
                        <Send className="w-4 h-4" />
                        <span className="hidden sm:inline">Ask</span>
                      </>
                    )}
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Send prompt to ReAct market research agent</p>
                </TooltipContent>
              </Tooltip>
            </form>
          </div>
        </Card>
      </div>
    </TooltipProvider>
  );
};
