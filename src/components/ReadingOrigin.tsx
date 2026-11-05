// A measurement origin in words (ADR-006's `measurement`, alpha 2.2 C.5): a
// reading a person deposited at the bench, named as `<deposition id>/<entry
// id>`, with the time it was taken, linked to the deposition's record
// (DepositionDetail), which opens at the reading, marked. The tables it sits
// in name the depositor in a column of their own, and `by` adds it here
// where none does. The service filled each from the deposition's rows when
// the value was set (measurements.py); nothing here reads a deposition.
//
// It also draws a reading as a person chooses it (`ReadingChoice`), for
// NewScenarioDialog and a Proforma scenario's parameter panel (alpha 2.2
// E.17): each one the service listed (GET /api/depositions/readings?unit=),
// said as what it measured and what it would set.
import type { DepositionReading, Origin } from '@/lib/studies';
import { href } from '@/router';
import { fmt } from '@/engine/units';
import { cx } from './ui';

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

/**
 * A reading as a person chooses it: its measure, its value and unit (and in the parameter's, where it converts), its
 * runbook, its time and its person. `label` and `unit` are the parameter's it would set, `name` the radio group's.
 */
export function ReadingChoice({
  reading,
  label,
  unit,
  name,
  chosen,
  onChoose,
  testid,
  disabled = false,
}: {
  reading: DepositionReading;
  label: string;
  unit: string;
  name: string;
  chosen: boolean;
  onChoose: () => void;
  testid: string;
  disabled?: boolean;
}) {
  const converted = reading.inUnit != null && reading.unit !== unit;
  return (
    <label
      className={cx('card p-2 flex items-start gap-2 min-h-[44px]', disabled ? 'opacity-60' : 'cursor-pointer', chosen && 'border-accent')}
      data-testid={testid}
      data-ref={reading.ref}
    >
      <input
        type="radio"
        className="mt-1"
        name={name}
        checked={chosen}
        disabled={disabled}
        onChange={onChoose}
        aria-label={`Reading ${reading.ref}`}
      />
      <span className="min-w-0">
        {/* What the reading measured, and what it would set: the pairing is the person's to choose, and the service holds the unit alone. */}
        <span className="block">
          a reading of {reading.measure ?? `measure ${reading.measureId}`}:{' '}
          <span className="font-num" title={String(reading.value)}>
            {fmt(reading.value, 6)} {reading.unit}
          </span>
          {converted && (
            <span className="font-num text-ink-soft">
              {' '}
              = {fmt(reading.inUnit ?? 0, 6)} {unit}
            </span>
          )}
          , set as <span className="font-medium">{label}</span>
        </span>
        <span className="block text-caption text-ink-soft">
          {reading.runbook ? <>runbook {reading.runbook}</> : <>runbook {reading.runbookId ?? 'not named'}, which the project does not hold</>} · taken{' '}
          <span className="font-num">{minute(reading.at)}</span>
          {reading.hours != null && <> at hour {reading.hours}</>} · deposited by {reading.by} · <span className="font-num">{reading.ref}</span>
        </span>
      </span>
    </label>
  );
}
