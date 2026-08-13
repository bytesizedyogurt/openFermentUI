/**
 * Proforma, answered from the cost models and the bioSTEAM port in this repo.
 *
 * ── WHAT MAY NOT CROSS THIS SEAM ──────────────────────────────────────────
 *
 * `CostModel` and `ResultGrid` — the two types `src/data/types.ts` names as
 * unable to round-trip through JSON Schema, one carrying a function and the
 * other `Float64Array`s. They are runtime shapes, and a method returning
 * either would compile perfectly today and be unimplementable by any backend
 * that has to serialise its answer. So `listCostModels` returns
 * `CostModelSummary` (the model minus its `evaluate`), and the grid itself
 * never appears: interpolating one for a slider is a client-side convenience
 * over data the client already holds, which is exactly what CLAUDE.md's table
 * keeps in TypeScript.
 */
import { COST_MODELS } from '@/data/scenarios';
import { buildGrid, evaluateGrid } from '@/engine/grids';
import { deriveSensitivity, evaluatePlantCached, type PlantResult } from '@/engine/plant';
import { FLOWSHEET_BY_MODEL } from '@/sim/flowsheets/plants';
import type { ResultGrid } from '@/data/types';
import type { EvaluatedPoint } from '@/engine/grids';
import type {
  AdapterResponse,
  CostModelSummary,
  EconomicsAdapter,
  PointRequest,
  SensitivityBar,
} from '@/adapters/types';
import { plantModelVersion, respond } from './meta';

/**
 * Stated on every `evaluatePoint` response.
 *
 * The number is real and the arithmetic behind it is real, but it was read off
 * a precomputed sweep rather than solved at the requested point — which is why
 * `clamped` exists and why a caller is entitled to know which of the two it
 * got.
 */
const INTERPOLATED =
  'Interpolated from the precomputed sweep, not solved at this point. A request outside the ' +
  'modelled envelope is pulled to its edge and comes back with clamped = true. Use solvePlant ' +
  'for a solve at the point itself.';

const GRIDS = new Map<string, ResultGrid>();

function gridFor(modelId: string): ResultGrid | null {
  const hit = GRIDS.get(modelId);
  if (hit) return hit;
  const model = COST_MODELS.find((m) => m.modelId === modelId);
  if (!model) return null;
  const grid = buildGrid(model);
  GRIDS.set(modelId, grid);
  return grid;
}

/** `CostModel` without the member that cannot be serialised. */
function summarise(model: (typeof COST_MODELS)[number]): CostModelSummary {
  const { modelId, dims, referencePoint } = model;
  return { modelId, dims, referencePoint };
}

export const fixtureEconomicsAdapter: EconomicsAdapter = {
  async listCostModels(): Promise<AdapterResponse<CostModelSummary[]>> {
    return respond(COST_MODELS.map(summarise));
  },

  async getCostModel(modelId: string): Promise<AdapterResponse<CostModelSummary | null>> {
    const model = COST_MODELS.find((m) => m.modelId === modelId);
    return respond(model ? summarise(model) : null);
  },

  async evaluatePoint(request: PointRequest): Promise<AdapterResponse<EvaluatedPoint | null>> {
    const grid = gridFor(request.modelId);
    if (!grid) return respond(null);
    return respond(evaluateGrid(grid, request.point), {
      modelVersion: plantModelVersion(),
      notice: INTERPOLATED,
    });
  },

  async solvePlant(request: PointRequest): Promise<AdapterResponse<PlantResult | null>> {
    // `null` for a model with no flowsheet, which is what `evaluatePlantCached`
    // already answers rather than throwing. A failed SOLVE is a different
    // thing and stays visible: it throws, and the plant screen renders the
    // failure instead of a price.
    return respond(evaluatePlantCached(request.modelId, request.point), {
      modelVersion: plantModelVersion(),
    });
  },

  async getSensitivity(request: PointRequest): Promise<AdapterResponse<SensitivityBar[]>> {
    const spec = FLOWSHEET_BY_MODEL[request.modelId];
    if (!spec) return respond([]);
    return respond(deriveSensitivity(spec, request.point), {
      modelVersion: plantModelVersion(),
    });
  },
};
