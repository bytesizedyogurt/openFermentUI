// H7-09: a deposition at the bench with a timer running and a deviation note logged, then one page reload (the
// browser's leave-page prompt accepted). Reads Settings' Storage row, the run screen and the browser's IndexedDB
// snapshot before the reload, and the run screen, the snapshot and the address after it.
//
//   node reload.mjs <origin> <project> <runbook> <protocol title> <out.json>
//
// Writes the facts to <out.json> for run.sh to judge.
import { chromium } from 'playwright';
import { writeFileSync } from 'node:fs';

const [origin, project, runbook, protocol, out] = process.argv.slice(2);
const PERSON = 'H7 Repro';
const NOTE = 'placeholder deviation note seven-nine';
const facts = { storageRow: null, before: null, after: null, dialogs: [], stopped: null };
const at = (page, path) => page.goto(`${origin}/#/p/${encodeURIComponent(project)}${path}`, { waitUntil: 'load' });
const flat = (s) => s.replace(/\s+/g, ' ').trim();
// The Durable snapshot as this browser keeps it (src/lib/durable.ts: database openferment, store durable, key snapshot).
const snapshot = (page) =>
  page.evaluate(
    () =>
      new Promise((resolve) => {
        const req = indexedDB.open('openferment');
        req.onerror = () => resolve(null);
        req.onsuccess = () => {
          const db = req.result;
          if (!db.objectStoreNames.contains('durable')) return resolve(null);
          const get = db.transaction('durable', 'readonly').objectStore('durable').get('snapshot');
          get.onsuccess = () => resolve(get.result ? JSON.stringify(get.result) : null);
          get.onerror = () => resolve(null);
        };
      }),
  );

const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--no-proxy-server'] });
const page = await browser.newPage({ viewport: { width: 810, height: 1080 }, hasTouch: true });
page.on('dialog', async (d) => {
  facts.dialogs.push(d.type());
  await d.accept();
});
try {
  // A reading names the person who took it: the name goes in Settings first.
  await at(page, '/settings/corpus');
  await page.locator('#reviewer-name').fill(PERSON);
  await page.waitForTimeout(800);

  // What Settings tells the person about this browser's storage.
  await at(page, '/settings/about');
  await page.getByText('Storage', { exact: true }).first().waitFor();
  const about = flat(await page.locator('body').innerText());
  const m = about.match(/The service keeps each project in its database\.[^]*?leaves the service.s untouched\./);
  facts.storageRow = m ? m[0] : null;

  // The protocol's run against the locked runbook, from the runbook's page: a deposition at the bench.
  await at(page, `/runbooks/${runbook}`);
  await page.getByRole('button', { name: /Start a deposition/ }).click();
  await page.getByRole('button', { name: new RegExp(protocol) }).click();
  await page.waitForURL(/\/run\//);
  await page.getByRole('button', { name: /Begin recording/ }).click();
  await page.getByRole('button', { name: /Add deviation note/ }).waitFor();
  await page.waitForTimeout(500);

  // A deviation note on step 1.
  await page.getByRole('button', { name: /Add deviation note/ }).click();
  await page.getByRole('dialog').locator('textarea').fill(NOTE);
  await page.getByRole('dialog').getByRole('button', { name: 'Record' }).click();
  await page.waitForTimeout(500);
  const noteShown = (await page.locator('body').innerText()).includes(NOTE);

  // Step 2, its timer started.
  await page.getByLabel('Next step').click();
  await page.waitForTimeout(400);
  await page.getByRole('button', { name: /Start timer/ }).click();
  await page.waitForTimeout(2500);
  const body = flat(await page.locator('body').innerText());
  facts.before = {
    address: await page.evaluate(() => location.hash),
    noteShown,
    timerShown: body.includes('placeholder wait'),
    pauseShown: await page.getByRole('button', { name: /^Pause/ }).count(),
    header: flat(await page.locator('header').first().innerText()).slice(0, 160),
    snapshot: await snapshot(page),
  };

  // One reload; the leave-page prompt the app raises for an active run is accepted.
  await page.reload({ waitUntil: 'load' });
  await page.waitForTimeout(4000);
  const after = flat(await page.locator('body').innerText());
  facts.after = {
    address: await page.evaluate(() => location.hash),
    noLongerActive: after.includes('This run is no longer active'),
    endsWords: (after.match(/A run at the bench lives in this page.s memory, so a reload ends it[^.]*\./) || [null])[0],
    noteShown: after.includes(NOTE),
    timerShown: after.includes('placeholder wait'),
    pauseShown: await page.getByRole('button', { name: /^Pause/ }).count(),
    snapshot: await snapshot(page),
    screen: after.slice(0, 300),
  };
  facts.note = NOTE;
} catch (e) {
  facts.stopped = String(e && e.message ? e.message : e).split('\n')[0];
}
writeFileSync(out, JSON.stringify(facts, null, 2));
await browser.close();
