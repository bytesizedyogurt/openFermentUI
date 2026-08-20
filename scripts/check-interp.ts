/**
 * Does multilinear interpolation still tell the truth about the grids?
 *
 *   pnpm check:interp   (→ tsx scripts/check-interp.ts)
 *
 * `interp.ts` is the one engine module CLAUDE.md keeps in TypeScript on its own
 * merits — grid interpolation for slider smoothness is a genuine UI concern —
 * and it was also the one numeric module with NO pin at all: the Phase 0
 * capture recorded units, scale, diff and metrics, and never interp. Every
 * number a slider shows between two solved points passes through this file
 * unchecked. This closes that.
 *
 * No remembered constants. Every expectation below is either a mathematical
 * property of multilinear interpolation or a cross-check against the live cost
 * models — the same discipline as the other checkers: an expected value someone
 * typed in is a second implementation of the answer.
 *
 *   1. NODE EXACTNESS   at every grid node, interpolation returns the stored
 *                       solve exactly. An interpolant that cannot reproduce its
 *                       own data is wrong before it starts.
 *   2. AXIS LINEARITY   halfway between two adjacent nodes (other dims held at
 *                       nodes), the value is the mean of the endpoints.
 *   3. CLAMPING         a point outside the grid answers as the nearest edge
 *                       point, and an empty point answers as the low corner —
 *                       absent keys clamp low by design.
 *   4. THE WATERFALL    cost lines sum to MSP at every node by construction;
 *                       interpolation is linear, so the identity must survive
 *                       at every point BETWEEN nodes too. This is what lets the
 *                       waterfall on screen agree with the headline while a
 *                       slider is mid-drag.
 *   5. LIVE CROSS-CHECK a sample of nodes re-solved through the model's own
 *                       evaluate(), tying the stored grid to the plant rather
 *                       than to itself.
 */
import { COST_MODELS } from '../src/data/scenarios';
import { buildGrid, COST_LINES } from '../src/engine/grids';
import { clampPoint, gridIndex, interpolate, type Grid } from '../src/engine/interp';

const REL_TOL = 1e-9; // float accumulation across 2^n corner weights
let checked = 0;
const failures: string[] = [];

function close(a: number, b: number, tol = REL_TOL): boolean {
  if (Object.is(a, b)) return true;
  if (!Number.isFinite(a) || !Number.isFinite(b)) return false;
  return Math.abs(a - b) <= tol * Math.max(Math.abs(a), Math.abs(b), 1e-300);
}

function fail(model: string, what: string, expected: number, got: number): void {
  failures.push(`${model}: ${what} — expected ${expected}, got ${got}`);
}

/** Deterministic PRNG so a failure names a reproducible point. */
function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function* nodes(dims: { key: string; values: number[] }[]): Generator<number[]> {
  const idx = dims.map(() => 0);
  while (true) {
    yield [...idx];
    let d = dims.length - 1;
    while (d >= 0 && ++idx[d] === dims[d].values.length) idx[d--] = 0;
    if (d < 0) return;
  }
}

const pointAt = (dims: { key: string; values: number[] }[], idx: number[]) =>
  Object.fromEntries(dims.map((d, i) => [d.key, d.values[idx[i]]]));

console.log('openFerment interpolation properties — live grids from the three cost models');
console.log('────────────────────────────────────────────────────────────────────────────');

for (const model of COST_MODELS) {
  const grid = buildGrid(model);
  const dims = grid.dims;
  const msp: Grid = { dims, data: grid.msp };
  const rand = mulberry32(0x0f_e2_71);

  // 1 — node exactness, every node, MSP and every cost line
  for (const idx of nodes(dims)) {
    const p = pointAt(dims, idx);
    const flat = gridIndex(dims, idx);
    checked += 1;
    if (!close(interpolate(msp, p), grid.msp[flat], 1e-12))
      fail(model.modelId, `node ${JSON.stringify(p)} msp`, grid.msp[flat], interpolate(msp, p));
    for (const line of COST_LINES) {
      checked += 1;
      const g: Grid = { dims, data: grid.costLines[line] };
      if (!close(interpolate(g, p), grid.costLines[line][flat], 1e-12))
        fail(model.modelId, `node ${JSON.stringify(p)} ${line}`, grid.costLines[line][flat], interpolate(g, p));
    }
  }

  // 2 — per-axis midpoint linearity from every node with a right-hand neighbour
  for (const idx of nodes(dims)) {
    for (let d = 0; d < dims.length; d++) {
      if (idx[d] + 1 >= dims[d].values.length) continue;
      const hi = [...idx];
      hi[d] += 1;
      const p = pointAt(dims, idx);
      p[dims[d].key] = (dims[d].values[idx[d]] + dims[d].values[idx[d] + 1]) / 2;
      const mean = (grid.msp[gridIndex(dims, idx)] + grid.msp[gridIndex(dims, hi)]) / 2;
      checked += 1;
      if (!close(interpolate(msp, p), mean)) fail(model.modelId, `midpoint ${JSON.stringify(p)}`, mean, interpolate(msp, p));
    }
  }

  // 3 — clamping: far outside ≡ nearest corner; empty point ≡ low corner
  const loCorner = pointAt(dims, dims.map(() => 0));
  const hiCorner = pointAt(dims, dims.map((d) => d.values.length - 1));
  const wayOut = Object.fromEntries(dims.map((d) => [d.key, d.values[d.values.length - 1] * 1e6 + 1]));
  const wayUnder = Object.fromEntries(dims.map((d) => [d.key, -1e9]));
  checked += 3;
  if (!close(interpolate(msp, wayOut), interpolate(msp, hiCorner), 1e-12))
    fail(model.modelId, 'clamp high', interpolate(msp, hiCorner), interpolate(msp, wayOut));
  if (!close(interpolate(msp, wayUnder), interpolate(msp, loCorner), 1e-12))
    fail(model.modelId, 'clamp low', interpolate(msp, loCorner), interpolate(msp, wayUnder));
  if (!close(interpolate(msp, {}), interpolate(msp, loCorner), 1e-12))
    fail(model.modelId, 'absent keys clamp low', interpolate(msp, loCorner), interpolate(msp, {}));
  const [, wasClamped] = clampPoint(dims, wayOut);
  checked += 1;
  if (!wasClamped) failures.push(`${model.modelId}: clampPoint did not report clamping a point far outside the grid`);

  // 4 — the waterfall survives interpolation: Σ lines = MSP at 200 seeded points
  for (let i = 0; i < 200; i++) {
    const p = Object.fromEntries(
      dims.map((d) => {
        const lo = d.values[0];
        const hi = d.values[d.values.length - 1];
        return [d.key, lo + (hi - lo) * rand()];
      }),
    );
    const sum = COST_LINES.reduce((acc, line) => acc + interpolate({ dims, data: grid.costLines[line] }, p), 0);
    checked += 1;
    if (!close(sum, interpolate(msp, p)))
      fail(model.modelId, `waterfall at ${JSON.stringify(p)}`, interpolate(msp, p), sum);
  }

  // 5 — a sample of nodes re-solved live through the model itself
  const all = [...nodes(dims)];
  for (let i = 0; i < 5; i++) {
    const idx = all[Math.floor(rand() * all.length)];
    const p = pointAt(dims, idx);
    const lines = model.evaluate(p);
    const sum = COST_LINES.reduce((acc, line) => acc + lines[line], 0);
    checked += 1;
    if (!close(sum, grid.msp[gridIndex(dims, idx)]))
      fail(model.modelId, `live re-solve at ${JSON.stringify(p)}`, grid.msp[gridIndex(dims, idx)], sum);
  }

  console.log(`  ${model.modelId}  dims=${dims.map((d) => d.values.length).join('×')}  ✓`);
}

console.log(`\n  ${checked} property checks across ${COST_MODELS.length} models`);
if (failures.length) {
  console.error(`\n✗ ${failures.length} interpolation propert${failures.length === 1 ? 'y' : 'ies'} violated:`);
  for (const f of failures.slice(0, 20)) console.error(`  - ${f}`);
  process.exit(1);
}
console.log('\n✓ interpolation reproduces its nodes, stays linear, clamps, and preserves the waterfall.\n');
