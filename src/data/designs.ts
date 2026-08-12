// Design records (OF-FE-004 §2).
//
// Derived at load from the authored cost models, never seeded — §0 generalises
// the contradictions rule: anything the engine can compute is computed. Each
// design is a point in a model's sweep grid re-presented as a design, so it
// inherits the grid's `demo` provenance and cannot drift from the model.
import { SCENARIOS } from '@/data/source';
import { buildGrid } from '@/engine/grids';
import { COST_MODELS } from './scenarios';
import { designsFor } from '@/engine/designs';
import type { DesignRecord } from './types';

const GRIDS = Object.fromEntries(COST_MODELS.map((m) => [m.modelId, buildGrid(m)]));

export const DESIGNS: DesignRecord[] = SCENARIOS.flatMap((s) => {
  const grid = GRIDS[s.modelId];
  return grid ? designsFor(s, grid) : [];
});
