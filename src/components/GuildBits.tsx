// Shared pieces of Guild's workforce views (OF-BLD-013 §1.4): the header with
// its tab strip and Acting as, one ledger entry, the sign-off sheet, the form
// that adds a person, and the ledger export. The review queue in
// src/screens/Guild.tsx shares only the tab strip.
import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { Check, Download, UserPlus, X } from 'lucide-react';
import type { Check as GuildCheck, DecisionCheck, Guild, GuildEvidence, GuildPerson, GuildRole, Skill } from '@/data/types';
import { useStore, guildView, actingIdOf } from '@/store';
import { SKILLS, SKILL_BY_ID } from '@/data/skills';
import { PROTOCOLS } from '@/data/protocols';
import { GUILD_TABS } from '@/data/tabs';
import { OwnerTabs } from '@/components/OwnerTabs';
import { Button, Callout, Card, PageHeader, Sheet, cx } from '@/components/ui';
import { LevelGlyph, levelLabel } from '@/components/LevelGlyph';
import {
  LEVEL_NAME,
  addDays,
  competenceOf,
  isAssessor,
  localToday,
  readyForCheck,
  statusOf,
  type StatusMap,
} from '@/engine/competence';
import { checkEvidence, offlineRefusal } from '@/lib/guild';
import { isOpen, mayQueue, shownTo } from '@/engine/checks';
import { download } from '@/lib/csv';
import { href, useRoute } from '@/router';

// ── the ledger, as every Guild view reads it ───────────────────────────

export interface GuildContext {
  guild: Guild;
  status: StatusMap;
  today: string;
  actingId: string | null;
  acting: GuildPerson | null;
  sample: boolean;
  /** Active people who can hold skills: everyone but auditors and the inactive. */
  members: GuildPerson[];
  personById: Map<string, GuildPerson>;
}

export function useGuild(): GuildContext {
  const guild = useStore((s) => guildView(s));
  const actingId = useStore((s) => actingIdOf(s));
  const sample = useStore((s) => s.guildSample !== null);
  const today = localToday();
  const status = useMemo(() => competenceOf(guild.evidence, guild.people, SKILL_BY_ID, today), [guild, today]);
  const personById = useMemo(() => new Map(guild.people.map((p) => [p.id, p])), [guild.people]);
  const members = useMemo(() => guild.people.filter((p) => p.active && p.role !== 'auditor'), [guild.people]);
  return { guild, status, today, actingId, acting: (actingId && personById.get(actingId)) || null, sample, members, personById };
}

// ── checks, as every Guild view reads them (OF-BLD-013 §5.4) ──────────

/** The checks the store holds: the sample's while it is shown. `loaded` is false until the service answers. */
export function useChecks(): { all: GuildCheck[]; loaded: boolean } {
  const sample = useStore((s) => s.guildSample !== null);
  const sampleChecks = useStore((s) => s.guildSampleChecks);
  const served = useStore((s) => s.checks);
  return useMemo(
    () => (sample ? { all: sampleChecks ?? [], loaded: true } : { all: served?.checks ?? [], loaded: served !== null }),
    [sample, sampleChecks, served],
  );
}

/**
 * Guild's tab strip. Checks shows for the lead and for assessors, with the
 * count of open checks they may see, and for anyone already on it, so the
 * strip never points at a tab other than the page it sits on.
 */
export function GuildTabs() {
  const ctx = useGuild();
  const { all } = useChecks();
  const route = useRoute();
  const here = route.segments[0] === 'guild' && route.segments[1] === 'checks';
  const queue = mayQueue(ctx.acting, ctx.status);
  const open = queue ? shownTo(all, ctx.actingId).filter(isOpen).length : 0;
  const tabs = GUILD_TABS.filter((t) => t.to !== '/guild/checks' || queue || here).map((t) =>
    t.to === '/guild/checks' && open > 0 ? { ...t, badge: open } : t,
  );
  return <OwnerTabs tabs={tabs} />;
}

export function nameOf(ctx: Pick<GuildContext, 'personById'>, id: string | null | undefined): string {
  if (!id) return 'nobody';
  return ctx.personById.get(id)?.name ?? id;
}

// ── header ─────────────────────────────────────────────────────────────

/** Who is signing, or learning: one choice shared by Guild, run mode and Primer. */
export function ActingAs({ id, label = 'Acting as' }: { id: string; label?: string }) {
  const { guild, actingId } = useGuild();
  const setActing = useStore((s) => s.guildSetActing);
  if (guild.people.length === 0) return null;
  return (
    <label className="flex items-center gap-2 text-caption text-ink-soft">
      <span className="hidden sm:inline">{label}</span>
      <select
        id={id}
        aria-label={label}
        className="input py-1 max-w-[240px]"
        value={actingId ?? ''}
        onChange={(e) => setActing(e.target.value || null)}
      >
        <option value="">Nobody chosen</option>
        {guild.people
          .filter((p) => p.active)
          .map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
              {p.title ? ` · ${p.title}` : ''}
            </option>
          ))}
      </select>
    </label>
  );
}

export function GuildHeader({ title, subtitle }: { title: string; subtitle: ReactNode }) {
  const sample = useStore((s) => s.guildSample !== null);
  const clearSample = useStore((s) => s.guildClearSample);
  const pending = useStore((s) => s.guildPending.length + s.guildPendingWithdrawals.length);
  const serviceUp = useStore((s) => s.serviceUp);
  return (
    <>
      <PageHeader
        eyebrow="Guild of Applied Life"
        title={title}
        subtitle={subtitle}
        actions={
          <div className="hidden md:block">
            <ActingAs id="guild-acting-as" />
          </div>
        }
      />
      {/* At phone width the selector gets its own row, so the title keeps the width. */}
      <div className="md:hidden -mt-2 mb-4">
        <ActingAs id="guild-acting-as-narrow" />
      </div>
      {sample && (
        <div className="mb-4">
          <Callout kind="warn" title="Sample team: invented people">
            <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <span>Everything shown here is made up, and nothing you do to it is saved or sent to the service.</span>
              <Button size="sm" onClick={clearSample}>
                Hide the sample
              </Button>
            </span>
          </Callout>
        </div>
      )}
      {!sample && pending > 0 && (
        <p className="text-caption text-signal-warn mb-3">
          {pending} change{pending === 1 ? '' : 's'} kept in this browser
          {serviceUp === false ? ' until the service answers' : ', being sent to the service'}.
        </p>
      )}
      <GuildTabs />
    </>
  );
}

// ── one ledger entry ───────────────────────────────────────────────────

export const KIND_LABEL: Record<GuildEvidence['kind'], string> = {
  knowledge: 'Training sign-off',
  supervised: 'Supervised run',
  witnessed: 'Witnessed check',
  designation: 'Assessor designation',
  independent: 'Independent run',
  deviation: 'Deviation',
  scenario: 'Practice',
};

/** What an entry is called: a lesson passed is knowledge nobody signed. */
export function kindLabel(e: Pick<GuildEvidence, 'kind' | 'source'>): string {
  return e.kind === 'knowledge' && e.source.kind === 'lesson' ? 'Lesson passed' : KIND_LABEL[e.kind];
}

/** Strongest tick for what an assessor watched, lightest for a briefing; lessons and practice are self-recorded. */
function tickFor(e: GuildEvidence): string {
  if (e.withdrawnAt) return 'tick tick-unverified';
  if (e.source.kind === 'lesson' || e.source.kind === 'scenario') return 'tick tick-user';
  if (e.kind === 'witnessed') return e.outcome === 'fail' ? 'tick tick-rejected' : 'tick tick-measured';
  if (e.kind === 'designation') return 'tick tick-gold';
  if (e.kind === 'supervised' || e.kind === 'independent') return 'tick tick-verified';
  if (e.kind === 'deviation') return 'tick tick-industry-estimate';
  return 'tick tick-curated';
}

export function EvidenceRow({
  e,
  ctx,
  showPerson,
  showSkill,
}: {
  e: GuildEvidence;
  ctx: GuildContext;
  showPerson?: boolean;
  showSkill?: boolean;
}) {
  const withdraw = useStore((s) => s.guildWithdraw);
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState('');
  const mayWithdraw =
    !e.withdrawnAt && !!ctx.acting && (ctx.acting.id === e.observerId || (ctx.acting.role === 'lead' && ctx.acting.active));
  const src =
    e.source.kind === 'lead' ? (
      'Lead'
    ) : e.source.kind === 'lesson' ? (
      <a className="text-accent hover:underline" href={href(`/primer/${e.source.ref}`)}>
        Primer lesson {e.source.ref}
      </a>
    ) : e.source.kind === 'scenario' ? (
      <a className="text-accent hover:underline" href={href(`/primer/practice/${e.source.ref}`)}>
        Practice transcript {e.source.ref}
      </a>
    ) : e.source.kind === 'check' ? (
      <a className="text-accent hover:underline" href={href(`/guild/checks/${e.source.ref}`)}>
        Bench check {e.source.ref}
      </a>
    ) : e.source.stepId ? (
      `${e.source.ref} · step ${e.source.stepId}`
    ) : (
      e.source.ref
    );
  return (
    <div className={cx(tickFor(e), 'py-2')}>
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
        <span className="font-num text-caption text-ink-soft">{e.at.slice(0, 10)}</span>
        <span className={cx('font-medium', e.withdrawnAt && 'line-through text-ink-soft')}>{kindLabel(e)}</span>
        {e.outcome === 'fail' && <span className="chip text-signal-error border-signal-error/40">not met</span>}
        {showSkill && (
          <a className="chip" href={href(`/guild/skills/${e.skillId}`)}>
            {SKILL_BY_ID[e.skillId]?.name ?? e.skillId}
          </a>
        )}
        {showPerson && (
          <a className="text-accent hover:underline" href={href(`/guild/people/${e.personId}`)}>
            {nameOf(ctx, e.personId)}
          </a>
        )}
        {!e.recordedAt && !ctx.sample && <span className="chip text-signal-warn border-signal-warn/40">not yet on the service</span>}
      </div>
      <div className="text-body text-ink-soft">
        &ldquo;{e.raw}&rdquo;
        <span className="text-caption">
          {' '}
          · {src}
          {e.observerId && (
            <>
              {' '}
              · {e.kind === 'designation' ? 'by' : e.kind === 'supervised' ? 'cosigned by' : 'observed by'} {nameOf(ctx, e.observerId)}
            </>
          )}
        </span>
      </div>
      {e.withdrawnAt && (
        <div className="text-caption text-ink-soft">
          Withdrawn {e.withdrawnAt.slice(0, 10)} by {nameOf(ctx, e.withdrawnBy)}: &ldquo;{e.withdrawReason}&rdquo;
        </div>
      )}
      {mayWithdraw && !open && (
        <button type="button" className="text-caption text-ink-soft hover:text-signal-error mt-0.5" onClick={() => setOpen(true)}>
          Withdraw
        </button>
      )}
      {open && (
        <div className="flex flex-wrap items-center gap-2 mt-1">
          <label className="sr-only" htmlFor={`withdraw-${e.id}`}>
            Why is this entry withdrawn
          </label>
          <input
            id={`withdraw-${e.id}`}
            className="input flex-1 min-w-[180px]"
            placeholder="Why it is withdrawn"
            value={reason}
            onChange={(ev) => setReason(ev.target.value)}
          />
          <Button
            size="sm"
            disabled={reason.trim().length < 2}
            onClick={async () => {
              if (await withdraw(e.id, reason)) setOpen(false);
            }}
          >
            Withdraw entry
          </Button>
          <Button size="sm" onClick={() => setOpen(false)}>
            Keep it
          </Button>
        </div>
      )}
    </div>
  );
}

// ── asking the service ─────────────────────────────────────────────────

/** The service's answer about an entry, asked shortly after it stops changing. Null while unknown. */
function useServiceCheck(entry: GuildEvidence | null): DecisionCheck | null {
  const serviceUp = useStore((s) => s.serviceUp);
  const sample = useStore((s) => s.guildSample !== null);
  const [answer, setAnswer] = useState<DecisionCheck | null>(null);
  const key = entry ? JSON.stringify({ ...entry, id: '' }) : '';
  useEffect(() => {
    setAnswer(null);
    if (!entry || !serviceUp || sample) return;
    const ctl = new AbortController();
    const t = window.setTimeout(() => {
      checkEvidence(entry, ctl.signal).then(setAnswer, () => undefined);
    }, 250);
    return () => {
      ctl.abort();
      window.clearTimeout(t);
    };
    // The key holds everything about the entry except its fresh id.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, serviceUp, sample]);
  return answer;
}

// ── the sign-off sheet ─────────────────────────────────────────────────

type SignKind = 'knowledge' | 'supervised' | 'witnessed';

const SIGN_LABEL: Record<SignKind, string> = {
  knowledge: 'Training sign-off',
  supervised: 'Supervised run',
  witnessed: 'Witnessed check',
};

const SIGN_HINT: Record<SignKind, string> = {
  knowledge: 'You briefed them on the procedure and they talked it back to you.',
  supervised: 'They performed it with you beside them.',
  witnessed: 'You watched them perform it against every criterion below.',
};

function stepsNeeding(skillId: string): { ref: string; stepId: string; text: string }[] {
  const out: { ref: string; stepId: string; text: string }[] = [];
  for (const p of PROTOCOLS) {
    const v = p.versions.find((x) => x.version === p.currentVersion) ?? p.versions[0];
    for (const st of v.steps) if (st.skills?.includes(skillId)) out.push({ ref: p.id, stepId: st.id, text: st.text });
  }
  return out;
}

export function SignoffSheet({ personId, skillId, onClose }: { personId: string | null; skillId: string | null; onClose: () => void }) {
  if (!personId || !skillId) return null;
  return <SheetBody key={`${personId}|${skillId}`} personId={personId} skillId={skillId} onClose={onClose} />;
}

function SheetBody({ personId, skillId, onClose }: { personId: string; skillId: string; onClose: () => void }) {
  const ctx = useGuild();
  const record = useStore((s) => s.guildRecord);
  const toast = useStore((s) => s.toast);
  const skill: Skill | undefined = SKILL_BY_ID[skillId];
  const person = ctx.personById.get(personId);
  const st = statusOf(ctx.status, personId, skillId);
  const entries = ctx.guild.evidence.filter((e) => e.personId === personId && e.skillId === skillId).slice().reverse();
  const steps = useMemo(() => stepsNeeding(skillId), [skillId]);

  const [kind, setKind] = useState<SignKind>(() =>
    !skill || !st.knowledgeComplete ? 'knowledge' : readyForCheck(st, skill) || st.level >= 3 ? 'witnessed' : 'supervised',
  );
  const [marks, setMarks] = useState<Record<number, 'meets' | 'needs'>>({});
  const [day, setDay] = useState(ctx.today);
  const [where, setWhere] = useState(steps[0] ? `${steps[0].ref}|${steps[0].stepId}` : '');
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [designating, setDesignating] = useState(false);
  const [designNote, setDesignNote] = useState('');

  const mastery = skill?.mastery ?? [];
  const canSign = !!ctx.acting && ctx.acting.id !== personId && isAssessor(ctx.status, ctx.acting.id, skillId);
  const canDesignate =
    !!ctx.acting && ctx.acting.role === 'lead' && ctx.acting.id !== personId && st.level < 4 && person?.role !== 'auditor';
  const allMarked = kind !== 'witnessed' || mastery.every((_, i) => marks[i]);
  const passed = kind !== 'witnessed' || mastery.every((_, i) => marks[i] === 'meets');
  const missed = mastery.filter((_, i) => marks[i] === 'needs');
  const [ref, stepId] = where ? where.split('|') : ['', ''];

  const draft: GuildEvidence | null =
    ctx.acting && allMarked
      ? {
          id: 'e-draft-0000',
          personId,
          skillId,
          kind,
          outcome: passed ? 'pass' : 'fail',
          at: day,
          observerId: ctx.acting.id,
          source: { kind: 'signoff', ref: ref || 'training record', stepId: stepId || null },
          raw: note.trim() || (kind === 'witnessed' && passed ? 'Met every criterion at the bench' : ''),
          recordedAt: null,
        }
      : null;
  const local = draft ? offlineRefusal(draft, ctx.guild) : null;
  const asked = useServiceCheck(canSign && draft && !local ? draft : null);
  const blocked = local ?? (asked && !asked.ok ? { rule: asked.rule ?? 'unknown', why: asked.why ?? '' } : null);

  if (!skill || !person) return null;

  const sign = async () => {
    if (!draft) return;
    setBusy(true);
    const { id: _draftId, recordedAt: _r, ...rest } = draft;
    const stored = await record(rest);
    setBusy(false);
    if (stored) {
      toast({ text: `Signed: ${SIGN_LABEL[kind].toLowerCase()} on ${skill.name} for ${person.name}`, kind: passed ? 'success' : 'warn' });
      setMarks({});
      setNote('');
    }
  };

  const designate = async () => {
    if (!ctx.acting) return;
    setBusy(true);
    const stored = await record({
      personId,
      skillId,
      kind: 'designation',
      outcome: 'pass',
      at: ctx.today,
      observerId: ctx.acting.id,
      source: { kind: 'lead', ref: 'designation' },
      raw: designNote.trim() || `Designated assessor on ${skill.name}`,
    });
    setBusy(false);
    if (stored) {
      setDesignating(false);
      toast({ text: `${person.name} can now sign off ${skill.name}`, kind: 'success' });
    }
  };

  return (
    <Sheet open onClose={onClose} title={`${person.name} · ${skill.name}`}>
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-3 text-body">
          <Fact label="Level">
            <span className="inline-flex items-center gap-1.5">
              <LevelGlyph status={st} size={12} /> {levelLabel(st)}
            </span>
          </Fact>
          <Fact label="Confidence">{st.level > 0 ? st.confidence : '·'}</Fact>
          <Fact label="Last performed">
            <span className="font-num">{st.lastPerformedAt ?? 'never'}</span>
          </Fact>
          <Fact label={st.lapsed ? 'Lapsed on' : 'Lapses on'}>
            <span className={cx('font-num', st.lapsed && 'text-signal-warn')}>{st.lapsesAt ?? '·'}</span>
          </Fact>
          <Fact label="Supervised runs">
            <span className="font-num">
              {st.supervisedCount} of {skill.supervisedRuns}
            </span>
          </Fact>
          <Fact label="Training">{st.knowledgeComplete ? 'Signed off' : 'Not yet'}</Fact>
        </div>

        {st.blockedBy.length > 0 && (
          <Callout kind="info" title="Held at Learning by a prerequisite">
            {st.blockedBy.map((s) => SKILL_BY_ID[s]?.name ?? s).join(', ')} must reach Supervised first.
          </Callout>
        )}
        {st.suspended && (
          <Callout kind="error" title="Suspended">
            The latest witnessed check did not meet every criterion. {person.name} runs this skill with a cosigner until a check passes.
          </Callout>
        )}
        {st.lapsed && (
          <Callout kind="warn" title="Lapsed">
            Nothing on {person.name}&rsquo;s ledger shows them performing this within {skill.recencyDays} days: no witnessed check, cosigned
            run or run alone. A cosigned run or a passed witnessed check brings it back.
          </Callout>
        )}
        {readyForCheck(st, skill) && (
          <Callout kind="info" title="Ready for a witnessed check">
            Training and supervised runs are complete. A passed check makes this Qualified.
          </Callout>
        )}

        {canSign ? (
          <div className="rounded-card border border-line p-3 space-y-3">
            <div className="font-medium">Record what you saw</div>
            <div className="flex flex-wrap gap-1.5" role="radiogroup" aria-label="What you are signing">
              {(Object.keys(SIGN_LABEL) as SignKind[]).map((k) => (
                <button
                  key={k}
                  type="button"
                  role="radio"
                  aria-checked={kind === k}
                  className={cx('chip py-1', kind === k && 'chip-active')}
                  onClick={() => setKind(k)}
                >
                  {SIGN_LABEL[k]}
                </button>
              ))}
            </div>
            <p className="text-caption text-ink-soft">{SIGN_HINT[kind]}</p>

            {kind === 'witnessed' && (
              <ol className="space-y-1.5">
                {skill.mastery.map((m, i) => (
                  <li key={m} className="flex flex-wrap items-center gap-2">
                    <span className="flex-1 min-w-[180px] text-body">{m}</span>
                    <span className="flex gap-1">
                      <button
                        type="button"
                        aria-pressed={marks[i] === 'meets'}
                        className={cx('chip py-1', marks[i] === 'meets' && 'chip-active')}
                        onClick={() => setMarks((x) => ({ ...x, [i]: 'meets' }))}
                      >
                        <Check size={12} /> Meets
                      </button>
                      <button
                        type="button"
                        aria-pressed={marks[i] === 'needs'}
                        className={cx('chip py-1', marks[i] === 'needs' && 'border-signal-error/60 text-signal-error')}
                        onClick={() => setMarks((x) => ({ ...x, [i]: 'needs' }))}
                      >
                        <X size={12} /> Needs work
                      </button>
                    </span>
                  </li>
                ))}
              </ol>
            )}

            <div className="grid sm:grid-cols-2 gap-2">
              <label className="text-caption text-ink-soft flex flex-col gap-1">
                Seen on
                <input
                  id="signoff-day"
                  type="date"
                  className="input font-num"
                  value={day}
                  max={ctx.today}
                  onChange={(e) => setDay(e.target.value || ctx.today)}
                />
              </label>
              <label className="text-caption text-ink-soft flex flex-col gap-1">
                At step
                <select id="signoff-step" className="input" value={where} onChange={(e) => setWhere(e.target.value)}>
                  <option value="">No step: a training record</option>
                  {steps.map((s) => (
                    <option key={s.ref + s.stepId} value={`${s.ref}|${s.stepId}`}>
                      {s.ref} · {s.stepId}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <label className="text-caption text-ink-soft flex flex-col gap-1">
              In your words
              <textarea
                id="signoff-note"
                className="input min-h-[72px] text-body"
                placeholder={
                  kind === 'witnessed' && allMarked && !passed
                    ? `What you saw on: ${missed.join('; ')}`
                    : kind === 'witnessed' && allMarked
                      ? 'Met every criterion at the bench'
                      : 'What you saw'
                }
                value={note}
                onChange={(e) => setNote(e.target.value)}
              />
            </label>

            {kind === 'witnessed' && allMarked && (
              <p className={cx('text-body', passed ? 'text-accent' : 'text-signal-error')}>
                {passed
                  ? `Every criterion met. Signing records a passed check${st.knowledgeComplete && st.supervisedCount >= skill.supervisedRuns ? ', which makes this Qualified' : ''}.`
                  : `Not every criterion met. Signing records a check that did not pass${st.level >= 3 ? ', which suspends this skill until one does' : ''}.`}
              </p>
            )}
            <div className="flex flex-wrap items-center gap-2">
              <Button variant="primary" disabled={!draft || !!blocked || busy || (!passed && !note.trim())} onClick={sign}>
                Sign as {ctx.acting?.name}
              </Button>
              {!allMarked && <span className="text-caption text-ink-soft">Mark every criterion first.</span>}
              {allMarked && !passed && !note.trim() && (
                <span className="text-caption text-ink-soft">A check that did not pass needs your words.</span>
              )}
              {blocked && <span className="text-caption text-signal-error">{blocked.why}</span>}
            </div>
          </div>
        ) : (
          <p className="text-caption text-ink-soft">
            {!ctx.acting
              ? 'Choose who you are with Acting as to sign anything here.'
              : ctx.acting.id === personId
                ? 'Nobody signs off their own work.'
                : `Sign-offs on ${skill.name} are made by an assessor on it. ${ctx.acting.name} is not one.`}
          </p>
        )}

        {canDesignate &&
          (designating ? (
            <div className="rounded-card border border-gold/50 p-3 space-y-2">
              <div className="font-medium">Designate {person.name} an assessor on {skill.name}</div>
              <p className="text-caption text-ink-soft">
                They will be able to sign off this skill for anyone else. The designation stands until you withdraw it.
              </p>
              <input
                id="designate-note"
                className="input w-full"
                placeholder="Why, in your words"
                value={designNote}
                onChange={(e) => setDesignNote(e.target.value)}
              />
              <div className="flex gap-2">
                <Button variant="primary" disabled={busy} onClick={designate}>
                  Designate
                </Button>
                <Button onClick={() => setDesignating(false)}>Not now</Button>
              </div>
            </div>
          ) : (
            <Button size="sm" onClick={() => setDesignating(true)}>
              Designate as assessor
            </Button>
          ))}

        <div>
          <div className="text-caption uppercase tracking-wide text-ink-soft mb-1">Entries, newest first</div>
          {entries.length === 0 ? (
            <p className="text-body text-ink-soft">Nothing recorded yet.</p>
          ) : (
            <div className="divide-y divide-line">
              {entries.map((e) => (
                <EvidenceRow key={e.id} e={e} ctx={ctx} />
              ))}
            </div>
          )}
        </div>
        <div className="flex gap-3 text-body">
          <a className="text-accent hover:underline" href={href(`/guild/people/${personId}`)} onClick={onClose}>
            {person.name}&rsquo;s ledger
          </a>
          <a className="text-accent hover:underline" href={href(`/guild/skills/${skillId}`)} onClick={onClose}>
            About {skill.name}
          </a>
        </div>
      </div>
    </Sheet>
  );
}

function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="min-w-0">
      <div className="text-caption uppercase tracking-wide text-ink-soft">{label}</div>
      <div className="mt-0.5">{children}</div>
    </div>
  );
}

// ── adding a person ────────────────────────────────────────────────────

export function AddPersonForm({ onDone }: { onDone?: () => void }) {
  const ctx = useGuild();
  const add = useStore((s) => s.guildAddPerson);
  const first = ctx.guild.people.length === 0;
  const [name, setName] = useState('');
  const [title, setTitle] = useState(first ? 'Lead' : '');
  const [role, setRole] = useState<GuildRole>(first ? 'lead' : 'member');
  const [joined, setJoined] = useState(ctx.today);
  const [busy, setBusy] = useState(false);
  const canAdd = first || (ctx.acting?.role === 'lead' && ctx.acting.active);
  return (
    <form
      className="space-y-2"
      onSubmit={async (e) => {
        e.preventDefault();
        setBusy(true);
        const stored = await add({ name, title, role: first ? 'lead' : role, joinedAt: joined });
        setBusy(false);
        if (stored) {
          setName('');
          setTitle('');
          onDone?.();
        }
      }}
    >
      <div className="grid sm:grid-cols-2 gap-2">
        <label className="text-caption text-ink-soft flex flex-col gap-1">
          Name
          <input id="person-name" className="input text-body" value={name} onChange={(e) => setName(e.target.value)} autoComplete="off" />
        </label>
        <label className="text-caption text-ink-soft flex flex-col gap-1">
          Title
          <input id="person-title" className="input text-body" value={title} onChange={(e) => setTitle(e.target.value)} />
        </label>
        <label className="text-caption text-ink-soft flex flex-col gap-1">
          Role
          <select
            id="person-role"
            className="input text-body"
            value={first ? 'lead' : role}
            disabled={first}
            onChange={(e) => setRole(e.target.value as GuildRole)}
          >
            <option value="member">Member: learns and runs steps</option>
            <option value="lead">Lead: adds people, designates assessors</option>
            <option value="auditor">Auditor: reads the ledger, holds no skills</option>
          </select>
        </label>
        <label className="text-caption text-ink-soft flex flex-col gap-1">
          Joined
          <input id="person-joined" type="date" className="input font-num" value={joined} max={ctx.today} onChange={(e) => setJoined(e.target.value || ctx.today)} />
        </label>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Button type="submit" variant="primary" disabled={busy || name.trim().length < 2 || !canAdd}>
          <UserPlus size={14} /> {first ? 'Start the ledger as its lead' : 'Add person'}
        </Button>
        {!canAdd && <span className="text-caption text-ink-soft">Only the lead adds people. Choose the lead with Acting as.</span>}
        {first && <span className="text-caption text-ink-soft">The first person on the ledger is its lead.</span>}
      </div>
    </form>
  );
}

// ── export ─────────────────────────────────────────────────────────────

/** One person's ledger as CSV, with a header that says what the file is. */
export function exportLedger(ctx: GuildContext, personId: string) {
  const person = ctx.personById.get(personId);
  if (!person) return;
  const esc = (v: unknown) => {
    const s = v === null || v === undefined ? '' : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const rows = ctx.guild.evidence
    .filter((e) => e.personId === personId)
    .map((e) => [
      e.at.slice(0, 10),
      SKILL_BY_ID[e.skillId]?.name ?? e.skillId,
      kindLabel(e),
      e.outcome,
      nameOf(ctx, e.observerId),
      e.source.stepId ? `${e.source.ref} ${e.source.stepId}` : e.source.ref,
      e.raw,
      e.recordedAt ?? 'not yet on the service',
      e.withdrawnAt ? `withdrawn ${e.withdrawnAt.slice(0, 10)} by ${nameOf(ctx, e.withdrawnBy)}: ${e.withdrawReason}` : '',
    ]);
  const levels = Object.values(SKILL_BY_ID).map((sk) => {
    const st = statusOf(ctx.status, personId, sk.id);
    return `#   ${sk.name}: ${LEVEL_NAME[st.level]}${st.suspended ? ', suspended' : ''}${st.lapsed ? ', lapsed' : ''}`;
  });
  const body = [
    `# openFerment Guild ledger — ${person.name}${person.title ? `, ${person.title}` : ''}`,
    `# Exported ${ctx.today}.${ctx.sample ? ' SAMPLE TEAM: invented people, not a real record.' : ''}`,
    '# Every row is an entry as recorded. Levels are computed from the rows that are not withdrawn:',
    ...levels,
    ['date', 'skill', 'entry', 'outcome', 'observer', 'source', 'note', 'recorded', 'withdrawn'].join(','),
    ...rows.map((r) => r.map(esc).join(',')),
  ].join('\n');
  const file = `guild-ledger-${person.id.replace(/^p-/, '')}-${ctx.today}.csv`;
  download(file, body);
  const st = useStore.getState();
  st.logExport(file, rows.length);
  st.toast({ text: `Exported ${file}, ${rows.length} entries`, kind: 'success' });
}

export function ExportLedgerButton({ ctx, personId }: { ctx: GuildContext; personId: string }) {
  return (
    <Button onClick={() => exportLedger(ctx, personId)}>
      <Download size={14} /> Export ledger as CSV
    </Button>
  );
}

// ── Home ───────────────────────────────────────────────────────────────

/** Rows that are work waiting, and no warning. */
const CALM = new Set(['ready for a witnessed check', 'checks open in the assessor queue']);

/**
 * The workforce at a glance, for Home's right rail (OF-BLD-013 §2): what
 * lapses in the next 30 days, who is ready for a witnessed check, and the
 * deviations runs wrote this week. Each line opens the view that acts on it.
 */
export function WorkforceCard() {
  const ctx = useGuild();
  const { all, loaded } = useChecks();
  if (ctx.guild.people.length === 0) {
    return (
      <Card className="p-3 text-body">
        <span className="text-ink-soft">Nobody is on Guild&rsquo;s ledger yet. </span>
        <a className="text-accent hover:underline" href={href('/guild/matrix')}>
          Start it
        </a>
      </Card>
    );
  }
  let lapsing = 0;
  let lapsed = 0;
  let ready = 0;
  for (const m of ctx.members)
    for (const sk of Object.values(SKILL_BY_ID)) {
      const st = statusOf(ctx.status, m.id, sk.id);
      if (st.lapsed || st.suspended) lapsed += 1;
      else if (st.lapsesAt && st.lapsesAt <= addDays(ctx.today, 30)) lapsing += 1;
      if (readyForCheck(st, sk)) ready += 1;
    }
  const weekAgo = addDays(ctx.today, -7);
  const deviations = ctx.guild.evidence.filter((e) => e.kind === 'deviation' && !e.withdrawnAt && e.at.slice(0, 10) >= weekAgo).length;
  const rows: [string, number, string][] = [
    ['qualifications lapsed or suspended', lapsed, '/guild/matrix'],
    ['qualifications lapse within 30 days', lapsing, '/guild/matrix'],
    ['ready for a witnessed check', ready, '/guild/matrix'],
    ['deviations logged from runs this week', deviations, '/guild/people'],
  ];
  // Checks that name whoever is acting stay out of the count, as they stay out of the queue.
  if (loaded) rows.push(['checks open in the assessor queue', shownTo(all, ctx.actingId).filter(isOpen).length, '/guild/checks']);
  return (
    <Card className="p-3 space-y-1.5">
      {ctx.sample && <div className="text-caption text-signal-warn">Sample team: invented people</div>}
      {rows.map(([label, n, to]) => (
        <a key={label} href={href(to)} className="flex items-baseline gap-2 text-body hover:text-accent">
          <span className={cx('font-num w-8 text-right', n > 0 && !CALM.has(label) ? 'text-signal-warn' : 'text-ink')}>{n}</span>
          <span>{label}</span>
        </a>
      ))}
      <div className="text-caption text-ink-soft pt-1">
        {ctx.members.length} {ctx.members.length === 1 ? 'person' : 'people'} on the ledger, auditors aside
      </div>
    </Card>
  );
}
