/**
 * The demo with nothing connected (OF-BLD-014 §10.3, Appendix 6).
 *
 *   pnpm demo:offline        # builds, then serves on http://127.0.0.1:4317
 *
 * The intake-loop demo of OF-BLD-012 §8.1, with the real service in fixture
 * mode, is `pnpm demo:offline:intake` (scripts/demo-offline.mjs).
 *
 * Serves the build beside the service double, which answers every /api route
 * the nine beats use from the fixtures `demo.py --prototype` generates: no
 * key, no network, no Python. Postdoc's live panel replays a recorded run and
 * says so, with the date it was recorded. Start it in a second terminal
 * before the demo; when the real service fails on the day, open this one.
 */
import { existsSync } from 'node:fs';
import { join } from 'node:path';
import { LOOPBACK } from './lib/serve-dist.mjs';
import { createServiceDouble } from './lib/service-double.mjs';

const DIST = join(process.cwd(), 'dist');
const PORT = Number(process.env.OPENFERMENT_DEMO_PORT ?? 4317);
if (!existsSync(join(DIST, 'index.html'))) {
  console.error('No build in dist/. Run `pnpm build` first (pnpm demo:offline does).');
  process.exit(1);
}
const { server } = createServiceDouble({ dist: DIST });
server.listen(PORT, LOOPBACK, () => {
  console.log(`openFerment, offline: http://${LOOPBACK}:${PORT}/`);
  console.log('Every service answer is a saved fixture; Postdoc labels its panel as a replay with its date.');
  console.log('Ctrl-C stops it.');
});
