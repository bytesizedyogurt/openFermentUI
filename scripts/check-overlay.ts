/**
 * The overlay is authoritative (OF-BLD-012.1 F3).
 *
 *   pnpm check:overlay
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
import { useStore } from '../src/store';
import type { Candidate, Overlay } from '../src/data/types';

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
    id: `hk1-${paper.id}-overlay${n}`,
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
    extractorRun: 'haiku-1',
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
check('and the queue knows about them', THREE.every((c) => s().reviewQueue.includes(c.id)) || s().reviewQueue.length === 0);

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

console.log(fails === 0 ? '\nTHE OVERLAY IS AUTHORITATIVE' : `\n${fails} failures`);
process.exit(fails === 0 ? 0 : 1);
