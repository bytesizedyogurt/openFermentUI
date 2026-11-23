// H7-08: inside a project, the rail's logo, and where the address and the rail's links stand after it.
//   node logo.mjs <origin> <project> <facts.json>
import { chromium } from 'playwright';
import { writeFileSync } from 'node:fs';

const [origin, project, factsPath] = process.argv.slice(2);
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--no-proxy-server'] });
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await context.newPage();
const rail = () => page.locator('nav[aria-label="Primary"] a').evaluateAll((as) => as.map((a) => a.getAttribute('href')));
const hash = () => page.evaluate(() => location.hash);
const main = async () => (await page.locator('#of-main').innerText()).replace(/\s+/g, ' ').slice(0, 120);
const topBar = async () => (await page.locator('[data-testid="project-switch"]').innerText().catch(() => '')).trim();

// A fresh browser opens a module screen inside the project; the page reloads once into it (ADR-009 7.1).
await page.goto(`${origin}/#/p/${project}/runbooks`, { waitUntil: 'load' });
await page.waitForFunction(() => document.querySelector('[data-testid="project-switch"]') && !document.querySelector('[data-testid="opening-project"]'), null, { timeout: 30000 });
await page.waitForTimeout(1500);
const before = { address: await hash(), rail: await rail(), topBar: await topBar(), main: await main() };

// The rail's logo: the first anchor in the primary navigation.
await page.locator('nav[aria-label="Primary"] a').first().click();
await page.waitForTimeout(1500);
const afterLogo = { address: await hash(), rail: await rail(), topBar: await topBar(), main: await main(),
  stored: await page.evaluate(() => localStorage.getItem('openferment.project')) };

// One rail link from the screen the logo opened.
await page.locator('nav[aria-label="Primary"] a[aria-label^="Intake:"]').click();
await page.waitForTimeout(1500);
const afterIntake = { address: await hash(), topBar: await topBar() };

writeFileSync(factsPath, JSON.stringify({ project, before, afterLogo, afterIntake }, null, 2));
await browser.close();
