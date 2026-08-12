// Design detail — the tier cascade (OF-FE-004 §2, OF-FE-003 §8.5).
//
// The cascade is four segments and two of them are absent, which is the point.
// A design that cleared T0 and T3 without T1 or T2 says the economics were
// modelled while the biology went unchecked — the actual state of the field, and
// a more useful thing to show than a full green row would be.
import { useMemo } from 'react';
import { ArrowLeft, ArrowRight } from 'lucide-react';
import { useStore } from '@/store';
import { DESIGNS } from '@/data/designs';
import { cascade } from '@/engine/designs';
import { fmt } from '@/engine/units';
import { fieldName } from '@/data/ontology';
import { href, navigate } from '@/router';
import { Card, PageHeader, SectionTitle, Callout, Explain, LinkButton, cx } from '@/components/ui';
import { Tick } from '@/components/Provenance';
import type { DesignRecord, TierResult } from '@/data/types';

const STATE_STYLE: Record<TierResult['state'], string> = {
  passed: 'bg-accent/15 border-accent/50 text-accent',
  failed: 'bg-signal-error/10 border-signal-error/50 text-signal-error',
  // Absent is visually distinct from both. It is not a soft pass.
  absent: 'bg-surface-1 border-line text-ink-soft border-dashed',
};

const TIER_LABEL: Record<string, string> = {
  T0: 'T0 · balance',
  T1: 'T1 · flux',
  T2: 'T2 · reactor',
  T3: 'T3 · cost',
};

export function DesignIndex() {
  const scenarios = useStore((st) => st.scenarios);

  // Grouped by scenario and carrying the MSP. A flat list of 19 rows showing
  // only a label and four badges omits the number designs exist to be compared
  // on, and makes the reader open each one to find it.
  const groups = scenarios
    .map((sc) => ({ sc, designs: DESIGNS.filter((d) => d.scenarioId === sc.id) }))
    .filter((g) => g.designs.length > 0);

  return (
    <div className="p-6 max-w-[1100px]">
      <PageHeader
        eyebrow="Reason · fermOS"
        title="Designs"
        subtitle="Points in the authored sweep grids, re-presented as designs. Modelled economics, not validated."
        actions={<LinkButton to="/fermos">Scenarios</LinkButton>}
      />

      {groups.map(({ sc, designs }) => (
        <section key={sc.id} className="mb-6">
          <SectionTitle>{sc.name}</SectionTitle>
          <div className="overflow-x-auto">
            <table className="w-full text-body">
              <thead>
                <tr className="text-caption uppercase tracking-wide text-ink-soft border-b border-line">
                  <th className="text-left font-medium py-1.5 pr-3">Design</th>
                  {/* The unit is constant across a scenario's designs, so it
                      belongs in the header rather than repeated 19 times. */}
                  <th className="text-right font-medium py-1.5 pr-6 whitespace-nowrap">
                    MSP{' '}
                    <span className="normal-case tracking-normal">
                      {designs[0]?.tiers.find((t) => t.tier === 'T3')?.values.msp?.unit ?? ''}
                    </span>
                  </th>
                  <th className="text-left font-medium py-1.5">Cascade</th>
                </tr>
              </thead>
              <tbody>
                {designs.map((d) => {
                  const msp = d.tiers.find((t) => t.tier === 'T3')?.values.msp;
                  return (
                    <tr key={d.id} className="border-b border-line/60 hover:bg-accent-wash/40">
                      <td className="py-1.5 pr-3">
                        {/* A real link, not a div with cursor-pointer: it has to
                            be reachable by keyboard and openable in a new tab. */}
                        <a href={href(`/fermos/d/${d.id}`)} className="text-ink hover:text-accent">
                          {d.label.replace(`${sc.name} — `, '')}
                        </a>
                        <span className="text-caption text-ink-soft font-mono ml-2">{d.id}</span>
                      </td>
                      <td className="py-1.5 pr-6 text-right font-num tabular-nums whitespace-nowrap">
                        {msp ? fmt(msp.value) : '—'}
                      </td>
                      <td className="py-1.5">
                        <Cascade design={d} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      ))}
    </div>
  );
}

function Cascade({ design }: { design: DesignRecord }) {
  return (
    <div className="flex items-center gap-1 shrink-0">
      {cascade(design).map((t) => (
        <span
          key={t.tier}
          className={cx(
            'text-caption border rounded-[3px] px-1.5 py-0.5 whitespace-nowrap',
            STATE_STYLE[t.state],
          )}
          title={t.state === 'absent' ? t.absentReason : t.bindingConstraint}
        >
          {t.tier} {t.state === 'absent' ? '—' : t.state === 'passed' ? '✓' : '✗'}
        </span>
      ))}
    </div>
  );
}

export function DesignDetail({ designId }: { designId: string }) {
  const records = useStore((s) => s.records);
  const design = useMemo(() => DESIGNS.find((d) => d.id === designId), [designId]);

  if (!design) {
    return (
      <div className="p-6">
        <PageHeader eyebrow="fermOS" title="Design not found" subtitle={designId} />
        <LinkButton to="/fermos/d">Back to designs</LinkButton>
      </div>
    );
  }

  const t3 = design.tiers.find((t) => t.tier === 'T3');
  const msp = t3?.values.msp;

  return (
    <div className="p-6 max-w-[1100px]">
      <button
        className="text-caption text-ink-soft hover:text-ink inline-flex items-center gap-1 mb-2"
        onClick={() => navigate('/fermos/d')}
      >
        <ArrowLeft size={12} aria-hidden /> Designs
      </button>

      <PageHeader
        eyebrow={<span className="font-mono">{design.id}</span>}
        title={design.label}
        subtitle="Demo model v0 — illustrative economics, not validated."
      />

      {/* ── cascade ── */}
      <section className="mb-5">
        <SectionTitle
          right={
            <Explain label="Why are two tiers empty?">
              T1 needs a genome-scale metabolic model and T2 a reactor model. Neither exists in
              this build, so both render absent rather than passed. A cascade showing four greens
              would claim the biology was checked when only the cost model ran.
            </Explain>
          }
        >
          Tier cascade
        </SectionTitle>

        <div className="space-y-1.5 max-w-3xl">
          {cascade(design).map((t) => (
            <Card
              key={t.tier}
              className={cx('px-3 py-2', t.state === 'absent' && 'border-dashed')}
            >
              <div className="flex items-baseline justify-between gap-3 flex-wrap">
                <span className="text-body font-medium">{TIER_LABEL[t.tier]}</span>
                <span
                  className={cx(
                    'text-caption border rounded-[3px] px-1.5 py-0.5',
                    STATE_STYLE[t.state],
                  )}
                >
                  {t.state}
                </span>
              </div>

              {t.state === 'absent' ? (
                <p className="text-caption text-ink-soft mt-1">{t.absentReason}</p>
              ) : (
                <>
                  {/* The binding constraint is the most useful string on the
                      page, so it gets the most prominent type in the row. */}
                  <p className="text-body mt-1">
                    {t.bindingConstraint}{' '}
                    <span className="text-caption text-ink-soft">
                      · engine <span className="font-mono">{t.engineVersion}</span>
                    </span>
                  </p>
                </>
              )}
            </Card>
          ))}
        </div>
      </section>

      {/* ── cost ── */}
      {t3 && (
        <section className="mb-5">
          <SectionTitle>Minimum selling price</SectionTitle>
          <Tick p="demo" className="card p-3 max-w-3xl">
            <div className="font-num text-[26px] leading-none">
              {msp ? fmt(msp.value) : '—'}{' '}
              <span className="text-body text-ink-soft">{msp?.unit}</span>
            </div>
            <p className="text-caption text-signal-warn mt-2">
              A point estimate, not a distribution. The sweep grid holds one MSP per point, so
              there is no interval to report — and error bars of zero width would read as
              certainty rather than as absence.
            </p>
          </Tick>
        </section>
      )}

      {/* ── tornado ── */}
      {t3?.sensitivity && t3.sensitivity.length > 0 && (
        <section className="mb-5">
          <SectionTitle
            right={
              <Explain label="Why does this link out?">
                The bar at the top is the parameter whose uncertainty moves the answer most. Its
                link to a parameter page is the entry to the experiment loop: see what the corpus
                knows, find the protocol that would measure it, run it, deposit the result.
              </Explain>
            }
          >
            Sensitivity
          </SectionTitle>
          <div className="space-y-1.5">
            {[...t3.sensitivity]
              .sort((a, b) => Math.abs(b.rho) - Math.abs(a.rho))
              .map((s) => (
                <div key={s.label} className="flex items-center gap-2">
                  <div className="w-[190px] shrink-0 text-caption">
                    {s.field ? (
                      <a
                        href={href(`/ledger/p/${s.field}`)}
                        className="text-accent hover:underline"
                        title={`Open ${fieldName(s.field)}`}
                      >
                        {s.label} <ArrowRight size={10} className="inline" aria-hidden />
                      </a>
                    ) : (
                      // A capital or labour line is a cost input, not a Ledger
                      // parameter. Linking it would imply a binding that is not
                      // there.
                      <span className="text-ink-soft" title="A cost input, not an ontology parameter">
                        {s.label}
                      </span>
                    )}
                  </div>
                  <div className="flex-1 h-3 bg-surface-1 rounded-[2px] overflow-hidden">
                    <div
                      className="h-full bg-signal-warn/60"
                      style={{ width: `${Math.min(100, Math.abs(s.rho) * 100)}%` }}
                    />
                  </div>
                  <span className="font-num text-caption text-ink-soft w-14 text-right">
                    {(s.rho * 100).toFixed(0)}%
                  </span>
                </div>
              ))}
          </div>
        </section>
      )}

      {/* ── consumed and scope ── */}
      <section className="grid gap-3 lg:grid-cols-2">
        <Card className="p-3">
          <div className="text-caption uppercase tracking-wide text-ink-soft mb-1.5">
            Records consumed
          </div>
          {design.consumedRecordIds.length === 0 ? (
            <p className="text-body text-ink-soft">None — this design binds no Ledger record.</p>
          ) : (
            <div className="space-y-1">
              {design.consumedRecordIds.map((id) => {
                const r = records.find((x) => x.id === id);
                return (
                  <div key={id} className="text-caption">
                    <a
                      href={href(`/ledger/records?record=${id}`)}
                      className="font-mono text-accent hover:underline"
                    >
                      {id}
                    </a>
                    {r && (
                      <span className="text-ink-soft">
                        {' '}
                        — {fieldName(r.field)} = {String(r.value)} {r.unit}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </Card>

        <Card className="p-3">
          <div className="text-caption uppercase tracking-wide text-ink-soft mb-1.5">Scope</div>
          <Callout kind="warn" title="Unevaluated, not clear">
            Parchment holds no parsed claim bounds for any of its six patents, so nothing has
            tested this configuration against a claim. The stored value reads{' '}
            <span className="font-mono">{design.scope}</span> only as a default —{' '}
            <span className="font-mono">scopeEvaluated</span> is false, and that is the field to
            read.
          </Callout>
        </Card>
      </section>
    </div>
  );
}
