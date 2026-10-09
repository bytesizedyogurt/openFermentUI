// Bench check (OF-BLD-013 §5.4). A witnessed check run at the bench: one
// mastery criterion at a time, Meets or Needs work, the assessor's own words,
// and a final step that signs it in the assessor's name. Full-screen
// takeover; App renders this without the shell.
//
// It lives under Deposition's constraints, which are load-bearing here for
// the same reasons:
//
//   - 810px tablet portrait at arm's length is the responsive target;
//   - touch targets ≥ 44px, and the two calls are 56px, because the hand
//     holding the tablet may be gloved;
//   - criterion text on `ink`, never `ink-soft`, for ≥ 7:1 contrast;
//   - no hover-dependent affordance anywhere;
//   - full-screen, because nothing should compete with the criterion.
//
// Nothing here decides anything. The calls are the assessor's; the service's
// `checks.record` refuses a check with a criterion uncalled or a skill with
// no words, and writes one witnessed entry per skill with the check as its
// source. With the sample shown, the store writes the same entries to the
// sample alone.
import { useEffect, useMemo, useState } from 'react';
import { ArrowLeft, ArrowRight, Check as Tick, X } from 'lucide-react';
import type { Check, CheckResult } from '@/data/types';
import { useStore } from '@/store';
import { SKILL_BY_ID } from '@/data/skills';
import { Button, cx } from '@/components/ui';
import { nameOf, useChecks, useGuild, type GuildContext } from '@/components/GuildBits';
import { isOpen, shownTo } from '@/engine/checks';
import { isAssessor } from '@/engine/competence';
import { BriefView } from '@/screens/GuildChecks';
import { navigate } from '@/router';

const BIG = { minHeight: 56 };
const TAP = { minHeight: 44 };

type Item = { kind: 'criterion'; skillId: string; index: number } | { kind: 'words'; skillId: string };

export default function BenchCheck({ checkId }: { checkId: string }) {
  const ctx = useGuild();
  const loadChecks = useStore((s) => s.loadChecks);
  const serviceUp = useStore((s) => s.serviceUp);
  const { all } = useChecks();
  const [asked, setAsked] = useState(ctx.sample);
  useEffect(() => {
    if (ctx.sample) return;
    void loadChecks().finally(() => setAsked(true));
  }, [loadChecks, serviceUp, ctx.sample]);
  // Kept once found, so the done screen survives the check closing.
  const [held, setHeld] = useState<Check | null>(null);
  const found = shownTo(all, ctx.actingId).find((c) => c.id === checkId) ?? null;
  useEffect(() => {
    if (found && isOpen(found) && !held) setHeld(found);
  }, [found, held]);
  const check = held ?? (found && isOpen(found) ? found : null);

  if (!check) {
    return (
      <Shell title="Witnessed check" onExit={() => navigate('/guild/checks')}>
        <p className="text-ink" style={{ fontSize: 21, lineHeight: '31px' }}>
          {!asked ? 'Asking the service for this check.' : `There is no open check ${checkId} to run here.`}
        </p>
        {asked && (
          <p className="text-body text-ink mt-3">
            It may have been run or dismissed already, the service may not be answering, or it names whoever is acting. The queue lists what is open.
          </p>
        )}
        <div className="mt-6">
          <Button style={BIG} onClick={() => navigate('/guild/checks')}>
            Back to the queue
          </Button>
        </div>
      </Shell>
    );
  }
  return <Run key={check.id} ctx={ctx} check={check} />;
}

function Shell({ title, sub, onExit, children }: { title: string; sub?: string; onExit: () => void; children: React.ReactNode }) {
  return (
    <div className="h-full flex flex-col bg-surface-0">
      <header className="shrink-0 border-b border-line bg-surface-1 px-4 py-2.5 flex items-center gap-3">
        <div className="min-w-0 flex-1">
          <div className="font-serif text-section-title font-semibold truncate">{title}</div>
          {sub && <div className="text-caption text-ink truncate">{sub}</div>}
        </div>
        <Button style={TAP} onClick={onExit}>
          <X size={16} /> Exit
        </Button>
      </header>
      <main className="flex-1 overflow-y-auto p-5 sm:p-8">
        <div className="max-w-[720px] mx-auto">{children}</div>
      </main>
    </div>
  );
}

function Run({ ctx, check }: { ctx: GuildContext; check: Check }) {
  const record = useStore((s) => s.checksRecord);
  const setActing = useStore((s) => s.guildSetActing);
  const person = nameOf(ctx, check.personId);
  const items: Item[] = useMemo(
    () =>
      check.skillIds.flatMap((k) => [
        ...(SKILL_BY_ID[k]?.mastery ?? []).map((_, index) => ({ kind: 'criterion' as const, skillId: k, index })),
        { kind: 'words' as const, skillId: k },
      ]),
    [check.skillIds],
  );
  const criteriaTotal = items.filter((i) => i.kind === 'criterion').length;

  // -1 is the start: who is assessing, and the brief. items.length is the sign step.
  const [at, setAt] = useState(-1);
  const [calls, setCalls] = useState<Record<string, boolean>>({});
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [words, setWords] = useState<Record<string, string>>({});
  const [leaving, setLeaving] = useState(false);
  const [busy, setBusy] = useState(false);
  const [why, setWhy] = useState<string | null>(null);
  const [signed, setSigned] = useState<{ by: string; day: string } | null>(null);

  const key = (k: string, i: number) => `${k}#${i}`;
  const assessor = ctx.acting;
  const eligible = ctx.members.filter((m) => m.id !== check.personId && check.skillIds.every((k) => isAssessor(ctx.status, m.id, k)));
  const mayRun = !!assessor && eligible.some((m) => m.id === assessor.id);
  const started = Object.keys(calls).length > 0 || Object.values(words).some((w) => w.trim());
  const skillsLine = check.skillIds.map((k) => SKILL_BY_ID[k]?.name ?? k).join(', ');
  const exit = () => (started && !signed ? setLeaving(true) : navigate('/guild/checks'));

  const announce =
    at >= 0 && at < items.length
      ? items[at].kind === 'criterion'
        ? `Criterion ${items.slice(0, at + 1).filter((i) => i.kind === 'criterion').length} of ${criteriaTotal}`
        : `What you saw on ${SKILL_BY_ID[items[at].skillId]?.name}`
      : at === items.length
        ? 'Sign the check'
        : '';

  const shell = (children: React.ReactNode) => (
    <Shell title={`Witnessed check · ${person}`} sub={skillsLine} onExit={exit}>
      <div className="sr-only" aria-live="polite">
        {announce}
      </div>
      {leaving && (
        <div role="alertdialog" aria-label="Leave without signing" className="card p-4 mb-5 border-signal-warn/50">
          <p className="text-ink text-reading">Leave without signing? The calls made so far are not kept, and the check stays in the queue.</p>
          <div className="flex flex-wrap gap-2 mt-3">
            <Button style={TAP} onClick={() => navigate('/guild/checks')}>
              Leave without signing
            </Button>
            <Button style={TAP} variant="primary" onClick={() => setLeaving(false)}>
              Stay
            </Button>
          </div>
        </div>
      )}
      {children}
    </Shell>
  );

  // ── signed ───────────────────────────────────────────────────────────
  if (signed) {
    return shell(
      <div className="space-y-5">
        <div className="flex items-center gap-3">
          <span className="w-10 h-10 rounded-full bg-accent text-surface-1 grid place-items-center">
            <Tick size={22} />
          </span>
          <p className="text-ink font-medium" style={{ fontSize: 21, lineHeight: '31px' }}>
            Signed by {nameOf(ctx, signed.by)} on {signed.day}.
          </p>
        </div>
        <p className="text-reading text-ink">
          {check.skillIds.length} witnessed {check.skillIds.length === 1 ? 'entry is' : 'entries are'} on {person}&rsquo;s ledger, each with your
          words and this check as its source. The Matrix reads them now.
        </p>
        <div className="flex flex-wrap gap-2">
          <Button style={BIG} variant="primary" onClick={() => navigate(`/guild/people/${check.personId}`)}>
            Open {person}&rsquo;s ledger
          </Button>
          <Button style={BIG} onClick={() => navigate('/guild/checks')}>
            Back to the queue
          </Button>
        </div>
      </div>,
    );
  }

  // ── start: who is assessing, and the brief ───────────────────────────
  if (at === -1) {
    return shell(
      <div className="space-y-6">
        <div>
          <div className="text-caption uppercase tracking-wide text-ink-soft mb-1">Assessing</div>
          {mayRun ? (
            <p className="text-ink" style={{ fontSize: 21, lineHeight: '31px' }}>
              {assessor!.name}, assessor on {check.skillIds.length === 1 ? 'this skill' : 'each of these skills'}.
            </p>
          ) : (
            <p className="text-ink text-reading">
              {assessor ? `${assessor.name} cannot run this check: ` : ''}a check is run by an assessor on every one of its skills, never by the
              person checked. Who is assessing?
            </p>
          )}
          <div className="flex flex-wrap gap-2 mt-3">
            {eligible.map((m) => (
              <Button
                key={m.id}
                style={TAP}
                variant={assessor?.id === m.id ? 'primary' : 'default'}
                aria-pressed={assessor?.id === m.id}
                onClick={() => setActing(m.id)}
              >
                I am {m.name}
              </Button>
            ))}
            {eligible.length === 0 && <p className="text-body text-ink">Nobody on the ledger is an assessor on every one of these skills.</p>}
          </div>
        </div>

        <div>
          <div className="text-caption uppercase tracking-wide text-ink-soft mb-1">Checking</div>
          <p className="text-ink text-reading">
            {person}, on {skillsLine}: <span className="font-num">{criteriaTotal}</span> criteria, one at a time.
          </p>
          <ul className="list-disc pl-5 mt-2 text-body text-ink">
            {check.reasons.map((r, i) => (
              <li key={i}>
                <span className="font-medium">{SKILL_BY_ID[r.skillId]?.name ?? r.skillId}:</span> {r.text}
              </li>
            ))}
          </ul>
        </div>

        {check.brief && (
          <div className="card p-4">
            <div className="text-caption uppercase tracking-wide text-ink-soft mb-2">Brief</div>
            <BriefView brief={check.brief} large />
          </div>
        )}

        <Button style={BIG} variant="primary" className="w-full justify-center" disabled={!mayRun} onClick={() => setAt(0)}>
          Begin with the first criterion <ArrowRight size={18} />
        </Button>
      </div>,
    );
  }

  // ── sign ─────────────────────────────────────────────────────────────
  if (at === items.length) {
    const day = ctx.today;
    const results: CheckResult[] = items
      .filter((i): i is Extract<Item, { kind: 'criterion' }> => i.kind === 'criterion')
      .map((i) => ({ skillId: i.skillId, criterion: i.index, meets: calls[key(i.skillId, i.index)], note: (notes[key(i.skillId, i.index)] ?? '').trim() }));
    const complete = results.every((r) => typeof r.meets === 'boolean');
    return shell(
      <div className="space-y-5">
        <p className="text-ink font-medium" style={{ fontSize: 21, lineHeight: '31px' }}>
          Sign the check on {person}
        </p>
        {check.skillIds.map((k) => {
          const mine = results.filter((r) => r.skillId === k);
          const met = mine.every((r) => r.meets);
          return (
            <div key={k} className="card p-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium text-ink text-reading">{SKILL_BY_ID[k]?.name ?? k}</span>
                <span className={cx('chip', met ? 'text-accent border-accent/40' : 'text-signal-error border-signal-error/40')}>
                  {met ? 'every criterion met' : `${mine.filter((r) => !r.meets).length} need work`}
                </span>
              </div>
              <p className="text-body text-ink mt-1">
                {met
                  ? 'Writes a witnessed pass to the ledger.'
                  : 'Writes a witnessed check not met. Someone who holds the skill is suspended on it until a passed re-check.'}
              </p>
              <p className="text-body text-ink mt-1">&ldquo;{words[k]?.trim()}&rdquo;</p>
            </div>
          );
        })}
        <p className="text-body text-ink">
          Dated <span className="font-num">{day}</span>, signed as {assessor?.name ?? 'nobody'}.
        </p>
        {why && (
          <p role="alert" className="text-reading text-signal-error">
            {why}
          </p>
        )}
        <div className="flex flex-wrap gap-2">
          <Button style={TAP} onClick={() => setAt(at - 1)}>
            <ArrowLeft size={16} /> Back
          </Button>
          <Button
            style={BIG}
            variant="primary"
            className="flex-1 justify-center"
            disabled={!mayRun || !complete || busy}
            onClick={async () => {
              setBusy(true);
              setWhy(null);
              const r = await record(
                check.id,
                results,
                check.skillIds.map((k) => ({ skillId: k, text: words[k] ?? '' })),
                day,
              );
              setBusy(false);
              if (r) setWhy(r);
              else setSigned({ by: assessor!.id, day });
            }}
          >
            {busy ? 'Signing…' : `Sign as ${assessor?.name ?? 'nobody'}`}
          </Button>
        </div>
      </div>,
    );
  }

  // ── one criterion, or the words on one skill ─────────────────────────
  const item = items[at];
  const skill = SKILL_BY_ID[item.skillId];
  const ofSkill = items.filter((i) => i.kind === 'criterion' && i.skillId === item.skillId).length;
  const nth = items.slice(0, at + 1).filter((i) => i.kind === 'criterion').length;
  const k = item.kind === 'criterion' ? key(item.skillId, item.index) : '';
  const call = item.kind === 'criterion' ? calls[k] : undefined;
  const ready = item.kind === 'criterion' ? typeof call === 'boolean' : (words[item.skillId] ?? '').trim().length >= 2;

  return shell(
    <div>
      <div className="flex flex-wrap items-center gap-2 mb-3">
        <span className="text-caption uppercase tracking-wide text-ink-soft font-num">
          {item.kind === 'criterion' ? `Criterion ${item.index + 1} of ${ofSkill} · ${skill?.name}` : `${skill?.name} · in your words`}
        </span>
        <span className="text-caption text-ink-soft font-num ml-auto">
          {Math.min(nth, criteriaTotal)} of {criteriaTotal} called
        </span>
      </div>
      <div className="w-full h-2 rounded-full bg-ink-soft/15 overflow-hidden mb-5">
        <div className="h-full bg-accent rounded-full" style={{ width: `${(Object.keys(calls).length / criteriaTotal) * 100}%` }} />
      </div>

      {item.kind === 'criterion' ? (
        <>
          {/* ink, not ink-soft: ≥7:1 contrast at arm's length */}
          <p className="text-ink font-medium mb-5" style={{ fontSize: 21, lineHeight: '31px' }}>
            {skill?.mastery[item.index]}
          </p>
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              className={cx('btn justify-center text-reading', call === true && 'btn-primary')}
              style={BIG}
              aria-pressed={call === true}
              onClick={() => setCalls((c) => ({ ...c, [k]: true }))}
            >
              <Tick size={18} /> Meets
            </button>
            <button
              type="button"
              className={cx('btn justify-center text-reading', call === false && 'btn-needs-work')}
              style={BIG}
              aria-pressed={call === false}
              onClick={() => setCalls((c) => ({ ...c, [k]: false }))}
            >
              <X size={18} /> Needs work
            </button>
          </div>
          <label className="block mt-5">
            <span className="text-caption text-ink">What you saw on this criterion, if anything to add (kept as written)</span>
            <textarea
              id={`bench-note-${at}`}
              className="input font-sans resize-y min-h-[88px] w-full mt-1 text-reading"
              value={notes[k] ?? ''}
              onChange={(e) => setNotes((n) => ({ ...n, [k]: e.target.value }))}
            />
          </label>
        </>
      ) : (
        <>
          <p className="text-ink font-medium mb-2" style={{ fontSize: 21, lineHeight: '31px' }}>
            What did you see {person} do on {skill?.name}?
          </p>
          <p className="text-body text-ink mb-3">
            Kept word for word as the entry on {person}&rsquo;s ledger, where an auditor reads it beside your name.
          </p>
          <ul className="mb-3 space-y-1">
            {items
              .filter((i): i is Extract<Item, { kind: 'criterion' }> => i.kind === 'criterion' && i.skillId === item.skillId)
              .map((i) => (
                <li key={i.index} className="text-body text-ink flex gap-2">
                  <span className={cx('chip shrink-0', calls[key(i.skillId, i.index)] ? 'text-accent border-accent/40' : 'text-signal-error border-signal-error/40')}>
                    {calls[key(i.skillId, i.index)] ? 'Meets' : 'Needs work'}
                  </span>
                  <span>{skill?.mastery[i.index]}</span>
                </li>
              ))}
          </ul>
          <label className="sr-only" htmlFor={`bench-words-${item.skillId}`}>
            What you saw on {skill?.name}
          </label>
          <textarea
            id={`bench-words-${item.skillId}`}
            className="input font-sans resize-y min-h-[120px] w-full text-reading"
            value={words[item.skillId] ?? ''}
            onChange={(e) => setWords((w) => ({ ...w, [item.skillId]: e.target.value }))}
          />
        </>
      )}

      <div className="flex gap-2 mt-6">
        <Button style={TAP} onClick={() => setAt(at - 1)}>
          <ArrowLeft size={16} /> Back
        </Button>
        <Button style={BIG} variant="primary" className="flex-1 justify-center" disabled={!ready} onClick={() => setAt(at + 1)}>
          {at + 1 === items.length ? 'To the sign step' : 'Next'} <ArrowRight size={18} />
        </Button>
      </div>
    </div>,
  );
}
