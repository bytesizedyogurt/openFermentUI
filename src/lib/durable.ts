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
//   Reference  papers, vocabulary — never mutated, so there is nothing to
//              persist. Reloading gets them from source.
//   Service    since alpha 2.0 (stage 2) every scientific record lives on the
//              service, in the open project: review decisions, Guild's
//              ledger, depositions, measured evidence, runbooks and their
//              locks, overrides, fits, scenarios, trains and Live
//              conversations (lib/projectState.ts), and since alpha 2.2 its
//              catalogues and protocols, a lesson's passing among the
//              ledger's entries (E.12).
//   Durable    who is deciding and who is acting, and the writes the service
//              has not yet acknowledged: review decisions, Guild changes and
//              project rows made while it was away — must survive until they
//              are sent.
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
import type { components } from '@/api/types.gen';
import type { Guild, GuildPerson, GuildWithdrawal } from '@/lib/guild';
import type { Deposition, MeasuredEvidence, Provenance, Runbook } from './studies';
import type { RecordStatus, ReviewDecision } from './review';
import type { Override } from './params';
import type { LiveConversation } from './postdoc';
import type { Scenario } from './proforma';
import type { OutboxEntry } from './projectState';

const DB_NAME = 'openferment';
const DB_VERSION = 1;
const STORE = 'durable';
const KEY = 'snapshot';

/**
 * A review decision, reduced to the fields review actually changes.
 *
 * Named DurableReviewDecision (OF-BLD-012 §2.1) because the service's
 * ReviewDecision (`src/lib/review.ts`, generated) is this plus recordId, at,
 * and an optional replacement span. Each field reads its type from it, and
 * `DecisionMirror` below has the compiler hold the two together: every field
 * here must exist there with the same type.
 */
export interface DurableReviewDecision {
  status: RecordStatus;
  provenance: Provenance;
  gold?: ReviewDecision['gold'];
  corrected?: ReviewDecision['corrected'];
  rejectReason?: ReviewDecision['rejectReason'];
  reviewer?: ReviewDecision['reviewer'];
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
  quote?: ReviewDecision['quote'];
  sectionId?: ReviewDecision['sectionId'];
  /**
   * The project the decision was made in, so a page re-applies and sends only
   * its own project's decisions. Absent from a decision saved before this was
   * kept, which a page reads as its own, as it did then.
   */
  project?: string;
  /**
   * The record decided. The snapshot keys a decision by its project and its
   * record (`decisionKey`), so two projects' decisions on one record id are
   * two; a decision saved before then is keyed by its record alone.
   */
  recordId?: ReviewDecision['recordId'];
}

/**
 * Compile-time proof that a ReviewDecision carries every DurableReviewDecision
 * field: every key here is a key there (a field added here alone fails the
 * build), and a ReviewDecision is assignable to this shape (the types agree).
 */
type KeysSubset<A, B> = [keyof A] extends [keyof B] ? true : never;
export const DecisionMirror: [KeysSubset<Omit<DurableReviewDecision, 'project'>, ReviewDecision>, (d: ReviewDecision) => DurableReviewDecision] = [
  true,
  (d) => d,
];

export interface DurableSnapshot {
  /** Bumped when the shape changes; an older snapshot is dropped, not guessed at. */
  version: 1;
  savedAt: string;
  /**
   * Review decisions the service has not yet acknowledged, keyed by their
   * project and record (`decisionKey`): re-applied over the service's records
   * at hydrate and posted when it answers (`syncDecisions`), each by a page
   * open on its project (`decisionsIn`).
   */
  reviewDecisions: Record<string, DurableReviewDecision>;
  /**
   * The project rows the service has not yet acknowledged, oldest first
   * (lib/projectState.ts). Each names its project.
   */
  outbox?: OutboxEntry[];
  /**
   * LEGACY, read once. Before alpha 2.0 the browser kept these itself; a
   * snapshot that still holds them has them carried to the open project's
   * outbox at hydrate, and the next save leaves them out.
   */
  depositions?: Deposition[];
  /** LEGACY, read once: first-party measurements released by reconciliation. */
  measuredEvidence?: MeasuredEvidence[];
  /** LEGACY, read once: locks by runbook id. */
  runbookLocks?: Record<string, { lockedAt: string; lockHash: string }>;
  /**
   * The person deciding, as they typed it in Settings (OF-BLD-012.1 F2).
   * Durable because a reviewer should not have to re-introduce themselves
   * after a refresh. Empty until set; `biorepo.write` refuses a decision
   * that carries no name, so nothing reaches the committed file unsigned.
   */
  reviewerName: string;
  /**
   * What Guild's ledger still owes the service, and who was signing
   * (OF-BLD-013 §1.3), by project: each project's ledger is its own, so a page
   * takes the block of the project it has open, and every other project's
   * block stays where it lies. Optional, so older snapshots still load.
   */
  guildOwed?: Record<string, GuildOwed>;
  /**
   * LEGACY, read once: the one block a snapshot kept before Guild's owed
   * writes were kept by project, read as the open project's by the page that
   * loads it (the reading it had when it was written), and left out of that
   * page's next save.
   */
  guild?: GuildOwed;
  /**
   * LEGACY, left where it lies. The lessons finished in this browser, by id,
   * as a snapshot before alpha 2.2 E.12 kept them; a lesson shows finished
   * from the ledger's entries for whoever is learning, so nothing reads this,
   * and the next save leaves it out.
   */
  learnProgress?: Record<string, true>;
  /**
   * LEGACY, read once. Proforma's typed assumptions, by scenario id
   * (OF-BLD-014 §8.4); a snapshot that holds them with no
   * `parameterOverrides` entry for a scenario is read into that scope (D3).
   */
  proformaAssumptions?: Record<string, ScenarioAssumption[]>;
  /** LEGACY, read once: the parameter panel's overrides, by scope (OF-BLD-020 D3). */
  parameterOverrides?: Record<string, Override[]>;
  /** LEGACY, read once: the fermOS fits chosen for a scenario's inputs (OF-BLD-019 §5.1). */
  proformaFits?: Record<string, Record<string, string>>;
  /** LEGACY, read once: runbooks adopted from a Postdoc draft (OF-BLD-014 §9.2). */
  adoptedRunbooks?: Runbook[];
  /** LEGACY, read once: Postdoc's Live conversations, newest first. */
  liveConversations?: LiveConversation[];
  /** LEGACY, read once: Proforma scenarios made here (OF-BLD-019 D6), keyed by id. */
  createdScenarios?: Record<string, Scenario>;
  /** LEGACY, read once: pureOS's trains built here (OF-BLD-020 §5.3), by train id. */
  trainsMade?: Record<string, TrainMade>;
}

/**
 * What Guild's ledger owes the service in one project: `ledger` holds the
 * people and entries made while the service was away (since alpha 2.0, those
 * alone; the ledger itself loads from the service), `pending` their ids,
 * `withdrawals` the withdrawals not yet sent, and `actingId` the person the
 * page acts as there.
 */
export interface GuildOwed {
  ledger: Guild;
  pending: string[];
  withdrawals: GuildWithdrawal[];
  actingId: string | null;
}

/**
 * A train built in pureOS's Builder and saved (OF-BLD-020 §5.3): one of the project's rows, the service's `TrainMade`
 * generated from its model (ADR-007). It holds the train as data, every value typed into its panels laid in as each
 * place's params; when it was saved, ISO, UTC; and the reviewer name it was saved under.
 */
export type TrainMade = components['schemas']['TrainMade'];

/**
 * A value a named person typed for one input of a Proforma scenario, with its range (OF-BLD-014 §8.4): the browser's
 * own shape, as a snapshot written before the parameter panel keeps it (`proformaAssumptions`, read once into the
 * scenario's overrides, each a person's assumption), and as the store reads a `proforma:` scope's numeric overrides
 * (`assumptionsFromOverrides`).
 */
export interface ScenarioAssumption {
  key: string;
  value: number;
  low: number;
  high: number;
  by: string;
  at: string;
  note: string | null;
}

export const EMPTY_SNAPSHOT: DurableSnapshot = {
  version: 1,
  savedAt: '',
  reviewDecisions: {},
  reviewerName: '',
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
      req.onsuccess = () => {
        opened = req.result;
        done(req.result);
      };
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

// ── Every tab of this browser writes the one snapshot ─────────────────
//
// Each tab keeps its own copy of the writes it owes the service, and every tab
// of this browser saves under the one key. So a save merges (H7-01, the bug
// hunt of November 2026): it keeps what this tab owes now, and from the
// snapshot already stored it keeps every owed write this tab has never held,
// which is another tab's. A tab that saves last leaves the others' writes in
// place. A write this tab held and no longer holds was answered by the service
// or replaced by this tab's later write of the same row, so the merge leaves it
// out. Two writes of one row from tabs that never saw each other's both stay,
// oldest first, so a page that sends from the merged snapshot puts them to the
// service in order; tabs still open send their own queues each on its own
// retry, in the order they come. A page that loads takes the whole outbox and
// the open project's Guild block at once (the store's `applyDurable`), beside
// the tab that queued them, and both may send a write: a row the service keeps
// whole takes it twice to the same end, and a second lock, a second withdrawal
// or a second Guild entry is refused, which the page that sent it second shows.
// The read and the write run in one IndexedDB transaction, and the browser runs
// two tabs' transactions on one store one after the other.

/** The owed writes a tab has held, each by what names it. */
export interface Held {
  outbox: Set<string>;
  decisions: Set<string>;
  guild: Set<string>;
  withdrawals: Set<string>;
  /** Whether this page took the snapshot's legacy Guild block as its own. */
  legacyGuild: boolean;
}

export function emptyHeld(): Held {
  return { outbox: new Set(), decisions: new Set(), guild: new Set(), withdrawals: new Set(), legacyGuild: false };
}

const entryOf = (e: OutboxEntry) => `${e.project}\u0000${e.kind}\u0000${e.id}\u0000${e.at}`;
const decisionOf = (key: string, at: string | undefined) => `${key}\u0000${at ?? ''}`;

/**
 * A review decision's key in the snapshot: its project and its record, so one
 * project's decision on a record never stands in for another project's on a
 * record of the same id (record ids are made from a paper and its words, and
 * one paper may be held by two projects). Without a project, the record alone.
 */
export function decisionKey(project: string | null | undefined, recordId: string): string {
  return project ? `${project}\u0000${recordId}` : recordId;
}

/**
 * The decisions a snapshot holds for `project`, by record id: the project's own,
 * and those saved before decisions named their project, which a page reads as
 * its own; of two on one record, the later.
 */
export function decisionsIn(snapshot: DurableSnapshot, project: string | null): Record<string, DurableReviewDecision> {
  const out: Record<string, DurableReviewDecision> = {};
  const when = (d: DurableReviewDecision) => d.at ?? snapshot.savedAt;
  for (const [key, d] of Object.entries(snapshot.reviewDecisions ?? {})) {
    if (d.project && d.project !== project) continue;
    const id = d.recordId ?? key;
    const was = out[id];
    if (!was || when(was) < when(d)) out[id] = d;
  }
  return out;
}
/** A withdrawal by every field it carries: two of one entry on one day by two people are two writes. */
const withdrawalOf = (project: string, w: GuildWithdrawal) =>
  `${project}\u0000${w.evidenceId}\u0000${w.at}\u0000${w.by}\u0000${w.reason}`;
/**
 * An owed Guild write by its project, its id and, for a person, the time of the
 * write itself: a person's id comes from the name, so two changes of one person
 * are two writes. An entry's id is new with each entry.
 */
function owedOf(project: string, id: string, ledger: Guild): string {
  const person = ledger.people.find((p) => p.id === id);
  return `${project}\u0000${id}\u0000${person ? (person.updatedAt ?? person.addedAt) : ''}`;
}

function holdGuild(held: Held, project: string, owed: GuildOwed): void {
  for (const id of owed.pending) held.guild.add(owedOf(project, id, owed.ledger));
  for (const w of owed.withdrawals) held.withdrawals.add(withdrawalOf(project, w));
}

/**
 * The Guild writes a snapshot owes in `project`: its block for the project,
 * with a legacy block (written before the blocks were kept by project) laid
 * beside it, as the open project's.
 */
export function owedGuild(snapshot: DurableSnapshot, project: string | null): GuildOwed | undefined {
  if (!project) return undefined;
  const block = snapshot.guildOwed?.[project];
  const legacy = snapshot.guild;
  if (!legacy) return block;
  if (!block) return legacy;
  const people = new Set(block.ledger.people.map((p) => p.id));
  const evidence = new Set(block.ledger.evidence.map((x) => x.id));
  const withdrawn = new Set(block.withdrawals.map((w) => withdrawalOf(project, w)));
  return {
    ...block,
    ledger: {
      ...block.ledger,
      people: [...block.ledger.people, ...legacy.ledger.people.filter((p) => !people.has(p.id))],
      evidence: [...block.ledger.evidence, ...legacy.ledger.evidence.filter((x) => !evidence.has(x.id))],
    },
    pending: [...block.pending, ...legacy.pending.filter((id) => !block.pending.includes(id))],
    withdrawals: [...block.withdrawals, ...legacy.withdrawals.filter((w) => !withdrawn.has(withdrawalOf(project, w)))],
  };
}

/** Add every owed write of a snapshot this tab saves to `held`. */
export function hold(held: Held, snapshot: DurableSnapshot): void {
  for (const e of snapshot.outbox ?? []) held.outbox.add(entryOf(e));
  for (const [key, d] of Object.entries(snapshot.reviewDecisions)) {
    held.decisions.add(decisionOf(key, d.at));
    // The same decision as a snapshot from before decisions were keyed by project kept it, by its record alone.
    if (d.recordId) held.decisions.add(decisionOf(d.recordId, d.at));
  }
  for (const [project, owed] of Object.entries(snapshot.guildOwed ?? {})) holdGuild(held, project, owed);
}

/**
 * Add what a page takes as its own from a loaded snapshot to `held`: the whole
 * outbox, and Guild's owed writes in the project it has open (`owedGuild`). Its
 * review decisions count as held once a snapshot the page saves carries them
 * (a page re-applies a decision only to the records it has loaded), or once
 * the service is found to hold them (`holdDecision`).
 */
export function holdLoaded(held: Held, snapshot: DurableSnapshot, project: string | null): void {
  for (const e of snapshot.outbox ?? []) held.outbox.add(entryOf(e));
  const owed = owedGuild(snapshot, project);
  if (owed && project) holdGuild(held, project, owed);
  if (snapshot.guild && project) held.legacyGuild = true;
}

/**
 * Merge one project's Guild block: this tab's, with every owed write of the
 * stored block it has never held.
 */
function mergeGuild(project: string, own: GuildOwed, stored: GuildOwed | undefined, held: Held): GuildOwed {
  if (!stored) return own;
  const owedHere = new Set(own.pending);
  const owedThere = stored.pending.filter((id) => !held.guild.has(owedOf(project, id, stored.ledger)) && !owedHere.has(id));
  const there = new Set(owedThere);
  const people = new Set(own.ledger.people.map((p) => p.id));
  const evidence = new Set(own.ledger.evidence.map((x) => x.id));
  const withdrawn = new Set(own.withdrawals.map((w) => withdrawalOf(project, w)));
  // A person both blocks owe: another tab's change this tab never held stands when it is the later.
  const when = (p: GuildPerson) => p.updatedAt ?? p.addedAt;
  const laterThere = new Map(
    stored.ledger.people
      .filter((p) => owedHere.has(p.id) && stored.pending.includes(p.id) && !held.guild.has(owedOf(project, p.id, stored.ledger)))
      .map((p) => [p.id, p]),
  );
  const settled = (p: GuildPerson) => {
    const q = laterThere.get(p.id);
    return q && when(q) > when(p) ? q : p;
  };
  return {
    ...own,
    ledger: {
      ...own.ledger,
      people: [...own.ledger.people.map(settled), ...stored.ledger.people.filter((p) => there.has(p.id) && !people.has(p.id))],
      evidence: [...own.ledger.evidence, ...stored.ledger.evidence.filter((x) => there.has(x.id) && !evidence.has(x.id))],
    },
    pending: [...own.pending, ...owedThere],
    withdrawals: [
      ...own.withdrawals,
      ...stored.withdrawals.filter((w) => !held.withdrawals.has(withdrawalOf(project, w)) && !withdrawn.has(withdrawalOf(project, w))),
    ],
  };
}

/**
 * The snapshot a tab writes: `mine`, what it owes now, with every owed write of
 * `stored` that it has never `held` laid beside it. The outbox runs oldest
 * first. Of two decisions under one key (`decisionKey`: a project and a
 * record) the later stands. A project's Guild block that `mine` does not carry,
 * another project's, stays as stored.
 */
export function mergeSnapshot(mine: DurableSnapshot, stored: DurableSnapshot | null, held: Held): DurableSnapshot {
  if (!stored) return mine;
  const theirs = (stored.outbox ?? []).filter((e) => !held.outbox.has(entryOf(e)));
  const outbox = [...(mine.outbox ?? []), ...theirs].sort((a, b) => (a.at < b.at ? -1 : a.at > b.at ? 1 : 0));

  // By project and record: of two decisions under one key, the later stands.
  const reviewDecisions = { ...mine.reviewDecisions };
  for (const [key, was] of Object.entries(stored.reviewDecisions ?? {})) {
    if (held.decisions.has(decisionOf(key, was.at))) continue;
    // A decision from before decisions carried their own time keeps its snapshot's.
    const d = was.at ? was : { ...was, at: stored.savedAt };
    if (held.decisions.has(decisionOf(key, d.at))) continue;
    const own = reviewDecisions[key];
    if (!own || (own.at ?? '') < (d.at ?? '')) reviewDecisions[key] = d;
  }

  const guildOwed: Record<string, GuildOwed> = { ...(stored.guildOwed ?? {}) };
  for (const [project, own] of Object.entries(mine.guildOwed ?? {}))
    guildOwed[project] = mergeGuild(project, own, stored.guildOwed?.[project], held);
  const { guild: _legacy, ...rest } = mine;
  return {
    ...rest,
    reviewDecisions,
    outbox,
    guildOwed,
    // The legacy block stays until the page that took it as its own saves.
    ...(stored.guild && !held.legacyGuild ? { guild: stored.guild } : {}),
  };
}

/** What this tab has held, for every save it makes. */
let held = emptyHeld();
/** The database once open, so a save made as the tab goes away places its write with no wait. */
let opened: IDBDatabase | null = null;

// ── A tab going away ──────────────────────────────────────────────────
//
// A page that is closing or reloading runs no event after its own, so a save
// made then cannot read the snapshot before it writes. It writes what the tab
// owes, and what it has held, under a key of its own (`parting:` and the tab's
// id), which no other tab writes, so the write erases nothing of theirs; a tab
// whose last save has landed writes nothing. The next page to load folds every
// such record into the snapshot and deletes it (`foldParting`): the owed writes
// as the tab's own save would have merged them, the rest from whichever was
// saved later. A tab that lives on (the back-forward cache) deletes its own on
// its next save.

const PARTING = 'parting:';

function tabId(): string {
  try {
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') return crypto.randomUUID();
  } catch {
    /* below */
  }
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
}

/** This tab's key for what it leaves as it goes. */
const TAB = `${PARTING}${tabId()}`;

/** What a tab leaves as it goes: its last snapshot and the owed writes it had held. */
export interface Parting {
  version: 1;
  snapshot: DurableSnapshot;
  held: { outbox: string[]; decisions: string[]; guild: string[]; withdrawals: string[]; legacyGuild: boolean };
}

export function partingOf(snapshot: DurableSnapshot, h: Held): Parting {
  return {
    version: 1,
    snapshot,
    held: { outbox: [...h.outbox], decisions: [...h.decisions], guild: [...h.guild], withdrawals: [...h.withdrawals], legacyGuild: h.legacyGuild },
  };
}

function asParting(v: unknown): Parting | null {
  const p = v as Parting | undefined;
  if (!p || p.version !== 1 || !asSnapshot(p.snapshot) || !p.held) return null;
  const list = (x: unknown) => (Array.isArray(x) ? x.filter((y): y is string => typeof y === 'string') : []);
  return {
    version: 1,
    snapshot: p.snapshot,
    held: { outbox: list(p.held.outbox), decisions: list(p.held.decisions), guild: list(p.held.guild), withdrawals: list(p.held.withdrawals), legacyGuild: p.held.legacyGuild === true },
  };
}

/**
 * The snapshot with each parting tab's last save laid in, oldest first: the
 * writes the tab owed, with every owed write of the snapshot it had never held,
 * as the tab's own save would have merged them. What a save takes whole (who
 * is reviewing, the person acted as in each project, the rows kept before
 * alpha 2.0) comes from whichever of the two was saved later, so a closed
 * tab's older choice never stands over a later one saved since.
 */
export function foldParting(main: DurableSnapshot | null, parting: Parting[]): DurableSnapshot | null {
  let folded = main;
  const inOrder = [...parting].sort((a, b) => (a.snapshot.savedAt < b.snapshot.savedAt ? -1 : a.snapshot.savedAt > b.snapshot.savedAt ? 1 : 0));
  for (const p of inOrder) {
    const h: Held = {
      outbox: new Set(p.held.outbox),
      decisions: new Set(p.held.decisions),
      guild: new Set(p.held.guild),
      withdrawals: new Set(p.held.withdrawals),
      legacyGuild: p.held.legacyGuild,
    };
    const merged = mergeSnapshot(p.snapshot, folded, h);
    folded = folded && folded.savedAt > p.snapshot.savedAt ? owedOver(folded, merged) : merged;
  }
  return folded;
}

/** `later` whole, with the owed writes of `merged` laid in, each Guild block keeping `later`'s acting person. */
function owedOver(later: DurableSnapshot, merged: DurableSnapshot): DurableSnapshot {
  const guildOwed: Record<string, GuildOwed> = {};
  for (const [project, block] of Object.entries(merged.guildOwed ?? {})) {
    const there = later.guildOwed?.[project];
    guildOwed[project] = there ? { ...block, actingId: there.actingId } : block;
  }
  const { guild: _legacy, ...rest } = later;
  return {
    ...rest,
    reviewDecisions: merged.reviewDecisions,
    outbox: merged.outbox,
    guildOwed,
    ...(merged.guild ? { guild: merged.guild } : {}),
  };
}

/**
 * Count a loaded review decision as held once the service is found to hold
 * it, or a later one, so the next save leaves it out. `savedAt` is the loaded
 * snapshot's time, which a decision from before decisions carried their own
 * time stands on.
 */
export function holdDecision(recordId: string, d: DurableReviewDecision, savedAt: string): void {
  for (const key of [decisionKey(d.project, recordId), recordId]) {
    held.decisions.add(decisionOf(key, d.at));
    held.decisions.add(decisionOf(key, d.at ?? savedAt));
  }
}

/** A stored value as a snapshot: one of an older shape is discarded rather than migrated on a guess. */
function asSnapshot(v: unknown): DurableSnapshot | null {
  const snapshot = v as DurableSnapshot | undefined;
  return snapshot && snapshot.version === 1 ? snapshot : null;
}

/**
 * The stored snapshot, or null when there is none or it cannot be read. The
 * page takes its outbox and Guild's owed writes in `project` as its own (the
 * store's `applyDurable`), so they count as held from here (`holdLoaded`).
 */
export async function loadDurable(project: string | null): Promise<DurableSnapshot | null> {
  const db = await openDb();
  if (!db) return null;
  return new Promise((resolve) => {
    let done = false;
    // The page takes a snapshot as its own once the transaction that read it has ended: the fold only when its
    // write-back and its deletes committed, else the snapshot as stored, and the parting records stay.
    const take = (snapshot: DurableSnapshot | null) => {
      if (done) return;
      done = true;
      if (snapshot) holdLoaded(held, snapshot, project);
      resolve(snapshot);
    };
    try {
      // One transaction: the snapshot and what parting tabs left are read, folded, written back and let go together.
      const tx = db.transaction(STORE, 'readwrite');
      const store = tx.objectStore(STORE);
      const range = IDBKeyRange.bound(PARTING, `${PARTING}\uffff`);
      const main = store.get(KEY);
      const left = store.getAll(range);
      const keys = store.getAllKeys(range);
      let read = 0;
      let partingRead = true;
      let stored: DurableSnapshot | null = null;
      let folded: DurableSnapshot | null = null;
      const settle = () => {
        if (++read < 3 || done) return;
        // Losing a session's depositions is bad; silently reinterpreting them
        // as a shape they were never written in is worse.
        stored = asSnapshot(main.result);
        const parting = partingRead ? ((left.result as unknown[]) ?? []).map(asParting).filter((p): p is Parting => p !== null) : [];
        if (!partingRead || !(keys.result ?? []).length) return;
        try {
          // What parting tabs left is let go in the transaction that writes it into the snapshot.
          const next = foldParting(stored, parting);
          if (parting.length && next) store.put(next, KEY);
          for (const k of keys.result ?? []) store.delete(k);
          folded = next;
        } catch {
          // As in a save: the page runs on the snapshot as stored, and the parting records stay for the next load.
          folded = null;
        }
      };
      main.onsuccess = settle;
      left.onsuccess = settle;
      keys.onsuccess = settle;
      main.onerror = () => take(null);
      // What parting tabs left cannot be read: the snapshot alone is read, and their records stay.
      const unread = (ev: Event) => {
        ev.preventDefault();
        partingRead = false;
        settle();
      };
      left.onerror = unread;
      keys.onerror = unread;
      tx.oncomplete = () => take(folded ?? stored);
      // The write-back failed (a full store, say) and the transaction rolled back: the snapshot as stored.
      tx.onabort = () => take(stored);
    } catch {
      take(null);
    }
  });
}

let pending: DurableSnapshot | null = null;
let timer: ReturnType<typeof setTimeout> | null = null;
/** The last snapshot this tab saved, which it leaves as it goes. */
let latest: DurableSnapshot | null = null;
/** The last snapshot this tab's save wrote and saw committed: a tab going away with nothing newer leaves nothing. */
let landed: DurableSnapshot | null = null;

async function flush(): Promise<void> {
  const snapshot = pending;
  pending = null;
  timer = null;
  if (!snapshot) return;
  const db = opened ?? (await openDb());
  if (!db) return;
  try {
    const tx = db.transaction(STORE, 'readwrite');
    tx.oncomplete = () => {
      landed = snapshot;
    };
    const store = tx.objectStore(STORE);
    const req = store.get(KEY);
    req.onsuccess = () => {
      try {
        store.put(mergeSnapshot(snapshot, asSnapshot(req.result), held), KEY);
        // What this tab left as it went once (the back-forward cache) is in the snapshot written now.
        store.delete(TAB);
      } catch {
        // As below: the app keeps running on memory.
      }
    };
    // A stored value this browser cannot read back: keep the read's error from
    // ending the transaction, and write this tab's snapshot over it, as a save
    // did before saves merged.
    req.onerror = (ev) => {
      ev.preventDefault();
      try {
        store.put(snapshot, KEY);
        store.delete(TAB);
      } catch {
        // As below: the app keeps running on memory.
      }
    };
  } catch {
    // Quota exceeded, or the store went away mid-session. The app keeps
    // running on memory; the next successful write catches up.
  }
}

/**
 * Queue a write. Coalesced on a short timer because a running deposition
 * mutates on every keystroke and every timer tick, and writing each one
 * through would put IndexedDB traffic in the way of the bench. Every owed write
 * the snapshot carries counts as held by this tab from here.
 */
export function saveDurable(snapshot: DurableSnapshot): void {
  if (!durableAvailable()) return;
  hold(held, snapshot);
  pending = snapshot;
  latest = snapshot;
  if (timer) return;
  timer = setTimeout(() => void flush(), 400);
}

/**
 * Write now — used when the tab is going away (`pagehide`). A closing page runs
 * no event after its own, so this write cannot wait on a read: it puts the
 * tab's last snapshot and what it has held under the tab's own key, in this
 * task, with the database the page already opened, and the browser commits it
 * as the page goes. The next page to load folds it into the snapshot
 * (`loadDurable`, `foldParting`). A page that goes before its database has
 * opened leaves nothing.
 */
export function flushDurable(): void {
  if (timer) {
    clearTimeout(timer);
    timer = null;
  }
  pending = null;
  if (!latest || !opened || latest === landed) return;
  try {
    const tx = opened.transaction(STORE, 'readwrite');
    tx.objectStore(STORE).put(partingOf(latest, held), TAB);
    // Commit now, so the write does not wait on an event the closing page will not run.
    tx.commit?.();
  } catch {
    // Quota exceeded, or the store went away: the page goes with what was stored last.
  }
}

/** Drop everything persisted. Used by "Clear this browser’s data", which must truly clear. */
export async function clearDurable(): Promise<void> {
  pending = null;
  latest = null;
  landed = null;
  held = emptyHeld();
  if (timer) {
    clearTimeout(timer);
    timer = null;
  }
  const db = await openDb();
  if (!db) return;
  try {
    // The snapshot and whatever parting tabs left, every record this browser keeps here.
    const tx = db.transaction(STORE, 'readwrite');
    tx.objectStore(STORE).clear();
  } catch {
    /* nothing to do — the caller cannot act on this either */
  }
}

// ── The last-open project (alpha 2.0, ADR-005) ─────────────────────────
//
// One id, the project this browser last opened. It is read synchronously at
// load, so the first call to the service already names it, which is why it
// lives in localStorage beside the IndexedDB snapshot. Like everything here,
// a failure reads as none.
const PROJECT_KEY = 'openferment.project';

export function lastProject(): string | null {
  try {
    return typeof localStorage === 'undefined' ? null : localStorage.getItem(PROJECT_KEY) || null;
  } catch {
    return null;
  }
}

export function rememberProject(id: string | null): void {
  try {
    if (typeof localStorage === 'undefined') return;
    if (id) localStorage.setItem(PROJECT_KEY, id);
    else localStorage.removeItem(PROJECT_KEY);
  } catch {
    /* the open project is then this page's alone */
  }
}
