// Review queue (OF-DES-001 §8.7). One record at a time, every decision on the
// home row. The target is twenty records mouse-free in under four minutes, so
// the keyboard path is the primary path and the mouse is the fallback.
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Award,
  Ban,
  Check,
  ChevronLeft,
  ChevronRight,
  ClipboardCheck,
  FileDown,
  Gauge,
  Pencil,
  SkipForward,
  Timer,
  Undo2,
  AlertTriangle,
} from 'lucide-react';
import type { ExtractionRecord } from '@/data/types';
import { ONTOLOGY_BY_ID, fieldName } from '@/data/ontology';
import { useStore, provenanceOf } from '@/store';
import { href } from '@/router';
import { fmt, toSI } from '@/engine/units';
import { CitationChip } from '@/components/Chip';
import { ProvenanceBadge, Tick, type ProvKind } from '@/components/Provenance';
import { QuantityField, type QuantityValue } from '@/components/QuantityField';
import {
  Bar,
  Button,
  Callout,
  Card,
  EmptyState,
  LinkButton,
  PageHeader,
  SectionTitle,
  cx,
} from '@/components/ui';
import { DISCLOSURE, exportText } from '@/lib/csv';

// ── reject reasons (numbered so they are one keystroke away) ────────────

const REASONS: { key: string; label: string; hint: string }[] = [
  { key: 'wrong value', label: 'Wrong value', hint: 'The number does not match the source' },
  { key: 'wrong unit', label: 'Wrong unit', hint: 'The magnitude is right, the unit is not' },
  { key: 'wrong span', label: 'Wrong span', hint: 'The quote is not where this number comes from' },
  { key: 'not this field', label: 'Not this field', hint: 'The value belongs to a different parameter' },
  { key: 'duplicate', label: 'Duplicate', hint: 'Already captured by another record' },
];

// ── span-in-context ────────────────────────────────────────────────────

interface SpanContext {
  before: string;
  quote: string;
  after: string;
  clippedStart: boolean;
  clippedEnd: boolean;
}

/**
 * Locate the quote inside the section text and return the surrounding
 * paragraph, clipped to a readable window. Returns null when the quote is not
 * present — that is a real failure mode and must be shown, not papered over.
 */
function spanContext(text: string, quote: string, radius = 440): SpanContext | null {
  if (!quote) return null;
  const at = text.indexOf(quote);
  if (at < 0) return null;
  const qEnd = at + quote.length;

  const paraStart = (() => {
    const i = text.lastIndexOf('\n', at);
    return i < 0 ? 0 : i + 1;
  })();
  const paraEnd = (() => {
    const i = text.indexOf('\n', qEnd);
    return i < 0 ? text.length : i;
  })();

  let start = paraStart;
  let end = paraEnd;
  let clippedStart = false;
  let clippedEnd = false;

  if (at - start > radius) {
    const raw = at - radius;
    const sp = text.indexOf(' ', raw);
    start = sp > -1 && sp < at ? sp + 1 : raw;
    clippedStart = true;
  }
  if (end - qEnd > radius) {
    const raw = qEnd + radius;
    const sp = text.lastIndexOf(' ', raw);
    end = sp > qEnd ? sp : raw;
    clippedEnd = true;
  }

  return {
    before: text.slice(start, at),
    quote: text.slice(at, qEnd),
    after: text.slice(qEnd, end),
    clippedStart,
    clippedEnd,
  };
}

function mmss(ms: number): string {
  const total = Math.max(0, Math.floor(ms / 1000));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

function median(values: number[]): number | null {
  if (values.length === 0) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

function provOf(r: ExtractionRecord): ProvKind {
  return r.status === 'rejected' ? 'rejected' : provenanceOf(r);
}

/** Key hint rendered on a button — fades once the reviewer is using the keyboard. */
function Hint({ k, faded }: { k: string; faded: boolean }) {
  return (
    <span
      className={cx('kbd transition-opacity duration-500', faded ? 'opacity-30' : 'opacity-100')}
      aria-hidden
    >
      {k}
    </span>
  );
}

// ── screen ─────────────────────────────────────────────────────────────

export default function Review() {
  const records = useStore((s) => s.records);
  const papers = useStore((s) => s.papers);
  const queue = useStore((s) => s.reviewQueue);
  const index = useStore((s) => s.reviewIndex);
  const stats = useStore((s) => s.reviewStats);
  const undoDepth = useStore((s) => s.undoStack.length);
  const startReview = useStore((s) => s.startReview);
  const reviewDecide = useStore((s) => s.reviewDecide);
  const editRecord = useStore((s) => s.editRecord);
  const undoReview = useStore((s) => s.undoReview);
  const advanceReview = useStore((s) => s.advanceReview);
  const toast = useStore((s) => s.toast);

  const [origin, setOrigin] = useState<'extract' | 'session'>('extract');
  const [usedKeyboard, setUsedKeyboard] = useState(false);
  const [rejecting, setRejecting] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editBase, setEditBase] = useState<QuantityValue>({ value: 0, unit: '' });
  const [draft, setDraft] = useState<QuantityValue | null>(null);
  const [undoneCount, setUndoneCount] = useState(0);
  const [now, setNow] = useState(() => Date.now());
  const [frozenEnd, setFrozenEnd] = useState<number | null>(null);

  const seeded = useRef(false);
  const lastAt = useRef(Date.now());
  const timings = useRef<number[]>([]);

  // Arriving without a queue (deep link, refresh) fills it with everything
  // still unverified, so the screen is never a dead end.
  useEffect(() => {
    if (seeded.current) return;
    seeded.current = true;
    if (queue.length === 0) {
      const ids = useStore
        .getState()
        .records.filter((r) => r.status === 'unverified')
        .map((r) => r.id);
      if (ids.length > 0) {
        startReview(ids);
        setOrigin('session');
      }
    }
  }, [queue.length, startReview]);

  useEffect(() => {
    const t = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(t);
  }, []);

  useEffect(() => {
    lastAt.current = Date.now();
    setRejecting(false);
    setEditing(false);
  }, [index]);

  const byId = useMemo(() => new Map(records.map((r) => [r.id, r])), [records]);
  const queueRecords = useMemo(
    () => queue.map((id) => byId.get(id)).filter((r): r is ExtractionRecord => Boolean(r)),
    [queue, byId],
  );

  const complete = queue.length > 0 && index >= queue.length;
  const record = complete ? undefined : byId.get(queue[index]);

  useEffect(() => {
    if (complete && frozenEnd === null) setFrozenEnd(Date.now());
    if (!complete && frozenEnd !== null) setFrozenEnd(null);
  }, [complete, frozenEnd]);

  const elapsed = (frozenEnd ?? now) - stats.startedAt;

  // ── decisions ────────────────────────────────────────────────────────

  const recordTiming = useCallback(() => {
    timings.current.push(Date.now() - lastAt.current);
    lastAt.current = Date.now();
  }, []);

  const decide = useCallback(
    (action: 'accept' | 'reject' | 'skip' | 'gold', reason?: string) => {
      const target = useStore.getState();
      const id = target.reviewQueue[target.reviewIndex];
      if (!id) return;
      recordTiming();
      reviewDecide(id, action, reason ? { reason } : undefined);
      setRejecting(false);
      setEditing(false);
    },
    [recordTiming, reviewDecide],
  );

  const openEdit = useCallback(() => {
    const state = useStore.getState();
    const target = state.records.find((r) => r.id === state.reviewQueue[state.reviewIndex]);
    if (!target) return;
    // Inline editing is numeric-only; categorical records (kinase_identity,
    // glycan_species) are corrected by rejecting with a reason, not by typing
    // a number into a unit-aware field.
    if (typeof target.value !== 'number') return;
    setEditBase({ value: target.value, unit: target.unit });
    setDraft({ value: target.value, unit: target.unit });
    setRejecting(false);
    setEditing(true);
  }, []);

  const saveEdit = useCallback(
    (thenAccept: boolean) => {
      const state = useStore.getState();
      const id = state.reviewQueue[state.reviewIndex];
      if (!id || !draft) return;
      const before = state.records.find((r) => r.id === id);
      const changed = !before || before.value !== draft.value || before.unit !== draft.unit;
      if (changed) editRecord(id, draft.value, draft.unit);
      if (thenAccept) {
        recordTiming();
        reviewDecide(id, 'accept');
      } else {
        toast({
          text: changed
            ? `Correction stored on ${id} — the original extraction is kept in the audit trail`
            : `No change to ${id}`,
          kind: changed ? 'success' : 'info',
        });
      }
      setEditing(false);
    },
    [draft, editRecord, recordTiming, reviewDecide, toast],
  );

  const doUndo = useCallback(() => {
    if (useStore.getState().undoStack.length === 0) {
      toast({ text: 'Nothing left to undo in this session', kind: 'info' });
      return;
    }
    undoReview();
    timings.current.pop();
    lastAt.current = Date.now();
    setUndoneCount((n) => n + 1);
    setRejecting(false);
    setEditing(false);
  }, [toast, undoReview]);

  // ── keyboard (capture phase, so 'g' never leaks to the global rail nav) ─

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement | null;
      if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.isContentEditable)) return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;

      const own = (fn: () => void) => {
        e.preventDefault();
        e.stopPropagation();
        setUsedKeyboard(true);
        fn();
      };

      if (complete) {
        if (e.key.toLowerCase() === 'u' && undoDepth > 0) own(doUndo);
        return;
      }
      if (!record) return;

      if (editing) {
        if (e.key === 'Escape') own(() => setEditing(false));
        return;
      }

      if (rejecting) {
        const n = Number(e.key);
        if (Number.isInteger(n) && n >= 1 && n <= REASONS.length) {
          own(() => decide('reject', REASONS[n - 1].key));
          return;
        }
        if (e.key === 'Escape' || e.key.toLowerCase() === 'r') {
          own(() => setRejecting(false));
          return;
        }
        return;
      }

      switch (e.key.toLowerCase()) {
        case 'a':
          return own(() => decide('accept'));
        case 'r':
          return own(() => setRejecting(true));
        case 'e':
          return own(openEdit);
        case 's':
          return own(() => decide('skip'));
        case 'g':
          return own(() => decide('gold'));
        case 'u':
          return own(doUndo);
        case 'j':
          return own(() => advanceReview(1));
        case 'k':
          return own(() => advanceReview(-1));
        default:
          return;
      }
    };
    window.addEventListener('keydown', onKey, true);
    return () => window.removeEventListener('keydown', onKey, true);
  }, [advanceReview, complete, decide, doUndo, editing, openEdit, record, rejecting, undoDepth]);

  // ── session log ──────────────────────────────────────────────────────

  const exportLog = () => {
    const med = median(timings.current);
    const lines: string[] = [
      'openFerment — extraction review session log',
      ...DISCLOSURE,
      '',
      `Queue length            ${queue.length}`,
      `Queue position reached  ${index}`,
      `Session duration        ${mmss(elapsed)}`,
      `Median per record       ${med === null ? '—' : `${(med / 1000).toFixed(1)} s`}`,
      '',
      'Actions taken (a running tally — undone actions are still counted)',
      `  accepted              ${stats.accepted}`,
      `  rejected              ${stats.rejected}`,
      `  edited                ${stats.edited}`,
      `  skipped               ${stats.skipped}`,
      `  flagged for gold      ${stats.gold}`,
      `  undone                ${undoneCount}`,
      '',
      'Queue outcome (final state of each record)',
      `  verified              ${queueRecords.filter((r) => r.status === 'verified').length}`,
      `  rejected              ${queueRecords.filter((r) => r.status === 'rejected').length}`,
      `  still unverified      ${queueRecords.filter((r) => r.status === 'unverified').length}`,
      `  in gold set           ${queueRecords.filter((r) => r.gold).length}`,
      '',
      '--- Records -------------------------------------------------------',
    ];
    for (const r of queueRecords) {
      lines.push('');
      lines.push(`[${r.id}] ${fieldName(r.field)} — ${r.paperId} §${r.sectionId}`);
      lines.push(
        `  as published: ${fmt(r.value)} ${r.unit}    SI: ${fmt(r.si.value)} ${r.si.unit}    confidence ${r.confidence.toFixed(2)}`,
      );
      lines.push(
        `  status: ${r.gold ? 'verified · gold set' : r.status}${r.reviewer ? ` (reviewer ${r.reviewer})` : ''}${
          r.rejectReason ? ` — ${r.rejectReason}` : ''
        }`,
      );
      if (r.corrected) {
        lines.push(`  correction: ${fmt(r.corrected.value)} ${r.corrected.unit}`);
      }
      lines.push(`  extractor: openFerment demo extractor ${r.extractorRun}`);
      lines.push(`  quote: “${r.quote}”`);
      for (const a of r.audit) {
        const delta =
          a.from !== undefined || a.to !== undefined
            ? `  (${a.from === undefined ? '—' : String(a.from)} → ${a.to === undefined ? '—' : String(a.to)})`
            : '';
        lines.push(`  audit: ${a.at}  ${a.who}  ${a.action}${delta}`);
      }
    }
    lines.push('');
    lines.push('End of log. Synthetic demonstration data — not evidence.');
    exportText('openferment-review-session.txt', lines.join('\n'));
  };

  // ── empty queue ──────────────────────────────────────────────────────

  if (queue.length === 0) {
    return (
      <>
        <PageHeader
          eyebrow="Module 0 · Evidence"
          title="Review queue"
          subtitle="Accept, correct, or reject each extraction against the span it came from."
        />
        <Card className="max-w-2xl">
          <EmptyState
            icon={<ClipboardCheck size={22} />}
            title="Nothing waiting for review"
            body="Every extraction in this session has already been decided. Queue a new batch from the Extract table — filter it first and only those rows enter the queue."
            action={
              <div className="flex gap-2">
                <LinkButton to="/extract" variant="primary">
                  Open Extract
                </LinkButton>
                <LinkButton to="/extract/validation">Open validation</LinkButton>
              </div>
            }
          />
        </Card>
      </>
    );
  }

  // ── top strip ────────────────────────────────────────────────────────

  const papersInQueue = new Set(queueRecords.map((r) => r.paperId)).size;
  const fieldsInQueue = new Set(queueRecords.map((r) => r.field)).size;

  const topStrip = (
    <Card className="p-3 mb-4">
      <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
        <div className="min-w-[150px]">
          <div className="text-caption uppercase tracking-wide text-ink-soft">Progress</div>
          <div className="font-num text-section-title leading-tight">
            {Math.min(index + (complete ? 0 : 1), queue.length)} / {queue.length}
          </div>
          <div className="mt-1 w-[150px]">
            <Bar value={index} max={queue.length} />
          </div>
        </div>

        <div className="min-w-[220px] flex-1">
          <div className="text-caption uppercase tracking-wide text-ink-soft">This queue</div>
          <div className="text-body">
            <span className="font-num">{queue.length}</span> records ·{' '}
            <span className="font-num">{papersInQueue}</span> paper{papersInQueue === 1 ? '' : 's'} ·{' '}
            <span className="font-num">{fieldsInQueue}</span> field{fieldsInQueue === 1 ? '' : 's'}
          </div>
          <div className="text-caption text-ink-soft">
            {origin === 'extract'
              ? 'Queued from the Extract table as it was filtered.'
              : 'Auto-filled with every unverified record in this session.'}
          </div>
        </div>

        <div>
          <div className="text-caption uppercase tracking-wide text-ink-soft">Session</div>
          <div
            className="font-num text-section-title leading-tight inline-flex items-center gap-1.5"
            role="timer"
            aria-label={`Session elapsed ${mmss(elapsed)}`}
          >
            <Timer size={14} className="text-ink-soft" aria-hidden />
            {mmss(elapsed)}
          </div>
        </div>

        <Button
          onClick={doUndo}
          disabled={undoDepth === 0}
          title={
            undoDepth === 0
              ? 'No decisions to undo yet'
              : `Undo the last of ${undoDepth} action${undoDepth === 1 ? '' : 's'} — restores the record and the queue position`
          }
        >
          <Undo2 size={14} /> Undo
          <Hint k="u" faded={usedKeyboard} />
        </Button>
      </div>
    </Card>
  );

  // ── queue complete ───────────────────────────────────────────────────

  if (complete) {
    const med = median(timings.current);
    const verified = queueRecords.filter((r) => r.status === 'verified').length;
    const rejected = queueRecords.filter((r) => r.status === 'rejected').length;
    const untouched = queueRecords.filter((r) => r.status === 'unverified').length;
    const goldNow = queueRecords.filter((r) => r.gold).length;

    const tally: { label: string; n: number; tone?: string }[] = [
      { label: 'Accepted', n: stats.accepted, tone: 'text-accent' },
      { label: 'Rejected', n: stats.rejected, tone: 'text-signal-error' },
      { label: 'Edited', n: stats.edited },
      { label: 'Skipped', n: stats.skipped },
      { label: 'Flagged for gold', n: stats.gold, tone: 'text-gold' },
      { label: 'Undone', n: undoneCount },
    ];

    return (
      <>
        <PageHeader
          eyebrow="Module 0 · Evidence"
          title="Queue complete"
          subtitle="Every record in this queue has been through the reviewer. The tallies below separate what you did from where the records ended up."
        />
        {topStrip}

        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px] items-start">
          <Card className="p-4">
            <SectionTitle>Session summary</SectionTitle>

            <div className="text-caption uppercase tracking-wide text-ink-soft mt-3 mb-1.5">
              Actions taken
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {tally.map((t) => (
                <div key={t.label} className="rounded-card border border-line p-2.5">
                  <div className={cx('font-num text-display leading-tight', t.tone)}>{t.n}</div>
                  <div className="text-caption text-ink-soft">{t.label}</div>
                </div>
              ))}
            </div>
            <p className="text-caption text-ink-soft mt-2">
              This is a log of keystrokes, not of outcomes: an action you later undid is still
              counted here. The queue outcome below is the state the records are actually in.
            </p>

            <div className="text-caption uppercase tracking-wide text-ink-soft mt-5 mb-1.5">
              Queue outcome
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="rounded-card border border-line p-2.5">
                <div className="font-num text-display leading-tight text-accent">{verified}</div>
                <div className="text-caption text-ink-soft">Verified</div>
              </div>
              <div className="rounded-card border border-line p-2.5">
                <div className="font-num text-display leading-tight text-signal-error">{rejected}</div>
                <div className="text-caption text-ink-soft">Rejected</div>
              </div>
              <div className="rounded-card border border-line p-2.5">
                <div className="font-num text-display leading-tight text-gold">{goldNow}</div>
                <div className="text-caption text-ink-soft">In gold set</div>
              </div>
              <div className="rounded-card border border-line p-2.5">
                <div className="font-num text-display leading-tight text-ink-soft">{untouched}</div>
                <div className="text-caption text-ink-soft">Still unverified</div>
              </div>
            </div>

            <div className="mt-5 grid grid-cols-2 gap-3">
              <div className="rounded-card border border-line p-2.5">
                <div className="font-num text-section-title leading-tight">
                  {med === null ? '—' : `${(med / 1000).toFixed(1)} s`}
                </div>
                <div className="text-caption text-ink-soft">
                  Median per record
                  {med === null ? ' — no decisions timed' : ` · ${timings.current.length} timed`}
                </div>
              </div>
              <div className="rounded-card border border-line p-2.5">
                <div className="font-num text-section-title leading-tight">{mmss(elapsed)}</div>
                <div className="text-caption text-ink-soft">Session duration</div>
              </div>
            </div>

            <div className="flex flex-wrap gap-2 mt-5 pt-4 border-t border-line">
              <Button onClick={exportLog}>
                <FileDown size={14} /> Export session log
              </Button>
              <LinkButton to="/extract/validation" variant="primary">
                <Gauge size={14} /> Open validation
              </LinkButton>
              <Button onClick={() => advanceReview(-1)} title="Step back into the last record">
                <ChevronLeft size={14} /> Back to the last record
              </Button>
              <LinkButton to="/extract">Back to Extract</LinkButton>
            </div>
          </Card>

          <Card className="p-4">
            <SectionTitle>What changed</SectionTitle>
            <p className="text-body text-ink-soft mb-3">
              Promoting a record to the gold set changes the denominator on the validation screen —
              precision and recall are recomputed from the gold set as it stands right now, not from
              a frozen snapshot.
            </p>
            <div className="space-y-1.5 max-h-[46vh] overflow-y-auto pr-1">
              {queueRecords
                .filter((r) => r.status !== 'unverified' || r.gold)
                .map((r) => (
                  <div
                    key={r.id}
                    className={cx(
                      'rounded-input border border-line px-2 py-1.5',
                      r.gold && 'border-gold/40',
                    )}
                  >
                    <div className="flex items-baseline justify-between gap-2">
                      <span className="truncate text-body">{fieldName(r.field)}</span>
                      <span className="font-num text-caption text-ink-soft shrink-0">{r.id}</span>
                    </div>
                    <div className="flex items-baseline justify-between gap-2 text-caption">
                      <span className="font-num">
                        {fmt(r.value)} {r.unit}
                      </span>
                      <span
                        className={cx(
                          r.gold
                            ? 'text-gold'
                            : r.status === 'verified'
                              ? 'text-accent'
                              : 'text-signal-error',
                        )}
                      >
                        {r.gold ? 'gold' : r.status}
                      </span>
                    </div>
                  </div>
                ))}
              {queueRecords.every((r) => r.status === 'unverified' && !r.gold) && (
                <div className="text-body text-ink-soft">
                  Nothing in this queue changed state — every record was skipped or stepped past.
                </div>
              )}
            </div>
          </Card>
        </div>
      </>
    );
  }

  // ── missing record (defensive) ───────────────────────────────────────

  if (!record) {
    return (
      <>
        <PageHeader eyebrow="Module 0 · Evidence" title="Review queue" />
        {topStrip}
        <Card className="p-4 max-w-2xl">
          <Callout kind="warn" title="This queue entry no longer resolves">
            <p className="mb-2">
              <span className="font-num">{queue[index]}</span> is in the queue but not in this
              session&rsquo;s records. Session state resets on refresh, so a queue built before a
              reset can outlive its rows.
            </p>
            <Button size="sm" onClick={() => advanceReview(1)}>
              Skip past it <ChevronRight size={13} />
            </Button>
          </Callout>
        </Card>
      </>
    );
  }

  // ── the record ───────────────────────────────────────────────────────

  const def = ONTOLOGY_BY_ID[record.field];
  const paper = papers.find((p) => p.id === record.paperId);
  const section = paper?.sections.find((s) => s.id === record.sectionId);
  const ctx = section ? spanContext(section.text, record.quote) : null;
  const prov = provOf(record);
  const draftSI = draft ? toSI(draft.value, draft.unit) : null;

  return (
    <>
      <PageHeader
        eyebrow="Module 0 · Evidence"
        title="Review queue"
        subtitle="Judge each extraction against the sentence it was pulled from. Accept, correct, or reject — the audit trail keeps both the original and your correction."
        actions={
          <>
            <Button
              onClick={() => advanceReview(-1)}
              disabled={index === 0}
              title="Previous record without deciding"
              aria-label="Previous record"
            >
              <ChevronLeft size={14} /> Prev
              <Hint k="k" faded={usedKeyboard} />
            </Button>
            <Button
              onClick={() => advanceReview(1)}
              title="Next record without deciding"
              aria-label="Next record"
            >
              Next <ChevronRight size={14} />
              <Hint k="j" faded={usedKeyboard} />
            </Button>
          </>
        }
      />

      {topStrip}

      <p className="sr-only" aria-live="polite">
        {`Record ${index + 1} of ${queue.length}. ${fieldName(record.field)}, ${fmt(record.value)} ${
          record.unit
        }, confidence ${record.confidence.toFixed(2)}, from ${record.paperId}.`}
      </p>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px] items-start">
        {/* ── centre card ────────────────────────────────────────────── */}
        <Card className="p-4">
          <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
            <span className="font-num text-caption text-ink-soft">{record.id}</span>
            <ProvenanceBadge
              p={prov}
              confidence={record.status === 'unverified' ? record.confidence : undefined}
            />
          </div>

          <h2 className="font-serif text-section-title font-semibold">{def.name}</h2>
          <p className="text-body text-ink-soft mt-1 max-w-2xl">{def.definition}</p>
          <p className="text-caption text-ink-soft mt-1">
            Ontology range{' '}
            <span className="font-num">
              {def.range[0]}–{def.range[1]} {def.canonicalUnit || '(dimensionless)'}
            </span>
            {def.notes ? ` · ${def.notes}` : ''}
          </p>

          {/* value block */}
          <div className="grid sm:grid-cols-3 gap-3 mt-4">
            <div className="rounded-card border border-line p-3">
              <div className="text-caption uppercase tracking-wide text-ink-soft">As published</div>
              <div className="font-num text-display leading-tight">
                {fmt(record.value)}
                {record.unit && <span className="text-section-title text-ink-soft ml-1">{record.unit}</span>}
              </div>
            </div>
            <div className="rounded-card border border-line p-3">
              <div className="text-caption uppercase tracking-wide text-ink-soft">SI twin</div>
              <div className="font-num text-display leading-tight">
                {fmt(record.si.value)}
                {record.si.unit && (
                  <span className="text-section-title text-ink-soft ml-1">{record.si.unit}</span>
                )}
              </div>
            </div>
            <div className="rounded-card border border-line p-3">
              <div className="text-caption uppercase tracking-wide text-ink-soft">Confidence</div>
              <div className="font-num text-display leading-tight">
                {record.confidence.toFixed(2)}
              </div>
              <div className="mt-1.5">
                <Bar
                  value={record.confidence}
                  className={cx(
                    record.confidence < 0.7 && 'bg-signal-warn',
                    record.confidence > 0.85 && 'bg-accent',
                  )}
                />
              </div>
            </div>
          </div>

          {record.corrected && (
            <div className="mt-3">
              <Callout kind="info" title="Already corrected in this session">
                Original extraction is preserved in the audit trail; the current value is{' '}
                <span className="font-num">
                  {fmt(record.corrected.value)} {record.corrected.unit}
                </span>
                .
              </Callout>
            </div>
          )}

          {/* inline editor */}
          {editing && (
            <div className="mt-4 rounded-card border border-accent/45 bg-accent-wash/40 p-3 anim-in">
              <div className="text-caption uppercase tracking-wide text-ink-soft mb-1.5">
                Correct the value
              </div>
              <div className="max-w-sm">
                <QuantityField
                  field={record.field}
                  value={editBase}
                  onChange={setDraft}
                  onSubmit={() => saveEdit(true)}
                  autoFocus
                  id={`edit-${record.id}`}
                />
              </div>
              <div className="flex flex-wrap items-center gap-2 mt-3">
                <Button variant="primary" onClick={() => saveEdit(true)} disabled={!draft}>
                  <Check size={14} /> Save &amp; accept
                </Button>
                <Button onClick={() => saveEdit(false)} disabled={!draft}>
                  Save correction only
                </Button>
                <Button onClick={() => setEditing(false)}>Cancel</Button>
                {draftSI && draft && (
                  <span className="text-caption text-ink-soft font-num">
                    stores {fmt(draft.value)} {draft.unit} = {fmt(draftSI.value)} {draftSI.unit}
                  </span>
                )}
              </div>
              <p className="text-caption text-ink-soft mt-2">
                Saving keeps the original extraction —{' '}
                <span className="font-num">
                  {fmt(record.value)} {record.unit}
                </span>{' '}
                — as a from/to entry in the audit trail.
              </p>
            </div>
          )}

          {/* span in context */}
          <div className="mt-5 pt-4 border-t border-line">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
              <div className="flex items-center gap-2">
                <CitationChip paperId={record.paperId} />
                <span className="text-caption text-ink-soft">
                  {paper ? paper.title : 'Source unavailable'}
                  {section ? ` · ${section.heading}` : ''}
                </span>
              </div>
              <a
                href={href(`/library/papers/${record.paperId}?span=${record.id}`)}
                className="text-caption text-accent hover:underline"
              >
                Open in the reader
              </a>
            </div>

            {ctx ? (
              <div className="prose-reading">
                <p style={{ whiteSpace: 'pre-line' }}>
                  {ctx.clippedStart && <span className="text-ink-soft">… </span>}
                  {ctx.before}
                  <mark className="span-unverified">{ctx.quote}</mark>
                  {ctx.after}
                  {ctx.clippedEnd && <span className="text-ink-soft"> …</span>}
                </p>
              </div>
            ) : (
              <Callout kind="warn" title="Quote not located in the parsed section">
                <p className="mb-2">
                  The extractor recorded this span, but the exact string is not present in{' '}
                  {section ? (
                    <>
                      <span className="font-serif">{section.heading}</span>
                    </>
                  ) : (
                    <span className="font-num">§{record.sectionId}</span>
                  )}
                  . Reject with <em>wrong span</em> unless you can confirm it in the reader.
                </p>
                <div className="font-serif italic rounded-input border border-line bg-surface-0 p-2">
                  “{record.quote}”
                </div>
              </Callout>
            )}
          </div>
        </Card>

        {/* ── right rail: audit + extractor ──────────────────────────── */}
        <Card className="p-4">
          <SectionTitle>Audit trail</SectionTitle>
          {record.audit.length === 0 ? (
            <p className="text-body text-ink-soft">
              Nothing has happened to this record beyond the extraction that created it.
            </p>
          ) : (
            <ol className="space-y-2.5 max-h-[42vh] overflow-y-auto pr-1">
              {record.audit.map((a, i) => (
                <li key={`${a.at}-${i}`} className="border-l border-line pl-2.5">
                  <div className="text-caption font-num text-ink-soft">{a.at}</div>
                  <div className="text-body">
                    <span className="font-medium">{a.who}</span> — {a.action}
                  </div>
                  {(a.from !== undefined || a.to !== undefined) && (
                    <div className="text-caption font-num mt-0.5">
                      <span className="text-ink-soft line-through">
                        {a.from === undefined ? '—' : String(a.from)}
                      </span>
                      <span className="mx-1 text-ink-soft" aria-hidden>
                        →
                      </span>
                      <span className="text-accent">
                        {a.to === undefined ? '—' : String(a.to)}
                      </span>
                    </div>
                  )}
                </li>
              ))}
            </ol>
          )}

          <div className="mt-4 pt-3 border-t border-line">
            <div className="text-caption uppercase tracking-wide text-ink-soft mb-1.5">
              Extractor
            </div>
            <Tick p="demo" title="Synthetic demonstration extractor">
              <div className="text-body">openFerment demo extractor</div>
              <div className="font-num text-caption text-ink-soft">
                run {record.extractorRun} · field {record.field}
              </div>
            </Tick>
            <p className="text-caption text-ink-soft mt-2">
              No model is executed in this Sim. The run label identifies which seeded extraction
              pass produced the record; confidence is authored, not inferred.
            </p>
          </div>

          {record.organism && (
            <div className="mt-4 pt-3 border-t border-line">
              <div className="text-caption uppercase tracking-wide text-ink-soft mb-1">Context</div>
              <div className="text-body italic">{record.organism}</div>
              {record.componentTag && (
                <div className="text-caption text-ink-soft">component · {record.componentTag}</div>
              )}
            </div>
          )}
        </Card>
      </div>

      {/* ── action bar ───────────────────────────────────────────────── */}
      <div className="sticky bottom-0 mt-4 z-20">
        <Card className="p-3">
          {rejecting ? (
            <div className="anim-in">
              <div className="text-caption uppercase tracking-wide text-ink-soft mb-2">
                Reject — why?
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {REASONS.map((r, i) => (
                  <button
                    key={r.key}
                    className="chip hover:bg-signal-error/10 hover:border-signal-error/40"
                    onClick={() => decide('reject', r.key)}
                    title={r.hint}
                  >
                    <span className="kbd">{i + 1}</span>
                    {r.label}
                  </button>
                ))}
                <Button onClick={() => setRejecting(false)}>
                  Cancel <span className="kbd">Esc</span>
                </Button>
              </div>
            </div>
          ) : (
            <div className="flex flex-wrap items-center gap-2">
              <Button
                variant="primary"
                onClick={() => decide('accept')}
                title="Accept this extraction as verified — shortcut a"
              >
                <Check size={14} /> Accept
                <Hint k="a" faded={usedKeyboard} />
              </Button>
              <Button
                onClick={() => setRejecting(true)}
                title="Reject and pick a reason — shortcut r"
              >
                <Ban size={14} /> Reject
                <Hint k="r" faded={usedKeyboard} />
              </Button>
              <Button onClick={openEdit} title="Correct the value inline — shortcut e">
                <Pencil size={14} /> Edit value
                <Hint k="e" faded={usedKeyboard} />
              </Button>
              <Button
                onClick={() => decide('skip')}
                title="Leave undecided and move on — shortcut s"
              >
                <SkipForward size={14} /> Skip
                <Hint k="s" faded={usedKeyboard} />
              </Button>
              <Button
                onClick={() => decide('gold')}
                title="Verify and promote this record into the curated gold set — shortcut g"
              >
                <Award size={14} /> Flag for gold
                <Hint k="g" faded={usedKeyboard} />
              </Button>

              <div className="flex-1" />

              <span className="text-caption text-ink-soft hidden md:inline">
                <span className="kbd">j</span> / <span className="kbd">k</span> move ·{' '}
                <span className="kbd">u</span> undo
              </span>
            </div>
          )}
        </Card>
      </div>

      {record.confidence < 0.7 && !editing && (
        <div className="mt-3 max-w-3xl">
          <Callout kind="warn" title="Low extractor confidence">
            <span className="inline-flex items-start gap-1.5">
              <AlertTriangle size={13} className="mt-[3px] shrink-0" aria-hidden />
              <span>
                Confidence <span className="font-num">{record.confidence.toFixed(2)}</span> is below
                the <span className="font-num">0.70</span> band. Read the span before accepting — this
                is where unit-normalisation errors cluster.
              </span>
            </span>
          </Callout>
        </div>
      )}
    </>
  );
}
