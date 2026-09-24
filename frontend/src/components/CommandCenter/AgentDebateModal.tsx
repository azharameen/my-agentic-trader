import React from 'react';
import { CheckCircle, ShieldAlert, Sparkles, Quote, Microscope } from 'lucide-react';
import { TradeProposal } from '../../types/api';
import { formatINR } from '../../lib/utils';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '../ui/tooltip';

interface AgentDebateModalProps {
  proposal: TradeProposal | null;
  onClose: () => void;
  onApprove: (proposalId: string) => void;
  onReject: (proposalId: string) => void;
}

export const AgentDebateModal: React.FC<AgentDebateModalProps> = ({
  proposal,
  onClose,
  onApprove,
  onReject,
}) => {
  if (!proposal) return null;

  const debate = proposal.debate;
  const verdict = debate?.research_verdict;
  const catalyst = debate?.catalyst_assessment;

  return (
    <TooltipProvider>
      <Dialog open={!!proposal} onOpenChange={(open) => !open && onClose()}>
        <DialogContent className="max-w-3xl max-h-[90vh] flex flex-col p-0 gap-0 overflow-hidden">
          {/* Modal Header */}
          <DialogHeader className="px-6 py-4 border-b border-border bg-muted/30">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center font-bold">
                <Microscope className="w-4 h-4" />
              </div>
              <div>
                <DialogTitle className="text-lg font-bold flex items-center gap-2">
                  Qualitative Agent Debate: <span className="text-primary">{proposal.symbol}</span>
                </DialogTitle>
                <DialogDescription className="text-xs text-muted-foreground mt-0.5">
                  Strategy: {proposal.strategy_name} | Entry: ₹{formatINR(proposal.entry_price)} | Target: ₹{formatINR(proposal.target_price)}
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>

          {/* Modal Content Scrollable */}
          <div className="p-6 overflow-y-auto space-y-6 flex-1 text-sm">
            {/* Synthesizer Consensus Verdict Banner */}
            <div className="bg-primary/5 border border-primary/20 rounded-xl p-4">
              <div className="flex items-center space-x-2 text-primary font-semibold mb-1">
                <Sparkles className="w-4 h-4" />
                <span>Synthesizer Consensus Summary</span>
              </div>
              <p className="text-foreground text-sm leading-relaxed">
                {verdict?.thesis_summary || proposal.thesis || "Setup demonstrates positive risk-reward asymmetry aligned with technical structure."}
              </p>
              {verdict?.confidence_score !== undefined && (
                <div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground font-mono">
                  <span>Confidence Score:</span>
                  <div className="w-24 h-2 bg-muted rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary rounded-full"
                      style={{ width: `${Math.min(100, Math.round(verdict.confidence_score * 100))}%` }}
                    />
                  </div>
                  <span className="text-foreground font-bold">{(verdict.confidence_score * 100).toFixed(0)}%</span>
                </div>
              )}
            </div>

            {/* Side-by-Side Debate Grid: Bear Critic vs Bull Analyst */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Bear Critic Objections */}
              <div className="bg-rose-500/5 border border-rose-500/20 rounded-xl p-4 space-y-3">
                <div className="flex items-center space-x-2 text-rose-400 font-semibold border-b border-rose-500/10 pb-2">
                  <ShieldAlert className="w-4 h-4" />
                  <span>Bear Critic Counter-Arguments</span>
                </div>
                {verdict?.bear_objections && verdict.bear_objections.length > 0 ? (
                  <ul className="space-y-2">
                    {verdict.bear_objections.map((obj, i) => (
                      <li key={i} className="flex items-start space-x-2 text-muted-foreground text-xs leading-normal">
                        <span className="text-rose-400 mt-0.5">•</span>
                        <span>{obj}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-muted-foreground italic">No critical macro or structural objections raised by Bear Critic.</p>
                )}
              </div>

              {/* Bull Analyst Thesis */}
              <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-xl p-4 space-y-3">
                <div className="flex items-center space-x-2 text-emerald-400 font-semibold border-b border-emerald-500/10 pb-2">
                  <CheckCircle className="w-4 h-4" />
                  <span>Bull Analyst Catalysts</span>
                </div>
                {verdict?.bull_catalysts && verdict.bull_catalysts.length > 0 ? (
                  <ul className="space-y-2">
                    {verdict.bull_catalysts.map((cat, i) => (
                      <li key={i} className="flex items-start space-x-2 text-muted-foreground text-xs leading-normal">
                        <span className="text-emerald-400 mt-0.5">•</span>
                        <span>{cat}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-muted-foreground italic">
                    {catalyst?.thesis_rationale || "Positive price action and technical setup aligned with momentum."}
                  </p>
                )}
              </div>
            </div>

            {/* Citations & Evidence Sources */}
            {debate?.citations && debate.citations.length > 0 && (
              <div className="bg-muted/40 border border-border rounded-xl p-4">
                <div className="flex items-center space-x-2 text-muted-foreground font-semibold mb-2 text-xs">
                  <Quote className="w-3.5 h-3.5" />
                  <span>Verified Evidence Citations</span>
                </div>
                <ul className="space-y-1.5 text-xs">
                  {debate.citations.map((cite, i) => (
                    <li key={i} className="text-muted-foreground font-mono text-[11px] bg-background/50 px-2.5 py-1.5 rounded border border-border">
                      {cite}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Deterministic Price & Risk Structure */}
            <div className="bg-muted/40 border border-border rounded-xl p-4 grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
              <div>
                <span className="text-[11px] text-muted-foreground block">Entry Fill</span>
                <span className="text-sm font-bold font-mono text-foreground">₹{formatINR(proposal.entry_price)}</span>
              </div>
              <div>
                <span className="text-[11px] text-muted-foreground block">Hard Stop (Exit)</span>
                <span className="text-sm font-bold font-mono text-rose-400">₹{formatINR(proposal.hard_stop)}</span>
              </div>
              <div>
                <span className="text-[11px] text-muted-foreground block">Target (Profit)</span>
                <span className="text-sm font-bold font-mono text-emerald-400">₹{formatINR(proposal.target_price)}</span>
              </div>
              <div>
                <span className="text-[11px] text-muted-foreground block">Risk:Reward</span>
                <span className="text-sm font-bold font-mono text-primary">{proposal.risk_to_reward.toFixed(1)}R</span>
              </div>
            </div>
          </div>

          {/* Modal Footer Actions */}
          <div className="px-6 py-4 border-t border-border bg-muted/30 flex items-center justify-between">
            <div className="text-xs text-muted-foreground">
              Quantity: <strong className="text-foreground font-mono">{proposal.quantity} shares</strong> | Total Risk: <strong className="text-rose-400 font-mono">₹{formatINR(proposal.risk_amount)}</strong>
            </div>
            <div className="flex items-center space-x-3">
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      onReject(proposal.proposal_id);
                      onClose();
                    }}
                    className="text-xs font-semibold text-rose-400 border-rose-500/30 hover:bg-rose-500/10 hover:text-rose-300"
                  >
                    Reject Proposal
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Decline this setup proposal and record the rejection in PostgreSQL audit log</p>
                </TooltipContent>
              </Tooltip>

              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="default"
                    size="sm"
                    onClick={() => {
                      onApprove(proposal.proposal_id);
                      onClose();
                    }}
                    className="text-xs font-bold bg-emerald-600 hover:bg-emerald-500 text-white gap-1.5 shadow-lg shadow-emerald-600/20"
                  >
                    <CheckCircle className="w-4 h-4" />
                    <span>Approve & Execute Paper Fill</span>
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Execute paper trade entry at ₹{formatINR(proposal.entry_price)} and activate live monitor</p>
                </TooltipContent>
              </Tooltip>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </TooltipProvider>
  );
};
