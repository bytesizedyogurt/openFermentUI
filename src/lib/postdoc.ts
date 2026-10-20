// The browser's side of Postdoc (OF-BLD-007 §8).
//
// No key here. The service holds the key, runs Postdoc's loop of tools and
// the model calls, and validates the plan; this asks it a question and gets
// back the plan, or watches the loop's steps arrive (`askPostdocStream`).
//
// NO SILENT FALLBACK. When the service is unreachable this says so and says how
// to start it. It never quietly replays a scripted flow — a convincing fake
// hiding a broken service is the single worst outcome available here, because
// everything looks like it is working and the thing you are demonstrating is
// not running. The scripted flows still exist; they are fixtures now, not a
// safety net (§9).
import type { AnswerPlan, AnswerPlanUsage, AskRequest, LiveTurn, PriorTurn, TraceStep } from '@/data/types';
import { useStore } from '@/store';

/** Exactly what to type, so the message is actionable rather than sympathetic. */
export const START_COMMAND = 'uv run uvicorn openferment_core.api:app --reload';

export class PostdocDown extends Error {
  constructor(
    message: string,
    /** How to fix it, when there is a fix the reader can carry out. */
    readonly remedy: string = `Start it with \`${START_COMMAND}\` from \`core/\`.`,
  ) {
    super(message);
    this.name = 'PostdocDown';
  }
}

export interface PostdocHealth {
  ok: boolean;
  model: string;
  /** The model a call moves to when `model` declines or is unavailable. */
  fallbackModel?: string;
  /** False means the service is up but has no key — a different fix entirely. */
  hasKey: boolean;
  records: number;
  corpusError: string | null;
}

/**
 * Is the service there, and can it actually answer?
 *
 * Separated from `askPostdoc` because "not running", "running without a key"
 * and "running without a corpus" need three different sentences, and a screen
 * that collapses them into "unavailable" sends somebody to restart a process
 * that is running fine.
 */
export async function postdocHealth(signal?: AbortSignal): Promise<PostdocHealth> {
  let response: Response;
  try {
    response = await fetch('/api/health', { signal });
  } catch {
    throw new PostdocDown('Postdoc service not running.');
  }
  if (!response.ok) {
    throw new PostdocDown(`Postdoc service answered ${response.status}.`);
  }
  return (await response.json()) as PostdocHealth;
}

/** `agent` is the bounded loop of tools (OF-BLD-014 §5.2), the service's
 * default; `single` is one retrieval and one call. */
export type AskMode = 'agent' | 'single';

async function post(
  path: string,
  question: string,
  opts: { maxEvidence?: number; signal?: AbortSignal; mode?: AskMode; history?: PriorTurn[] },
): Promise<Response> {
  const body: AskRequest = {
    question,
    maxEvidence: opts.maxEvidence ?? 30,
    mode: opts.mode ?? 'agent',
    history: opts.history ?? [],
    // Settings → Programs (OF-BLD-016 §2.3): off, the service leaves archived
    // programs out of everything Postdoc reads. Read when the question is
    // sent, so a change of the switch holds from the next question on.
    includeArchived: useStore.getState().showArchived,
  };
  let response: Response;
  try {
    response = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: opts.signal,
    });
  } catch (e) {
    // An aborted request is the user changing their mind, not a failure.
    if (e instanceof DOMException && e.name === 'AbortError') throw e;
    throw new PostdocDown('Postdoc service not running.');
  }

  if (!response.ok) {
    // A DEAD UPSTREAM DOES NOT LOOK LIKE A NETWORK ERROR. The Vite dev proxy
    // answers 500 when it cannot reach the service, so the fetch above
    // resolves and the catch never runs — telling the reader to "check the
    // service log" when there is no service and no log.
    //
    // 422 is the one status our own service produces, for a malformed request
    // body. Everything else is ambiguous between "the service crashed" and
    // "the proxy could not reach it", so ask health which it was. One extra
    // request, and the difference is the difference between "start it" and
    // "look at why it fell over".
    if (response.status !== 422) {
      try {
        await postdocHealth(opts.signal);
      } catch {
        throw new PostdocDown('Postdoc service not running.');
      }
    }
    throw new PostdocDown(
      `Postdoc service answered ${response.status} ${response.statusText}.`,
      'The service is running, so check its log — it will name what went wrong.',
    );
  }
  return response;
}

/**
 * Ask a question, get a plan.
 *
 * A declined plan is a SUCCESS, not an error: "the corpus cannot support this"
 * is an answer, and one of the more useful ones. Only the service being
 * unreachable throws.
 */
export async function askPostdoc(
  question: string,
  opts: { maxEvidence?: number; signal?: AbortSignal; mode?: AskMode; history?: PriorTurn[] } = {},
): Promise<AnswerPlan> {
  const response = await post('/api/ask', question, opts);
  return (await response.json()) as AnswerPlan;
}

/**
 * Sent first by a stream that replays a recorded run rather than running one
 * (OF-BLD-014 §10.3: the service double, `pnpm demo:offline`). The real
 * service never sends it. `standIn` is true when the recording was made with
 * a scripted stand-in in place of the model.
 */
export interface ReplayInfo {
  recordedAt: string;
  standIn: boolean;
}

/** One server-sent event: its name and its parsed data. */
export interface StreamEvent {
  event: string;
  data: unknown;
}

/** Split a buffer of server-sent events into whole events and the rest. */
export function parseEvents(buffer: string): { events: StreamEvent[]; rest: string } {
  const events: StreamEvent[] = [];
  const blocks = buffer.replace(/\r\n/g, '\n').split('\n\n');
  const rest = blocks.pop() ?? '';
  for (const block of blocks) {
    let event = 'message';
    const data: string[] = [];
    for (const line of block.split('\n')) {
      if (line.startsWith('event:')) event = line.slice(6).trim();
      else if (line.startsWith('data:')) data.push(line.slice(5).replace(/^ /, ''));
    }
    if (data.length) events.push({ event, data: JSON.parse(data.join('\n')) });
  }
  return { events, rest };
}

/**
 * Ask through the loop and watch it work (OF-BLD-014 §5.3). `onStep` is
 * called with each step as the service completes it; the promise resolves
 * with the validated plan. An `error` event, or a stream that ends without a
 * plan, throws PostdocDown with the service's words.
 */
export async function askPostdocStream(
  question: string,
  onStep: (step: TraceStep) => void,
  opts: { maxEvidence?: number; signal?: AbortSignal; onReplay?: (r: ReplayInfo) => void; history?: PriorTurn[] } = {},
): Promise<AnswerPlan> {
  const { onReplay, ...rest } = opts;
  const response = await post('/api/ask/stream', question, { ...rest, mode: 'agent' });
  const checkLog = 'The service is running, so check its log — it will name what went wrong.';
  if (!response.body) throw new PostdocDown('Postdoc answered with no stream.', checkLog);
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  for (;;) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    const parsed = parseEvents(done ? `${buffer}\n\n` : buffer);
    buffer = parsed.rest;
    for (const e of parsed.events) {
      if (e.event === 'replay') onReplay?.(e.data as ReplayInfo);
      else if (e.event === 'step') onStep(e.data as TraceStep);
      else if (e.event === 'plan') return e.data as AnswerPlan;
      else if (e.event === 'error') throw new PostdocDown(String((e.data as { message?: string }).message ?? 'Postdoc failed.'), checkLog);
    }
    if (done) throw new PostdocDown('The stream from Postdoc ended before its answer.', checkLog);
  }
}

/** Per-query cost, at the precision the number actually has. */
export function formatCost(usd: number): string {
  if (usd === 0) return '$0';
  if (usd < 0.01) return `$${usd.toFixed(4)}`;
  return `$${usd.toFixed(3)}`;
}

/**
 * The share of the prompt the cache served, as a whole percent, or null when
 * it served none (OF-BLD-014 §3.3). The prompt is the uncached input plus the
 * cache reads and writes, which the API counts apart.
 */
export function cachedShare(u: AnswerPlanUsage): number | null {
  const read = u.cacheReadTokens ?? 0;
  const prompt = u.inputTokens + read + (u.cacheWriteTokens ?? 0);
  if (read <= 0 || prompt <= 0) return null;
  return Math.round((read / prompt) * 100);
}

/**
 * The earlier turns a follow-up sends: each answered turn's question and its
 * plan's words. A turn that failed, or was stopped, carries no answer and is
 * left out.
 */
export function priorTurns(turns: LiveTurn[]): PriorTurn[] {
  return turns
    .filter((t) => t.status === 'answered' && t.plan)
    .map((t) => ({
      question: t.question,
      claims: t.plan!.claims.map((c) => c.text),
      gaps: t.plan!.gaps,
      declined: t.plan!.declined,
    }));
}
