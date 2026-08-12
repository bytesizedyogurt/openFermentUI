// Ledger (OF-FE-003 §8.2) — the parameter index and the parameter page.
//
// This is where the app stops being a corpus browser and becomes a
// parameter-first instrument. A record is evidence about a parameter; the
// parameter is the thing you actually reason with, and until now it had no
// surface of its own.
//
// Everything on these screens is derived from RECORDS at render time through
// engine/posterior.ts, so nothing here can drift from the records it claims to
// summarise.
import { useMemo } from 'react';
import { AlertTriangle, ArrowLeft, CheckCircle2, CircleDashed } from 'lucide-react';
import { useStore } from '@/store';
import { provenanceOf, isAggregatable, aggregateExclusion, EXCLUSION_NOTE } from '@/engine/aggregation';
import { buildParameterView } from '@/engine/posterior';
import { ContradictionRail, type RailMark } from '@/components/ContradictionRail';
import { ONTOLOGY, ONTOLOGY_BY_ID, ONTOLOGY_GAPS, FAMILY_LABEL, fieldName } from '@/data/ontology';
import type { ExtractionRecord, FieldId, ParameterView } from '@/data/types';
import { convert, asNumber, fmt, explainRefusal } from '@/engine/units';
import { navigate, href } from '@/router';
import { Card, PageHeader, SectionTitle, Callout, Explain, LinkButton, cx } from '@/components/ui';
import { Tick, ProvenanceBadge } from '@/components/Provenance';

// ── shared helpers ─────────────────────────────────────────────────────

/** Records converted into the field's canonical unit, for plotting. */
function railMarks(records: ExtractionRecord[], unit: string): RailMark[] {
  const out: RailMark[] = [];
  for (const r of records) {
    const n = asNumber(r.value);
    if (n === null) continue;
    let v = n;
    if (unit && r.unit !== unit) {
      try {
        v = convert(n, r.unit, unit);
      } catch {
        continue;
      }
    }
    out.push({ record: r, value: v });
  }
  return out;
}

function useViews(): ParameterView[] {
  const records = useStore((s) => s.records);
  const papers = useStore((s) => s.papers);
  const contradictions = useStore((s) => s.contradictions);
  return useMemo(() => {
    const yearOf = (paperId: string) => papers.find((p) => p.id === paperId)?.year || undefined;
    return ONTOLOGY.map((d) => buildParameterView(d.id, records, contradictions, yearOf));
  }, [records, papers, contradictions]);
}

function RefereeChip({ v }: { v: ParameterView }) {
  if (v.referee.state === 'contradicted') {
    return (
      <span className="inline-flex items-center gap-1 text-signal-error text-caption">
        <AlertTriangle size={12} aria-hidden />
        contradicted
      </span>
    );
  }
  if (v.referee.state === 'unchecked') {
    return (
      <span className="inline-flex items-center gap-1 text-ink-soft text-caption">
        <CircleDashed size={12} aria-hidden />
        unchecked — no records
      </span>
    );
  }
  return (
    <span
      className="inline-flex items-center gap-1 text-accent text-caption"
      title={`checks run: ${v.referee.checks.join(', ')}`}
    >
      <CheckCircle2 size={12} aria-hidden />
      consistent
    </span>
  );
}

// ── index ──────────────────────────────────────────────────────────────

export function Ledger() {
  const views = useViews();
  const allRecords = useStore((s) => s.records);
  const byField = useMemo(() => {
    const m = new Map<FieldId, ExtractionRecord[]>();
    for (const r of allRecords) {
      const list = m.get(r.field) ?? [];
      list.push(r);
      m.set(r.field, list);
    }
    return m;
  }, [allRecords]);

  const withRecords = views.filter((v) => v.recordIds.length > 0);
  const contradicted = views.filter((v) => v.referee.state === 'contradicted');
  const empty = views.filter((v) => v.recordIds.length === 0);

  return (
    <div className="p-6 max-w-[1400px]">
      <PageHeader
        eyebrow="Read · Ledger"
        title="Parameters"
        subtitle="The 24 ontology fields, each as an aggregate over the records that measure it. A record is evidence; the parameter is the thing you reason with."
        actions={<LinkButton to="/ledger/records">Record table</LinkButton>}
      />

      {contradicted.length > 0 && (
        <div className="mb-4 max-w-3xl">
        <Callout
          kind="warn"
          title={`${contradicted.length} parameter${contradicted.length === 1 ? '' : 's'} carry a contradiction`}
        >
          A contradiction means a set of records cannot all be true. The referee flags the set; it
          does not need to know which member is wrong to be useful.{' '}
          <a href={href('/ledger/contradictions')} className="text-accent hover:underline">
            Open the queue
          </a>
          .
        </Callout>
        </div>
      )}

      <div className="overflow-x-auto">
        {/* Density is a CSS variable the shell stamps on the root; a table
            that hardcodes its own type size ignores Shift+D entirely. */}
        <table className="w-full" style={{ fontSize: 'var(--table-fs)' }}>
          <thead>
            <tr className="text-caption uppercase tracking-wide text-ink-soft border-b border-line">
              <th className="text-left font-medium py-2 pr-3">Parameter</th>
              <th className="text-left font-medium py-2 pr-3">Family</th>
              <th className="text-right font-medium py-2 pr-1.5">Median</th>
              <th className="text-left font-medium py-2 pr-6 pl-0">Unit</th>
              <th className="text-right font-medium py-2 pr-3">n</th>
              <th className="text-right font-medium py-2 pr-3">primary</th>
              <th className="text-left font-medium py-2 pr-3">Spread</th>
              <th className="text-left font-medium py-2">Referee</th>
            </tr>
          </thead>
          <tbody>
            {withRecords.map((v) => {
              const unit = v.aggregate?.unit ?? v.def.canonicalUnit;
              const marks = railMarks(byField.get(v.field) ?? [], unit);
              return (
                <tr
                  key={v.field}
                  className="border-b border-line/60 hover:bg-accent-wash/40 cursor-pointer align-middle"
                  onClick={() => navigate(`/ledger/p/${v.field}`)}
                >
                  <td className="py-1.5 pr-3">
                    <a
                      href={href(`/ledger/p/${v.field}`)}
                      className="text-ink hover:text-accent"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {v.def.name}
                    </a>
                  </td>
                  <td className="py-1.5 pr-3 text-ink-soft text-caption">
                    {FAMILY_LABEL[v.def.family]}
                  </td>
                  <td className="py-1.5 pr-1 text-right font-num tabular-nums whitespace-nowrap">
                    {v.aggregate ? (
                      fmt(v.aggregate.median)
                    ) : (
                      <span className="text-ink-soft" title="Fewer than two comparable records">
                        —
                      </span>
                    )}
                  </td>
                  <td className="py-1.5 pr-6 text-caption text-ink-soft whitespace-nowrap">
                    {v.aggregate ? unit : ''}
                  </td>
                  <td className="py-1.5 pr-3 text-right font-num tabular-nums">{v.recordIds.length}</td>
                  <td className="py-1.5 pr-3 text-right font-num tabular-nums text-ink-soft">
                    {v.aggregate ? (
                      v.aggregate.nPrimary
                    ) : (
                      <span title="No aggregate — categorical, or too few comparable records">—</span>
                    )}
                  </td>
                  <td className="py-1.5 pr-3">
                    <ContradictionRail
                      marks={marks}
                      aggregate={v.aggregate}
                      contradictions={v.contradictions}
                      height={34}
                    />
                  </td>
                  <td className="py-1.5">
                    <RefereeChip v={v} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {empty.length > 0 && (
        <section className="mt-6">
          <SectionTitle>Fields with no records yet</SectionTitle>
          <p className="text-caption text-ink-soft mb-2 max-w-3xl">
            Part of the ontology the corpus does not yet populate. Listed rather than hidden — an
            empty field is a statement about coverage, and hiding it would make the ontology look
            better served than it is.
          </p>
          <div className="flex flex-wrap gap-1.5">
            {empty.map((v) => (
              <a
                key={v.field}
                href={href(`/ledger/p/${v.field}`)}
                className="text-caption border border-line rounded-btn px-2 py-1 text-ink-soft hover:border-accent/45"
              >
                {v.def.name}
              </a>
            ))}
          </div>
        </section>
      )}

      <section className="mt-6 max-w-3xl">
        <SectionTitle>What the ontology cannot hold</SectionTitle>
        <p className="text-caption text-ink-soft mb-2">
          Real values in the corpus with no field to put them in. Recorded here rather than
          dropped, because a value discarded for want of a schema is the kind of loss nothing
          downstream can detect.
        </p>
        <div className="space-y-1.5">
          {ONTOLOGY_GAPS.map((g, i) => (
            <Card key={i} className="p-2.5">
              <div className="text-caption text-ink-soft">
                <span className="font-mono text-ink">{g.entry}</span> — {g.values}
              </div>
              <div className="text-caption text-ink-soft mt-0.5">
                would need: <span className="font-mono">{g.wouldNeed}</span>
              </div>
            </Card>
          ))}
        </div>
      </section>
    </div>
  );
}

// ── parameter page ─────────────────────────────────────────────────────

export function ParameterPage({ field }: { field: FieldId }) {
  const records = useStore((s) => s.records);
  const papers = useStore((s) => s.papers);
  const contradictions = useStore((s) => s.contradictions);
  const protocols = useStore((s) => s.protocols);
  const scenarios = useStore((s) => s.scenarios);

  const def = ONTOLOGY_BY_ID[field];

  const view = useMemo(() => {
    const yearOf = (paperId: string) => papers.find((p) => p.id === paperId)?.year || undefined;
    return buildParameterView(field, records, contradictions, yearOf);
  }, [field, records, papers, contradictions]);

  const mine = useMemo(() => records.filter((r) => r.field === field), [records, field]);

  if (!def) {
    return (
      <div className="p-6">
        <PageHeader eyebrow="Ledger" title="Unknown parameter" subtitle={field} />
        <LinkButton to="/ledger">Back to the Ledger</LinkButton>
      </div>
    );
  }

  const unit = view.aggregate?.unit ?? def.canonicalUnit;
  const marks = railMarks(mine, unit);
  const excludedById = new Map(view.excluded.map((e) => [e.recordId, e.reason]));

  // Downstream consumers, resolved from the live store rather than a seeded list.
  // The protocol that exists to measure this parameter, if one declares it.
  // This is the forward leg of the experiment loop — the tornado sends a reader
  // here, and this sends them on to the bench.
  const measuredBy = protocols.flatMap((p) =>
    p.versions
      .filter((v) => v.decisive?.field === field && v.version === p.currentVersion)
      .map((v) => ({ protocol: p, decisive: v.decisive! })),
  );

  const usingProtocols = protocols.filter((p) =>
    p.versions.some((v) =>
      v.materials.some((m) => m.sourceRecordId && mine.some((r) => r.id === m.sourceRecordId)),
    ),
  );
  const usingScenarios = scenarios.filter(
    (s) =>
      s.assumptions.some((a) => a.recordId && mine.some((r) => r.id === a.recordId)) ||
      s.dims.some((d) => d.sourceRecordId && mine.some((r) => r.id === d.sourceRecordId)),
  );

  const refusal = def.canonicalUnit
    ? explainRefusal(mine.find((r) => r.unit !== def.canonicalUnit)?.unit ?? '', def.canonicalUnit)
    : null;

  return (
    <div className="p-6 max-w-[1200px]">
      <button
        className="text-caption text-ink-soft hover:text-ink inline-flex items-center gap-1 mb-2"
        onClick={() => navigate('/ledger')}
      >
        <ArrowLeft size={12} aria-hidden /> Ledger
      </button>

      {/* The rail sits beside the number it summarises. justify-between flung it
          to the far edge of a 1200px column, where it read as unrelated chrome. */}
      <div className="flex items-start gap-6 flex-wrap">
        <div className="min-w-[300px]">
          <h1 className="font-serif text-page-title font-semibold">{def.name}</h1>
          <div className="text-caption text-ink-soft mt-0.5">
            <span className="font-mono">{def.canonicalUnit || 'categorical'}</span> ·{' '}
            {FAMILY_LABEL[def.family]}
          </div>

          <div className="mt-3">
            {view.aggregate ? (
              <>
                <div className="font-num text-[28px] leading-none">
                  {fmt(view.aggregate.median)}{' '}
                  <span className="text-body text-ink-soft">{unit}</span>
                </div>
                <div className="text-caption text-ink-soft mt-1.5">
                  IQR {fmt(view.aggregate.p25)}–{fmt(view.aggregate.p75)} · range{' '}
                  {fmt(view.aggregate.min)}–{fmt(view.aggregate.max)} ·{' '}
                  <span className="font-num">{view.aggregate.nPrimary}</span> primary of{' '}
                  <span className="font-num">{view.aggregate.n}</span> in the statistic
                </div>
                <div className="text-caption text-ink-soft mt-0.5">
                  method <span className="font-mono">{view.aggregate.method}</span>
                </div>
              </>
            ) : (
              <div className="max-w-xl"><Callout kind="info" title="No median">
                {mine.length === 0
                  ? 'No records for this field yet.'
                  : mine.length === 1
                    ? 'One record. A single value is a value, not a statistic — reporting a median over it would invent a consensus that does not exist.'
                    : 'Fewer than two records can be expressed in the canonical unit, so there is nothing to take a median over.'}
              </Callout></div>
            )}
          </div>
        </div>

        {marks.length > 1 && (
          <ContradictionRail
            marks={marks}
            aggregate={view.aggregate}
            contradictions={view.contradictions}
            height={160}
            showScale
            className="shrink-0"
          />
        )}
      </div>

      {/* ── referee ── */}
      <section className="mt-6">
        <SectionTitle
          right={
            <Explain label="What does the referee check?">
              Cheap, arithmetic checks that do not need a simulation: numbering conventions that
              disagree, a degree inconsistent with a count, a fraction above one. It flags a set of
              records that cannot all be true. It does not need to know which member is wrong to be
              useful, and it never reports a check it did not run.
            </Explain>
          }
        >
          Referee
        </SectionTitle>
        {view.referee.state === 'contradicted' ? (
          <div className="space-y-2">
            {view.contradictions.map((c) => (
              <Card key={c.id} className="p-3 border-signal-error/50">
                <div className="flex items-start gap-2">
                  <AlertTriangle size={14} className="text-signal-error mt-0.5 shrink-0" aria-hidden />
                  <div className="min-w-0">
                    <div className="text-body">{c.statement}</div>
                    <div className="text-caption text-ink-soft mt-1 font-mono">
                      {c.constraint.expression} · residual {fmt(c.constraint.residual)}{' '}
                      {c.constraint.unit} · tolerance {fmt(c.constraint.tolerance)}{' '}
                      {c.constraint.unit}
                    </div>
                    <div className="text-caption text-ink-soft mt-1">
                      detected by {c.detectedBy} · {c.recordIds.length} records ·{' '}
                      <a
                        href={href('/ledger/contradictions')}
                        className="text-accent hover:underline"
                      >
                        open in the queue
                      </a>
                    </div>
                    {c.note && <div className="text-caption text-ink-soft mt-1">{c.note}</div>}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        ) : view.referee.state === 'consistent' ? (
          <p className="text-body text-ink-soft">
            Consistent under{' '}
            <span className="font-mono">{view.referee.checks.join(', ')}</span>. That is the set of
            checks that ran — not a claim that nothing else could be wrong.
          </p>
        ) : (
          <p className="text-body text-ink-soft">
            Unchecked. There are no records for this field, so no constraint had anything to bite
            on.
          </p>
        )}
      </section>

      {/* ── excluded ── */}
      {view.excluded.length > 0 && (
        <section className="mt-6">
          <SectionTitle>Held out of the statistic</SectionTitle>
          <p className="text-caption text-ink-soft mb-2 max-w-3xl">
            <span className="font-num">{view.excluded.length}</span> record
            {view.excluded.length === 1 ? '' : 's'} excluded. They stay listed below and plotted on
            the rail at reduced opacity — the rule is about medians, not about hiding data.
          </p>
          <div className="space-y-1">
            {view.excluded.map((e) => (
              <div key={e.recordId} className="text-caption">
                <span className="font-mono text-ink">{e.recordId}</span>{' '}
                <span className="text-ink-soft">— {e.reason}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ── evidence ── */}
      <section className="mt-6">
        <SectionTitle>Evidence</SectionTitle>
        {/* A fixed grid, not justify-between. The first cut put the value hard
            left and a run-on of "primary uvm4 <title>" hard right, so nothing
            aligned down the column and the title truncated into the gutter. */}
        <div className="space-y-1">
          {mine.map((r) => {
            const held = !isAggregatable(r);
            const paper = papers.find((p) => p.id === r.paperId);
            return (
              <Tick
                key={r.id}
                p={provenanceOf(r)}
                e={r.evidenceClass}
                className={cx('card px-3 py-2', held && 'opacity-75')}
              >
                <div className="grid gap-x-3 gap-y-1 items-baseline grid-cols-[7.5rem_5.5rem_1fr] sm:grid-cols-[8rem_6rem_7rem_1fr]">
                  <span className="font-num tabular-nums">
                    {String(r.value)}{' '}
                    <span className="text-ink-soft text-caption">{r.unit}</span>
                  </span>

                  <span className="text-caption">
                    {r.isPrimary ? (
                      <span className="text-ink-soft">primary</span>
                    ) : (
                      <span className="text-signal-warn">recites</span>
                    )}
                  </span>

                  <span className="text-caption text-ink-soft hidden sm:block truncate">
                    {r.organism ?? '—'}
                    {r.method ? ` · ${r.method}` : ''}
                  </span>

                  <a
                    href={href(`/trawl/sources/${r.paperId}`)}
                    className="text-caption text-accent hover:underline truncate min-w-0"
                    title={paper?.title ?? r.paperId}
                  >
                    {paper?.title ?? r.paperId}
                  </a>
                </div>
                {excludedById.has(r.id) && (
                  <div className="text-caption text-signal-warn mt-1">
                    {excludedById.get(r.id)}
                  </div>
                )}
              </Tick>
            );
          })}
          {mine.length === 0 && (
            <p className="text-body text-ink-soft">
              No records yet. This field is part of the ontology the corpus does not populate.
            </p>
          )}
        </div>
      </section>

      {/* ── strata ── */}
      {view.aggregate && view.aggregate.strata.length > 0 && (
        <section className="mt-6">
          <SectionTitle>Strata</SectionTitle>
          <p className="text-caption text-ink-soft mb-2 max-w-3xl">
            The same records grouped. A median over mixed hosts or mixed assays can hide the thing
            that actually explains the spread.
          </p>
          <div className="grid gap-1.5 sm:grid-cols-2 lg:grid-cols-3">
            {view.aggregate.strata.map((s) => (
              <Card key={`${s.label}-${s.key}`} className="p-2.5">
                <div className="text-caption text-ink-soft">{s.label}</div>
                <div className="font-num mt-0.5">
                  {fmt(s.median)} <span className="text-caption text-ink-soft">{unit}</span>
                  <span className="text-caption text-ink-soft"> · n={s.n}</span>
                </div>
              </Card>
            ))}
          </div>
        </section>
      )}

      {/* ── what would measure this ── */}
      {measuredBy.length > 0 && (
        <section className="mt-6">
          <SectionTitle>What would settle this</SectionTitle>
          {measuredBy.map(({ protocol, decisive }) => (
            <Card key={protocol.id} className="p-3 border-accent/45 bg-accent-wash/30">
              <a
                href={href(`/runbook/${protocol.id}`)}
                className="text-body text-accent hover:underline"
              >
                {protocol.title} →
              </a>
              <p className="text-caption text-ink-soft mt-1.5">{decisive.currentUncertainty}</p>
              <p className="text-caption mt-1.5">
                <span className="text-ink-soft">If it runs: </span>
                {decisive.whatWouldChange}
              </p>
            </Card>
          ))}
        </section>
      )}

      {/* ── downstream ── */}
      <section className="mt-6">
        <SectionTitle>Downstream</SectionTitle>
        {usingProtocols.length === 0 && usingScenarios.length === 0 ? (
          <p className="text-body text-ink-soft">
            Nothing in this build consumes a record from this field yet.
          </p>
        ) : (
          <div className="space-y-1.5">
            {usingProtocols.map((p) => (
              <div key={p.id} className="text-body">
                <a href={href(`/runbook/${p.id}`)} className="text-accent hover:underline">
                  {p.title}
                </a>{' '}
                <span className="text-caption text-ink-soft">protocol</span>
              </div>
            ))}
            {usingScenarios.map((s) => (
              <div key={s.id} className="text-body">
                <a href={href(`/fermos/s/${s.id}`)} className="text-accent hover:underline">
                  {s.name}
                </a>{' '}
                <span className="text-caption text-ink-soft">scenario</span>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ── ontology ── */}
      <section className="mt-6 max-w-3xl">
        <SectionTitle>Ontology</SectionTitle>
        <Card className="p-3 space-y-1.5">
          <div className="text-body">{def.definition}</div>
          <div className="text-caption text-ink-soft">
            canonical unit <span className="font-mono">{def.canonicalUnit || '—'}</span> · plausible
            range <span className="font-num">{def.range[0]}</span>–
            <span className="font-num">{def.range[1]}</span>
          </div>
          {def.requiresMethod && (
            <div className="text-caption text-signal-warn">
              Requires a method. A value in this field without its assay is not interpretable, so
              the method qualifier is mandatory rather than advisory.
            </div>
          )}
          {refusal && (
            <div className="text-caption text-ink-soft">
              <span className="text-ink">The engine refuses one conversion here:</span> {refusal}
            </div>
          )}
          {def.notes && <div className="text-caption text-ink-soft">{def.notes}</div>}
        </Card>
      </section>
    </div>
  );
}

// ── contradiction queue ────────────────────────────────────────────────

export function Contradictions() {
  const contradictions = useStore((s) => s.contradictions);
  const records = useStore((s) => s.records);

  const open = contradictions.filter((c) => c.status === 'open');
  const closed = contradictions.filter((c) => c.status !== 'open');

  return (
    <div className="p-6 max-w-[1000px]">
      <PageHeader
        eyebrow="Read · Ledger"
        title="Contradictions"
        subtitle="Sets of records that cannot all be true. Found by arithmetic over what the ontology already knows, not by judgement."
        actions={<LinkButton to="/ledger">Back to parameters</LinkButton>}
      />

      {contradictions.length === 0 && (
        <Callout kind="info" title="No contradictions detected">
          The referee has run its ontology-consistency checks over every record and found no set
          that violates a constraint. That is a statement about the checks that exist, not a claim
          that the corpus agrees with itself everywhere.
        </Callout>
      )}

      {[...open, ...closed].map((c) => {
        const involved = records.filter((r) => c.recordIds.includes(r.id));
        return (
          <Card
            key={c.id}
            className={cx('p-4 mb-3', c.status === 'open' && 'border-signal-error/50')}
          >
            <div className="flex items-start gap-2">
              <AlertTriangle
                size={15}
                className={c.status === 'open' ? 'text-signal-error mt-0.5' : 'text-ink-soft mt-0.5'}
                aria-hidden
              />
              <div className="min-w-0 flex-1">
                <div className="text-reading font-serif">{c.statement}</div>
                <div className="text-caption text-ink-soft mt-1.5 font-mono">
                  {c.constraint.expression}
                </div>
                <div className="text-caption text-ink-soft mt-1">
                  residual <span className="font-num text-signal-error">
                    {fmt(c.constraint.residual)}
                  </span>{' '}
                  {c.constraint.unit} against a tolerance of{' '}
                  <span className="font-num">{fmt(c.constraint.tolerance)}</span>{' '}
                  {c.constraint.unit} · {c.kind} · detected by {c.detectedBy} ·{' '}
                  <span
                    className={
                      c.status === 'open' ? 'text-signal-error' : 'text-accent'
                    }
                  >
                    {c.status}
                  </span>
                </div>
                {c.note && (
                  <div className="text-caption text-ink-soft mt-1.5 border-l-2 border-line pl-2">
                    {c.note}
                  </div>
                )}

                <div className="mt-3 space-y-1">
                  {involved.map((r) => (
                    <Tick key={r.id} p={provenanceOf(r)} e={r.evidenceClass} className="card p-2">
                      <div className="flex items-baseline justify-between gap-3 flex-wrap">
                        <span className="font-num">
                          {String(r.value)}{' '}
                          <span className="text-ink-soft text-caption">{r.unit}</span>
                        </span>
                        <span className="text-caption text-ink-soft">
                          <a
                            href={href(`/ledger/p/${r.field}`)}
                            className="text-accent hover:underline"
                          >
                            {fieldName(r.field)}
                          </a>{' '}
                          ·{' '}
                          <a
                            href={href(`/trawl/sources/${r.paperId}`)}
                            className="text-accent hover:underline"
                          >
                            {r.paperId}
                          </a>
                          {r.numbering && <> · {r.numbering} numbering</>}
                        </span>
                      </div>
                    </Tick>
                  ))}
                </div>
              </div>
            </div>
          </Card>
        );
      })}
    </div>
  );
}

// ── not yet built ──────────────────────────────────────────────────────

/**
 * A part named in the architecture whose surface does not exist yet. Says so
 * plainly, and says what it will be, rather than rendering "route not found" —
 * which reads as a bug — or a fake screen, which would be worse.
 */
export function UnbuiltPart({ name, blurb }: { name: string; blurb: string }) {
  return (
    <div className="p-6 max-w-2xl">
      <PageHeader
        eyebrow="Not built yet"
        title={name}
        subtitle="Specified in OF-FE-003, not implemented in this build."
      />
      <Callout kind="info" title="Nothing here yet">
        <p className="mb-2">{blurb}</p>
        <p>
          It is in the rail because the rail is the architecture, and hiding an unbuilt part
          would misrepresent the shape of the system. It is marked so the gap is not mistaken
          for a broken link.
        </p>
      </Callout>
    </div>
  );
}
