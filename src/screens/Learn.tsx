// Module map (OF-DES-001 §8.14).
import { BookOpen, Check, Clock, Lock } from 'lucide-react';
import { useStore } from '@/store';
import { PageHeader, Card, LinkButton, cx } from '@/components/ui';

/** Completion ring — session-scoped progress, no persistence (§9.5). */
function Ring({ done, total }: { done: number; total: number }) {
  const r = 15;
  const c = 2 * Math.PI * r;
  const frac = total === 0 ? 0 : done / total;
  return (
    <svg width="38" height="38" viewBox="0 0 38 38" aria-label={`${done} of ${total} lessons complete`}>
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

export default function Learn() {
  const modules = useStore((s) => s.modules);
  const progress = useStore((s) => s.learnProgress);

  const totalDone = modules.reduce(
    (n, m) => n + m.lessons.filter((l) => progress[l.id]).length,
    0,
  );
  const totalLessons = modules.reduce((n, m) => n + m.lessons.length, 0);

  return (
    <div>
      <PageHeader
        title="Learn"
        subtitle="Bioprocess taught through the live platform rather than beside it. Every embedded widget in these lessons is the real component, operating on the real session state."
        actions={
          <span className="text-body text-ink-soft font-num">
            {totalDone}/{totalLessons} lessons complete
          </span>
        }
      />

      <div className="max-w-[860px] space-y-4">
        {modules.map((mod) => {
          const done = mod.lessons.filter((l) => progress[l.id]).length;
          const isFlagship = mod.lessons.length >= 4;
          return (
            <Card key={mod.id} className="p-4">
              <div className="flex items-start gap-4">
                <div className="shrink-0 pt-0.5">
                  <Ring done={done} total={mod.lessons.length} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-baseline gap-2 flex-wrap">
                    <span className="font-num text-caption text-ink-soft">
                      Module {mod.index}
                    </span>
                    {isFlagship && (
                      <span className="chip text-accent border-accent/40 text-[11px] py-0">
                        fully built
                      </span>
                    )}
                  </div>
                  <h2 className="font-serif text-section-title font-semibold leading-snug">
                    {mod.title}
                  </h2>
                  <p className="text-body text-ink-soft mt-1">{mod.blurb}</p>

                  <div className="mt-3 space-y-1.5">
                    {mod.lessons.map((lesson) => {
                      const complete = progress[lesson.id];
                      return (
                        <a
                          key={lesson.id}
                          href={`#/learn/${mod.id}/${lesson.id}`}
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
                          <span className="flex-1 text-body truncate">{lesson.title}</span>
                          <span className="text-caption text-ink-soft font-num shrink-0 flex items-center gap-1">
                            <Clock size={11} /> {lesson.minutes} min
                          </span>
                          <span className="text-caption text-ink-soft shrink-0 hidden sm:inline font-num">
                            {lesson.checkpoint.length} checks
                          </span>
                        </a>
                      );
                    })}

                    {mod.outline?.map((item) => (
                      <div
                        key={item}
                        className="flex items-center gap-2.5 px-2.5 py-2 rounded-btn border border-dashed border-line text-ink-soft"
                      >
                        <Lock size={12} className="shrink-0" />
                        <span className="flex-1 text-body truncate">{item}</span>
                        <span className="text-caption shrink-0">outlined, not yet written</span>
                      </div>
                    ))}
                  </div>

                  {mod.lessons.length > 0 && (
                    <div className="mt-3">
                      <LinkButton
                        to={`/learn/${mod.id}/${mod.lessons[0].id}`}
                        variant={isFlagship ? 'primary' : 'default'}
                        size="sm"
                      >
                        {done > 0 ? 'Continue module' : 'Start module'}
                      </LinkButton>
                    </div>
                  )}
                </div>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
