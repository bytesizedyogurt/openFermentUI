// What an emptied list says when the program filter emptied it
// (OF-BLD-016 §2.2): what is hidden, which archived program holds it, and
// where the switch is. Shared by every screen whose list the filter can
// empty, beside ArchivedBanner, which a detail page opened by link renders.
import type { Program } from '@/data/types';
import { href } from '@/router';
import { PROGRAMS, PROGRAMS_SETTINGS_PATH } from '@/data/programs';
import { archivedProgramOf, type ProgramEntityKind, type ProgramLookup } from '@/store';

/** The archived programs a set of hidden entities belongs to, in the order PROGRAMS declares them. */
export function archivedProgramsOf(items: [ProgramEntityKind, string][], s: ProgramLookup = {}): Program[] {
  const ids = new Set(items.map(([k, id]) => archivedProgramOf(k, id, s)?.id).filter(Boolean));
  return PROGRAMS.filter((p) => ids.has(p.id));
}

/**
 * What an emptied list says when the program filter emptied it: what is
 * hidden, which archived program holds it, and where the switch is. Renders
 * nothing when nothing is hidden.
 */
export function HiddenByArchive({
  subject,
  plural,
  programs,
}: {
  /** What is hidden, as a sentence's subject: "4 records for this strain". */
  subject: string;
  plural: boolean;
  programs: Program[];
}) {
  if (programs.length === 0) return null;
  const names =
    programs.length === 1
      ? programs[0].name
      : `${programs
          .slice(0, -1)
          .map((p) => p.name)
          .join(', ')} and ${programs[programs.length - 1].name}`;
  return (
    <span data-testid="hidden-by-archive">
      {subject} {plural ? 'are' : 'is'} hidden: {plural ? 'they belong' : 'it belongs'} to {names},{' '}
      {programs.length === 1 ? 'an archived program' : 'archived programs'}.{' '}
      <a className="text-accent underline underline-offset-2" href={href(PROGRAMS_SETTINGS_PATH)}>
        Settings → Programs
      </a>{' '}
      shows archived programs again.
    </span>
  );
}
