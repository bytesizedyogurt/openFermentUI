// Primer's lessons (OF-DES-001 §8.14; alpha 2.2 E.12).
//
// The lessons are the project's lesson catalogue (lib/catalogues.ts), read
// from GET /api/catalogues/lesson, each with the skills it counts toward and
// its body (ADR-018). No lesson ships with the app (ADR-010): until the lab
// keeps one at /catalogues/lessons, the page says so. A lesson shows passed
// from Guild's ledger: passing its checkpoint writes a knowledge entry for
// each skill it counts toward on the ledger of whoever is learning, and this
// browser keeps no lesson of its own.
import { BookOpen, Check, Clock } from 'lucide-react';
import { useSkillById, useStore } from '@/store';
import { lessonPassed } from '@/engine/path';
import { ActingAs, useGuild } from '@/components/GuildBits';
import { PageHeader, Card, EmptyState, LinkButton, cx } from '@/components/ui';
import { OwnerTabs } from '@/components/OwnerTabs';
import { PRIMER_TABS } from '@/data/tabs';
import { href } from '@/router';

/** Completion ring: the lessons the learner has passed, from the ledger. */
function Ring({ done, total }: { done: number; total: number }) {
  const r = 15;
  const c = 2 * Math.PI * r;
  const frac = total === 0 ? 0 : done / total;
  return (
    <svg width="38" height="38" viewBox="0 0 38 38" aria-label={`${done} of ${total} lessons passed`}>
      <circle cx="19" cy="19" r={r} fill="none" stroke="rgb(var(--line))" strokeWidth="3.5" />
      <circle
        cx="19"
        cy="19"
        r={r}
        fill="none"
        stroke="rgb(var(--accent))"
        strokeWidth="3.5"
        strokeLinecap="round"
        strokeDasharray={c}
        strokeDashoffset={c * (1 - frac)}
        transform="rotate(-90 19 19)"
      />
      <text x="19" y="23" textAnchor="middle" fontSize="11" className="font-num" fill="rgb(var(--ink))">
        {done}
      </text>
    </svg>
  );
}

export default function Primer() {
  const SKILL_BY_ID = useSkillById();
  const lessons = useStore((s) => s.lessons);
  const read = useStore((s) => s.cataloguesRead);
  const problem = useStore((s) => s.cataloguesProblem);
  const ctx = useGuild();
  const learner = ctx.acting && ctx.acting.active && ctx.acting.role !== 'auditor' ? ctx.acting : null;

  // A lesson toward no skill goes on no ledger, so only the others can show passed.
  const counted = lessons.filter((l) => (l.skills ?? []).length > 0);
  const passed = (id: string) => {
    const lesson = lessons.find((l) => l.id === id);
    return !!learner && !!lesson && lessonPassed(ctx.guild.evidence, learner.id, lesson);
  };
  const done = counted.filter((l) => passed(l.id)).length;

  return (
    <div>
      <PageHeader
        eyebrow="Learn the system"
        title="Primer"
        subtitle="Bioprocess taught through the live platform: the project's lessons, each with the skills it counts toward and its checkpoint."
        actions={
          learner && counted.length > 0 ? (
            <span className="text-body text-ink-soft font-num">
              {done}/{counted.length} passed by {learner.name}
            </span>
          ) : undefined
        }
      />
      <OwnerTabs tabs={PRIMER_TABS} />

      <div className="max-w-[860px] space-y-4">
        {problem && (
          <Card className="p-4 text-body" role="alert">
            The project&rsquo;s lessons could not be read: {problem}
          </Card>
        )}
        {lessons.length === 0 && !problem && (
          <Card>
            <EmptyState
              icon={<BookOpen size={22} />}
              title={read ? 'No lesson yet' : 'Reading the project’s lessons'}
              body={
                <span data-testid="primer-empty">
                  {read ? (
                    <>
                      No lesson ships with the app. A lesson the lab keeps in the{' '}
                      <a className="text-accent hover:underline" href={href('/catalogues/lessons')}>
                        lesson catalogue
                      </a>{' '}
                      appears here, with the skills it counts toward and its checkpoint.
                    </>
                  ) : (
                    'The lessons are read from the project’s lesson catalogue as the page opens.'
                  )}
                </span>
              }
            />
          </Card>
        )}

        {lessons.length > 0 && (
          <Card className="p-4">
            <div className="flex items-start gap-4">
              <div className="shrink-0 pt-0.5">
                <Ring done={done} total={counted.length} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h2 className="font-serif text-section-title font-semibold leading-snug">The project&rsquo;s lessons</h2>
                  {ctx.guild.people.length > 0 && <ActingAs id="primer-learning-as" label="Learning as" />}
                </div>
                <p className="text-body text-ink-soft mt-1">
                  {learner
                    ? `A lesson shows passed when ${learner.name}’s ledger holds its passing on every skill it counts toward.`
                    : ctx.guild.people.length === 0
                      ? 'Nobody is on Guild’s ledger yet, so no lesson shows as passed.'
                      : 'Choose who is learning, and the lessons their ledger holds as passed show here.'}
                </p>

                <div className="mt-3 space-y-1.5">
                  {lessons.map((lesson) => {
                    const complete = passed(lesson.id);
                    const counts = lesson.skills ?? [];
                    const checks = (lesson.checkpoint ?? []).length;
                    return (
                      <a
                        key={lesson.id}
                        href={href(`/primer/${lesson.id}`)}
                        className={cx(
                          'flex items-center gap-2.5 px-2.5 py-2 rounded-btn border transition-colors',
                          complete
                            ? 'border-accent/35 bg-accent-wash'
                            : 'border-line hover:border-accent/40 hover:bg-ink-soft/[0.04]',
                        )}
                      >
                        <span
                          className={cx(
                            'shrink-0 w-5 h-5 rounded-full grid place-items-center',
                            complete ? 'bg-accent text-surface-1' : 'border border-line',
                          )}
                        >
                          {complete ? <Check size={12} /> : <BookOpen size={11} className="text-ink-soft" />}
                        </span>
                        <span className="flex-1 min-w-0">
                          <span className="block text-body truncate">{lesson.name}</span>
                          {lesson.summary && <span className="block text-caption text-ink truncate">{lesson.summary}</span>}
                          <span className="block text-caption text-ink-soft truncate">
                            {counts.length > 0
                              ? `Counts toward ${counts.map((id) => SKILL_BY_ID[id]?.name ?? id).join(', ')}`
                              : 'Counts toward no skill, so passing it goes on no ledger'}
                          </span>
                        </span>
                        {lesson.minutes != null && (
                          <span className="text-caption text-ink-soft font-num shrink-0 flex items-center gap-1">
                            <Clock size={11} /> {lesson.minutes} min
                          </span>
                        )}
                        <span className="text-caption text-ink-soft shrink-0 hidden sm:inline font-num">
                          {checks === 0 ? 'no checkpoint' : `${checks} checkpoint question${checks === 1 ? '' : 's'}`}
                        </span>
                      </a>
                    );
                  })}
                </div>

                <div className="mt-3">
                  <LinkButton to={`/primer/${(lessons.find((l) => !passed(l.id)) ?? lessons[0]).id}`} variant="primary" size="sm">
                    {done > 0 ? 'Continue' : 'Start the first lesson'}
                  </LinkButton>
                </div>
              </div>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
