// A person's path (OF-BLD-013 §3.3): for every skill, the one step that moves
// it next, and which part of My path it belongs in. Pure, like
// `competenceOf`: it reads statuses and lessons and holds nothing. The words
// on the screen are PrimerPath's; the rules are here, where check:guild can
// hold them still.
//
//   refresh   Qualified, and suspended, lapsed, or lapsing within the window
//   held      Qualified or Assessor, and current
//   waiting   a prerequisite is below Supervised, so nothing here moves it yet
//   bench     the screen has done its part: every lesson passed and a training
//             sign-off is next, or the supervised runs are done and a
//             witnessed check is next
//   next      a lesson to take, supervised runs to do, or (when no lesson
//             counts toward the skill) a training sign-off to ask for
import type { Skill } from '@/data/types';
import { addDays, readyForCheck, statusOf, type CompetenceStatus, type StatusMap } from './competence';

export type PathSection = 'next' | 'refresh' | 'bench' | 'held' | 'waiting';

export type PathStep =
  | { kind: 'suspended' }
  | { kind: 'lapsed' }
  | { kind: 'lapsing' }
  | { kind: 'held' }
  | { kind: 'waiting'; on: string[] }
  | { kind: 'witnessed-check' }
  | { kind: 'cosigned-runs'; done: number; needed: number }
  | { kind: 'lesson'; lessonId: string; passed: number; total: number }
  /** `lessons` is how many lessons count toward the skill; zero when none does yet. */
  | { kind: 'training-signoff'; lessons: number };

export interface PathItem {
  skill: Skill;
  status: CompetenceStatus;
  section: PathSection;
  step: PathStep;
  /** A run in progress needs this skill. */
  soon: boolean;
}

/** How far ahead "due for refresh" looks, in days. */
export const REFRESH_WINDOW = 30;

export function pathOf(input: {
  personId: string;
  skills: Skill[];
  status: StatusMap;
  /** Lessons that count toward each skill, in the order Primer lists them. */
  lessonsFor: Record<string, { id: string }[]>;
  /** Whether this person has passed this lesson for this skill. */
  passed: (skillId: string, lessonId: string) => boolean;
  /** Skills a run in progress needs. */
  soon: Set<string>;
  today: string;
}): PathItem[] {
  const { personId, skills, status, lessonsFor, passed, soon, today } = input;
  const horizon = addDays(today, REFRESH_WINDOW);
  const items = skills.map((skill): PathItem => {
    const st = statusOf(status, personId, skill.id);
    const at = (section: PathSection, step: PathStep): PathItem => ({ skill, status: st, section, step, soon: soon.has(skill.id) });
    if (st.level >= 3) {
      if (st.suspended) return at('refresh', { kind: 'suspended' });
      if (st.lapsed) return at('refresh', { kind: 'lapsed' });
      if (st.level === 3 && st.lapsesAt && st.lapsesAt <= horizon) return at('refresh', { kind: 'lapsing' });
      return at('held', { kind: 'held' });
    }
    if (st.blockedBy.length > 0) return at('waiting', { kind: 'waiting', on: st.blockedBy });
    if (st.level === 2) {
      if (readyForCheck(st, skill)) return at('bench', { kind: 'witnessed-check' });
      return at('next', { kind: 'cosigned-runs', done: st.supervisedCount, needed: skill.supervisedRuns });
    }
    const lessons = lessonsFor[skill.id] ?? [];
    const open = lessons.find((l) => !passed(skill.id, l.id));
    if (open)
      return at('next', {
        kind: 'lesson',
        lessonId: open.id,
        passed: lessons.filter((l) => passed(skill.id, l.id)).length,
        total: lessons.length,
      });
    return at(lessons.length > 0 ? 'bench' : 'next', { kind: 'training-signoff', lessons: lessons.length });
  });
  // Within a section: what a run in progress needs, then critical skills, then
  // skills a lesson can move, then the furthest behind.
  const hasLesson = (i: PathItem) => (lessonsFor[i.skill.id]?.length ?? 0) > 0;
  return items.sort(
    (a, b) =>
      Number(b.soon) - Number(a.soon) ||
      Number(b.skill.criticality === 'critical') - Number(a.skill.criticality === 'critical') ||
      Number(hasLesson(b)) - Number(hasLesson(a)) ||
      a.status.level - b.status.level,
  );
}
