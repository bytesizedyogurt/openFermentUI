// Utility agents — steam, fired gas, cooling water, refrigeration — and what an
// hour of each of them costs.
//
// Ported from BioSTEAM v2.53.11 `_heat_utility.py` (the `UtilityAgent` class and
// the `default_heating_agents` / `default_cooling_agents` class methods) and
// `_power_utility.py` (UIUC/NCSA licence; see NOTICE.md).
//
// Left behind, and why:
//
//   - `UtilityAgent` is a thermosteam `Stream` upstream, so an agent carries a
//     full property package: `Hvap` at the agent's state for a condensing
//     utility, `H(T)` at two temperatures for a sensible one, and for natural
//     gas a combustion-reaction solve that dilutes the flue gas with air to a
//     5.5 wt% CO₂ target and takes the enthalpy difference to the stack
//     temperature. None of that exists here. Each agent therefore carries one
//     precomputed `energyPerKmol`, and every one of those numbers is sourced in
//     a comment beside it, to three significant figures and no more.
//   - the refrigerants below chilled brine — propane, propylene, ethylene. Their
//     pressures upstream are `Psat(T)` evaluated by thermosteam at import time,
//     so porting them would mean either inventing an Antoine fit or writing down
//     a pressure and calling it upstream's. `pickCoolingAgent` therefore refuses
//     below roughly 257 K rather than quietly costing a cryogenic duty as brine.
//   - the heat-exchanger-network machinery that consumes these agents:
//     `HeatUtility.__call__`, the pinch-temperature helpers, `mix_from`,
//     `sum_by_agent`, the fuel/emissions streams, and the characterisation
//     factors for life-cycle assessment. This module answers one question —
//     given an agent and a duty, what does the hour cost — which is the only
//     question the costing engine asks of it.
//
// The prices, temperatures and pressures are upstream's exactly. They are not
// rounded, not converted, and not "updated": a utility price is an assumption a
// reviewer is entitled to challenge, and it can only be challenged if it is the
// number bioSTEAM actually ships.

/**
 * One utility option: a fluid at a stated state, with the two prices that
 * bioSTEAM charges for it.
 *
 * Upstream charges some agents per kJ transferred (`heat_transfer_price`) and
 * others per kmol circulated (`regeneration_price`), and the two are not
 * interchangeable. Steam is bought as condensate — you pay for the mole, and the
 * energy you get from it is whatever its latent heat happens to be. Chilled
 * water is bought as refrigeration duty — you pay for the joule, and the flow is
 * bookkeeping. Both fields are kept so that neither kind has to be re-expressed
 * as the other.
 */
export interface UtilityAgent {
  ID: string;
  /** Supply temperature, K. */
  T: number;
  /** Supply pressure, Pa. */
  P: number;
  kind: 'heating' | 'cooling';
  /** USD/kJ transferred. */
  heatTransferPrice: number;
  /** USD/kmol circulated. */
  regenerationPrice: number;
  /** Fraction of the utility's heat that reaches the process, 0–1. */
  heatTransferEfficiency: number;
  /**
   * Return temperature, K, for an agent that works by sensible heat. Absent
   * means the agent works by phase change and returns at its own temperature.
   */
  T_limit?: number;
  /**
   * Minimum temperature margin, K, an agent must have over the duty before it
   * is considered suitable. Upstream's guard against a sensible-heat agent
   * approaching its own supply temperature and demanding a near-infinite flow.
   */
  dT: number;
  /** kJ/kmol — latent heat for a condensing agent, sensible dT*Cp for a liquid agent. */
  energyPerKmol: number;
}

// Every `energyPerKmol` below that involves water was obtained from a
// steam-table enthalpy per kilogram multiplied by water's molar mass,
// 18.015 kg/kmol, because the prices are quoted per kmol and the tables are
// published per kilogram.

/**
 * Heating agents, in upstream's list order.
 *
 * The order is load-bearing and is *not* a price ranking, which is worth saying
 * plainly because `pickHeatingAgent` looks like it should be one. Per kJ
 * delivered, natural gas is the cheapest of the four — roughly 5.2 USD/GJ
 * against low-pressure steam's 6.5 — yet upstream puts it last and reaches it
 * only when no steam is hot enough. That is a modelling decision, not an
 * oversight: a fired heater is a different piece of equipment from a steam coil,
 * and bioSTEAM will not silently swap one for the other to save money.
 */
export const HEATING_AGENTS: UtilityAgent[] = [
  {
    ID: 'low_pressure_steam',
    T: 412.189,
    P: 344738.0,
    kind: 'heating',
    heatTransferPrice: 0,
    regenerationPrice: 0.2378,
    heatTransferEfficiency: 0.95,
    dT: 0,
    // Latent heat of water at 0.345 MPa: 2150 kJ/kg from the saturation-pressure
    // steam table (interpolated between the 0.30 and 0.35 MPa rows of Cengel &
    // Boles, Table A-5), times water's molar mass. This one can be checked against
    // upstream directly: the `HeatUtility` docstring's `hu(1000, 300, 350)`
    // reports 1052.63 kJ/hr against 0.0272127 kmol/hr, which is 38 682 kJ/kmol.
    energyPerKmol: 3.87e4,
  },
  {
    ID: 'medium_pressure_steam',
    T: 454.77,
    P: 1.041e6,
    kind: 'heating',
    heatTransferPrice: 0,
    regenerationPrice: 0.2756,
    heatTransferEfficiency: 0.9,
    dT: 0,
    // Latent heat of water at 181.6 °C: 2009 kJ/kg, interpolated in the
    // saturation-temperature steam table between the 180 and 185 °C rows.
    energyPerKmol: 3.62e4,
  },
  {
    ID: 'high_pressure_steam',
    T: 508.991,
    P: 3.11e6,
    kind: 'heating',
    heatTransferPrice: 0,
    regenerationPrice: 0.3171,
    heatTransferEfficiency: 0.85,
    dT: 0,
    // Latent heat of water at 3.11 MPa: 1785 kJ/kg, interpolated between the
    // 3.0 and 3.5 MPa rows of the saturation-pressure table. That interpolation
    // also puts saturation at 508.9 K, which agrees with the 508.991 K upstream
    // states — so the pressure and the temperature here describe one state, not
    // two.
    energyPerKmol: 3.22e4,
  },
  {
    ID: 'natural_gas',
    T: 298.15,
    // 200 atm, written as `200 * 101325` upstream.
    P: 200 * 101325,
    kind: 'heating',
    heatTransferPrice: 0,
    regenerationPrice: 3.49672,
    heatTransferEfficiency: 0.95,
    // Upstream's comment: reasonably above the flue gas dew point at 500 psig.
    T_limit: 405,
    dT: 0,
    // The weakest number in this file, and it is worth being explicit about how
    // weak. Upstream burns the gas and takes the enthalpy drop of the flue gas
    // down to T_limit, which needs combustion stoichiometry and a mixture
    // enthalpy this port does not have. The estimate is methane's lower heating
    // value, 8.02e5 kJ/kmol at 298.15 K (NIST), less the sensible heat carried
    // out of the stack at 405 K by the diluted flue gas — 44 kg CO₂ per kmol of
    // methane at upstream's 5.5 wt% CO₂ target is about 800 kg of flue gas, and
    // 800 kg × 1.05 kJ/(kg·K) × 107 K is roughly 9.0e4 kJ/kmol. Treat this as
    // good to two figures, not three: an error here moves the fired-heater
    // utility bill proportionally.
    energyPerKmol: 7.13e5,
  },
];

/**
 * Cooling agents, in upstream's list order, truncated after chilled brine.
 *
 * Here the order *is* a price ranking — cooling water, chilled water and brine
 * cost 0.33, 5.0 and 8.1 USD/GJ respectively — so taking the first suitable
 * agent genuinely takes the cheapest one.
 */
export const COOLING_AGENTS: UtilityAgent[] = [
  {
    ID: 'cooling_water',
    // 90 °F supply, returned at 125 °F: the classic cooling-tower loop.
    T: 305.372,
    P: 101325,
    kind: 'cooling',
    heatTransferPrice: 0,
    regenerationPrice: 4.8785e-4,
    heatTransferEfficiency: 1,
    T_limit: 324.817,
    dT: 2,
    // Sensible heat over the agent's own 19.445 K rise: 75.3 kJ/(kmol·K) ×
    // 19.445 K. Against upstream's regeneration price that works out to
    // 0.33 USD/GJ, which is where published cooling-water costs sit.
    energyPerKmol: 1.46e3,
  },
  {
    ID: 'chilled_water',
    // 45 °F supply, returned at 80.6 °F.
    T: 280.372,
    P: 101325,
    kind: 'cooling',
    heatTransferPrice: 5e-6,
    regenerationPrice: 0,
    heatTransferEfficiency: 1,
    T_limit: 300.372,
    dT: 2,
    // Sensible heat over 20.000 K at 75.5 kJ/(kmol·K). Chilled water is priced
    // per kJ, so this figure sets the reported flow and nothing else.
    energyPerKmol: 1.51e3,
  },
  {
    ID: 'chilled_brine',
    // 0 °F supply, returned at 36 °F.
    T: 255.372,
    P: 101325,
    kind: 'cooling',
    heatTransferPrice: 8.145e-6,
    regenerationPrice: 0,
    heatTransferEfficiency: 1,
    T_limit: 275.372,
    dT: 2,
    // Upstream declares brine as pure water, which cannot be liquid at 255 K;
    // it is a stand-in so that the agent has some property package at all. That
    // stand-in is kept rather than corrected, because brine is priced per kJ and
    // the only thing this number changes is a reported flow. A real CaCl₂ brine
    // would be nearer 3.0 kJ/(kg·K), so the flow shown for this agent is low by
    // about a third. It does not touch the cost.
    energyPerKmol: 1.51e3,
  },
];

/**
 * Agents that are burned rather than circulated. Upstream carries this as the
 * `isfuel` flag, and `get_suitable_heating_agent` short-circuits on it: a fired
 * heater is limited by its flame, not by the fuel's storage temperature, so it
 * can serve any duty and never fails the temperature test.
 */
const FUEL_AGENT_IDS = new Set(['natural_gas']);

/** Electricity price, USD/kWhr. Upstream's `PowerUtility.default_price`. */
export const ELECTRICITY_PRICE = 0.0782;

/**
 * Cost of electricity, USD/hr, for a net draw in kW.
 *
 * Signed the way upstream signs it — `PowerUtility.cost` is `price * power`,
 * where power is consumption minus production — so a unit that exports power
 * returns a credit. Turbogenerators and expanders are the whole reason that sign
 * survives instead of being clamped at zero.
 */
export function costPower(kW: number): number {
  return kW * ELECTRICITY_PRICE;
}

/** Look up an agent by ID across both lists. */
export function getAgent(ID: string): UtilityAgent {
  for (const agent of HEATING_AGENTS) if (agent.ID === ID) return agent;
  for (const agent of COOLING_AGENTS) if (agent.ID === ID) return agent;
  const valid = [...HEATING_AGENTS, ...COOLING_AGENTS].map((a) => a.ID).join(', ');
  throw new Error(`Unknown utility agent '${ID}'. Valid agents: ${valid}.`);
}

/**
 * Cost of a heating (duty > 0) or cooling (duty < 0) demand, USD/hr.
 *
 * `duty` is the duty seen by the process — upstream's `unit_duty`. The utility
 * has to supply more than that, because some of its heat is lost to the
 * surroundings, which is what `heatTransferEfficiency` divides out; upstream
 * does the same division before it prices anything. The result is always a
 * charge and never a credit: cooling a stream and heating one both cost money,
 * so only the magnitude of the duty matters to the bill.
 *
 * The agent's `kind` is deliberately not checked against the sign of the duty.
 * The caller chose the agent, and pairing cooling water with a positive duty is
 * a mistake in the flowsheet rather than in the price list — one that costing
 * cannot detect, because the arithmetic is identical either way.
 */
export function costHeatUtility(agentID: string, duty_kJ_per_hr: number): number {
  if (!duty_kJ_per_hr) return 0;
  const agent = getAgent(agentID);
  const duty = Math.abs(duty_kJ_per_hr) / agent.heatTransferEfficiency;
  const flow_kmol_per_hr = duty / agent.energyPerKmol;
  return duty * agent.heatTransferPrice + flow_kmol_per_hr * agent.regenerationPrice;
}

/**
 * The first heating agent hot enough for a duty at `T_required_K`, following
 * upstream's `get_suitable_heating_agent`.
 *
 * "First" rather than "cheapest": see the note on `HEATING_AGENTS` for why those
 * are not the same thing here. Upstream is called with a pinch temperature — the
 * process temperature plus its 5 K minimum approach — not with the process
 * temperature itself, and this function inherits that expectation. Passing the
 * raw process temperature will occasionally pick an agent that cannot actually
 * drive the exchanger.
 */
export function pickHeatingAgent(T_required_K: number): UtilityAgent {
  for (const agent of HEATING_AGENTS) {
    if (T_required_K < agent.T - agent.dT || FUEL_AGENT_IDS.has(agent.ID)) return agent;
  }
  throw new Error(`No heating agent can heat above ${T_required_K.toPrecision(4)} K.`);
}

/**
 * The cheapest cooling agent cold enough for a duty at `T_required_K`, following
 * upstream's `get_suitable_cooling_agent`.
 *
 * As above, upstream expects a pinch temperature. Below about 257 K this throws
 * where upstream would reach for propane, propylene or ethylene — the
 * refrigerants left out of this port. Refusing is the honest failure: the
 * alternative is costing a cryogenic duty at brine prices and reporting a number
 * that is wrong by an order of magnitude without saying so.
 */
export function pickCoolingAgent(T_required_K: number): UtilityAgent {
  for (const agent of COOLING_AGENTS) {
    if (T_required_K > agent.T + agent.dT) return agent;
  }
  throw new Error(
    `No cooling agent can cool below ${T_required_K.toPrecision(4)} K. ` +
      `The coldest agent ported is chilled_brine at ${COOLING_AGENTS[COOLING_AGENTS.length - 1].T} K; ` +
      `bioSTEAM's propane, propylene and ethylene refrigerants are not ported.`,
  );
}
