// A flowsheet's page (execution prompt §8.5): an SFF record of the project, as
// the toolkit checked and scored it, and its graph, units as nodes and streams
// as edges. A run's file, a library plant's, or one a person imported.
import { useEffect, useState } from 'react';
import { Download } from 'lucide-react';
import type { SFFFlowsheet } from '@/data/types';
import { SffGraph } from '@/components/SffGraph';
import { Card, PageHeader } from '@/components/ui';
import { downloadFlowsheet, getFlowsheet } from '@/lib/studies';
import { href } from '@/router';

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
              {f.units} units and {f.streams} streams; from {f.source}.
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
          <div className="mt-3">
            {f.graph ? <SffGraph graph={f.graph} /> : <p className="text-caption text-ink-soft">The file draws no graph.</p>}
          </div>
        </Card>
      )}
    </div>
  );
}
