// The subsystem shelf, rendered at the foot of an owner's screen (OF-BLD-010 §2).
//
// Each named part of a module that has no implementation says so, in an
// EmptyState that describes the code. The statement describes the code alone:
// a stub stays a stub until the code exists, and this component never changes
// a subsystem's status.
//
// The reference shelf that sat beneath each statement (tables on what the
// field looks like) left with the seed in alpha 2.0 (ADR-010): literature
// arrives through Intake, where every passage is read with its source.
import { CircleDashed } from 'lucide-react';
import { stubsFor, type SubsystemOwner } from '@/data/subsystems';
import { Card, EmptyState } from './ui';

const slug = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');

/** One unbuilt subsystem: its name, and what is true of its code. */
export function SubsystemBlock({
  label,
  state,
  id,
}: {
  label: string;
  state: string;
  id: string;
}) {
  return (
    <section className="mt-8 first:mt-0" aria-labelledby={`sub-${slug(id)}`}>
      <div className="flex flex-wrap items-baseline gap-2">
        <h2 id={`sub-${slug(id)}`} className="font-serif text-section-title font-semibold">
          {label}
        </h2>
        <span className="chip text-[11px] py-0 text-ink-soft inline-flex items-center gap-1">
          <CircleDashed size={11} aria-hidden />
          not built
        </span>
        <span className="font-num text-caption text-ink-soft ml-auto">{id}</span>
      </div>
      <Card className="mt-2 py-0">
        <EmptyState title={`${label} has no implementation`} body={state} />
      </Card>
    </section>
  );
}

/**
 * Every UNBUILT subsystem one of the owners holds, as a shelf.
 *
 * Mounted at the FOOT of its owner's screen, below whatever that owner actually
 * has, so the part that is not built reads as such wherever the owner's live
 * views stand.
 *
 * `stubsFor` lists the stubs alone (OF-BLD-011 §2): a seeded subsystem has its
 * own view, and listing it here under "no implementation" would contradict that
 * view.
 */
export function SubsystemShelf({ owner }: { owner: SubsystemOwner }) {
  const stubs = stubsFor(owner);
  if (stubs.length === 0) return null;

  return (
    <section className="mt-10" aria-labelledby="subsystem-shelf">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 pb-2 border-b-2 border-line">
        <h2 id="subsystem-shelf" className="font-serif text-section-title font-semibold">
          {owner} subsystems
        </h2>
        <span className="font-num text-caption text-ink-soft">{stubs.length} named, 0 built</span>
      </div>
      <p className="text-body text-ink-soft mt-2 max-w-3xl">
        Named parts of {owner} that have no implementation. Each one states what is true of the code.
      </p>
      {stubs.map((s) => (
        <SubsystemBlock key={s.id} id={s.id} label={s.label} state={s.state} />
      ))}
    </section>
  );
}
