// fermOS — hosts, metabolism, strain design (OF-BLD-008 §4).
//
// A SHELL, NOT A REWRITE. The organism catalogue already existed as a rail
// destination; it is now fermOS's default view, and `Organisms.tsx` and
// `StrainPage.tsx` are the same files they were. What changed is the URL and
// what sits above it.
//
// The header exists because "fermOS" over a list of strains would be a
// coinage with no explanation attached — it says what fermOS covers and which
// part of that is actually built, so a reader is not left guessing whether the
// metabolic modelling is somewhere they have not found yet.
import { useMemo } from 'react';
import { STRAINS } from '@/data/strains';
import { Callout, PageHeader } from '@/components/ui';
import { OwnerTabs, type OwnerTab } from '@/components/OwnerTabs';
import { ComponentTag } from '@/components/ComponentTag';
import { UnbuiltList } from '@/components/Unbuilt';
import { SubsystemShelf } from '@/components/ReferenceView';
import Organisms from './Organisms';

const PLANNED = [
  {
    what: 'Metabolic models',
    why: 'Flux balance over a host, so a pathway can be checked against the carbon it would need.',
  },
  {
    what: 'Pathway design',
    why: 'What has to be added to a host to make a molecule, and what has to be removed.',
  },
  {
    what: 'Strain design',
    why: 'A construct plus a host plus the edits between them, as one designed object.',
  },
];

export default function FermOS() {
  const tabs: OwnerTab[] = useMemo(
    () => [{ label: 'Organisms', to: '/fermos/organisms', badge: STRAINS.length }],
    [],
  );

  return (
    <>
      <PageHeader
        eyebrow="Hosts, metabolism, strain design"
        title="fermOS"
        subtitle="The organism side of making something. fermOS covers hosts, their metabolism, the pathways a molecule needs, and the strain design that gets from one to the other. Organisms — the catalogue below — is the part that exists."
      />

      <OwnerTabs tabs={tabs} />

      <Callout kind="info" title="Organisms is the built part of fermOS">
        The catalogue and its strain pages are real: hosts, lineages, and the extraction records
        anchored to each. Metabolic models, pathway design and strain design are not built, and are
        named at the bottom of this page rather than implied by the rail entry.
      </Callout>

      <div className="mt-5">
        <Organisms embedded />
      </div>

      <div className="mt-6">
        <UnbuiltList
          title="The rest of fermOS"
          note="Not built. Listed so the gap between the name and the code is legible from the screen rather than only from COMPONENTS.md."
          items={PLANNED}
        />
      </div>

      <SubsystemShelf owner="fermOS" />

      <div className="mt-5">
        <ComponentTag component="fermOS" action={`${STRAINS.length} organisms, no metabolic model`} />
      </div>
    </>
  );
}
