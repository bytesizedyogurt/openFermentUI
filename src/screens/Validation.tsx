// Validation (OF-DES-001 §8.8). The screen a sceptical PI judges the platform
// by, so every number here is either measured or explicitly marked as
// undefined. Metrics recompute from the live gold set: promote a record in the
// review queue and these numbers move.
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import {
  ArrowDown,
  ArrowUp,
  Download,
  FileWarning,
  Gauge,
  Minus,
  ScrollText,
  Send,
  ArrowUpDown,
} from 'lucide-react';
import type { ExtractionRecord, ExtractorRun, FieldId, RunOutput } from '@/data/types';
import { fieldName } from '@/data/ontology';
import { useStore } from '@/store';
import { computeRunMetrics, type FieldMetrics, type RunMetrics } from '@/engine/metrics';
import { GOLD_SET_PLAN, GOLD_SET_DIFFICULTY_CASES } from '@/data/runOutputs';
import { ONTOLOGY_GAPS } from '@/data/ontology';
import { convert, fmt, sameFamily, toSI } from '@/engine/units';
import { href } from '@/router';
import { CitationChip } from '@/components/Chip';
import { ProvenanceBadge, Tick } from '@/components/Provenance';
import {
  Bar,
  Button,
  Callout,
  Card,
  EmptyState,
  Explain,
  LinkButton,
  PageHeader,
  SectionTitle,
  Sheet,
  Skeleton,
  cx,
} from '@/components/ui';
import { useCategorical } from '@/lib/viz';
import { exportCSV } from '@/lib/csv';
import { delayClass } from '@/sim/latency';

// ── run identity ───────────────────────────────────────────────────────

const RUN_ORDER: ExtractorRun[] = ['v0.3', 'v0.4', 'v0.4r'];
const RUN_LABEL: Record<ExtractorRun, string> = {
  'v0.3': 'v0.3',
  'v0.4': 'v0.4',
  'v0.4r': 'v0.4 + rules',
};
const RUN_BLURB: Record<ExtractorRun, string> = {
  'v0.3': 'Baseline pass — span retrieval plus a single extraction prompt.',
  'v0.4': 'Adds unit normalisation against the ontology before scoring.',
  'v0.4r': 'v0.4 with hand-written guard rules for the fields that failed most.',
};

const INSUFFICIENT_N = 5;

const OUTCOME_LABEL: Record<string, string> = {
  value_mismatch: 'Value mismatch',
  unit_error: 'Unit normalisation',
  span_error: 'Wrong span',
  miss: 'Missed entirely',
  spurious: 'Spurious extraction',
};

const OUTCOME_EXPLAIN: Record<string, string> = {
  value_mismatch:
    'The run anchored the right sentence and the right field, but read a different number out of it. Counts once as a false positive and once as a false negative.',
  unit_error:
    'The magnitude was read correctly and the unit was not, so the normalised value is wrong. Counts once as a false positive and once as a false negative.',
  span_error:
    'The run attributed the value to a different sentence. The run output records the outcome but not the rejected span, so only the curated span can be shown below.',
  miss: 'The run produced no record for this gold annotation. Counts as a false negative only.',
  spurious:
    'The run produced a record the curated set does not contain. Counts as a false positive only; there is no gold annotation to compare against.',
};

/** Severity colouring for the extracted side of a diff — never a provenance hue. */
function extractedTone(outcome: string): string {
  return outcome === 'value_mismatch' || outcome === 'unit_error'
    ? 'text-signal-warn'
    : 'text-signal-error';
}

// ── span-in-context (local, mirrors the reader's anchoring) ─────────────

interface SpanContext {
  before: string;
  quote: string;
  after: string;
  clipped: boolean;
}

function spanContext(text: string, quote: string, radius = 260): SpanContext | null {
  if (!quote) return null;
  const at = text.indexOf(quote);
  if (at < 0) return null;
  const qEnd = at + quote.length;
  const start = Math.max(0, at - radius);
  const end = Math.min(text.length, qEnd + radius);
  return {
    before: text.slice(start, at),
    quote: text.slice(at, qEnd),
    after: text.slice(qEnd, end),
    clipped: start > 0 || end < text.length,
  };
}

// ── small display helpers ──────────────────────────────────────────────

const pct = (x: number) => `${(x * 100).toFixed(1)}`;

function nowStamp(): string {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

function Delta({
  now,
  prev,
  kind,
  up,
  down,
  baseline,
}: {
  now: number | null;
  prev: number | null;
  kind: 'pp' | 'count';
  up: string;
  down: string;
  baseline: boolean;
}) {
  if (baseline) return <span className="text-caption text-ink-soft">baseline run</span>;
  if (now === null || prev === null)
    return <span className="text-caption text-ink-soft">no comparable value</span>;
  const raw = kind === 'pp' ? (now - prev) * 100 : now - prev;
  const rounded = kind === 'pp' ? Number(raw.toFixed(1)) : raw;
  const Icon = rounded > 0 ? ArrowUp : rounded < 0 ? ArrowDown : Minus;
  const color = rounded > 0 ? up : rounded < 0 ? down : undefined;
  const text =
    kind === 'pp'
      ? `${rounded > 0 ? '+' : ''}${rounded.toFixed(1)} pp`
      : `${rounded > 0 ? '+' : ''}${rounded}`;
  return (
    <span
      className="text-caption inline-flex items-center gap-1 font-num"
      style={color ? { color } : undefined}
      title="Change against the previous extractor run"
    >
      <Icon size={11} aria-hidden />
      {text}
      <span className="text-ink-soft">vs prev</span>
    </span>
  );
}

function MetricValue({ value, defined }: { value: number | null; defined: boolean }) {
  if (!defined || value === null)
    return (
      <span className="font-num text-display leading-tight text-ink-soft" title="Undefined — the denominator is zero">
        —
      </span>
    );
  return (
    <span className="font-num text-display leading-tight">
      {pct(value)}
      <span className="text-section-title text-ink-soft ml-1">%</span>
    </span>
  );
}

// ── mismatch rows ──────────────────────────────────────────────────────

interface MismatchRow {
  key: string;
  outcome: 'value_mismatch' | 'unit_error' | 'span_error' | 'miss' | 'spurious';
  field: FieldId;
  paperId: string;
  recordId?: string;
  gold?: { value: number | string; unit: string };
  extracted?: { value: number; unit: string };
  note?: string;
}

function relativeGap(
  gold: { value: number; unit: string },
  extracted: { value: number; unit: string },
): string | null {
  if (!sameFamily(gold.unit, extracted.unit)) return null;
  try {
    const e = convert(extracted.value, extracted.unit, gold.unit);
    if (gold.value === 0) return null;
    const d = ((e - gold.value) / Math.abs(gold.value)) * 100;
    if (!isFinite(d)) return null;
    return `${d > 0 ? '+' : ''}${d.toFixed(1)}% against the gold value`;
  } catch {
    return null;
  }
}

// ── screen ─────────────────────────────────────────────────────────────

type SortKey = 'field' | 'nGold' | 'precision' | 'recall' | 'f1' | 'topFailure';

export default function Validation() {
  const runOutputs = useStore((s) => s.runOutputs);
  const records = useStore((s) => s.records);
  const papers = useStore((s) => s.papers);
  const contradictions = useStore((s) => s.contradictions);
  const logActivity = useStore((s) => s.logActivity);
  const toast = useStore((s) => s.toast);
  const palette = useCategorical();

  const [ready, setReady] = useState(false);
  const [pickedRun, setPickedRun] = useState<ExtractorRun | null>(null);
  const [sort, setSort] = useState<{ key: SortKey; dir: 1 | -1 }>({ key: 'nGold', dir: -1 });
  const [tag, setTag] = useState<string>('all');
  const [open, setOpen] = useState<MismatchRow | null>(null);
  const [noteText, setNoteText] = useState('');
  const [filed, setFiled] = useState<Set<string>>(new Set());

  const upColor = palette[0];
  const downColor = palette[1];

  useEffect(() => {
    let alive = true;
    delayClass('quick').then(() => {
      if (alive) setReady(true);
    });
    return () => {
      alive = false;
    };
  }, []);

  const orderedRuns = useMemo<RunOutput[]>(
    () =>
      [...runOutputs].sort(
        (a, b) => RUN_ORDER.indexOf(a.run) - RUN_ORDER.indexOf(b.run) || a.run.localeCompare(b.run),
      ),
    [runOutputs],
  );

  // Every run is scored, every render, from the live records array — editing
  // the gold set during a review session moves these numbers immediately.
  const allMetrics = useMemo<RunMetrics[]>(
    () => orderedRuns.map((r) => computeRunMetrics(r, records)),
    [orderedRuns, records],
  );

  const recordById = useMemo(
    () => new Map<string, ExtractionRecord>(records.map((r) => [r.id, r])),
    [records],
  );

  const activeIdx = useMemo(() => {
    const i = orderedRuns.findIndex((r) => r.run === pickedRun);
    return i >= 0 ? i : orderedRuns.length - 1;
  }, [orderedRuns, pickedRun]);

  const run = orderedRuns[activeIdx];
  const metrics = allMetrics[activeIdx];
  const prevMetrics = activeIdx > 0 ? allMetrics[activeIdx - 1] : null;

  const mismatches = useMemo<MismatchRow[]>(() => {
    if (!run) return [];
    const out: MismatchRow[] = [];
    for (const res of run.results) {
      if (res.outcome === 'match') continue;
      const rec = recordById.get(res.goldRecordId);
      if (!rec || !rec.gold) continue;
      out.push({
        key: `${run.run}:${res.goldRecordId}`,
        outcome: res.outcome,
        field: rec.field,
        paperId: rec.paperId,
        recordId: rec.id,
        gold: rec.gold,
        extracted: res.extracted,
      });
    }
    for (const fp of run.falsePositives) {
      out.push({
        key: `${run.run}:fp:${fp.id}`,
        outcome: 'spurious',
        field: fp.field,
        paperId: fp.paperId,
        extracted: fp.extracted,
        note: fp.note,
      });
    }
    return out;
  }, [run, recordById]);

  const tagCounts = useMemo(() => {
    const m = new Map<string, number>();
    for (const r of mismatches) m.set(r.outcome, (m.get(r.outcome) ?? 0) + 1);
    return m;
  }, [mismatches]);

  const visibleMismatches = tag === 'all' ? mismatches : mismatches.filter((r) => r.outcome === tag);

  const sortedFields = useMemo<FieldMetrics[]>(() => {
    if (!metrics) return [];
    const rows = [...metrics.perField];
    rows.sort((a, b) => {
      const dir = sort.dir;
      switch (sort.key) {
        case 'field':
          return fieldName(a.field).localeCompare(fieldName(b.field)) * dir;
        case 'topFailure':
          return a.topFailure.localeCompare(b.topFailure) * dir;
        case 'nGold':
          return (a.nGold - b.nGold) * dir;
        default:
          return (a[sort.key] - b[sort.key]) * dir;
      }
    });
    return rows;
  }, [metrics, sort]);

  const toggleSort = useCallback((key: SortKey) => {
    setSort((s) => (s.key === key ? { key, dir: s.dir === 1 ? -1 : 1 } : { key, dir: -1 }));
  }, []);

  const fileCorrection = () => {
    if (!open || !run) return;
    const label = open.recordId ?? `${open.paperId} · ${fieldName(open.field)}`;
    const body = noteText.trim();
    logActivity({
      at: nowStamp(),
      icon: 'flag',
      text: `Correction note filed on ${label} (${RUN_LABEL[run.run]} · ${
        OUTCOME_LABEL[open.outcome]
      })${body ? ` — ${body.slice(0, 90)}` : ''}`,
      href: '#/assay',
      provenance: 'user',
    });
    toast({
      text: `Correction note filed on ${label} — it appears in the activity feed for this session only`,
      kind: 'success',
      href: '#/assay',
      hrefLabel: 'Stay',
    });
    setFiled((s) => new Set(s).add(open.key));
    setNoteText('');
  };

  const exportMetrics = () => {
    const rows: unknown[][] = [];
    for (const m of allMetrics) {
      rows.push([
        m.run,
        RUN_LABEL[m.run as ExtractorRun] ?? m.run,
        'micro (all fields)',
        '',
        m.goldSize,
        m.micro.tp,
        m.micro.fp,
        m.micro.fn,
        m.micro.tp + m.micro.fp > 0 ? m.micro.precision.toFixed(4) : 'undefined',
        m.micro.tp + m.micro.fn > 0 ? m.micro.recall.toFixed(4) : 'undefined',
        m.micro.tp + m.micro.fp > 0 && m.micro.tp + m.micro.fn > 0 ? m.micro.f1.toFixed(4) : 'undefined',
        '',
        m.papersCovered,
      ]);
      for (const f of m.perField) {
        const thin = f.nGold < INSUFFICIENT_N;
        rows.push([
          m.run,
          RUN_LABEL[m.run as ExtractorRun] ?? m.run,
          'field',
          fieldName(f.field),
          f.nGold,
          f.tp,
          f.fp,
          f.fn,
          thin ? 'insufficient gold data' : f.precision.toFixed(4),
          thin ? 'insufficient gold data' : f.recall.toFixed(4),
          thin ? 'insufficient gold data' : f.f1.toFixed(4),
          f.topFailure,
          '',
        ]);
      }
    }
    exportCSV(
      'openferment-validation-metrics.csv',
      [
        'Run',
        'Run label',
        'Scope',
        'Field',
        'n (gold)',
        'TP',
        'FP',
        'FN',
        'Precision',
        'Recall',
        'F1',
        'Most-common failure',
        'Papers covered',
      ],
      rows,
    );
  };

  // ── states ───────────────────────────────────────────────────────────

  const header = (actions?: ReactNode) => (
    <PageHeader
      eyebrow="Module 0 · Evidence"
      title="Extraction validation"
      subtitle="What the extractor would be scored on, and what it has been scored on so far."
      actions={actions}
    />
  );

  if (!ready) {
    return (
      <>
        {header()}
        <Card>
          <Skeleton rows={10} />
        </Card>
      </>
    );
  }

  // No extractor has been run against this corpus, and the screen says so
  // rather than showing a number (OF-COR-001 §22, actions 6–7). Every entry is
  // catalogued: the curator's notes stand in for source text, so there are no
  // source spans to annotate a gold set against and nothing to score.
  if (!run || !metrics) {
    const plannedRecords = GOLD_SET_PLAN.reduce((n, p) => n + p.records, 0);

    // Known-bad, derived rather than maintained. Three signals the corpus can
    // answer on its own: a field the referee has contradicted, a field where
    // most records are recitations rather than measurements, and a field the
    // ontology cannot express what the literature actually reports.
    const withRecords = new Set(records.map((r) => r.paperId));
    const silentPapers = papers.filter((p) => !withRecords.has(p.id)).length;
    const negativeResults = records.filter((r) => r.negativeResult).length;

    const byField = new Map<string, typeof records>();
    for (const r of records) {
      const list = byField.get(r.field) ?? [];
      list.push(r);
      byField.set(r.field, list);
    }

    const knownBad: { field: string; why: string }[] = [];
    for (const c of contradictions) {
      for (const rid of c.recordIds) {
        const rec = records.find((r) => r.id === rid);
        if (!rec || knownBad.some((k) => k.field === rec.field)) continue;
        knownBad.push({
          field: rec.field,
          why: 'the referee found a set of records here that cannot all be true',
        });
      }
    }
    for (const [field, list] of byField) {
      if (knownBad.some((k) => k.field === field)) continue;
      const secondary = list.filter((r) => r.isPrimary === false).length;
      if (secondary > 0 && secondary >= list.length / 2) {
        knownBad.push({
          field,
          why: `${secondary} of ${list.length} records here recite another study rather than measure — a median would count the same measurement twice`,
        });
      }
    }

    return (
      <>
        {header(<LinkButton to="/library">Open the Library</LinkButton>)}

        <div className="max-w-3xl space-y-4">
          <Callout kind="info" title="No extractor has been run against this corpus yet">
            <p className="mb-2">
              Every one of the{' '}
              <span className="font-num">{papers.length}</span> entries is{' '}
              <strong>catalogued</strong>, not ingested: the curator&rsquo;s notes stand in for the
              source text. There are no parsed source spans to annotate a gold set against, and no
              extractor output to compare with one.
            </p>
            <p>
              Showing a precision or recall figure here would mean scoring a run that never happened
              against annotations that were never made. So this screen shows the plan and the gap
              instead.
            </p>
          </Callout>

          {/* Known-bad first (§8.3.2). Leading with the weakness is what makes
              the rest of the screen credible, so this sits above the plan. */}
          <Card className="p-4 border-signal-warn/50">
            <h2 className="font-serif text-section-title font-semibold mb-1">
              Known bad, before anything else
            </h2>
            <p className="text-body text-ink-soft mb-3">
              Fields where this corpus is already known to be unreliable. Derived from the records
              rather than a list someone maintains, so it cannot quietly go out of date.
            </p>
            <ul className="space-y-2">
              {knownBad.map((k) => (
                <li key={k.field} className="text-body">
                  <a href={href(`/ledger/p/${k.field}`)} className="text-accent hover:underline">
                    {fieldName(k.field as FieldId)}
                  </a>
                  <span className="text-signal-warn"> — {k.why}</span>
                </li>
              ))}
              {knownBad.length === 0 && (
                <li className="text-body text-ink-soft">
                  No field currently trips a known-bad signal.
                </li>
              )}
            </ul>
          </Card>

          {/* Negative controls (§8.3.1) — the cheapest high-value measurement
              available, and the first thing a skeptic reaches for. */}
          <Card className="p-4">
            <h2 className="font-serif text-section-title font-semibold mb-1">
              Negative controls — designed, not yet run
            </h2>
            <p className="text-body text-ink-soft mb-3">
              The question a precision figure cannot answer: when a source contains no value for a
              field, does the extractor invent one? Two populations in this corpus can answer it,
              and neither needs new annotation work.
            </p>
            <div className="space-y-2 text-body">
              <div>
                <span className="font-num text-ink">{silentPapers}</span> catalogued sources carry
                no record at all. An extractor run that returns a value for any of them has
                fabricated it, and no gold set is needed to say so.
              </div>
              <div>
                <span className="font-num text-ink">{negativeResults}</span> records are explicit
                negative results — &ldquo;no detectable product&rdquo;, a catalytically dead mutant,
                an assay that found nothing. Turning one of these into a positive number is the
                failure mode that would most flatter a precision score, because the span is there
                and only its polarity is wrong.
              </div>
            </div>
          </Card>

          {/* Intra-rater (§8.3.3) — measures gold-set noise, which leave-one-out
              cannot see at all. */}
          <Card className="p-4">
            <h2 className="font-serif text-section-title font-semibold mb-1">
              Intra-rater agreement — designed, not yet run
            </h2>
            <p className="text-body text-ink-soft">
              A single curator built this corpus, so inter-rater agreement is unavailable. The
              honest substitute is re-annotating a subset blind, weeks apart, and reporting
              disagreement with oneself. It measures the noise floor of the gold set — the ceiling
              any extractor score is really being read against — and leave-one-out cannot see it,
              because it holds the annotations themselves fixed.
            </p>
            <p className="text-body text-ink-soft mt-2">
              Nothing is reported here because no second pass has been done. A number would have to
              be invented to fill the space.
            </p>
          </Card>

          <Card className="p-4">
            <div className="flex items-baseline justify-between gap-3 mb-1">
              <h2 className="font-serif text-section-title font-semibold">Gold set — planned</h2>
              <span className="font-num text-caption text-ink-soft">
                0 of {plannedRecords} annotated
              </span>
            </div>
            <p className="text-body text-ink-soft mb-3">
              {GOLD_SET_PLAN.length} papers, weighted toward fields with enough independent
              measurements to make precision and recall mean something.{' '}
              {GOLD_SET_PLAN.some((p) => p.blocked) && (
                <span className="text-signal-warn">
                  One row is blocked: the ontology has no field for what it asks for.
                </span>
              )}
            </p>
            <div className="overflow-x-auto">
              <table className="w-full text-body">
                <thead>
                  <tr className="border-b border-line text-caption text-ink-soft">
                    <th className="text-left py-1.5">Paper</th>
                    <th className="text-left">Field focus</th>
                    <th className="text-right px-2">Records</th>
                    <th className="text-left">Why chosen</th>
                  </tr>
                </thead>
                <tbody>
                  {GOLD_SET_PLAN.map((p) => (
                    <tr key={p.paperId} className="border-b border-line/60 align-top">
                      <td className="py-1.5">
                        <CitationChip paperId={p.paperId} />
                      </td>
                      <td className="text-caption text-ink-soft pr-3">{p.fields}</td>
                      <td className="text-right font-num px-2">{p.records}</td>
                      <td className={cx('text-caption', p.blocked ? 'text-signal-warn' : 'text-ink-soft')}>
                        {p.rationale}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          <Card className="p-4">
            <h2 className="font-serif text-section-title font-semibold mb-2">
              Difficulty cases the gold set must include
            </h2>
            <p className="text-body text-ink-soft mb-2">
              A benchmark that only contains easy cases measures nothing. These are the six the
              corpus document calls for.
            </p>
            <ul className="space-y-1.5">
              {GOLD_SET_DIFFICULTY_CASES.map((c, i) => (
                <li key={i} className="tick tick-gold text-body">
                  {c}
                </li>
              ))}
            </ul>
          </Card>

          <Card className="p-4">
            <h2 className="font-serif text-section-title font-semibold mb-1">
              Values the ontology cannot hold
            </h2>
            <p className="text-body text-ink-soft mb-3">
              These are real numbers in the corpus with no field to put them in. They were left
              unrecorded rather than forced into an ill-fitting field, because an ontology that
              quietly absorbs values it was not designed for produces confident nonsense.
            </p>
            <div className="space-y-2">
              {ONTOLOGY_GAPS.map((g) => (
                <div key={g.entry} className="tick tick-industry-estimate">
                  <div className="flex items-baseline gap-2">
                    <span className="font-num text-caption text-ink-soft">{g.entry}</span>
                    <span className="text-body">{g.values}</span>
                  </div>
                  <div className="text-caption text-ink-soft mt-0.5">Would need: {g.wouldNeed}</div>
                </div>
              ))}
            </div>
          </Card>

          <Card className="p-4">
            <h2 className="font-serif text-section-title font-semibold mb-2">What unblocks this</h2>
            <ol className="list-decimal pl-5 space-y-1 text-body">
              <li>Ingest tranche 1 — the open-access core papers — so spans anchor to real text.</li>
              <li>Hand-annotate the gold set against those spans.</li>
              <li>Run an extractor and score it here.</li>
            </ol>
            <div className="mt-3">
              <LinkButton to="/library/ingest" variant="primary">
                Open the ingest pipeline
              </LinkButton>
            </div>
          </Card>
        </div>
      </>
    );
  }

  const precisionDefined = metrics.micro.tp + metrics.micro.fp > 0;
  const recallDefined = metrics.micro.tp + metrics.micro.fn > 0;
  const f1Defined = precisionDefined && recallDefined;
  const prevPrecisionDefined = prevMetrics ? prevMetrics.micro.tp + prevMetrics.micro.fp > 0 : false;
  const prevRecallDefined = prevMetrics ? prevMetrics.micro.tp + prevMetrics.micro.fn > 0 : false;

  const partial = run.results.length < metrics.goldSize;
  const isBaseline = activeIdx === 0;

  const headerActions = (
    <>
      <Button onClick={exportMetrics} title="Headline and per-field metrics for every run">
        <Download size={14} /> Export metrics CSV
      </Button>
      <LinkButton to="/extract/review">
        <ScrollText size={14} /> Review queue
      </LinkButton>
    </>
  );

  return (
    <>
      {header(headerActions)}

      {/* ── run selector + evaluation scheme ─────────────────────────── */}
      <div className="flex flex-wrap items-center gap-x-5 gap-y-3 mb-4">
        <div className="flex items-center gap-2">
          <span className="text-caption uppercase tracking-wide text-ink-soft">Run</span>
          <div className="flex rounded-input border border-line overflow-hidden" role="group" aria-label="Extractor run">
            {orderedRuns.map((r, i) => (
              <button
                key={r.run}
                onClick={() => setPickedRun(r.run)}
                aria-pressed={i === activeIdx}
                title={RUN_BLURB[r.run] ?? r.run}
                className={cx(
                  'px-2.5 py-1 text-body font-num',
                  i === activeIdx
                    ? 'bg-accent-wash text-ink font-medium'
                    : 'text-ink-soft hover:text-ink',
                )}
              >
                {RUN_LABEL[r.run] ?? r.run}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          <span className="text-caption uppercase tracking-wide text-ink-soft">Scheme</span>
          <span className="chip">Leave-one-out</span>
          <Explain label="What leave-one-out means here">
            <p className="mb-2">
              Leave-one-out means each gold annotation is scored as if it had been held out of
              everything used to tune the extractor, so a field is never judged on the very example
              that shaped its rule. It is a guard against flattering yourself with numbers measured
              on your own tuning data.
            </p>
            <p className="text-signal-warn">
              This Sim trains and runs no models. The scheme is described here, not executed.
            </p>
          </Explain>
        </div>

        <div className="text-caption text-ink-soft">{RUN_BLURB[run.run]}</div>
      </div>

      {partial && (
        <div className="mb-4">
          <Callout kind="warn" title="Partial results — read the headline with that in mind">
            <span className="inline-flex items-start gap-1.5">
              <FileWarning size={13} className="mt-[3px] shrink-0" aria-hidden />
              <span>
                {RUN_LABEL[run.run]} reports <span className="font-num">{run.results.length}</span> of
                the <span className="font-num">{metrics.goldSize}</span> records now in the gold set.
                The missing{' '}
                <span className="font-num">{metrics.goldSize - run.results.length}</span> are not
                counted as misses — they were never scored, so precision and recall below describe
                only the scored subset.
              </span>
            </span>
          </Callout>
        </div>
      )}

      {metrics.goldSize === 0 && (
        <div className="mb-4">
          <Callout kind="warn" title="No gold annotations in this session">
            Precision and recall are undefined without a gold set. Flag records for gold in the
            review queue and this screen fills in.
          </Callout>
        </div>
      )}

      {/* ── band 1: headline ─────────────────────────────────────────── */}
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5 mb-2">
        <Tick
          p="demo"
          className="card py-3 pr-3"
          title="Micro-averaged over this run's matched records against the gold-set annotations"
        >
          <div className="text-caption uppercase tracking-wide text-ink-soft">Precision</div>
          <MetricValue value={metrics.micro.precision} defined={precisionDefined} />
          <div className="mt-0.5">
            <Delta
              now={precisionDefined ? metrics.micro.precision : null}
              prev={prevMetrics && prevPrecisionDefined ? prevMetrics.micro.precision : null}
              kind="pp"
              up={upColor}
              down={downColor}
              baseline={isBaseline}
            />
          </div>
        </Tick>

        <Tick
          p="demo"
          className="card py-3 pr-3"
          title="Micro-averaged over this run's matched records against the gold-set annotations"
        >
          <div className="text-caption uppercase tracking-wide text-ink-soft">Recall</div>
          <MetricValue value={metrics.micro.recall} defined={recallDefined} />
          <div className="mt-0.5">
            <Delta
              now={recallDefined ? metrics.micro.recall : null}
              prev={prevMetrics && prevRecallDefined ? prevMetrics.micro.recall : null}
              kind="pp"
              up={upColor}
              down={downColor}
              baseline={isBaseline}
            />
          </div>
        </Tick>

        <Tick
          p="demo"
          className="card py-3 pr-3"
          title="Micro-averaged over this run's matched records against the gold-set annotations"
        >
          <div className="text-caption uppercase tracking-wide text-ink-soft">F1 (micro)</div>
          <MetricValue value={metrics.micro.f1} defined={f1Defined} />
          <div className="mt-0.5">
            <Delta
              now={f1Defined ? metrics.micro.f1 : null}
              prev={
                prevMetrics && prevPrecisionDefined && prevRecallDefined ? prevMetrics.micro.f1 : null
              }
              kind="pp"
              up={upColor}
              down={downColor}
              baseline={isBaseline}
            />
          </div>
        </Tick>

        <Tick p="gold" className="card py-3 pr-3" title="Curated gold-set annotations">
          <div className="text-caption uppercase tracking-wide text-ink-soft">Gold-set size</div>
          <div className="font-num text-display leading-tight">{metrics.goldSize}</div>
          <div className="mt-0.5">
            <Delta
              now={metrics.goldSize}
              prev={prevMetrics ? prevMetrics.goldSize : null}
              kind="count"
              up={upColor}
              down={downColor}
              baseline={isBaseline}
            />
          </div>
        </Tick>

        <Tick p="gold" className="card py-3 pr-3" title="Distinct papers contributing gold records">
          <div className="text-caption uppercase tracking-wide text-ink-soft">Papers covered</div>
          <div className="font-num text-display leading-tight">{metrics.papersCovered}</div>
          <div className="mt-0.5">
            <Delta
              now={metrics.papersCovered}
              prev={prevMetrics ? prevMetrics.papersCovered : null}
              kind="count"
              up={upColor}
              down={downColor}
              baseline={isBaseline}
            />
          </div>
        </Tick>
      </div>

      <p className="text-caption text-ink-soft mb-6 max-w-4xl">
        <span className="font-num">tp {metrics.micro.tp}</span> ·{' '}
        <span className="font-num">fp {metrics.micro.fp}</span> ·{' '}
        <span className="font-num">fn {metrics.micro.fn}</span>. A value or unit mismatch is counted
        twice — once as a false positive for the wrong record produced, once as a false negative for
        the gold record missed — which is why F1 falls faster than a raw error count suggests. The
        same gold set is used for every run, so its size and paper coverage only move when you
        promote a record in the review queue.
      </p>

      {/* ── band 2: per-field ────────────────────────────────────────── */}
      <SectionTitle
        right={
          <span className="text-caption text-ink-soft">
            Fields with fewer than <span className="font-num">{INSUFFICIENT_N}</span> gold records
            report no metrics
          </span>
        }
      >
        Per-field performance
      </SectionTitle>

      <Card className="overflow-x-auto mb-6">
        {sortedFields.length === 0 ? (
          <EmptyState
            title="No fields scored"
            body="This run produced no results that map onto a gold record in the current session."
          />
        ) : (
          <table className="w-full border-collapse" style={{ fontSize: 'var(--table-fs)' }}>
            <caption className="sr-only">
              Precision, recall and F1 by ontology field for run {RUN_LABEL[run.run]}
            </caption>
            <thead>
              <tr className="border-b border-line">
                {(
                  [
                    ['field', 'Field', false],
                    ['nGold', 'n (gold)', true],
                    ['precision', 'P', true],
                    ['recall', 'R', true],
                    ['f1', 'F1', true],
                    ['topFailure', 'Most-common failure', false],
                  ] as [SortKey, string, boolean][]
                ).map(([key, label, numeric]) => (
                  <th
                    key={key}
                    scope="col"
                    className={cx(
                      'text-caption font-medium text-ink-soft px-3 py-2 whitespace-nowrap',
                      numeric ? 'text-right' : 'text-left',
                    )}
                    aria-sort={
                      sort.key === key ? (sort.dir === 1 ? 'ascending' : 'descending') : 'none'
                    }
                  >
                    <button
                      className="inline-flex items-center gap-1 hover:text-ink"
                      onClick={() => toggleSort(key)}
                      title={`Sort by ${label}`}
                    >
                      {label}
                      {sort.key === key ? (
                        sort.dir === 1 ? (
                          <ArrowUp size={11} />
                        ) : (
                          <ArrowDown size={11} />
                        )
                      ) : (
                        <ArrowUpDown size={11} className="opacity-40" />
                      )}
                    </button>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sortedFields.map((f) => {
                const thin = f.nGold < INSUFFICIENT_N;
                return (
                  <tr key={f.field} className={cx('border-b border-line/70', thin && 'text-ink-soft')}>
                    <td className="px-3 py-1.5">{fieldName(f.field)}</td>
                    <td className="px-3 py-1.5 text-right font-num">{f.nGold}</td>
                    {thin ? (
                      <td className="px-3 py-1.5 text-ink-soft italic" colSpan={3}>
                        insufficient gold data — n &lt; {INSUFFICIENT_N}, no precision or recall
                        reported
                      </td>
                    ) : (
                      <>
                        <td className="px-3 py-1.5 text-right font-num">{pct(f.precision)}%</td>
                        <td className="px-3 py-1.5 text-right font-num">{pct(f.recall)}%</td>
                        <td className="px-3 py-1.5">
                          <span className="flex items-center gap-2 justify-end">
                            <span className="w-16 shrink-0">
                              <Bar value={f.f1} />
                            </span>
                            <span className="font-num w-12 text-right">{pct(f.f1)}%</span>
                          </span>
                        </td>
                      </>
                    )}
                    <td className="px-3 py-1.5">
                      {thin ? (
                        <span className="text-ink-soft">
                          {f.tp + f.fp + f.fn === 0 ? 'not scored' : f.topFailure}
                        </span>
                      ) : (
                        <span title={`tp ${f.tp} · fp ${f.fp} · fn ${f.fn}`}>{f.topFailure}</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </Card>

      {/* ── band 3: mismatch browser ─────────────────────────────────── */}
      <SectionTitle
        right={
          <span className="text-caption text-ink-soft font-num">
            {visibleMismatches.length} of {mismatches.length}
          </span>
        }
      >
        Mismatch browser
      </SectionTitle>

      <div className="flex flex-wrap items-center gap-1.5 mb-2">
        <button
          className={cx('chip', tag === 'all' && 'chip-active')}
          onClick={() => setTag('all')}
          aria-pressed={tag === 'all'}
        >
          All <span className="font-num">{mismatches.length}</span>
        </button>
        {Object.keys(OUTCOME_LABEL)
          .filter((k) => (tagCounts.get(k) ?? 0) > 0)
          .map((k) => (
            <button
              key={k}
              className={cx('chip', tag === k && 'chip-active')}
              onClick={() => setTag(k)}
              aria-pressed={tag === k}
              title={OUTCOME_EXPLAIN[k]}
            >
              {OUTCOME_LABEL[k]} <span className="font-num">{tagCounts.get(k)}</span>
            </button>
          ))}
      </div>

      <Card className="overflow-x-auto">
        {mismatches.length === 0 ? (
          <EmptyState
            title="No mismatches in this run"
            body="Every scored gold record matched and the run produced no spurious extractions. With a gold set this small that is a statement about the gold set, not about the extractor."
          />
        ) : visibleMismatches.length === 0 ? (
          <EmptyState
            title="Nothing matches that failure tag"
            body={`No ${(OUTCOME_LABEL[tag] ?? tag).toLowerCase()} rows in ${RUN_LABEL[run.run]}.`}
            action={<Button onClick={() => setTag('all')}>Show every mismatch</Button>}
          />
        ) : (
          <table className="w-full border-collapse" style={{ fontSize: 'var(--table-fs)' }}>
            <caption className="sr-only">
              Every false positive, false negative and value mismatch in run {RUN_LABEL[run.run]}
            </caption>
            <thead>
              <tr className="border-b border-line">
                <th scope="col" className="text-left text-caption font-medium text-ink-soft px-3 py-2">
                  Field
                </th>
                <th scope="col" className="text-left text-caption font-medium text-ink-soft px-3 py-2">
                  Gold
                </th>
                <th scope="col" className="text-left text-caption font-medium text-ink-soft px-3 py-2">
                  Extracted
                </th>
                <th scope="col" className="text-left text-caption font-medium text-ink-soft px-3 py-2">
                  Source
                </th>
                <th scope="col" className="text-left text-caption font-medium text-ink-soft px-3 py-2">
                  Failure
                </th>
                <th scope="col" className="px-3 py-2">
                  <span className="sr-only">Open comparison</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {visibleMismatches.map((m) => (
                <tr
                  key={m.key}
                  className="border-b border-line/70 hover:bg-ink-soft/[0.04] cursor-pointer"
                  onClick={() => {
                    setOpen(m);
                    setNoteText('');
                  }}
                >
                  <td className="px-3 py-1.5">
                    <span className="block truncate max-w-[220px]" title={fieldName(m.field)}>
                      {fieldName(m.field)}
                    </span>
                  </td>
                  <td className="px-3 py-1.5 font-num">
                    {m.gold ? (
                      <span className="text-accent">
                        {fmt(m.gold.value)} {m.gold.unit}
                      </span>
                    ) : (
                      <span className="text-ink-soft">no gold record</span>
                    )}
                  </td>
                  <td className="px-3 py-1.5 font-num">
                    {m.extracted ? (
                      <span className={extractedTone(m.outcome)}>
                        {fmt(m.extracted.value)} {m.extracted.unit}
                      </span>
                    ) : (
                      <span className="text-signal-error">nothing extracted</span>
                    )}
                  </td>
                  <td className="px-3 py-1.5">
                    <span onClick={(e) => e.stopPropagation()}>
                      <CitationChip paperId={m.paperId} recordId={m.recordId} />
                    </span>
                  </td>
                  <td className="px-3 py-1.5">
                    <span
                      className={cx(
                        'chip',
                        m.outcome === 'value_mismatch' || m.outcome === 'unit_error'
                          ? 'text-signal-warn border-signal-warn/40'
                          : 'text-signal-error border-signal-error/40',
                      )}
                      title={OUTCOME_EXPLAIN[m.outcome]}
                    >
                      {OUTCOME_LABEL[m.outcome]}
                    </span>
                  </td>
                  <td className="px-3 py-1.5 text-right">
                    <button
                      className="btn btn-sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        setOpen(m);
                        setNoteText('');
                      }}
                    >
                      Compare
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <p className="text-caption text-ink-soft mt-3 max-w-4xl">
        Every row above is a disagreement between the curated gold annotation and what the run
        produced. Open one to read both sides against the text held for that paper — for a
        catalogued entry that text is the curator&rsquo;s note, not the paper&rsquo;s own words. The
        literature is real and citable, but a curated annotation has not yet been checked against
        the source PDF, so a row here is a lead to check, not a verdict.
      </p>

      {/* ── comparison sheet ─────────────────────────────────────────── */}
      <Sheet
        open={open !== null}
        onClose={() => setOpen(null)}
        width={720}
        title={
          open ? (
            <span className="flex items-baseline gap-2">
              <span>{fieldName(open.field)}</span>
              <span className="font-num text-caption text-ink-soft">
                {open.recordId ?? open.paperId}
              </span>
            </span>
          ) : (
            'Comparison'
          )
        }
      >
        {open && (
          <ComparisonBody
            row={open}
            runLabel={RUN_LABEL[run.run] ?? run.run}
            record={open.recordId ? recordById.get(open.recordId) : undefined}
            paperSectionText={(() => {
              if (!open.recordId) return null;
              const rec = recordById.get(open.recordId);
              if (!rec) return null;
              const paper = papers.find((p) => p.id === rec.paperId);
              const section = paper?.sections.find((s) => s.id === rec.sectionId);
              return section ? { heading: section.heading, text: section.text } : null;
            })()}
            filed={filed.has(open.key)}
            noteText={noteText}
            onNoteText={setNoteText}
            onFile={fileCorrection}
          />
        )}
      </Sheet>
    </>
  );
}

// ── sheet body ─────────────────────────────────────────────────────────

function SpanBlock({
  text,
  quote,
  markClass,
  emptyNote,
}: {
  text: string | null;
  quote: string;
  markClass: string;
  emptyNote: string;
}) {
  const ctx = text ? spanContext(text, quote) : null;
  if (!ctx) {
    return (
      <div className="text-caption text-ink-soft rounded-input border border-line bg-surface-0 p-2">
        {emptyNote}
      </div>
    );
  }
  return (
    <div className="rounded-input border border-line bg-surface-0 p-2 font-serif text-body leading-relaxed max-h-56 overflow-y-auto">
      {ctx.clipped && <span className="text-ink-soft">… </span>}
      {ctx.before}
      <mark className={markClass}>{ctx.quote}</mark>
      {ctx.after}
      {ctx.clipped && <span className="text-ink-soft"> …</span>}
    </div>
  );
}

function ComparisonBody({
  row,
  runLabel,
  record,
  paperSectionText,
  filed,
  noteText,
  onNoteText,
  onFile,
}: {
  row: MismatchRow;
  runLabel: string;
  record?: ExtractionRecord;
  paperSectionText: { heading: string; text: string } | null;
  filed: boolean;
  noteText: string;
  onNoteText: (v: string) => void;
  onFile: () => void;
}) {
  const goldSI = row.gold && typeof row.gold.value === 'number' ? toSI(row.gold.value, row.gold.unit) : null;
  const extractedSI = row.extracted ? toSI(row.extracted.value, row.extracted.unit) : null;
  const gap =
    row.gold && row.extracted && typeof row.gold.value === 'number'
      ? relativeGap({ value: row.gold.value, unit: row.gold.unit }, row.extracted)
      : null;
  const showExtractedSpan = row.outcome === 'value_mismatch' || row.outcome === 'unit_error';

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={cx(
            'chip',
            row.outcome === 'value_mismatch' || row.outcome === 'unit_error'
              ? 'text-signal-warn border-signal-warn/40'
              : 'text-signal-error border-signal-error/40',
          )}
        >
          {OUTCOME_LABEL[row.outcome]}
        </span>
        <span className="chip font-num">{runLabel}</span>
        <CitationChip paperId={row.paperId} recordId={row.recordId} />
        {record && (
          <a
            href={href(`/library/papers/${record.paperId}?span=${record.id}`)}
            className="text-caption text-accent hover:underline"
          >
            Open in the reader
          </a>
        )}
      </div>

      <p className="text-body text-ink-soft">{OUTCOME_EXPLAIN[row.outcome]}</p>

      <div className="grid sm:grid-cols-2 gap-3">
        {/* gold side */}
        <div className="card p-3">
          <div className="flex items-center justify-between gap-2 mb-1.5">
            <div className="text-caption uppercase tracking-wide text-ink-soft">Gold annotation</div>
            <ProvenanceBadge p="gold" compact />
          </div>
          {row.gold ? (
            <>
              <div className="font-num text-section-title text-accent leading-tight">
                {fmt(row.gold.value)} <span className="text-ink-soft">{row.gold.unit}</span>
              </div>
              {goldSI && goldSI.unit !== row.gold.unit && (
                <div className="font-num text-caption text-ink-soft">
                  = {fmt(goldSI.value)} {goldSI.unit}
                </div>
              )}
            </>
          ) : (
            <div className="text-body text-ink-soft">
              No gold annotation — the curated set contains no record for this claim.
            </div>
          )}

          <div className="text-caption uppercase tracking-wide text-ink-soft mt-3 mb-1">
            Curated span{paperSectionText ? ` · ${paperSectionText.heading}` : ''}
          </div>
          <SpanBlock
            text={paperSectionText?.text ?? null}
            quote={record?.quote ?? ''}
            markClass="span-gold"
            emptyNote={
              record
                ? 'The curated quote is not present in the parsed section text for this paper, so it cannot be shown in context.'
                : 'No curated record exists for this row, so there is no span to show.'
            }
          />
        </div>

        {/* extraction side */}
        <div className="card p-3">
          <div className="flex items-center justify-between gap-2 mb-1.5">
            <div className="text-caption uppercase tracking-wide text-ink-soft">
              {runLabel} extraction
            </div>
            <ProvenanceBadge p="demo" compact />
          </div>
          {row.extracted ? (
            <>
              <div
                className={cx('font-num text-section-title leading-tight', extractedTone(row.outcome))}
              >
                {fmt(row.extracted.value)}{' '}
                <span className="text-ink-soft">{row.extracted.unit}</span>
              </div>
              {extractedSI && extractedSI.unit !== row.extracted.unit && (
                <div className="font-num text-caption text-ink-soft">
                  = {fmt(extractedSI.value)} {extractedSI.unit}
                </div>
              )}
              {gap && <div className="text-caption text-ink-soft mt-0.5">{gap}</div>}
            </>
          ) : (
            <div className="text-body text-signal-error">
              Nothing extracted for this gold annotation.
            </div>
          )}

          <div className="text-caption uppercase tracking-wide text-ink-soft mt-3 mb-1">
            Span the run used
          </div>
          {showExtractedSpan ? (
            <SpanBlock
              text={paperSectionText?.text ?? null}
              quote={record?.quote ?? ''}
              markClass="span-unverified"
              emptyNote="The span cannot be located in the parsed section text."
            />
          ) : (
            <div className="text-caption text-ink-soft rounded-input border border-line bg-surface-0 p-2">
              {row.outcome === 'span_error'
                ? 'The run attributed the value to a different sentence. The run output stores the outcome but not the rejected span, so it cannot be shown.'
                : row.outcome === 'miss'
                  ? 'The run produced no record here, so there is no span.'
                  : 'Spurious extractions are recorded at paper level, not span level; no span is retained.'}
            </div>
          )}

          {row.note && (
            <p className="text-caption text-ink-soft mt-2">
              <span className="font-medium">Curator note:</span> {row.note}
            </p>
          )}
        </div>
      </div>

      <div className="pt-3 border-t border-line">
        <label
          htmlFor="correction-note"
          className="block text-caption uppercase tracking-wide text-ink-soft mb-1"
        >
          Correction note (optional)
        </label>
        <textarea
          id="correction-note"
          className="input font-sans"
          rows={2}
          value={noteText}
          onChange={(e) => onNoteText(e.target.value)}
          placeholder="What should the extractor have done here?"
        />
        <div className="flex flex-wrap items-center gap-2 mt-2">
          <Button variant="primary" onClick={onFile} disabled={filed}>
            <Send size={14} /> {filed ? 'Correction note filed' : 'File a correction note'}
          </Button>
          <span className="text-caption text-ink-soft">
            Filed notes land in this session&rsquo;s activity feed. Nothing is sent anywhere and
            nothing survives a refresh.
          </span>
        </div>
      </div>
    </div>
  );
}
