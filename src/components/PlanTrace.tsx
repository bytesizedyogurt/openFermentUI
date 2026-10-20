// Postdoc's loop, one line a step (OF-BLD-014 §5.4).
//
// Every line is written by code in postdoc_agent.py from the tool's name, its
// input and what it returned; the model writes none of it. A line opens to
// the exact input the tool was given, so what was searched is checkable, and
// a refused call reads as refused. The first line is the coverage pass
// (OF-BLD-015 §7.1): code sweeping every module for what the question names,
// opening to one line a module.
import { AlertTriangle, CheckCircle2, Database, FileSearch, LayoutGrid, RefreshCw, Repeat, Wrench } from 'lucide-react';
import type { StopReason, TraceStep } from '@/data/types';

const ICON: Record<string, typeof Database> = {
  search_records: Database,
  search_passages: FileSearch,
};

/** Why the loop stopped, in words. */
export const STOPPED_WORDS: Record<StopReason, string> = {
  done: 'answered when it had what it needed',
  rounds: 'stopped at its round limit and answered from what it had',
  calls: 'stopped at its tool-call limit and answered from what it had',
  cost: 'stopped at its cost limit and answered from what it had',
  time: 'stopped at its time limit and answered from what it had',
};

function duration(ms: number): string {
  return ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(1)} s`;
}

function StepLine({ step }: { step: TraceStep }) {
  const Icon =
    step.kind === 'coverage'
      ? step.ok
        ? LayoutGrid
        : AlertTriangle
      : step.kind === 'restart'
      ? Repeat
      : step.kind === 'final'
        ? step.ok
          ? CheckCircle2
          : AlertTriangle
        : !step.ok
          ? AlertTriangle
          : (ICON[step.tool ?? ''] ?? Wrench);
  const tone = step.ok ? 'text-ink-soft' : 'text-signal-warn';
  const line = (
    <span className="flex items-baseline gap-2 min-w-0">
      <Icon size={13} className={`${tone} shrink-0 translate-y-0.5`} aria-hidden />
      <span className="text-body text-ink min-w-0 break-words">{step.summary}</span>
      {(step.kind === 'tool' || step.kind === 'coverage') && <span className="font-num text-caption text-ink-soft shrink-0 ml-auto">{duration(step.ms)}</span>}
    </span>
  );
  const modules = step.kind === 'coverage' ? (step.input?.modules as string[] | undefined) : undefined;
  if (modules) {
    return (
      <li className="py-1" data-testid="trace-step">
        <details>
          <summary className="cursor-pointer list-none">{line}</summary>
          <ul className="mt-1 ml-5 text-caption text-ink-soft" data-testid="trace-coverage">
            {modules.map((m) => (
              <li key={m}>{m}</li>
            ))}
          </ul>
        </details>
      </li>
    );
  }
  if (step.kind !== 'tool' || !step.input) {
    return (
      <li className="py-1" data-testid="trace-step">
        {line}
      </li>
    );
  }
  return (
    <li className="py-1" data-testid="trace-step">
      <details>
        <summary className="cursor-pointer list-none">{line}</summary>
        <pre className="mt-1 ml-5 p-2 rounded bg-surface-1 text-caption font-num overflow-x-auto" data-testid="trace-input">
          {step.tool}
          {' '}
          {JSON.stringify(step.input, null, 2)}
        </pre>
      </details>
    </li>
  );
}

export function PlanTrace({ steps, running }: { steps: TraceStep[]; running: boolean }) {
  if (steps.length === 0 && !running) return null;
  return (
    <section aria-label="What Postdoc did" data-testid="plan-trace">
      <ol className="divide-y divide-line/60">
        {steps.map((s) => (
          <StepLine key={s.n} step={s} />
        ))}
        {running && (
          <li className="py-1 flex items-center gap-2 text-body text-ink-soft">
            <RefreshCw size={13} className="animate-spin shrink-0" aria-hidden />
            {steps.length === 0 ? 'Reading the question…' : 'Working…'}
          </li>
        )}
      </ol>
    </section>
  );
}
