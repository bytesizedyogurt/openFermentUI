// Design records from grid points (OF-FE-004 §2).
//
// A DesignRecord is a point in a CostModel's sweep grid, re-presented as a
// design rather than as a slider position. That is re-presentation, not
// fabrication: the MSP and the cost lines were computed together by the
// authored engine, and the design inherits their `demo` provenance and the
// permanent "illustrative economics, not validated" subtitle.
//
// §0 of OF-FE-004 generalises the contradictions rule — anything the engine can
// compute is computed, not seeded — so these are derived at load like everything
// else, and cannot drift from the models they came from.
//
// Tier discipline is the load-bearing part:
//
//   T0 balance   computed here, over the config and the ontology's own bounds
//   T1 flux      ABSENT — no genome-scale model in this build
//   T2 reactor   ABSENT — no reactor model in this build
//   T3 cost      the authored CostModel, interpolated from its grid
//
// A design that reached T0 and T3 but not T1 or T2 is an honest and interesting
// object: it says the economics were modelled without the biology being checked,
// which is exactly the state of the field. Rendering an absent tier as passed
// would be a lie about which half of the work was done.
import type {
  DesignRecord,
  ResultGrid,
  Scenario,
  TierResult,
} from '@/data/types';
import { evaluateGrid } from '@/engine/grids';
import { ONTOLOGY_BY_ID } from '@/data/ontology';

export const DESIGN_ENGINE_VERSION = 'grid-interp-v1';

/**
 * T0 — does the configuration sit inside the bounds the ontology declares
 * physically meaningful? Real arithmetic over real declarations, and the only
 * tier in this build that checks anything about the biology at all.
 */
function tierZero(config: Record<string, number>, dimField: Record<string, string>): TierResult {
  const values: TierResult['values'] = {};
  const violations: string[] = [];

  for (const [key, v] of Object.entries(config)) {
    const fieldId = dimField[key];
    const def = fieldId ? ONTOLOGY_BY_ID[fieldId as keyof typeof ONTOLOGY_BY_ID] : undefined;
    values[key] = { value: v, unit: def?.canonicalUnit ?? '' };
    if (!def) continue;
    const [lo, hi] = def.range;
    if (v < lo || v > hi) {
      violations.push(`${def.name} ${v} outside ${lo}–${hi}`);
    }
  }

  return {
    tier: 'T0',
    state: violations.length ? 'failed' : 'passed',
    bindingConstraint: violations.length
      ? violations[0]
      : 'every configured parameter sits inside its declared ontology range',
    values,
    engineVersion: DESIGN_ENGINE_VERSION,
  };
}

function absentTier(tier: 'T1' | 'T2', reason: string): TierResult {
  return {
    tier,
    state: 'absent',
    absentReason: reason,
    bindingConstraint: 'not evaluated — no engine',
    values: {},
    engineVersion: '—',
  };
}

/**
 * T3 — the authored cost model at this grid point.
 *
 * `msp` stays undefined. The grid holds one number per point, not a
 * distribution, and setting p05 = p95 = median would put a point estimate in the
 * field reserved for an interval — the most flattering lie available on this
 * screen, because a reader would see error bars of zero width and read certainty
 * rather than absence. The point value goes in `values` and the design detail
 * says which it is.
 */
function tierThree(grid: ResultGrid, config: Record<string, number>): TierResult {
  const at = evaluateGrid(grid, config);
  return {
    tier: 'T3',
    state: 'passed',
    bindingConstraint: grid.sensitivity[0]
      ? `most influential: ${grid.sensitivity[0].assumption}`
      : 'no sensitivity recorded',
    values: {
      msp: { value: at.msp, unit: 'USD kg⁻¹' },
      ...Object.fromEntries(
        Object.entries(at.costLines).map(([k, v]) => [k, { value: v, unit: 'USD kg⁻¹' }]),
      ),
    },
    sensitivity: grid.sensitivity.map((s) => ({
      field: s.field,
      label: s.assumption,
      rho: Math.max(Math.abs(s.lowPct), Math.abs(s.hiPct)) / 100,
    })),
    engineVersion: DESIGN_ENGINE_VERSION,
  };
}

/** Which ontology field each sweep axis is keyed to. */
function dimFieldMap(scenario: Scenario): Record<string, string> {
  const dimField: Record<string, string> = {};
  for (const d of scenario.dims) {
    if (d.field) dimField[d.key] = d.field;
  }
  return dimField;
}

/** The records a scenario's assumptions rest on — the basis for staleness. */
function consumedRecordIds(scenario: Scenario): string[] {
  return scenario.assumptions
    .filter((a) => a.basis.kind === 'record')
    .map((a) => (a.basis as { recordId: string }).recordId);
}

/**
 * One configuration, run through the cascade.
 *
 * Split out of `designsFor` so that evaluating an ARBITRARY point — which is
 * what `ProcessAdapter.submitEvaluation` does at the adapter seam — goes
 * through the same code as evaluating a sweep corner, rather than through a
 * second assembly that would have to keep agreeing with this one. In
 * particular the two absent-tier reasons below are rendered verbatim on the
 * design detail screen, and there is exactly one copy of each.
 */
export function evaluateDesign(
  scenario: Scenario,
  grid: ResultGrid,
  config: Record<string, number>,
  identity: { id: string; label: string },
): DesignRecord {
  return {
    id: identity.id,
    label: identity.label,
    scenarioId: scenario.id,
    config,
    tiers: [
      tierZero(config, dimFieldMap(scenario)),
      absentTier('T1', 'No genome-scale metabolic model in this build. Flux balance is server-side work outside this repo.'),
      absentTier('T2', 'No reactor model in this build. Mass transfer and mixing are unmodelled.'),
      tierThree(grid, config),
    ],
    consumedRecordIds: consumedRecordIds(scenario),
    // Parchment holds no parsed claim bounds, so nothing has evaluated scope.
    scope: 'clear',
    scopeEvaluated: false,
    scopeHits: [],
    publication: 'draft',
  };
}

/**
 * Designs for a scenario: the reference point plus the corners of its sweep, so
 * the set spans the space the model was authored over rather than sampling it
 * arbitrarily.
 */
export function designsFor(scenario: Scenario, grid: ResultGrid): DesignRecord[] {
  const points: { label: string; config: Record<string, number> }[] = [];
  const ref = Object.fromEntries(grid.dims.map((d) => [d.key, d.values[Math.floor(d.values.length / 2)]]));
  points.push({ label: 'reference', config: ref });

  for (const d of grid.dims) {
    for (const [name, v] of [
      ['low', d.values[0]],
      ['high', d.values[d.values.length - 1]],
    ] as const) {
      points.push({ label: `${d.key} ${name}`, config: { ...ref, [d.key]: v } });
    }
  }

  return points.map((p, i) =>
    evaluateDesign(scenario, grid, p.config, {
      id: `${scenario.id}-d${String(i + 1).padStart(2, '0')}`,
      label: `${scenario.name} — ${p.label}`,
    }),
  );
}

/** The four-segment cascade badge, in tier order. */
export function cascade(d: DesignRecord): TierResult[] {
  const order: DesignRecord['tiers'][number]['tier'][] = ['T0', 'T1', 'T2', 'T3'];
  return order
    .map((t) => d.tiers.find((x) => x.tier === t))
    .filter((x): x is TierResult => Boolean(x));
}
