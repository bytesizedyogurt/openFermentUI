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
//     precomputed `energyPerKmol`, measured by running that upstream machinery
//     (biosteam 2.53.11 on thermosteam 0.53.5) and reading the answer off, and
//     each one is sourced in a comment beside it.
//
//     Two of those quantities are not actually constants upstream — cooling
//     water's sensible rise and natural gas's recovered heat both depend on the
//     process temperature, because the utility's return temperature is pinched
//     against it. Each is pinned here at its most favourable value, and the
//     comment beside it says so and gives the size of the error. A caller that
//     needs those right needs a function that takes the process temperature,
//     which is a different contract from this one.
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

// Every `energyPerKmol` below is upstream's own number, obtained by importing
// biosteam 2.53.11 and evaluating the expression `HeatUtility.__call__` would
// evaluate for that agent: `_get_property('Hvap', nophase=True)` for the
// condensing agents, `H(T) - H(T_limit)` for the sensible ones, and the
// feed-minus-emissions enthalpy drop for natural gas. They are not steam-table
// lookups and not correlations refitted here; where the number is a state
// property it carries thermosteam's value for that state, digit for digit.

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
    // Water's latent heat at (412.189 K, 344738 Pa), read straight out of
    // upstream: `HeatUtility.get_agent('low_pressure_steam')._get_property('Hvap',
    // nophase=True)` under biosteam 2.53.11 / thermosteam 0.53.5. The
    // `HeatUtility` docstring's `hu(1000, 300, 350)` is the same number seen
    // through the results — 1052.6315789473686 kJ/hr over 0.02721274387089031
    // kmol/hr — and this port reproduces that flow and its 0.006471190492497716
    // USD/hr exactly.
    energyPerKmol: 38681.56713419028,
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
    // Water's latent heat at (454.77 K, 1.041 MPa), from upstream's own
    // `_get_property('Hvap', nophase=True)` (biosteam 2.53.11 / thermosteam
    // 0.53.5). Cross-checked end to end: upstream's `hu(1000, 300, 440)` costs
    // 0.008463437829755435 USD/hr, and so does this module.
    energyPerKmol: 36181.77723780491,
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
    // Water's latent heat at (508.991 K, 3.11 MPa), from upstream's own
    // `_get_property('Hvap', nophase=True)` (biosteam 2.53.11 / thermosteam
    // 0.53.5). Cross-checked end to end: upstream's `hu(1000, 300, 500)` costs
    // 0.011598376122202983 USD/hr, and so does this module.
    energyPerKmol: 32164.746133319342,
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
    // Upstream's `feed.Hnet - emissions.Hnet` after the full combustion solve —
    // air diluted to the 5.5 wt% CO₂ target, emissions leaving at 500 psig — with
    // the emissions at T_limit = 405 K. Measured by running biosteam 2.53.11
    // (patched to this source tree's 0.95 efficiency) as `hu(1000, 300, 520)`,
    // which gives duty/flow = 712649.148290721.
    //
    // Read the caveat: this is *not* a constant upstream. The emissions leave at
    // `max(405 K, T_process_in + 5 K)`, so the hotter the process, the less of
    // the flame's heat is recovered and the more gas the same duty burns. The
    // value below is the T_limit floor, i.e. the most favourable case, and it is
    // only reached when the fired heater's inlet is at or below 400 K. Upstream's
    // dh falls to 538 930 kJ/kmol for a process entering at 600 K and to
    // 166 740 kJ/kmol at 1000 K — a fired heater on a hot inlet costs up to
    // roughly four times what this module reports. Fixing that needs the process
    // inlet temperature, which this module's one-function contract does not take.
    energyPerKmol: 712649.148290721,
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
    // Upstream's `H(305.372) - H(324.817)` for liquid water, i.e. the full rise
    // from supply to T_limit (biosteam 2.53.11 / thermosteam 0.53.5). Against the
    // regeneration price that is 0.33 USD/GJ, where published cooling-water costs
    // sit, and it reproduces upstream's `hu(-1000, 400, 350)` cost of
    // 0.00033316882671025717 USD/hr exactly.
    //
    // Read the caveat: upstream only gets the full rise when the process is hot
    // enough to deliver it. The return temperature is `min(324.817 K,
    // T_process_in - 5 K)`, so cooling a stream that enters at 320 K warms the
    // water only to 315 K, halves dh, and doubles the flow — and cooling water is
    // priced per kmol, so it doubles the cost too (upstream: 0.000673 USD/hr for
    // that same 1000 kJ/hr). This module reports the full-rise cost for every
    // duty and so understates near-ambient cooling. Fixing that needs the process
    // inlet temperature, which this module's one-function contract does not take.
    energyPerKmol: 1464.272647645581,
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
    // Upstream's `H(280.372) - H(300.372)` for liquid water (biosteam 2.53.11 /
    // thermosteam 0.53.5). Chilled water is priced per kJ, so this figure sets
    // the reported flow and nothing else — the cost matches upstream exactly
    // (0.005 USD/hr per 1000 kJ/hr) whatever the process temperature does to the
    // return temperature.
    energyPerKmol: 1508.8158608767862,
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
    // Upstream's `H(255.372) - H(275.372)` for liquid water (biosteam 2.53.11 /
    // thermosteam 0.53.5). Upstream declares brine as pure water, which cannot be
    // liquid at 255 K; it is a stand-in so that the agent has some property
    // package at all. The stand-in is reproduced rather than corrected, because
    // the point of this module is to be upstream — and because brine is priced
    // per kJ, so this number sets the reported flow and never the cost. A real
    // CaCl₂ brine would be nearer 3.0 kJ/(kg·K), so the flow shown here is low by
    // about a third, exactly as it is upstream.
    energyPerKmol: 1537.0442883491269,
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
/**
 * Minimum approach temperature in a utility exchanger, K.
 *
 * Upstream's class attribute `HeatUtility.dT = 5` (`_heat_utility.py:421`),
 * which is what `get_outlet_temperature` pinches against. Not to be confused
 * with the per-agent `dT` field, which is only used to decide whether an agent
 * is hot or cold enough to be eligible.
 */
export const MINIMUM_APPROACH_DT = 5;

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
export function costHeatUtility(
  agentID: string,
  duty_kJ_per_hr: number,
  T_process_in_K?: number,
): number {
  // Zero is free. NaN is not: upstream's `if unit_duty == 0` lets a NaN duty
  // propagate to a NaN cost, where it is visible. A falsy test swallows NaN and
  // prices a broken energy balance at nothing, which is the one failure mode
  // this app is least able to notice.
  if (duty_kJ_per_hr === 0) return 0;
  if (Number.isNaN(duty_kJ_per_hr)) return NaN;
  const agent = getAgent(agentID);
  const duty = Math.abs(duty_kJ_per_hr) / agent.heatTransferEfficiency;
  const flow_kmol_per_hr = duty / effectiveEnergyPerKmol(agent, T_process_in_K);
  return duty * agent.heatTransferPrice + flow_kmol_per_hr * agent.regenerationPrice;
}

/**
 * How much heat one kmol of the agent actually carries against *this* process.
 *
 * A cooling utility only achieves its full temperature rise if the process is
 * hot enough to deliver it. Upstream returns cooling water at
 * `min(T_limit, T_process_in - dT)`, so a stream entering at 320 K warms the
 * water to 315 K instead of 324.8 K, halving the enthalpy each mole carries and
 * doubling the flow — and cooling water is billed per mole, so it doubles the
 * bill. Reporting the full-rise figure for every duty understates near-ambient
 * cooling by up to about a factor of two, and near-ambient cooling is exactly
 * what a photobioreactor needs.
 *
 * The scaling below is linear in the achieved rise, which is what a constant
 * heat capacity gives; the constant is implied by the pinned `energyPerKmol`
 * rather than assumed separately, so at the full rise this returns that value
 * unchanged and reproduces upstream exactly. Omit the temperature and the
 * behaviour is the old one.
 */
function effectiveEnergyPerKmol(agent: UtilityAgent, T_process_in_K?: number): number {
  if (T_process_in_K === undefined || agent.kind !== 'cooling' || agent.T_limit === undefined) {
    return agent.energyPerKmol;
  }
  const fullRise = agent.T_limit - agent.T;
  if (!(fullRise > 0)) return agent.energyPerKmol;
  // MINIMUM_APPROACH_DT, not `agent.dT`. The two are different numbers doing
  // different jobs upstream and it is easy to reach for the wrong one: the
  // agent's own dT (2 K for the water agents) decides whether an agent is
  // eligible at all, while the class-level `HeatUtility.dT = 5` sets how close
  // the utility may come to the process in the exchanger. Using the agent's
  // value here would return cooling water at 318 K against a 320 K process
  // instead of 315 K, and understate the cost by a third.
  const achievedReturn = Math.min(agent.T_limit, T_process_in_K - MINIMUM_APPROACH_DT);
  const achievedRise = achievedReturn - agent.T;
  if (achievedRise <= 0) {
    throw new Error(
      `${agent.ID} supplies at ${agent.T} K and cannot cool a process entering at ${T_process_in_K} K — pick a colder agent`,
    );
  }
  return agent.energyPerKmol * (achievedRise / fullRise);
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
