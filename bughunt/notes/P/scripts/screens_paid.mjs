// Hunt P: the paid debts tried on the built app in Chromium, against a service of the hunt's own.
//   ORIGIN=http://127.0.0.1:8950 node bughunt/notes/P/scripts/screens_paid.mjs
// Rows: 5 (catalogues screen keeps a strain; geneOS Hosts names it; a protocol begun on its page, its editor's
// skill picker naming the project's skill catalogue, kept as 1.1), 6 (a skill kept with no policy: Guild says it
// waits), 7 (the protocols page begins one), 29 (the rail), 32 (Postdoc's empty list words).
import { chromium } from 'playwright';

const ORIGIN = process.env.ORIGIN ?? 'http://127.0.0.1:8950';
const PERSON = 'Ada Moreno';
const out = [];
const say = (ok, what) => { out.push(`${ok ? 'OK ' : 'XX '} ${what}`); console.log(`${ok ? 'OK ' : 'XX '} ${what}`); };
const api = async (path, project, init = {}) => {
  const r = await fetch(`${ORIGIN}${path}`, { ...init, headers: { 'X-OpenFerment-Project': project, 'content-type': 'application/json', ...(init.headers ?? {}) } });
  return { status: r.status, body: await r.json().catch(() => null) };
};

const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1243/chrome-linux64/chrome', args: ['--no-proxy-server'] });
const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
page.setDefaultTimeout(30000);
const errors = [];
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
page.on('pageerror', (e) => errors.push(e.message));
const at = (p, path) => page.goto(`${ORIGIN}/#/p/${p}${path}`);

async function step(name, body) {
  try { say(true, `${name}: ${await body()}`); }
  catch (e) {
    const words = (await page.locator('#of-main').innerText({ timeout: 2000 }).catch(() => '')).replace(/\s+/g, ' ').slice(0, 400);
    say(false, `${name}: ${String(e.message ?? e).split('\n')[0]} | page: ${words}`);
  }
}

await step('name', async () => {
  await at('pb', '/settings/corpus');
  await page.locator('#reviewer-name').fill(PERSON);
  await page.waitForTimeout(600);
  return 'set';
});

await step('row 29 rail', async () => {
  await at('pb', '/');
  const rail = await page.locator('nav').first().innerText();
  return rail.replace(/\s+/g, ' | ').slice(0, 400);
});

await step('row 5 catalogue strain kept on the screen', async () => {
  await at('pb', '/catalogues');
  await page.locator('[data-testid="catalogues"][data-kind="strain"]').waitFor();
  await page.locator('[data-testid="catalogue-entry"][data-entry="st-p5"]').waitFor();
  await page.getByTestId('catalogue-add').click();
  const add = page.locator('[data-testid="catalogue-form"][data-mode="add"]');
  await add.getByTestId('catalogue-field-id').fill('st-ui-p');
  await add.getByTestId('catalogue-field-name').fill('Placeholdera screenii');
  await add.getByTestId('catalogue-field-aliases').fill('UI alias');
  await add.getByTestId('catalogue-keep').click();
  await page.locator('[data-testid="catalogue-entry"][data-entry="st-ui-p"]').waitFor();
  const held = await api('/api/catalogues/strain/st-ui-p', 'pb');
  if (held.status !== 200 || held.body.by !== PERSON || held.body.agent !== 'person') throw new Error(JSON.stringify(held));
  return `kept by ${held.body.by} (${held.body.agent}); st-p5 from the file listed`;
});

await step('row 5 geneOS Hosts names both strains with no reload', async () => {
  await at('pb', '/geneos/hosts');
  for (const id of ['st-p5', 'st-ui-p']) await page.locator(`[data-testid="strain-card"][data-strain="${id}"]`).waitFor();
  const other = await page.locator('[data-testid="strain-card"]').count();
  return `${other} strain cards`;
});

await step('row 5 pa sees none of pb strains on Hosts', async () => {
  await at('pa', '/geneos/hosts');
  await page.waitForTimeout(2500);
  const n = await page.locator('[data-testid="strain-card"]').count();
  if (n !== 0) throw new Error(`${n} cards in pa`);
  return 'no strain card in pa';
});

await step('row 7 protocols page begins one; row 5 editor picker names pa skills, kept as 1.1', async () => {
  await at('pa', '/runbooks/protocols');
  await page.getByTestId('begin-protocol-open').click();
  const f = page.getByTestId('begin-protocol');
  await f.getByTestId('begin-protocol-id').fill(process.env.PROTO ?? 'pr-ui-p');
  await f.getByTestId('begin-protocol-title').fill('A placeholder protocol begun on the page');
  await f.getByTestId('begin-protocol-batchValue').fill('1');
  await f.getByTestId('begin-protocol-batchUnit').fill('L');
  await f.getByTestId('begin-protocol-active').fill('5');
  await f.getByTestId('begin-protocol-total').fill('10');
  await f.getByTestId('begin-protocol-steps').fill('A first placeholder step\nA second placeholder step');
  await f.getByTestId('begin-protocol-keep').click();
  await page.waitForURL(/\/edit/);
  const group = page.getByRole('group', { name: 'Step 1 skills' });
  await group.waitFor();
  const chips = (await group.innerText()).replace(/\s+/g, ' ');
  await group.getByRole('button', { name: 'A placeholder skill', exact: true }).first().click();
  await page.getByRole('button', { name: /Save as v/ }).click();
  await page.getByRole('button', { name: /Keep this version/ }).click();
  await page.waitForTimeout(2500);
  const held = await api(`/api/protocols/${process.env.PROTO ?? 'pr-ui-p'}`, 'pa');
  const v = held.body?.versions?.map((x) => `${x.version}:${x.by}:${x.steps.map((s) => (s.skills ?? []).join('+')).join(',')}`);
  if (held.body?.currentVersion !== '1.1') throw new Error(`current ${held.body?.currentVersion} ${JSON.stringify(v)}`);
  return `picker: "${chips.slice(0, 120)}"; versions ${JSON.stringify(v)}`;
});

await step('row 6 a skill kept with no policy', async () => {
  const r = await api('/api/catalogues/skill/SK-P5', 'pa');
  await at('pa', `/guild/skills/${encodeURIComponent('SK-P5')}`);
  await page.waitForTimeout(2500);
  const words = (await page.locator('#of-main').innerText()).replace(/\s+/g, ' ');
  const m = words.match(/[^.]*polic[^.]*\./gi);
  return `criticality ${r.body?.criticality}; page says: ${m ? m.slice(0, 3).join(' / ') : words.slice(0, 200)}`;
});

await step('row 32 Postdoc empty list', async () => {
  await at('pb', '/postdoc');
  await page.waitForTimeout(2500);
  const words = (await page.locator('#of-main').innerText()).replace(/\s+/g, ' ');
  const m = words.match(/[^.]*(conversation)[^.]*\./gi);
  return m ? m.slice(0, 3).join(' / ') : words.slice(0, 300);
});

say(errors.length === 0, `console errors: ${errors.length} ${errors.slice(0, 5).join(' || ')}`);
await browser.close();
