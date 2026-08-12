// Pressure-vessel design and purchase costing.
//
// Ported from BioSTEAM v2.53.11 `units/design_tools/flash_vessel_design.py`,
// `units/design_tools/pressure_vessel.py` and
// `units/design_tools/specification_factors.py` (UIUC/NCSA licence; see
// NOTICE.md). The correlations are Seider, Lewin, Seader, Widagdo, Gani & Ng,
// *Product and Process Design Principles* (Wiley, 2017), chapter 16, with the
// two-phase separator geometry from *Chemical Engineering Progress*, Oct 1993.
//
// Left behind from `flash_vessel_design.py`: `GTable` (which upstream itself
// marks as untested and unused), `HNATable`, `compute_low_liq_level_height`,
// `compute_Stokes_law_York_Demister_K_value` and `ceil_half_step`. Those size
// the *internals* of a flash drum — demister K-values, liquid level heights —
// and nothing in openFerment flashes anything, because flashing needs the
// vapour–liquid equilibrium this port does not have.
//
// Left behind from `pressure_vessel.py`: the `PressureVessel` mixin class
// itself. Its methods are thin dispatchers that pick horizontal or vertical
// and stuff a dictionary; a `BioUnit` subclass here calls the functions below
// directly and fills its own `designResults`, which keeps the sizing visible at
// the call site instead of hidden behind an inherited `_vessel_design`.
//
// Left behind from `specification_factors.py`: every table that is not about
// pressure vessels — ordinary vessel, pump, distillation tray and column, and
// shell-and-tube factors. Those belong with the units that use them.
import { CE } from './cepci';

/**
 * Material factors for pressure vessels, upstream's
 * `pressure_vessel_material_factors`.
 *
 * These multiply the *vessel* purchase cost only, never the platform and
 * ladders — upstream's `PressureVessel.vessel_material` setter writes the
 * factor into `F_M['Vertical pressure vessel']` and
 * `F_M['Horizontal pressure vessel']` and leaves the platform alone.
 */
export const PRESSURE_VESSEL_MATERIAL_FACTORS: Record<string, number> = {
  'Carbon steel': 1.0,
  'Low-alloy steel': 1.2,
  'Stainless steel 304': 1.7,
  'Stainless steel 316': 2.1,
  'Carpenter 20CB-3': 3.2,
  'Nickel-200': 5.4,
  'Monel-400': 3.6,
  'Inconel-600': 3.9,
  'Incoloy-825': 3.7,
  Titanium: 7.7,
};

/**
 * Densities of construction materials, lb/ft³, upstream's
 * `material_densities_lb_per_ft3`.
 *
 * Upstream lists all ten pressure-vessel materials but gives a number for only
 * three of them; the other seven — low-alloy steel, Carpenter 20CB-3,
 * Nickel-200, Monel-400, Inconel-600, Incoloy-825 and titanium — are `None`,
 * and a vessel built from one of them raises a `TypeError` deep inside the
 * weight correlation. That gap is real and this map reproduces it by omission
 * rather than papering over it with handbook densities bioSTEAM never used: a
 * cost computed from a density the published method does not carry is not the
 * published method's cost. Callers should treat a missing key as "this
 * material cannot be costed here" and say so.
 */
export const MATERIAL_DENSITIES_LB_PER_FT3: Record<string, number> = {
  'Carbon steel': 490,
  'Stainless steel 304': 499.4,
  'Stainless steel 316': 499.4,
};

/** Vessel weight in lb and wall thickness in inches. */
export interface VesselWeightAndWallThickness {
  /** lb. */
  weight: number;
  /** in. */
  thickness: number;
}

/**
 * Return the vessel weight [lb] and wall thickness [in].
 *
 * @param P pressure, psia
 * @param D internal diameter, ft
 * @param L vessel length, ft
 * @param rho_M density of the construction material, lb/ft³
 * @param Da annular diameter for jacketed vessels, ft; 0 means no jacket
 * @param Je joint efficiency, 1.0 for X-rayed joints, 0.85 for thin carbon steel
 * @param S vessel material stress coefficient, psi — see the note below
 *
 * Only valid for positive internal pressure. A vacuum vessel may need
 * stiffening rings and a thicker wall than this returns, and upstream warns
 * about exactly that at any pressure below 14.68 psia.
 */
export function computeVesselWeightAndWallThickness(
  P: number,
  D: number,
  L: number,
  rho_M: number,
  Da = 0,
  Je = 0.85,
  S = 15000,
): VesselWeightAndWallThickness {
  // Upstream opens the function body with `S = 15000.0`, which discards
  // whatever the caller passed for the stress coefficient — the parameter is
  // documented and defaulted, then immediately shadowed. That is almost
  // certainly a bug in bioSTEAM, but every published bioSTEAM vessel cost was
  // computed with carbon steel's 15000 psi regardless of the material named,
  // so reproducing the bug is what keeps this port's numbers comparable with
  // theirs. Fixing it here would silently change every cost on the screen.
  S = 15000.0;
  const Ca = 1.0 / 8.0; // corrosion allowance, in
  let Di = D;
  if (Da) {
    // The size of the entire vessel increases to the outside diameter, while
    // the internal wall stays at the original size.
    Di = D;
    D = Di + Da;
  }
  const P_gauge = Math.abs(P - 14.7); // psig
  const P1 = P_gauge + 30.0;
  const P2 = 1.1 * P_gauge;
  const PT = P1 > P2 ? P1 : P2; // test pressure, psig

  // Shell wall thickness [in] and shell surface area [ft²].
  const SWT = (PT * D * 12.0) / (2.0 * S * Je - 1.2 * PT) + Ca;
  let SSA = Math.PI * D * L;

  // Head geometry follows diameter and test pressure. Note that a vessel of
  // exactly 15 ft falls through to the dished-head branch in both bioSTEAM and
  // here: the first branch tests `D < 15` and the second `D > 15`.
  let HWT: number;
  let HSA: number;
  if (D < 15.0 && PT > 100 - 14.7) {
    // Elliptical heads.
    HWT = (PT * D * 12.0) / (2.0 * S * Je - 0.2 * PT) + Ca;
    HSA = 1.09 * D ** 2;
  } else if (D > 15.0) {
    // Hemispherical heads.
    HWT = (PT * D * 12.0) / (4.0 * S * Je - 0.4 * PT) + Ca;
    HSA = 1.571 * D ** 2;
  } else {
    // Dished heads.
    HWT = (0.885 * (PT * D * 12.0)) / (S * Je - 0.1 * PT) + Ca;
    HSA = 0.842 * D ** 2;
  }

  // The wall has to satisfy both the shell and the heads, so take the thicker.
  let ts = SWT > HWT ? SWT : HWT;

  // A wide thin-walled vessel would buckle under its own handling long before
  // it failed on pressure, so a minimum thickness for rigidity applies below
  // 12 ft diameter. Above that upstream declines to impose one and leaves the
  // pressure-derived thickness standing.
  let ts_min: number;
  if (D < 4) ts_min = 1 / 4;
  else if (D < 6) ts_min = 5 / 16;
  else if (D < 8) ts_min = 3 / 8;
  else if (D < 10) ts_min = 7 / 16;
  else if (D < 12) ts_min = 1 / 2;
  else ts_min = ts;
  if (ts < ts_min) ts = ts_min;

  // A jacket adds a second cylindrical wall, so its area is charged on top of
  // the outer shell's rather than replacing it.
  if (Da) SSA += Math.PI * (Di + ts / 12) * L;

  let VW = ((rho_M * ts) / 12) * (SSA + 2.0 * HSA); // lb
  VW = roundHalfEven(VW, 2);
  return { weight: VW, thickness: ts };
}

/**
 * Return the purchase cost [USD] of a horizontal vessel of weight `W` [lb],
 * without the platform and ladders.
 */
export function computeHorizontalVesselPurchaseCost(W: number): number {
  const lnW = Math.log(W);
  const C_v = Math.exp(5.6336 + 0.4599 * lnW + 0.00582 * lnW * lnW);
  return (CE.value / 567) * C_v;
}

/**
 * Return the purchase cost [USD] of a vertical vessel of weight `W` [lb],
 * without the platform and ladders.
 */
export function computeVerticalVesselPurchaseCost(W: number): number {
  const lnW = Math.log(W);
  const C_v = Math.exp(7.139 + 0.18255 * lnW + 0.02297 * lnW * lnW);
  return (CE.value / 567) * C_v;
}

/**
 * Return the purchase cost [USD] of the platform and ladders for a horizontal
 * vessel of diameter `D` [ft].
 */
export function computeHorizontalVesselPlatformAndLaddersPurchaseCost(D: number): number {
  const C_pl = 2275 * D ** 0.20294;
  return (CE.value / 567) * C_pl;
}

/**
 * Return the purchase cost [USD] of the platform and ladders for a vertical
 * vessel of diameter `D` [ft] and length `L` [ft].
 */
export function computeVerticalVesselPlatformAndLaddersPurchaseCost(D: number, L: number): number {
  const C_pl = 410 * D ** 0.7396 * L ** 0.70684;
  return (CE.value / 567) * C_pl;
}

/**
 * Bare-module factors, upstream's `PressureVessel._F_BM_default`.
 *
 * The keys are the purchase-cost line items themselves, so a unit that costs a
 * vessel plus its platform reports two lines with two different factors — the
 * platform is bought and bolted down, not piped and insulated, so it carries
 * no bare-module multiplier at all.
 */
export const VESSEL_F_BM: Record<string, number> = {
  'Horizontal pressure vessel': 3.05,
  'Vertical pressure vessel': 4.16,
  'Horizontal pressure vessel (jacketed)': 3.05,
  'Vertical pressure vessel (jacketed)': 4.16,
  'Platform and ladders': 1,
};

/**
 * Validity ranges of the vessel cost correlations, upstream's
 * `PressureVessel._bounds`. Weights are lb, diameter and length are ft.
 */
export const VESSEL_BOUNDS = {
  'Vertical vessel weight': [4200, 1e6],
  'Horizontal vessel weight': [1e3, 9.2e5],
  'Horizontal vessel diameter': [3, 21],
  'Vertical vessel length': [12, 40],
} as const;

export type VesselBoundKind = keyof typeof VESSEL_BOUNDS;

const VESSEL_BOUND_UNITS: Record<VesselBoundKind, string> = {
  'Vertical vessel weight': 'lb',
  'Horizontal vessel weight': 'lb',
  'Horizontal vessel diameter': 'ft',
  'Vertical vessel length': 'ft',
};

/**
 * Return the out-of-bounds message bioSTEAM would emit for `value`, or null
 * when the value is inside the correlation's range.
 *
 * Upstream raises this through `warnings.warn`, where a Python process prints
 * it to stderr and a browser would drop it on the floor. Returning the string
 * lets the caller push it onto `BioUnit.warnings`, which is what puts it in
 * front of the reader next to the number it undermines. A cost extrapolated
 * outside the range Seider fitted is still a number, and the only honest thing
 * to do with it is show it with the caveat attached.
 *
 * All four vessel bounds are checked against the cost correlation rather than
 * the design algorithm, hence the fixed suffix.
 */
export function checkVesselBounds(kind: VesselBoundKind, value: number): string | null {
  const [lb, ub] = VESSEL_BOUNDS[kind];
  if (lb <= value && value <= ub) return null;
  const units = ' ' + VESSEL_BOUND_UNITS[kind];
  return (
    `${kind} (${formatG(value, 4)}${units}) is out of bounds ` +
    `(${formatG(lb, 4)} to ${formatG(ub, 4)}${units}) for cost correlation`
  );
}

/**
 * Round to `decimals` places the way NumPy does, half to even.
 *
 * `Math.round` breaks ties upward, NumPy's `rint` breaks them to the nearest
 * even digit. Ties are rare in floating point and the two agree almost always,
 * but "almost always" is not something to leave undocumented in a number a
 * reviewer will check against a bioSTEAM run.
 */
function roundHalfEven(value: number, decimals: number): number {
  const scale = 10 ** decimals;
  const x = value * scale;
  const floor = Math.floor(x);
  const frac = x - floor;
  let n: number;
  if (frac > 0.5) n = floor + 1;
  else if (frac < 0.5) n = floor;
  else n = floor % 2 === 0 ? floor : floor + 1;
  return n / scale;
}

/**
 * Format a number the way Python's `:.{precision}g` does.
 *
 * The warning text above is meant to be comparable with a bioSTEAM run
 * character for character, and `toPrecision` is not a substitute: Python
 * renders a million at four significant figures as `1e+06`, JavaScript as
 * `1.000e+6`. The rules reproduced here are fixed notation when the decimal
 * exponent falls in [-4, precision), scientific otherwise, trailing zeros
 * stripped either way, and an exponent padded to two digits.
 */
function formatG(value: number, precision: number): string {
  if (value === 0) return '0';
  if (Number.isNaN(value)) return 'nan';
  if (!Number.isFinite(value)) return value > 0 ? 'inf' : '-inf';
  const rounded = roundSignificantHalfEven(value, precision);
  const [mantissa, exponent] = rounded.toExponential(precision - 1).split('e');
  const e = Number(exponent);
  if (e >= -4 && e < precision) {
    const fixed = rounded.toFixed(Math.max(0, precision - 1 - e));
    return fixed.includes('.') ? fixed.replace(/\.?0+$/, '') : fixed;
  }
  const m = mantissa.includes('.') ? mantissa.replace(/\.?0+$/, '') : mantissa;
  const sign = e < 0 ? '-' : '+';
  return `${m}e${sign}${String(Math.abs(e)).padStart(2, '0')}`;
}

/**
 * Round `value` to `precision` significant digits, breaking an exact decimal
 * tie towards the even digit.
 *
 * C's `printf("%g")`, which is what Python's `:.4g` ends up calling, rounds a
 * value sitting exactly halfway between two printable results to the even last
 * digit; every rounding primitive JavaScript offers — `toFixed`,
 * `toExponential`, `toPrecision` — rounds a half away from zero instead. A
 * vessel weight arrives here already rounded to two decimals, so a tie is not
 * hypothetical: a 1234.5 lb vessel prints as `1234` in bioSTEAM and would print
 * as `1235` from `toFixed` alone.
 *
 * Twenty-one significant digits distinguishes a true tie from a value that only
 * looks like one at four: a double carries about seventeen, so any neighbour of
 * the tie differs well inside that window.
 */
function roundSignificantHalfEven(value: number, precision: number): number {
  const [mantissa, exponent] = value.toExponential(20).split('e');
  const digits = mantissa.replace('-', '').replace('.', '');
  const dropped = digits.slice(precision);
  if (!dropped) return value;
  const kept = digits.slice(0, precision);
  // Equal-length digit strings compare lexicographically exactly as the numbers
  // they spell, so this is the comparison against one half of the last kept
  // digit, done without ever building a second float.
  const half = '5'.padEnd(dropped.length, '0');
  const tie = dropped === half;
  const roundUp = dropped > half || (tie && Number(kept[precision - 1]) % 2 === 1);
  let e = Number(exponent);
  let result = kept;
  if (roundUp) {
    const bumped = (BigInt(kept) + 1n).toString();
    if (bumped.length > kept.length) {
      // 9999 -> 10000: keep the leading `precision` digits and let the exponent
      // absorb the extra place. The digit dropped here is always the trailing 0.
      result = bumped.slice(0, precision);
      e += 1;
    } else {
      result = bumped;
    }
  }
  const sign = value < 0 ? '-' : '';
  return Number(`${sign}${result}e${e - (precision - 1)}`);
}
