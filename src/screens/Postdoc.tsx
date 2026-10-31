// Agent Workspace (OF-DES-001 §8.2). The platform's front door, and the screen
// that must earn trust: answers with visible retrieval, auditable citations,
// and honest uncertainty.
//
// ONE PATH (OF-BLD-016 §3.1). Every answer on this screen comes from the
// service: Postdoc's bounded loop in openferment-core, its steps drawn as they
// arrive. There is no scripted player behind it and no mode to switch. With
// the service down the screen says so and how to start it, the conversations
// stay where they were, and a question typed meanwhile stays in the box.
import { useEffect, useRef, useState } from 'react';
import { MessageSquarePlus, PanelLeft, RefreshCw, Send, Sparkles, Square } from 'lucide-react';
import { useStore, timeId, reviewerName } from '@/store';
import { navigate, useRoute } from '@/router';
import type { LiveConversation, LiveTurn } from '@/data/types';
import { Button, Card, cx, EmptyState, Callout } from '@/components/ui';
import { AnswerPlanView, PostdocDownNotice } from '@/components/AnswerPlanView';
import { askPostdocStream, fetchConversation, postdocHealth, PostdocDown, type PostdocHealth } from '@/lib/postdoc';
import { PlanTrace } from '@/components/PlanTrace';

/**
 * A conversation of questions, each answered by Postdoc's bounded loop
 * (OF-BLD-014 §5.4), its steps drawn as the service completes them: what was
 * searched, what came back, how long it took.
 *
 * A turn is a question and the AnswerPlan the service returned (LiveTurn), in
 * its own list (`liveConversations`), kept in the open project's rows
 * (lib/projectState.ts): a citation followed and returned from, or a reload,
 * finds the conversation where it was. Each question names its conversation
 * and its turn, and the service keeps it as that turn (postdoc/conversations.py):
 * a follow-up's history is what the service keeps of the conversation, and a
 * turn the service is still answering after a reload is followed there until
 * it ends (`fetchConversation`).
 */

/** How often a turn the service is answering for another page, or from before a reload, is looked at. */
const FOLLOW_MS = 2000;

/** The streams in flight, by turn id. Module-level, so Stop still reaches a
 * question asked before the page last mounted. */
const inflight = new Map<string, AbortController>();

const TURN_NOTE: Record<Exclude<LiveTurn['status'], 'running' | 'answered' | 'failed'>, string> = {
  stopped: 'Stopped before an answer came back. The turn keeps the steps it took until then.',
  interrupted: 'Cut short before an answer came back: the service stopped while answering it, or the page closed before asking it. Ask it again.',
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
        </div>
      )}
    </div>
  );
}

/** A turn's time, as the conversations list writes it. */
function askedAt(): string {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

/** What `activeId` holds after "New conversation", before its first question. */
const NEW_CONVERSATION = 'new';

export default function Postdoc({ sessionId, initialQuery }: { sessionId?: string; initialQuery?: string }) {
  const liveConversations = useStore((s) => s.liveConversations);
  const sessionsOpen = useStore((s) => s.ui.sessionsOpen);
  const setUI = useStore((s) => s.setUI);
  const route = useRoute();

  const [activeId, setActiveId] = useState<string | null>(sessionId ?? null);
  const [input, setInput] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);
  const handledQuery = useRef<string | null>(null);

  // The live turns are in the store (`liveConversations`), so this component
  // holds only what it is showing and whether the service answers.
  const [health, setHealth] = useState<PostdocHealth | null>(null);
  const [healthChecked, setHealthChecked] = useState(false);
  // An answer streamed since the page loaded: the service is there, whatever
  // the health probe last said.
  const [reached, setReached] = useState(false);

  // Lets the screen tell "not running" from "running without a key" — two
  // different problems with two different fixes.
  const probeHealth = (signal?: AbortSignal) =>
    postdocHealth(signal)
      .then((h) => {
        setHealth(h);
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

  // A link to a conversation opens it.
  useEffect(() => {
    if (sessionId) setActiveId(sessionId);
  }, [sessionId]);

  // With nothing chosen, the latest conversation is resumed; "New
  // conversation" shows an empty one until its first question.
  const conversation =
    liveConversations.find((c) => c.id === activeId) ?? (activeId === null ? (liveConversations[0] ?? null) : null);
  const running = !!conversation?.turns.some((t) => t.status === 'running' && inflight.has(t.id));
  const down = healthChecked && health === null && !reached;

  // A turn running with no stream in this page (asked before a reload, or in
  // another tab) is being answered on the service: follow it there, and take
  // the service's turn once it ends.
  const followed = (conversation?.turns ?? [])
    .filter((t) => t.status === 'running' && !inflight.has(t.id))
    .map((t) => t.id)
    .join(' ');
  useEffect(() => {
    const id = conversation?.id;
    if (!followed || !id) return;
    const ac = new AbortController();
    const timer = setInterval(() => {
      fetchConversation(id, ac.signal)
        .then((held) => {
          for (const t of held.turns)
            if (followed.split(' ').includes(t.id) && t.status !== 'running') useStore.getState().patchLiveTurn(id, t.id, t);
        })
        .catch(() => undefined);
    }, FOLLOW_MS);
    return () => {
      ac.abort();
      clearInterval(timer);
    };
  }, [followed, conversation?.id]);

  // A question handed over in the address (?q=) is asked once, after the
  // health probe has settled, and then leaves the address so a reload or
  // Back does not ask it again.
  useEffect(() => {
    if (!initialQuery) {
      handledQuery.current = null;
      return;
    }
    if (!healthChecked || handledQuery.current === initialQuery) return;
    handledQuery.current = initialQuery;
    void ask(initialQuery, true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialQuery, healthChecked]);

  const steps = conversation?.turns.reduce((n, t) => n + t.steps.length + (t.plan ? 1 : 0), 0) ?? 0;
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [conversation?.turns.length, steps]);

  /**
   * One question to openferment-core, which runs the loop and validates. NO
   * FALLBACK when it fails — a convincing fake standing in for a broken
   * service is the one outcome worth avoiding, because everything looks like
   * it is working and the thing being demonstrated is not running. Every write
   * goes through the store, so the answer lands in its conversation even if
   * this screen was left meanwhile.
   *
   * When nothing answers at all, the question never reached a service: its
   * turn is taken back (and the conversation, when it was made for it), and
   * the question goes back in the box to send once the service is started.
   */
  async function ask(text: string, fresh: boolean) {
    const store = useStore.getState();
    const before = { activeId, path: route.path };
    const current = fresh ? null : conversation;
    const convId = current?.id ?? store.startLiveConversation(text.slice(0, 60));
    const turnId = timeId('lt');
    const by = reviewerName() ?? undefined;
    store.addLiveTurn(convId, {
      id: turnId,
      question: text,
      askedAt: askedAt(),
      steps: [],
      plan: null,
      error: null,
      status: 'running',
      by,
    });
    setActiveId(convId);
    if (route.path !== `/postdoc/${convId}` || route.query.has('q')) navigate(`/postdoc/${convId}`, { replace: true });

    const ac = new AbortController();
    inflight.set(turnId, ac);
    const patch = useStore.getState().patchLiveTurn;
    try {
      const plan = await askPostdocStream(
        text,
        (step) => {
          setReached(true);
          patch(convId, turnId, { step });
        },
        { signal: ac.signal, conversationId: convId, turnId, by },
      );
      setReached(true);
      patch(convId, turnId, { plan, status: 'answered' });
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        patch(convId, turnId, { status: 'stopped' });
      } else if (err instanceof PostdocDown && (await probeHealth()) === null) {
        // Nothing answers: not a failed answer, an unasked question.
        setReached(false);
        useStore.getState().dropLiveTurn(convId, turnId);
        setInput((typed) => (typed.trim() ? typed : text));
        if (!current) {
          setActiveId(before.activeId);
          navigate(before.path === `/postdoc/${convId}` ? '/postdoc' : before.path, { replace: true });
        }
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

  const stop = () => {
    for (const t of conversation?.turns ?? []) inflight.get(t.id)?.abort();
  };

  const submit = () => {
    const text = input.trim();
    if (!text || running) return;
    setInput('');
    void ask(text, false);
  };

  return (
    <div className="flex gap-4 items-start" style={{ height: 'calc(100vh - 132px)' }}>
      {/* Conversations, newest first, kept in this browser. */}
      {sessionsOpen && (
        <aside className="w-[240px] shrink-0 hidden lg:flex flex-col h-full">
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
                No conversation yet: a person asks the first question. Conversations asked here are kept in
                this browser, across reloads.
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
        </aside>
      )}

      {/* Conversation */}
      <div className="flex-1 min-w-0 flex flex-col h-full">
        <div className="flex items-center gap-2 mb-2">
          <button
            className="btn btn-sm hidden lg:flex"
            onClick={() => setUI({ sessionsOpen: !sessionsOpen })}
            aria-label="Toggle conversation list"
          >
            <PanelLeft size={13} />
          </button>
          <h1 className="font-serif text-page-title font-semibold truncate flex-1">{conversation?.title ?? 'Postdoc'}</h1>
        </div>

        <div className="flex-1 overflow-y-auto pr-1 space-y-3">
          <LivePanel conversation={conversation} health={health} onAsk={(q) => void ask(q, false)} />
          <div ref={bottomRef} />
        </div>

        {/* Composer */}
        <div className="pt-3 mt-2 border-t border-line">
          {down && (
            <div className="mb-2" data-testid="postdoc-down">
              <Callout kind="warn" title="Postdoc needs the service">
                <p className="text-ink">
                  Start it with <code className="font-num text-caption bg-surface-1 rounded px-1">pnpm prototype:up</code>{' '}
                  from the repository root, then send the question again. The conversations here stay in this browser,
                  and a question typed meanwhile stays in the box.
                </p>
                <button className="btn btn-sm mt-2" onClick={() => void probeHealth()}>
                  <RefreshCw size={12} /> Check again
                </button>
              </Callout>
            </div>
          )}

          <div className="flex items-end gap-2">
            <div className="flex-1">
              <textarea
                className="input font-sans resize-none"
                rows={2}
                placeholder={
                  conversation && conversation.turns.length > 0
                    ? 'Ask a follow-up — Postdoc reads this conversation first'
                    : 'Ask a question about the corpus'
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
            </div>
            {running ? (
              <Button onClick={stop} style={{ minHeight: 40 }} data-testid="stop-ask">
                <Square size={13} /> Stop
              </Button>
            ) : (
              <Button variant="primary" onClick={submit} disabled={!input.trim()} style={{ minHeight: 40 }}>
                <Send size={14} /> Send
              </Button>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2 mt-2">
            <span className="text-caption text-ink-soft">
              <span className="kbd">Enter</span> send · <span className="kbd">⇧Enter</span> newline
            </span>
            <div className="flex-1" />
            {health?.ok && health.hasKey && (
              <span className="text-caption text-ink-soft">
                The Postdoc service answers on <span className="font-num">{health.model}</span>
                {health.fallbackModel && health.fallbackModel !== health.model && (
                  <>
                    , falling back to <span className="font-num">{health.fallbackModel}</span>
                  </>
                )}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
