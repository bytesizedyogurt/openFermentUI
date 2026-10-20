// New scenario (OF-BLD-019 §3.1, D2, D5, D6): pick a flowsheet from the
// service's shelf, name the scenario, choose its program, and it opens.
//
// The shelf is the service's (`GET /api/proforma/shelf`): with archived
// programs hidden it lists only the active program's flowsheets and the
// general ones, and the toy never. A reference biorefinery runs whole on its
// package's own defaults, so it is not offered here: a scenario is made on a
// flowsheet whose inputs bind to records or to a named person's assumption.
// What is made is a `biosteam` scenario and nothing else (D5), held in this
// browser's Durable tier under a time-based id (D6); it carries no input
// value of its own.
//
// Proforma's index opens this, and so does the palette's "New Proforma
// scenario" (through `ui.newScenarioOpen`).
import { useEffect, useMemo, useState } from 'react';
import type { FlowsheetInfo, ProgramId } from '@/data/types';
import { PROGRAMS, PROGRAMS_SETTINGS_PATH } from '@/data/programs';
import { activePrograms, useStore } from '@/store';
import { href, navigate } from '@/router';
import { Button, Modal } from './ui';
import { ProformaDown, defaultProgram, proformaShelf } from '@/lib/proforma';

/** The line a shelf with nothing to start a scenario from shows, here and on the index. */
export function NoFlowsheetLine({ showArchived }: { showArchived: boolean }) {
  const active = activePrograms();
  return (
    <span data-testid="no-flowsheet">
      No flowsheet of {active.map((p) => p.name).join(' or ') || 'an active program'} is on this service&rsquo;s shelf
      yet, so there is nothing to start a scenario from.
      {active.some((p) => p.id === 'yeast') &&
        ' Glucose to ethanol, the yeast program’s own flowsheet, is still to be added to it.'}{' '}
      The reference biorefineries run whole on their package&rsquo;s defaults and are not a starting point.
      {!showArchived && (
        <>
          {' '}
          Flowsheets of archived programs show when{' '}
          <a className="text-accent underline underline-offset-2" href={href(PROGRAMS_SETTINGS_PATH)}>
            Settings → Programs
          </a>{' '}
          shows archived programs.
        </>
      )}
    </span>
  );
}

/** How one input of a flowsheet gets its value, in words. */
export function inputSourceWords(i: FlowsheetInfo['inputs'][number]): string {
  if (i.fields.length > 0) return `binds to records of ${i.fields.join(' or ')}`;
  if (i.kind === 'convention') return 'a convention the run states';
  return "a named person's assumption";
}

export function NewScenarioDialog({
  open,
  onClose,
  initialFlowsheet = null,
}: {
  open: boolean;
  onClose: () => void;
  /** The flowsheet chosen when it opens ("New scenario from this"). */
  initialFlowsheet?: string | null;
}) {
  const showArchived = useStore((s) => s.showArchived);
  const createScenario = useStore((s) => s.createScenario);
  const toast = useStore((s) => s.toast);
  const [shelf, setShelf] = useState<FlowsheetInfo[] | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [chosen, setChosen] = useState<string | null>(initialFlowsheet);
  const [name, setName] = useState('');
  const [named, setNamed] = useState(false);
  const [program, setProgram] = useState<ProgramId | null>(null);

  useEffect(() => {
    if (!open) return;
    const ctrl = new AbortController();
    setProblem(null);
    proformaShelf(showArchived, ctrl.signal)
      .then(setShelf)
      .catch(
        (e: unknown) =>
          !ctrl.signal.aborted && setProblem(e instanceof ProformaDown ? `${e.message} ${e.remedy ?? ''}`.trim() : String(e instanceof Error ? e.message : e)),
      );
    return () => ctrl.abort();
  }, [open, showArchived]);

  // A fresh dialog each time it opens, on the flowsheet it was opened for.
  useEffect(() => {
    if (!open) return;
    setChosen(initialFlowsheet);
    setNamed(false);
  }, [open, initialFlowsheet]);

  const choices = useMemo(() => (shelf ?? []).filter((f) => !f.reference), [shelf]);
  const offered = useMemo(
    () => PROGRAMS.filter((p) => p.status === 'active' || showArchived),
    [showArchived],
  );
  const flowsheet = choices.find((f) => f.id === chosen) ?? (choices.length === 1 ? choices[0] : null);

  // The name follows the flowsheet until a person types one; the program is
  // the flowsheet's own when it is offered, else the active program.
  useEffect(() => {
    if (!flowsheet) return;
    if (!named) setName(flowsheet.title);
    setProgram(defaultProgram(flowsheet, offered.map((p) => p.id)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [flowsheet?.id, open]);

  const create = () => {
    if (!flowsheet || !name.trim()) return;
    const id = createScenario(flowsheet.id, name, program);
    onClose();
    navigate(`/proforma/scenario/${id}`);
    toast({ text: `Scenario made on ${flowsheet.title}; it has not run yet`, kind: 'success' });
  };

  return (
    <Modal open={open} onClose={onClose} title="New scenario" width={620}>
      <div data-testid="new-scenario-dialog">
        <p className="text-body text-ink-soft mb-3">
          A scenario runs one flowsheet from the shelf. Its process inputs bind to records when it runs, and every other
          input waits for a named person&rsquo;s assumption, typed on its page.
        </p>
        {problem && <p className="text-body text-signal-warn mb-2">The shelf is the service&rsquo;s. {problem}</p>}
        {!problem && shelf === null && <p className="text-body text-ink-soft">Reading the shelf…</p>}
        {shelf !== null && choices.length === 0 && (
          <p className="text-body mb-2">
            <NoFlowsheetLine showArchived={showArchived} />
          </p>
        )}
        {choices.length > 0 && (
          <>
            <fieldset className="mb-3">
              <legend className="text-caption uppercase tracking-wide text-ink-soft mb-1">Flowsheet</legend>
              <ul className="space-y-1.5 max-h-[300px] overflow-y-auto">
                {choices.map((f) => (
                  <li key={f.id}>
                    <label
                      className="card p-3 flex items-start gap-2 cursor-pointer hover:border-accent/45"
                      data-testid="new-scenario-flowsheet"
                      data-flowsheet={f.id}
                    >
                      <input
                        type="radio"
                        name="new-scenario-flowsheet"
                        className="mt-1"
                        checked={flowsheet?.id === f.id}
                        onChange={() => setChosen(f.id)}
                      />
                      <span className="min-w-0">
                        <span className="block font-medium">{f.title}</span>
                        <span className="block text-caption text-ink-soft">
                          <span className="font-num">{f.id}</span> · {f.source}
                          {f.program && <> · {PROGRAMS.find((p) => p.id === f.program)?.name ?? f.program}</>} ·{' '}
                          <span className="font-num">{f.inputs.length}</span> inputs
                        </span>
                      </span>
                    </label>
                  </li>
                ))}
              </ul>
            </fieldset>
            {flowsheet && (
              <ul className="text-caption text-ink-soft mb-3 list-disc pl-5" data-testid="new-scenario-inputs">
                {flowsheet.inputs.map((i) => (
                  <li key={i.key}>
                    {i.name}
                    {i.unit && <span className="font-num"> ({i.unit})</span>}: {inputSourceWords(i)}
                    {i.kind === 'economic' && ', an economic input'}
                  </li>
                ))}
              </ul>
            )}
            <div className="grid grid-cols-1 sm:grid-cols-[1fr_200px] gap-3 mb-3">
              <label className="text-caption text-ink-soft">
                <span className="block mb-0.5">Name</span>
                <input
                  className="input w-full"
                  aria-label="Scenario name"
                  data-testid="new-scenario-name"
                  value={name}
                  onChange={(e) => {
                    setName(e.target.value);
                    setNamed(true);
                  }}
                />
              </label>
              <label className="text-caption text-ink-soft">
                <span className="block mb-0.5">Program</span>
                <select
                  className="input w-full"
                  aria-label="Program"
                  data-testid="new-scenario-program"
                  value={program ?? ''}
                  onChange={(e) => setProgram((e.target.value || null) as ProgramId | null)}
                >
                  {offered.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                      {p.status === 'archived' ? ' (archived)' : ''}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </>
        )}
        <div className="flex justify-end gap-2">
          <Button onClick={onClose}>Cancel</Button>
          {choices.length > 0 && (
            <Button variant="primary" onClick={create} disabled={!flowsheet || !name.trim()} data-testid="new-scenario-create">
              Make the scenario
            </Button>
          )}
        </div>
      </div>
    </Modal>
  );
}
