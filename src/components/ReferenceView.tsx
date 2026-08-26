// Reference content, rendered beneath a stub's EmptyState (OF-BLD-010 §2).
//
// THE DIVIDER IS THE WHOLE IDEA. Above it is the state of the PRODUCT: what
// this subsystem does, what would appear here, what has to exist first. Below
// it is the state of the FIELD: what a textbook would say about the same
// territory. Those are different kinds of claim and a reader must never have to
// work out which one they are looking at.
//
// So the divider is not decoration and it is not the caller's responsibility.
// It is rendered by this component, at its own top edge, carrying a label that
// says what the line means. A caller cannot forget it, and cannot render this
// content flush against an EmptyState as though the two were one statement.
//
// WHAT THIS DOES NOT DO. It does not change a subsystem's status. A stub that
// grew a reference shelf is still a stub — the statement above the line
// describes the code, and no amount of domain knowledge below the line makes
// the code exist. `SubsystemShelf` below enforces the ordering, and
// `pnpm check:reference` enforces that the content itself never carries a
// result: no number in a result unit, no status attached to a patent.
import { BookOpen, CircleDashed } from 'lucide-react';
import { referenceFor, type ReferenceContent, type ReferenceTable } from '@/data/reference';
import { subsystemsFor, type SubsystemOwner } from '@/data/subsystems';
import { Callout, Card, EmptyState, SectionTitle, cx } from './ui';

/** One table. Plain, scrollable, no sorting and no interaction — this is a shelf. */
function Table({ table }: { table: ReferenceTable }) {
  return (
    <section aria-labelledby={`ref-${slug(table.title)}`} className="mt-4 first:mt-0">
      {/* Through the shared primitive rather than a hand-rolled heading, so a
          reference table carries the same title-plus-count shape as every other
          counted card in the app (Unbuilt, Architecture, PureOS, Dominion). */}
      <SectionTitle
        right={
          <span className="font-num text-caption text-ink-soft">
            {table.rows.length} {table.rows.length === 1 ? 'entry' : 'entries'}
          </span>
        }
      >
        <span id={`ref-${slug(table.title)}`}>{table.title}</span>
      </SectionTitle>
      {/* Wide tables scroll inside their own box rather than pushing the page
          sideways — several of these are three columns of prose. */}
      <Card className="overflow-x-auto px-0 py-0">
        <table className="w-full border-collapse text-body">
          <thead>
            <tr className="border-b border-line">
              {table.cols.map((col) => (
                <th
                  key={col}
                  scope="col"
                  className="text-caption font-medium text-ink-soft px-3 py-2 text-left align-bottom"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {table.rows.map((row, i) => (
              <tr key={i} className="border-b border-line/60 last:border-0 align-top">
                {row.map((cell, j) => (
                  <td
                    key={j}
                    className={cx(
                      'px-3 py-2',
                      // The first column is the term being defined; the rest is
                      // what it means. Monospacing the term makes a long list
                      // scannable down its left edge.
                      j === 0 ? 'font-num text-ink whitespace-nowrap' : 'text-ink-soft',
                    )}
                  >
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </section>
  );
}

const slug = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');

export function ReferenceView({ content }: { content: ReferenceContent }) {
  const rows = content.tables.reduce((n, t) => n + t.rows.length, 0);

  return (
    <div className="mt-8">
      {/* The line, and what it means. A bare rule would leave the reader to
          infer the distinction; this states it. */}
      <div className="flex items-center gap-3 mb-4" role="separator" aria-label="Reference content begins">
        <span className="h-px flex-1 bg-line" aria-hidden />
        <span className="inline-flex items-baseline gap-1.5 text-caption text-ink-soft shrink-0">
          <BookOpen size={13} className="self-center" aria-hidden />
          <span className="uppercase tracking-wide">Reference</span>
          <span className="opacity-60">·</span>
          <span>what the field looks like, not what your answer would be</span>
        </span>
        <span className="h-px flex-1 bg-line" aria-hidden />
      </div>

      <p className="text-reading text-ink max-w-3xl">{content.blurb}</p>
      <p className="text-caption text-ink-soft mt-1">
        <span className="font-num">{content.tables.length}</span>{' '}
        {content.tables.length === 1 ? 'table' : 'tables'},{' '}
        <span className="font-num">{rows}</span> {rows === 1 ? 'entry' : 'entries'}. Domain
        knowledge — nothing here is a measurement, a prediction, or a claim about any
        particular molecule.
      </p>

      <div className="mt-4 space-y-5">
        {content.tables.map((table) => (
          <Table key={table.title} table={table} />
        ))}
      </div>

      {/* §4 — the note carries the argument for why the subsystem exists at
          all. Rendered as a Callout with weight, never as small print under a
          table: "artifact caching decides who can afford the platform" is the
          most important sentence on that screen, and setting it in caption grey
          would bury the one thing worth reading. */}
      {content.note && (
        <div className="mt-5">
          <Callout kind="info" title="Why this matters">
            <p className="text-ink">{content.note}</p>
          </Callout>
        </div>
      )}
    </div>
  );
}

/**
 * §2's stack, for one subsystem: what the PRODUCT is, the line, what the FIELD
 * is. In that order, always.
 *
 * The ordering is enforced here rather than left to eight call sites, because
 * "beneath the EmptyState, never instead of it" is the constraint the whole
 * increment turns on and a caller cannot be trusted to remember it at 3pm on a
 * Friday. A subsystem with no reference entry renders its statement alone,
 * unchanged — `referenceFor` returning null is the normal case, not an error.
 */
export function SubsystemBlock({
  label,
  state,
  id,
}: {
  label: string;
  state: string;
  id: string;
}) {
  const reference = referenceFor(id);
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

      {/* ABOVE THE LINE: the state of the product. */}
      <Card className="mt-2 py-0">
        <EmptyState
          title={`${label} has no implementation`}
          body={state}
        />
      </Card>

      {/* BELOW THE LINE: the state of the field. Absent when there is no entry,
          and that is a normal outcome rather than a gap to paper over. */}
      {reference && <ReferenceView content={reference} />}
    </section>
  );
}

/**
 * Every subsystem one of the eleven owns, as a reference shelf.
 *
 * Mounted at the FOOT of its owner's screen, below whatever that owner actually
 * has. On geneOS there is nothing above it; on Dominion there are a hundred and
 * seventeen molecules above it. Either way this section is the part that is not
 * built, and putting a "nothing is built here" panel above a live catalogue to
 * satisfy the letter of the layout would be a false statement on a screen whose
 * whole purpose is not making false statements.
 */
export function SubsystemShelf({ owner }: { owner: SubsystemOwner }) {
  const subsystems = subsystemsFor(owner);
  if (subsystems.length === 0) return null;
  const withReference = subsystems.filter((s) => referenceFor(s.id) !== null).length;

  return (
    <section className="mt-10" aria-labelledby="subsystem-shelf">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 pb-2 border-b-2 border-line">
        <h2 id="subsystem-shelf" className="font-serif text-section-title font-semibold">
          {owner} subsystems
        </h2>
        <span className="font-num text-caption text-ink-soft">
          {subsystems.length} named, 0 built, {withReference} with reference content
        </span>
      </div>
      <p className="text-body text-ink-soft mt-2 max-w-3xl">
        Named parts of {owner} that have no implementation. Each one states what is true of the
        code, and then — below its own line — what the field looks like in that territory.
        Nothing below a line is a measurement, a prediction, or a claim about any particular
        molecule.
      </p>
      {subsystems.map((s) => (
        <SubsystemBlock key={s.id} id={s.id} label={s.label} state={s.state} />
      ))}
    </section>
  );
}
