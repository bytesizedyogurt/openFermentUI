// H7: the pending-writes queue (ADR-014) with the service stopped and started again, driven through the bench.
//
//   node outbox.mjs <origin> <project> <runbook> <db> <port> <scenario: stop|reload|twotabs> <out.json>
//
// stop:     a deposition begun with the service up; the service stopped (bh_svc_stop) and readings recorded; the
//           service started again (bh_svc_start, BH_KEEP_DB=1); what the service holds after, and in what order.
// reload:   readings recorded with every /api request refused, the page reloaded while still refused, then the
//           refusals lifted; what the page shows and what reaches the service, before and after a second reload.
// twotabs:  two tabs on one project, every /api request refused; tab A records a reading, tab B records one on its
//           own deposition; tab A reloaded; the refusals lifted; what the service holds of A's reading.
import { chromium } from 'playwright';
import { execFileSync } from 'node:child_process';
import { writeFileSync } from 'node:fs';

const [origin, project, runbook, db, port, scenario, out] = process.argv.slice(2);
const ENV = '/home/user/openFermentUI/bughunt/lib/env.sh';
const sh = (cmd) => execFileSync('bash', ['-c', `source ${ENV}; ${cmd}`], { encoding: 'utf8', timeout: 300000 }).trim();
const report = { scenario, steps: [] };
const note = (what, data) => {
  report.steps.push({ what, ...(data === undefined ? {} : { data }) });
  console.log(`- ${what}${data === undefined ? '' : ` ${JSON.stringify(data).slice(0, 400)}`}`);
};
const at = (page, path) => page.goto(`${origin}/#/p/${encodeURIComponent(project)}${path}`, { waitUntil: 'load' });
const PERSON = 'H7 Hunter';

async function state() {
  const r = await fetch(`${origin}/api/state`, { headers: { 'X-OpenFerment-Project': project } });
  return r.ok ? r.json() : { error: r.status };
}
async function depositionHeld(id) {
  const s = await state();
  const d = (s.depositions ?? []).find((x) => x.id === id);
  return d ? { entries: d.entries.map((e) => `${e.value} ${e.unit}`), observations: d.observations.map((o) => o.raw), state: d.state } : null;
}
async function snapshotOutbox(page) {
  return page.evaluate(
    () =>
      new Promise((done) => {
        const req = indexedDB.open('openferment', 1);
        req.onsuccess = () => {
          const tx = req.result.transaction('durable', 'readonly');
          const get = tx.objectStore('durable').get('snapshot');
          get.onsuccess = () =>
            done((get.result?.outbox ?? []).map((e) => ({ kind: e.kind, id: e.id, entries: e.value?.entries?.length, obs: e.value?.observations?.length })));
          get.onerror = () => done('unreadable');
        };
        req.onerror = () => done('no db');
      }),
  );
}
async function setName(page) {
  await at(page, '/settings/corpus');
  await page.locator('#reviewer-name').fill(PERSON);
  await page.waitForTimeout(800);
}
async function beginDeposition(page) {
  await at(page, `/runbooks/${runbook}`);
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
    if (await yes.count()) {
      await yes.first().click();
      await page.waitForTimeout(300);
    }
  }
  await page.waitForTimeout(400);
}
async function said(page) {
  const text = (await page.locator('body').innerText().catch(() => '')).replace(/\s+/g, ' ');
  const hits = text.match(/[^.]*(not running|wait|not yet|outbox|will be sent|is sent|could not|refused|offline|away)[^.]*\./gi) ?? [];
  return [...new Set(hits)].slice(0, 8);
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
const errors = [];
const watch = (page, tag) => {
  page.on('pageerror', (e) => errors.push(`${tag} uncaught: ${e.message}`));
  page.on('console', (m) => m.type() === 'error' && errors.push(`${tag} console: ${m.text().slice(0, 200)}`));
};
const refuse = (r) => r.abort('connectionrefused');
try {
  const page = await context.newPage();
  watch(page, 'A');
  await setName(page);

  if (scenario === 'stop') {
    const dep = await beginDeposition(page);
    note('deposition begun with the service up', dep);
    await record(page, 'first came in at 1.1 USD/kg');
    note('one reading recorded with the service up; the service holds', await waitFor(() => depositionHeld(dep).then((d) => (d?.entries.length ? d : null)), 10000));
    sh(`bh_svc_stop ${port}`);
    note('service stopped', sh(`bh_port_pid ${port} || true`) || 'no listener');
    await record(page, 'second came in at 2.2 USD/kg');
    await record(page, 'foam rose on the second impeller', false);
    await record(page, 'third came in at 3.3 USD/kg');
    await page.waitForTimeout(1500);
    note('what the page shows after three writes with the service stopped', await said(page));
    note('the page counts', (await page.locator('[data-testid="deposition-bench"] header').innerText()).replace(/\s+/g, ' '));
    note('the snapshot outbox in IndexedDB', await snapshotOutbox(page));
    await page.waitForTimeout(16000);
    note('the outbox after a 16 s retry with the service still stopped', await snapshotOutbox(page));
    sh(`BH_KEEP_DB=1 bh_svc_start ${db} ${port} >/dev/null`);
    note('service started again', true);
    const held = await waitFor(() => depositionHeld(dep).then((d) => (d && d.entries.length >= 3 ? d : null)), 40000);
    note('what the service holds of the deposition within 40 s of starting, with no reload', held ?? (await depositionHeld(dep)));
    note('the outbox after', await snapshotOutbox(page));
    note('what the page shows after the service is back', await said(page));
  }

  if (scenario === 'reload') {
    const dep = await beginDeposition(page);
    note('deposition begun with the service up', dep);
    await context.route('**/api/**', refuse);
    note('every /api request refused from here', true);
    await record(page, 'first came in at 4.4 USD/kg');
    await record(page, 'a smell of sulphur', false);
    await page.waitForTimeout(1500);
    note('the outbox after two writes', await snapshotOutbox(page));
    note('what the page shows', await said(page));
    await page.reload({ waitUntil: 'load' });
    await page.waitForTimeout(4000);
    note('after a reload, refused still: the bench says', {
      state: await page.locator('[data-testid="deposition-bench"]').getAttribute('data-state').catch(() => null),
      text: (await page.locator('body').innerText()).replace(/\s+/g, ' ').slice(0, 400),
    });
    note('the outbox after the reload', await snapshotOutbox(page));
    // A write after the reload, while refused: on the Depositions list's own bench there is none to write to, so try
    // the runbook again.
    await at(page, `/runbooks/${runbook}`);
    await page.waitForTimeout(2500);
    note('the runbook page after the reload, refused', (await page.locator('#of-main').innerText().catch(() => '')).replace(/\s+/g, ' ').slice(0, 300));
    await context.unroute('**/api/**', refuse);
    note('refusals lifted; waiting 40 s with no reload', true);
    const sent = await waitFor(() => depositionHeld(dep).then((d) => (d && d.entries.length >= 1 ? d : null)), 40000);
    note('what the service holds within 40 s, no reload', sent ?? (await depositionHeld(dep)));
    await page.reload({ waitUntil: 'load' });
    const after = await waitFor(() => depositionHeld(dep).then((d) => (d && d.entries.length >= 1 ? d : null)), 30000);
    note('what the service holds within 30 s of a second reload', after ?? (await depositionHeld(dep)));
    note('the outbox after', await snapshotOutbox(page));
  }

  if (scenario === 'twotabs') {
    const depA = await beginDeposition(page);
    note('tab A: deposition begun', depA);
    const pageB = await context.newPage();
    watch(pageB, 'B');
    const depB = await beginDeposition(pageB);
    note('tab B: its own deposition begun', depB);
    await context.route('**/api/**', refuse);
    note('every /api request refused from here (both tabs)', true);
    await page.bringToFront();
    await record(page, 'tab A came in at 5.5 USD/kg');
    await page.waitForTimeout(1200);
    note('the outbox after tab A wrote', await snapshotOutbox(page));
    await pageB.bringToFront();
    await record(pageB, 'tab B came in at 6.6 USD/kg');
    await pageB.waitForTimeout(1200);
    note('the outbox after tab B wrote', await snapshotOutbox(pageB));
    await page.reload({ waitUntil: 'load' });
    await page.waitForTimeout(3000);
    note('the outbox after tab A reloaded', await snapshotOutbox(page));
    await pageB.close();
    note('tab B closed', true);
    await context.unroute('**/api/**', refuse);
    await page.reload({ waitUntil: 'load' });
    await page.waitForTimeout(20000);
    note('what the service holds of tab A\'s deposition after the refusals lifted and a reload', await depositionHeld(depA));
    note('what the service holds of tab B\'s deposition', await depositionHeld(depB));
  }
} catch (e) {
  note('stopped', String(e).slice(0, 400));
}
report.errors = errors;
writeFileSync(out, JSON.stringify(report, null, 1));
await browser.close();
