// Proforma's demo-pool surfaces, as one card on Proforma's corpus index.
//
// `/proforma` used to render the demo pool's own index — a 27-line list of two
// deliverable links. Proforma now has a corpus surface (the three β-casein
// plants and their prices), and the part index belongs to it, so the demo half
// arrives here instead.
//
// It stays a COMPONENT for the reason the pool separation exists: `screens/
// Proforma.tsx` reads the corpus through the store and the adapter seam, and
// must never hold a `Candidate` or a `FacilityConcept`. This file reads the
// demo modules directly and hands back markup. Same arrangement as
// `DemoPoolCard` on the Bench, and the same reason.
import { ArrowUpRight } from 'lucide-react';

import { DELIVERABLES } from '@/data/demo/archetypes';
import { deliverableRoute } from '@/lib/demo';
import { href } from '@/router';
import { Card } from '@/components/ui';

/** The two archetypes `ARCHETYPE_PART` routes to Proforma: AR3 and AR4. */
const PROFORMA_KINDS = ['capacity-screen', 'facility-concept'] as const;

export function ProformaDemoCard() {
  const mine = DELIVERABLES.filter((d) =>
    (PROFORMA_KINDS as readonly string[]).includes(d.payload.kind),
  );

  return (
    <Card className="p-3">
      <div className="text-caption uppercase tracking-wide text-ink-soft">Demo suite</div>
      <div className="text-body mt-0.5 max-w-prose">
        The same part, against a different pool. These carry the regional basis the corpus plants
        do not have — a sited facility, a jurisdiction, and a capital estimate that states its
        accuracy class.
      </div>
      <ul className="mt-2 space-y-2">
        {mine.map((d) => (
          <li key={d.id}>
            <a
              href={href(deliverableRoute(d.id))}
              className="group inline-flex items-baseline gap-1.5 motion-colors"
            >
              <span className="font-medium group-hover:text-accent">{d.title}</span>
              <ArrowUpRight size={12} className="text-ink-soft shrink-0" aria-hidden />
            </a>
            <div className="text-caption text-ink-soft max-w-prose">{d.query}</div>
          </li>
        ))}
      </ul>
    </Card>
  );
}
