// Chips for the demo pool's identifiers.
//
// `Markdown`'s `[[chip]]` syntax already resolves paper and record ids from the
// casein corpus. The demo flows write `[[OF-A-00147]]`, `[[PF-003]]`,
// `[[ORG-CGL-02]]`, `[[RUN-047]]` and `[[DLV-AR1-001]]`, and without this they
// would render as a paper chip pointing at a paper that does not exist.
//
// RESOLUTION IS BY PREFIX, and the prefixes are the same ones `check:demo-seed`
// enforces on every demo id. That is not a coincidence: the gate exists so a
// demo object can never be mistaken for a corpus object, and this is the place
// where being able to tell them apart is load-bearing at render time.
//
// An id that matches a demo prefix but resolves to nothing renders as a VISIBLE
// fault rather than as plain text. A dangling chip is Rule 1 breaking, and it
// should look like it.
import { ACCESSION_BY_ID } from '@/data/demo/accessions';
import { PATENT_BY_ID } from '@/data/demo/patents';
import { ORGANISM_BY_ID } from '@/data/demo/core';
import { RUN_BY_ID } from '@/data/demo/runs';
import { DELIVERABLE_BY_ID, AUX_ORGANISMS } from '@/data/demo/archetypes';
import { normalise, deliverableRoute } from '@/lib/demo';
import { href } from '@/router';
import { cx } from '@/components/ui';
import { demoTickClass, demoTickTitle } from './DemoTick';

/** Does this id belong to the demo pool at all? */
export function isDemoId(id: string): boolean {
  return /^(OF-A-|PF-|ORG-|RUN-|DLV-|CND-|RTE-|FC-|DC-|PN-)/.test(id);
}

export function DemoChip({ id }: { id: string }) {
  // Accession — the common case, and the only one that carries a value.
  const acc = ACCESSION_BY_ID[id];
  if (acc) {
    return (
      <a
        href={href(`/repo/a/${acc.id}`)}
        className={cx(
          demoTickClass(acc.provenance, acc.sourceType),
          acc.hold && 'opacity-60',
          'pl-1.5 font-num text-[0.92em] hover:text-accent whitespace-nowrap',
        )}
        title={`${demoTickTitle(acc.provenance, acc.sourceType, acc.hold)} — ${+normalise(acc, ACCESSION_BY_ID).toFixed(4)} ${acc.normalized.unit}`}
      >
        {acc.id}
      </a>
    );
  }

  const fam = PATENT_BY_ID[id];
  if (fam) {
    return (
      <a
        href={href(`/parchment/families#${fam.id}`)}
        className="font-num text-[0.92em] hover:underline whitespace-nowrap text-signal-closed"
        title={`${fam.representativeNumber} · ${fam.assignee} · ${fam.title}`}
      >
        {fam.id}
      </a>
    );
  }

  const org = ORGANISM_BY_ID[id] ?? AUX_ORGANISMS.find((o) => o.id === id);
  if (org) {
    return (
      <a href={href(`/geneos/${org.id}`)} className="italic text-[0.95em] hover:text-accent" title={org.binomial}>
        {org.binomial}
      </a>
    );
  }

  const run = RUN_BY_ID[id];
  if (run) {
    return (
      <a
        href={href(`/fermos/runs/${run.id}`)}
        className={cx('font-num text-[0.92em] hover:text-accent whitespace-nowrap', run.excursions.length > 0 && 'text-signal-warn')}
        title={`${run.productId} · started ${run.startedAt}${run.excursions.length ? ` · ${run.excursions.length} excursion(s)` : ''}`}
      >
        {run.id}
      </a>
    );
  }

  const dlv = DELIVERABLE_BY_ID[id];
  if (dlv) {
    return (
      // Was hard-coded to `/bench` — a menu of all six deliverables — because
      // the route table lived in a screen module and importing it from a
      // component was a cycle. It lives in `lib/demo` now, so a deliverable
      // chip goes to the deliverable.
      <a href={href(deliverableRoute(dlv.id))} className="font-num text-[0.92em] hover:text-accent whitespace-nowrap" title={dlv.title}>
        {dlv.id}
      </a>
    );
  }

  // Matched a demo prefix and resolved to nothing.
  return (
    <span className="font-num text-[0.92em] text-signal-error whitespace-nowrap" title={`${id} is not in the demo pool`}>
      ⚠ {id}
    </span>
  );
}
