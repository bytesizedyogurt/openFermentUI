// An engine run's page (execution prompt §7.4, §9.1 step 5): /proforma/runs/:id.
//
// One run of a library plant, an openFerment flowsheet or another engine's
// thing, as the service kept it (GET /api/runs/{id}, engine/runs.py). What it
// reads:
//
//   the run         its plant and configuration, its status and provenance,
//                   who asked and when, the study scenario that asked for it;
//                   a train run names its train's name beside its id, links
//                   to the train on pureOS → Train, and shows the `train`
//                   input as its name and units, the train as data on asking;
//   its outputs     a contract engine's or a kinetics run (docs/api/engines.md,
//                   docs/api/runs.md): each output its name, value and unit,
//                   with its interval where it carries one (a forecast's
//                   median between its 5th and 95th percentiles), its origin
//                   the run's artifact; each number shown to a few digits,
//                   in full in its title and the CSV; a BioSTEAM run's numbers
//                   are in its sections below;
//   its parameters  every value the run was bound with, in the parameter panel,
//                   read-only: a person's assumption or a model's estimate where
//                   the run set one, the library's own default elsewhere, each
//                   with its source (the service builds them from the run's
//                   artifact, `parameters_of`; no override in the project lays
//                   on a run, so the panel's scope is the run's own); the values
//                   the run set first, all of them on asking;
//   its test        the package's own test beside what this run measured, when
//                   the run set no value of its own (`output.checks`);
//   its sections    the sections a scenario run shows (RunReport), over the
//                   run's `library.run` artifact read as one case
//                   (`runViewOfRun`): the result, the cost breakdown, the
//                   streams, the equipment, the utilities and the read-back;
//   its SFF file    the record the run wrote, as the toolkit checked and scored
//                   it, and the file itself to download.
//
// A scenario is made here from the run (alpha 2.1 stage B): parameters found
// by words, each value set as the person's assumption, the scenario made and
// run in their name (POST /api/studies/scenarios, then its run), and the new
// run's page opens. A runbook is made here from the run's numbers: each output
// chosen becomes a prediction in the run's unit, measured at harvest
// (POST /api/studies/runbooks), and opens on the runbook's page, where it is
// locked.
import { SffGraph } from '@/components/SffGraph';
import { useEffect, useState } from 'react';
import { BookOpen, Download, ListChecks, Play } from 'lucide-react';
import type { ParamScope, Quantity, RegressionCheck, RunReport as EngineRunReport } from '@/data/types';
import { href, navigate } from '@/router';
import { useStore } from '@/store';
import { exportCSV } from '@/lib/csv';
import { runViewOfRun, stamp } from '@/lib/proforma';
import { trainOfRun } from '@/lib/pureos';
import { StudiesDown, downloadFlowsheet, makeRunbook, makeScenario, predictable, runReport, runScenario } from '@/lib/studies';
import { Button, Callout, Card, LinkButton, PageHeader, cx } from '@/components/ui';
import { ProvenanceBadge } from '@/components/Provenance';
import { ParameterPanel } from '@/components/ParameterPanel';
import { RunReport } from '@/screens/ProformaBiosteam';
import { regressionTable } from '@/screens/ProformaReference';
import { fmt } from '@/engine/units';

const problemOf = (e: unknown) => (e instanceof StudiesDown ? `${e.message} ${e.remedy ?? ''}`.trim() : e instanceof Error ? e.message : String(e));

/** The words a run's input's origin is said in. */
export const ORIGIN_WORDS: Record<string, string> = {
  record: 'a record',
  artifact: 'an artifact',
  'person-assumption': 'a person’s assumption',
  'model-estimate': 'a model’s estimate',
  'library-default': 'the library’s default',
  convention: 'a convention',
};

/**
 * The run's parameters in the panel, read-only: the values the run set first,
 * every parameter on asking. A run's values are its own, so the panel's scope
 * is the run's, which no override names.
 */
function Parameters({ runId, data }: { runId: string; data: ParamScope }) {
  const [all, setAll] = useState(false);
  const set = new Set(data.values.filter((v) => v.origin === 'assumption' || v.origin === 'model-estimate').map((v) => v.key));
  const shown: ParamScope = all ? data : { ...data, specs: data.specs.filter((s) => set.has(s.key)), values: data.values.filter((v) => set.has(v.key)) };
  return (
    <Card className="p-4" data-testid="run-parameters" data-set={set.size}>
      <div className="flex flex-wrap items-start justify-between gap-2 mb-1">
        <h2 className="font-serif text-section-title font-semibold">What it was bound with</h2>
        <button className="chip" aria-pressed={all} onClick={() => setAll(!all)} data-testid="run-parameters-all">
          {all ? 'The values it set' : `All ${data.specs.length} parameters`}
        </button>
      </div>
      <p className="text-caption text-ink-soft mb-2">
        {data.title}.{' '}
        {set.size === 0
          ? `It set no value of its own: each of its ${data.specs.length} parameters is the library’s default.`
          : `It set ${set.size} of its ${data.specs.length} parameters; the rest are the library’s defaults.`}
      </p>
      {shown.specs.length > 0 && <ParameterPanel scope={`run:${runId}`} data={shown} readOnly />}
    </Card>
  );
}

/** One output a run kept (`outputs.values`): its name and the quantity, in its unit, with its origin. */
interface RunOutput {
  name: string;
  quantity: Quantity;
}

/** The artifact tools whose run builds no plant, so it keeps no SFF file by design: the kinetics engine's (docs/api/runs.md). */
const NO_PLANT_TOOLS = new Set(['fermos.simulation', 'growth_forecast', 'fermos.vessel']);

/** A value as a page shows it: a number to a few significant digits (its full value in the title and the CSV), words as they are. */
const shown = (v: unknown) => (typeof v === 'number' ? fmt(v) : String(v));

/** A run's time in words: milliseconds under a tenth of a second, seconds above. */
const took = (ms: number) => (ms < 100 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(1)} s`);

/** Words a sentence follows on: a full stop added when they end with none. */
const ended = (words: string) => (/[.!?]$/.test(words.trim()) ? words.trim() : `${words.trim()}.`);

/** The outputs a contract engine's run kept. A library run keeps its `outputs.values` too, and its page shows them in its artifact's own sections. */
function runOutputs(run: EngineRunReport['run']): RunOutput[] {
  if (run.tool === 'library.run') return [];
  const values = run.outputs.values;
  if (!Array.isArray(values)) return [];
  return values.filter(
    (v): v is RunOutput =>
      typeof v === 'object' && v !== null && typeof (v as RunOutput).name === 'string' && typeof (v as RunOutput).quantity === 'object' && (v as RunOutput).quantity !== null,
  );
}

/**
 * A contract engine's or a kinetics run (docs/api/engines.md): each output with its value, its interval where it
 * carries one, its unit and its origin, the run's artifact. A forecast's value is its median, and its interval the
 * 5th to the 95th percentile.
 */
function Outputs({ report }: { report: EngineRunReport }) {
  const values = runOutputs(report.run);
  if (!values.length) return null;
  const forecast = report.run.tool === 'growth_forecast';
  const banded = values.some((v) => v.quantity.low != null || v.quantity.high != null);
  const headers = ['Output', forecast ? 'Median' : 'Value', ...(banded ? [forecast ? '5th percentile' : 'Low', forecast ? '95th percentile' : 'High'] : []), 'Unit', 'Origin'];
  const originOf = (q: Quantity) => (q.origin?.kind === 'artifact' ? `the run's artifact ${q.origin.ref ?? ''}`.trim() : (ORIGIN_WORDS[q.origin?.kind ?? ''] ?? q.origin?.kind ?? '—'));
  const ends = (q: Quantity) => (banded ? [q.low == null ? '' : String(q.low), q.high == null ? '' : String(q.high)] : []);
  // The CSV keeps every number in full; the table shows each to a few digits, in full in its title.
  const rows = values.map((v) => [v.name, String(v.quantity.value), ...ends(v.quantity), v.quantity.unit || '—', originOf(v.quantity)]);
  const band = (q: Quantity) =>
    q.low == null && q.high == null ? '—' : `${q.low == null ? '…' : shown(q.low)} to ${q.high == null ? '…' : shown(q.high)}`;
  return (
    <Card className="p-4" data-testid="run-outputs" data-engine={report.run.engine}>
      <div className="flex flex-wrap items-start justify-between gap-2 mb-1">
        <h2 className="font-serif text-section-title font-semibold">What it computed</h2>
        <button className="chip" onClick={() => exportCSV(`run-${report.run.id}-outputs.csv`, headers, rows)}>
          <Download size={12} aria-hidden /> CSV
        </button>
      </div>
      <p className="text-caption text-ink-soft mb-2">
        Each output the {report.run.engine} engine computed, in its unit, its origin the run&rsquo;s artifact: a replay computes it again from the
        basis below.
        {forecast && ' Each is the band’s median, between its 5th and 95th percentiles: a band for readings of a run like the fitted one.'}
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-caption">
          <thead>
            <tr className="border-b border-line text-ink-soft">
              {['Output', forecast ? 'Median' : 'Value', ...(banded ? [forecast ? '5th to 95th percentile' : 'Low to high'] : []), 'Unit', 'Origin'].map((h) => (
                <th key={h} className="text-left py-1 pr-2 font-medium">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {values.map((v) => (
              <tr key={v.name} className="border-b border-line/50 align-top" data-testid="run-output" data-origin={v.quantity.origin?.kind}>
                <td className="py-1 pr-2 font-num">{v.name}</td>
                <td className="py-1 pr-2 font-num" title={String(v.quantity.value)} data-testid="run-output-value">
                  {shown(v.quantity.value)}
                </td>
                {banded && (
                  <td className="py-1 pr-2 font-num" title={`${v.quantity.low ?? ''} to ${v.quantity.high ?? ''}`} data-testid="run-output-band">
                    {band(v.quantity)}
                  </td>
                )}
                <td className="py-1 pr-2 font-num">{v.quantity.unit || '—'}</td>
                <td className="py-1 pr-2">
                  {v.quantity.origin?.kind === 'artifact' && v.quantity.origin.ref ? (
                    <a className="text-accent hover:underline" href={href(`/biorepo/artifacts/${v.quantity.origin.ref}`)}>
                      {originOf(v.quantity)}
                    </a>
                  ) : (
                    originOf(v.quantity)
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

/** A train run's `train` input as a person reads it: the train's name and units, the train as data on asking. */
function TrainInput({ value, train }: { value: unknown; train: { name: string; units: number } }) {
  let held = String(value);
  try {
    held = JSON.stringify(JSON.parse(held), null, 1);
  } catch {
    // shown as kept
  }
  return (
    <details data-testid="run-input-train">
      <summary className="cursor-pointer">
        {train.name}: {train.units} unit{train.units === 1 ? '' : 's'}
      </summary>
      <pre className="text-caption whitespace-pre-wrap break-all max-h-64 overflow-auto mt-1">{held}</pre>
    </details>
  );
}

function Inputs({ report }: { report: EngineRunReport }) {
  const train = trainOfRun(report.run);
  const rows = report.run.inputs.map((i) => [
    i.name,
    String(i.quantity.value),
    i.quantity.unit || '—',
    ORIGIN_WORDS[i.quantity.origin?.kind ?? ''] ?? i.quantity.origin?.kind ?? '—',
    i.quantity.origin?.by ?? i.quantity.origin?.ref ?? '—',
    i.quantity.origin?.note ?? '',
  ]);
  const headers = ['Input', 'Value', 'Unit', 'Origin', 'By or from', 'Rests on'];
  return (
    <Card className="p-4" data-testid="run-inputs">
      <div className="flex flex-wrap items-start justify-between gap-2 mb-1">
        <h2 className="font-serif text-section-title font-semibold">Its basis</h2>
        <button className="chip" onClick={() => exportCSV(`run-${report.run.id}-inputs.csv`, headers, rows)}>
          <Download size={12} aria-hidden /> CSV
        </button>
      </div>
      <p className="text-caption text-ink-soft mb-2">Every input the run&rsquo;s computation names, each with its origin as the service computed it.</p>
      <div className="overflow-x-auto">
        <table className="w-full text-caption">
          <thead>
            <tr className="border-b border-line text-ink-soft">
              {headers.map((h) => (
                <th key={h} className="text-left py-1 pr-2 font-medium">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={r[0]} className="border-b border-line/50 align-top" data-testid="run-input" data-origin={report.run.inputs[i]?.quantity.origin?.kind}>
                {r.map((c, j) => (
                  <td key={j} className={cx('py-1 pr-2', j < 3 && 'font-num')} title={j === 1 && !(train && r[0] === 'train') ? c : undefined}>
                    {j === 1 && train && r[0] === 'train' ? (
                      <TrainInput value={report.run.inputs[i]?.quantity.value} train={train} />
                    ) : j === 1 ? (
                      shown(report.run.inputs[i]?.quantity.value ?? c)
                    ) : (
                      c
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function PackageTest({ report }: { report: EngineRunReport }) {
  const o = (report.artifact?.output ?? {}) as Record<string, unknown>;
  const checks = Array.isArray(o.checks) ? (o.checks as RegressionCheck[]) : [];
  const note = typeof o.regressionNote === 'string' ? o.regressionNote : null;
  if (!checks.length && !note) return null;
  const t = regressionTable(checks.map((c) => ({ ...c })));
  const within = checks.filter((c) => c.within).length;
  return (
    <Card className="p-4" data-testid="run-package-test">
      <h2 className="font-serif text-section-title font-semibold mb-1">Held to its package&rsquo;s own test</h2>
      {checks.length ? (
        <>
          <p className="text-caption text-ink-soft mb-2" data-testid="run-package-test-count">
            {within} of {checks.length} values within the package&rsquo;s tolerance, each read from the run&rsquo;s artifact.
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-caption">
              <thead>
                <tr className="border-b border-line text-ink-soft">
                  {t.headers.map((h, i) => (
                    <th key={h} className={i < 3 ? 'text-left py-1 pr-2 font-medium' : 'text-right py-1 px-1.5 font-medium'}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {t.rows.map((r, i) => (
                  <tr key={checks[i].expression} className="border-b border-line/50">
                    {r.map((c, j) => (
                      <td key={j} className={cx(j < 3 ? 'py-1 pr-2' : 'py-1 px-1.5 text-right font-num', j === 7 && !checks[i].within && 'text-signal-warn')}>
                        {c}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : (
        <p className="text-body text-ink-soft">{note}.</p>
      )}
    </Card>
  );
}

function FlowsheetCard({ report }: { report: EngineRunReport }) {
  const f = report.flowsheet;
  const [problem, setProblem] = useState<string | null>(null);
  if (!f)
    return report.run.sffRefused ? (
      <Card className="p-4" data-testid="run-sff">
        <h2 className="font-serif text-section-title font-semibold mb-1">Its SFF file</h2>
        {NO_PLANT_TOOLS.has(report.run.tool) ? (
          <p className="text-body text-ink-soft" data-testid="run-sff-none">This run keeps no SFF file: {ended(report.run.sffRefused)}</p>
        ) : (
          <p className="text-body text-signal-warn">No SFF file could be written: {report.run.sffRefused}</p>
        )}
      </Card>
    ) : null;
  const earned = Object.entries(f.tags)
    .filter(([, t]) => t.earned)
    .map(([k]) => k);
  return (
    <Card className="p-4" data-testid="run-sff" data-valid={f.validation.valid ? 'true' : 'false'}>
      <div className="flex flex-wrap items-start justify-between gap-2 mb-1">
        <h2 className="font-serif text-section-title font-semibold">Its SFF file</h2>
        <button
          className="chip"
          data-testid="run-sff-download"
          onClick={() => {
            setProblem(null);
            downloadFlowsheet(f.id).catch((e: unknown) => setProblem(problemOf(e)));
          }}
        >
          <Download size={12} aria-hidden /> {f.id}.sff.json
        </button>
      </div>
      <p className="text-body">
        {f.validation.valid ? 'Valid' : 'Not valid'} against the schema the toolkit ships (SFF {f.validation.schemaVersion}), scored{' '}
        <span className="font-num">{f.completeness.score == null ? '—' : f.completeness.score.toFixed(2)}</span> for what BioSTEAM needs to rebuild,
        simulate and cost the plant; {f.units} units and {f.streams} streams, checked by {f.toolkit}.
        {earned.length > 0 && <> Tags it earns: {earned.join(', ')}.</>}
      </p>
      <p className="text-caption text-ink-soft mt-1">
        Record <span className="font-num">{f.id}</span>, sha256 <span className="font-num">{f.sha256.slice(0, 16)}…</span>, written {stamp(f.createdAt)}.{' '}
        <a className="text-accent hover:underline" href={href(`/flowsheets/${f.id}`)}>
          Its page
        </a>
      </p>
      {problem && <p className="text-caption text-signal-warn mt-1">{problem}</p>}
      {f.graph && (
        <div className="mt-3">
          <SffGraph graph={f.graph} title="The plant the run built" />
        </div>
      )}
    </Card>
  );
}

/** How many matching parameters the finder lists at once. */
const FOUND_ROWS = 12;

interface Setting {
  key: string;
  label: string;
  unit: string;
  /** As the person typed it; read as a number when the scenario is made. */
  value: string;
  /** What the value rests on, in the person's words. */
  note: string;
}

/**
 * A scenario from this run (alpha 2.1 stage B): the person finds parameters
 * of the run by words, sets each one's value as their own assumption, and the
 * scenario is made (POST /api/studies/scenarios) and run (…/{id}/run) in their
 * name. The plant and its configuration are the run's; every value the person
 * leaves alone stays the package's own.
 */
function MakeScenario({ report }: { report: EngineRunReport }) {
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
  if (run.status !== 'done' || !scope) return null;
  const valueOf = new Map(scope.values.map((v) => [v.key, v.value]));
  const numeric = scope.specs.filter((s) => !s.choices && typeof valueOf.get(s.key) === 'number');
  const wanted = words.toLowerCase().split(/\s+/).filter(Boolean);
  const taken = new Set(settings.map((s) => s.key));
  const found = wanted.length
    ? numeric.filter((s) => !taken.has(s.key) && wanted.every((w) => `${s.key} ${s.label}`.toLowerCase().includes(w)))
    : [];
  const add = (key: string) => {
    const spec = numeric.find((s) => s.key === key);
    if (!spec) return;
    setSettings((list) => [...list, { key, label: spec.label, unit: spec.unit, value: String(valueOf.get(key) ?? ''), note: '' }]);
  };
  const change = (key: string, patch: Partial<Setting>) => setSettings((list) => list.map((s) => (s.key === key ? { ...s, ...patch } : s)));
  const make = () => {
    const at = new Date().toISOString();
    const bad = settings.find((s) => s.value.trim() === '' || !Number.isFinite(Number(s.value)));
    if (bad) {
      setProblem(`${bad.label}: a value is one number, in ${bad.unit || 'the parameter’s own terms'}.`);
      return;
    }
    setBusy(true);
    setProblem(null);
    makeScenario({
      title: title.trim(),
      plant: run.plant,
      configuration: run.configuration ?? null,
      values: settings.map((s) => ({
        key: s.key,
        quantity: {
          value: Number(s.value),
          unit: s.unit,
          origin: { kind: 'person-assumption', by: reviewer, at, note: s.note.trim() || note.trim() || null },
        },
      })),
      note: note.trim() || null,
      by: reviewer,
    })
      .then((scenario) => {
        setMade(scenario.id);
        return runScenario(scenario.id, reviewer);
      })
      .then((rep) => navigate(`/proforma/runs/${rep.run.id}`))
      .catch((e: unknown) => setProblem(problemOf(e)))
      .finally(() => setBusy(false));
  };
  return (
    <Card className="p-4" data-testid="run-make-scenario">
      <h2 className="font-serif text-section-title font-semibold mb-1">A scenario from this run</h2>
      <p className="text-caption text-ink-soft mb-2">
        Find a parameter by its words, set its value as your assumption, and the scenario is made on {run.plant}
        {run.configuration ? ` (${run.configuration})` : ''} and run in your name. Each value starts at this run&rsquo;s; every parameter you leave alone
        stays the package&rsquo;s own.
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
        <table className="w-full text-caption mb-2" data-testid="scenario-settings">
          <tbody>
            {settings.map((s) => (
              <tr key={s.key} className="border-b border-line/50 align-top" data-testid="scenario-setting" data-key={s.key}>
                <td className="py-1 pr-2">{s.label}</td>
                <td className="py-1 pr-2">
                  <input
                    className="input text-caption font-num w-28"
                    inputMode="decimal"
                    aria-label={`Your value for ${s.label}`}
                    value={s.value}
                    onChange={(e) => change(s.key, { value: e.target.value })}
                  />{' '}
                  <span className="font-num text-ink-soft">{s.unit}</span>
                </td>
                <td className="py-1 pr-2">
                  <input
                    className="input text-caption w-full"
                    aria-label={`What ${s.label} rests on`}
                    placeholder="What it rests on (optional)"
                    value={s.note}
                    onChange={(e) => change(s.key, { note: e.target.value })}
                  />
                </td>
                <td className="py-1">
                  <button className="chip" onClick={() => setSettings((list) => list.filter((x) => x.key !== s.key))} aria-label={`Leave ${s.label} as the run's`}>
                    Leave
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <input className="input text-body" aria-label="The scenario's title" placeholder="What the scenario asks" value={title} onChange={(e) => setTitle(e.target.value)} />
        <input className="input text-body flex-1 min-w-48" aria-label="What the scenario rests on" placeholder="What it rests on, in words" value={note} onChange={(e) => setNote(e.target.value)} />
        <Button variant="primary" disabled={busy || !reviewer || settings.length === 0 || !title.trim()} onClick={make} data-testid="run-make-scenario-go">
          <Play size={14} /> {busy ? 'Running…' : 'Make the scenario and run it'}
        </Button>
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
    </Card>
  );
}

function MakeRunbook({ report }: { report: EngineRunReport }) {
  const reviewer = useStore((s) => s.reviewer).trim();
  const hydrate = useStore((s) => s.hydrateProjectState);
  const numbers = predictable(report.run, report.artifact);
  const [chosen, setChosen] = useState<Record<string, string>>({});
  const [title, setTitle] = useState(`${report.run.plant} at the bench`);
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  if (report.run.status !== 'done' || numbers.length === 0) return null;
  const picked = numbers.filter((n) => n.output in chosen);
  const make = () => {
    setBusy(true);
    setProblem(null);
    makeRunbook({ title: title.trim(), runId: report.run.id, by: reviewer, predict: picked.map((n) => ({ output: n.output, label: chosen[n.output].trim() || n.output })) })
      .then(async (rb) => {
        await hydrate();
        navigate(`/runbooks/${rb.id}`);
      })
      .catch((e: unknown) => setProblem(problemOf(e)))
      .finally(() => setBusy(false));
  };
  return (
    <Card className="p-4" data-testid="run-make-runbook">
      <h2 className="font-serif text-section-title font-semibold mb-1">A runbook from this run</h2>
      <p className="text-caption text-ink-soft mb-2">
        Each number chosen becomes a prediction in the run&rsquo;s unit, its basis this run, measured at harvest. The runbook opens as a draft; lock it on
        its page before the bench starts.
      </p>
      <ul className="space-y-1 mb-2">
        {numbers.map((n) => (
          <li key={n.output} className="flex flex-wrap items-center gap-2 text-caption">
            <label className="flex items-center gap-1.5">
              <input
                type="checkbox"
                checked={n.output in chosen}
                onChange={(e) =>
                  setChosen((c) => {
                    const next = { ...c };
                    if (e.target.checked) next[n.output] = n.output;
                    else delete next[n.output];
                    return next;
                  })
                }
              />
              <span className="font-num">{n.output}</span>
            </label>
            <span className="font-num text-ink-soft">
              {String(n.value)} {n.unit}
            </span>
            {n.output in chosen && (
              <input
                className="input text-caption"
                aria-label={`What the bench calls ${n.output}`}
                value={chosen[n.output]}
                onChange={(e) => setChosen((c) => ({ ...c, [n.output]: e.target.value }))}
              />
            )}
          </li>
        ))}
      </ul>
      <div className="flex flex-wrap items-center gap-2">
        <input className="input text-body" aria-label="The runbook's title" value={title} onChange={(e) => setTitle(e.target.value)} />
        <Button variant="primary" disabled={busy || !reviewer || picked.length === 0 || !title.trim()} onClick={make} data-testid="run-make-runbook-go">
          <ListChecks size={14} /> Make the runbook
        </Button>
      </div>
      {!reviewer && <p className="text-caption text-ink-soft mt-1">A runbook is made in a person&rsquo;s name: set yours in Settings first.</p>}
      {problem && <p className="text-caption text-signal-warn mt-1">{problem}</p>}
    </Card>
  );
}

export default function ProformaRun({ runId }: { runId: string }) {
  const [report, setReport] = useState<EngineRunReport | null>(null);
  const [problem, setProblem] = useState<string | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    setReport(null);
    setProblem(null);
    runReport(runId, ctrl.signal)
      .then(setReport)
      .catch((e: unknown) => !ctrl.signal.aborted && setProblem(problemOf(e)));
    return () => ctrl.abort();
  }, [runId]);

  const run = report?.run ?? null;
  const view = report?.artifact ? runViewOfRun(report.artifact) : null;
  const price = (report?.artifact?.output?.price ?? {}) as Record<string, unknown>;
  const product = typeof price.product === 'string' ? price.product : 'the product';
  const train = run ? trainOfRun(run) : null;
  const where = run ? (train ? `${train.name} (${run.plant})` : run.plant + (run.configuration ? ` (${run.configuration})` : '')) : runId;

  return (
    <div data-testid="proforma-run" data-run={runId} data-status={run?.status ?? ''}>
      <PageHeader
        eyebrow={<>engine run · <span className="normal-case font-num">{runId}</span></>}
        title={where}
        subtitle={
          run && (
            <span className="flex flex-wrap items-center gap-2">
              {run.provenance && <ProvenanceBadge p={run.provenance} />}
              <span>
                {run.status === 'done' ? 'Run' : 'Refused'} for {run.by}, {stamp(run.at)}
                {run.durationMs != null && <>, in {took(run.durationMs)}</>}
                {run.scenarioId && (
                  <>
                    {' '}
                    · asked for by scenario <span className="font-num">{run.scenarioId}</span>
                  </>
                )}
                .
              </span>
            </span>
          )
        }
        actions={
          <>
            {run?.artifactId && (
              <LinkButton to={`/biorepo/artifacts/${run.artifactId}`}>Its artifact</LinkButton>
            )}
            {train && <LinkButton to={`/pureos/train/${encodeURIComponent(train.id)}`}>Its train on pureOS</LinkButton>}
            <LinkButton to="/proforma/studies">
              <BookOpen size={14} /> Studies
            </LinkButton>
          </>
        }
      />

      {problem && (
        <div className="mb-4">
          <Callout kind="warn">
            <span data-testid="run-problem">{problem}</span>
          </Callout>
        </div>
      )}

      {report && run && (
        <div className="space-y-4">
          {run.status === 'refused' && (
            <Callout kind="warn" title={run.engine === 'biosteam' ? 'The plant refused these values' : `The ${run.engine} engine refused these values`}>
              <span data-testid="run-refused">{ended(run.refused ?? '')}</span> The receipt is kept with the run, and no artifact or SFF file was written.
            </Callout>
          )}
          {report.parameters && <Parameters runId={run.id} data={report.parameters} />}
          <Outputs report={report} />
          <Inputs report={report} />
          <PackageTest report={report} />
          {view && (
            <RunReport
              view={view}
              priceBasis={`USD per kg of ${product}`}
              labels={{}}
              unitLabels={{}}
              scenarioId={run.scenarioId ?? ''}
              csvName={`run-${run.id}`}
              oneCase
            />
          )}
          <FlowsheetCard report={report} />
          <MakeScenario key={run.id} report={report} />
          <MakeRunbook report={report} />
          <p className="text-caption text-ink-soft">
            The run as the service keeps it: <a className="font-num underline underline-offset-2" href={href('/proforma/studies')}>Studies</a> lists every run
            of the project, and its export package holds this one.
          </p>
        </div>
      )}
    </div>
  );
}
