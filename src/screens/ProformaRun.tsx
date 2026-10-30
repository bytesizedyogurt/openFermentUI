// An engine run's page (execution prompt §7.4, §9.1 step 5): /proforma/runs/:id.
//
// One run of a library plant or an openFerment flowsheet, as the service kept
// it (GET /api/runs/{id}, engine/runs.py). It reads, and never types:
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
// A runbook is made here from the run's numbers: each output chosen becomes a
// prediction in the run's unit, measured at harvest (POST /api/studies/runbooks),
// and opens on the runbook's page, where it is locked.
import { useEffect, useState } from 'react';
import { BookOpen, Download, ListChecks } from 'lucide-react';
import type { ParamScope, RegressionCheck, RunReport as EngineRunReport } from '@/data/types';
import { href, navigate } from '@/router';
import { useStore } from '@/store';
import { exportCSV } from '@/lib/csv';
import { runViewOfRun, stamp } from '@/lib/proforma';
import { StudiesDown, downloadFlowsheet, makeRunbook, predictable, runReport } from '@/lib/studies';
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
        Record <span className="font-num">{f.id}</span>, sha256 <span className="font-num">{f.sha256.slice(0, 16)}…</span>, written {stamp(f.createdAt)}.
      </p>
      {problem && <p className="text-caption text-signal-warn mt-1">{problem}</p>}
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
        eyebrow={`engine run · ${runId}`}
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
