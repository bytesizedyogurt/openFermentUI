// Library — the faceted corpus table (OF-DES-001 §8.3). Every row is a paper
// in the OF-COR-001 catalogue; the ingest queue lives on the Ingest screen.
import { useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  BookMarked,
  Download,
  FolderPlus,
  Layers,
  Loader2,
  Wand2,
  X,
} from 'lucide-react';
import type { Job, Paper } from '@/data/types';
import { useStore } from '@/store';
import { href, navigate } from '@/router';
import { DataTable, type Column, type FacetDef } from '@/components/DataTable';
import { ProvenanceLegend, Tick, type ProvKind } from '@/components/Provenance';
import {
  Button,
  Callout,
  Card,
  EmptyState,
  LinkButton,
  PageHeader,
  Popover,
  Skeleton,
  cx,
} from '@/components/ui';
import { exportCSV } from '@/lib/csv';
import { delayClass } from '@/sim/latency';

import { partEyebrow } from '@/data/parts';

/** Movement · part · pool, from the one table that names the parts. */
const EYEBROW = partEyebrow('trawl', 'corpus');
const STAGE_KEYS = ['fetch', 'parse', 'chunk', 'embed', 'extract'] as const;
const STAGE_LABELS = ['Fetch', 'Parse', 'Chunk', 'Embed', 'Extract'];

const INGEST_FACET_LABEL: Record<string, string> = {
  complete: 'In corpus',
  ingesting: 'Ingesting',
  failed: 'Parse failed',
};

const GOLD_FACET_LABEL: Record<string, string> = {
  yes: 'Has gold records',
  no: 'No gold records',
};

interface LibRow {
  paper: Paper;
  extractions: number;
  goldCount: number;
  verifiedCount: number;
  collections: string[];
  prov: ProvKind;
  ingestKey: 'complete' | 'catalogued' | 'ingesting' | 'failed';
}

/** Latest ingest job that references this paper (jobs carry the id in href). */
function ingestJobFor(jobs: Job[], paperId: string): Job | undefined {
  for (let i = jobs.length - 1; i >= 0; i--) {
    const j = jobs[i];
    if (j.kind !== 'ingest') continue;
    if (j.href?.endsWith(`/${paperId}`) || j.title.includes(paperId)) return j;
  }
  return undefined;
}

/**
 * Stage read live from the running job. A paper seeded mid-pipeline has no job
 * behind it, so its progress is genuinely unknown — `pct` is null rather than a
 * plausible-looking number.
 */
function stageOf(
  paper: Paper,
  job: Job | undefined,
): { index: number; label: string; pct: number | null } {
  if (job && job.status === 'running') {
    const index = Math.min(job.stageIndex, STAGE_LABELS.length - 1);
    return {
      index,
      label: STAGE_LABELS[index],
      pct: (job.stageIndex + job.stageProgress) / job.stages.length,
    };
  }
  const key = paper.ingest.startsWith('stage:') ? paper.ingest.slice(6) : 'fetch';
  const index = Math.max(0, STAGE_KEYS.indexOf(key as (typeof STAGE_KEYS)[number]));
  return { index, label: STAGE_LABELS[index], pct: null };
}

function authorLabel(authors: string[]): string {
  if (authors.length === 0) return '—';
  if (authors.length === 1) return authors[0];
  if (authors.length === 2) return `${authors[0]}, ${authors[1]}`;
  return `${authors[0]}, ${authors[1]} et al.`;
}

function nowStamp(): string {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

function TagList({ items, max = 2 }: { items: string[]; max?: number }) {
  if (items.length === 0) return <span className="text-ink-soft">—</span>;
  const shown = items.slice(0, max);
  const rest = items.length - shown.length;
  return (
    <span className="flex flex-nowrap items-center gap-1 overflow-hidden">
      {shown.map((t) => (
        <span key={t} className="chip text-caption text-ink-soft max-w-[110px]" title={t}>
          <span className="truncate">{t}</span>
        </span>
      ))}
      {rest > 0 && (
        <span className="text-caption text-ink-soft font-num shrink-0" title={items.join(', ')}>
          +{rest}
        </span>
      )}
    </span>
  );
}

export default function Library() {
  const papers = useStore((s) => s.papers);
  const records = useStore((s) => s.records);
  const collections = useStore((s) => s.collections);
  const jobs = useStore((s) => s.jobs);
  const density = useStore((s) => s.ui.density);
  const addCollectionPapers = useStore((s) => s.addCollectionPapers);
  const startJob = useStore((s) => s.startJob);
  const logActivity = useStore((s) => s.logActivity);
  const toast = useStore((s) => s.toast);

  const [ready, setReady] = useState(false);
  const [collectionFilter, setCollectionFilter] = useState<string | null>(null);

  // Simulated first-paint latency (§13.5) so the loading state is real.
  useEffect(() => {
    let alive = true;
    delayClass('quick').then(() => {
      if (alive) setReady(true);
    });
    return () => {
      alive = false;
    };
  }, []);

  const allRows = useMemo<LibRow[]>(() => {
    const byPaper = new Map<string, { total: number; gold: number; verified: number }>();
    for (const r of records) {
      const agg = byPaper.get(r.paperId) ?? { total: 0, gold: 0, verified: 0 };
      agg.total += 1;
      if (r.gold) agg.gold += 1;
      if (r.status === 'verified') agg.verified += 1;
      byPaper.set(r.paperId, agg);
    }
    return papers
      .filter((p) => p.ingest !== 'shelf')
      .map((paper) => {
        const agg = byPaper.get(paper.id) ?? { total: 0, gold: 0, verified: 0 };
        const ingestKey: LibRow['ingestKey'] = paper.ingest.startsWith('failed:')
          ? 'failed'
          : paper.ingest.startsWith('stage:')
            ? 'ingesting'
            : paper.ingest === 'catalogued'
              ? 'catalogued'
              : 'complete';
        const prov: ProvKind =
          ingestKey === 'failed'
            ? 'rejected'
            : ingestKey === 'ingesting'
              ? 'demo'
              : ingestKey === 'catalogued' && agg.gold === 0 && agg.verified === 0
                ? 'curated'
                : agg.gold > 0
                ? 'gold'
                : agg.verified > 0
                  ? 'verified'
                  : 'unverified';
        return {
          paper,
          extractions: agg.total,
          goldCount: agg.gold,
          verifiedCount: agg.verified,
          collections: collections.filter((c) => c.paperIds.includes(paper.id)).map((c) => c.name),
          prov,
          ingestKey,
        };
      });
  }, [papers, records, collections]);

  const activeCollection = collections.find((c) => c.id === collectionFilter) ?? null;
  const rows = useMemo(
    () => (activeCollection ? allRows.filter((r) => activeCollection.paperIds.includes(r.paper.id)) : allRows),
    [allRows, activeCollection],
  );

  const pinned = allRows.filter((r) => r.ingestKey === 'ingesting');
  const brokenRows = allRows.filter((r) => r.ingestKey === 'failed');

  // ── actions ──────────────────────────────────────────────────────────
  const addToCollection = (collectionId: string, selected: LibRow[], clear: () => void) => {
    const col = collections.find((c) => c.id === collectionId);
    if (!col) return;
    const ids = selected.map((r) => r.paper.id);
    const added = ids.filter((id) => !col.paperIds.includes(id)).length;
    addCollectionPapers(collectionId, ids);
    toast({
      text:
        added === 0
          ? `All ${ids.length} papers were already in ${col.name}`
          : `Added ${added} paper${added === 1 ? '' : 's'} to ${col.name}`,
      kind: added === 0 ? 'info' : 'success',
    });
    clear();
  };

  const queueExtraction = (selected: LibRow[], clear: () => void) => {
    const n = selected.length;
    const weight = Math.min(4, Math.max(1, n));
    startJob({
      title: `Extraction — ${n} paper${n === 1 ? '' : 's'}`,
      kind: 'extraction',
      stages: [
        { label: 'Load sections', ms: 600 * weight },
        { label: 'Chunk', ms: 500 * weight },
        { label: 'Extract fields', ms: 1400 * weight },
        { label: 'Score confidence', ms: 700 },
        { label: 'Stage for review', ms: 500 },
      ],
      href: n === 1 ? `#/ledger/records?paper=${selected[0].paper.id}` : '#/ledger/records',
    });
    logActivity({
      at: nowStamp(),
      icon: 'table',
      text: `Extraction queued for ${n} paper${n === 1 ? '' : 's'}`,
      href: '#/ledger/records',
      provenance: 'demo',
    });
    toast({
      text: `Extraction queued for ${n} paper${n === 1 ? '' : 's'} — the demo extractor replays the seeded records, it does not mint new ones`,
      kind: 'info',
      href: '#/ledger/records',
      hrefLabel: 'Extract',
    });
    clear();
  };

  const exportSelected = (selected: LibRow[]) => {
    exportCSV(
      'openferment-library-selection.csv',
      [
        'Paper ID',
        'Title',
        'Authors',
        'Year',
        'Venue',
        'Organisms',
        'Topics',
        'Extractions',
        'Gold records',
        'Ingest status',
        'Collections',
      ],
      selected.map((r) => [
        r.paper.id,
        r.paper.title,
        r.paper.authors.join('; '),
        r.paper.year,
        r.paper.venue,
        r.paper.organisms.join('; '),
        r.paper.topics.join('; '),
        r.extractions,
        r.goldCount,
        r.paper.ingest,
        r.collections.join('; '),
      ]),
    );
  };

  // ── columns ──────────────────────────────────────────────────────────
  const columns: Column<LibRow>[] = [
    {
      key: 'id',
      header: 'ID',
      width: '88px',
      priority: 1,
      render: (r) => (
        <Tick p={r.prov} className="inline-block whitespace-nowrap">
          <a
            href={href(`/trawl/sources/${r.paper.id}`)}
            className="font-num text-accent hover:underline"
            onClick={(e) => e.stopPropagation()}
          >
            {r.paper.id}
          </a>
        </Tick>
      ),
      value: (r) => r.paper.id,
    },
    {
      key: 'title',
      header: 'Title',
      priority: 1,
      render: (r) => (
        <a
          href={href(`/trawl/sources/${r.paper.id}`)}
          className="font-serif hover:text-accent hover:underline block truncate"
          style={{ maxWidth: 340 }}
          title={r.paper.title}
          onClick={(e) => e.stopPropagation()}
        >
          {r.paper.title}
        </a>
      ),
      value: (r) => r.paper.title,
    },
    {
      key: 'authors',
      header: 'Authors',
      width: '124px',
      priority: 2,
      render: (r) => (
        <span
          className="text-ink-soft block truncate"
          style={{ maxWidth: 116 }}
          title={r.paper.authors.join(', ')}
        >
          {authorLabel(r.paper.authors)}
        </span>
      ),
      value: (r) => r.paper.authors.join('; '),
    },
    {
      key: 'year',
      header: 'Year',
      width: '56px',
      numeric: true,
      priority: 2,
      render: (r) => <span className="font-num">{r.paper.year}</span>,
      value: (r) => r.paper.year,
    },
    {
      key: 'organisms',
      header: 'Organisms',
      width: '124px',
      priority: 2,
      render: (r) => <TagList items={r.paper.organisms} />,
      value: (r) => r.paper.organisms.join('; '),
    },
    {
      key: 'topics',
      header: 'Topics',
      width: '124px',
      priority: 3,
      render: (r) => <TagList items={r.paper.topics} max={1} />,
      value: (r) => r.paper.topics.join('; '),
    },
    {
      key: 'extractions',
      header: 'Extractions',
      width: '82px',
      numeric: true,
      priority: 2,
      render: (r) =>
        r.extractions === 0 ? (
          <span className="font-num text-ink-soft">0</span>
        ) : (
          <a
            href={href(`/extract?paper=${r.paper.id}`)}
            className="font-num text-accent hover:underline"
            title={`Open Extract filtered to ${r.paper.id}`}
            onClick={(e) => e.stopPropagation()}
          >
            {r.extractions}
            {r.goldCount > 0 && <span className="text-gold"> ★{r.goldCount}</span>}
          </a>
        ),
      value: (r) => r.extractions,
    },
    {
      key: 'status',
      header: 'Status',
      width: '140px',
      priority: 1,
      render: (r) => {
        if (r.ingestKey === 'failed') {
          return (
            <a
              href={href('/trawl/ingest')}
              className="chip text-signal-error border-signal-error/40 hover:bg-signal-error/10"
              title="Ingest halted — open the board for the reason and a retry"
              onClick={(e) => e.stopPropagation()}
            >
              <AlertTriangle size={11} /> Ingest halted
            </a>
          );
        }
        if (r.ingestKey === 'ingesting') {
          const st = stageOf(r.paper, ingestJobFor(jobs, r.paper.id));
          return (
            <span className="chip text-signal-info border-signal-info/40">
              <Loader2 size={11} className={cx(st.pct !== null && 'animate-spin')} />
              {st.label}
              {st.pct !== null && <span className="font-num">{Math.round(st.pct * 100)}%</span>}
            </span>
          );
        }
        if (r.ingestKey === 'catalogued') {
          // Bibliographically real, full text not parsed. Saying "in corpus"
          // here would imply the spans anchor to the paper's own words; they
          // anchor to the curator's notes.
          return (
            <span
              className="chip text-ink-soft"
              title="Catalogued: real citation, full text not ingested. Spans anchor to the curation note."
            >
              <BookMarked size={11} /> Catalogued
              {r.goldCount > 0 && <span className="text-gold">· gold</span>}
            </span>
          );
        }
        return (
          <span className="chip text-ink-soft">
            Full text
            {r.goldCount > 0 && <span className="text-gold">· gold</span>}
          </span>
        );
      },
      value: (r) => r.paper.ingest,
    },
  ];

  const facets: FacetDef<LibRow>[] = [
    { key: 'organism', label: 'Organism', valuesOf: (r) => r.paper.organisms },
    { key: 'topic', label: 'Topic', valuesOf: (r) => r.paper.topics },
    { key: 'year', label: 'Year', valuesOf: (r) => [String(r.paper.year)] },
    {
      key: 'ingest',
      label: 'Ingest status',
      valuesOf: (r) => [r.ingestKey],
      labelOf: (v) => INGEST_FACET_LABEL[v] ?? v,
    },
    {
      key: 'gold',
      label: 'Gold set',
      valuesOf: (r) => [r.goldCount > 0 ? 'yes' : 'no'],
      labelOf: (v) => GOLD_FACET_LABEL[v] ?? v,
    },
    { key: 'collection', label: 'Collection', valuesOf: (r) => r.collections },
  ];

  // ── header actions ───────────────────────────────────────────────────
  const headerActions = (
    <>
      <Popover
        openOnHover={false}
        width={330}
        label="Collections"
        trigger={(p) => (
          <button {...p} className="btn btn-sm" title="Collection manager">
            <Layers size={13} /> Collections
          </button>
        )}
      >
        <div className="space-y-1">
          <div className="text-caption uppercase tracking-wide text-ink-soft mb-1">Collections</div>
          {collections.length === 0 && (
            <div className="text-body text-ink-soft">
              No collections in this session. Select rows to add papers to one.
            </div>
          )}
          {collections.map((c) => {
            const on = collectionFilter === c.id;
            return (
              <div key={c.id} className="flex items-center gap-2">
                <button
                  className={cx(
                    'flex-1 flex items-center justify-between gap-2 px-1.5 py-1 rounded-input text-left',
                    on ? 'bg-accent-wash font-medium' : 'hover:bg-ink-soft/[0.08]',
                  )}
                  onClick={() => setCollectionFilter(on ? null : c.id)}
                  aria-pressed={on}
                  title={on ? 'Remove this filter' : `Filter the table to ${c.name}`}
                >
                  <span className="truncate">{c.name}</span>
                  <span className="font-num text-caption text-ink-soft shrink-0">
                    {c.paperIds.length}
                  </span>
                </button>
              </div>
            );
          })}
          {collectionFilter && (
            <button className="btn btn-sm w-full mt-1" onClick={() => setCollectionFilter(null)}>
              <X size={12} /> Show all papers
            </button>
          )}
          <div className="text-caption text-ink-soft pt-2 mt-1 border-t border-line">
            Collections are session-scoped. Add papers with the row selection toolbar.
          </div>
        </div>
      </Popover>
      <LinkButton to="/trawl/ingest" variant="primary" size="sm">
        Ingest papers
      </LinkButton>
    </>
  );

  const header = (
    <PageHeader eyebrow={EYEBROW}
      title="Sources"
      subtitle={
        <>
          Real literature, catalogued by hand — <span className="font-num">{allRows.length}</span> papers carrying{' '}
          <span className="font-num">{records.length}</span> extraction records. Filters combine with AND
          across groups and OR inside a group.
        </>
      }
      actions={headerActions}
    />
  );

  if (!ready) {
    return (
      <>
        {header}
        <Card>
          <Skeleton rows={10} />
        </Card>
        <div className="sr-only" aria-live="polite">
          Loading corpus table
        </div>
      </>
    );
  }

  if (allRows.length === 0) {
    return (
      <>
        {header}
        <Card>
          <EmptyState
            title="No papers in the corpus yet"
            body="Every paper is still held on the demo shelf. Ingest one to see it flow through fetch, parse, chunk, embed and extract."
            action={<LinkButton to="/trawl/ingest">Open the ingest board</LinkButton>}
          />
        </Card>
      </>
    );
  }

  return (
    <>
      {header}

      {brokenRows.length > 0 && (
        <div className="mb-3">
          <Callout kind="error" title={`${brokenRows.length} paper${brokenRows.length === 1 ? '' : 's'} failed to parse`}>
            {brokenRows.map((r) => r.paper.id).join(', ')} could not be segmented into sections. Retry the
            ingest or continue with abstract-only text on the{' '}
            <a href={href('/trawl/ingest')} className="text-accent hover:underline">
              ingest board
            </a>
            .
          </Callout>
        </div>
      )}

      {pinned.length > 0 && (
        <Card className="p-3 mb-3">
          <div className="text-caption uppercase tracking-wide text-ink-soft mb-2">
            Ingesting now — pinned
          </div>
          <div className="space-y-2" aria-live="polite">
            {pinned.map((r) => {
              const job = ingestJobFor(jobs, r.paper.id);
              const st = stageOf(r.paper, job);
              return (
                <div key={r.paper.id} className="flex items-center gap-3">
                  <span className="font-num text-caption text-ink-soft w-[62px] shrink-0">
                    {r.paper.id}
                  </span>
                  <a
                    href={href(`/trawl/sources/${r.paper.id}`)}
                    className="font-serif truncate flex-1 min-w-0 hover:text-accent hover:underline"
                    title={r.paper.title}
                  >
                    {r.paper.title}
                  </a>
                  <span className="chip text-signal-info border-signal-info/40 shrink-0">
                    <Loader2 size={11} className={cx(st.pct !== null && 'animate-spin')} />
                    {st.label}
                    {st.pct !== null ? (
                      <span className="font-num">{Math.round(st.pct * 100)}%</span>
                    ) : (
                      <span className="text-ink-soft">· waiting</span>
                    )}
                  </span>
                  <div className="w-[120px] shrink-0 h-1.5 rounded-full bg-ink-soft/15 overflow-hidden">
                    {st.pct !== null ? (
                      <div
                        className="h-full rounded-full bg-signal-info transition-[width] duration-200"
                        style={{ width: `${Math.round(st.pct * 100)}%` }}
                      />
                    ) : (
                      <div
                        className="h-full rounded-full bg-signal-info/40 animate-pulse"
                        style={{ width: `${((st.index + 0.5) / STAGE_LABELS.length) * 100}%` }}
                        title="Progress within this stage is unknown — no worker is attached"
                      />
                    )}
                  </div>
                  <LinkButton to="/trawl/ingest" size="sm">
                    Board
                  </LinkButton>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      <div className="mb-2">
        <ProvenanceLegend />
      </div>

      <DataTable<LibRow>
        rows={rows}
        columns={columns}
        rowKey={(r) => r.paper.id}
        tickOf={(r) => r.prov}
        dense={density === 'dense'}
        onOpen={(r) => navigate(`/trawl/sources/${r.paper.id}`)}
        facets={facets}
        searchOf={(r) =>
          `${r.paper.id} ${r.paper.title} ${r.paper.authors.join(' ')} ${r.paper.topics.join(' ')}`
        }
        exportName="openferment-library"
        exportNote="CSV exports carry the provenance disclosure header — the citations are real, and a per-class note says what each provenance value is worth."
        emptyTitle={activeCollection ? 'This collection is empty' : 'No papers match'}
        emptyBody={
          activeCollection
            ? `${activeCollection.name} has no papers in it yet. Select rows and use “Add to collection”.`
            : 'Nothing in the corpus matches the current filters.'
        }
        toolbar={
          activeCollection ? (
            <button
              className="chip chip-active"
              onClick={() => setCollectionFilter(null)}
              title="Remove the collection filter"
            >
              <Layers size={12} /> {activeCollection.name}
              <span className="font-num text-caption text-ink-soft">
                {activeCollection.paperIds.length}
              </span>
              <X size={11} />
            </button>
          ) : undefined
        }
        bulkActions={(selected, clear) => (
          <>
            <Popover
              openOnHover={false}
              width={300}
              label="Add to collection"
              trigger={(p) => (
                <button {...p} className="btn btn-sm">
                  <FolderPlus size={13} /> Add to collection
                </button>
              )}
            >
              <div className="space-y-1">
                <div className="text-caption text-ink-soft mb-1">
                  Add <span className="font-num">{selected.length}</span> selected paper
                  {selected.length === 1 ? '' : 's'} to:
                </div>
                {collections.length === 0 && (
                  <div className="text-body text-ink-soft">No collections exist in this session.</div>
                )}
                {collections.map((c) => {
                  const already = selected.filter((r) => c.paperIds.includes(r.paper.id)).length;
                  return (
                    <button
                      key={c.id}
                      className="w-full flex items-center justify-between gap-2 px-1.5 py-1 rounded-input text-left hover:bg-accent-wash"
                      onClick={() => addToCollection(c.id, selected, clear)}
                    >
                      <span className="truncate">{c.name}</span>
                      <span className="font-num text-caption text-ink-soft shrink-0">
                        {already > 0 ? `${already} already` : `${c.paperIds.length}`}
                      </span>
                    </button>
                  );
                })}
              </div>
            </Popover>
            <Button size="sm" onClick={() => queueExtraction(selected, clear)}>
              <Wand2 size={13} /> Queue extraction
            </Button>
            <Button size="sm" onClick={() => exportSelected(selected)}>
              <Download size={13} /> Export metadata
            </Button>
          </>
        )}
      />
    </>
  );
}
