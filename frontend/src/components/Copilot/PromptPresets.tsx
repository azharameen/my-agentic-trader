import React from 'react';
import { BarChart3, Globe, Zap, Search, Target, ChevronLeft, ChevronRight, LucideIcon } from 'lucide-react';
import { Button } from '../ui/button';

interface PromptPresetsProps {
  onSelectPrompt: (prompt: string) => void;
}

interface PresetItem {
  icon: LucideIcon;
  label: string;
  text: string;
}

export const PromptPresets: React.FC<PromptPresetsProps> = ({ onSelectPrompt }) => {
  const presets: PresetItem[] = [
    { icon: BarChart3, label: "Active Portfolio & Heat", text: "What are our current open paper positions and what is our portfolio heat %?" },
    { icon: Globe, label: "Macro Market Regime", text: "What is the current India VIX, NIFTY 50 EMA trend, and macro regime status?" },
    { icon: Zap, label: "Run Setup Scan", text: "Run a full universe scan across NIFTY 100 for pullback setups and report qualifiers." },
    { icon: Search, label: "Analyze RELIANCE", text: "Run full catalyst analysis and risk check for RELIANCE." },
    { icon: Target, label: "Strategy Performance", text: "How is the trading strategy performing against the NIFTY 100 Buy & Hold benchmark?" },
  ];

  const scrollBy = (direction: number) => {
    document.getElementById('agent-prompt-presets')?.scrollBy({ left: direction * 220, behavior: 'smooth' });
  };

  return (
    <div className="relative -mx-1">
      <button
        type="button"
        aria-label="Scroll suggestions left"
        onClick={() => scrollBy(-1)}
        className="absolute left-0 top-1/2 z-10 flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded-full border border-border bg-card text-muted-foreground shadow-md hover:text-foreground"
      >
        <ChevronLeft className="h-3.5 w-3.5" />
      </button>
      <div
        id="agent-prompt-presets"
        tabIndex={0}
        aria-label="Agent prompt suggestions. Scroll horizontally for more suggestions."
        className="flex gap-2 overflow-x-scroll px-9 pb-2 snap-x snap-mandatory scrollbar-visible"
      >
        {presets.map((p, i) => {
          const Icon = p.icon;
          return (
            <Button
              key={i}
              variant="outline"
              size="sm"
              onClick={() => onSelectPrompt(p.text)}
              className="h-7 shrink-0 snap-start rounded-full text-xs text-muted-foreground hover:text-foreground gap-1.5"
            >
              <Icon className="w-3 h-3 text-primary flex-shrink-0" />
              <span>{p.label}</span>
            </Button>
          );
        })}
      </div>
      <button
        type="button"
        aria-label="Scroll suggestions right"
        onClick={() => scrollBy(1)}
        className="absolute right-0 top-1/2 z-10 flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded-full border border-border bg-card text-muted-foreground shadow-md hover:text-foreground"
      >
        <ChevronRight className="h-3.5 w-3.5" />
      </button>
    </div>
  );
};
