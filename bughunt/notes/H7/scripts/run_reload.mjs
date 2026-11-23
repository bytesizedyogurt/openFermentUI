// H7: a protocol's run at the bench, a step completed and a deviation note added, then the page reloaded (the
// browser's leave-page prompt accepted, as a person does who reloads a frozen tablet); what the run screen shows after.
//   node run_reload.mjs <origin> <project> <protocol id>
import { chromium } from 'playwright';

const [origin, project, protocol] = process.argv.slice(2);
const at = (page, path) => page.goto(`${origin}/#/p/${encodeURIComponent(project)}${path}`, { waitUntil: 'load' });
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--no-proxy-server'] });
const page = await browser.newPage({ viewport: { width: 810, height: 1080 } });
const dialogs = [];
page.on('dialog', async (d) => {
  dialogs.push(d.type());
  await d.accept();
});
await at(page, '/settings/corpus');
await page.locator('#reviewer-name').fill('H7 Hunter');
await page.waitForTimeout(800);
await at(page, `/runbooks/protocols/${protocol}`);
await page.getByRole('button', { name: /Start run at/ }).first().click();
await page.waitForURL(/\/run\//);
await page.waitForTimeout(1000);
const address = await page.evaluate(() => location.hash);
console.log('run opened at', address);
await page.getByRole('button', { name: /Add deviation note/ }).click();
await page.locator('textarea').last().fill('the flask was left uncapped for a minute');
await page.getByRole('dialog').getByRole('button', { name: 'Record' }).click();
await page.waitForTimeout(500);
console.log('the step shows the note:', (await page.locator('main').innerText()).includes('uncapped'));
await page.getByLabel('Next step').click();
await page.getByRole('button', { name: /Start timer/ }).click();
await page.waitForTimeout(1500);
console.log('before the reload:', (await page.locator('header').first().innerText()).replace(/\s+/g, ' '));
await page.reload({ waitUntil: 'load' });
await page.waitForTimeout(3000);
console.log('leave-page prompts shown:', dialogs);
console.log('after the reload, address', await page.evaluate(() => location.hash));
console.log('after the reload, the screen:', (await page.locator('body').innerText()).replace(/\s+/g, ' ').slice(0, 400));
await browser.close();
