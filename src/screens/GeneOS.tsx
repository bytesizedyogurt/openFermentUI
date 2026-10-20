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
// PROGRAMS (OF-BLD-016 §2.2). The Hosts badge and count, and every molecule
// count on the Pathway view, pass the program selector; a route that only
// archived molecules declare leaves the Pathway list with them, while a route
// nobody declares still reads "on none". With the switch on, all as before.
import { useMemo } from 'react';
import { STRAINS } from '@/data/strains';
import { PATHWAYS } from '@/data/vocabulary';
import { PRODUCTS } from '@/data/products';
import { useProgramFilter } from '@/store';
import { href, useRoute } from '@/router';
import { Callout, Card, PageHeader, SectionTitle, cx } from '@/components/ui';
import GeneOSModel from './GeneOSModel';
import { OwnerTabs, activeTab, type OwnerTab } from '@/components/OwnerTabs';
import { ComponentTag } from '@/components/ComponentTag';
import { SubsystemReference, SubsystemShelf } from '@/components/ReferenceView';
import Organisms from './Organisms';

/**
 * Pathway — the biosynthetic vocabulary, and who declares each route.
 *
 * A LIST, NOT A MODEL. Every entry is a route that already exists in
 * `vocabulary.ts` and is already cited by molecules in the catalogue; the
 * counts are derived from `PRODUCTS` rather than declared, so a route nobody
 * uses reads as zero instead of being quietly dropped. Nothing here balances a
 * pathway, checks it against a host, or computes a flux — those are the parts
 * that have no code, and they are named on the shelf below.
 */
function PathwayView() {
  const shows = useProgramFilter();
  const { usage, hiddenUsage } = useMemo(() => {
    const counts = new Map<string, number>();
    const hidden = new Map<string, number>();
    for (const product of PRODUCTS) {
      const into = shows('product', product.id) ? counts : hidden;
      for (const id of product.pathwayIds ?? []) {
        into.set(id, (into.get(id) ?? 0) + 1);
      }
    }
    return { usage: counts, hiddenUsage: hidden };
  }, [shows]);

  // A route only archived molecules declare belongs to them and is hidden
  // with them; a route nobody declares stays, and reads "on none".
  const routes = PATHWAYS.filter((p) => usage.has(p.id) || !hiddenUsage.has(p.id));
  const unused = routes.filter((p) => !usage.has(p.id)).length;

  return (
    <>
      <Callout kind="info" title="A vocabulary of routes, not a pathway model">
        Each row names a metabolic route and the branch point flux has to be pushed through.
        Nothing here balances a pathway, sizes a precursor pool, or checks a route against the
        host that would carry it. What exists is the shared language the molecule catalogue
        describes a route in, which is worth surfacing because it is real.
      </Callout>

      <section aria-labelledby="pathway-routes" className="mt-5">
        <SectionTitle
          right={
            <span className="font-num text-caption text-ink-soft">
              {routes.length} routes
              {unused > 0 ? ` · ${unused} on no molecule` : ''}
            </span>
          }
        >
          <span id="pathway-routes">Routes in the vocabulary</span>
        </SectionTitle>
        <Card className="px-4 py-1">
          <ul>
            {routes.map((pathway) => {
              const used = usage.get(pathway.id) ?? 0;
              return (
                <li key={pathway.id} className="py-2.5 border-b border-line/70 last:border-0">
                  <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                    <span className="font-num text-body text-ink">{pathway.label}</span>
                    <span className="text-caption text-ink-soft">{pathway.fluxNode}</span>
                    <span
                      className={cx(
                        'ml-auto font-num text-caption shrink-0',
                        used > 0 ? 'text-ink-soft' : 'text-ink-soft/55',
                      )}
                      title={
                        used > 0
                          ? `${used} molecule${used === 1 ? '' : 's'} in the catalogue declare this route`
                          : 'no molecule in the catalogue declares this route'
                      }
                    >
                      {used > 0 ? `on ${used}` : 'on none'}
                    </span>
                  </div>
                  <div className="text-body text-ink-soft mt-0.5">
                    {pathway.products.join(', ')}
                    {pathway.note ? ` — ${pathway.note}` : ''}
                  </div>
                </li>
              );
            })}
          </ul>
        </Card>
      </section>

      <SubsystemReference id="geneos.pathway" />
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
  const shows = useProgramFilter();
  // OF-BLD-016 §2.2 — the counts the program switch lets show.
  const hosts = useMemo(() => STRAINS.filter((s) => shows('strain', s.id)).length, [shows]);
  const routeCount = useMemo(() => {
    const declared = new Map<string, boolean>();
    for (const product of PRODUCTS) {
      const shown = shows('product', product.id);
      for (const id of product.pathwayIds ?? []) declared.set(id, (declared.get(id) ?? false) || shown);
    }
    return PATHWAYS.filter((p) => declared.get(p.id) !== false).length;
  }, [shows]);
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
          <Callout kind="info" title="Hosts is the built part of geneOS">
            The catalogue and its strain pages are real: hosts, lineages, and the extraction
            records anchored to each. Choosing a chassis is a genetic design decision — it sets
            whether the product is secreted, whether endotoxin clearance is mandatory, and what
            the entire downstream train will have to be — which is why it lives here rather than
            with the reactor.
          </Callout>
          <div className="mt-5">
            <Organisms embedded />
          </div>
          <SubsystemReference id="geneos.hosts" />
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
