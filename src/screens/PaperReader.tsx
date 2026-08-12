// Paper reader (OF-DES-001 §8.4). The left pane renders the paper with every
// extraction anchored to the exact quoted substring; the right rail lists the
// same records. Selection is synchronised in both directions.
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import {
  AlertTriangle,
  ArrowLeft,
  FolderPlus,
  Loader2,
  MessageSquare,
  RefreshCw,
} from 'lucide-react';
import type { Contradiction, ExtractionRecord, FieldId, Job, Paper } from '@/data/types';
import { fieldName, ONTOLOGY_BY_ID } from '@/data/ontology';
import { ContradictionRail, railMarksByField } from '@/components/ContradictionRail';
import { aggregate } from '@/engine/posterior';
import { asNumber, convert } from '@/engine/units';
import { useStore, provenanceOf, tickClass } from '@/store';
import { href, navigate } from '@/router';
import { Quantity } from '@/components/QuantityField';
import { ProvenanceLegend, provMeta, type ProvKind } from '@/components/Provenance';
import {
  Button,
  Callout,
  Card,
  EmptyState,
  LinkButton,
  Popover,
  SectionTitle,
  Skeleton,
  cx,
} from '@/components/ui';
import { delayClass } from '@/sim/latency';

const STAGE_KEYS = ['fetch', 'parse', 'chunk', 'embed', 'extract'] as const;
const STAGE_LABELS = ['Fetch', 'Parse', 'Chunk', 'Embed', 'Extract'];

interface Span {
  record: ExtractionRecord;
  start: number;
  end: number;
}

/** Locate each quote in the section text; drop overlaps, keep source order. */
function locateSpans(text: string, recs: ExtractionRecord[]): Span[] {
  const found: Span[] = [];
  for (const r of recs) {
    if (!r.quote) continue;
    const start = text.indexOf(r.quote);
    if (start < 0) continue;
    found.push({ record: r, start, end: start + r.quote.length });
  }
  found.sort((a, b) => a.start - b.start || b.end - a.end);
  const kept: Span[] = [];
  let lastEnd = -1;
  for (const s of found) {
    if (s.start >= lastEnd) {
      kept.push(s);
      lastEnd = s.end;
    }
  }
  return kept;
}

function provOf(r: ExtractionRecord): ProvKind {
  return r.status === 'rejected' ? 'rejected' : provenanceOf(r);
}

function markClass(r: ExtractionRecord): string {
  if (r.gold) return 'span-gold';
  if (r.status === 'verified') return 'span-verified';
  return 'span-unverified';
}

function ingestJobFor(jobs: Job[], paperId: string): Job | undefined {
  for (let i = jobs.length - 1; i >= 0; i--) {
    const j = jobs[i];
    if (j.kind !== 'ingest') continue;
    if (j.href?.endsWith(`/${paperId}`) || j.title.includes(paperId)) return j;
  }
  return undefined;
}

function stageLabelOf(paper: Paper, job: Job | undefined): string {
  if (job && job.status === 'running') {
    return STAGE_LABELS[Math.min(job.stageIndex, STAGE_LABELS.length - 1)];
  }
  const key = paper.ingest.startsWith('stage:') ? paper.ingest.slice(6) : 'fetch';
  const idx = Math.max(0, STAGE_KEYS.indexOf(key as (typeof STAGE_KEYS)[number]));
  return STAGE_LABELS[idx];
}

export default function PaperReader({ paperId, spanId }: { paperId: string; spanId?: string }) {
  const paper = useStore((s) => s.papers.find((p) => p.id === paperId));
  const records = useStore((s) => s.records);
  const contradictions = useStore((s) => s.contradictions);
  const collections = useStore((s) => s.collections);
  const jobs = useStore((s) => s.jobs);
  const unitMode = useStore((s) => s.ui.unitMode);
  const reducedMotion = useStore((s) => s.ui.reducedMotion);
  const setUI = useStore((s) => s.setUI);
  const startJob = useStore((s) => s.startJob);
  const ingestPaper = useStore((s) => s.ingestPaper);
  const addCollectionPapers = useStore((s) => s.addCollectionPapers);
  const toast = useStore((s) => s.toast);

  const [ready, setReady] = useState(false);
  const [activeId, setActiveId] = useState<string | null>(spanId ?? null);
  const [hoverId, setHoverId] = useState<string | null>(null);
  const [pulseId, setPulseId] = useState<string | null>(null);

  const spanRefs = useRef<Record<string, HTMLElement | null>>({});
  const rowRefs = useRef<Record<string, HTMLButtonElement | null>>({});
  const sectionRefs = useRef<Record<string, HTMLElement | null>>({});

  const behavior: ScrollBehavior = reducedMotion ? 'auto' : 'smooth';

  useEffect(() => {
    let alive = true;
    setReady(false);
    delayClass('quick').then(() => {
      if (alive) setReady(true);
    });
    return () => {
      alive = false;
    };
  }, [paperId]);

  const recs = useMemo(() => records.filter((r) => r.paperId === paperId), [records, paperId]);

  // Every corpus value for each field this paper touches, so a row can show
  // where this paper sits among its peers. The question a reader actually has
  // in front of a number is "is this one an outlier?", and until now the screen
  // could not answer it without leaving.
  const peersByField = useMemo(
    () => railMarksByField(records, (f) => ONTOLOGY_BY_ID[f]?.canonicalUnit ?? ''),
    [records],
  );

  const sectionSpans = useMemo(() => {
    const map = new Map<string, Span[]>();
    if (!paper) return map;
    for (const s of paper.sections) {
      map.set(
        s.id,
        locateSpans(
          s.text,
          recs.filter((r) => r.sectionId === s.id),
        ),
      );
    }
    return map;
  }, [paper, recs]);

  /** Rail order follows reading order; records whose quote is missing sink last. */
  const railRecords = useMemo(() => {
    if (!paper) return [] as { record: ExtractionRecord; located: boolean }[];
    const order = new Map<string, number>();
    paper.sections.forEach((s, i) => order.set(s.id, i));
    const offsetOf = (r: ExtractionRecord) => {
      const spans = sectionSpans.get(r.sectionId) ?? [];
      const hit = spans.find((s) => s.record.id === r.id);
      return hit ? hit.start : Number.MAX_SAFE_INTEGER;
    };
    const anchorable = paper.ingest !== 'failed:parse';
    return [...recs]
      .map((record) => ({
        record,
        located: anchorable && offsetOf(record) !== Number.MAX_SAFE_INTEGER,
      }))
      .sort((a, b) => {
        const sa = order.get(a.record.sectionId) ?? 999;
        const sb = order.get(b.record.sectionId) ?? 999;
        if (sa !== sb) return sa - sb;
        return offsetOf(a.record) - offsetOf(b.record);
      });
  }, [paper, recs, sectionSpans]);

  // Deep link: select, scroll into view, pulse once.
  useEffect(() => {
    if (!spanId || !ready) return;
    setActiveId(spanId);
    const t1 = window.setTimeout(() => {
      spanRefs.current[spanId]?.scrollIntoView({ behavior, block: 'center' });
      rowRefs.current[spanId]?.scrollIntoView({ block: 'nearest' });
      setPulseId(spanId);
    }, 60);
    const t2 = window.setTimeout(() => setPulseId(null), 1500);
    return () => {
      window.clearTimeout(t1);
      window.clearTimeout(t2);
    };
  }, [spanId, ready, behavior]);

  const topField = useMemo(() => {
    const counts = new Map<FieldId, number>();
    for (const r of recs) counts.set(r.field, (counts.get(r.field) ?? 0) + 1);
    let best: FieldId | null = null;
    let bestN = 0;
    counts.forEach((n, f) => {
      if (n > bestN) {
        bestN = n;
        best = f;
      }
    });
    return best as FieldId | null;
  }, [recs]);

  if (!paper) {
    return (
      <div className="max-w-2xl">
        <Card className="p-6">
          <EmptyState
            title="No such paper"
            body={`${paperId} is not in this session's corpus. It may have been a link from an older session — session state resets on refresh.`}
            action={<LinkButton to="/library">Back to Library</LinkButton>}
            icon={<AlertTriangle size={22} />}
          />
        </Card>
      </div>
    );
  }

  // ── actions ──────────────────────────────────────────────────────────
  const selectFromText = (id: string) => {
    setActiveId(id);
    rowRefs.current[id]?.scrollIntoView({ behavior, block: 'nearest' });
  };

  const selectFromRail = (id: string) => {
    setActiveId(id);
    spanRefs.current[id]?.scrollIntoView({ behavior, block: 'center' });
  };

  const runExtraction = (label: string) => {
    startJob({
      title: `${label} — ${paper.id}`,
      kind: 'extraction',
      stages: [
        { label: 'Load sections', ms: 700 },
        { label: 'Chunk', ms: 600 },
        { label: 'Extract fields', ms: 1800 },
        { label: 'Score confidence', ms: 800 },
        { label: 'Stage for review', ms: 500 },
      ],
      href: `#/ledger/records?paper=${paper.id}`,
    });
    toast({
      text: `${label} queued for ${paper.id} — the demo extractor replays this paper's seeded records rather than minting new ones`,
      kind: 'info',
      href: '#/ledger/records',
      hrefLabel: 'Extract',
    });
  };

  const askQuery = topField
    ? `What does ${paper.id} report for ${fieldName(topField)}, and under what culture conditions?`
    : `Summarise the quantitative claims in ${paper.id} and flag anything still unverified.`;

  const parseFailed = paper.ingest === 'failed:parse';
  const ingesting = paper.ingest.startsWith('stage:');
  const onShelf = paper.ingest === 'shelf';

  const totalChars = paper.sections.reduce((n, s) => n + s.text.length, 0) || 1;

  // ── left pane ────────────────────────────────────────────────────────
  const renderWithSpans = (text: string, spans: Span[]): ReactNode => {
    if (spans.length === 0) return text;
    const out: ReactNode[] = [];
    let cursor = 0;
    for (const s of spans) {
      if (s.start > cursor) out.push(text.slice(cursor, s.start));
      const r = s.record;
      const isActive = activeId === r.id || hoverId === r.id;
      out.push(
        <mark
          key={r.id}
          id={`span-${r.id}`}
          ref={(el) => {
            spanRefs.current[r.id] = el;
          }}
          role="button"
          tabIndex={0}
          aria-pressed={activeId === r.id}
          aria-label={`Extraction ${r.id}: ${fieldName(r.field)}, ${r.value} ${r.unit}. Select to show in the extraction rail.`}
          title={`${r.id} · ${fieldName(r.field)} · ${r.value} ${r.unit}`}
          className={cx(
            markClass(r),
            isActive && 'span-active',
            pulseId === r.id && 'pulse-once',
            r.status === 'rejected' && 'opacity-60',
            'cursor-pointer',
          )}
          onClick={() => selectFromText(r.id)}
          onMouseEnter={() => setHoverId(r.id)}
          onMouseLeave={() => setHoverId(null)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              selectFromText(r.id);
            }
          }}
        >
          {text.slice(s.start, s.end)}
          <sup>{r.id}</sup>
        </mark>,
      );
      cursor = s.end;
    }
    if (cursor < text.length) out.push(text.slice(cursor));
    return out;
  };

  const miniMap = (
    <nav
      className="hidden lg:flex w-[14px] shrink-0 sticky top-0 self-start flex-col gap-[2px] h-[62vh] min-h-[280px]"
      aria-label="Section map — extraction density"
    >
      {paper.sections.map((s) => {
        const count = (sectionSpans.get(s.id) ?? []).length;
        const alpha = count === 0 ? 0 : Math.min(0.8, 0.16 + count * 0.14);
        return (
          <button
            key={s.id}
            onClick={() => sectionRefs.current[s.id]?.scrollIntoView({ behavior, block: 'start' })}
            className="w-full rounded-[2px] border border-line hover:border-accent transition-colors"
            style={{
              flexGrow: Math.max(1, s.text.length / totalChars * 100),
              background: alpha === 0 ? 'rgb(var(--surface-1))' : `rgb(var(--accent) / ${alpha})`,
            }}
            title={`${s.heading} — ${count} extraction${count === 1 ? '' : 's'}`}
            aria-label={`Jump to ${s.heading}, ${count} extraction${count === 1 ? '' : 's'}`}
          />
        );
      })}
    </nav>
  );

  const article = (
    <article className="flex-1 min-w-0 max-w-[760px]">
      <div className="mb-3 flex items-center gap-2 text-caption text-ink-soft">
        <a href={href('/trawl')} className="inline-flex items-center gap-1 hover:text-accent">
          <ArrowLeft size={12} /> Library
        </a>
        <span aria-hidden>/</span>
        <span className="font-num">{paper.id}</span>
      </div>

      <h1 className="font-serif text-page-title font-semibold leading-snug">{paper.title}</h1>

      <div className="mt-2 text-body text-ink-soft">
        {paper.authors.join(', ')}
        {' · '}
        <span className="font-num">{paper.year}</span>
        {' · '}
        <span className="italic">{paper.venue}</span>
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-1.5">
        {paper.organisms.map((o) => (
          <span key={o} className="chip italic">
            {o}
          </span>
        ))}
        {paper.topics.map((t) => (
          <span key={t} className="chip text-ink-soft">
            {t}
          </span>
        ))}
      </div>

      {paper.textSource === 'curation-note' && (
        <div className="mt-2 text-caption text-signal-warn flex items-start gap-1.5">
          <span
            className="inline-block w-[3px] h-3 rounded-[1px] shrink-0 mt-[3px]"
            style={{
              backgroundImage:
                'repeating-linear-gradient(to bottom, rgb(var(--signal-warn)) 0 3px, transparent 3px 6px)',
            }}
            aria-hidden
          />
          <span>
            Catalogued from OF-COR-001: a real, citable paper whose full text has not been ingested.
            The abstract and the highlighted spans below are the curator&rsquo;s note, not the
            paper&rsquo;s own words.
          </span>
        </div>
      )}

      {onShelf && (
        <div className="mt-4">
          <Callout kind="info" title="Not ingested yet">
            <p className="mb-2">
              <span className="font-num">{paper.id}</span> is still on the demo shelf, so it is not part of
              the searchable corpus and carries no extractions.
            </p>
            <div className="flex gap-2">
              <Button
                size="sm"
                onClick={() => {
                  ingestPaper(paper.id);
                  toast({
                    text: `Ingest started for ${paper.id}`,
                    kind: 'info',
                    href: '#/trawl/ingest',
                    hrefLabel: 'Board',
                  });
                }}
              >
                Ingest this paper
              </Button>
              <LinkButton to="/library/ingest" size="sm">
                Open ingest board
              </LinkButton>
            </div>
          </Callout>
        </div>
      )}

      {ingesting && (
        <div className="mt-4">
          <Callout kind="info" title="Ingest in progress">
            <span className="inline-flex items-center gap-1.5">
              <Loader2 size={13} className="animate-spin" />
              Currently at <strong>{stageLabelOf(paper, ingestJobFor(jobs, paper.id))}</strong>. Extractions
              appear once the pipeline reaches Extract.
            </span>
          </Callout>
        </div>
      )}

      {parseFailed && (
        <div className="mt-4">
          <Callout kind="error" title="Section boundaries not detected — full text unavailable">
            <p className="mb-2">
              The parser could not segment this paper into sections, so extraction spans cannot be anchored.
              The abstract below is the raw-text fallback.
            </p>
            <div className="flex gap-2">
              <Button
                size="sm"
                onClick={() => {
                  ingestPaper(paper.id);
                  toast({
                    text: `Retrying ingest for ${paper.id}`,
                    kind: 'info',
                    href: '#/trawl/ingest',
                    hrefLabel: 'Board',
                  });
                }}
              >
                <RefreshCw size={12} /> Retry ingest
              </Button>
              <LinkButton to="/library/ingest" size="sm">
                Open ingest board
              </LinkButton>
            </div>
          </Callout>
        </div>
      )}

      {!ready ? (
        <Card className="mt-5">
          <Skeleton rows={12} />
        </Card>
      ) : (
        <>
          <section className="mt-6">
            <h2 className="font-serif text-section-title font-semibold mb-1">Abstract</h2>
            <div className="prose-reading">
              <p>{paper.abstract}</p>
            </div>
          </section>

          {parseFailed ? (
            <section className="mt-4">
              <h2 className="font-serif text-section-title font-semibold mb-1">
                Raw text — unsegmented
              </h2>
              <p className="text-caption text-ink-soft mb-2">
                Recovered character stream from the fetch stage. Headings were not identified, so no
                extraction spans are anchored here.
              </p>
              <div className="card p-3 bg-surface-0 font-num text-caption leading-relaxed whitespace-pre-line max-h-[420px] overflow-y-auto">
                {paper.sections.length > 0
                  ? paper.sections.map((s) => `${s.heading}\n${s.text}`).join('\n\n')
                  : paper.abstract}
              </div>
            </section>
          ) : (
            paper.sections.map((s) => (
              <section
                key={s.id}
                ref={(el) => {
                  sectionRefs.current[s.id] = el;
                }}
                className="mt-6 scroll-mt-4"
              >
                <h2 className="font-serif text-section-title font-semibold mb-1">{s.heading}</h2>
                <div className="prose-reading">
                  <p style={{ whiteSpace: 'pre-line' }}>
                    {renderWithSpans(s.text, sectionSpans.get(s.id) ?? [])}
                  </p>
                </div>
              </section>
            ))
          )}
        </>
      )}
    </article>
  );

  // ── right rail ───────────────────────────────────────────────────────
  const rail = (
    <aside className="w-full xl:w-[360px] shrink-0 xl:sticky xl:top-0 self-start flex flex-col gap-3">
      <Card className="p-3">
        <SectionTitle
          right={
            <div
              className="flex rounded-input border border-line overflow-hidden"
              role="group"
              aria-label="Unit display"
            >
              {(['published', 'si'] as const).map((m) => (
                <button
                  key={m}
                  onClick={() => setUI({ unitMode: m })}
                  aria-pressed={unitMode === m}
                  className={cx(
                    'px-2 py-[2px] text-[11px]',
                    unitMode === m
                      ? 'bg-accent-wash text-ink font-medium'
                      : 'text-ink-soft hover:text-ink',
                  )}
                >
                  {m === 'published' ? 'Published' : 'SI'}
                </button>
              ))}
            </div>
          }
        >
          Extractions <span className="font-num text-ink-soft">{railRecords.length}</span>
        </SectionTitle>

        <CoverageDispute paper={paper} count={recs.length} />

        {railRecords.length === 0 ? (
          <EmptyState
            title="No extractions yet"
            body={
              parseFailed
                ? 'Nothing can be extracted until the paper parses into sections. Retry the ingest, or continue with abstract-only text from the ingest board.'
                : 'Nothing has been pulled from this paper yet. Run the extractor to stage candidate records for review.'
            }
            action={
              parseFailed ? (
                <LinkButton to="/library/ingest" size="sm">
                  Open ingest board
                </LinkButton>
              ) : (
                <Button size="sm" onClick={() => runExtraction('Extraction')}>
                  Run extraction
                </Button>
              )
            }
          />
        ) : (
          <div className="max-h-[46vh] overflow-y-auto -mx-1 px-1">
            {railRecords.map(({ record: r, located }) => {
              const p = provOf(r);
              const isActive = activeId === r.id;
              return (
                <button
                  key={r.id}
                  ref={(el) => {
                    rowRefs.current[r.id] = el;
                  }}
                  onClick={() => (located ? selectFromRail(r.id) : setActiveId(r.id))}
                  onMouseEnter={() => setHoverId(r.id)}
                  onMouseLeave={() => setHoverId(null)}
                  onFocus={() => setHoverId(r.id)}
                  onBlur={() => setHoverId(null)}
                  aria-pressed={isActive}
                  title={
                    located
                      ? `Scroll to the quoted span for ${r.id}`
                      : parseFailed
                        ? `${r.id}: spans cannot be anchored while the paper is unparsed`
                        : `${r.id}: the quoted text was not found in this paper's sections`
                  }
                  className={cx(
                    'w-full text-left rounded-input pr-1.5 py-1.5 mb-0.5 border transition-colors',
                    tickClass(p),
                    isActive
                      ? 'border-accent/50 bg-accent-wash'
                      : hoverId === r.id
                        ? 'border-line bg-ink-soft/[0.05]'
                        : 'border-transparent hover:bg-ink-soft/[0.05]',
                  )}
                >
                  <span className="sr-only">{`${provMeta(p).label}. `}</span>
                  <span className="flex items-baseline justify-between gap-2">
                    <span className="truncate">{fieldName(r.field)}</span>
                    <span className="font-num text-caption text-ink-soft shrink-0">{r.id}</span>
                  </span>
                  <span className="flex items-baseline justify-between gap-2 mt-0.5">
                    <span className="flex items-center gap-1.5">
                      <ContradictionRail
                        marks={peersByField.get(r.field) ?? []}
                        aggregate={aggregate(
                          (peersByField.get(r.field) ?? []).map((x) => x.record),
                        )}
                        contradictions={contradictions.filter((c: Contradiction) => c.recordIds.includes(r.id))}
                        highlightId={r.id}
                      />
                      <Quantity value={r.value} unit={r.unit} si={r.si} mode={unitMode} />
                    </span>
                    <span className="text-caption text-ink-soft font-num shrink-0">
                      {r.status === 'unverified'
                        ? `conf ${r.confidence.toFixed(2)}`
                        : r.status === 'rejected'
                          ? 'rejected'
                          : r.gold
                            ? 'gold'
                            : 'verified'}
                    </span>
                  </span>
                  {!located && (
                    <span className="mt-1 text-caption text-signal-warn flex items-center gap-1">
                      <AlertTriangle size={11} />
                      {parseFailed ? 'No anchor — paper is unparsed' : 'Quote not located in the text'}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        )}

        <div className="pt-2 mt-2 border-t border-line">
          <ProvenanceLegend />
        </div>
      </Card>

      <Card className="p-3">
        <div className="text-caption uppercase tracking-wide text-ink-soft mb-2">Paper actions</div>
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            onClick={() =>
              navigate(`/ask?q=${encodeURIComponent(askQuery)}&scope=${encodeURIComponent(paper.id)}`)
            }
            title={askQuery}
          >
            <MessageSquare size={13} /> Ask about this paper
          </Button>
          <Button size="sm" onClick={() => runExtraction('Re-extraction')}>
            <RefreshCw size={13} /> Queue re-extraction
          </Button>
          <Popover
            openOnHover={false}
            width={280}
            label="Add to collection"
            trigger={(pr) => (
              <button {...pr} className="btn btn-sm">
                <FolderPlus size={13} /> Add to collection
              </button>
            )}
          >
            <div className="space-y-1">
              <div className="text-caption text-ink-soft mb-1">
                Add <span className="font-num">{paper.id}</span> to:
              </div>
              {collections.length === 0 && (
                <div className="text-body text-ink-soft">No collections exist in this session.</div>
              )}
              {collections.map((c) => {
                const already = c.paperIds.includes(paper.id);
                return (
                  <button
                    key={c.id}
                    className="w-full flex items-center justify-between gap-2 px-1.5 py-1 rounded-input text-left hover:bg-accent-wash disabled:opacity-50 disabled:hover:bg-transparent"
                    disabled={already}
                    onClick={() => {
                      addCollectionPapers(c.id, [paper.id]);
                      toast({ text: `${paper.id} added to ${c.name}`, kind: 'success' });
                    }}
                  >
                    <span className="truncate">{c.name}</span>
                    <span className="font-num text-caption text-ink-soft shrink-0">
                      {already ? 'already in' : c.paperIds.length}
                    </span>
                  </button>
                );
              })}
            </div>
          </Popover>
        </div>
        <p className="text-caption text-ink-soft mt-2">
          Re-extraction replays this paper&rsquo;s seeded records through the pipeline animation; it does not
          invent new ones.
        </p>
      </Card>
    </aside>
  );

  return (
    <div className="flex flex-col xl:flex-row gap-5 items-start">
      <div className="flex gap-5 items-start w-full min-w-0">
        {miniMap}
        {article}
      </div>
      {rail}
    </div>
  );
}

/**
 * Coverage dispute (OF-FE-003 §8.4).
 *
 * A wrong value gets clicked and corrected. A missed one is invisible forever —
 * nothing in the interface counts what was never extracted, and no metric on the
 * Assay screen can see it either. This control is the only mechanism in the
 * system that surfaces recall failure, and it costs an afternoon.
 */
function CoverageDispute({ paper, count }: { paper: Paper; count: number }) {
  const disputeCoverage = useStore((s) => s.disputeCoverage);
  const [open, setOpen] = useState(false);
  const [note, setNote] = useState('');

  if (paper.coverageDisputed) {
    return (
      <div className="mb-2 text-caption border-l-2 border-signal-warn pl-2 py-1">
        <div className="text-signal-warn font-medium">Coverage disputed</div>
        <div className="text-ink-soft mt-0.5">{paper.coverageDisputed.note}</div>
        <div className="text-ink-soft mt-0.5">
          Filed {paper.coverageDisputed.at} · back in the review queue
        </div>
      </div>
    );
  }

  return (
    <div className="mb-2">
      <div className="flex items-baseline justify-between gap-2 flex-wrap">
        <span className="text-caption text-ink-soft">
          <span className="font-num text-ink">{count}</span> value
          {count === 1 ? '' : 's'} recorded from this source.
        </span>
        <button
          className="text-caption text-accent hover:underline"
          onClick={() => setOpen((v) => !v)}
        >
          Something’s missing.
        </button>
      </div>
      {open && (
        <div className="mt-2 border border-line rounded-card p-2.5">
          <label className="text-caption text-ink-soft block mb-1" htmlFor="cov-note">
            What did the extractor miss? A value, a table, a figure — anything it should have
            picked up and did not.
          </label>
          <textarea
            id="cov-note"
            className="input w-full text-body"
            rows={2}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Table 2 reports a secreted titer that is not in the record list."
          />
          <div className="flex items-center gap-2 mt-2">
            <Button
              disabled={note.trim().length === 0}
              onClick={() => {
                disputeCoverage(paper.id, note.trim());
                setOpen(false);
                setNote('');
              }}
            >
              File it
            </Button>
            <button
              className="text-caption text-ink-soft hover:text-ink"
              onClick={() => {
                setOpen(false);
                setNote('');
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
