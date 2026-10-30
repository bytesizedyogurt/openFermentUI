// New scenario (OF-BLD-019 §3.1, D2, D5, D6): pick a flowsheet from the
// service's shelf, name the scenario, and it opens.
//
// The shelf is the service's (`GET /api/proforma/shelf`): every flowsheet a
// scenario can name, and the toy never. A reference biorefinery runs whole on its
// package's own defaults, so it is not offered here: a scenario is made on a
// flowsheet whose inputs bind to records or to a named person's assumption.
// What is made is a `biosteam` scenario and nothing else (D5), kept in the
// open project's rows under a time-based id (D6; lib/projectState.ts); it
// carries no input value of its own.
//
// Proforma's index opens this, and so does the palette's "New Proforma
// scenario" (through `ui.newScenarioOpen`); fermOS → Forecast's "Send to
// Proforma" opens it with the fit to attach (OF-BLD-019 §5.1), and the new
// scenario's page attaches it.
//
// NEW SCENARIO FROM A VESSEL AND A TRAIN (OF-BLD-020 §6.1, D11). A flowsheet
// built from kept artifacts (`builtFrom`: `custom_train_v1`, a fermOS vessel
// design and a pureOS train run) asks for both: a chooser over the vessel
// designs the service keeps (`GET /api/fermos/vessels`) and one over its
// train runs (`GET /api/pureos/train-runs`). An empty list says why in words
// and where one is made, and Make the scenario waits, saying what for;
// nothing is silent. The scenario keeps both ids (Durable
// `createdScenarios`). fermOS → Vessel's **Price this in Proforma** opens
// this with its design chosen (`initialVessel`).
import { useEffect, useMemo, useState } from 'react';
import type { FlowsheetInfo, TrainSummary, VesselSummary } from '@/data/types';
import { useStore } from '@/store';
import { href, navigate } from '@/router';
import { Button, Modal } from './ui';
import {
  ProformaDown,
  builtFromParts,
  compositeTrainRuns,
  compositeVessels,
  proformaShelf,
  sendFitPath,
  trainRunWords,
  vesselWords,
} from '@/lib/proforma';

/** The line a shelf with nothing to start a scenario from shows, here and on the index. */
export function NoFlowsheetLine() {
  return (
    <span data-testid="no-flowsheet">
      No flowsheet is on this service&rsquo;s shelf yet, so there is nothing to start a scenario from. The reference
      biorefineries run whole on their package&rsquo;s defaults and are not a starting point.
    </span>
  );
}

/** What a flowsheet built from kept artifacts is built from, in words. */
export const BUILT_FROM_WORDS: Record<string, string> = {
  'fermos.vessel': 'a vessel design kept in fermOS',
  'pureos.train_run': 'a train run kept in pureOS',
};

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
  attachFit = null,
  initialVessel = null,
  initialTrainRun = null,
}: {
  open: boolean;
  onClose: () => void;
  /** The flowsheet chosen when it opens ("New scenario from this"). */
  initialFlowsheet?: string | null;
  /** A fermOS fit's artifact id the new scenario's page attaches when it opens (fermOS → Forecast, "Send to Proforma"). */
  attachFit?: string | null;
  /** OF-BLD-020 §6.1: the vessel design chosen when it opens (fermOS → Vessel, "Price this in Proforma"). */
  initialVessel?: string | null;
  /** The train run chosen when it opens. */
  initialTrainRun?: string | null;
}) {
  const createScenario = useStore((s) => s.createScenario);
  const toast = useStore((s) => s.toast);
  const [shelf, setShelf] = useState<FlowsheetInfo[] | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [chosen, setChosen] = useState<string | null>(initialFlowsheet);
  const [name, setName] = useState('');
  const [named, setNamed] = useState(false);
  // OF-BLD-020 §6.1: the kept vessel designs and train runs a composite is made from, and the two chosen.
  const [vessels, setVessels] = useState<VesselSummary[] | null>(null);
  const [trainRuns, setTrainRuns] = useState<TrainSummary[] | null>(null);
  const [partsProblem, setPartsProblem] = useState<string | null>(null);
  const [vessel, setVessel] = useState<string | null>(initialVessel);
  const [trainRun, setTrainRun] = useState<string | null>(initialTrainRun);

  useEffect(() => {
    if (!open) return;
    const ctrl = new AbortController();
    setProblem(null);
    proformaShelf(ctrl.signal)
      .then(setShelf)
      .catch(
        (e: unknown) =>
          !ctrl.signal.aborted && setProblem(e instanceof ProformaDown ? `${e.message} ${e.remedy ?? ''}`.trim() : String(e instanceof Error ? e.message : e)),
      );
    return () => ctrl.abort();
  }, [open]);

  // A fresh dialog each time it opens, on the flowsheet it was opened for.
  useEffect(() => {
    if (!open) return;
    setChosen(initialFlowsheet);
    setNamed(false);
    setVessel(initialVessel);
    setTrainRun(initialTrainRun);
  }, [open, initialFlowsheet, initialVessel, initialTrainRun]);

  const choices = useMemo(() => (shelf ?? []).filter((f) => !f.reference), [shelf]);
  const composite = useMemo(() => choices.some((f) => builtFromParts(f)), [choices]);

  // The kept parts, asked for when the shelf holds a flowsheet built from them.
  useEffect(() => {
    if (!open || !composite) return;
    const ctrl = new AbortController();
    setVessels(null);
    setTrainRuns(null);
    setPartsProblem(null);
    const said = (e: unknown) =>
      !ctrl.signal.aborted && setPartsProblem(e instanceof ProformaDown ? `${e.message} ${e.remedy ?? ''}`.trim() : String(e instanceof Error ? e.message : e));
    compositeVessels(ctrl.signal)
      .then(setVessels)
      .catch((e: unknown) => {
        said(e);
        if (!ctrl.signal.aborted) setVessels([]);
      });
    compositeTrainRuns(ctrl.signal)
      .then(setTrainRuns)
      .catch((e: unknown) => {
        said(e);
        if (!ctrl.signal.aborted) setTrainRuns([]);
      });
    return () => ctrl.abort();
  }, [open, composite]);
  const flowsheet = choices.find((f) => f.id === chosen) ?? (choices.length === 1 ? choices[0] : null);
  const needsParts = builtFromParts(flowsheet);
  // What a composite still waits for, in words (never a silent empty).
  const partsWait = !needsParts
    ? null
    : vessels === null || trainRuns === null
      ? 'Asking the service for its kept vessel designs and train runs…'
      : (vessels.length === 0 && !vessel) || (trainRuns.length === 0 && !trainRun)
        ? null
        : !vessel || !trainRun
          ? `Choose ${!vessel && !trainRun ? 'a vessel design and a train run' : !vessel ? 'a vessel design' : 'a train run'} to make the scenario from.`
          : null;

  // The name follows the flowsheet until a person types one.
  useEffect(() => {
    if (!flowsheet) return;
    if (!named) setName(flowsheet.title);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [flowsheet?.id, open]);

  const parts = needsParts && vessel && trainRun ? { vessel, trainRun } : null;
  const create = () => {
    if (!flowsheet || !name.trim() || (needsParts && !parts)) return;
    const id = createScenario(flowsheet.id, name, parts);
    onClose();
    navigate(attachFit ? sendFitPath(id, attachFit) : `/proforma/scenario/${id}`);
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
            <NoFlowsheetLine />
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
                          <span className="font-num">{f.id}</span> · {f.source} ·{' '}
                          <span className="font-num">{f.inputs.length}</span> inputs
                          {builtFromParts(f) && <> · built from {f.builtFrom.map((t) => BUILT_FROM_WORDS[t] ?? t).join(' and ')}</>}
                        </span>
                      </span>
                    </label>
                  </li>
                ))}
              </ul>
            </fieldset>
            {needsParts && (
              <fieldset className="mb-3 card p-3" data-testid="new-scenario-composite">
                <legend className="text-caption uppercase tracking-wide text-ink-soft px-1">New scenario from a vessel and a train</legend>
                <p className="text-caption text-ink-soft mb-2">
                  The fermenter is rebuilt from a vessel design fermOS keeps, every design parameter as the design holds it, and the train&rsquo;s
                  units follow it from a train run pureOS keeps, each with its values as that run held them. The train&rsquo;s own inlet is not an
                  input: the fermenter&rsquo;s beer is.
                </p>
                {partsProblem && <p className="text-caption text-signal-warn mb-1">{partsProblem}</p>}
                {vessels !== null && vessels.length === 0 && !vessel && (
                  <p className="text-body mb-1" data-testid="new-scenario-composite-empty" data-part="vessel">
                    No vessel design is kept on this service yet: <a className="text-accent underline underline-offset-2" href={href('/fermos/vessel')}>fermOS → Vessel</a>{' '}
                    designs one for a kept simulation, and it is listed here.
                  </p>
                )}
                {trainRuns !== null && trainRuns.length === 0 && !trainRun && (
                  <p className="text-body mb-1" data-testid="new-scenario-composite-empty" data-part="train-run">
                    No train run is kept on this service yet: <a className="text-accent underline underline-offset-2" href={href('/pureos')}>pureOS → New train</a>{' '}
                    builds and runs one, and it is listed here.
                  </p>
                )}
                <div className="grid grid-cols-1 gap-2">
                  {vessels !== null && (vessels.length > 0 || vessel) && (
                    <label className="text-caption text-ink-soft">
                      <span className="block mb-0.5">Vessel design</span>
                      <select
                        className="input w-full min-h-[44px]"
                        aria-label="Vessel design"
                        data-testid="new-scenario-vessel"
                        value={vessel ?? ''}
                        onChange={(e) => setVessel(e.target.value || null)}
                      >
                        <option value="">Choose a kept vessel design</option>
                        {vessel && !vessels.some((v) => v.artifactId === vessel) && <option value={vessel}>{`vessel design ${vessel}`}</option>}
                        {vessels.map((v) => (
                          <option key={v.artifactId} value={v.artifactId}>
                            {vesselWords(v)}
                          </option>
                        ))}
                      </select>
                    </label>
                  )}
                  {trainRuns !== null && (trainRuns.length > 0 || trainRun) && (
                    <label className="text-caption text-ink-soft">
                      <span className="block mb-0.5">Train run</span>
                      <select
                        className="input w-full min-h-[44px]"
                        aria-label="Train run"
                        data-testid="new-scenario-train-run"
                        value={trainRun ?? ''}
                        onChange={(e) => setTrainRun(e.target.value || null)}
                      >
                        <option value="">Choose a kept train run</option>
                        {trainRun && !trainRuns.some((t) => t.artifactId === trainRun) && <option value={trainRun}>{`train run ${trainRun}`}</option>}
                        {trainRuns.map((t) => (
                          <option key={t.artifactId} value={t.artifactId}>
                            {trainRunWords(t)}
                          </option>
                        ))}
                      </select>
                    </label>
                  )}
                </div>
                {(partsWait || (vessels !== null && trainRuns !== null && ((vessels.length === 0 && !vessel) || (trainRuns.length === 0 && !trainRun)))) && (
                  <p className="text-caption text-signal-warn mt-2" data-testid="new-scenario-composite-waits">
                    {partsWait ?? 'Make the scenario waits until a vessel design and a train run are kept.'}
                  </p>
                )}
              </fieldset>
            )}
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
            <label className="block text-caption text-ink-soft mb-3">
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
          </>
        )}
        <div className="flex justify-end gap-2">
          <Button onClick={onClose}>Cancel</Button>
          {choices.length > 0 && (
            <Button variant="primary" onClick={create} disabled={!flowsheet || !name.trim() || (needsParts && !parts)} data-testid="new-scenario-create">
              Make the scenario
            </Button>
          )}
        </div>
      </div>
    </Modal>
  );
}
