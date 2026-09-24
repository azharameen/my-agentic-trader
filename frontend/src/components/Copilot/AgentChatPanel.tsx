import React, { useEffect, useRef, useState } from 'react';
import { Send, Bot, User, Loader2, Trash2, Sparkles, ArrowRight, Wrench } from 'lucide-react';
import { AgentQuestionnaire, ChatMessage, StrategyBasket, StockAllocation } from '../../types/api';
import { Card, CardContent } from '../ui/card';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Message, MessageAvatar, MessageContent, MessageFooter } from '../ui/message';
import { Bubble, BubbleContent } from '../ui/bubble';
import { Marker, MarkerIcon, MarkerContent } from '../ui/marker';
import { Empty, EmptyMedia, EmptyTitle, EmptyDescription } from '../ui/empty';
import {
  MessageScrollerProvider,
  MessageScroller,
  MessageScrollerViewport,
  MessageScrollerContent,
  MessageScrollerItem,
  MessageScrollerButton,
  useAutoScrollOnChange,
} from '../ui/message-scroller';
import { PromptPresets } from './PromptPresets';
import { formatDateTime } from '../../lib/utils';
import { confirmBatchExecutions } from '../../lib/api';
import { AgentQuestionnaireCard } from '../ui/questionnaire';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface AgentChatPanelProps {
  onShowToast?: (msg: string) => void;
  onPortfolioChanged?: () => void;
  initialPrompt?: string;
}

export const AgentChatPanel: React.FC<AgentChatPanelProps> = ({ onShowToast, onPortfolioChanged, initialPrompt }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const lastInitialPrompt = useRef<string>();

  useEffect(() => {
    if (initialPrompt && lastInitialPrompt.current !== initialPrompt) {
      lastInitialPrompt.current = initialPrompt;
      handleSendMessage(initialPrompt);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialPrompt]);

  const handleSendMessage = async (textToSend?: string) => {
    const query = (textToSend || input).trim();
    if (!query || isStreaming) return;

    const userMsgId = `user-${Date.now()}`;
    const agentMsgId = `agent-${Date.now()}`;

    setMessages((prev) => [
      ...prev,
      { id: userMsgId, sender: 'user', text: query, timestamp: new Date().toISOString() },
      { id: agentMsgId, sender: 'agent', text: '', toolCalls: [], timestamp: new Date().toISOString() },
    ]);
    setInput('');
    setIsStreaming(true);

    try {
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: query, thread_id: 'web-session-1' }),
      });
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

      const reader = response.body?.getReader();
      if (!reader) throw new Error('ReadableStream not supported');

      const decoder = new TextDecoder();
      let buffer = '';
      let accumulatedText = '';
      const accumulatedToolCalls: Array<{ name: string; input?: string; output?: string }> = [];

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const dataStr = line.slice(6).trim();
          if (!dataStr) continue;
          try {
            const event = JSON.parse(dataStr);
            if (event.type === 'token') {
              accumulatedText += event.content;
              setMessages((prev) => prev.map((m) => (m.id === agentMsgId ? { ...m, text: accumulatedText } : m)));
            } else if (event.type === 'tool_start') {
              accumulatedToolCalls.push({ name: event.tool, input: event.input });
              setMessages((prev) => prev.map((m) => (m.id === agentMsgId ? { ...m, toolCalls: [...accumulatedToolCalls] } : m)));
            } else if (event.type === 'tool_end') {
              const last = accumulatedToolCalls[accumulatedToolCalls.length - 1];
              if (last && last.name === event.tool) {
                last.output = event.output;
                setMessages((prev) => prev.map((m) => (m.id === agentMsgId ? { ...m, toolCalls: [...accumulatedToolCalls] } : m)));
              }
            } else if (event.type === 'tool_result' && event.structured_type === 'investment_basket') {
              const basket: StrategyBasket = event.data.basket;
              setMessages((prev) => prev.map((m) => (m.id === agentMsgId ? { ...m, basket } : m)));
            } else if (event.type === 'tool_result' && event.structured_type === 'questionnaire') {
              const questionnaire: AgentQuestionnaire = event.data.questionnaire;
              setMessages((prev) => prev.map((m) => (m.id === agentMsgId ? { ...m, questionnaire } : m)));
            } else if (event.type === 'error') {
              accumulatedText += `\n\n[Error: ${event.content}]`;
              setMessages((prev) => prev.map((m) => (m.id === agentMsgId ? { ...m, text: accumulatedText } : m)));
            }
          } catch (err) {
            console.error('Failed to parse SSE line:', line, err);
          }
        }
      }
    } catch (err: any) {
      setMessages((prev) => prev.map((m) => (m.id === agentMsgId ? { ...m, text: `Failed to connect to research agent: ${err.message || 'Unknown error'}` } : m)));
    } finally {
      setIsStreaming(false);
    }
  };

  const handleClearHistory = () => {
    setMessages([]);
  };

  const handleConfirmBasket = async (basket: StrategyBasket, fillPrices: Record<string, number>) => {
    try {
      await confirmBatchExecutions({
        basket_id: basket.basket_id,
        confirmations: basket.allocations.map((a) => ({
          symbol: a.symbol,
          shares: a.shares,
          executed_price: fillPrices[a.symbol] ?? a.suggested_entry_price,
          broker_name: 'External Broker',
        })),
      });
      onShowToast?.('Plan confirmed — positions now tracked in your Stocks tab');
      onPortfolioChanged?.();
    } catch (err: any) {
      onShowToast?.(err.message || 'Failed to confirm plan');
    }
  };

  const handleSubmitQuestion = (questionnaire: AgentQuestionnaire, answer: string) => {
    void handleSendMessage(`${questionnaire.field}: ${answer}`);
  };

  return (
    <MessageScrollerProvider>
      <div className="h-full flex flex-col">
        <div className="flex items-center justify-between px-1 pb-3 shrink-0">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-primary">
              <Bot className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-foreground flex items-center gap-2">
                TrAId Copilot
                <Badge variant="outline" className="text-[10px] bg-primary/10 text-primary border-primary/20">ReAct Agent</Badge>
              </h2>
              <p className="text-[11px] text-muted-foreground">Read/Trigger only — live introspection &amp; research triggers</p>
            </div>
          </div>
          <Button variant="ghost" size="sm" onClick={handleClearHistory} className="text-xs h-8 gap-1.5 text-muted-foreground">
            <Trash2 className="w-3.5 h-3.5" /> Clear
          </Button>
        </div>

        <MessageScroller className="border border-border rounded-lg bg-card/50">
          <MessageScrollerViewport>
            <MessageScrollerContent>
              {messages.length === 0 && (
                <Empty>
                  <EmptyMedia><Bot className="w-6 h-6" /></EmptyMedia>
                  <EmptyTitle>Ask me anything</EmptyTitle>
                  <EmptyDescription>
                    Any symbol, your positions, market regime — or say "build me an investment plan" and I'll ask what I need to know.
                  </EmptyDescription>
                </Empty>
              )}
              {messages.map((msg) => (
                <MessageScrollerItem key={msg.id} messageId={msg.id} scrollAnchor={msg.sender === 'user'}>
                  <AgentMessageRow message={msg} onConfirmBasket={handleConfirmBasket} onSubmitQuestion={handleSubmitQuestion} />
                </MessageScrollerItem>
              ))}
              {isStreaming && (
                <Marker>
                  <MarkerIcon><Loader2 className="w-3.5 h-3.5 animate-spin text-primary" /></MarkerIcon>
                  <MarkerContent>Thinking...</MarkerContent>
                </Marker>
              )}
              <ScrollAnchor dep={[messages, isStreaming]} />
            </MessageScrollerContent>
          </MessageScrollerViewport>
          <MessageScrollerButton />
        </MessageScroller>

        <div className="pt-3 space-y-2.5 shrink-0">
          <PromptPresets onSelectPrompt={(p) => handleSendMessage(p)} />
          <form onSubmit={(e) => { e.preventDefault(); handleSendMessage(); }} className="flex items-center space-x-2">
            <Input
              type="text"
              placeholder="Ask anything, or say 'build me an investment plan'..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={isStreaming}
              className="flex-1 text-xs h-9"
            />
            <Button type="submit" size="sm" disabled={!input.trim() || isStreaming} className="h-9 px-3 font-semibold text-xs gap-1">
              {isStreaming ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <><Send className="w-3.5 h-3.5" /><span>Ask</span></>}
            </Button>
          </form>
        </div>
      </div>
    </MessageScrollerProvider>
  );
};

const ScrollAnchor: React.FC<{ dep: unknown }> = ({ dep }) => {
  useAutoScrollOnChange(dep);
  return null;
};

const AgentMessageRow: React.FC<{
  message: ChatMessage;
  onConfirmBasket: (basket: StrategyBasket, fillPrices: Record<string, number>) => void;
  onSubmitQuestion: (questionnaire: AgentQuestionnaire, answer: string) => void;
}> = ({ message, onConfirmBasket, onSubmitQuestion }) => {
  const isUser = message.sender === 'user';

  return (
    <div className="space-y-2">
      <Message align={isUser ? 'end' : 'start'}>
        <MessageAvatar>
          <div className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 ${isUser ? 'bg-muted border border-border text-muted-foreground' : 'bg-primary/10 border border-primary/20 text-primary'}`}>
            {isUser ? <User className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
          </div>
        </MessageAvatar>
        <MessageContent>
          {!isUser && message.toolCalls && message.toolCalls.length > 0 && (
            <ToolTrace toolCalls={message.toolCalls} />
          )}
          <Bubble align={isUser ? 'end' : 'start'}>
            <BubbleContent variant={isUser ? 'default' : 'secondary'} className="whitespace-pre-wrap font-sans">
              {message.text ? <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.text}</ReactMarkdown> : (message.toolCalls?.length ? '' : '\u00A0')}
            </BubbleContent>
          </Bubble>
          <MessageFooter className={isUser ? 'self-end' : 'self-start'}>
            {formatDateTime(message.timestamp)}
          </MessageFooter>
        </MessageContent>
      </Message>
      {message.basket && (
        <div className="pl-9">
          <BasketCard basket={message.basket} onConfirm={(prices) => onConfirmBasket(message.basket!, prices)} />
        </div>
      )}
      {message.questionnaire && (
        <div className="pl-9">
          <AgentQuestionnaireCard
            questionnaire={message.questionnaire}
            onSubmit={(answer) => onSubmitQuestion(message.questionnaire!, answer)}
          />
        </div>
      )}
    </div>
  );
};

const ToolTrace: React.FC<{ toolCalls: Array<{ name: string; input?: string; output?: string }> }> = ({ toolCalls }) => (
  <div className="flex flex-col gap-1">
    {toolCalls.map((tc, idx) => (
      <Marker key={idx} className="font-mono">
        <MarkerIcon><Wrench className="w-3 h-3 text-primary" /></MarkerIcon>
        <MarkerContent className={tc.output ? '' : 'animate-none'}>
          {tc.output ? `${tc.name} \u2192 done` : `Running ${tc.name}...`}
        </MarkerContent>
      </Marker>
    ))}
  </div>
);

const BasketCard: React.FC<{ basket: StrategyBasket; onConfirm: (fillPrices: Record<string, number>) => void }> = ({ basket, onConfirm }) => {
  const [fillPrices, setFillPrices] = useState<Record<string, number>>(() => {
    const initial: Record<string, number> = {};
    basket.allocations.forEach((a: StockAllocation) => { initial[a.symbol] = a.suggested_entry_price; });
    return initial;
  });
  const [confirmed, setConfirmed] = useState(false);

  return (
    <Card className="border-blue-500/30 bg-blue-950/10 max-w-md">
      <CardContent className="p-4 space-y-3">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-blue-400" />
          <span className="text-sm font-bold">{basket.risk_vibe} plan — ₹{basket.total_capital.toLocaleString()}</span>
        </div>
        <p className="text-xs text-muted-foreground">{basket.overall_thesis}</p>
        <div className="space-y-2">
          {basket.allocations.map((a) => (
            <div key={a.symbol} className="border border-border rounded-lg p-2.5 text-xs space-y-1">
              <div className="flex justify-between font-semibold"><span>{a.symbol} · {a.shares} sh</span><span>₹{a.total_cost.toLocaleString()}</span></div>
              <p className="text-muted-foreground">{a.layman_rationale}</p>
              {!confirmed && (
                <div className="flex items-center gap-2">
                  <label className="text-[10px] text-muted-foreground">Actual fill price:</label>
                  <Input
                    type="number"
                    className="h-7 text-xs w-24"
                    value={fillPrices[a.symbol] ?? a.suggested_entry_price}
                    onChange={(e) => setFillPrices((prev) => ({ ...prev, [a.symbol]: parseFloat(e.target.value) || a.suggested_entry_price }))}
                  />
                </div>
              )}
            </div>
          ))}
        </div>
        {!confirmed ? (
          <Button size="sm" onClick={() => { onConfirm(fillPrices); setConfirmed(true); }} className="w-full">
            Confirm buys <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
          </Button>
        ) : (
          <Badge variant="outline" className="bg-emerald-500/10 text-emerald-400 border-emerald-500/30">Confirmed — check your Stocks tab</Badge>
        )}
      </CardContent>
    </Card>
  );
};

export default AgentChatPanel;
