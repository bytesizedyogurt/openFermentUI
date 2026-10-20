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
import { isExample, mergeAssumptions, programOf, programVisible, snapshotOf, useStore } from '../src/store';
import { RECORDS } from '../src/data/records';
import { PRODUCTS } from '../src/data/products';
import { lockIntact } from '../src/engine/lock';
import { placeRow, seriesOf } from '../src/engine/series';
import type { Artifact, BasisSource, Candidate, Overlay } from '../src/data/types';
import { visibleArtifacts } from '../src/lib/artifacts';

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

console.log(fails === 0 ? '\nTHE STORE KEEPS ITS CONTRACTS' : `\n${fails} failures`);
process.exit(fails === 0 ? 0 : 1);
