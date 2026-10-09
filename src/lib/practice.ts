// The browser's side of Practice (OF-BLD-013 §4.3).
//
// Three calls, no key: read the scenarios and sessions, draft a scenario,
// answer the tutor. Both writes are model calls, so Practice needs the
// service; with it down there is nothing to draft and nobody to ask, and the
// screens say so. The rules live in `core/openferment_core/practice.py`; a
// refusal comes back as the rule and the reason, and nothing here repeats
// them.
import type {
  Deposition,
  Practice,
  PracticeDeposition,
  PracticeDraftRequest,
  PracticeScenario,
  PracticeSession,
  PracticeTurnRequest,
  Runbook,
} from '@/data/types';
import { IntakeDown } from './intake';

/** The service refused what the model wrote, or the request, and said which rule held. */
export class PracticeRefused extends Error {
  constructor(
    readonly rule: string,
    readonly why: string,
  ) {
    super(why);
    this.name = 'PracticeRefused';
  }
}

async function call<T>(path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  let response: Response;
  try {
    response = await fetch(
      path,
      body === undefined
        ? { signal }
        : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal },
    );
  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') throw e;
    throw new IntakeDown('The service is not running.');
  }
  let detail = '';
  if (!response.ok) {
    try {
      detail = String(((await response.json()) as { detail?: string }).detail ?? '');
    } catch {
      /* the status is the message */
    }
  }
  if (response.status === 422) {
    const m = /^([a-z]+): (.*)$/s.exec(detail);
    throw new PracticeRefused(m ? m[1] : 'unknown', m ? m[2] : detail || 'refused without a reason');
  }
  // 503: no key, no network, or every model declined. The detail says which.
  if (!response.ok) throw new IntakeDown(detail || `The service answered ${response.status}.`);
  return (await response.json()) as T;
}

/** Every scenario and session, or null when there is no service to ask. */
export async function loadPractice(signal?: AbortSignal): Promise<Practice | null> {
  try {
    return await call<Practice>('/api/practice', undefined, signal);
  } catch {
    return null;
  }
}

export const draftScenario = (r: PracticeDraftRequest) => call<PracticeScenario>('/api/practice/draft', r);
export const takeTurn = (r: PracticeTurnRequest) => call<PracticeSession>('/api/practice/turn', r);
/** Ask the ledger again for a closed session it holds no entry for. */
export const recordSession = (sessionId: string) => call<PracticeSession>('/api/practice/record', { sessionId });

/**
 * A Deposition as the service reads it for drafting: what was recorded, at
 * which step, in the operator's words, with the measure's name from the
 * runbook as its label. Depositions live in this browser, so the service sees
 * the ones it is sent.
 */
export function forDrafting(d: Deposition, runbooks: Runbook[]): PracticeDeposition {
  const schema = runbooks.find((r) => r.id === d.runbookId)?.measurementSchema ?? [];
  return {
    id: d.id,
    protocolId: d.protocolId,
    startedAt: d.startedAt,
    entries: d.entries.map((e) => ({
      id: e.id,
      stepId: e.stepId,
      at: e.at,
      value: e.value,
      unit: e.unit,
      raw: e.raw,
      label: schema.find((m) => m.id === e.measureId)?.label ?? null,
      confirmed: e.confirmed,
    })),
    observations: d.observations.map((o) => ({ id: o.id, stepId: o.stepId, at: o.at, raw: o.raw })),
  };
}

/** Text the model wrote, split where it marks an evidence item: [v1] and so on. */
export function splitMarkers(text: string): (string | { marker: string })[] {
  const out: (string | { marker: string })[] = [];
  let last = 0;
  for (const m of text.matchAll(/\[(v\d+)\]/g)) {
    if (m.index! > last) out.push(text.slice(last, m.index));
    out.push({ marker: m[1] });
    last = m.index! + m[0].length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}
