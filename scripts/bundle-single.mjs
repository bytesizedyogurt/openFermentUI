/**
 * Produce a single self-contained HTML file from the Vite build.
 *
 * The artifact host wraps the output in its own <!doctype>/<head>/<body>, and
 * a strict CSP blocks every external host — so CSS, JS and fonts all have to
 * be inlined. woff2 covers every browser that can run this app, so the woff
 * fallbacks are dropped rather than doubling the payload.
 *
 *   pnpm build && node scripts/bundle-single.mjs
 */
import { readFile, writeFile, readdir } from 'node:fs/promises';
import { join } from 'node:path';

const DIST = join(process.cwd(), 'dist');
const ASSETS = join(DIST, 'assets');

const files = await readdir(ASSETS);
const jsName = files.find((f) => f.endsWith('.js'));
const cssName = files.find((f) => f.endsWith('.css'));
if (!jsName || !cssName) throw new Error('run `pnpm build` first');

let css = await readFile(join(ASSETS, cssName), 'utf8');
const js = await readFile(join(ASSETS, jsName), 'utf8');

// Inline woff2 as data URIs; drop the woff duplicates entirely.
let inlined = 0;
const woff2 = files.filter((f) => f.endsWith('.woff2'));
for (const f of woff2) {
  const b64 = (await readFile(join(ASSETS, f))).toString('base64');
  const re = new RegExp(`url\\(["']?[^)"']*${f.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}["']?\\)`, 'g');
  if (re.test(css)) inlined++;
  css = css.replace(re, `url(data:font/woff2;base64,${b64})`);
}
// Strip any remaining src entries that point at files we are not inlining.
css = css.replace(/,?\s*url\((?!data:)[^)]*\.woff\)\s*format\(["']woff["']\)/g, '');
css = css.replace(/src:\s*;/g, '');

const remaining = css.match(/url\((?!data:)[^)]+\)/g);
if (remaining) console.warn(`⚠ ${remaining.length} un-inlined url() left:`, remaining.slice(0, 3));

const html = `<title>openFerment — agentic bioprocess platform</title>
<style>
${css}
</style>
<div id="root"></div>
<script type="module">
${js.replace(/<\/script/gi, '<\\/script')}
</script>
`;

const out = join(DIST, 'openferment-standalone.html');
await writeFile(out, html);
const mb = (Buffer.byteLength(html) / 1024 / 1024).toFixed(2);
console.log(`✓ ${out}\n  ${mb} MB · ${inlined}/${woff2.length} woff2 inlined · woff fallbacks dropped`);
