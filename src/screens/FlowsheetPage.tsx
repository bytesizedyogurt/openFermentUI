// A flowsheet's page (execution prompt §8.5): an SFF record of the project, as
// the toolkit checked and scored it, and its graph, units as nodes and streams
// as edges. A run's file, a library plant's, or one a person imported.
import { useEffect, useState } from 'react';
import { Download } from 'lucide-react';
import { SffGraph } from '@/components/SffGraph';
import { Card, PageHeader } from '@/components/ui';
import { downloadFlowsheet, getFlowsheet, type SFFFlowsheet } from '@/lib/studies';
import { href } from '@/router';

/** What the toolkit's check found: its counts by severity and status, and the findings that did not pass, in a table that opens. */
function ValidationFound({ validation }: { validation: SFFFlowsheet['validation'] }) {
  const counts = Object.entries(validation.summary).flatMap(([severity, byStatus]) =>
    Object.entries(byStatus).map(([status, n]) => ({ severity, status, n })),
  );
  const failing = validation.findings.filter((x) => x.status !== 'pass');
  if (counts.length === 0 && failing.length === 0) return null;
  return (
    <div className="mt-2 text-body" data-testid="flowsheet-findings">
      {counts.length > 0 && (
        <p className="text-ink-soft">
          What the check found:{' '}
          {counts.map((c, i) => (
            <span key={`${c.severity}-${c.status}`}>
              {i > 0 && '; '}
              {c.severity} {c.status} <span className="font-num">{c.n}</span>
            </span>
          ))}
          .
        </p>
      )}
      {failing.length > 0 && (
        <details className="mt-1">
          <summary className="cursor-pointer text-accent">
            The <span className="font-num">{failing.length}</span> finding{failing.length === 1 ? '' : 's'} that did not pass
          </summary>
          <table className="mt-2 w-full text-caption">
            <thead>
              <tr className="text-left text-ink-soft border-b border-line">
                <th className="py-1 pr-2 font-medium">Check</th>
                <th className="py-1 pr-2 font-medium">Severity</th>
                <th className="py-1 pr-2 font-medium">Status</th>
                <th className="py-1 pr-2 font-medium">What it says</th>
              </tr>
            </thead>
            <tbody>
              {failing.map((x, i) => (
                <tr key={`${x.checkId}-${x.path}-${i}`} className="border-b border-line/60 align-top">
                  <td className="py-1 pr-2 font-num whitespace-nowrap">{x.checkId}</td>
                  <td className="py-1 pr-2">{x.severity}</td>
                  <td className="py-1 pr-2">{x.status}</td>
                  <td className="py-1 pr-2" title={x.path}>
                    {x.message}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      )}
    </div>
  );
}

export function FlowsheetPage({ recordId }: { recordId: string }) {
  const [f, setF] = useState<SFFFlowsheet | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  useEffect(() => {
    const ac = new AbortController();
    setF(null);
    setProblem(null);
    getFlowsheet(recordId, ac.signal)
      .then(setF)
      .catch((e: unknown) => {
        if (!(e instanceof DOMException && e.name === 'AbortError')) setProblem(e instanceof Error ? e.message : String(e));
      });
    return () => ac.abort();
  }, [recordId]);
  return (
    <div className="space-y-4" data-testid="flowsheet-page">
      <PageHeader title={f?.title ?? recordId} subtitle={`SFF flowsheet record ${recordId}`} />
      {problem && <p className="text-body text-signal-warn">{problem}</p>}
      {f && (
        <Card className="p-4">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <p className="text-body">
              {f.validation.valid ? 'Valid' : 'Not valid'} against SFF {f.validation.schemaVersion}; completeness{' '}
              <span className="font-num">{f.completeness.score == null ? '—' : f.completeness.score.toFixed(2)}</span>;{' '}
              {f.units} units and {f.streams} streams; source: {f.source}.
              {f.runArtifactId && (
                <>
                  {' '}
                  Written by run{' '}
                  <a className="font-num text-accent hover:underline" href={href(`/proforma/runs/${f.runArtifactId}`)}>
                    {f.runArtifactId}
                  </a>
                  .
                </>
              )}
            </p>
            <button className="chip" onClick={() => downloadFlowsheet(f.id).catch((e: unknown) => setProblem(String(e)))}>
              <Download size={12} aria-hidden /> {f.id}.sff.json
            </button>
          </div>
          <ValidationFound validation={f.validation} />
          <div className="mt-3">
            {f.graph ? <SffGraph graph={f.graph} /> : <p className="text-caption text-ink-soft">The file draws no graph.</p>}
          </div>
        </Card>
      )}
    </div>
  );
}
