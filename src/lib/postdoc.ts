// The browser's side of Postdoc (OF-BLD-007 §8).
//
// One function, one endpoint, no key. The service holds the key and does the
// retrieval and the model call; this asks it a question and gets back a plan.
//
// NO SILENT FALLBACK. When the service is unreachable this says so and says how
// to start it. It never quietly replays a scripted flow — a convincing fake
// hiding a broken service is the single worst outcome available here, because
// everything looks like it is working and the thing you are demonstrating is
// not running. The scripted flows still exist; they are fixtures now, not a
// safety net (§9).
import type { AnswerPlan } from '@/data/types';

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

/**
 * Ask a question, get a plan.
 *
 * A declined plan is a SUCCESS, not an error: "the corpus cannot support this"
 * is an answer, and one of the more useful ones. Only the service being
 * unreachable throws.
 */
export async function askPostdoc(
  question: string,
  opts: { maxEvidence?: number; signal?: AbortSignal } = {},
): Promise<AnswerPlan> {
  let response: Response;
  try {
    response = await fetch('/api/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, maxEvidence: opts.maxEvidence ?? 30 }),
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

  return (await response.json()) as AnswerPlan;
}

/** Per-query cost, at the precision the number actually has. */
export function formatCost(usd: number): string {
  if (usd === 0) return '$0';
  if (usd < 0.01) return `$${usd.toFixed(4)}`;
  return `$${usd.toFixed(3)}`;
}
