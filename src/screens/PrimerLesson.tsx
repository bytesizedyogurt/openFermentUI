// Lesson page (OF-DES-001 §8.14). Reading column interleaved with live embeds,
// closing on a checkpoint whose numeric grading is unit-aware.
import { useMemo, useState } from 'react';
import { ArrowLeft, ArrowRight, Check, RotateCcw, X } from 'lucide-react';
import { useStore } from '@/store';
import { navigate } from '@/router';
import type { CheckpointQuestion } from '@/data/types';
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
  const [results, setResults] = useState<Record<string, boolean>>({});

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

  const onResult = (q: CheckpointQuestion, correct: boolean) => {
    recordCheckpoint(q.id, correct);
    setResults((r) => {
      const nextR = { ...r, [q.id]: correct };
      if (lesson.checkpoint.every((x) => nextR[x.id])) completeLesson(lesson.id);
      return nextR;
    });
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
              <Checkpoint key={q.id} q={q} onResult={(c) => onResult(q, c)} />
            ))}
          </div>
        </section>
      )}

      {isComplete && (
        <div className="mt-5">
          <Callout kind="info" title="Lesson complete">
            Recorded for this session. Progress lives in memory and resets on refresh — that is a
            stated constraint of this simulation, not an oversight.
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
