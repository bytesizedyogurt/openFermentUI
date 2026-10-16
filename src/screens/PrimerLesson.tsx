// Lesson page (OF-DES-001 §8.14). Reading column interleaved with live embeds,
// closing on a checkpoint whose numeric grading is unit-aware.
//
// A lesson that names skills (OF-BLD-013 §3.2) counts toward them: the moment
// its checkpoint is passed, Primer writes a knowledge entry for each skill on
// the ledger of whoever is learning, which is whoever is signing in Guild.
// That entry puts them at Learning. Supervised waits for an assessor's
// training sign-off at the bench, and the page says so before and after.
import { useMemo, useState } from 'react';
import { ArrowLeft, ArrowRight, Check, RotateCcw, X } from 'lucide-react';
import { useStore } from '@/store';
import { href, navigate } from '@/router';
import type { CheckpointQuestion } from '@/data/types';
import { SKILL_BY_ID } from '@/data/skills';
import { statusOf } from '@/engine/competence';
import { ActingAs, useGuild } from '@/components/GuildBits';
import { LevelGlyph, levelLabel } from '@/components/LevelGlyph';
import { parseQuantity, quantityEquals, fmt } from '@/engine/units';
import { Button, Card, EmptyState, cx, Callout } from '@/components/ui';
import { Markdown } from '@/components/Markdown';
import { CitationChip } from '@/components/Chip';
import { LessonEmbed } from '@/components/LessonEmbeds';

function Checkpoint({
  q,
  onResult,
}: {
  q: CheckpointQuestion;
  onResult: (correct: boolean) => void;
}) {
  const [choice, setChoice] = useState<number | null>(null);
  const [text, setText] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [correct, setCorrect] = useState(false);

  const grade = () => {
    let ok = false;
    if (q.kind === 'mc') {
      ok = choice === q.answerIndex;
    } else if (q.answer) {
      const parsed = parseQuantity(text.trim());
      // Unit-aware: 0.15 h⁻¹ and 3.6 d⁻¹ are the same answer.
      if (parsed) {
        ok =
          q.answer.unit === ''
            ? Math.abs(parsed.value - q.answer.value) <=
              (Math.abs(q.answer.value) * q.answer.tolerancePct) / 100
            : quantityEquals(parsed, q.answer, q.answer.tolerancePct);
      }
    }
    setCorrect(ok);
    setSubmitted(true);
    onResult(ok);
  };

  const reset = () => {
    setSubmitted(false);
    setChoice(null);
    setText('');
  };

  return (
    <Card className="p-4">
      <p className="text-reading font-medium mb-3">{q.prompt}</p>

      {q.kind === 'mc' ? (
        <div className="space-y-1.5">
          {(q.options ?? []).map((opt, i) => {
            const isAnswer = i === q.answerIndex;
            const chosen = choice === i;
            return (
              <button
                key={i}
                disabled={submitted}
                onClick={() => setChoice(i)}
                className={cx(
                  'w-full text-left px-3 py-2 rounded-btn border transition-colors flex items-start gap-2',
                  submitted && isAnswer && 'border-accent bg-accent-wash',
                  submitted && chosen && !isAnswer && 'border-signal-error bg-signal-error/[0.07]',
                  !submitted && chosen && 'border-accent bg-accent-wash',
                  !submitted && !chosen && 'border-line hover:border-accent/40',
                )}
              >
                <span className="shrink-0 mt-[3px]">
                  {submitted && isAnswer && <Check size={13} className="text-accent" />}
                  {submitted && chosen && !isAnswer && <X size={13} className="text-signal-error" />}
                  {!submitted && (
                    <span
                      className={cx(
                        'inline-block w-3 h-3 rounded-full border',
                        chosen ? 'border-accent bg-accent' : 'border-line',
                      )}
                    />
                  )}
                </span>
                <span className="text-body">{opt}</span>
              </button>
            );
          })}
        </div>
      ) : (
        <div className="flex gap-2 items-start">
          <input
            className={cx(
              'input font-num max-w-[240px]',
              submitted && (correct ? 'border-accent' : 'border-signal-error'),
            )}
            placeholder={q.answer?.unit ? `e.g. 0.15 ${q.answer.unit}` : 'e.g. 0.75'}
            value={text}
            disabled={submitted}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !submitted && text.trim() && grade()}
            aria-label="Your answer"
          />
          {q.answer?.unit && (
            <span className="text-caption text-ink-soft pt-2">
              any equivalent unit is accepted
            </span>
          )}
        </div>
      )}

      {!submitted ? (
        <Button
          variant="primary"
          className="mt-3"
          disabled={q.kind === 'mc' ? choice === null : !text.trim()}
          onClick={grade}
        >
          Check answer
        </Button>
      ) : (
        <div className="mt-3">
          <Callout kind={correct ? 'info' : 'warn'} title={correct ? 'Correct' : 'Not quite'}>
            <p>{q.explanation}</p>
            {q.evidenceChip && (
              <div className="mt-2 flex items-center gap-2">
                <span className="text-caption text-ink-soft">Evidence:</span>
                <CitationChip
                  paperId={q.evidenceChip.startsWith('r-') ? undefined : q.evidenceChip}
                  recordId={q.evidenceChip.startsWith('r-') ? q.evidenceChip : undefined}
                />
              </div>
            )}
          </Callout>
          {!correct && (
            <Button className="mt-2" onClick={reset}>
              <RotateCcw size={13} /> Try again
            </Button>
          )}
        </div>
      )}
    </Card>
  );
}

export default function PrimerLesson({ moduleId, lessonId }: { moduleId: string; lessonId: string }) {
  const modules = useStore((s) => s.modules);
  const progress = useStore((s) => s.learnProgress);
  const completeLesson = useStore((s) => s.completeLesson);
  const recordCheckpoint = useStore((s) => s.recordCheckpoint);
  const recordLesson = useStore((s) => s.recordLessonForGuild);
  const toast = useStore((s) => s.toast);
  const ctx = useGuild();
  const [results, setResults] = useState<Record<string, boolean>>({});
  // Bumped to put every question back to unanswered, for a learner who
  // passed it before anyone was chosen and wants it to count.
  const [attempt, setAttempt] = useState(0);

  const mod = modules.find((m) => m.id === moduleId);
  const lessonIndex = mod?.lessons.findIndex((l) => l.id === lessonId) ?? -1;
  const lesson = lessonIndex >= 0 ? mod!.lessons[lessonIndex] : undefined;

  const flat = useMemo(
    () => modules.flatMap((m) => m.lessons.map((l) => ({ moduleId: m.id, lessonId: l.id, title: l.title }))),
    [modules],
  );
  const flatIdx = flat.findIndex((f) => f.moduleId === moduleId && f.lessonId === lessonId);
  const prev = flatIdx > 0 ? flat[flatIdx - 1] : null;
  const next = flatIdx >= 0 && flatIdx < flat.length - 1 ? flat[flatIdx + 1] : null;

  if (!mod || !lesson) {
    return (
      <EmptyState
        title="Lesson not found"
        body={`No lesson ${lessonId} exists in module ${moduleId}.`}
        action={<Button onClick={() => navigate('/primer')}>Back to Primer</Button>}
      />
    );
  }

  const allCorrect =
    lesson.checkpoint.length > 0 && lesson.checkpoint.every((q) => results[q.id]);
  const isComplete = progress[lesson.id] || allCorrect;

  const counts = lesson.skills ?? [];
  const learner = ctx.acting && ctx.acting.active && ctx.acting.role !== 'auditor' ? ctx.acting : null;
  const onLedger = learner
    ? counts.filter((sk) =>
        ctx.guild.evidence.some(
          (e) =>
            e.personId === learner.id &&
            e.skillId === sk &&
            e.source.kind === 'lesson' &&
            e.source.ref === lesson.id &&
            !e.withdrawnAt,
        ),
      )
    : [];
  const skillNames = (ids: string[]) => ids.map((id) => SKILL_BY_ID[id]?.name ?? id).join(', ');

  const finish = () => {
    completeLesson(lesson.id);
    void recordLesson(lesson.id).then((r) => {
      if (r && r.skills.length > 0) {
        const who = ctx.personById.get(r.personId)?.name ?? r.personId;
        toast({ text: `On ${who}\u2019s ledger: lesson passed, Learning on ${skillNames(r.skills)}.`, kind: 'info' });
      }
    });
  };

  const onResult = (q: CheckpointQuestion, correct: boolean) => {
    recordCheckpoint(q.id, correct);
    const nextR = { ...results, [q.id]: correct };
    setResults(nextR);
    if (correct && lesson.checkpoint.every((x) => nextR[x.id])) finish();
  };

  const answerAgain = () => {
    setResults({});
    setAttempt((n) => n + 1);
  };

  return (
    <div className="max-w-[760px] mx-auto">
      {/* Sticky nav */}
      <div className="sticky top-0 z-20 -mx-5 px-5 py-2.5 bg-surface-0/95 backdrop-blur border-b border-line mb-5">
        <div className="flex items-center gap-3">
          <a href="#/primer" className="text-caption text-ink-soft hover:text-accent shrink-0">
            Module {mod.index}
          </a>
          <span className="text-ink-soft">·</span>
          <span className="text-caption text-ink-soft truncate flex-1">{mod.title}</span>
          {isComplete && (
            <span className="chip text-accent border-accent/40 shrink-0">
              <Check size={11} /> complete
            </span>
          )}
        </div>
      </div>

      <div className="mb-1 text-caption uppercase tracking-wide text-ink-soft font-num">
        Lesson {lessonIndex + 1} of {mod.lessons.length} · {lesson.minutes} min
      </div>
      <h1 className="font-serif text-page-title font-semibold mb-5">{lesson.title}</h1>

      {counts.length > 0 && (
        <Card className="p-3 mb-6 space-y-2" aria-label="What this lesson counts toward">
          <div className="flex flex-wrap items-center gap-2 text-body">
            <span className="text-ink-soft">Counts toward</span>
            {counts.map((id) => {
              const level = learner ? statusOf(ctx.status, learner.id, id).level : 0;
              return (
                <a key={id} className="chip inline-flex items-center gap-1.5" href={href(`/guild/skills/${id}`)}>
                  {learner && <LevelGlyph level={level} size={10} />}
                  {SKILL_BY_ID[id]?.name ?? id}
                  {learner && <span className="sr-only">: {levelLabel(statusOf(ctx.status, learner.id, id))}</span>}
                </a>
              );
            })}
          </div>
          <p className="text-body text-ink-soft">
            {learner ? (
              onLedger.length === counts.length ? (
                <>Already on {learner.name}&rsquo;s ledger as a lesson passed. A training sign-off from an assessor, at the bench, is the next step on each skill.</>
              ) : (
                <>
                  Passing the checkpoint records this lesson on {learner.name}&rsquo;s ledger, which puts them at Learning on each skill. A
                  training sign-off from an assessor, at the bench, is what moves them to Supervised.
                </>
              )
            ) : ctx.guild.people.length === 0 ? (
              <>
                Nobody is on Guild&rsquo;s ledger yet, so passing the checkpoint records nothing.{' '}
                <a className="text-accent hover:underline" href={href('/guild/matrix')}>
                  Start the ledger
                </a>
              </>
            ) : (
              <>Choose who is learning to have this lesson count toward a skill.</>
            )}
          </p>
          {ctx.sample && (
            <p className="text-caption text-signal-warn">
              Sample team: invented people. A lesson passed now is recorded on the sample alone.
            </p>
          )}
          {ctx.guild.people.length > 0 && <ActingAs id="lesson-learning-as" label="Learning as" />}
        </Card>
      )}

      <div className="prose-reading">
        {lesson.blocks.map((block, i) =>
          block.kind === 'prose' ? (
            <div key={i} className="font-serif" style={{ fontSize: 16, lineHeight: '25px' }}>
              <Markdown md={block.md} />
            </div>
          ) : (
            <LessonEmbed key={i} embed={block.embed} arg={block.arg} />
          ),
        )}
      </div>

      {/* Checkpoint */}
      {lesson.checkpoint.length > 0 && (
        <section className="mt-8">
          <h2 className="font-serif text-section-title font-semibold mb-1">Checkpoint</h2>
          <p className="text-body text-ink-soft mb-3">
            {lesson.checkpoint.length} question{lesson.checkpoint.length === 1 ? '' : 's'}. Retry as
            many times as you like — the explanation is the point, not the score.
          </p>
          <div className="space-y-3">
            {lesson.checkpoint.map((q) => (
              <Checkpoint key={`${q.id}:${attempt}`} q={q} onResult={(c) => onResult(q, c)} />
            ))}
          </div>
        </section>
      )}

      {isComplete && (
        <div className="mt-5">
          <Callout kind="info" title="Lesson complete">
            <p>Kept in this browser across a refresh.</p>
            {counts.length > 0 && learner && onLedger.length === counts.length && (
              <p className="mt-1">
                On {learner.name}&rsquo;s ledger as a lesson passed for {skillNames(counts)}.
              </p>
            )}
            {counts.length > 0 && onLedger.length < counts.length && (
              <div className="mt-1 space-y-2">
                <p>
                  {learner
                    ? `Not yet on ${learner.name}\u2019s ledger for ${skillNames(counts.filter((c) => !onLedger.includes(c)))}: the checkpoint was passed before ${learner.name} was chosen. Answer it again and it counts.`
                    : 'Recorded for nobody, because nobody was chosen as learning when the checkpoint was passed.'}
                </p>
                {learner && (
                  <Button size="sm" onClick={answerAgain}>
                    <RotateCcw size={13} /> Answer it again
                  </Button>
                )}
              </div>
            )}
          </Callout>
        </div>
      )}

      {/* Prev / next */}
      <nav className="flex items-center justify-between gap-3 mt-8 pt-4 border-t border-line">
        {prev ? (
          <a
            href={`#/primer/${prev.moduleId}/${prev.lessonId}`}
            className="btn max-w-[45%]"
            title={prev.title}
          >
            <ArrowLeft size={14} /> <span className="truncate">{prev.title}</span>
          </a>
        ) : (
          <span />
        )}
        {next ? (
          <a
            href={`#/primer/${next.moduleId}/${next.lessonId}`}
            className={cx('btn max-w-[45%]', isComplete && 'btn-primary')}
            title={next.title}
          >
            <span className="truncate">{next.title}</span> <ArrowRight size={14} />
          </a>
        ) : (
          <a href="#/primer" className="btn">
            Back to the module map <ArrowRight size={14} />
          </a>
        )}
      </nav>
    </div>
  );
}
