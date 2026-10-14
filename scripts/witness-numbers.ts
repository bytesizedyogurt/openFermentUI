/**
 * The precision and recall Witness shows, printed (OF-BLD-014 §1.5).
 *
 *   pnpm witness:numbers [--url http://127.0.0.1:8000]
 *
 * Witness computes its scores in the browser, so this is how a session reads
 * them. It builds the store the app builds: the seed, with the service's
 * overlay applied by the store's own `applyOverlay`, and the runs from
 * GET /api/witness/runs. Then `computeRunMetrics` (src/engine/metrics.ts)
 * scores each run on the two bases the screen offers: provisional, where
 * the curated records on fetched papers stand in as gold until a reviewer
 * flags gold in Guild, and measured, gold records alone. The provisional
 * records are made exactly as Witness.tsx makes them (OF-BLD-012 §6.4).
 *
 * Needs a running service (`pnpm prototype:up`, or `pnpm demo:offline` for
 * the fixtures). Spends nothing.
 */
import { useStore } from '../src/store';
import { computeRunMetrics, type RunMetrics } from '../src/engine/metrics';
import type { ExtractionRecord, Overlay, RunOutput } from '../src/data/types';

const args = process.argv.slice(2);
const at = args.indexOf('--url');
const base = (at >= 0 ? args[at + 1] : 'http://127.0.0.1:8000')?.replace(/\/+$/, '');
const stray = args.filter((a, i) => !(i === at || (at >= 0 && i === at + 1)));
if (!base || stray.length) {
  console.error('usage: pnpm witness:numbers [--url http://127.0.0.1:8000]');
  process.exit(2);
}

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${base}${path}`);
  if (!r.ok) throw new Error(`${path} answered ${r.status}: ${(await r.text()).slice(0, 200)}`);
  return (await r.json()) as T;
}

// Witness.tsx's rules: a ratio with nothing under it shows as a dash, and F1
// shows when both of its parts do.
const pct = (x: number, defined: boolean) => (defined ? `${(100 * x).toFixed(1)} %` : '—');

function line(label: string, m: RunMetrics, headline: boolean): string {
  const { precision, recall, f1, tp, fp, fn } = m.micro;
  const p = tp + fp > 0;
  const r = tp + fn > 0;
  return (
    `  ${label.padEnd(12)} precision ${pct(precision, p).padStart(7)}  recall ${pct(recall, r).padStart(7)}  ` +
    `F1 ${pct(f1, p && r).padStart(7)}   tp ${tp}  fp ${fp}  fn ${fn}   ` +
    `gold set ${m.goldSize} records on ${m.papersCovered} papers${headline ? '   (the screen\'s headline)' : ''}`
  );
}

async function main(): Promise<number> {
  let overlay: Overlay;
  let runs: RunOutput[];
  try {
    [overlay, runs] = await Promise.all([get<Overlay>('/api/biorepo/overlay'), get<RunOutput[]>('/api/witness/runs')]);
  } catch (e) {
    console.error(`✗ could not read the service at ${base}: ${(e as Error).message}`);
    console.error('  Start it first: pnpm prototype:up (or pnpm demo:offline for the fixtures).');
    return 1;
  }

  useStore.getState().applyOverlay({ ...overlay, runs });
  const { records, papers, runOutputs } = useStore.getState();

  // Witness.tsx, provisional mode: a curated record on a fetched paper stands
  // in as gold at its own value; gold, rejected and extracted records do not.
  const fetched = new Set(papers.filter((p) => p.textSource === 'full-text').map((p) => p.id));
  const provisional: ExtractionRecord[] = records.map((r) =>
    r.gold || r.status === 'rejected' || r.extractorRun === 'claude-1' || !fetched.has(r.paperId)
      ? r
      : { ...r, gold: { value: r.value, unit: r.unit } },
  );
  const hasRealGold = records.some((r) => r.gold);

  console.log(`openFerment — what Witness shows (${base}, ${new Date().toISOString().slice(0, 10)})`);
  console.log('──────────────────────────────────────────────');
  console.log(`  papers with fetched full text  ${fetched.size}`);
  console.log(`  records with gold set          ${records.filter((r) => r.gold).length}`);
  const live = new Set(runs.map((r) => r.run));
  if (!runs.length) console.log('\n  No extraction has run on this service yet: GET /api/witness/runs is empty.');
  for (const run of runOutputs) {
    const from = live.has(run.run) ? 'GET /api/witness/runs' : 'seed (src/data/runOutputs.ts)';
    console.log(`\n${run.run}  (${from})`);
    // The screen opens on provisional until a gold record exists, and on
    // measured from then on, with the other basis beside it.
    console.log(line('provisional', computeRunMetrics(run, provisional), !hasRealGold));
    console.log(
      hasRealGold
        ? line('measured', computeRunMetrics(run, records), true)
        : '  measured     no gold record yet: a reviewer flags gold in Guild',
    );
  }
  return 0;
}

process.exit(await main());
