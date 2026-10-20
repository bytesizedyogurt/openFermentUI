// The browser's side of passage search (OF-BLD-014 §4.4).
//
// Three calls: what is indexed, search, and the scorecard. Same discipline as
// lib/intake.ts: with the service down this says so and names the command
// that starts it, and nothing stands in for a result (E.2).
import type { PassageHit, RagReport, RagSearchRequest, RagSearchResponse, RagStatus } from '@/data/types';
import { href } from '@/router';
import { useStore } from '@/store';
import { START_COMMAND, postdocHealth } from './postdoc';

export class RagDown extends Error {
  constructor(
    message: string,
    readonly remedy: string = `Start it with \`${START_COMMAND}\` from \`core/\`.`,
  ) {
    super(message);
    this.name = 'RagDown';
  }
}

/** The service answered and said no: no scorecard yet, a lane that cannot run, a spent budget. */
export class RagRefused extends Error {
  constructor(
    readonly status: number,
    why: string,
  ) {
    super(why);
    this.name = 'RagRefused';
  }
}

/** A call to the service, with RagDown and RagRefused as its two failures;
 * lib/geneos.ts shares it. */
export async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, init);
  } catch {
    throw new RagDown('The service is not running.');
  }
  if (response.ok) return (await response.json()) as T;
  if ([404, 409, 422, 503].includes(response.status)) {
    let detail = '';
    try {
      detail = String(((await response.json()) as { detail?: unknown }).detail ?? '');
    } catch {
      /* the status is the message */
    }
    if (response.status !== 404 || detail) throw new RagRefused(response.status, detail || `The service answered ${response.status}.`);
  }
  try {
    await postdocHealth(init?.signal ?? undefined);
  } catch {
    throw new RagDown('The service is not running.');
  }
  throw new RagDown(`The service answered ${response.status}.`, 'The service is running, so check its log — it will name what went wrong.');
}

export const ragStatus = (signal?: AbortSignal) => call<RagStatus>('/api/rag/status', { signal });

export const ragReport = (signal?: AbortSignal) => call<RagReport>('/api/rag/report', { signal });

export const ragSearch = (question: string, lane: string | null, signal?: AbortSignal) => {
  // Settings → Programs (OF-BLD-016 §2.3): off, archived programs' passages
  // are left out by the service.
  const body: RagSearchRequest = { question, k: 8, lane, includeArchived: useStore.getState().showArchived };
  return call<RagSearchResponse>('/api/rag/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  });
};

/**
 * The paper's own words a hit points at, as the reader will look for them:
 * the grading reader's sentence when it chose one, else the passage's span of
 * its section. A table chunk carries its heading (and, after the first, its
 * header row) for context; those lines are not in that span, so they go.
 */
export function quoteOf(hit: PassageHit): string {
  if (hit.sentence) return hit.sentence;
  const p = hit.passage;
  if (p.kind !== 'table') return p.text;
  const lines = p.text.split('\n');
  return lines.slice(p.start === 0 ? 1 : 2).join('\n');
}

/** The reader, open at the hit's section with its words marked. */
export function readerHref(hit: PassageHit): string {
  const q = new URLSearchParams({ section: hit.passage.sectionId, quote: quoteOf(hit) });
  return href(`/biorepo/paper/${hit.passage.paperId}?${q.toString()}`);
}
