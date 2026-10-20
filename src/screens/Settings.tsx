// Settings (OF-DES-001 §8.15) — appearance, units, corpus ownership, the
// export center, and the colophon that tells the truth about this build.
import { useMemo, useState, type ReactNode } from 'react';
import {
  Award,
  Beaker,
  ChartScatter,
  Database,
  Download,
  Gauge,
  Info,
  KeyRound,
  Layers,
  Moon,
  Palette,
  RotateCcw,
  Ruler,
  ShieldCheck,
  Sun,
} from 'lucide-react';
import {
  useStore,
  provenanceOf,
  guildView,
  actingIdOf,
  useProgramFilter,
  type Density,
  type Theme,
  type UnitMode,
} from '@/store';
import { PROGRAMS } from '@/data/programs';
import { policyOf } from '@/engine/competence';
import { Tick } from '@/components/Provenance';
import {
  Bar,
  Button,
  Callout,
  Card,
  Explain,
  LinkButton,
  Modal,
  PageHeader,
  SectionTitle,
  cx,
} from '@/components/ui';
import { DataTable, type Column } from '@/components/DataTable';
import { FiguresSection } from './SettingsFigures';
import { QuantityField, Quantity, type QuantityValue } from '@/components/QuantityField';
import { ONTOLOGY, ONTOLOGY_BY_ID, fieldName } from '@/data/ontology';
import type { FieldId, GateMode, GuildPolicy, ParameterDef } from '@/data/types';
import { convert, fmt, toSI } from '@/engine/units';
import { DISCLOSURE, exportCSV } from '@/lib/csv';

// Seed counts are captured once, at module load, before any session edit — so
// the reset confirmation describes what will actually be restored.
const SEEDED = (() => {
  const s = useStore.getState();
  return {
    records: s.records.length,
    protocols: s.protocols.length,
    scenarios: s.scenarios.length,
  };
})();

const APP_VERSION = '0.1.0';

interface SectionDef {
  id: string;
  label: string;
  blurb: string;
  owner?: boolean;
}

const SECTIONS: SectionDef[] = [
  {
    id: 'appearance',
    label: 'Appearance',
    blurb: 'Theme, density, motion and the rehearsal clock. Changes apply immediately.',
  },
  {
    id: 'programs',
    label: 'Programs',
    blurb:
      'The research programs the corpus serves, which are active and which archived, and the one switch that shows archived programs again.',
  },
  {
    id: 'units',
    label: 'Units & display',
    blurb:
      'Choose how quantities are shown, and inspect the 24-field parameter ontology every number is validated against.',
  },
  {
    id: 'architecture',
    label: 'Architecture',
    blurb:
      'The eighteen named components and the seven layers they sit in — the map the system is built from.',
  },
  {
    id: 'corpus',
    label: 'Corpus & ontology',
    blurb: 'Owner controls: the ontology reference, the gold set, and clearing this browser’s data.',
    owner: true,
  },
  {
    id: 'guild',
    label: 'Guild policy',
    blurb:
      'How the run-mode gate treats routine and critical skills, and how often each holder of a critical skill is checked. Set by the lead, kept by the service for every device.',
    owner: true,
  },
  {
    id: 'figures',
    label: 'Figure grammar',
    blurb:
      'How every chart draws results and predictions: the mark for each kind of thing, the stroke for each provenance, and a table behind every figure. Drawn over the newest computed results the service keeps, or by its legend alone.',
  },
  {
    id: 'export',
    label: 'Export center',
    blurb: 'Everything you have exported this session, and what is deliberately not wired up.',
  },
  {
    id: 'about',
    label: 'About & fidelity',
    blurb: 'What is real in this build, what follows an authored timeline, and what is only a surface.',
  },
];

// ── small shared controls ──────────────────────────────────────────────

function RadioCards<T extends string | number>({
  name,
  label,
  value,
  onChange,
  options,
  className,
}: {
  name: string;
  label: string;
  value: T;
  onChange: (v: T) => void;
  options: { value: T; label: string; desc?: string; preview?: ReactNode }[];
  className?: string;
}) {
  return (
    <div role="radiogroup" aria-label={label} className={cx('grid gap-2', className)}>
      {options.map((o) => {
        const on = o.value === value;
        return (
          <label
            key={String(o.value)}
            className={cx(
              'card p-3 flex items-start gap-2.5 cursor-pointer transition-colors',
              on ? 'border-accent bg-accent-wash' : 'hover:border-accent/40',
            )}
          >
            <input
              type="radio"
              name={name}
              className="mt-1 shrink-0"
              checked={on}
              onChange={() => onChange(o.value)}
            />
            <span className="min-w-0">
              <span className="block text-body font-medium">{o.label}</span>
              {o.desc && <span className="block text-caption text-ink-soft mt-0.5">{o.desc}</span>}
              {o.preview && <span className="block mt-2">{o.preview}</span>}
            </span>
          </label>
        );
      })}
    </div>
  );
}

// ── Guild policy (OF-BLD-013 §5.1) ──────────────────────────────────────

function GuildPolicySection() {
  const ledger = useStore((s) => guildView(s));
  const actingId = useStore((s) => actingIdOf(s));
  const save = useStore((s) => s.guildSetPolicy);
  const current = policyOf(ledger);
  // Only what the lead has changed is held here; every other field reads the
  // stored policy, so a ledger that arrives after this mounts is shown as it
  // is, and a save never sends back a default nobody chose (§5.5).
  const [edits, setEdits] = useState<Partial<Pick<GuildPolicy, 'routineGate' | 'criticalGate' | 'checksPerQuarter'>>>({});
  const routineGate = edits.routineGate ?? current.routineGate;
  const criticalGate = edits.criticalGate ?? current.criticalGate;
  const checksPerQuarter = edits.checksPerQuarter ?? current.checksPerQuarter;
  const setRoutine = (v: GateMode) => setEdits((e) => ({ ...e, routineGate: v }));
  const setCritical = (v: GateMode) => setEdits((e) => ({ ...e, criticalGate: v }));
  const setRate = (v: number) => setEdits((e) => ({ ...e, checksPerQuarter: v }));
  const lead = ledger.people.find((p) => p.id === actingId && p.active && p.role === 'lead') ?? null;
  const by = ledger.people.find((p) => p.id === current.updatedBy)?.name;
  const changed =
    routineGate !== current.routineGate || criticalGate !== current.criticalGate || checksPerQuarter !== current.checksPerQuarter;
  const MODES: { value: GateMode; label: string; desc: string }[] = [
    { value: 'advise', label: 'Advise', desc: 'The gate says what the step needs and lets it complete; a step done without that level is written as a deviation.' },
    { value: 'enforce', label: 'Enforce', desc: 'The step waits until a cosigner who holds the skill is recorded, or someone qualified takes over.' },
  ];
  return (
    <div className="space-y-6 max-w-2xl">
      {ledger.people.length === 0 && (
        <p className="text-body text-ink-soft">
          Nobody is on Guild&rsquo;s ledger yet, so the gate holds nothing. The first person added is the lead, who sets these.
        </p>
      )}
      <section>
        <h2 className="font-serif text-section-title font-semibold mb-2">Critical skills</h2>
        <RadioCards name="critical-gate" label="Gate on critical skills" value={criticalGate} onChange={setCritical} options={MODES} />
      </section>
      <section>
        <h2 className="font-serif text-section-title font-semibold mb-2">Routine skills</h2>
        <RadioCards name="routine-gate" label="Gate on routine skills" value={routineGate} onChange={setRoutine} options={MODES} />
      </section>
      <section>
        <h2 className="font-serif text-section-title font-semibold mb-2">Checks on critical skills</h2>
        <label className="flex flex-wrap items-center gap-3 text-body">
          <span>Witnessed checks each holder gets, at least, every quarter</span>
          <input
            type="number"
            min={0}
            max={12}
            step={1}
            className="input w-20 font-num"
            value={checksPerQuarter}
            onChange={(e) => setRate(Math.max(0, Math.min(12, Math.round(Number(e.target.value) || 0))))}
            aria-label="Witnessed checks per quarter"
          />
        </label>
        <p className="text-caption text-ink-soft mt-1">Fewer than this puts the holder in the assessors&rsquo; queue of proposed checks.</p>
      </section>
      <div className="flex flex-wrap items-center gap-3">
        <Button variant="primary" disabled={!lead || !changed} onClick={async () => {
            if (await save({ routineGate, criticalGate, checksPerQuarter })) setEdits({});
          }}>
          Save the policy
        </Button>
        <span className="text-caption text-ink-soft">
          {lead ? `Saved as ${lead.name}, the lead.` : 'Only the lead changes these. Choose who you are with Acting as in Guild.'}
          {current.updatedAt && by && ` Last set by ${by} on ${current.updatedAt.slice(0, 10)}.`}
        </span>
      </div>
    </div>
  );
}

function Swatches({ colors }: { colors: string[] }) {
  return (
    <span className="flex gap-1" aria-hidden>
      {colors.map((c) => (
        <span
          key={c}
          className="w-5 h-5 rounded-input border border-line"
          style={{ background: c }}
        />
      ))}
    </span>
  );
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5 py-1.5 border-b border-line last:border-0">
      <div className="text-caption uppercase tracking-wide text-ink-soft w-[168px] shrink-0">
        {label}
      </div>
      <div className="text-body min-w-0 flex-1">{children}</div>
    </div>
  );
}

// ── appearance ─────────────────────────────────────────────────────────

function AppearanceSection() {
  const theme = useStore((s) => s.ui.theme);
  const density = useStore((s) => s.ui.density);
  const reducedMotion = useStore((s) => s.ui.reducedMotion);
  const simSpeed = useStore((s) => s.ui.simSpeed);
  const setUI = useStore((s) => s.setUI);
  const allRecords = useStore((s) => s.records);
  const shows = useProgramFilter();
  // The preview draws the first records whose program shows (OF-BLD-016 §2.2).
  const records = useMemo(() => allRecords.filter((r) => shows('record', r.id)), [allRecords, shows]);
  const previewRecords = records.slice(0, 3);

  const [systemReduced] = useState(() =>
    typeof window !== 'undefined' && typeof window.matchMedia === 'function'
      ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
      : false,
  );

  return (
    <div className="space-y-6">
      <section>
        <SectionTitle
          right={
            <span className="text-caption text-ink-soft inline-flex items-center gap-1.5">
              <Palette size={13} aria-hidden /> applied live
            </span>
          }
        >
          Theme
        </SectionTitle>
        <RadioCards<Theme>
          name="theme"
          label="Theme"
          value={theme}
          onChange={(v) => setUI({ theme: v })}
          className="sm:grid-cols-2"
          options={[
            {
              value: 'bench',
              label: 'Bench',
              desc: 'Light. Paper-white panels on a faint engineering grid, for daylight lab work.',
              preview: <Swatches colors={['#F4F6F3', '#FFFFFF', '#2E6B4F', '#B07C22', '#1C221E']} />,
            },
            {
              value: 'night',
              label: 'Night Shift',
              desc: 'Dark. Same hierarchy at lower luminance, for fermentation halls and late runs.',
              preview: <Swatches colors={['#101613', '#171E1A', '#6FAE8F', '#D3A24C', '#E6EBE7']} />,
            },
          ]}
        />
      </section>

      <section>
        <SectionTitle>Density</SectionTitle>
        <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_260px] items-start">
          <RadioCards<Density>
            name="density"
            label="Density"
            value={density}
            onChange={(v) => setUI({ density: v })}
            className="sm:grid-cols-2"
            options={[
              {
                value: 'comfortable',
                label: 'Comfortable',
                desc: '40px rows, 14px table text. The default for reading and review.',
              },
              {
                value: 'dense',
                label: 'Dense',
                desc: '30px rows, 13px table text. More rows per screen for triage. Shortcut: ⇧D.',
              },
            ]}
          />
          <Card className="p-2">
            <div className="text-caption uppercase tracking-wide text-ink-soft px-1 pb-1">
              Live preview — real records
            </div>
            <table className="w-full" style={{ fontSize: 'var(--table-fs)' }}>
              <tbody>
                {previewRecords.length === 0 ? (
                  <tr>
                    <td
                      colSpan={2}
                      className="px-1 text-caption text-ink-soft"
                      style={{ height: 'var(--row-h)' }}
                    >
                      {allRecords.length > records.length
                        ? 'No values in the active programs yet. Values in archived programs are hidden; Settings → Programs shows them.'
                        : 'No records loaded in this session.'}
                    </td>
                  </tr>
                ) : (
                  previewRecords.map((r) => (
                    <tr key={r.id} className="border-b border-line/70 last:border-0">
                      <td className="px-1" style={{ height: 'var(--row-h)' }}>
                        <Tick p={provenanceOf(r)}>
                          <span className="font-num">{r.id}</span>
                        </Tick>
                      </td>
                      <td className="px-1 font-num text-right whitespace-nowrap">
                        {fmt(r.value)} {r.unit}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </Card>
        </div>
      </section>

      <section>
        <SectionTitle>Motion</SectionTitle>
        <Card className="p-3">
          <label className="flex items-start gap-2.5 cursor-pointer">
            <input
              type="checkbox"
              className="mt-1 shrink-0"
              checked={reducedMotion}
              onChange={(e) => setUI({ reducedMotion: e.target.checked })}
            />
            <span>
              <span className="block text-body font-medium">Reduce motion (override)</span>
              <span className="block text-caption text-ink-soft mt-0.5">
                Collapses every transition and entrance animation to near-zero, on top of your
                system preference. Progress bars, timers and job stages keep updating — only the
                easing disappears.
              </span>
            </span>
          </label>
          <div className="text-caption text-ink-soft mt-2 pt-2 border-t border-line">
            Your system currently requests{' '}
            <span className="font-medium text-ink">
              {systemReduced ? 'reduced motion' : 'no motion preference'}
            </span>
            . That preference is already honoured; this switch forces reduction regardless.
          </div>
        </Card>
      </section>

      <section>
        <SectionTitle
          right={
            <span className="text-caption text-ink-soft inline-flex items-center gap-1.5">
              <Gauge size={13} aria-hidden /> rehearsal clock
            </span>
          }
        >
          Simulation speed
        </SectionTitle>
        <RadioCards<number>
          name="simspeed"
          label="Simulation speed"
          value={simSpeed}
          onChange={(v) => setUI({ simSpeed: v })}
          className="sm:grid-cols-3"
          options={[
            { value: 1, label: '1× — real time', desc: 'Stages and timers run at their authored durations.' },
            { value: 4, label: '4× — rehearsal', desc: 'Four times faster. Useful when walking someone through a flow.' },
            { value: Infinity, label: 'Instant', desc: 'Jobs land immediately; run timers burn at 60× so a soak finishes on stage.' },
          ]}
        />
        <p className="text-caption text-ink-soft mt-2 max-w-3xl">
          This scales <span className="font-medium text-ink">simulated latency only</span> — ingest
          stages, extraction and solver jobs, and Deposition timers. It changes nothing about the
          numbers those steps produce. Whenever the speed is not 1×, the top bar shows a badge so
          nobody watching is misled about how fast the real thing would be.
        </p>
      </section>
    </div>
  );
}

// ── programs (OF-BLD-016 §2.1, §2.2, E.1′) ───────────────────────────────
//
// The programs are data (src/data/programs.ts); this section lists them and
// holds the one switch. Off, the default, an archived program's papers,
// values, strains, molecules, scenarios, protocols, runbooks, lessons and
// suggested questions leave every list, count and prompt; on, everything
// shows as it did before programs existed. Nothing is deleted either way
// (D1), and a link to an archived entity opens it under a banner. The switch
// is in the Durable tier, so it survives a reload and a reset.

/** "threads A to O", "thread Q": a program's letters, written out. */
function lettersLabel(letters: readonly string[]): string {
  const l = [...letters].sort();
  return l.length === 1 ? `thread ${l[0]}` : `threads ${l[0]} to ${l[l.length - 1]}`;
}

function ProgramsSection() {
  const showArchived = useStore((s) => s.showArchived);
  const setShowArchived = useStore((s) => s.setShowArchived);
  const archived = PROGRAMS.filter((p) => p.status === 'archived');

  return (
    <div className="space-y-6" data-testid="settings-programs">
      <section>
        <SectionTitle>Programs</SectionTitle>
        <ul className="space-y-2">
          {PROGRAMS.map((p) => (
            <li key={p.id}>
              <Card className="p-3" data-program={p.id} data-program-status={p.status}>
                <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                  <span className="font-serif text-section-title font-semibold">{p.name}</span>
                  <span className="text-caption uppercase tracking-wide text-ink-soft">
                    {lettersLabel(p.letters)}
                  </span>
                  <span
                    className={cx(
                      'chip text-[11px] py-0',
                      p.status === 'active'
                        ? 'border-accent/40 text-accent'
                        : 'border-line text-ink-soft',
                    )}
                  >
                    {p.status === 'active' ? 'Active' : 'Archived'}
                  </span>
                </div>
                <p className="text-body text-ink-soft mt-1 max-w-3xl">{p.summary}</p>
              </Card>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <SectionTitle>Archived programs and examples</SectionTitle>
        <Card className="p-3">
          <label className="flex items-start gap-2.5 cursor-pointer">
            <input
              type="checkbox"
              role="switch"
              aria-checked={showArchived}
              className="mt-1 shrink-0"
              checked={showArchived}
              onChange={(e) => setShowArchived(e.target.checked)}
              data-testid="show-archived"
            />
            <span>
              <span className="block text-body font-medium">Show archived programs and examples</span>
              <span className="block text-caption text-ink-soft mt-0.5 max-w-3xl">
                When it is off,{' '}
                {archived.length === 0 ? 'nothing is hidden, because no program is archived' : (
                  <>
                    the papers, values, strains, molecules, scenarios, protocols, runbooks, lessons
                    and suggested questions of{' '}
                    {archived.map((p, i) => (
                      <span key={p.id}>
                        {i > 0 && (i === archived.length - 1 ? ' and ' : ', ')}
                        <span className="text-ink">{p.name}</span>
                      </span>
                    ))}{' '}
                    leave every list, count and prompt
                  </>
                )}
                . When it is on, everything shows as before. Nothing is deleted either way, and a
                link to something archived still opens it, under a note that names its program.
              </span>
              <span className="block text-caption text-ink-soft mt-1 max-w-3xl" data-testid="show-archived-examples">
                The same switch shows the examples: the seed runbooks, protocols, scenarios and lessons that
                describe a run nobody made. They are kept to show the shape of a run, never as a record of one.
              </span>
            </span>
          </label>
          <div className="text-caption text-ink-soft mt-2 pt-2 border-t border-line" data-testid="show-archived-state">
            {showArchived
              ? 'Archived programs and examples are showing everywhere. The setting is kept in this browser across reloads.'
              : 'Archived programs and examples are hidden. The setting is kept in this browser across reloads.'}
          </div>
        </Card>
      </section>
    </div>
  );
}

// ── units ──────────────────────────────────────────────────────────────

function defaultFor(def: ParameterDef): QuantityValue {
  const [lo, hi] = def.range;
  const mid = lo + (hi - lo) * 0.3;
  const step = Math.pow(10, Math.floor(Math.log10(mid))) / 10;
  const rounded = Math.max(lo, Math.round(mid / step) * step);
  return { value: Number(rounded.toPrecision(3)), unit: def.canonicalUnit };
}

function UnitsSection() {
  const unitMode = useStore((s) => s.ui.unitMode);
  const setUI = useStore((s) => s.setUI);

  const [field, setField] = useState<FieldId>('growth_rate_mu');
  const [qty, setQty] = useState<QuantityValue>(() => defaultFor(ONTOLOGY_BY_ID.growth_rate_mu));

  const def = ONTOLOGY_BY_ID[field];
  const si = toSI(qty.value, qty.unit);
  let canonical: number | null = null;
  try {
    canonical = def.canonicalUnit === '' ? qty.value : convert(qty.value, qty.unit, def.canonicalUnit);
  } catch {
    canonical = null;
  }
  const outOfRange =
    canonical !== null && (canonical < def.range[0] || canonical > def.range[1]);

  const columns: Column<ParameterDef>[] = [
    {
      key: 'name',
      header: 'Field',
      width: '32%',
      priority: 1,
      render: (d) => (
        <div>
          <div className="leading-snug">{d.name}</div>
          <div className="text-caption text-ink-soft font-num">{d.id}</div>
        </div>
      ),
      value: (d) => d.name,
    },
    {
      key: 'unit',
      header: 'Canonical unit',
      priority: 1,
      render: (d) => (
        <span className="font-num">{d.canonicalUnit || <span className="text-ink-soft">dimensionless</span>}</span>
      ),
      value: (d) => d.canonicalUnit,
    },
    {
      key: 'range',
      header: 'Validation range',
      numeric: true,
      priority: 1,
      render: (d) => (
        <span className="font-num">
          {fmt(d.range[0])} – {fmt(d.range[1])}
        </span>
      ),
      value: (d) => d.range[0],
    },
    {
      key: 'notes',
      header: 'Notes',
      priority: 3,
      render: (d) => <span className="text-ink-soft">{d.notes || '—'}</span>,
      value: (d) => d.notes,
    },
    {
      key: 'definition',
      header: 'Definition',
      defaultHidden: true,
      render: (d) => <span className="text-ink-soft">{d.definition}</span>,
      value: (d) => d.definition,
    },
  ];

  return (
    <div className="space-y-6">
      <section>
        <SectionTitle
          right={
            <Explain label="What does the SI setting change?">
              Records store the number in the unit the source reported it in, plus a canonical SI
              twin recomputed from that pair when the corpus loads. Switching to SI changes which of
              the two is displayed in tables, chips and protocol references — it never rewrites the
              stored value, and the reported figure is always one hover away.
            </Explain>
          }
        >
          Preferred display system
        </SectionTitle>
        <RadioCards<UnitMode>
          name="unitmode"
          label="Preferred display system"
          value={unitMode}
          onChange={(v) => setUI({ unitMode: v })}
          className="sm:grid-cols-2"
          options={[
            {
              value: 'published',
              label: 'As published',
              desc: 'Show the unit the source paper used. Best for checking an extraction against its span.',
            },
            {
              value: 'si',
              label: 'SI-normalized',
              desc: 'Show the canonical SI twin everywhere. Best for comparing across papers.',
            },
          ]}
        />
        <div className="text-caption text-ink-soft mt-2">
          A doubling time entered as <span className="font-num text-ink">14 h</span> currently
          renders as{' '}
          <Quantity
            value={14}
            unit="h"
            si={toSI(14, 'h')}
            mode={unitMode}
            className="text-ink font-medium"
          />
          .
        </div>
      </section>

      <section>
        <SectionTitle
          right={
            <span className="text-caption text-ink-soft inline-flex items-center gap-1.5">
              <Ruler size={13} aria-hidden /> parameter ontology v1
            </span>
          }
        >
          Conversion playground
        </SectionTitle>
        <Card className="p-3">
          <div className="grid gap-3 md:grid-cols-[240px_minmax(0,1fr)] items-start">
            <div>
              <label htmlFor="play-field" className="block text-caption text-ink-soft mb-1">
                Field
              </label>
              <select
                id="play-field"
                className="input"
                value={field}
                onChange={(e) => {
                  const next = e.target.value as FieldId;
                  setField(next);
                  setQty(defaultFor(ONTOLOGY_BY_ID[next]));
                }}
              >
                {ONTOLOGY.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
              <p className="text-caption text-ink-soft mt-1.5 leading-snug">{def.definition}</p>
            </div>

            <div>
              <label htmlFor="play-value" className="block text-caption text-ink-soft mb-1">
                Value — type any compatible unit
              </label>
              <QuantityField
                id="play-value"
                field={field}
                value={qty}
                onChange={(v) => {
                  if (v) setQty(v);
                }}
              />
              <dl className="mt-2 grid grid-cols-2 gap-2">
                <div className="rounded-input border border-line p-2">
                  <dt className="text-caption text-ink-soft">SI twin</dt>
                  <dd className="font-num text-body mt-0.5">
                    {si.unit === '' ? (
                      <>
                        {fmt(si.value)} <span className="text-ink-soft">dimensionless</span>
                      </>
                    ) : (
                      <>
                        {fmt(si.value)} <span className="text-ink-soft">{si.unit}</span>
                      </>
                    )}
                  </dd>
                </div>
                <div className="rounded-input border border-line p-2">
                  <dt className="text-caption text-ink-soft">Canonical (ontology)</dt>
                  <dd className="font-num text-body mt-0.5">
                    {canonical === null ? (
                      <span className="text-signal-error">not convertible</span>
                    ) : (
                      <>
                        {fmt(canonical)}{' '}
                        <span className="text-ink-soft">
                          {def.canonicalUnit || 'dimensionless'}
                        </span>
                      </>
                    )}
                  </dd>
                </div>
              </dl>
              <div className="text-caption text-ink-soft mt-2">
                Validation range for {fieldName(field)}:{' '}
                <span className="font-num text-ink">
                  {fmt(def.range[0])} – {fmt(def.range[1])} {def.canonicalUnit || '(dimensionless)'}
                </span>
                {outOfRange && (
                  <span className="text-signal-warn"> — the current value sits outside it.</span>
                )}
              </div>
            </div>
          </div>
        </Card>
      </section>

      <section>
        <SectionTitle>The {ONTOLOGY.length} fields</SectionTitle>
        {/*
          'curated', not 'demo': these definitions, canonical units and ranges were written by
          hand from the catalogued literature, so nothing in this table is modeled. They carry
          the same weight as any other curated row — real, and not yet checked back against the
          source PDFs.
        */}
        <DataTable<ParameterDef>
          rows={ONTOLOGY}
          columns={columns}
          rowKey={(d) => d.id}
          tickOf={() => 'curated'}
          searchOf={(d) => `${d.name} ${d.id} ${d.canonicalUnit} ${d.notes} ${d.definition}`}
          exportName="openferment-ontology-v1"
          exportNote="Ranges are the curator's, drawn from the catalogued literature, and are not a published standard. Values outside a range are warned about, never blocked — a paper may report a genuine outlier."
          maxHeight="520px"
          emptyTitle="No fields"
          emptyBody="The ontology module is empty, which should never happen in this build."
        />
      </section>
    </div>
  );
}

// ── corpus (owner) ─────────────────────────────────────────────────────

function CorpusSection() {
  const allPapers = useStore((s) => s.papers);
  const allRecords = useStore((s) => s.records);
  const shows = useProgramFilter();
  // The ontology and gold-set counts are of the papers and values whose
  // program shows (OF-BLD-016 §2.2). The reset dialog below counts the whole
  // store, because a reset restores all of it, archived programs included.
  const papers = useMemo(() => allPapers.filter((p) => shows('paper', p.id)), [allPapers, shows]);
  const visibleRecords = useMemo(() => allRecords.filter((r) => shows('record', r.id)), [allRecords, shows]);
  const records = allRecords;
  const archivedHidden = papers.length < allPapers.length || visibleRecords.length < allRecords.length;
  const protocols = useStore((s) => s.protocols);
  const scenarios = useStore((s) => s.scenarios);
  const clearBrowserData = useStore((s) => s.clearBrowserData);
  const depositions = useStore((s) => s.depositions);
  const [confirm, setConfirm] = useState(false);
  const reviewer = useStore((s) => s.reviewer);
  const setReviewerName = useStore((s) => s.setReviewerName);

  const gold = useMemo(() => visibleRecords.filter((r) => r.gold), [visibleRecords]);
  const goldPapers = useMemo(() => new Set(gold.map((r) => r.paperId)).size, [gold]);
  const goldByField = useMemo(() => {
    const m = new Map<FieldId, number>();
    for (const r of gold) m.set(r.field, (m.get(r.field) ?? 0) + 1);
    return [...m.entries()].sort((a, b) => b[1] - a[1]);
  }, [gold]);
  const maxField = goldByField.length > 0 ? goldByField[0][1] : 1;

  return (
    <div className="space-y-6">
      <Callout kind="info" title="Owner view">
        This panel is the owner&rsquo;s. Everything on it edits the corpus for the whole session; there is
        no second reviewer to undo it for you.
      </Callout>

      <section>
        <SectionTitle>Reviewer</SectionTitle>
        <Card className="p-3">
          <Row label="Your name">
            <input
              id="reviewer-name"
              type="text"
              value={reviewer}
              onChange={(e) => setReviewerName(e.target.value)}
              placeholder="e.g. Sean Creighton"
              aria-label="Reviewer name"
              autoComplete="name"
              className="w-full max-w-sm rounded border border-line bg-surface px-2 py-1 text-body"
            />
          </Row>
          <p className="text-body text-ink-soft mt-3 max-w-3xl">
            Every decision you make in the review queue is stored against this name, in{' '}
            <code className="font-mono text-caption">core/data/biorepo.json</code>, which is
            committed. A record is only verified when a named person promoted it against a sentence
            in the paper&rsquo;s own text — so the service refuses a decision signed by nobody, or
            by a word like &ldquo;you&rdquo; that names nobody. The name is kept in this browser and is not
            sent anywhere except with a decision.
          </p>
        </Card>
      </section>

      <section>
        <SectionTitle
          right={
            <span className="text-caption text-ink-soft inline-flex items-center gap-1.5">
              <Database size={13} aria-hidden /> reference
            </span>
          }
        >
          Ontology
        </SectionTitle>
        <Card className="p-3">
          <div className="grid gap-3 sm:grid-cols-3">
            <div>
              <div className="text-caption uppercase tracking-wide text-ink-soft">Fields</div>
              <div className="font-num text-display leading-tight">{ONTOLOGY.length}</div>
            </div>
            <div>
              <div className="text-caption uppercase tracking-wide text-ink-soft">
                Papers in corpus
              </div>
              <div className="font-num text-display leading-tight">{papers.length}</div>
            </div>
            <div>
              <div className="text-caption uppercase tracking-wide text-ink-soft">Records</div>
              <div className="font-num text-display leading-tight">{visibleRecords.length}</div>
            </div>
          </div>
          {archivedHidden && (
            <p className="text-caption text-ink-soft mt-2" data-testid="corpus-archived-hidden">
              Counted over the active programs. Papers and values in archived programs are kept and
              hidden;{' '}
              <a className="text-accent hover:underline" href="#/settings/programs">
                Settings → Programs
              </a>{' '}
              shows them again.
            </p>
          )}
          <p className="text-body text-ink-soft mt-3 max-w-3xl">
            Every extracted value is typed to one of these fields, converted to the field's
            canonical unit, and range-checked at entry. Extending the ontology is a schema change,
            not a setting — this build ships v1 and does not allow adding fields. Real values the
            corpus holds that v1 has no field for are listed on the validation screen rather than
            forced into a neighbouring field.
          </p>
          <div className="flex flex-wrap items-center gap-2 mt-3">
            <LinkButton to="/settings/units" size="sm">
              <Ruler size={13} /> Open the field table
            </LinkButton>
            <Button
              size="sm"
              onClick={() =>
                exportCSV(
                  'openferment-ontology-v1.csv',
                  ['Field id', 'Name', 'Canonical unit', 'Range low', 'Range high', 'Definition', 'Notes'],
                  ONTOLOGY.map((d) => [
                    d.id,
                    d.name,
                    d.canonicalUnit,
                    d.range[0],
                    d.range[1],
                    d.definition,
                    d.notes,
                  ]),
                )
              }
            >
              <Download size={13} /> Export ontology
            </Button>
          </div>
        </Card>
      </section>

      <section>
        <SectionTitle
          right={
            <span className="text-caption text-gold inline-flex items-center gap-1.5">
              <Award size={13} aria-hidden /> curated
            </span>
          }
        >
          Gold set
        </SectionTitle>
        <Card className="p-3">
          {gold.length === 0 && archivedHidden && allRecords.some((r) => r.gold) ? (
            <div className="text-body text-ink-soft">
              No value in the active programs is flagged for the gold set yet. The gold set&rsquo;s
              values sit in archived programs, which are hidden;{' '}
              <a className="text-accent hover:underline" href="#/settings/programs">
                Settings → Programs
              </a>{' '}
              shows them again. Flag a value with <span className="kbd">g</span> in the review queue
              and it joins the baseline immediately.
            </div>
          ) : gold.length === 0 ? (
            <div className="text-body text-ink-soft">
              No records are flagged for the gold set, and none ship flagged: a gold annotation
              has to be made against the paper's own words, and no full text has been retrieved.
              Flag one with <span className="kbd">g</span> in the review queue and it joins the
              baseline immediately — but nothing scores against that baseline until an extractor
              has actually been run.
            </div>
          ) : (
            <>
              <div className="grid gap-3 sm:grid-cols-3">
                <div>
                  <div className="text-caption uppercase tracking-wide text-ink-soft">
                    Gold records
                  </div>
                  <div className="font-num text-display leading-tight">{gold.length}</div>
                </div>
                <div>
                  <div className="text-caption uppercase tracking-wide text-ink-soft">
                    Papers covered
                  </div>
                  <div className="font-num text-display leading-tight">
                    {goldPapers}
                    <span className="text-section-title text-ink-soft ml-1.5">
                      / {papers.length}
                    </span>
                  </div>
                </div>
                <div>
                  <div className="text-caption uppercase tracking-wide text-ink-soft">
                    Fields covered
                  </div>
                  <div className="font-num text-display leading-tight">
                    {goldByField.length}
                    <span className="text-section-title text-ink-soft ml-1.5">
                      / {ONTOLOGY.length}
                    </span>
                  </div>
                </div>
              </div>
              <ul className="mt-3 space-y-1.5">
                {goldByField.map(([f, n]) => (
                  <li key={f} className="grid grid-cols-[minmax(0,1fr)_120px_36px] items-center gap-2">
                    <span className="text-body truncate">{fieldName(f)}</span>
                    <Bar value={n} max={maxField} className="bg-gold" />
                    <span className="font-num text-caption text-right">{n}</span>
                  </li>
                ))}
              </ul>
              <div className="mt-3">
                <LinkButton to="/biorepo/witness" size="sm">
                  <Beaker size={13} /> See the validation plan
                </LinkButton>
              </div>
            </>
          )}
        </Card>
      </section>

      <section>
        <SectionTitle>This browser&rsquo;s data</SectionTitle>
        <Card className="p-3">
          <p className="text-body text-ink-soft max-w-3xl">
            Depositions, review decisions, runbook locks, lessons finished, Postdoc&rsquo;s conversations
            and Guild entries the service has not stored yet are kept in this browser (the Durable tier).
            Clearing them leaves what the service keeps untouched.
          </p>
          <div className="mt-3">
            <Button onClick={() => setConfirm(true)}>
              <RotateCcw size={13} /> Clear this browser&rsquo;s data
            </Button>
          </div>
        </Card>
      </section>

      <Modal open={confirm} onClose={() => setConfirm(false)} title="Clear this browser’s data">
        <p className="text-body">
          Restores all <span className="font-num">{SEEDED.records}</span> records,{' '}
          <span className="font-num">{SEEDED.protocols}</span> protocols, and{' '}
          <span className="font-num">{SEEDED.scenarios}</span> scenarios to their seeded state.
          Exports you&rsquo;ve downloaded are unaffected.
        </p>
        <p className="text-body mt-2">
          This also clears the durable store in this browser, so{' '}
          <span className="font-num">{depositions.length}</span> deposition
          {depositions.length === 1 ? '' : 's'}, every review decision, every runbook lock, every
          lesson finished here, and any Guild entry the service has not yet stored are discarded —
          including the ones that would otherwise survive a refresh. A reset that left them behind
          would restore itself on the next reload.
        </p>
        <div className="text-caption text-ink-soft mt-2">
          Currently in session: <span className="font-num">{records.length}</span> records,{' '}
          <span className="font-num">{protocols.length}</span> protocols,{' '}
          <span className="font-num">{scenarios.length}</span> scenarios,{' '}
          <span className="font-num">{depositions.length}</span> depositions.
        </div>
        <div className="flex items-center justify-end gap-2 mt-4">
          <Button onClick={() => setConfirm(false)}>Cancel</Button>
          <Button
            variant="primary"
            onClick={() => {
              clearBrowserData();
              setConfirm(false);
            }}
          >
            <RotateCcw size={13} /> Clear this browser&rsquo;s data
          </Button>
        </div>
      </Modal>
    </div>
  );
}

// ── export center ──────────────────────────────────────────────────────

interface ExportRow {
  key: string;
  name: string;
  at: string;
  rows: number;
}

function ExportSection() {
  const exports = useStore((s) => s.exports);

  const rows = useMemo<ExportRow[]>(
    () => exports.map((e, i) => ({ ...e, key: `${i}-${e.name}-${e.at}` })),
    [exports],
  );

  const columns: Column<ExportRow>[] = [
    {
      key: 'name',
      header: 'File',
      priority: 1,
      render: (r) => <span className="font-num">{r.name}</span>,
      value: (r) => r.name,
    },
    {
      key: 'at',
      header: 'Generated',
      priority: 1,
      render: (r) => <span className="font-num">{r.at}</span>,
      value: (r) => r.at,
    },
    {
      key: 'rows',
      header: 'Rows',
      numeric: true,
      priority: 1,
      render: (r) => r.rows,
      value: (r) => r.rows,
    },
  ];

  const totalRows = rows.reduce((n, r) => n + r.rows, 0);

  return (
    <div className="space-y-6">
      <section>
        <SectionTitle
          right={
            <span className="text-caption text-ink-soft font-num">
              {rows.length} files · {totalRows} rows
            </span>
          }
        >
          This session's exports
        </SectionTitle>
        <DataTable<ExportRow>
          rows={rows}
          columns={columns}
          rowKey={(r) => r.key}
          tickOf={() => 'user'}
          searchOf={(r) => `${r.name} ${r.at}`}
          exportName="openferment-export-log"
          maxHeight="420px"
          emptyTitle="Nothing exported yet"
          emptyBody="Session state lives in memory and disappears on refresh — export is how anything leaves this build. Any table with a CSV button writes a row here."
        />
        <Callout kind="warn" title="Every file is stamped">
          Every CSV opens with the same <span className="font-num">{DISCLOSURE.length}</span>-line
          disclosure header. It names the literature entries as real, then defines each provenance
          class that can appear in the file — including that a curated row was transcribed from the
          curation document and not yet checked against the source PDF, that an industry estimate
          has no source document behind it, and that simulation outputs are modeled rather than
          measured. The text and markdown exports — run logs, review sessions, materials
          checklists, agent answers — carry their own headers saying the same thing in the shape
          their format allows. Nothing leaves here unweighted, so a file cannot quietly become
          evidence in someone else's analysis.
        </Callout>
      </section>

      <section>
        <SectionTitle
          right={
            <span className="chip text-signal-warn border-signal-warn/40">
              Not active in this build
            </span>
          }
        >
          API keys
        </SectionTitle>
        <Card className="p-3">
          <div className="flex items-start gap-2.5">
            <KeyRound size={16} className="mt-1 shrink-0 text-ink-soft" aria-hidden />
            <div className="min-w-0 flex-1">
              <label htmlFor="api-key" className="block text-caption text-ink-soft mb-1">
                Personal access key
              </label>
              <input
                id="api-key"
                className="input font-num max-w-[420px] opacity-60"
                value="of_live_—————————————— (none issued)"
                disabled
                readOnly
                aria-describedby="api-key-note"
              />
              <div className="mt-2 flex flex-wrap gap-2">
                <Button size="sm" disabled title="Not active in this build">
                  Generate key
                </Button>
                <Button size="sm" disabled title="Not active in this build">
                  Revoke all
                </Button>
              </div>
              <p id="api-key-note" className="text-body text-ink-soft mt-2 max-w-3xl">
                These controls are deliberately dead and shown disabled rather than hidden. There is
                no server, no account and no key issuance in this build: nothing here would
                authenticate against anything. In the product this panel would mint scoped tokens
                for the extraction and retrieval endpoints and list their last use.
              </p>
            </div>
          </div>
        </Card>
      </section>
    </div>
  );
}

// ── about / colophon ───────────────────────────────────────────────────

type Fidelity = 'Full' | 'Authored' | 'Visual';

/** `fidelity` carries the full honest phrase; `fidelityKind` reduces it to a badge colour. */
const FIDELITY_ROWS: { feature: string; fidelity: string; notes: string }[] = [
  {
    feature: 'Navigation, routing, deep links, command palette',
    fidelity: 'Full',
    notes:
      'Every screen is hash-addressable and shareable within the session; the palette searches papers, parameters, protocols and actions.',
  },
  {
    feature: 'Theme, density, reduced motion',
    fidelity: 'Full',
    notes: 'Applied at the document root and honoured by every screen. No reload, no flash.',
  },
  {
    feature: 'Data tables, including CSV export',
    fidelity: 'Full',
    notes:
      'Sorting, facets, column visibility, keyboard row traversal and virtualization past 200 rows are real; exports write real files.',
  },
  {
    feature: 'Global and entity search',
    fidelity: 'Full',
    notes: 'Lexical scoring over the in-memory corpus. No search service is contacted.',
  },
  {
    feature: 'Citation chips and reader span anchoring',
    fidelity: 'Full',
    notes:
      'Every chip resolves to a section, and the quote is found in that section by string match and highlighted in place. The section holds the curator’s catalogue note, so a span anchors to curator prose rather than to the paper’s own words.',
  },
  {
    feature: 'Unit-aware fields and the SI toggle',
    fidelity: 'Full',
    notes:
      'Parsing, dimension checking, conversion and range validation run for all 24 ontology fields, including temperature offsets and the conversions the engine refuses outright.',
  },
  {
    feature: 'Review queue',
    fidelity: 'Full',
    notes:
      'Accept, reject, edit, gold-flag and undo mutate the session record set and propagate to strain pages, protocols and metrics.',
  },
  {
    feature: 'Validation metrics',
    fidelity: 'Real, from the service when it is running',
    notes:
      'Witness scores the extractor\'s run (claude-1) against the curated records on the papers it fetched, and labels the figures provisional with the number of records they stand on. With the service down, or before any run, it shows the planned gold set and the difficulty cases instead, and no figure.',
  },
  {
    feature: 'Leave-one-out methodology',
    fidelity: 'Visual + explainer',
    notes:
      'The Sim does not train models. The panel explains what a leave-one-out evaluation would mean; no fold is ever run.',
  },
  {
    feature: 'Organism strip plots',
    fidelity: 'Full',
    notes: 'Drawn from the live record set — points move as you verify, edit or reject.',
  },
  {
    feature: 'Protocol scaling and materials math',
    fidelity: 'Full',
    notes:
      'Real arithmetic with per-material rounding precision and stock-solution volumes, so a scaled recipe stays pipettable.',
  },
  {
    feature: 'Deposition timers and summary',
    fidelity: 'Full',
    notes: 'Timers, checks, deviations and the end-of-run summary all run in the browser.',
  },
  {
    feature: 'Protocol version diff',
    fidelity: 'Full',
    notes: 'Structural diff of materials and steps computed between any two versions.',
  },
  {
    feature: 'Protocol editor',
    fidelity: 'Full for edit and reorder, authored for validation edge cases',
    notes:
      'Editing, reordering and saving a new version are real; the validation warnings for pathological edits are authored examples.',
  },
  {
    feature: 'Simulation results',
    fidelity: 'Full interpolation over authored precomputed grids',
    notes:
      'Multilinear interpolation across an authored cost-model sweep. The interpolation is real; the cost model is invented.',
  },
  {
    feature: 'Scenario compare',
    fidelity: 'Full',
    notes: 'Deltas, shared assumptions and divergences are computed from the pinned scenarios.',
  },
  {
    feature: 'Agent chat',
    fidelity: 'Real model call, through openferment-core',
    notes:
      'Postdoc, when the service is running, on the model its health check names (Claude Opus 5.5 with Sonnet 5.5 as fallback unless core/.env says otherwise): a bounded loop of tools, then a validated plan, and the browser renders every value from the cited record — the prose carries no numbers of its own. A follow-up sends the conversation\'s earlier questions and claims in words. With the service down Postdoc says so and how to start it, and keeps the conversations and the typed question; nothing answers in its place.',
  },
  {
    feature: 'Ingest pipeline',
    fidelity: 'Authored',
    notes:
      'Fetch, parse, chunk, embed and extract are timed stages over entries already present in the build, including one authored parse failure. No document is retrieved and no text is added: every entry is still catalogued when the run finishes.',
  },
  {
    feature: 'Learn lessons and checkpoints',
    fidelity: 'Full',
    notes:
      'Lesson prose is authored; navigation, live embeds, checkpoint grading and progress tracking are real.',
  },
  {
    feature: 'Guided tour',
    fidelity: 'Full',
    notes: 'Six stops that drive the actual screens rather than screenshots.',
  },
  {
    feature: 'Jobs tray',
    fidelity: 'Full over authored job timelines',
    notes: 'Progress, failure surfacing and completion toasts are real; stage durations are authored.',
  },
  {
    feature: 'Authentication, API keys, sharing',
    fidelity: 'Visual',
    notes: 'One identity: the reviewer name set in Settings, a claim and not a sign-in. No accounts, no tokens, no sharing.',
  },
  {
    feature: 'Real PDF rendering',
    fidelity: 'Visual',
    notes:
      'Each entry carries the curator’s catalogue note as its text. No PDF is fetched, parsed or displayed, and no paper’s full text is present in this build.',
  },
];

const FIDELITY_STYLE: Record<Fidelity, string> = {
  Full: 'text-accent border-accent/45',
  Authored: 'text-signal-info border-signal-info/45',
  Visual: 'text-signal-warn border-signal-warn/45',
};

function fidelityKind(f: string): Fidelity {
  if (f.startsWith('Full')) return 'Full';
  if (f.startsWith('Authored')) return 'Authored';
  return 'Visual';
}

function AboutSection() {
  const allPapers = useStore((s) => s.papers);
  const allRecords = useStore((s) => s.records);
  const shows = useProgramFilter();
  // The colophon counts what shows: with archived programs hidden it counts
  // the active ones, and says so (OF-BLD-016 §2.2).
  const papers = useMemo(() => allPapers.filter((p) => shows('paper', p.id)), [allPapers, shows]);
  const records = useMemo(() => allRecords.filter((r) => shows('record', r.id)), [allRecords, shows]);
  const archivedHidden = papers.length < allPapers.length || records.length < allRecords.length;

  const counts = useMemo(() => {
    const c: Record<Fidelity, number> = { Full: 0, Authored: 0, Visual: 0 };
    for (const r of FIDELITY_ROWS) c[fidelityKind(r.fidelity)]++;
    return c;
  }, []);

  // Identifier coverage is partial and the colophon must not round it up, so
  // every figure below is counted from the corpus rather than written down.
  const corpus = useMemo(() => {
    let doi = 0;
    let noId = 0;
    let noAuthors = 0;
    let verify = 0;
    const threads = new Set<string>();
    for (const p of papers) {
      if (p.doi) doi++;
      if (!p.doi && !p.pmcid && !p.pmid) noId++;
      if (p.authors.length === 0) noAuthors++;
      if (p.verifyNeeded) verify++;
      threads.add(p.thread);
    }
    return { doi, noId, noAuthors, verify, threads: threads.size };
  }, [papers]);

  const prov = useMemo(() => {
    let curated = 0;
    let estimate = 0;
    for (const r of records) {
      if (r.provenance === 'curated') curated++;
      else if (r.provenance === 'industry-estimate') estimate++;
    }
    return { curated, estimate };
  }, [records]);

  return (
    <div className="space-y-6">
      <section>
        <SectionTitle>Colophon</SectionTitle>
        {archivedHidden && (
          <p className="text-caption text-ink-soft mb-2" data-testid="about-archived-hidden">
            The counts below are of the active programs. Archived programs are kept and hidden;{' '}
            <a className="text-accent hover:underline" href="#/settings/programs">
              Settings → Programs
            </a>{' '}
            shows them again.
          </p>
        )}
        <Callout kind="warn" title="Read this before you believe a number on this site">
          <ul className="space-y-1.5 mt-1">
            <li>
              <span className="font-medium">The literature is real.</span> All{' '}
              <span className="font-num">{papers.length}</span> entries are real papers, theses,
              patents and reports, spread over{' '}
              <span className="font-num">{corpus.threads}</span> corpus threads, with real titles,
              real venues and real DOIs where one exists. They are citable. Identifier coverage is
              partial and the corpus does not pretend otherwise:{' '}
              <span className="font-num">{corpus.doi}</span> of{' '}
              <span className="font-num">{papers.length}</span> entries carry a DOI,{' '}
              <span className="font-num">{corpus.noId}</span> carry no DOI, PMCID or PMID at all,{' '}
              <span className="font-num">{corpus.noAuthors}</span> have no author list yet, and{' '}
              <span className="font-num">{corpus.verify}</span> are flagged for verification.
            </li>
            <li>
              <span className="font-medium">Every entry is catalogued, not ingested.</span> No full
              text has been retrieved. Each entry is metadata plus a hand-written curator note, so a
              highlighted extraction span anchors to the curator&rsquo;s prose, not to the
              paper&rsquo;s own words. Of the{' '}
              <span className="font-num">{records.length}</span> extraction records,{' '}
              <span className="font-num">{prov.curated}</span> are curated: transcribed from the
              curation document and not yet checked against the source PDF. The remaining{' '}
              <span className="font-num">{prov.estimate}</span> are industry estimates, which are
              not evidence. Read a value against its source before you cite it.
            </li>
            <li>
              <span className="font-medium">No extractor has ever been run.</span> There is no
              extractor output in this build, so no precision, recall or F1 figure appears anywhere.
              Validation shows the gold set that is planned, the difficulty cases it has to include,
              and the values the ontology cannot yet hold — and states that nothing has been scored.
            </li>
            <li>
              <span className="font-medium">Session state is held in memory only.</span> Reviews,
              edits, runs, new protocol versions and chat history live in this browser tab and are
              gone on refresh. There is no database, no account and no server; exporting a CSV is
              the only way anything leaves.
            </li>
            <li>
              <span className="font-medium">Simulation economics are illustrative.</span> The cost
              models are authored spreadsheets swept over a grid — cost model v0, illustrative
              economics, not validated. This is the part of the build that really is synthetic.
              Treat a minimum selling price here as a shape to reason about, never as a number to
              plan against.
            </li>
            <li>
              <span className="font-medium">Postdoc answers only through the service.</span>{' '}
              Every answer is a real model call through openferment-core, and every value in it is
              rendered from the record it cites. With the service down Postdoc says so and how to
              start it; nothing answers in its place.
            </li>
          </ul>
        </Callout>
      </section>

      <section>
        <SectionTitle
          right={
            <Button
              size="sm"
              onClick={() =>
                exportCSV(
                  'openferment-fidelity-matrix.csv',
                  ['Feature', 'Fidelity', 'Notes'],
                  FIDELITY_ROWS.map((r) => [r.feature, r.fidelity, r.notes]),
                )
              }
            >
              <Download size={13} /> Export
            </Button>
          }
        >
          Fidelity matrix
        </SectionTitle>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-caption text-ink-soft mb-2">
          <span className="inline-flex items-center gap-1.5">
            <span className="chip text-accent border-accent/45">Full</span>
            computed here, from the corpus in memory —{' '}
            <span className="font-num">{counts.Full}</span>
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="chip text-signal-info border-signal-info/45">Authored</span>
            follows an authored timeline or answer —{' '}
            <span className="font-num">{counts.Authored}</span>
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="chip text-signal-warn border-signal-warn/45">Visual</span>
            the surface exists, the mechanism does not —{' '}
            <span className="font-num">{counts.Visual}</span>
          </span>
        </div>
        <Card className="overflow-x-auto">
          <table className="w-full border-collapse" style={{ fontSize: 'var(--table-fs)' }}>
            <caption className="sr-only">
              Fidelity of each feature in the openFerment simulation
            </caption>
            <thead>
              <tr className="bg-surface-1 border-b border-line">
                <th className="text-left text-caption font-medium text-ink-soft px-3 py-2 w-[28%]">
                  Feature
                </th>
                <th className="text-left text-caption font-medium text-ink-soft px-3 py-2 w-[22%]">
                  Fidelity
                </th>
                <th className="text-left text-caption font-medium text-ink-soft px-3 py-2">
                  Notes
                </th>
              </tr>
            </thead>
            <tbody>
              {FIDELITY_ROWS.map((r) => {
                const kind = fidelityKind(r.fidelity);
                return (
                  <tr key={r.feature} className="border-b border-line/70 last:border-0 align-top">
                    <td className="px-3 py-2">{r.feature}</td>
                    <td className="px-3 py-2">
                      <span className={cx('chip', FIDELITY_STYLE[kind])}>{r.fidelity}</span>
                    </td>
                    <td className="px-3 py-2 text-ink-soft">{r.notes}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Card>
      </section>

      <section>
        <SectionTitle
          right={
            <span className="text-caption text-ink-soft inline-flex items-center gap-1.5">
              <Info size={13} aria-hidden /> disclosure
            </span>
          }
        >
          Version and configuration
        </SectionTitle>
        <Card className="p-3">
          <Row label="App version">
            <span className="font-num">openFerment Sim {APP_VERSION}</span> — implements design
            OF-DES-001 v0.1 over corpus OF-COR-001 v1.0
          </Row>
          <Row label="Corpus">
            <span className="font-num">{papers.length}</span> catalogued papers across{' '}
            <span className="font-num">{corpus.threads}</span> threads,{' '}
            <span className="font-num">{records.length}</span> extraction records, ontology v1 with{' '}
            <span className="font-num">{ONTOLOGY.length}</span> fields
          </Row>
          <Row label="Extractor">
            The seed records were transcribed by hand from the curation document and carry no run
            label. With the service running, the extractor&rsquo;s candidates (run claude-1) arrive
            through the overlay, each anchored to a sentence of a fetched paper and unverified until a
            named reviewer decides; Witness scores that run.
          </Row>
          <Row label="Agent">
            One path: Postdoc through openferment-core, on the model the service reports (Opus 5.5 with
            Sonnet 5.5 as fallback by default), values rendered from the cited records. With the
            service down it says so, and nothing answers in its place.
          </Row>
          <Row label="Retrieval">
            In the service: passages cut from the fetched papers, searched by the lane the service
            names (BioRepo &rarr; Search, Witness &rarr; Retrieval). The browser holds no index; the
            &ldquo;Embed&rdquo; stage in the offline ingest board is a timed animation. Fetch and Extract, when the service is up, are real: Europe PMC for the text,
            one structured response per paper for the candidates.
          </Row>
          <Row label="Storage">
            Split by lifetime. Reference data — papers, protocols, molecules, vocabulary — is never
            mutated and is read from the build every load. The Durable tier — depositions, review
            decisions, runbook locks and Postdoc&rsquo;s Live conversations — is written to
            IndexedDB in this browser, because a fermentation at hour 14 with timers running cannot
            be lost to a page reload, and neither can a question somebody is halfway through. Everything
            else is memory only and resets: open panels, density, theme, simulation speed. No
            localStorage, no sessionStorage, no cookies, no telemetry, and nothing leaves the
            browser. &ldquo;Clear this browser&rsquo;s data&rdquo; clears the durable store as well as memory.
          </Row>
          <Row label="Type">
            <span className="inline-flex items-center gap-1.5">
              <span
                className="inline-block w-[3px] h-4 rounded-[1px]"
                style={{
                  backgroundImage:
                    'repeating-linear-gradient(to bottom, rgb(var(--signal-warn)) 0 3px, transparent 3px 6px)',
                }}
                aria-hidden
              />
              A working simulation of a product, built to be judged as a design — not a beta, not a
              preview of a shipping service.
            </span>
          </Row>
        </Card>
      </section>
    </div>
  );
}

// ── screen ─────────────────────────────────────────────────────────────

export default function Settings({ section }: { section: string }) {
  const active = SECTIONS.some((s) => s.id === section) ? section : 'appearance';
  const def = SECTIONS.find((s) => s.id === active)!;

  return (
    <div>
      <PageHeader eyebrow="Settings" title={def.label} subtitle={def.blurb} />

      <div className="grid grid-cols-1 gap-6 md:grid-cols-[184px_minmax(0,1fr)] items-start">
        <nav aria-label="Settings sections" className="min-w-0">
          <ul className="flex md:flex-col gap-1 overflow-x-auto pb-1 md:pb-0">
            {SECTIONS.map((s) => {
              const on = s.id === active;
              return (
                <li key={s.id}>
                  <a
                    href={`#/settings/${s.id}`}
                    aria-current={on ? 'page' : undefined}
                    className={cx(
                      'flex items-center gap-2 rounded-btn px-2.5 py-1.5 text-body whitespace-nowrap transition-colors',
                      on
                        ? 'bg-accent-wash text-accent font-medium'
                        : 'text-ink-soft hover:text-ink hover:bg-ink-soft/[0.06]',
                    )}
                  >
                    {s.id === 'appearance' && <Sun size={14} aria-hidden />}
                    {s.id === 'programs' && <Layers size={14} aria-hidden />}
                    {s.id === 'units' && <Ruler size={14} aria-hidden />}
                    {s.id === 'corpus' && <Database size={14} aria-hidden />}
                    {s.id === 'guild' && <ShieldCheck size={14} aria-hidden />}
                    {s.id === 'figures' && <ChartScatter size={14} aria-hidden />}
                    {s.id === 'export' && <Download size={14} aria-hidden />}
                    {s.id === 'about' && <Moon size={14} aria-hidden />}
                    <span className="truncate">{s.label}</span>
                    {s.owner && (
                      <span className="text-[10px] uppercase tracking-wide text-ink-soft border border-line rounded-input px-1">
                        owner
                      </span>
                    )}
                  </a>
                </li>
              );
            })}
          </ul>
        </nav>

        <div className="min-w-0">
          {active === 'appearance' && <AppearanceSection />}
          {active === 'programs' && <ProgramsSection />}
          {active === 'units' && <UnitsSection />}
          {active === 'corpus' && <CorpusSection />}
          {active === 'guild' && <GuildPolicySection />}
          {active === 'figures' && <FiguresSection />}
          {active === 'export' && <ExportSection />}
          {active === 'about' && <AboutSection />}
        </div>
      </div>
    </div>
  );
}
