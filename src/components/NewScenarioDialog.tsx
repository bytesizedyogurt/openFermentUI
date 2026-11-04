// New scenario (OF-BLD-019 §3.1, D2, D5, D6): pick a flowsheet from the
// service's shelf, name the scenario, and it opens.
//
// The shelf is the service's (`GET /api/proforma/shelf`): every flowsheet a
// scenario can name, each one whose inputs bind to records or to a named
// person's assumption, and the toy never. The reference plants are the
// library shelf's, run whole from their reference page or from Studies.
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
// nothing is silent. The scenario keeps both ids in its row (`vessel`,
// `trainRun`). fermOS → Vessel's **Price this in Proforma** opens
// this with its design chosen (`initialVessel`).
//
// NEW SCENARIO FROM A RUN (alpha 2.1 stage B; alpha 2.2 C.5). Opened with
// `fromRun`, an engine run's report, the dialog makes a study scenario on the
// run's plant and configuration (POST /api/studies/scenarios) and runs it in
// the person's name (…/{id}/run); the new run's page opens. The person finds
// parameters of the run by words and sets each one, and every parameter left
// alone stays the package's own. A value is either the person's own, typed
// as their assumption with what it rests on, or a reading a person deposited
// at the bench: beside the typed value, the dialog lists the project's
// confirmed readings whose unit is the parameter's or converts into it, as
// the service's lookup answers them (GET /api/depositions/readings?unit=),
// each with its runbook, measure, value, unit, time and person. Choosing one
// sends `{value, unit, origin: {kind: 'measurement', ref}}`, the reading's
// own value and unit; the service fills the depositor and the time, converts
// the unit, and looks the reading up again when the scenario runs, so a run
// resting on readings and the package's defaults alone is `measured`.
import { useEffect, useMemo, useRef, useState } from 'react';
import { Play } from 'lucide-react';
import type { FlowsheetInfo, RunReport, ScenarioValue, TrainSummary, VesselSummary } from '@/data/types';
import { useStore } from '@/store';
import { href, navigate } from '@/router';
import { fmt } from '@/engine/units';
import { Button, Modal, cx } from './ui';
import { minute } from './ReadingOrigin';
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
import { StudiesDown, depositionReadings, makeScenario, runScenario, type DepositionReading } from '@/lib/studies';

/** The line a shelf with nothing to start a scenario from shows, here and on the index. */
export function NoFlowsheetLine() {
  return (
    <span data-testid="no-flowsheet">
      No flowsheet is on this service&rsquo;s shelf yet, so there is nothing to start a scenario from. The reference
      plants are the library shelf&rsquo;s, run whole from Proforma&rsquo;s Reference runs row or from Studies.
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

interface ShelfProps {
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
}

/**
 * A new scenario: with `fromRun`, a study scenario on that engine run's plant, each value the person's own or a
 * deposition's reading, made and run in their name; else a Proforma scenario on a flowsheet from the shelf.
 */
export function NewScenarioDialog({ fromRun = null, ...shelf }: ShelfProps & { fromRun?: RunReport | null }) {
  return fromRun ? <ScenarioFromRun open={shelf.open} onClose={shelf.onClose} report={fromRun} /> : <ShelfScenario {...shelf} />;
}

function ShelfScenario({ open, onClose, initialFlowsheet = null, attachFit = null, initialVessel = null, initialTrainRun = null }: ShelfProps) {
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

  // Every flowsheet on the shelf is one a scenario runs (alpha 2.2 D8).
  const choices = useMemo(() => shelf ?? [], [shelf]);
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

// ── a scenario from a run (alpha 2.1 stage B; alpha 2.2 C.5) ───────────

/** How many matching parameters the finder lists at once. */
const FOUND_ROWS = 12;

const problemOf = (e: unknown) =>
  e instanceof StudiesDown || e instanceof ProformaDown ? `${e.message} ${e.remedy ?? ''}`.trim() : e instanceof Error ? e.message : String(e);

/** One parameter a person sets: their own typed value, or a deposition's reading. */
interface Setting {
  key: string;
  label: string;
  unit: string;
  /** Where its value comes from. */
  source: 'typed' | 'reading';
  /** As the person typed it; read as a number when the scenario is made. */
  value: string;
  /** What the typed value rests on, in the person's words. */
  note: string;
  /** The reading chosen, by its ref (`<deposition id>/<entry id>`). */
  reading: string | null;
  /** Why the chosen reading stands for the parameter, in the person's words: its own note, apart from the typed value's. */
  readingNote: string;
}

/** The readings of one unit as the service listed them: null while it is asked, with its words when it could not answer. */
type Listed = { readings: DepositionReading[] | null; problem: string | null };

/** A reading as a person chooses it: its measure, its value and unit (and in the parameter's, where it converts), its runbook, its time and its person. */
function ReadingChoice({ reading, setting, chosen, onChoose }: { reading: DepositionReading; setting: Setting; chosen: boolean; onChoose: () => void }) {
  const converted = reading.inUnit != null && reading.unit !== setting.unit;
  return (
    <label
      className={cx('card p-2 flex items-start gap-2 cursor-pointer min-h-[44px]', chosen && 'border-accent')}
      data-testid="scenario-reading"
      data-ref={reading.ref}
    >
      <input type="radio" className="mt-1" name={`scenario-reading-${setting.key}`} checked={chosen} onChange={onChoose} aria-label={`Reading ${reading.ref}`} />
      <span className="min-w-0">
        {/* What the reading measured, and what it would set: the pairing is the person's to choose, and the service holds the unit alone. */}
        <span className="block">
          a reading of {reading.measure ?? `measure ${reading.measureId}`}:{' '}
          <span className="font-num" title={String(reading.value)}>
            {fmt(reading.value, 6)} {reading.unit}
          </span>
          {converted && (
            <span className="font-num text-ink-soft">
              {' '}
              = {fmt(reading.inUnit ?? 0, 6)} {setting.unit}
            </span>
          )}
          , set as <span className="font-medium">{setting.label}</span>
        </span>
        <span className="block text-caption text-ink-soft">
          {reading.runbook ? <>runbook {reading.runbook}</> : <>runbook {reading.runbookId ?? 'not named'}, which the project does not hold</>} · taken{' '}
          <span className="font-num">{minute(reading.at)}</span>
          {reading.hours != null && <> at hour {reading.hours}</>} · deposited by {reading.by} · <span className="font-num">{reading.ref}</span>
        </span>
      </span>
    </label>
  );
}

/**
 * A study scenario from an engine run (the module's header): parameters found by words, each set to the person's
 * own value or to a deposition's reading, the scenario made and run in their name, and the new run's page opened.
 */
function ScenarioFromRun({ open, onClose, report }: { open: boolean; onClose: () => void; report: RunReport }) {
  const reviewer = useStore((s) => s.reviewer).trim();
  const run = report.run;
  const scope = report.parameters;
  const [words, setWords] = useState('');
  const [settings, setSettings] = useState<Setting[]>([]);
  const [title, setTitle] = useState('');
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [made, setMade] = useState<string | null>(null);
  // The readings each unit takes, asked of the service once a setting asks for a reading in that unit.
  const [listed, setListed] = useState<Record<string, Listed>>({});
  const asked = useRef(new Set<string>());

  // A fresh dialog each time it opens, its readings asked again: a reading deposited since stands among them.
  useEffect(() => {
    if (!open) return;
    setWords('');
    setSettings([]);
    setTitle('');
    setNote('');
    setProblem(null);
    setMade(null);
    setListed({});
    asked.current = new Set();
  }, [open]);

  useEffect(() => {
    for (const s of settings) {
      if (s.source !== 'reading' || asked.current.has(s.unit)) continue;
      const unit = s.unit;
      asked.current.add(unit);
      setListed((l) => ({ ...l, [unit]: { readings: null, problem: null } }));
      depositionReadings(unit).then(
        (readings) => setListed((l) => ({ ...l, [unit]: { readings, problem: null } })),
        (e: unknown) => setListed((l) => ({ ...l, [unit]: { readings: [], problem: problemOf(e) } })),
      );
    }
  }, [settings]);

  const valueOf = new Map((scope?.values ?? []).map((v) => [v.key, v.value]));
  const numeric = (scope?.specs ?? []).filter((s) => !s.choices && typeof valueOf.get(s.key) === 'number');
  const wanted = words.toLowerCase().split(/\s+/).filter(Boolean);
  const taken = new Set(settings.map((s) => s.key));
  const found = wanted.length ? numeric.filter((s) => !taken.has(s.key) && wanted.every((w) => `${s.key} ${s.label}`.toLowerCase().includes(w))) : [];
  const add = (key: string) => {
    const spec = numeric.find((s) => s.key === key);
    if (!spec) return;
    setSettings((list) => [
      ...list,
      { key, label: spec.label, unit: spec.unit, source: 'typed', value: String(valueOf.get(key) ?? ''), note: '', reading: null, readingNote: '' },
    ]);
  };
  const change = (key: string, patch: Partial<Setting>) => setSettings((list) => list.map((s) => (s.key === key ? { ...s, ...patch } : s)));
  // The reading a setting rests on, while its source is a reading.
  const chosenOf = (s: Setting) =>
    s.source === 'reading' && s.reading ? (listed[s.unit]?.readings?.find((r) => r.ref === s.reading) ?? null) : null;

  const make = () => {
    const at = new Date().toISOString();
    const bad = settings.find((s) => s.source === 'typed' && (s.value.trim() === '' || !Number.isFinite(Number(s.value))));
    if (bad) {
      setProblem(`${bad.label}: a value is one number, in ${bad.unit || 'the parameter’s own terms'}.`);
      return;
    }
    const unread = settings.find((s) => s.source === 'reading' && !chosenOf(s));
    if (unread) {
      setProblem(`${unread.label}: choose the reading it rests on, or type your own value.`);
      return;
    }
    const values: ScenarioValue[] = settings.map((s) => {
      const r = chosenOf(s);
      return r
        ? { key: s.key, quantity: { value: r.value, unit: r.unit, origin: { kind: 'measurement', ref: r.ref, note: s.readingNote.trim() || null } } }
        : {
            key: s.key,
            quantity: { value: Number(s.value), unit: s.unit, origin: { kind: 'person-assumption', by: reviewer, at, note: s.note.trim() || note.trim() || null } },
          };
    });
    setBusy(true);
    setProblem(null);
    makeScenario({ title: title.trim(), plant: run.plant, configuration: run.configuration ?? null, values, note: note.trim() || null, by: reviewer })
      .then((scenario) => {
        setMade(scenario.id);
        return runScenario(scenario.id, reviewer);
      })
      .then((rep) => {
        onClose();
        navigate(`/proforma/runs/${rep.run.id}`);
      })
      .catch((e: unknown) => setProblem(problemOf(e)))
      .finally(() => setBusy(false));
  };

  const where = `${run.plant}${run.configuration ? ` (${run.configuration})` : ''}`;
  return (
    <Modal open={open} onClose={onClose} title="New scenario from this run" width={780}>
      <div className="max-h-[78vh] overflow-y-auto pr-1" data-testid="run-make-scenario-dialog">
        <p className="text-caption text-ink-soft mb-2">
          The scenario runs {where} with the values you set, and every parameter you leave alone stays the package&rsquo;s own. Find a parameter by its
          words and set it: to your own value, typed as your assumption, or to a reading a person deposited at the bench and confirmed, which the
          service looks up in the project&rsquo;s depositions when the scenario is made and again when it runs.
        </p>
        <input
          className="input text-body w-full mb-2"
          aria-label="Find a parameter"
          placeholder="Words of a parameter: xylose ethanol, moisture, price…"
          value={words}
          onChange={(e) => setWords(e.target.value)}
          data-testid="scenario-find"
        />
        {found.length > 0 && (
          <ul className="space-y-0.5 mb-2 text-caption" data-testid="scenario-found">
            {found.slice(0, FOUND_ROWS).map((s) => (
              <li key={s.key} className="flex flex-wrap items-center gap-2" data-testid="scenario-found-row" data-key={s.key}>
                <button className="chip" onClick={() => add(s.key)} aria-label={`Set ${s.label}`}>
                  Set
                </button>
                <span>{s.label}</span>
                <span className="font-num text-ink-soft">
                  {String(valueOf.get(s.key))} {s.unit}
                </span>
              </li>
            ))}
            {found.length > FOUND_ROWS && <li className="text-ink-soft">and {found.length - FOUND_ROWS} more: add words to narrow them.</li>}
          </ul>
        )}
        {wanted.length > 0 && found.length === 0 && <p className="text-caption text-ink-soft mb-2">No parameter of this run left to set matches those words.</p>}
        {settings.length > 0 && (
          <ul className="space-y-2 mb-3" data-testid="scenario-settings">
            {settings.map((s) => {
              const held = listed[s.unit];
              return (
                <li key={s.key} className="border-t border-line/50 pt-2 text-caption" data-testid="scenario-setting" data-key={s.key} data-source={s.source}>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-body">
                      {s.label} <span className="font-num text-ink-soft">({s.unit || 'no unit'})</span>
                    </span>
                    <span className="flex flex-wrap items-center gap-1.5" role="group" aria-label={`Where ${s.label} comes from`}>
                      <button className={cx('chip', s.source === 'typed' && 'border-accent text-accent')} aria-pressed={s.source === 'typed'} onClick={() => change(s.key, { source: 'typed' })} data-testid="scenario-source-typed">
                        Your value
                      </button>
                      <button className={cx('chip', s.source === 'reading' && 'border-accent text-accent')} aria-pressed={s.source === 'reading'} onClick={() => change(s.key, { source: 'reading' })} data-testid="scenario-source-reading">
                        A reading
                      </button>
                      <button className="chip" onClick={() => setSettings((list) => list.filter((x) => x.key !== s.key))} aria-label={`Leave ${s.label} as the run's`}>
                        Leave
                      </button>
                    </span>
                  </div>
                  {s.source === 'typed' ? (
                    <div className="flex flex-wrap items-center gap-2 mt-1">
                      <input
                        className="input text-caption font-num w-28"
                        inputMode="decimal"
                        aria-label={`Your value for ${s.label}`}
                        value={s.value}
                        onChange={(e) => change(s.key, { value: e.target.value })}
                      />
                      <span className="font-num text-ink-soft">{s.unit}</span>
                      <input
                        className="input text-caption flex-1 min-w-48"
                        aria-label={`What ${s.label} rests on`}
                        placeholder="What it rests on (optional)"
                        value={s.note}
                        onChange={(e) => change(s.key, { note: e.target.value })}
                      />
                    </div>
                  ) : (
                    <div className="mt-1 space-y-1" data-testid="scenario-readings" data-unit={s.unit}>
                      {!held || held.readings === null ? (
                        <p className="text-ink-soft">Asking the service for the project&rsquo;s readings in {s.unit || 'no unit'}…</p>
                      ) : held.problem ? (
                        <p className="text-signal-warn">{held.problem}</p>
                      ) : held.readings.length === 0 ? (
                        <p className="text-ink-soft" data-testid="scenario-no-reading">
                          No confirmed reading of this project is in {s.unit || 'no unit'} or in a unit that converts into it. A reading is deposited at the
                          bench on a locked runbook, from its page, and read back there.
                        </p>
                      ) : (
                        held.readings.map((r) => (
                          <ReadingChoice key={r.ref} reading={r} setting={s} chosen={s.reading === r.ref} onChoose={() => change(s.key, { reading: r.ref })} />
                        ))
                      )}
                      <input
                        className="input text-caption w-full"
                        aria-label={`What the reading for ${s.label} rests on`}
                        placeholder="Why this reading stands for it (optional)"
                        value={s.readingNote}
                        onChange={(e) => change(s.key, { readingNote: e.target.value })}
                      />
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}
        <div className="flex flex-wrap items-center gap-2">
          <input className="input text-body" aria-label="The scenario's title" placeholder="What the scenario asks" value={title} onChange={(e) => setTitle(e.target.value)} />
          <input className="input text-body flex-1 min-w-48" aria-label="What the scenario rests on" placeholder="What it rests on, in words" value={note} onChange={(e) => setNote(e.target.value)} />
          <Button variant="primary" disabled={busy || !reviewer || settings.length === 0 || !title.trim()} onClick={make} data-testid="run-make-scenario-go">
            <Play size={14} /> {busy ? 'Running…' : 'Make the scenario and run it'}
          </Button>
          <Button onClick={onClose}>Cancel</Button>
        </div>
        {!reviewer && <p className="text-caption text-ink-soft mt-1">A scenario is made in a person&rsquo;s name: set yours in Settings first.</p>}
        {problem && (
          <p className="text-caption text-signal-warn mt-1" data-testid="run-make-scenario-problem">
            {problem}
            {made && (
              <>
                {' '}
                The scenario <span className="font-num">{made}</span> is kept;{' '}
                <a className="underline underline-offset-2" href={href('/proforma/studies')}>
                  Studies
                </a>{' '}
                lists it.
              </>
            )}
          </p>
        )}
      </div>
    </Modal>
  );
}
