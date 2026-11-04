// A measurement origin in words (ADR-006's `measurement`, alpha 2.2 C.5): a
// reading a person deposited at the bench, named as `<deposition id>/<entry
// id>`, with the time it was taken, linked to the deposition's record
// (DepositionDetail), which opens at the reading, marked. The tables it sits
// in name the depositor in a column of their own, and `by` adds it here
// where none does. The service filled each from the deposition's rows when
// the value was set (measurements.py); nothing here reads a deposition.
import type { Origin } from '@/data/types';
import { href } from '@/router';

/** The deposition and the entry a reading's ref names. */
export function readingOf(ref: string | null | undefined): { deposition: string; entry: string } | null {
  const [deposition, entry, ...rest] = (ref ?? '').split('/');
  return deposition && entry && rest.length === 0 ? { deposition, entry } : null;
}

/** Where a deposition's record opens; with `entryId`, at that reading, marked. */
export const depositionPath = (depositionId: string, entryId?: string) =>
  `/runbooks/depositions/${encodeURIComponent(depositionId)}${entryId ? `?entry=${encodeURIComponent(entryId)}` : ''}`;

/** A time as the record shows it: the day and the minute, in UTC where the time names it. */
export const minute = (at: string) => `${at.slice(0, 16).replace('T', ' ')}${/(Z|[+-]00:00)$/.test(at) ? ' UTC' : ''}`;

/** A measurement's note as a table shows it beside the time it was taken: the basis's "measured on <time>" read off. */
export const readingNote = (note: string | null | undefined) => (note ?? '').replace(/^measured on \S+?(?:: |$)/, '');

export function ReadingOrigin({ origin, by = false }: { origin: Pick<Origin, 'ref' | 'by' | 'at'>; by?: boolean }) {
  const reading = readingOf(origin.ref);
  return (
    <span data-testid="measurement-origin" data-ref={origin.ref ?? ''}>
      a reading deposited at the bench
      {reading ? (
        <>
          ,{' '}
          <a
            className="text-accent underline underline-offset-2"
            href={href(depositionPath(reading.deposition, reading.entry))}
            data-testid="measurement-deposition"
            data-deposition={reading.deposition}
          >
            reading <span className="font-num whitespace-nowrap">{reading.entry}</span> of deposition{' '}
            <span className="font-num whitespace-nowrap">{reading.deposition}</span>
          </a>
        </>
      ) : (
        origin.ref && (
          <>
            , <span className="font-num whitespace-nowrap">{origin.ref}</span>
          </>
        )
      )}
      {by && origin.by && <>, deposited by {origin.by}</>}
      {origin.at && (
        <>
          , taken <span className="font-num whitespace-nowrap">{minute(origin.at)}</span>
        </>
      )}
    </span>
  );
}
