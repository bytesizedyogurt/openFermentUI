/**
 * What a project keeps of its pages, on the browser's side (alpha 2.0, stage
 * 2; src/lib/projectState.ts): the writes a change makes, the outbox they
 * wait in, the rows laid over a load, and a flush that drops a refusal and
 * keeps everything from the first write the service did not answer; and the
 * overlay a project's pages load (src/lib/intake.ts), where a service that
 * answers and refuses is running and says why, and a candidate it brings
 * enters the store as a record when the ontology names its field
 * (src/lib/review.ts, `recordOf`); the configurations a plant
 * is offered in (src/lib/library.ts), and those a thing of another engine is
 * offered in on Studies' run card, each by the engine's title for it beside
 * its name (src/lib/studies.ts, `offeredConfigurations`), as the card's line
 * for the run it made names it (src/lib/pureos.ts, `ranWhat`; alpha 2.2
 * E.18); the refusals an SFF import answers
 * in the service's words (src/lib/http.ts), a refusal of a request's own
 * fields among them; and the unit each person's change is sent in
 * (src/lib/params.ts, `inputsOf`), a panel that shows part of its scope
 * among them, a deposition's reading sent as the reading it names, in its own
 * value and unit where its row keeps them (alpha 2.2 E.17), and a change kept
 * with no origin sent as a person's assumption; the
 * bench's readings as the service's lookup reads them (src/engine/readings.ts:
 * a correction, the numbers that wait to be read back, a series); a
 * train's changes named by their place (src/lib/pureos.ts,
 * `trainInputs`), a Proforma scenario's run carrying its changes as typed
 * inputs (src/lib/proforma.ts, `runBody`) and its ceiling check its typed
 * yield (`ceilingQuery`), a reading among them in its own value and unit, the
 * scenario page's binding with a person's value and a reading laid on
 * (`laidOn`) and the questions it asks (`modellerQuestions`), the Proforma
 * assumptions an older build reads holding a person's values alone
 * (src/store.ts, `assumptionOfOverride`), a scenario card's counts (`inputCounts`, an input
 * the vessel design binds apart from a chosen fit), the reference run a
 * plant's page reads in its default configuration (`referenceRunOf`) and the
 * runs kept from the retired reference entries it lists (`keptRunsOf`), and a
 * run's grid read where it holds a dimension at one value
 * (src/engine/interp.ts); and the runbooks a page makes (src/store.ts): a
 * draft's predictions and measures kept as the service wrote them, the lock
 * taken over them, and a runbook adopted, revised or promoted on the page
 * among the rows the page sends; and the words every screen, component and
 * module shows, which put a project's rows with the service and keep in this
 * browser its preferences and the writes that wait for the service (ADR-014;
 * alpha 2.2 E.19). Run by `pnpm check:state`, offline: the
 * service is a stand-in for `fetch`. A fixture of a shape the service's
 * models define is a whole value of its generated type (src/api/types.gen.ts).
 */
import { readdirSync, readFileSync } from 'node:fs';
import { join, relative } from 'node:path';
import ts from 'typescript';
import {
  EMPTY_STATE,
  applyEntries,
  changes,
  conversationsHeld,
  enqueue,
  flush,
  type OutboxEntry,
  type ProjectState,
} from '../src/lib/projectState';
import type { Override, ParameterSpec } from '../src/lib/params';
import type { LiveConversation, RunbookDraft } from '../src/lib/postdoc';
import type { FlowsheetInfo, ProformaScenarioInfo, Scenario, ScenarioInput } from '../src/lib/proforma';
import type { Artifact, BasisSource, Deposition, EngineRun, EngineThing, Prediction } from '../src/lib/studies';
import { offeredConfigurations } from '../src/lib/studies';
import { loadOverlay } from '../src/lib/intake';
import { recordOf, type Candidate } from '../src/lib/review';
import { ONTOLOGY } from '../src/data/ontology';
import { bodyWords, edited, type CatalogueEntry } from '../src/lib/catalogues';
import { ServiceDown, ServiceRefused, call, detailWords } from '../src/lib/http';
import { runnable, type LibraryPlant } from '../src/lib/library';
import { inputsOf, readingLeftTheList } from '../src/lib/params';
import { ranWhat, trainInputs, unitScope, type TrainSpec } from '../src/lib/pureos';
import {
  ceilingQuery,
  inputCounts,
  isReading,
  keptRunsOf,
  laidOn,
  modellerQuestions,
  readBackRows,
  referenceRunOf,
  retiredEntryOf,
  runBody,
  plainNote,
  runSpecs,
  stampsIn,
} from '../src/lib/proforma';
import { RAIL } from '../src/data/nav';
import { COMPONENTS } from '../src/data/components';
import { stubsFor, type SubsystemOwner } from '../src/data/subsystems';
import { idTail, shortCite } from '../src/lib/cite';
import { fmt } from '../src/engine/units';
import { interpolate } from '../src/engine/interp';
import { awaitingReadBack, correctedBy, correctionOf } from '../src/engine/readings';
import { lockIntact, runbookLockHash } from '../src/engine/lock';
import { assumptionOfOverride, projectStateOf, useStore } from '../src/store';
import {
  EMPTY_SNAPSHOT,
  emptyHeld,
  hold,
  holdLoaded,
  mergeSnapshot,
  owedGuild,
  type DurableReviewDecision,
  type DurableSnapshot,
  type GuildOwed,
} from '../src/lib/durable';
import type { Guild, GuildWithdrawal } from '../src/lib/guild';

let fails = 0;
const check = (label: string, ok: boolean, extra = '') => {
  console.log((ok ? '✓' : '✗') + ' ' + label + (extra ? '  ' + extra : ''));
  if (!ok) fails++;
};

// ── whole values of the service's shapes (src/api/types.gen.ts) ────────
// A fixture of a shape the service's models define is a whole value of its
// generated type, each field a placeholder, so the typecheck holds every
// fixture to the service's shape; a check reads the fields it names.

const AT = '2026-11-03T00:00:00Z';
const aScenario = (id: string, more: Partial<Scenario> = {}): Scenario => ({
  id, modelId: 'placeholder-flowsheet', kind: 'biosteam', name: 'S', description: '', product: '', pinned: false, ...more,
});
const aSpec = (key: string, unit: string, group = 'parameters'): ParameterSpec => ({
  key, label: key, symbol: '', gloss: '', dimension: '', unit, min: null, max: null, step: null, scale: 'linear', group,
  sourceRule: ['assumption'], note: null, boundsReason: 'a placeholder bound', choices: null, convention: null,
});
const anOverride = (scope: string, key: string, value: number | string, more: Partial<Override> = {}): Override => ({
  scope, key, value, by: 'Ada', at: AT, origin: 'person-assumption', ...more,
});
const aShelfInput = (key: string, unit: string): FlowsheetInfo['inputs'][number] => ({ key, name: key, unit, dimension: '', kind: 'process', fields: [], note: '' });
const aFlowsheet = (inputs: FlowsheetInfo['inputs']): FlowsheetInfo => ({
  id: 'placeholder-flowsheet', title: 'A placeholder flowsheet', description: '', source: '', inputs, outputs: [], gridInputs: [],
  leavesOut: [], priceBasis: null, priceOutput: null, program: null, brothStream: null, builtFrom: [],
});
const aConversation = (id: string): LiveConversation => ({ id, title: 'A placeholder conversation', startedAt: AT, turns: [] });
const aDeposition = (id: string, more: Partial<Deposition> = {}): Deposition => ({
  id, runbookId: 'rb-1', protocolId: null, operatorId: null, startedAt: AT, closedAt: null, state: 'running', entries: [],
  observations: [], reconciliation: null, ...more,
});

const dep = aDeposition('dep-1');
const scenario = aScenario('sc-1');
const talk = aConversation('lc-1');
const before: ProjectState = { ...EMPTY_STATE, depositions: [dep], scenarios: [scenario], conversations: [talk], fits: { 'sc-1': { mu: 'a'.repeat(16) } } };

// ── changes ────────────────────────────────────────────────────────────

check('nothing changed is nothing to send', changes(before, { ...before }, 'p', 'Ada').length === 0);
const moved: Deposition = { ...dep, state: 'closed', closedAt: AT };
const pinned: Scenario = { ...scenario, pinned: true };
const after: ProjectState = { ...before, depositions: [moved], scenarios: [pinned], fits: {} };
const sent = changes(before, after, 'p', 'Ada');
check(
  'a changed row is written whole and a row taken back is sent as nothing',
  JSON.stringify(sent.map((e) => [e.kind, e.id, e.value === null])) ===
    JSON.stringify([['depositions', 'dep-1', false], ['fits', 'sc-1', true], ['scenarios', 'sc-1', false]]),
  JSON.stringify(sent.map((e) => [e.kind, e.id, e.value === null])),
);
check('each write names its project and its signer', sent.every((e) => e.project === 'p' && e.by === 'Ada'));
const gone = changes(before, { ...before, depositions: [], conversations: [] }, 'p', 'Ada');
check('a deposition and a conversation that leave the page are never taken back', gone.length === 0, JSON.stringify(gone));

// ── the conversations a page holds (alpha 2.1 stage F) ─────────────────
// The service lists a project's conversations oldest first; the page held only
// the 30 newest, so stage C's 31 evaluation runs left every earlier answer
// unreachable, and a link to one opened an empty pane.

const kept = Array.from({ length: 51 }, (_, i) => aConversation(`lc-${i}`));
const begun = aConversation('lc-new');
const held = conversationsHeld(kept, [begun]);
check(
  'every conversation the service keeps is held, newest first, after those the page began: a link to the oldest finds it',
  held.length === 52 && held[0] === begun && held[1].id === 'lc-50' && held[51].id === 'lc-0',
  JSON.stringify([held.length, held[0]?.id, held[1]?.id, held[held.length - 1]?.id]),
);
check('a conversation the page began and the service also keeps is held once', conversationsHeld([begun, ...kept], [begun]).length === 52);

// ── the outbox ─────────────────────────────────────────────────────────

const e = (id: string, value: unknown, project = 'p'): OutboxEntry => ({ project, kind: 'scenarios', id, value, by: 'Ada', at: '' });
const queued = enqueue([e('sc-1', 1), e('sc-2', 2)], [e('sc-1', 3)]);
check('a later write of a row replaces the one still unsent, and goes last', JSON.stringify(queued.map((x) => [x.id, x.value])) === '[["sc-2",2],["sc-1",3]]');
check('the same row in another project is another write', enqueue([e('sc-1', 1, 'a')], [e('sc-1', 2, 'b')]).length === 2);
const laid = applyEntries(before, [{ ...e('sc-1', null) }, { ...e('sc-9', pinned) }]);
check('an owed write is laid over the loaded rows, a take-back removes', laid.scenarios.length === 1 && laid.scenarios[0] === pinned);
const answered = { ...before, depositedBy: { 'dep-1': 'Ada' }, refused: [{ kind: 'runbooks', id: 'rb-old', why: 'a placeholder reason' }] };
const answeredLaid = applyEntries(answered, [e('sc-9', pinned)]);
check(
  'what the service answers beside the rows, who deposited each deposition and the rows it cannot read, stays as it answered',
  answeredLaid.depositedBy === answered.depositedBy && answeredLaid.refused === answered.refused && EMPTY_STATE.refused.length === 0,
);

// ── the flush ──────────────────────────────────────────────────────────

type Answer = { status: number; body?: unknown } | 'down';
async function flushAgainst(answers: Answer[], outbox: OutboxEntry[]) {
  const asked: string[] = [];
  const real = globalThis.fetch;
  globalThis.fetch = (async (url: string, init?: RequestInit) => {
    asked.push(`${init?.method} ${url} ${new Headers(init?.headers).get('X-OpenFerment-Project')}`);
    const next = answers.shift() ?? { status: 200, body: {} };
    if (next === 'down') throw new TypeError('fetch failed');
    return new Response(JSON.stringify(next.body ?? { detail: 'refused in words' }), { status: next.status });
  }) as typeof fetch;
  try {
    return { result: await flush(outbox), asked };
  } finally {
    globalThis.fetch = real;
  }
}

const three = [e('sc-1', { id: 'sc-1' }), e('sc-2', null, 'q'), e('sc-3', { id: 'sc-3' })];
{
  const { result, asked } = await flushAgainst([{ status: 200 }, { status: 200 }, { status: 200 }], three);
  check('every row is sent in order, each naming its own project', result.left.length === 0 && result.sent === 3 &&
    asked[0] === 'PUT /api/state/scenarios/sc-1 p' && asked[1] === 'DELETE /api/state/scenarios/sc-2?by=Ada q', asked.join('; '));
}
{
  const { result } = await flushAgainst([{ status: 422, body: { detail: 'not a row' } }, { status: 200 }, { status: 200 }], three);
  check('a refusal is the service answering: dropped with its words, and the rest go', result.left.length === 0 &&
    result.refused.length === 1 && result.refused[0].why === 'not a row' && result.sent === 2);
}
{
  const { result } = await flushAgainst([{ status: 200 }, 'down'], three);
  check('a service that does not answer stops the flush, and everything from there stays', result.sent === 1 &&
    result.left.length === 2 && result.left[0] === three[1], `${result.left.length} left`);
}

// ── the browser's one snapshot, two tabs (H7-01) ──────────────────────
//
// Two tabs on one project while the service is away, each saving under the one key every tab shares
// (src/lib/durable.ts). A save merges: what the tab owes now, beside every owed write in the stored snapshot it has
// never held.
{
  const at = (n: number) => `2026-11-11T10:00:0${n}.000Z`;
  const deposition = (id: string, reading: string, n: number): OutboxEntry =>
    ({ project: 'p', kind: 'depositions', id, value: { id, entries: [reading] }, by: 'Ada', at: at(n) });
  const snap = (outbox: OutboxEntry[], extra: Partial<DurableSnapshot> = {}): DurableSnapshot =>
    ({ ...EMPTY_SNAPSHOT, savedAt: at(9), outbox, ...extra });
  const save = (held: ReturnType<typeof emptyHeld>, mine: DurableSnapshot, stored: DurableSnapshot | null) => {
    hold(held, mine);
    return mergeSnapshot(mine, stored, held);
  };
  const ids = (x: DurableSnapshot) => JSON.stringify((x.outbox ?? []).map((e) => `${e.id}@${e.at.slice(18, 19)}`));
  const tabA = emptyHeld();
  const tabB = emptyHeld();
  const fromA = deposition('dep-a', '5.5 USD/kg', 1);
  const fromB = deposition('dep-b', '6.6 USD/kg', 2);
  let stored = save(tabA, snap([fromA]), null);
  stored = save(tabB, snap([fromB]), stored);
  check('a tab that saves last keeps the other tab’s queued write beside its own, oldest first', ids(stored) === '["dep-a@1","dep-b@2"]', ids(stored));
  {
    const { result, asked } = await flushAgainst([{ status: 200 }, { status: 200 }], stored.outbox ?? []);
    check('once both tabs have closed, the page that opens next sends both tabs’ writes', result.sent === 2 &&
      asked[0] === 'PUT /api/state/depositions/dep-a p' && asked[1] === 'PUT /api/state/depositions/dep-b p', asked.join('; '));
  }
  const afterAnswer = save(tabA, snap([]), stored);
  check('a write the tab held and the service answered leaves the store, and the other tab’s stays', ids(afterAnswer) === '["dep-b@2"]', ids(afterAnswer));
  const againB = save(tabB, snap([fromB]), afterAnswer);
  check('a tab that saves again over its own earlier save keeps the write it still owes, once', ids(againB) === '["dep-b@2"]', ids(againB));
  const later = deposition('dep-a', '7.7 USD/kg', 3);
  const rewritten = save(tabB, snap([fromB, later]), stored);
  check('two writes of one row from tabs that never saw each other’s both stay, oldest first, for the service to rule on in order',
    ids(rewritten) === '["dep-a@1","dep-b@2","dep-a@3"]', ids(rewritten));
  const olderMine = save(tabA, snap([fromA]), rewritten);
  check('a stored write later than the tab’s own write of the row stays beside it, oldest first',
    ids(olderMine) === '["dep-a@1","dep-b@2","dep-a@3"]' && (olderMine.outbox ?? [])[2] === later, ids(olderMine));
  {
    // A page that loads the snapshot takes its writes as its own, then writes the row again: its later write
    // replaces the one it took, so the one it took leaves with it.
    const tabC = emptyHeld();
    holdLoaded(tabC, stored, 'p');
    const replaced = save(tabC, snap([fromB, deposition('dep-a', '8.8 USD/kg', 4)]), stored);
    check('a page that took a write at load and wrote the row again keeps its own write alone',
      ids(replaced) === '["dep-b@2","dep-a@4"]', ids(replaced));
  }

  const decision = (status: DurableReviewDecision['status'], n: number): DurableReviewDecision =>
    ({ status, provenance: 'unverified', reviewer: 'Ada', at: at(n) });
  const decA = emptyHeld();
  const decB = emptyHeld();
  let decided = save(decA, snap([], { reviewDecisions: { 'rec-1': decision('verified', 1) } }), null);
  decided = save(decB, snap([], { reviewDecisions: { 'rec-2': decision('rejected', 2) } }), decided);
  check('each tab’s review decision stays in the one snapshot', JSON.stringify(Object.keys(decided.reviewDecisions).sort()) === '["rec-1","rec-2"]');
  decided = save(decB, snap([], { reviewDecisions: { 'rec-1': decision('rejected', 3), 'rec-2': decision('rejected', 2) } }), decided);
  check('of two decisions on one record from two tabs, the later stands', decided.reviewDecisions['rec-1']?.status === 'rejected' &&
    decided.reviewDecisions['rec-1']?.at === at(3) && 'rec-2' in decided.reviewDecisions, JSON.stringify(decided.reviewDecisions));
  const answeredDecision = save(decA, snap([], { reviewDecisions: {} }), snap([], { reviewDecisions: { 'rec-1': decision('verified', 1), 'rec-3': decision('verified', 4) } }));
  check('a decision the tab held and the service answered leaves the store, and another tab’s stays',
    JSON.stringify(Object.keys(answeredDecision.reviewDecisions)) === '["rec-3"]', JSON.stringify(answeredDecision.reviewDecisions));
  {
    // A page that loads a decision on a record it has not loaded (another project's) leaves it in the store.
    const tabQ = emptyHeld();
    const loaded = snap([], { reviewDecisions: { 'rec-9': decision('verified', 5) } });
    holdLoaded(tabQ, loaded, 'p');
    const kept = save(tabQ, snap([], { reviewDecisions: {} }), loaded);
    check('a loaded decision on a record the page has not loaded stays in the store', 'rec-9' in kept.reviewDecisions, JSON.stringify(kept.reviewDecisions));
    const old = { ...loaded, savedAt: at(6), reviewDecisions: { 'rec-8': { status: 'verified', provenance: 'unverified', reviewer: 'Ada' } as DurableReviewDecision } };
    const carried = save(emptyHeld(), snap([], { reviewDecisions: {} }), old);
    check('a decision from before decisions carried their own time keeps its snapshot’s time when carried',
      carried.reviewDecisions['rec-8']?.at === at(6), JSON.stringify(carried.reviewDecisions));
  }

  const ledger = (people: [string, string][], evidence: string[]) =>
    ({ version: 1, people: people.map(([id, when]) => ({ id, addedAt: when })), evidence: evidence.map((id) => ({ id })), policy: {} }) as unknown as Guild;
  const owing = (people: [string, string][], evidence: string[], withdrawals: GuildWithdrawal[] = []): GuildOwed =>
    ({ ledger: ledger(people, evidence), pending: [...people.map(([id]) => id), ...evidence], withdrawals, actingId: null });
  const guildA = emptyHeld();
  const guildB = emptyHeld();
  let guilded = save(guildA, snap([], { guildOwed: { p: owing([['p-ada', at(1)]], []) } }), null);
  guilded = save(guildB, snap([], { guildOwed: { p: owing([], ['ev-b']) } }), guilded);
  check('each tab’s owed Guild writes stay in the project’s block, each with its ledger row',
    JSON.stringify(guilded.guildOwed?.p?.pending) === '["ev-b","p-ada"]' &&
    JSON.stringify(guilded.guildOwed?.p?.ledger.people.map((x) => x.id)) === '["p-ada"]' &&
    JSON.stringify(guilded.guildOwed?.p?.ledger.evidence.map((x) => x.id)) === '["ev-b"]', JSON.stringify(guilded.guildOwed));
  const guildAnswered = save(guildA, snap([], { guildOwed: { p: owing([], []) } }), guilded);
  check('a Guild write the tab held and the service answered leaves the store, and the other tab’s stays',
    JSON.stringify(guildAnswered.guildOwed?.p?.pending) === '["ev-b"]' && guildAnswered.guildOwed?.p?.ledger.people.length === 0,
    JSON.stringify(guildAnswered.guildOwed?.p));
  const changedLater = save(guildB, snap([], { guildOwed: { p: owing([['p-ada', at(5)]], ['ev-b']) } }), guildAnswered);
  const answeredAgain = save(guildA, snap([], { guildOwed: { p: owing([], []) } }), changedLater);
  check('a later change of a person another tab once owed is another write, and stays',
    JSON.stringify([...(answeredAgain.guildOwed?.p?.pending ?? [])].sort()) === '["ev-b","p-ada"]', JSON.stringify(answeredAgain.guildOwed?.p?.pending));
  const withdrawal = (by: string): GuildWithdrawal => ({ evidenceId: 'ev-x', by, at: '2026-11-11', reason: `a placeholder reason of ${by}` });
  let withdrawn = save(emptyHeld(), snap([], { guildOwed: { p: owing([], [], [withdrawal('p-ada')]) } }), null);
  withdrawn = save(emptyHeld(), snap([], { guildOwed: { p: owing([], [], [withdrawal('p-bo')]) } }), withdrawn);
  check('two withdrawals of one entry on one day by two people are two writes, and both stay',
    withdrawn.guildOwed?.p?.withdrawals.length === 2, JSON.stringify(withdrawn.guildOwed?.p?.withdrawals));
  const otherProject = save(emptyHeld(), snap([], { guildOwed: { q: owing([['p-cy', at(1)]], []) } }), guilded);
  check('another project’s owed Guild writes stay in its own block, and this project’s stay in theirs',
    JSON.stringify(otherProject.guildOwed?.q?.pending) === '["p-cy"]' && JSON.stringify(otherProject.guildOwed?.p?.pending) === '["ev-b","p-ada"]',
    JSON.stringify(otherProject.guildOwed));
  {
    const legacySnap = snap([], { guild: owing([['p-old', at(1)]], []) });
    check('a page takes a snapshot’s legacy Guild block as the open project’s, and none when no project is open',
      JSON.stringify(owedGuild(legacySnap, 'p')?.pending) === '["p-old"]' && owedGuild(legacySnap, null) === undefined);
    const took = emptyHeld();
    holdLoaded(took, legacySnap, 'p');
    const afterTaking = save(took, snap([], { guildOwed: { p: owing([['p-old', at(1)]], []) } }), legacySnap);
    const untouched = save(emptyHeld(), snap([], { guildOwed: { q: owing([], []) } }), legacySnap);
    check('the legacy block leaves once the page that took it saves, and stays for a page that did not',
      afterTaking.guild === undefined && JSON.stringify(afterTaking.guildOwed?.p?.pending) === '["p-old"]' &&
      JSON.stringify(untouched.guild?.pending) === '["p-old"]');
  }
}

// ── the overlay a project's pages load ───────────────────────────────

async function overlayAgainst(health: Answer, overlay: Answer) {
  const real = globalThis.fetch;
  globalThis.fetch = (async (input: RequestInfo | URL) => {
    const next = String(input).startsWith('/api/health') ? health : overlay;
    if (next === 'down') throw new TypeError('fetch failed');
    return new Response(JSON.stringify(next.body ?? {}), { status: next.status });
  }) as typeof fetch;
  try {
    return await loadOverlay();
  } finally {
    globalThis.fetch = real;
  }
}
{
  const got = await overlayAgainst('down', { status: 200 });
  check('a service that does not answer its health is down', 'down' in got, JSON.stringify(got));
}
{
  const got = await overlayAgainst({ status: 200, body: { ok: true } }, { status: 500, body: { detail: 'column decisions.record does not exist' } });
  check('a service that answers its health and refuses the overlay is running, and says why in its words',
    'refused' in got && got.refused.includes('500') && got.refused.includes('column decisions.record does not exist'), JSON.stringify(got));
}
{
  const got = await overlayAgainst({ status: 200, body: { ok: true } }, { status: 200, body: { papers: {}, records: {} } });
  check('an overlay that loads is the overlay', 'overlay' in got, JSON.stringify(got));
}

// A candidate the overlay brings enters the store as a record when its field
// is one the ontology names (src/lib/review.ts, `recordOf`).
const aCandidate = (id: string, field: string): Candidate => ({
  id, paperId: 'placeholder-paper', sectionId: 's1', quote: 'a placeholder sentence', field,
  value: 1, unit: 'placeholder-unit', si: { value: 1, unit: 'placeholder-unit' }, confidence: 0,
  status: 'unverified', provenance: 'unverified', extractorRun: 'claude-1', isPrimary: true,
  carbonSource: null, citesRecordId: null, comparativeBaseline: null, componentTag: null, curationRef: null,
  goldOnly: null, method: null, negativeResult: null, numbering: null, organism: null, organismText: null,
  range: null, rejectReason: null, valueBasis: null,
});
{
  const named = ONTOLOGY[0].id;
  const entered = recordOf(aCandidate('c-1', named));
  check('a candidate on a field the ontology names enters the store as a record of its values, its audit trail empty',
    entered !== null && entered.field === named && entered.value === 1 && entered.unit === 'placeholder-unit' && entered.audit.length === 0,
    JSON.stringify(entered && { field: entered.field, audit: entered.audit }));
  check('a candidate on a field the ontology does not name stays out of the records',
    recordOf(aCandidate('c-2', 'placeholder_field')) === null);
}

// ── what a person may run, and what an import's refusal says (alpha 2.1 stage B) ──

{
  const plant = (builds: { configuration?: string | null; ok: boolean; error?: string | null }[], defaultConfiguration: string | null = null) =>
    ({ id: 'p', module: 'biorefineries.p', kind: 'flowsheet', defaultConfiguration, builds }) as unknown as LibraryPlant;
  const composed = runnable(
    plant(
      [
        { configuration: 'hot water, IB', ok: true },
        { configuration: 'dilute acid, IB', ok: true },
        { configuration: 'AFEX, IB', ok: false, error: 'infeasible here' },
      ],
      'dilute acid, IB',
    ),
  );
  check('a plant is offered in the configurations it built in, its default first', JSON.stringify(composed.configurations) === '["dilute acid, IB","hot water, IB"]', JSON.stringify(composed));
  check('a configuration that did not build is named with the package’s words', composed.failed.length === 1 && composed.failed[0].error === 'infeasible here', JSON.stringify(composed.failed));
  const own = runnable(plant([{ configuration: null, ok: true }]));
  check('a plant that takes no configuration runs in its own', JSON.stringify(own.configurations) === '[null]', JSON.stringify(own));
  check('a plant that never built is offered in none', runnable(plant([{ ok: false, error: 'no' }])).configurations.length === 0);
}

// ── the configurations a thing of another engine is offered in (alpha 2.2 E.18; src/lib/studies.ts) ──

{
  const aThing = (configurations: string[], defaultConfiguration: string | null, configurationTitles: Record<string, string> = {}): EngineThing => ({
    id: 'a-thing',
    title: 'A placeholder thing',
    kind: 'placeholder',
    configurations,
    defaultConfiguration,
    configurationTitles,
    precision: { rtol: 0, atol: 0 },
  });
  const shown = (t: EngineThing | null) => JSON.stringify(offeredConfigurations(t).map((o) => [o.configuration, o.words]));
  const titled = aThing(['one way', 'another way', 'a third way'], 'another way', { 'a third way': 'A placeholder way, in words' });
  check(
    'a thing of another engine is offered in its default first, then the rest in the engine’s order',
    JSON.stringify(offeredConfigurations(titled).map((o) => o.configuration)) === '["another way","one way","a third way"]',
    shown(titled),
  );
  check(
    'a configuration the engine titles reads its title beside its name, and one it titles none reads its name',
    shown(titled) === '[["another way","another way"],["one way","one way"],["a third way","A placeholder way, in words · a third way"]]',
    shown(titled),
  );
  const newestFirst = aThing(['a newer placeholder', 'an older placeholder'], null, {
    'a newer placeholder': 'A placeholder kind, kept at a placeholder time',
    'an older placeholder': 'Another placeholder kind, kept at a placeholder time',
  });
  check(
    'a thing with no default is offered in the engine’s order (the kinetics engine’s, newest first)',
    shown(newestFirst) ===
      '[["a newer placeholder","A placeholder kind, kept at a placeholder time · a newer placeholder"],["an older placeholder","Another placeholder kind, kept at a placeholder time · an older placeholder"]]',
    shown(newestFirst),
  );
  check('a thing that takes no configuration runs in its own', shown(aThing([], null)) === '[[null,"its own"]]', shown(aThing([], null)));
  const ran = { engine: 'a-placeholder-engine', plant: 'a-thing', configuration: 'a third way', inputs: [] };
  check(
    'the card’s line for a run it made names the configuration as the chooser does, and by its name where it holds no title',
    ranWhat(ran, titled.configurationTitles) === 'a-thing (A placeholder way, in words · a third way)' &&
      ranWhat({ ...ran, configuration: 'one way' }, titled.configurationTitles) === 'a-thing (one way)' &&
      ranWhat(ran) === 'a-thing (a third way)',
    ranWhat(ran, titled.configurationTitles),
  );
}

async function callAgainst(answer: { status: number; body?: unknown }, healthy = true): Promise<unknown> {
  const real = globalThis.fetch;
  globalThis.fetch = (async (input: RequestInfo | URL) => {
    if (String(input).startsWith('/api/health')) {
      if (!healthy) throw new TypeError('fetch failed');
      return new Response(JSON.stringify({ ok: true }), { status: 200 });
    }
    return new Response(answer.body === undefined ? 'Bad Gateway' : JSON.stringify(answer.body), { status: answer.status });
  }) as typeof fetch;
  try {
    return await call('/api/flowsheets/import', { method: 'POST' });
  } catch (e) {
    return e;
  } finally {
    globalThis.fetch = real;
  }
}
{
  const big = await callAgainst({ status: 413, body: { detail: 'plant.json is larger than 8 MB' } });
  check('an upload past the size an import takes is refused in the service’s words', big instanceof ServiceRefused && big.message === 'plant.json is larger than 8 MB', String(big));
  const unfetched = await callAgainst({ status: 502, body: { detail: 'the reference file could not be fetched' } });
  check('a source the service could not fetch is its refusal, in its words', unfetched instanceof ServiceRefused && unfetched.status === 502, String(unfetched));
  const proxy = await callAgainst({ status: 502 }, false);
  check('a 502 with no words and no health is the service down', proxy instanceof ServiceDown, String(proxy));
}

// ── a request's own fields refused, and a page older than the service (alpha 2.2 C.2) ──

{
  // FastAPI's 422 for a field the request does not hold: a page loaded before the service took inputs.
  const stale = await callAgainst({
    status: 422,
    body: { detail: [{ type: 'extra_forbidden', loc: ['body', 'overrides'], msg: 'Extra inputs are not permitted', input: [] }] },
  });
  check(
    'a refusal of the request’s own fields is said field by field, with what to do when the page is older than the service',
    stale instanceof ServiceRefused &&
      stale.message ===
        "The service refused the request's fields: overrides: Extra inputs are not permitted. This page was loaded before the service changed what it takes: reload the page." &&
      !stale.message.includes('[object Object]'),
    String(stale),
  );
  const missing = detailWords([{ type: 'missing', loc: ['body', 'inputs', 0, 'quantity'], msg: 'Field required' }]);
  check('a field the request lacks is named where it stands, and no reload is asked for', missing === "The service refused the request's fields: inputs.0.quantity: Field required.", missing);
  check('the service’s own words stand as they are', detailWords('a placeholder refusal') === 'a placeholder refusal');
  // alpha 2.2 E.8: a catalogue entry's own refusal reaches the page as a field error, which Pydantic writes after "Value error, ".
  const own = detailWords([{ type: 'value_error', loc: ['body', 'entry'], msg: 'Value error, a placeholder refusal of the entry' }]);
  check('a model’s own refusal of a field is said in its own words', own === "The service refused the request's fields: entry: a placeholder refusal of the entry.", own);
}

// ── the unit each change is sent in (alpha 2.2 D2; src/lib/params.ts) ──

{
  const scope: ParameterSpec[] = [aSpec('x0', 'placeholder-unit-a', 'Start values'), aSpec('mu_max', 'placeholder-unit-b', 'Kinetics')];
  const shownOnly = scope.filter((s) => s.group === 'Start values');
  const typed = (key: string): Override => anOverride('a-scope', key, 1);
  const changes = [typed('x0'), typed('mu_max')];
  const units = (specs: ParameterSpec[]) => inputsOf(changes, specs).map((i) => `${i.name} ${i.quantity.unit}`).join(', ');
  // FermOSForecast's batch fit shows part of its family's scope and resolves with all of it (ParameterPanel's unitSpecs).
  check('a panel that shows part of its scope sends each change in the unit its scope’s every spec names', units(scope) === 'x0 placeholder-unit-a, mu_max placeholder-unit-b', units(scope));
  check('the shown specs alone would send a change typed elsewhere on the scope with no unit', units(shownOnly) === 'x0 placeholder-unit-a, mu_max ', units(shownOnly));
  const expanded = inputsOf([typed('split.Water')], [aSpec('split', 'placeholder-share', 'Separation')]);
  check('a key expanded per item is sent in its template’s unit', expanded[0]?.quantity.unit === 'placeholder-share', JSON.stringify(expanded));
  // alpha 2.2 C.5: a deposition's reading travels as the reading it is, its ref beside its depositor and its time.
  const reading: Override = { ...typed('x0'), origin: 'measurement', ref: 'dep-1/de-1' };
  const [sentReading, sentTyped] = inputsOf([reading, typed('mu_max')], scope);
  check(
    'a reading is sent as a measurement naming its reading; a typed value is sent as a person’s assumption',
    sentReading?.quantity.origin?.kind === 'measurement' &&
      sentReading.quantity.origin.ref === 'dep-1/de-1' &&
      sentReading.quantity.origin.by === 'Ada' &&
      sentTyped?.quantity.origin?.kind === 'person-assumption' &&
      !('ref' in (sentTyped.quantity.origin ?? {})),
    JSON.stringify([sentReading, sentTyped]),
  );
  // alpha 2.2 E.1: the service serves a change as the page kept it, so a change kept before the page wrote its origin
  // comes back with none, and the generated type names an origin on every change.
  const keptBefore = { scope: 'a-scope', key: 'x0', value: 1, by: 'Ada', at: AT } as Override;
  const [sentKept] = inputsOf([keptBefore], scope);
  check('a change kept with no origin is sent as a person’s assumption, as the service reads it', sentKept?.quantity.origin?.kind === 'person-assumption', JSON.stringify(sentKept));
  // alpha 2.2 E.17: a reading Proforma's panel keeps holds the reading's own value and unit, which go as they are.
  const own: Override = { ...typed('x0'), value: 1000, unit: 'placeholder-unit-c', by: 'Grace', at: AT, origin: 'measurement', ref: 'dep-1/de-1' };
  const [sentOwn, sentBeside] = inputsOf([own, typed('mu_max')], scope);
  check(
    'a reading kept in its own unit goes in that value and unit, its ref, depositor and time beside it and no low or high; a person’s change beside it goes in its parameter’s unit',
    sentOwn?.quantity.value === 1000 &&
      sentOwn.quantity.unit === 'placeholder-unit-c' &&
      sentOwn.quantity.origin?.kind === 'measurement' &&
      sentOwn.quantity.origin.ref === 'dep-1/de-1' &&
      sentOwn.quantity.origin.by === 'Grace' &&
      sentOwn.quantity.origin.at === AT &&
      !('low' in sentOwn.quantity) &&
      !('high' in sentOwn.quantity) &&
      sentBeside?.quantity.unit === 'placeholder-unit-b',
    JSON.stringify([sentOwn, sentBeside]),
  );
}

// ── the bench's readings, read as the service's lookup reads them (alpha 2.2 C.5; src/engine/readings.ts) ──

{
  const entry = (id: string, value: number, confirmed = false) =>
    ({ id, measureId: 'm-1', stepId: 'readings', at: '2026-11-03T09:00:00Z', value, unit: 'placeholder-unit', raw: `came in at ${value}`, confirmed });
  // "came in at 3", fixed to 2 at the bench: the correction appended, the 3 kept with its words.
  const first = entry('de-1', 3);
  const fixed = correctionOf(first, 'de-2', 2, '2026-11-03T11:30:00Z');
  const bench = aDeposition('dep-1', { entries: [first, fixed], sampleTimes: {} });
  check(
    'a correction keeps the time its reading was taken, says when it was typed, and stands confirmed',
    fixed.at === first.at && fixed.correctedAt === '2026-11-03T11:30:00Z' && fixed.confirmed && fixed.value === 2,
    JSON.stringify(fixed),
  );
  check(
    'after a correction, only the newest number waits to be read back, and the corrected one waits for nothing',
    correctedBy(bench, first) === 'de-2' && correctedBy(bench, fixed) === null && awaitingReadBack(bench).length === 0,
    JSON.stringify(awaitingReadBack(bench)),
  );
  // Then "came in at 5" and "came in at 7": the 7 alone waits, the number the person said last.
  const later: Deposition = { ...bench, entries: [first, fixed, entry('de-3', 5), entry('de-4', 7)] };
  check(
    'of several numbers on one measure, the read-back box holds the newest alone',
    JSON.stringify(awaitingReadBack(later).map((e) => e.id)) === '["de-4"]',
    JSON.stringify(awaitingReadBack(later).map((e) => e.id)),
  );
  // A series: each reading at its own hour stands, and a later one at the same hour corrects it.
  const series: Deposition = {
    ...bench,
    entries: [entry('de-5', 1), entry('de-6', 2), entry('de-7', 1.5)],
    sampleTimes: { 'de-5': 1, 'de-6': 2, 'de-7': 1 },
  };
  check(
    'a reading in a series is its own, corrected by a later one at its hour alone',
    correctedBy(series, series.entries[0]) === 'de-7' && correctedBy(series, series.entries[1]) === null,
    JSON.stringify(series.entries.map((e) => [e.id, correctedBy(series, e)])),
  );
  check(
    'a basis source is a reading where it names one reading and when it was measured, and a series is no reading',
    isReading({ kind: 'deposition', id: 'dep-1/de-2', note: 'measured on 2026-11-03T09:00:00Z', by: 'Ada' }) &&
      !isReading({ kind: 'deposition', id: 'dep-1', note: 'the readings as the browser sent them', by: null }),
  );
}

// ── a train's changes, each named by its place (alpha 2.2 D2; src/lib/pureos.ts) ──

{
  const train = { id: 'tr-1', units: [{ id: 'U1' }, { id: 'U2' }] } as unknown as TrainSpec;
  const typed = (place: string, key: string, trainId = 'tr-1'): Override => anOverride(unitScope(trainId, place), key, 1);
  const overrides = [typed('U2', 'b'), typed('inlet', 'a'), typed('U1', 'c'), typed('U1', 'a', 'tr-2')];
  const read = {
    [unitScope('tr-1', 'inlet')]: [aSpec('a', 'placeholder-unit-a')],
    [unitScope('tr-1', 'U2')]: [aSpec('b', 'placeholder-unit-b')],
  };
  const named = trainInputs(train, overrides, read).map((i) => `${i.name} ${i.quantity.unit}`).join(', ');
  check(
    'a train’s changes are named <place>.<key>, the inlet first and then each unit in order, each in its spec’s unit; a place whose specs are unread sends none yet, and another train’s change none',
    named === 'inlet.a placeholder-unit-a, U2.b placeholder-unit-b',
    named,
  );
  check('a train with nothing read sends nothing', trainInputs(train, overrides, {}).length === 0);
}

// ── a Proforma scenario's run, its changes sent as typed inputs (alpha 2.2 D2; src/lib/proforma.ts) ──

{
  const typed = (key: string, value: number, low?: number): Override => anOverride('proforma:sc-1', key, value, low != null ? { low } : {});
  const changes = [typed('a', 1, 0.5), typed('b', 2)];
  const panel = { specs: [aSpec('a', 'placeholder-unit-a'), aSpec('b', 'placeholder-unit-b')] };
  const shelfOnly = aFlowsheet([aShelfInput('a', 'placeholder-unit-c')]);
  const ask = { scenarioId: 'sc-1', overrides: changes, by: 'Ada', host: null };
  const body = runBody({ ...ask, specs: runSpecs(panel, shelfOnly) }) as unknown as Record<string, unknown>;
  const sent = (body.inputs as { name: string; quantity: { unit: string; low?: number } }[]) ?? [];
  check(
    'a scenario’s run sends each change as a typed input in its panel spec’s unit, with its range, by the person asking, and neither older field',
    sent.map((i) => `${i.name} ${i.quantity.unit}`).join(', ') === 'a placeholder-unit-a, b placeholder-unit-b' &&
      sent[0]?.quantity.low === 0.5 && body.by === 'Ada' && !('overrides' in body) && !('assumptions' in body),
    JSON.stringify(body),
  );
  const early = (runBody({ ...ask, specs: runSpecs(null, shelfOnly) }).inputs ?? []).map((i) => `${i.name} ${i.quantity.unit}`).join(', ');
  check('before the panel answers, the shelf’s inputs name each unit, and a key they lack goes with none for the service to refuse', early === 'a placeholder-unit-c, b ', early);
  // Before the panel answers, the inputs as the service bound them name each unit, the shelf's a key they lack.
  const bound = { inputs: [{ key: 'a', unit: 'placeholder-unit-e' }, { key: 'b', unit: 'placeholder-unit-d' }] };
  const boundFirst = (runBody({ ...ask, specs: runSpecs(null, shelfOnly, bound) }).inputs ?? []).map((i) => `${i.name} ${i.quantity.unit}`).join(', ');
  check('before the panel answers, the inputs as bound name each unit, the shelf’s only a key they lack', boundFirst === 'a placeholder-unit-e, b placeholder-unit-d', boundFirst);
  const partly = (runBody({ ...ask, specs: runSpecs(null, shelfOnly, { inputs: [bound.inputs[1]] }) }).inputs ?? []).map((i) => `${i.name} ${i.quantity.unit}`).join(', ');
  check('a key the binding lacks takes the shelf’s unit', partly === 'a placeholder-unit-c, b placeholder-unit-d', partly);
  const neither = (runBody({ ...ask, specs: runSpecs(null, null, { inputs: [bound.inputs[1]] }) }).inputs ?? []).map((i) => `${i.name} ${i.quantity.unit}`).join(', ');
  check('with no shelf yet, the inputs as bound still name theirs', neither === 'a , b placeholder-unit-d', neither);
  // A composite's Finance value goes in the unit its panel names (OF-BLD-020 §6.1).
  const composite = { specs: [aSpec('a', 'placeholder-unit-a'), aSpec('fin', 'placeholder-unit-per-year')] };
  const fin = runBody({ ...ask, overrides: [typed('a', 1), typed('fin', 3)], specs: runSpecs(composite, shelfOnly, bound) });
  const finSent = (fin.inputs ?? []).map((i) => `${i.name} ${i.quantity.unit}`).join(', ');
  check('a composite’s Finance value goes in the unit its panel names', finSent === 'a placeholder-unit-a, fin placeholder-unit-per-year', finSent);
  // The ceiling check sends the yield's change as a typed input in its unit, and neither older field.
  const q = ceilingQuery({ scenarioId: 'sc-1', host: null, overrides: [typed('yield', 0.4)], specs: [{ key: 'yield', unit: 'placeholder-share' }] });
  const asked = JSON.parse(q.get('inputs') ?? '[]') as { name: string; quantity: { value: number; unit: string } }[];
  check(
    'the ceiling check sends the yield as a typed input in its unit, and neither older field',
    asked.length === 1 && asked[0].name === 'yield' && asked[0].quantity.unit === 'placeholder-share' && !q.has('overrides') && !q.has('assumptions'),
    q.toString(),
  );
  check('a ceiling check with no typed yield sends no inputs', !ceilingQuery({ scenarioId: 'sc-1', host: null }).has('inputs'));
  // alpha 2.2 E.17: a reading chosen on the panel goes in its own value and unit from the run and the ceiling check alike.
  const reading = anOverride('proforma:sc-1', 'yield', 0.5, { unit: 'placeholder-share-b', origin: 'measurement', ref: 'dep-1/de-1' });
  const ran = (runBody({ ...ask, overrides: [reading, typed('b', 2)], specs: runSpecs(panel, shelfOnly) }).inputs ?? []).map(
    (i) => `${i.name} ${i.quantity.value} ${i.quantity.unit} ${i.quantity.origin?.ref ?? ''}`.trim(),
  );
  check('a scenario’s run sends a reading in its own value and unit, with its ref', ran.join(', ') === 'yield 0.5 placeholder-share-b dep-1/de-1, b 2 placeholder-unit-b', ran.join(', '));
  const checked = JSON.parse(
    ceilingQuery({ scenarioId: 'sc-1', host: null, overrides: [reading], specs: [{ key: 'yield', unit: 'placeholder-share' }] }).get('inputs') ?? '[]',
  ) as { name: string; quantity: { value: number; unit: string; origin?: { ref?: string } } }[];
  check(
    'the ceiling check sends a yield set to a reading in the reading’s own value and unit',
    checked.length === 1 && checked[0].quantity.value === 0.5 && checked[0].quantity.unit === 'placeholder-share-b' && checked[0].quantity.origin?.ref === 'dep-1/de-1',
    JSON.stringify(checked),
  );
}

// ── the scenario page's binding with its overrides laid on (alpha 2.2 E.17; src/lib/proforma.ts `laidOn`) ──

{
  const input = (key: string, unit: string): ScenarioInput => ({
    key, label: key, unit, binding: 'waiting', value: null, low: null, high: null, sampling: null, source: null,
    recordIds: [], records: [], leftOutNoCarbon: 0, leftOutOtherCarbon: 0, flags: [],
  });
  const inputs = [input('a', 'placeholder-unit-a'), input('b', 'placeholder-unit-b'), input('c', 'placeholder-unit-c'), input('d', 'placeholder-unit-d')];
  const person = anOverride('proforma:sc-1', 'a', 2, { low: 1, note: 'a placeholder' });
  const inItsUnit = anOverride('proforma:sc-1', 'b', 3, { unit: 'placeholder-unit-b', origin: 'measurement', ref: 'dep-1/de-1', by: 'Grace' });
  const inAnother = anOverride('proforma:sc-1', 'c', 4, { unit: 'placeholder-unit-e', origin: 'measurement', ref: 'dep-1/de-2', by: 'Grace' });
  const [a, b, c, d] = laidOn(inputs, [person, inItsUnit, inAnother]);
  check(
    'a person’s value binds as their assumption with its interval',
    a.binding === 'assumption' && a.value === 2 && a.low === 1 && a.high === 2 && a.sampling === 'uniform' && a.source?.kind === 'assumption' && a.source.by === 'Ada' &&
      a.source.note === `typed on ${AT}: a placeholder`,
    JSON.stringify(a),
  );
  check(
    'a reading in the input’s unit binds as the reading it is: one value held fixed, its source the reading',
    b.binding === 'assumption' && b.value === 3 && b.low === 3 && b.high === 3 && b.sampling === 'fixed' && isReading(b.source) && b.source?.id === 'dep-1/de-1' && b.source.by === 'Grace',
    JSON.stringify(b),
  );
  check(
    'a reading in another unit binds as the reading with no value, which the service sets in the input’s unit',
    c.binding === 'assumption' && c.value === null && c.sampling === 'fixed' && isReading(c.source) && c.source?.id === 'dep-1/de-2',
    JSON.stringify(c),
  );
  check('an input no override names stands as the service bound it', d === inputs[3]);
  const asked = modellerQuestions([a, b, c, d], null, null).map((q) => q.key);
  check('the questions for a modeller ask of a person’s value and an input that waits, and of no reading', asked.join() === 'a,d', asked.join());
  check(
    'a Proforma assumption an older build reads holds a person’s value, and none for a reading',
    assumptionOfOverride(inItsUnit) === null && assumptionOfOverride(person)?.value === 2,
    JSON.stringify([assumptionOfOverride(inItsUnit), assumptionOfOverride(person)]),
  );
}

// ── a reading a panel row is set to, against the listing the service gave (alpha 2.2 E.debts; src/lib/params.ts) ──

{
  const set = anOverride('proforma:sc-1', 'yield', 0.5, { unit: 'placeholder-share-b', origin: 'measurement', ref: 'dep-1/de-1' });
  check('a reading the service’s listing names stands on the row', !readingLeftTheList(set, { readings: [{ ref: 'dep-1/de-1' }], problem: null }));
  check('a reading a listing that answered names nowhere has left it', readingLeftTheList(set, { readings: [{ ref: 'dep-1/de-2' }], problem: null }));
  check(
    'a listing the service could not give, or one still asked for, says nothing of the reading',
    !readingLeftTheList(set, { readings: [], problem: 'The service is not running.' }) && !readingLeftTheList(set, { readings: null, problem: null }),
  );
  // A composite's Finance value set to a reading is credited to its depositor as a reading, a person's as theirs.
  const composite = { ...aFlowsheet([]), id: 'custom_train_v1' };
  const rows = readBackRows({ 'finance.a': 1, 'finance.b': 2 }, composite, [
    { name: 'finance.a', value: 1, unit: '', source: { kind: 'deposition', id: 'dep-1/de-1', by: 'Grace', note: null } },
    { name: 'finance.b', value: 2, unit: '', source: { kind: 'assumption', id: null, by: 'Ada', note: null } },
  ]);
  check(
    'a run’s read-back credits a reading a person chose to its depositor as a reading, and a person’s value to them',
    JSON.stringify(rows.map((r) => [r.key, r.origin, r.by, r.reading ?? false])) === '[["finance.a","person","Grace",true],["finance.b","person","Ada",false]]',
    JSON.stringify(rows),
  );
}

// ── a scenario card's counts, the reference runs a page reads (src/lib/proforma.ts) ──

{
  // A custom_train_v1 scenario's plant scale, bound from the vessel design it names, is counted by what binds it;
  // an input with a fit chosen is counted as a fit (alpha 2.2 C.6, the screens' review).
  const scenario = aScenario('sc-2', { modelId: 'custom_train_v1' });
  const fromArtifact = (id: string, note: string): BasisSource => ({ kind: 'artifact', id, note, by: null });
  const input = (key: string, binding: ScenarioInput['binding'], source: BasisSource | null): ScenarioInput => ({
    key, label: key, unit: '', binding, value: null, low: null, high: null, sampling: null, source,
    recordIds: [], records: [], leftOutNoCarbon: 0, leftOutOtherCarbon: 0, flags: [],
  });
  const info: ProformaScenarioInfo = {
    id: 'sc-2', name: 'S', product: '', flowsheet: 'custom_train_v1', host: null, hosts: [], waiting: [], leavesOut: [],
    priceBasis: '', refused: null,
    inputs: [
      input('plant_scale', 'artifact', fromArtifact('v'.repeat(16), 'the plant scale vessel design vvvv was designed at')),
      input('titre', 'artifact', fromArtifact('f'.repeat(16), 'a fit')),
      input('glucose_price', 'assumption', null),
    ],
  };
  const c = inputCounts(scenario, info, [], [], { titre: 'f'.repeat(16) });
  check(
    'a plant scale the vessel design binds is counted by what binds it, and a chosen fit as a fit',
    !!c && c.kept === 1 && c.keptBy.join() === 'the vessel design' && c.computed === 1 && c.assumed === 1,
    JSON.stringify(c),
  );
  const none = inputCounts(scenario, { ...info, inputs: [info.inputs[0]] }, [], [], {});
  check('with no fit chosen, no input is counted as a fit', !!none && none.computed === 0 && none.kept === 1, JSON.stringify(none));

  // A plant that takes configurations is run in its default, and its page finds that run on a reload.
  const run = (configuration: string | null, plant = 'placeholder-plant'): EngineRun => ({
    id: `run-${configuration}`, engine: 'biosteam', tool: 'library.run', toolVersion: '', plant, configuration, status: 'done',
    artifactId: 'a'.repeat(16), inputs: [], outputs: {}, provenance: null, refused: null, scenarioId: null, sff: null,
    sffRefused: null, versions: {}, diagnostics: [], by: 'Ada', at: AT, durationMs: null,
  });
  const runs = [run('S2'), run('S1'), run(null, 'other')];
  check('a plant’s reference run is its run in the default configuration', referenceRunOf('placeholder-plant', runs, 'S1')?.id === 'run-S1');
  check('and a plant that takes none is found with none', referenceRunOf('other', runs)?.id === 'run-null' && referenceRunOf('placeholder-plant', runs) === null);

  // The runs kept from the retired reference entries map to the library plant each entry built.
  const art = (tool: string, flowsheet?: string): Artifact => ({
    id: `${tool}-${flowsheet ?? ''}`, tool, toolVersion: '', output: {}, outputHash: '', provenance: 'assumed', createdAt: AT,
    durationMs: 0, seed: null,
    inputs: flowsheet ? [{ name: 'flowsheet', value: flowsheet, unit: '', source: { kind: 'convention', id: null, note: null, by: null } }] : [],
  });
  const kept = [art('proforma.reference', 'corn_drygrind'), art('proforma_benchmark'), art('proforma.reference', 'cornstover_benchmark'), art('library.run')];
  check('a kept reference run names its retired entry, the benchmark the corn stover entry', retiredEntryOf(kept[0]) === 'corn_drygrind' && retiredEntryOf(kept[1]) === 'cornstover_benchmark' && retiredEntryOf(kept[3]) === null);
  check(
    'and each plant’s page lists the runs kept from its entry alone',
    keptRunsOf('corn', kept).map((a) => a.id).join() === 'proforma.reference-corn_drygrind' &&
      keptRunsOf('cornstover', kept).map((a) => a.id).join() === 'proforma_benchmark-,proforma.reference-cornstover_benchmark',
  );
}

// ── the runbooks a page makes (alpha 2.2 E.11; src/store.ts) ───────────
// A runbook is the generated Runbook, served as kept: a draft's prediction may
// hold its kind, interval, artifact and records as null or leave them out, and
// a measure may leave its prediction out. lock.ts and runbook_lock.py read the
// two apart, so the page keeps each as the service wrote it. Every runbook the
// page makes is one of the project's rows: adopted from a draft, opened to
// revise a locked one, or promoted from a research one.

{
  const S = () => useStore.getState();
  const aPrediction = (id: string, more: Partial<Prediction> = {}): Prediction => ({
    id, label: `A placeholder claim ${id}`, value: 1, unit: 'placeholder-unit', confidence: 'medium', basis: 'a placeholder basis', ...more,
  });
  const draft: RunbookDraft = {
    title: 'A placeholder draft',
    productId: '',
    strainId: '',
    predictions: [aPrediction('p1', { kind: null, interval: null, artifactId: null, recordIds: null }), aPrediction('p2')],
    measures: [
      { id: 'm1', label: 'A placeholder measure', unit: 'placeholder-unit', timepoint: 'harvest', predictionId: 'p1' },
      { id: 'm2', label: 'A placeholder context', unit: 'placeholder-unit', timepoint: 'harvest' },
    ],
  };
  const drafted = S().adoptRunbookDraft(draft);
  const adopted = S().runbooks.find((r) => r.id === drafted);
  check(
    'a draft’s predictions and measures enter the runbook as the service wrote them, each null and each field left out kept',
    JSON.stringify(adopted?.predictions) === JSON.stringify(draft.predictions) &&
      JSON.stringify(adopted?.measurementSchema) === JSON.stringify(draft.measures) &&
      adopted?.predictions?.[0].kind === null && !('kind' in (adopted?.predictions?.[1] ?? {})) &&
      !('predictionId' in (adopted?.measurementSchema?.[1] ?? {})),
    JSON.stringify(adopted?.predictions),
  );
  S().lockRunbook(drafted);
  const locked = S().runbooks.find((r) => r.id === drafted);
  check(
    'its lock is taken over the values as they arrived, and reads as intact',
    locked?.lockHash === runbookLockHash(draft.predictions, draft.measures) && locked !== undefined && lockIntact(locked) &&
      locked.lockHash !== runbookLockHash([aPrediction('p1'), aPrediction('p2')], draft.measures),
    String(locked?.lockHash),
  );
  const revised = S().supersedeRunbook(drafted);
  useStore.setState((x) => ({ runbooks: x.runbooks.map((r) => (r.id === drafted ? { ...r, status: 'complete' as const } : r)) }));
  const promoted = S().promoteRunbook(drafted);
  const sent = new Set(projectStateOf(S()).runbooks.map((r) => r.id));
  check(
    'a runbook adopted, revised or promoted on the page is among the rows the page sends, each under an id that holds across reloads',
    revised !== null && promoted !== null && sent.has(drafted) && sent.has(revised) && sent.has(promoted) &&
      [revised, promoted].every((id) => /^rb-[0-9a-z]+-\d+$/.test(id ?? '')),
    JSON.stringify([...sent]),
  );
  const revision = S().runbooks.find((r) => r.id === revised);
  check(
    'the revision keeps the locked runbook’s values as they were and is open to change; the original keeps its lock',
    JSON.stringify(revision?.predictions) === JSON.stringify(draft.predictions) && revision?.lockedAt === null &&
      S().runbooks.find((r) => r.id === drafted)?.lockHash === locked?.lockHash,
  );
  useStore.setState({ runbooks: [], adoptedRunbookIds: [] });
}

// ── a run's grid with a dimension of one value (src/engine/interp.ts) ──

{
  // Two dimensions held at one value each and one swept over three: the base point reads the grid's own number.
  const grid = {
    dims: [
      { key: 'held-a', values: [45] },
      { key: 'held-b', values: [0.45] },
      { key: 'swept', values: [0.3, 0.4, 0.5] },
    ],
    data: [1.0, 1.5, 2.0],
  };
  const base = interpolate(grid, { 'held-a': 45, 'held-b': 0.45, swept: 0.4 });
  const between = interpolate(grid, { 'held-a': 45, 'held-b': 0.45, swept: 0.45 });
  check('a grid holding a dimension at one value reads its own number at the base point', base === 1.5, String(base));
  check('and interpolates along the dimension it sweeps', Math.abs(between - 1.75) < 1e-12, String(between));
  check('a point off a held dimension is held to its one value', interpolate(grid, { 'held-a': 50, 'held-b': 0.45, swept: 0.3 }) === 1.0);
}

// ── a catalogue entry as the catalogues screen's form keeps it (alpha 2.2 E.gate) ──

{
  // A lesson taken in from a file with its body (ADR-018), every word and number a placeholder.
  const lesson: CatalogueEntry = {
    kind: 'lesson',
    id: 'placeholder-lesson',
    name: 'A placeholder lesson',
    skills: ['placeholder-skill'],
    minutes: 5,
    blocks: [{ kind: 'prose', md: 'A placeholder paragraph.' }, { kind: 'embed', embed: 'mini-queue', arg: null }],
    checkpoint: [{ id: 'q1', prompt: 'A placeholder choice?', kind: 'mc', options: ['One', 'Two'], answerIndex: 1, explanation: '' }],
    by: 'Placeholder Keeper',
    at: '2026-11-01T00:00:00+00:00',
    agent: 'person',
    via: null,
  };
  const sent = edited(lesson, { name: 'A placeholder lesson, renamed', skills: [] });
  check(
    'a lesson edited on the catalogues form sends its minutes, its blocks and its checkpoint as it holds them',
    sent.minutes === 5 && JSON.stringify(sent.blocks) === JSON.stringify(lesson.blocks) && JSON.stringify(sent.checkpoint) === JSON.stringify(lesson.checkpoint),
    JSON.stringify(sent),
  );
  check('with the fields the form holds laid over them', sent.name === 'A placeholder lesson, renamed' && (sent.skills ?? []).length === 0 && sent.kind === 'lesson');
  check('and leaves its keeper, lane, door and time for the service to write', sent.by === '' && sent.at === '' && sent.agent === null && sent.via === null);
  check(
    "a lesson's body is said in words, and one with none says so",
    bodyWords(lesson) === '5 min, 2 blocks, 1 checkpoint question' && bodyWords({ minutes: null, blocks: [], checkpoint: [] }) === 'no body yet',
    bodyWords(lesson),
  );
}

// ── where the screens say a project's rows are kept (alpha 2.2 E.19; ADR-014) ──
// The service keeps every row a project holds, for every page that opens the project: its conversations,
// depositions, runbooks and their locks, scenarios, trains, overrides and fits, its ledger, records and decisions,
// catalogues and protocols. This browser keeps its preferences and the writes the service has not yet acknowledged
// (src/lib/durable.ts). The words a person reads say so: a sentence that keeps something in this browser names a
// write that waits for the service or a preference, a browser owns no row, and a session holds what it loaded and
// what lives on the page alone (a run at the bench, an export, a proposal, an undo). A sentence here is a string or
// a template, a JSX attribute's words, or one JSX element's text with the strings of its expressions; the words of
// comments are the code's own.

{
  const SRC = join(import.meta.dirname, '..', 'src');
  /** Every source file under `dir` with words a person may read; the generated types hold the service's own. */
  const sourcesUnder = (dir: string): string[] =>
    readdirSync(dir, { withFileTypes: true }).flatMap((d) => {
      const path = join(dir, d.name);
      if (d.isDirectory()) return sourcesUnder(path);
      return /\.tsx?$/.test(d.name) && !d.name.endsWith('.gen.ts') ? [path] : [];
    });
  const ENTITIES: Record<string, string> = {
    rsquo: '’', lsquo: '‘', ldquo: '“', rdquo: '”', mdash: '—', ndash: '–', amp: '&', nbsp: ' ', hellip: '…', middot: '·', rarr: '→', larr: '←', times: '×',
  };
  const plain = (text: string) =>
    text
      .replace(/&(#\d+|[a-z]+);/g, (whole, name: string) => (name.startsWith('#') ? String.fromCharCode(Number(name.slice(1))) : (ENTITIES[name] ?? whole)))
      .replace(/\s+/g, ' ')
      .trim();
  /** The sentences a file shows, each with its line and the test id of the element that draws it. */
  const sentencesOf = (path: string): { line: number; text: string; testid: string | null }[] => {
    const file = ts.createSourceFile(path, readFileSync(path, 'utf8'), ts.ScriptTarget.Latest, true, path.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS);
    const joined = new Map<ts.Node, string[]>();
    // A string joins the JSX attribute or element that shows it, or else the strings it is joined or chosen with.
    const sentenceOf = (node: ts.Node): ts.Node => {
      let words: ts.Node = node;
      let joining = true;
      for (let at = node.parent; at && !ts.isSourceFile(at); at = at.parent) {
        if (ts.isJsxAttribute(at) || ts.isJsxElement(at) || ts.isJsxFragment(at)) return at;
        const joins =
          ts.isTemplateExpression(at) || ts.isTemplateSpan(at) || ts.isConditionalExpression(at) || ts.isParenthesizedExpression(at) ||
          (ts.isBinaryExpression(at) && at.operatorToken.kind === ts.SyntaxKind.PlusToken);
        if (joining && joins) words = at;
        else joining = false;
      }
      return words;
    };
    const visit = (node: ts.Node) => {
      const text =
        ts.isJsxText(node) || ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node) || ts.isTemplateHead(node) ||
        ts.isTemplateMiddle(node) || ts.isTemplateTail(node)
          ? node.text
          : null;
      if (text && text.trim()) {
        const at = sentenceOf(node);
        joined.set(at, [...(joined.get(at) ?? []), text]);
      }
      ts.forEachChild(node, visit);
    };
    visit(file);
    const testidOf = (node: ts.Node): string | null => {
      const opening = ts.isJsxElement(node) ? node.openingElement : null;
      const id = opening?.attributes.properties.find((p) => ts.isJsxAttribute(p) && p.name.getText(file) === 'data-testid');
      return id && ts.isJsxAttribute(id) && id.initializer && ts.isStringLiteral(id.initializer) ? id.initializer.text : null;
    };
    return [...joined].map(([node, parts]) => ({
      line: file.getLineAndCharacterOfPosition(node.getStart(file)).line + 1,
      text: plain(parts.join(' ')),
      testid: testidOf(node),
    }));
  };

  /** A sentence that keeps something in this browser, or has this browser hold it. */
  const KEPT_IN_THIS_BROWSER =
    /\b(?:kept|keeps|held|holds|stored|stores|saved|saves|lives|waits)\b[^.;]{0,40}\bin (?:this|the) browser\b|\bthis browser (?:keeps|holds|stores|saves|kept|held|stored|saved)\b|\bthe store (?:keeps|holds)\b/i;
  /** What this browser keeps (ADR-014): a write the service has not yet acknowledged, or a preference (the reviewer's name, the person it acts as). */
  const WAITS_OR_PREFERS =
    /\buntil\b|\bnot yet\b|\bhas not\b|\bhad not\b|\bis away\b|\bwas away\b|\bstopped answering\b|\bsent when\b|\bbeing sent\b|\bsent only with\b|\bwould refuse\b|\bpreferences\b|\b(?:the|your|reviewer['’]s) name\b|\bacts as\b/i;
  /** A row as one browser's own, or as made in another: a project's rows are the project's on every page. */
  const A_BROWSERS_OWN = /\bof (?:this|that|another|each) browser\b|\b(?:in|from|by) (?:another|other|a different) browser\b|\banother browser['’]s\b/i;
  /** A session holding what the service keeps. */
  const KEPT_IN_THIS_SESSION =
    /\b(?:records?|extract(?:ed|ions?)|decisions?|decided|corrected|gold(?: set| annotations?)?|versions?|conversations?|trains?|ledger|depositions?|scenarios?|protocols?|lessons?)\b[^.;]*\b(?:in|of|from) this session\b|\bthis session['’]s (?:records?|extractions?|decisions?|gold set|ledger|conversations?|trains?|scenarios?|protocols?|versions?)\b/i;
  /** What a session holds of them: what it loaded. */
  const LOADED = /\bloaded\b/i;

  /**
   * A browser shown where a person's name stands: a row's maker drawn as `x || 'this browser'` (or `??`) on a screen.
   * The service's own word for a row kept with no reviewer name set (project_state.UNNAMED, src/store.ts `decidedBy`)
   * is a value it reads, and a screen names such a row's maker as nobody named.
   */
  const browserNamed = (path: string): number[] => {
    const file = ts.createSourceFile(path, readFileSync(path, 'utf8'), ts.ScriptTarget.Latest, true, path.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS);
    const lines: number[] = [];
    const shown = (node: ts.Node): boolean => {
      for (let at = node.parent; at && !ts.isSourceFile(at); at = at.parent) {
        if (ts.isJsxExpression(at) || ts.isTemplateSpan(at)) return true;
        if (ts.isFunctionLike(at)) return false;
      }
      return false;
    };
    const visit = (node: ts.Node) => {
      const p = node.parent;
      if (
        (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) &&
        /^this browser$/i.test(node.text.trim()) &&
        p && ts.isBinaryExpression(p) && p.right === node &&
        (p.operatorToken.kind === ts.SyntaxKind.BarBarToken || p.operatorToken.kind === ts.SyntaxKind.QuestionQuestionToken) &&
        shown(node)
      )
        lines.push(file.getLineAndCharacterOfPosition(node.getStart(file)).line + 1);
      ts.forEachChild(node, visit);
    };
    visit(file);
    return lines;
  };

  const misplaced: string[] = [];
  let read = 0;
  for (const path of sourcesUnder(SRC)) {
    for (const { line, text } of sentencesOf(path)) {
      read++;
      const where = `${relative(join(SRC, '..'), path)}:${line}`;
      if (A_BROWSERS_OWN.test(text)) misplaced.push(`${where} gives a browser a row the project keeps: “${text}”`);
      else if (KEPT_IN_THIS_BROWSER.test(text) && !WAITS_OR_PREFERS.test(text)) misplaced.push(`${where} keeps in this browser what the service keeps: “${text}”`);
      else if (KEPT_IN_THIS_SESSION.test(text) && !LOADED.test(text)) misplaced.push(`${where} keeps in this session what the service keeps: “${text}”`);
    }
    for (const line of browserNamed(path)) misplaced.push(`${relative(join(SRC, '..'), path)}:${line} names this browser where a person’s name stands`);
  }
  check(
    'the words on every screen put a project’s rows with the service, and in this browser its preferences and the writes that wait for the service',
    misplaced.length === 0,
    misplaced.length ? misplaced.map((m) => `\n    ${m}`).join('') : `${read} sentences read`,
  );
  const none = sentencesOf(join(SRC, 'screens', 'Postdoc.tsx')).find((s) => s.testid === 'live-conversations-none');
  check(
    'Postdoc’s empty list says the service keeps each conversation with the project, for every page that opens it',
    !!none && /\bThe service keeps each conversation with the project\b/.test(none.text) && /\bevery page that opens the project\b/.test(none.text),
    none?.text ?? 'no live-conversations-none words in src/screens/Postdoc.tsx',
  );
}

// H.0, the sweep on the final tree: what a person reads where an address,
// a time, a document or a number stood raw.
{
  // Every link inside a project keeps the project in its address (router.tsx `href`): a link written as a bare
  // hash drops it. Home's own `#/`, and a link naming a project's address (`#/p/<id>`), are the plain ones.
  const SRC = join(import.meta.dirname, '..', 'src');
  const sourcesUnder = (dir: string): string[] =>
    readdirSync(dir, { withFileTypes: true }).flatMap((d) => {
      const path = join(dir, d.name);
      if (d.isDirectory()) return sourcesUnder(path);
      return /\.tsx?$/.test(d.name) && !d.name.endsWith('.gen.ts') ? [path] : [];
    });
  const bare: string[] = [];
  for (const path of sourcesUnder(SRC)) {
    const text = readFileSync(path, 'utf8');
    text.split('\n').forEach((line, i) => {
      if (/href=\{`#\$\{|href=\{`#\/(?!p\/)|href="#\/[^"]/.test(line)) bare.push(`${relative(join(SRC, '..'), path)}:${i + 1}`);
    });
  }
  check('every link inside a project goes through the router, so the address keeps the project', bare.length === 0, bare.map((b) => `\n    ${b}`).join(''));
  check(
    'an ISO time in a basis note reads as the page writes a time, the day and the minute in UTC',
    stampsIn('estimated on 2026-11-08T03:23:03.514708Z: a value') === 'estimated on 2026-11-08 03:23 UTC: a value' &&
      stampsIn('no time here') === 'no time here',
    stampsIn('estimated on 2026-11-08T03:23:03.514708Z: a value'),
  );
  const paper = { id: '2fc3d2a2a57446a6b9f1090a2a236bc6', title: 'A placeholder title', authors: ['Doe, Jane', 'Roe, Rick', 'Poe, Paul'], year: 2014 };
  check(
    'a document is named by its first author and year, and a long id by its last characters',
    shortCite(paper) === 'Doe et al. 2014' && shortCite({ ...paper, authors: [] }) === 'A placeholder title 2014' && idTail(paper.id) === '…2a236bc6',
    `${shortCite(paper)} · ${idTail(paper.id)}`,
  );
  check('a power of ten is written in superscript, never with a caret', fmt(88467389.96) === '8.85×10⁷' && fmt(6.88e-6) === '6.88×10⁻⁶', `${fmt(88467389.96)} · ${fmt(6.88e-6)}`);
}

// H.0's second sweep: the names a screen reads, held to the rail, the service and the build's own words.
{
  // A note the service keeps whole in a basis (its id hashes the words) reads on a screen with the build's decision
  // tags dropped: a decision, a build document, a rule's constant. A parenthesis of plain words stays.
  const said = [
    plainNote('No death or decay term: zero when absent, said so (D5).'),
    plainNote('Until the sugar runs out (Appendix 2 §A): the first hour (kinetics.RUN_OUT_SHARE). A run stops.'),
    plainNote('Absent: anaerobic. A record of biomass_yield_oxygen (OF-BLD-020 §3.2 added the field) binds it.'),
    plainNote('D8: the medium belongs to the experimenter (STRAIN_FREE).'),
    plainNote('Off when absent, said so, never Ki = 0 (D5 as built, 4). Left out (CARBON_RULE).'),
  ];
  check(
    'a kept note reads on a screen with its decision tags, build documents and constants dropped, its plain parentheses kept',
    said.join(' | ') ===
      'No death or decay term: zero when absent, said so. | Until the sugar runs out: the first hour. A run stops. | ' +
        'Absent: anaerobic. A record of biomass_yield_oxygen binds it. | the medium belongs to the experimenter. | ' +
        'Off when absent, said so, never Ki = 0. Left out.' &&
      plainNote('the Haldane term (Haldane) and 2026-11-08T03:23:03Z') === 'the Haldane term (Haldane) and 2026-11-08 03:23 UTC',
    said.join(' | '),
  );

  // Every destination on the rail is named on Settings → Architecture, read at its rail address.
  const unmapped = RAIL.filter((r) => r.to !== '/' && !COMPONENTS.some((c) => c.owner === r.label && (c.surfacedAs ?? '').includes(r.to)));
  check('every destination on the rail is a named component, read at its rail address', unmapped.length === 0, unmapped.map((r) => r.label).join(', '));

  // A link back to a rail destination names it by its rail label (the reader's crumb said "Library" for BioRepo).
  const SRC = join(import.meta.dirname, '..', 'src');
  const filesUnder = (dir: string): string[] =>
    readdirSync(dir, { withFileTypes: true }).flatMap((d) => {
      const path = join(dir, d.name);
      if (d.isDirectory()) return filesUnder(path);
      return /\.tsx$/.test(d.name) ? [path] : [];
    });
  const labelOf = new Map(RAIL.map((r) => [r.to, r.label]));
  const misnamed: string[] = [];
  const backFromTab: string[] = [];
  for (const path of filesUnder(SRC)) {
    const text = readFileSync(path, 'utf8');
    for (const m of text.matchAll(/<a href=\{href\('(\/[a-z-]+)'\)\}[^>]*>\s*<ArrowLeft[^>]*\/>\s*([^<{]+?)\s*<\/a>/g)) {
      const label = labelOf.get(m[1]);
      if (label && m[2] !== label) misnamed.push(`${relative(SRC, path)}: ${m[2]} for ${label}`);
    }
    // A tab of a destination sits beside its siblings; its header sends nobody back elsewhere.
    if (text.includes('<OwnerTabs') && /actions=\{<LinkButton[^>]*>Back to /.test(text)) backFromTab.push(relative(SRC, path));
  }
  check('a link back to a rail destination names it as the rail does', misnamed.length === 0, misnamed.join('; '));
  check("a destination's tab carries no link back to another destination in its header", backFromTab.length === 0, backFromTab.join(', '));

  // A subsystem the shelf lists as not built has no route of its own on the service (the shelf once called Audit unbuilt
  // while GET /api/audit served the trail).
  const served = new Set(Object.keys((JSON.parse(readFileSync(join(SRC, '..', 'docs', 'api', 'openapi.json'), 'utf8')) as { paths: Record<string, unknown> }).paths));
  const OWNERS: SubsystemOwner[] = ['Intake', 'BioRepo', 'geneOS', 'fermOS', 'pureOS', 'Proforma', 'Guild'];
  const builtAfterAll = OWNERS.flatMap((o) => stubsFor(o)).filter((st) => {
    const [owner, part] = st.id.split('.');
    return served.has(`/api/${part}`) || served.has(`/api/${owner}/${part}`);
  });
  check('no subsystem the shelf calls unbuilt has a route the service serves', builtAfterAll.length === 0, builtAfterAll.map((st) => st.id).join(', '));
}

console.log(fails ? `\n✗ ${fails} check(s) failed` : '\n✓ The project rows are sent as the page changes them, and kept until the service answers; a refusal is never an outage.');
process.exit(fails ? 1 : 0);
