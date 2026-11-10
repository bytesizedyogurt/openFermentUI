// Fresh service: a new lab member opens Home, tries to make a project, sets a name, makes one, opens Intake's ingest.
//   node fresh1.mjs ORIGIN
import { open, shot, go, text, drain } from './lib.mjs';

const [origin] = process.argv.slice(2);
const { browser, page, log } = await open(origin);
await go(page, origin, '/');
await shot(page, 'f1-home-empty');
console.log('== home\n' + (await text(page)).slice(0, 3000));
console.log(drain(log).join('\n'));

// Make a project before a reviewer name is set.
await page.fill('#new-project-name', 'Lignin valorisation');
await page.click('[data-testid="new-project"] button[type=submit]');
await page.waitForTimeout(800);
console.log('== after Make it with no name:\n' + (await page.locator('[data-testid="new-project"]').innerText()));
await shot(page, 'f1-make-noname');

// Settings → reviewer name
await go(page, origin, '/settings/corpus');
await shot(page, 'f1-settings-corpus');
console.log('== settings corpus\n' + (await text(page)).slice(0, 2500));
console.log(drain(log).join('\n'));
await browser.close();
