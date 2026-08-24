// Deposition capture, at the bench (OF-BLD-006 §4.3, §4.4).
//
// Rendered inside RunMode, under the current step. It inherits that screen's
// constraints and does not get to relax them: 810px tablet portrait at arm's
// length, touch targets at least 44px, primary text on `ink` rather than
// `ink-soft` for contrast, and nothing that depends on hover — a gloved hand
// on a tablet has no hover state to give.
//
// THE OPERATOR NEVER FILLS A FORM. One box. They describe what they see, and
// the system decides afterwards whether it belongs in the schema. A form with
// a field per measure would be faster to build and would discard exactly the
// observation worth having, because an unexpected result has no field waiting
// for it — by definition.
import { useMemo, useState } from 'react';
import { AlertTriangle, Check, CornerDownLeft, Eye, Ruler } from 'lucide-react';
import type { Deposition, Measure } from '@/data/types';
import { useStore } from '@/store';
import { matchToSchema, readBackText, type CaptureMatch } from '@/engine/capture';
import { ComponentTag } from './ComponentTag';
import { Button, cx } from './ui';

export function DepositionPanel({
  deposition,
  schema,
  stepId,
}: {
  deposition: Deposition;
  schema: Measure[];
  stepId: string;
}) {
  const capture = useStore((s) => s.captureDeposition);
  const confirm = useStore((s) => s.confirmEntry);
  const amend = useStore((s) => s.amendEntry);
  const [text, setText] = useState('');
  const [amending, setAmending] = useState<string | null>(null);
  const [amendText, setAmendText] = useState('');

  const closed = deposition.state === 'closed';

  // Previewed live, so the operator can see where a line is about to land
  // before committing it — and correct the wording instead of the record.
  const preview: CaptureMatch | null = useMemo(
    () => (text.trim() ? matchToSchema(text, schema) : null),
    [text, schema],
  );

  const measureById = useMemo(
    () => Object.fromEntries(schema.map((m) => [m.id, m])),
    [schema],
  );

  const unconfirmed = deposition.entries.filter((e) => !e.confirmed);
  const stepEntries = deposition.entries.filter((e) => e.stepId === stepId);
  const stepObs = deposition.observations.filter((o) => o.stepId === stepId);

  const submit = () => {
    const raw = text.trim();
    if (!raw || closed) return;
    capture(deposition.id, stepId, raw, preview);
    setText('');
  };

  return (
    <section className="card p-4 mt-4" aria-label="Record what happened">
      <div className="flex items-center gap-2 mb-2">
        <Ruler size={16} className="text-accent shrink-0" aria-hidden />
        <span className="font-medium text-reading">Record what happened</span>
        <span className="ml-auto font-num text-caption text-ink-soft">
          {deposition.entries.length} measured · {deposition.observations.length} observed
        </span>
      </div>

      <p className="text-body text-ink mb-2">
        Say it however you say it. Anything that matches the plan is filed as a measurement;
        everything else is kept word for word.
      </p>

      <textarea
        className="input text-reading w-full"
        style={{ minHeight: 88 }}
        rows={2}
        value={text}
        disabled={closed}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          // Enter commits; Shift+Enter is a newline. A gloved thumb should not
          // have to find a small button to file a line.
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            submit();
          }
        }}
        placeholder="e.g. titre came in at 7.4 g/L — or — foam was worse than usual on the second impeller"
        aria-label="Describe what you observed"
      />

      <div className="flex flex-wrap items-center gap-2 mt-2">
        <Button variant="primary" style={{ minHeight: 44 }} onClick={submit} disabled={closed || !text.trim()}>
          <CornerDownLeft size={15} /> Record
        </Button>
        {text.trim() &&
          (preview ? (
            <span className="text-body text-accent">
              files as <span className="font-num">{measureById[preview.measureId]?.label}</span> ={' '}
              <span className="font-num">{readBackText(preview)}</span>
            </span>
          ) : (
            <span className="text-body text-ink-soft inline-flex items-center gap-1.5">
              <Eye size={14} aria-hidden /> kept as an observation — nothing in the plan matches it
            </span>
          ))}
      </div>

      {/* §4.4 — read back numbers, not narrative. */}
      {unconfirmed.length > 0 && (
        <div className="mt-4 rounded-card border border-signal-warn/50 bg-signal-warn/[0.10] p-3">
          <div className="flex items-center gap-2 mb-1.5">
            <AlertTriangle size={15} className="text-signal-warn shrink-0" aria-hidden />
            <span className="font-medium text-ink">
              Read {unconfirmed.length === 1 ? 'this' : 'these'} back before we keep{' '}
              {unconfirmed.length === 1 ? 'it' : 'them'}
            </span>
          </div>
          <p className="text-body text-ink mb-2">
            &ldquo;Four two&rdquo; is 4.2 or 42, and getting it wrong is silent. Numbers get one
            check; narrative does not.
          </p>
          <ul className="space-y-2">
            {unconfirmed.map((e) => (
              <li key={e.id} className="rounded-input bg-surface-1 border border-line p-2.5">
                <div className="text-reading text-ink">
                  <span className="font-num">{measureById[e.measureId]?.label ?? e.measureId}</span>
                  {' = '}
                  <span className="font-num font-medium">
                    {e.value} {e.unit}
                  </span>
                </div>
                <div className="text-caption text-ink-soft mt-0.5">
                  you said: &ldquo;{e.raw}&rdquo;
                </div>
                {amending === e.id ? (
                  <div className="flex flex-wrap items-center gap-2 mt-2">
                    <input
                      className="input font-num text-reading"
                      style={{ minHeight: 44, width: 140 }}
                      type="number"
                      autoFocus
                      value={amendText}
                      onChange={(ev) => setAmendText(ev.target.value)}
                      aria-label={`Corrected value for ${measureById[e.measureId]?.label ?? e.measureId}`}
                    />
                    <Button
                      variant="primary"
                      style={{ minHeight: 44 }}
                      onClick={() => {
                        const v = Number(amendText);
                        if (isFinite(v)) amend(deposition.id, e.id, v);
                        setAmending(null);
                        setAmendText('');
                      }}
                    >
                      Save correction
                    </Button>
                    <Button style={{ minHeight: 44 }} onClick={() => setAmending(null)}>
                      Cancel
                    </Button>
                  </div>
                ) : (
                  <div className="flex flex-wrap gap-2 mt-2">
                    <Button
                      variant="primary"
                      style={{ minHeight: 44 }}
                      onClick={() => confirm(deposition.id, e.id)}
                    >
                      <Check size={15} /> That is right
                    </Button>
                    <Button
                      style={{ minHeight: 44 }}
                      onClick={() => {
                        setAmending(e.id);
                        setAmendText(String(e.value));
                      }}
                    >
                      No — fix it
                    </Button>
                  </div>
                )}
              </li>
            ))}
          </ul>
          <p className="text-caption text-ink-soft mt-2">
            A correction is appended, never written over the top. What you first said stays in the
            record with the correction beside it.
          </p>
        </div>
      )}

      {(stepEntries.length > 0 || stepObs.length > 0) && (
        <div className="mt-4 pt-3 border-t border-line">
          <div className="text-caption uppercase tracking-wide text-ink-soft mb-1.5">
            Recorded at this step
          </div>
          <ul className="space-y-1.5">
            {stepEntries.map((e) => (
              <li key={e.id} className="text-body text-ink flex items-baseline gap-2">
                <span
                  className={cx(
                    'w-1.5 h-1.5 rounded-full shrink-0 mt-1.5',
                    e.confirmed ? 'bg-accent' : 'bg-signal-warn',
                  )}
                  aria-hidden
                />
                <span>
                  <span className="font-num">{measureById[e.measureId]?.label ?? e.measureId}</span>{' '}
                  <span className="font-num font-medium">
                    {e.value} {e.unit}
                  </span>
                  {!e.confirmed && <span className="text-signal-warn"> · unconfirmed</span>}
                </span>
              </li>
            ))}
            {stepObs.map((o) => (
              <li key={o.id} className="text-body text-ink flex items-baseline gap-2">
                <Eye size={13} className="text-ink-soft shrink-0 mt-1" aria-hidden />
                <span className="text-ink">&ldquo;{o.raw}&rdquo;</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-3">
        <ComponentTag
          component="Deposition"
          action={closed ? 'closed to new entries' : 'recording'}
        />
      </div>
    </section>
  );
}
