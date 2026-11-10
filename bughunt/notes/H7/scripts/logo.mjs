// H7: the rail's logo inside a project, and where the links of the screen it opens lead.
//   node logo.mjs <origin> <project>
import { chromium } from 'playwright';

const [origin, project] = process.argv.slice(2);
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--no-proxy-server'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await page.goto(`${origin}/#/p/${project}/runbooks`, { waitUntil: 'load' });
await page.waitForTimeout(2500);
console.log('start address:', await page.evaluate(() => location.hash));
await page.locator('nav[aria-label="Primary"] a').first().click();
await page.waitForTimeout(1500);
console.log('after the logo:', await page.evaluate(() => location.hash));
console.log('the screen drawn:', (await page.locator('#of-main').innerText()).replace(/\s+/g, ' ').slice(0, 160));
console.log('the top bar names:', (await page.locator('[data-testid="project-switch"]').innerText().catch(() => '')).trim());
const rail = await page.locator('nav[aria-label="Primary"] a').evaluateAll((as) => as.map((a) => a.getAttribute('href')));
console.log('rail links now:', rail.join(' '));
await page.locator('nav[aria-label="Primary"] a[href="#/intake"]').click();
await page.waitForTimeout(1500);
console.log('after the rail Intake link:', await page.evaluate(() => location.hash));
await browser.close();
