// The browser's side of Postdoc (OF-BLD-007 §8).
//
// No key here. The service holds the key, runs Postdoc's loop of tools and
// the model calls, and validates the plan; this asks it a question and gets
// back the plan, or watches the loop's steps arrive (`askPostdocStream`). The
// service keeps each question as a turn of its conversation, and a follow-up
// reads the earlier turns from what the service keeps (`fetchConversation`).
//
// NO SILENT FALLBACK. When the service is unreachable this says so and says how
// to start it. It never quietly replays a scripted flow — a convincing fake
// hiding a broken service is the single worst outcome available here, because
// everything looks like it is working and the thing you are demonstrating is
// not running. The scripted flows still exist; they are fixtures now, not a
// safety net (§9).
//
// Every shape here is the service's own, generated from its models into
// src/api/types.gen.ts (ADR-007): the health it answers, the question as
// asked, the plan with all it rests on, and the conversation the plan is
// kept in. The screens and components that draw a plan read these names.
import type { components } from '@/api/types.gen';
import { apiFetch } from './project';

type S = components['schemas'];

/** `GET /api/health`: the service answering, the model a call goes to and the one it falls back to, and whether the service holds a key. */
export type Health = S['Health'];
/** What `POST /api/ask` and `/api/ask/stream` take: the question, who asks, and the conversation and turn it is kept as. */
export type AskRequest = S['AskRequest'];
/** An earlier turn sent with a follow-up asked outside a conversation the service keeps: the question and the plan's words. */
export type PriorTurn = S['PriorTurn'];
/** The validated answer (models.py `AnswerPlan`): claims whose words hold no number, each with what it rests on. */
export type AnswerPlan = S['AnswerPlan'];
/** The tokens a plan took, the share the prompt cache served, its cost and the models that answered. */
export type AnswerPlanUsage = S['Usage'];
/** One claim, each number it states typed with its origin (`ClaimValue`), and each sentence it quotes from a passage (`PassageRef`). */
export type Claim = S['Claim'];
export type ClaimValue = S['ClaimValue'];
export type PassageRef = S['PassageRef'];
/** A piece of a paper's own text, as a search returns it. */
export type Passage = S['Passage'];
/** A computed value a claim may cite, with its basis; a geneOS ceiling and a fermOS forecast answer one too. */
export type Evidence = S['Evidence'];
/** One row of one module a claim rests on, and the sweep of every module before the loop's first turn. */
export type ModuleRow = S['ModuleRow'];
export type CoverageMap = S['CoverageMap'];
/** A runbook Postdoc drafted, its numbers written by the service, for a person to adopt and lock. */
export type RunbookDraft = S['RunbookDraft'];
/** One step of the loop as the service completed it, and why the loop stopped. */
export type TraceStep = S['TraceStep'];
export type StopReason = AnswerPlan['stopped'];
/** A conversation as the service keeps it, its turns oldest first (postdoc/conversations.py). */
export type LiveConversation = S['LiveConversation'];
export type LiveTurn = S['LiveTurn'];

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

/**
 * Is the service there, and can it actually answer?
 *
 * Separated from asking because "not running" and "running without a key"
 * need different sentences, and a screen that collapses them into
 * "unavailable" sends somebody to restart a process that is running fine.
 */
export async function postdocHealth(signal?: AbortSignal): Promise<Health> {
  let response: Response;
  try {
    response = await fetch('/api/health', { signal });
  } catch {
    throw new PostdocDown('Postdoc service not running.');
  }
  if (!response.ok) {
    throw new PostdocDown(`Postdoc service answered ${response.status}.`);
  }
  return (await response.json()) as Health;
}

/** What a question names besides its words: the conversation and the turn the
 * service keeps it as (a follow-up's history is the conversation's), and who asked. */
export interface AskOptions {
  signal?: AbortSignal;
  /** Earlier turns, for a question asked outside a conversation the service keeps. */
  history?: PriorTurn[];
  conversationId?: string;
  turnId?: string;
  /** Who asks, by the reviewer name the page signs with; null when nobody is named. */
  by?: string | null;
}

async function post(path: string, question: string, opts: AskOptions): Promise<Response> {
  // `by` is sent with every question, empty when nobody is named: the
  // service's own default.
  const body: AskRequest = {
    question,
    history: opts.history ?? [],
    ...(opts.conversationId ? { conversationId: opts.conversationId } : {}),
    ...(opts.turnId ? { turnId: opts.turnId } : {}),
    by: opts.by ?? '',
  };
  let response: Response;
  try {
    response = await apiFetch(path, {
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
 * plan, throws PostdocDown with the service's words. The stream's first
 * event, `turn`, names the conversation and the turn the service keeps the
 * question as: the ids the page sent, or ids the service made.
 */
export async function askPostdocStream(
  question: string,
  onStep: (step: TraceStep) => void,
  opts: AskOptions = {},
): Promise<AnswerPlan> {
  const response = await post('/api/ask/stream', question, opts);
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
      if (e.event === 'step') onStep(e.data as TraceStep);
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
 * A conversation as the service keeps it, its turns in order, each with its
 * steps, its plan and who asked (`GET /api/conversations/{id}`).
 */
export async function fetchConversation(id: string, signal?: AbortSignal): Promise<LiveConversation> {
  const response = await apiFetch(`/api/conversations/${encodeURIComponent(id)}`, { signal });
  if (!response.ok) throw new PostdocDown(`Postdoc answered ${response.status} for conversation ${id}.`);
  return (await response.json()) as LiveConversation;
}
