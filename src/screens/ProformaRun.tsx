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
//   its diagnostics what a contract engine's computation reported about
//                   itself beside its outputs (the time it took, the
//                   iterations it made), kept with the run and left
//                   uncompared by a replay;
//   its parameters  every value the run was bound with, in the parameter panel,
//                   read-only: a person's assumption or a model's estimate where
//                   the run set one, the library's own default elsewhere, each
//                   with its source (the service builds them from the run's
//                   artifact, `parameters_of`; no override in the project lays
//                   on a run, so the panel's scope is the run's own); the values
//                   the run set first, all of them on asking;
//   its test        the package's own test beside what this run measured, when
//                   the run set no value of its own (`output.checks`);
//   its sections    the sections a scenario run shows (RunReport): over a
//                   library run's `library.run` artifact read as one case
//                   (`runViewOfRun`), the result, the cost breakdown, the
//                   streams, the equipment, the utilities and the read-back;
//                   over a Proforma scenario's `proforma.run` artifact, a run
//                   of the biosteam engine since alpha 2.2 (D6), those and
//                   its sensitivity and price distribution over its samples,
//                   as the scenario's own page shows them (`runViewOfArtifact`);
//   its SFF file    the record the run wrote, as the toolkit checked and scored
//                   it, and the file itself to download.
//
// A scenario is made here from the run (alpha 2.1 stage B; alpha 2.2 C.5):
// NewScenarioDialog, opened from the run, finds parameters by words and sets
// each one to the person's own value or to a reading deposited at the bench,
// makes the scenario and runs it in their name (POST /api/studies/scenarios,
// then its run), and the new run's page opens. A value a reading set reads
// here as a measurement in words, linked to the deposition its reading was
// recorded in (DepositionDetail); its parameter's chip says measured, and a
// run resting on readings and the package's defaults alone is `measured`.
// A runbook is made here from the run's numbers: each output
// chosen becomes a prediction in the run's unit, measured at harvest
// (POST /api/studies/runbooks), and opens on the runbook's page, where it is
// locked.
import { SffGraph } from '@/components/SffGraph';
import { useEffect, useState, type ReactNode } from 'react';
import { BookOpen, Download, ListChecks, Play } from 'lucide-react';
import type { FlowsheetInfo, ParamScope, Quantity, RegressionCheck, RunReport as EngineRunReport } from '@/data/types';
import { href, navigate } from '@/router';
import { useStore } from '@/store';
import { exportCSV } from '@/lib/csv';
import { RUN_TOOL, baseCaseRefusal, proformaShelf, regressionTable, runViewOfArtifact, runViewOfRun, stamp } from '@/lib/proforma';
import { trainOfRun } from '@/lib/pureos';
import { StudiesDown, downloadFlowsheet, makeRunbook, predictable, runReport } from '@/lib/studies';
import { Button, Callout, Card, LinkButton, PageHeader, cx } from '@/components/ui';
import { ProvenanceBadge } from '@/components/Provenance';
import { ParameterPanel } from '@/components/ParameterPanel';
import { NewScenarioDialog } from '@/components/NewScenarioDialog';
import { ReadingOrigin, readingNote } from '@/components/ReadingOrigin';
import { RunReport, inputLabels } from '@/screens/ProformaBiosteam';
import { fmt } from '@/engine/units';

const problemOf = (e: unknown) => (e instanceof StudiesDown ? `${e.message} ${e.remedy ?? ''}`.trim() : e instanceof Error ? e.message : String(e));

/** The words a run's input's origin is said in. */
export const ORIGIN_WORDS: Record<string, string> = {
  record: 'a record',
  artifact: 'an artifact',
  'person-assumption': 'a person’s assumption',
  'model-estimate': 'a model’s estimate',
  measurement: 'a reading deposited at the bench',
  'library-default': 'the library’s default',
  convention: 'a convention',
};

/** The origins of a value a run set for itself (basis.SET_PARAM_ORIGINS): a person's, a model's, a deposition's reading. */
const SET_HERE = new Set(['assumption', 'model-estimate', 'measurement']);

/**
 * The run's parameters in the panel, read-only: the values the run set first,
 * every parameter on asking. A run's values are its own, so the panel's scope
 * is the run's, which no override names.
 */
function Parameters({ runId, data }: { runId: string; data: ParamScope }) {
  const [all, setAll] = useState(false);
  const set = new Set(data.values.filter((v) => SET_HERE.has(v.origin)).map((v) => v.key));
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

/**
 * A train run's file, which waits on the toolkit: the SFF schema it ships requires every file's TEA year, and a train
 * carries no TEA, so every train run keeps those words as its `sffRefused` (docs/PROGRESS.md, Known debts). Said in
 * plain ink, as a kinetics run's none is; any other refusal of a file is a failure, said as one.
 */
const fileWaitsOnToolkit = (run: EngineRunReport['run']) => run.tool === 'pureos.train_run' && /TEA_year/.test(run.sffRefused ?? '');

/**
 * BioSTEAM's runs, whose page shows their numbers in their artifact's own sections: their `outputs.values`, the
 * values a comparison reads, fold under the outputs card's summary.
 */
const FOLDED_OUTPUTS = new Set(['library.run', RUN_TOOL]);

/** A value as a page shows it: a number to a few significant digits (its full value in the title and the CSV), words as they are. */
const shown = (v: unknown) => (typeof v === 'number' ? fmt(v) : String(v));

/**
 * A basis note as the page shows it, the build's own decision tags dropped: a leading `D8: `, and a trailing
 * parenthesis naming a decision, a build document or a rule's constant (`(D9)`, `(OF-BLD-020 §3.2 added the
 * field)`, `(Appendix 2 §A)`, `(CARBON_RULE)`). The basis keeps the words whole, its id hashing them, and so does
 * the CSV.
 */
const LEADING_TAG = /^D\d+:\s+/;
const TRAILING_TAG = /\s*\((?:D\d+\b[^)]*|OF-[A-Z]+-\d+[^)]*|Appendix \d+[^)]*|[A-Z][A-Z0-9]*_[A-Z0-9_]+)\)\s*$/;
export const plainNote = (note: string) => note.replace(LEADING_TAG, '').replace(TRAILING_TAG, '').trim();

/** A run's time in words: milliseconds under a tenth of a second, seconds above. */
const took = (ms: number) => (ms < 100 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(1)} s`);

/** Words a sentence follows on: a full stop added when they end with none. */
const ended = (words: string) => (/[.!?]$/.test(words.trim()) ? words.trim() : `${words.trim()}.`);

/** The outputs a run kept (`outputs.values`), every engine's: the values a comparison of it reads. */
function runOutputs(run: EngineRunReport['run']): RunOutput[] {
  const values = run.outputs.values;
  if (!Array.isArray(values)) return [];
  return values.filter(
    (v): v is RunOutput =>
      typeof v === 'object' && v !== null && typeof (v as RunOutput).name === 'string' && typeof (v as RunOutput).quantity === 'object' && (v as RunOutput).quantity !== null,
  );
}

/**
 * Any engine's run (docs/api/engines.md): each output with its value, its interval where it carries one, its unit
 * and its origin, the run's artifact. A forecast's value is its median, and its interval the 5th to the 95th
 * percentile. A BioSTEAM run's table folds under its summary, its numbers shown in the sections below as well.
 */
function Outputs({ report }: { report: EngineRunReport }) {
  const values = runOutputs(report.run);
  if (!values.length) return null;
  const folded = FOLDED_OUTPUTS.has(report.run.tool);
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
        {folded && ' These are the values a comparison of this run reads; the sections below show the run’s price, its tables and its costs.'}
      </p>
      <OutputsTable folded={folded} count={values.length}>
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
      </OutputsTable>
    </Card>
  );
}

/**
 * What a run's computation reported about itself (`run.diagnostics`: the time it took, the iterations it made), as its
 * engine's worker answered it beside the outputs. The run keeps them from the computation that made it; a replay
 * compares the outputs alone and leaves these uncompared.
 */
function Diagnostics({ run }: { run: EngineRunReport['run'] }) {
  const reported = run.diagnostics ?? [];
  if (!reported.length) return null;
  return (
    <Card className="p-4" data-testid="run-diagnostics" data-engine={run.engine}>
      <h2 className="font-serif text-section-title font-semibold mb-1">What the computation reported about itself</h2>
      <p className="text-caption text-ink-soft mb-2">
        Each value the {run.engine} engine&rsquo;s computation reported beside its outputs, kept with the run as its first computation
        answered it. A replay compares the outputs alone and leaves these uncompared.
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-caption">
          <thead>
            <tr className="border-b border-line text-ink-soft">
              {['Diagnostic', 'Value', 'Unit'].map((h) => (
                <th key={h} className="text-left py-1 pr-2 font-medium">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {reported.map((d) => (
              <tr key={d.name} className="border-b border-line/50 align-top" data-testid="run-diagnostic">
                <td className="py-1 pr-2 font-num">{d.name}</td>
                <td className="py-1 pr-2 font-num" title={String(d.value)} data-testid="run-diagnostic-value">
                  {shown(d.value)}
                </td>
                <td className="py-1 pr-2 font-num">{d.unit || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

/** The outputs' table, open for a run whose page shows it alone, folded under its summary for a BioSTEAM run's. */
function OutputsTable({ folded, count, children }: { folded: boolean; count: number; children: ReactNode }) {
  if (!folded) return <>{children}</>;
  return (
    <details data-testid="run-outputs-folded">
      <summary className="cursor-pointer text-caption">
        Every value it kept as an output ({count}), each with its unit and origin
      </summary>
      {children}
    </details>
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
  const reading = (i: EngineRunReport['run']['inputs'][number]) => i.quantity.origin?.kind === 'measurement';
  const rows = report.run.inputs.map((i) => [
    i.name,
    String(i.quantity.value),
    i.quantity.unit || '—',
    ORIGIN_WORDS[i.quantity.origin?.kind ?? ''] ?? i.quantity.origin?.kind ?? '—',
    i.quantity.origin?.by ?? i.quantity.origin?.ref ?? '—',
    // A reading's time stands in its Origin cell once; the note keeps the conversion and the person's words.
    reading(i) ? readingNote(i.quantity.origin?.note) : (i.quantity.origin?.note ?? ''),
  ]);
  // The file names each reading beside its depositor, and keeps the basis's note whole.
  const csvRows = report.run.inputs.map((i, n) =>
    reading(i)
      ? [...rows[n].slice(0, 4), `${i.quantity.origin?.by ?? 'nobody named'}, reading ${i.quantity.origin?.ref ?? ''}`, i.quantity.origin?.note ?? '']
      : rows[n],
  );
  const headers = ['Input', 'Value', 'Unit', 'Origin', 'By or from', 'Rests on'];
  return (
    <Card className="p-4" data-testid="run-inputs">
      <div className="flex flex-wrap items-start justify-between gap-2 mb-1">
        <h2 className="font-serif text-section-title font-semibold">Its basis</h2>
        <button className="chip" onClick={() => exportCSV(`run-${report.run.id}-inputs.csv`, headers, csvRows)}>
          <Download size={12} aria-hidden /> CSV
        </button>
      </div>
      <p className="text-caption text-ink-soft mb-2">
        Every input the run&rsquo;s computation names, each with its origin as the service computed it; a reading deposited at the bench links to
        the deposition it was recorded in.
      </p>
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
                  <td
                    key={j}
                    className={cx('py-1 pr-2', j < 3 && 'font-num', j === 2 && 'whitespace-nowrap')}
                    title={j === 1 && !(train && r[0] === 'train') ? c : undefined}
                  >
                    {j === 1 && train && r[0] === 'train' ? (
                      <TrainInput value={report.run.inputs[i]?.quantity.value} train={train} />
                    ) : j === 1 ? (
                      shown(report.run.inputs[i]?.quantity.value ?? c)
                    ) : j === 3 && report.run.inputs[i]?.quantity.origin?.kind === 'measurement' ? (
                      <ReadingOrigin origin={report.run.inputs[i].quantity.origin!} />
                    ) : j === 5 ? (
                      <span title={c}>{plainNote(c)}</span>
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
        ) : fileWaitsOnToolkit(report.run) ? (
          <p className="text-body text-ink-soft" data-testid="run-sff-waits">This run keeps no SFF file yet: {ended(report.run.sffRefused)}</p>
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

/**
 * A scenario from this run (alpha 2.1 stage B; alpha 2.2 C.5): NewScenarioDialog, opened on the run, finds its
 * parameters by words and sets each one to the person's own value or to a reading deposited at the bench, makes the
 * scenario (POST /api/studies/scenarios) and runs it (…/{id}/run) in their name. The plant and its configuration
 * are the run's; every value the person leaves alone stays the package's own.
 */
function MakeScenario({ report }: { report: EngineRunReport }) {
  const reviewer = useStore((s) => s.reviewer).trim();
  const [open, setOpen] = useState(false);
  const run = report.run;
  if (run.status !== 'done' || !report.parameters) return null;
  return (
    <Card className="p-4" data-testid="run-make-scenario">
      <h2 className="font-serif text-section-title font-semibold mb-1">A scenario from this run</h2>
      <p className="text-caption text-ink-soft mb-2">
        Set some of this run&rsquo;s parameters, each to your own value or to a reading a person deposited at the bench, and the scenario is made on{' '}
        {run.plant}
        {run.configuration ? ` (${run.configuration})` : ''} and run in your name. Every parameter you leave alone stays the package&rsquo;s own.
      </p>
      <Button variant="primary" onClick={() => setOpen(true)} data-testid="run-make-scenario-open">
        <Play size={14} /> New scenario from this run
      </Button>
      {!reviewer && <p className="text-caption text-ink-soft mt-1">A scenario is made in a person&rsquo;s name: set yours in Settings first.</p>}
      <NewScenarioDialog open={open} onClose={() => setOpen(false)} fromRun={report} />
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
  const art = report?.artifact ?? null;
  // A Proforma scenario's run names its inputs as the shelf's flowsheet does, and its scenario by name.
  const [shelf, setShelf] = useState<FlowsheetInfo[] | null>(null);
  const isScenarioRun = art?.tool === RUN_TOOL;
  useEffect(() => {
    if (!isScenarioRun) return;
    const ctrl = new AbortController();
    proformaShelf(ctrl.signal).then(setShelf, () => !ctrl.signal.aborted && setShelf([]));
    return () => ctrl.abort();
  }, [isScenarioRun]);
  const proformaScenarios = useStore((s) => s.scenarios);
  const ownScenario = run?.scenarioId ? (proformaScenarios.find((s) => s.id === run.scenarioId) ?? null) : null;
  const flowsheetInfo = isScenarioRun ? (shelf?.find((f) => f.id === run?.plant) ?? null) : null;
  // A library run reads as one case; a Proforma scenario's run as the scenario's page reads it, with its samples.
  const view = art ? (runViewOfRun(art) ?? runViewOfArtifact(art)) : null;
  const scenarioRun = art?.tool === RUN_TOOL;
  const price = (art?.output?.price ?? {}) as Record<string, unknown>;
  const product = typeof price.product === 'string' ? price.product : 'the product';
  // A Proforma run's price is per unit of the basis its TEA states (the run's outputs.values say the same).
  const priceBasis = scenarioRun
    ? view?.tables.tea?.basis
      ? `USD per ${view.tables.tea.basis}`
      : 'USD per unit of the basis its flowsheet states'
    : `USD per kg of ${product}`;
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
              {run.provenance && (
                <span data-testid="run-provenance" data-provenance={run.provenance}>
                  <ProvenanceBadge p={run.provenance} />
                </span>
              )}
              <span>
                {run.status === 'done' ? 'Run' : 'Refused'} for {run.by}, {stamp(run.at)}
                {run.durationMs != null && <>, in {took(run.durationMs)}</>}
                {run.scenarioId && ownScenario && (
                  <>
                    {' '}
                    · asked for by scenario{' '}
                    <a className="underline underline-offset-2 hover:text-accent" href={href(`/proforma/scenario/${encodeURIComponent(ownScenario.id)}`)}>
                      {ownScenario.name || ownScenario.id}
                    </a>
                  </>
                )}
                {run.scenarioId && !ownScenario && (
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
          {scenarioRun && run.status === 'done' && !(Array.isArray(run.outputs.values) && run.outputs.values.length > 0) && (
            <Callout kind="warn" title="This run holds no price">
              <span data-testid="run-holds-no-price">
                No sample the flowsheet could hold priced it
                {typeof art?.output?.baseInfeasible === 'string' && art.output.baseInfeasible
                  ? `; its base case could not run: ${baseCaseRefusal(art.output.baseInfeasible)}`
                  : ''}
                . The run is kept with its basis, so the same values asked again answer from it.
              </span>
            </Callout>
          )}
          {report.parameters && <Parameters runId={run.id} data={report.parameters} />}
          <Outputs report={report} />
          <Diagnostics run={run} />
          <Inputs report={report} />
          <PackageTest report={report} />
          {view && (
            <RunReport
              view={view}
              priceBasis={priceBasis}
              labels={inputLabels(null, flowsheetInfo)}
              unitLabels={inputLabels(null, flowsheetInfo, true)}
              scenarioId={run.scenarioId ?? ''}
              csvName={`run-${run.id}`}
              oneCase={!scenarioRun}
              sffRecord={report.flowsheet?.id ?? null}
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
