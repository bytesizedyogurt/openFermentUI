// H7: two tabs on one Proforma scenario's parameter panel, the service up, each setting a different parameter.
// A scope's overrides are one row (lib/projectState.ts: overrides keyed by scope, the value the whole list), so the
// second tab's write carries the list as that tab last saw it.
//   node overrides_twotabs.mjs <origin> <project> <flowsheet> <out.json>
import { chromium } from 'playwright';
import { writeFileSync } from 'node:fs';

const [origin, project, flowsheet, out] = process.argv.slice(2);
const PERSON = 'H7 Hunter';
const at = (page, path) => page.goto(`${origin}/#/p/${encodeURIComponent(project)}${path}`, { waitUntil: 'load' });
const report = {};
const log = (k, v) => {
  report[k] = v;
  console.log(`- ${k}: ${JSON.stringify(v).slice(0, 400)}`);
};
async function held(scope) {
  const r = await fetch(`${origin}/api/state`, { headers: { 'X-OpenFerment-Project': project } });
  const s = await r.json();
  return (s.overrides[scope] ?? []).map((o) => `${o.key}=${o.value}`);
}
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--no-proxy-server'] });
const context = await browser.newContext({ viewport: { width: 1400, height: 1000 } });
try {
  const a = await context.newPage();
  await at(a, '/settings/corpus');
  await a.locator('#reviewer-name').fill(PERSON);
  await a.waitForTimeout(800);
  await at(a, '/proforma');
  await a.getByTestId('new-scenario').click();
  const dialog = a.getByTestId('new-scenario-dialog');
  await dialog.locator(`[data-testid="new-scenario-flowsheet"][data-flowsheet="${flowsheet}"] input[type="radio"]`).check();
  await dialog.getByTestId('new-scenario-name').fill('H7 two tabs');
  await dialog.getByTestId('new-scenario-create').click();
  const panelA = a.getByTestId('parameter-panel');
  await panelA.waitFor({ timeout: 120000 });
  const scope = await panelA.getAttribute('data-scope');
  log('scenario scope', scope);
  const keys = await panelA.locator('[data-testid="param-row"]').evaluateAll((rows) => rows.map((r) => r.getAttribute('data-key')));
  log('rows', keys.slice(0, 8));
  await a.waitForTimeout(2500);
  const b = await context.newPage();
  await b.goto(a.url(), { waitUntil: 'load' });
  const panelB = b.getByTestId('parameter-panel');
  await panelB.waitFor({ timeout: 120000 });
  await b.waitForTimeout(2500);
  log('tab B open on the same scenario', await panelB.getAttribute('data-scope'));
  // Tab A sets the first parameter that offers a value box.
  const settable = async (page) => {
    const rows = page.locator('[data-testid="param-row"]');
    const n = await rows.count();
    const found = [];
    for (let i = 0; i < n && found.length < 2; i++) if (await rows.nth(i).getByTestId('param-value-input').count()) found.push(await rows.nth(i).getAttribute('data-key'));
    return found;
  };
  let [k1, k2] = await settable(a);
  if (!k1) {
    // A row shows its value box once a person chooses to type: open each row's own control if there is one.
    log('no value box shown at rest', true);
  }
  log('keys set', [k1, k2]);
  const set = async (page, key, v) => {
    const row = page.locator(`[data-testid="param-row"][data-key="${key}"]`);
    const box = row.getByTestId('param-value-input');
    await box.fill(String(v));
    await box.blur();
  };
  await a.bringToFront();
  await set(a, k1, 1.234);
  await a.waitForTimeout(2500);
  log('the service after tab A set its parameter', await held(scope));
  await b.bringToFront();
  await set(b, k2, 5.678);
  await b.waitForTimeout(2500);
  log('the service after tab B set another', await held(scope));
  await a.reload({ waitUntil: 'load' });
  await a.getByTestId('parameter-panel').waitFor({ timeout: 120000 });
  await a.waitForTimeout(2500);
  log('tab A after a reload shows', await a.locator(`[data-testid="param-row"][data-key="${k1}"] [data-testid="param-value"]`).innerText().catch(() => ''));
} catch (e) {
  log('stopped', String(e).slice(0, 300));
}
writeFileSync(out, JSON.stringify(report, null, 1));
await browser.close();
