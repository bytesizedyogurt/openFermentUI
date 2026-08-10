// Protocol library (OF-DES-001 §8.10) — a filterable card grid over the seeded
// protocols, with a table view for scanning. Filter state lives in this screen
// rather than inside DataTable, so switching between card and table view
// preserves exactly what the user has narrowed to.
import { useEffect, useMemo, useState } from 'react';
import {
  Beaker,
  Calculator,
  ClipboardList,
  Container,
  Filter as FilterIcon,
  FlaskConical,
  LayoutGrid,
  Microscope,
  Play,
  Scaling,
  Search,
  SlidersHorizontal,
  Table2,
  Timer,
  X,
} from 'lucide-react';
import type {
  ExtractionRecord,
  Protocol,
  ProtocolCategory,
  ProtocolVersion,
  Strain,
} from '@/data/types';
import { useStore, provenanceOf } from '@/store';
import { href, navigate } from '@/router';
import { DataTable, type Column } from '@/components/DataTable';
import { Tick, ProvenanceLegend, type ProvKind } from '@/components/Provenance';
import {
  Button,
  Card,
  EmptyState,
  LinkButton,
  PageHeader,
  Popover,
  Skeleton,
  cx,
} from '@/components/ui';
import { delayClass } from '@/sim/latency';

// ── Category vocabulary (shared with ProtocolDetail) ───────────────────

export const CATEGORY_META: Record<
  ProtocolCategory,
  { label: string; Icon: typeof Beaker; blurb: string }
> = {
  media: { label: 'Media', Icon: Beaker, blurb: 'Recipes and buffer preparation' },
  culture: { label: 'Culture', Icon: FlaskConical, blurb: 'Seed trains and maintenance' },
  fermentation: { label: 'Fermentation', Icon: Container, blurb: 'Reactor and photobioreactor operation' },
  analytics: { label: 'Analytics', Icon: Microscope, blurb: 'Measurement and assay' },
  harvest: { label: 'Harvest', Icon: FilterIcon, blurb: 'Recovery and downstream' },
  sop: { label: 'SOP', Icon: ClipboardList, blurb: 'Standing operating procedure' },
};

export const CATEGORY_ORDER: ProtocolCategory[] = [
  'media',
  'culture',
  'fermentation',
  'analytics',
  'harvest',
  'sop',
];

// ── Derived capabilities ───────────────────────────────────────────────

export interface Capabilities {
  scalable: boolean;
  timed: boolean;
  calculator: boolean;
  scalableCount: number;
  timedCount: number;
  stockCount: number;
  calcStepCount: number;
}

/**
 * Steps that ask the operator to work a number out rather than read one off.
 * Matches a `{{stock:…}}` binding (an explicit stock-solution computation) or
 * the arithmetic verbs the seeded protocols use: calculat*, dilut*, inocul*,
 * "adjust to", "make up to".
 */
const CALC_TEXT_RE = /\{\{stock:|\b(?:calculat|dilut|inocul)|\b(?:adjust|make up) to\b/i;

/**
 * Capability icons are DERIVED FROM PROTOCOL CONTENT — never hand-set on a
 * protocol record. Exact rules, evaluated against the version being shown:
 *
 *   scalable   — at least one material declares a `scaling` class other than
 *                'fixed', so changing the batch size moves a real quantity.
 *   timed      — at least one step declares `timerSec`, so Run Mode can put a
 *                real countdown on the bench.
 *   calculator — either (a) at least one material declares a `.stock`
 *                concentration, which forces stock-solution volume math, or
 *                (b) at least one step's RAW text (before quantity binding)
 *                matches CALC_TEXT_RE above. Raw text is used deliberately:
 *                a `{{stock:…}}` binding is the strongest signal that a
 *                calculation is happening, and it disappears once rendered.
 */
export function capabilitiesOf(version: ProtocolVersion): Capabilities {
  const scalableCount = version.materials.filter((m) => m.scaling !== 'fixed').length;
  const timedCount = version.steps.filter((s) => s.timerSec !== undefined).length;
  const stockCount = version.materials.filter((m) => !!m.stock).length;
  const calcStepCount = version.steps.filter((s) => CALC_TEXT_RE.test(s.text)).length;
  return {
    scalable: scalableCount > 0,
    timed: timedCount > 0,
    calculator: stockCount > 0 || calcStepCount > 0,
    scalableCount,
    timedCount,
    stockCount,
    calcStepCount,
  };
}

export type CapabilityKey = 'scalable' | 'timed' | 'calculator';

export const CAPABILITY_META: Record<
  CapabilityKey,
  { label: string; Icon: typeof Scaling; facet: string }
> = {
  scalable: { label: 'Scales', Icon: Scaling, facet: 'Scales with batch size' },
  timed: { label: 'Timed', Icon: Timer, facet: 'Has bench timers' },
  calculator: { label: 'Calculation', Icon: Calculator, facet: 'Needs a calculation' },
};

export function capabilityKeys(c: Capabilities): CapabilityKey[] {
  const out: CapabilityKey[] = [];
  if (c.scalable) out.push('scalable');
  if (c.timed) out.push('timed');
  if (c.calculator) out.push('calculator');
  return out;
}

/** Why each icon is lit, in the operator's words — used as the chip tooltip. */
export function capabilityReason(key: CapabilityKey, c: Capabilities): string {
  if (key === 'scalable')
    return `Computed: ${c.scalableCount} material${c.scalableCount === 1 ? '' : 's'} scale with batch size.`;
  if (key === 'timed')
    return `Computed: ${c.timedCount} step${c.timedCount === 1 ? '' : 's'} declare a timer.`;
  const parts: string[] = [];
  if (c.stockCount > 0)
    parts.push(`${c.stockCount} material${c.stockCount === 1 ? '' : 's'} prepared from a stock solution`);
  if (c.calcStepCount > 0)
    parts.push(`${c.calcStepCount} step${c.calcStepCount === 1 ? '' : 's'} ask for a calculation`);
  return `Computed: ${parts.join('; ')}.`;
}

// ── Derived provenance ─────────────────────────────────────────────────

/**
 * The strongest provenance among a set of cited records and papers. Anything
 * citing nothing at all has no literature ancestry, so it is demo data and
 * gets the dashed tick (§20).
 */
export function provenanceFromRefs(
  recordIds: Iterable<string>,
  paperIds: Iterable<string>,
  records: ExtractionRecord[],
): ProvKind {
  const resolved: ExtractionRecord[] = [];
  let cited = 0;
  for (const id of recordIds) {
    cited++;
    const rec = records.find((r) => r.id === id);
    if (rec) resolved.push(rec);
  }
  for (const _ of paperIds) cited++;
  if (resolved.some((r) => provenanceOf(r) === 'gold')) return 'gold';
  if (resolved.some((r) => provenanceOf(r) === 'verified')) return 'verified';
  return cited > 0 ? 'unverified' : 'demo';
}

/** A protocol version's provenance: everything its materials and steps cite. */
export function protocolProvenance(version: ProtocolVersion, records: ExtractionRecord[]): ProvKind {
  const recordIds = new Set<string>();
  const paperIds = new Set<string>();
  for (const m of version.materials) if (m.sourceRecordId) recordIds.add(m.sourceRecordId);
  for (const r of version.references) {
    if (r.recordId) recordIds.add(r.recordId);
    if (r.paperId) paperIds.add(r.paperId);
  }
  for (const s of version.steps)
    for (const ref of s.refs ?? []) (ref.startsWith('ex-') ? recordIds : paperIds).add(ref);
  return provenanceFromRefs(recordIds, paperIds, records);
}

// ── Small shared formatters ────────────────────────────────────────────

export function fmtMinutes(min: number): string {
  if (!isFinite(min) || min < 0) return '—';
  if (min < 60) return `${Math.round(min)} min`;
  const h = Math.floor(min / 60);
  const m = Math.round(min % 60);
  return m === 0 ? `${h} h` : `${h} h ${m} min`;
}

export function strainLabel(id: string, strains: Strain[]): { label: string; title: string } {
  const s = strains.find((x) => x.id === id);
  if (!s) return { label: id, title: `${id} — not a seeded strain in this session` };
  return { label: s.designation, title: `${s.binomial} ${s.designation} · BSL-${s.bsl}` };
}

// ── Row model ──────────────────────────────────────────────────────────

interface ProtoRow {
  protocol: Protocol;
  version: ProtocolVersion;
  caps: Capabilities;
  prov: ProvKind;
  runCount: number;
}

type FacetKey = 'category' | 'organism' | 'capability';

interface FacetGroup {
  key: FacetKey;
  label: string;
  options: { value: string; label: string; title?: string; count: number }[];
}

const EMPTY_SELECTION: Record<FacetKey, string[]> = { category: [], organism: [], capability: [] };

function valuesOf(row: ProtoRow, key: FacetKey): string[] {
  if (key === 'category') return [row.protocol.category];
  if (key === 'organism') return row.protocol.organisms;
  return capabilityKeys(row.caps);
}

// ── Facet panel (shared by the card and table views) ────────────────────

function FacetPanel({
  groups,
  selection,
  onToggle,
  onClear,
}: {
  groups: FacetGroup[];
  selection: Record<FacetKey, string[]>;
  onToggle: (key: FacetKey, value: string) => void;
  onClear: () => void;
}) {
  const anyActive = Object.values(selection).some((v) => v.length > 0);
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <div className="text-caption uppercase tracking-wide text-ink-soft">Filters</div>
        {anyActive && (
          <button className="text-caption text-accent hover:underline" onClick={onClear}>
            Clear
          </button>
        )}
      </div>
      <div className="space-y-4">
        {groups.map((g) => (
          <div key={g.key}>
            <div className="text-caption font-medium mb-1">{g.label}</div>
            <div className="space-y-0.5">
              {g.options.map((o) => {
                const on = selection[g.key].includes(o.value);
                return (
                  <button
                    key={o.value}
                    onClick={() => onToggle(g.key, o.value)}
                    title={o.title}
                    aria-pressed={on}
                    className={cx(
                      'w-full flex items-center justify-between gap-2 px-1.5 py-[3px] rounded-input text-left text-caption',
                      on ? 'bg-accent-wash text-ink font-medium' : 'hover:bg-ink-soft/[0.08] text-ink-soft',
                      o.count === 0 && !on && 'opacity-45',
                    )}
                  >
                    <span className="truncate">{o.label}</span>
                    <span className="font-num text-[11px] shrink-0">{o.count}</span>
                  </button>
                );
              })}
              {g.options.length === 0 && <div className="text-caption text-ink-soft">—</div>}
            </div>
          </div>
        ))}
      </div>
      <p className="text-caption text-ink-soft mt-4 pt-3 border-t border-line">
        Capabilities are computed from protocol content — materials that scale, steps that declare
        timers, and stock-solution or dilution math.
      </p>
    </div>
  );
}

// ── Capability chips ───────────────────────────────────────────────────

function CapabilityChips({ caps }: { caps: Capabilities }) {
  const keys = capabilityKeys(caps);
  if (keys.length === 0)
    return (
      <span className="text-caption text-ink-soft" title="No scaling, timers, or calculations declared">
        Fixed procedure
      </span>
    );
  return (
    <span className="flex items-center gap-1">
      {keys.map((k) => {
        const { Icon, label } = CAPABILITY_META[k];
        return (
          <span key={k} className="chip text-caption text-ink-soft" title={capabilityReason(k, caps)}>
            <Icon size={11} aria-hidden />
            {label}
          </span>
        );
      })}
    </span>
  );
}

// ── Card ───────────────────────────────────────────────────────────────

function ProtocolCard({ row, strains }: { row: ProtoRow; strains: Strain[] }) {
  const { protocol, version, caps, prov } = row;
  const meta = CATEGORY_META[protocol.category];
  const Glyph = meta.Icon;
  return (
    <Card className="overflow-hidden">
      <Tick p={prov} className="h-full flex flex-col gap-2 py-3 pr-3">
        <div className="flex items-start gap-2.5">
          <span
            className="w-8 h-8 rounded-btn border border-line bg-surface-0 grid place-items-center shrink-0 text-ink-soft"
            title={`${meta.label} — ${meta.blurb}`}
          >
            <Glyph size={16} aria-hidden />
          </span>
          <div className="min-w-0 flex-1">
            <a
              href={href(`/protocols/${protocol.id}`)}
              className="font-serif text-section-title font-semibold leading-snug hover:text-accent hover:underline block"
            >
              {protocol.title}
            </a>
            <div className="text-caption text-ink-soft font-num mt-0.5">
              {protocol.id} · {meta.label}
            </div>
          </div>
          <span
            className="chip font-num text-caption shrink-0"
            title={`Current version · ${protocol.versions.length} version${protocol.versions.length === 1 ? '' : 's'} on file`}
          >
            v{version.version}
          </span>
        </div>

        <p className="text-body text-ink-soft line-clamp-2">{protocol.purpose}</p>

        <div className="flex flex-wrap items-center gap-1">
          {protocol.organisms.length === 0 && (
            <span className="text-caption text-ink-soft">Organism-independent</span>
          )}
          {protocol.organisms.map((o) => {
            const s = strainLabel(o, strains);
            return (
              <a
                key={o}
                href={href(`/organisms/${o}`)}
                className="chip text-caption text-ink-soft hover:border-accent/40 hover:bg-accent-wash"
                title={s.title}
              >
                {s.label}
              </a>
            );
          })}
          <span className="chip text-caption text-ink-soft" title={`Biosafety level ${protocol.bsl}`}>
            BSL-<span className="font-num">{protocol.bsl}</span>
          </span>
        </div>

        <div className="text-caption text-ink-soft font-num">
          {version.steps.length} steps · {fmtMinutes(version.estMinutes.active)} active ·{' '}
          {fmtMinutes(version.estMinutes.total)} total
        </div>

        <div className="mt-auto pt-2 flex items-center justify-between gap-2 border-t border-line">
          <CapabilityChips caps={caps} />
          <div className="flex items-center gap-2 shrink-0">
            {row.runCount > 0 && (
              <a
                href={href(`/protocols/${protocol.id}`)}
                className="text-caption text-ink-soft hover:text-accent font-num"
                title="Runs recorded in this session"
              >
                {row.runCount} run{row.runCount === 1 ? '' : 's'}
              </a>
            )}
            <LinkButton to={`/protocols/${protocol.id}`} variant="primary" size="sm">
              Open
            </LinkButton>
          </div>
        </div>
      </Tick>
    </Card>
  );
}

// ── Screen ─────────────────────────────────────────────────────────────

export default function Protocols() {
  const protocols = useStore((s) => s.protocols);
  const records = useStore((s) => s.records);
  const strains = useStore((s) => s.strains);
  const runs = useStore((s) => s.runs);
  const density = useStore((s) => s.ui.density);

  const [ready, setReady] = useState(false);
  const [view, setView] = useState<'cards' | 'table'>('cards');
  const [query, setQuery] = useState('');
  const [selection, setSelection] = useState<Record<FacetKey, string[]>>(EMPTY_SELECTION);

  // Simulated first-paint latency (§13.5) so the loading state is a real state.
  useEffect(() => {
    let alive = true;
    delayClass('quick').then(() => {
      if (alive) setReady(true);
    });
    return () => {
      alive = false;
    };
  }, []);

  const allRows = useMemo<ProtoRow[]>(() => {
    const runCounts = new Map<string, number>();
    for (const r of Object.values(runs))
      runCounts.set(r.protocolId, (runCounts.get(r.protocolId) ?? 0) + 1);
    return protocols.map((protocol) => {
      const version =
        protocol.versions.find((v) => v.version === protocol.currentVersion) ?? protocol.versions[0];
      return {
        protocol,
        version,
        caps: capabilitiesOf(version),
        prov: protocolProvenance(version, records),
        runCount: runCounts.get(protocol.id) ?? 0,
      };
    });
  }, [protocols, records, runs]);

  const matchesQuery = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (row: ProtoRow) =>
      q === '' ||
      `${row.protocol.id} ${row.protocol.title} ${row.protocol.purpose} ${row.protocol.organisms.join(' ')} ${CATEGORY_META[row.protocol.category].label}`
        .toLowerCase()
        .includes(q);
  }, [query]);

  /** Rows passing every facet except `except` — the basis for honest counts. */
  const passing = useMemo(() => {
    const test = (row: ProtoRow, except: FacetKey | null) =>
      (['category', 'organism', 'capability'] as FacetKey[]).every((k) => {
        if (k === except) return true;
        const sel = selection[k];
        if (sel.length === 0) return true;
        return valuesOf(row, k).some((v) => sel.includes(v));
      }) && matchesQuery(row);
    return test;
  }, [selection, matchesQuery]);

  const rows = useMemo(() => allRows.filter((r) => passing(r, null)), [allRows, passing]);

  const groups = useMemo<FacetGroup[]>(() => {
    const build = (key: FacetKey): FacetGroup => {
      const pool = allRows.filter((r) => passing(r, key));
      const counts = new Map<string, number>();
      for (const row of pool) for (const v of valuesOf(row, key)) counts.set(v, (counts.get(v) ?? 0) + 1);
      // Every value that exists anywhere is listed, so a zero count reads as
      // "this filter would empty the view" rather than silently vanishing.
      const universe = new Set<string>();
      for (const row of allRows) for (const v of valuesOf(row, key)) universe.add(v);
      for (const v of selection[key]) universe.add(v);

      let options = [...universe].map((value) => ({
        value,
        label: value,
        title: undefined as string | undefined,
        count: counts.get(value) ?? 0,
      }));

      if (key === 'category') {
        options = options
          .map((o) => ({
            ...o,
            label: CATEGORY_META[o.value as ProtocolCategory]?.label ?? o.value,
            title: CATEGORY_META[o.value as ProtocolCategory]?.blurb,
          }))
          .sort(
            (a, b) =>
              CATEGORY_ORDER.indexOf(a.value as ProtocolCategory) -
              CATEGORY_ORDER.indexOf(b.value as ProtocolCategory),
          );
      } else if (key === 'organism') {
        options = options
          .map((o) => {
            const s = strainLabel(o.value, strains);
            return { ...o, label: s.label, title: s.title };
          })
          .sort((a, b) => b.count - a.count || a.label.localeCompare(b.label));
      } else {
        const order: CapabilityKey[] = ['scalable', 'timed', 'calculator'];
        options = options
          .map((o) => ({ ...o, label: CAPABILITY_META[o.value as CapabilityKey]?.facet ?? o.value }))
          .sort(
            (a, b) => order.indexOf(a.value as CapabilityKey) - order.indexOf(b.value as CapabilityKey),
          );
      }
      return {
        key,
        label: key === 'category' ? 'Category' : key === 'organism' ? 'Organism' : 'Capability',
        options,
      };
    };
    return [build('category'), build('organism'), build('capability')];
  }, [allRows, passing, selection, strains]);

  const toggleFacet = (key: FacetKey, value: string) =>
    setSelection((s) => ({
      ...s,
      [key]: s[key].includes(value) ? s[key].filter((v) => v !== value) : [...s[key], value],
    }));

  const clearFilters = () => {
    setSelection(EMPTY_SELECTION);
    setQuery('');
  };

  const activeChips = useMemo(() => {
    const out: { key: FacetKey; value: string; label: string }[] = [];
    for (const g of groups)
      for (const v of selection[g.key])
        out.push({ key: g.key, value: v, label: g.options.find((o) => o.value === v)?.label ?? v });
    return out;
  }, [groups, selection]);

  const anyFilter = activeChips.length > 0 || query.trim() !== '';

  // ── table columns ────────────────────────────────────────────────────
  const columns: Column<ProtoRow>[] = [
    {
      key: 'id',
      header: 'ID',
      width: '96px',
      priority: 1,
      render: (r) => (
        <a
          href={href(`/protocols/${r.protocol.id}`)}
          className="font-num text-accent hover:underline"
          onClick={(e) => e.stopPropagation()}
        >
          {r.protocol.id}
        </a>
      ),
      value: (r) => r.protocol.id,
    },
    {
      key: 'title',
      header: 'Protocol',
      priority: 1,
      render: (r) => (
        <a
          href={href(`/protocols/${r.protocol.id}`)}
          className="font-serif hover:text-accent hover:underline block truncate"
          style={{ maxWidth: 320 }}
          title={r.protocol.purpose}
          onClick={(e) => e.stopPropagation()}
        >
          {r.protocol.title}
        </a>
      ),
      value: (r) => r.protocol.title,
    },
    {
      key: 'category',
      header: 'Category',
      width: '124px',
      priority: 2,
      render: (r) => {
        const m = CATEGORY_META[r.protocol.category];
        const Icon = m.Icon;
        return (
          <span className="inline-flex items-center gap-1.5 text-ink-soft" title={m.blurb}>
            <Icon size={13} aria-hidden />
            {m.label}
          </span>
        );
      },
      value: (r) => CATEGORY_META[r.protocol.category].label,
    },
    {
      key: 'organisms',
      header: 'Organisms',
      width: '140px',
      priority: 2,
      render: (r) =>
        r.protocol.organisms.length === 0 ? (
          <span className="text-ink-soft">—</span>
        ) : (
          <span className="flex flex-nowrap gap-1 overflow-hidden">
            {r.protocol.organisms.slice(0, 2).map((o) => {
              const s = strainLabel(o, strains);
              return (
                <span key={o} className="chip text-caption text-ink-soft" title={s.title}>
                  {s.label}
                </span>
              );
            })}
            {r.protocol.organisms.length > 2 && (
              <span className="text-caption text-ink-soft font-num">
                +{r.protocol.organisms.length - 2}
              </span>
            )}
          </span>
        ),
      value: (r) => r.protocol.organisms.join('; '),
    },
    {
      key: 'version',
      header: 'Version',
      width: '76px',
      priority: 2,
      render: (r) => <span className="font-num">v{r.version.version}</span>,
      value: (r) => r.version.version,
    },
    {
      key: 'steps',
      header: 'Steps',
      width: '64px',
      numeric: true,
      priority: 2,
      render: (r) => <span className="font-num">{r.version.steps.length}</span>,
      value: (r) => r.version.steps.length,
    },
    {
      key: 'active',
      header: 'Active',
      headerUnit: 'min',
      width: '72px',
      numeric: true,
      priority: 3,
      render: (r) => <span className="font-num">{r.version.estMinutes.active}</span>,
      value: (r) => r.version.estMinutes.active,
    },
    {
      key: 'total',
      header: 'Total',
      headerUnit: 'min',
      width: '72px',
      numeric: true,
      priority: 3,
      render: (r) => <span className="font-num">{r.version.estMinutes.total}</span>,
      value: (r) => r.version.estMinutes.total,
    },
    {
      key: 'capabilities',
      header: 'Capabilities',
      width: '210px',
      priority: 2,
      sortable: false,
      render: (r) => <CapabilityChips caps={r.caps} />,
      value: (r) => capabilityKeys(r.caps).join('; ') || 'none',
    },
    {
      key: 'runs',
      header: 'Runs',
      width: '64px',
      numeric: true,
      priority: 3,
      render: (r) => (
        <span className={cx('font-num', r.runCount === 0 && 'text-ink-soft')}>{r.runCount}</span>
      ),
      value: (r) => r.runCount,
    },
  ];

  const header = (
    <PageHeader
      title="Protocols"
      subtitle={
        <>
          Executable bench procedures whose quantities are bound to materials, so a batch-size change
          rewrites every number. <span className="font-num">{allRows.length}</span> protocols across{' '}
          <span className="font-num">{allRows.reduce((n, r) => n + r.protocol.versions.length, 0)}</span>{' '}
          versions. Capability icons are computed from content, never declared.
        </>
      }
      actions={
        <div className="flex items-center gap-1 rounded-btn border border-line p-0.5" role="group" aria-label="View">
          <button
            className={cx(
              'btn btn-sm border-0',
              view === 'cards' ? 'bg-accent-wash text-accent' : 'bg-transparent text-ink-soft',
            )}
            aria-pressed={view === 'cards'}
            onClick={() => setView('cards')}
            title="Card grid"
          >
            <LayoutGrid size={13} /> Cards
          </button>
          <button
            className={cx(
              'btn btn-sm border-0',
              view === 'table' ? 'bg-accent-wash text-accent' : 'bg-transparent text-ink-soft',
            )}
            aria-pressed={view === 'table'}
            onClick={() => setView('table')}
            title="Table view — keeps the current filters"
          >
            <Table2 size={13} /> Table
          </button>
        </div>
      }
    />
  );

  if (!ready) {
    return (
      <>
        {header}
        <div className="grid grid-cols-1 md:grid-cols-2 2xl:grid-cols-3 gap-3">
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <Card key={i}>
              <Skeleton rows={4} />
            </Card>
          ))}
        </div>
        <div className="sr-only" aria-live="polite">
          Loading protocols
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
            title="No protocols in this session"
            body="The protocol set is empty. Restore the seeded demo data from the corpus settings to bring the bench procedures back."
            icon={<ClipboardList size={22} />}
            action={<LinkButton to="/settings/corpus">Open corpus settings</LinkButton>}
          />
        </Card>
      </>
    );
  }

  const toolbar = (
    <div className="flex flex-wrap items-center gap-2 mb-3">
      <div className="relative">
        <Search size={13} className="absolute left-2 top-1/2 -translate-y-1/2 text-ink-soft" />
        <input
          className="input pl-7 w-[240px]"
          placeholder="Filter protocols…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Filter protocols by name, id, or organism"
        />
        {query && (
          <button
            className="absolute right-1.5 top-1/2 -translate-y-1/2 text-ink-soft hover:text-ink"
            onClick={() => setQuery('')}
            aria-label="Clear text filter"
          >
            <X size={13} />
          </button>
        )}
      </div>

      <div className="lg:hidden">
        <Popover
          openOnHover={false}
          width={260}
          label="Filters"
          trigger={(p) => (
            <button {...p} className="btn btn-sm">
              <SlidersHorizontal size={13} /> Filters
              {activeChips.length > 0 && <span className="font-num">{activeChips.length}</span>}
            </button>
          )}
        >
          <FacetPanel
            groups={groups}
            selection={selection}
            onToggle={toggleFacet}
            onClear={clearFilters}
          />
        </Popover>
      </div>

      {activeChips.map((c) => (
        <button
          key={`${c.key}:${c.value}`}
          className="chip chip-active"
          onClick={() => toggleFacet(c.key, c.value)}
          title="Remove this filter"
        >
          {c.label}
          <X size={11} />
        </button>
      ))}
      {anyFilter && (
        <button className="text-caption text-accent hover:underline" onClick={clearFilters}>
          Clear all
        </button>
      )}

      <div className="flex-1" />
      <span className="text-caption text-ink-soft font-num">
        {rows.length === allRows.length ? `${allRows.length} protocols` : `${rows.length} of ${allRows.length}`}
      </span>
    </div>
  );

  const nothingMatches = (
    <Card>
      <EmptyState
        title="Nothing matches these filters"
        body={
          activeChips.length > 0
            ? `No protocol satisfies ${activeChips.map((c) => c.label).join(' + ')}${query.trim() ? ` with “${query.trim()}”` : ''}.`
            : `No protocol matches “${query.trim()}”.`
        }
        icon={<FilterIcon size={22} />}
        action={
          <Button onClick={clearFilters}>
            <X size={13} /> Clear filters
          </Button>
        }
      />
    </Card>
  );

  return (
    <>
      {header}
      <div className="flex gap-4 items-start">
        <aside className="w-[196px] shrink-0 hidden lg:block">
          <FacetPanel
            groups={groups}
            selection={selection}
            onToggle={toggleFacet}
            onClear={clearFilters}
          />
        </aside>

        <div className="flex-1 min-w-0">
          {toolbar}

          {rows.length === 0 ? (
            nothingMatches
          ) : view === 'cards' ? (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 2xl:grid-cols-3 gap-3 items-stretch">
                {rows.map((r) => (
                  <ProtocolCard key={r.protocol.id} row={r} strains={strains} />
                ))}
              </div>
              <div className="mt-3">
                <ProvenanceLegend />
              </div>
            </>
          ) : (
            <DataTable<ProtoRow>
              rows={rows}
              columns={columns}
              rowKey={(r) => r.protocol.id}
              tickOf={(r) => r.prov}
              dense={density === 'dense'}
              onOpen={(r) => navigate(`/protocols/${r.protocol.id}`)}
              searchOf={undefined}
              exportName="openferment-protocols"
              exportNote="CSV exports carry the synthetic-data disclosure header. Capability columns are computed from protocol content."
              emptyTitle="Nothing matches these filters"
              emptyBody="Clear a filter above to widen the view."
              maxHeight="calc(100vh - 300px)"
              toolbar={
                <span className="text-caption text-ink-soft inline-flex items-center gap-1.5">
                  <Play size={12} aria-hidden /> Double-click or press Enter to open a protocol
                </span>
              }
            />
          )}
        </div>
      </div>
    </>
  );
}
