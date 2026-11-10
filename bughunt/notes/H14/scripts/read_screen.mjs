// Open one screen of a project in Chromium, print the lines matching a pattern (with the next two), keep a screenshot.
//   node read_screen.mjs ORIGIN PROJECT PATH PATTERN SHOTNAME   (PATH HOME opens the project, then Home at /)
import { open, shot, go, text } from './lib.mjs';

const [origin, project, path, pattern, name] = process.argv.slice(2);
const { browser, page } = await open(origin);
await go(page, origin, `/p/${project}${path === 'HOME' ? '' : path}`);
await page.waitForTimeout(3000);
if (path === 'HOME') {
  await go(page, origin, '/');
  await page.waitForTimeout(3000);
}
const lines = (await text(page)).split('\n');
const re = new RegExp(pattern);
lines.forEach((l, i) => {
  if (re.test(l)) console.log(lines.slice(i, i + 3).join(' | '));
});
await shot(page, name);
await browser.close();
