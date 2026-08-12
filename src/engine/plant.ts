// Where a plant becomes a price.
//
// This module replaces the six authored cost curves fermOS used to ship. The
// contract to the rest of the app is deliberately unchanged — give it a point,
// get back an MSP and six cost lines that sum to it — but what happens in
// between is now a sized flowsheet and a discounted cash flow rather than a
// closure with coefficients typed into it.
//
// The one thing worth reading closely is `decompose`. A DCF does not hand you a
// cost breakdown; it hands you the price at which net present value reaches
// zero. Turning that back into lines a reader can argue with has to be done
// without inventing anything, and the way to do that is to take the operating
// lines as they are and let capital be the residual, because the residual *is*
// what the plant has to charge above its operating cost to service its capital
// and its tax. That number is not an allocation. It is the answer.
import type { CostLine } from '@/data/types';
import type { AreaSummary, BioSystem } from '@/engine/biosteam/system';
import type { UnitResult } from '@/engine/biosteam/types';
import { TEA, type CashflowRow } from '@/engine/biosteam/tea';
import { FLOWSHEET_BY_MODEL } from '@/sim/flowsheets/plants';
import type { FlowsheetSpec } from '@/sim/flowsheets/spec';

export interface PlantResult {
  modelId: string;
  point: Record<string, number>;
  /** USD per kg of product. */
  msp: number;
  /** kg/yr. */
  annualProduction: number;
  costLines: Record<CostLine, number>;
  units: UnitResult[];
  areas: AreaSummary[];
  cashflow: CashflowRow[];
  capital: {
    purchaseCost: number;
    installedEquipmentCost: number;
    DPI: number;
    TDC: number;
    FCI: number;
    workingCapital: number;
    TCI: number;
  };
  operating: {
    materialCost: number;
    utilityCost: number;
    powerCost: number;
    VOC: number;
    FOC: number;
    AOC: number;
  };
  process: {
    heatingDuty: number;
    coolingDuty: number;
    powerConsumption: number;
  };
  costSourceSplit: { biosteam: number; authored: number };
  warnings: { ID: string; message: string }[];
  /** Solver residual on NPV at the solved price, USD. Near zero or it is wrong. */
  npvResidual: number;
}

/**
 * Split the price into lines that sum to it exactly.
 *
 * Operating lines are read straight off the TEA. The capital residual is then
 * apportioned between the fermentation island and the recovery train by their
 * share of installed cost — the only split that does not require choosing a
 * capital charge factor, which is the assumption the old model had to make and
 * could never defend.
 */
function decompose(
  sys: BioSystem,
  tea: TEA,
  msp: number,
  annualProduction: number,
): Record<CostLine, number> {
  const perKg = (annual: number): number => (annualProduction > 0 ? annual / annualProduction : 0);

  const media = perKg(sys.materialCost);
  const utilities = perKg(sys.utilityCost);
  // The same split the TEA's own `_FOC` makes: what the payroll costs, and what
  // the plant costs to keep standing.
  const payroll = tea.laborCost * (1 + tea.fringeBenefits + tea.supplies);
  const labour = perKg(payroll);
  const other = perKg(tea.FOC - payroll);

  const residual = msp - media - utilities - labour - other;
  const upstream = sys
    .byArea()
    .filter((a) => a.area < 400)
    .reduce((t, a) => t + a.installedCost, 0);
  const total = sys.installedEquipmentCost;
  const upstreamShare = total > 0 ? upstream / total : 1;

  return {
    capex: residual * upstreamShare,
    downstream: residual * (1 - upstreamShare),
    media,
    utilities,
    labor: labour,
    other,
  };
}

/** Build, size, cost and price a plant at one parameter point. */
export function evaluatePlant(spec: FlowsheetSpec, point: Record<string, number>): PlantResult {
  const sys = spec.build(point);
  const tea = new TEA(sys, spec.tea);
  const annualProduction = sys.annualProduction(spec.productStreamID);
  const msp = tea.solvePrice(spec.productStreamID);

  // Confirm the solve actually landed. A price that does not zero the NPV is a
  // solver failure wearing a plausible number, which is worse than an error, so
  // the residual is carried all the way to the screen rather than trusted here.
  // `solvePrice` restores the stream price when it returns, so the product is
  // repriced deliberately and left that way: the cash-flow table below is the
  // one the plant would actually run, with sales at the solved price.
  const product = sys.products.find((p) => p.ID === spec.productStreamID);
  if (product) product.price = msp;
  const npvResidual = tea.NPV;

  return {
    modelId: spec.modelId,
    point: { ...point },
    msp,
    annualProduction,
    costLines: decompose(sys, tea, msp, annualProduction),
    units: sys.results(),
    areas: sys.byArea(),
    cashflow: tea.getCashflowTable(),
    capital: {
      purchaseCost: sys.purchaseCost,
      installedEquipmentCost: sys.installedEquipmentCost,
      DPI: tea.DPI,
      TDC: tea.TDC,
      FCI: tea.FCI,
      workingCapital: tea.workingCapital,
      TCI: tea.TCI,
    },
    operating: {
      materialCost: sys.materialCost,
      utilityCost: sys.utilityCost,
      powerCost: sys.powerCost,
      VOC: tea.VOC,
      FOC: tea.FOC,
      AOC: tea.AOC,
    },
    process: {
      heatingDuty: sys.heatingDuty,
      coolingDuty: sys.coolingDuty,
      powerConsumption: sys.powerConsumption,
    },
    costSourceSplit: sys.costSourceSplit(),
    warnings: sys.warnings,
    npvResidual,
  };
}

/**
 * Memoised evaluation.
 *
 * A plant solve is a flowsheet build plus a bracketing DCF solve — cheap enough
 * to run on a slider drag, but not cheap enough to run three times per render.
 * The cache is per-session and unbounded, which is fine for a grid whose
 * cardinality is fixed by the scenario's own dimensions.
 */
const CACHE = new Map<string, PlantResult>();

function cacheKey(modelId: string, point: Record<string, number>): string {
  const keys = Object.keys(point).sort();
  return `${modelId}|${keys.map((k) => `${k}=${point[k]}`).join(',')}`;
}

export function evaluatePlantCached(
  modelId: string,
  point: Record<string, number>,
): PlantResult | null {
  const spec = FLOWSHEET_BY_MODEL[modelId];
  if (!spec) return null;
  const key = cacheKey(modelId, point);
  const hit = CACHE.get(key);
  if (hit) return hit;
  const result = evaluatePlant(spec, point);
  CACHE.set(key, result);
  return result;
}

export function clearPlantCache(): void {
  CACHE.clear();
}

/**
 * Did the plant fail to size at this point?
 *
 * The S2 model used to carry a `nonConvergent` predicate naming one corner of
 * its grid as unsolvable. That corner is not unsolvable — the flowsheet builds
 * there and the cash flow solves; it simply returns a very large number,
 * because a plant making almost nothing has to charge almost anything. An
 * authored failure that does not fail when computed is the same defect class as
 * an authored contradiction that passes its own tolerance, and the app already
 * refuses the second one.
 *
 * So failure is asked of the plant instead. Today no grid point in any of the
 * three models fails, and the workspace's failure state is therefore unreachable
 * from the seeded scenarios — which is the correct outcome. It is kept because
 * it becomes reachable the moment somebody widens a bound past what the sizing
 * routines can resolve, and finding out then is better than finding out never.
 */
export function plantFails(modelId: string, point: Record<string, number>): boolean {
  try {
    const r = evaluatePlantCached(modelId, point);
    return !r || !Number.isFinite(r.msp) || r.msp <= 0;
  } catch {
    return true;
  }
}

/**
 * One-at-a-time sensitivity: re-solve the whole plant at each parameter's
 * bounds, holding the rest at the point.
 *
 * This replaces a table of authored percentages. Those percentages said the
 * titer moved the answer 118% down and 41% up because somebody typed 118 and
 * 41; nothing recomputed them when the model changed, and nothing could have
 * contradicted them. These are two plant solves per parameter, so a bar that
 * looks wrong can be checked by dragging the slider to the bound and reading
 * the headline.
 *
 * Local, not global: it holds everything else fixed, so it cannot see
 * interactions. The Spearman ranking on the plant screen can, and the two are
 * kept separate rather than blended into one chart that is neither.
 */
export function deriveSensitivity(
  spec: FlowsheetSpec,
  point: Record<string, number>,
): { assumption: string; key: string; lowPct: number; hiPct: number; field?: string }[] {
  const base = evaluatePlantCached(spec.modelId, point);
  if (!base || !Number.isFinite(base.msp) || base.msp <= 0) return [];
  const out: { assumption: string; key: string; lowPct: number; hiPct: number; field?: string }[] =
    [];
  for (const p of spec.parameters) {
    const at = (v: number): number | null => {
      try {
        const r = evaluatePlantCached(spec.modelId, { ...point, [p.key]: v });
        return r && Number.isFinite(r.msp) ? r.msp : null;
      } catch {
        return null;
      }
    };
    const lo = at(p.bounds[0]);
    const hi = at(p.bounds[1]);
    if (lo === null || hi === null) continue;
    out.push({
      assumption: p.label,
      key: p.key,
      lowPct: ((lo - base.msp) / base.msp) * 100,
      hiPct: ((hi - base.msp) / base.msp) * 100,
      field: p.field,
    });
  }
  return out.sort(
    (a, b) =>
      Math.max(Math.abs(b.lowPct), Math.abs(b.hiPct)) -
      Math.max(Math.abs(a.lowPct), Math.abs(a.hiPct)),
  );
}
