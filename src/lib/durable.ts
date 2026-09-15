// Durable state (OF-BLD-006 §4.6).
//
// A DELIBERATE REVERSAL. OF-BLD-005 §10 forbade browser storage outright, and
// that was the right call for what it was solving: the app ships as a
// single-file artifact, and an artifact that quietly accumulates state across
// visits is a bad neighbour. It is the wrong call here. A fermentation at hour
// 14 with timers running and deviations logged cannot be lost to a page
// reload. That is a safety problem, not an inconvenience.
//
// So state is split by lifetime rather than persisted wholesale:
//
//   Reference  papers, protocols, products, vocabulary — never mutated, so
//              there is nothing to persist. Reloading gets them from source.
//   Durable    depositions, review decisions, runbook locks — must survive.
//   Ephemeral  open panels, density, theme, sim speed — must NOT survive. A
//              theme that follows you across sessions is a preference; a
//              collapsed panel that does is a bug.
//
// IndexedDB rather than localStorage: it is asynchronous, so a large
// deposition never blocks the step the operator is standing at, and it is not
// capped at a few megabytes.
//
// EVERY PATH HERE CAN FAIL AND NONE OF THEM THROWS. Private windows, blocked
// site data, a browser with the store disabled, Node during a check script —
// all of these end with the app running normally on in-memory state. Losing
// persistence is bad; refusing to open the screen because persistence is
// unavailable would be worse.
import type { Deposition, MeasuredEvidence, Provenance, RecordStatus, ReviewDecision } from '@/data/types';

const DB_NAME = 'openferment';
const DB_VERSION = 1;
const STORE = 'durable';
const KEY = 'snapshot';

/**
 * A review decision, reduced to the fields review actually changes.
 *
 * Named DurableReviewDecision (OF-BLD-012 §2.1) because the service's
 * ReviewDecision in `src/data/types.ts` is this plus recordId, at, and an
 * optional replacement span. `DecisionMirror` below has the compiler hold the
 * two together: every field here must exist there with the same type.
 */
export interface DurableReviewDecision {
  status: RecordStatus;
  provenance: Provenance;
  gold?: { value: number | string; unit: string };
  corrected?: { value: number; unit: string };
  rejectReason?: string;
  reviewer?: string;
  /**
   * When THIS decision was made, ISO. Compared against the service's
   * decision for the same record — the later wins (OF-BLD-012 §7.3). The
   * snapshot's savedAt moves on every deposition and lock save, so it is only
   * the fallback for snapshots written before this field existed.
   */
  at?: string;
  /**
   * The sentence and section a promotion re-anchored the record to
   * (OF-BLD-012 §7.3), when it carried the extractor's span. Absent for a
   * record decided on its own quote. Kept so a carry-over made offline is
   * still standing on the paper's words after a reload, and is posted with
   * them when the service is back.
   */
  quote?: string;
  sectionId?: string;
}

/**
 * Compile-time proof that a ReviewDecision carries every DurableReviewDecision
 * field: every key here is a key there (a field added here alone fails the
 * build), and a ReviewDecision is assignable to this shape (the types agree).
 */
type KeysSubset<A, B> = [keyof A] extends [keyof B] ? true : never;
export const DecisionMirror: [KeysSubset<DurableReviewDecision, ReviewDecision>, (d: ReviewDecision) => DurableReviewDecision] = [
  true,
  (d) => d,
];

export interface DurableSnapshot {
  /** Bumped when the shape changes; an older snapshot is dropped, not guessed at. */
  version: 1;
  savedAt: string;
  depositions: Deposition[];
  /** First-party measurements released by reconciliation. */
  measuredEvidence: MeasuredEvidence[];
  /** Keyed by record id. Re-applied over the seeded records at hydrate. */
  reviewDecisions: Record<string, DurableReviewDecision>;
  /** Keyed by runbook id. Locks only — the runbook itself comes from seed. */
  runbookLocks: Record<string, { lockedAt: string; lockHash: string }>;
}

export const EMPTY_SNAPSHOT: DurableSnapshot = {
  version: 1,
  savedAt: '',
  depositions: [],
  measuredEvidence: [],
  reviewDecisions: {},
  runbookLocks: {},
};

/**
 * Whether persistence is possible at all. False in Node (the check scripts
 * import the store) and in browsers with site data blocked.
 */
export function durableAvailable(): boolean {
  try {
    return typeof indexedDB !== 'undefined' && indexedDB !== null;
  } catch {
    return false;
  }
}

let dbPromise: Promise<IDBDatabase | null> | null = null;

function openDb(): Promise<IDBDatabase | null> {
  if (!durableAvailable()) return Promise.resolve(null);
  if (dbPromise) return dbPromise;
  dbPromise = new Promise((resolve) => {
    let settled = false;
    const done = (v: IDBDatabase | null) => {
      if (!settled) {
        settled = true;
        resolve(v);
      }
    };
    try {
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains(STORE)) db.createObjectStore(STORE);
      };
      req.onsuccess = () => done(req.result);
      req.onerror = () => done(null);
      // A blocked upgrade never fires either handler. Time out rather than
      // leaving every caller awaiting a promise that will not settle.
      req.onblocked = () => done(null);
      setTimeout(() => done(null), 3000);
    } catch {
      done(null);
    }
  });
  return dbPromise;
}

/** The stored snapshot, or null when there is none or it cannot be read. */
export async function loadDurable(): Promise<DurableSnapshot | null> {
  const db = await openDb();
  if (!db) return null;
  return new Promise((resolve) => {
    try {
      const tx = db.transaction(STORE, 'readonly');
      const req = tx.objectStore(STORE).get(KEY);
      req.onsuccess = () => {
        const v = req.result as DurableSnapshot | undefined;
        // A snapshot from an older shape is discarded rather than migrated on
        // a guess. Losing a session's depositions is bad; silently
        // reinterpreting them as a shape they were never written in is worse.
        resolve(v && v.version === 1 ? v : null);
      };
      req.onerror = () => resolve(null);
    } catch {
      resolve(null);
    }
  });
}

let pending: DurableSnapshot | null = null;
let timer: ReturnType<typeof setTimeout> | null = null;

async function flush(): Promise<void> {
  const snapshot = pending;
  pending = null;
  timer = null;
  if (!snapshot) return;
  const db = await openDb();
  if (!db) return;
  try {
    const tx = db.transaction(STORE, 'readwrite');
    tx.objectStore(STORE).put(snapshot, KEY);
  } catch {
    // Quota exceeded, or the store went away mid-session. The app keeps
    // running on memory; the next successful write catches up.
  }
}

/**
 * Queue a write. Coalesced on a short timer because a running deposition
 * mutates on every keystroke and every timer tick, and writing each one
 * through would put IndexedDB traffic in the way of the bench.
 */
export function saveDurable(snapshot: DurableSnapshot): void {
  if (!durableAvailable()) return;
  pending = snapshot;
  if (timer) return;
  timer = setTimeout(() => void flush(), 400);
}

/** Write immediately — used when the tab is going away. */
export function flushDurable(): void {
  if (timer) {
    clearTimeout(timer);
    timer = null;
  }
  void flush();
}

/** Drop everything persisted. Used by the demo reset, which must truly reset. */
export async function clearDurable(): Promise<void> {
  pending = null;
  if (timer) {
    clearTimeout(timer);
    timer = null;
  }
  const db = await openDb();
  if (!db) return;
  try {
    const tx = db.transaction(STORE, 'readwrite');
    tx.objectStore(STORE).delete(KEY);
  } catch {
    /* nothing to do — the caller cannot act on this either */
  }
}
