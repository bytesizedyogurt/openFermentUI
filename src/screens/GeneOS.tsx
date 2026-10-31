// geneOS — the organism as an engineered system (OF-BLD-011 §2).
//
// WHAT CHANGED, AND WHY. OF-BLD-008 gave geneOS a screen with nothing on it:
// homology search, structure prediction, enzyme annotation. That was a split
// along software categories — sequence tools here, metabolic modelling next
// door — which is how a toolkit is organised, not how bioprocess work is.
// OF-BLD-011 §1 corrects it. geneOS is now the FIRST OF THE THREE STAGES: the
// organism as an engineered system. Host choice, genetic parts, pathway
// assembly, the genome-scale model, strain design. Stoichiometry.
//
//     geneOS answers: what CAN this cell do?
//
// Two things moved in as a consequence. The strain catalogue is geneOS's
// default view rather than fermOS's, because choosing a chassis is a genetic
// design decision, not a reactor one. And strain design — deciding which genes
// to knock out — came back from fermOS, where it had no business being.
//
// THE SEAM TO FERMOS IS ON THIS SCREEN, not implied by the rail order. A
// genome-scale model gives a yield ceiling with no time axis; kinetics gives
// the curve in a specific vessel. Titre is fermOS's output, not geneOS's, and
// the gap between ceiling and achieved titre is exactly what reconciliation
// measures. A reader who does not know where that line falls will look for
// titre here and conclude the platform lost it.
//
// HOSTS AND ROUTES (alpha 2.0, ADR-010). The Hosts badge counts the strains
// the store holds, and the Pathway view lists the routes the products on file
// declare. Both are empty: no store holds a strain or product catalogue yet.
import { useMemo } from 'react';
import { useStore } from '@/store';
import { href, useRoute } from '@/router';
import { Callout, Card, EmptyState, PageHeader, SectionTitle } from '@/components/ui';
import GeneOSModel from './GeneOSModel';
import { OwnerTabs, activeTab, type OwnerTab } from '@/components/OwnerTabs';
import { ComponentTag } from '@/components/ComponentTag';
import { SubsystemShelf } from '@/components/ReferenceView';
import Organisms from './Organisms';

/** Each route the products on file declare, with how many declare it, most first. */
function useRoutes(): [string, number][] {
  const products = useStore((s) => s.products);
  return useMemo(() => {
    const counts = new Map<string, number>();
    for (const product of products) {
      for (const id of product.pathwayIds ?? []) counts.set(id, (counts.get(id) ?? 0) + 1);
    }
    return [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  }, [products]);
}

/**
 * Pathway — the routes the products on file declare.
 *
 * A LIST, NOT A MODEL. Every entry is a route id a product names, and its
 * count is derived from the products rather than declared. Nothing here
 * balances a pathway, checks it against a host, or computes a flux — those are
 * the parts that have no code, and they are named on the shelf below.
 */
function PathwayView() {
  const routes = useRoutes();
  return (
    <>
      <Callout kind="info" title="The routes products declare, without a pathway model">
        Each row names a metabolic route a product on file declares. Nothing here balances a pathway, sizes a
        precursor pool, or checks a route against the host that would carry it.
      </Callout>

      <section aria-labelledby="pathway-routes" className="mt-5">
        <SectionTitle right={<span className="font-num text-caption text-ink-soft">{routes.length} routes</span>}>
          <span id="pathway-routes">Routes products declare</span>
        </SectionTitle>
        {routes.length === 0 ? (
          <Card className="py-0">
            <EmptyState
              title="No route is declared yet"
              body="A route shows here once a product on file declares it. Products arrive with the documents that report them, through Intake."
            />
          </Card>
        ) : (
          <Card className="px-4 py-1">
            <ul>
              {routes.map(([id, used]) => (
                <li key={id} className="py-2.5 border-b border-line/70 last:border-0">
                  <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                    <span className="font-num text-body text-ink">{id}</span>
                    <span
                      className="ml-auto font-num text-caption shrink-0 text-ink-soft"
                      title={`${used} product${used === 1 ? '' : 's'} on file declare this route`}
                    >
                      on {used}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          </Card>
        )}
      </section>
    </>
  );
}

/** §5 — the seam, stated where a reader stands rather than left to the docs. */
function StoichiometryToDynamics() {
  return (
    <div className="mt-8">
      <Callout kind="info" title="Where geneOS stops and fermOS starts">
        <p className="text-ink">
          geneOS is stoichiometry: what the engineered cell <em>can</em> do, at steady state, with
          no time axis and no vessel. A genome-scale model gives a yield ceiling. What a real
          fermenter achieves over ninety hours is a different claim in a different discipline, and
          it belongs to{' '}
          <a href={href('/fermos')} className="text-accent hover:underline">
            fermOS
          </a>
          .
        </p>
        <p className="text-ink mt-2">
          <strong>Titre is fermOS's output, not geneOS's.</strong> The gap between the ceiling here
          and the titre achieved there is exactly what reconciliation measures against a
          deposition — so nothing on this screen should ever be read as a prediction of what a
          vessel will produce.
        </p>
      </Callout>
    </div>
  );
}

export default function GeneOS() {
  const route = useRoute();
  const hosts = useStore((s) => s.strains.length);
  const routeCount = useRoutes().length;
  const tabs: OwnerTab[] = useMemo(
    () => [
      { label: 'Hosts', to: '/geneos/hosts', badge: hosts },
      { label: 'Pathway', to: '/geneos/pathway', badge: routeCount },
      { label: 'Model', to: '/geneos/model' },
    ],
    [hosts, routeCount],
  );
  const active = activeTab(route.path, tabs);
  const onPathway = active === '/geneos/pathway';
  const onModel = active === '/geneos/model';

  return (
    <>
      <PageHeader
        eyebrow="Host, construct, pathway, design"
        title="geneOS"
        subtitle="The organism as an engineered system. Host choice, genetic parts, pathway assembly, the genome-scale model and strain design — everything that decides what a cell CAN do, before any vessel is involved."
      />

      <OwnerTabs tabs={tabs} />

      {onModel ? (
        <GeneOSModel />
      ) : onPathway ? (
        <PathwayView />
      ) : (
        <>
          <Callout kind="info" title="Hosts">
            The strain catalogue and its pages: hosts, lineages, and the extraction records
            anchored to each, as a project's records name them. Choosing a chassis is a genetic
            design decision — it sets
            whether the product is secreted, whether endotoxin clearance is mandatory, and what
            the entire downstream train will have to be — which is why it lives here rather than
            with the reactor.
          </Callout>
          <div className="mt-5">
            <Organisms embedded />
          </div>
        </>
      )}

      <StoichiometryToDynamics />

      <SubsystemShelf owner="geneOS" />

      <div className="mt-5">
        <ComponentTag
          component="geneOS"
          action={
            onPathway
              ? `${routeCount} routes, no pathway model`
              : `${hosts} hosts, no chassis recommendation`
          }
        />
      </div>
    </>
  );
}
