import React, { useState, useRef, useEffect } from 'react';
import {
  Bot,
  Send,
  Trash2,
  Loader2,
  X,
  Minimize2,
  Maximize2,
  MessageSquare,
  Sparkles,
} from 'lucide-react';
import { ChatMessage } from '../../types/api';
import { MessageItem } from './MessageItem';
import { PromptPresets } from './PromptPresets';
import { Card, CardHeader, CardContent, CardFooter } from '../ui/card';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '../ui/tooltip';

interface FloatingCopilotProps {
  isOpen?: boolean;
  onToggle?: () => void;
}

export const FloatingCopilot: React.FC<FloatingCopilotProps> = ({
  isOpen: controlledIsOpen,
  onToggle: controlledOnToggle,
}) => {
  const [internalIsOpen, setInternalIsOpen] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);

  const isOpen = controlledIsOpen !== undefined ? controlledIsOpen : internalIsOpen;
  const toggleOpen = () => {
    if (controlledOnToggle) {
      controlledOnToggle();
    } else {
      setInternalIsOpen((prev) => !prev);
    }
  };

  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      sender: 'agent',
      text: "Hello! I am TrAId's conversational market research assistant.\n\nI can inspect live NIFTY 100 snapshots, explain setup rationale and Bear/Bull debates, report active paper positions, check macro market regime status, or run on-demand graph research for any symbol. How can I help you today?",
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
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isStreaming, isOpen]);

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
      {/* Floating Trigger Button (Bottom Right) */}
      {!isOpen && (
        <div className="fixed bottom-6 right-6 z-50">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                onClick={toggleOpen}
                size="lg"
                className="h-14 w-14 rounded-full shadow-2xl bg-primary text-primary-foreground hover:scale-105 transition-transform flex items-center justify-center relative p-0 group"
              >
                <span className="absolute -top-1 -right-1 flex h-4 w-4">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-4 w-4 bg-emerald-500 border-2 border-background"></span>
                </span>
                <Bot className="w-7 h-7" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="left">
              <p className="font-semibold">TrAId Market Copilot (ReAct Agent)</p>
              <p className="text-[11px] text-muted-foreground">Click to open AI research popup</p>
            </TooltipContent>
          </Tooltip>
        </div>
      )}

      {/* Floating Popup Window */}
      {isOpen && (
        <div
          className={`fixed z-50 transition-all duration-300 shadow-2xl flex flex-col ${
            isExpanded
              ? 'inset-6 sm:inset-10 rounded-xl'
              : 'bottom-6 right-6 w-[92vw] sm:w-[460px] md:w-[500px] h-[600px] max-h-[85vh] rounded-2xl'
          }`}
        >
          <Card className="flex flex-col h-full overflow-hidden border-2 border-primary/20 bg-card/95 backdrop-blur-md shadow-2xl">
            {/* Window Header */}
            <CardHeader className="p-3.5 border-b border-border bg-muted/40 flex flex-row items-center justify-between space-y-0 shrink-0">
              <div className="flex items-center space-x-2.5 min-w-0">
                <div className="w-8 h-8 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-primary shrink-0">
                  <Sparkles className="w-4 h-4" />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center space-x-2">
                    <span className="text-sm font-bold text-foreground truncate">TrAId Copilot</span>
                    <Badge variant="outline" className="text-[10px] py-0 px-1.5 bg-primary/10 text-primary border-primary/30">
                      ReAct
                    </Badge>
                  </div>
                  <p className="text-[11px] text-muted-foreground truncate">Live Market & Setup Analysis</p>
                </div>
              </div>

              <div className="flex items-center space-x-1 shrink-0">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={handleClearHistory}
                      className="h-8 w-8 text-muted-foreground hover:text-foreground"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Clear chat session</p>
                  </TooltipContent>
                </Tooltip>

                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => setIsExpanded(!isExpanded)}
                      className="h-8 w-8 text-muted-foreground hover:text-foreground hidden sm:inline-flex"
                    >
                      {isExpanded ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>{isExpanded ? 'Restore window size' : 'Expand window'}</p>
                  </TooltipContent>
                </Tooltip>

                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={toggleOpen}
                      className="h-8 w-8 text-muted-foreground hover:text-foreground"
                    >
                      <X className="w-4 h-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Minimize popup</p>
                  </TooltipContent>
                </Tooltip>
              </div>
            </CardHeader>

            {/* Window Chat Content */}
            <CardContent className="flex-1 overflow-y-auto p-4 space-y-4">
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
            </CardContent>

            {/* Window Footer Input Area */}
            <CardFooter className="p-3 border-t border-border bg-muted/20 flex flex-col space-y-2.5 shrink-0">
              <PromptPresets onSelectPrompt={(p) => handleSendMessage(p)} />

              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSendMessage();
                }}
                className="flex items-center space-x-2 w-full"
              >
                <Input
                  type="text"
                  placeholder="Ask about symbols, positions, market regime..."
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  disabled={isStreaming}
                  className="flex-1 text-xs h-9"
                />
                <Button
                  type="submit"
                  size="sm"
                  disabled={!input.trim() || isStreaming}
                  className="h-9 px-3 font-semibold text-xs gap-1 shadow-sm"
                >
                  {isStreaming ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <>
                      <Send className="w-3.5 h-3.5" />
                      <span>Ask</span>
                    </>
                  )}
                </Button>
              </form>
            </CardFooter>
          </Card>
        </div>
      )}
    </TooltipProvider>
  );
};
