// H14-05: open a project's Home in headless Chromium (no proxy) and print, as one JSON line, the Gold set tile's
// text and the BioRepo destination's text.   node screen.mjs ORIGIN PROJECT SHOT.png
import { chromium } from 'playwright';

const [origin, project, shotPath] = process.argv.slice(2);
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--no-proxy-server'] });
const page = await (await browser.newContext({ viewport: { width: 1440, height: 1000 } })).newPage();
const go = async (path) => {
  await page.goto(`${origin}/#${path}`);
  await page.waitForLoadState('networkidle').catch(() => {});
  await page.waitForTimeout(2500);
};
await go(`/p/${project}`);
await go('/');
const main = (await page.$('#of-main')) ? await page.innerText('#of-main') : '';
const lines = main.split('\n').map((l) => l.trim()).filter(Boolean);
const after = (re, n) => {
  const i = lines.findIndex((l) => re.test(l));
  return i < 0 ? [] : lines.slice(i, i + n);
};
// The Gold set tile: its label, its count and its sub-line.
const goldTile = after(/^gold set$/i, 3);
// The BioRepo destination card: its title, descriptor and state line.
const bioRepo = after(/^BioRepo$/, 3);
if (shotPath) await page.screenshot({ path: shotPath, fullPage: true });
console.log(JSON.stringify({ goldTile, bioRepo }));
await browser.close();
