// Ingest (OF-DES-001 §8.5, OF-BLD-012 §5.4). The queue on the left is the
// one live input method; the pipeline board on the right shows what happened
// to each paper that entered it.
//
// TWO PATHS, LABELLED. When openferment-core is running, "Fetch" makes the
// first real network request this pipeline has ever made: the service asks
// Europe PMC for the JATS, splits it, and the paper's own text replaces the
// curation note. When the service is not running, the five-stage timer
// simulation runs instead and halts at Fetch with a reason naming the missing
// service. The board says which of the two it is showing, because a timed
// animation that looked like a fetch would be the exact fake this project
// exists to avoid.
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
import { START_COMMAND } from '@/lib/postdoc';
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
// The scripted path halts at Fetch: with no service there is nothing to fetch
// with. The live path halts wherever the service says it did.
const FAIL_STAGE_INDEX = STAGE_KEYS.indexOf('fetch');
/** The stages a real fetch actually runs. Chunk, Embed and Extract are not built. */
const REAL_STAGES = 2;

type RowState = 'running' | 'complete' | 'failed' | 'degraded' | 'stalled';
type CellState = 'done' | 'active' | 'pending' | 'failed' | 'skipped' | 'notrun';

interface BoardRow {
  paper: Paper;
  job?: Job;
  state: RowState;
  stageIndex: number;
  extractions: number;
  /** A real fetch (live, or applied from the overlay) rather than the timer simulation. */
  real: boolean;
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
    // A real fetch runs two stages and ticks off nothing it did not do.
    if (row.real && i >= REAL_STAGES) {
      return { label, state: 'notrun' as CellState, fill: 0, timing: 'not built' };
    }
    if (row.real) {
      if (row.state === 'complete') return { label, state: 'done' as CellState, fill: 1, timing: 'done' };
      if (row.state === 'failed') {
        if (i < row.stageIndex) return { label, state: 'done' as CellState, fill: 1, timing: 'done' };
        if (i === row.stageIndex) return { label, state: 'failed' as CellState, fill: 1, timing: 'halted' };
        return { label, state: 'notrun' as CellState, fill: 0, timing: 'not run' };
      }
      // running: the fetch owns both cells until the service answers
      return i === 0
        ? { label, state: 'active' as CellState, fill: 0.5, timing: 'in flight' }
        : { label, state: 'pending' as CellState, fill: 0, timing: 'after fetch' };
    }
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
  const serviceUp = useStore((s) => s.serviceUp);
  const live = serviceUp === true;

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
      const fetched = paper.textSource === 'full-text';
      // Papers the overlay brought in are on the board as well as papers
      // with a job — a fetch that happened before this page load is still a
      // thing that happened.
      if (!job && !ingesting && !failed && !fetched) continue;
      const real = fetched || Boolean(job?.real) || (!job && failed && Boolean(paper.ingestReason));

      const seededIndex = Math.max(
        0,
        STAGE_KEYS.indexOf(paper.ingest.slice(6) as (typeof STAGE_KEYS)[number]),
      );

      let state: RowState;
      let stageIndex: number;
      if (failed) {
        state = 'failed';
        stageIndex = real
          ? paper.ingest === 'failed:parse'
            ? STAGE_KEYS.indexOf('parse')
            : STAGE_KEYS.indexOf('fetch')
          : Math.min(job?.stageIndex ?? FAIL_STAGE_INDEX, FAIL_STAGE_INDEX);
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

      out.push({ paper, job, state, stageIndex, extractions: counts.get(paper.id) ?? 0, real });
    }
    return out.sort(
      (a, b) => ROW_ORDER[a.state] - ROW_ORDER[b.state] || a.paper.id.localeCompare(b.paper.id),
    );
  }, [papers, jobs, records]);

  const addFromShelf = (paper: Paper) => {
    ingestPaper(paper.id);
    toast({
      text: live
        ? `${paper.id} — asking Europe PMC for the full text`
        : `${paper.id} entered the simulated pipeline — Fetch → Parse → Chunk → Embed → Extract`,
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
            A paper enters the corpus here or not at all. Fetch asks Europe PMC for the open-access
            full text and splits it into sections, so a record&rsquo;s quote can anchor to the
            paper&rsquo;s own words rather than to a curation note. Twenty-seven of the 132 entries
            carry a PMCID and are fetchable; the DOI-only ones are looked up once; the rest need
            manual retrieval.
          </>
        }
        actions={<LinkButton to="/biorepo">Back to BioRepo</LinkButton>}
      />
      <OwnerTabs tabs={INTAKE_TABS} />

      {/* Which of the two paths this board is showing. Stated, not inferred. */}
      {serviceUp === false && (
        <div className="mb-4">
          <Callout kind="warn" title="Offline — the pipeline below is a timed simulation">
            The Intake service is not running, so nothing here makes a network request: every run
            halts at Fetch with a reason that says so, and no paper&rsquo;s text changes. Start it
            with <span className="font-num">{START_COMMAND}</span> from <span className="font-num">core/</span>{' '}
            and reload to fetch for real.
          </Callout>
        </div>
      )}
      {live && (
        <div className="mb-4">
          <Callout kind="info" title="Live — fetching through openferment-core">
            Fetch makes a real request to Europe PMC and the paper&rsquo;s own sections replace the
            curation note. Chunk, Embed and Extract are not built and the board says so rather than
            ticking them off.
          </Callout>
        </div>
      )}

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
              Tranche-1 entries whose full text has not been fetched. {live
                ? 'Fetch asks Europe PMC for the paper and, when it is open access, replaces the curation note with its own text.'
                : 'With the service down, Add runs the timed simulation and halts at Fetch.'}
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
                      <Plus size={13} /> {live ? 'Fetch' : 'Add'}
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
              Not active in this build. Fetch by identifier runs from the queue above.
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
              Not active in this build. Fetch by identifier runs from the queue above.
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
            <span>
              {live
                ? 'Chunk, Embed and Extract are not built; a fetched paper shows them as not run.'
                : 'Stage times are scripted demo budgets, not measured throughput.'}
            </span>
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
                          : row.real
                            ? `${row.paper.sections.length} sections from Europe PMC${row.paper.license ? ` · ${row.paper.license}` : ''}`
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
                              <CheckCircle2 size={11} /> {row.real ? 'Full text' : 'In corpus'}
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
                        <Callout kind="error" title={`Halted at ${STAGE_LABELS[row.stageIndex]}`}>
                          <p className="mb-2">
                            {row.job?.failReason ??
                              row.paper.ingestReason ??
                              'Source document could not be retrieved.'}
                          </p>
                          <p className="mb-2 text-ink-soft">
                            {row.real
                              ? 'The service records a miss so the same paper is not asked again; Retry forces a fresh request.'
                              : 'Retry re-runs the same parser. Continuing without full text admits the paper on its abstract alone — extractions will be limited to that text and spans cannot be anchored to sections.'}
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
