// Agent Workspace (OF-DES-001 §8.2). The platform's front door, and the screen
// that must earn trust: answers with visible retrieval, auditable citations,
// and honest uncertainty.
import { useEffect, useMemo, useRef, useState } from 'react';
import {
  ChevronDown,
  ChevronRight,
  Copy,
  CornerDownLeft,
  FileDown,
  MessageSquarePlus,
  PanelLeft,
  PanelRightClose,
  PanelRightOpen,
  Pin,
  RefreshCw,
  Send,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
  Wrench,
  X,
  Check,
  AlertCircle,
  Square,
} from 'lucide-react';
import { useStore, provenanceOf, timeId, useProgramFilter, archivedProgramOf } from '@/store';
import { href, navigate, useRoute } from '@/router';
import type { ChatMessage, ChatRetrievalHit, ChatToolCall, LiveConversation, LiveTurn } from '@/data/types';
import { SUGGESTED_PROMPTS, flowOfPrompt, flowShows, sessionShows, subjectsOfFlow, suggestedPrompts } from '@/data/flows';
import { LIVE_PROMPT_LIST, livePrompts, type PromptSubject } from '@/data/livePrompts';
import { PROGRAMS_SETTINGS_PATH } from '@/data/programs';
import { send, sendFlow } from '@/sim/chat';
import { fieldName } from '@/data/ontology';
import { convert, fmt, asNumber } from '@/engine/units';
import { ONTOLOGY_BY_ID } from '@/data/ontology';
import { exportText } from '@/lib/csv';
import { Button, Card, cx, EmptyState, Callout } from '@/components/ui';
import { CitationChip } from '@/components/Chip';
import { Markdown } from '@/components/Markdown';
import { ProvDot } from '@/components/Provenance';
import { useSeriesColor } from '@/lib/viz';
import { AnswerPlanView, PostdocDownNotice } from '@/components/AnswerPlanView';
import { askPostdocStream, postdocHealth, PostdocDown, priorTurns, type PostdocHealth } from '@/lib/postdoc';
import { PlanTrace } from '@/components/PlanTrace';

const SLASH_HINTS = [
  { cmd: '/extract <paper>', does: 'queue an extraction job' },
  { cmd: '/compare <A> <B>', does: 'compare two papers' },
  { cmd: '/protocol <name>', does: 'look up a protocol' },
  { cmd: '/scope <paper>', does: 'restrict retrieval' },
];

// ── programs (OF-BLD-016 §2.2) ─────────────────────────────────────────
//
// Every question this screen offers — the live five, the suggested prompts,
// an answer's follow-ups — and every session, protocol and scenario it lists
// passes through the program selector. What a conversation already holds is
// history and stays as it was asked; what the screen offers next does not.

/** The archived programs some hidden questions are about, by name, in the order they are met. */
function hiddenProgramNames(about: PromptSubject[][]): string[] {
  const names = new Set<string>();
  for (const subjects of about)
    for (const a of subjects) {
      const p = archivedProgramOf(a.kind, a.id);
      if (p) names.add(p.name);
    }
  return [...names];
}

/** "Casein", "Casein and PHA", "Casein, PHA and X". */
function joinNames(names: string[]): string {
  return names.length <= 1 ? (names[0] ?? '') : `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}`;
}

/**
 * The line a list of questions shows when the program filter emptied it:
 * what is hidden, and where the switch is.
 */
function HiddenQuestionsNote({ about, className }: { about: PromptSubject[][]; className?: string }) {
  const names = hiddenProgramNames(about);
  return (
    <p className={cx('text-caption text-ink-soft text-center', className)} data-testid="prompts-hidden">
      {names.length === 0
        ? 'The suggested questions here are about archived programs, which are hidden.'
        : names.length === 1
          ? `The suggested questions here are about ${names[0]}, an archived program, and are hidden.`
          : `The suggested questions here are about ${joinNames(names)}, archived programs, and are hidden.`}{' '}
      <a className="text-accent hover:underline" href={href(PROGRAMS_SETTINGS_PATH)}>
        Settings → Programs
      </a>{' '}
      shows them again.
    </p>
  );
}

/** A strip chart of the record values an answer cites (§8.2, message type 5). */
function AnswerStrip({ md }: { md: string }) {
  const records = useStore((s) => s.records);
  const color = useSeriesColor();

  const cited = useMemo(() => {
    const ids = [...md.matchAll(/\[\[(r-[A-Za-z0-9]+-\d+)\]\]/g)].map((m) => m[1]);
    const recs = ids
      .map((id) => records.find((r) => r.id === id))
      .filter(Boolean) as typeof records;
    // Only plot when four or more comparable numbers share one field.
    const byField = new Map<string, typeof records>();
    for (const r of recs) {
      const arr = byField.get(r.field) ?? [];
      arr.push(r);
      byField.set(r.field, arr);
    }
    for (const [field, arr] of byField) {
      if (arr.length >= 4) {
        const def = ONTOLOGY_BY_ID[field as keyof typeof ONTOLOGY_BY_ID];
        if (!def) continue;
        const points = arr
          .map((r) => {
            try {
              return {
                r,
                v:
                  def.canonicalUnit === ''
                    ? (asNumber(r.value) ?? 0)
                    : convert(asNumber(r.value) ?? 0, r.unit, def.canonicalUnit),
              };
            } catch {
              return null;
            }
          })
          .filter(Boolean) as { r: (typeof records)[number]; v: number }[];
        if (points.length >= 4) return { field, def, points };
      }
    }
    return null;
  }, [md, records]);

  if (!cited) return null;
  const values = cited.points.map((p) => p.v);
  const lo = Math.min(...values);
  const hi = Math.max(...values);
  const span = hi - lo || 1;

  return (
    <div className="mt-3 pt-3 border-t border-line">
      <div className="text-caption text-ink-soft mb-2">
        {cited.def.name} across the cited records ({cited.def.canonicalUnit})
      </div>
      <div className="relative h-11">
        <div className="absolute left-0 right-0 top-5 h-px bg-line" />
        {cited.points.map((p, i) => {
          const pct = ((p.v - lo) / span) * 100;
          const jitter = (i % 3) - 1;
          return (
            <button
              key={p.r.id}
              className="absolute -translate-x-1/2 group"
              style={{ left: `${pct}%`, top: 20 + jitter * 7 }}
              onClick={() => navigate(`/biorepo/paper/${p.r.paperId}?span=${p.r.id}`)}
              title={`${fmt(p.v)} ${cited.def.canonicalUnit} — ${p.r.paperId} (${p.r.status})`}
            >
              <ProvDot p={provenanceOf(p.r)} size={9} />
            </button>
          );
        })}
        <span className="absolute left-0 bottom-0 text-[10px] font-num text-ink-soft">{fmt(lo)}</span>
        <span className="absolute right-0 bottom-0 text-[10px] font-num text-ink-soft">{fmt(hi)}</span>
      </div>
    </div>
  );
}

function PlanMessage({ m }: { m: Extract<ChatMessage, { kind: 'plan' }> }) {
  const [open, setOpen] = useState(!m.collapsed);
  useEffect(() => setOpen(!m.collapsed), [m.collapsed]);
  const complete = m.done >= m.steps.length;

  return (
    <div className="card p-3">
      <button
        className="w-full flex items-center gap-2 text-left"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        {open ? <ChevronDown size={14} className="text-ink-soft" /> : <ChevronRight size={14} className="text-ink-soft" />}
        <span className="text-caption uppercase tracking-wide text-ink-soft">Plan</span>
        <span className="text-body text-ink-soft flex-1 truncate">
          {complete ? `${m.steps.length} steps completed` : m.steps[Math.min(m.done, m.steps.length - 1)]}
        </span>
        {!complete && (
          <span className="inline-block w-3 h-3 rounded-full border-2 border-accent border-t-transparent animate-spin" />
        )}
      </button>
      {open && (
        <ol className="mt-2 space-y-1 pl-6">
          {m.steps.map((s, i) => (
            <li key={i} className="flex items-start gap-2 text-body">
              <span
                className={cx(
                  'shrink-0 w-4 h-4 rounded-full grid place-items-center mt-[2px]',
                  i < m.done ? 'bg-accent text-surface-1' : 'border border-line',
                )}
              >
                {i < m.done && <Check size={10} />}
              </span>
              <span className={cx(i < m.done ? 'text-ink' : 'text-ink-soft')}>{s}</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

function RetrievalCards({
  hits,
  onInspect,
}: {
  hits: ChatRetrievalHit[];
  onInspect: () => void;
}) {
  const papers = useStore((s) => s.papers);
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2">
      {hits.map((h, i) => {
        const paper = papers.find((p) => p.id === h.paperId);
        const section = paper?.sections.find((s) => s.id === h.sectionId);
        return (
          <div key={`${h.paperId}-${h.sectionId}-${i}`} className="card p-2.5">
            <div className="flex items-center justify-between gap-2 mb-1">
              <CitationChip paperId={h.paperId} />
              <span className="text-caption text-ink-soft truncate">{section?.heading ?? h.sectionId}</span>
            </div>
            <div className="flex items-center gap-1.5 mb-1.5">
              <div className="h-1 flex-1 rounded-full bg-ink-soft/15 overflow-hidden">
                <div className="h-full bg-accent rounded-full" style={{ width: `${h.score * 100}%` }} />
              </div>
              <span className="font-num text-[10px] text-ink-soft">{h.score.toFixed(2)}</span>
            </div>
            <p className="text-caption text-ink-soft line-clamp-2 leading-snug">{h.snippet}</p>
            <div className="flex gap-2 mt-1.5">
              <button className="text-caption text-accent hover:underline" onClick={onInspect}>
                Inspect
              </button>
              <button
                className="text-caption text-accent hover:underline"
                onClick={() => navigate(`/biorepo/paper/${h.paperId}`)}
              >
                Open source
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function ToolMessage({ m, onInspect }: { m: Extract<ChatMessage, { kind: 'tool' }>; onInspect: () => void }) {
  const [expanded, setExpanded] = useState(false);
  const call = m.call;
  return (
    <div>
      <div className="card p-2.5">
        <button
          className="w-full flex items-center gap-2 text-left"
          onClick={() => setExpanded((e) => !e)}
          aria-expanded={expanded}
        >
          <Wrench size={13} className="text-signal-info shrink-0" />
          <span className="font-num text-body">{call.name}</span>
          <span className="text-caption text-ink-soft truncate flex-1">
            {Object.entries(call.args)
              .map(([k, v]) => `${k}=${typeof v === 'object' ? JSON.stringify(v) : String(v)}`)
              .join(' · ')}
          </span>
          <span className="font-num text-caption text-ink-soft shrink-0">{call.durationMs} ms</span>
          {expanded ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
        </button>
        {expanded && (
          <pre className="mt-2 text-[11px] font-num bg-surface-0 rounded-input p-2 overflow-x-auto">
            {JSON.stringify({ tool: call.name, args: call.args, durationMs: call.durationMs, hits: call.retrieval?.length ?? 0 }, null, 2)}
          </pre>
        )}
      </div>
      {call.retrieval && call.retrieval.length > 0 && (
        <RetrievalCards hits={call.retrieval} onInspect={onInspect} />
      )}
      {call.retrieval && call.retrieval.length === 0 && (
        <div className="mt-2">
          <Callout kind="info">
            No passages in this corpus match. Broaden the question, or{' '}
            <a href="#/biorepo" className="text-accent hover:underline">
              check Library coverage
            </a>
            .
          </Callout>
        </div>
      )}
    </div>
  );
}

/**
 * Live mode (OF-BLD-007 §8): a conversation of questions, each answered by
 * Postdoc's bounded loop (OF-BLD-014 §5.4), its steps drawn as the service
 * completes them: what was searched, what came back, how long it took.
 *
 * A turn is NOT a ChatMessage. A scripted turn is a transcript the store
 * holds; a live turn is a question and the AnswerPlan the service returned.
 * Conflating them would invent a message shape for something that is not one,
 * the mistake §1 warns about. So live turns keep their own shape (LiveTurn),
 * in their own list (`liveConversations`), in the Durable tier: a citation
 * followed and returned from, or a reload, finds the conversation where it
 * was, and a follow-up sends the earlier turns' words with its question
 * (`priorTurns`). The service keeps no history; the browser sends it.
 */

/** The streams in flight, by turn id. Module-level, so Stop still reaches a
 * question asked before the page last mounted. */
const inflight = new Map<string, AbortController>();

/** Whether somebody picked a mode on this page load; until then, Live is
 * chosen for them when the service can answer. */
let modeChosen = false;

const TURN_NOTE: Record<Exclude<LiveTurn['status'], 'running' | 'answered' | 'failed'>, string> = {
  stopped: 'Stopped before an answer came back. Nothing was kept from this question.',
  interrupted: 'The page reloaded before this answer came back, so it never arrived. Ask it again.',
};

function LiveTurnView({
  turn,
  health,
  latest,
  onAskAgain,
}: {
  turn: LiveTurn;
  health: PostdocHealth | null;
  latest: boolean;
  onAskAgain: (q: string) => void;
}) {
  const running = turn.status === 'running' && inflight.has(turn.id);
  const steps = turn.plan?.trace ?? turn.steps;
  return (
    <article className="space-y-3" data-testid="live-turn">
      {turn.replay && (
        <div className="rounded-input border border-signal-warn/50 px-3 py-2 text-caption text-signal-warn" data-testid="replay-label">
          {/* §10.R: a stand-in recording's date is fixed to keep the fixture
              stable, so it claims none; a real recording names its day. */}
          {turn.replay.standIn
            ? 'Replay of a recorded test run, made with a scripted stand-in in place of the model.'
            : `Replay of a run on ${turn.replay.recordedAt.slice(0, 10)}.`}{' '}
          Nothing is being asked now.
        </div>
      )}
      <div className="flex items-baseline gap-2">
        <span className="text-caption uppercase tracking-wide text-ink-soft shrink-0">Asked</span>
        <p className="text-reading text-ink flex-1">{turn.question}</p>
        <span className="font-num text-caption text-ink-soft shrink-0">{turn.askedAt}</span>
      </div>

      {(running || steps.length > 0) && (
        <Card className="px-4 py-2">
          <div className="text-caption uppercase tracking-wide text-ink-soft mb-1">
            {running ? (
              <>
                Working on{' '}
                <span className="font-num normal-case">
                  {/* After a restart the second model in the chain answers (§5.R). */}
                  {(steps.some((s) => s.kind === 'restart') ? health?.fallbackModel : health?.model) ?? 'the model'}
                </span>
              </>
            ) : (
              'What Postdoc did'
            )}
          </div>
          {latest || running ? (
            <PlanTrace steps={steps} running={running} />
          ) : (
            <details>
              <summary className="cursor-pointer text-caption text-ink-soft py-1">
                {steps.length} {steps.length === 1 ? 'step' : 'steps'}
              </summary>
              <PlanTrace steps={steps} running={false} />
            </details>
          )}
        </Card>
      )}

      {turn.status === 'failed' && turn.error && <PostdocDownNotice message={turn.error.message} remedy={turn.error.remedy} />}
      {(turn.status === 'stopped' || turn.status === 'interrupted') && (
        <Callout kind="info" title={turn.status === 'stopped' ? 'Stopped' : 'No answer arrived'}>
          <p className="text-ink">{TURN_NOTE[turn.status]}</p>
          <button className="btn btn-sm mt-2" onClick={() => onAskAgain(turn.question)}>
            <RefreshCw size={12} /> Ask again
          </button>
        </Callout>
      )}
      {turn.status === 'running' && !running && (
        // A running turn with no stream behind it: the page reloaded mid-answer.
        <Callout kind="info" title="No answer arrived">
          <p className="text-ink">{TURN_NOTE.interrupted}</p>
          <button className="btn btn-sm mt-2" onClick={() => onAskAgain(turn.question)}>
            <RefreshCw size={12} /> Ask again
          </button>
        </Callout>
      )}

      {turn.plan && !running && <AnswerPlanView plan={turn.plan} />}
    </article>
  );
}

function LivePanel({
  conversation,
  health,
  onAsk,
}: {
  conversation: LiveConversation | null;
  health: PostdocHealth | null;
  onAsk: (q: string) => void;
}) {
  const turns = conversation?.turns ?? [];
  const shows = useProgramFilter();
  const offered = livePrompts(shows);
  const hiddenAbout = LIVE_PROMPT_LIST.filter((p) => !offered.includes(p.text)).map((p) => p.about);
  return (
    <div className="space-y-3 pt-1">
      {/* The service is up but cannot answer. A different problem from being
          down, and a different fix — restarting it would not help. */}
      {health && health.ok && !health.hasKey && (
        <Callout kind="warn" title="Postdoc is running without an API key">
          {/* The variable is deliberately NOT named here. check:secrets forbids
              src/ from naming it at all — src/ is the browser bundle, and the
              rule is absence rather than care. Pointing at the template is a
              better instruction anyway: it names the exact file operation. */}
          <p className="text-ink">
            Copy <span className="font-num">core/.env.example</span> to{' '}
            <span className="font-num">core/.env</span>, fill in the key it names, and restart
            the service. That file is gitignored, and the key never reaches the browser — which
            is the whole reason the service exists.
          </p>
        </Callout>
      )}
      {health && !health.ok && health.corpusError && (
        <Callout kind="warn" title="Postdoc is running without a corpus">
          <p className="text-ink">
            Run <span className="font-num">pnpm export:corpus</span> from the repository root and
            restart the service.
          </p>
        </Callout>
      )}

      {turns.map((t, i) => (
        <div key={t.id} className={cx(i > 0 && 'pt-4 border-t border-line')}>
          <LiveTurnView turn={t} health={health} latest={i === turns.length - 1} onAskAgain={onAsk} />
        </div>
      ))}

      {turns.length === 0 && (
        <div className="pt-6">
          <EmptyState
            title="Ask the corpus a question"
            body="Postdoc searches the records and the papers' own text with its tools, then writes claims that carry no numbers of their own: every value is rendered from the record it cites, and every quoted sentence was checked word for word against its paper. A question the corpus cannot support gets an explicit decline. Ask a follow-up and it reads this conversation first."
            icon={<Sparkles size={28} />}
          />
          {offered.length > 0 && (
            <div className="flex flex-wrap gap-2 justify-center mt-2">
              {offered.map((p) => (
                // A whole question, so it wraps rather than running off the column.
                <button
                  key={p}
                  className="chip hover:border-accent hover:bg-accent-wash whitespace-normal text-left max-w-full py-1"
                  onClick={() => onAsk(p)}
                >
                  {p}
                </button>
              ))}
            </div>
          )}
          {offered.length === 0 && hiddenAbout.length > 0 && <HiddenQuestionsNote about={hiddenAbout} className="mt-2" />}
        </div>
      )}
    </div>
  );
}

/** A turn's time, as the sessions list writes it. */
function askedAt(): string {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

/** What `activeId` holds after "New conversation", before its first question. */
const NEW_CONVERSATION = 'new';

export default function Postdoc({ sessionId, initialQuery }: { sessionId?: string; initialQuery?: string }) {
  const sessions = useStore((s) => s.sessions);
  const liveConversations = useStore((s) => s.liveConversations);
  const createSession = useStore((s) => s.createSession);
  const appendMessage = useStore((s) => s.appendMessage);
  const pinEvidence = useStore((s) => s.pinEvidence);
  const chatMode = useStore((s) => s.ui.chatMode);
  const inspectorOpen = useStore((s) => s.ui.inspectorOpen);
  const sessionsOpen = useStore((s) => s.ui.sessionsOpen);
  const setUI = useStore((s) => s.setUI);
  const toast = useStore((s) => s.toast);
  const collections = useStore((s) => s.collections);
  const route = useRoute();
  const shows = useProgramFilter();
  const offeredPrompts = useMemo(() => suggestedPrompts(shows), [shows]);
  const hiddenPromptAbout = useMemo(
    () =>
      SUGGESTED_PROMPTS.filter((p) => !offeredPrompts.includes(p)).map((p) => {
        const flow = flowOfPrompt(p);
        return flow ? subjectsOfFlow(flow) : [];
      }),
    [offeredPrompts],
  );
  // The sidebar lists the sessions whose program shows; a link to any other
  // still opens it (`session` below reads every session).
  const listedSessions = useMemo(
    () => sessions.filter((s) => sessionShows(s, shows, collections)),
    [sessions, shows, collections],
  );

  const [activeId, setActiveId] = useState<string | null>(sessionId ?? null);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [tab, setTab] = useState<'retrieval' | 'trace' | 'pinned'>('retrieval');
  const [feedbackFor, setFeedbackFor] = useState<string | null>(null);
  const [feedbackText, setFeedbackText] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);
  const handledQuery = useRef<string | null>(null);

  // ── live mode (OF-BLD-007) ──────────────────────────────────────────
  // A plan is NOT a message (see LivePanel). The live turns are in the store
  // (`liveConversations`), so this component holds only what it is showing.
  const [health, setHealth] = useState<PostdocHealth | null>(null);
  const [healthChecked, setHealthChecked] = useState(false);

  // Lets the screen tell "not running" from "running without a key" — two
  // different problems with two different fixes — and opens in Live when the
  // service can answer, unless somebody already picked a mode.
  const probeHealth = (signal?: AbortSignal) =>
    postdocHealth(signal)
      .then((h) => {
        setHealth(h);
        if (h.ok && h.hasKey && !modeChosen) setUI({ chatMode: 'live' });
        return h;
      })
      .catch(() => {
        setHealth(null);
        return null;
      })
      .finally(() => setHealthChecked(true));

  useEffect(() => {
    const ac = new AbortController();
    void probeHealth(ac.signal);
    return () => ac.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // A browser that has Live conversations opens in Live even when the service
  // does not answer: the history stays on screen, and the next question says
  // the service is down rather than a scripted transcript answering it.
  const hasLive = liveConversations.length > 0;
  useEffect(() => {
    if (hasLive && !modeChosen) setUI({ chatMode: 'live' });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasLive]);

  // A link to a Live conversation opens it in Live mode.
  useEffect(() => {
    if (!sessionId) return;
    setActiveId(sessionId);
    if (liveConversations.some((c) => c.id === sessionId)) {
      modeChosen = true;
      setUI({ chatMode: 'live' });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  const session = sessions.find((s) => s.id === activeId) ?? null;
  // A link still opens a session the list hides; the pane says why it is not listed (§2.2).
  const sessionArchived = !!session && !listedSessions.includes(session);
  const sessionProgram =
    sessionArchived && session?.scope?.kind === 'paper' ? archivedProgramOf('paper', session.scope.id) : null;
  // With nothing chosen, Live resumes the latest conversation; "New
  // conversation" shows an empty one until its first question.
  const conversation =
    liveConversations.find((c) => c.id === activeId) ?? (activeId === null ? (liveConversations[0] ?? null) : null);
  const liveRunning = !!conversation?.turns.some((t) => t.status === 'running' && inflight.has(t.id));
  const liveReady = !!health?.ok && !!health.hasKey;

  // A question handed over in the address (?q=) is asked once, after the
  // health probe has settled which mode it belongs to, and then leaves the
  // address so a reload or Back does not ask it again.
  useEffect(() => {
    if (!initialQuery) {
      handledQuery.current = null;
      return;
    }
    if (!healthChecked || handledQuery.current === initialQuery) return;
    handledQuery.current = initialQuery;
    const scopeParam = route.query.get('scope');
    if (useStore.getState().ui.chatMode === 'live') {
      void run(initialQuery, { fresh: true });
      return;
    }
    if (sessionId && sessions.some((s) => s.id === sessionId)) {
      void run(initialQuery, { sid: sessionId });
      return;
    }
    const scope = scopeParam ? { kind: 'paper' as const, id: scopeParam, label: scopeParam } : undefined;
    const id = createSession(initialQuery.slice(0, 52), scope);
    setActiveId(id);
    void run(initialQuery, { sid: id });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialQuery, healthChecked]);

  const liveSteps = conversation?.turns.reduce((n, t) => n + t.steps.length + (t.plan ? 1 : 0), 0) ?? 0;
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [session?.messages.length, conversation?.turns.length, liveSteps]);

  // ⌘I toggles the Inspector; ⌘⇧P pins the last answer's sources.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'i') {
        e.preventDefault();
        setUI({ inspectorOpen: !inspectorOpen });
      }
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key.toLowerCase() === 'p') {
        e.preventDefault();
        pinLatest();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  });

  const allHits = useMemo<ChatRetrievalHit[]>(() => {
    if (!session) return [];
    return session.messages.flatMap((m) => (m.kind === 'tool' ? (m.call.retrieval ?? []) : []));
  }, [session]);

  const allCalls = useMemo<ChatToolCall[]>(
    () => (session ? session.messages.filter((m) => m.kind === 'tool').map((m) => (m as Extract<ChatMessage, { kind: 'tool' }>).call) : []),
    [session],
  );

  const ensureSession = (title: string): string => {
    if (activeId && sessions.some((s) => s.id === activeId)) return activeId;
    const id = createSession(title.slice(0, 52));
    setActiveId(id);
    return id;
  };

  /**
   * Live: one question to openferment-core, which runs the loop and
   * validates. NO FALLBACK to the scripted flows when it fails — a convincing
   * fake standing in for a broken service is the one outcome worth avoiding,
   * because everything looks like it is working and the thing being
   * demonstrated is not running. Every write goes through the store, so the
   * answer lands in its conversation even if this screen was left meanwhile.
   */
  async function ask(text: string, fresh: boolean) {
    const store = useStore.getState();
    if (!health) void probeHealth();
    const current = fresh ? null : conversation;
    const history = current ? priorTurns(current.turns) : [];
    const convId = current?.id ?? store.startLiveConversation(text.slice(0, 60));
    const turnId = timeId('lt');
    store.addLiveTurn(convId, {
      id: turnId,
      question: text,
      askedAt: askedAt(),
      steps: [],
      plan: null,
      error: null,
      status: 'running',
      replay: null,
    });
    setActiveId(convId);
    if (route.path !== `/postdoc/${convId}` || route.query.has('q')) navigate(`/postdoc/${convId}`, { replace: true });

    const ac = new AbortController();
    inflight.set(turnId, ac);
    const patch = useStore.getState().patchLiveTurn;
    try {
      const plan = await askPostdocStream(text, (step) => patch(convId, turnId, { step }), {
        signal: ac.signal,
        history,
        onReplay: (replay) => patch(convId, turnId, { replay }),
      });
      patch(convId, turnId, { plan, status: 'answered' });
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        patch(convId, turnId, { status: 'stopped' });
      } else if (err instanceof PostdocDown) {
        patch(convId, turnId, { status: 'failed', error: { message: err.message, remedy: err.remedy } });
      } else {
        patch(convId, turnId, {
          status: 'failed',
          error: {
            message: 'The request to Postdoc failed.',
            remedy: 'Check the service log — it will name what went wrong.',
          },
        });
      }
    } finally {
      inflight.delete(turnId);
    }
  }

  const stopLive = () => {
    for (const t of conversation?.turns ?? []) inflight.get(t.id)?.abort();
  };

  async function run(text: string, opts: { sid?: string; fresh?: boolean } = {}) {
    if (useStore.getState().ui.chatMode === 'live') {
      await ask(text, !!opts.fresh);
      return;
    }

    const id = opts.sid ?? ensureSession(text);
    setBusy(true);
    try {
      const res = await send(text, id);
      if (res.scope !== undefined || res.handled) {
        // /scope returns a new scope; apply it to the session record.
        if (res.scope) {
          const s = useStore.getState().sessions.find((x) => x.id === id);
          if (s) useStore.setState({ sessions: useStore.getState().sessions.map((x) => (x.id === id ? { ...x, scope: res.scope } : x)) });
        }
      }
    } catch (err) {
      appendMessage(id, {
        kind: 'system',
        id: `err-${Date.now()}`,
        text: 'That turn failed to complete. Nothing was lost — try again.',
        retry: true,
      });
    } finally {
      setBusy(false);
    }
  }

  const live = chatMode === 'live';
  const working = live ? liveRunning : busy;

  const submit = () => {
    const text = input.trim();
    if (!text || working) return;
    setInput('');
    void run(text);
  };

  const pinLatest = () => {
    if (!activeId || allHits.length === 0) return;
    pinEvidence(activeId, allHits);
    setTab('pinned');
    toast({ text: `${allHits.length} sources pinned to this session`, kind: 'success' });
  };

  const lastAnswer = session?.messages.filter((m) => m.kind === 'answer').slice(-1)[0] as
    | Extract<ChatMessage, { kind: 'answer' }>
    | undefined;

  return (
    <div className="flex gap-4 items-start" style={{ height: 'calc(100vh - 132px)' }}>
      {/* Sessions: Live conversations in Live mode, the scripted sessions otherwise. */}
      {sessionsOpen && (
        <aside className="w-[240px] shrink-0 hidden lg:flex flex-col h-full">
          {live ? (
            <>
              <Button
                className="w-full justify-center mb-2"
                onClick={() => {
                  setActiveId(NEW_CONVERSATION);
                  navigate(`/postdoc/${NEW_CONVERSATION}`);
                }}
              >
                <MessageSquarePlus size={14} /> New conversation
              </Button>
              <div className="flex-1 overflow-y-auto space-y-1" data-testid="live-conversations">
                {liveConversations.length === 0 && (
                  <p className="text-caption text-ink-soft px-2.5 py-2">
                    Conversations asked in Live mode are kept here, in this browser, across reloads.
                  </p>
                )}
                {liveConversations.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => {
                      setActiveId(c.id);
                      navigate(`/postdoc/${c.id}`);
                    }}
                    className={cx(
                      'w-full text-left px-2.5 py-2 rounded-btn',
                      c.id === conversation?.id ? 'bg-accent-wash' : 'hover:bg-ink-soft/[0.06]',
                    )}
                  >
                    <div className="text-body truncate">{c.title}</div>
                    <div className="text-caption text-ink-soft">
                      <span className="font-num">{c.startedAt}</span> · <span className="font-num">{c.turns.length}</span>{' '}
                      {c.turns.length === 1 ? 'question' : 'questions'}
                    </div>
                  </button>
                ))}
              </div>
            </>
          ) : (
            <>
              <Button
                className="w-full justify-center mb-2"
                onClick={() => {
                  const id = createSession('New session');
                  setActiveId(id);
                  navigate(`/postdoc/${id}`);
                }}
              >
                <MessageSquarePlus size={14} /> New session
              </Button>
              <div className="flex-1 overflow-y-auto space-y-1">
                {listedSessions.length < sessions.length && (
                  <p className="text-caption text-ink-soft px-2.5 py-2" data-testid="sessions-hidden">
                    Sessions about archived programs are hidden.{' '}
                    <a className="text-accent hover:underline" href={href(PROGRAMS_SETTINGS_PATH)}>
                      Settings → Programs
                    </a>{' '}
                    shows them again.
                  </p>
                )}
                {listedSessions.map((s) => (
                  <button
                    key={s.id}
                    onClick={() => {
                      setActiveId(s.id);
                      navigate(`/postdoc/${s.id}`);
                    }}
                    className={cx(
                      'w-full text-left px-2.5 py-2 rounded-btn',
                      s.id === activeId ? 'bg-accent-wash' : 'hover:bg-ink-soft/[0.06]',
                    )}
                  >
                    <div className="text-body truncate">{s.title}</div>
                    <div className="text-caption text-ink-soft flex items-center gap-1.5">
                      <span className="font-num">{s.startedAt}</span>
                      {s.scope && (
                        <span className="chip text-[10px] py-0 border-signal-info/40 text-signal-info">
                          {s.scope.label}
                        </span>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            </>
          )}
        </aside>
      )}

      {/* Conversation */}
      <div className="flex-1 min-w-0 flex flex-col h-full">
        <div className="flex items-center gap-2 mb-2">
          <button
            className="btn btn-sm hidden lg:flex"
            onClick={() => setUI({ sessionsOpen: !sessionsOpen })}
            aria-label="Toggle session list"
          >
            <PanelLeft size={13} />
          </button>
          <h1 className="font-serif text-page-title font-semibold truncate flex-1">
            {(live ? conversation?.title : session?.title) ?? 'Postdoc'}
          </h1>
          {!live && session?.scope && (
            <span className="chip text-signal-info border-signal-info/40">
              scoped to {session.scope.label}
            </span>
          )}
          {/* The Inspector reads the scripted transcript; a live answer shows
              its trace and its quoted sentences inline, so Live has none. */}
          {!live && (
            <button
              className="btn btn-sm hidden xl:inline-flex"
              onClick={() => setUI({ inspectorOpen: !inspectorOpen })}
              title="Toggle Inspector (⌘I)"
            >
              {inspectorOpen ? <PanelRightClose size={13} /> : <PanelRightOpen size={13} />}
              <span>Inspector</span>
            </button>
          )}
        </div>

        <div className="flex-1 overflow-y-auto pr-1 space-y-3">
          {!live && sessionArchived && (
            <div
              role="note"
              data-archived-program={sessionProgram?.id ?? 'archived'}
              className="rounded-card border border-line bg-ink-soft/[0.05] p-3 text-body"
            >
              <div className="font-medium mb-0.5">
                {sessionProgram
                  ? `This session is about ${sessionProgram.name}, an archived program`
                  : 'This session is about an archived program'}
              </div>
              <p className="text-ink-soft">
                It is not listed while archived programs are hidden; a link still opens it.{' '}
                <a className="text-accent underline underline-offset-2" href={href(PROGRAMS_SETTINGS_PATH)}>
                  Settings → Programs
                </a>{' '}
                shows archived programs again.
              </p>
            </div>
          )}
          {live ? (
            <LivePanel conversation={conversation} health={health} onAsk={(q) => void run(q)} />
          ) : !session || session.messages.length === 0 ? (
            <div className="pt-6">
              <EmptyState
                title="Ask the corpus a question"
                body="Answers come with their retrieval visible and every number carrying a citation you can follow to its source span. Questions the corpus can't support get an explicit decline rather than a guess."
                icon={<Sparkles size={28} />}
              />
              <div className="flex flex-wrap gap-2 justify-center mt-2">
                {offeredPrompts.map((p) => (
                  <button key={p} className="chip hover:border-accent hover:bg-accent-wash" onClick={() => void run(p)}>
                    {p}
                  </button>
                ))}
              </div>
              {offeredPrompts.length === 0 && hiddenPromptAbout.length > 0 && (
                <HiddenQuestionsNote about={hiddenPromptAbout} className="mt-2" />
              )}
            </div>
          ) : (
            session.messages.map((m) => {
              if (m.kind === 'user') {
                return (
                  <div key={m.id} className="flex justify-end">
                    <div className="tick tick-verified max-w-[80%] bg-accent-wash rounded-card px-3 py-2">
                      <div className="text-body">{m.text}</div>
                    </div>
                  </div>
                );
              }
              if (m.kind === 'plan') return <PlanMessage key={m.id} m={m} />;
              if (m.kind === 'tool')
                return <ToolMessage key={m.id} m={m} onInspect={() => { setUI({ inspectorOpen: true }); setTab('retrieval'); }} />;
              if (m.kind === 'clarify') {
                return (
                  <Card key={m.id} className="p-3">
                    <div className="flex items-center gap-2 mb-2">
                      <AlertCircle size={14} className="text-signal-info" />
                      <span className="text-body font-medium">{m.question}</span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {m.options.map((o) => (
                        <button
                          key={o.label}
                          className="chip hover:border-accent hover:bg-accent-wash"
                          onClick={() => activeId && void sendFlow(o.flowId, o.label, activeId)}
                        >
                          {o.label}
                        </button>
                      ))}
                    </div>
                  </Card>
                );
              }
              if (m.kind === 'system') {
                return (
                  <div key={m.id} className="flex items-start gap-2 text-body text-ink-soft px-1">
                    <AlertCircle size={14} className="mt-[3px] shrink-0" />
                    <span className="flex-1">{m.text}</span>
                    {m.retry && (
                      <button className="btn btn-sm" onClick={() => void run(session.messages.filter((x) => x.kind === 'user').slice(-1)[0]?.kind === 'user' ? (session.messages.filter((x) => x.kind === 'user').slice(-1)[0] as Extract<ChatMessage, { kind: 'user' }>).text : '')}>
                        <RefreshCw size={12} /> Retry
                      </button>
                    )}
                  </div>
                );
              }
              // answer
              const sourceCount = new Set(
                [...m.md.matchAll(/\[\[(SP-\d+)\]\]/g)].map((x) => x[1]),
              ).size;
              return (
                <Card key={m.id} className="p-4">
                  <Markdown md={m.md} />
                  {m.streaming && (
                    <span className="inline-block w-2 h-4 bg-accent align-text-bottom animate-pulse ml-0.5" />
                  )}
                  {!m.streaming && <AnswerStrip md={m.md} />}

                  {!m.streaming && (
                    <>
                      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-3 pt-2 border-t border-line text-caption text-ink-soft">
                        <span className="font-num">{sourceCount} sources</span>
                        <span>
                          {sourceCount >= 4
                            ? 'Well supported across several papers'
                            : sourceCount > 0
                              ? 'Supported, but from few sources'
                              : 'No corpus support — see the decline above'}
                        </span>
                        <span className="inline-flex items-center gap-1 text-signal-warn">
                          <span
                            className="inline-block w-[3px] h-3 rounded-[1px]"
                            style={{
                              backgroundImage:
                                'repeating-linear-gradient(to bottom, rgb(var(--signal-warn)) 0 3px, transparent 3px 6px)',
                            }}
                          />
                          scripted answer prose
                        </span>
                      </div>

                      <div className="flex flex-wrap items-center gap-1.5 mt-2">
                        <button
                          className="btn btn-sm"
                          onClick={() => {
                            navigator.clipboard?.writeText(m.md);
                            toast({ text: 'Answer copied as markdown', kind: 'info' });
                          }}
                        >
                          <Copy size={12} /> Copy
                        </button>
                        <button
                          className="btn btn-sm"
                          onClick={() =>
                            exportText(
                              `answer-${m.id}.md`,
                              [
                                // A markdown file, so the disclosure is written as markdown. '#'
                                // is a heading marker here, not a comment: the CSV header's
                                // shape would render as a stack of H1s split mid-sentence.
                                '# openFerment answer',
                                '',
                                '> **Corpus OF-COR-001 v1.0.** Cited papers, venues and',
                                '> identifiers are real, though coverage is uneven — 36 of 132',
                                '> entries carry a DOI and 73 carry no persistent identifier at all.',
                                '>',
                                '> Every entry is catalogued, not ingested: metadata plus a curator',
                                '> note, no full text. A cited span quotes that note rather than the',
                                '> paper, and curated values have not been checked against the source',
                                '> PDF. Verify before citing. Figures marked `industry-estimate` are',
                                '> vendor or market claims with no source document behind them.',
                                '>',
                                '> The prose below is authored for this build, not model output.',
                                '> Any simulation economics it quotes are illustrative, not validated.',
                                '',
                                m.md,
                                '',
                              ].join('\n'),
                            )
                          }
                        >
                          <FileDown size={12} /> Export
                        </button>
                        <button className="btn btn-sm" onClick={pinLatest}>
                          <Pin size={12} /> Pin sources
                        </button>
                        <InsertInto md={m.md} />
                        <button
                          className="btn btn-sm"
                          onClick={() => setFeedbackFor(m.id)}
                          aria-label="Helpful"
                        >
                          <ThumbsUp size={12} />
                        </button>
                        <button
                          className="btn btn-sm"
                          onClick={() => setFeedbackFor(m.id)}
                          aria-label="Not helpful"
                        >
                          <ThumbsDown size={12} />
                        </button>
                      </div>

                      {feedbackFor === m.id && (
                        <div className="flex gap-2 mt-2">
                          <input
                            className="input flex-1"
                            placeholder="One line on what was wrong or useful (logged to this session)"
                            value={feedbackText}
                            onChange={(e) => setFeedbackText(e.target.value)}
                            autoFocus
                          />
                          <Button
                            onClick={() => {
                              if (activeId && feedbackText.trim()) {
                                appendMessage(activeId, {
                                  kind: 'system',
                                  id: `fb-${Date.now()}`,
                                  text: `Feedback logged: “${feedbackText.trim()}”`,
                                });
                              }
                              setFeedbackText('');
                              setFeedbackFor(null);
                            }}
                          >
                            Log
                          </Button>
                          <Button onClick={() => setFeedbackFor(null)}>
                            <X size={13} />
                          </Button>
                        </div>
                      )}

                      {m.followups.some((f) => !f.startsWith('flow:') || flowShows(f.slice(5).split('|')[0], shows)) && (
                        <div className="flex flex-wrap gap-2 mt-3">
                          {/* A follow-up is offered only when the flow it opens shows (§2.2). */}
                          {m.followups.filter((f) => !f.startsWith('flow:') || flowShows(f.slice(5).split('|')[0], shows)).map((f) => {
                            const isFlow = f.startsWith('flow:');
                            const [flowId, label] = isFlow ? f.slice(5).split('|') : ['', f];
                            return (
                              <button
                                key={f}
                                className="chip hover:border-accent hover:bg-accent-wash"
                                onClick={() => {
                                  if (!activeId) return;
                                  if (isFlow) void sendFlow(flowId, label ?? flowId, activeId);
                                  else void run(label);
                                }}
                              >
                                {label ?? flowId}
                              </button>
                            );
                          })}
                        </div>
                      )}
                    </>
                  )}
                </Card>
              );
            })
          )}
          <div ref={bottomRef} />
        </div>

        {/* Composer */}
        <div className="pt-3 mt-2 border-t border-line">
          {/* Scripted mode is now a fixture player, not a fallback. When the
              service is up and keyed, say so rather than letting somebody
              demo the transcript by accident (§9). */}
          {chatMode === 'scripted' && health?.ok && health.hasKey && (
            <div className="mb-2 text-caption text-ink-soft">
              Postdoc service is running on <span className="font-num">{health.model}</span>
              {health.fallbackModel && health.fallbackModel !== health.model && (
                <>
                  , falling back to <span className="font-num">{health.fallbackModel}</span>
                </>
              )}
              .
              These are authored transcripts —{' '}
              <button
                className="text-accent hover:underline"
                onClick={() => {
                  modeChosen = true;
                  setUI({ chatMode: 'live' });
                }}
              >
                switch to Live
              </button>{' '}
              for a real answer over the same corpus.
            </div>
          )}

          <div className="flex items-end gap-2">
            <div className="flex-1">
              <textarea
                className="input font-sans resize-none"
                rows={2}
                placeholder={
                  live
                    ? conversation && conversation.turns.length > 0
                      ? 'Ask a follow-up — Postdoc reads this conversation first'
                      : 'Ask a question about the corpus'
                    : 'Ask about the corpus — or type / for commands'
                }
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    submit();
                  }
                }}
                aria-label="Ask a question"
              />
              {!live && input.startsWith('/') && (
                <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1 text-caption text-ink-soft">
                  {SLASH_HINTS.map((h) => (
                    <span key={h.cmd}>
                      <span className="font-num text-ink">{h.cmd}</span> — {h.does}
                    </span>
                  ))}
                </div>
              )}
            </div>
            {live && liveRunning ? (
              <Button onClick={stopLive} style={{ minHeight: 40 }} data-testid="stop-ask">
                <Square size={13} /> Stop
              </Button>
            ) : (
              <Button variant="primary" onClick={submit} disabled={working || !input.trim()} style={{ minHeight: 40 }}>
                <Send size={14} /> Send
              </Button>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2 mt-2">
            <span className="text-caption text-ink-soft">
              <span className="kbd">Enter</span> send · <span className="kbd">⇧Enter</span> newline
            </span>
            <div className="flex-1" />
            <div className="flex items-center gap-1 text-caption">
              <span className="text-ink-soft">Mode</span>
              {/* With the service up and keyed, Live is the only mode offered:
                  the scripted transcripts are fixtures for when it is not, and
                  nobody should demo them by accident (§9). */}
              {(liveReady ? (['live'] as const) : (['scripted', 'live'] as const)).map((mode) => (
                <button
                  key={mode}
                  className={cx('chip', chatMode === mode && 'chip-active')}
                  onClick={() => {
                    modeChosen = true;
                    setUI({ chatMode: mode });
                  }}
                  aria-pressed={chatMode === mode}
                >
                  {mode === 'scripted' ? 'Scripted' : 'Live (Postdoc service)'}
                </button>
              ))}
              {live && liveReady && (
                <span className="text-ink-soft">
                  · <span className="font-num">{health?.model}</span>
                </span>
              )}
            </div>
          </div>

          {!live && session && session.messages.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {offeredPrompts.slice(0, 3).map((p) => (
                <button
                  key={p}
                  className="chip text-caption hover:border-accent hover:bg-accent-wash"
                  onClick={() => void run(p)}
                  disabled={busy}
                >
                  {p}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Inspector */}
      {inspectorOpen && !live && (
        <aside className="w-[340px] shrink-0 hidden xl:flex flex-col h-full card">
          <div className="flex border-b border-line">
            {(['retrieval', 'trace', 'pinned'] as const).map((t) => (
              <button
                key={t}
                className={cx(
                  'flex-1 px-3 py-2 text-body capitalize',
                  tab === t ? 'border-b-2 border-accent text-accent font-medium' : 'text-ink-soft hover:text-ink',
                )}
                onClick={() => setTab(t)}
              >
                {t}
                {t === 'pinned' && session && session.pinned.length > 0 && (
                  <span className="font-num text-caption ml-1">({session.pinned.length})</span>
                )}
              </button>
            ))}
          </div>

          <div className="flex-1 overflow-y-auto p-3">
            {tab === 'retrieval' && (
              allHits.length === 0 ? (
                <p className="text-body text-ink-soft">
                  Retrieved passages appear here as soon as a turn runs. They are the same chunks
                  shown inline — this pane does not re-run retrieval.
                </p>
              ) : (
                <div className="space-y-2">
                  {allHits.map((h, i) => (
                    <div key={i} className="card p-2.5">
                      <div className="flex items-center justify-between gap-2">
                        <CitationChip paperId={h.paperId} />
                        <span className="font-num text-caption text-ink-soft">{h.score.toFixed(2)}</span>
                      </div>
                      <p className="text-caption text-ink-soft mt-1 leading-snug">{h.snippet}</p>
                    </div>
                  ))}
                </div>
              )
            )}

            {tab === 'trace' && (
              allCalls.length === 0 ? (
                <p className="text-body text-ink-soft">No tool calls yet in this session.</p>
              ) : (
                <div className="space-y-2">
                  {allCalls.map((c, i) => (
                    <div key={i} className="card p-2.5">
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <span className="font-num text-body">{c.name}</span>
                        <span className="font-num text-caption text-ink-soft">{c.durationMs} ms</span>
                      </div>
                      <pre className="text-[10px] font-num bg-surface-0 rounded-input p-1.5 overflow-x-auto">
                        {JSON.stringify(c.args, null, 1)}
                      </pre>
                      <div className="text-caption text-ink-soft mt-1">
                        {c.retrieval ? `${c.retrieval.length} passages returned` : 'no retrieval'}
                      </div>
                    </div>
                  ))}
                  <p className="text-caption text-ink-soft pt-1">
                    This trace is the data that produced the answer, not a reconstruction of it.
                  </p>
                </div>
              )
            )}

            {tab === 'pinned' && (
              !session || session.pinned.length === 0 ? (
                <p className="text-body text-ink-soft">
                  Nothing pinned yet. Use <span className="kbd">⌘⇧P</span> or an answer's Pin sources
                  action to keep evidence across the session.
                </p>
              ) : (
                <div className="space-y-2">
                  {session.pinned.map((h, i) => (
                    <div key={i} className="card p-2.5">
                      <CitationChip paperId={h.paperId} />
                      <p className="text-caption text-ink-soft mt-1 leading-snug">{h.snippet}</p>
                    </div>
                  ))}
                </div>
              )
            )}
          </div>
        </aside>
      )}
    </div>
  );
}

/** The cross-module handoff (§8.2): insert an answer's citations into a target. */
function InsertInto({ md }: { md: string }) {
  const [open, setOpen] = useState(false);
  const allProtocols = useStore((s) => s.protocols);
  const allScenarios = useStore((s) => s.scenarios);
  const toast = useStore((s) => s.toast);
  // The targets offered are the ones whose program shows (§2.2).
  const shows = useProgramFilter();
  const protocols = allProtocols.filter((p) => shows('protocol', p.id));
  const scenarios = allScenarios.filter((s) => shows('scenario', s.id));
  const hiddenTargets = protocols.length < allProtocols.length || scenarios.length < allScenarios.length;

  const ids = [...md.matchAll(/\[\[([A-Za-z0-9-]+)\]\]/g)].map((m) => m[1]);
  if (ids.length === 0) return null;

  return (
    <div className="relative">
      <button className="btn btn-sm" onClick={() => setOpen((o) => !o)}>
        <CornerDownLeft size={12} /> Insert into…
      </button>
      {open && (
        <div className="absolute bottom-full mb-1 left-0 z-40 overlay rounded-card p-2 w-[240px]">
          <div className="text-caption uppercase tracking-wide text-ink-soft mb-1">Protocols</div>
          {protocols.slice(0, 4).map((p) => (
            <button
              key={p.id}
              className="w-full text-left px-2 py-1 rounded-input hover:bg-accent-wash text-body truncate"
              onClick={() => {
                setOpen(false);
                toast({
                  text: `${ids.length} references staged for ${p.id}`,
                  kind: 'success',
                  href: `#/runbooks/protocols/${p.id}`,
                  hrefLabel: 'Open',
                });
                navigate(`/runbooks/protocols/${p.id}`);
              }}
            >
              {p.title}
            </button>
          ))}
          <div className="text-caption uppercase tracking-wide text-ink-soft mt-2 mb-1">Scenarios</div>
          {scenarios.map((s) => (
            <button
              key={s.id}
              className="w-full text-left px-2 py-1 rounded-input hover:bg-accent-wash text-body truncate"
              onClick={() => {
                setOpen(false);
                toast({
                  text: `${ids.length} references staged for ${s.name}`,
                  kind: 'success',
                  href: `#/proforma/scenario/${s.id}`,
                  hrefLabel: 'Open',
                });
                navigate(`/proforma/scenario/${s.id}`);
              }}
            >
              {s.name}
            </button>
          ))}
          {hiddenTargets && (
            <p className="text-caption text-ink-soft px-2 pt-2 mt-1 border-t border-line">
              Protocols and scenarios of archived programs are hidden.{' '}
              <a className="text-accent hover:underline" href={href(PROGRAMS_SETTINGS_PATH)}>
                Settings → Programs
              </a>{' '}
              shows them again.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
