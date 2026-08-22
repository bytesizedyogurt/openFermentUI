// The demo pool, as one card on the Bench.
//
// This replaces `DemoSuiteBand`, which was a whole band at the foot of the page
// — three context cards and six archetype tiles, arriving after everything else
// and reading as an appendix. The pool separation is a claim about what the two
// object types ARE, so it belongs beside the corpus rather than below it, and it
// belongs in the first screenful rather than the last.
//
// It stays a COMPONENT rather than a section of `Home.tsx` for the reason the
// separation exists: `Home` reads the casein corpus through the adapter seam,
// and this pool is read from its modules directly. Home composes this card; it
// never imports an Accession.
import { ACCESSIONS } from '@/data/demo/accessions';
import { PATENT_FAMILIES } from '@/data/demo/patents';
import { DELIVERABLES, DISCLOSURES } from '@/data/demo/archetypes';
import { jurisdictionRollup } from '@/lib/demo';
import { href } from '@/router';
import { Card } from '@/components/ui';

export function DemoPoolCard() {
  const roll = jurisdictionRollup();

  return (
    <Card className="p-3">
      <div className="text-caption uppercase tracking-wide text-ink-soft">Demo suite</div>
      <div className="text-body mt-0.5">
        An <span className="font-medium">Accession</span> — a normalised quantity with complete
        provenance under a permanent identifier.
      </div>

      <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-caption">
        <a href={href('/repo')} className="hover:text-accent">
          <span className="font-num text-ink">{ACCESSIONS.length}</span> Accessions
        </a>
        <a href={href('/parchment/families')} className="hover:text-accent">
          <span className="font-num text-ink">{PATENT_FAMILIES.length}</span> patent families
        </a>
        <a href={href('/notary/disclosures')} className="hover:text-accent">
          <span className="font-num text-ink">{DISCLOSURES.length}</span> to publish
        </a>
        <a href={href('/postdoc')} className="hover:text-accent">
          <span className="font-num text-ink">{DELIVERABLES.length}</span> archetype answers
        </a>
      </div>

      <div className="text-caption text-ink-soft mt-2 max-w-prose">
        Every identifier, author, patent number and assignee here is synthetic, in provably
        impossible series. The <em>shape</em> is not: the suite models{' '}
        <span className="font-num text-ink">{roll.open}</span> of{' '}
        <span className="font-num text-ink">{roll.total}</span> positions as open ground, because
        that pattern is real in the fermentation literature even though these families are not.
        A modelled ratio, not a measurement.
      </div>
    </Card>
  );
}
