/**
 * The canonical entity types.
 *
 * Everything below the re-export is GENERATED from the Pydantic models in
 * `packages/core/openferment_core/schema`, via `pnpm gen:types`. This file is
 * the seam, and it exists only because two of the types in it are not data.
 *
 * `CostModel` carries a function and `ResultGrid` carries `Float64Array`.
 * Neither survives a round trip through JSON Schema, and a model that dropped
 * those members would generate a `CostModel` missing the only member anything
 * calls. They are runtime shapes rather than corpus shapes, so they are written
 * here by hand and everything else comes from Python.
 *
 * If you are about to add a type to this file, ask first whether it is data. If
 * it is, it belongs in the Pydantic models — a schema kept in two languages is
 * two schemas, and they diverge on the day nobody is looking.
 */
export * from './types.generated';

import type { CostLine, ScenarioDim, SensitivityRow } from './types.generated';

/**
 * A cost model is a set of sweep axes over a plant. Every evaluation goes
 * through a flowsheet: equipment sized, costed against bioSTEAM's correlations,
 * and priced by a discounted cash flow solved at NPV = 0. Cost lines are
 * USD/kg product and sum to MSP by construction, so the waterfall always agrees
 * with the headline.
 *
 * There is no `sensitivity` field any more. It used to hold authored
 * percentages that nothing could contradict; a tornado is now derived by
 * re-solving the plant at each parameter's bounds, which means it changes when
 * the model changes and can be checked by dragging a slider.
 *
 * NOT GENERATED: `evaluate` is a function, and JSON Schema has no way to say so.
 */
export interface CostModel {
  modelId: 'S1' | 'S2' | 'S3';
  dims: ScenarioDim[];
  referencePoint: Record<string, number>;
  evaluate: (point: Record<string, number>) => Record<CostLine, number>;
}

/**
 * Precomputed sweep of a CostModel (§15 ResultGrid).
 *
 * NOT GENERATED: `Float64Array` is a JavaScript typed array. It is here because
 * a grid of a few hundred points is read on every slider frame and a plain
 * array of boxed numbers is the wrong shape for that.
 */
export interface ResultGrid {
  modelId: string;
  dims: { key: string; values: number[] }[];
  msp: Float64Array;
  costLines: Record<CostLine, Float64Array>;
  sensitivity: SensitivityRow[];
}
