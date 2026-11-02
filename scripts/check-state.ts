/**
 * What a project keeps of its pages, on the browser's side (alpha 2.0, stage
 * 2; src/lib/projectState.ts): the writes a change makes, the outbox they
 * wait in, the rows laid over a load, and a flush that drops a refusal and
 * keeps everything from the first write the service did not answer. Run by
 * `pnpm check:state`, offline: the service is a stand-in for `fetch`.
 */
import {
  EMPTY_STATE,
  applyEntries,
  changes,
  enqueue,
  flush,
  type OutboxEntry,
  type ProjectState,
} from '../src/lib/projectState';
import type { Deposition, LiveConversation, Scenario } from '../src/data/types';

let fails = 0;
const check = (label: string, ok: boolean, extra = '') => {
  console.log((ok ? '✓' : '✗') + ' ' + label + (extra ? '  ' + extra : ''));
  if (!ok) fails++;
};

const dep = { id: 'dep-1', runbookId: 'rb-1' } as unknown as Deposition;
const scenario = { id: 'sc-1', name: 'S', pinned: false } as unknown as Scenario;
const talk = { id: 'lc-1', turns: [] } as unknown as LiveConversation;
const before: ProjectState = { ...EMPTY_STATE, depositions: [dep], scenarios: [scenario], conversations: [talk], fits: { 'sc-1': { mu: 'a'.repeat(16) } } };

// ── changes ────────────────────────────────────────────────────────────

check('nothing changed is nothing to send', changes(before, { ...before }, 'p', 'Ada').length === 0);
const moved = { ...dep, entries: [] } as unknown as Deposition;
const pinned = { ...scenario, pinned: true } as Scenario;
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

// ── the outbox ─────────────────────────────────────────────────────────

const e = (id: string, value: unknown, project = 'p'): OutboxEntry => ({ project, kind: 'scenarios', id, value, by: 'Ada', at: '' });
const queued = enqueue([e('sc-1', 1), e('sc-2', 2)], [e('sc-1', 3)]);
check('a later write of a row replaces the one still unsent, and goes last', JSON.stringify(queued.map((x) => [x.id, x.value])) === '[["sc-2",2],["sc-1",3]]');
check('the same row in another project is another write', enqueue([e('sc-1', 1, 'a')], [e('sc-1', 2, 'b')]).length === 2);
const laid = applyEntries(before, [{ ...e('sc-1', null) }, { ...e('sc-9', pinned) }]);
check('an owed write is laid over the loaded rows, a take-back removes', laid.scenarios.length === 1 && laid.scenarios[0] === pinned);

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

console.log(fails ? `\n✗ ${fails} check(s) failed` : '\n✓ The project rows are sent as the page changes them, and kept until the service answers.');
process.exit(fails ? 1 : 0);
