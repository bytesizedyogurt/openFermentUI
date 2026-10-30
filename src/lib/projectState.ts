// What a project keeps of the work done in its pages (alpha 2.0, stage 2;
// the service's project_state.py).
//
// The service is the store. Depositions, measured evidence, runbooks adopted
// from a draft and every runbook's lock, the parameter panel's overrides, the
// fits chosen for a scenario's inputs, the scenarios made in Proforma, the
// trains built in pureOS's Builder and Postdoc's Live conversations load from
// `GET /api/state` when a project opens, and every change is sent one row at a
// time. The browser keeps only the rows the service has not yet acknowledged:
// an outbox, saved with the preferences (durable.ts), so a deposition at the
// bench survives a reload while the service is away and is sent when it
// answers again.
import type { Deposition, LiveConversation, MeasuredEvidence, Override, Runbook, Scenario } from '@/data/types';
import type { TrainMade } from './durable';
import { ServiceDown, ServiceRefused, call } from './http';

export type StateKind =
  | 'depositions'
  | 'measuredEvidence'
  | 'runbooks'
  | 'runbookLocks'
  | 'overrides'
  | 'fits'
  | 'scenarios'
  | 'trains'
  | 'conversations';

/** Everything a project keeps of its pages, keyed as the page keeps it. */
export interface ProjectState {
  depositions: Deposition[];
  measuredEvidence: MeasuredEvidence[];
  /** Runbooks adopted from a Postdoc draft, unlocked; a lock rides in runbookLocks. */
  runbooks: Runbook[];
  runbookLocks: Record<string, { lockedAt: string; lockHash: string }>;
  /** The parameter panel's overrides, by scope. */
  overrides: Record<string, Override[]>;
  /** The fermOS fits chosen for a scenario's inputs: scenario id → input key → artifact id. */
  fits: Record<string, Record<string, string>>;
  /** The scenarios made in Proforma, whole. */
  scenarios: Scenario[];
  /** pureOS's trains built in the Builder, by train id. */
  trains: Record<string, TrainMade>;
  conversations: LiveConversation[];
}

export const EMPTY_STATE: ProjectState = {
  depositions: [],
  measuredEvidence: [],
  runbooks: [],
  runbookLocks: {},
  overrides: {},
  fits: {},
  scenarios: [],
  trains: {},
  conversations: [],
};

/** One row the service has not yet acknowledged. `value` null takes the row back. */
export interface OutboxEntry {
  project: string;
  kind: StateKind;
  id: string;
  value: unknown;
  by: string;
  at: string;
}

export function loadProjectState(signal?: AbortSignal): Promise<ProjectState> {
  return call<ProjectState>('/api/state', { signal });
}

/** Each kind's rows by id, so two states compare row by row. */
function rowsOf(state: ProjectState): Record<StateKind, Map<string, unknown>> {
  const byId = <T>(items: T[], id: (x: T) => string) => new Map(items.map((x) => [id(x), x as unknown]));
  const entries = <T>(record: Record<string, T>) => new Map(Object.entries(record) as [string, unknown][]);
  return {
    depositions: byId(state.depositions, (d) => d.id),
    measuredEvidence: byId(state.measuredEvidence, (m) => m.id),
    runbooks: byId(state.runbooks, (r) => r.id),
    runbookLocks: entries(state.runbookLocks),
    overrides: entries(state.overrides),
    fits: entries(state.fits),
    scenarios: byId(state.scenarios, (s) => s.id),
    trains: entries(state.trains),
    conversations: byId(state.conversations, (c) => c.id),
  };
}

// What leaves the page without being taken back: the Live conversations past
// the newest the page shows stay on the service, and a deposition or a
// measurement is never taken back.
const KEPT_WHEN_GONE: ReadonlySet<StateKind> = new Set(['conversations', 'depositions', 'measuredEvidence']);

/**
 * The writes that take `before` to `after`: every row whose object changed,
 * and every row a person took back. The store replaces what it changes, so a
 * row whose object is the same is the same row.
 */
export function changes(before: ProjectState, after: ProjectState, project: string, by: string): OutboxEntry[] {
  const at = new Date().toISOString();
  const was = rowsOf(before);
  const now = rowsOf(after);
  const out: OutboxEntry[] = [];
  for (const kind of Object.keys(now) as StateKind[]) {
    for (const [id, value] of now[kind]) if (was[kind].get(id) !== value) out.push({ project, kind, id, value, by, at });
    if (KEPT_WHEN_GONE.has(kind)) continue;
    for (const id of was[kind].keys()) if (!now[kind].has(id)) out.push({ project, kind, id, value: null, by, at });
  }
  return out;
}

/** `state` with the outbox's rows laid over it, in order: what the page owes stands. */
export function applyEntries(state: ProjectState, entries: OutboxEntry[]): ProjectState {
  const rows = rowsOf(state);
  for (const e of entries) {
    if (e.value === null) rows[e.kind].delete(e.id);
    else rows[e.kind].set(e.id, e.value);
  }
  const list = <T>(kind: StateKind) => [...rows[kind].values()] as T[];
  const record = <T>(kind: StateKind) => Object.fromEntries(rows[kind]) as Record<string, T>;
  return {
    depositions: list('depositions'),
    measuredEvidence: list('measuredEvidence'),
    runbooks: list('runbooks'),
    runbookLocks: record('runbookLocks'),
    overrides: record('overrides'),
    fits: record('fits'),
    scenarios: list('scenarios'),
    trains: record('trains'),
    conversations: list('conversations'),
  };
}

/** Add `entries` to `outbox`, a later write of a row replacing an earlier one still unsent. */
export function enqueue(outbox: OutboxEntry[], entries: OutboxEntry[]): OutboxEntry[] {
  const key = (e: OutboxEntry) => `${e.project}\u0000${e.kind}\u0000${e.id}`;
  const later = new Set(entries.map(key));
  return [...outbox.filter((e) => !later.has(key(e))), ...entries];
}

export interface Flushed {
  /** What is still owed: everything from the first write the service did not answer. */
  left: OutboxEntry[];
  sent: number;
  /** Writes the service answered with a refusal, in its words; they are dropped. */
  refused: { entry: OutboxEntry; why: string }[];
}

/**
 * Send the outbox in order, each row naming its own project. A refusal is the
 * service's answer and the row is dropped with its reason; a service that does
 * not answer stops the flush, and everything from there on is kept.
 */
export async function flush(outbox: OutboxEntry[]): Promise<Flushed> {
  const refused: Flushed['refused'] = [];
  let sent = 0;
  for (let i = 0; i < outbox.length; i++) {
    const e = outbox[i];
    const path = `/api/state/${encodeURIComponent(e.kind)}/${encodeURIComponent(e.id)}`;
    const headers = { 'X-OpenFerment-Project': e.project };
    try {
      if (e.value === null) await call(`${path}?by=${encodeURIComponent(e.by)}`, { method: 'DELETE', headers });
      else
        await call(path, {
          method: 'PUT',
          headers: { ...headers, 'Content-Type': 'application/json' },
          body: JSON.stringify({ by: e.by, value: e.value }),
        });
      sent += 1;
    } catch (err) {
      if (err instanceof ServiceRefused && err.status !== 503) {
        refused.push({ entry: e, why: err.message });
        continue;
      }
      if (err instanceof ServiceDown || err instanceof ServiceRefused) return { left: outbox.slice(i), sent, refused };
      throw err;
    }
  }
  return { left: [], sent, refused };
}
