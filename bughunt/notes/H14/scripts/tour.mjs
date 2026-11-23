// A first tour: every rail entry inside a project, a screenshot and the main region's text, console errors noted.
//   node tour.mjs ORIGIN PROJECT OUTPREFIX
import { open, shot, go, text, drain } from './lib.mjs';
import { writeFileSync } from 'node:fs';

const [origin, project, prefix = 'tour'] = process.argv.slice(2);
const paths = process.argv[5]
  ? process.argv[5].split(',')
  : ['', '/intake', '/biorepo', '/postdoc', '/geneos', '/fermos', '/pureos', '/proforma', '/runbooks', '/primer', '/guild', '/catalogues', '/settings'];
const { browser, page, log } = await open(origin);
await go(page, origin, '/');
await page.waitForTimeout(1000);
let out = '';
out += `== Home (no project)\n${await text(page)}\n${drain(log).join('\n')}\n`;
await shot(page, `${prefix}-home`);
for (const p of paths) {
  const addr = `/p/${project}${p}`;
  await go(page, origin, addr);
  await page.waitForTimeout(1500);
  const name = `${prefix}${p.replace(/\//g, '-') || '-project'}`;
  await shot(page, name);
  out += `\n== ${addr}\n${await text(page)}\n${drain(log).join('\n')}\n`;
}
writeFileSync(`/home/user/openFermentUI/bughunt/notes/H14/shots/${prefix}.txt`, out);
console.log(out.slice(0, 200000));
await browser.close();
