import React, { useState } from 'react';
import { Clock, CheckCircle2, XCircle, Filter, Microscope } from 'lucide-react';
import { TradeProposal } from '../../types/api';
import { formatINR } from '../../lib/utils';
import { Card, CardContent, CardFooter, CardHeader } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '../ui/tooltip';

interface PendingProposalsProps {
  proposals: TradeProposal[];
  onApprove: (proposalId: string) => void;
  onReject: (proposalId: string) => void;
  onViewDebate: (proposal: TradeProposal) => void;
}

export const PendingProposals: React.FC<PendingProposalsProps> = ({
  proposals,
  onApprove,
  onReject,
  onViewDebate,
}) => {
  const [strategyFilter, setStrategyFilter] = useState<string>('ALL');

  if (proposals.length === 0) {
    return (
      <Card className="p-8 text-center border-dashed">
        <div className="w-12 h-12 rounded-full bg-muted border border-border flex items-center justify-center mx-auto mb-3 text-muted-foreground">
          <Clock className="w-6 h-6" />
        </div>
        <h3 className="text-sm font-semibold text-foreground">No Proposals Awaiting Approval</h3>
        <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
          When the screener and multi-agent qualitative research filter qualify an asymmetric setup, actionable proposals will appear here.
        </p>
      </Card>
    );
  }

  const strategies = Array.from(new Set(proposals.map((p) => p.strategy_name)));
  const filteredProposals =
    strategyFilter === 'ALL'
      ? proposals
      : proposals.filter((p) => p.strategy_name === strategyFilter);

  return (
    <TooltipProvider>
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center space-x-2">
            <h2 className="text-base font-bold text-foreground flex items-center gap-2">
              <span>Action Required: Pending Proposals</span>
              <Badge variant="outline" className="bg-amber-500/10 text-amber-400 border-amber-500/30 font-mono">
                {proposals.length}
              </Badge>
            </h2>
            <span className="text-xs text-muted-foreground hidden md:inline">
              — Pure risk math verified
            </span>
          </div>

          {/* Quick Strategy Filter Pills */}
          <div className="flex items-center space-x-1.5 overflow-x-auto pb-1 sm:pb-0">
            <Button
              variant={strategyFilter === 'ALL' ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => setStrategyFilter('ALL')}
              className="h-7 px-2.5 text-xs font-medium"
            >
              All ({proposals.length})
            </Button>
            {strategies.map((strat) => (
              <Button
                key={strat}
                variant={strategyFilter === strat ? 'secondary' : 'ghost'}
                size="sm"
                onClick={() => setStrategyFilter(strat)}
                className="h-7 px-2.5 text-xs font-mono"
              >
                {strat} ({proposals.filter((p) => p.strategy_name === strat).length})
              </Button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredProposals.map((prop) => (
            <Card
              key={prop.proposal_id}
              className="flex flex-col justify-between shadow-lg hover:border-primary/50 transition-all border border-border"
            >
              <CardHeader className="pb-2">
                {/* Header: Symbol, Strategy, Catalyst */}
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="text-lg font-bold text-foreground font-mono">{prop.symbol}</span>
                      <Badge variant="secondary" className="font-mono text-[10px]">
                        {prop.strategy_name}
                      </Badge>
                    </div>
                    <span className="text-xs text-muted-foreground block mt-0.5">
                      Catalyst: <strong className="text-foreground">{prop.catalyst_type}</strong>
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="text-xs text-muted-foreground block">Risk:Reward</span>
                    <span className="text-sm font-bold text-primary font-mono">
                      {prop.risk_to_reward.toFixed(1)} : 1
                    </span>
                  </div>
                </div>
              </CardHeader>

              <CardContent className="space-y-3 pt-0">
                {/* Thesis Snippet */}
                <div className="bg-muted/50 border border-border/60 rounded-lg p-3 text-xs text-muted-foreground line-clamp-2 leading-relaxed">
                  "{prop.thesis || 'Technical consolidation breakout aligned with momentum and qualitative confirmation.'}"
                </div>

                {/* Price Structure Matrix */}
                <div className="grid grid-cols-4 gap-2 bg-muted/30 border border-border/60 rounded-lg p-2.5 text-center">
                  <div>
                    <span className="text-[10px] text-muted-foreground block">Entry Fill</span>
                    <span className="text-xs font-bold font-mono text-foreground">₹{formatINR(prop.entry_price)}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-muted-foreground block">Hard Stop</span>
                    <span className="text-xs font-bold font-mono text-rose-400">₹{formatINR(prop.hard_stop)}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-muted-foreground block">Target</span>
                    <span className="text-xs font-bold font-mono text-emerald-400">₹{formatINR(prop.target_price)}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-muted-foreground block">Qty (Shares)</span>
                    <span className="text-xs font-bold font-mono text-primary">{prop.quantity}</span>
                  </div>
                </div>
              </CardContent>

              {/* Actions Bar */}
              <CardFooter className="pt-2 border-t border-border flex items-center justify-between gap-2">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onViewDebate(prop)}
                      className="h-8 text-xs font-semibold text-primary hover:text-primary/80 gap-1.5"
                    >
                      <Microscope className="w-3.5 h-3.5" />
                      <span>Agent Debate</span>
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Inspect detailed Bear Critic vs Bull Analyst qualitative reasoning and citations</p>
                  </TooltipContent>
                </Tooltip>

                <div className="flex items-center space-x-2">
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="outline"
                        size="icon"
                        onClick={() => onReject(prop.proposal_id)}
                        className="h-8 w-8 text-rose-400 border-rose-500/30 hover:bg-rose-500/10 hover:text-rose-300"
                      >
                        <XCircle className="w-4 h-4" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>Reject this trade proposal and record audit rationale</p>
                    </TooltipContent>
                  </Tooltip>

                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="default"
                        size="sm"
                        onClick={() => onApprove(prop.proposal_id)}
                        className="h-8 text-xs font-bold bg-emerald-600 hover:bg-emerald-500 text-white gap-1.5 shadow-md shadow-emerald-600/20"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Approve Fill</span>
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>Approve and immediately execute paper trade order at ₹{formatINR(prop.entry_price)}</p>
                    </TooltipContent>
                  </Tooltip>
                </div>
              </CardFooter>
            </Card>
          ))}
        </div>
      </div>
    </TooltipProvider>
  );
};
