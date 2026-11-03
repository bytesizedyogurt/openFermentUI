/**
 * What a project keeps of its pages, on the browser's side (alpha 2.0, stage
 * 2; src/lib/projectState.ts): the writes a change makes, the outbox they
 * wait in, the rows laid over a load, and a flush that drops a refusal and
 * keeps everything from the first write the service did not answer; and the
 * overlay a project's pages load (src/lib/intake.ts), where a service that
 * answers and refuses is running and says why; the configurations a plant
 * is offered in (src/lib/library.ts), and the refusals an SFF import answers
 * in the service's words (src/lib/http.ts), a refusal of a request's own
 * fields among them; and the unit each person's change is sent in
 * (src/lib/params.ts, `inputsOf`), a panel that shows part of its scope
 * among them. Run by `pnpm check:state`, offline: the service is a stand-in
 * for `fetch`.
 */
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
import type { Deposition, LiveConversation, Override, ParameterSpec, Scenario } from '../src/data/types';
import { loadOverlay } from '../src/lib/intake';
import { ServiceDown, ServiceRefused, call, detailWords } from '../src/lib/http';
import { runnable, type LibraryPlant } from '../src/lib/library';
import { inputsOf } from '../src/lib/params';

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

// ── the conversations a page holds (alpha 2.1 stage F) ─────────────────
// The service lists a project's conversations oldest first; the page held only
// the 30 newest, so stage C's 31 evaluation runs left every earlier answer
// unreachable, and a link to one opened an empty pane.

const kept = Array.from({ length: 51 }, (_, i) => ({ id: `lc-${i}`, turns: [] }) as unknown as LiveConversation);
const begun = { id: 'lc-new', turns: [] } as unknown as LiveConversation;
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
}

// ── the unit each change is sent in (alpha 2.2 D2; src/lib/params.ts) ──

{
  const spec = (key: string, unit: string, group: string) => ({ key, unit, group }) as unknown as ParameterSpec;
  const scope: ParameterSpec[] = [spec('x0', 'placeholder-unit-a', 'Start values'), spec('mu_max', 'placeholder-unit-b', 'Kinetics')];
  const shownOnly = scope.filter((s) => s.group === 'Start values');
  const typed = (key: string): Override => ({ scope: 'a-scope', key, value: 1, by: 'Ada', at: '2026-11-03T00:00:00Z' }) as Override;
  const changes = [typed('x0'), typed('mu_max')];
  const units = (specs: ParameterSpec[]) => inputsOf(changes, specs).map((i) => `${i.name} ${i.quantity.unit}`).join(', ');
  // FermOSForecast's batch fit shows part of its family's scope and resolves with all of it (ParameterPanel's unitSpecs).
  check('a panel that shows part of its scope sends each change in the unit its scope’s every spec names', units(scope) === 'x0 placeholder-unit-a, mu_max placeholder-unit-b', units(scope));
  check('the shown specs alone would send a change typed elsewhere on the scope with no unit', units(shownOnly) === 'x0 placeholder-unit-a, mu_max ', units(shownOnly));
  const expanded = inputsOf([typed('split.Water')], [spec('split', 'placeholder-share', 'Separation')]);
  check('a key expanded per item is sent in its template’s unit', expanded[0]?.quantity.unit === 'placeholder-share', JSON.stringify(expanded));
}

console.log(fails ? `\n✗ ${fails} check(s) failed` : '\n✓ The project rows are sent as the page changes them, and kept until the service answers; a refusal is never an outage.');
process.exit(fails ? 1 : 0);
