// Settings (OF-DES-001 §8.15) — appearance, units, the reviewer and the
// record fields, the export center, and the colophon that tells the truth
// about this build.
import { useMemo, useState, type ReactNode } from 'react';
import {
  Award,
  Beaker,
  ChartScatter,
  Database,
  Download,
  Info,
  KeyRound,
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
  type Density,
  type Theme,
  type UnitMode,
} from '@/store';
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
    id: 'units',
    label: 'Units & display',
    blurb:
      `Choose how quantities are shown, and inspect the ${ONTOLOGY.length} record fields every number is typed to.`,
  },
  {
    id: 'architecture',
    label: 'Architecture',
    blurb:
      'The named components and the layers they sit in — the map the system is built from.',
  },
  {
    id: 'corpus',
    label: 'Reviewer & ontology',
    blurb: 'Owner controls: who signs the decisions made here, the record fields, the gold set, and clearing this browser’s data.',
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
    blurb: 'What is real in this build, what is written into it by hand, and what is only a surface.',
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
  const setUI = useStore((s) => s.setUI);
  const records = useStore((s) => s.records);
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
                      No records loaded in this session.
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

    </div>
  );
}

// ── units ──────────────────────────────────────────────────────────────

/**
 * The playground starts at one of the field's canonical unit: a unit to
 * convert, which states nothing about what any culture or process reaches.
 */
function defaultFor(def: ParameterDef): QuantityValue {
  return { value: 1, unit: def.canonicalUnit };
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
      key: 'definition',
      header: 'Definition',
      priority: 3,
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
              twin recomputed from that pair when the records load. Switching to SI changes which of
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
              <Ruler size={13} aria-hidden /> record fields
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
                {fieldName(field)} is stored in{' '}
                <span className="font-num text-ink">{def.canonicalUnit || '(dimensionless)'}</span>. A field
                carries no range: a value is held to its unit and to the quote it stands in.
              </div>
            </div>
          </div>
        </Card>
      </section>

      <section>
        <SectionTitle>The {ONTOLOGY.length} fields</SectionTitle>
        {/*
          'curated': these definitions and canonical units are written by hand in
          core/openferment_core/schema/fields.yaml, the one source of the fields, and nothing in
          this table is modeled.
        */}
        <DataTable<ParameterDef>
          rows={ONTOLOGY}
          columns={columns}
          rowKey={(d) => d.id}
          tickOf={() => 'curated'}
          searchOf={(d) => `${d.name} ${d.id} ${d.canonicalUnit} ${d.definition}`}
          exportName="openferment-record-fields"
          exportNote="The record fields as core/openferment_core/schema/fields.yaml defines them: an id, a name, a definition and a canonical unit. A field carries no range and no example value."
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
  const papers = useStore((s) => s.papers);
  const records = useStore((s) => s.records);
  const protocols = useStore((s) => s.protocols);
  const scenarios = useStore((s) => s.scenarios);
  const clearBrowserData = useStore((s) => s.clearBrowserData);
  const depositions = useStore((s) => s.depositions);
  const [confirm, setConfirm] = useState(false);
  const reviewer = useStore((s) => s.reviewer);
  const setReviewerName = useStore((s) => s.setReviewerName);

  const gold = useMemo(() => records.filter((r) => r.gold), [records]);
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
        This panel is the owner&rsquo;s: who signs the decisions made in this browser, the fields every
        value is typed to, and this browser&rsquo;s data. There is no second reviewer to undo it for you.
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
            Every decision you make in the review queue is stored against this name by the service,
            among the open project&rsquo;s decisions. A record is only verified when a named person
            promoted it against a sentence in the paper&rsquo;s own text — so the service refuses a
            decision signed by nobody, or by a word like &ldquo;you&rdquo; that names nobody. The name is
            kept in this browser and is sent only with a decision.
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
                Documents held
              </div>
              <div className="font-num text-display leading-tight">{papers.length}</div>
            </div>
            <div>
              <div className="text-caption uppercase tracking-wide text-ink-soft">Records</div>
              <div className="font-num text-display leading-tight">{records.length}</div>
            </div>
          </div>
          <p className="text-body text-ink-soft mt-3 max-w-3xl">
            Every extracted value is typed to one of these fields and converted to the field&rsquo;s
            canonical unit. The fields are defined in{' '}
            <code className="font-mono text-caption">core/openferment_core/schema/fields.yaml</code>; adding one
            is a schema change, made there.
          </p>
          <div className="flex flex-wrap items-center gap-2 mt-3">
            <LinkButton to="/settings/units" size="sm">
              <Ruler size={13} /> Open the field table
            </LinkButton>
            <Button
              size="sm"
              onClick={() =>
                exportCSV(
                  'openferment-record-fields.csv',
                  ['Field id', 'Name', 'Canonical unit', 'Definition'],
                  ONTOLOGY.map((d) => [d.id, d.name, d.canonicalUnit, d.definition]),
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
              <Award size={13} aria-hidden /> reviewer-typed
            </span>
          }
        >
          Gold set
        </SectionTitle>
        <Card className="p-3">
          {gold.length === 0 ? (
            <div className="text-body text-ink-soft">
              No record is flagged for the gold set. A gold annotation is made against a sentence of
              a document the project holds: flag one with <span className="kbd">g</span> in the
              review queue and it joins the values Witness scores the extractor against.
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
          Returns this browser to the state it starts in, with no records, protocols or scenarios of its
          own; what the service keeps is laid back on at once. Exports you&rsquo;ve downloaded are
          unaffected.
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
          emptyBody="Any table with a CSV button writes a row here when it exports."
        />
        <Callout kind="warn" title="Every file is stamped">
          Every CSV opens with the same <span className="font-num">{DISCLOSURE.length}</span>-line
          disclosure header. It names the literature entries as real, then defines each provenance
          class that can appear in the file — including that an unverified row is the extractor&rsquo;s
          reading no reviewer has checked against its sentence, that an industry estimate
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
      'Every screen has an address inside its project (/p/:project/…); the palette searches papers, parameters, protocols and actions.',
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
    feature: 'Search over the project’s documents',
    fidelity: 'Full, through the service when it is running',
    notes:
      'Sci RAG Kit searches the passages of the documents the project holds, embedded on the service’s machine, and answers a question with the passages it cites. With the service down, nothing is searched.',
  },
  {
    feature: 'Citation chips and reader span anchoring',
    fidelity: 'Full',
    notes:
      'Every chip resolves to a passage of a document the project holds, and the quote is found in that passage and highlighted in place.',
  },
  {
    feature: 'Unit-aware fields and the SI toggle',
    fidelity: 'Full',
    notes: `Parsing, dimension checking and conversion run for all ${ONTOLOGY.length} record fields, including temperature offsets and the conversions the engine refuses outright.`,
  },
  {
    feature: 'Review queue',
    fidelity: 'Full, through the service when it is running',
    notes:
      'Accept, reject, edit, gold-flag and undo post a decision the service holds to its anchoring rules and keeps under the project; one made while the service is away waits in this browser until it answers.',
  },
  {
    feature: 'Validation metrics',
    fidelity: 'Real, from the service when it is running',
    notes:
      'Witness scores the extractor\'s run (claude-1) against the values reviewers typed on the documents the project holds. Before any run or any typed value, it shows what unblocks a figure, and no figure.',
  },
  {
    feature: 'Leave-one-out methodology',
    fidelity: 'Visual + explainer',
    notes: 'The panel explains what a leave-one-out evaluation would mean; no fold is ever run.',
  },
  {
    feature: 'Organism strip plots',
    fidelity: 'Full',
    notes: 'Drawn from the project’s records — points move as you verify, edit or reject.',
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
    fidelity: 'Full, through the service when it is running',
    notes:
      'A library plant or an openFerment flowsheet runs on BioSTEAM in the service and is kept as a run with its inputs and their origins, its tables, its SFF file and the versions it ran on.',
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
      'Postdoc, when the service is running, on the models its routing table names: a bounded loop of tools, then a validated plan in which every number carries its origin and an estimate is marked as one. The service keeps each conversation, and a follow-up reads it there. With the service down Postdoc says so and how to start it; nothing answers in its place.',
  },
  {
    feature: 'Ingest pipeline',
    fidelity: 'Full, through the service when it is running',
    notes:
      'Intake collects a paper by its PMCID, DOI, PMID, OSTI or SGD id, an uploaded file or pasted text into the project’s documents, cut into passages and embedded on the service’s machine. Extraction is its own step. With the service down nothing is collected.',
  },
  {
    feature: 'Learn lessons and checkpoints',
    fidelity: 'Full',
    notes:
      'No lesson ships with this build. Navigation, live embeds, checkpoint grading and progress tracking work for any lesson the store holds.',
  },
  {
    feature: 'Guided tour',
    fidelity: 'Full',
    notes: 'Six stops that drive the actual screens rather than screenshots.',
  },
  {
    feature: 'Jobs tray',
    fidelity: 'Full for fetches and extractions',
    notes:
      'A fetch or an extraction moves only on the service\u2019s answer, and its failure is the service\u2019s reason. Any other job advances on stage durations set in the browser, not on work done.',
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
      'The reader shows a document as the passages the service holds for it. No PDF is rendered.',
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
  const papers = useStore((s) => s.papers);
  const records = useStore((s) => s.records);

  const counts = useMemo(() => {
    const c: Record<Fidelity, number> = { Full: 0, Authored: 0, Visual: 0 };
    for (const r of FIDELITY_ROWS) c[fidelityKind(r.fidelity)]++;
    return c;
  }, []);

  // Counted from the open project rather than written down.
  const decided = useMemo(() => {
    let verified = 0;
    let gold = 0;
    for (const r of records) {
      if (r.gold) gold++;
      else if (r.status === 'verified') verified++;
    }
    return { verified, gold };
  }, [records]);

  return (
    <div className="space-y-6">
      <section>
        <SectionTitle>Colophon</SectionTitle>
        <Callout kind="warn" title="Read this before you believe a number on this site">
          <ul className="space-y-1.5 mt-1">
            <li>
              <span className="font-medium">Nothing scientific ships with the app.</span> The open
              project holds <span className="font-num">{papers.length}</span> documents and{' '}
              <span className="font-num">{records.length}</span> extraction records, all of them
              brought in here: documents through Intake, records through extraction and review. Of
              the records, <span className="font-num">{decided.verified}</span> are verified by a
              named reviewer against a sentence of their document,{' '}
              <span className="font-num">{decided.gold}</span> are gold, and the rest are
              unverified candidates, each marked by its badge. Read a value against its source
              before you cite it.
            </li>
            <li>
              <span className="font-medium">The extractor runs in the service.</span> What it
              extracts arrives as unverified candidates, each anchored to a sentence of a document
              the project holds, and waits for a reviewer. Witness scores a run against the values
              reviewers typed; before any run or any typed value, it shows no figure.
            </li>
            <li>
              <span className="font-medium">The service keeps the project.</span> Documents,
              records, decisions, runs, studies and Postdoc&rsquo;s conversations are kept by the
              service, in its database, under the project. This browser keeps its preferences and
              the writes the service has not yet acknowledged, and sends them when it answers.
              There is no account and no sign-in.
            </li>
            <li>
              <span className="font-medium">Simulation economics come from BioSTEAM.</span> A price
              here is a run the service kept, with its inputs and where each came from. A minimum
              selling price is a model output to reason about; plan against one only once its inputs
              are checked.
            </li>
            <li>
              <span className="font-medium">Postdoc answers only through the service.</span>{' '}
              Every answer is a real model call through openferment-core, and every number in it
              carries where it came from: a record, a computed value, or a model&rsquo;s estimate
              marked as one. With the service down Postdoc says so and how to start it; nothing
              answers in its place.
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
            computed from the project&rsquo;s data —{' '}
            <span className="font-num">{counts.Full}</span>
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="chip text-signal-info border-signal-info/45">Authored</span>
            is written into the build by hand, not computed —{' '}
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
              Fidelity of each feature in openFerment
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
            <span className="font-num">openFerment {APP_VERSION}</span> — alpha 2.0, the foundation
            build
          </Row>
          <Row label="Project">
            <span className="font-num">{papers.length}</span> documents held,{' '}
            <span className="font-num">{records.length}</span> extraction records,{' '}
            <span className="font-num">{ONTOLOGY.length}</span> record fields
          </Row>
          <Row label="Extractor">
            With the service running, the extractor&rsquo;s candidates (run claude-1) arrive
            through the overlay, each anchored to a sentence of a document the project holds and
            unverified until a named reviewer decides; Witness scores that run.
          </Row>
          <Row label="Agent">
            One path: Postdoc through openferment-core, on the models its routing table names, every
            number with its origin. With the service down it says so, and nothing answers in its
            place.
          </Row>
          <Row label="Retrieval">
            In the service: Sci RAG Kit holds each project&rsquo;s documents, cut into passages and
            embedded on the service&rsquo;s machine, and answers searches and cited questions over
            them. The browser holds no index.
          </Row>
          <Row label="Storage">
            The service keeps each project in its database. This browser keeps its preferences and
            the writes the service has not yet acknowledged, in IndexedDB, because a deposition at
            hour 14 with timers running cannot be lost to a page reload; they are sent when the
            service answers. No cookies, no telemetry. &ldquo;Clear this browser&rsquo;s data&rdquo;
            clears this browser&rsquo;s copy and leaves the service&rsquo;s untouched.
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
              alpha 2.0: a working platform, run on one machine, on loopback, by its owner.
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
