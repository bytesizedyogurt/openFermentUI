// The browser's side of Intake (OF-BLD-012 §5.4).
//
// Three calls, no key. The service fetches from Europe PMC, splits the JATS,
// and caches the result; this asks for one paper, asks what has been fetched,
// and asks for the overlay the store applies at load.
//
// SAME DISCIPLINE AS lib/postdoc.ts. When the service is unreachable this says
// so and says how to start it, and it never quietly substitutes the timer
// simulation for a real fetch — the ingest board keeps that path, labelled as
// the offline one, and the choice between them is made in the store where the
// reader can see which one ran.
import type { DecisionCheck, ExtractResponse, FetchResult, IntakeStatus, Overlay, ReviewDecision } from '@/data/types';
import { START_COMMAND, postdocHealth } from './postdoc';

export class IntakeDown extends Error {
  constructor(
    message: string,
    /** How to fix it, when there is a fix the reader can carry out. */
    readonly remedy: string = `Start it with \`${START_COMMAND}\` from \`core/\`.`,
  ) {
    super(message);
    this.name = 'IntakeDown';
  }
}

/**
 * The service answered with an error. Decide whether it is running.
 *
 * The Vite dev proxy answers 500 when it cannot reach the service, so a dead
 * upstream does not look like a network error and the catch never runs. 404
 * and 422 are statuses our own service produces (unknown paper; bad body) and
 * mean it is up; anything else is ambiguous, so ask health which it was.
 */
async function explain(response: Response, signal?: AbortSignal): Promise<never> {
  if (response.status !== 404 && response.status !== 422) {
    try {
      await postdocHealth(signal);
    } catch {
      throw new IntakeDown('Intake service not running.');
    }
  }
  let detail = '';
  try {
    detail = String(((await response.json()) as { detail?: string }).detail ?? '');
  } catch {
    /* not JSON — the status is the message */
  }
  throw new IntakeDown(
    `Intake service answered ${response.status}${detail ? ` — ${detail}` : ''}.`,
    'The service is running, so check its log — it will name what went wrong.',
  );
}

/**
 * The service stored nothing: `biorepo.write` refused the decision (OF-BLD-012
 * §2.3). `rule` is which of its conditions held — record, reviewer,
 * fulltext, quote — and the message is the reason in words. Not an outage:
 * the service is up and said no.
 */
export class DecisionRefused extends Error {
  constructor(
    readonly rule: string,
    readonly why: string,
  ) {
    super(why);
    this.name = 'DecisionRefused';
  }
}

/**
 * Post one review decision (§7.2, §7.3). The service's `biorepo.write` is the
 * only thing that stores it; this returns what was stored — the decision as
 * sent, plus the quote and section a gold decision anchored on — or throws
 * DecisionRefused with the rule, or IntakeDown when there is no service.
 */
export async function postDecision(decision: ReviewDecision, signal?: AbortSignal): Promise<ReviewDecision> {
  let response: Response;
  try {
    response = await fetch('/api/biorepo/decisions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(decision),
      signal,
    });
  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') throw e;
    throw new IntakeDown('Intake service not running.');
  }
  if (response.status === 422) {
    let detail = '';
    try {
      detail = String(((await response.json()) as { detail?: string }).detail ?? '');
    } catch {
      /* the status is the message */
    }
    const m = /^([a-z]+): (.*)$/s.exec(detail);
    throw new DecisionRefused(m ? m[1] : 'unknown', m ? m[2] : detail || 'refused without a reason');
  }
  if (!response.ok) await explain(response, signal);
  return (await response.json()) as ReviewDecision;
}

/**
 * Would the service keep this decision? (OF-BLD-012.1 F1.5)
 *
 * `biorepo.write` runs every one of its rules with nothing written and
 * answers 200 either way — a refusal is an answer here, not an error, so
 * only an outage throws. The screen asks before the reviewer presses the
 * key, which is why the rules live in one place and are not mirrored.
 */
export async function checkDecision(decision: ReviewDecision, signal?: AbortSignal): Promise<DecisionCheck> {
  let response: Response;
  try {
    response = await fetch('/api/biorepo/check', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(decision),
      signal,
    });
  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') throw e;
    throw new IntakeDown('Intake service not running.');
  }
  if (!response.ok) await explain(response, signal);
  return (await response.json()) as DecisionCheck;
}

/**
 * Fetch one paper's full text through the service.
 *
 * A FAILED FETCH IS A SUCCESS OF THIS CALL: the result carries `failed:fetch`
 * or `failed:parse` and a reason, and the board renders it. Only the service
 * being unreachable throws.
 */
export async function fetchPaper(
  paperId: string,
  opts: { force?: boolean; signal?: AbortSignal } = {},
): Promise<FetchResult> {
  let response: Response;
  try {
    response = await fetch(
      `/api/intake/${encodeURIComponent(paperId)}/fetch${opts.force ? '?force=true' : ''}`,
      { method: 'POST', signal: opts.signal },
    );
  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') throw e;
    throw new IntakeDown('Intake service not running.');
  }
  if (!response.ok) await explain(response, opts.signal);
  return (await response.json()) as FetchResult;
}

/**
 * Extract one fetched paper through the service (OF-BLD-012 §6.3): one
 * forced tool call, every candidate anchored, the refusals counted. 422 when
 * the paper has no full text and 503 when there is no key both surface as
 * IntakeDown with the service's own reason; nothing is invented to fill in.
 */
export async function extractPaper(
  paperId: string,
  opts: { force?: boolean; signal?: AbortSignal } = {},
): Promise<ExtractResponse> {
  let response: Response;
  try {
    response = await fetch(
      `/api/intake/${encodeURIComponent(paperId)}/extract${opts.force ? '?force=true' : ''}`,
      { method: 'POST', signal: opts.signal },
    );
  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') throw e;
    throw new IntakeDown('Intake service not running.');
  }
  if (!response.ok) await explain(response, opts.signal);
  return (await response.json()) as ExtractResponse;
}

/** Every paper the service has a cached fetch for, success or failure. */
export async function intakeStatus(signal?: AbortSignal): Promise<Record<string, IntakeStatus>> {
  let response: Response;
  try {
    response = await fetch('/api/intake/status', { signal });
  } catch {
    throw new IntakeDown('Intake service not running.');
  }
  if (!response.ok) await explain(response, signal);
  return (await response.json()) as Record<string, IntakeStatus>;
}

/**
 * The overlay, or null when there is no service to ask.
 *
 * Deliberately never throws: this runs at every page load, and a page that
 * fails to load because an optional service is absent has the priorities
 * backwards. The built artifact has no server at all — the fetch answers 404
 * from whatever static host it sits on, and the app is exactly the seed.
 */
export async function loadOverlay(signal?: AbortSignal): Promise<Overlay | null> {
  try {
    const health = await postdocHealth(signal);
    if (!health.ok) return null;
    const response = await fetch('/api/biorepo/overlay', { signal });
    if (!response.ok) return null;
    return (await response.json()) as Overlay;
  } catch {
    return null;
  }
}
