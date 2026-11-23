// H7-03: one running deposition open at its bench in two tabs, the service up. Tab A records a reading, which the
// service keeps; tab B, whose rows were read before A's reading, records one of its own. The service refuses tab B's
// writes (the recorded debt), and this script reads what tab B's bench and record page go on showing after that.
//
//   node sameonline.mjs <origin> <project> <runbook> <out.json>
//
// Prints one JSON line `FACTS {...}` for run.sh to read.
import { chromium } from 'playwright';
import { writeFileSync } from 'node:fs';

const [origin, project, runbook, out] = process.argv.slice(2);
const PERSON = 'H7 Repro';
const facts = { steps: [], errors: [], putsB: [] };
const note = (what, data) => {
  facts.steps.push({ what, data });
  console.log(`- ${what}: ${JSON.stringify(data)}`);
};
const at = (page, path) => page.goto(`${origin}/#/p/${encodeURIComponent(project)}${path}`, { waitUntil: 'load' });
const flat = (s) => (s ?? '').replace(/\s+/g, ' ').trim();

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
// The browser's durable snapshot, read straight from IndexedDB: the queue of writes not yet acknowledged.
async function snapshotOutbox(page) {
  return page.evaluate(
    () =>
      new Promise((done) => {
        const req = indexedDB.open('openferment', 1);
        req.onsuccess = () => {
          try {
            const get = req.result.transaction('durable', 'readonly').objectStore('durable').get('snapshot');
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
// One reading said into the capture box, then read back with "That is right", as the bench asks.
async function record(page, words) {
  const box = page.getByLabel('Describe what you observed');
  await box.fill(words);
  await box.press('Enter');
  const yes = page.getByRole('button', { name: 'That is right' });
  await yes.first().waitFor({ timeout: 10000 });
  await yes.first().click();
  await page.waitForTimeout(1500);
}
async function waitFor(check, ms) {
  const end = Date.now() + ms;
  for (;;) {
    const v = await check();
    if (v || Date.now() > end) return v;
    await new Promise((r) => setTimeout(r, 500));
  }
}
// What a bench shows: its header's count, each measure's standing reading, and the panel's "Recorded here" list.
async function bench(page) {
  return {
    header: flat(await page.locator('[data-testid="deposition-bench"] header').innerText().catch(() => '')),
    measures: (await page.locator('[data-testid="deposition-bench-measure"]').allInnerTexts().catch(() => [])).map(flat),
    recordedHere: flat(await page.locator('section[aria-label="Record what happened"]').innerText().catch(() => '')).replace(/^.*?recorded here/i, 'Recorded here:').replace(/ Produced by .*$/, '').slice(0, 200),
  };
}

const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--no-proxy-server'] });
const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
const watch = (page, tag) => page.on('pageerror', (e) => facts.errors.push(`${tag}: ${e.message.slice(0, 200)}`));
try {
  const A = await context.newPage();
  watch(A, 'A');
  await at(A, '/settings/corpus');
  await A.locator('#reviewer-name').fill(PERSON);
  await A.waitForTimeout(1000);
  facts.dep = await beginDeposition(A);
  note('tab A: deposition begun and running; the service holds', await waitFor(() => depositionHeld(facts.dep).then((d) => (d?.state === 'running' ? d : null)), 10000));

  // Tab B opens the same deposition's bench and reads the project's rows now, before tab A's reading.
  const B = await context.newPage();
  watch(B, 'B');
  B.on('response', async (r) => {
    if (r.request().method() === 'PUT' && r.url().includes('/api/state/depositions/'))
      facts.putsB.push(`${r.status()} ${(await r.text().catch(() => '')).slice(0, 300)}`);
  });
  await at(B, `/runbooks/depositions/${encodeURIComponent(facts.dep)}/bench`);
  await B.locator('[data-testid="deposition-bench"][data-state="running"]').waitFor({ timeout: 30000 });
  note('tab B: the same deposition open at its bench', await bench(B));

  await A.bringToFront();
  await record(A, 'tab A came in at 7.7 USD/kg');
  facts.heldAfterA = await waitFor(() => depositionHeld(facts.dep).then((d) => (d?.entries?.length ? d : null)), 10000);
  note('the service after tab A recorded 7.7 USD/kg', facts.heldAfterA);

  await B.bringToFront();
  await record(B, 'tab B came in at 8.8 USD/kg');
  facts.toastsB = (await B.locator('[aria-live="polite"]').allInnerTexts().catch(() => [])).map(flat).filter(Boolean);
  note('tab B: its PUT answers', facts.putsB);
  note('tab B: its toasts', facts.toastsB);
  facts.heldAfterB = await depositionHeld(facts.dep);
  note('the service after tab B recorded 8.8 USD/kg', facts.heldAfterB);

  // Twenty seconds on, past the store's 15 s retry: the queue and the bench as they settle.
  await B.waitForTimeout(20000);
  facts.outboxB = await snapshotOutbox(B);
  note('the browser queue 20 s later (writes still owed to the service)', facts.outboxB);
  facts.benchB = await bench(B);
  note('tab B bench 20 s later', facts.benchB);
  facts.toastsLater = (await B.locator('[aria-live="polite"]').allInnerTexts().catch(() => [])).map(flat).filter(Boolean);
  note('tab B toasts 20 s later', facts.toastsLater);
  facts.heldLater = await depositionHeld(facts.dep);
  note('the service 20 s later', facts.heldLater);

  // The close dialog's count, then the deposition's record page, both in tab B with no reload.
  await B.getByTestId('deposition-bench-close').click();
  facts.closeDialogB = flat(await B.getByRole('dialog').innerText().catch(() => '')).slice(0, 300);
  note('tab B close dialog', facts.closeDialogB);
  await B.getByRole('button', { name: 'Stay here' }).click();
  await B.getByRole('button', { name: /Exit/ }).click();
  await B.locator('[data-testid="deposition-entry"]').first().waitFor({ timeout: 10000 }).catch(() => {});
  facts.recordB = await B.locator('[data-testid="deposition-entry"]').evaluateAll((els) =>
    els.map((el) => ({ text: el.innerText.replace(/\s+/g, ' ').trim().slice(0, 160), stands: el.getAttribute('data-stands') })),
  );
  note('tab B record page, no reload: the entries it lists', facts.recordB);

  // A reload reads the service's rows again.
  await at(B, `/runbooks/depositions/${encodeURIComponent(facts.dep)}/bench`);
  await B.reload({ waitUntil: 'load' });
  await B.locator('[data-testid="deposition-bench"][data-state="running"]').waitFor({ timeout: 30000 });
  await B.waitForTimeout(1500);
  facts.benchBReloaded = await bench(B);
  note('tab B bench after a reload', facts.benchBReloaded);
} catch (e) {
  facts.stopped = String(e).slice(0, 400);
  note('stopped', facts.stopped);
}
writeFileSync(out, JSON.stringify(facts, null, 1));
console.log(`FACTS ${JSON.stringify(facts)}`);
await browser.close();
