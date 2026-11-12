// What a project keeps of the work done in its pages (alpha 2.0, stage 2;
// the service's project_state.py).
//
// The service is the store. Depositions, measured evidence, the runbooks a
// page adopts from a draft, promotes or opens to revise, and every runbook's
// lock, the parameter panel's overrides, the fits chosen for a scenario's
// inputs, the scenarios made in Proforma, the trains built in pureOS's Builder
// and Postdoc's Live conversations load from `GET /api/state` when a project
// opens, and every change is sent one row at a time. The browser keeps only
// the rows the service has not yet acknowledged: an outbox, saved with the
// preferences (durable.ts), so a deposition at the bench survives a reload
// while the service is away and is sent when it answers again. The service
// reads each row as its kind's model (alpha 2.2 E.0b): a write that does not
// read is refused in words, and a row kept before, that does not read, is
// named in `refused` while the rest load. What it answers is the generated
// `ProjectState` (alpha 2.2 E.11), each row served as kept.
import type { components } from '@/api/types.gen';
import type { LiveConversation } from './postdoc';
import { ServiceDown, ServiceRefused, call } from './http';

/** Each kind of row a project keeps of its pages: every field of `ProjectState` that holds rows. */
type StateKind = Exclude<keyof ProjectState, 'depositedBy' | 'refused'>;

/** A row the service keeps that does not read as its kind, and why; the store says each in words. */
export type RefusedRow = components['schemas']['RefusedRow'];

/** What a page sends to keep one row (`PUT /api/state/{kind}/{id}`): the row, who, and for a scope's overrides the rows it read. */
type StateWrite = components['schemas']['StateWrite'];

/** What the service answers a kept row with: the row as the project keeps it now. */
type StateKept = components['schemas']['StateKept'];

/**
 * Everything a project keeps of its pages (`GET /api/state`), keyed as the page keeps it, each row read as its kind's
 * model and served as kept: the depositions and measured evidence, the runbooks a page adopted or made and those
 * studies made (a lock rides in `runbookLocks`), the parameter panel's overrides by scope, the fermOS fits chosen for
 * a scenario's inputs (scenario id, input key, the fit's artifact id), the scenarios made in Proforma, pureOS's trains
 * built in the Builder by train id, and the Live conversations; who deposited each deposition, by id, which the
 * service writes from its rows' makers and no page sends (project_state.py `MAKERS`); and the rows the service keeps
 * that do not read as their kind, each with why.
 */
export type ProjectState = components['schemas']['ProjectState'];

/** The rows a page keeps of a project, kind by kind: what it compares and sends. */
export type ProjectRows = Pick<ProjectState, StateKind>;

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
  depositedBy: {},
  refused: [],
};

/** One row the service has not yet acknowledged. `value` null takes the row back. */
export interface OutboxEntry {
  project: string;
  kind: StateKind;
  id: string;
  value: unknown;
  by: string;
  at: string;
  /**
   * For a scope's overrides, the rows of the scope the page's view stood on when it made this write: the service lays
   * the write on what it keeps key by key against them, so another page's key stays, and refuses it in words when
   * another page changed a key this write changes too (bug hunt H7-04). Left out, the write replaces the scope
   * whole, as a write an older page queued does.
   */
  base?: unknown;
}

/** A row as the outbox names it: one project's one row of one kind. */
export const rowKey = (e: Pick<OutboxEntry, 'project' | 'kind' | 'id'>) => `${e.project}\u0000${e.kind}\u0000${e.id}`;

export function loadProjectState(signal?: AbortSignal): Promise<ProjectState> {
  return call<ProjectState>('/api/state', { signal });
}

/** Each kind's rows by id, so two states compare row by row. */
function rowsOf(state: ProjectRows): Record<StateKind, Map<string, unknown>> {
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
 * row whose object is the same is the same row. A scope's overrides carry the
 * rows the scope held in `before` (`base`), none where it held none.
 */
export function changes(before: ProjectRows, after: ProjectRows, project: string, by: string): OutboxEntry[] {
  const at = new Date().toISOString();
  const was = rowsOf(before);
  const now = rowsOf(after);
  const out: OutboxEntry[] = [];
  for (const kind of Object.keys(now) as StateKind[]) {
    for (const [id, value] of now[kind])
      if (was[kind].get(id) !== value)
        out.push(kind === 'overrides' ? { project, kind, id, value, by, at, base: was[kind].get(id) ?? [] } : { project, kind, id, value, by, at });
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
    ...state,
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

/**
 * The Live conversations a page holds once a project's rows load: those the
 * page started first, then every one the service keeps, newest first. The
 * service keeps every conversation, so the page holds every one too, and a
 * link to the oldest opens it.
 */
export function conversationsHeld(saved: LiveConversation[], current: LiveConversation[]): LiveConversation[] {
  const ids = new Set(current.map((c) => c.id));
  return [...current, ...saved.filter((c) => !ids.has(c.id)).reverse()];
}

/**
 * Add `entries` to `outbox`, a later write of a row replacing an earlier one still unsent.
 *
 * A scope's overrides are laid on key by key against the rows a write read (`base`), so a later write of a scope
 * replaces the scope's last queued write only while that write has never been sent (`mayHaveLanded` says no): it then
 * stands on what that write stood on, which the service has not seen changed. A write that may have reached the
 * service (sent, its answer lost, or taken from another tab at load) stays queued, and the later write follows it on
 * the rows it was made from, so the two land in order whether or not the first was kept (bug hunt H7-04).
 */
export function enqueue(
  outbox: OutboxEntry[],
  entries: OutboxEntry[],
  mayHaveLanded: (e: OutboxEntry) => boolean = () => false,
): OutboxEntry[] {
  const merges = (e: OutboxEntry) => e.kind === 'overrides' && e.value !== null;
  const later = new Set(entries.map(rowKey));
  // The page's row stands on the last queued write of it, which the new write replaces; an earlier write of the
  // row, another tab's that the page took at load, stays for the service to rule on in order (durable.ts).
  const last = new Map<string, number>();
  outbox.forEach((e, i) => {
    if (later.has(rowKey(e))) last.set(rowKey(e), i);
  });
  const replaced = new Set<number>();
  const added = entries.map((e) => {
    const i = last.get(rowKey(e));
    if (i === undefined) return e;
    if (!merges(e)) {
      replaced.add(i);
      return e;
    }
    if (mayHaveLanded(outbox[i])) return e;
    replaced.add(i);
    const { base: _stood, ...rest } = e;
    return 'base' in outbox[i] ? { ...rest, base: outbox[i].base } : rest;
  });
  return [...outbox.filter((_, i) => !replaced.has(i)), ...added];
}

/** Whether two lists of a scope's overrides hold the same rows, each read by its key and its fields, in any order. */
export function sameOverrides(a: unknown, b: unknown): boolean {
  if (!Array.isArray(a) || !Array.isArray(b) || a.length !== b.length) return false;
  const canon = (v: unknown): string =>
    Array.isArray(v)
      ? `[${v.map(canon).join(',')}]`
      : v !== null && typeof v === 'object'
        ? `{${Object.keys(v as Record<string, unknown>)
            .filter((k) => (v as Record<string, unknown>)[k] !== undefined && (v as Record<string, unknown>)[k] !== null)
            .sort()
            .map((k) => `${JSON.stringify(k)}:${canon((v as Record<string, unknown>)[k])}`)
            .join(',')}}`
        : JSON.stringify(v);
  const rows = (l: unknown[]) => l.map(canon).sort();
  return JSON.stringify(rows(a)) === JSON.stringify(rows(b));
}

interface Flushed {
  /** What is still owed: everything from the first write the service did not answer. */
  left: OutboxEntry[];
  sent: number;
  /** Writes the service answered with a refusal, in its words; they are dropped. */
  refused: { entry: OutboxEntry; why: string }[];
  /**
   * The writes the service kept, in order, each with the row as it answered it: a scope's overrides as the scope
   * holds once the write was laid on, another page's keys among them; a take-back answers null.
   */
  kept: { entry: OutboxEntry; value: unknown }[];
}

/**
 * Send the outbox in order, each row naming its own project. A refusal is the
 * service's answer and the row is dropped with its reason; a service that does
 * not answer stops the flush, and everything from there on is kept. `still`,
 * asked before each row, stops the flush the same way when it answers false
 * (the browser's data was cleared while the flush ran).
 */
export async function flush(outbox: OutboxEntry[], still: () => boolean = () => true): Promise<Flushed> {
  const refused: Flushed['refused'] = [];
  const kept: Flushed['kept'] = [];
  let sent = 0;
  for (let i = 0; i < outbox.length; i++) {
    if (!still()) return { left: outbox.slice(i), sent, refused, kept };
    const e = outbox[i];
    const path = `/api/state/${encodeURIComponent(e.kind)}/${encodeURIComponent(e.id)}`;
    const headers = { 'X-OpenFerment-Project': e.project };
    try {
      if (e.value === null) {
        await call(`${path}?by=${encodeURIComponent(e.by)}`, { method: 'DELETE', headers });
        kept.push({ entry: e, value: null });
      } else {
        const write: StateWrite = { by: e.by, value: e.value, ...(e.base !== undefined ? { base: e.base } : {}) };
        const answer = await call<StateKept>(path, {
          method: 'PUT',
          headers: { ...headers, 'Content-Type': 'application/json' },
          body: JSON.stringify(write),
        });
        kept.push({ entry: e, value: answer?.value ?? e.value });
      }
      sent += 1;
    } catch (err) {
      if (err instanceof ServiceRefused && err.status !== 503) {
        refused.push({ entry: e, why: err.message });
        continue;
      }
      if (err instanceof ServiceDown || err instanceof ServiceRefused) return { left: outbox.slice(i), sent, refused, kept };
      throw err;
    }
  }
  return { left: [], sent, refused, kept };
}
