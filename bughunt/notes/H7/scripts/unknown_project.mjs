// H7: an address naming a project the service does not hold (/p/<unknown>/...): how many times the page loads in
// 15 s, where the address ends, and what the screen says.
//   node unknown_project.mjs <origin> <unknown id>
import { chromium } from 'playwright';

const [origin, unknown] = process.argv.slice(2);
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--no-proxy-server'] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
let loads = 0;
const projects = [];
page.on('load', () => (loads += 1));
page.on('request', (r) => r.url().endsWith('/api/projects') && projects.push(Date.now()));
await page.goto(`${origin}/#/p/${unknown}/runbooks`, { waitUntil: 'load' });
await page.waitForTimeout(15000);
console.log('page loads in 15 s:', loads);
console.log('GET /api/projects in 15 s:', projects.length);
console.log('address now:', await page.evaluate(() => location.hash).catch(() => '?'));
console.log('localStorage project:', await page.evaluate(() => localStorage.getItem('openferment.project')).catch(() => '?'));
console.log('screen:', (await page.locator('body').innerText().catch(() => '')).replace(/\s+/g, ' ').slice(0, 300));
await browser.close();
