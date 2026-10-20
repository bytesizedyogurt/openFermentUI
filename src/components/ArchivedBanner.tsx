// The banner over an archived program's entity (OF-BLD-016 §2.1, E.1′).
//
// Archived programs leave every list by default, but a deep link still opens
// what it names: a paper cited in an old answer, a strain page bookmarked
// last month. The page opens under this banner, which names the program and
// says where the switch is, rather than refusing the link or showing the
// entity as though nothing had changed. A detail page renders it at the top
// with its entity's kind and id; for a general entity, or one whose program
// is active, it renders nothing.
//
// An example (OF-BLD-016 §3.3, D3) is treated as archived: a seed runbook,
// protocol, scenario or lesson that describes a run nobody made opens under
// this same banner, which says so, beside the program when it has an archived
// one. There is one banner, not a second for examples.
import { Archive } from 'lucide-react';
import { href } from '@/router';
import { PROGRAMS_SETTINGS_PATH } from '@/data/programs';
import { archivedProgramOf, isExample, useProgramLookup, useStore, type ProgramEntityKind } from '@/store';
import { cx } from './ui';

const NOUN: Record<ProgramEntityKind, string> = {
  paper: 'paper',
  record: 'value',
  strain: 'strain',
  product: 'molecule',
  scenario: 'scenario',
  protocol: 'protocol',
  runbook: 'runbook',
  module: 'module',
  lesson: 'lesson',
  deposition: 'deposition',
};

export function ArchivedBanner({
  kind,
  id,
  className,
}: {
  kind: ProgramEntityKind;
  id: string;
  className?: string;
}) {
  const showArchived = useStore((s) => s.showArchived);
  const lookup = useProgramLookup();
  const program = archivedProgramOf(kind, id, lookup);
  const example = isExample(kind, id, lookup);
  if (!program && !example) return null;
  const exampleLine = `${program ? 'It is also an example' : 'It'} describes a run nobody made: kept to show the shape of one, never a record of one. `;
  return (
    <div
      role="note"
      data-archived-program={program?.id}
      data-example={example ? 'true' : undefined}
      className={cx('rounded-card border border-line bg-ink-soft/[0.05] p-3 flex gap-2 mb-4', className)}
    >
      <Archive size={16} className="mt-[2px] shrink-0 text-ink-soft" aria-hidden />
      <div className="text-body">
        <div className="font-medium mb-0.5">
          {program ? (
            <>
              This {NOUN[kind]} belongs to {program.name}, an archived program
            </>
          ) : (
            <>This {NOUN[kind]} is an example</>
          )}
        </div>
        <p className="text-ink-soft">
          {example && exampleLine}
          {showArchived
            ? 'Archived programs and examples are showing everywhere, because the switch in Settings is on. '
            : 'Archived programs and examples are hidden from every list, count and answer; a link still opens what it names. '}
          <a className="text-accent underline underline-offset-2" href={href(PROGRAMS_SETTINGS_PATH)}>
            Settings → Programs
          </a>{' '}
          {showArchived ? 'turns them off again.' : 'shows them again.'}
        </p>
      </div>
    </div>
  );
}
