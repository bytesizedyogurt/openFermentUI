// The contract every ported bioSTEAM module binds to.
//
// Ported from BioSTEAM v2.53.11 (UIUC/NCSA licence) — see NOTICE.md in this
// directory for the full attribution and, more importantly, for the list of
// what is deliberately *not* ported.
//
// Naming follows upstream: a reader who knows `Unit.design_results`,
// `baseline_purchase_costs`, `F_BM` and `installed_cost` should recognise every
// field here, and can check this code against the Python line by line.

/** One entry in a unit's design results table, with its unit of measure. */
export interface DesignEntry {
  value: number;
  units: string;
}

export type DesignResults = Record<string, DesignEntry>;

/**
 * A process stream.
 *
 * Lumped component mass flows, not a thermosteam Stream. There is no property
 * package behind this: no VLE, no enthalpy departure, no phase inference. `T`
 * and `P` are carried because equipment sizing needs them (vessel wall
 * thickness is a function of pressure), not because anything here solves an
 * equilibrium at that state.
 */
export interface Stream {
  ID: string;
  /** Component mass flow, kg/hr. */
  flow: Record<string, number>;
  /** K. */
  T: number;
  /** Pa. */
  P: number;
  /** USD/kg. Zero for internal streams; non-zero on feeds and products. */
  price: number;
  /** Bulk density, kg/m³, for volumetric sizing. Water-like unless set. */
  rho?: number;
  phase?: 'l' | 'g' | 's';
}

/** Total mass flow of a stream, kg/hr. */
export function massFlow(s: Stream): number {
  let t = 0;
  for (const k in s.flow) t += s.flow[k];
  return t;
}

/** Volumetric flow, m³/hr. */
export function volFlow(s: Stream): number {
  return massFlow(s) / (s.rho ?? 1000);
}

/**
 * A heating or cooling demand placed on a utility agent.
 *
 * `duty` is signed the way bioSTEAM signs it: positive is heat into the
 * process (a heating agent), negative is heat out (a cooling agent). Getting
 * this backwards silently turns a chiller into a boiler, so the sign is part
 * of the contract rather than a convention to remember.
 */
export interface HeatUtilityDemand {
  agent: string;
  /** kJ/hr. */
  duty: number;
  /** USD/hr. */
  cost: number;
}

/**
 * Where a purchase-cost correlation came from.
 *
 * bioSTEAM has no photobioreactor, no pulsed-electric-field cell disruptor and
 * no membrane skid, because nobody has published a costing correlation for them
 * into it. Those units are costed by correlations written here, and the
 * difference between a number carrying Seider's authority and a number carrying
 * ours is exactly the kind of thing this app refuses to blur. The capital
 * breakdown reports the split.
 */
export type CostSource = 'biosteam' | 'authored';

/** One row of the unit results table — bioSTEAM's `system.results()`. */
export interface UnitResult {
  ID: string;
  /** Upstream calls this `line`: the class of equipment, e.g. 'Bioreactor'. */
  line: string;
  costSource: CostSource;
  /** For an authored correlation, what it is anchored on. */
  costBasis: string;
  /** Area number for grouping, NREL style: 100 feed, 300 fermentation, … */
  area: number;
  areaName: string;
  design: DesignResults;
  /** Baseline purchase cost per cost item, USD, at the current CE index. */
  purchaseCosts: Record<string, number>;
  /** Bare-module factor per cost item. */
  F_BM: Record<string, number>;
  /** Number of parallel units per cost item. */
  parallel: Record<string, number>;
  /** Σ baseline × N, USD. */
  purchaseCost: number;
  /** Σ baseline × N × F_BM, USD. */
  installedCost: number;
  /** kW. Positive consumes, negative produces. */
  powerKW: number;
  heatUtilities: HeatUtilityDemand[];
  /** USD/hr, power plus heat. */
  utilityCostPerHr: number;
  /**
   * Where the size or the cost correlation is being pushed past the range its
   * authors validated. bioSTEAM raises a warning; refusing to show it would be
   * worse than the extrapolation itself.
   */
  warnings: string[];
}

/** NREL-style process areas, used for the capital breakdown. */
export const AREA_NAMES: Record<number, string> = {
  100: 'Feed handling',
  200: 'Seed train',
  300: 'Fermentation',
  400: 'Recovery',
  500: 'Purification',
  600: 'Drying & packaging',
  700: 'Utilities',
  800: 'Storage',
};
