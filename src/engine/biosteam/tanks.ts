// Tank purchase-cost algorithms, and how many tanks a duty needs.
//
// Ported from BioSTEAM v2.53.11 `units/design_tools/tank_design.py`, with
// `ExponentialFunctor` brought across from `utils/functors.py` because five of
// the six storage algorithms and the only mix-tank algorithm are built from it
// (UIUC/NCSA licence; see NOTICE.md). The correlations are Apostolakou et al.,
// *Fuel Processing Technology* 90 (2009) 1023–1031, for the field-erected and
// conventional-mix tanks, and Seider, Lewin, Seader, Widagdo, Gani & Ng,
// *Product and Process Design Principles* (Wiley, 2017), pp 426–485, for the
// rest.
//
// Left behind: `TankPurchaseCostAlgorithm.__repr__`, which exists to make the
// upstream doctest printable and has no reader here; and thermosteam's
// `UnitsOfMeasure`, which upstream stores in `V_units` and asks for a
// conversion factor at call time. Only three units appear across all six
// algorithms, so they are a string union against a fixed table below — that is
// the entire part of the units machinery this port exercises, and a general
// unit registry would be a much larger thing to have to trust.

import { CE } from './cepci';

/**
 * A purchase-cost correlation for one vessel type, upstream's
 * `TankPurchaseCostAlgorithm`.
 *
 * `CE` is the cost index the correlation was published at and is not optional:
 * these curves span 2007 to 2017 dollars, and mixing a 525.4-basis tank with a
 * 567-basis one without indexing each to today would quietly understate the
 * older by about eight per cent.
 */
export interface TankPurchaseCostAlgorithm {
  /** Purchase cost [USD at index `CE`] given one vessel's volume in `V_units`. */
  f_Cp: (V: number) => number;
  /** Smallest volume the correlation was fitted over, in `V_units`. */
  V_min: number;
  /** Largest volume a single vessel of this type is built at, in `V_units`. */
  V_max: number;
  V_units: 'm^3' | 'gal' | 'ft^3';
  /** Chemical Engineering Plant Cost Index the correlation is quoted at. */
  CE: number;
  /** Construction material the correlation assumes. */
  material: string;
}

/**
 * Build `f(S) = A · S^n`, upstream's `ExponentialFunctor`.
 *
 * Upstream makes this an object with `A` and `n` on it so a correlation can be
 * inspected and printed; nothing in this port reads those back, so a closure
 * carries the same arithmetic with less to keep in sync.
 */
export function exponentialFunctor(A: number, n: number): (S: number) => number {
  return (S: number) => A * S ** n;
}

/**
 * Cubic metres in one unit of each algorithm's own volume measure — upstream's
 * `V_units.conversion_factor('m^3')`, which is what a total volume in m³ is
 * *divided* by to reach the correlation's units.
 *
 * Both figures are exact: the US liquid gallon is defined as 231 in³ and the
 * inch as 25.4 mm, giving 3.785411784 L exactly, and the foot is exactly
 * 0.3048 m, giving 0.028316846592 m³. Stated this way and divided by rather
 * than reciprocated into a rounded multiplier, the conversion tracks the Python
 * to the last bit or two of a double instead of to nine significant figures.
 */
const M3_PER_UNIT: Record<TankPurchaseCostAlgorithm['V_units'], number> = {
  'm^3': 1,
  gal: 0.003785411784,
  'ft^3': 0.028316846592,
};

/**
 * Return the purchase cost [USD, 2007 basis] of a single field-erected vessel
 * of volume `V_m3` [m³], assuming stainless steel construction.
 *
 * The upstream docstring and the upstream code disagree. The docstring gives
 * `32500 + 79.35 V` below 2000 m³ and `125000 + 47.1 V` above it; the code
 * computes `65000 + 158.7 V` and `250000 + 94.2 V`, which is exactly twice the
 * docstring in every coefficient. This port follows the **code**, because the
 * doctest in that same docstring — 300 m³ costing 112610 USD — is what the code
 * returns and what every published bioSTEAM biorefinery result was built from.
 * Following the prose instead would halve every storage tank in the estimate.
 * Which of the two Apostolakou et al. actually published is not something this
 * file can settle, and pretending the discrepancy is not there would be worse
 * than the discrepancy.
 */
export function fieldErectedTankPurchaseCost(V_m3: number): number {
  return V_m3 < 2e3 ? 65000.0 + 158.7 * V_m3 : 250000.0 + 94.2 * V_m3;
}

/** Cost algorithms for storage tank vessel types, upstream's `storage_tank_purchase_cost_algorithms`. */
export const STORAGE_TANK_ALGORITHMS: Record<string, TankPurchaseCostAlgorithm> = {
  'Field erected': {
    f_Cp: fieldErectedTankPurchaseCost,
    V_min: 0,
    V_max: 50e3,
    V_units: 'm^3',
    CE: 525.4,
    material: 'Stainless steel',
  },
  'Floating roof': {
    f_Cp: exponentialFunctor(475, 0.507),
    V_min: 3e4,
    V_max: 1e6,
    V_units: 'gal',
    CE: 567,
    material: 'Carbon steel',
  },
  'Cone roof': {
    f_Cp: exponentialFunctor(265, 0.513),
    V_min: 1e4,
    V_max: 1e6,
    V_units: 'gal',
    CE: 567,
    material: 'Carbon steel',
  },
  'Spherical; 0-30 psig': {
    f_Cp: exponentialFunctor(68, 0.72),
    V_min: 1e4,
    V_max: 1e6,
    V_units: 'gal',
    CE: 567,
    material: 'Carbon steel',
  },
  // The en dash in this key is upstream's, and a hyphen here would be a silent
  // lookup miss against any code or dataset that spells the key the same way
  // bioSTEAM does. Note the neighbouring 0-30 psig entry uses a plain hyphen.
  'Spherical; 30–200 psig': {
    f_Cp: exponentialFunctor(53, 0.78),
    V_min: 1e4,
    V_max: 7.5e5,
    V_units: 'gal',
    CE: 567,
    material: 'Carbon steel',
  },
  'Gas holder': {
    f_Cp: exponentialFunctor(3595, 0.43),
    V_min: 4e3,
    V_max: 4e5,
    V_units: 'ft^3',
    CE: 567,
    material: 'Carbon steel',
  },
};

/** Cost algorithms for mix tank vessel types, upstream's `mix_tank_purchase_cost_algorithms`. */
export const MIX_TANK_ALGORITHMS: Record<string, TankPurchaseCostAlgorithm> = {
  Conventional: {
    f_Cp: exponentialFunctor(12080, 0.525),
    V_min: 0.1,
    V_max: 30,
    V_units: 'm^3',
    CE: 525.4,
    material: 'Stainless steel',
  },
};

/** What `computeNumberOfTanksAndPurchaseCost` returns. */
export interface TankCountAndCost {
  /** Number of identical vessels in parallel. */
  N: number;
  /** Purchase cost of **one** vessel [USD at the current CE], not of all N. */
  Cp: number;
  /** Out-of-range text to show beside the number, or null when in range. */
  warning: string | null;
}

/**
 * Return how many tanks of this type a total volume needs, and what one of
 * them costs. Upstream's `compute_number_of_tanks_and_purchase_cost`.
 *
 * The split is deliberate and easy to misread: `Cp` is the cost of a single
 * vessel, and a caller that wants the capital for the whole duty must multiply
 * by `N` itself. That is upstream's contract because bioSTEAM's `Unit` carries
 * the parallel count separately from the baseline purchase cost, and changing
 * it here would put this port a factor of N away from every bioSTEAM result it
 * is supposed to be checkable against.
 *
 * The below-bound case is returned as text rather than logged. bioSTEAM raises
 * a `CostWarning` that a Python run prints to stderr; a browser would swallow
 * it, and a cost extrapolated below the smallest tank its authors priced is
 * precisely the number a reader deserves to see flagged.
 */
export function computeNumberOfTanksAndPurchaseCost(
  totalVolume_m3: number,
  algo: TankPurchaseCostAlgorithm,
): TankCountAndCost {
  const V_total = totalVolume_m3 / M3_PER_UNIT[algo.V_units];
  const warning =
    V_total < algo.V_min
      ? `volume (${formatG(V_total, 5)} ${algo.V_units}) is below the lower bound ` +
        `(${formatG(algo.V_min, 5)} ${algo.V_units}) for purchase cost estimation`
      : null;
  const N = Math.ceil(V_total / algo.V_max);
  // A zero or negative duty needs no tank at all, and asking the correlation
  // for the cost of one would return the intercept — 65000 USD of vessel that
  // does not exist. Upstream guards this the same way.
  if (N <= 0) return { N, Cp: 0, warning };
  const F_CE = CE.value / algo.CE;
  return { N, Cp: F_CE * algo.f_Cp(V_total / N), warning };
}

/**
 * Format a number the way Python's `:.{precision}g` does.
 *
 * The warning text above is meant to line up with a bioSTEAM run character for
 * character, and `toPrecision` will not do it: Python renders a million at five
 * significant figures as `1e+06`, JavaScript as `1.0000e+6`. `vessel.ts` keeps
 * its own copy of this for the same reason and neither module exports it,
 * because a shared formatting helper is a thing other code would start reaching
 * for, and this exists only to imitate one Python format specifier.
 */
function formatG(value: number, precision: number): string {
  if (value === 0) return '0';
  // Python spells these 'nan'/'inf'/'-inf'; `String(value)` would spell them
  // 'NaN'/'Infinity'. Only a non-finite input volume reaches here, which is a
  // caller bug either way, but a warning that quotes a bioSTEAM run should
  // quote it in bioSTEAM's spelling.
  if (Number.isNaN(value)) return 'nan';
  if (!Number.isFinite(value)) return value > 0 ? 'inf' : '-inf';
  const [mantissa, exponent] = value.toExponential(precision - 1).split('e');
  const e = Number(exponent);
  if (e >= -4 && e < precision) {
    const fixed = value.toFixed(Math.max(0, precision - 1 - e));
    return fixed.includes('.') ? fixed.replace(/\.?0+$/, '') : fixed;
  }
  const m = mantissa.includes('.') ? mantissa.replace(/\.?0+$/, '') : mantissa;
  const sign = e < 0 ? '-' : '+';
  return `${m}e${sign}${String(Math.abs(e)).padStart(2, '0')}`;
}
