// Ingest (OF-DES-001 §8.5). The demo shelf is the one live input method; the
// pipeline board on the right shows the same five stages a real ingest runs,
// including the scripted parse failure and its two recovery paths.
import { useMemo } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  FileUp,
  Link2,
  Loader2,
  Plus,
  RefreshCw,
  ShieldAlert,
} from 'lucide-react';
import type { Job, Paper } from '@/data/types';
import { useStore } from '@/store';
import { href } from '@/router';
import { OwnerTabs } from '@/components/OwnerTabs';
import { INTAKE_TABS } from '@/data/tabs';
import {
  Button,
  Callout,
  Card,
  EmptyState,
  LinkButton,
  PageHeader,
  SectionTitle,
  cx,
} from '@/components/ui';

const STAGE_KEYS = ['fetch', 'parse', 'chunk', 'embed', 'extract'] as const;
const STAGE_LABELS = ['Fetch', 'Parse', 'Chunk', 'Embed', 'Extract'];
/** Scripted stage budgets — the same values `ingestPaper` puts on the job. */
const DEFAULT_MS = [900, 1400, 700, 1100, 1800];
/**
 * The halt is pinned to the stage that actually failed
 * to the Parse cell. The job's stageIndex can drift a cell past it (the failure
 * is scheduled on a timer, not on the stage boundary), so it is clamped here.
 */
// Nothing gets past Fetch in this build: no network requests are made, so the
// pipeline halts at the first stage rather than at Parse.
const FAIL_STAGE_INDEX = STAGE_KEYS.indexOf('fetch');

type RowState = 'running' | 'complete' | 'failed' | 'degraded' | 'stalled';
type CellState = 'done' | 'active' | 'pending' | 'failed' | 'skipped' | 'notrun';

interface BoardRow {
  paper: Paper;
  job?: Job;
  state: RowState;
  stageIndex: number;
  extractions: number;
}

interface Cell {
  label: string;
  state: CellState;
  fill: number;
  timing: string;
}

const ROW_ORDER: Record<RowState, number> = {
  running: 0,
  failed: 1,
  stalled: 2,
  degraded: 3,
  complete: 4,
};

function ingestJobFor(jobs: Job[], paperId: string): Job | undefined {
  for (let i = jobs.length - 1; i >= 0; i--) {
    const j = jobs[i];
    if (j.kind !== 'ingest') continue;
    if (j.href?.endsWith(`/${paperId}`) || j.title.includes(paperId)) return j;
  }
  return undefined;
}

function secs(ms: number): string {
  return `${(ms / 1000).toFixed(1)} s`;
}

function cellsFor(row: BoardRow): Cell[] {
  const stages = row.job?.stages ?? [];
  const msOf = (i: number) => stages[i]?.ms ?? DEFAULT_MS[i];
  const progress = row.job?.stageProgress ?? 0;

  return STAGE_LABELS.map((label, i) => {
    const ms = msOf(i);
    if (row.state === 'complete') {
      return { label, state: 'done' as CellState, fill: 1, timing: secs(ms) };
    }
    if (row.state === 'failed' || row.state === 'degraded') {
      if (i < row.stageIndex) return { label, state: 'done' as CellState, fill: 1, timing: secs(ms) };
      if (i === row.stageIndex)
        return row.state === 'failed'
          ? { label, state: 'failed' as CellState, fill: 1, timing: 'halted' }
          : { label, state: 'skipped' as CellState, fill: 1, timing: 'skipped' };
      return { label, state: 'notrun' as CellState, fill: 0, timing: 'not run' };
    }
    if (row.state === 'stalled') {
      if (i < row.stageIndex) return { label, state: 'done' as CellState, fill: 1, timing: secs(ms) };
      if (i === row.stageIndex)
        return { label, state: 'active' as CellState, fill: 0.35, timing: '—' };
      return { label, state: 'pending' as CellState, fill: 0, timing: `~${secs(ms)}` };
    }
    // running
    if (i < row.stageIndex) return { label, state: 'done' as CellState, fill: 1, timing: secs(ms) };
    if (i === row.stageIndex)
      return { label, state: 'active' as CellState, fill: progress, timing: secs(ms * progress) };
    return { label, state: 'pending' as CellState, fill: 0, timing: `~${secs(ms)}` };
  });
}

const CELL_FILL: Record<CellState, string> = {
  done: 'bg-accent',
  active: 'bg-signal-info',
  pending: 'bg-transparent',
  failed: 'bg-signal-error',
  skipped: 'bg-signal-warn',
  notrun: 'bg-transparent',
};

const CELL_BORDER: Record<CellState, string> = {
  done: 'border-accent/35',
  active: 'border-signal-info/45',
  pending: 'border-line',
  failed: 'border-signal-error/50',
  skipped: 'border-signal-warn/45',
  notrun: 'border-line border-dashed',
};

export default function IntakeIngest() {
  const papers = useStore((s) => s.papers);
  const records = useStore((s) => s.records);
  const jobs = useStore((s) => s.jobs);
  const ingestPaper = useStore((s) => s.ingestPaper);
  const setPaperIngest = useStore((s) => s.setPaperIngest);
  const resetDemo = useStore((s) => s.resetDemo);
  const toast = useStore((s) => s.toast);

  // The demo shelf is gone with the synthetic corpus. What sits here now is
  // the real ingest queue: tranche-1 entries whose full text has not been
  // parsed yet (OF-COR-001 §22.6).
  const shelf = useMemo(
    () => papers.filter((p) => p.tranche === 1 && p.textSource === 'curation-note'),
    [papers],
  );

  const rows = useMemo<BoardRow[]>(() => {
    const counts = new Map<string, number>();
    for (const r of records) counts.set(r.paperId, (counts.get(r.paperId) ?? 0) + 1);

    const out: BoardRow[] = [];
    for (const paper of papers) {
      const job = ingestJobFor(jobs, paper.id);
      const ingesting = paper.ingest.startsWith('stage:');
      const failed = paper.ingest.startsWith('failed:');
      if (!job && !ingesting && !failed) continue;

      const seededIndex = Math.max(
        0,
        STAGE_KEYS.indexOf(paper.ingest.slice(6) as (typeof STAGE_KEYS)[number]),
      );

      let state: RowState;
      let stageIndex: number;
      if (failed) {
        state = 'failed';
        stageIndex = Math.min(job?.stageIndex ?? FAIL_STAGE_INDEX, FAIL_STAGE_INDEX);
      } else if (job?.status === 'running') {
        state = 'running';
        stageIndex = Math.min(job.stageIndex, STAGE_LABELS.length - 1);
      } else if (job?.status === 'failed') {
        state = 'failed';
        stageIndex = Math.min(job.stageIndex, FAIL_STAGE_INDEX);
      } else if (job?.status === 'done' || paper.ingest === 'complete') {
        state = 'complete';
        stageIndex = STAGE_LABELS.length;
      } else {
        state = 'stalled';
        stageIndex = seededIndex;
      }

      out.push({ paper, job, state, stageIndex, extractions: counts.get(paper.id) ?? 0 });
    }
    return out.sort(
      (a, b) => ROW_ORDER[a.state] - ROW_ORDER[b.state] || a.paper.id.localeCompare(b.paper.id),
    );
  }, [papers, jobs, records]);

  const addFromShelf = (paper: Paper) => {
    ingestPaper(paper.id);
    toast({
      text: `${paper.id} entered the pipeline — Fetch → Parse → Chunk → Embed → Extract`,
      kind: 'info',
    });
  };

  const continueDegraded = (row: BoardRow) => {
    setPaperIngest(row.paper.id, 'complete');
    toast({
      text: `${row.paper.id} joined the corpus with abstract-only text — extractions are limited to the abstract until it re-parses`,
      kind: 'warn',
      href: `#/biorepo/paper/${row.paper.id}`,
      hrefLabel: 'Open',
    });
  };

  return (
    <>
      <PageHeader
        eyebrow="Intake"
        title="Ingest papers"
        subtitle={
          <>
            Papers move through five stages before their spans anchor to the source rather than to a
            curation note. Nothing in the corpus has been through them yet: this build makes no
            network requests, so every run halts at Fetch with the reason it could not get the
            document. Roughly 55% of the corpus is openly retrievable; the rest needs institutional
            access.
          </>
        }
        actions={<LinkButton to="/biorepo">Back to BioRepo</LinkButton>}
      />
      <OwnerTabs tabs={INTAKE_TABS} />

      <div className="grid grid-cols-1 xl:grid-cols-[380px_minmax(0,1fr)] gap-5 items-start">
        {/* ── LEFT: input methods ───────────────────────────────────── */}
        <div className="space-y-4">
          <Card className="p-3">
            <SectionTitle
              right={
                <span className="text-caption text-ink-soft font-num">{shelf.length} available</span>
              }
            >
              Tranche 1 — ingest queue
            </SectionTitle>
            <p className="text-caption text-ink-soft mb-2">
              Papers held out of the seeded corpus. Adding one runs the full pipeline and genuinely joins
              it to the corpus for the rest of this session.
            </p>

            {shelf.length === 0 ? (
              <EmptyState
                title="The shelf is empty"
                body="Every tranche-1 entry already has parsed full text."
                action={
                  <Button size="sm" onClick={resetDemo}>
                    <RefreshCw size={13} /> Reset demo data
                  </Button>
                }
              />
            ) : (
              <div>
                {shelf.map((p) => (
                  <div
                    key={p.id}
                    className="flex items-start gap-3 py-2.5 border-b border-line last:border-0"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="font-num text-caption text-ink-soft">
                        {p.id} · {p.year}
                      </div>
                      <div className="font-serif leading-snug">{p.title}</div>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {p.organisms.map((o) => (
                          <span key={o} className="chip italic text-caption">
                            {o}
                          </span>
                        ))}
                      </div>
                    </div>
                    <Button
                      size="sm"
                      onClick={() => addFromShelf(p)}
                      aria-label={`Add ${p.id} to the ingest pipeline`}
                    >
                      <Plus size={13} /> Add
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* Inactive input methods — visibly present, explicitly off. */}
          <Card className="p-3">
            <div className="flex items-center justify-between gap-2 mb-1">
              <h2 className="font-serif text-section-title font-semibold text-ink-soft">
                Import by DOI list
              </h2>
              <span className="chip text-ink-soft border-dashed">Inactive</span>
            </div>
            <fieldset disabled className="opacity-55 space-y-2">
              <textarea
                className="input font-num h-[68px] resize-none"
                placeholder={'10.0000/openferment.demo.001\n10.0000/openferment.demo.002'}
                aria-label="DOI list (inactive in this demo)"
              />
              <Button size="sm">
                <Link2 size={13} /> Fetch metadata
              </Button>
            </fieldset>
            <p className="text-caption text-ink-soft mt-2">
              Not active in this build — no network requests are made.
            </p>
          </Card>

          <Card className="p-3">
            <div className="flex items-center justify-between gap-2 mb-1">
              <h2 className="font-serif text-section-title font-semibold text-ink-soft">
                Upload PDFs
              </h2>
              <span className="chip text-ink-soft border-dashed">Inactive</span>
            </div>
            <fieldset disabled className="opacity-55 space-y-2">
              <div className="rounded-card border border-dashed border-line py-5 grid place-items-center text-center gap-1">
                <FileUp size={18} className="text-ink-soft" aria-hidden />
                <span className="text-body text-ink-soft">Drop PDFs here</span>
              </div>
              <Button size="sm">Choose files</Button>
            </fieldset>
            <p className="text-caption text-ink-soft mt-2">
              Not active in this build — no network requests are made.
            </p>
          </Card>
        </div>

        {/* ── RIGHT: pipeline board ─────────────────────────────────── */}
        <div>
          <SectionTitle
            right={
              <span className="text-caption text-ink-soft font-num">
                {rows.filter((r) => r.state === 'running').length} running · {rows.length} total
              </span>
            }
          >
            Pipeline
          </SectionTitle>

          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-caption text-ink-soft mb-3">
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block w-3 h-1.5 rounded-full bg-accent" /> complete
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block w-3 h-1.5 rounded-full bg-signal-info" /> in progress
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block w-3 h-1.5 rounded-full bg-signal-warn" /> skipped
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block w-3 h-1.5 rounded-full bg-signal-error" /> halted
            </span>
            <span>Stage times are scripted demo budgets, not measured throughput.</span>
          </div>

          {rows.length === 0 ? (
            <Card>
              <EmptyState
                title="Nothing in the pipeline"
                body="Add a paper from the demo shelf on the left and its five stages will fill in here, left to right."
              />
            </Card>
          ) : (
            <div className="space-y-3">
              {rows.map((row) => {
                const cells = cellsFor(row);
                const statusText =
                  row.state === 'running'
                    ? `Stage ${Math.min(row.stageIndex + 1, 5)} of 5 — ${STAGE_LABELS[row.stageIndex]}`
                    : row.state === 'failed'
                      ? `Halted at ${STAGE_LABELS[row.stageIndex]}`
                      : row.state === 'degraded'
                        ? 'In corpus — abstract-only text'
                        : row.state === 'stalled'
                          ? `Waiting at ${STAGE_LABELS[row.stageIndex]} — resume to run the remaining stages`
                          : 'In corpus';
                return (
                  <Card key={row.paper.id} className="p-3">
                    <div className="flex items-start gap-3 mb-2">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-num text-caption text-ink-soft">{row.paper.id}</span>
                          {row.state === 'running' && (
                            <span className="chip text-signal-info border-signal-info/40">
                              <Loader2 size={11} className="animate-spin" /> Ingesting
                            </span>
                          )}
                          {row.state === 'complete' && (
                            <span className="chip text-accent border-accent/40">
                              <CheckCircle2 size={11} /> In corpus
                            </span>
                          )}
                          {row.state === 'failed' && (
                            <span className="chip text-signal-error border-signal-error/40">
                              <AlertTriangle size={11} /> Failed at {STAGE_LABELS[row.stageIndex]}
                            </span>
                          )}
                          {row.state === 'degraded' && (
                            <span className="chip text-signal-warn border-signal-warn/40">
                              <ShieldAlert size={11} /> Abstract only
                            </span>
                          )}
                          {row.state === 'stalled' && (
                            <span className="chip text-ink-soft border-dashed">Queued</span>
                          )}
                          {(row.state === 'complete' || row.state === 'degraded') && (
                            <span className="chip text-ink-soft">
                              <span className="font-num">{row.extractions}</span> extractions
                            </span>
                          )}
                        </div>
                        <a
                          href={href(`/biorepo/paper/${row.paper.id}`)}
                          className="font-serif leading-snug hover:text-accent hover:underline block mt-0.5"
                        >
                          {row.paper.title}
                        </a>
                        <div className="text-caption text-ink-soft mt-0.5" aria-live="polite">
                          {statusText}
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-2 shrink-0 justify-end">
                        {(row.state === 'complete' || row.state === 'degraded') && (
                          <LinkButton to={`/biorepo/paper/${row.paper.id}`} size="sm">
                            View paper
                          </LinkButton>
                        )}
                        {row.state === 'stalled' && (
                          <Button size="sm" onClick={() => ingestPaper(row.paper.id)}>
                            <RefreshCw size={12} /> Resume ingest
                          </Button>
                        )}
                      </div>
                    </div>

                    <div className="grid grid-cols-5 gap-1.5">
                      {cells.map((cell) => (
                        <div
                          key={cell.label}
                          className={cx('rounded-input border px-1.5 py-1', CELL_BORDER[cell.state])}
                        >
                          <div
                            className={cx(
                              'text-caption truncate',
                              cell.state === 'notrun' ? 'text-ink-soft' : 'text-ink',
                            )}
                          >
                            {cell.label}
                          </div>
                          <div className="h-1 mt-1 rounded-full bg-ink-soft/15 overflow-hidden">
                            <div
                              className={cx(
                                'h-full rounded-full transition-[width] duration-200',
                                CELL_FILL[cell.state],
                                row.state === 'stalled' && cell.state === 'active' && 'animate-pulse',
                              )}
                              style={{ width: `${Math.round(Math.max(0, Math.min(1, cell.fill)) * 100)}%` }}
                            />
                          </div>
                          <div className="font-num text-[10px] text-ink-soft mt-0.5">{cell.timing}</div>
                        </div>
                      ))}
                    </div>

                    {row.state === 'failed' && (
                      <div className="mt-3">
                        <Callout kind="error" title="Parse failed">
                          <p className="mb-2">
                            {row.job?.failReason ?? 'Source document could not be retrieved.'}
                          </p>
                          <p className="mb-2 text-ink-soft">
                            Retry re-runs the same parser. Continuing without full text admits the paper on
                            its abstract alone — extractions will be limited to that text and spans cannot
                            be anchored to sections.
                          </p>
                          <div className="flex flex-wrap gap-2">
                            <Button size="sm" onClick={() => ingestPaper(row.paper.id)}>
                              <RefreshCw size={12} /> Retry
                            </Button>
                            <Button size="sm" onClick={() => continueDegraded(row)}>
                              Mark as needing manual retrieval
                            </Button>
                          </div>
                        </Callout>
                      </div>
                    )}

                    {row.state === 'degraded' && (
                      <div className="mt-3">
                        <Callout kind="warn" title="Admitted with abstract-only text">
                          Full-text parsing never succeeded for{' '}
                          <span className="font-num">{row.paper.id}</span>, so Chunk, Embed and Extract did
                          not run over the body. Retry the parse to promote it to a full corpus member.
                          <div className="flex gap-2 mt-2">
                            <Button size="sm" onClick={() => ingestPaper(row.paper.id)}>
                              <RefreshCw size={12} /> Retry parse
                            </Button>
                          </div>
                        </Callout>
                      </div>
                    )}
                  </Card>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
