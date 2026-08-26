// fermOS — the reactor (OF-BLD-011 §3).
//
// THIS SCREEN GOT EMPTIER ON PURPOSE. Until OF-BLD-011, fermOS held the strain
// catalogue and named "metabolic models" and "strain design" as its unbuilt
// parts. Both were wrong. Choosing a chassis and deciding which genes to knock
// out are genetic design decisions, and they have gone to geneOS where they
// belong. What was left behind was the discovery that THE COMPONENT NAMED AFTER
// FERMENTATION CONTAINED NOTHING ABOUT RUNNING A FERMENTER — no kinetics, no
// oxygen transfer, no feeding strategy, no scale-up.
//
//     fermOS answers: what DOES a real vessel achieve over time?
//
// So fermOS is now the five reactor subsystems and nothing else, which makes it
// the emptiest of the eleven. That is the honest state: there is no kinetic
// model, no transport calculation and no scale-up logic anywhere in this
// codebase. Showing a chart here would be inventing the one thing the platform
// exists to avoid inventing.
//
// AND IT MUST NOT BE SEEDED FROM LITERATURE (§3). Kinetic parameters are fitted
// to real runs in a specific vessel; mu_max copied out of a paper about a
// different strain in a different reactor is a number with no owner. fermOS is
// the component that most needs the Assay loop, and the only honest route from
// here to a kinetic model runs through Deposition.
import { FlaskConical } from 'lucide-react';
import { href } from '@/router';
import { Callout, EmptyState, PageHeader } from '@/components/ui';
import { ComponentTag } from '@/components/ComponentTag';
import { SubsystemShelf } from '@/components/ReferenceView';
import { stubsFor } from '@/data/subsystems';

export default function FermOS() {
  const stubs = stubsFor('fermOS');

  return (
    <>
      <PageHeader
        eyebrow="Reactor, kinetics, scale"
        title="fermOS"
        subtitle="The vessel. Kinetics, oxygen and heat transport, operating mode and feeding, scale-up, instrumentation and control — what a real reactor achieves over time, as opposed to what the cell could do in principle."
      />

      <EmptyState
        icon={<FlaskConical size={28} />}
        title="Nothing is built here yet"
        body="fermOS has no code behind it. No kinetic model, no oxygen-transfer calculation, no scale-up logic — and no sample curve standing in for one. It is the emptiest of the eleven, and the rail says so rather than implying the reactor is handled somewhere the reader has not found."
      />

      <div className="mt-6 space-y-4">
        <Callout kind="warn" title="Kinetic parameters come from runs, not from papers">
          <p className="text-ink">
            mu_max, Ks, qp and a maintenance coefficient are <em>fitted</em> to a real
            fermentation in a specific vessel. Lifting them from a paper about a different strain
            in a different reactor produces a number with no owner and no error bar, which is the
            failure mode this whole platform is built against. So fermOS is deliberately not
            seeded: the only honest route to a kinetic model here runs through{' '}
            <a href={href('/runbooks/depositions')} className="text-accent hover:underline">
              Deposition
            </a>
            . fermOS is the component that most needs the Assay loop, and the one that cannot be
            built from literature alone.
          </p>
        </Callout>

        <Callout kind="info" title="Titre is fermOS's output — and the seam on either side">
          <p className="text-ink">
            Upstream,{' '}
            <a href={href('/geneos')} className="text-accent hover:underline">
              geneOS
            </a>{' '}
            is stoichiometry: a genome-scale model gives a yield ceiling with no time axis. fermOS
            is dynamics: the curve in a specific vessel. The gap between the ceiling and the titre
            actually achieved is exactly what reconciliation measures.
          </p>
          <p className="text-ink mt-2">
            Downstream, the seam to{' '}
            <a href={href('/pureos')} className="text-accent hover:underline">
              pureOS
            </a>{' '}
            is the harvest step, and it carries a decision made back in geneOS:{' '}
            <strong>secreted or intracellular</strong>. A secreted product starts at centrifuge
            and filter; an intracellular one starts at lysis and inherits every problem after it.
            The handoff has to carry product location, not just a titre.
          </p>
        </Callout>
      </div>

      <SubsystemShelf owner="fermOS" />

      <div className="mt-5">
        <ComponentTag component="fermOS" action={`${stubs.length} subsystems named, none built`} />
      </div>
    </>
  );
}
