// Techno-economic scenarios (OF-COR-001 §20). The algal route, the incumbent
// yeast route, and the cow.
//
// These were three authored cost engines. They are now three plants. Each model
// below keeps its sweep dimensions and its reference point — the axes a reader
// already knows how to read — and delegates every evaluation to a flowsheet in
// `src/sim/flowsheets`, where the equipment is sized, costed against bioSTEAM's
// correlations, and priced by a discounted cash flow solved at NPV = 0.
//
// What that buys, concretely: the old S1 charged a fixed 18 USD/kg of
// "downstream" plus a penalty for imperfect recovery, so improving disruption
// yield moved a coefficient. Now it changes how much paste the centrifuge
// handles, which changes the centrifuge, the membrane area, the pumping load
// and the electricity bill, and the price falls out of the cash flow. Nothing
// on the way is authored.
//
// HONESTY, unchanged and still load-bearing: a correct arithmetic chain over
// uncertain inputs is still uncertain. The photobioreactor and the PEF skid
// have no published cost correlation and are marked `authored` wherever they
// appear; the whole surface remains provenance 'demo'; and the plant view
// states what each flowsheet does not model before it shows the number.
// The collection itself now comes from the adapter; this module keeps only
// the derived views built on top of it.
import { SCENARIOS } from '@/data/source';

export { SCENARIOS };

import type { CostLine, CostModel, Scenario } from './types';
import { evaluatePlantCached } from '@/engine/plant';

/**
 * Evaluate a point through its plant.
 *
 * A failed build returns zeros rather than throwing: the grid sweep visits
 * corners the sizing routines cannot resolve, and a zero cell is caught by the
 * non-convergence machinery the workspace already has. The plant screen, which
 * a reader arrives at deliberately, fails visibly instead.
 */
function viaPlant(modelId: 'S1' | 'S2' | 'S3') {
  return (point: Record<string, number>): Record<CostLine, number> => {
    try {
      const r = evaluatePlantCached(modelId, point);
      if (!r || !Number.isFinite(r.msp)) return ZERO_LINES();
      return r.costLines;
    } catch {
      return ZERO_LINES();
    }
  };
}

const ZERO_LINES = (): Record<CostLine, number> => ({
  capex: 0,
  media: 0,
  utilities: 0,
  labor: 0,
  downstream: 0,
  other: 0,
});

// ══ S1 — cw15 intracellular β-casein ═══════════════════════════════════
// Sweep chosen per OF-COR-001 §20 and parameterised on exactly the two
// variables O3 identifies as dominant: biomass density and target protein as a
// share of cell mass. Both axes are marked with where the literature actually
// sits today, which is at the very bottom of each.
const S1: CostModel = {
  modelId: 'S1',
  dims: [
    { key: 'density', field: 'final_biomass_density' as const, label: 'Biomass density', unit: 'g L⁻¹', values: [0.5, 1.25, 2, 3, 4, 5] },
    { key: 'pctTsp', field: 'expression_pct_tsp' as const, label: 'β-casein as % of cell mass', unit: '% TSP', values: [0.1, 1, 3, 6, 12, 20] },
    { key: 'dispYield', field: 'disruption_protein_yield' as const, label: 'Disruption + recovery yield', unit: '%', values: [10, 20, 30, 40, 50] },
  ],
  referencePoint: { density: 2, pctTsp: 3, dispYield: 31 },
  evaluate: viaPlant('S1'),
};

// ══ S2 — K. phaffii secreted comparator ════════════════════════════════
// Anchored on the two real eukaryotic data points: Choi & Jiménez-Flores
// (0.7–1.0 g/L bovine β-casein, intracellular) and Aro et al. (1 g/L secreted
// β-lactoglobulin from T. reesei) as the upper end of what secretion achieves.
const S2: CostModel = {
  modelId: 'S2',
  dims: [
    { key: 'titer', field: 'titer_secreted' as const, label: 'Secreted titer', unit: 'g L⁻¹', values: [0.05, 0.25, 0.5, 1, 2, 3, 5] },
    { key: 'scale', label: 'Fermenter scale', unit: 'm³', values: [20, 65, 110, 155, 200] },
    { key: 'dspYield', label: 'Downstream yield', unit: 'fraction', values: [0.55, 0.65, 0.75, 0.85] },
  ],
  referencePoint: { titer: 1, scale: 110, dspYield: 0.75 },
  evaluate: viaPlant('S2'),
};

// ══ S3 — conventional β-casein isolation from milk ═════════════════════
// The incumbent baseline, and the comparison a faculty reviewer asks about
// first. Grounded in Atamer's review: β-casein is present in milk at ~2.6 g/L,
// and cold microfiltration recovers a fraction of it.
const S3: CostModel = {
  modelId: 'S3',
  dims: [
    { key: 'milkPrice', label: 'Raw milk price', unit: 'USD L⁻¹', values: [0.3, 0.4, 0.5, 0.6, 0.75] },
    { key: 'recovery', label: 'β-casein recovery', unit: 'fraction', values: [0.3, 0.45, 0.6, 0.75, 0.9] },
  ],
  referencePoint: { milkPrice: 0.45, recovery: 0.6 },
  evaluate: viaPlant('S3'),
};

export const COST_MODELS: CostModel[] = [S1, S2, S3];

// ── Scenarios ─────────────────────────────────────────────────────────

