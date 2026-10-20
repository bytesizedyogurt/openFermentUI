// The banner over an archived program's entity (OF-BLD-016 §2.1, E.1′).
//
// Archived programs leave every list by default, but a deep link still opens
// what it names: a paper cited in an old answer, a strain page bookmarked
// last month. The page opens under this banner, which names the program and
// says where the switch is, rather than refusing the link or showing the
// entity as though nothing had changed. A detail page renders it at the top
// with its entity's kind and id; for a general entity, or one whose program
// is active, it renders nothing.
import { Archive } from 'lucide-react';
import { href } from '@/router';
import { PROGRAMS_SETTINGS_PATH } from '@/data/programs';
import { archivedProgramOf, useStore, type ProgramEntityKind } from '@/store';
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
  const records = useStore((s) => s.records);
  const runbooks = useStore((s) => s.runbooks);
  const depositions = useStore((s) => s.depositions);
  const program = archivedProgramOf(kind, id, { records, runbooks, depositions });
  if (!program) return null;
  return (
    <div
      role="note"
      data-archived-program={program.id}
      className={cx('rounded-card border border-line bg-ink-soft/[0.05] p-3 flex gap-2 mb-4', className)}
    >
      <Archive size={16} className="mt-[2px] shrink-0 text-ink-soft" aria-hidden />
      <div className="text-body">
        <div className="font-medium mb-0.5">
          This {NOUN[kind]} belongs to {program.name}, an archived program
        </div>
        <p className="text-ink-soft">
          {showArchived
            ? 'Archived programs are showing everywhere, because the switch in Settings is on. '
            : 'Archived programs are hidden from every list, count and answer; a link still opens what it names. '}
          <a className="text-accent underline underline-offset-2" href={href(PROGRAMS_SETTINGS_PATH)}>
            Settings → Programs
          </a>{' '}
          {showArchived ? 'turns them off again.' : 'shows them again.'}
        </p>
      </div>
    </div>
  );
}
