import React, { useMemo, useState } from 'react';
import { Check, ChevronLeft, ChevronRight } from 'lucide-react';
import { cn } from '../../lib/utils';
import { Button } from './button';
import { Input } from './input';
import { AgentQuestionnaire } from '../../types/api';

interface AgentQuestionnaireProps {
  questionnaire: AgentQuestionnaire;
  onSubmit: (answer: string) => void;
}

export const AgentQuestionnaireCard: React.FC<AgentQuestionnaireProps> = ({ questionnaire, onSubmit }) => {
  const [selected, setSelected] = useState('');
  const [custom, setCustom] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const canSubmit = Boolean(selected || custom.trim());
  const answer = custom.trim() || selected;

  const progressLabel = useMemo(() => questionnaire.required ? 'Required question' : 'Optional question', [questionnaire.required]);

  return (
    <div className="mt-2 max-w-md rounded-xl border border-primary/25 bg-primary/5 p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-[10px] font-medium uppercase tracking-wider text-primary">Agent questionnaire</span>
        <span className="text-[10px] text-muted-foreground">{progressLabel}</span>
      </div>
      <fieldset disabled={submitted} className="space-y-3">
        <legend className="text-sm font-semibold text-foreground">{questionnaire.question}</legend>
        <p className="text-xs text-muted-foreground">{questionnaire.description}</p>
        <div className="space-y-2">
          {questionnaire.choices.map((choice, index) => {
            const active = selected === choice.value;
            return (
              <button
                key={choice.value}
                type="button"
                onClick={() => { setSelected(choice.value); setCustom(''); }}
                className={cn(
                  'flex w-full items-center gap-3 rounded-lg border px-3 py-2 text-left transition-colors',
                  active ? 'border-primary bg-primary/10' : 'border-border bg-background/50 hover:bg-accent'
                )}
              >
                <span className={cn('flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-[10px] font-semibold', active ? 'border-primary bg-primary text-primary-foreground' : 'border-border text-muted-foreground')}>
                  {active ? <Check className="h-3.5 w-3.5" /> : String.fromCharCode(65 + index)}
                </span>
                <span className="min-w-0">
                  <span className="block text-xs font-medium">{choice.label}</span>
                  {choice.description && <span className="block text-[11px] text-muted-foreground">{choice.description}</span>}
                </span>
              </button>
            );
          })}
          <Input
            aria-label="Your own answer"
            placeholder="Or write your own answer..."
            value={custom}
            onChange={(event) => { setCustom(event.target.value); setSelected(''); }}
            className="h-9 text-xs"
          />
        </div>
      </fieldset>
      <div className="mt-4 flex items-center justify-between">
        <div className="flex gap-1 text-muted-foreground" aria-hidden="true">
          <ChevronLeft className="h-3.5 w-3.5 opacity-40" />
          <ChevronRight className="h-3.5 w-3.5 opacity-40" />
        </div>
        <Button size="sm" disabled={!canSubmit || submitted} onClick={() => { setSubmitted(true); onSubmit(answer); }}>
          {submitted ? 'Answer sent' : 'Continue'}
          {!submitted && <ChevronRight className="ml-1.5 h-3.5 w-3.5" />}
        </Button>
      </div>
    </div>
  );
};
