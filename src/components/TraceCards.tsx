// The live trace (execution prompt §8.5): every event on the project's stream
// (lib/events.ts) becomes a card at once. A worker job shows its state and how
// long it has run, the way a lab shows an incubator's clock; a Postdoc turn
// shows its question, each tool it called and how many hits came back; an
// artifact kept shows its tool and its provenance. Each card links to the
// record the tables keep. Nothing here computes a number: the counts and the
// marks are the service's.
import { useEffect, useMemo, useState } from 'react';
import { Box, Cpu, MessageSquare } from 'lucide-react';
import type { Provenance } from '@/data/types';
import { watchEvents, type ServiceEvent } from '@/lib/events';
import { href } from '@/router';
import { ProvenanceBadge } from './Provenance';
import { Card, cx } from './ui';

type JobState = 'queued' | 'running' | 'done' | 'failed' | 'refused';

interface JobCard {
  kind: 'job';
  key: string;
  id: string;
  plant: string;
  scenarioId: string | null;
  state: JobState;
  since: number;
  ended: number | null;
  provenance: Provenance | null;
  words: string | null;
}

interface TurnCard {
  kind: 'turn';
  key: string;
  turnId: string;
  conversationId: string;
  question: string;
  state: 'running' | 'answered' | 'declined';
  since: number;
  ended: number | null;
  steps: number;
  calls: { tool: string; ok: boolean | null; hits: number | null }[];
  claims: number | null;
}

interface ArtifactCard {
  kind: 'artifact';
  key: string;
  id: string;
  tool: string;
  provenance: Provenance;
  since: number;
}

export type TraceCard = JobCard | TurnCard | ArtifactCard;

const str = (v: unknown): string => (typeof v === 'string' ? v : '');
const when = (e: ServiceEvent) => Date.parse(e.at) || Date.now();

/** The cards after one event: a new card, or the card the event is about brought up to date. */
export function withEvent(cards: TraceCard[], e: ServiceEvent): TraceCard[] {
  const d = e.data;
  const replace = (key: string, make: (old: TraceCard | undefined) => TraceCard | null): TraceCard[] => {
    const old = cards.find((c) => c.key === key);
    const next = make(old);
    if (!next) return cards;
    return old ? cards.map((c) => (c.key === key ? next : c)) : [next, ...cards];
  };
  if (e.type.startsWith('job.')) {
    const id = str(d.id);
    const state: JobState =
      e.type === 'job.queued' ? 'queued' : e.type === 'job.running' ? 'running' : e.type === 'job.done' ? 'done'
        : str(d.status) === 'refused' ? 'refused' : 'failed';
    return replace(`job:${id}`, (old) => ({
      kind: 'job',
      key: `job:${id}`,
      id,
      plant: str(d.plant),
      scenarioId: str(d.scenarioId) || null,
      state,
      since: old?.since ?? when(e),
      ended: state === 'done' || state === 'failed' || state === 'refused' ? when(e) : null,
      provenance: (str(d.provenance) || null) as Provenance | null,
      words: str(d.words) || null,
    }));
  }
  if (e.type === 'artifact.kept') {
    const id = str(d.id);
    return replace(`artifact:${id}`, () => ({
      kind: 'artifact', key: `artifact:${id}`, id, tool: str(d.tool), provenance: str(d.provenance) as Provenance,
      since: when(e),
    }));
  }
  const turnId = str(d.turnId);
  if (!turnId) return cards;
  return replace(`turn:${turnId}`, (old) => {
    const base: TurnCard =
      old?.kind === 'turn'
        ? old
        : { kind: 'turn', key: `turn:${turnId}`, turnId, conversationId: str(d.conversationId), question: str(d.question),
            state: 'running', since: when(e), ended: null, steps: 0, calls: [], claims: null };
    if (e.type === 'turn.started') return { ...base, question: str(d.question) || base.question };
    if (e.type === 'turn.delta') return { ...base, steps: base.steps + 1 };
    if (e.type === 'tool.call') return { ...base, calls: [...base.calls, { tool: str(d.tool), ok: null, hits: null }] };
    if (e.type === 'tool.result') {
      const calls = [...base.calls];
      const at = calls.map((c) => c.tool === str(d.tool) && c.ok === null).lastIndexOf(true);
      const hits = typeof d.hits === 'number' ? d.hits : null;
      const done = { tool: str(d.tool), ok: d.ok === true, hits };
      if (at >= 0) calls[at] = done;
      else calls.push(done);
      return { ...base, calls };
    }
    const plan = (d.plan ?? {}) as { claims?: unknown[] };
    return { ...base, state: e.type === 'turn.decline' ? 'declined' : 'answered', ended: when(e),
             claims: Array.isArray(plan.claims) ? plan.claims.length : 0 };
  });
}

function useNow(live: boolean): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!live) return;
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [live]);
  return now;
}

function seconds(from: number, to: number): string {
  const s = Math.max(0, Math.round((to - from) / 1000));
  return s < 60 ? `${s} s` : `${Math.floor(s / 60)} min ${s % 60} s`;
}

function Alive({ on }: { on: boolean }) {
  return (
    <span
      aria-hidden
      className={cx('inline-block w-2 h-2 rounded-full shrink-0', on ? 'bg-accent animate-pulse' : 'bg-line')}
    />
  );
}

function OneCard({ card, now }: { card: TraceCard; now: number }) {
  if (card.kind === 'job') {
    const live = card.state === 'queued' || card.state === 'running';
    return (
      <Card className="p-3" data-testid="trace-card" data-kind="job" data-state={card.state}>
        <div className="flex items-center gap-2 text-body">
          <Alive on={live} />
          <Cpu size={14} aria-hidden className="text-ink-soft" />
          <span className="font-semibold truncate">Engine run · {card.plant}</span>
          <span className="ml-auto font-num text-caption text-ink-soft">{seconds(card.since, card.ended ?? now)}</span>
        </div>
        <div className="mt-1 flex flex-wrap items-center gap-2 text-caption text-ink-soft">
          <span>{card.state}</span>
          {card.scenarioId && <span className="font-num">{card.scenarioId}</span>}
          {card.provenance && <ProvenanceBadge p={card.provenance} compact />}
          {card.state === 'done' && (
            <a className="text-accent hover:underline" href={href(`/proforma/runs/${card.id}`)}>
              Run report
            </a>
          )}
        </div>
        {card.words && <p className="mt-1 text-caption text-signal-warn">{card.words}</p>}
      </Card>
    );
  }
  if (card.kind === 'artifact') {
    return (
      <Card className="p-3" data-testid="trace-card" data-kind="artifact">
        <div className="flex items-center gap-2 text-body">
          <Box size={14} aria-hidden className="text-ink-soft" />
          <span className="font-semibold truncate">Kept · {card.tool}</span>
          <ProvenanceBadge p={card.provenance} compact />
          <a className="ml-auto font-num text-caption text-accent hover:underline" href={href(`/biorepo/artifacts/${card.id}`)}>
            {card.id}
          </a>
        </div>
      </Card>
    );
  }
  const live = card.state === 'running';
  return (
    <Card className="p-3" data-testid="trace-card" data-kind="turn" data-state={card.state}>
      <div className="flex items-center gap-2 text-body">
        <Alive on={live} />
        <MessageSquare size={14} aria-hidden className="text-ink-soft" />
        <a className="font-semibold truncate hover:text-accent" href={href(`/postdoc/${card.conversationId}`)}>
          {card.question || 'Postdoc'}
        </a>
        <span className="ml-auto font-num text-caption text-ink-soft">{seconds(card.since, card.ended ?? now)}</span>
      </div>
      {card.calls.length > 0 && (
        <ul className="mt-1.5 space-y-0.5">
          {card.calls.map((c, i) => (
            <li key={`${c.tool}-${i}`} className="flex items-center gap-2 text-caption text-ink-soft">
              <span className={cx('font-num', c.ok === false && 'text-signal-warn')}>{c.tool}</span>
              <span>{c.ok === null ? 'running' : c.ok ? (c.hits !== null ? `${c.hits} back` : 'answered') : 'refused'}</span>
            </li>
          ))}
        </ul>
      )}
      <div className="mt-1 text-caption text-ink-soft">
        {card.state === 'running'
          ? `${card.steps} step${card.steps === 1 ? '' : 's'} so far`
          : card.state === 'declined'
            ? 'Declined, in words'
            : `${card.claims ?? 0} claim${card.claims === 1 ? '' : 's'} kept`}
      </div>
    </Card>
  );
}

/**
 * The project's live cards, newest first. `only` keeps one kind (Home shows
 * the running jobs); `limit` caps how many are drawn.
 */
export function TraceCards({ project, only, limit = 30 }: { project: string; only?: TraceCard['kind']; limit?: number }) {
  const [cards, setCards] = useState<TraceCard[]>([]);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    setCards([]);
    return watchEvents(project, (e) => setCards((cs) => withEvent(cs, e)), setOpen);
  }, [project]);
  const shown = useMemo(() => cards.filter((c) => !only || c.kind === only).slice(0, limit), [cards, only, limit]);
  const live = shown.some((c) => (c.kind === 'job' && (c.state === 'queued' || c.state === 'running')) ||
    (c.kind === 'turn' && c.state === 'running'));
  const now = useNow(live);
  return (
    <section className="space-y-2" data-testid="trace-cards" data-open={open ? 'true' : 'false'}>
      <div className="flex items-center gap-2 text-caption uppercase tracking-wide text-ink-soft">
        <Alive on={open && live} />
        <span>{live ? 'Working' : 'As it happens'}</span>
        {!open && <span className="normal-case tracking-normal">the stream is closed; it reconnects by itself</span>}
      </div>
      {shown.length === 0 ? (
        <p className="text-caption text-ink-soft">
          Runs, tool calls, artifacts and Postdoc's turns show here as they happen.
        </p>
      ) : (
        shown.map((c) => <OneCard key={c.key} card={c} now={now} />)
      )}
    </section>
  );
}
