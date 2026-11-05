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
// HOSTS AND ROUTES (alpha 2.2 E.9). The Hosts badge counts the strains the
// project's strain catalogue keeps, which the store reads (lib/catalogues.ts).
// The Pathway view points to Model, where each model on geneOS's shelf names
// its route; a product's entry keeps its class, where the cells leave it and a
// protein's sequence.
import { useMemo } from 'react';
import { useStore } from '@/store';
import { href, useRoute } from '@/router';
import { Callout, Card, EmptyState, LinkButton, PageHeader, SectionTitle } from '@/components/ui';
import GeneOSModel from './GeneOSModel';
import { OwnerTabs, activeTab, type OwnerTab } from '@/components/OwnerTabs';
import { ComponentTag } from '@/components/ComponentTag';
import { SubsystemShelf } from '@/components/ReferenceView';
import Organisms from './Organisms';

/**
 * Pathway — where geneOS's routes are named.
 *
 * The routes geneOS knows are the ones its shelf's models name, each listed
 * under Model with the model that takes it; a product's entry in the
 * project's catalogue keeps its class, where the cells leave it and a
 * protein's sequence. Nothing here balances a pathway, checks it against a
 * host, or computes a flux — those are the parts that have no code, and they
 * are named on the shelf below.
 */
function PathwayView() {
  const products = useStore((s) => s.products.length);
  return (
    <>
      <Callout kind="info" title="Routes, without a pathway model">
        Nothing here balances a pathway, sizes a precursor pool, or checks a route against the host that would carry it.
      </Callout>

      <section aria-labelledby="pathway-routes" className="mt-5">
        <SectionTitle>
          <span id="pathway-routes">Routes</span>
        </SectionTitle>
        <Card className="py-0">
          <EmptyState
            title="The routes geneOS knows are on its shelf"
            body={`Each model on geneOS's shelf names its route to its products, listed under Model with the model that takes it. The project's product catalogue keeps ${products} product${products === 1 ? '' : 's'}, each with its class, where the cells leave it and, for a protein, its sequence.`}
            action={<LinkButton to="/geneos/model">Open Model</LinkButton>}
          />
        </Card>
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
  const tabs: OwnerTab[] = useMemo(
    () => [
      { label: 'Hosts', to: '/geneos/hosts', badge: hosts },
      { label: 'Pathway', to: '/geneos/pathway' },
      { label: 'Model', to: '/geneos/model' },
    ],
    [hosts],
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
            The project&rsquo;s strain catalogue and its pages: each strain kept on the{' '}
            <a href={href('/catalogues')} className="text-accent hover:underline">
              Catalogues screen
            </a>
            , and the extraction records anchored to it, as a project&rsquo;s records name them. Choosing a chassis is a genetic
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
              ? 'routes on the shelf, no pathway model'
              : `${hosts} hosts, no chassis recommendation`
          }
        />
      </div>
    </>
  );
}
