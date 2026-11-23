// H7-01: two tabs on one project, the service stopped; each tab writes a reading to its own deposition; both tabs
// close; the service starts again and one tab opens. What the browser's one IndexedDB snapshot holds at each step,
// and what reaches the service.
//
//   node twotabs.mjs <origin> <project> <runbook> <db> <port> <out.json>
//
// Prints one JSON line `FACTS {...}` for run.sh to read.
import { chromium } from 'playwright';
import { execFileSync } from 'node:child_process';
import { writeFileSync } from 'node:fs';

const [origin, project, runbook, db, port, out] = process.argv.slice(2);
const ENV = '/home/user/openFermentUI/bughunt/lib/env.sh';
const sh = (cmd) => execFileSync('bash', ['-c', `source ${ENV}; ${cmd}`], { stdio: 'ignore', timeout: 300000 });
const PERSON = 'H7 Repro';
const facts = { steps: [], errors: [] };
const note = (what, data) => {
  facts.steps.push({ what, data });
  console.log(`- ${what}: ${JSON.stringify(data)}`);
};
const at = (page, path) => page.goto(`${origin}/#/p/${encodeURIComponent(project)}${path}`, { waitUntil: 'load' });

async function depositionHeld(id) {
  try {
    const r = await fetch(`${origin}/api/state`, { headers: { 'X-OpenFerment-Project': project } });
    if (!r.ok) return { error: r.status };
    const d = ((await r.json()).depositions ?? []).find((x) => x.id === id);
    return d ? { entries: d.entries.map((e) => `${e.value} ${e.unit}`), state: d.state } : null;
  } catch (e) {
    return { error: String(e).slice(0, 120) };
  }
}
// The browser's one durable snapshot, read straight from IndexedDB: the queue's entries, by kind and id.
async function snapshotOutbox(page) {
  return page.evaluate(
    () =>
      new Promise((done) => {
        const req = indexedDB.open('openferment', 1);
        req.onsuccess = () => {
          try {
            const tx = req.result.transaction('durable', 'readonly');
            const get = tx.objectStore('durable').get('snapshot');
            get.onsuccess = () =>
              done((get.result?.outbox ?? []).map((e) => ({ kind: e.kind, id: e.id, entries: (e.value?.entries ?? []).map((x) => `${x.value} ${x.unit}`) })));
            get.onerror = () => done('unreadable');
          } catch (e) {
            done(`no store: ${e}`);
          }
        };
        req.onerror = () => done('no db');
      }),
  );
}
async function beginDeposition(page) {
  await at(page, `/runbooks/${encodeURIComponent(runbook)}`);
  await page.getByRole('button', { name: /Start a deposition/ }).click();
  await page.getByTestId('deposition-readings-alone').click();
  const staged = page.locator('[data-testid="deposition-bench"][data-state="staged"]');
  await staged.waitFor({ timeout: 30000 });
  const id = await staged.getAttribute('data-deposition');
  await page.getByTestId('deposition-bench-begin').click();
  await page.locator('[data-testid="deposition-bench"][data-state="running"]').waitFor();
  return id;
}
async function record(page, words) {
  const box = page.getByLabel('Describe what you observed');
  await box.fill(words);
  await box.press('Enter');
  const yes = page.getByRole('button', { name: 'That is right' });
  if (await yes.count()) await yes.first().click();
  await page.waitForTimeout(1200);
}
async function waitFor(check, ms) {
  const end = Date.now() + ms;
  for (;;) {
    const v = await check();
    if (v || Date.now() > end) return v;
    await new Promise((r) => setTimeout(r, 1000));
  }
}

const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--no-proxy-server'] });
const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
// A blank page on the service's origin, answered by the browser itself, so the snapshot can be read with every tab
// of the app closed and the service stopped.
await context.route(`${origin}/h7-01-blank`, (r) => r.fulfill({ status: 200, contentType: 'text/html', body: '<!doctype html><title>h7</title>' }));
const watch = (page, tag) => page.on('pageerror', (e) => facts.errors.push(`${tag}: ${e.message.slice(0, 200)}`));
try {
  const A = await context.newPage();
  watch(A, 'A');
  await at(A, '/settings/corpus');
  await A.locator('#reviewer-name').fill(PERSON);
  await A.waitForTimeout(1000);
  facts.depA = await beginDeposition(A);
  const B = await context.newPage();
  watch(B, 'B');
  facts.depB = await beginDeposition(B);
  note('both depositions begun with the service up; the service holds A', await depositionHeld(facts.depA));
  note('and B', await depositionHeld(facts.depB));

  sh(`bh_svc_stop ${port}`);
  note('service stopped; health answers', await fetch(`${origin}/api/health`).then((r) => r.status).catch(() => 'no answer'));

  await A.bringToFront();
  await record(A, 'tab A came in at 5.5 USD/kg');
  facts.afterA = await snapshotOutbox(A);
  note('the snapshot queue after tab A recorded 5.5 USD/kg', facts.afterA);

  await B.bringToFront();
  await record(B, 'tab B came in at 6.6 USD/kg');
  facts.afterB = await snapshotOutbox(B);
  note('the snapshot queue after tab B recorded 6.6 USD/kg', facts.afterB);
  facts.benchA = (await A.locator('[data-testid="deposition-bench"] header').innerText().catch(() => '')).replace(/\s+/g, ' ').slice(0, 200);
  note('tab A still shows, in its own memory', facts.benchA);

  await A.close({ runBeforeUnload: true });
  await B.close({ runBeforeUnload: true });
  const R = await context.newPage();
  await R.goto(`${origin}/h7-01-blank`);
  await R.waitForTimeout(500);
  facts.afterClose = await snapshotOutbox(R);
  await R.close();
  note('the snapshot queue with both tabs closed, the service still stopped', facts.afterClose);

  sh(`BH_KEEP_DB=1 bh_svc_start ${db} ${port}`);
  note('service started again; health answers', await fetch(`${origin}/api/health`).then((r) => r.status).catch(() => 'no answer'));
  const C = await context.newPage();
  watch(C, 'C');
  await at(C, `/runbooks/${encodeURIComponent(runbook)}`);
  facts.heldB = await waitFor(() => depositionHeld(facts.depB).then((d) => (d?.entries?.length ? d : null)), 45000);
  await C.waitForTimeout(8000);
  facts.heldA = await depositionHeld(facts.depA);
  facts.heldB = facts.heldB ?? (await depositionHeld(facts.depB));
  note('a new tab open 8 s after the queue sent B: the service holds A', facts.heldA);
  note('and B', facts.heldB);
  facts.afterSend = await snapshotOutbox(C);
  note('the snapshot queue after', facts.afterSend);
  const words = (await C.locator('body').innerText().catch(() => '')).replace(/\s+/g, ' ');
  facts.warned = [...new Set(words.match(/[^.]*(dropped|lost|never sent|not sent|overwrit)[^.]*\./gi) ?? [])].slice(0, 4);
  note('words on the new tab about a dropped or lost reading', facts.warned);
} catch (e) {
  facts.stopped = String(e).slice(0, 400);
  note('stopped', facts.stopped);
}
writeFileSync(out, JSON.stringify(facts, null, 1));
console.log(`FACTS ${JSON.stringify(facts)}`);
await browser.close();
