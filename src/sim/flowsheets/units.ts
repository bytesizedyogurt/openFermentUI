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
// The equipment this plant is made of.
//
// Each class is a BioUnit: run, design, cost, in that order. Where bioSTEAM
// publishes a correlation it is used and cited by file; where it does not, the
// correlation is written here and marked `authored`, because the difference
// between a number carrying Seider's authority and a number carrying ours is
// the whole argument of this application.
//
// Every class also publishes `specs()` — the attributes you would set on the
// unit before simulating it upstream, spelled the way upstream spells them.
// Those are live: editing `tau` re-sizes the vessel, re-costs it, re-runs the
// cash flow and moves the selling price. A control that changed a label and
// nothing else would be worse than no control.
//
// The costing convention throughout: purchase costs are baseline, indexed to
// the current CE, and installation is a bare-module factor rather than a Lang
// factor — the same choice bioSTEAM makes by default.
import { BioUnit, type Inlet, type UnitSpec } from '@/engine/biosteam/unit';
import type { CostSource, Stream } from '@/engine/biosteam/types';
import { massFlow, volFlow } from '@/engine/biosteam/types';
import { CE } from '@/engine/biosteam/cepci';
import { applyReaction, type Reaction } from '@/engine/biosteam/reaction';
import {
  MATERIAL_DENSITIES_LB_PER_FT3,
  PRESSURE_VESSEL_MATERIAL_FACTORS,
  checkVesselBounds,
  computeVesselWeightAndWallThickness,
  computeHorizontalVesselPurchaseCost,
  computeHorizontalVesselPlatformAndLaddersPurchaseCost,
  computeVerticalVesselPurchaseCost,
  computeVerticalVesselPlatformAndLaddersPurchaseCost,
} from '@/engine/biosteam/vessel';
import {
  MIX_TANK_ALGORITHMS,
  STORAGE_TANK_ALGORITHMS,
  computeNumberOfTanksAndPurchaseCost,
} from '@/engine/biosteam/tanks';
import { sizeBatch } from '@/engine/biosteam/batch';
import {
  C_O2_L,
  KLA_COEFFICIENTS_RIET,
  PAtKLaRiet,
  logMeanDrivingForce,
} from '@/engine/biosteam/aeration';
import { COOLING_AGENTS, HEATING_AGENTS } from '@/engine/biosteam/utilities';

const FT_PER_M = 3.28084;

/**
 * Components a crossflow membrane holds back.
 *
 * Everything else is treated as a small solute that passes freely, which is the
 * right default for glycerol, acetate and lactose and the wrong one for
 * anything colloidal. The list is short because the component vocabulary is:
 * with no property package there is no molecular weight to decide this from, so
 * it is decided here and written down.
 */
const MEMBRANE_REJECTED = new Set(['biomass', 'protein', 'fat']);
const PSI_PER_PA = 1.450377e-4;

/** Water-like heat capacity, kJ/kg/K. Broth is mostly water and says so. */
export const CP_BROTH = 4.18;

/**
 * Heat released per mole of oxygen consumed, kJ/mol.
 *
 * The oxycalorific equivalent: aerobic growth on almost any substrate releases
 * close to this per mole of O₂, which is why oxygen uptake sets both the
 * aeration duty and the cooling duty of a fermenter and why the two cannot be
 * traded off against each other.
 */
export const HEAT_PER_MOL_O2 = 460;

/** Declare an inlet fed from outside the flowsheet. */
export function fromFeed(stream: Stream): Inlet {
  return { kind: 'feed', stream };
}

/** Declare an inlet taken from another unit's outlet. */
export function fromUnit(from: string, port = 0): Inlet {
  return { kind: 'unit', from, port };
}

/**
 * Copy a stream with a new identity, keeping the state costing depends on.
 *
 * Price is explicitly dropped. Spreading the inlet carried it forward, so every
 * internal stream in the plant inherited the media price and the stream table
 * cheerfully reported that the fermenter's carbon-dioxide vent was worth 55
 * cents a kilogram. Only what the plant buys and what it sells has a price;
 * everything in between is worth whatever the next unit does with it.
 */
function derive(
  s: Stream,
  ID: string,
  flow: Record<string, number>,
  over: Partial<Stream> = {},
): Stream {
  return { ...s, ID, flow, price: 0, ...over };
}

// ══ bioSTEAM-derived units ═════════════════════════════════════════════

/** Media preparation and hold. bioSTEAM `units/tank.py` MixTank. */
export class MixTank extends BioUnit {
  readonly line = 'Mix tank';
  readonly costSource: CostSource = 'biosteam';
  /** Residence time, hr. Upstream's `tau`. */
  tau: number;
  /** Working volume fraction. Upstream's `V_wf`. */
  V_wf = 0.8;
  /** bioSTEAM's MixTank default agitator power, kW/m³. */
  kW_per_m3 = 0.0985;

  constructor(ID: string, sources: Inlet[], tau: number) {
    super(ID, sources);
    this.tau = tau;
    this.area = 100;
  }

  specs(): UnitSpec[] {
    return [
      { key: 'tau', label: 'Residence time', biosteamName: 'tau', kind: 'number', value: this.tau, min: 0.5, max: 48, step: 0.5, units: 'hr', note: 'Hold-up time. Sets the tank volume directly.' },
      { key: 'V_wf', label: 'Working volume fraction', biosteamName: 'V_wf', kind: 'number', value: this.V_wf, min: 0.5, max: 1, step: 0.05, units: '', note: 'How full the tank runs. The vessel is grossed up by its inverse.' },
      { key: 'kW_per_m3', label: 'Agitator power', biosteamName: 'kW_per_m3', kind: 'number', value: this.kW_per_m3, min: 0, max: 2, step: 0.01, units: 'kW m⁻³', note: "bioSTEAM's MixTank default is 0.0985 kW/m³." },
    ];
  }

  protected _run(): void {
    const feed = this.ins[0];
    this.outs = [derive(feed, `${this.ID}-out`, { ...feed.flow })];
  }

  protected _design(): void {
    const F_vol = this.ins.reduce((t, s) => t + volFlow(s), 0);
    const V = (F_vol * this.tau) / this.V_wf;
    this.setDesign('Total volume', V, 'm^3');
  }

  protected _cost(): void {
    const V = this.designResults['Total volume'].value;
    const { N, Cp, warning } = computeNumberOfTanksAndPurchaseCost(V, MIX_TANK_ALGORITHMS.Conventional);
    this.baselinePurchaseCosts.Tanks = Cp;
    this.parallel.Tanks = N;
    this.F_BM.Tanks = 1.8;
    if (warning) this.warnings.push(warning);
    this.powerUtility += this.kW_per_m3 * V;
  }
}

/** Field-erected storage. bioSTEAM `units/tank.py` StorageTank. */
export class StorageTank extends BioUnit {
  readonly line = 'Storage tank';
  readonly costSource: CostSource = 'biosteam';
  /** Days of hold-up. */
  tauDays: number;
  /** Upstream's `vessel_type`, keyed into the storage cost algorithms. */
  vessel_type = 'Field erected';

  constructor(ID: string, sources: Inlet[], tauDays: number, area = 800) {
    super(ID, sources);
    this.tauDays = tauDays;
    this.area = area;
  }

  specs(): UnitSpec[] {
    return [
      { key: 'tauDays', label: 'Days of storage', biosteamName: 'tau', kind: 'number', value: this.tauDays, min: 0.5, max: 30, step: 0.5, units: 'd', note: 'Hold-up in days. Upstream states tau in hours; days read better at this scale.' },
      {
        key: 'vessel_type',
        label: 'Vessel type',
        biosteamName: 'vessel_type',
        kind: 'select',
        value: this.vessel_type,
        options: Object.keys(STORAGE_TANK_ALGORITHMS).map((k) => ({ value: k, label: k })),
        units: '',
        note: 'Selects the purchase-cost algorithm. Each carries its own validity range, published index and construction material.',
      },
    ];
  }

  protected _run(): void {
    const feed = this.ins[0];
    this.outs = [derive(feed, `${this.ID}-out`, { ...feed.flow })];
  }

  protected _design(): void {
    const F_vol = this.ins.reduce((t, s) => t + volFlow(s), 0);
    this.setDesign('Total volume', F_vol * this.tauDays * 24, 'm^3');
  }

  protected _cost(): void {
    const V = this.designResults['Total volume'].value;
    const algo = STORAGE_TANK_ALGORITHMS[this.vessel_type] ?? STORAGE_TANK_ALGORITHMS['Field erected'];
    const { N, Cp, warning } = computeNumberOfTanksAndPurchaseCost(V, algo);
    this.baselinePurchaseCosts[this.vessel_type] = Cp;
    this.parallel[this.vessel_type] = N;
    this.F_BM[this.vessel_type] = 1.7;
    if (warning) this.warnings.push(warning);
  }
}

/**
 * The five exchanger correlations bioSTEAM ships, in `units/heat_exchange.py`.
 * Area in ft², all indexed CE/567, all Seider via bioSTEAM.
 */
const HX_CORRELATIONS: Record<string, { f: (A: number) => number; BM: number }> = {
  'Floating head': { f: (A) => Math.exp(12.031 - 0.8709 * Math.log(A) + 0.09005 * Math.log(A) ** 2), BM: 3.17 },
  'Fixed head': { f: (A) => Math.exp(11.4185 - 0.9228 * Math.log(A) + 0.09861 * Math.log(A) ** 2), BM: 3.17 },
  'U tube': { f: (A) => Math.exp(11.551 - 0.9186 * Math.log(A) + 0.0979 * Math.log(A) ** 2), BM: 3.17 },
  'Kettle vaporizer': { f: (A) => Math.exp(12.331 - 0.8709 * Math.log(A) + 0.09005 * Math.log(A) ** 2), BM: 3.17 },
  'Double pipe': { f: (A) => Math.exp(7.2718 + 0.16 * Math.log(A)), BM: 1.8 },
};

/**
 * Shell-and-tube exchanger against a utility.
 *
 * Area from Q = U·A·ΔT_lm. The overall coefficient is a heuristic rather than a
 * computed one, since computing it needs the property package this port does
 * not have; it is a design result so it can be argued with.
 */
export class HXutility extends BioUnit {
  readonly line = 'Heat exchanger';
  readonly costSource: CostSource = 'biosteam';
  /** kJ/hr, signed: positive heats the process. */
  duty: number;
  /** kW/m²/K. */
  U: number;
  /** K. */
  dT_lm: number;
  /** Utility agent ID. Upstream picks it from the pinch; here it is stated. */
  agent: string;
  /** Upstream's `heat_exchanger_type`. */
  heat_exchanger_type = 'Floating head';
  /** Outlet temperature, K. */
  T_out: number;

  constructor(
    ID: string,
    sources: Inlet[],
    opts: { duty: number; agent: string; T_out: number; U?: number; dT_lm?: number; area?: number },
  ) {
    super(ID, sources);
    this.duty = opts.duty;
    this.agent = opts.agent;
    this.T_out = opts.T_out;
    this.U = opts.U ?? 0.5;
    this.dT_lm = opts.dT_lm ?? 20;
    this.area = opts.area ?? 400;
  }

  specs(): UnitSpec[] {
    return [
      {
        key: 'heat_exchanger_type',
        label: 'Exchanger type',
        biosteamName: 'heat_exchanger_type',
        kind: 'select',
        value: this.heat_exchanger_type,
        options: Object.keys(HX_CORRELATIONS).map((k) => ({ value: k, label: k })),
        units: '',
        note: 'Five correlations, and a double pipe carries a different bare-module factor as well as a different curve.',
      },
      { key: 'U', label: 'Overall coefficient', biosteamName: 'U', kind: 'number', value: this.U, min: 0.05, max: 3, step: 0.05, units: 'kW m⁻² K⁻¹', note: 'Heuristic. Computing it needs the property package this port does not have, so it is stated rather than derived.' },
      { key: 'dT_lm', label: 'Log-mean driving force', biosteamName: 'LMTD', kind: 'number', value: this.dT_lm, min: 2, max: 120, step: 1, units: 'K', note: 'Sets the area for a given duty. Halving it doubles the exchanger.' },
      {
        key: 'agent',
        label: 'Utility agent',
        biosteamName: 'agent',
        kind: 'select',
        value: this.agent,
        options: [...HEATING_AGENTS, ...COOLING_AGENTS].map((a) => ({ value: a.ID, label: a.ID.replace(/_/g, ' ') })),
        units: '',
        note: 'A cooling agent that cannot reach the process temperature refuses rather than quietly costing the impossible.',
      },
    ];
  }

  protected _run(): void {
    const feed = this.ins[0];
    this.outs = [derive(feed, `${this.ID}-out`, { ...feed.flow }, { T: this.T_out })];
  }

  protected _design(): void {
    const Q_kW = Math.abs(this.duty) / 3600;
    const A_m2 = Q_kW / (this.U * this.dT_lm);
    this.setDesign('Area', A_m2, 'm^2');
    this.setDesign('Duty', this.duty, 'kJ/hr');
    this.setDesign('Overall coefficient', this.U, 'kW/m^2/K');
    this.setDesign('Log-mean driving force', this.dT_lm, 'K');
  }

  protected _cost(): void {
    const A_ft2 = this.designResults.Area.value * FT_PER_M ** 2;
    const corr = HX_CORRELATIONS[this.heat_exchanger_type] ?? HX_CORRELATIONS['Floating head'];
    const N = Math.max(1, Math.ceil(A_ft2 / 5000));
    const A = Math.max(150, A_ft2 / N);
    this.baselinePurchaseCosts[this.heat_exchanger_type] = corr.f(A) * (CE.value / 567);
    this.parallel[this.heat_exchanger_type] = N;
    this.F_BM[this.heat_exchanger_type] = corr.BM;
    if (A_ft2 < 150) {
      this.warnings.push(
        `Heat-transfer area ${A_ft2.toPrecision(3)} ft² is below the 150 ft² floor of the ${this.heat_exchanger_type.toLowerCase()} correlation — costed at the floor.`,
      );
    }
    this.addHeatUtility(this.agent, this.duty, this.ins[0]?.T);
  }
}

/** Centrifugal pump. bioSTEAM `units/_pump.py`, base cost only. */
export class Pump extends BioUnit {
  readonly line = 'Pump';
  readonly costSource: CostSource = 'biosteam';
  /** Pressure rise, Pa. Upstream derives this from the sink's P. */
  dP: number;
  /** Shaft efficiency on the hydraulic power. */
  efficiency = 0.7;

  constructor(ID: string, sources: Inlet[], dP = 2e5, area = 100) {
    super(ID, sources);
    this.dP = dP;
    this.area = area;
  }

  specs(): UnitSpec[] {
    return [
      { key: 'dP', label: 'Pressure rise', biosteamName: 'dP', kind: 'number', value: this.dP, min: 5e4, max: 2e6, step: 5e4, units: 'Pa', note: 'Sets the head, which sets the size factor q·√h the cost correlation runs on.' },
      { key: 'efficiency', label: 'Pump efficiency', biosteamName: 'efficiency', kind: 'number', value: this.efficiency, min: 0.3, max: 0.9, step: 0.05, units: '', note: 'Hydraulic power over this is the shaft power the motor draws.' },
    ];
  }

  protected _run(): void {
    const feed = this.ins[0];
    this.outs = [derive(feed, `${this.ID}-out`, { ...feed.flow }, { P: feed.P + this.dP })];
  }

  protected _design(): void {
    const F_vol = this.ins.reduce((t, s) => t + volFlow(s), 0);
    const gpm = F_vol * 4.40287;
    const rho = this.ins[0]?.rho ?? 1000;
    const head_ft = (this.dP / (rho * 9.80665)) * FT_PER_M;
    this.setDesign('Flow rate', gpm, 'gal/min');
    this.setDesign('Head', head_ft, 'ft');
    this.powerUtility += ((F_vol / 3600) * this.dP) / this.efficiency / 1000;
    this.setDesign('Power', this.powerUtility, 'kW');
  }

  protected _cost(): void {
    const q = Math.max(50, this.designResults['Flow rate'].value);
    const h = Math.max(50, this.designResults.Head.value);
    const S = q * Math.sqrt(h);
    const S_new = S > 400 ? S : 400;
    const lnS = Math.log(S_new);
    const Cb = Math.exp(12.1656 - 1.1448 * lnS + 0.0862 * lnS * lnS) * (S / S_new);
    this.baselinePurchaseCosts.Pump = Cb * (CE.value / 567);
    this.F_BM.Pump = 3.3;
  }
}

/**
 * Solid-bowl centrifuge. bioSTEAM `units/solids_separation.py` SolidsCentrifuge.
 *
 * Two outlets, as upstream: centrate at port 0, cake at port 1. Which one is the
 * product depends on the process — the yeast route keeps the centrate, the algal
 * route keeps the cake — and the flowsheet says which by what it connects.
 */
export class SolidsCentrifuge extends BioUnit {
  readonly line = 'Centrifuge';
  readonly costSource: CostSource = 'biosteam';
  /** Fraction of the solids reporting to the cake. Upstream's `split`. */
  split: number;
  /** Fraction of the dissolved product carried with the cake. */
  productToCake: number;
  /** Upstream's `kWhr_per_m3`. */
  kWhr_per_m3 = 1.4;
  /** Upstream's `centrifuge_type`. */
  centrifuge_type = 'reciprocating pusher';
  /** Water retained in the cake, kg per kg of solids. */
  cakeMoisture = 4;

  constructor(
    ID: string,
    sources: Inlet[],
    opts: { split: number; productToCake: number; area?: number; cakeMoisture?: number },
  ) {
    super(ID, sources);
    this.split = opts.split;
    this.productToCake = opts.productToCake;
    if (opts.cakeMoisture !== undefined) this.cakeMoisture = opts.cakeMoisture;
    this.area = opts.area ?? 400;
  }

  specs(): UnitSpec[] {
    return [
      { key: 'split', label: 'Solids to cake', biosteamName: 'split', kind: 'number', value: this.split, min: 0.5, max: 0.999, step: 0.005, units: '', note: 'Separation efficiency on the solid phase.' },
      { key: 'productToCake', label: 'Product lost to cake', biosteamName: 'split[product]', kind: 'number', value: this.productToCake, min: 0, max: 1, step: 0.01, units: '', note: 'Dissolved product carried out wet with the solids. A physical loss, not an adjustable one.' },
      {
        key: 'centrifuge_type',
        label: 'Centrifuge type',
        biosteamName: 'centrifuge_type',
        kind: 'select',
        value: this.centrifuge_type,
        options: [
          { value: 'reciprocating pusher', label: 'Reciprocating pusher' },
          { value: 'scroll solid bowl', label: 'Scroll solid bowl' },
        ],
        units: '',
        note: 'Two correlations on solids loading: 68 040·ts^0.5 against 170 100·ts^0.3. The scroll bowl is dearer at small scale and cheaper at large.',
      },
      { key: 'kWhr_per_m3', label: 'Specific energy', biosteamName: 'kWhr_per_m3', kind: 'number', value: this.kWhr_per_m3, min: 0.2, max: 5, step: 0.1, units: 'kWh m⁻³', note: "bioSTEAM's default is 1.4 kWh per m³ of feed." },
      { key: 'cakeMoisture', label: 'Cake moisture', biosteamName: 'moisture_content', kind: 'number', value: this.cakeMoisture, min: 0.5, max: 12, step: 0.5, units: 'kg kg⁻¹', note: 'Water carried out with the solids, per kilogram of solids. Wetter cake means more product lost with it.' },
    ];
  }

  protected _run(): void {
    const feed = this.ins[0];
    const cakeFlow: Record<string, number> = {};
    const centrateFlow: Record<string, number> = {};
    let solidsToCake = 0;
    for (const k in feed.flow) {
      if (k === 'water') continue;
      const f = feed.flow[k];
      const toCake = k === 'biomass' ? this.split : k === 'product' ? this.productToCake : 0.05;
      cakeFlow[k] = f * toCake;
      centrateFlow[k] = f * (1 - toCake);
      if (k === 'biomass') solidsToCake += f * toCake;
    }
    // Water follows the cake only as far as the cake is wet.
    const water = feed.flow.water ?? 0;
    const waterToCake = Math.min(water, solidsToCake * this.cakeMoisture);
    cakeFlow.water = waterToCake;
    centrateFlow.water = water - waterToCake;
    this.outs = [
      derive(feed, `${this.ID}-centrate`, centrateFlow),
      derive(feed, `${this.ID}-cake`, cakeFlow, { phase: 's' }),
    ];
  }

  protected _design(): void {
    const solids_kg_hr = this.ins.reduce((t, s) => t + (s.flow.biomass ?? 0), 0);
    const ts = solids_kg_hr * 0.0011023; // short tons/hr
    this.setDesign('Solids loading', ts, 'ton/hr');
    this.setDesign('Number of centrifuges', Math.max(1, Math.ceil(ts / 40)), '');
    const F_vol = this.ins.reduce((t, s) => t + volFlow(s), 0);
    this.setDesign('Flow rate', F_vol, 'm^3/hr');
    this.powerUtility += F_vol * this.kWhr_per_m3;
  }

  protected _cost(): void {
    const ts = Math.max(this.designResults['Solids loading'].value, 1e-6);
    const cost =
      this.centrifuge_type === 'scroll solid bowl'
        ? 170100 * Math.pow(ts, 0.3)
        : 68040 * Math.pow(ts, 0.5);
    this.baselinePurchaseCosts.Centrifuges = cost * (CE.value / 567);
    this.parallel.Centrifuges = this.designResults['Number of centrifuges'].value;
    this.F_BM.Centrifuges = 2.03;
    if (ts < 2) {
      this.warnings.push(
        `Solids loading ${ts.toPrecision(3)} ton/hr is below the range bioSTEAM's centrifuge correlation was fitted over — the cost is an extrapolation downwards.`,
      );
    }
  }
}

/** Spray dryer. bioSTEAM `units/drying.py` SprayDryer. Powder at 0, vapour at 1. */
export class SprayDryer extends BioUnit {
  readonly line = 'Spray dryer';
  readonly costSource: CostSource = 'biosteam';
  /** Solids fraction of the dried product. */
  finalSolids = 0.95;

  constructor(ID: string, sources: Inlet[]) {
    super(ID, sources);
    this.area = 600;
  }

  specs(): UnitSpec[] {
    return [
      { key: 'finalSolids', label: 'Final solids', biosteamName: 'moisture_content', kind: 'number', value: this.finalSolids, min: 0.8, max: 0.99, step: 0.01, units: '', note: 'Drier powder costs more steam and weighs less. Both move the price.' },
    ];
  }

  protected _run(): void {
    const feed = this.ins[0];
    const solids = Object.entries(feed.flow)
      .filter(([k]) => k !== 'water')
      .reduce((t, [, v]) => t + v, 0);
    const retainedWater = (solids / this.finalSolids) * (1 - this.finalSolids);
    const feedWater = feed.flow.water ?? 0;
    const evaporated = Math.max(0, feedWater - retainedWater);
    const powderFlow = { ...feed.flow, water: Math.min(feedWater, retainedWater) };
    this.outs = [
      derive(feed, `${this.ID}-powder`, powderFlow, { phase: 's' }),
      derive(feed, `${this.ID}-vapour`, { water: evaporated }, { phase: 'g', T: 373 }),
    ];
  }

  protected _design(): void {
    const evaporated = massFlow(this.outs[1]);
    this.setDesign('Evaporation rate', evaporated * 2.20462, 'lb/hr');
    this.addHeatUtility(
      'low_pressure_steam',
      evaporated * 2260 + massFlow(this.ins[0]) * CP_BROTH * 60,
      this.ins[0]?.T,
    );
  }

  protected _cost(): void {
    const W = Math.max(30, this.designResults['Evaporation rate'].value);
    const logW = Math.log(W);
    this.baselinePurchaseCosts['Spray dryer'] =
      Math.exp(8.5133 + 0.9847 * logW - 0.0561 * logW * logW) * (CE.value / 567);
    this.F_BM['Spray dryer'] = 2.06;
  }
}

/**
 * Aerated stirred-tank bioreactor.
 *
 * The unit the whole plant turns on, and the one place where a fermentation TEA
 * earns the right to be called one rather than a spreadsheet. Four couplings are
 * real here:
 *
 *  - a `Reaction` consumes substrate and makes biomass, product and carbon
 *    dioxide, so the mass balance closes and the vent carries what it should;
 *  - the vessel is sized by `size_batch`, so cleaning and loading time buy
 *    volume rather than being absorbed into a fudge factor;
 *  - the agitator power comes from the oxygen the culture demands, inverted
 *    through van 't Riet's kLa correlation against a driving force read from
 *    Henry's law at the sparger and at the surface;
 *  - the cooling duty comes from the same oxygen uptake through the
 *    oxycalorific equivalent, which is why you cannot buy your way out of the
 *    aeration bill by chilling harder.
 *
 * Broth leaves at port 0 and the vent at port 1.
 */
export class AeratedBioreactor extends BioUnit {
  readonly line = 'Bioreactor';
  readonly costSource: CostSource = 'biosteam';

  /** Reaction time, hr. */
  tau: number;
  /** Cleaning and turnaround, hr. */
  tau_cleaning: number;
  V_wf = 0.9;
  /** Largest single vessel, m³. */
  V_max: number;
  /** Superficial gas velocity, m/s. */
  U = 0.06;
  /** Oxygen uptake, mol O₂ per litre of broth per hour. */
  OUR: number;
  /** Broth temperature, K. */
  T: number;
  vessel_material = 'Stainless steel 304';
  vessel_type = 'Vertical';
  /** Design pressure, Pa absolute. */
  P_design = 4 * 101325;
  /** Which fitted kLa row to use. */
  kLa_correlation = 'Figueiredo & Calderbank';
  reaction: Reaction;

  constructor(
    ID: string,
    sources: Inlet[],
    opts: {
      tau: number;
      reaction: Reaction;
      OUR: number;
      tau_cleaning?: number;
      V_max?: number;
      T?: number;
      area?: number;
    },
  ) {
    super(ID, sources);
    this.tau = opts.tau;
    this.reaction = opts.reaction;
    this.OUR = opts.OUR;
    this.tau_cleaning = opts.tau_cleaning ?? 12;
    this.V_max = opts.V_max ?? 500;
    this.T = opts.T ?? 303;
    this.area = opts.area ?? 300;
  }

  specs(): UnitSpec[] {
    return [
      { key: 'tau', label: 'Reaction time', biosteamName: 'tau', kind: 'number', value: this.tau, min: 12, max: 240, step: 6, units: 'hr', note: 'Longer batches make more per turn and fewer turns per year. The vessel count follows.' },
      { key: 'tau_cleaning', label: 'Turnaround', biosteamName: 'tau_0', kind: 'number', value: this.tau_cleaning, min: 0, max: 48, step: 1, units: 'hr', note: 'Clean-in-place and unloading. Dead time you still pay vessel capital for.' },
      { key: 'V_wf', label: 'Working volume fraction', biosteamName: 'V_wf', kind: 'number', value: this.V_wf, min: 0.5, max: 0.95, step: 0.05, units: '', note: 'Headspace for foam. The vessel is grossed up by its inverse.' },
      { key: 'V_max', label: 'Largest vessel', biosteamName: 'V_max', kind: 'number', value: this.V_max, min: 20, max: 1000, step: 10, units: 'm³', note: 'Above this, size_batch adds vessels in parallel instead of growing one.' },
      { key: 'U', label: 'Superficial gas velocity', biosteamName: 'U', kind: 'number', value: this.U, min: 0.01, max: 0.15, step: 0.005, units: 'm s⁻¹', note: 'More sparge buys kLa cheaply until it floods the impeller. This model does not check for flooding.' },
      { key: 'T', label: 'Broth temperature', biosteamName: 'T', kind: 'number', value: this.T, min: 285, max: 320, step: 1, units: 'K', note: 'Sets oxygen solubility through Henry’s law and decides which cooling agent can serve the vessel.' },
      { key: 'X', label: 'Substrate conversion', biosteamName: 'reaction.X', kind: 'number', value: this.reaction.X, min: 0.1, max: 1, step: 0.01, units: '', note: 'Upstream’s Reaction.X. Unconverted substrate leaves in the broth and is paid for anyway.' },
      {
        key: 'vessel_material',
        label: 'Vessel material',
        biosteamName: 'vessel_material',
        kind: 'select',
        value: this.vessel_material,
        options: Object.entries(PRESSURE_VESSEL_MATERIAL_FACTORS)
          .filter(([m]) => MATERIAL_DENSITIES_LB_PER_FT3[m] !== undefined)
          .map(([m, f]) => ({ value: m, label: `${m} · F_M ${f}` })),
        units: '',
        note: 'The material factor multiplies the vessel cost and the density changes its weight. Only materials bioSTEAM gives a density for are offered.',
      },
      {
        key: 'vessel_type',
        label: 'Vessel orientation',
        biosteamName: 'vessel_type',
        kind: 'select',
        value: this.vessel_type,
        options: [
          { value: 'Vertical', label: 'Vertical' },
          { value: 'Horizontal', label: 'Horizontal' },
        ],
        units: '',
        note: 'Different weight correlation, different platform cost, different bare-module factor. A horizontal fermenter is unusual; the option is here because upstream has it.',
      },
      {
        key: 'kLa_correlation',
        label: 'kLa correlation',
        biosteamName: 'coefficients',
        kind: 'select',
        value: this.kLa_correlation,
        options: Object.keys(KLA_COEFFICIENTS_RIET).map((k) => ({ value: k, label: k })),
        units: '',
        note: 'Two fitted rows for the same equation. Inverting for power magnifies the gap between them, so this is a real assumption and not a detail.',
      },
    ];
  }

  /** `setSpec` has to reach inside the Reaction for X. */
  setSpec(key: string, value: number | string): boolean {
    if (key === 'X') {
      this.reaction = { ...this.reaction, X: Number(value) };
      return true;
    }
    return super.setSpec(key, value);
  }

  protected _run(): void {
    const feed = this.ins[0];
    const reacted = applyReaction(feed, this.reaction);
    const co2 = reacted.flow.co2 ?? 0;
    const brothFlow = { ...reacted.flow };
    delete brothFlow.co2;
    this.outs = [
      derive(feed, `${this.ID}-broth`, brothFlow, { T: this.T }),
      derive(feed, `${this.ID}-vent`, { co2 }, { phase: 'g', T: this.T }),
    ];
  }

  protected _design(): void {
    const F_vol = this.ins.reduce((t, s) => t + volFlow(s), 0);
    const batch = sizeBatch(F_vol, this.tau, this.tau_cleaning, this.V_wf, { V_max: this.V_max });
    this.setDesign('Reactor volume', batch.reactorVolume, 'm^3');
    this.setDesign('Batch time', batch.batchTime, 'hr');
    this.setDesign('Loading time', batch.loadingTime, 'hr');
    this.setDesign('Number of reactors', batch.nReactors, '');

    // A 2:1 vertical vessel, the usual aspect ratio for a stirred fermenter and
    // the one the kLa correlations were fitted on.
    const V = batch.reactorVolume;
    const D_m = Math.cbrt((2 * V) / Math.PI);
    const L_m = 2 * D_m;
    this.setDesign('Diameter', D_m, 'm');
    this.setDesign('Length', L_m, 'm');

    const workingV_m3 = V * this.V_wf;
    const OTR_mol_hr = this.OUR * workingV_m3 * 1000;
    this.setDesign('Oxygen uptake', OTR_mol_hr, 'mol/hr');

    // Saturation from Henry's law at the sparger and at the surface, log-mean
    // between them. The remembered "0.21 mol/m³ in air" is 17% low at the
    // pressure a real fermenter runs at, and power goes as kLa^(1/b).
    const P_head = 1.3e5;
    const liquidHeight_m = L_m * this.V_wf;
    const P_sparger = P_head + 1000 * 9.80665 * liquidHeight_m;
    const Y_O2 = 0.21;
    const C_sat_top = C_O2_L(this.T, Y_O2 * P_head) * 1000;
    const C_sat_bottom = C_O2_L(this.T, Y_O2 * P_sparger) * 1000;
    const C_dissolved = 0.2 * C_sat_top;
    const driving = logMeanDrivingForce(C_sat_top, C_sat_bottom, C_dissolved);
    this.setDesign('Oxygen driving force', driving, 'mol/m^3');

    const kLa = OTR_mol_hr / 3600 / (driving * workingV_m3);
    this.setDesign('kLa', kLa, '1/s');
    const P_W = PAtKLaRiet(kLa, workingV_m3, this.U, this.kLa_correlation);
    const nReactors = batch.nReactors;
    this.powerUtility += (P_W / 1000) * nReactors;
    this.setDesign('Agitation power', P_W / 1000, 'kW');

    const metabolic_kJ_hr = OTR_mol_hr * HEAT_PER_MOL_O2;
    const shaft_kJ_hr = (P_W / 1000) * 3600;
    this.addHeatUtility('chilled_water', -(metabolic_kJ_hr + shaft_kJ_hr) * nReactors, this.T);

    const area_m2 = (Math.PI / 4) * D_m * D_m;
    const Q_air_m3_s = this.U * area_m2;
    const P_comp_kW = ((Q_air_m3_s * 101325 * Math.log(1.5)) / 0.7 / 1000) * nReactors;
    this.powerUtility += P_comp_kW;
    this.setDesign('Air compression power', P_comp_kW, 'kW');
  }

  protected _cost(): void {
    const D_ft = this.designResults.Diameter.value * FT_PER_M;
    const L_ft = this.designResults.Length.value * FT_PER_M;
    const N = this.designResults['Number of reactors'].value;
    const rho = MATERIAL_DENSITIES_LB_PER_FT3[this.vessel_material] ?? 499.4;
    const P_psia = this.P_design * PSI_PER_PA;
    const horizontal = this.vessel_type === 'Horizontal';
    const { weight, thickness } = computeVesselWeightAndWallThickness(P_psia, D_ft, L_ft, rho, 0.5);
    this.setDesign('Weight', weight, 'lb');
    this.setDesign('Wall thickness', thickness, 'in');
    const F_M = PRESSURE_VESSEL_MATERIAL_FACTORS[this.vessel_material] ?? 1.7;
    const vesselKey = horizontal
      ? 'Horizontal pressure vessel (jacketed)'
      : 'Vertical pressure vessel (jacketed)';
    this.baselinePurchaseCosts[vesselKey] =
      (horizontal ? computeHorizontalVesselPurchaseCost(weight) : computeVerticalVesselPurchaseCost(weight)) *
      F_M;
    this.parallel[vesselKey] = N;
    this.F_BM[vesselKey] = horizontal ? 3.05 : 4.16;
    this.baselinePurchaseCosts['Platform and ladders'] = horizontal
      ? computeHorizontalVesselPlatformAndLaddersPurchaseCost(D_ft)
      : computeVerticalVesselPlatformAndLaddersPurchaseCost(D_ft, L_ft);
    this.parallel['Platform and ladders'] = N;
    this.F_BM['Platform and ladders'] = 1;

    const agitator_kW = this.designResults['Agitation power'].value;
    this.baselinePurchaseCosts.Agitator =
      3200 * Math.pow(Math.max(agitator_kW, 1), 0.72) * (CE.value / 567);
    this.parallel.Agitator = N;
    this.F_BM.Agitator = 1.5;

    // Upstream raises these from inside `PressureVessel._vessel_design`. This
    // port left them to the calling unit, which means a unit that forgets to ask
    // gets a silent extrapolation — the worse of the two failures.
    for (const w of [
      checkVesselBounds(horizontal ? 'Horizontal vessel weight' : 'Vertical vessel weight', weight),
      horizontal
        ? checkVesselBounds('Horizontal vessel diameter', D_ft)
        : checkVesselBounds('Vertical vessel length', L_ft),
    ]) {
      if (w) this.warnings.push(w);
    }
    if (P_psia < 14.68) {
      this.warnings.push(
        'Vessel designed below atmospheric pressure. The ASME vacuum codes are not implemented — wall thickness may be under-estimated and stiffening rings may be required.',
      );
    }
  }
}

// ══ Authored units — no bioSTEAM correlation exists ════════════════════

/**
 * Tubular photobioreactor.
 *
 * bioSTEAM has no photobioreactor and no published correlation to borrow, so
 * this one is written here and anchored on the only real operating plant in the
 * corpus: Acién's 3 m³ tubular installation, which reported 69 €/kg of biomass
 * across two years. That anchors the order of magnitude and nothing finer.
 */
export class Photobioreactor extends BioUnit {
  readonly line = 'Photobioreactor';
  readonly costSource: CostSource = 'authored';
  readonly costBasis =
    "Six-tenths scaling from Acién et al.'s 3 m³ tubular plant (record r-O4-1, 69 EUR/kg biomass over two years of operation). Order of magnitude only.";

  tau: number;
  V_wf = 0.9;
  V_max = 200;
  /** Photosynthetically active irradiance delivered, W per m³ of culture. */
  lightingWPerM3: number;
  /** Circulation power, kW per m³. */
  circulationKWPerM3 = 0.15;
  T: number;
  /** Reference capital, USD at the reference volume. */
  refCost = 9.5e6;
  refVolume = 120;
  scalingExponent = 0.6;
  reaction: Reaction;

  constructor(
    ID: string,
    sources: Inlet[],
    opts: { tau: number; reaction: Reaction; lightingWPerM3?: number; T?: number },
  ) {
    super(ID, sources);
    this.tau = opts.tau;
    this.reaction = opts.reaction;
    this.lightingWPerM3 = opts.lightingWPerM3 ?? 60;
    this.T = opts.T ?? 298;
    this.area = 300;
  }

  specs(): UnitSpec[] {
    return [
      { key: 'tau', label: 'Cultivation time', biosteamName: 'tau', kind: 'number', value: this.tau, min: 24, max: 480, step: 12, units: 'hr', note: 'Mixotrophic cultures reach maximum biomass in about five days.' },
      { key: 'V_max', label: 'Largest loop', biosteamName: 'V_max', kind: 'number', value: this.V_max, min: 20, max: 500, step: 10, units: 'm³', note: 'Tubular loops do not scale as single vessels; above this the plant adds loops.' },
      { key: 'lightingWPerM3', label: 'Light delivered', biosteamName: '—', kind: 'number', value: this.lightingWPerM3, min: 10, max: 200, step: 5, units: 'W m⁻³', note: 'Flat with depth, which flatters a dense culture: attenuation is not modelled.' },
      { key: 'circulationKWPerM3', label: 'Circulation power', biosteamName: '—', kind: 'number', value: this.circulationKWPerM3, min: 0.02, max: 1, step: 0.01, units: 'kW m⁻³', note: 'Keeps cells moving through the light. Ends up in the broth as heat.' },
      { key: 'refCost', label: 'Reference capital', biosteamName: '—', kind: 'number', value: this.refCost, min: 1e6, max: 3e7, step: 5e5, units: 'USD', note: 'Cost of the reference installation. The least defensible number on this screen, and the one that dominates the answer.' },
      { key: 'scalingExponent', label: 'Scaling exponent', biosteamName: 'n', kind: 'number', value: this.scalingExponent, min: 0.4, max: 1, step: 0.05, units: '', note: 'Six-tenths rule. At 1.0 there is no economy of scale at all.' },
      { key: 'X', label: 'Substrate conversion', biosteamName: 'reaction.X', kind: 'number', value: this.reaction.X, min: 0.1, max: 1, step: 0.01, units: '', note: 'Acetate consumed by the mixotrophic culture.' },
    ];
  }

  setSpec(key: string, value: number | string): boolean {
    if (key === 'X') {
      this.reaction = { ...this.reaction, X: Number(value) };
      return true;
    }
    return super.setSpec(key, value);
  }

  protected _run(): void {
    const feed = this.ins[0];
    const reacted = applyReaction(feed, this.reaction, 'o2');
    const o2 = reacted.flow.o2 ?? 0;
    const brothFlow = { ...reacted.flow };
    delete brothFlow.o2;
    this.outs = [
      derive(feed, `${this.ID}-broth`, brothFlow, { T: this.T }),
      derive(feed, `${this.ID}-vent`, { o2 }, { phase: 'g', T: this.T }),
    ];
  }

  protected _design(): void {
    const F_vol = this.ins.reduce((t, s) => t + volFlow(s), 0);
    const batch = sizeBatch(F_vol, this.tau, 24, this.V_wf, { V_max: this.V_max });
    this.setDesign('Reactor volume', batch.reactorVolume, 'm^3');
    this.setDesign('Batch time', batch.batchTime, 'hr');
    this.setDesign('Number of reactors', batch.nReactors, '');
    const totalV = batch.reactorVolume * batch.nReactors * this.V_wf;
    this.setDesign('Total culture volume', totalV, 'm^3');

    const lighting_kW = (this.lightingWPerM3 * totalV) / 1000;
    this.powerUtility += lighting_kW;
    this.setDesign('Lighting load', lighting_kW, 'kW');
    const circulation_kW = this.circulationKWPerM3 * totalV;
    this.powerUtility += circulation_kW;
    this.setDesign('Circulation power', circulation_kW, 'kW');

    // Chilled water, not cooling water. A cooling tower supplies at 305.4 K and
    // this culture is held at 298 K, so the tower loop cannot take heat out of
    // it at all — passing the process temperature makes that pairing throw.
    this.addHeatUtility('chilled_water', -(lighting_kW + circulation_kW) * 3600, this.T);
  }

  protected _cost(): void {
    const totalV = this.designResults['Total culture volume'].value;
    this.baselinePurchaseCosts['Tubular loops'] =
      this.refCost * Math.pow(totalV / this.refVolume, this.scalingExponent) * (CE.value / 567);
    this.F_BM['Tubular loops'] = 1.8;
  }
}

/**
 * Pulsed-electric-field cell disruption.
 *
 * Authored. The energy input is the load-bearing number and it is taken from
 * the specific energy the disruption literature reports for microalgae; the
 * capital is scaled off pilot skid pricing, which is the weakest number in this
 * plant and is labelled as such.
 */
export class PEFDisruption extends BioUnit {
  readonly line = 'PEF disruptor';
  readonly costSource: CostSource = 'authored';
  readonly costBasis =
    'Pilot-scale PEF skid pricing scaled on throughput. No published correlation; the capital here is the least defensible number in the plant.';

  /** Fraction of intracellular protein released. */
  releaseYield: number;
  /** Specific energy, kJ per kg of broth. */
  specificEnergy = 100;
  refCost = 480000;
  refThroughput = 5000;
  scalingExponent = 0.65;

  constructor(ID: string, sources: Inlet[], releaseYield: number) {
    super(ID, sources);
    this.releaseYield = releaseYield;
    this.area = 400;
  }

  specs(): UnitSpec[] {
    return [
      { key: 'releaseYield', label: 'Protein released', biosteamName: '—', kind: 'number', value: this.releaseYield, min: 0.02, max: 0.95, step: 0.01, units: '', note: 'The cell-wall-deficient chassis exists for this number: 31% against 11% for the walled wild type.' },
      { key: 'specificEnergy', label: 'Specific energy', biosteamName: '—', kind: 'number', value: this.specificEnergy, min: 10, max: 400, step: 10, units: 'kJ kg⁻¹', note: 'Pulse energy per kilogram of broth. Mild PEF is cheap; the penalty is in the release yield.' },
      { key: 'refCost', label: 'Reference skid cost', biosteamName: '—', kind: 'number', value: this.refCost, min: 1e5, max: 3e6, step: 2e4, units: 'USD', note: 'Vendor-class pricing at the reference throughput. Nothing published stands behind it.' },
    ];
  }

  protected _run(): void {
    const feed = this.ins[0];
    // Disruption releases protein from the cells; nothing leaves the stream, so
    // the mass balance is a pass-through and the yield shows up downstream as
    // how much product the clarifier can actually take away.
    this.outs = [
      derive(feed, `${this.ID}-lysate`, {
        ...feed.flow,
        product: (feed.flow.product ?? 0) * this.releaseYield,
        biomass: (feed.flow.biomass ?? 0) + (feed.flow.product ?? 0) * (1 - this.releaseYield),
      }),
    ];
  }

  protected _design(): void {
    const m = this.ins.reduce((t, s) => t + massFlow(s), 0);
    this.setDesign('Throughput', m, 'kg/hr');
    this.setDesign('Release yield', this.releaseYield, '');
    const kW = (m * this.specificEnergy) / 3600;
    this.powerUtility += kW;
    this.setDesign('Pulse energy', kW, 'kW');
  }

  protected _cost(): void {
    const m = this.designResults.Throughput.value;
    this.baselinePurchaseCosts['PEF skid'] =
      this.refCost * Math.pow(Math.max(m, 1) / this.refThroughput, this.scalingExponent) * (CE.value / 567);
    this.F_BM['PEF skid'] = 2.2;
  }
}

/**
 * Crossflow membrane skid — microfiltration, ultrafiltration or diafiltration.
 *
 * Authored. bioSTEAM ships no membrane unit, and this is the workhorse of every
 * protein recovery train, so it could not simply be left out. Area comes from a
 * design flux; capital comes from installed area at a module price. Both are
 * quoted openly rather than hidden inside a lumped "downstream" line.
 *
 * Retentate at port 0, permeate at port 1.
 */
export class MembraneSkid extends BioUnit {
  readonly line = 'Membrane skid';
  readonly costSource: CostSource = 'authored';
  readonly costBasis =
    'Installed membrane area at a module price, with flux as the design variable. Vendor-class pricing, not a published correlation.';

  /** L per m² per hour. */
  flux: number;
  /** Fraction of the product this step keeps. */
  productYield: number;
  /** USD per m² of installed membrane, module plus skid. */
  usdPerM2 = 850;
  label: string;
  /** Diavolumes, for a diafiltration step; drives water use and pumping. */
  diavolumes: number;
  /** Fraction of the water removed to permeate. */
  waterRemoval = 0.9;
  /**
   * Whether the product is retained or passes. An ultrafiltration keeps it in
   * the retentate; a cold microfiltration on milk pushes β-casein into the
   * permeate, which is the entire trick of that route.
   */
  productInRetentate = true;
  /** Crossflow recirculation power, kW per m². */
  kWPerM2 = 0.05;
  /** Fraction of a rejected macromolecule that stays in the retentate. */
  rejection = 0.99;

  constructor(
    ID: string,
    sources: Inlet[],
    opts: {
      flux: number;
      productYield: number;
      label: string;
      diavolumes?: number;
      area?: number;
      usdPerM2?: number;
      waterRemoval?: number;
      productInRetentate?: boolean;
    },
  ) {
    super(ID, sources);
    this.flux = opts.flux;
    this.productYield = opts.productYield;
    this.label = opts.label;
    this.diavolumes = opts.diavolumes ?? 0;
    this.area = opts.area ?? 500;
    if (opts.usdPerM2) this.usdPerM2 = opts.usdPerM2;
    if (opts.waterRemoval !== undefined) this.waterRemoval = opts.waterRemoval;
    if (opts.productInRetentate !== undefined) this.productInRetentate = opts.productInRetentate;
  }

  specs(): UnitSpec[] {
    return [
      { key: 'flux', label: 'Design flux', biosteamName: '—', kind: 'number', value: this.flux, min: 5, max: 120, step: 5, units: 'L m⁻² hr⁻¹', note: 'Halving the flux doubles the membrane area and the capital with it.' },
      { key: 'productYield', label: 'Product recovery', biosteamName: '—', kind: 'number', value: this.productYield, min: 0.3, max: 0.999, step: 0.005, units: '', note: 'Fraction of the product this step keeps.' },
      { key: 'diavolumes', label: 'Diavolumes', biosteamName: '—', kind: 'number', value: this.diavolumes, min: 0, max: 12, step: 1, units: '', note: 'Wash volumes for diafiltration. Each one is another pass through the membrane.' },
      { key: 'usdPerM2', label: 'Module price', biosteamName: '—', kind: 'number', value: this.usdPerM2, min: 200, max: 3000, step: 50, units: 'USD m⁻²', note: 'Installed module plus skid. Vendor-class, not published.' },
      { key: 'waterRemoval', label: 'Water to permeate', biosteamName: 'split', kind: 'number', value: this.waterRemoval, min: 0.1, max: 0.99, step: 0.01, units: '', note: 'How much of the water this step takes out, which sets how concentrated the retentate is.' },
      { key: 'rejection', label: 'Macromolecule rejection', biosteamName: 'split', kind: 'number', value: this.rejection, min: 0.8, max: 0.999, step: 0.005, units: '', note: 'How completely the membrane holds back biomass, fat and other proteins. What leaks through ends up in the powder and dilutes it.' },
    ];
  }

  protected _run(): void {
    const feed = this.ins[0];
    const retentate: Record<string, number> = {};
    const permeate: Record<string, number> = {};
    for (const k in feed.flow) {
      const f = feed.flow[k];
      retentate[k] = f * this.retention(k);
      permeate[k] = f - retentate[k];
    }
    this.outs = [
      derive(feed, `${this.ID}-retentate`, retentate),
      derive(feed, `${this.ID}-permeate`, permeate),
    ];
  }

  /**
   * What fraction of a component stays behind.
   *
   * Three behaviours, and getting them wrong is not a rounding error. A
   * macromolecule is rejected almost completely. A small solute — glycerol,
   * lactose, residual acetate — is not rejected at all, so it leaves in
   * proportion to the water that carries it, and diafiltration is precisely the
   * operation that washes it out: each diavolume is another pass, so retention
   * falls as 1/(1 + N). The product is whichever side the process puts it on.
   *
   * The first cut of this model gave every non-water component a flat 20%
   * retention. That made the yeast plant's powder about half unconverted
   * glycerol, and since the plant is priced on what it sells, it halved the
   * selling price. A mass balance that closes can still be wrong about where
   * the mass went.
   */
  private retention(component: string): number {
    if (component === 'product') {
      return this.productInRetentate ? this.productYield : 1 - this.productYield;
    }
    if (MEMBRANE_REJECTED.has(component)) return this.rejection;
    // Water is set by how far the step concentrates. A solute that the membrane
    // does not reject leaves with that water and is then washed further by each
    // diavolume — which is the entire reason diafiltration exists, and the
    // reason the diavolume control has to do something rather than only cost
    // pumping.
    if (component === 'water') return 1 - this.waterRemoval;
    return (1 - this.waterRemoval) / (1 + this.diavolumes);
  }

  protected _design(): void {
    const F_vol_L = this.ins.reduce((t, s) => t + volFlow(s), 0) * 1000;
    const throughput = F_vol_L * (1 + this.diavolumes);
    const A = throughput / this.flux;
    this.setDesign('Membrane area', A, 'm^2');
    this.setDesign('Design flux', this.flux, 'L/m^2/hr');
    this.setDesign('Diavolumes', this.diavolumes, '');
    this.powerUtility += A * this.kWPerM2;
  }

  protected _cost(): void {
    const A = this.designResults['Membrane area'].value;
    this.baselinePurchaseCosts[this.label] = A * this.usdPerM2 * (CE.value / 567);
    this.F_BM[this.label] = 2.1;
  }
}
