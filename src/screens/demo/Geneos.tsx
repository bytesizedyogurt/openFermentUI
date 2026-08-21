// geneOS — Archetype 2, route comparison with the claim overlay.
//
// THE FINDING IS A REVERSAL and the screen has to make it visible before the
// text does: the biochemistry ranks the routes one way and the expiry dates
// rank them the other. So the table is sorted by the biochemical ranking and
// the claim overlay runs down the same rows — the eye travels down a column of
// filled enclosure chips and arrives at the winner, which is the wrong winner.
//
// The per-step detail is where the reversal becomes concrete: the wild-type
// enzyme is free and the variant that makes the route viable is not.
import { useMemo } from 'react';

import type { ClaimStatus, EnzymeStep, Route } from '@/data/demo/types';
import { ROUTES_3HP, DELIVERABLES, DISCLOSURES, AUX_ORGANISMS } from '@/data/demo/archetypes';
import { ORGANISM_BY_ID } from '@/data/demo/core';
import { ACCESSION_BY_ID } from '@/data/demo/accessions';
import { PATENT_BY_ID } from '@/data/demo/patents';
import { href, navigate } from '@/router';
import { PageHeader, Card, SectionTitle, EmptyState, Callout, cx } from '@/components/ui';
import { AccessionValue } from '@/components/demo/AccessionValue';
import { ClaimOverlay, OpenSurfaceSummary } from '@/components/demo/ClaimOverlay';
import { DisclosureSection } from './Fermos';
import { DemoFooter } from '@/components/demo/DemoFooter';


import { partEyebrow } from '@/data/parts';

/** Movement · part · pool, from the one table that names the parts. */
const EYEBROW = partEyebrow('geneos', 'demo');
/**
 * A step's claims, flattened to one chip per jurisdiction.
 *
 * `EnzymeStep.claims` groups by family and lists the jurisdictions each family
 * covers; the overlay reads one chip per jurisdiction, because a reader is
 * asking "can I practise this HERE" and not "who owns this". Flattening here
 * rather than in the component keeps the component reading a single shape.
 */
function stepPositions(step: EnzymeStep) {
  const byJurisdiction = new Map<string, { jurisdiction: string; status: ClaimStatus; familyIds: string[] }>();
  for (const c of step.claims) {
    for (const j of c.jurisdictions) {
      const prev = byJurisdiction.get(j);
      // Where two families touch the same jurisdiction, the LOUDER status wins:
      // one expired family does not open a step another still encloses.
      if (!prev || RANKED.indexOf(c.status) < RANKED.indexOf(prev.status)) {
        byJurisdiction.set(j, { jurisdiction: j, status: c.status, familyIds: [...(prev?.familyIds ?? []), c.patentFamilyId] });
      } else {
        prev.familyIds.push(c.patentFamilyId);
      }
    }
  }
  return [...byJurisdiction.values()];
}

const RANKED: ClaimStatus[] = ['enclosed', 'expiring', 'pending', 'never-nationalised', 'expired', 'no-claim-found'];

function organismName(id: string): string {
  const o = ORGANISM_BY_ID[id] ?? AUX_ORGANISMS.find((x) => x.id === id);
  return o ? o.binomial : id;
}

export function RouteComparison({ productId }: { productId: string }) {
  const routes = useMemo(() => ROUTES_3HP.filter((r) => r.productId === productId), [productId]);
  const dlv = DELIVERABLES.find(
    (d) => d.payload.kind === 'route-comparison' && d.payload.productId === productId,
  );
  const disclosures = dlv ? DISCLOSURES.filter((d) => dlv.disclosureCandidateIds.includes(d.id)) : [];

  if (!routes.length) {
    return <EmptyState title={`No routes for ${productId}`} body="This pool holds no route comparison for that product." />;
  }

  // Ranked by the biochemistry, deliberately. Sorting by openness would hide
  // the reversal, which is the finding.
  const ranked = useMemo(
    () =>
      [...routes].sort((a, b) => {
        const ya = ACCESSION_BY_ID[a.theoreticalYieldAccessionId]?.normalized.value ?? 0;
        const yb = ACCESSION_BY_ID[b.theoreticalYieldAccessionId]?.normalized.value ?? 0;
        return yb - ya;
      }),
    [routes],
  );

  return (
    <>
      <PageHeader eyebrow={EYEBROW}
        title={dlv?.title ?? `${productId} — route comparison`}
        subtitle={dlv?.query ?? 'Which route, and is it available?'}
      />

      <Callout>
        The rows are ranked by yield ceiling, which is the ranking a biochemist would give. Read
        the open-surface column down the same order. The route that wins on stoichiometry is the
        one with the most enclosure on it, and nothing in the chemistry says so.
      </Callout>

      <Card className="mt-4 p-0 overflow-x-auto">
        <table className="w-full text-body">
          <thead className="text-caption text-ink-soft text-left">
            <tr className="border-b border-line">
              <th className="font-normal p-2">Route</th>
              <th className="font-normal p-2">Theoretical yield</th>
              <th className="font-normal p-2">O₂ demand</th>
              <th className="font-normal p-2">Downstream</th>
              <th className="font-normal p-2">Open surface</th>
            </tr>
          </thead>
          <tbody>
            {ranked.map((r, i) => (
              <tr
                key={r.id}
                className="border-b border-line/50 hover:bg-[rgb(var(--accent-wash))]/30 cursor-pointer align-top"
                onClick={() => navigate(`/geneos/routes/${productId}/${r.id}`)}
              >
                <td className="p-2">
                  <div className="flex items-baseline gap-2">
                    <span className="font-num text-ink-soft">{i + 1}</span>
                    <span>{r.name}</span>
                  </div>
                  <div className="text-caption text-ink-soft mt-0.5 max-w-prose">{r.summary}</div>
                </td>
                <td className="p-2 whitespace-nowrap">
                  <AccessionValue id={r.theoreticalYieldAccessionId} />
                </td>
                <td className="p-2 text-caption">{r.oxygenDemand}</td>
                <td className="p-2 text-caption">{r.downstreamDifficulty}</td>
                <td className="p-2 whitespace-nowrap">
                  <OpenSurfaceSummary {...r.openSurface} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <div className="grid lg:grid-cols-2 gap-4 mt-6">
        {ranked.map((r) => (
          <Card key={r.id}>
            <SectionTitle>{r.name}</SectionTitle>
            <div className="mt-2">
              <ClaimOverlay
                rows={r.steps.map((s) => ({ step: s.name, positions: stepPositions(s) }))}
              />
            </div>
            <div className="mt-2 text-caption">
              <a href={href(`/geneos/routes/${productId}/${r.id}`)} className="text-accent hover:underline">
                per-step detail →
              </a>
            </div>
          </Card>
        ))}
      </div>

      {dlv && dlv.payload.kind === 'route-comparison' && (
        <Card className="mt-6">
          <SectionTitle>Recommendation</SectionTitle>
          <div className="mt-1 max-w-prose">{dlv.payload.recommendation}</div>
          <div className="mt-3 border-l-2 border-signal-closed pl-3">
            <div className="text-caption font-medium text-signal-closed">
              The asymmetry
            </div>
            <div className="text-caption mt-0.5 max-w-prose">{dlv.payload.asymmetry}</div>
          </div>
        </Card>
      )}

      <DisclosureSection disclosures={disclosures} />
      <DemoFooter />
    </>
  );
}

// ── /geneos/routes/:productId/:routeId ─────────────────────────────────

export function RouteDetail({ productId, routeId }: { productId: string; routeId: string }) {
  const route = ROUTES_3HP.find((r) => r.id === routeId && r.productId === productId);
  if (!route) return <EmptyState title={`No route ${routeId}`} body="Not in this comparison." />;

  return (
    <>
      <PageHeader eyebrow={EYEBROW}
        title={route.name}
        subtitle={
          <a href={href(`/geneos/routes/${productId}`)} className="hover:text-accent">
            ← back to the comparison
          </a>
        }
      />
      <div className="text-caption text-ink-soft max-w-prose mb-4">{route.summary}</div>

      <Card>
        <SectionTitle>Steps</SectionTitle>
        <div className="mt-2 space-y-4">
          {route.steps.map((s, i) => (
            <div key={i} className="border-b border-line/60 pb-3 last:border-0 last:pb-0">
              <div className="flex flex-wrap items-baseline gap-2">
                <span className="font-num text-ink-soft">{i + 1}</span>
                <span>{s.name}</span>
                {s.ec && <span className="font-num text-caption text-ink-soft">EC {s.ec}</span>}
                <span className="text-caption text-ink-soft">
                  {s.substrate} → {s.product}
                </span>
              </div>
              {s.cofactors.length > 0 && (
                <div className="text-caption text-ink-soft mt-0.5">
                  cofactors: {s.cofactors.join(', ')}
                  {s.cofactorStoich.length > 0 && (
                    <span className="font-num">
                      {' '}
                      ({s.cofactorStoich.map((c) => `${c.molPerMolProduct} ${c.species}`).join(', ')} per mol product)
                    </span>
                  )}
                </div>
              )}
              {s.knownIssues.length > 0 && (
                <ul className="mt-1">
                  {s.knownIssues.map((k, j) => (
                    <li key={j} className="text-caption text-ink-soft pl-3 relative">
                      <span className="absolute left-0">·</span>
                      {k}
                    </li>
                  ))}
                </ul>
              )}
              {s.accessionIds.length > 0 && (
                <div className="flex flex-wrap gap-3 mt-1">
                  {s.accessionIds.map((aid) => (
                    <AccessionValue key={aid} id={aid} />
                  ))}
                </div>
              )}
              <div className="mt-2">
                <ClaimOverlay rows={[{ step: s.name, positions: stepPositions(s) }]} />
              </div>
              {s.claims.map((c) => c.patentFamilyId).map((fid) => {
                const fam = PATENT_BY_ID[fid];
                if (!fam) return null;
                return (
                  <div key={fid} className="text-caption text-ink-soft mt-1">
                    <span className="font-num">{fam.representativeNumber}</span> · {fam.assignee} ·{' '}
                    {fam.title}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </Card>

      <Card className="mt-4">
        <SectionTitle>Hosts</SectionTitle>
        <div className="mt-2 space-y-2">
          {route.hosts.map((h) => (
            <div key={h.organismId} className="text-caption">
              <a href={href(`/geneos/${h.organismId}`)} className="italic hover:text-accent">
                {organismName(h.organismId)}
              </a>
              <div className="text-ink-soft">{h.note}</div>
              <div className="flex flex-wrap gap-3 mt-0.5">
                {h.bestTiter && <AccessionValue id={h.bestTiter} />}
                {h.bestYield && <AccessionValue id={h.bestYield} />}
              </div>
            </div>
          ))}
        </div>
      </Card>

      <DemoFooter />
    </>
  );
}
