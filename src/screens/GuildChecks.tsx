// Guild · Checks (OF-BLD-013 §5.4). The assessor queue: witnessed checks
// proposed by fixed rules over the ledger (src/engine/checks.ts, mirrored in
// core/openferment_core/checks.py and run each night by nightly.sh) or asked
// for by a person or an assessor; each one scheduled, run at the bench, or
// dismissed with a reason that stays on the record. Desktop-first. The bench
// itself is BenchCheck.tsx, a full-screen takeover.
//
// Who sees what. The queue is for the lead and for assessors. A check never
// shows to the person it names while they are acting: they learn of it when
// it has been run, as a witnessed entry on their ledger, and from then on its
// record is theirs to read like anyone's. Every rule that decides a write is
// the service's; with the sample shown, the store makes the same moves in
// memory and nothing is posted.
import { useEffect, useMemo, useState } from 'react';
import type { Check, CheckBrief } from '@/data/types';
import { useStore } from '@/store';
import { SKILL_BY_ID } from '@/data/skills';
import { PROTOCOLS } from '@/data/protocols';
import { Button, Callout, Card, EmptyState, LinkButton, SectionTitle, cx } from '@/components/ui';
import { EvidenceRow, GuildHeader, nameOf, useChecks, useGuild, type GuildContext } from '@/components/GuildBits';
import { isOpen, mayQueue, shownTo } from '@/engine/checks';
import { LevelGlyph, levelLabel } from '@/components/LevelGlyph';
import { addDays, isAssessor, statusOf } from '@/engine/competence';
import { renderStepText } from '@/engine/scale';
import { href } from '@/router';

const SUBTITLE =
  'Witnessed checks at the bench: proposed by fixed rules over the ledger or asked for, then scheduled and run by an assessor. The person checked is not told in advance.';

export default function GuildChecks({ checkId }: { checkId?: string }) {
  const ctx = useGuild();
  const loadChecks = useStore((s) => s.loadChecks);
  const serviceUp = useStore((s) => s.serviceUp);
  const loadSample = useStore((s) => s.guildLoadSample);
  const { all, loaded } = useChecks();
  const [asked, setAsked] = useState(false);
  useEffect(() => {
    if (ctx.sample) return;
    void loadChecks().finally(() => setAsked(true));
  }, [loadChecks, serviceUp, ctx.sample]);

  if (ctx.guild.people.length === 0) {
    return (
      <>
        <GuildHeader title="Checks" subtitle={SUBTITLE} />
        <Card className="max-w-2xl">
          <EmptyState
            title="Nobody is on the ledger yet"
            body="Checks are proposed from the ledger: the people on it and what has been recorded about each. Start it under People, or look at an invented team first."
            action={
              <span className="flex flex-wrap gap-2 justify-center">
                <LinkButton to="/guild/people" variant="primary">
                  Start the ledger
                </LinkButton>
                <Button onClick={loadSample}>Show a sample team</Button>
              </span>
            }
          />
        </Card>
      </>
    );
  }

  const down = !ctx.sample && asked && !loaded;
  const shown = shownTo(all, ctx.actingId);
  if (checkId) {
    return (
      <>
        <GuildHeader title="Checks" subtitle={SUBTITLE} />
        <OneCheck ctx={ctx} check={shown.find((c) => c.id === checkId) ?? null} id={checkId} asked={asked || ctx.sample} down={down} />
      </>
    );
  }

  return (
    <>
      <GuildHeader title="Checks" subtitle={SUBTITLE} />
      {down && (
        <div className="mb-4 max-w-3xl">
          <Callout kind="warn" title="Checks need the openFerment service">
            The queue is kept by the service, which is not answering here. The Matrix, the ledgers and sign-offs work without it.
          </Callout>
        </div>
      )}
      {!ctx.acting ? (
        <Card className="p-4 text-body max-w-3xl">
          Choose who you are with Acting as. The queue is for the lead and for assessors, and a check never shows to the person it names until it
          has been run.
        </Card>
      ) : ctx.acting.role === 'auditor' ? (
        <Finished ctx={ctx} checks={shown} intro={`${ctx.acting.name} reads the record: every check run or dismissed, who signed it, and why.`} />
      ) : !mayQueue(ctx.acting, ctx.status) ? (
        <Card className="p-4 text-body max-w-3xl space-y-3">
          <p>
            The queue is for the lead and for assessors, and {ctx.acting.name} holds Assessor on no skill yet. To ask for a check on your own
            skills, use My path: an assessor picks the moment.
          </p>
          <LinkButton to="/primer/path" size="sm">
            Open My path
          </LinkButton>
        </Card>
      ) : (
        <Queue ctx={ctx} checks={shown} down={down} />
      )}
    </>
  );
}

// ── the queue ──────────────────────────────────────────────────────────

function Queue({ ctx, checks, down }: { ctx: GuildContext; checks: Check[]; down: boolean }) {
  const propose = useStore((s) => s.checksPropose);
  const [busy, setBusy] = useState(false);
  const [said, setSaid] = useState<{ text: string; bad: boolean } | null>(null);
  const open = checks.filter(isOpen).sort(byUrgency);
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <Button
          disabled={busy || down}
          onClick={async () => {
            setBusy(true);
            const r = await propose();
            setBusy(false);
            setSaid(
              'why' in r
                ? { text: r.why, bad: true }
                : { text: r.made === 0 ? 'Nothing new to propose: every pair the rules point at is in the queue already.' : `${r.made} check${r.made === 1 ? '' : 's'} proposed.`, bad: false },
            );
          }}
        >
          {busy ? 'Ranking…' : 'Propose now'}
        </Button>
        <span className="text-caption text-ink-soft max-w-2xl">
          {ctx.sample
            ? 'The sample’s queue was ranked in this browser when the sample loaded. Proposing again ranks what has changed since.'
            : 'The service ranks every person and skill each night. This runs the same ranking now and adds what is not in the queue already.'}
        </span>
        {said && (
          <span role="status" className={cx('text-caption', said.bad ? 'text-signal-error' : 'text-ink')}>
            {said.text}
          </span>
        )}
      </div>

      <div>
        <SectionTitle>
          Open <span className="font-num text-ink-soft">({open.length})</span>
        </SectionTitle>
        {open.length === 0 ? (
          <Card className="p-4 text-body text-ink-soft max-w-3xl">Nothing in the queue. The ranking finds nothing new until the ledger changes.</Card>
        ) : (
          <div className="space-y-3 max-w-5xl">
            {open.map((c) => (
              <CheckCard key={c.id} ctx={ctx} check={c} />
            ))}
          </div>
        )}
      </div>

      <Finished ctx={ctx} checks={checks} />

      <p className="text-caption text-ink-soft max-w-3xl">
        A check that names {ctx.acting?.name ?? 'the person acting'} does not show here while they are acting; it reaches their ledger once it has
        been run. Reasons are written by fixed rules from the ledger, and every call at the bench is the assessor&rsquo;s.
      </p>
    </div>
  );
}

/** Scheduled first, by day; then the ranking's order. */
function byUrgency(a: Check, b: Check): number {
  if (a.state !== b.state) return a.state === 'scheduled' ? -1 : 1;
  if (a.state === 'scheduled') return (a.scheduledFor ?? '') < (b.scheduledFor ?? '') ? -1 : 1;
  return b.score - a.score || (a.proposedAt < b.proposedAt ? -1 : 1);
}

function stateLine(ctx: GuildContext, c: Check): string {
  if (c.state === 'scheduled') return `Scheduled for ${c.scheduledFor} by ${nameOf(ctx, c.assessorId)}`;
  if (c.state === 'done') return `Run on ${c.closedAt?.slice(0, 10)} by ${nameOf(ctx, c.assessorId)}`;
  if (c.state === 'dismissed') return `Dismissed on ${c.closedAt?.slice(0, 10)} by ${nameOf(ctx, c.dismissedBy)}`;
  return c.proposedBy ? `Asked for by ${nameOf(ctx, c.proposedBy)} on ${c.proposedAt.slice(0, 10)}` : `Proposed by the ranking on ${c.proposedAt.slice(0, 10)}`;
}

function CheckCard({ ctx, check: c }: { ctx: GuildContext; check: Check }) {
  const schedule = useStore((s) => s.checksSchedule);
  const dismiss = useStore((s) => s.checksDismiss);
  const brief = useStore((s) => s.checksBrief);
  const [day, setDay] = useState(c.scheduledFor ?? addDays(ctx.today, 1));
  const [dismissing, setDismissing] = useState(false);
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState<string | null>(null);
  const [why, setWhy] = useState<string | null>(null);

  const me = ctx.acting!;
  const mine = me.id === c.personId;
  const canRun = !mine && c.skillIds.every((k) => isAssessor(ctx.status, me.id, k));
  const canDismiss = !mine && (me.role === 'lead' || c.skillIds.some((k) => isAssessor(ctx.status, me.id, k)));
  const act = async (label: string, f: () => Promise<string | null>) => {
    setBusy(label);
    setWhy(null);
    const r = await f();
    setBusy(null);
    setWhy(r);
    return r === null;
  };

  return (
    <Card className="p-4">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <a className="font-medium hover:text-accent" href={href(`/guild/people/${c.personId}`)}>
          {nameOf(ctx, c.personId)}
        </a>
        <span className="text-caption text-ink-soft">{ctx.personById.get(c.personId)?.title}</span>
        <span className={cx('chip', c.state === 'scheduled' && 'text-accent border-accent/40')}>{stateLine(ctx, c)}</span>
        <a className="text-caption text-ink-soft hover:text-accent ml-auto font-num" href={href(`/guild/checks/${c.id}`)}>
          {c.id}
        </a>
      </div>

      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <div>
          <div className="text-caption uppercase tracking-wide text-ink-soft mb-1">Skills and why</div>
          <SkillReasons ctx={ctx} check={c} />
        </div>
        <div>
          <div className="text-caption uppercase tracking-wide text-ink-soft mb-1">Brief</div>
          {c.brief ? (
            <BriefView brief={c.brief} />
          ) : ctx.sample ? (
            <p className="text-caption text-ink-soft">A brief is drafted by the service from the ledger it keeps, and the sample stays in this browser.</p>
          ) : (
            <div className="space-y-1">
              <p className="text-caption text-ink-soft">
                The service drafts one each night: steps to watch, criteria to probe, and questions to ask, with no number in them.
              </p>
              <Button size="sm" disabled={busy !== null || !canDismiss} onClick={() => act('brief', () => brief(c.id))}>
                {busy === 'brief' ? 'Drafting…' : 'Draft a brief now'}
              </Button>
            </div>
          )}
        </div>
      </div>

      <div className="mt-4 pt-3 border-t border-line flex flex-wrap items-center gap-2">
        {canRun ? (
          <LinkButton to={`/guild/checks/${c.id}/run`} variant="primary" size="sm">
            Run now at the bench
          </LinkButton>
        ) : (
          <Button size="sm" variant="primary" disabled>
            Run now at the bench
          </Button>
        )}
        <label className="sr-only" htmlFor={`schedule-${c.id}`}>
          Day to run it
        </label>
        <input
          id={`schedule-${c.id}`}
          type="date"
          className="input py-1 font-num"
          style={{ width: 160 }}
          value={day}
          min={ctx.today}
          onChange={(e) => setDay(e.target.value)}
          disabled={!canRun}
        />
        <Button size="sm" disabled={!canRun || !day || busy !== null} onClick={() => act('schedule', () => schedule(c.id, day))}>
          {c.state === 'scheduled' ? 'Move to this day' : 'Schedule'}
        </Button>
        {!dismissing ? (
          <Button size="sm" disabled={!canDismiss || busy !== null} onClick={() => setDismissing(true)}>
            Dismiss
          </Button>
        ) : (
          <span className="flex flex-wrap items-center gap-2 basis-full mt-1">
            <label className="sr-only" htmlFor={`dismiss-${c.id}`}>
              Why this check is dismissed
            </label>
            <input
              id={`dismiss-${c.id}`}
              className="input flex-1 min-w-[240px]"
              placeholder="Why it is dismissed: kept for the audit trail"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
            <Button
              size="sm"
              disabled={reason.trim().length < 2 || busy !== null}
              onClick={async () => {
                if (await act('dismiss', () => dismiss(c.id, reason))) setDismissing(false);
              }}
            >
              Dismiss check
            </Button>
            <Button size="sm" onClick={() => setDismissing(false)}>
              Keep it
            </Button>
          </span>
        )}
        {!canRun && (
          <span className="text-caption text-ink-soft">
            {mine
              ? 'Never run, scheduled or dismissed by the person checked.'
              : `Run and scheduled by an assessor on every one of its skills${canDismiss ? '; you may dismiss it.' : '.'}`}
          </span>
        )}
      </div>
      {why && (
        <p role="alert" className="text-caption text-signal-error mt-2">
          {why}
        </p>
      )}
    </Card>
  );
}

function SkillReasons({ ctx, check: c }: { ctx: GuildContext; check: Check }) {
  return (
    <div className="space-y-2">
      {c.skillIds.map((k) => {
        const skill = SKILL_BY_ID[k];
        const st = statusOf(ctx.status, c.personId, k);
        return (
          <div key={k}>
            <div className="flex flex-wrap items-center gap-2">
              <LevelGlyph status={st} size={12} />
              <a className="font-medium hover:text-accent" href={href(`/guild/skills/${k}`)}>
                {skill?.name ?? k}
              </a>
              <span className="text-caption text-ink-soft">{isOpen(c) ? levelLabel(st) : `now ${levelLabel(st)}`}</span>
              {skill?.criticality === 'critical' && <span className="chip text-signal-warn border-signal-warn/40">critical</span>}
            </div>
            <ul className="list-disc pl-5 text-body text-ink-soft">
              {c.reasons
                .filter((r) => r.skillId === k)
                .map((r, i) => (
                  <li key={i}>{r.text}</li>
                ))}
            </ul>
          </div>
        );
      })}
    </div>
  );
}

/** A step a brief names, as its protocol's current version words it. */
export function stepWords(protocolId: string, stepId: string): string {
  const p = PROTOCOLS.find((x) => x.id === protocolId);
  const v = p?.versions.find((x) => x.version === p.currentVersion) ?? p?.versions[0];
  const st = v?.steps.find((x) => x.id === stepId);
  return st && v ? renderStepText(st, v, 1) : '';
}

export function BriefView({ brief, large }: { brief: CheckBrief; large?: boolean }) {
  const text = large ? 'text-reading text-ink' : 'text-body';
  return (
    <div className="space-y-2">
      {brief.steps.length > 0 && (
        <div>
          <div className="text-caption text-ink-soft">Steps to watch</div>
          <ul className="space-y-1">
            {brief.steps.map((s) => (
              <li key={`${s.protocolId}:${s.stepId}`} className={text}>
                <a className="chip mr-1.5" href={href(`/runbooks/protocols/${s.protocolId}`)}>
                  {s.protocolId} · {s.stepId}
                </a>
                {stepWords(s.protocolId, s.stepId)}
              </li>
            ))}
          </ul>
        </div>
      )}
      {brief.criteria.length > 0 && (
        <div>
          <div className="text-caption text-ink-soft">Criteria to probe hardest</div>
          <ul className="list-disc pl-5">
            {brief.criteria.map((cr) => (
              <li key={`${cr.skillId}:${cr.index}`} className={text}>
                {SKILL_BY_ID[cr.skillId]?.mastery[cr.index] ?? `${cr.skillId} #${cr.index}`}{' '}
                <span className="text-caption text-ink-soft">({SKILL_BY_ID[cr.skillId]?.name ?? cr.skillId})</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {brief.questions.length > 0 && (
        <div>
          <div className="text-caption text-ink-soft">Questions to ask while they work</div>
          <ul className="list-disc pl-5">
            {brief.questions.map((q, i) => (
              <li key={i} className={text}>
                {q}
              </li>
            ))}
          </ul>
        </div>
      )}
      <p className="text-caption text-ink-soft">
        Drafted by <span className="font-num">{brief.model}</span> on {brief.draftedAt.slice(0, 10)}. A suggestion of where to look; every call is
        the assessor&rsquo;s.
      </p>
    </div>
  );
}

// ── what was run and dismissed ─────────────────────────────────────────

/** Per skill, whether every criterion was called met. */
function outcomes(c: Check): { skillId: string; met: boolean }[] {
  return c.skillIds.map((k) => ({ skillId: k, met: c.results.filter((r) => r.skillId === k).every((r) => r.meets) }));
}

function Finished({ ctx, checks, intro }: { ctx: GuildContext; checks: Check[]; intro?: string }) {
  const closed = useMemo(() => checks.filter((c) => !isOpen(c)).sort((a, b) => ((a.closedAt ?? '') < (b.closedAt ?? '') ? 1 : -1)), [checks]);
  return (
    <div>
      <SectionTitle>
        Run and dismissed <span className="font-num text-ink-soft">({closed.length})</span>
      </SectionTitle>
      {intro && <p className="text-caption text-ink-soft -mt-1 mb-2">{intro}</p>}
      {closed.length === 0 ? (
        <Card className="p-4 text-body text-ink-soft max-w-3xl">No check has been run or dismissed yet.</Card>
      ) : (
        <Card className="max-w-5xl">
          <div className="overflow-x-auto">
            <table className="w-full text-body border-collapse min-w-[720px]">
              <thead>
                <tr className="border-b border-line text-left text-caption uppercase tracking-wide text-ink-soft">
                  <th className="px-4 py-2 font-normal">Closed</th>
                  <th className="px-3 py-2 font-normal">Person</th>
                  <th className="px-3 py-2 font-normal">Outcome</th>
                  <th className="px-3 py-2 font-normal">By</th>
                  <th className="px-4 py-2 font-normal">Record</th>
                </tr>
              </thead>
              <tbody>
                {closed.map((c) => (
                  <tr key={c.id} className="border-b border-line last:border-b-0 align-top">
                    <td className="px-4 py-2 font-num text-ink-soft">{c.closedAt?.slice(0, 10)}</td>
                    <td className="px-3 py-2">
                      <a className="hover:text-accent" href={href(`/guild/people/${c.personId}`)}>
                        {nameOf(ctx, c.personId)}
                      </a>
                    </td>
                    <td className="px-3 py-2">
                      {c.state === 'done' ? (
                        <span className="flex flex-wrap gap-1.5">
                          {outcomes(c).map((o) => (
                            <span key={o.skillId} className={cx('chip', o.met ? 'text-accent border-accent/40' : 'text-signal-error border-signal-error/40')}>
                              {SKILL_BY_ID[o.skillId]?.name ?? o.skillId}: {o.met ? 'met' : 'not met'}
                            </span>
                          ))}
                        </span>
                      ) : (
                        <span className="text-ink-soft">Dismissed: &ldquo;{c.dismissReason}&rdquo;</span>
                      )}
                    </td>
                    <td className="px-3 py-2">{nameOf(ctx, c.state === 'done' ? c.assessorId : c.dismissedBy)}</td>
                    <td className="px-4 py-2">
                      <a className="text-accent hover:underline font-num" href={href(`/guild/checks/${c.id}`)}>
                        {c.id}
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}

// ── one check ──────────────────────────────────────────────────────────

function OneCheck({ ctx, check: c, id, asked, down }: { ctx: GuildContext; check: Check | null; id: string; asked: boolean; down: boolean }) {
  // An open check is the queue's; one that has been run or dismissed is the record's, and anyone reads it.
  if (!c || (isOpen(c) && !mayQueue(ctx.acting, ctx.status))) {
    return (
      <Card className="max-w-2xl">
        <EmptyState
          title={!asked ? 'Asking the service' : down ? 'Checks need the openFerment service' : 'No check by that id to show'}
          body={
            !asked
              ? 'One moment.'
              : down
                ? 'Checks are kept by the service, which is not answering here.'
                : `${id} is not a check this browser can show to whoever is acting. If the sample team was shown when this link was made, it is gone after a reload.`
          }
          action={<LinkButton to="/guild/checks">All checks</LinkButton>}
        />
      </Card>
    );
  }
  if (isOpen(c)) return <div className="max-w-5xl"><CheckCard ctx={ctx} check={c} /></div>;

  const entries = ctx.guild.evidence.filter((e) => c.evidenceIds.includes(e.id));
  return (
    <div className="space-y-4 max-w-4xl">
      <Card className="p-4 space-y-3">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <span className="font-serif text-section-title font-semibold">Check {c.id}</span>
          <span className="chip">{stateLine(ctx, c)}</span>
        </div>
        <p className="text-body">
          For{' '}
          <a className="text-accent hover:underline" href={href(`/guild/people/${c.personId}`)}>
            {nameOf(ctx, c.personId)}
          </a>
          . {c.proposedBy ? `Asked for by ${nameOf(ctx, c.proposedBy)}` : 'Proposed by the ranking'} on {c.proposedAt.slice(0, 10)}
          {c.state === 'done' && (
            <>
              ; run and signed by <span className="font-medium">{nameOf(ctx, c.assessorId)}</span> on {c.closedAt?.slice(0, 10)}
            </>
          )}
          {c.state === 'dismissed' && (
            <>
              ; dismissed by <span className="font-medium">{nameOf(ctx, c.dismissedBy)}</span>: &ldquo;{c.dismissReason}&rdquo;
            </>
          )}
          .
        </p>
        <div>
          <div className="text-caption uppercase tracking-wide text-ink-soft mb-1">Why it was proposed</div>
          <SkillReasons ctx={ctx} check={c} />
        </div>
      </Card>

      {c.state === 'done' &&
        c.skillIds.map((k) => {
          const skill = SKILL_BY_ID[k];
          const calls = c.results.filter((r) => r.skillId === k).sort((a, b) => a.criterion - b.criterion);
          const entry = entries.find((e) => e.skillId === k);
          return (
            <Card key={k} className="p-4">
              <SectionTitle right={<span className="text-caption">{calls.every((r) => r.meets) ? 'every criterion met' : 'not every criterion met'}</span>}>
                {skill?.name ?? k}
              </SectionTitle>
              <ol className="space-y-1.5">
                {calls.map((r) => (
                  <li key={r.criterion} className={cx('tick', r.meets ? 'tick-measured' : 'tick-rejected')}>
                    <span className="text-body">{skill?.mastery[r.criterion] ?? `criterion ${r.criterion}`}</span>
                    <span className={cx('ml-2 chip', r.meets ? 'text-accent border-accent/40' : 'text-signal-error border-signal-error/40')}>
                      {r.meets ? 'Meets' : 'Needs work'}
                    </span>
                    {r.note && <div className="text-body text-ink-soft">&ldquo;{r.note}&rdquo;</div>}
                  </li>
                ))}
              </ol>
              <div className="mt-3 border-t border-line pt-2">
                <div className="text-caption uppercase tracking-wide text-ink-soft">On the ledger</div>
                {entry ? <EvidenceRow e={entry} ctx={ctx} /> : <p className="text-caption text-ink-soft">The entry is not in the ledger this browser holds.</p>}
              </div>
            </Card>
          );
        })}
    </div>
  );
}
