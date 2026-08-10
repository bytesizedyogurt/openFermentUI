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
} from 'lucide-react';
import { useStore } from '@/store';
import { navigate, useRoute } from '@/router';
import type { ChatMessage, ChatRetrievalHit, ChatToolCall } from '@/data/types';
import { SUGGESTED_PROMPTS } from '@/data/flows';
import { send, sendFlow } from '@/sim/chat';
import { fieldName } from '@/data/ontology';
import { convert, fmt } from '@/engine/units';
import { ONTOLOGY_BY_ID } from '@/data/ontology';
import { exportText } from '@/lib/csv';
import { Button, Card, cx, EmptyState, Callout } from '@/components/ui';
import { CitationChip } from '@/components/Chip';
import { Markdown } from '@/components/Markdown';
import { ProvDot } from '@/components/Provenance';
import { useSeriesColor } from '@/lib/viz';

const SLASH_HINTS = [
  { cmd: '/extract <paper>', does: 'queue an extraction job' },
  { cmd: '/compare <A> <B>', does: 'compare two papers' },
  { cmd: '/protocol <name>', does: 'look up a protocol' },
  { cmd: '/scope <paper>', does: 'restrict retrieval' },
];

/** A strip chart of the record values an answer cites (§8.2, message type 5). */
function AnswerStrip({ md }: { md: string }) {
  const records = useStore((s) => s.records);
  const color = useSeriesColor();

  const cited = useMemo(() => {
    const ids = [...md.matchAll(/\[\[(ex-\d+)\]\]/g)].map((m) => m[1]);
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
                v: def.canonicalUnit === '' ? r.value : convert(r.value, r.unit, def.canonicalUnit),
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
              onClick={() => navigate(`/library/papers/${p.r.paperId}?span=${p.r.id}`)}
              title={`${fmt(p.v)} ${cited.def.canonicalUnit} — ${p.r.paperId} (${p.r.status})`}
            >
              <ProvDot p={p.r.gold ? 'gold' : p.r.status === 'verified' ? 'verified' : 'unverified'} size={9} />
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
                onClick={() => navigate(`/library/papers/${h.paperId}`)}
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
            <a href="#/library" className="text-accent hover:underline">
              check Library coverage
            </a>
            .
          </Callout>
        </div>
      )}
    </div>
  );
}

export default function Ask({ sessionId, initialQuery }: { sessionId?: string; initialQuery?: string }) {
  const sessions = useStore((s) => s.sessions);
  const createSession = useStore((s) => s.createSession);
  const appendMessage = useStore((s) => s.appendMessage);
  const pinEvidence = useStore((s) => s.pinEvidence);
  const chatMode = useStore((s) => s.ui.chatMode);
  const inspectorOpen = useStore((s) => s.ui.inspectorOpen);
  const sessionsOpen = useStore((s) => s.ui.sessionsOpen);
  const setUI = useStore((s) => s.setUI);
  const toast = useStore((s) => s.toast);
  const route = useRoute();

  const [activeId, setActiveId] = useState<string | null>(sessionId ?? null);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [tab, setTab] = useState<'retrieval' | 'trace' | 'pinned'>('retrieval');
  const [feedbackFor, setFeedbackFor] = useState<string | null>(null);
  const [feedbackText, setFeedbackText] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);
  const started = useRef(false);

  const session = sessions.find((s) => s.id === activeId) ?? null;

  // Resolve or create the session, and play an initial query once.
  useEffect(() => {
    if (started.current) return;
    started.current = true;
    const scopeParam = route.query.get('scope');
    if (sessionId && sessions.some((s) => s.id === sessionId)) {
      setActiveId(sessionId);
      if (initialQuery) void run(initialQuery, sessionId);
      return;
    }
    if (initialQuery) {
      const scope = scopeParam
        ? ({ kind: 'paper' as const, id: scopeParam, label: scopeParam })
        : undefined;
      const id = createSession(initialQuery.slice(0, 52), scope);
      setActiveId(id);
      void run(initialQuery, id);
    } else if (sessionId) {
      setActiveId(sessionId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [session?.messages.length]);

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

  async function run(text: string, sid?: string) {
    const id = sid ?? ensureSession(text);
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

  const submit = () => {
    const text = input.trim();
    if (!text || busy) return;
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
      {/* Sessions */}
      {sessionsOpen && (
        <aside className="w-[240px] shrink-0 hidden lg:flex flex-col h-full">
          <Button
            className="w-full justify-center mb-2"
            onClick={() => {
              const id = createSession('New session');
              setActiveId(id);
              navigate(`/ask/${id}`);
            }}
          >
            <MessageSquarePlus size={14} /> New session
          </Button>
          <div className="flex-1 overflow-y-auto space-y-1">
            {sessions.map((s) => (
              <button
                key={s.id}
                onClick={() => {
                  setActiveId(s.id);
                  navigate(`/ask/${s.id}`);
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
            {session?.title ?? 'Ask'}
          </h1>
          {session?.scope && (
            <span className="chip text-signal-info border-signal-info/40">
              scoped to {session.scope.label}
            </span>
          )}
          <button
            className="btn btn-sm"
            onClick={() => setUI({ inspectorOpen: !inspectorOpen })}
            title="Toggle Inspector (⌘I)"
          >
            {inspectorOpen ? <PanelRightClose size={13} /> : <PanelRightOpen size={13} />}
            <span className="hidden xl:inline">Inspector</span>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto pr-1 space-y-3">
          {!session || session.messages.length === 0 ? (
            <div className="pt-6">
              <EmptyState
                title="Ask the corpus a question"
                body="Answers come with their retrieval visible and every number carrying a citation you can follow to its source span. Questions the corpus can't support get an explicit decline rather than a guess."
                icon={<Sparkles size={28} />}
              />
              <div className="flex flex-wrap gap-2 justify-center mt-2">
                {SUGGESTED_PROMPTS.map((p) => (
                  <button key={p} className="chip hover:border-accent hover:bg-accent-wash" onClick={() => void run(p)}>
                    {p}
                  </button>
                ))}
              </div>
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
                          synthetic demonstration corpus
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
                              `# openFerment answer — SYNTHETIC DEMO CORPUS\n\n${m.md}\n`,
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

                      {m.followups.length > 0 && (
                        <div className="flex flex-wrap gap-2 mt-3">
                          {m.followups.map((f) => {
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
          {chatMode === 'live' && (
            <div className="mb-2">
              <Callout kind="warn" title="Live mode is not wired in this build">
                Live mode would call a model API and retrieve over the seeded corpus client-side. It
                is not connected here, and it is deliberately not on the demo path. Turns will
                continue to run in Scripted mode.
              </Callout>
            </div>
          )}

          <div className="flex items-end gap-2">
            <div className="flex-1">
              <textarea
                className="input font-sans resize-none"
                rows={2}
                placeholder="Ask about the corpus — or type / for commands"
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
              {input.startsWith('/') && (
                <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1 text-caption text-ink-soft">
                  {SLASH_HINTS.map((h) => (
                    <span key={h.cmd}>
                      <span className="font-num text-ink">{h.cmd}</span> — {h.does}
                    </span>
                  ))}
                </div>
              )}
            </div>
            <Button variant="primary" onClick={submit} disabled={busy || !input.trim()} style={{ minHeight: 40 }}>
              <Send size={14} /> Send
            </Button>
          </div>

          <div className="flex flex-wrap items-center gap-2 mt-2">
            <span className="text-caption text-ink-soft">
              <span className="kbd">Enter</span> send · <span className="kbd">⇧Enter</span> newline
            </span>
            <div className="flex-1" />
            <div className="flex items-center gap-1 text-caption">
              <span className="text-ink-soft">Mode</span>
              {(['scripted', 'live'] as const).map((mode) => (
                <button
                  key={mode}
                  className={cx('chip', chatMode === mode && 'chip-active')}
                  onClick={() => setUI({ chatMode: mode })}
                  aria-pressed={chatMode === mode}
                >
                  {mode === 'scripted' ? 'Scripted' : 'Live (needs network)'}
                </button>
              ))}
            </div>
          </div>

          {session && session.messages.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {SUGGESTED_PROMPTS.slice(0, 3).map((p) => (
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
      {inspectorOpen && (
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
  const protocols = useStore((s) => s.protocols);
  const scenarios = useStore((s) => s.scenarios);
  const toast = useStore((s) => s.toast);

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
                  href: `#/protocols/${p.id}`,
                  hrefLabel: 'Open',
                });
                navigate(`/protocols/${p.id}`);
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
                  href: `#/simulate/${s.id}`,
                  hrefLabel: 'Open',
                });
                navigate(`/simulate/${s.id}`);
              }}
            >
              {s.name}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
