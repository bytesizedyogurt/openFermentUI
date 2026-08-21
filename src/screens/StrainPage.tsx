// Strain page (OF-DES-001 §8.9) — the platform's thesis in one screen: every
// number the corpus holds about one organism, normalized to canonical units,
// summarized honestly, and traceable back to the span it came from.
//
// Statistics are derived from the live store, so a record verified in the
// review queue changes the median and turns its dot green without a reload.
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertTriangle,
  ArrowRight,
  BookOpen,
  ClipboardCheck,
  ClipboardList,
  Download,
  FlaskConical,
  Layers,
  LineChart,
  Microscope,
  NotebookPen,
  Play,
  ScatterChart,
  Table2,
  X,
} from 'lucide-react';
import type { ExtractionRecord, FieldId, ParameterDef, Protocol, Scenario } from '@/data/types';
import { ONTOLOGY } from '@/data/source';
import { ONTOLOGY_BY_ID, fieldName } from '@/data/ontology';
import { useStore, provenanceOf, aggregateExclusion, isAggregatable, EXCLUSION_NOTE } from '@/store';
import { href, navigate } from '@/router';
import { convert, fmt, asNumber } from '@/engine/units';
import { CitationChip } from '@/components/Chip';
import { DataTable, type Column, type FacetDef } from '@/components/DataTable';
import { ProvDot, ProvenanceLegend, Tick, type ProvKind } from '@/components/Provenance';
import { ContradictionRail } from '@/components/ContradictionRail';
import {
  Button,
  Callout,
  Card,
  EmptyState,
  Explain,
  LinkButton,
  PageHeader,
  SectionTitle,
  Skeleton,
  cx,
} from '@/components/ui';
import { exportCSV } from '@/lib/csv';
import { delayClass } from '@/sim/latency';

import { partEyebrow } from '@/data/parts';

/** Movement · part · pool, from the one table that names the parts. */
const EYEBROW = partEyebrow('geneos', 'corpus');
// ── model ──────────────────────────────────────────────────────────────

interface SPoint {
  rec: ExtractionRecord;
  prov: ProvKind;
  /** True when the strain link came from the paper's organism list, not the record. */
  viaPaper: boolean;
  /** Value converted into the field's canonical unit, or null if incommensurable. */
  canonical: number | null;
}

interface ScenarioLink {
  sc: Scenario;
  via: 'record' | 'named';
  recordId?: string;
}

const STATUS_FACET_LABEL: Record<string, string> = {
  gold: 'In gold set',
  verified: 'Verified',
  unverified: 'Unverified',
  rejected: 'Rejected',
};

interface FieldGroup {
  def: ParameterDef;
  all: SPoint[];
  live: SPoint[]; // not rejected
  rejected: SPoint[];
  usable: SPoint[]; // live and convertible
  rejectedUsable: SPoint[];
  /** Usable but held out of the statistics — industry estimates and recitations. */
  held: SPoint[];
  heldIndustry: number;
  heldSecondary: number;
  unconvertible: number;
  stats: { n: number; median: number; min: number; max: number } | null;
  verified: number;
  gold: number;
  unverified: number;
  viaPaper: number;
}

/** Plain-language reason a set of records sits outside the median and range. */
function heldReason(industry: number, secondary: number): string {
  const parts: string[] = [];
  if (industry > 0) parts.push(`${industry} industry estimate${industry === 1 ? '' : 's'}`);
  if (secondary > 0) parts.push(`${secondary} quoting another record's measurement`);
  return parts.join(' and ');
}

function provOf(r: ExtractionRecord): ProvKind {
  return r.status === 'rejected' ? 'rejected' : provenanceOf(r);
}

/** Convert into the ontology's canonical unit; null when the families disagree. */
function toCanonical(rec: ExtractionRecord, canonicalUnit: string): number | null {
  try {
    const n = asNumber(rec.value);
    if (n === null) return null; // categorical record — not plottable
    const v = convert(n, rec.unit, canonicalUnit);
    return Number.isFinite(v) ? v : null;
  } catch {
    return null;
  }
}

function summarize(values: number[]) {
  if (values.length === 0) return null;
  const s = [...values].sort((a, b) => a - b);
  const mid = s.length >> 1;
  const median = s.length % 2 === 1 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
  return { n: s.length, median, min: s[0], max: s[s.length - 1] };
}

/** Aggregate provenance of a set of records — the strongest tier present. */
function aggregateProv(points: SPoint[]): ProvKind {
  if (points.some((p) => p.prov === 'gold')) return 'gold';
  if (points.some((p) => p.prov === 'verified')) return 'verified';
  return 'unverified';
}

function stamp(ms?: number): string {
  const d = ms === undefined ? new Date() : new Date(ms);
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

function unitLabel(u: string): string {
  return u === '' ? 'dimensionless' : u;
}

// ── strip plot ─────────────────────────────────────────────────────────

const LANE_H = 11;
const MAX_LANES = 5;
const AXIS_H = 14;
const MIN_GAP = 0.019; // fraction of the axis width before two dots collide
const DENSITY_CAP = 200;
const DENSITY_BINS = 60;

/** Greedy lane assignment: first lane whose last point clears the minimum gap. */
function assignLanes(xs: number[]): number[] {
  const lastInLane: number[] = [];
  const out: number[] = [];
  xs.forEach((x, i) => {
    let lane = -1;
    for (let l = 0; l < lastInLane.length; l++) {
      if (x - lastInLane[l] >= MIN_GAP) {
        lane = l;
        break;
      }
    }
    if (lane === -1) {
      if (lastInLane.length < MAX_LANES) {
        lastInLane.push(x);
        lane = lastInLane.length - 1;
      } else {
        lane = i % MAX_LANES;
      }
    }
    lastInLane[lane] = x;
    out.push(lane);
  });
  return out;
}

interface PlotPoint extends SPoint {
  canonical: number;
}

function StripPlot({
  points,
  def,
  medianValue,
}: {
  points: PlotPoint[];
  def: ParameterDef;
  medianValue: number | null;
}) {
  const [focus, setFocus] = useState(0);
  const [hover, setHover] = useState<number | null>(null);
  const papers = useStore((s) => s.papers);
  const btnRefs = useRef<(HTMLButtonElement | null)[]>([]);

  const sorted = useMemo(() => [...points].sort((a, b) => a.canonical - b.canonical), [points]);
  const lo = sorted.length ? sorted[0].canonical : 0;
  const hi = sorted.length ? sorted[sorted.length - 1].canonical : 0;
  const span = hi - lo;

  // Map a value into 2…98% so edge dots are never clipped by the container.
  const posOf = (v: number) => (span === 0 ? 50 : 2 + ((v - lo) / span) * 96);

  const lanes = useMemo(
    () => (sorted.length > DENSITY_CAP ? [] : assignLanes(sorted.map((p) => (span === 0 ? 0.5 : (p.canonical - lo) / span)))),
    [sorted, lo, span],
  );

  const dense = sorted.length > DENSITY_CAP;
  const laneCount = lanes.length ? Math.max(...lanes) + 1 : 1;
  const plotH = dense ? 56 : laneCount * LANE_H + AXIS_H + 6;

  const idx = Math.min(focus, Math.max(0, sorted.length - 1));
  const active = hover !== null ? hover : idx;
  const activePoint = sorted[active];
  const activePaper = activePoint ? papers.find((p) => p.id === activePoint.rec.paperId) : undefined;
  const activeExclusion = activePoint ? aggregateExclusion(activePoint.rec) : null;

  const move = (delta: number) => {
    if (sorted.length === 0) return;
    const next = Math.max(0, Math.min(sorted.length - 1, idx + delta));
    setFocus(next);
    btnRefs.current[next]?.focus();
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
      e.preventDefault();
      move(1);
    } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
      e.preventDefault();
      move(-1);
    } else if (e.key === 'Home') {
      e.preventDefault();
      move(-sorted.length);
    } else if (e.key === 'End') {
      e.preventDefault();
      move(sorted.length);
    }
  };

  // ── density mode: one bar per bin, past the point where dots stop reading ──
  const bins = useMemo(() => {
    if (!dense) return [];
    const out = Array.from({ length: DENSITY_BINS }, () => ({ count: 0, points: [] as PlotPoint[] }));
    for (const p of sorted) {
      const t = span === 0 ? 0 : (p.canonical - lo) / span;
      const b = Math.min(DENSITY_BINS - 1, Math.floor(t * DENSITY_BINS));
      out[b].count += 1;
      out[b].points.push(p);
    }
    return out;
  }, [dense, sorted, lo, span]);
  const binMax = bins.reduce((m, b) => Math.max(m, b.count), 1);

  if (sorted.length === 0) {
    return (
      <div className="text-caption text-ink-soft py-3">
        No plottable values — every record for this field is in a unit that cannot be converted to{' '}
        <span className="font-num">{unitLabel(def.canonicalUnit)}</span>.
      </div>
    );
  }

  return (
    <div>
      <div
        className="relative"
        style={{ height: plotH }}
        role="group"
        aria-label={`${def.name} — ${sorted.length} record${sorted.length === 1 ? '' : 's'} plotted from ${fmt(lo)} to ${fmt(hi)} ${unitLabel(def.canonicalUnit)}`}
        onKeyDown={dense ? undefined : onKeyDown}
      >
        {/* axis */}
        <div
          className="absolute left-0 right-0 border-t border-line"
          style={{ top: plotH - AXIS_H }}
          aria-hidden
        />
        {/* median marker */}
        {medianValue !== null && span > 0 && (
          <div
            className="absolute w-px bg-ink-soft/60"
            style={{ left: `${posOf(medianValue)}%`, top: 0, height: plotH - AXIS_H + 3 }}
            aria-hidden
            title={`Median ${fmt(medianValue)} ${def.canonicalUnit}`}
          />
        )}

        {dense
          ? bins.map((b, i) => {
              if (b.count === 0) return null;
              const h = Math.max(2, (b.count / binMax) * (plotH - AXIS_H - 4));
              const prov = aggregateProv(b.points);
              const binLo = lo + (span * i) / DENSITY_BINS;
              const binHi = lo + (span * (i + 1)) / DENSITY_BINS;
              return (
                <div
                  key={i}
                  className={cx(
                    'absolute rounded-[1px]',
                    prov === 'gold' ? 'bg-gold' : prov === 'verified' ? 'bg-accent' : 'bg-ink-soft',
                  )}
                  style={{
                    left: `${2 + (i / DENSITY_BINS) * 96}%`,
                    width: `${96 / DENSITY_BINS - 0.2}%`,
                    bottom: AXIS_H,
                    height: h,
                    opacity: 0.75,
                  }}
                  title={`${b.count} record${b.count === 1 ? '' : 's'} between ${fmt(binLo)} and ${fmt(binHi)} ${def.canonicalUnit}`}
                />
              );
            })
          : sorted.map((p, i) => {
              const rejected = p.rec.status === 'rejected';
              const excl = aggregateExclusion(p.rec);
              return (
                <button
                  key={p.rec.id}
                  ref={(el) => {
                    btnRefs.current[i] = el;
                  }}
                  type="button"
                  tabIndex={i === idx ? 0 : -1}
                  onFocus={() => setFocus(i)}
                  onMouseEnter={() => setHover(i)}
                  onMouseLeave={() => setHover(null)}
                  onClick={() => navigate(`/trawl/sources/${p.rec.paperId}?span=${p.rec.id}`)}
                  className={cx(
                    'absolute -translate-x-1/2 rounded-full leading-none p-0 border-0 bg-transparent',
                    'hover:scale-125 focus-visible:scale-125 transition-transform',
                    rejected && 'opacity-45',
                  )}
                  style={{ left: `${posOf(p.canonical)}%`, top: lanes[i] * LANE_H }}
                  title={`${fmt(p.canonical)} ${def.canonicalUnit} · ${p.rec.paperId} · ${p.rec.id}${
                    excl ? ` · ${EXCLUSION_NOTE[excl]}` : ''
                  }`}
                  aria-label={`${fmt(p.canonical)} ${unitLabel(def.canonicalUnit)}, ${p.rec.paperId}, record ${p.rec.id}, ${
                    rejected ? 'rejected' : p.prov
                  }${excl && !rejected ? ', excluded from the statistics' : ''}. Opens the quoted span.`}
                >
                  <ProvDot p={p.prov} size={i === active ? 11 : 9} />
                </button>
              );
            })}

        {/* axis end labels */}
        <div
          className="absolute left-0 right-0 flex justify-between text-caption text-ink-soft font-num"
          style={{ top: plotH - AXIS_H + 2 }}
          aria-hidden
        >
          <span>{fmt(lo)}</span>
          {span > 0 && <span>{fmt(hi)}</span>}
        </div>
      </div>

      <div className="mt-1 min-h-[18px] text-caption" aria-hidden>
        {activePoint ? (
          <span className="inline-flex flex-wrap items-center gap-x-2 gap-y-0.5">
            <ProvDot p={activePoint.prov} />
            <span className="font-num text-ink">
              {fmt(activePoint.canonical)} {def.canonicalUnit}
            </span>
            <span className="text-ink-soft">
              {activePaper ? activePaper.title.slice(0, 68) : activePoint.rec.paperId}
              {activePaper && activePaper.title.length > 68 ? '…' : ''}
            </span>
            <span className="font-num text-ink-soft">{activePoint.rec.id}</span>
            {activeExclusion && (
              <span
                className={activeExclusion === 'rejected' ? 'text-signal-error' : 'text-signal-warn'}
              >
                {activeExclusion === 'not-primary' && activePoint.rec.citesRecordId
                  ? `quotes ${activePoint.rec.citesRecordId} — excluded from statistics`
                  : EXCLUSION_NOTE[activeExclusion]}
              </span>
            )}
            {activePoint.viaPaper && (
              <span className="text-ink-soft">attributed via the paper&rsquo;s organism list</span>
            )}
          </span>
        ) : (
          <span className="text-ink-soft">Hover or arrow through the dots to read a value.</span>
        )}
      </div>

      {dense && (
        <div className="text-caption text-ink-soft mt-1">
          <span className="font-num">{sorted.length}</span> records — drawn as density bins because
          individual dots stop being legible past{' '}
          <span className="font-num">{DENSITY_CAP}</span>. Switch to the table view to reach a single
          row.
        </div>
      )}
    </div>
  );
}

// ── one field summary row ──────────────────────────────────────────────

function FieldRow({
  g,
  showRejected,
  onQueue,
}: {
  g: FieldGroup;
  showRejected: boolean;
  onQueue: (ids: string[], label: string) => void;
}) {
  // Read from the store rather than thread a prop through every call site —
  // the referee's findings are global, not something this row owns.
  const contradictions = useStore((s) => s.contradictions);

  const plotted = useMemo(() => {
    const base = g.usable as PlotPoint[];
    return showRejected ? ([...base, ...g.rejectedUsable] as PlotPoint[]) : base;
  }, [g.usable, g.rejectedUsable, showRejected]);

  const unverifiedIds = g.live.filter((p) => p.rec.status === 'unverified').map((p) => p.rec.id);
  const prov = aggregateProv(g.live);

  return (
    <Tick
      p={prov}
      className="py-3 border-b border-line last:border-b-0"
      title={
        prov === 'gold'
          ? 'At least one record for this field is in the curated gold set'
          : prov === 'verified'
            ? 'At least one record for this field has been verified by a reviewer'
            : 'No record for this field has been reviewed yet'
      }
    >
      <div className="grid grid-cols-1 lg:grid-cols-[minmax(210px,266px)_1fr] gap-x-5 gap-y-2">
        <div className="min-w-0">
          <div className="font-medium leading-snug">{g.def.name}</div>
          <div className="text-caption text-ink-soft font-num">
            {unitLabel(g.def.canonicalUnit)}
          </div>

          <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-caption">
            <span title="Records attributed to this strain, excluding rejected ones">
              n <span className="font-num text-ink">{g.live.length}</span>
            </span>
            <span className="inline-flex items-center gap-1" title="Verified by a reviewer">
              <ProvDot p="verified" />
              <span className="font-num text-ink">{g.verified}</span>
            </span>
            {g.gold > 0 && (
              <span className="inline-flex items-center gap-1" title="In the curated gold set">
                <ProvDot p="gold" />
                <span className="font-num text-ink">{g.gold}</span>
              </span>
            )}
            <span className="inline-flex items-center gap-1" title="Extracted but not yet reviewed">
              <ProvDot p="unverified" />
              <span className="font-num text-ink">{g.unverified}</span>
            </span>
          </div>

          {g.stats ? (
            <div className="mt-1.5 text-caption flex items-start gap-2">
              <ContradictionRail
                marks={g.usable.map((p) => ({ record: p.rec, value: p.canonical as number }))}
                aggregate={{
                  median: g.stats.median,
                  p25: g.stats.median,
                  p75: g.stats.median,
                  min: g.stats.min,
                  max: g.stats.max,
                  n: g.usable.length,
                  nPrimary: g.usable.filter((p) => p.rec.isPrimary).length,
                  unit: g.def.canonicalUnit,
                  strata: [],
                  method: 'median-of-primary-v1',
                }}
                contradictions={contradictions.filter((c) =>
                  c.recordIds.some((id: string) => g.all.some((p) => p.rec.id === id)),
                )}
              />
              <div>
              <div>
                median{' '}
                <span className="font-num text-ink">
                  {fmt(g.stats.median)} {g.def.canonicalUnit}
                </span>
              </div>
              <div className="text-ink-soft">
                range{' '}
                <span className="font-num">
                  {g.stats.min === g.stats.max
                    ? fmt(g.stats.min)
                    : `${fmt(g.stats.min)} – ${fmt(g.stats.max)}`}{' '}
                  {g.def.canonicalUnit}
                </span>
              </div>
              <a
                href={href(`/ledger/p/${g.def.id}`)}
                className="text-accent hover:underline"
              >
                open the parameter
              </a>
              </div>
            </div>
          ) : g.usable.length > 0 ? (
            <div className="mt-1.5 text-caption text-signal-warn">
              No median — every convertible record for this field is held out of the statistics.
            </div>
          ) : (
            <div className="mt-1.5 text-caption text-signal-warn">
              No convertible values — nothing to summarize.
            </div>
          )}

          {g.held.length > 0 && (
            <div className="mt-1.5 text-caption text-ink-soft">
              <span className="font-num">{g.held.length}</span> record
              {g.held.length === 1 ? ' is' : 's are'} drawn but held out of the median and range —{' '}
              {heldReason(g.heldIndustry, g.heldSecondary)}.
            </div>
          )}

          {g.verified === 0 && (
            <div className="mt-1.5 text-caption text-ink-soft">
              No verified records yet —{' '}
              <span className="font-num text-ink">{g.unverified}</span> unverified.{' '}
              {unverifiedIds.length > 0 && (
                <button
                  className="text-accent hover:underline"
                  onClick={() => onQueue(unverifiedIds, g.def.name)}
                  title={`Queue exactly these ${unverifiedIds.length} records into the review workspace`}
                >
                  Review them
                </button>
              )}
              {g.stats && (
                <span className="block">
                  The median above is computed over unverified extractions only.
                </span>
              )}
            </div>
          )}

          {g.unconvertible > 0 && (
            <div className="mt-1.5 text-caption text-signal-warn flex items-start gap-1">
              <AlertTriangle size={12} className="mt-[2px] shrink-0" />
              <span>
                <span className="font-num">{g.unconvertible}</span> record
                {g.unconvertible === 1 ? '' : 's'} in a unit that does not convert to{' '}
                <span className="font-num">{unitLabel(g.def.canonicalUnit)}</span> — excluded from
                the statistics and the plot.
              </span>
            </div>
          )}

          {g.viaPaper > 0 && (
            <div className="mt-1.5 text-caption text-ink-soft">
              <span className="font-num">{g.viaPaper}</span> attributed through the paper&rsquo;s
              organism list rather than a per-record tag.
            </div>
          )}
        </div>

        <div className="min-w-0">
          <StripPlot points={plotted} def={g.def} medianValue={g.stats ? g.stats.median : null} />
        </div>
      </div>
    </Tick>
  );
}

// ── screen ─────────────────────────────────────────────────────────────

export default function StrainPage({ strainId }: { strainId: string }) {
  const strains = useStore((s) => s.strains);
  const papers = useStore((s) => s.papers);
  const records = useStore((s) => s.records);
  const protocols = useStore((s) => s.protocols);
  const scenarios = useStore((s) => s.scenarios);
  const collections = useStore((s) => s.collections);
  const runs = useStore((s) => s.runs);
  const activeRunId = useStore((s) => s.activeRunId);
  const density = useStore((s) => s.ui.density);
  const startReview = useStore((s) => s.startReview);
  const logActivity = useStore((s) => s.logActivity);
  const toast = useStore((s) => s.toast);

  const [ready, setReady] = useState(false);
  const [view, setView] = useState<'plots' | 'table'>('plots');
  const [showRejected, setShowRejected] = useState(false);
  const [fieldQuery, setFieldQuery] = useState('');

  useEffect(() => {
    let alive = true;
    setReady(false);
    delayClass('quick').then(() => {
      if (alive) setReady(true);
    });
    return () => {
      alive = false;
    };
  }, [strainId]);

  const strain = strains.find((s) => s.id === strainId);

  const paperById = useMemo(() => new Map(papers.map((p) => [p.id, p])), [papers]);

  const strainPapers = useMemo(
    () => papers.filter((p) => p.organisms.includes(strainId)),
    [papers, strainId],
  );

  // A record belongs to this strain when it says so, or — absent a per-record
  // tag — when its paper's organism list says so. An explicit tag for another
  // strain always wins.
  const points = useMemo<SPoint[]>(() => {
    const out: SPoint[] = [];
    for (const rec of records) {
      const direct = rec.organism === strainId;
      const viaPaper =
        !rec.organism && (paperById.get(rec.paperId)?.organisms.includes(strainId) ?? false);
      if (!direct && !viaPaper) continue;
      const def = ONTOLOGY_BY_ID[rec.field];
      out.push({
        rec,
        prov: provOf(rec),
        viaPaper,
        canonical: def ? toCanonical(rec, def.canonicalUnit) : null,
      });
    }
    return out;
  }, [records, paperById, strainId]);

  const recordIds = useMemo(() => new Set(points.map((p) => p.rec.id)), [points]);

  const groups = useMemo<FieldGroup[]>(() => {
    const by = new Map<FieldId, SPoint[]>();
    for (const p of points) {
      const arr = by.get(p.rec.field);
      if (arr) arr.push(p);
      else by.set(p.rec.field, [p]);
    }
    return ONTOLOGY.filter((def) => by.has(def.id)).map((def) => {
      const all = by.get(def.id)!;
      const rejected = all.filter((p) => p.rec.status === 'rejected');
      const live = all.filter((p) => p.rec.status !== 'rejected');
      const usable = live.filter((p) => p.canonical !== null);
      const rejectedUsable = rejected.filter((p) => p.canonical !== null);
      // The statistics run over independent evidence only; the held-out records
      // stay in `usable` so they are still drawn and still clickable.
      const aggregatable = usable.filter((p) => isAggregatable(p.rec));
      const held = usable.filter((p) => !isAggregatable(p.rec));
      return {
        def,
        all,
        live,
        rejected,
        usable,
        rejectedUsable,
        held,
        heldIndustry: held.filter((p) => aggregateExclusion(p.rec) === 'industry-estimate').length,
        heldSecondary: held.filter((p) => aggregateExclusion(p.rec) === 'not-primary').length,
        unconvertible: live.length - usable.length,
        stats: summarize(aggregatable.map((p) => p.canonical as number)),
        verified: live.filter((p) => p.rec.status === 'verified').length,
        gold: live.filter((p) => !!p.rec.gold).length,
        unverified: live.filter((p) => p.rec.status === 'unverified').length,
        viaPaper: live.filter((p) => p.viaPaper).length,
      };
    });
  }, [points]);

  const visibleGroups = useMemo(() => {
    const q = fieldQuery.trim().toLowerCase();
    if (!q) return groups;
    return groups.filter(
      (g) => g.def.name.toLowerCase().includes(q) || g.def.id.toLowerCase().includes(q),
    );
  }, [groups, fieldQuery]);

  // The table view honours the same field filter and rejected toggle as the plots,
  // so switching between them never changes which records you are looking at.
  const tableRows = useMemo(() => {
    const allowed = new Set(visibleGroups.map((g) => g.def.id));
    return points.filter(
      (p) => allowed.has(p.rec.field) && (showRejected || p.rec.status !== 'rejected'),
    );
  }, [points, visibleGroups, showRejected]);

  const rejectedTotal = points.filter((p) => p.rec.status === 'rejected').length;
  const verifiedTotal = points.filter((p) => p.rec.status === 'verified').length;
  const goldTotal = points.filter((p) => !!p.rec.gold && p.rec.status !== 'rejected').length;

  // ── linked assets ────────────────────────────────────────────────────

  const linkedProtocols = useMemo(
    () => protocols.filter((p) => p.organisms.includes(strainId)),
    [protocols, strainId],
  );

  const runList = useMemo(() => Object.values(runs), [runs]);

  const lastRunFor = useCallback(
    (protocolId: string) =>
      runList
        .filter((r) => r.protocolId === protocolId)
        .sort((a, b) => b.startedAt - a.startedAt)[0],
    [runList],
  );

  const currentVersionOf = (p: Protocol) =>
    p.versions.find((v) => v.version === p.currentVersion) ?? p.versions[p.versions.length - 1];

  const linkedScenarios = useMemo<ScenarioLink[]>(() => {
    const needles = strain
      ? [strain.designation.toLowerCase(), strain.binomial.toLowerCase()]
      : [strainId.toLowerCase()];
    const out: ScenarioLink[] = [];
    for (const sc of scenarios) {
      const viaRecord =
        sc.assumptions.find((a) => a.recordId && recordIds.has(a.recordId))?.recordId ??
        sc.dims.find((d) => d.sourceRecordId && recordIds.has(d.sourceRecordId))?.sourceRecordId;
      if (viaRecord) {
        out.push({ sc, via: 'record', recordId: viaRecord });
        continue;
      }
      const text = `${sc.name} ${sc.description} ${sc.product}`.toLowerCase();
      if (needles.some((n) => n.length > 2 && text.includes(n))) out.push({ sc, via: 'named' });
    }
    return out;
  }, [scenarios, recordIds, strain, strainId]);

  const linkedCollections = useMemo(() => {
    const ids = new Set(strainPapers.map((p) => p.id));
    return collections
      .map((c) => ({ c, hits: c.paperIds.filter((id) => ids.has(id)) }))
      .filter((x) => x.hits.length > 0);
  }, [collections, strainPapers]);

  // ── media ────────────────────────────────────────────────────────────

  const mediaProtocols = useMemo(() => {
    const scored = linkedProtocols
      .filter((p) => p.category === 'media')
      .map((p) => {
        const v = currentVersionOf(p);
        const cited = v ? v.materials.filter((m) => m.sourceRecordId && recordIds.has(m.sourceRecordId)).length : 0;
        return { protocol: p, version: v, cited, materials: v ? v.materials.length : 0 };
      });
    return scored.sort((a, b) => b.cited - a.cited || b.materials - a.materials);
  }, [linkedProtocols, recordIds]);

  const components = useMemo(() => {
    const by = new Map<string, SPoint[]>();
    for (const p of points) {
      if (p.rec.field !== 'medium_component_conc') continue;
      if (p.rec.status === 'rejected') continue;
      const tag = p.rec.componentTag ?? 'unnamed component';
      const arr = by.get(tag);
      if (arr) arr.push(p);
      else by.set(tag, [p]);
    }
    const canonicalUnit = ONTOLOGY_BY_ID.medium_component_conc.canonicalUnit;
    return [...by.entries()]
      .map(([tag, ps]) => {
        const usable = ps.filter((p) => p.canonical !== null);
        const aggregatable = usable.filter((p) => isAggregatable(p.rec));
        return {
          tag,
          points: ps,
          stats: summarize(aggregatable.map((p) => p.canonical as number)),
          held: usable.length - aggregatable.length,
          unconvertible: ps.length - usable.length,
          verified: ps.filter((p) => p.rec.status === 'verified').length,
          prov: aggregateProv(ps),
          canonicalUnit,
        };
      })
      .sort((a, b) => b.points.length - a.points.length || a.tag.localeCompare(b.tag));
  }, [points]);

  // ── actions ──────────────────────────────────────────────────────────

  const queueReview = useCallback(
    (ids: string[], label: string) => {
      if (ids.length === 0) return;
      startReview(ids);
      logActivity({
        at: stamp(),
        icon: 'clipboard-check',
        text: `Review session started — ${label} for ${strainId} (${ids.length} record${ids.length === 1 ? '' : 's'})`,
        href: '#/trawl/review',
        provenance: 'user',
      });
      navigate('/trawl/review');
    },
    [startReview, logActivity, strainId],
  );

  const exportSummary = () => {
    if (groups.length === 0) {
      toast({ text: 'Nothing to export — no records are attributed to this strain', kind: 'warn' });
      return;
    }
    exportCSV(
      `openferment-${strainId}-parameter-summary.csv`,
      [
        'Strain ID',
        'Strain designation',
        'Field ID',
        'Field',
        'Canonical unit',
        'n (excludes rejected)',
        'Verified',
        'Gold',
        'Unverified',
        'Rejected (excluded)',
        'Unconvertible (excluded)',
        'Held out of statistics (industry estimate or quoting another record)',
        'Median (canonical)',
        'Min (canonical)',
        'Max (canonical)',
        'Attributed via paper organism list',
      ],
      groups.map((g) => [
        strainId,
        strain?.designation ?? '',
        g.def.id,
        g.def.name,
        g.def.canonicalUnit,
        g.live.length,
        g.verified,
        g.gold,
        g.unverified,
        g.rejected.length,
        g.unconvertible,
        g.held.length,
        g.stats ? g.stats.median : '',
        g.stats ? g.stats.min : '',
        g.stats ? g.stats.max : '',
        g.viaPaper,
      ]),
    );
  };

  // ── table view of band 1 ─────────────────────────────────────────────

  const tableColumns: Column<SPoint>[] = [
    {
      key: 'id',
      header: 'Record',
      width: '96px',
      priority: 1,
      render: ({ rec }) => (
        <a
          href={href(`/trawl/sources/${rec.paperId}?span=${rec.id}`)}
          className="font-num text-accent hover:underline"
          onClick={(e) => e.stopPropagation()}
          title={`Open ${rec.id} anchored in ${rec.paperId}`}
        >
          {rec.id}
        </a>
      ),
      value: ({ rec }) => rec.id,
    },
    {
      key: 'field',
      header: 'Field',
      width: '220px',
      priority: 1,
      render: ({ rec }) => <span className="block truncate">{fieldName(rec.field)}</span>,
      value: ({ rec }) => fieldName(rec.field),
    },
    {
      key: 'canonical',
      header: 'Value (canonical)',
      width: '130px',
      numeric: true,
      priority: 1,
      render: ({ rec, canonical }) =>
        canonical === null ? (
          <span className="text-signal-warn" title="Unit does not convert to the canonical unit">
            n/a
          </span>
        ) : (
          <span className="font-num">{fmt(canonical)}</span>
        ),
      value: ({ canonical }) => (canonical === null ? '' : canonical),
    },
    {
      key: 'canonicalUnit',
      header: 'Canonical unit',
      width: '116px',
      priority: 2,
      render: ({ rec }) => (
        <span className="font-num text-ink-soft">
          {unitLabel(ONTOLOGY_BY_ID[rec.field]?.canonicalUnit ?? '')}
        </span>
      ),
      value: ({ rec }) => ONTOLOGY_BY_ID[rec.field]?.canonicalUnit ?? '',
    },
    {
      key: 'published',
      header: 'As published',
      width: '140px',
      priority: 2,
      render: ({ rec }) => (
        <span className="font-num">
          {fmt(rec.value)} <span className="text-ink-soft">{rec.unit || '—'}</span>
        </span>
      ),
      value: ({ rec }) => `${rec.value} ${rec.unit}`,
    },
    {
      key: 'status',
      header: 'Status',
      width: '104px',
      priority: 1,
      render: ({ rec, prov }) => (
        <span className="inline-flex items-center gap-1.5">
          <ProvDot p={prov} />
          <span className={cx(rec.status === 'rejected' && 'text-signal-error')}>
            {rec.gold ? 'Gold' : rec.status === 'verified' ? 'Verified' : rec.status === 'rejected' ? 'Rejected' : 'Unverified'}
          </span>
        </span>
      ),
      value: ({ rec }) => (rec.gold ? 'gold' : rec.status),
    },
    {
      key: 'source',
      header: 'Source',
      width: '92px',
      priority: 1,
      render: ({ rec }) => (
        <span onClick={(e) => e.stopPropagation()}>
          <CitationChip paperId={rec.paperId} />
        </span>
      ),
      value: ({ rec }) => rec.paperId,
    },
    {
      key: 'attribution',
      header: 'Attribution',
      width: '116px',
      priority: 3,
      render: ({ viaPaper }) => (
        <span className="text-ink-soft">{viaPaper ? 'via paper' : 'per record'}</span>
      ),
      value: ({ viaPaper }) => (viaPaper ? 'via paper' : 'per record'),
    },
    {
      key: 'quote',
      header: 'Quoted span',
      priority: 3,
      render: ({ rec }) => (
        <span className="font-serif italic text-ink-soft block truncate" title={rec.quote}>
          “{rec.quote.length > 90 ? `${rec.quote.slice(0, 89)}…` : rec.quote}”
        </span>
      ),
      value: ({ rec }) => rec.quote,
    },
  ];

  const tableFacets: FacetDef<SPoint>[] = [
    {
      key: 'field',
      label: 'Field',
      valuesOf: ({ rec }) => [rec.field],
      labelOf: (v) => fieldName(v as FieldId),
    },
    {
      key: 'status',
      label: 'Status',
      valuesOf: ({ rec }) => (rec.gold ? [rec.status, 'gold'] : [rec.status]),
      labelOf: (v) => STATUS_FACET_LABEL[v] ?? v,
    },
    { key: 'paper', label: 'Paper', valuesOf: ({ rec }) => [rec.paperId] },
  ];

  // ── states ───────────────────────────────────────────────────────────

  if (!strain) {
    return (
      <>
        <PageHeader
          eyebrow={EYEBROW}
          title="Strain not found"
          subtitle="Session state resets on refresh, so a deep link from an earlier session can point at nothing."
        />
        <Card>
          <EmptyState
            icon={<Microscope size={22} />}
            title={`No strain with the id “${strainId}”`}
            body="The organism index lists every strain this corpus covers. Open it to pick one."
            action={<LinkButton to="/organisms">Back to organisms</LinkButton>}
          />
        </Card>
      </>
    );
  }

  if (!ready) {
    return (
      <>
        <PageHeader
          eyebrow={EYEBROW}
          title={
            <span>
              <span className="italic">{strain.binomial}</span>{' '}
              <span className="font-num not-italic">{strain.designation}</span>
            </span>
          }
        />
        <Card className="p-4 mb-4">
          <Skeleton rows={3} />
        </Card>
        <Card>
          <Skeleton rows={10} />
        </Card>
      </>
    );
  }

  const bandControls = (
    <div className="flex flex-wrap items-center gap-2">
      <div className="relative">
        <input
          className="input w-[190px] pr-6"
          placeholder="Filter fields…"
          value={fieldQuery}
          onChange={(e) => setFieldQuery(e.target.value)}
          aria-label="Filter parameter fields by name"
        />
        {fieldQuery && (
          <button
            className="absolute right-1.5 top-1/2 -translate-y-1/2 text-ink-soft hover:text-ink"
            onClick={() => setFieldQuery('')}
            aria-label="Clear the field filter"
          >
            <X size={13} />
          </button>
        )}
      </div>
      {rejectedTotal > 0 && (
        <button
          className={cx('btn btn-sm', showRejected && 'chip-active')}
          onClick={() => setShowRejected((v) => !v)}
          aria-pressed={showRejected}
          title="Rejected records are never counted in the statistics; this only draws them greyed on the plots"
        >
          {showRejected ? 'Hide' : 'Show'} rejected{' '}
          <span className="font-num">({rejectedTotal})</span>
        </button>
      )}
      <div className="flex rounded-input border border-line overflow-hidden" role="group" aria-label="Band view">
        {(
          [
            ['plots', 'Strip plots', ScatterChart],
            ['table', 'View as table', Table2],
          ] as const
        ).map(([mode, label, Icon]) => (
          <button
            key={mode}
            onClick={() => setView(mode)}
            aria-pressed={view === mode}
            className={cx(
              'px-2 py-[3px] text-[11px] inline-flex items-center gap-1',
              view === mode ? 'bg-accent-wash text-ink font-medium' : 'text-ink-soft hover:text-ink',
            )}
          >
            <Icon size={12} /> {label}
          </button>
        ))}
      </div>
    </div>
  );

  return (
    <>
      <PageHeader
        eyebrow={`${EYEBROW} · BSL-${strain.bsl}`}
        title={
          <span>
            <span className="italic">{strain.binomial}</span>{' '}
            <span className="font-num not-italic">{strain.designation}</span>
          </span>
        }
        subtitle={
          <nav aria-label="Taxonomy" className="flex flex-wrap items-center gap-x-1 gap-y-0.5">
            {strain.taxonomy.map((t, i) => (
              <span key={t} className="inline-flex items-center gap-1">
                {i > 0 && (
                  <span className="text-ink-soft/60" aria-hidden>
                    ›
                  </span>
                )}
                <span className={cx(i === strain.taxonomy.length - 1 && 'italic text-ink')}>{t}</span>
              </span>
            ))}
          </nav>
        }
        actions={
          <>
            <Button onClick={exportSummary} title="CSV of the parameter summary below, one row per field">
              <Download size={14} /> Export summary
            </Button>
            <LinkButton to="/organisms">
              <ArrowRight size={14} className="rotate-180" /> All organisms
            </LinkButton>
          </>
        }
      />

      <div className="flex flex-wrap items-center gap-2 mb-3">
        {strain.badges.map((b) => (
          <span key={b} className="chip text-ink-soft">
            {b}
          </span>
        ))}
        <span className="chip text-ink-soft font-num">{strainId}</span>
      </div>

      <Card className="p-4 mb-5">
        <Tick p="gold" title="Curator-authored description — hand-written, not extracted">
          <div className="text-caption uppercase tracking-wide text-ink-soft mb-1">
            Curator description
          </div>
          <p className="font-serif text-reading">{strain.description}</p>
        </Tick>
      </Card>

      <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5 mb-4 text-caption text-ink-soft">
        <span>
          <span className="font-num text-ink">{strainPapers.length}</span> papers
        </span>
        <span>
          <span className="font-num text-ink">{points.length}</span> records
        </span>
        <span>
          <span className="font-num text-accent">{verifiedTotal}</span> verified
        </span>
        <span>
          <span className="font-num text-gold">{goldTotal}</span> gold
        </span>
        <ProvenanceLegend />
      </div>

      {/* ── BAND 1 — parameter summary ─────────────────────────────────── */}
      <section className="mb-6" aria-labelledby="band-parameters">
        <SectionTitle right={bandControls}>
          <span id="band-parameters">Parameter summary</span>
        </SectionTitle>
        <p className="text-caption text-ink-soft mb-2 max-w-3xl">
          Every field with at least one record for this strain, normalized into the ontology&rsquo;s
          canonical unit before any statistic is taken.{' '}
          <Explain label="How these statistics are computed">
            Records arrive in whatever unit the paper used. Each value is converted with the shared
            unit engine into the field&rsquo;s canonical unit, then the median and range are taken
            over the converted set. Four kinds of record are excluded from that statistic and
            counted separately: rejected ones, ones whose unit belongs to a different dimensional
            family, industry estimates, and ones quoting another paper&rsquo;s measurement rather
            than reporting their own. The last two are still drawn — they are real values, just not
            independent evidence, and counting a recitation twice would manufacture agreement.
            Verifying a record in the review queue changes these numbers immediately — nothing here
            is precomputed.
          </Explain>{' '}
          One dot is one record; click a dot to open the quoted span in its paper.
        </p>

        {groups.length === 0 ? (
          <Card>
            <EmptyState
              icon={<FlaskConical size={22} />}
              title="No extraction records for this strain"
              body={`Nothing in this session's corpus is attributed to ${strain.designation}, either by a per-record organism tag or by a paper's organism list. The extraction table is the place to check what the corpus does cover.`}
              action={
                <div className="flex gap-2">
                  <LinkButton to="/extract">Open the extraction table</LinkButton>
                  <LinkButton to="/trawl">Browse the sources</LinkButton>
                </div>
              }
            />
          </Card>
        ) : visibleGroups.length === 0 ? (
          <Card>
            <EmptyState
              icon={<FlaskConical size={22} />}
              title="No field matches that filter"
              body={`“${fieldQuery}” excludes all ${groups.length} fields with records for this strain, in both the plot and the table view.`}
              action={<Button onClick={() => setFieldQuery('')}>Clear the filter</Button>}
            />
          </Card>
        ) : view === 'table' ? (
          <DataTable
            rows={tableRows}
            columns={tableColumns}
            rowKey={({ rec }) => rec.id}
            tickOf={({ prov }) => prov}
            facets={tableFacets}
            dense={density === 'dense'}
            exportName={`openferment-${strainId}-records`}
            exportNote="Canonical values are converted from the stored published pair on every render, so the table and the plots can never disagree."
            onOpen={({ rec }) => navigate(`/trawl/sources/${rec.paperId}?span=${rec.id}`)}
            searchOf={({ rec }) =>
              `${rec.id} ${rec.paperId} ${fieldName(rec.field)} ${rec.unit} ${rec.componentTag ?? ''} ${rec.quote}`
            }
            emptyTitle="No records match"
            emptyBody="Every record was filtered out. Clear a facet or widen the row filter."
            maxHeight="640px"
          />
        ) : (
          <Card className="px-4">
            {visibleGroups.map((g) => (
              <FieldRow key={g.def.id} g={g} showRejected={showRejected} onQueue={queueReview} />
            ))}
          </Card>
        )}

        {rejectedTotal > 0 && !showRejected && view === 'plots' && (
          <p className="text-caption text-ink-soft mt-1.5">
            <span className="font-num">{rejectedTotal}</span> rejected record
            {rejectedTotal === 1 ? '' : 's'} for this strain {rejectedTotal === 1 ? 'is' : 'are'} not
            drawn and never enter a statistic.
          </p>
        )}
      </section>

      {/* ── BAND 2 — media ─────────────────────────────────────────────── */}
      <section className="mb-6" aria-labelledby="band-media">
        <SectionTitle>
          <span id="band-media">Media</span>
        </SectionTitle>
        <p className="text-caption text-ink-soft mb-2 max-w-3xl">
          Medium composition as the corpus records it, and the media protocols in this workspace that
          list <span className="italic">{strain.binomial}</span> {strain.designation}.
        </p>

        <div className="grid grid-cols-1 xl:grid-cols-[1fr_360px] gap-4">
          <Card className="p-4">
            <div className="text-caption uppercase tracking-wide text-ink-soft mb-2">
              Components extracted from the literature
            </div>
            {components.length === 0 ? (
              <div className="text-body text-ink-soft">
                No <span className="font-num">medium_component_conc</span> records are attributed to
                this strain. Medium composition for it would have to come from a protocol, not from
                the corpus.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full border-collapse text-body">
                  <caption className="sr-only">
                    Medium components recorded for {strain.designation}, median concentration in
                    grams per litre
                  </caption>
                  <thead>
                    <tr className="border-b border-line text-caption text-ink-soft">
                      <th className="text-left font-medium py-1.5 pl-3">Component</th>
                      <th className="text-right font-medium py-1.5">
                        Median <span className="font-num">(g L⁻¹)</span>
                      </th>
                      <th className="text-right font-medium py-1.5">Range</th>
                      <th className="text-right font-medium py-1.5">n</th>
                      <th className="text-left font-medium py-1.5 pl-3">Evidence</th>
                    </tr>
                  </thead>
                  <tbody>
                    {components.map((c) => (
                      <tr key={c.tag} className="border-b border-line/70 last:border-b-0 align-middle">
                        <td className="py-1.5">
                          <Tick p={c.prov} title={`Strongest provenance among ${c.points.length} records`}>
                            {c.tag}
                          </Tick>
                        </td>
                        <td className="text-right font-num py-1.5">
                          {c.stats ? fmt(c.stats.median) : '—'}
                        </td>
                        <td className="text-right font-num py-1.5 text-ink-soft">
                          {c.stats
                            ? c.stats.min === c.stats.max
                              ? fmt(c.stats.min)
                              : `${fmt(c.stats.min)} – ${fmt(c.stats.max)}`
                            : '—'}
                        </td>
                        <td className="text-right font-num py-1.5">{c.points.length}</td>
                        <td className="py-1.5 pl-3">
                          <span className="inline-flex flex-wrap gap-1">
                            {c.points.slice(0, 3).map((p) => (
                              <CitationChip key={p.rec.id} recordId={p.rec.id} label={p.rec.id} />
                            ))}
                            {c.points.length > 3 && (
                              <span className="text-caption text-ink-soft font-num self-center">
                                +{c.points.length - 3}
                              </span>
                            )}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {components.some((c) => c.unconvertible > 0) && (
                  <div className="text-caption text-signal-warn mt-2 flex items-start gap-1">
                    <AlertTriangle size={12} className="mt-[2px] shrink-0" />
                    <span>
                      Some records are held in a unit that does not convert to{' '}
                      <span className="font-num">g L⁻¹</span> — a molar concentration, which would
                      need a molar mass the corpus does not carry, or a unit error still awaiting
                      review. Those records are counted but never averaged.
                    </span>
                  </div>
                )}
                {components.some((c) => c.held > 0) && (
                  <div className="text-caption text-ink-soft mt-2">
                    Some records are listed and counted in n but held out of the median and range —
                    industry estimates, and records quoting another paper&rsquo;s measurement rather
                    than reporting their own.
                  </div>
                )}
              </div>
            )}
          </Card>

          <Card className="p-4">
            <div className="text-caption uppercase tracking-wide text-ink-soft mb-2">
              Media protocols in this workspace
            </div>
            {mediaProtocols.length === 0 ? (
              <div className="text-body text-ink-soft">
                No protocol in the <span className="font-num">media</span> category lists this
                organism.{' '}
                <a className="text-accent hover:underline" href={href('/runbook')}>
                  Browse all protocols
                </a>
                .
              </div>
            ) : (
              <ul className="space-y-2">
                {mediaProtocols.map(({ protocol, version, cited, materials }, i) => (
                  <li key={protocol.id}>
                    <a
                      href={href(`/runbook/${protocol.id}`)}
                      className="block rounded-card border border-line p-2.5 hover:border-accent hover:bg-accent-wash transition-colors"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="font-serif font-semibold leading-snug">{protocol.title}</div>
                        {i === 0 && cited > 0 && (
                          <span
                            className="chip chip-active shrink-0 text-caption"
                            title="Most literature-linked medium for this strain in this corpus"
                          >
                            dominant
                          </span>
                        )}
                      </div>
                      <div className="text-caption text-ink-soft mt-0.5 font-num">
                        {protocol.id} · v{protocol.currentVersion} · {materials} materials
                      </div>
                      <div className="text-caption text-ink-soft mt-1">
                        {cited > 0 ? (
                          <>
                            <span className="font-num text-ink">{cited}</span> material
                            {cited === 1 ? '' : 's'} cite a record for this strain
                          </>
                        ) : (
                          'No material in this version cites a record for this strain'
                        )}
                      </div>
                      {version?.baseBatch && (
                        <div className="text-caption text-ink-soft font-num mt-0.5">
                          base batch {fmt(version.baseBatch.value)} {version.baseBatch.unit}
                        </div>
                      )}
                    </a>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </section>

      {/* ── BAND 3 — linked assets ─────────────────────────────────────── */}
      <section className="mb-6" aria-labelledby="band-assets">
        <SectionTitle>
          <span id="band-assets">Linked assets</span>
        </SectionTitle>
        <p className="text-caption text-ink-soft mb-2 max-w-3xl">
          Everything else in the workspace that names this organism or leans on its records.
        </p>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <Card className="p-4">
            <div className="flex items-center gap-2 text-caption uppercase tracking-wide text-ink-soft mb-2">
              <ClipboardList size={13} /> Protocols
              <span className="font-num">({linkedProtocols.length})</span>
            </div>
            {linkedProtocols.length === 0 ? (
              <div className="text-body text-ink-soft">
                No protocol lists this organism yet.{' '}
                <a className="text-accent hover:underline" href={href('/runbook')}>
                  Open the protocol library
                </a>
                .
              </div>
            ) : (
              <ul className="space-y-2">
                {linkedProtocols.map((p) => {
                  const run = lastRunFor(p.id);
                  const live = run && !run.finishedAt && activeRunId === run.id;
                  return (
                    <li key={p.id} className="border-b border-line/70 last:border-b-0 pb-2 last:pb-0">
                      <a
                        href={href(`/runbook/${p.id}`)}
                        className="font-serif font-semibold hover:text-accent hover:underline"
                      >
                        {p.title}
                      </a>
                      <div className="text-caption text-ink-soft font-num">
                        {p.id} · v{p.currentVersion} · {p.category} · BSL-{p.bsl}
                      </div>
                      {run ? (
                        <div className="text-caption mt-0.5 flex flex-wrap items-center gap-2">
                          <span className="text-ink-soft">
                            last run{' '}
                            <span className="font-num text-ink">{stamp(run.startedAt)}</span>
                            {run.finishedAt ? ' · finished' : ' · in progress'}
                          </span>
                          {live && (
                            <a
                              className="btn btn-sm"
                              href={href(`/runbook/${p.id}/run/${run.id}`)}
                              title="Return to the active run"
                            >
                              <Play size={12} /> Resume
                            </a>
                          )}
                        </div>
                      ) : (
                        <div className="text-caption text-ink-soft mt-0.5">
                          no run in this session
                        </div>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </Card>

          <Card className="p-4">
            <div className="flex items-center gap-2 text-caption uppercase tracking-wide text-ink-soft mb-2">
              <LineChart size={13} /> Scenarios
              <span className="font-num">({linkedScenarios.length})</span>
            </div>
            {linkedScenarios.length === 0 ? (
              <div className="text-body text-ink-soft">
                No scenario draws on a record for this strain or names it.{' '}
                <a className="text-accent hover:underline" href={href('/fermos')}>
                  Open the simulation index
                </a>
                .
              </div>
            ) : (
              <ul className="space-y-2">
                {linkedScenarios.map(({ sc, via, recordId }) => (
                  <li key={sc.id} className="border-b border-line/70 last:border-b-0 pb-2 last:pb-0">
                    <a
                      href={href(`/simulate/${sc.id}`)}
                      className="font-serif font-semibold hover:text-accent hover:underline"
                    >
                      {sc.name}
                    </a>
                    <div className="text-caption text-ink-soft font-num">
                      {sc.modelId} · {sc.product}
                    </div>
                    <div className="text-caption text-ink-soft mt-0.5 flex flex-wrap items-center gap-1.5">
                      {via === 'record' && recordId ? (
                        <>
                          assumption sourced from <CitationChip recordId={recordId} label={recordId} />
                        </>
                      ) : (
                        <>named in the scenario description — no record link</>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
            <div className="text-caption text-ink-soft mt-2">
              Demo model v0 — illustrative economics, not validated.
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center gap-2 text-caption uppercase tracking-wide text-ink-soft mb-2">
              <Layers size={13} /> Collections
              <span className="font-num">({linkedCollections.length})</span>
            </div>
            {linkedCollections.length === 0 ? (
              <div className="text-body text-ink-soft">
                None of this strain&rsquo;s papers sit in a collection yet.{' '}
                <a className="text-accent hover:underline" href={href('/trawl')}>
                  Open the library
                </a>
                .
              </div>
            ) : (
              <ul className="space-y-2">
                {linkedCollections.map(({ c, hits }) => (
                  <li key={c.id} className="border-b border-line/70 last:border-b-0 pb-2 last:pb-0">
                    <div className="font-medium">{c.name}</div>
                    <div className="text-caption text-ink-soft">
                      <span className="font-num">{hits.length}</span> of{' '}
                      <span className="font-num">{c.paperIds.length}</span> papers in this collection
                      cover the strain
                    </div>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {hits.slice(0, 6).map((id) => (
                        <CitationChip key={id} paperId={id} />
                      ))}
                      {hits.length > 6 && (
                        <span className="text-caption text-ink-soft font-num self-center">
                          +{hits.length - 6}
                        </span>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
            <div className="mt-3 pt-2 border-t border-line text-caption text-ink-soft flex flex-wrap items-center gap-2">
              <BookOpen size={13} />
              <span>
                <span className="font-num text-ink">{strainPapers.length}</span> paper
                {strainPapers.length === 1 ? '' : 's'} list this organism
              </span>
              <a className="text-accent hover:underline" href={href('/trawl')}>
                Open the library
              </a>
              <span className="w-full text-ink-soft">
                Collection membership is filtered inside the library, not by this link.
              </span>
            </div>
          </Card>
        </div>
      </section>

      {/* ── BAND 4 — curator notes ─────────────────────────────────────── */}
      <section className="mb-4" aria-labelledby="band-notes">
        <SectionTitle>
          <span id="band-notes">Curator notes</span>
        </SectionTitle>
        <p className="text-caption text-ink-soft mb-2 max-w-3xl">
          Free text written by the corpus curator. Not extracted, not scored — hand-authored bench
          judgement, carried with the gold tick because a person put their name on it.
        </p>
        <Card className="p-4">
          {strain.notes.length === 0 ? (
            <EmptyState
              icon={<NotebookPen size={22} />}
              title="No curator notes for this strain"
              body="Notes are authored alongside the seeded corpus; this strain has none. The parameter summary above is the whole of what the platform knows about it."
            />
          ) : (
            <ul className="space-y-4">
              {[...strain.notes]
                .sort((a, b) => b.at.localeCompare(a.at))
                .map((n) => (
                  <li key={`${n.at}-${n.who}`}>
                    <Tick p="gold" title="Curator-authored note">
                      <div className="text-caption text-ink-soft">
                        <span className="font-num">{n.at}</span> · {n.who}
                      </div>
                      <p className="font-serif text-reading mt-1">{n.text}</p>
                    </Tick>
                  </li>
                ))}
            </ul>
          )}
        </Card>
      </section>

      {points.length > 0 && (
        <Callout kind="info" title="What this page is claiming">
          Every number above is a summary of{' '}
          <span className="font-num">{points.length}</span> extraction record
          {points.length === 1 ? '' : 's'} drawn from{' '}
          <span className="font-num">{strainPapers.length}</span> catalogued paper
          {strainPapers.length === 1 ? '' : 's'} — real, citable sources, but most records are
          transcribed from the curation document and not yet checked against the source PDF. Medians
          over a handful of records are descriptions of this corpus, not of the published literature.{' '}
          <a className="text-accent hover:underline" href={href('/ledger/records')}>
            Open the full extraction table
          </a>{' '}
          to audit the rows behind them.
        </Callout>
      )}

      {points.length > 0 && verifiedTotal === 0 && (
        <div className="mt-3">
          <Callout kind="warn" title="Nothing here has been reviewed">
            All <span className="font-num">{points.length}</span> records for this strain are
            unverified extractions.{' '}
            <button
              className="text-accent hover:underline"
              onClick={() =>
                queueReview(
                  points.filter((p) => p.rec.status === 'unverified').map((p) => p.rec.id),
                  'all fields',
                )
              }
            >
              <ClipboardCheck size={12} className="inline align-[-2px]" /> Queue them all for review
            </button>
            .
          </Callout>
        </div>
      )}
    </>
  );
}
