// Primer · My path (OF-BLD-013 §3.3). One person's way from the screen to the
// bench: the next thing that moves each open skill, what is ready for an
// assessor, and what is due for a refresh. Designed at phone width first,
// because trainees will open it on their phones.
//
// Everything here is read from Guild's ledger through `competenceOf`, and the
// step for each skill comes from `pathOf` in src/engine/path.ts, so the page
// shows levels and next steps and holds nothing of its own. No points,
// scores or streaks: a count appears only where a skill asks for one, as the
// supervised runs it needs before a witnessed check.
import { useMemo, useState, type ReactNode } from 'react';
import type { Lesson } from '@/data/types';
import { useStore } from '@/store';
import { SKILLS, SKILL_BY_ID } from '@/data/skills';
import { PROTOCOLS } from '@/data/protocols';
import { PRIMER_TABS } from '@/data/tabs';
import { isAssessor, mayCosign } from '@/engine/competence';
import { REFRESH_WINDOW, pathOf, type PathItem, type PathSection } from '@/engine/path';
import { ActingAs, useGuild, type GuildContext } from '@/components/GuildBits';
import { LevelGlyph, levelLabel } from '@/components/LevelGlyph';
import { OwnerTabs } from '@/components/OwnerTabs';
import { Button, Callout, Card, EmptyState, LinkButton, PageHeader, SectionTitle, cx } from '@/components/ui';
import { href } from '@/router';

/** Up to three names, then how many more. */
function few(names: string[]): string {
  if (names.length === 0) return 'nobody on the ledger yet';
  if (names.length <= 3) return names.join(', ');
  return `${names.slice(0, 3).join(', ')} and ${names.length - 3} more`;
}

export default function PrimerPath() {
  const ctx = useGuild();
  const modules = useStore((s) => s.modules);
  const runs = useStore((s) => s.runs);
  const loadSample = useStore((s) => s.guildLoadSample);
  const clearSample = useStore((s) => s.guildClearSample);

  const lessonsFor = useMemo(() => {
    const out: Record<string, Lesson[]> = {};
    for (const m of modules) for (const l of m.lessons) for (const sk of l.skills ?? []) (out[sk] ??= []).push(l);
    return out;
  }, [modules]);

  const openRuns = Object.values(runs).filter((r) => !r.finishedAt);
  const learner = ctx.acting && ctx.acting.active ? ctx.acting : null;

  return (
    <div className="max-w-[760px]">
      <PageHeader
        eyebrow="Primer"
        title="My path"
        subtitle="One person’s way from the screen to the bench: the next step on each skill, what an assessor can see now, and what is due for a refresh."
      />
      <div className="-mt-2 mb-4">
        <ActingAs id="path-learning-as" label="Learning as" />
      </div>
      {ctx.sample && (
        <div className="mb-4">
          <Callout kind="warn" title="Sample team: invented people">
            <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <span>Nothing done to the sample is saved or sent to the service.</span>
              <Button size="sm" onClick={clearSample}>
                Hide the sample
              </Button>
            </span>
          </Callout>
        </div>
      )}
      <OwnerTabs tabs={PRIMER_TABS} />

      {ctx.guild.people.length === 0 ? (
        <Card>
          <EmptyState
            title="Nobody is on Guild’s ledger yet"
            body="A path is read from the ledger: the people on the team and what has been recorded about each of them. Start the ledger in Guild, or look at an invented team first."
            action={
              <span className="flex flex-wrap gap-2 justify-center">
                <LinkButton to="/guild/matrix" variant="primary">
                  Start the ledger
                </LinkButton>
                <Button onClick={loadSample}>Show a sample team</Button>
              </span>
            }
          />
        </Card>
      ) : !learner ? (
        <Card className="p-4 text-body">Choose who is learning, and their path appears here.</Card>
      ) : learner.role === 'auditor' ? (
        <Card className="p-4 text-body">
          {learner.name} is an auditor: they read the ledger and hold no skills, so there is no path to show.
        </Card>
      ) : (
        <Path ctx={ctx} personId={learner.id} name={learner.name} lessonsFor={lessonsFor} openRuns={openRuns} />
      )}
    </div>
  );
}

function Path({
  ctx,
  personId,
  name,
  lessonsFor,
  openRuns,
}: {
  ctx: GuildContext;
  personId: string;
  name: string;
  lessonsFor: Record<string, Lesson[]>;
  openRuns: { id: string; protocolId: string; version: string }[];
}) {
  const others = ctx.members.filter((m) => m.id !== personId);
  const assessors = (sk: string) => few(others.filter((m) => isAssessor(ctx.status, m.id, sk)).map((m) => m.name));
  const cosigners = (sk: string) => few(others.filter((m) => mayCosign(ctx.status, m.id, [sk])).map((m) => m.name));
  const passed = (sk: string, lessonId: string) =>
    ctx.guild.evidence.some(
      (e) =>
        e.personId === personId &&
        e.skillId === sk &&
        e.source.kind === 'lesson' &&
        e.source.ref === lessonId &&
        !e.withdrawnAt,
    );
  const needs = (protocolId: string, version: string, sk: string) =>
    PROTOCOLS.find((p) => p.id === protocolId)
      ?.versions.find((v) => v.version === version)
      ?.steps.some((st) => st.skills?.includes(sk)) ?? false;
  /** The run in progress that needs this skill, else the first protocol that does. */
  const bench = (sk: string): { to: string; cta: string } | null => {
    const run = openRuns.find((r) => needs(r.protocolId, r.version, sk));
    if (run) return { to: `/runbooks/protocols/${run.protocolId}/run/${run.id}`, cta: `Open the ${run.protocolId} run in progress` };
    // Otherwise the protocol that asks the most of it.
    const uses = (x: (typeof PROTOCOLS)[number]) =>
      x.versions.find((v) => v.version === x.currentVersion)?.steps.filter((st) => st.skills?.includes(sk)).length ?? 0;
    const p = PROTOCOLS.filter((x) => uses(x) > 0).sort((x, y) => uses(y) - uses(x))[0];
    return p ? { to: `/runbooks/protocols/${p.id}`, cta: `Open ${p.id}` } : null;
  };
  const soon = new Set(SKILLS.filter((sk) => openRuns.some((r) => needs(r.protocolId, r.version, sk.id))).map((sk) => sk.id));
  const items = pathOf({ personId, skills: SKILLS, status: ctx.status, lessonsFor, passed, soon, today: ctx.today });
  const lessonById = new Map(Object.values(lessonsFor).flat().map((l) => [l.id, l]));
  const of = (section: PathSection) => items.filter((i) => i.section === section);

  /** What to do next, in words, and where to go to do it. */
  const say: Say = (i) => {
    const sk = i.skill.id;
    const st = i.status;
    const run = bench(sk) ?? undefined;
    switch (i.step.kind) {
      case 'suspended':
        return {
          text: <>Suspended after the latest witnessed check. Until an assessor checks again, run it with a cosigner beside you. Assessors: {assessors(sk)}.</>,
          ...run,
          ask: personId,
        };
      case 'lapsed':
        return {
          text: (
            <>
              Lapsed on <span className="font-num">{st.lapsesAt}</span>, so it counts as Supervised until someone sees it performed. Run it with
              a cosigner, or ask an assessor for a witnessed check. Qualified to cosign: {cosigners(sk)}.
            </>
          ),
          ...run,
          ask: personId,
        };
      case 'lapsing':
        return {
          text: (
            <>
              Lapses on <span className="font-num">{st.lapsesAt}</span>. A run of it before then, alone or witnessed, keeps it current.
            </>
          ),
          ...run,
        };
      case 'held':
        return { text: null };
      case 'waiting':
        return { text: <>Waits for {i.step.on.map((b) => SKILL_BY_ID[b]?.name ?? b).join(' and ')} to reach Supervised.</> };
      case 'witnessed-check':
        return {
          text: <>Supervised runs done. Ready for a witnessed check: an assessor watches you perform it against the criteria. Assessors: {assessors(sk)}.</>,
          to: `/guild/skills/${sk}`,
          cta: 'What the assessor watches for',
          ask: personId,
        };
      case 'cosigned-runs':
        return {
          text: (
            <>
              Run it with a cosigner beside you: <span className="font-num">{i.step.done}</span> of{' '}
              <span className="font-num">{i.step.needed}</span> supervised runs before a witnessed check. Qualified to cosign: {cosigners(sk)}.
            </>
          ),
          ...run,
        };
      case 'lesson': {
        const lesson = lessonById.get(i.step.lessonId);
        return {
          text: (
            <>
              Take the lesson &ldquo;{lesson?.title ?? i.step.lessonId}&rdquo;
              {i.step.total > 1 && (
                <>
                  {' '}
                  (<span className="font-num">{i.step.passed}</span> of <span className="font-num">{i.step.total}</span> passed)
                </>
              )}
              .{' '}
              {st.level === 0 ? 'Passing it puts you at Learning; the bench does the rest.' : 'Passing it goes on your ledger beside what is there.'}
            </>
          ),
          to: `/primer/${i.step.lessonId}`,
          cta: 'Open the lesson',
        };
      }
      case 'training-signoff':
        return i.step.lessons > 0
          ? {
              text: (
                <>
                  Lessons passed. Ready for a training sign-off: an assessor briefs you at the bench and hears you talk the steps back. Assessors:{' '}
                  {assessors(sk)}.
                </>
              ),
              to: `/guild/skills/${sk}`,
              cta: 'What the assessor watches for',
            }
          : {
              text: <>No lesson counts toward it yet. An assessor briefs you at the bench and signs off your training. Assessors: {assessors(sk)}.</>,
              to: `/guild/skills/${sk}`,
              cta: 'Read the skill',
            };
    }
  };

  const next = of('next');
  const top = next.slice(0, 3);
  const rest = next.slice(3);

  return (
    <div className="space-y-6">
      <div>
        <SectionTitle>Next up</SectionTitle>
        <p className="text-caption text-ink-soft -mt-1 mb-2">
          Skills a run in progress needs come first, then critical skills, then skills with a lesson to take.
        </p>
        {top.length === 0 ? (
          <Card className="p-4 text-body text-ink-soft">Nothing open: every skill is held, ready for the bench, or waiting on another.</Card>
        ) : (
          <Card>
            {top.map((i) => (
              <Row key={i.skill.id} item={i} say={say} />
            ))}
          </Card>
        )}
      </div>

      <div>
        <SectionTitle>Due for refresh</SectionTitle>
        <Rows items={of('refresh')} say={say} none={`Nothing lapses in the next ${REFRESH_WINDOW} days.`} />
      </div>

      <div>
        <SectionTitle>Ready for the bench</SectionTitle>
        <p className="text-caption text-ink-soft -mt-1 mb-2">
          The screen has done what it can for these. The next entry on {name}&rsquo;s ledger is an assessor&rsquo;s, at the bench.
        </p>
        <Rows items={of('bench')} say={say} none="Nothing yet: pass a lesson, or finish the supervised runs a skill asks for." />
      </div>

      <div>
        <SectionTitle>Held</SectionTitle>
        {of('held').length === 0 ? (
          <Card className="p-4 text-body text-ink-soft">No skill is held yet.</Card>
        ) : (
          <Card className="p-3 flex flex-wrap gap-2">
            {of('held').map((i) => (
              <a key={i.skill.id} className="chip inline-flex items-center gap-1.5" href={href(`/guild/skills/${i.skill.id}`)}>
                <LevelGlyph status={i.status} size={11} /> {i.skill.name}
                <span className="text-ink-soft">· {levelLabel(i.status)}</span>
              </a>
            ))}
          </Card>
        )}
      </div>

      {(rest.length > 0 || of('waiting').length > 0) && (
        <div>
          <SectionTitle>Also open</SectionTitle>
          <Card>
            {[...rest, ...of('waiting')].map((i) => (
              <Row key={i.skill.id} item={i} say={say} compact />
            ))}
          </Card>
        </div>
      )}

      <p className="text-caption text-ink-soft">
        Levels are computed from{' '}
        <a className="text-accent hover:underline" href={href(`/guild/people/${personId}`)}>
          {name}&rsquo;s ledger
        </a>{' '}
        and change only when an entry does. A lesson passed puts a skill at Learning. A training sign-off, supervised runs and a witnessed check
        come from people at the bench.
      </p>
    </div>
  );
}

type Say = (i: PathItem) => { text: ReactNode; to?: string; cta?: string; ask?: string };

function Rows({ items, none, say }: { items: PathItem[]; none: string; say: Say }) {
  if (items.length === 0) return <Card className="p-4 text-body text-ink-soft">{none}</Card>;
  return (
    <Card>
      {items.map((i) => (
        <Row key={i.skill.id} item={i} say={say} />
      ))}
    </Card>
  );
}

function Row({ item, say, compact }: { item: PathItem; say: Say; compact?: boolean }) {
  const { skill, status } = item;
  const { text, to, cta, ask } = say(item);
  return (
    <div className={cx('px-4 border-b border-line last:border-b-0', compact ? 'py-2.5' : 'py-3')}>
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <LevelGlyph status={status} size={14} />
        <a className="font-medium hover:text-accent" href={href(`/guild/skills/${skill.id}`)}>
          {skill.name}
        </a>
        <span className="text-caption text-ink-soft">{levelLabel(status)}</span>
        {skill.criticality === 'critical' && <span className="chip text-signal-warn border-signal-warn/40">critical</span>}
        {item.soon && <span className="chip text-accent border-accent/40">a run in progress needs it</span>}
      </div>
      {text && <p className={cx('text-body mt-1', compact && 'text-ink-soft')}>{text}</p>}
      {!compact && ((to && cta) || ask) && (
        <div className="mt-2 flex flex-wrap items-center gap-2">
          {ask && <AskForCheck personId={ask} skillId={skill.id} />}
          {to && cta && (
            <LinkButton to={to} size="sm">
              {cta}
            </LinkButton>
          )}
          {item.step.kind !== 'held' && item.step.kind !== 'waiting' && (
            <LinkButton to={`/primer/practice?skill=${skill.id}`} size="sm">
              Practise it with the tutor
            </LinkButton>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Puts a check in the assessor queue (OF-BLD-013 §5.4). It says the same
 * whether or not one was already there, and never which day: the assessor
 * picks the moment and the person is not told.
 */
function AskForCheck({ personId, skillId }: { personId: string; skillId: string }) {
  const request = useStore((s) => s.checksRequest);
  const [state, setState] = useState<'idle' | 'busy' | 'asked'>('idle');
  const [why, setWhy] = useState<string | null>(null);
  if (state === 'asked')
    return (
      <span role="status" className="text-caption text-ink">
        Asked. It is in the assessors&rsquo; queue; they pick the moment, unannounced.
      </span>
    );
  return (
    <>
      <Button
        size="sm"
        variant="primary"
        disabled={state === 'busy'}
        onClick={async () => {
          setState('busy');
          const r = await request(personId, [skillId]);
          setWhy(r);
          setState(r ? 'idle' : 'asked');
        }}
      >
        Ask for a check
      </Button>
      {why && (
        <span role="alert" className="text-caption text-signal-error basis-full">
          {why}
        </span>
      )}
    </>
  );
}
