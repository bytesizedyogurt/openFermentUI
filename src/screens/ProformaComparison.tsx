// A comparison's page (execution prompt §9.1 step 5): /proforma/comparisons/:id.
//
// Engine runs set side by side, as one `study.comparison` artifact computed
// over the runs' artifacts (GET /api/studies/comparisons/{id},
// studies/comparisons.py). It reads, and never types or derives:
//
//   the runs     in the order the comparison reads them, each a link to its
//                page; every change is reckoned from the first;
//   the figure   how far each later run moves each output from the first, one
//                Tornado row per output (the figure grammar's frame: the table
//                twin, CSV, the comparison's provenance on every bar), each
//                change the artifact's own (`rows[].change`), drawn in percent;
//   the rows     every number of the price block and of a flowsheet's outputs,
//                in its unit, each run's value and its change;
//   the values   every value any run set for itself, each run's with its
//                origin, the library's default where a run set none.
import { useEffect, useState } from 'react';
import { BookOpen, Download } from 'lucide-react';
import type { ComparisonReport } from '@/data/types';
import { href } from '@/router';
import { exportCSV } from '@/lib/csv';
import { stamp } from '@/lib/proforma';
import { StudiesDown, comparisonReport } from '@/lib/studies';
import { Callout, Card, LinkButton, PageHeader } from '@/components/ui';
import { ProvenanceBadge } from '@/components/Provenance';
import { Tornado, type TornadoRow } from '@/components/figures';
import { ORIGIN_WORDS } from '@/screens/ProformaRun';

const problemOf = (e: unknown) => (e instanceof StudiesDown ? `${e.message} ${e.remedy ?? ''}`.trim() : e instanceof Error ? e.message : String(e));

interface ComparedRun {
  artifactId: string;
  plant: string;
  configuration: string | null;
  provenance: string;
}
interface ComparedRow {
  key: string;
  unit: string | null;
  values: (number | string | null)[];
  change: (number | null)[];
}
interface ComparedValue {
  key: string;
  values: { value: number | string | null; unit: string; origin: string; by: string | null }[];
}

/** The artifact's output as the comparison computed it (studies/comparisons.py `_compare`). */
export function comparedOf(report: ComparisonReport): { runs: ComparedRun[]; rows: ComparedRow[]; values: ComparedValue[] } {
  const o = report.artifact.output as Record<string, unknown>;
  return {
    runs: Array.isArray(o.runs) ? (o.runs as ComparedRun[]) : [],
    rows: Array.isArray(o.rows) ? (o.rows as ComparedRow[]) : [],
    values: Array.isArray(o.values) ? (o.values as ComparedValue[]) : [],
  };
}

/** One Tornado row per output whose every later change is a number, in percent; the rest are said in the table alone. */
export function changeRows(rows: ComparedRow[]): TornadoRow[] {
  return rows
    .filter((r) => r.change.length > 1 && r.change.slice(1).every((c) => typeof c === 'number' && Number.isFinite(c)))
    .map((r) => ({ label: r.key, values: r.change.slice(1).map((c) => (c as number) * 100), tag: r.unit || undefined }));
}

const shown = (v: number | string | null | undefined) =>
  v == null ? '—' : typeof v === 'number' ? (Math.abs(v) >= 1000 ? Math.round(v).toLocaleString('en-US') : String(Number(v.toPrecision(6)))) : v;
const pct = (c: number | null) => (c == null ? '—' : `${c >= 0 ? '+' : ''}${(c * 100).toFixed(2)} %`);

export default function ProformaComparison({ comparisonId }: { comparisonId: string }) {
  const [report, setReport] = useState<ComparisonReport | null>(null);
  const [problem, setProblem] = useState<string | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    setReport(null);
    setProblem(null);
    comparisonReport(comparisonId, ctrl.signal)
      .then(setReport)
      .catch((e: unknown) => !ctrl.signal.aborted && setProblem(problemOf(e)));
    return () => ctrl.abort();
  }, [comparisonId]);

  const c = report?.comparison ?? null;
  const out = report ? comparedOf(report) : null;
  const names = (out?.runs ?? []).map((_, i) => `Run ${i + 1}`);
  const moved = out ? changeRows(out.rows) : [];
  const still = moved.filter((r) => r.values.every((v) => v === 0));
  const rowsHead = ['Output', 'Unit', ...names, ...names.slice(1).map((n) => `${n}: change`)];
  const rowsBody = (out?.rows ?? []).map((r) => [r.key, r.unit || '—', ...r.values.map(shown), ...r.change.slice(1).map(pct)]);
  const valuesHead = ['Value', ...names];
  const valuesBody = (out?.values ?? []).map((v) => [
    v.key,
    ...v.values.map((x) => `${shown(x.value)} ${x.unit} (${ORIGIN_WORDS[x.origin] ?? x.origin}${x.by ? `, ${x.by}` : ''})`),
  ]);

  return (
    <div data-testid="proforma-comparison" data-comparison={comparisonId}>
      <PageHeader
        eyebrow={<>comparison · <span className="normal-case font-num">{comparisonId}</span></>}
        title={c?.title ?? comparisonId}
        subtitle={
          c && (
            <span className="flex flex-wrap items-center gap-2">
              <ProvenanceBadge p={c.provenance} />
              <span>
                {c.runIds.length} runs set side by side for {c.by || 'this browser'}, {stamp(c.at)}. Each change is reckoned from the first run.
              </span>
            </span>
          )
        }
        actions={
          <>
            {c && <LinkButton to={`/biorepo/artifacts/${c.artifactId}`}>Its artifact</LinkButton>}
            <LinkButton to="/proforma/studies">
              <BookOpen size={14} /> Studies
            </LinkButton>
          </>
        }
      />

      {problem && (
        <div className="mb-4">
          <Callout kind="warn">
            <span data-testid="comparison-problem">{problem}</span>
          </Callout>
        </div>
      )}

      {report && c && out && (
        <div className="space-y-4">
          <Card className="p-4" data-testid="comparison-runs">
            <h2 className="font-serif text-section-title font-semibold mb-1">The runs, in order</h2>
            <ol className="list-decimal pl-5 space-y-0.5 text-body">
              {out.runs.map((r, i) => (
                <li key={r.artifactId}>
                  <a className="font-num underline underline-offset-2 hover:text-accent" href={href(`/proforma/runs/${r.artifactId}`)}>
                    {r.artifactId}
                  </a>{' '}
                  {r.plant}
                  {r.configuration ? ` (${r.configuration})` : ''}, {r.provenance}
                  {i === 0 && <span className="text-ink-soft"> · each change is reckoned from this run</span>}
                </li>
              ))}
            </ol>
          </Card>

          <Tornado
            title="How far does each run move each output from the first?"
            drawn={`One row per output whose every later change is a number, sorted by how far it moved; each bar is ${names.length > 2 ? 'a later run’s' : 'the second run’s'} change from run 1.`}
            series={names.slice(1)}
            unit="% from run 1"
            rows={moved}
            provenance={c.provenance}
            csvName={`comparison-${c.id}-changes`}
            notes={[
              'Every change is the comparison artifact’s own, relative to the first run’s value; the browser divides nothing.',
              ...(still.length ? [`${still.length} of these outputs did not move: ${still.map((r) => r.label).join(', ')}.`] : []),
            ]}
          />

          <Card className="p-4" data-testid="comparison-rows">
            <div className="flex flex-wrap items-start justify-between gap-2 mb-1">
              <h2 className="font-serif text-section-title font-semibold">Every number, run by run</h2>
              <button className="chip" onClick={() => exportCSV(`comparison-${c.id}-rows.csv`, rowsHead, rowsBody)}>
                <Download size={12} aria-hidden /> CSV
              </button>
            </div>
            <p className="text-caption text-ink-soft mb-2">The price block in BioSTEAM&rsquo;s TEA units and a flowsheet&rsquo;s outputs in theirs, read from each run&rsquo;s artifact.</p>
            <div className="overflow-x-auto">
              <table className="w-full text-caption">
                <thead>
                  <tr className="border-b border-line text-ink-soft">
                    {rowsHead.map((h, i) => (
                      <th key={h} className={i < 2 ? 'text-left py-1 pr-2 font-medium' : 'text-right py-1 px-1.5 font-medium'}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rowsBody.map((r) => (
                    <tr key={r[0]} className="border-b border-line/50" data-testid="comparison-row">
                      {r.map((cell, j) => (
                        <td key={j} className={j < 2 ? 'py-1 pr-2 font-num' : 'py-1 px-1.5 text-right font-num'}>
                          {cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          <Card className="p-4" data-testid="comparison-values">
            <div className="flex flex-wrap items-start justify-between gap-2 mb-1">
              <h2 className="font-serif text-section-title font-semibold">The values the runs set</h2>
              {valuesBody.length > 0 && (
                <button className="chip" onClick={() => exportCSV(`comparison-${c.id}-values.csv`, valuesHead, valuesBody)}>
                  <Download size={12} aria-hidden /> CSV
                </button>
              )}
            </div>
            {valuesBody.length ? (
              <>
                <p className="text-caption text-ink-soft mb-2">Each value any run set for itself, each run&rsquo;s with its origin; a run that set none ran on the library&rsquo;s default.</p>
                <div className="overflow-x-auto">
                  <table className="w-full text-caption">
                    <thead>
                      <tr className="border-b border-line text-ink-soft">
                        {valuesHead.map((h) => (
                          <th key={h} className="text-left py-1 pr-2 font-medium">
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {valuesBody.map((r) => (
                        <tr key={r[0]} className="border-b border-line/50 align-top" data-testid="comparison-value">
                          {r.map((cell, j) => (
                            <td key={j} className="py-1 pr-2 font-num">
                              {cell}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            ) : (
              <p className="text-body text-ink-soft">Every run here ran on the library&rsquo;s own defaults: none set a value of its own.</p>
            )}
          </Card>
        </div>
      )}
    </div>
  );
}
