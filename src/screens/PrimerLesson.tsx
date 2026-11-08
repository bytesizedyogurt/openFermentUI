// Lesson page (OF-DES-001 §8.14). Reading column interleaved with live embeds,
// closing on a checkpoint whose numeric grading is unit-aware. The lesson is
// an entry of the project's lesson catalogue (alpha 2.2 E.12; ADR-018): its
// words, the skills it counts toward, and its body, its minutes, blocks and
// checkpoint. A lesson kept with no body shows its words and its skills.
//
// A lesson that names skills (OF-BLD-013 §3.2) counts toward them: the moment
// its checkpoint is passed, Primer writes a knowledge entry for each skill on
// the ledger of whoever is learning, which is whoever is signing in Guild.
// That entry puts them at Learning, and it is how the lesson shows passed: the
// browser keeps no lesson of its own. Supervised waits for an assessor's
// training sign-off at the bench, and the page says so before and after.
//
// Previous and next walk the project's lessons in the catalogue's order.
import { useState } from 'react';
import { ArrowLeft, ArrowRight, Check, RotateCcw, X } from 'lucide-react';
import { useSkillById, useStore } from '@/store';
import { href, navigate } from '@/router';
import type { CheckpointQuestion } from '@/lib/catalogues';
import { statusOf } from '@/engine/competence';
import { lessonOnLedger } from '@/engine/path';
import { ActingAs, useGuild } from '@/components/GuildBits';
import { LevelGlyph, levelLabel } from '@/components/LevelGlyph';
import { parseQuantity, quantityEquals } from '@/engine/units';
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

export default function PrimerLesson({ lessonId }: { lessonId: string }) {
  const SKILL_BY_ID = useSkillById();
  const lessons = useStore((s) => s.lessons);
  const read = useStore((s) => s.cataloguesRead);
  const problem = useStore((s) => s.cataloguesProblem);
  const recordLesson = useStore((s) => s.recordLessonForGuild);
  const toast = useStore((s) => s.toast);
  const ctx = useGuild();
  const [results, setResults] = useState<Record<string, boolean>>({});
  // Bumped to put every question back to unanswered, for a learner who
  // passed it before anyone was chosen and wants it to count.
  const [attempt, setAttempt] = useState(0);

  const index = lessons.findIndex((l) => l.id === lessonId);
  const lesson = index >= 0 ? lessons[index] : undefined;
  const prev = index > 0 ? lessons[index - 1] : null;
  const next = index >= 0 && index < lessons.length - 1 ? lessons[index + 1] : null;

  if (!lesson) {
    return (
      <EmptyState
        title={read ? 'Lesson not found' : problem ? 'The lessons could not be read' : 'Reading the project\u2019s lessons'}
        body={
          read
            ? `The project's lesson catalogue holds no lesson ${lessonId}.`
            : (problem ?? 'The lessons are read from the project\u2019s lesson catalogue as the page opens.')
        }
        action={<Button onClick={() => navigate('/primer')}>Back to Primer</Button>}
      />
    );
  }

  const checkpoint = lesson.checkpoint ?? [];
  const blocks = lesson.blocks ?? [];
  const allCorrect = checkpoint.length > 0 && checkpoint.every((q) => results[q.id]);

  const counts = lesson.skills ?? [];
  const learner = ctx.acting && ctx.acting.active && ctx.acting.role !== 'auditor' ? ctx.acting : null;
  const onLedger = learner ? lessonOnLedger(ctx.guild.evidence, learner.id, lesson) : [];
  // Passed on the ledger, or answered correctly on this page just now.
  const isComplete = (counts.length > 0 && onLedger.length === counts.length) || allCorrect;
  const skillNames = (ids: string[]) => ids.map((id) => SKILL_BY_ID[id]?.name ?? id).join(', ');

  const finish = () => {
    void recordLesson(lesson.id).then((r) => {
      if (r && r.skills.length > 0) {
        const who = ctx.personById.get(r.personId)?.name ?? r.personId;
        toast({ text: `On ${who}\u2019s ledger: lesson passed, Learning on ${skillNames(r.skills)}.`, kind: 'info' });
      }
    });
  };

  const onResult = (q: CheckpointQuestion, correct: boolean) => {
    const nextR = { ...results, [q.id]: correct };
    setResults(nextR);
    if (correct && checkpoint.every((x) => nextR[x.id])) finish();
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
          <a href={href('/primer')} className="text-caption text-ink-soft hover:text-accent shrink-0">
            Primer
          </a>
          <span className="text-ink-soft">·</span>
          <span className="text-caption text-ink-soft truncate flex-1">The project&rsquo;s lessons</span>
          {isComplete && (
            <span className="chip text-accent border-accent/40 shrink-0">
              <Check size={11} /> complete
            </span>
          )}
        </div>
      </div>

      <div className="mb-1 text-caption uppercase tracking-wide text-ink-soft font-num">
        Lesson {index + 1} of {lessons.length}
        {lesson.minutes != null && <> · {lesson.minutes} min</>}
      </div>
      <h1 className={cx('font-serif text-page-title font-semibold', lesson.summary ? 'mb-1' : 'mb-5')}>{lesson.name}</h1>
      {lesson.summary && (
        <p className="text-body text-ink-soft mb-5" data-testid="primer-lesson-summary">
          {lesson.summary}
        </p>
      )}

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
          {ctx.guild.people.length > 0 && <ActingAs id="lesson-learning-as" label="Learning as" />}
        </Card>
      )}

      {lesson.note && (
        <div className="font-serif mb-5" style={{ fontSize: 16, lineHeight: '25px' }}>
          <Markdown md={lesson.note} />
        </div>
      )}

      <div className="prose-reading">
        {blocks.map((block, i) =>
          block.kind === 'prose' ? (
            <div key={i} className="font-serif" style={{ fontSize: 16, lineHeight: '25px' }}>
              <Markdown md={block.md} />
            </div>
          ) : (
            <LessonEmbed key={i} embed={block.embed} arg={block.arg ?? undefined} />
          ),
        )}
      </div>

      {blocks.length === 0 && checkpoint.length === 0 && (
        <Card className="p-4 text-body text-ink-soft">
          The lesson catalogue keeps this lesson&rsquo;s name, words and skills, and no body yet: no block to read and no
          checkpoint to pass. A body kept in the{' '}
          <a className="text-accent hover:underline" href={href('/catalogues/lessons')}>
            lesson catalogue
          </a>{' '}
          appears here.
        </Card>
      )}

      {/* Checkpoint */}
      {checkpoint.length > 0 && (
        <section className="mt-8">
          <h2 className="font-serif text-section-title font-semibold mb-1">Checkpoint</h2>
          <p className="text-body text-ink-soft mb-3">
            {checkpoint.length} question{checkpoint.length === 1 ? '' : 's'}. Retry as many times as you like: the
            explanation is the point of each one.
          </p>
          <div className="space-y-3">
            {checkpoint.map((q) => (
              <Checkpoint key={`${q.id}:${attempt}`} q={q} onResult={(c) => onResult(q, c)} />
            ))}
          </div>
        </section>
      )}

      {isComplete && (
        <div className="mt-5">
          <Callout kind="info" title="Lesson complete">
            {counts.length === 0 && <p>This lesson counts toward no skill, so its passing goes on no ledger.</p>}
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
          <a href={href(`/primer/${prev.id}`)} className="btn max-w-[45%]" title={prev.name}>
            <ArrowLeft size={14} /> <span className="truncate">{prev.name}</span>
          </a>
        ) : (
          <span />
        )}
        {next ? (
          <a href={href(`/primer/${next.id}`)} className={cx('btn max-w-[45%]', isComplete && 'btn-primary')} title={next.name}>
            <span className="truncate">{next.name}</span> <ArrowRight size={14} />
          </a>
        ) : (
          <a href={href('/primer')} className="btn">
            Back to the lessons <ArrowRight size={14} />
          </a>
        )}
      </nav>
    </div>
  );
}
