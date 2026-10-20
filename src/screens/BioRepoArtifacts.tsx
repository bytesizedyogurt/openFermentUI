// BioRepo → Artifacts (OF-BLD-014 §3.2, E.5): what the service computed, kept
// with the inputs it was computed from, and replayable.
//
// Every value here was computed by the running service; none is a paper's
// number. Its provenance is the one the service computed from its inputs
// (`basis_provenance`), shown as it arrived. With the service down this view
// says so and names the command that starts it; it shows no stand-in (E.2).
import { useEffect, useState } from 'react';
import { Box, RotateCcw } from 'lucide-react';
import type { Artifact, BasisSource, ReplayResult } from '@/data/types';
import { ArtifactRefused, ArtifactsDown, getArtifact, headline, listArtifacts, programOfArtifact, replayArtifact, visibleArtifacts } from '@/lib/artifacts';
import { useProgramLookup, useStore } from '@/store';
import { PROGRAM_BY_ID, PROGRAMS_SETTINGS_PATH, isArchived } from '@/data/programs';
import { href, navigate } from '@/router';
import { CitationChip } from '@/components/Chip';
import { ProvenanceBadge, Tick } from '@/components/Provenance';
import { Button, Callout, Card, EmptyState, PageHeader, SectionTitle } from '@/components/ui';
import { OwnerTabs } from '@/components/OwnerTabs';
import { BIOREPO_TABS } from '@/data/tabs';

type Load<T> = { state: 'loading' } | { state: 'down'; error: ArtifactsDown } | { state: 'refused'; why: string } | { state: 'ok'; data: T };

function useLoad<T>(load: (signal: AbortSignal) => Promise<T>, key: string): Load<T> {
  const [result, setResult] = useState<Load<T>>({ state: 'loading' });
  useEffect(() => {
    const ctrl = new AbortController();
    setResult({ state: 'loading' });
    load(ctrl.signal).then(
      (data) => !ctrl.signal.aborted && setResult({ state: 'ok', data }),
      (e: unknown) => {
        if (ctrl.signal.aborted) return;
        if (e instanceof ArtifactRefused) setResult({ state: 'refused', why: e.message });
        else setResult({ state: 'down', error: e instanceof ArtifactsDown ? e : new ArtifactsDown(String(e)) });
      },
    );
    return () => ctrl.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  return result;
}

function ServiceDown({ error }: { error: ArtifactsDown }) {
  return (
    <EmptyState
      icon={<Box size={28} />}
      title="Artifacts need the service"
      body={
        <>
          {error.message} The service keeps every value it computed, and this view lists them. {error.remedy}
        </>
      }
    />
  );
}

const day = (iso: string) => iso.slice(0, 10);

export default function BioRepoArtifacts({ artifactId }: { artifactId?: string }) {
  return artifactId ? <ArtifactPage id={artifactId} /> : <ArtifactList />;
}

function ArtifactList() {
  // The program switch (OF-BLD-016 §2): an artifact computed from an archived
  // program's records, product or strain is left out until the switch is on.
  const showArchived = useStore((s) => s.showArchived);
  const load = useLoad((signal) => listArtifacts(signal, showArchived), showArchived ? 'list-all' : 'list');
  const lookup = useProgramLookup();
  const all = load.state === 'ok' ? load.data : [];
  const shown = visibleArtifacts(all, { ...lookup, showArchived });
  const hidden = all.length - shown.length;
  const hiddenNote = hidden > 0 && (
    <p className="text-caption text-ink-soft mt-3" data-testid="artifacts-hidden">
      {hidden} computed from an archived program {hidden === 1 ? 'is' : 'are'} not listed.{' '}
      <a className="underline" href={href(PROGRAMS_SETTINGS_PATH)}>Settings → Programs</a> shows archived programs.
    </p>
  );
  return (
    <div>
      <PageHeader
        title="Artifacts"
        subtitle="Values the service computed, each kept with the inputs it was computed from and the source of every input. None of them is a paper's number. Open one to see its basis or replay it."
      />
      <OwnerTabs tabs={BIOREPO_TABS} />
      {load.state === 'loading' && <p className="text-body text-ink-soft">Asking the service…</p>}
      {load.state === 'down' && <ServiceDown error={load.error} />}
      {load.state === 'refused' && <Callout kind="warn">{load.why}</Callout>}
      {load.state === 'ok' && shown.length === 0 && (
        <EmptyState
          icon={<Box size={28} />}
          title="Nothing computed yet"
          body="The service keeps a value here each time one of its tools computes one: a converted unit, a yield ceiling, a fitted rate, a price. None has run on this machine."
        />
      )}
      {load.state === 'ok' && shown.length > 0 && (
        <Card className="overflow-x-auto">
          <table className="w-full border-collapse text-body" data-testid="artifact-table">
            <thead>
              <tr className="border-b border-line text-caption text-ink-soft">
                <th className="text-left font-medium px-3 py-2">Value</th>
                <th className="text-left font-medium px-3 py-2">Tool</th>
                <th className="text-left font-medium px-3 py-2">Provenance</th>
                <th className="text-left font-medium px-3 py-2">Computed</th>
              </tr>
            </thead>
            <tbody>
              {shown.map((a) => {
                const h = headline(a);
                return (
                  <tr key={a.id} className="border-b border-line last:border-0">
                    <td className="px-3 py-2">
                      <Tick p={a.provenance}>
                        <a className="text-accent hover:underline" href={href(`/biorepo/artifacts/${a.id}`)}>
                          {h.label ?? a.id}
                        </a>
                        {h.value !== null && (
                          <span className="font-num text-ink-soft ml-2">
                            {h.value}
                            {h.unit ? ` ${h.unit}` : ''}
                          </span>
                        )}
                      </Tick>
                    </td>
                    <td className="px-3 py-2 font-mono text-caption">{a.tool}</td>
                    <td className="px-3 py-2">
                      <ProvenanceBadge p={a.provenance} compact />
                    </td>
                    <td className="px-3 py-2 font-num text-caption text-ink-soft">{day(a.createdAt)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Card>
      )}
      {hiddenNote}
    </div>
  );
}

/** A link opens what it names; an artifact of an archived program says so. */
function ArchivedNote({ a }: { a: Artifact }) {
  const lookup = useProgramLookup();
  const p = programOfArtifact(a, lookup);
  if (!p || !isArchived(p)) return null;
  return (
    <p role="note" className="text-caption text-ink-soft mb-3" data-archived-program={p}>
      This value was computed from inputs of {PROGRAM_BY_ID[p].name}, an archived program.{' '}
      <a className="underline" href={href(PROGRAMS_SETTINGS_PATH)}>Settings → Programs</a>
    </p>
  );
}

function SourceChip({ source }: { source: BasisSource }) {
  switch (source.kind) {
    case 'record':
      return source.id ? <CitationChip recordId={source.id} /> : <span className="text-ink-soft">a record, unnamed</span>;
    case 'artifact':
      return source.id ? (
        <a className="chip font-mono" href={href(`/biorepo/artifacts/${source.id}`)}>
          artifact {source.id}
        </a>
      ) : (
        <span className="text-ink-soft">an artifact, unnamed</span>
      );
    case 'assumption':
      return (
        <span className="chip">
          assumed by {source.by ?? 'nobody named'}
          {source.note ? ` — ${source.note}` : ''}
        </span>
      );
    case 'deposition':
      return <span className="chip font-mono">deposition {source.id ?? ''}</span>;
    case 'model':
      return <span className="chip font-mono">model {source.id ?? ''}</span>;
    case 'convention':
      return <span className="chip">convention{source.note ? ` — ${source.note}` : ''}</span>;
  }
}

function ArtifactPage({ id }: { id: string }) {
  const load = useLoad((signal) => getArtifact(id, signal), id);
  const [replay, setReplay] = useState<{ busy: boolean; result?: ReplayResult; error?: string }>({ busy: false });

  const run = async () => {
    setReplay({ busy: true });
    try {
      setReplay({ busy: false, result: await replayArtifact(id) });
    } catch (e) {
      setReplay({ busy: false, error: e instanceof ArtifactsDown ? `${e.message} ${e.remedy}` : String((e as Error).message) });
    }
  };

  return (
    <div>
      <PageHeader
        title={load.state === 'ok' ? (headline(load.data).label ?? `Artifact ${id}`) : `Artifact ${id}`}
        subtitle="A value the service computed, with every input it was computed from."
        actions={
          <Button onClick={() => navigate('/biorepo/artifacts')} size="sm">
            All artifacts
          </Button>
        }
      />
      <OwnerTabs tabs={BIOREPO_TABS} />
      {load.state === 'loading' && <p className="text-body text-ink-soft">Asking the service…</p>}
      {load.state === 'down' && <ServiceDown error={load.error} />}
      {load.state === 'refused' && <Callout kind="warn">{load.why}</Callout>}
      {load.state === 'ok' && <ArchivedNote a={load.data} />}
      {load.state === 'ok' && <ArtifactBody a={load.data} replay={replay} onReplay={run} />}
    </div>
  );
}

function ArtifactBody({
  a,
  replay,
  onReplay,
}: {
  a: Artifact;
  replay: { busy: boolean; result?: ReplayResult; error?: string };
  onReplay: () => void;
}) {
  const h = headline(a);
  return (
    <div className="space-y-5">
      <Card className="p-4">
        <div className="flex flex-wrap items-baseline gap-x-4 gap-y-2">
          {h.value !== null && (
            <span className="font-num text-section-title" data-testid="artifact-value">
              {h.value}
              {h.unit ? ` ${h.unit}` : ''}
            </span>
          )}
          <ProvenanceBadge p={a.provenance} />
        </div>
        <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 mt-3 text-body">
          <dt className="text-ink-soft">Tool</dt>
          <dd className="font-mono">{a.tool}</dd>
          <dt className="text-ink-soft">Version</dt>
          <dd className="font-mono break-all">{a.toolVersion}</dd>
          <dt className="text-ink-soft">Computed</dt>
          <dd className="font-num">
            {a.createdAt} · {a.durationMs} ms
          </dd>
          {a.seed !== null && (
            <>
              <dt className="text-ink-soft">Seed</dt>
              <dd className="font-num">{a.seed}</dd>
            </>
          )}
          <dt className="text-ink-soft">Id</dt>
          <dd className="font-mono">{a.id}</dd>
        </dl>
      </Card>

      <section>
        <SectionTitle>Inputs</SectionTitle>
        <Card className="overflow-x-auto">
          <table className="w-full border-collapse text-body" data-testid="artifact-inputs">
            <thead>
              <tr className="border-b border-line text-caption text-ink-soft">
                <th className="text-left font-medium px-3 py-2">Input</th>
                <th className="text-left font-medium px-3 py-2">Value</th>
                <th className="text-left font-medium px-3 py-2">Source</th>
              </tr>
            </thead>
            <tbody>
              {a.inputs.map((i, n) => (
                <tr key={`${i.name}-${n}`} className="border-b border-line last:border-0">
                  <td className="px-3 py-2">{i.name}</td>
                  <td className="px-3 py-2 font-num">
                    {String(i.value)}
                    {i.unit ? ` ${i.unit}` : ''}
                  </td>
                  <td className="px-3 py-2">
                    <SourceChip source={i.source} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </section>

      <section>
        <SectionTitle
          right={
            <Button onClick={onReplay} disabled={replay.busy} size="sm">
              <RotateCcw size={14} className="mr-1" />
              {replay.busy ? 'Replaying…' : 'Replay'}
            </Button>
          }
        >
          Output
        </SectionTitle>
        {replay.result && (
          <div className="mb-3" data-testid="replay-result">
            {replay.result.identical ? (
              <Callout kind="info">Replayed identically: the tool computed the same output from the same inputs.</Callout>
            ) : (
              <Callout kind="warn">
                The replay differs from what was stored:
                <ul className="list-disc ml-5 mt-1">
                  {replay.result.differences.map((d, n) => (
                    <li key={n} className="font-mono text-caption">
                      {d.path || 'output'}: stored {JSON.stringify(d.stored)}, replayed {JSON.stringify(d.replayed)}
                    </li>
                  ))}
                </ul>
              </Callout>
            )}
          </div>
        )}
        {replay.error && (
          <div className="mb-3">
            <Callout kind="warn">{replay.error}</Callout>
          </div>
        )}
        <Card className="p-3">
          <pre className="font-mono text-caption whitespace-pre-wrap break-all">{JSON.stringify(a.output, null, 2)}</pre>
        </Card>
      </section>
    </div>
  );
}
