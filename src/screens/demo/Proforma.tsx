// Proforma — Archetype 3 (the capacity screen) and Archetype 4 (greenfield).
//
// ARCHETYPE 3 IS THE TECHNICAL CENTRE of the demo and the table has one rule
// that matters more than its columns: FAILED CANDIDATES STAY IN IT. Greyed,
// sorted to the bottom, with the failing axis named. A screen that shows only
// survivors is a screen a reviewer distrusts, because they cannot tell whether
// the filter was a judgement or a sieve.
//
// The other thing it must show is the RESCUE — a candidate that fails at its
// naive operating point and survives de-rated, where the de-rating comes from a
// different archetype's deliverable. That link is the argument for the shared
// object pool, so it renders as a link rather than as a sentence.
import { useMemo, useState } from 'react';
import { ArrowUpRight } from 'lucide-react';

import type { Candidate } from '@/data/demo/types';
import { PLANTS, PLANT_BY_ID, ORGANISM_BY_ID, HS_CODES } from '@/data/demo/core';
import { ACCESSION_BY_ID } from '@/data/demo/accessions';
import {
  CANDIDATES,
  DELIVERABLES,
  DELIVERABLE_BY_ID,
  DISCLOSURES,
  BAGASSE_CONCEPTS,
  AUX_ORGANISMS,
} from '@/data/demo/archetypes';
import { matchEnvelope, plantCeilings } from '@/lib/demo';
import { href, navigate } from '@/router';
import { PageHeader, Card, SectionTitle, EmptyState, Callout, cx } from '@/components/ui';
import { AccessionValue } from '@/components/demo/AccessionValue';
import { EnvelopeMatch } from '@/components/demo/EnvelopeMatch';
import { ClaimOverlay } from '@/components/demo/ClaimOverlay';
import { CapexCurve } from '@/components/demo/CapexCurve';
import { DisclosureSection } from './Fermos';
import { DemoFooter } from '@/components/demo/DemoFooter';

function organismName(id: string): string {
  const o = ORGANISM_BY_ID[id] ?? AUX_ORGANISMS.find((x) => x.id === id);
  return o ? o.binomial : id;
}

const VERDICT_ORDER: Record<string, number> = {
  promoted: 0,
  viable: 1,
  marginal: 2,
  excluded: 3,
};

// ── /proforma — the index ──────────────────────────────────────────────

export function ProformaIndex() {
  const screens = DELIVERABLES.filter((d) => d.payload.kind === 'capacity-screen');
  const concepts = DELIVERABLES.filter((d) => d.payload.kind === 'facility-concept');
  return (
    <div className="p-6 max-w-[900px]">
      <PageHeader title="Proforma" subtitle="Techno-economics against an explicit regional and temporal basis." />
      <div className="space-y-3">
        {[...screens, ...concepts].map((d) => (
          <Card key={d.id}>
            <a
              href={href(
                d.payload.kind === 'capacity-screen'
                  ? `/proforma/screen/${d.payload.plantId}`
                  : `/proforma/concept/${d.id}`,
              )}
              className="hover:text-accent"
            >
              <div>{d.title}</div>
              <div className="text-caption text-ink-soft mt-0.5">{d.query}</div>
            </a>
          </Card>
        ))}
      </div>
      <DemoFooter />
    </div>
  );
}

// ── /proforma/screen/:plantId — ARCHETYPE 3 ────────────────────────────

export function CapacityScreen({ plantId }: { plantId: string }) {
  const plant = PLANT_BY_ID[plantId] ?? PLANTS[0];
  const dlv = DELIVERABLES.find(
    (d) => d.payload.kind === 'capacity-screen' && d.payload.plantId === plant.id,
  );
  const disclosures = dlv ? DISCLOSURES.filter((d) => dlv.disclosureCandidateIds.includes(d.id)) : [];
  const ceilings = useMemo(() => plantCeilings(plant), [plant]);

  const rows = useMemo(
    () =>
      [...CANDIDATES]
        .map((c) => ({ c, m: c.match ?? matchEnvelope(plant, c) }))
        .sort((a, b) => {
          const va = VERDICT_ORDER[a.c.verdict ?? (a.m.feasible ? 'viable' : 'excluded')] ?? 9;
          const vb = VERDICT_ORDER[b.c.verdict ?? (b.m.feasible ? 'viable' : 'excluded')] ?? 9;
          return va - vb;
        }),
    [plant],
  );

  const failing = rows.filter((r) => !r.m.feasible);
  const byAxis = useMemo(() => {
    const m = new Map<string, number>();
    for (const r of failing) {
      const k = r.m.bindingAxis ?? 'unknown';
      m.set(k, (m.get(k) ?? 0) + 1);
    }
    return [...m].sort((a, b) => b[1] - a[1]);
  }, [failing]);

  return (
    <div className="p-6 max-w-[1500px]">
      <PageHeader
        title={dlv?.title ?? `${plant.name} — capacity screen`}
        subtitle={dlv?.query ?? `What can this plant actually make?`}
      />

      <Callout>
        {failing.length} of {rows.length} candidates fail, on {byAxis.length} distinct axes:{' '}
        {byAxis.map(([a, n]) => `${n} on ${a}`).join(', ')}. Note what is NOT in that list. At one
        atmosphere oxygen transfer fails{' '}
        <span className="font-num">
          {(ceilings.coolingCeiling - ceilings.otrCeiling).toFixed(1)}
        </span>{' '}
        mmol before cooling does, so cooling never binds — which is the opposite of what a
        tropical-siting argument predicts. Transfer fails first; cooling is what stops you fixing
        it.
      </Callout>

      <Card className="mt-4 p-0 overflow-x-auto">
        <table className="w-full text-body" data-density="dense">
          <thead className="text-caption text-ink-soft text-left">
            <tr className="border-b border-line">
              <th className="font-normal p-2">Candidate</th>
              <th className="font-normal p-2">Organism</th>
              <th className="font-normal p-2">Binding constraint</th>
              <th className="font-normal p-2 text-right">Headroom</th>
              <th className="font-normal p-2">Patent position</th>
              <th className="font-normal p-2 text-right">Feedstock</th>
              <th className="font-normal p-2 text-right">Import, at CIF</th>
              <th className="font-normal p-2">Regulatory</th>
              <th className="font-normal p-2 text-right">To revenue</th>
              <th className="font-normal p-2">Verdict</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(({ c, m }) => {
              const verdict = c.verdict ?? (m.feasible ? 'viable' : 'excluded');
              const dead = verdict === 'excluded';
              const binding = m.axes.find((a) => a.binding);
              const feedstock = ACCESSION_BY_ID[c.feedstockCostAccessionId];
              // Keyed by FIELD, not by position: an Accession list whose order
              // carries meaning is one a reorder silently corrupts.
              const trade = c.tradeAccessionIds.map((id) => ACCESSION_BY_ID[id]).filter(Boolean);
              const volume = trade.find((a) => a.field === 'import_volume');
              const cif = trade.find((a) => a.field === 'import_cif');
              return (
                <tr
                  key={c.id}
                  className={cx(
                    'border-b border-line/50 hover:bg-[rgb(var(--accent-wash))]/30 cursor-pointer align-top',
                    dead && 'opacity-55',
                  )}
                  onClick={() => navigate(`/proforma/screen/${plant.id}/c/${c.id}`)}
                >
                  <td className="p-2">
                    <span className="font-num text-ink-soft mr-1.5">{c.id}</span>
                    {c.product}
                  </td>
                  <td className="p-2 italic text-caption">{organismName(c.organismId)}</td>
                  <td className="p-2 text-caption">
                    {m.feasible ? (
                      <span className="text-ink-soft">fits</span>
                    ) : (
                      <span className="text-signal-error">{m.bindingAxis}</span>
                    )}
                  </td>
                  <td className="p-2 text-right font-num text-caption whitespace-nowrap">
                    {binding ? `${(binding.headroom * 100).toFixed(1)} %` : '—'}
                  </td>
                  <td className="p-2">
                    <div className="flex flex-wrap gap-1">
                      <ClaimOverlay
                        rows={[{ step: '', positions: c.patentPosition }]}
                        className="[&_.min-w-\\[13rem\\]]:hidden"
                      />
                    </div>
                  </td>
                  <td className="p-2 text-right whitespace-nowrap">
                    {feedstock ? <AccessionValue id={feedstock.id} /> : <span className="text-ink-soft">—</span>}
                  </td>
                  {/* NOT a displacement value. `importDisplacementUSD` needs a
                      landed cost and this pool holds none for these candidates,
                      so what is shown is the two quantities that DO exist — the
                      volume and the CIF price — and the header says which. A
                      number computed from a landed cost nobody measured would be
                      the most quotable thing on this screen and the least
                      defensible. */}
                  <td className="p-2 text-right font-num text-caption whitespace-nowrap">
                    {volume && cif ? (
                      <>
                        {volume.normalized.value} {volume.normalized.unit}
                        <span className="text-ink-soft"> @ </span>
                        {cif.normalized.value} {cif.normalized.unit}
                      </>
                    ) : (
                      <span className="text-ink-soft">—</span>
                    )}
                  </td>
                  <td className="p-2 text-caption">{c.regulatoryClass}</td>
                  <td className="p-2 text-right font-num text-caption">{c.timeToRevenueMonths} mo</td>
                  <td className="p-2 text-caption">
                    <span
                      className={cx(
                        verdict === 'promoted' && 'text-signal-open',
                        verdict === 'excluded' && 'text-signal-error',
                      )}
                    >
                      {verdict}
                    </span>
                    {c.rescue && (
                      <span className="ml-1.5 text-caption text-accent">rescued</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Card>

      <div className="text-caption text-ink-soft mt-2 max-w-prose">
        Failed candidates are greyed and sorted to the bottom rather than filtered out. A screen
        that shows only survivors cannot be told apart from a screen with a bug in its filter.
      </div>
      <div className="text-caption text-ink-soft mt-1 max-w-prose">
        The import column is the volume and the CIF price, not a displacement value. Displacing an
        import is worth <span className="font-num">min(capacity, volume) × (CIF − landed cost)</span>,
        and this pool holds no landed cost for these candidates. The arithmetic is in{' '}
        <span className="font-num">lib/demo.ts</span> and will run the moment a landed cost is
        measured; until then the column shows what is on record rather than what would be
        persuasive.
      </div>

      <DisclosureSection disclosures={disclosures} />
      <DemoFooter />
    </div>
  );
}

// ── /proforma/screen/:plantId/c/:candidateId ───────────────────────────

export function CandidateDetail({ plantId, candidateId }: { plantId: string; candidateId: string }) {
  const plant = PLANT_BY_ID[plantId] ?? PLANTS[0];
  const c = CANDIDATES.find((x) => x.id === candidateId);
  if (!c) return <EmptyState title={`No candidate ${candidateId}`} body="Not on this screen." />;
  const m = c.match ?? matchEnvelope(plant, c);
  const hs = HS_CODES.find((h) => h.code === c.hsCode);

  return (
    <div className="p-6 max-w-[1000px]">
      <PageHeader
        title={`${c.id} — ${c.product}`}
        subtitle={
          <a href={href(`/proforma/screen/${plant.id}`)} className="hover:text-accent">
            ← back to the screen
          </a>
        }
      />

      <Card>
        <SectionTitle>Why it survived, or did not</SectionTitle>
        <div className="mt-2">
          <EnvelopeMatch match={m} />
        </div>
        <div className="text-caption text-ink-soft mt-3 max-w-prose">{c.note}</div>
      </Card>

      {c.rescue && (
        <Card className="mt-4">
          <SectionTitle>Rescued</SectionTitle>
          <div className="text-caption mt-1 max-w-prose">{c.rescue.change}</div>
          <div className="text-caption text-ink-soft mt-2 max-w-prose">
            <span className="text-ink">What it costs: </span>
            {c.rescue.cost}
          </div>
          <div className="text-caption mt-2">
            The de-rating comes from{' '}
            <a
              href={href(`/fermos/gap/${c.rescue.byDeliverableId}`)}
              className="text-accent hover:underline inline-flex items-center gap-1"
            >
              {c.rescue.byDeliverableId}
              <ArrowUpRight className="w-3 h-3" />
            </a>
            , a different archetype's deliverable. This candidate is promoted because another
            question was asked first.
          </div>
        </Card>
      )}

      <Card className="mt-4">
        <SectionTitle>Patent position</SectionTitle>
        <div className="mt-2">
          <ClaimOverlay rows={[{ step: c.product, positions: c.patentPosition }]} />
        </div>
      </Card>

      <Card className="mt-4">
        <SectionTitle>Trade basis</SectionTitle>
        {hs && (
          <div className="text-caption text-ink-soft">
            HS {hs.code} — {hs.description}
          </div>
        )}
        <div className="flex flex-wrap gap-4 mt-2">
          {c.tradeAccessionIds.map((id) => (
            <AccessionValue key={id} id={id} />
          ))}
          <AccessionValue id={c.feedstockCostAccessionId} />
        </div>
      </Card>

      <DemoFooter />
    </div>
  );
}

// ── /proforma/concept/:id — ARCHETYPE 4 ────────────────────────────────

export function FacilityConceptPage({ deliverableId }: { deliverableId: string }) {
  const dlv =
    DELIVERABLE_BY_ID[deliverableId] ?? DELIVERABLES.find((d) => d.payload.kind === 'facility-concept');
  const concepts =
    dlv && dlv.payload.kind === 'facility-concept' ? dlv.payload.concepts : BAGASSE_CONCEPTS;
  const disclosures = dlv ? DISCLOSURES.filter((d) => dlv.disclosureCandidateIds.includes(d.id)) : [];
  const [openId, setOpenId] = useState(concepts[0]?.id ?? '');
  const open = concepts.find((c) => c.id === openId) ?? concepts[0];

  if (!concepts.length) return <EmptyState title="No concepts" body="Nothing to render." />;

  return (
    <div className="p-6 max-w-[1200px]">
      <PageHeader title={dlv?.title ?? 'Greenfield concept'} subtitle={dlv?.query} />

      <Card>
        <SectionTitle>Capex against scale</SectionTitle>
        <div className="mt-2">
          <CapexCurve concepts={concepts} />
        </div>
      </Card>

      <div className="flex flex-wrap gap-2 mt-4">
        {concepts.map((c) => (
          <button
            key={c.id}
            className={cx('btn', c.id === open.id && 'chip-active')}
            onClick={() => setOpenId(c.id)}
          >
            {c.id}
          </button>
        ))}
      </div>

      <Card className="mt-3">
        <SectionTitle>{open.name}</SectionTitle>
        <div className="text-caption text-ink-soft mt-0.5 font-num">
          {open.scaleTonnesPerYear.toLocaleString()} t a⁻¹ · {(open.capexUSD / 1e6).toFixed(1)} M USD ·{' '}
          {open.capexAccuracyClass} · risk {open.riskLevel}
        </div>

        <div className="grid lg:grid-cols-2 gap-6 mt-4">
          <div>
            <div className="text-caption text-ink-soft mb-1">Block flow</div>
            {open.blockFlow.map((b, i) => (
              <div key={i} className="border-l-2 border-line pl-3 py-1">
                <div className="text-caption">{b.block}</div>
                <div className="text-caption text-ink-soft">{b.detail}</div>
                <div className="flex flex-wrap gap-3 mt-1">
                  {b.accessionIds.map((id) => (
                    <AccessionValue key={id} id={id} />
                  ))}
                </div>
              </div>
            ))}
          </div>

          <div>
            <div className="text-caption text-ink-soft mb-1">Major equipment</div>
            <table className="w-full text-caption">
              <tbody>
                {open.majorEquipment.map((e, i) => (
                  <tr key={i} className="border-b border-line/50">
                    <td className="py-1 pr-2">{e.item}</td>
                    <td className="py-1 pr-2 text-ink-soft">{e.sizingBasis}</td>
                    <td className="py-1 text-right font-num whitespace-nowrap">
                      {(e.costUSD / 1e6).toFixed(2)} M
                    </td>
                  </tr>
                ))}
                <tr>
                  <td className="py-1 font-medium">Total</td>
                  <td />
                  <td className="py-1 text-right font-num">
                    {(open.majorEquipment.reduce((s, e) => s + e.costUSD, 0) / 1e6).toFixed(2)} M
                  </td>
                </tr>
              </tbody>
            </table>
            <div className="text-caption text-ink-soft mt-1">
              The capex above is the sum of these lines, checked by the seed gate rather than
              stated alongside them.
            </div>

            <div className="text-caption text-ink-soft mt-4 mb-1">NPV sensitivity</div>
            {[...open.npvSensitivity]
              .sort((a, b) => Math.abs(b.highPct - b.lowPct) - Math.abs(a.highPct - a.lowPct))
              .map((s, i) => {
                const span = Math.abs(s.highPct - s.lowPct);
                return (
                  <div key={i} className="flex items-center gap-2 text-caption py-0.5">
                    <span className="w-40 shrink-0 truncate" title={s.parameter}>
                      {i + 1}. {s.parameter}
                    </span>
                    <div className="flex-1 h-2 bg-[rgb(var(--line))]/40 relative">
                      <div
                        className="absolute inset-y-0 bg-[rgb(var(--accent))]"
                        style={{ width: `${Math.min(100, span)}%` }}
                      />
                    </div>
                    <span className="font-num w-24 text-right shrink-0">
                      {s.lowPct.toFixed(0)} / +{s.highPct.toFixed(0)} %
                    </span>
                  </div>
                );
              })}
          </div>
        </div>

        <div className="mt-4">
          <div className="text-caption text-ink-soft mb-1">Patent overlay</div>
          <ClaimOverlay
            rows={open.patentOverlay.map((p) => ({ step: p.step, status: p.status, familyIds: p.familyIds }))}
          />
        </div>

        <div className="text-caption text-ink-soft mt-3 font-num">
          Breakeven at {open.breakevenTonnesPerYear.toLocaleString()} t a⁻¹ · opex{' '}
          {open.opexPerTonneUSD.toLocaleString()} USD t⁻¹
        </div>
      </Card>

      <DisclosureSection disclosures={disclosures} />
      <DemoFooter />
    </div>
  );
}
