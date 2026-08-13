// NOT SIMULATION — NOT DELETED WITH THE REST OF `sim/`.
//
// Every other file in `src/sim/` is a rehearsal with a removal date: the
// scripted agent, its intent matcher, its latency model and its job pacing all
// go in the phase that lands the real agent. `sim/flowsheets/` does not. It is
// the bioSTEAM plant definition — a real mass balance over real, cited
// equipment correlations, attributed in `src/engine/biosteam/NOTICE.md` and
// asserted against upstream doctests on every `pnpm verify`. No phase of this
// migration deletes it.
//
// It sits under `sim/` because a plant simulation is a simulation in the
// engineering sense, not in the "stands in until the backend exists" sense the
// rest of this directory means. Where the cost model is ultimately AUTHORED is
// the BioSTEAM question in CLAUDE.md — a question about which language owns
// the model, not a removal date.
//
// What a flowsheet is, as far as the rest of the app is concerned.
//
// A scenario used to be a closure that returned six cost lines. It is now a
// plant: a set of parameters, a function that turns those parameters into
// sized and costed equipment, and a TEA that solves the price at which the
// plant breaks even. The important part of this file is not the shape of the
// data — it is that every parameter carries an `AssumptionBasis`, so a number
// in the cash-flow table can be walked back to the record it came from, or
// convicted of having no record at all.
import type { AssumptionBasis, FieldId } from '@/data/types';
import type { BioSystem } from '@/engine/biosteam/system';
import type { TEAOptions } from '@/engine/biosteam/tea';

/**
 * One input to a plant.
 *
 * `bounds` are the range the parameter is swept and sampled over. They are not
 * decoration: the Monte Carlo draws from them and the tornado ranks on them, so
 * a bound invented for convenience becomes a claim about uncertainty.
 */
export interface FlowsheetParam {
  key: string;
  label: string;
  unit: string;
  baseline: number;
  bounds: [low: number, high: number];
  /**
   * Sampling shape. 'triangular' peaks at the baseline — the right default when
   * the baseline is a measurement and the bounds are judgement.
   */
  distribution: 'triangular' | 'uniform';
  basis: AssumptionBasis;
  /** The ontology parameter this varies, where it is one. */
  field?: FieldId;
  /** Cite the paper when the parameter rests on a source but no single record. */
  paperId?: string;
  /** Why this parameter matters to the plant, in one sentence. */
  note: string;
}

export interface FlowsheetSpec {
  modelId: 'S1' | 'S2' | 'S3';
  /** Plant name as it appears above the flowsheet. */
  name: string;
  /** The stream the TEA solves a price for. */
  productStreamID: string;
  productLabel: string;
  parameters: FlowsheetParam[];
  /** Build and simulate the plant at a parameter point. */
  build: (point: Record<string, number>) => BioSystem;
  tea: TEAOptions;
  /**
   * What this flowsheet does not model, stated in the plant view rather than
   * buried. Every entry here is a place a reviewer is entitled to push back.
   */
  limitations: string[];
}

/** 330 operating days, the availability the whole app assumes. */
export const OPERATING_DAYS = 330;
export const OPERATING_HOURS = OPERATING_DAYS * 24;

/**
 * The financial basis shared by all three plants.
 *
 * Shared deliberately: three plants compared on three discount rates is not a
 * comparison. The numbers follow the bioSTEAM tutorial's SugarcaneTEA, which in
 * turn follows Huang et al., except for the tax rate, which is current US
 * federal, and the DPI→FCI factors, which are the NREL indirect-cost structure
 * every published fermentation TEA uses.
 */
export function baseTEA(overrides: Partial<TEAOptions> = {}): TEAOptions {
  return {
    IRR: 0.1,
    duration: [2026, 2046],
    depreciation: 'MACRS7',
    incomeTax: 0.21,
    operatingDays: OPERATING_DAYS,
    langFactor: null,
    constructionSchedule: [0.08, 0.6, 0.32],
    startupMonths: 3,
    startupFOCfrac: 1,
    startupVOCfrac: 0.75,
    startupSalesfrac: 0.5,
    WC_over_FCI: 0.05,
    financeInterest: 0.08,
    financeYears: 10,
    financeFraction: 0.4,
    laborCost: 2.1e6,
    fringeBenefits: 0.4,
    propertyTax: 0.001,
    propertyInsurance: 0.005,
    supplies: 0.2,
    maintenance: 0.03,
    administration: 0.005,
    warehouse: 0.04,
    siteDevelopment: 0.09,
    additionalPiping: 0.045,
    proratableCosts: 0.1,
    fieldExpenses: 0.1,
    construction: 0.2,
    contingency: 0.1,
    otherIndirect: 0.1,
    ...overrides,
  };
}
