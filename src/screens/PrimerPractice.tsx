// Primer · Practice (OF-BLD-013 §4.3). Situations drafted from the protocols
// and from runs at this bench; the trainee answers in their own words and a
// tutor questions their reasoning in short turns, then says what it observed.
// Designed at phone width first, because trainees open it on their phones.
//
//   /primer/practice          the scenarios for whoever is learning, by skill
//   /primer/practice/ps-…     one scenario, answered with the tutor
//   /primer/practice/pt-…     one session's transcript, for the trainee and
//                             for assessors reading what a ledger entry rests on
//
// The model's words reach the screen with [v1] marks in them, and every value
// is the evidence pane's, copied by the service from the source it cites
// (practice.py). Nothing here grades: the tutor's close says what it saw.
import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { MessageCircleQuestion, Send, Sparkles } from 'lucide-react';
import type { PracticeScenario, PracticeSession, PracticeStepRef, PracticeValue } from '@/data/types';
import { useStore } from '@/store';
import { SKILLS, SKILL_BY_ID } from '@/data/skills';
import { PROTOCOLS } from '@/data/protocols';
import { PRIMER_TABS } from '@/data/tabs';
import { statusOf } from '@/engine/competence';
import { fmt } from '@/engine/units';
import { ActingAs, useGuild } from '@/components/GuildBits';
import { LevelGlyph, levelLabel } from '@/components/LevelGlyph';
import { OwnerTabs } from '@/components/OwnerTabs';
import { Button, Callout, Card, EmptyState, LinkButton, PageHeader, SectionTitle, cx } from '@/components/ui';
import { PracticeRefused, draftScenario, forDrafting, splitMarkers, takeTurn } from '@/lib/practice';
import { IntakeDown } from '@/lib/intake';
import { href, navigate, useRoute } from '@/router';

export default function PrimerPractice({ id }: { id?: string }) {
  const practice = useStore((s) => s.practice);
  const load = useStore((s) => s.loadPractice);
  const serviceUp = useStore((s) => s.serviceUp);
  const [asked, setAsked] = useState(false);
  useEffect(() => {
    void load().finally(() => setAsked(true));
  }, [load, serviceUp]);

  if (id?.startsWith('ps-') || id?.startsWith('pt-')) {
    const session = id.startsWith('pt-') ? practice?.sessions.find((x) => x.id === id) ?? null : null;
    const scenario = practice?.scenarios.find((x) => x.id === (session ? session.scenarioId : id)) ?? null;
    if (!scenario) {
      return (
        <Frame>
          <Card>
            <EmptyState
              title={!asked ? 'Asking the service' : practice ? 'No such scenario or session' : 'Practice needs the service'}
              body={
                !asked
                  ? 'One moment.'
                  : practice
                    ? `${id} is not in the service's practice store.`
                    : 'Scenarios and sessions are kept by the openFerment service, which is not answering here.'
              }
              action={<LinkButton to="/primer/practice">All practice</LinkButton>}
            />
          </Card>
        </Frame>
      );
    }
    return <Player key={scenario.id + (session?.id ?? '')} scenario={scenario} opened={session} />;
  }
  return <PracticeList asked={asked} />;
}

// ── header ─────────────────────────────────────────────────────────────

function Frame({ title = 'Practice', subtitle, children }: { title?: string; subtitle?: ReactNode; children: ReactNode }) {
  const sample = useStore((s) => s.guildSample !== null);
  return (
    <div className="max-w-[760px]">
      <PageHeader
        eyebrow="Primer"
        title={title}
        subtitle={
          subtitle ??
          'Situations drafted from the protocols and from runs at this bench. Answer in your own words, and a tutor questions your reasoning.'
        }
      />
      <div className="-mt-2 mb-4">
        <ActingAs id="practice-learning-as" label="Learning as" />
      </div>
      {sample && (
        <div className="mb-4">
          <Callout kind="warn" title="Sample team: invented people">
            The service holds the session with nobody named on it, and the sample&rsquo;s learner gets the practice entry in the sample alone.
          </Callout>
        </div>
      )}
      <OwnerTabs tabs={PRIMER_TABS} />
      {children}
    </div>
  );
}

// ── the list ───────────────────────────────────────────────────────────

function PracticeList({ asked }: { asked: boolean }) {
  const ctx = useGuild();
  const practice = useStore((s) => s.practice);
  const depositions = useStore((s) => s.depositions);
  const runbooks = useStore((s) => s.runbooks);
  const merge = useStore((s) => s.mergePractice);
  const route = useRoute();
  const focus = route.query.get('skill');
  const [drafting, setDrafting] = useState<string | null>(null);
  const [problem, setProblem] = useState<{ skillId: string; text: string } | null>(null);

  const learner = ctx.acting && ctx.acting.active && ctx.acting.role !== 'auditor' ? ctx.acting : null;
  // Who the service knows this learner as: nobody, with the sample shown.
  const named = useStore((s) => s.practiceLearner)();
  // Every skill a protocol step needs: a scenario is drafted from those steps.
  const tagged = useMemo(() => {
    const needed = new Set(PROTOCOLS.flatMap((p) => p.versions.flatMap((v) => v.steps.flatMap((st) => st.skills ?? []))));
    return SKILLS.filter((sk) => needed.has(sk.id));
  }, []);
  const skills = useMemo(() => {
    const open = (id: string) => (learner ? statusOf(ctx.status, learner.id, id).effective < 3 : true);
    return [...tagged].sort(
      (a, b) =>
        Number(b.id === focus) - Number(a.id === focus) ||
        Number(open(b.id)) - Number(open(a.id)) ||
        Number(b.criticality === 'critical') - Number(a.criticality === 'critical'),
    );
  }, [tagged, learner, ctx.status, focus]);

  const draft = async (skillId: string) => {
    setDrafting(skillId);
    setProblem(null);
    try {
      const scenario = await draftScenario({ skillId, depositions: depositions.map((d) => forDrafting(d, runbooks)) });
      merge({ scenario });
      navigate(`/primer/practice/${scenario.id}`);
    } catch (e) {
      setProblem({
        skillId,
        text:
          e instanceof PracticeRefused
            ? `The draft was discarded (${e.rule}): ${e.why}. Nothing was kept; draft again.`
            : e instanceof IntakeDown
              ? e.message
              : String(e),
      });
    } finally {
      setDrafting(null);
    }
  };

  if (asked && !practice) {
    return (
      <Frame>
        <Card className="p-4 text-body space-y-2">
          <p className="font-medium">Practice needs the openFerment service</p>
          <p className="text-ink-soft">
            Drafting a scenario and the tutor are model calls the service makes, with the key in{' '}
            <span className="font-num">core/.env</span>. The service is not answering here, so there is nothing to draft and nobody to ask.
            Lessons and My path work without it.
          </p>
        </Card>
      </Frame>
    );
  }

  const sessions = (practice?.sessions ?? [])
    .filter((x) => (x.personId ?? null) === named)
    .sort((a, b) => (a.startedAt < b.startedAt ? 1 : -1));

  return (
    <Frame>
      {!learner && ctx.guild.people.length > 0 && !ctx.sample && (
        <p className="text-body text-ink-soft mb-4">
          Nobody is chosen as learning, so a session goes on nobody&rsquo;s record. Choose who is learning above to have it count.
        </p>
      )}
      {sessions.length > 0 && (
        <div className="mb-6">
          <SectionTitle>
            {named && learner ? `${learner.name}’s sessions` : ctx.sample ? 'Sessions held while the sample is shown' : 'Sessions on nobody’s record'}
          </SectionTitle>
          <Card>
            {sessions.slice(0, 8).map((x) => {
              const sc = practice?.scenarios.find((s) => s.id === x.scenarioId);
              return (
                <a
                  key={x.id}
                  href={href(`/primer/practice/${x.id}`)}
                  className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5 px-4 py-3 border-b border-line last:border-b-0 hover:bg-ink-soft/[0.03]"
                >
                  <span className="font-medium flex-1 min-w-[180px]">{sc?.title ?? x.scenarioId}</span>
                  <span className="text-caption text-ink-soft">{SKILL_BY_ID[x.skillId]?.name}</span>
                  <span className={cx('text-caption', x.closedAt ? 'text-ink-soft' : 'text-accent')}>
                    {x.closedAt ? `closed ${x.closedAt.slice(0, 10)}` : 'open: answer the tutor'}
                  </span>
                </a>
              );
            })}
          </Card>
        </div>
      )}
      <SectionTitle>By skill</SectionTitle>
      <p className="text-caption text-ink-soft -mt-1 mb-2">
        {learner ? 'Skills still open for this learner come first.' : 'Every skill a protocol step needs.'} Drafting is one model call, and its
        scenario is kept for everyone learning that skill.
      </p>
      <div className="space-y-3">
        {skills.map((sk) => {
          const st = learner ? statusOf(ctx.status, learner.id, sk.id) : null;
          const mine = (practice?.scenarios ?? []).filter((x) => x.skillId === sk.id).sort((a, b) => (a.createdAt < b.createdAt ? 1 : -1));
          return (
            <Card key={sk.id} className={cx('p-4', sk.id === focus && 'border-accent')}>
              <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                {st && <LevelGlyph status={st} size={14} />}
                <a className="font-medium hover:text-accent" href={href(`/guild/skills/${sk.id}`)}>
                  {sk.name}
                </a>
                {st && <span className="text-caption text-ink-soft">{levelLabel(st)}</span>}
                {sk.criticality === 'critical' && <span className="chip text-signal-warn border-signal-warn/40">critical</span>}
              </div>
              {mine.length > 0 && (
                <div className="mt-2 flex flex-col gap-1.5">
                  {mine.slice(0, 4).map((x) => (
                    <a
                      key={x.id}
                      href={href(`/primer/practice/${x.id}`)}
                      className="flex items-center gap-2 px-3 py-2 rounded-btn border border-line hover:border-accent/40"
                      style={{ minHeight: 44 }}
                    >
                      <MessageCircleQuestion size={14} className="text-ink-soft shrink-0" aria-hidden />
                      <span className="flex-1 text-body">{x.title}</span>
                      {x.depositionIds.length > 0 && <span className="chip text-caption">from a run</span>}
                    </a>
                  ))}
                </div>
              )}
              {problem?.skillId === sk.id && <p className="text-body text-signal-error mt-2">{problem.text}</p>}
              <div className="mt-2">
                <Button size="sm" onClick={() => draft(sk.id)} disabled={drafting !== null} style={{ minHeight: 40 }}>
                  <Sparkles size={13} aria-hidden /> {drafting === sk.id ? 'Drafting a scenario…' : mine.length ? 'Draft another' : 'Draft a scenario'}
                </Button>
              </div>
            </Card>
          );
        })}
      </div>
    </Frame>
  );
}

// ── the player ─────────────────────────────────────────────────────────

const MOVE: Record<string, string> = {
  why: 'Asks why',
  change: 'Changes one condition',
  next: 'Asks what next',
  close: 'Closes',
};

function Player({ scenario, opened }: { scenario: PracticeScenario; opened: PracticeSession | null }) {
  const ctx = useGuild();
  const practice = useStore((s) => s.practice);
  const merge = useStore((s) => s.mergePractice);
  const learnerForService = useStore((s) => s.practiceLearner)();
  const closed = useStore((s) => s.practiceClosed);
  const learner = ctx.acting && ctx.acting.active && ctx.acting.role !== 'auditor' ? ctx.acting : null;

  // Resume this learner's open session on the scenario, unless a session was opened by its id.
  const resumable = (practice?.sessions ?? [])
    .filter((x) => x.scenarioId === scenario.id && !x.closedAt && (x.personId ?? null) === learnerForService)
    .sort((a, b) => (a.startedAt < b.startedAt ? 1 : -1))[0];
  const [sessionId, setSessionId] = useState<string | null>(opened?.id ?? resumable?.id ?? null);
  const session = (practice?.sessions ?? []).find((x) => x.id === sessionId) ?? null;
  const [answer, setAnswer] = useState('');
  const [sending, setSending] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  const skill = SKILL_BY_ID[scenario.skillId];
  const byId = new Map(scenario.evidence.map((v) => [v.id, v]));
  const someoneElses = !!session && (session.personId ?? null) !== learnerForService;
  const canAnswer = !session?.closedAt && !someoneElses;

  const send = async () => {
    setSending(true);
    setProblem(null);
    try {
      const next = await takeTurn({ scenarioId: scenario.id, sessionId, personId: learnerForService, answer });
      merge({ session: next });
      setSessionId(next.id);
      setAnswer('');
      if (next.closedAt) await closed(next, scenario.title);
    } catch (e) {
      setProblem(
        e instanceof PracticeRefused
          ? e.rule === 'quantity'
            ? 'The tutor’s reply stated a number of its own, so it was discarded. Your answer is still here: send it again.'
            : `The service refused this turn (${e.rule}): ${e.why}. Your answer is still here.`
          : e instanceof IntakeDown
            ? `${e.message} Your answer is still here.`
            : String(e),
      );
    } finally {
      setSending(false);
    }
  };

  const owner = session?.personId ? ctx.personById.get(session.personId)?.name ?? session.personId : null;
  return (
    <Frame
      title={scenario.title}
      subtitle={
        <>
          Practice on{' '}
          <a className="text-accent hover:underline" href={href(`/guild/skills/${scenario.skillId}`)}>
            {skill?.name ?? scenario.skillId}
          </a>
          {session && <> · session {session.id}</>}
          {owner && <> · {owner}</>}
        </>
      }
    >
      <div className="space-y-5">
        <Card className="p-4 space-y-3">
          <div className="text-caption uppercase tracking-wide text-ink-soft">The situation</div>
          <p className="text-reading">
            <Marked text={scenario.situation} byId={byId} />
          </p>
          <div className="text-caption uppercase tracking-wide text-ink-soft pt-1">The question</div>
          <p className="text-reading font-medium">
            <Marked text={scenario.prompt} byId={byId} />
          </p>
        </Card>

        <div>
          <SectionTitle>Evidence</SectionTitle>
          <div className="space-y-2">
            {scenario.evidence.map((v) => (
              <EvidenceItem key={v.id} v={v} />
            ))}
          </div>
        </div>

        {session && session.turns.length > 0 && (
          <div>
            <SectionTitle>With the tutor</SectionTitle>
            <div className="space-y-2">
              {session.turns.map((t, i) => (
                <div
                  key={i}
                  className={cx(
                    'rounded-card px-3 py-2 text-reading max-w-[92%]',
                    t.role === 'trainee' ? 'ml-auto bg-accent-wash border border-accent/30' : 'bg-surface-1 border border-line',
                  )}
                >
                  <div className="text-caption text-ink-soft mb-0.5">
                    {t.role === 'trainee' ? owner ?? 'Trainee' : `Tutor · ${MOVE[t.move ?? ''] ?? t.move}`}
                  </div>
                  {t.role === 'tutor' ? <Marked text={t.text} byId={byId} /> : t.text}
                  {t.steps.length > 0 && <StepChips steps={t.steps} />}
                </div>
              ))}
            </div>
          </div>
        )}

        {session?.closedAt && (
          <div>
            <SectionTitle>What the tutor observed</SectionTitle>
            <Card className="p-4 space-y-2">
              {session.observed.map((o, i) => (
                <div key={i} className="text-reading">
                  <Marked text={o.text} byId={byId} />
                  {o.steps.length > 0 && <StepChips steps={o.steps} />}
                </div>
              ))}
              <p className="text-caption text-ink-soft pt-1">
                {session.evidenceId
                  ? `On ${owner}’s record as practice, which counts toward Learning. An assessor at the bench does the rest.`
                  : session.personId
                    ? `Closed, and the ledger kept nothing for ${owner}; the service's log says why.`
                    : ctx.sample && learner
                      ? `Recorded for ${learner.name} in the sample team alone.`
                      : 'On nobody’s record: nobody was chosen as learning.'}
              </p>
            </Card>
            {scenario.watchFor.length > 0 && (
              <div className="mt-4">
                <SectionTitle>What a sound answer reaches</SectionTitle>
                <Card className="p-4">
                  <ul className="list-disc pl-5 space-y-1 text-body">
                    {scenario.watchFor.map((w) => (
                      <li key={w}>
                        <Marked text={w} byId={byId} />
                      </li>
                    ))}
                  </ul>
                  <p className="text-caption text-ink-soft mt-2">Shown once a session has closed. The tutor reads it from the start.</p>
                </Card>
              </div>
            )}
          </div>
        )}

        {canAnswer ? (
          <Card className="p-4 space-y-2">
            <label htmlFor="practice-answer" className="text-caption uppercase tracking-wide text-ink-soft">
              {session ? 'Your answer to the tutor' : 'Your answer'}
            </label>
            <textarea
              id="practice-answer"
              className="input w-full text-reading"
              style={{ minHeight: 110 }}
              value={answer}
              disabled={sending}
              placeholder="What you would do, and why, in your own words"
              onChange={(e) => setAnswer(e.target.value)}
            />
            {problem && <p className="text-body text-signal-error">{problem}</p>}
            <div className="flex flex-wrap items-center gap-3">
              <Button variant="primary" onClick={send} disabled={sending || answer.trim().length < 2} style={{ minHeight: 44 }}>
                <Send size={14} aria-hidden /> {sending ? 'The tutor is reading your answer…' : 'Send answer'}
              </Button>
              <span className="text-caption text-ink-soft">
                {learnerForService
                  ? `Goes on ${learner?.name}’s record when the session closes.`
                  : ctx.sample && learner
                    ? `Recorded for ${learner.name} in the sample alone.`
                    : 'Goes on nobody’s record.'}
              </span>
            </div>
          </Card>
        ) : (
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => setSessionId(null)} style={{ minHeight: 44 }}>
              Answer it again, in a new session
            </Button>
            <LinkButton to="/primer/practice">All practice</LinkButton>
          </div>
        )}
      </div>
    </Frame>
  );
}

/** Text the model wrote, with each [vN] shown as the evidence item's label. */
function Marked({ text, byId }: { text: string; byId: Map<string, PracticeValue> }) {
  return (
    <>
      {splitMarkers(text).map((part, i) =>
        typeof part === 'string' ? (
          <span key={i}>{part}</span>
        ) : (
          <button
            key={i}
            type="button"
            onClick={() => document.getElementById(`evidence-${part.marker}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })}
            className="chip mx-0.5 align-baseline text-accent border-accent/40"
            title="Show it in the evidence pane"
          >
            {byId.get(part.marker)?.label ?? part.marker}
          </button>
        ),
      )}
    </>
  );
}

function sourceLink(v: PracticeValue): { to: string; label: string } {
  const s = v.source;
  if (s.kind === 'entry' || s.kind === 'observation')
    return { to: `/runbooks/depositions/${s.depositionId}`, label: `${s.depositionId} · step ${s.stepId}` };
  if (s.kind === 'material') return { to: `/runbooks/protocols/${s.protocolId}`, label: `${s.protocolId} · materials` };
  return { to: `/runbooks/protocols/${s.protocolId}`, label: `${s.protocolId} · step ${s.stepId}` };
}

function EvidenceItem({ v }: { v: PracticeValue }) {
  const link = sourceLink(v);
  const quantity = typeof v.value === 'number';
  return (
    <Card className="p-3" id={`evidence-${v.id}`}>
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
        <span className="font-medium">{v.label}</span>
        <a className="chip text-caption" href={href(link.to)} title="Where this comes from">
          {link.label}
        </a>
      </div>
      {quantity ? (
        <div className="mt-1">
          <span className="font-num text-[22px] leading-tight">{fmt(v.value as number)}</span>{' '}
          <span className="text-body text-ink-soft">{v.unit}</span>
          <div className="text-caption text-ink-soft">
            {v.source.kind === 'entry' ? <>Recorded as &ldquo;{v.text}&rdquo;</> : v.text}
            {v.at && <> · {v.at.slice(0, 16).replace('T', ' ')}</>}
          </div>
        </div>
      ) : (
        <p className="text-body mt-1">
          {v.source.kind === 'observation' ? <>&ldquo;{v.text}&rdquo;</> : v.text}
          {v.at && <span className="text-caption text-ink-soft"> · {v.at.slice(0, 16).replace('T', ' ')}</span>}
        </p>
      )}
    </Card>
  );
}

function StepChips({ steps }: { steps: PracticeStepRef[] }) {
  return (
    <span className="flex flex-wrap gap-1 mt-1">
      {steps.map((s) => (
        <a key={s.protocolId + s.stepId} className="chip text-caption" href={href(`/runbooks/protocols/${s.protocolId}`)}>
          {s.protocolId} · {s.stepId}
        </a>
      ))}
    </span>
  );
}
