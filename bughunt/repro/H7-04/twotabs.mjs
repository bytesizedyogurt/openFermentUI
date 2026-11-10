// H7-04: two tabs on one Proforma scenario's parameter panel, the service up; tab A types a value for one parameter,
// then tab B types a value for another. What each tab sends (PUT /api/state/overrides/<scope>), what the service holds
// after each write (GET /api/state), what tab A shows after a reload, and every toast either tab showed.
//
//   node twotabs.mjs <origin> <project> <scenario id> <key A> <key B> <out.json>
import { chromium } from 'playwright';
import { writeFileSync } from 'node:fs';

const [origin, project, scenarioId, keyA, keyB, out] = process.argv.slice(2);
const PERSON = 'H7 Repro';
const VALUE_A = 1.234;
const VALUE_B = 5.678;
const scope = `proforma:${scenarioId}`;
const facts = { scope, keyA, keyB, valueA: VALUE_A, valueB: VALUE_B, sent: { A: [], B: [] }, words: { A: [], B: [] } };
const note = (what, data) => console.log(`- ${what}: ${JSON.stringify(data)}`);
const at = (page, path) => page.goto(`${origin}/#/p/${encodeURIComponent(project)}${path}`, { waitUntil: 'load' });

/** The scope's overrides the service holds, as key=value. */
async function held() {
  const r = await fetch(`${origin}/api/state`, { headers: { 'X-OpenFerment-Project': project } });
  const s = await r.json();
  return (s.overrides?.[scope] ?? []).map((o) => `${o.key}=${o.value}`);
}
async function until(test, ms = 15000) {
  const end = Date.now() + ms;
  for (;;) {
    const got = await held();
    if (test(got) || Date.now() > end) return got;
    await new Promise((r) => setTimeout(r, 250));
  }
}
/** Each PUT of this scope's overrides a tab sends, with the list it carries. */
function watch(page, tab) {
  page.on('request', (req) => {
    if (req.method() === 'PUT' && decodeURIComponent(req.url()).includes(`/api/state/overrides/${scope}`)) {
      let list = null;
      try {
        list = (JSON.parse(req.postData() ?? '{}').value ?? []).map((o) => `${o.key}=${o.value}`);
      } catch {
        list = 'unreadable';
      }
      facts.sent[tab].push(list);
    }
  });
}
/** Every toast the page shows, read off the polite live region as it appears. */
const TOAST_WATCH = () => {
  window.__h7words = [];
  const seen = new Set();
  new MutationObserver(() => {
    for (const region of document.querySelectorAll('[aria-live="polite"]'))
      for (const el of region.children) {
        const t = (el.textContent ?? '').trim();
        if (t && !seen.has(t)) {
          seen.add(t);
          window.__h7words.push(t);
        }
      }
  }).observe(document, { childList: true, subtree: true, characterData: true });
};
const wordsOf = (page) => page.evaluate(() => window.__h7words ?? []).catch(() => []);
async function openPanel(page) {
  await at(page, `/proforma/scenario/${encodeURIComponent(scenarioId)}`);
  const panel = page.locator(`[data-testid="parameter-panel"][data-scope="${scope}"]`);
  await panel.waitFor({ timeout: 60000 });
  await panel.locator(`[data-testid="param-row"][data-key="${keyA}"] [data-testid="param-value-input"]:not([disabled])`).waitFor({ timeout: 30000 });
  await page.waitForTimeout(1500);
  return panel;
}
async function type(page, key, v) {
  const box = page.locator(`[data-testid="param-row"][data-key="${key}"] [data-testid="param-value-input"]`);
  await box.fill(String(v));
  await box.blur();
}

const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--no-proxy-server'] });
const context = await browser.newContext({ viewport: { width: 1400, height: 1000 } });
await context.addInitScript(TOAST_WATCH);
try {
  // The reviewer name, a preference both tabs read from the browser's snapshot.
  const a = await context.newPage();
  await at(a, '/settings/corpus');
  await a.locator('#reviewer-name').fill(PERSON);
  await a.locator('#reviewer-name').blur();
  await a.waitForTimeout(1000);
  watch(a, 'A');
  await openPanel(a);
  const b = await context.newPage();
  watch(b, 'B');
  await openPanel(b);
  facts.before = await held();
  note('the service before either tab types', facts.before);

  await a.bringToFront();
  await type(a, keyA, VALUE_A);
  facts.afterA = await until((h) => h.includes(`${keyA}=${VALUE_A}`));
  note(`the service after tab A typed ${keyA}=${VALUE_A}`, facts.afterA);

  await b.bringToFront();
  await type(b, keyB, VALUE_B);
  facts.afterB = await until((h) => h.includes(`${keyB}=${VALUE_B}`));
  await b.waitForTimeout(1500);
  facts.afterB = await held();
  note(`the service after tab B typed ${keyB}=${VALUE_B}`, facts.afterB);
  facts.bShowsKeyA = await b.locator(`[data-testid="param-row"][data-key="${keyA}"] [data-testid="param-value"]`).innerText();
  facts.words.B = await wordsOf(b);
  facts.words.A = await wordsOf(a);

  await a.reload({ waitUntil: 'load' });
  await openPanel(a);
  await a.waitForTimeout(1500);
  facts.aShowsKeyAAfterReload = await a.locator(`[data-testid="param-row"][data-key="${keyA}"] [data-testid="param-value"]`).innerText();
  facts.aOverriddenAfterReload = await a.locator(`[data-testid="param-row"][data-key="${keyA}"]`).getAttribute('data-overridden');
  facts.words.A = [...facts.words.A, ...(await wordsOf(a))];
  note('tab A after a reload shows ' + keyA, { value: facts.aShowsKeyAAfterReload, overridden: facts.aOverriddenAfterReload });
  note('what each tab sent for the scope', facts.sent);
  note('toasts shown', facts.words);
} catch (e) {
  facts.stopped = String(e).slice(0, 400);
  note('stopped', facts.stopped);
}
writeFileSync(out, JSON.stringify(facts, null, 1));
await browser.close();
