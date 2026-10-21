/**
 * What the store does to records when the world changes (OF-BLD-012.1 F3, F7).
 *
 *   pnpm check:store
 *
 * Two contracts, both about record identity:
 *
 *   F3  the overlay is authoritative — an empty candidate list means empty
 *   F7  a record remembers what it was, in a stored field, not by diffing
 *       against the seed it was loaded from
 *
 * `applyOverlay` is the one action that puts the service's view on top of the
 * seed. It used to KEEP the previous candidate list whenever the new one was
 * empty, which was meant for a partial overlay — but `overlay_bundle()` always
 * sends the full lists, so a cleared cache on the service left stale
 * candidates on Witness and in the review queue until a reload. An empty list
 * now means empty; only `null` means "not supplied".
 *
 * The other half is what happens to the RECORDS those candidates became. A
 * candidate nobody has decided on is the extractor's current opinion and goes
 * when the opinion does. One a reviewer decided is a decision, and a decision
 * does not evaporate because a re-extraction stopped producing the sentence —
 * it stays, labelled, so the reviewer can see what happened to it.
 *
 * Driven against the real seeded store rather than a fixture, so a regression
 * in `applyOverlay` fails the build instead of being found by a reviewer
 * wondering why a record they rejected came back.
 */
import { readFileSync } from 'node:fs';
import {
  assumptionOfOverride,
  isExample,
  mergeAssumptions,
  overrideEnds,
  overrideOfAssumption,
  overridesFor,
  programOf,
  programVisible,
  proformaScope,
  snapshotOf,
  useStore,
} from '../src/store';
import { RECORDS } from '../src/data/records';
import { PRODUCTS } from '../src/data/products';
import { lockIntact } from '../src/engine/lock';
import { placeRow, seriesOf } from '../src/engine/series';
import type { Artifact, BasisSource, Candidate, FlowsheetInfo, Overlay, Override, ProformaScenarioInfo, Scenario } from '../src/data/types';
import { visibleArtifacts } from '../src/lib/artifacts';
import { COMPOSITE_FLOWSHEET, inputCounts, partsOf, referencePrice, runBody, runOverrides, scenarioFromVesselAndTrain } from '../src/lib/proforma';
import { resolveRequest } from '../src/lib/params';
import * as ts from 'typescript';
import { readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';

let fails = 0;
const check = (label: string, ok: boolean, extra: unknown = '') => {
  console.log(`${ok ? '✓' : '✗'} ${label}${extra === '' ? '' : `  ${JSON.stringify(extra)}`}`);
  if (!ok) fails++;
};

const s = () => useStore.getState();

// A paper with a fetched-looking text, and three fields the seed has no
// record of on it — so every candidate below is NEW and joins the records.
const paper = s().papers[0];
const taken = new Set(s().records.filter((r) => r.paperId === paper.id).map((r) => r.field));
const FIELDS = ['titer_secreted', 'growth_rate_mu', 'time_to_colony'].filter((f) => !taken.has(f as never));
if (FIELDS.length < 3) {
  console.error(`✗ the seed's first paper already has records for ${[...taken].join(', ')}`);
  process.exit(1);
}

const candidate = (n: number, field: string): Candidate =>
  ({
    id: `cl1-${paper.id}-overlay${n}`,
    paperId: paper.id,
    sectionId: 's1',
    quote: `a sentence the extractor read, number ${n}`,
    field,
    value: n,
    unit: 'g L⁻¹',
    si: { value: n, unit: 'kg m⁻³' },
    confidence: 0.8,
    status: 'unverified',
    provenance: 'unverified',
    isPrimary: true,
    extractorRun: 'claude-1',
  }) as Candidate;

const THREE = FIELDS.map((f, i) => candidate(i + 1, f));
const overlay = (over: Partial<Overlay>): Overlay =>
  ({ papers: {}, records: {}, candidates: [], runs: [], ...over }) as Overlay;

const ours = () => s().records.filter((r) => THREE.some((c) => c.id === r.id));

// The store must not try to post anything: this is about the overlay.
useStore.setState({ serviceUp: false, decisionAt: {}, durableReview: null });

// 1. Three candidates arrive and become records.
useStore.getState().applyOverlay(overlay({ candidates: THREE }));
check('three candidates joined the records', ours().length === 3, ours().map((r) => r.id));
check('with no queue open, an arriving candidate does not force one', s().reviewQueue.length === 0, s().reviewQueue.length);

// 2. An empty list means the extractor produced nothing. Undecided
//    candidates are the extractor's current opinion, and go with it.
useStore.getState().applyOverlay(overlay({ candidates: [] }));
check('an empty candidate list removes the undecided ones', ours().length === 0, ours().map((r) => r.id));
check('and the store forgot them in the overlay too', (s().overlay?.candidates ?? []).length === 0);

// 3. A decided candidate is a decision, not an opinion. It stays.
useStore.getState().applyOverlay(overlay({ candidates: THREE }));
useStore.getState().reviewDecide(THREE[0].id, 'reject', { reason: 'not this field' });
check('the decision landed', s().records.find((r) => r.id === THREE[0].id)?.status === 'rejected');
useStore.getState().applyOverlay(overlay({ candidates: [] }));
const kept = ours();
check('the decided candidate survived the empty list', kept.length === 1 && kept[0].id === THREE[0].id, kept.map((r) => r.id));
check('and is labelled as gone from the current run', kept[0]?.absentFromRun === true);
check('the undecided two went', !ours().some((r) => r.id === THREE[1].id || r.id === THREE[2].id));

// 4. `null` is the only thing that means "not supplied".
const before = s().records.length;
useStore.getState().applyOverlay(overlay({ candidates: null as never, runs: null as never }));
check('a null candidate list changes nothing', s().records.length === before, { before, after: s().records.length });
check('and leaves the overlay it had', (s().overlay?.candidates ?? []).length === 0);

// 5. A candidate that comes back is no longer labelled.
useStore.getState().applyOverlay(overlay({ candidates: THREE }));
check(
  'a returning candidate loses the label',
  s().records.find((r) => r.id === THREE[0].id)?.absentFromRun !== true,
);
check('and its decision is still there', s().records.find((r) => r.id === THREE[0].id)?.status === 'rejected');

// 6. §7.3 — a candidate that arrives while a queue is OPEN joins it. The
//    smoke was the only place this was checked, by opening Guild cold and
//    racing the double's delayed overlay against the queue's own seeding.
//    F9 made that seeding wait for /api/health, so the race is gone and the
//    contract needs a home that is not a clock.
useStore.getState().applyOverlay(overlay({ candidates: [] }));
const open = s().records.filter((r) => r.status === 'unverified').slice(0, 5).map((r) => r.id);
useStore.getState().startReview(open);
check('a queue is open', s().reviewQueue.length === open.length, s().reviewQueue.length);
useStore.getState().applyOverlay(overlay({ candidates: THREE }));
check(
  'an undecided candidate arriving joins the open queue',
  [THREE[1], THREE[2]].every((c) => s().reviewQueue.includes(c.id)),
  s().reviewQueue.slice(-3),
);
check('a decided one does not queue itself for review again', !s().reviewQueue.includes(THREE[0].id));
check('and the records already queued are still queued', open.every((id) => s().reviewQueue.includes(id)));

// ── F7 — a record remembers what it was ──────────────────────────────
//
// `reanchoredSpan` used to decide whether a promotion had moved a record's
// quote by comparing it against the SEED the store was built from. A corpus
// update that rewrote a decided record's quote would then make that record
// look re-anchored, and the sync would post the seed's new sentence as if
// the reviewer had chosen it. The original is a stored field now.

const posted: { quote?: string; sectionId?: string; recordId: string }[] = [];
(globalThis as any).fetch = async (url: string, init?: { body: string }) => {
  if (String(url).includes('/api/biorepo/')) {
    const body = JSON.parse(init!.body);
    if (String(url).endsWith('/decisions')) posted.push(body);
    return { status: 200, ok: true, json: async () => (String(url).endsWith('/check') ? { ok: true } : body) };
  }
  throw new Error('no service');
};

const seeded = s().records.find((r) => r.extractorRun !== 'claude-1')!;
check('a seeded record carries what it was published as', !!seeded.original, seeded.original);
check(
  'and it is the record as the seed wrote it',
  seeded.original?.quote === seeded.quote && seeded.original?.value === seeded.value,
);
const arrived = s().records.find((r) => r.id === THREE[0].id)!;
check('an arriving candidate carries it too', arrived.original?.quote === THREE[0].quote, arrived.original);

// A record still standing on its own sentence posts no span, even when the
// sentence the SEED now holds has moved on.
const identified = s().papers.find((p) => p.pmcid || p.doi || p.pmid)!;
const onIts = { ...seeded, paperId: identified.id, quote: 'the sentence this record has always stood on', sectionId: 's1' };
useStore.setState({
  serviceUp: true,
  reviewer: 'Sam Okonkwo',
  records: s().records.map((r) => (r.id === seeded.id ? { ...onIts, original: { value: onIts.value, unit: onIts.unit, quote: onIts.quote, sectionId: 's1' } } : r)),
});
posted.length = 0;
useStore.getState().editRecord(seeded.id, 42, 'g L⁻¹');
await new Promise((r) => setTimeout(r, 20));
check('an unmoved record posts no span, whatever the seed now says', posted[0] === undefined || posted[0].quote === undefined, posted[0]);

// A record a promotion re-anchored posts the sentence it was moved to.
useStore.setState({
  records: s().records.map((r) =>
    r.id === seeded.id
      ? { ...r, quote: 'the sentence a promotion moved it to', sectionId: 's2' }
      : r,
  ),
});
posted.length = 0;
useStore.getState().editRecord(seeded.id, 43, 'g L⁻¹');
await new Promise((r) => setTimeout(r, 20));
check('a re-anchored record posts the sentence it was moved to', posted[0]?.quote === 'the sentence a promotion moved it to', posted[0]?.quote);

// ── §6.9 — what a review of the branch found ─────────────────────────

// 7. F3 again — a live FETCH is a paper arriving, not an extractor saying
//    nothing. `ingestPaperLive` applies its result through `applyOverlay`,
//    and sent it with `candidates: []` and `runs: []`; under F3 those read
//    as "the extractor produced nothing", so every fetch wiped the undecided
//    candidates from the store and the queue. A fetch supplies papers only.
(globalThis as any).fetch = async (url: string, init?: { body: string }) => {
  const u = String(url);
  if (/\/api\/intake\/[^/]+\/fetch/.test(u)) {
    return {
      ok: true,
      status: 200,
      json: async () => ({
        paperId: paper.id,
        pmcid: 'PMC0000000',
        status: 'complete',
        reason: null,
        fetchedAt: new Date().toISOString(),
        license: null,
        sections: [{ id: 's1', heading: 'Results', text: 'a sentence the extractor read, number 1' }],
        bytes: 1,
      }),
    };
  }
  if (u.includes('/api/biorepo/')) {
    const body = JSON.parse(init!.body);
    if (u.endsWith('/decisions')) posted.push(body);
    return { status: 200, ok: true, json: async () => (u.endsWith('/check') ? { ok: true } : body) };
  }
  throw new Error('no service');
};
useStore.setState({ serviceUp: true });
useStore.getState().applyOverlay(overlay({ candidates: THREE }));
check('three candidates are in the store before the fetch', ours().length === 3);
await useStore.getState().ingestPaperLive(paper.id);
check('the paper now carries its text', s().papers.find((p) => p.id === paper.id)?.textSource === 'full-text');
check('a live fetch leaves the extractor’s candidates where they were', ours().length === 3, ours().map((r) => r.id));
check('and the overlay still carries them', (s().overlay?.candidates ?? []).length === 3, (s().overlay?.candidates ?? []).length);

// 8. The reviewer stays on their card when the queue is pruned under them.
//    `applyOverlay` dropped gone records from the queue and left
//    `reviewIndex` pointing at a position, so the card under the reviewer
//    changed — or the index ran past the end and Guild showed "complete"
//    mid-review. The index follows the RECORD; a reviewer whose record went
//    lands on the next survivor.
const seedIds = s()
  .records.filter((r) => r.status === 'unverified' && r.extractorRun !== 'claude-1')
  .slice(0, 3)
  .map((r) => r.id);
useStore.getState().startReview([THREE[1].id, THREE[2].id, ...seedIds]);
useStore.setState({ reviewIndex: 3 });
useStore.getState().applyOverlay(overlay({ candidates: [] }));
check('the queue lost the two undecided candidates', s().reviewQueue.length === 3, s().reviewQueue);
check('and the reviewer is still on the same card', s().reviewQueue[s().reviewIndex] === seedIds[1], {
  index: s().reviewIndex,
  card: s().reviewQueue[s().reviewIndex],
});
useStore.getState().applyOverlay(overlay({ candidates: THREE }));
useStore.getState().startReview([THREE[1].id, THREE[2].id, ...seedIds]);
useStore.setState({ reviewIndex: 1 });
useStore.getState().applyOverlay(overlay({ candidates: [] }));
check('a reviewer whose card went lands on the next survivor, not past the end', s().reviewQueue[s().reviewIndex] === seedIds[0], {
  index: s().reviewIndex,
  length: s().reviewQueue.length,
});

// 9. F7 again — withdrawing a correction restores the SENTENCE as well as
//    the number. A promotion that carried the extractor's span and the
//    paper's number, withdrawn, put the published number back beside the
//    carried sentence: a record whose quote no longer states its value.
const fresh = s().records.find((r) => r.extractorRun !== 'claude-1' && r.id !== seeded.id && !s().decisionAt[r.id])!;
const moved = { quote: 'the sentence a promotion moved it to', sectionId: 's2' };
useStore.getState().applyOverlay(
  overlay({
    records: {
      [fresh.id]: {
        status: 'verified', provenance: 'curated', reviewer: 'Sam Okonkwo', recordId: fresh.id,
        at: '2026-09-21T00:00:01Z', corrected: { value: 42, unit: 'g L⁻¹' }, ...moved,
      },
    } as never,
  }),
);
const carried = s().records.find((r) => r.id === fresh.id)!;
check('a promotion with a span moves the record onto it', carried.quote === moved.quote && carried.value === 42);
useStore.getState().applyOverlay(
  overlay({
    records: {
      [fresh.id]: {
        status: 'unverified', provenance: 'curated', reviewer: 'Sam Okonkwo', recordId: fresh.id,
        at: '2026-09-21T00:00:02Z',
      },
    } as never,
  }),
);
const back = s().records.find((r) => r.id === fresh.id)!;
check('withdrawing it restores the published number', back.value === fresh.original?.value, back.value);
check('and the published sentence with it', back.quote === fresh.original?.quote && back.sectionId === fresh.original?.sectionId, {
  quote: back.quote,
  sectionId: back.sectionId,
});

// ── OF-BLD-014 §7.1 — a deposition's readings become a time series ────
{
  const rb = s().runbooks.find((r) => r.measurementSchema.some((m) => m.id === 'ms-taq-od'))!;
  const dep = {
    id: 'dep-series-check', runbookId: rb.id, protocolId: 'p', operatorId: null, startedAt: '2026-10-15T00:00:00Z',
    closedAt: null, state: 'running' as const, entries: [], observations: [], reconciliation: null,
  };
  useStore.setState({ depositions: [dep, ...s().depositions] });
  // Rows out of time order, one the schema cannot place, one that is not a row.
  const r = s().attachReadings(dep.id, [
    'time_h, measure, value, unit',
    '6, Cell density at harvest, 3.1, OD600',
    '0, Cell density at harvest, 0.2, OD600',
    '3, Titre at harvest, 0.4, g/L',
    '2, mystery glow, 7, lumens',
    'a note with no time',
    '3, Cell density at harvest, 1.1, OD600',
  ].join('\n'));
  const d = () => s().depositions.find((x) => x.id === dep.id)!;
  check('a CSV attaches the rows it can place, and keeps every other line as an observation', r.attached === 4 && r.kept === 2, r);
  check('each attached row is unconfirmed, its raw the CSV line', d().entries.every((e) => !e.confirmed && e.stepId === 'attached' && /, /.test(e.raw)));
  check('the unplaceable row is kept word for word', d().observations.some((o) => o.raw === '2, mystery glow, 7, lumens'));
  check('rows attach in time order, so the last entry is the last reading', d().entries.filter((e) => e.measureId === 'ms-taq-od').map((e) => e.value).join() === '0.2,1.1,3.1');
  const od = seriesOf(d(), rb).find((x) => x.measureId === 'ms-taq-od');
  check('seriesOf orders a measure\'s readings by time', od?.points.map((p) => p.t).join() === '0,3,6', od?.points);
  check('a measure with one reading is no series', !seriesOf(d(), rb).some((x) => x.measureId === 'ms-taq-titre'));
  const mid = d().entries.find((e) => e.value === 1.1)!;
  s().amendEntry(dep.id, mid.id, 1.3);
  const after = seriesOf(d(), rb).find((x) => x.measureId === 'ms-taq-od')!;
  check('a correction keeps its reading\'s time and replaces it in the series', after.points.map((p) => p.value).join() === '0.2,1.3,3.1', after.points);
  s().setSampleTime(dep.id, d().entries.find((e) => e.value === 3.1)!.id, null);
  check('a reading taken out of time leaves the series', seriesOf(d(), rb).find((x) => x.measureId === 'ms-taq-od')!.points.length === 2);
  s().setSeriesRole(dep.id, 'ms-taq-od', 'biomass');
  check('a person assigns a series its role', seriesOf(d(), rb).find((x) => x.measureId === 'ms-taq-od')!.role === 'biomass');
  check('the Durable snapshot carries times and roles', (() => {
    const snap = snapshotOf(s());
    const kept = snap.depositions.find((x) => x.id === dep.id)!;
    return Object.keys(kept.sampleTimes ?? {}).length === 4 && kept.seriesRoles?.['ms-taq-od'] === 'biomass';
  })());
  useStore.setState({ depositions: s().depositions.filter((x) => x.id !== dep.id) });
}

// §7.R — a row is placed by its measure's name, never by its unit alone.
{
  const schema = [
    { id: 'titre', label: 'PHB titre', unit: 'g/L', timepoint: '', predictionId: null },
    { id: 'glc', label: 'Residual glucose', unit: 'g/L', timepoint: '', predictionId: null },
  ];
  const at = (measure: string) => placeRow({ line: '', time: 1, measure, value: 5, unit: 'g/L' }, schema);
  check('a row names its measure: glucose and titre place', at('glucose') === 'glc' && at('PHB titre') === 'titre' && at('titre') === 'titre');
  check('a row whose name matches no measure is not placed by its unit', [at('sugar'), at('biomass'), at('cdw')].every((x) => x === null), [at('sugar'), at('biomass'), at('cdw')]);
}

// §8.R — Proforma's assumptions merge by input key at hydrate: one typed
// before the snapshot loads keeps every other one the snapshot saved.
{
  const a = (key: string, value: number) => ({ key, value, low: value, high: value, by: 'Sean Creighton', at: '2026-10-15', note: null });
  const merged = mergeAssumptions({ 'sc-pha-1': [a('recovery', 0.9), a('sugarPrice', 0.4)] }, { 'sc-pha-1': [a('sugarPrice', 0.5)] });
  const keys = merged['sc-pha-1'].map((x) => `${x.key}=${x.value}`).sort().join();
  check('an assumption typed before hydrate keeps the saved ones beside it', keys === 'recovery=0.9,sugarPrice=0.5', keys);
}

// §9.2 — a drafted runbook adopted here is a research runbook, unlocked,
// with the service's predictions; it and its lock survive a reload (the
// snapshot applied to a store that has lost it).
{
  const st = () => useStore.getState();
  const draft = {
    title: 'Secreted titre on xylose', productId: 'taq-dna-polymerase', strainId: 'c-necator-h16',
    predictions: [{ id: 'p1', label: 'Secreted titre', value: 0.9, unit: 'g L⁻¹', confidence: 'low' as const, basis: 'Range of 2 reported values: a, b', kind: 'interval' as const, interval: { low: 0.8, high: 1 }, recordIds: ['a', 'b'] }],
    measures: [{ id: 'm1', label: 'Titre at harvest', unit: 'g/L', timepoint: 'harvest', predictionId: 'p1' }],
  };
  const id = st().adoptRunbookDraft(draft);
  const made = st().runbooks.find((r) => r.id === id)!;
  check('an adopted draft is a research runbook, unlocked, with the service\'s predictions',
    made.kind === 'research' && made.lockedAt === null && made.predictions[0].interval?.high === 1 && made.measurementSchema[0].predictionId === 'p1');
  st().lockRunbook(id);
  const hash = st().runbooks.find((r) => r.id === id)!.lockHash;
  const snap = snapshotOf(st());
  check('the snapshot carries the adopted runbook and its lock', snap.adoptedRunbooks?.some((r) => r.id === id) === true && snap.runbookLocks[id]?.lockHash === hash);
  useStore.setState((s) => ({ runbooks: s.runbooks.filter((r) => r.id !== id), adoptedRunbookIds: [] }));
  st().applyDurable(snap);
  const back = st().runbooks.find((r) => r.id === id);
  check('after a reload the adopted runbook is back, locked, and its content hashes to its lock',
    !!back && back.lockHash === hash && lockIntact(back) && Object.isFrozen(back.predictions) && st().adoptedRunbookIds.includes(id));
}

// Postdoc's Live conversations are Durable: a question, its steps and its
// plan survive a reload; a turn the reload cut short says so; one this page
// started since loading is kept beside the saved ones; a reset clears them.
{
  const st = () => useStore.getState();
  const id = st().startLiveConversation('What growth rate does CEN.PK113-7D reach?');
  const turn = (tid: string, status: 'answered' | 'running') => ({
    id: tid, question: 'What growth rate does CEN.PK113-7D reach?', askedAt: '2026-10-20 09:00',
    steps: [], plan: null, error: null, status, replay: null,
  });
  st().addLiveTurn(id, turn('lt-a', 'answered'));
  st().addLiveTurn(id, turn('lt-b', 'running'));
  st().patchLiveTurn(id, 'lt-a', { step: { n: 1, kind: 'tool', tool: 'search_records', input: { query: 'growth rate' }, summary: 'Looked up records of growth rate · 0 records', ms: 3, ok: true } });
  const snap = snapshotOf(st());
  check('the snapshot carries the conversation and its steps',
    snap.liveConversations?.find((c) => c.id === id)?.turns.find((t) => t.id === 'lt-a')?.steps.length === 1);
  const fresh = st().startLiveConversation('Asked after the page loaded');
  useStore.setState((s) => ({ liveConversations: s.liveConversations.filter((c) => c.id !== id) }));
  st().applyDurable(snap);
  const back = st().liveConversations.find((c) => c.id === id);
  check('after a reload the conversation is back with both turns', back?.turns.map((t) => t.id).join() === 'lt-a,lt-b');
  check('a turn the reload cut short reads interrupted', back?.turns.find((t) => t.id === 'lt-b')?.status === 'interrupted');
  check('a conversation started since the page loaded is kept, first', st().liveConversations[0]?.id === fresh);
  // OF-BLD-016 §3.1 — a question the service never received is taken back:
  // its turn goes, the turns before it stay, and a conversation made for it
  // alone goes with it.
  st().addLiveTurn(id, turn('lt-c', 'running'));
  st().dropLiveTurn(id, 'lt-c');
  check('a turn the service never received is taken back, and the turns before it stay',
    st().liveConversations.find((c) => c.id === id)?.turns.map((t) => t.id).join() === 'lt-a,lt-b');
  st().addLiveTurn(fresh, turn('lt-d', 'running'));
  st().dropLiveTurn(fresh, 'lt-d');
  check('a conversation made for an unreceived question goes with it', !st().liveConversations.some((c) => c.id === fresh));
  st().clearBrowserData();
  check('Clearing this browser\u2019s data clears the conversations', st().liveConversations.length === 0);
}

// OF-BLD-016 §2.1 — whether archived programs show is Durable: the switch
// survives a reload, a snapshot from before programs existed leaves it where
// it is, and it starts off. The selector every screen calls answers from it.
{
  const st = () => useStore.getState();
  check('archived programs start hidden', st().showArchived === false && !programVisible('paper', 'P1', st()) && programVisible('paper', 'Q1', st()));
  st().setShowArchived(true);
  const snap = snapshotOf(st());
  check('the snapshot carries the switch', snap.showArchived === true, snap.showArchived);
  st().setShowArchived(false);
  st().applyDurable(snap);
  check('after a reload the switch is back on, and an archived paper shows', st().showArchived === true && programVisible('paper', 'P1', st()));
  st().setShowArchived(false);
  const { showArchived: _dropped, ...older } = snapshotOf(st());
  st().applyDurable(older);
  check('a snapshot from before programs leaves the switch where it is', st().showArchived === false);
  check('a general entity shows with the switch off', programVisible('strain', 's-cerevisiae', st()));
  check('an archived strain does not', !programVisible('strain', 'c-necator-h16', st()));
  check('a record shows as its paper does', programOf('record', RECORDS.find((r) => r.paperId.startsWith('H'))!.id, st()) === 'casein');
}

// OF-BLD-016 §3.3 (D3) — an example is treated as archived: a general seed
// runbook that describes a run nobody made is hidden with the switch off and
// shows with it on; a general protocol that teaches a method stays; a lesson
// takes its module's flag; a copy of an example scenario stays an example;
// and a deposition a person starts from an example runbook is not one.
{
  const st = () => useStore.getState();
  st().setShowArchived(false);
  check('an example runbook is general, yet hidden with the switch off',
    programOf('runbook', 'rb-taq-kigali', st()) === null && isExample('runbook', 'rb-taq-kigali', st()) && !programVisible('runbook', 'rb-taq-kigali', st()));
  check('no seed runbook shows with the switch off', st().runbooks.every((r) => !programVisible('runbook', r.id, st())));
  check('the generic protocols show with the switch off', programVisible('protocol', 'PR-OD-01', st()) && programVisible('protocol', 'PR-CIP-01', st()));
  check('a lesson of an example module is an example', isExample('lesson', st().modules.find((m) => m.id === 'm0')!.lessons[0].id, st()));
  check('the bench-track lessons show with the switch off', st().modules.find((m) => m.id === 'm6')!.lessons.every((l) => programVisible('lesson', l.id, st())));
  st().setShowArchived(true);
  check('the switch brings every example back', st().runbooks.every((r) => programVisible('runbook', r.id, st())));
  st().setShowArchived(false);
  const copyId = st().duplicateScenario('sc-s1');
  check('a copy of an example scenario stays an example', isExample('scenario', copyId, st()) && !programVisible('scenario', copyId, st()), copyId);
  check('a deposition is an example only by its own flag',
    !isExample('deposition', 'dep-x', { ...st(), depositions: [{ id: 'dep-x', runbookId: 'rb-taq-kigali', protocolId: 'PR-OD-01' } as never] }));
  st().clearBrowserData();
}

// OF-BLD-016 §3.R — a research handoff, a promotion, a resume and an
// authorisation invent nothing: no ETA, no cost, no progress figure, no
// locked count, and no timed job with no work behind it.
{
  const st = () => useStore.getState();
  const before = st().jobs.length;
  const invented = (id: string | null) => {
    const r = st().runbooks.find((x) => x.id === id);
    return !r || r.eta !== null || r.estCostUsd !== null || (r.status !== 'complete' && r.progressPct !== 0) ||
      r.predictions.some((p) => typeof p.value === 'number' && p.value > 0);
  };
  const states = [...new Set(st().products.map((p) => p.clearanceState))];
  const opened = states.map((c) => st().handoffToResearchRunbook(st().products.find((p) => p.clearanceState === c)!.id));
  check('a research handoff invents no ETA, cost, progress or count', opened.every((id) => !invented(id)), opened.filter(invented));
  const promoted = opened.map((id) => st().promoteRunbook(id!)).filter(Boolean);
  check('a promotion invents no ETA, cost, progress or count', promoted.every((id) => !invented(id)), promoted.filter(invented));
  const blocked = st().runbooks.find((r) => r.status === 'blocked_unverified');
  if (blocked) {
    st().resolveRunbookInput(blocked.id, 'source');
    check('a resume sets no ETA', st().runbooks.find((r) => r.id === blocked.id)!.eta === null);
  }
  const waiting = st().runbooks.find((r) => r.status === 'awaiting_budget');
  if (waiting) st().authoriseRunbookBudget(waiting.id);
  check('none of them starts a timed job', st().jobs.length === before, st().jobs.slice(before).map((j) => j.title));
  st().clearBrowserData();
}

// OF-BLD-016 §3.R — clearing this browser's data returns it to the shipped
// state, and the shipped state has archived programs hidden.
{
  const st = () => useStore.getState();
  st().setShowArchived(true);
  st().clearBrowserData();
  check('Clearing this browser\u2019s data turns the archive switch off', st().showArchived === false && snapshotOf(st()).showArchived === false);
}

// OF-BLD-016 §2.R — a computed artifact follows what its basis names: a
// record (by its paper, a candidate's id included), a product or a strain.
// BioRepo → Artifacts and Settings → Figure grammar list through it, so a
// PHB ceiling or a thread P conversion hides with the switch off.
{
  const st = () => useStore.getState();
  const src = (kind: BasisSource['kind'], id: string | null = null): BasisSource => ({ kind, id, note: null, by: null });
  const art = (id: string, inputs: Artifact['inputs']): Artifact => ({
    id, tool: 't', toolVersion: 'v', inputs, output: {}, outputHash: '', provenance: 'computed', createdAt: '', durationMs: 0, seed: null,
  });
  const list = [
    art('phb-ceiling', [{ name: 'model', value: 'E. coli core', unit: '', source: src('model', 'e_coli_core') }, { name: 'product', value: 'phb', unit: '', source: src('convention') }]),
    art('p-conversion', [{ name: 'record value', value: 'x', unit: '', source: src('record', 'cl1-P6-ef418c6a') }]),
    art('b5-conversion', [{ name: 'record value', value: 'x', unit: '', source: src('record', 'r-B5-3') }]),
    art('ethanol-ceiling', [{ name: 'model', value: 'iMM904', unit: '', source: src('model', 'iMM904') }, { name: 'product', value: 'ethanol', unit: '', source: src('convention') }]),
    art('benchmark', [{ name: 'model', value: 'cornstover', unit: '', source: src('model', 'biorefineries.cornstover@2.35.1') }]),
  ];
  st().setShowArchived(false);
  const shown = visibleArtifacts(list, st()).map((a) => a.id).join();
  check('with the switch off, artifacts computed from casein or PHA inputs are not listed', shown === 'ethanol-ceiling,benchmark', shown);
  st().setShowArchived(true);
  check('with the switch on, every artifact is listed', visibleArtifacts(list, st()).length === list.length);
  st().setShowArchived(false);
}

// OF-BLD-016 §3.R — Settings → About says what this build does. The
// sentences a review found false are gone, and the one it now makes about
// what survives a refresh is held against the snapshot itself.
{
  const about = readFileSync(new URL('../src/screens/Settings.tsx', import.meta.url), 'utf8');
  for (const said of ['No extractor has ever been run', 'held in memory only', 'There is no database, no account and no server', 'No document is retrieved', 'No full\n              text has been retrieved']) {
    check(`Settings → About no longer says "${said.replace(/\s+/g, ' ')}"`, !about.includes(said));
  }
  const snap = snapshotOf(useStore.getState()) as unknown as Record<string, unknown>;
  const kept = ['depositions', 'liveConversations', 'showArchived'];
  check('what About says survives a refresh is in the Durable snapshot', kept.every((k) => k in snap), kept.filter((k) => !(k in snap)));
}

// OF-BLD-016 §2.R — Intake → Ingest's header counts what shows; it never
// states the casein catalogue's counts in writing.
{
  const ingest = readFileSync(new URL('../src/screens/IntakeIngest.tsx', import.meta.url), 'utf8');
  check('Intake → Ingest states no written count of the catalogue', !/Twenty-seven|of the 132 entries/.test(ingest));
}

// OF-BLD-016 §2.R — BioRepo → Search's status line counts the whole index,
// which holds every program's passages; with archived programs hidden it
// says so, since a search returns only what shows.
{
  const search = readFileSync(new URL('../src/screens/BioRepoSearch.tsx', import.meta.url), 'utf8');
  check('BioRepo → Search does not present the whole index as what a search reaches',
    !/\{status\.passages\.toLocaleString\(\)\} passages from \{status\.papersIndexed\} papers\.\{' '\}/.test(search) && /every program/.test(search));
}

// OF-BLD-016 §2.R — pureOS counts the molecules that show, as Dominion and
// Home do: it never counts the seed's product list straight.
{
  const pure = readFileSync(new URL('../src/screens/PureOS.tsx', import.meta.url), 'utf8');
  check('pureOS counts products through the program filter', !/PRODUCTS\.length|of PRODUCTS\)|PRODUCTS\.filter\(\(p\) => \(p\.unitOperationIds/.test(pure) && /shows\('product'/.test(pure));
  const shownProducts = PRODUCTS.filter((p) => programVisible('product', p.id, { ...useStore.getState(), showArchived: false })).length;
  check('with the switch off, fewer products show than the catalogue holds', shownProducts < PRODUCTS.length, [shownProducts, PRODUCTS.length]);
}

// OF-BLD-016 §2.R — fermOS offers the runs Runbooks → Depositions shows: a
// deposition of an archived protocol is not in its chooser.
{
  const ferm = readFileSync(new URL('../src/screens/FermOS.tsx', import.meta.url), 'utf8');
  check("fermOS filters its runs through shows('deposition')", /shows\('deposition', d\.id\)/.test(ferm));
}

// OF-BLD-019 §3.1 (D5, D6) — New scenario makes a `biosteam` scenario on a
// shelf flowsheet, and it is Durable: it survives a reload keyed by id, with
// its flowsheet, name, program, pin, the assumptions typed for it and the id
// of its newest run; a seeded scenario's newest run survives beside it; a
// copy is made the same way; clearing this browser's data drops it. The
// index's button opens the chooser: it never copies the first scenario in a
// list, and it is never disabled because the list is empty (B.1).
{
  const st = () => useStore.getState();
  st().setShowArchived(false);
  const id = st().createScenario('ethanol_glucose_v0', 'Glucose to ethanol, a first look', 'yeast');
  const other = st().createScenario('ethanol_glucose_v0', 'A second one', 'yeast');
  const made = st().scenarios.find((x) => x.id === id);
  check('New scenario makes a biosteam scenario on its flowsheet, in its program, holding no input value and not run',
    !!made && made.kind === 'biosteam' && made.flowsheetId === 'ethanol_glucose_v0' && made.program === 'yeast' &&
      made.lastRunId === null && made.dims.length === 0 && Object.keys(made.point).length === 0 && made.assumptions.length === 0);
  check('its id is time-based and its own', /^sc-[0-9a-z]+-\d+$/.test(id) && id !== other, [id, other]);
  check('a scenario made in the active program shows with the switch off', programVisible('scenario', id, st()));
  st().togglePin(id);
  const typed = { key: 'glucose_price', value: 0.3, low: 0.2, high: 0.4, by: 'Sean Creighton', at: '2026-10-20', note: null };
  st().setProformaAssumption(id, typed);
  st().recordScenarioRun(id, 'a1b2c3d4e5f60718');
  st().recordScenarioRun('sc-pha-1', '0f1e2d3c4b5a6978');
  // OF-BLD-019 §3.3 — a seeded scenario pinned to compare stays pinned.
  st().togglePin('sc-yeast-1');
  const snap = snapshotOf(st());
  const kept = snap.createdScenarios?.[id];
  check('the snapshot keeps a scenario made here by id, with its flowsheet, name, program, pin and newest run',
    !!kept && kept.flowsheetId === 'ethanol_glucose_v0' && kept.name === 'Glucose to ethanol, a first look' &&
      kept.program === 'yeast' && kept.pinned === true && kept.lastRunId === 'a1b2c3d4e5f60718');
  check("a seeded scenario's newest run rides beside them, and the seed is not saved whole",
    snap.scenarioRuns?.['sc-pha-1'] === '0f1e2d3c4b5a6978' && !snap.createdScenarios?.['sc-pha-1'] && !snap.createdScenarios?.['sc-s1'],
    snap.scenarioRuns);
  check('the snapshot names the seeded scenarios pinned here, and no other, and no scenario made here',
    JSON.stringify(snap.pinnedScenarios) === JSON.stringify(['sc-yeast-1']), snap.pinnedScenarios);
  // A reload: a store that has lost both, and the assumptions typed for it.
  useStore.setState((s) => ({
    scenarios: s.scenarios
      .filter((x) => x.id !== id && x.id !== other)
      .map((x) => (x.id === 'sc-pha-1' ? { ...x, lastRunId: null } : x.id === 'sc-yeast-1' ? { ...x, pinned: false } : x)),
    createdScenarioIds: [],
    proformaAssumptions: {},
  }));
  st().applyDurable(snap);
  const back = st().scenarios.find((x) => x.id === id);
  check('after a reload the scenario made here is back, whole, and counted as made here',
    !!back && back.flowsheetId === 'ethanol_glucose_v0' && back.pinned && back.lastRunId === 'a1b2c3d4e5f60718' &&
      st().createdScenarioIds.includes(id) && st().createdScenarioIds.includes(other));
  check('the assumption typed for it is back under its id', st().proformaAssumptions[id]?.[0]?.value === 0.3);
  check('the seeded scenario has its newest run back', st().scenarios.find((x) => x.id === 'sc-pha-1')?.lastRunId === '0f1e2d3c4b5a6978');
  check('the seeded scenario pinned here is pinned again after a reload, and no other seeded one',
    st().scenarios.find((x) => x.id === 'sc-yeast-1')?.pinned === true &&
      st().scenarios.filter((x) => !st().createdScenarioIds.includes(x.id) && x.pinned).map((x) => x.id).join() === 'sc-yeast-1');
  st().applyDurable(snap);
  check('a second hydrate does not make it twice', st().scenarios.filter((x) => x.id === id).length === 1 && st().createdScenarioIds.filter((x) => x === id).length === 1);
  const copy = st().duplicateScenario(id);
  const copied = st().scenarios.find((x) => x.id === copy);
  check('a copy of it is made the same way: its own time-based id, Durable, the same flowsheet, not run',
    copy !== id && st().createdScenarioIds.includes(copy) && copied?.flowsheetId === 'ethanol_glucose_v0' && copied?.lastRunId === null && copied?.program === 'yeast');
  const pha = st().createScenario('pha_sugar_v0', 'PHA, made with the switch on', 'pha');
  check('a scenario made in an archived program hides with the switch off and its link still names the program',
    !programVisible('scenario', pha, st()) && programOf('scenario', pha, st()) === 'pha');
  // OF-BLD-020 §6.1 (D11): a scenario on custom_train_v1 keeps the vessel
  // design and the train run it is built from, through a reload, a copy and
  // the helper pureOS's Builder calls; a scenario on any other flowsheet keeps
  // neither, and clearing this browser's data drops it with the rest.
  const vesselId = 'a1a1a1a1a1a1a1a1';
  const trainRunId = 'b2b2b2b2b2b2b2b2';
  const seam = st().createScenario(COMPOSITE_FLOWSHEET, 'A vessel and a train', 'yeast', { vessel: vesselId, trainRun: trainRunId });
  const seamSnap = snapshotOf(st());
  const keptSeam = seamSnap.createdScenarios?.[seam];
  check('the snapshot keeps a composite scenario with its vessel design and train run',
    keptSeam?.flowsheetId === COMPOSITE_FLOWSHEET && keptSeam.vessel === vesselId && keptSeam.trainRun === trainRunId &&
      seamSnap.createdScenarios?.[id]?.vessel === undefined, keptSeam);
  useStore.setState((s) => ({ scenarios: s.scenarios.filter((x) => x.id !== seam), createdScenarioIds: s.createdScenarioIds.filter((x) => x !== seam) }));
  st().applyDurable(seamSnap);
  const seamBack = st().scenarios.find((x) => x.id === seam);
  check('after a reload the composite scenario is back with both parts, and partsOf reads them',
    JSON.stringify(partsOf(seamBack)) === JSON.stringify({ vessel: vesselId, trainRun: trainRunId }) && partsOf(st().scenarios.find((x) => x.id === id)) === null);
  const seamCopyId = st().duplicateScenario(seam);
  const seamCopy = st().scenarios.find((x) => x.id === seamCopyId);
  check('a copy of a composite scenario keeps its parts', seamCopy?.vessel === vesselId && seamCopy?.trainRun === trainRunId && seamCopy.id !== seam);
  const helpedId = scenarioFromVesselAndTrain(vesselId, trainRunId, 'yeast');
  const helped = st().scenarios.find((x) => x.id === helpedId);
  check('scenarioFromVesselAndTrain makes a Durable composite scenario in the train run\u2019s program, not run',
    helped?.flowsheetId === COMPOSITE_FLOWSHEET && helped.vessel === vesselId && helped.trainRun === trainRunId && helped.program === 'yeast' &&
      helped.lastRunId === null && st().createdScenarioIds.includes(helped.id));
  const seamBody = runBody({ scenarioId: seam, flowsheet: COMPOSITE_FLOWSHEET, overrides: [], host: null, vessel: vesselId, trainRun: trainRunId, includeArchived: false });
  check('a composite run carries its parts and the switch, and a run of any other flowsheet carries neither',
    seamBody.vessel === vesselId && seamBody.trainRun === trainRunId && seamBody.includeArchived === false &&
      !('vessel' in runBody({ scenarioId: id, flowsheet: 'ethanol_glucose_v0', overrides: [], host: null })));
  const page = readFileSync(new URL('../src/screens/ProformaScenario.tsx', import.meta.url), 'utf8');
  check('a composite scenario\u2019s page sends its parts with every binding, panel read and run, names them with links, and shows Finance',
    /partsOf\(scenario\)/.test(page) && /vessel: vesselId, trainRun: trainRunId/.test(page) && /data-testid="scenario-parts"/.test(page) &&
      /vesselDesignPath\(parts\.vessel\)/.test(page) && /trainRunPath\(parts\.trainRun\)/.test(page) &&
      /const PROFORMA_GROUPS = \[[^\]]*'Finance'\]/.test(page) && /sp\.group === 'Finance'/.test(page));
  const dialog = readFileSync(new URL('../src/components/NewScenarioDialog.tsx', import.meta.url), 'utf8');
  check('New scenario reads the kept vessel designs and train runs for a flowsheet built from them, and says why a list is empty',
    /compositeVessels\(/.test(dialog) && /compositeTrainRuns\(/.test(dialog) && /No vessel design is kept on this service yet/.test(dialog) &&
      /No train run is kept on this service yet/.test(dialog) && /pureOS → New train/.test(dialog) &&
      /disabled=\{[^}]*\(needsParts && !parts\)\} data-testid="new-scenario-create"/.test(dialog));
  st().clearBrowserData();
  check('Clearing this browser\u2019s data drops the scenarios made here, their newest runs and every pin',
    !st().scenarios.some((x) => x.createdAt) && st().createdScenarioIds.length === 0 && !st().scenarios.some((x) => x.lastRunId) &&
      !st().scenarios.some((x) => x.pinned));
  const index = readFileSync(new URL('../src/screens/Proforma.tsx', import.meta.url), 'utf8');
  check('Proforma\u2019s New scenario opens the chooser: it copies no scenario and is not disabled for an empty list',
    !/duplicateScenario/.test(index) && !/disabled=\{scenarios\.length === 0\}/.test(index) && /NewScenarioDialog/.test(index));
}

// OF-BLD-019 §3.3 — a reference biorefinery's page reads its package test
// from the run (`output.checks`, through referenceChecks) and the service
// (`regression`), and types no value of it (a decimal outside a Tailwind
// class name fails); it shows the TEA's installed
// equipment cost, never a sum over the units' (the corn TEA prices
// installation with a Lang factor, so the two differ).
{
  const ref = readFileSync(new URL('../src/screens/ProformaReference.tsx', import.meta.url), 'utf8');
  const code = ref.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
  check('the reference page reads its package test from the run and the service, and types no decimal value of its own',
    /referenceChecks\(/.test(code) && /regression/.test(code) && !/(?<![-\w.])\d+\.\d+\b/.test(code), code.match(/(?<![-\w.])\d+\.\d+\b/g));
  check("the reference page shows the TEA's own installed equipment cost and sums no unit's",
    /tea\.installedEquipmentCost/.test(code) && !/\.installedCost\b/.test(code) && !/\.reduce\(/.test(code));
  const compare = readFileSync(new URL('../src/screens/Compare.tsx', import.meta.url), 'utf8');
  check('Compare reads each BioSTEAM scenario from its newest run artifact, and makes no price of its own',
    /proformaArtifact\(/.test(compare) && /runViewOfArtifact\(/.test(compare) && /viewPrice\(/.test(compare) && !/basePrice\s*[-+]/.test(compare));
}
// OF-BLD-019 §2.R — what the index says of a run and a scenario is what the
// service says. A reference card names how its price was had in no words of
// its own beyond the shelf's: the corn plant's price is the package's own,
// set, and its TEA solves the IRR at it, so the card may not say the package
// solved or gave it (review 8 and 12). A scenario made here is counted as the
// service binds it, as its page lists it, and a card that could not ask says
// only what can bind (review 13).
{
  const fixture = <T,>(name: string): T =>
    JSON.parse(readFileSync(new URL(`../core/tests/fixtures/prototype/${name}`, import.meta.url), 'utf8')).response as T;
  const shelf = fixture<FlowsheetInfo[]>('proforma-shelf.json');
  const corn = shelf.find((f) => f.id === 'corn_drygrind');
  const price = corn?.priceOutput ? referencePrice(corn, { output: { [corn.priceOutput]: 0.5 } } as unknown as Artifact) : null;
  check('the corn plant\u2019s card claims no solving and no giving of the price its package set',
    !!price && !/solve|gives/i.test(price.reads) && price.basis === corn?.priceBasis, price);
  const ethanol = shelf.find((f) => f.id === 'ethanol_glucose_v0');
  const made = { id: 'sc-made-1', kind: 'biosteam', flowsheetId: 'ethanol_glucose_v0', modelId: 'ethanol_glucose_v0' } as unknown as Scenario;
  const bound = fixture<{ off: Record<string, { status: number; body: ProformaScenarioInfo }> }>('proforma-bind.json').off.ethanol_glucose_v0.body;
  const byService = inputCounts(made, bound, shelf, []);
  // OF-BLD-020 §2.R (finding 16): the page lists the flowsheet's convention
  // among its inputs (the panel's Conventions group), and the binding holds
  // none, so the card counts it from the shelf, as the page shows it.
  const stated = ethanol?.inputs.filter((i) => i.kind === 'convention').length ?? 0;
  check('a made scenario\u2019s card counts the inputs the service binds, and the convention its page lists, as its page lists them',
    !!byService && byService.bound && stated === 1 && byService.total === bound.inputs.length + stated && byService.conventions === stated &&
      byService.waiting === bound.inputs.filter((i) => i.binding === 'waiting').length, byService);
  const scenarios = fixture<ProformaScenarioInfo[]>('proforma-scenarios.json');
  const yeastInfo = scenarios.find((x) => x.id === 'sc-yeast-1') ?? null;
  const panelSpecs = JSON.parse(readFileSync(new URL('../core/tests/fixtures/prototype/params-proforma.json', import.meta.url), 'utf8'))
    .response.scopes['proforma:sc-yeast-1'].body.specs as { key: string }[];
  const yeastCard = inputCounts({ id: 'sc-yeast-1', kind: 'biosteam', flowsheetId: 'ethanol_glucose_v0', modelId: 'ethanol_glucose_v0' } as unknown as Scenario,
    yeastInfo, shelf, []);
  check('sc-yeast-1\u2019s card counts as many inputs as its page\u2019s panel lists, the convention among them',
    !!yeastCard && yeastCard.total === panelSpecs.length && yeastCard.conventions === 1, { card: yeastCard, panel: panelSpecs.length });
  const index = readFileSync(new URL('../src/screens/Proforma.tsx', import.meta.url), 'utf8');
  check('the index asks the service to bind a scenario made here, and says only what can bind when it cannot ask',
    /proformaBind\(/.test(index) && /can bind to records/.test(index) && !/bind to records when it runs/.test(index) && !!ethanol);
}

// OF-BLD-019 §5.1 (D10) — the fermOS fits a person chose for a scenario's
// inputs are Durable, like its assumptions: which artifact feeds which input
// survives a reload keyed by scenario and input, one input can stop using its
// fit or all can, a choice made since load wins over the snapshot's, and
// clearing this browser's data drops them. The page asks the service for the
// fits and their values; Send to Proforma rides on fermOS → Forecast.
{
  const st = () => useStore.getState();
  const fit = '1a2b3c4d5e6f7a8b';
  const forecast = '8b7a6f5e4d3c2b1a';
  st().setProformaFits('sc-yeast-1', { titre: forecast, yield: forecast, productivity: forecast });
  st().setProformaFits('sc-yeast-1', { yield: fit });
  check('choosing a fit binds the inputs it feeds, and a later choice replaces only its own inputs',
    JSON.stringify(st().proformaFits['sc-yeast-1']) === JSON.stringify({ titre: forecast, yield: fit, productivity: forecast }), st().proformaFits);
  const snap = snapshotOf(st());
  check('the snapshot keeps each scenario\u2019s fits by input', snap.proformaFits?.['sc-yeast-1']?.productivity === forecast, snap.proformaFits);
  useStore.setState({ proformaFits: {} });
  st().applyDurable(snap);
  check('after a reload the fits are back under the scenario, input by input',
    JSON.stringify(st().proformaFits['sc-yeast-1']) === JSON.stringify({ titre: forecast, yield: fit, productivity: forecast }), st().proformaFits);
  st().setProformaFits('sc-yeast-1', { titre: fit });
  st().applyDurable(snap);
  check('a choice made since load wins over the snapshot\u2019s', st().proformaFits['sc-yeast-1']?.titre === fit, st().proformaFits);
  st().clearProformaFit('sc-yeast-1', 'productivity');
  check('one input can stop using its fit, and the others keep theirs',
    !('productivity' in (st().proformaFits['sc-yeast-1'] ?? {})) && st().proformaFits['sc-yeast-1']?.yield === fit);
  st().clearProformaFit('sc-yeast-1');
  check('every input can stop using its fit at once', Object.keys(st().proformaFits['sc-yeast-1'] ?? {}).length === 0);
  st().setProformaFits('sc-yeast-1', { titre: fit });
  st().clearBrowserData();
  check('Clearing this browser\u2019s data drops the fits chosen here', Object.keys(st().proformaFits).length === 0, st().proformaFits);
  const page = readFileSync(new URL('../src/screens/ProformaScenario.tsx', import.meta.url), 'utf8');
  const forecastPage = readFileSync(new URL('../src/screens/FermOSForecast.tsx', import.meta.url), 'utf8');
  check('the scenario page lists the fits the service keeps, and keeps the choice in the store',
    /fermosFits\(/.test(page) && /setProformaFits|setFits\(scenario\.id/.test(page) && !/<FermosFitSlot fits=\{\[\]\}/.test(page));
  check('fermOS \u2192 Forecast sends a fit to Proforma', /Send to Proforma/.test(forecastPage) && /sendFitPath/.test(forecastPage));
}

// OF-BLD-019 \u00a73.R \u2014 the Phase 3 review's findings, each held here where a
// pure function or the page's source can hold it (the smoke holds the
// pages). Namespace imports, so a function a finding needs and the tree
// lacks fails its own check rather than the whole script.
await (async () => {
  const pf = (await import('../src/lib/proforma')) as unknown as Record<string, any>;
  const pb = (await import('../src/screens/ProformaBiosteam')) as unknown as Record<string, any>;
  const fixture = (name: string) => JSON.parse(readFileSync(new URL(`../core/tests/fixtures/prototype/${name}`, import.meta.url), 'utf8')).response;
  const shelf = fixture('proforma-shelf.json') as { id: string; reference: boolean; inputs: { key: string; name: string; unit: string }[] }[];
  const ethanol = shelf.find((f) => f.id === 'ethanol_glucose_v0')!;
  const corn = shelf.find((f) => f.id === 'corn_drygrind')!;
  const bound = (fixture('proforma-scenarios.json') as any[]).find((s) => s.id === 'sc-yeast-1');
  const call = (fn: string, ...args: unknown[]) => {
    try {
      return typeof pf[fn] === 'function' ? pf[fn](...args) : typeof pb[fn] === 'function' ? pb[fn](...args) : undefined;
    } catch (e) {
      return `threw ${String(e)}`;
    }
  };

  // (5, high) The yeast page asks its own flowsheet's questions: with titre
  // and yield waiting, no question and no line of the exported text is PHA's.
  const waiting = { ...bound, inputs: bound.inputs.map((i: any) => (['titre', 'yield'].includes(i.key) ? { ...i, binding: 'waiting', records: [], value: null } : i)) };
  const qs = (call('modellerQuestions', waiting.inputs, null, 'ethanol_glucose_v0') ?? []) as { key: string; question: string }[];
  const text = String(call('questionsText', waiting, null) ?? '');
  check('the yeast scenario\u2019s questions for a process modeller are its own flowsheet\u2019s, never PHA\u2019s fixed words',
    qs.some((q) => q.key === 'titre') && qs.some((q) => q.key === 'yield') && !qs.some((q) => /PHA|hydrolysate/.test(q.question)) && !/PHA|hydrolysate/.test(text) && /titre/.test(text),
    qs.map((q) => q.question));
  const phaQs = (call('modellerQuestions', [{ key: 'titre', label: 'PHA titre at harvest', binding: 'waiting' }], null, 'pha_sugar_v0') ?? []) as { question: string }[];
  check('the PHA draft keeps its own questions', /PHA titre/.test(phaQs[0]?.question ?? ''), phaQs);

  // (6, high; 20) What a run read back is credited to whoever set it: on
  // the ethanol flowsheet the glucose and water fed, the conversion and the
  // batch time follow from the records and the person's assumptions, never
  // from the reference model; on a reference plant every value is the
  // package's own default, named and in its unit, as the shelf lists it.
  const rb = (call('readBackRows', { glucoseFedKgPerH: 1, waterFedKgPerH: 2, fermenterConversion: 0.5, batchTimeH: 3, rateOfReturn: 0.1, somethingNew: 4 }, ethanol) ?? []) as {
    key: string;
    origin: string;
    label: string;
    unit: string;
  }[];
  const origin = (k: string) => rb.find((r) => r.key === k)?.origin;
  check('what the case gave from its inputs is never credited to the reference model',
    ['glucoseFedKgPerH', 'waterFedKgPerH', 'fermenterConversion', 'batchTimeH'].every((k) => origin(k) === 'case') && origin('rateOfReturn') === 'setting' && origin('somethingNew') === 'read', rb);
  const biosteamSrc = readFileSync(new URL('../src/screens/ProformaBiosteam.tsx', import.meta.url), 'utf8');
  check('no read-back heading credits the reference model with a value a person or a record set', !/What the reference model supplied/.test(biosteamSrc));
  const cornRb = (call('readBackRows', { cornFeed: 46380, depreciation: 'MACRS7' }, corn) ?? []) as { key: string; origin: string; label: string; unit: string }[];
  const cornFeed = cornRb.find((r) => r.key === 'cornFeed');
  check('a reference plant\u2019s read-back names each default and its unit, as the shelf lists it, and credits the package',
    cornFeed?.label === 'corn fed' && cornFeed?.unit === 'kg h-1' && cornRb.every((r) => r.origin === 'setting'), cornRb);

  // (27) The left-out line names the flowsheet's own feed. Since OF-BLD-020
  // §2.2 a person reads it from the service (the panel shows the value's
  // detail), so test_params holds its words, and nothing here writes a line
  // of its own (§2.R, finding 15: this check held a function no screen called).
  const libText = readFileSync(new URL('../src/lib/proforma.ts', import.meta.url), 'utf8');
  check('the left-out line is the service\u2019s alone: no browser function writes one of its own',
    !/leftOutWords|on a feed other than/.test(libText) && call('leftOutWords', {}, 'ethanol_glucose_v0') === undefined);

  // (3) A flowsheet with a program files its scenario there and nowhere else.
  check('New scenario offers only the flowsheet\u2019s own program when it has one',
    JSON.stringify(call('programsFor', { program: 'pha' }, ['yeast', 'casein', 'pha'])) === '["pha"]' &&
      JSON.stringify(call('programsFor', { program: null }, ['yeast', 'casein'])) === '["yeast","casein"]');

  // (4) A time the service wrote in UTC says so.
  check('a run\u2019s time says it is UTC', call('stamp', '2026-10-21T01:00:00Z') === '2026-10-21 01:00 UTC', call('stamp', '2026-10-21T01:00:00Z'));
  for (const f of ['Proforma.tsx', 'ProformaBiosteam.tsx', 'ProformaReference.tsx', 'Compare.tsx', 'ProformaScenario.tsx']) {
    const src = readFileSync(new URL(`../src/screens/${f}`, import.meta.url), 'utf8');
    check(`${f} cuts no UTC time to a bare minute or date`, !/replace\('T', ' '\)\.slice\(0, 16\)|createdAt\.slice\(0, 10\)/.test(src));
  }

  // (12) A table's CSV carries the run's numbers, not the screen's strings.
  const yeastArt = (fixture('artifacts.json') as any[]).find((a) => a.tool === 'proforma.run' && a.output?.flowsheet === 'ethanol_glucose_v0');
  const view = pf.runViewOfArtifact(yeastArt);
  const st = call('streamsTable', view) as { headers: string[]; rows: unknown[][]; csv?: unknown[][] } | undefined;
  const csv = st?.csv ?? st?.rows ?? [];
  const numericCols = [4, 5, 6, 8];
  check('the streams CSV carries the run\u2019s numbers, each column parsing as a number where the run holds one',
    csv.length === view.tables.streams.length &&
      csv.every((r, i) => numericCols.every((c) => {
        const raw = [view.tables.streams[i].T, view.tables.streams[i].P, view.tables.streams[i].massFlow, null, view.tables.streams[i].price][[4, 5, 6, 7, 8].indexOf(c)];
        return raw == null ? r[c] === '' : Number(r[c]) === raw;
      })),
    csv[0]);
  const eq = call('equipmentTable', view) as { csv?: unknown[][] } | undefined;
  check('the equipment CSV carries the run\u2019s numbers', !!eq?.csv && eq.csv.every((r, i) => {
    const u = [...view.tables.units].sort((a: any, b: any) => a.order - b.order)[i];
    return (u.installedCost == null ? r[3] === '' : Number(r[3]) === u.installedCost) && (u.power == null ? r[7] === '' : Number(r[7]) === u.power);
  }));

  // (10) The cost breakdown's note puts sales in its annual unit beside the one-off capital sums.
  const note = String(call('costBreakdownNote', view) ?? '');
  check('the cost breakdown\u2019s note gives sales a year and capital once', /sales [\d,.]+ USD\/yr/.test(note) && /total capital [\d,.]+ USD\b/.test(note), note);

  // (11) An infeasible base case's empty breakdown says why, not "run it again".
  const empty = call('costBreakdownEmpty', { ...view, basePrice: null, baseInfeasible: 'Infeasible: this yield is above the theoretical yield', tables: { ...view.tables, tea: null } }) as { what: string; where: string } | undefined;
  check('an infeasible base case\u2019s empty breakdown names the base case, not a rerun',
    !!empty && /base case could not run/.test(`${empty.what} ${empty.where}`) && !/run the scenario again/.test(`${empty.what} ${empty.where}`), empty);

  // (28) The sliders' cost lines, split as the flowsheet splits its grid,
  // take no word the TEA breakdown above uses for another quantity.
  const teaLabels = new Set((view.tables.tea?.lines ?? []).map((l: { label: string }) => l.label));
  const sliderLabels = Object.values((pb.SLIDER_LINE_LABEL ?? {}) as Record<string, string>);
  check('the sliders’ cost lines share no label with the TEA breakdown’s lines',
    sliderLabels.length === 6 && teaLabels.size > 0 && !sliderLabels.some((l) => teaLabels.has(l)) && !sliderLabels.includes('Utilities'), { sliderLabels, tea: [...teaLabels] });

  // (2) Home's pinned card reads what is pinned: Cost model v0 for the
  // authored surfaces alone, and no modeled tick for a BioSTEAM scenario.
  const yeastSc = useStore.getState().scenarios.find((s) => s.id === 'sc-yeast-1')!;
  const s1 = useStore.getState().scenarios.find((s) => s.id === 'sc-s1')!;
  const card = call('pinnedCard', [yeastSc]) as { prov: string | null; words: string } | undefined;
  const authored = call('pinnedCard', [s1]) as { prov: string | null; words: string } | undefined;
  check('Home\u2019s pinned card says Cost model v0 for an authored surface alone, and puts no modeled tick on a BioSTEAM scenario',
    !!card && card.prov === null && !/Cost model v0/.test(card.words) && authored?.prov === 'demo' && /Cost model v0/.test(authored.words), { card, authored });
  const home = readFileSync(new URL('../src/screens/Home.tsx', import.meta.url), 'utf8');
  check('Home\u2019s pinned card is drawn from pinnedCard', /pinnedCard\(/.test(home) && !/pinned \u2014 open the\s+comparison\. Cost model v0/.test(home));

  // (26) New scenario is never disabled, in any spelling: the header button
  // and the empty state's.
  const index = readFileSync(new URL('../src/screens/Proforma.tsx', import.meta.url), 'utf8');
  // An opening tag, its attributes' braces read whole (an arrow's `>` is not the tag's end).
  const header = /<Button\b(?:[^>{]|\{[^}]*\})*data-testid="new-scenario"(?:[^>{]|\{[^}]*\})*>/.exec(index)?.[0] ?? '';
  const emptyAction = /action=\{\s*<Button\b(?:[^>{]|\{[^}]*\})*>/.exec(index)?.[0] ?? '';
  check('New scenario, on the header and in the empty state, carries no disabled attribute in any spelling',
    !!header && !!emptyAction && !/\bdisabled\b/.test(header) && !/\bdisabled\b/.test(emptyAction), { header, emptyAction });

  // (21, 8) A run the service holds for a scenario is found by the page, the
  // index card and Compare, not only the one this browser kept.
  for (const f of ['ProformaScenario.tsx', 'Proforma.tsx', 'Compare.tsx']) {
    const src = readFileSync(new URL(`../src/screens/${f}`, import.meta.url), 'utf8');
    check(`${f} asks the service for a scenario\u2019s newest run`, /proformaNewestRun\(/.test(src));
  }
})();

// OF-BLD-019 \u00a77.R (2) \u2014 Compare reads a fermOS fit as the input's source.
// proforma.basis_inputs names a fit-bound input `<key> fit`, `<key> fit low`
// and `<key> fit high` (source artifact), and a productivity the fit gave
// carries `fit batch time`. runInputs reads them as one row for the key,
// of kind artifact with the fit's range and id, never as 'not in this
// run's basis' beside a raw 'titre fit' row.
await (async () => {
  const pf = (await import('../src/lib/proforma')) as unknown as Record<string, any>;
  let words: ((i: unknown) => string) | null = null;
  try {
    words = ((await import('../src/screens/Compare')) as unknown as Record<string, any>).inputWords ?? null;
  } catch {
    words = null;
  }
  const src = (id: string, note: string) => ({ kind: 'artifact', id, note });
  const basisIn = (name: string, value: number, unit: string, source: object) => ({ name, value, unit, source });
  const view = {
    basis: {
      inputs: [
        basisIn('flowsheet', 0, '', { kind: 'convention' }),
        basisIn('titre fit', 80, 'g L-1', src('fitA', 'the forecast median titre')),
        basisIn('titre fit low', 70, 'g L-1', src('fitA', 'the forecast median titre')),
        basisIn('titre fit high', 90, 'g L-1', src('fitA', 'the forecast median titre')),
        basisIn('productivity fit', 2, 'g L-1 h-1', src('fitA', 'titre over the run-out hour')),
        basisIn('productivity fit low', 1.5, 'g L-1 h-1', src('fitA', 'titre over the run-out hour')),
        basisIn('productivity fit high', 2.5, 'g L-1 h-1', src('fitA', 'titre over the run-out hour')),
        basisIn('fit batch time', 40, 'h', src('fitA', 'the hour the median sugar runs out')),
        basisIn('yield record', 0.4, 'g g-1', { kind: 'record', id: 'r1' }),
      ],
    },
  };
  const flowsheet = { inputs: ['titre', 'yield', 'productivity'].map((key) => ({ key, name: key, unit: '', kind: 'bound' })) };
  let rows: any[] = [];
  try {
    rows = typeof pf.runInputs === 'function' ? pf.runInputs(view, flowsheet) : [];
  } catch (e) {
    rows = [{ threw: String(e) }];
  }
  const titre = rows.find((r) => r.key === 'titre');
  const prod = rows.find((r) => r.key === 'productivity');
  check('Compare reads a titre a fermOS fit fed as one artifact row with the fit\u2019s value, range and id',
    titre?.kind === 'artifact' && titre.value === 80 && titre.low === 70 && titre.high === 90 && titre.by === 'fitA', titre);
  check('no input row is keyed by a fit\u2019s own basis name', !rows.some((r) => / fit$|^fit /.test(String(r.key))), rows.map((r) => r.key));
  check('a productivity from a fit names the fit\u2019s batch time', prod?.kind === 'artifact' && /40 h/.test(String(prod?.note ?? '')), prod);
  const said = words && titre ? words(titre) : '';
  check('Compare\u2019s words for a fitted input name the artifact and its range, never \u201cnot in this run\u2019s basis\u201d',
    /fitA/.test(said) && /70/.test(said) && /90/.test(said) && !/not in this run/.test(said), said);
  const compareSrc = readFileSync(new URL('../src/screens/Compare.tsx', import.meta.url), 'utf8');
  check('Compare links an artifact-fed input to its artifact', /data-testid="compare-input-artifact"/.test(compareSrc));
})();

// OF-BLD-020 §2.1 (D3) — a person's change to a parameter is an Override,
// kept in this browser by scope and key and round-tripped through the
// Durable tier; a snapshot written before the panel, holding only
// proformaAssumptions, is read once into `proforma:<id>` and the old field
// still answers; Proforma's assumptions are the overrides of its scope, so
// the scenario page reads them unchanged; clearing this browser's data drops
// both.
{
  const st = () => useStore.getState();
  const scope = 'fermos:family:batch_v1';
  const typed: Override = { scope, key: 'mu_max', value: 0.3, low: 0.2, high: 0.4, by: 'Sean Creighton', at: '2026-10-21', note: 'a check-store fixture' };
  st().setOverride(typed);
  st().setOverride({ ...typed, key: 'kla_method', value: 'Riet', low: null, high: null });
  st().setOverride({ ...typed, value: 0.35 });
  check('an override replaces the one for its scope and key, and keeps the rest',
    JSON.stringify(st().parameterOverrides[scope]?.map((o) => `${o.key}=${o.value}`)) === JSON.stringify(['kla_method=Riet', 'mu_max=0.35']),
    st().parameterOverrides[scope]);
  check('overridesFor(scope) reads one scope, and the same empty list for a scope with none',
    overridesFor(scope)(st()).length === 2 && overridesFor('proforma:nowhere')(st()) === overridesFor('pureos:unit:t:u')(st()));
  st().setProformaAssumption('sc-yeast-1', { key: 'glucose_price', value: 0.4, low: 0.3, high: 0.5, by: 'Sean Creighton', at: '2026-10-21', note: null });
  const yeast = st().parameterOverrides[proformaScope('sc-yeast-1')]?.[0];
  check('a Proforma assumption is the override of its scenario’s scope, and proformaAssumptions reads it back',
    yeast?.scope === 'proforma:sc-yeast-1' && yeast.key === 'glucose_price' && yeast.value === 0.4 && yeast.by === 'Sean Creighton' &&
      st().proformaAssumptions['sc-yeast-1']?.[0]?.value === 0.4, { yeast, assumptions: st().proformaAssumptions['sc-yeast-1'] });
  st().setOverride({ scope: 'proforma:sc-yeast-1', key: 'plant_scale', value: 100000, low: null, high: null, by: 'Sean Creighton', at: '2026-10-21', note: null });
  const scale = st().proformaAssumptions['sc-yeast-1']?.find((a) => a.key === 'plant_scale');
  check('an override typed in a proforma scope reaches proformaAssumptions, a value with no range held at itself',
    scale?.value === 100000 && scale.low === 100000 && scale.high === 100000, scale);
  const snap = snapshotOf(st());
  check('the snapshot keeps every scope’s overrides, and writes proformaAssumptions from them',
    snap.parameterOverrides?.[scope]?.length === 2 && snap.parameterOverrides?.['proforma:sc-yeast-1']?.length === 2 &&
      snap.proformaAssumptions?.['sc-yeast-1']?.length === 2, snap.parameterOverrides);
  // A reload: a store that has lost them.
  useStore.setState({ parameterOverrides: {}, proformaAssumptions: {} });
  st().applyDurable(snap);
  check('after a reload every override is back by scope and key, a value in words with it',
    JSON.stringify(st().parameterOverrides[scope]?.map((o) => `${o.key}=${o.value}`)) === JSON.stringify(['kla_method=Riet', 'mu_max=0.35']) &&
      st().parameterOverrides['proforma:sc-yeast-1']?.length === 2, st().parameterOverrides);
  check('…and the scenario’s assumptions answer from them', st().proformaAssumptions['sc-yeast-1']?.map((a) => a.key).sort().join() === 'glucose_price,plant_scale');
  st().clearOverride(proformaScope('sc-yeast-1'), 'plant_scale');
  check('Reset to source drops one override, and the assumption with it',
    st().parameterOverrides['proforma:sc-yeast-1']?.map((o) => o.key).join() === 'glucose_price' &&
      st().proformaAssumptions['sc-yeast-1']?.map((a) => a.key).join() === 'glucose_price');
  // The migration: a snapshot written before the panel holds proformaAssumptions alone.
  const old = (key: string, value: number) => ({ key, value, low: value, high: value, by: 'Sean Creighton', at: '2026-10-20', note: 'typed before the panel' });
  const before = { ...snap, parameterOverrides: undefined, proformaAssumptions: { 'sc-old-1': [old('glucose_price', 0.5), old('plant_scale', 50000)] } };
  useStore.setState({ parameterOverrides: {}, proformaAssumptions: {} });
  st().applyDurable(before);
  const migrated = st().parameterOverrides['proforma:sc-old-1'] ?? [];
  check('a snapshot holding only proformaAssumptions comes back as overrides under proforma:<id>, each named',
    migrated.length === 2 && migrated.every((o) => o.scope === 'proforma:sc-old-1' && o.by === 'Sean Creighton' && o.note === 'typed before the panel') &&
      migrated.find((o) => o.key === 'plant_scale')?.value === 50000, migrated);
  check('…and the old field still answers for the scenario', st().proformaAssumptions['sc-old-1']?.map((a) => `${a.key}=${a.value}`).sort().join() === 'glucose_price=0.5,plant_scale=50000');
  check('…and the next save writes the new field', snapshotOf(st()).parameterOverrides?.['proforma:sc-old-1']?.length === 2);
  const both = { ...snap, parameterOverrides: { 'proforma:sc-old-1': [overrideOfAssumption('sc-old-1', old('glucose_price', 0.6))] },
    proformaAssumptions: { 'sc-old-1': [old('glucose_price', 0.5), old('plant_scale', 50000)] } };
  useStore.setState({ parameterOverrides: {}, proformaAssumptions: {} });
  st().applyDurable(both);
  check('the old field is read only for a scope the snapshot holds no overrides for',
    st().parameterOverrides['proforma:sc-old-1']?.map((o) => `${o.key}=${o.value}`).join() === 'glucose_price=0.6');
  st().clearBrowserData();
  check('Clearing this browser’s data drops every override and every assumption',
    Object.keys(st().parameterOverrides).length === 0 && Object.keys(st().proformaAssumptions).length === 0);
  const durable = readFileSync(new URL('../src/lib/durable.ts', import.meta.url), 'utf8');
  check('the Durable snapshot names parameterOverrides as a record of Override lists by scope', /parameterOverrides\?: Record<string, Override\[\]>/.test(durable));
}

// OF-BLD-020 §2.2 (D3) — the scenario page's inputs are the parameter
// panel over `proforma:<id>`, and a run carries that scope's overrides and
// nothing else of a person: the overrides of the inputs its flowsheet takes,
// never another scope's, and no `assumptions` (the older field the service
// still reads for one release). Reset to source removes exactly one
// override. The panel's resolve carries the scope's overrides with what the
// page binds by. Nothing under src/ reads `proformaAssumptions` but the
// store's own migration, and the panel's every control is labelled and
// bench-sized (Deposition.tsx's constraints).
{
  const st = () => useStore.getState();
  useStore.setState({ parameterOverrides: {}, proformaAssumptions: {} });
  const scope = proformaScope('sc-yeast-1');
  const at = '2026-10-21T02:00:00Z';
  const typed = (o: Partial<Override> & Pick<Override, 'scope' | 'key' | 'value'>): Override => ({ low: null, high: null, by: 'Sean Creighton', at, note: null, ...o });
  st().setOverride(typed({ scope, key: 'plant_scale', value: 100000 }));
  st().setOverride(typed({ scope, key: 'glucose_price', value: 0.4, low: 0.3, high: 0.5, note: 'a check-store fixture' }));
  st().setOverride(typed({ scope, key: 'titre', value: 50 }));
  st().setOverride(typed({ scope: proformaScope('sc-pha-1'), key: 'sugarPrice', value: 0.4 }));
  st().setOverride(typed({ scope: 'fermos:family:batch_v1', key: 'mu_max', value: 0.3 }));
  const keys = ['feed_glucose_conc', 'titre', 'yield', 'productivity', 'plant_scale', 'glucose_price'];
  const body = runBody({ scenarioId: 'sc-yeast-1', overrides: runOverrides(overridesFor(scope)(st()), keys), host: null, fits: { yield: 'a1b2c3d4e5f60718' } });
  check('a run request carries its scope\u2019s overrides, every one, and no other scope\u2019s',
    (body.overrides ?? []).map((o) => o.key).sort().join() === 'glucose_price,plant_scale,titre' && (body.overrides ?? []).every((o) => o.scope === scope) &&
      (body.overrides ?? []).find((o) => o.key === 'glucose_price')?.low === 0.3, body.overrides);
  check('…and sends no assumptions, the older field', !('assumptions' in body), Object.keys(body));
  check('an override of an input the flowsheet does not take stays in this browser and is not sent',
    runOverrides([...overridesFor(scope)(st()), typed({ scope, key: 'recovery', value: 0.9 })], keys).map((o) => o.key).sort().join() === 'glucose_price,plant_scale,titre');
  const resolve = resolveRequest(overridesFor(scope)(st()), { flowsheet: null, host: null, fits: {} });
  check('the panel\u2019s resolve carries the scope\u2019s overrides and nothing it was not asked with',
    resolve.overrides.length === 3 && !('flowsheet' in resolve) && !('fits' in resolve) &&
      resolveRequest([], { flowsheet: 'ethanol_glucose_v0', fits: { titre: 'f' } }).flowsheet === 'ethanol_glucose_v0', resolve);
  st().clearOverride(scope, 'titre');
  check('Reset to source removes exactly one override: that input\u2019s, in that scope',
    overridesFor(scope)(st()).map((o) => o.key).sort().join() === 'glucose_price,plant_scale' &&
      overridesFor(proformaScope('sc-pha-1'))(st()).length === 1 && overridesFor('fermos:family:batch_v1')(st()).length === 1);
  const snap = snapshotOf(st());
  useStore.setState({ parameterOverrides: {}, proformaAssumptions: {} });
  st().applyDurable(snap);
  check('after a reload the run would carry the same overrides',
    runOverrides(overridesFor(scope)(st()), keys).map((o) => `${o.key}=${o.value}`).sort().join() === 'glucose_price=0.4,plant_scale=100000');
  const counted = inputCounts({ id: 'sc-yeast-1', kind: 'biosteam', flowsheetId: 'ethanol_glucose_v0', modelId: 'ethanol_glucose_v0' } as unknown as Scenario,
    { inputs: [{ key: 'titre', binding: 'records' }, { key: 'plant_scale', binding: 'waiting' }] } as unknown as ProformaScenarioInfo, [], [{ key: 'titre' }], { titre: 'f' });
  check('the index counts an input a person overrode as assumed, over its records and its fit', counted?.assumed === 1 && counted?.records === 0 && counted?.computed === 0 && counted?.waiting === 1, counted);
  useStore.setState({ parameterOverrides: {}, proformaAssumptions: {} });

  const page = readFileSync(new URL('../src/screens/ProformaScenario.tsx', import.meta.url), 'utf8');
  check('the scenario page\u2019s inputs are the parameter panel over its scope, and Keep assumption is gone',
    /<ParameterPanel[\s\S]*?scope=\{scope\}/.test(page) && /proformaScope\(scenario\.id\)/.test(page) && !/Keep assumption/.test(page) && !/AssumptionForm/.test(page));
  check('the scenario page runs with the scope\u2019s overrides', /runOverrides\(overrides,/.test(page) && /overrides: sent/.test(page));
  const lib = readFileSync(new URL('../src/lib/proforma.ts', import.meta.url), 'utf8');
  check('runProformaScenario posts what runBody makes', /const body = runBody\(ask\)/.test(lib));
  // Nothing reads the older field but the store's migration (and this check's own tests of it).
  const walk = (dir: string): string[] =>
    readdirSync(dir).flatMap((name) => {
      const path = join(dir, name);
      return statSync(path).isDirectory() ? walk(path) : /\.tsx?$/.test(name) ? [path] : [];
    });
  const readers = walk('src').filter((f) => !/src[\\/](store\.ts|lib[\\/]durable\.ts|data[\\/]types\.ts)$/.test(f) && /proformaAssumptions|setProformaAssumption|clearProformaAssumption/.test(readFileSync(f, 'utf8')));
  check('nothing under src/ reads proformaAssumptions but the store\u2019s migration', readers.length === 0, readers);

  // The panel's controls: every input and select labelled, every one at least 44 px (Deposition.tsx's constraints).
  // OF-BLD-020 §2.R (finding 11): a link and the controls a component renders
  // (CitationChip's trigger, Button) are touch targets too, so the walk sees
  // `<a>`, `<CitationChip>` and `<Button>` beside the intrinsic controls, and
  // the records Proforma renders into a row (RecordsChooser) with the panel's
  // two files: each must carry a 44 px class (TOUCH_CHIP for a chip).
  const TARGETS = ['input', 'select', 'button', 'summary', 'a', 'CitationChip', 'Button'];
  const within = [
    { file: 'src/components/ParameterRow.tsx', fn: null },
    { file: 'src/components/ParameterPanel.tsx', fn: null },
    { file: 'src/screens/ProformaScenario.tsx', fn: 'RecordsChooser' },
  ];
  for (const { file, fn } of within) {
    const text = readFileSync(file, 'utf8');
    const sf = ts.createSourceFile(file, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
    const unlabelled: string[] = [];
    const small: string[] = [];
    let seen = 0;
    const visit = (node: ts.Node, inside: boolean): void => {
      const here = inside || (ts.isFunctionDeclaration(node) && node.name?.getText(sf) === fn);
      if (here && (ts.isJsxSelfClosingElement(node) || ts.isJsxOpeningElement(node)) && TARGETS.includes(node.tagName.getText(sf))) {
        const attrs = node.attributes.properties.filter(ts.isJsxAttribute);
        const named = (n: string) => attrs.find((a) => a.name.getText(sf) === n);
        const tag = node.tagName.getText(sf);
        const line = sf.getLineAndCharacterOfPosition(node.getStart()).line + 1;
        seen++;
        if ((tag === 'input' || tag === 'select') && !named('aria-label')) unlabelled.push(`${file}:${line}`);
        const cls = named('className')?.getText(sf) ?? '';
        if (!/min-h-\[44px\]|TOUCH_CHIP|linkClass/.test(cls)) small.push(`${file}:${line} <${tag}>`);
      }
      ts.forEachChild(node, (child) => visit(child, here));
    };
    visit(sf, fn === null);
    const where = fn ? `${file} (${fn})` : file;
    check(`${where}: every input and select carries a label`, unlabelled.length === 0, unlabelled);
    check(`${where}: every control, link and chip is a 44 px touch target`, small.length === 0 && (fn === null || seen > 0), small);
  }
  check('TOUCH_CHIP and the links\u2019 class are 44 px',
    /export const TOUCH_CHIP = '[^']*min-h-\[44px\]/.test(readFileSync('src/components/ParameterRow.tsx', 'utf8')) &&
      /const linkClass = '[^']*min-h-\[44px\]/.test(readFileSync('src/components/ParameterRow.tsx', 'utf8')));
  const row = readFileSync(new URL('../src/components/ParameterRow.tsx', import.meta.url), 'utf8');
  check('a row offers Reset to source and Why, and says where a reviewer name is set when there is none',
    /Reset to source/.test(row) && />Why</.test(row) && /Set a reviewer name in Settings/.test(row) && /disabled=\{!named/.test(row));
  const panelSrc = readFileSync(new URL('../src/components/ParameterPanel.tsx', import.meta.url), 'utf8');
  check('the panel keeps a change as an override under the reviewer name and asks the service to resolve it',
    /setOverride\(\{ scope, key: spec\.key[^}]*by: reviewer/.test(panelSrc) && /resolveParams\(/.test(panelSrc) && /clearOverride\(scope, spec\.key\)/.test(panelSrc));
}

// OF-BLD-020 §2.R — the Phase 2 review. A migrated assumption whose ends
// were its own value moves freely (10); one end of an interval typed is read
// the same way by the row, the page's binding and the run (1, 14: the
// service's `params.held`); an override wins over a fit on the scenario page
// and the fit card, which never claim a fit feeds an input a person's value
// overrides (8, 12); the panel tells the page when the service refuses the
// scope's overrides, and Run waits with those words (13).
{
  const st = () => useStore.getState();
  useStore.setState({ parameterOverrides: {}, proformaAssumptions: {} });
  const fixed = { key: 'plant_scale', value: 100000, low: 100000, high: 100000, by: 'Sean Creighton', at: '2026-10-20', note: 'typed before the panel' };
  st().applyDurable({ ...snapshotOf(st()), parameterOverrides: undefined, proformaAssumptions: { 'sc-x': [fixed] } });
  const migrated = st().parameterOverrides['proforma:sc-x']?.[0];
  check('a migrated assumption with both ends at its value comes back with no ends, so the value is held at itself',
    migrated?.value === 100000 && migrated.low === null && migrated.high === null, migrated);
  // ParameterRow's keep: a new value keeps the override's ends.
  if (migrated) st().setOverride({ ...migrated, value: 200000, low: migrated.low, high: migrated.high, by: 'Sean Creighton', at: '2026-10-21T04:00:00Z' });
  const moved = st().parameterOverrides['proforma:sc-x']?.[0];
  const asRun = moved ? assumptionOfOverride(moved) : null;
  check('…and a new value typed over it stands inside its own ends, held at itself in the run',
    moved?.value === 200000 && moved.low === null && moved.high === null && asRun?.low === 200000 && asRun.high === 200000, { moved, asRun });
  const ranged = overrideOfAssumption('sc-x', { ...fixed, low: 90000, high: 110000 });
  check('a migrated assumption with a range keeps it', ranged.low === 90000 && ranged.high === 110000, ranged);
  useStore.setState({ parameterOverrides: {}, proformaAssumptions: {} });

  const one = overrideEnds({ value: 50, low: 40, high: null });
  const other = overrideEnds({ value: 50, low: null, high: 70 });
  const none = overrideEnds({ value: 50, low: null, high: null });
  check('one end typed, the other is the value; neither, held at itself with no interval (the service\u2019s params.held)',
    one.low === 40 && one.high === 50 && other.low === 50 && other.high === 70 && none.low === null && none.high === null, { one, other, none });
  const half = assumptionOfOverride({ scope: 'proforma:sc-x', key: 'titre', value: 50, low: 40, high: null, by: 'Sean Creighton', at: '2026-10-21', note: null });
  check('…and the run\u2019s assumption takes the same interval', half?.low === 40 && half.high === 50, half);
  const panelText = readFileSync(new URL('../src/components/ParameterPanel.tsx', import.meta.url), 'utf8');
  const page = readFileSync(new URL('../src/screens/ProformaScenario.tsx', import.meta.url), 'utf8');
  check('the panel\u2019s row and the page\u2019s binding read an override\u2019s ends through overrideEnds',
    /const ends = overrideEnds\(o\)/.test(panelText) && /low: ends\.low/.test(panelText) && /const ends = overrideEnds\(o\)/.test(page) && !/o\.low \?\? o\.value/.test(page));
  check('the fit card says it is in use only for the inputs no person\u2019s value overrides, and whose value wins elsewhere',
    /const used = mine\.filter\(\(k\) => !\(k in overridden\)\)/.test(page) && /In use for \$\{used\.join/.test(page) && /data-testid="fermos-fit-overridden"/.test(page) &&
      !/In use for \{Object\.entries\(chosen\)/.test(page));
  check('the line under the panel says a person\u2019s value replaces the fit where one overrides it',
    /key in overridden \?/.test(page) && /value replaces the fermOS \{fitWord\(key\)\}/.test(page) && /data-overridden="true"/.test(page));
  check('the panel tells the page when the service refuses the scope\u2019s overrides, and Run waits with its words',
    /onRefused=\{setRefused\}/.test(page) && /refused !== null\}/.test(page) && /data-testid="run-held"/.test(page) &&
      /if \(!down\) refusedRef\.current\?\.\(words\)/.test(panelText) && /refusedRef\.current\?\.\(null\)/.test(panelText));
}

// OF-BLD-020 \u00a73.R (part B) \u2014 the Phase 3 review's screen findings, held by
// the pure function and the pages' source (test_fermos_3r holds the service).
await (async () => {
  const fl = (await import('../src/lib/fermos')) as unknown as Record<string, any>;
  const read = (path: string) => readFileSync(new URL(path, import.meta.url), 'utf8');
  const typedAs = (key: string, value: number, by: string) => ({ scope: 'fermos:forecast:0000000000000000', key, value, low: null, high: null, by, at: '2026-10-21', note: null });
  // (7, 11) A forecast length typed in the panel goes with its person's name.
  const alone = typeof fl.forecastAsk === 'function' ? fl.forecastAsk([typedAs('t_end', 12, 'Alice Example')]) : null;
  check('a forecast length typed in the panel goes with the name of the person who typed it',
    alone?.durationH === 12 && alone?.durationBy === 'Alice Example' && alone?.changedBy === null, alone);
  const both = typeof fl.forecastAsk === 'function' ? fl.forecastAsk([typedAs('s0', 80, 'Bob Example'), typedAs('t_end', 12, 'Alice Example')]) : null;
  check('\u2026and a changed start and a changed length each name who typed them', both?.changedBy === 'Bob Example' && both?.durationBy === 'Alice Example', both);
  const forecastPage = read('../src/screens/FermOSForecast.tsx');
  check('fermOS \u2192 Forecast sends who set the length with the forecast', /durationBy: a\.durationBy/.test(forecastPage));
  // (4, 15) A batch fit's simulation sends only what its panel shows, and waits in words.
  check('fermOS \u2192 Forecast sends a batch fit\u2019s simulation only the overrides of the keys its panel shows',
    /scoped\.filter\(\(o\) => shownKeys\.has\(o\.key\)\)/.test(forecastPage) && /fermosSimulate\(batchAsk, overrides\)/.test(forecastPage));
  check('\u2026and holds Simulate from this fit while anything waits, naming it',
    /disabled=\{busy \|\| !fit \|\| held\}/.test(forecastPage) && /data-testid="forecast-waiting"/.test(forecastPage) && /setElsewhere\(d\.waiting\.filter/.test(forecastPage));
  // (10, 12) Every fits list carries the program switch.
  for (const [name, path] of [['the scenario page', '../src/screens/ProformaScenario.tsx'], ['Simulate', '../src/screens/FermOSSimulate.tsx'], ['Vessel', '../src/screens/FermOSVessel.tsx']]) {
    const text = read(path);
    const calls = text.match(/fermosFits\([^)]*\)/g) ?? [];
    check(`${name} asks for the fits with the program switch`, calls.length > 0 && calls.every((c) => /, showArchived, /.test(c)), calls);
  }
  // (14) None named stays chosen, and a store family names no product by default.
  const simulatePage = read('../src/screens/FermOSSimulate.tsx');
  check('fermOS \u2192 Simulate keeps None named once chosen, and names no product by default for a family whose product is a store',
    /product === '' \? ''/.test(simulatePage) && /chosen\.states\.includes\('P'\)/.test(simulatePage) && /useState<string \| null>\(route\.query\.get\('product'\)\)/.test(simulatePage));
  // (16) What the other values leave unread is said so, never waiting.
  const row = read('../src/components/ParameterRow.tsx');
  check('a parameter its other values leave unread shows as not read here, never as waiting', /case 'not-read':/.test(row) && /not read here/.test(row));
})();

// OF-BLD-020 \u00a78.R \u2014 the final review of night one: a simulation fed to
// Proforma is called a simulation wherever it feeds it (findings 0, 4, 10,
// 11), Simulate holds what the run refuses (12, 14), Vessel says it is asking
// (15), and operating mode's reference sits on Simulate (7). The service is
// held by test_review_8r.
await (async () => {
  const read = (path: string) => readFileSync(new URL(path, import.meta.url), 'utf8');
  const pf = (await import('../src/lib/proforma')) as unknown as Record<string, any>;
  const simNote = 'the final product of simulation simA at harvest (its run\u2019s end)';
  const batchNote = 'the harvest hour of simulation simA (its run\u2019s end); productivity is the simulation\u2019s final titre over it';
  const src = (note: string) => ({ kind: 'artifact', id: 'simA', note });
  const inp = (name: string, value: number, unit: string, note: string) => ({ name, value, unit, source: src(note) });
  const view = { basis: { inputs: [
    inp('titre fit', 8, 'g L-1', simNote), inp('titre fit low', 8, 'g L-1', simNote), inp('titre fit high', 8, 'g L-1', simNote),
    inp('productivity fit', 1, 'g L-1 h-1', 'the final titre of simulation simA over its harvest hour'),
    inp('fit batch time', 3, 'h', batchNote),
  ] } };
  const flowsheet = { inputs: ['titre', 'productivity'].map((key) => ({ key, name: key, unit: '', kind: 'bound' })) };
  let rows: any[] = [];
  try {
    rows = pf.runInputs(view, flowsheet);
  } catch (e) {
    rows = [{ threw: String(e) }];
  }
  const titre = rows.find((r) => r.key === 'titre');
  const prod = rows.find((r) => r.key === 'productivity');
  check('a run\u2019s input fed by a simulation is never labelled a fermOS fit, and carries the service\u2019s words',
    titre?.kind === 'artifact' && !/fermOS fit/.test(String(titre?.note)) && String(titre?.note).includes(simNote), titre);
  check('\u2026and its productivity names the batch time as the service words it (the simulation\u2019s harvest hour)',
    /batch time 3 h/.test(String(prod?.note)) && String(prod?.note).includes('harvest hour of simulation simA') && !/fit\u2019s batch time|fit's batch time/.test(String(prod?.note)), prod);
  const page = read('../src/screens/ProformaScenario.tsx');
  check('the fit card\u2019s batch time is worded by the tool that kept it, never a forecast\u2019s for every source',
    /f\.batchTimeNote \?\?/.test(page) && !/where the forecast&rsquo;s median sugar runs out/.test(page));
  check('the fit card says a simulation is computed, not measured, instead of naming no run',
    /f\.tool === 'fermos\.simulation' \? 'computed, not measured'/.test(page));
  check('the ceiling\u2019s yield chip and the fit line name a simulation as one',
    /check\.yieldTool && FIT_TOOL_WORDS\[check\.yieldTool\]/.test(page) && /from the fermOS \{fitWord\(key\)\}/.test(page) &&
      /origin === 'simulation' \? 'simulation' : 'fit'/.test(page) && !/>\s*fermOS fit \{src\.id\}/.test(page));
  const sim = read('../src/screens/FermOSSimulate.tsx');
  check('fermOS \u2192 Simulate holds its button on what the run would refuse, in the service\u2019s words',
    /const refused = binding\?\.refused \?\? null/.test(sim) && /waiting\.length === 0 && !refused && !busy/.test(sim) && /data-testid="simulate-refused"/.test(sim));
  check('fermOS \u2192 Simulate carries operating mode\u2019s reference', /<SubsystemReference id="fermos\.mode" \/>/.test(sim));
  const vessel = read('../src/screens/FermOSVessel.tsx');
  check('fermOS \u2192 Vessel says it is asking (BioSTEAM starting) until the panel answers, and holds Design and Scale until then',
    /data-testid="vessel-panel-asking"/.test(vessel) && /\{!panel && !panelProblem && \(/.test(vessel) && /proformaStatus\(ctrl\.signal\)/.test(vessel) &&
      /\{panel && \(\s*<div className="flex flex-wrap items-center gap-3">\s*<p className="text-body" data-testid="vessel-scale"/.test(vessel));
})();

console.log(fails === 0 ? '\nTHE STORE KEEPS ITS CONTRACTS' : `\n${fails} failures`);
process.exit(fails === 0 ? 0 : 1);
