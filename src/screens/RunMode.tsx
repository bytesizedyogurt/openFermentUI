// Run Mode (OF-DES-001 §8.12). Bench execution: one step at a time,
// glove-tolerant, timed, and logged. Full-screen takeover — App renders this
// without the shell.
//
// Explicit responsive target: 810px tablet portrait at arm's length. Touch
// targets ≥ 44px, step text on `ink` (not ink-soft) for ≥ 7:1 contrast, and no
// hover-dependent affordances anywhere on this screen.
import { useEffect, useMemo, useRef, useState } from 'react';
import {
  ArrowLeft,
  ArrowRight,
  Check,
  ChevronsLeft,
  ChevronsRight,
  Clock,
  Download,
  ListChecks,
  Pause,
  Play,
  Plus,
  SkipForward,
  StickyNote,
  X,
} from 'lucide-react';
import { useStore } from '@/store';
import { navigate } from '@/router';
import type { Step } from '@/data/types';
import { renderStepText, batchLabel, scaleMaterials } from '@/engine/scale';
import { fmt } from '@/engine/units';
import { exportText } from '@/lib/csv';
import { Button, Modal, cx, EmptyState, Callout } from '@/components/ui';
import { CitationChip } from '@/components/Chip';

const SKIP_REASONS = [
  'Not applicable to this batch',
  'Equipment unavailable',
  'Already performed',
  'Deviation — see note',
];

function mmss(sec: number): string {
  const s = Math.max(0, Math.round(sec));
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
}

function elapsedLabel(ms: number): string {
  const s = Math.floor(ms / 1000);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  return h > 0 ? `${h}h ${String(m).padStart(2, '0')}m` : `${m}m ${String(s % 60).padStart(2, '0')}s`;
}

/** Ring countdown — the timer affordance for a gloved hand at arm's length. */
function TimerRing({ remaining, total }: { remaining: number; total: number }) {
  const r = 42;
  const circumference = 2 * Math.PI * r;
  const frac = total > 0 ? remaining / total : 0;
  return (
    <svg width="104" height="104" viewBox="0 0 104 104" aria-hidden>
      <circle cx="52" cy="52" r={r} fill="none" stroke="rgb(var(--line))" strokeWidth="7" />
      <circle
        cx="52"
        cy="52"
        r={r}
        fill="none"
        stroke={remaining <= 0 ? 'rgb(var(--accent))' : 'rgb(var(--signal-info))'}
        strokeWidth="7"
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={circumference * (1 - frac)}
        transform="rotate(-90 52 52)"
        style={{ transition: 'stroke-dashoffset 240ms linear' }}
      />
      <text
        x="52"
        y="57"
        textAnchor="middle"
        className="font-num"
        fontSize="20"
        fill="rgb(var(--ink))"
      >
        {mmss(remaining)}
      </text>
    </svg>
  );
}

export default function RunMode({ protocolId, runId }: { protocolId: string; runId: string }) {
  const run = useStore((s) => s.runs[runId]);
  const protocol = useStore((s) => s.protocols.find((p) => p.id === protocolId));
  const setRunStep = useStore((s) => s.setRunStep);
  const completeStep = useStore((s) => s.completeStep);
  const skipStep = useStore((s) => s.skipStep);
  const toggleCheck = useStore((s) => s.toggleCheck);
  const addDeviation = useStore((s) => s.addDeviation);
  const addTimer = useStore((s) => s.addTimer);
  const toggleTimer = useStore((s) => s.toggleTimer);
  const extendTimer = useStore((s) => s.extendTimer);
  const dismissTimer = useStore((s) => s.dismissTimer);
  const finishRun = useStore((s) => s.finishRun);
  const startRun = useStore((s) => s.startRun);
  const toast = useStore((s) => s.toast);

  const [now, setNow] = useState(Date.now());
  const [stepsOpen, setStepsOpen] = useState(false);
  const [noteOpen, setNoteOpen] = useState(false);
  const [noteText, setNoteText] = useState('');
  const [skipOpen, setSkipOpen] = useState(false);
  const [exitOpen, setExitOpen] = useState(false);
  const [summary, setSummary] = useState(false);
  const [announce, setAnnounce] = useState('');
  const noteRef = useRef<HTMLTextAreaElement>(null);

  const version = protocol?.versions.find((v) => v.version === run?.version);
  const steps = version?.steps ?? [];
  const step: Step | undefined = steps[run?.currentStep ?? 0];

  // Session clock, ticked once a second (the store drives timer countdown).
  useEffect(() => {
    const t = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(t);
  }, []);

  // Announce timer completion for screen readers (§6.6).
  const timers = run?.timers ?? [];
  const doneTimerIds = timers.filter((t) => t.remainingSec <= 0).map((t) => t.id).join(',');
  useEffect(() => {
    if (!doneTimerIds) return;
    const done = timers.filter((t) => t.remainingSec <= 0);
    if (done.length) setAnnounce(`Timer complete: ${done.map((t) => t.label).join(', ')}`);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [doneTimerIds]);

  const completedCount = Object.keys(run?.completed ?? {}).length;
  const skippedCount = Object.keys(run?.skipped ?? {}).length;
  const runningTimers = timers.filter((t) => t.running && t.remainingSec > 0);
  const allResolved = steps.length > 0 && steps.every((s) => run?.completed[s.id] || run?.skipped[s.id]);

  const stepTimer = step ? timers.find((t) => t.stepId === step.id) : undefined;

  const advance = (delta: number) => {
    if (!run) return;
    setRunStep(runId, Math.max(0, Math.min(steps.length - 1, run.currentStep + delta)));
  };

  const markComplete = () => {
    if (!run || !step) return;
    completeStep(runId, step.id);
    if (run.currentStep < steps.length - 1) advance(1);
    else setSummary(true);
  };

  const startStepTimer = () => {
    if (!run || !step?.timerSec) return;
    if (stepTimer) {
      toggleTimer(runId, stepTimer.id);
      return;
    }
    addTimer(runId, {
      id: `${runId}-${step.id}`,
      stepId: step.id,
      label: step.timerLabel ?? `Step ${run.currentStep + 1}`,
      totalSec: step.timerSec,
    });
  };

  // Bench keyboard vocabulary (Appendix A). Capture phase so single letters
  // never leak into the app's global g-then-rail navigation.
  useEffect(() => {
    if (summary) return;
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement;
      if (el?.tagName === 'INPUT' || el?.tagName === 'TEXTAREA' || el?.isContentEditable) return;
      if (noteOpen || skipOpen || exitOpen) return;
      if (e.key === ' ') {
        e.preventDefault();
        e.stopPropagation();
        markComplete();
      } else if (e.key === 't') {
        e.preventDefault();
        e.stopPropagation();
        startStepTimer();
      } else if (e.key === 'n') {
        e.preventDefault();
        e.stopPropagation();
        setNoteOpen(true);
        setTimeout(() => noteRef.current?.focus(), 30);
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        e.stopPropagation();
        advance(-1);
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        e.stopPropagation();
        advance(1);
      }
    };
    window.addEventListener('keydown', onKey, true);
    return () => window.removeEventListener('keydown', onKey, true);
  });

  const stepLog = useMemo(() => {
    if (!run || !version) return [];
    const perStepEstimate = version.estMinutes.total / Math.max(1, steps.length);
    const times = steps
      .map((s) => ({ id: s.id, at: run.completed[s.id] }))
      .filter((x) => x.at) as { id: string; at: number }[];
    times.sort((a, b) => a.at - b.at);
    return times.map((t, i) => ({
      stepId: t.id,
      index: steps.findIndex((s) => s.id === t.id),
      at: t.at,
      durationMin: (t.at - (i === 0 ? run.startedAt : times[i - 1].at)) / 60000,
      estimateMin: perStepEstimate,
    }));
  }, [run, version, steps]);

  if (!protocol || !version) {
    return (
      <div className="p-8">
        <EmptyState
          title="Protocol not found"
          body={`No protocol with id ${protocolId} exists in this session.`}
          action={<Button onClick={() => navigate('/protocols')}>Back to protocols</Button>}
        />
      </div>
    );
  }

  if (!run) {
    return (
      <div className="p-8">
        <EmptyState
          title="This run is no longer active"
          body="Run state lives in memory for the session and does not survive a page refresh — that is a stated constraint of this simulation, and it is why every run offers a text-log export before you leave it."
          action={
            <div className="flex gap-2">
              <Button
                variant="primary"
                onClick={() => {
                  const id = startRun(protocolId, protocol.currentVersion, 1);
                  navigate(`/protocols/${protocolId}/run/${id}`);
                }}
              >
                Start a fresh run
              </Button>
              <Button onClick={() => navigate(`/protocols/${protocolId}`)}>Open the protocol</Button>
            </div>
          }
        />
      </div>
    );
  }

  // ── Run summary ──────────────────────────────────────────────────────
  if (summary) {
    const totalMin = (Date.now() - run.startedAt) / 60000;
    const textLog = [
      `${protocol.title} — run log`,
      `Version ${version.version} · ${batchLabel(version, run.scale)}`,
      `Started ${new Date(run.startedAt).toLocaleString()} · duration ${elapsedLabel(Date.now() - run.startedAt)}`,
      '',
      '# openFerment export — corpus OF-COR-001 v1.0',
      '# Protocol content is real: drawn from the catalogued literature and standard bench practice.',
      '# Amounts are computed by scaling the base batch, not measured at this scale.',
      '# Timings below are wall-clock from a walkthrough in the app, not a record of bench work.',
      '',
      'STEPS',
      ...steps.map((s, i) => {
        const done = run.completed[s.id];
        const skipped = run.skipped[s.id];
        const state = done ? `completed ${new Date(done).toLocaleTimeString()}` : skipped ? `SKIPPED — ${skipped}` : 'not reached';
        return `${String(i + 1).padStart(2, ' ')}. [${done ? 'x' : ' '}] ${renderStepText(s, version, run.scale)}\n      ${state}`;
      }),
      '',
      'DEVIATIONS',
      ...(run.deviations.length
        ? run.deviations.map((d) => `  ${d.at} (step ${steps.findIndex((s) => s.id === d.stepId) + 1}): ${d.text}`)
        : ['  none recorded']),
      '',
      'MATERIALS AT SCALE',
      ...scaleMaterials(version, run.scale).map(
        (m) => `  ${m.name}: ${fmt(m.scaledAmount)} ${m.unit}${m.scales ? '' : ' (fixed)'}`,
      ),
    ].join('\n');

    return (
      <div className="h-full overflow-y-auto bg-surface-0">
        <div className="max-w-[860px] mx-auto p-6">
          <div className="mb-5">
            <div className="text-caption uppercase tracking-wide text-ink-soft">Run complete</div>
            <h1 className="font-serif text-page-title font-semibold">{protocol.title}</h1>
            <div className="text-body text-ink-soft mt-1">
              v{version.version} · {batchLabel(version, run.scale)} ·{' '}
              <span className="font-num">{elapsedLabel(Date.now() - run.startedAt)}</span> elapsed
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
            {[
              { label: 'Steps completed', value: `${completedCount}/${steps.length}` },
              { label: 'Skipped', value: String(skippedCount) },
              { label: 'Deviations', value: String(run.deviations.length) },
              {
                label: 'vs. estimate',
                value: `${totalMin > version.estMinutes.total ? '+' : ''}${Math.round(totalMin - version.estMinutes.total)} min`,
              },
            ].map((t) => (
              <div key={t.label} className="card p-3">
                <div className="text-caption uppercase tracking-wide text-ink-soft">{t.label}</div>
                <div className="font-num text-section-title">{t.value}</div>
              </div>
            ))}
          </div>

          <div className="card p-4 mb-4">
            <h2 className="font-serif text-section-title font-semibold mb-2">Step log</h2>
            <table className="w-full text-body">
              <thead>
                <tr className="border-b border-line text-caption text-ink-soft">
                  <th className="text-left py-1.5">#</th>
                  <th className="text-left">Step</th>
                  <th className="text-right">Took</th>
                  <th className="text-right">Est.</th>
                </tr>
              </thead>
              <tbody>
                {steps.map((s, i) => {
                  const log = stepLog.find((l) => l.stepId === s.id);
                  const skipped = run.skipped[s.id];
                  return (
                    <tr key={s.id} className="border-b border-line/60">
                      <td className="py-1.5 font-num text-ink-soft">{i + 1}</td>
                      <td className="pr-3">
                        <span className={cx(skipped && 'text-ink-soft line-through')}>
                          {renderStepText(s, version, run.scale).slice(0, 96)}
                          {renderStepText(s, version, run.scale).length > 96 ? '…' : ''}
                        </span>
                        {skipped && (
                          <span className="ml-2 chip text-signal-warn border-signal-warn/40">
                            skipped — {skipped}
                          </span>
                        )}
                      </td>
                      <td className="text-right font-num">
                        {log ? `${log.durationMin.toFixed(1)} min` : '—'}
                      </td>
                      <td className="text-right font-num text-ink-soft">
                        {log ? `${log.estimateMin.toFixed(1)}` : '—'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="card p-4 mb-4">
            <h2 className="font-serif text-section-title font-semibold mb-2">
              Deviations{' '}
              <span className="font-sans text-caption text-ink-soft font-normal">
                recorded verbatim
              </span>
            </h2>
            {run.deviations.length === 0 ? (
              <p className="text-body text-ink-soft">None recorded during this run.</p>
            ) : (
              <ul className="space-y-2">
                {run.deviations.map((d, i) => (
                  <li key={i} className="tick tick-user">
                    <div className="text-caption text-ink-soft font-num">
                      {d.at} · step {steps.findIndex((s) => s.id === d.stepId) + 1}
                    </div>
                    <div className="text-body">{d.text}</div>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="card p-4 mb-5">
            <h2 className="font-serif text-section-title font-semibold mb-2">Materials confirmation</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1">
              {scaleMaterials(version, run.scale).map((m) => (
                <div key={m.name} className="flex justify-between text-body border-b border-line/50 py-1">
                  <span>
                    {m.name}
                    {!m.scales && <span className="text-caption text-ink-soft"> (fixed)</span>}
                  </span>
                  <span className="font-num">
                    {fmt(m.scaledAmount)} {m.unit}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <Button
              variant="primary"
              onClick={() => {
                finishRun(runId);
                toast({ text: 'Run summary saved to this protocol’s history', kind: 'success' });
                navigate(`/protocols/${protocolId}`);
              }}
            >
              <Check size={15} /> Save to run history
            </Button>
            <Button onClick={() => exportText(`run-${protocol.id}-${runId}.txt`, textLog)}>
              <Download size={15} /> Export as text log
            </Button>
            <Button onClick={() => setSummary(false)}>Back to steps</Button>
          </div>
        </div>
      </div>
    );
  }

  // ── Active run ───────────────────────────────────────────────────────
  const stepText = step ? renderStepText(step, version, run.scale) : '';
  const isDone = step ? Boolean(run.completed[step.id]) : false;
  const isSkipped = step ? Boolean(run.skipped[step.id]) : false;
  const outOfOrder =
    step && !isDone && steps.slice(run.currentStep + 1).some((s) => run.completed[s.id]);

  return (
    <div className="h-full flex flex-col bg-surface-0">
      <div className="sr-only" aria-live="polite">
        {announce}
      </div>

      {/* Top strip */}
      <header className="shrink-0 border-b border-line bg-surface-1 px-4 py-2.5 flex items-center gap-3">
        <button
          className="btn"
          style={{ minHeight: 44 }}
          onClick={() => setStepsOpen((o) => !o)}
          aria-label="Toggle step list"
        >
          {stepsOpen ? <ChevronsLeft size={16} /> : <ChevronsRight size={16} />}
          <ListChecks size={16} />
        </button>
        <div className="min-w-0 flex-1">
          <div className="font-serif text-section-title font-semibold truncate">{protocol.title}</div>
          <div className="text-caption text-ink-soft font-num">
            v{version.version} · {batchLabel(version, run.scale)} ·{' '}
            {elapsedLabel(now - run.startedAt)} elapsed
          </div>
        </div>
        <div className="hidden sm:flex items-center gap-2 shrink-0">
          <div className="w-40 h-2 rounded-full bg-ink-soft/15 overflow-hidden">
            <div
              className="h-full bg-accent rounded-full transition-[width]"
              style={{ width: `${((completedCount + skippedCount) / steps.length) * 100}%` }}
            />
          </div>
          <span className="font-num text-caption text-ink-soft">
            {completedCount + skippedCount}/{steps.length}
          </span>
        </div>
        <Button style={{ minHeight: 44 }} onClick={() => setExitOpen(true)}>
          <X size={16} /> Exit
        </Button>
      </header>

      <div className="flex-1 flex min-h-0">
        {/* Step list */}
        {stepsOpen && (
          <nav className="w-[300px] shrink-0 border-r border-line bg-surface-1 overflow-y-auto">
            {steps.map((s, i) => {
              const done = run.completed[s.id];
              const skip = run.skipped[s.id];
              return (
                <button
                  key={s.id}
                  onClick={() => setRunStep(runId, i)}
                  className={cx(
                    'w-full text-left px-3 py-2.5 border-b border-line/60 flex gap-2.5',
                    i === run.currentStep ? 'bg-accent-wash' : 'hover:bg-ink-soft/[0.05]',
                  )}
                  style={{ minHeight: 44 }}
                >
                  <span
                    className={cx(
                      'shrink-0 w-6 h-6 rounded-full grid place-items-center text-caption font-num',
                      done
                        ? 'bg-accent text-surface-1'
                        : skip
                          ? 'bg-signal-warn/20 text-signal-warn'
                          : 'border border-line text-ink-soft',
                    )}
                  >
                    {done ? <Check size={13} /> : i + 1}
                  </span>
                  <span className="text-body leading-snug">
                    {renderStepText(s, version, run.scale).slice(0, 70)}
                    {renderStepText(s, version, run.scale).length > 70 ? '…' : ''}
                  </span>
                </button>
              );
            })}
          </nav>
        )}

        {/* Current step */}
        <main className="flex-1 overflow-y-auto p-5 sm:p-8">
          <div className="max-w-[720px] mx-auto">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-caption uppercase tracking-wide text-ink-soft font-num">
                Step {run.currentStep + 1} of {steps.length}
              </span>
              {isDone && (
                <span className="chip text-accent border-accent/40">
                  <Check size={12} /> complete
                </span>
              )}
              {isSkipped && (
                <span className="chip text-signal-warn border-signal-warn/40">
                  skipped — {run.skipped[step!.id]}
                </span>
              )}
              {outOfOrder && (
                <span className="chip text-signal-info border-signal-info/40">
                  later steps already completed
                </span>
              )}
            </div>

            {/* ink, not ink-soft: ≥7:1 contrast at arm's length */}
            <p className="text-ink font-medium mb-5" style={{ fontSize: 21, lineHeight: '31px' }}>
              {stepText}
            </p>

            {step?.note && (
              <Callout kind="info" title="Why this step">
                {step.note}
              </Callout>
            )}

            {step?.refs && step.refs.length > 0 && (
              <div className="flex flex-wrap items-center gap-2 mt-3">
                <span className="text-caption text-ink-soft">Source:</span>
                {step.refs.map((r) => (
                  <CitationChip
                    key={r}
                    paperId={r.startsWith('r-') ? undefined : r}
                    recordId={r.startsWith('r-') ? r : undefined}
                  />
                ))}
              </div>
            )}

            {step?.multiCheck && step.multiCheck.length > 0 && (
              <div className="card p-3 mt-4">
                <div className="text-caption uppercase tracking-wide text-ink-soft mb-2">
                  Complete each
                </div>
                <div className="space-y-1">
                  {step.multiCheck.map((label, i) => (
                    <label
                      key={i}
                      className="flex items-center gap-3 cursor-pointer py-1.5"
                      style={{ minHeight: 44 }}
                    >
                      <input
                        type="checkbox"
                        className="w-5 h-5"
                        checked={run.checks[step.id]?.[i] ?? false}
                        onChange={() => toggleCheck(runId, step.id, i)}
                      />
                      <span className="text-reading">{label}</span>
                    </label>
                  ))}
                </div>
              </div>
            )}

            {step?.timerSec !== undefined && (
              <div className="card p-4 mt-4 flex items-center gap-5">
                {stepTimer ? (
                  <>
                    <TimerRing remaining={stepTimer.remainingSec} total={stepTimer.totalSec} />
                    <div className="flex-1 min-w-0">
                      <div className="font-medium">{stepTimer.label}</div>
                      <div className="text-caption text-ink-soft">
                        {stepTimer.remainingSec <= 0
                          ? 'Complete'
                          : stepTimer.running
                            ? 'Running'
                            : 'Paused'}
                      </div>
                      <div className="flex gap-2 mt-2 flex-wrap">
                        <Button
                          style={{ minHeight: 44 }}
                          onClick={() => toggleTimer(runId, stepTimer.id)}
                          disabled={stepTimer.remainingSec <= 0}
                        >
                          {stepTimer.running ? <Pause size={15} /> : <Play size={15} />}
                          {stepTimer.running ? 'Pause' : 'Resume'}
                        </Button>
                        <Button style={{ minHeight: 44 }} onClick={() => extendTimer(runId, stepTimer.id, 60)}>
                          <Plus size={15} /> 1 min
                        </Button>
                        {stepTimer.remainingSec <= 0 && (
                          <Button style={{ minHeight: 44 }} onClick={() => dismissTimer(runId, stepTimer.id)}>
                            Dismiss
                          </Button>
                        )}
                      </div>
                    </div>
                  </>
                ) : (
                  <>
                    <Clock size={30} className="text-ink-soft" />
                    <div className="flex-1">
                      <div className="font-medium">{step.timerLabel ?? 'Timed step'}</div>
                      <div className="text-caption text-ink-soft font-num">
                        {mmss(step.timerSec)} — timers keep running while you move between steps
                      </div>
                    </div>
                    <Button variant="primary" style={{ minHeight: 44 }} onClick={startStepTimer}>
                      <Play size={15} /> Start timer <span className="kbd ml-1">t</span>
                    </Button>
                  </>
                )}
              </div>
            )}

            <div className="mt-4">
              <Button style={{ minHeight: 44 }} onClick={() => setNoteOpen(true)}>
                <StickyNote size={15} /> Add deviation note <span className="kbd ml-1">n</span>
              </Button>
            </div>

            {run.deviations.filter((d) => d.stepId === step?.id).length > 0 && (
              <div className="mt-3 space-y-1.5">
                {run.deviations
                  .filter((d) => d.stepId === step?.id)
                  .map((d, i) => (
                    <div key={i} className="tick tick-user text-body">
                      <span className="font-num text-caption text-ink-soft">{d.at}</span> — {d.text}
                    </div>
                  ))}
              </div>
            )}
          </div>
        </main>

        {/* Concurrent-timer mini-tray */}
        {timers.length > 0 && (
          <aside className="hidden lg:block w-[212px] shrink-0 border-l border-line bg-surface-1 p-3 overflow-y-auto">
            <div className="text-caption uppercase tracking-wide text-ink-soft mb-2">
              Timers ({runningTimers.length} running)
            </div>
            <div className="space-y-2">
              {timers.map((t) => (
                <div
                  key={t.id}
                  className={cx(
                    'card p-2',
                    t.remainingSec <= 0 && 'border-accent bg-accent-wash',
                  )}
                >
                  <div className="text-caption truncate">{t.label}</div>
                  <div className="font-num text-section-title">{mmss(t.remainingSec)}</div>
                  <div className="flex gap-1 mt-1">
                    <button
                      className="btn btn-sm"
                      onClick={() => toggleTimer(runId, t.id)}
                      disabled={t.remainingSec <= 0}
                      aria-label={t.running ? `Pause ${t.label}` : `Resume ${t.label}`}
                    >
                      {t.running ? <Pause size={12} /> : <Play size={12} />}
                    </button>
                    <button className="btn btn-sm" onClick={() => extendTimer(runId, t.id, 60)}>
                      +1
                    </button>
                    <button className="btn btn-sm" onClick={() => dismissTimer(runId, t.id)}>
                      <X size={12} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </aside>
        )}
      </div>

      {/* Bottom bar */}
      <footer className="shrink-0 border-t border-line bg-surface-1 px-4 py-3 flex items-center gap-3">
        <Button
          style={{ minHeight: 56, minWidth: 96 }}
          onClick={() => advance(-1)}
          disabled={run.currentStep === 0}
        >
          <ArrowLeft size={17} /> Back
        </Button>
        <button
          className="btn btn-primary flex-1 justify-center"
          style={{ minHeight: 56, fontSize: 17 }}
          onClick={markComplete}
        >
          <Check size={20} />
          {run.currentStep === steps.length - 1 && !allResolved
            ? 'Complete final step'
            : 'Mark step complete'}
          <span className="kbd ml-2">space</span>
        </button>
        <Button style={{ minHeight: 56 }} onClick={() => setSkipOpen(true)}>
          <SkipForward size={17} /> Skip
        </Button>
        <Button
          style={{ minHeight: 56 }}
          onClick={() => advance(1)}
          disabled={run.currentStep >= steps.length - 1}
          aria-label="Next step"
        >
          <ArrowRight size={17} />
        </Button>
      </footer>

      {/* Deviation note */}
      <Modal open={noteOpen} onClose={() => setNoteOpen(false)} title="Add deviation note">
        <p className="text-body text-ink-soft mb-2">
          Recorded verbatim against step {run.currentStep + 1} with a timestamp, and reproduced in
          the run summary.
        </p>
        <textarea
          ref={noteRef}
          className="input font-sans resize-y min-h-[100px]"
          value={noteText}
          placeholder="e.g. pH drifted to 7.6 before adjustment; added 0.4 mL extra acetic acid."
          onChange={(e) => setNoteText(e.target.value)}
        />
        <div className="flex justify-end gap-2 mt-3">
          <Button onClick={() => setNoteOpen(false)}>Cancel</Button>
          <Button
            variant="primary"
            disabled={!noteText.trim()}
            onClick={() => {
              if (!step) return;
              addDeviation(runId, {
                at: new Date().toLocaleTimeString(),
                stepId: step.id,
                text: noteText.trim(),
              });
              setNoteText('');
              setNoteOpen(false);
              toast({ text: 'Deviation recorded', kind: 'info' });
            }}
          >
            Record
          </Button>
        </div>
      </Modal>

      {/* Skip with reason */}
      <Modal open={skipOpen} onClose={() => setSkipOpen(false)} title="Skip this step">
        <p className="text-body text-ink-soft mb-3">
          A skipped step appears in the run summary with its reason. Nothing is silently omitted.
        </p>
        <div className="space-y-1.5">
          {SKIP_REASONS.map((reason) => (
            <button
              key={reason}
              className="w-full text-left btn"
              style={{ minHeight: 44 }}
              onClick={() => {
                if (!step) return;
                skipStep(runId, step.id, reason);
                setSkipOpen(false);
                if (run.currentStep < steps.length - 1) advance(1);
                else setSummary(true);
              }}
            >
              {reason}
            </button>
          ))}
        </div>
      </Modal>

      {/* Exit confirm */}
      <Modal open={exitOpen} onClose={() => setExitOpen(false)} title="Leave this run?">
        <p className="text-body mb-4">
          This run has{' '}
          <span className="font-num">{steps.length - completedCount - skippedCount}</span> incomplete{' '}
          {steps.length - completedCount - skippedCount === 1 ? 'step' : 'steps'} and{' '}
          <span className="font-num">{runningTimers.length}</span> running{' '}
          {runningTimers.length === 1 ? 'timer' : 'timers'}. Leave and keep the run active, or end it
          now?
        </p>
        <div className="flex justify-end gap-2 flex-wrap">
          <Button onClick={() => setExitOpen(false)}>Stay here</Button>
          <Button
            onClick={() => {
              setExitOpen(false);
              toast({
                text: 'Run kept active — find it in the Jobs tray',
                kind: 'info',
                href: `#/protocols/${protocolId}/run/${runId}`,
                hrefLabel: 'Resume',
              });
              navigate(`/protocols/${protocolId}`);
            }}
          >
            Keep active
          </Button>
          <Button
            variant="primary"
            onClick={() => {
              setExitOpen(false);
              setSummary(true);
            }}
          >
            End run now
          </Button>
        </div>
      </Modal>
    </div>
  );
}
