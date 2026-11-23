// H7-02: a reading recorded at the bench while the service is away, the page reloaded while it is still away, then
// the service answering again. What the bench shows after the reload, what the browser's queue holds, and when the
// queued reading reaches the service: with no reload, and after a second reload.
//
//   node reload.mjs <origin> <project> <runbook> <db> <away: refuse|dbaway> <out.json>
//
// away=refuse  every /api request the page makes is refused at the browser (the page itself still loads).
// away=dbaway  the service keeps running and serving the page, and its database takes no connection
//              (ALTER DATABASE <db> ALLOW_CONNECTIONS false, its sessions ended), so every /api call answers 500.
import { chromium } from 'playwright';
import { execFileSync } from 'node:child_process';
import { writeFileSync } from 'node:fs';

const [origin, project, runbook, db, away, out] = process.argv.slice(2);
const SERVER = 'postgresql://openferment:openferment@127.0.0.1:5432/postgres';
const psql = (sql) => execFileSync('psql', [SERVER, '-qXAtc', sql], { encoding: 'utf8', timeout: 60000 }).trim();
const PERSON = 'H7-02 Repro';
const facts = { away, steps: [], errors: [] };
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
    return d ? { entries: d.entries.map((e) => `${e.value} ${e.unit}`), observations: d.observations.length, state: d.state } : null;
  } catch (e) {
    return { error: String(e).slice(0, 120) };
  }
}
// The browser's durable snapshot, read straight from IndexedDB: the queue's entries.
async function snapshotOutbox(page) {
  return page.evaluate(
    () =>
      new Promise((done) => {
        const req = indexedDB.open('openferment', 1);
        req.onsuccess = () => {
          try {
            const get = req.result.transaction('durable', 'readonly').objectStore('durable').get('snapshot');
            get.onsuccess = () =>
              done(
                (get.result?.outbox ?? []).map((e) => ({
                  kind: e.kind,
                  id: e.id,
                  entries: (e.value?.entries ?? []).map((x) => `${x.value} ${x.unit}`),
                  observations: (e.value?.observations ?? []).length,
                })),
              );
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
async function record(page, words, readBack = true) {
  const box = page.getByLabel('Describe what you observed');
  await box.fill(words);
  await box.press('Enter');
  if (readBack) {
    const yes = page.getByRole('button', { name: 'That is right' });
    if (await yes.count()) await yes.first().click();
  }
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
const hasEntry = (id) => () => depositionHeld(id).then((d) => (d && Array.isArray(d.entries) && d.entries.length ? d : null));

const refuse = (r) => r.abort('connectionrefused');
async function goAway(context) {
  if (away === 'refuse') await context.route('**/api/**', refuse);
  else {
    psql(`ALTER DATABASE "${db}" ALLOW_CONNECTIONS false`);
    psql(`SELECT count(pg_terminate_backend(pid)) FROM pg_stat_activity WHERE datname = '${db}' AND pid <> pg_backend_pid()`);
  }
}
async function comeBack(context) {
  if (away === 'refuse') await context.unroute('**/api/**', refuse);
  else psql(`ALTER DATABASE "${db}" ALLOW_CONNECTIONS true`);
}

const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--no-proxy-server'] });
const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
try {
  const page = await context.newPage();
  page.on('pageerror', (e) => facts.errors.push(e.message.slice(0, 200)));
  await at(page, '/settings/corpus');
  await page.locator('#reviewer-name').fill(PERSON);
  await page.waitForTimeout(1000);
  facts.dep = await beginDeposition(page);
  note('deposition begun at the bench with the service answering; the service holds it', await depositionHeld(facts.dep));

  await goAway(context);
  facts.awayState = away === 'refuse' ? 'the browser refuses /api' : await depositionHeld(facts.dep);
  note('service away', facts.awayState);
  await record(page, 'first came in at 4.4 USD/kg');
  await record(page, 'a smell of sulphur at the vent', false);
  const benchWhole = flat(await page.locator('body').innerText().catch(() => ''));
  facts.benchBefore = flat(await page.locator('[data-testid="deposition-bench"]').innerText().catch(() => '')).slice(0, 300);
  facts.waitWordsBefore = [...new Set(benchWhole.match(/[^.]*(wait|not yet|will be sent|is sent|not running|away|outbox|this browser)[^.]*\.?/gi) ?? [])];
  note('the bench after a reading and an observation, service away', facts.benchBefore);
  facts.outboxBefore = await snapshotOutbox(page);
  note('the queue in IndexedDB', facts.outboxBefore);

  await page.reload({ waitUntil: 'load' });
  await page.waitForTimeout(4000);
  facts.reloadState = await page.locator('[data-testid="deposition-bench"]').getAttribute('data-state').catch(() => null);
  facts.reloadText = flat(await page.locator('[data-testid="deposition-bench"]').innerText().catch(() => '')).slice(0, 300);
  note('after a reload, service still away: the bench data-state', facts.reloadState);
  note('and says', facts.reloadText);
  facts.outboxAfterReload = await snapshotOutbox(page);
  note('the queue in IndexedDB after the reload', facts.outboxAfterReload);

  await comeBack(context);
  facts.backAt = Date.now();
  note('service answers again; waiting 45 s with no reload (the queue retries every 15 s)', await depositionHeld(facts.dep));
  facts.heldNoReload = await waitFor(hasEntry(facts.dep), 45000);
  facts.heldNoReload = facts.heldNoReload ?? (await depositionHeld(facts.dep));
  note('what the service holds of the deposition 45 s after it answers, no reload', facts.heldNoReload);
  facts.benchNoReload = await page.locator('[data-testid="deposition-bench"]').getAttribute('data-state').catch(() => null);
  note('the bench data-state meanwhile', facts.benchNoReload);
  facts.outboxNoReload = await snapshotOutbox(page);
  note('the queue in IndexedDB meanwhile', facts.outboxNoReload);

  await page.reload({ waitUntil: 'load' });
  facts.heldSecondReload = await waitFor(hasEntry(facts.dep), 30000);
  facts.heldSecondReload = facts.heldSecondReload ?? (await depositionHeld(facts.dep));
  note('what the service holds within 30 s of a second reload', facts.heldSecondReload);
  facts.benchSecondReload = await page.locator('[data-testid="deposition-bench"]').getAttribute('data-state').catch(() => null);
  facts.outboxSecondReload = await snapshotOutbox(page);
  note('the bench data-state and the queue after the second reload', { state: facts.benchSecondReload, outbox: facts.outboxSecondReload });
} catch (e) {
  facts.stopped = String(e).slice(0, 400);
  note('stopped', facts.stopped);
} finally {
  if (away === 'dbaway') {
    try {
      psql(`ALTER DATABASE "${db}" ALLOW_CONNECTIONS true`);
    } catch {
      /* run.sh drops the database */
    }
  }
}
writeFileSync(out, JSON.stringify(facts, null, 1));
await browser.close();
