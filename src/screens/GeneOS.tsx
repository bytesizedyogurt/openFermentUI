// geneOS — sequence, structure and function (OF-BLD-008 §4).
//
// A PLACEHOLDER THAT IS HONEST ABOUT BEING EMPTY. There is no geneOS code, so
// this screen shows no data, no mock chart and no sample result. It states what
// the component is for, what it will hold, and what it currently holds, which
// is nothing.
//
// The alternative — leaving geneOS out of the rail until it has content — is
// what the closed list of §1 exists to prevent. A name with nothing under it is
// a smaller problem than a system with no name for the thing it is missing:
// when sequence work arrives, the question is what geneOS does with it, not
// where in the navigation it should go.
import { Dna } from 'lucide-react';
import { EmptyState, PageHeader } from '@/components/ui';
import { ComponentTag } from '@/components/ComponentTag';
import { UnbuiltList } from '@/components/Unbuilt';

/**
 * What geneOS will hold. Stated as work not started rather than as a roadmap
 * — none of these has a date, an owner, or a line of code.
 */
const PLANNED = [
  {
    what: 'Homology search',
    why: 'Find the sequences a construct is related to, and how far the relation actually goes.',
  },
  {
    what: 'Structure prediction',
    why: 'Fold a candidate and see whether the active site survives the changes made to it.',
  },
  {
    what: 'Enzyme function annotation',
    why: 'What a sequence is likely to do, with the evidence for the guess attached.',
  },
  {
    what: 'Genus enumeration',
    why: 'Which organisms carry a pathway, so a host search starts from biology rather than habit.',
  },
];

export default function GeneOS() {
  return (
    <>
      <PageHeader
        eyebrow="Sequence, structure, function"
        title="geneOS"
        subtitle="What a molecule is, at the level of sequence and fold. geneOS answers the questions that come before a host is chosen: what is this protein related to, what shape does it take, and which organisms already make something like it."
      />

      <EmptyState
        icon={<Dna size={28} />}
        title="Nothing is built here yet"
        body="geneOS has no code behind it. This screen shows no data because there is none — not a sample, not a placeholder chart, not a worked example. It is in the navigation because the architecture says sequence work belongs somewhere, and this is where it will go."
      />

      <div className="mt-6">
        <UnbuiltList
          title="What geneOS will hold"
          note="None of this exists. It is listed so that when sequence work arrives the question is what geneOS does with it, rather than where in the navigation it should live."
          items={PLANNED}
        />
      </div>

      <div className="mt-5">
        <ComponentTag component="geneOS" action="no implementation" />
      </div>
    </>
  );
}
