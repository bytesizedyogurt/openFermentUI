// Aeration: the oxygen a culture demands, and the shaft power it costs to
// deliver it.
//
// Ported from BioSTEAM v2.53.11 `units/design_tools/aeration.py` (UIUC/NCSA
// licence; see NOTICE.md). Only the stirred-tank subset is here — van 't Riet's
// kLa correlation, its inversion for gassed power, Henry's law for dissolved
// oxygen, and the log-mean driving force — because that is the chain the
// fermenter in `src/sim/flowsheets/units.ts` walks: oxygen uptake gives a
// required kLa, and the required kLa gives the agitator's power draw. This is
// what makes a fermenter a fermenter rather than a stirred tank: its electricity
// bill is set by the culture's respiration, not by a W/m³ rule of thumb.
//
// Left behind, and why:
//
//   - `vent_broth`, which flashes the broth against the vent. It needs a
//     MultiStream and a vapour–liquid equilibrium solve, and there is no
//     thermosteam here to do either honestly.
//   - the general `C_L(T, Py, chemical)` and the full `H_coefficients` table
//     (O2, CO2, CO, H2, N2). Upstream stores it in a `ChemicalDataDictionary`,
//     so the lookup goes through the `chemicals` package's identifier
//     resolution — a whole chemical registry to carry for one dictionary. Only
//     the oxygen pair is carried below, which is the only one this port needs.
//   - every other correlation in the module: the bubble-column family
//     (Deshpande, De Jesus, Akita & Yoshida, Pošarac & Tekić, Seno, Suh, Shah,
//     Dewes) and the remaining stirred-tank ones (Labík, Galaction). None is
//     reachable from a stirred fermenter, and `kla_bubcol_Deshpande` cannot run
//     upstream as written in this release anyway — it calls
//     `Henrys_law_constant(T)` without the coefficients that function requires.
//   - the `kLa_methods` / `kLa_method_names` registry and its `register`
//     decorator, which builds method names by splitting Python function names,
//     and the `__main__` block of published validity ranges.
//
// Two deliberate unit changes at the boundary, and nowhere else. Upstream takes
// oxygen partial pressure in bar and returns dissolved concentration in mol/kg
// of broth; `C_O2_L` here takes pascals and returns kmol/m³, because stream
// pressures in this engine are pascals and every other concentration it handles
// is per unit volume. The correlation itself, its coefficients and the power
// functions are untouched, and van 't Riet's arguments keep upstream's units of
// W, m³ and m/s.

/** Coefficients (a, b, c) of kLa = a·(P/V)^b·U^c. */
export type RietCoefficients = readonly [a: number, b: number, c: number];

/**
 * Fitted coefficients for van 't Riet's form, upstream's
 * `_kLa_coefficients_Riet`, as tabulated by Garcia-Ochoa & Gomez, *Biotechnol.
 * Adv.* 27 (2009) 153–176.
 *
 * The two rows disagree by more than their shared prefactor suggests: at a
 * gassed power of 500 W/m³ and a superficial velocity of 0.03 m/s, Figueiredo &
 * Calderbank's stronger exponents give roughly a fifth more kLa than van 't
 * Riet's own, and inverting for power magnifies that gap further. Which row a
 * design uses is therefore a real assumption and not a detail.
 */
export const KLA_COEFFICIENTS_RIET: Record<string, RietCoefficients> = {
  // kLa = a · (P/V)^b · U^c, with P/V in W/m³ and U in m/s.
  'Figueiredo & Calderbank': [0.026, 0.6, 0.8],
  "Van't Riet": [0.026, 0.4, 0.5],
};

/**
 * Upstream defaults both Riet functions to Figueiredo & Calderbank, not to the
 * row that carries van 't Riet's name. That reads like a slip and is not one, so
 * it is named here rather than buried in two `?? ` expressions.
 */
const DEFAULT_RIET_AUTHOR = 'Figueiredo & Calderbank';

/** Henry's law coefficient for oxygen, mol/(kg·bar) at 298.15 K. */
const K_H_O2_MOL_PER_KG_BAR = 0.0013;

/** Temperature coefficient for oxygen, K. NIST WebBook, species C7782447. */
const A_O2_K = 1500;

/**
 * Density assumed for fermentation broth, kg/m³.
 *
 * Upstream's dissolved concentrations are per kilogramme of broth and are
 * multiplied by the effluent density where they are used. This port has no
 * property package to ask for that density, so it assumes water. The conversion
 * is written out below even though it is numerically an identity at this value,
 * because the assumption is what a reviewer needs to see — a broth thick with
 * biomass is heavier than this, and the saturation concentration in kmol/m³
 * scales directly with whatever number stands here.
 */
const BROTH_DENSITY_KG_PER_M3 = 1000;

function resolveRietCoefficients(coefficients?: string | RietCoefficients): RietCoefficients {
  if (coefficients === undefined) return KLA_COEFFICIENTS_RIET[DEFAULT_RIET_AUTHOR];
  if (typeof coefficients !== 'string') return coefficients;
  // Upstream would raise a KeyError on an unknown author; failing loudly here
  // keeps a typo from silently costing the plant its agitator power.
  const named: RietCoefficients | undefined = KLA_COEFFICIENTS_RIET[coefficients];
  if (named === undefined) {
    throw new Error(
      `unknown kLa correlation '${coefficients}'; valid authors are ` +
        Object.keys(KLA_COEFFICIENTS_RIET)
          .map((k) => `'${k}'`)
          .join(', '),
    );
  }
  return named;
}

/**
 * Volumetric mass transfer coefficient kLa [1/s] for a stirred tank, upstream's
 * `kLa_stirred_Riet`.
 *
 * The correlation is kLa = a·(P/V)^b·U^c, where P is the *gassed* power drawn by
 * the impeller in W, V the total volume in m³, and U the superficial gas
 * velocity in m/s. It lumps the film coefficient and the specific interfacial
 * area together because the two cannot be measured apart in a working vessel:
 * more power makes smaller bubbles, which raises both at once.
 *
 * `coefficients` is either an author in `KLA_COEFFICIENTS_RIET` or an explicit
 * (a, b, c); omitting it selects Figueiredo & Calderbank, as upstream does.
 */
export function kLaStirredRiet(
  P_W: number,
  V_m3: number,
  U_m_s: number,
  coefficients?: string | RietCoefficients,
): number {
  const [a, b, c] = resolveRietCoefficients(coefficients);
  return a * (P_W / V_m3) ** b * U_m_s ** c;
}

/**
 * Gassed power [W] that achieves a required kLa [1/s], upstream's
 * `P_at_kLa_Riet`.
 *
 * This is the inversion of `kLaStirredRiet` in closed form, taken from upstream
 * rather than solved numerically: P = (kLa / (a·U^c))^(1/b) · V. It is the
 * direction a design actually runs in — the culture states its oxygen demand,
 * the vessel states its volume and sparge rate, and the impeller has to make up
 * the difference. Because b < 1 the exponent 1/b exceeds one, so power rises
 * faster than linearly in the demanded kLa: with Figueiredo & Calderbank,
 * doubling kLa costs about 3.2 times the power. That convexity is the reason
 * high-density aerobic fermentation is expensive to run, and it is why the
 * choice of coefficients above matters.
 */
export function PAtKLaRiet(
  kLa: number,
  V: number,
  U: number,
  coefficients?: string | RietCoefficients,
): number {
  const [a, b, c] = resolveRietCoefficients(coefficients);
  return (kLa / (a * U ** c)) ** (1 / b) * V;
}

/**
 * Henry's law constant [mol/(kg·bar)] at temperature `T` [K], upstream's
 * `Henrys_law_constant`.
 *
 * `k_H` is the constant at 298.15 K in mol/(kg·bar) and `A` its temperature
 * coefficient in K, in the van 't Hoff form used by the NIST WebBook. Solubility
 * falls as the broth warms, which is the direction that matters here: a
 * fermentation held at 30 °C has about eight per cent less oxygen available at
 * saturation than the same vessel at 25 °C.
 */
export function henrysLawConstant(T: number, k_H: number, A: number): number {
  const dTinv = 1 / T - 1 / 298.15;
  return k_H * Math.exp(A * dTinv);
}

/**
 * Saturation concentration of dissolved oxygen [kmol/m³] at broth temperature
 * `T_K` [K] and oxygen partial pressure `P_O2_Pa` [Pa], upstream's `C_O2_L`.
 *
 * The number is small and the whole design turns on it: air at one atmosphere
 * puts about 2.5e-4 kmol/m³ of oxygen into water at 30 °C, some eight
 * milligrammes per litre, which a dense culture consumes in seconds. Oxygen has
 * to be transferred continuously rather than stocked, and the tiny gap between
 * this saturation value and the dissolved concentration the culture is held at
 * is the entire driving force the agitator is paid to maintain.
 */
export function C_O2_L(T_K: number, P_O2_Pa: number): number {
  const P_O2_bar = P_O2_Pa / 1e5;
  const C_mol_per_kg = P_O2_bar * henrysLawConstant(T_K, K_H_O2_MOL_PER_KG_BAR, A_O2_K);
  return (C_mol_per_kg * BROTH_DENSITY_KG_PER_M3) / 1000;
}

/**
 * Log-mean driving force for mass transfer, upstream's
 * `log_mean_driving_force`, in whatever concentration unit the arguments carry.
 *
 * Both the saturation concentration and the dissolved concentration differ
 * between the bottom and the top of a tall vessel — the sparged gas loses oxygen
 * as it rises and the hydrostatic head falls with it — so the simple difference
 * overstates the driving force in anything over a metre or so of liquid
 * (Benz, *AIChE CEP* 2011, 21–26). Averaging logarithmically is the standard
 * correction, exactly as for a counter-current exchanger.
 *
 * `C_in` defaults to `C_out`, which assumes perfect mixing and the same oxygen
 * uptake rate everywhere in the broth, leaving only the saturation profile to
 * vary.
 */
export function logMeanDrivingForce(
  C_sat_out: number,
  C_sat_in: number,
  C_out: number,
  C_in?: number,
): number {
  // Perfect mixing, so the culture draws oxygen at the same rate top and bottom.
  const C_in_ = C_in ?? C_out;
  let dC_out = C_sat_out - C_out;
  const dC_in = C_sat_in - C_in_;
  // A dissolved concentration at or above saturation is not physically possible
  // and means the caller's assumptions have crossed; upstream pins it just
  // above zero rather than returning a negative driving force.
  if (dC_out < 1e-9) dC_out = 1e-9;
  // The log mean is continuous where the two ends coincide, and equals them.
  // Upstream divides by log(1) and raises there; a flat oxygen profile is an
  // ordinary enough case in a short vessel that a NaN leaking into the power
  // calculation would be the worse answer.
  if (dC_out === dC_in) return dC_out;
  return (dC_out - dC_in) / Math.log(dC_out / dC_in);
}
