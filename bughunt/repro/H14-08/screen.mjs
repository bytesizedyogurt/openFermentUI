// H14-08: open a project's Home and its pureOS page in headless Chromium (no proxy) and print, as one JSON line,
// Home's pureOS destination (title, descriptor, state line), pureOS's subtitle and pureOS's "Produced by" line.
//   node screen.mjs ORIGIN PROJECT [SHOT_PREFIX]
import { chromium } from 'playwright';

const [origin, project, shot] = process.argv.slice(2);
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--no-proxy-server'] });
const page = await (await browser.newContext({ viewport: { width: 1440, height: 1000 } })).newPage();
const go = async (path) => {
  await page.goto(`${origin}/#${path}`);
  await page.waitForLoadState('networkidle').catch(() => {});
  await page.waitForTimeout(2500);
};
const lines = async () => {
  const main = (await page.$('#of-main')) ? await page.innerText('#of-main') : '';
  return main.split('\n').map((l) => l.trim()).filter(Boolean);
};
const after = (ls, re, n) => {
  const i = ls.findIndex((l) => re.test(l));
  return i < 0 ? [] : ls.slice(i, i + n);
};

await go(`/p/${project}`);
await go('/');
const home = await lines();
const homePureos = after(home, /^pureOS$/, 3);
if (shot) await page.screenshot({ path: `${shot}-home.png`, fullPage: true });

await go(`/p/${project}/pureos`);
const pure = await lines();
const titleAt = pure.findIndex((l) => l === 'pureOS');
const subtitle = titleAt < 0 ? '' : pure[titleAt + 1] || '';
const producedAt = pure.findIndex((l) => /^Produced by$/.test(l));
const produced = producedAt < 0 ? [] : pure.slice(producedAt, producedAt + 4);
if (shot) await page.screenshot({ path: `${shot}-pureos.png`, fullPage: true });

console.log(JSON.stringify({ homePureos, subtitle, produced }));
await browser.close();
