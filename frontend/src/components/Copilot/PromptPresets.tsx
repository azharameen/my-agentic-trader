import React from 'react';
import { BarChart3, Globe, Zap, Search, Target, LucideIcon } from 'lucide-react';
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

  return (
    <div className="flex flex-wrap gap-2 pb-2">
      {presets.map((p, i) => {
        const Icon = p.icon;
        return (
          <Button
            key={i}
            variant="outline"
            size="sm"
            onClick={() => onSelectPrompt(p.text)}
            className="h-7 rounded-full text-xs text-muted-foreground hover:text-foreground gap-1.5"
          >
            <Icon className="w-3 h-3 text-primary flex-shrink-0" />
            <span>{p.label}</span>
          </Button>
        );
      })}
    </div>
  );
};
