// An engine run's page (execution prompt §7.4, §9.1 step 5): /proforma/runs/:id.
//
// One run of a library plant or an openFerment flowsheet, as the service kept
// it (GET /api/runs/{id}, engine/runs.py). What it reads:
//
//   the run         its plant and configuration, its status and provenance,
//                   who asked and when, the study scenario that asked for it;
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
import type { ParamScope, RegressionCheck, RunReport as EngineRunReport } from '@/data/types';
import { href, navigate } from '@/router';
import { useStore } from '@/store';
import { exportCSV } from '@/lib/csv';
import { runViewOfRun, stamp } from '@/lib/proforma';
import { StudiesDown, downloadFlowsheet, makeRunbook, makeScenario, predictable, runReport, runScenario } from '@/lib/studies';
import { Button, Callout, Card, LinkButton, PageHeader, cx } from '@/components/ui';
import { ProvenanceBadge } from '@/components/Provenance';
import { ParameterPanel } from '@/components/ParameterPanel';
import { RunReport } from '@/screens/ProformaBiosteam';
import { regressionTable } from '@/screens/ProformaReference';

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

function Inputs({ report }: { report: EngineRunReport }) {
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
            {rows.map((r) => (
              <tr key={r[0]} className="border-b border-line/50 align-top" data-testid="run-input" data-origin={report.run.inputs.find((i) => i.name === r[0])?.quantity.origin?.kind}>
                {r.map((c, j) => (
                  <td key={j} className={cx('py-1 pr-2', j < 3 && 'font-num')}>
                    {c}
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
        <p className="text-body text-signal-warn">No SFF file could be written: {report.run.sffRefused}</p>
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
  const numbers = predictable(report.artifact);
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
  const where = run ? run.plant + (run.configuration ? ` (${run.configuration})` : '') : runId;

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
                {run.durationMs != null && <>, in {(run.durationMs / 1000).toFixed(1)} s</>}
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
            <Callout kind="warn" title="The plant refused these values">
              <span data-testid="run-refused">{run.refused}</span> The receipt is kept with the run, and no artifact or SFF file was written.
            </Callout>
          )}
          {report.parameters && <Parameters runId={run.id} data={report.parameters} />}
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
