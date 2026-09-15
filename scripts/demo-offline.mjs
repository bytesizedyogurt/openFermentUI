/**
 * The offline demo (OF-BLD-012 §8.1).
 *
 *   pnpm demo:offline
 *
 * Replays the whole Intake → Extract → Witness → Guild loop from saved
 * responses, with no key and no network. Three things run:
 *
 *   1. openferment-core in FIXTURE MODE. `OPENFERMENT_FIXTURES=1` makes
 *      intake.py read the JATS from core/tests/fixtures/demo/jats/ and
 *      extract.py read the saved model response from .../demo/extract/, and
 *      makes both refuse the network and the API. `OPENFERMENT_DATA_DIR`
 *      points the service's fulltext/, candidates/ and biorepo.json at a
 *      scratch directory under core/data/demo/ (gitignored), seeded with the
 *      demo's biorepo.json — so nothing here touches core/data/biorepo.json,
 *      the committed decisions, or anything fetched for real.
 *   2. A production build of the app (`pnpm build`), unless --no-build.
 *   3. A static server for dist/ that proxies /api to the service, the way
 *      the Vite dev server does.
 *
 * Then it prints the route to open. The demo is: open Intake, fetch B5, run
 * extraction, open Witness, open Guild, decide a record, watch Witness move.
 *
 * What is and is not real in it: the B5 text is the structural stand-in
 * document until the real JATS is saved beside it (the fixture says how);
 * the "model response" is hand-written in the tool's shape; the anchoring,
 * the matching, the scoring, the write function and every refusal are the
 * real code paths. Ctrl-C stops everything.
 */
import { spawn, spawnSync } from 'node:child_process';
import { cpSync, existsSync, mkdirSync, rmSync } from 'node:fs';
import { createServer, request as httpRequest } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { join, extname } from 'node:path';

const ROOT = process.cwd();
const CORE = join(ROOT, 'core');
const DIST = join(ROOT, 'dist');
const DEMO = join(CORE, 'tests', 'fixtures', 'demo');
const DATA = join(CORE, 'data', 'demo');
const API_PORT = Number(process.env.OPENFERMENT_DEMO_API_PORT ?? 8000);
const PORT = Number(process.env.OPENFERMENT_DEMO_PORT ?? 4173);
const noBuild = process.argv.includes('--no-build');

const MIME = {
  '.html': 'text/html',
  '.js': 'text/javascript',
  '.css': 'text/css',
  '.svg': 'image/svg+xml',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.json': 'application/json',
};

const die = (m) => {
  console.error(`\n✗ ${m}`);
  process.exit(1);
};

// ── 0. what has to be there ─────────────────────────────────────────────
for (const f of ['jats/PMC8471596.xml', 'extract/B5.json', 'biorepo.json']) {
  if (!existsSync(join(DEMO, f))) die(`missing demo fixture core/tests/fixtures/demo/${f}`);
}
if (spawnSync('uv', ['--version'], { stdio: 'ignore' }).status !== 0) {
  die('`uv` is not on PATH — the service is Python; install uv (https://docs.astral.sh/uv/) and retry');
}

// ── 1. scratch data, seeded with the demo's decisions ─────────────────
rmSync(DATA, { recursive: true, force: true });
mkdirSync(DATA, { recursive: true });
cpSync(join(DEMO, 'biorepo.json'), join(DATA, 'biorepo.json'));

// ── 2. the corpus projection, and the build ────────────────────────────
const run = (cmd, args, extraEnv = {}) => {
  const r = spawnSync(cmd, args, { stdio: 'inherit', cwd: ROOT, env: { ...process.env, ...extraEnv } });
  if (r.status !== 0) die(`${cmd} ${args.join(' ')} failed`);
};
run('pnpm', ['export:corpus']);
if (!noBuild) run('pnpm', ['build']);
if (!existsSync(join(DIST, 'index.html'))) die('dist/index.html is missing — drop --no-build');

// ── 3. the service, in fixture mode ────────────────────────────────────
const service = spawn(
  'uv',
  ['run', 'uvicorn', 'openferment_core.api:app', '--port', String(API_PORT), '--log-level', 'warning'],
  {
    cwd: CORE,
    stdio: 'inherit',
    env: {
      ...process.env,
      OPENFERMENT_FIXTURES: '1',
      OPENFERMENT_FIXTURE_DIR: DEMO,
      OPENFERMENT_DATA_DIR: DATA,
      // No key, on purpose: fixture mode never calls the API, and the demo
      // must not be able to spend anything even if core/.env holds one.
      ANTHROPIC_API_KEY: '',
    },
  },
);
service.on('exit', (code) => {
  if (code !== null && code !== 0) die(`the service exited with ${code}`);
});

const waitForHealth = async () => {
  for (let i = 0; i < 60; i++) {
    try {
      const r = await fetch(`http://127.0.0.1:${API_PORT}/api/health`);
      if (r.ok) return await r.json();
    } catch {
      /* not up yet */
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  die(`the service did not answer /api/health on port ${API_PORT} within 30 s`);
};
const health = await waitForHealth();

// ── 4. dist/ plus a proxy to the service ───────────────────────────────
const web = createServer(async (req, res) => {
  const url = decodeURIComponent((req.url ?? '/').split('?')[0]);
  if (url.startsWith('/api/')) {
    const upstream = httpRequest(
      { host: '127.0.0.1', port: API_PORT, path: req.url, method: req.method, headers: req.headers },
      (up) => {
        res.writeHead(up.statusCode ?? 502, up.headers);
        up.pipe(res);
      },
    );
    upstream.on('error', () => {
      res.writeHead(502, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ detail: 'the demo service is not answering' }));
    });
    req.pipe(upstream);
    return;
  }
  try {
    let file = join(DIST, url === '/' ? 'index.html' : url);
    try {
      if ((await stat(file)).isDirectory()) file = join(file, 'index.html');
    } catch {
      file = join(DIST, 'index.html');
    }
    const body = await readFile(file);
    res.writeHead(200, { 'Content-Type': MIME[extname(file)] ?? 'application/octet-stream' });
    res.end(body);
  } catch {
    res.writeHead(404).end('not found');
  }
});
await new Promise((r) => web.listen(PORT, r));

console.log('\nopenFerment — offline demo');
console.log('──────────────────────────');
console.log(`  service     http://127.0.0.1:${API_PORT}  fixture mode, ${health.records} records, key: ${health.hasKey ? 'PRESENT (unexpected)' : 'none'}`);
console.log(`  data        ${DATA}  (scratch; seeded with the demo's three decisions)`);
console.log(`  fixtures    ${DEMO}`);
console.log(`\n  open        http://localhost:${PORT}/#/intake/ingest`);
console.log('\n  The loop: fetch B5 · Extract · open Witness · open Guild · decide a record · Witness moves.');
console.log('  B5’s text is the structural stand-in until the real JATS is saved (see the fixture).');
console.log('  Ctrl-C stops the service and the server.\n');

const stop = () => {
  service.kill('SIGTERM');
  web.close();
  process.exit(0);
};
process.on('SIGINT', stop);
process.on('SIGTERM', stop);
