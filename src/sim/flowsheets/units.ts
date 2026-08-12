// The equipment this plant is made of.
//
// Each class is a BioUnit: run, design, cost, in that order. Where bioSTEAM
// publishes a correlation it is used and cited by file; where it does not, the
// correlation is written here and marked `authored`, because the difference
// between a number carrying Seider's authority and a number carrying ours is
// the whole argument of this application.
//
// The costing convention throughout: purchase costs are baseline, indexed to
// the current CE, and installation is a bare-module factor rather than a Lang
// factor — the same choice bioSTEAM makes by default.
import { BioUnit } from '@/engine/biosteam/unit';
import type { CostSource, Stream } from '@/engine/biosteam/types';
import { massFlow, volFlow } from '@/engine/biosteam/types';
import { CE } from '@/engine/biosteam/cepci';
import {
  MATERIAL_DENSITIES_LB_PER_FT3,
  PRESSURE_VESSEL_MATERIAL_FACTORS,
  checkVesselBounds,
  computeVesselWeightAndWallThickness,
  computeVerticalVesselPurchaseCost,
  computeVerticalVesselPlatformAndLaddersPurchaseCost,
} from '@/engine/biosteam/vessel';
import {
  MIX_TANK_ALGORITHMS,
  STORAGE_TANK_ALGORITHMS,
  computeNumberOfTanksAndPurchaseCost,
} from '@/engine/biosteam/tanks';
import { sizeBatch } from '@/engine/biosteam/batch';
import { C_O2_L, PAtKLaRiet, logMeanDrivingForce } from '@/engine/biosteam/aeration';

const FT_PER_M = 3.28084;
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

// ══ bioSTEAM-derived units ═════════════════════════════════════════════

/** Media preparation and hold. bioSTEAM `units/tank.py` MixTank. */
export class MixTank extends BioUnit {
  readonly line = 'Mix tank';
  readonly costSource: CostSource = 'biosteam';
  /** Residence time, hr. */
  tau: number;
  /** Working volume fraction. */
  V_wf = 0.8;
  /** bioSTEAM's MixTank default agitator power, kW/m³. */
  kW_per_m3 = 0.0985;

  constructor(ID: string, ins: Stream[], tau: number) {
    super(ID, ins);
    this.tau = tau;
    this.area = 100;
  }

  protected _run(): void {
    this.outs = this.ins.map((s) => ({ ...s, ID: `${this.ID}-out` }));
  }

  protected _design(): void {
    const F_vol = this.ins.reduce((t, s) => t + volFlow(s), 0);
    const V = (F_vol * this.tau) / this.V_wf;
    this.setDesign('Total volume', V, 'm^3');
  }

  protected _cost(): void {
    const V = this.designResults['Total volume'].value;
    const { N, Cp, warning } = computeNumberOfTanksAndPurchaseCost(
      V,
      MIX_TANK_ALGORITHMS.Conventional,
    );
    this.baselinePurchaseCosts['Tanks'] = Cp;
    this.parallel['Tanks'] = N;
    this.F_BM['Tanks'] = 1.8;
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

  constructor(ID: string, ins: Stream[], tauDays: number, area = 800) {
    super(ID, ins);
    this.tauDays = tauDays;
    this.area = area;
  }

  protected _run(): void {
    this.outs = this.ins.map((s) => ({ ...s, ID: `${this.ID}-out` }));
  }

  protected _design(): void {
    const F_vol = this.ins.reduce((t, s) => t + volFlow(s), 0);
    this.setDesign('Total volume', F_vol * this.tauDays * 24, 'm^3');
  }

  protected _cost(): void {
    const V = this.designResults['Total volume'].value;
    const { N, Cp, warning } = computeNumberOfTanksAndPurchaseCost(
      V,
      STORAGE_TANK_ALGORITHMS['Field erected'],
    );
    this.baselinePurchaseCosts['Tanks'] = Cp;
    this.parallel['Tanks'] = N;
    this.F_BM['Tanks'] = 1.7;
    if (warning) this.warnings.push(warning);
  }
}

/**
 * Shell-and-tube exchanger against a utility.
 *
 * Area from Q = U·A·ΔT_lm, cost from bioSTEAM's floating-head correlation in
 * `units/heat_exchange.py`. The overall coefficient is a heuristic rather than a
 * computed one, since computing it needs the property package this port does
 * not have; it is stated as a design result so it can be argued with.
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
  agent: string;

  constructor(
    ID: string,
    ins: Stream[],
    opts: { duty: number; agent: string; U?: number; dT_lm?: number; area?: number },
  ) {
    super(ID, ins);
    this.duty = opts.duty;
    this.agent = opts.agent;
    this.U = opts.U ?? 0.5;
    this.dT_lm = opts.dT_lm ?? 20;
    this.area = opts.area ?? 400;
  }

  protected _run(): void {
    this.outs = this.ins.map((s) => ({ ...s, ID: `${this.ID}-out` }));
  }

  protected _design(): void {
    // Q [kW] = U [kW/m²/K] · A [m²] · ΔT [K]
    const Q_kW = Math.abs(this.duty) / 3600;
    const A_m2 = Q_kW / (this.U * this.dT_lm);
    this.setDesign('Area', A_m2, 'm^2');
    this.setDesign('Overall coefficient', this.U, 'kW/m^2/K');
    this.setDesign('Log-mean driving force', this.dT_lm, 'K');
  }

  protected _cost(): void {
    const A_ft2 = this.designResults['Area'].value * FT_PER_M ** 2;
    // Upstream costs a single shell up to 5000 ft²; above that it splits.
    const N = Math.max(1, Math.ceil(A_ft2 / 5000));
    const A = Math.max(150, A_ft2 / N);
    const lnA = Math.log(A);
    const Cb = Math.exp(12.031 - 0.8709 * lnA + 0.09005 * lnA * lnA) * (CE.value / 567);
    this.baselinePurchaseCosts['Floating head'] = Cb;
    this.parallel['Floating head'] = N;
    this.F_BM['Floating head'] = 3.17;
    if (A_ft2 < 150) {
      this.warnings.push(
        `Heat-transfer area ${A_ft2.toPrecision(3)} ft² is below the 150 ft² floor of the floating-head correlation — costed at the floor.`,
      );
    }
    this.addHeatUtility(this.agent, this.duty, this.ins[0]?.T);
  }
}

/** Centrifugal pump. bioSTEAM `units/_pump.py`, base cost only. */
export class Pump extends BioUnit {
  readonly line = 'Pump';
  readonly costSource: CostSource = 'biosteam';
  /** Pressure rise, Pa. */
  dP: number;

  constructor(ID: string, ins: Stream[], dP = 2e5, area = 100) {
    super(ID, ins);
    this.dP = dP;
    this.area = area;
  }

  protected _run(): void {
    this.outs = this.ins.map((s) => ({ ...s, ID: `${this.ID}-out`, P: s.P + this.dP }));
  }

  protected _design(): void {
    const F_vol = this.ins.reduce((t, s) => t + volFlow(s), 0); // m³/hr
    const gpm = F_vol * 4.40287;
    const rho = this.ins[0]?.rho ?? 1000;
    const head_ft = (this.dP / (rho * 9.80665)) * FT_PER_M;
    this.setDesign('Flow rate', gpm, 'gal/min');
    this.setDesign('Head', head_ft, 'ft');
    // Hydraulic power over an assumed 70% efficiency.
    this.powerUtility += ((F_vol / 3600) * this.dP) / 0.7 / 1000;
    this.setDesign('Power', this.powerUtility, 'kW');
  }

  protected _cost(): void {
    const q = Math.max(50, this.designResults['Flow rate'].value);
    const h = Math.max(50, this.designResults['Head'].value);
    const S = q * Math.sqrt(h);
    const S_new = S > 400 ? S : 400;
    const lnS = Math.log(S_new);
    let Cb = Math.exp(12.1656 - 1.1448 * lnS + 0.0862 * lnS * lnS);
    Cb *= S / S_new;
    this.baselinePurchaseCosts['Pump'] = Cb * (CE.value / 567);
    this.F_BM['Pump'] = 3.3;
  }
}

/**
 * Disc-stack centrifuge. bioSTEAM `units/solids_separation.py` SolidsCentrifuge,
 * scroll-solid ('reciprocating pusher') branch.
 */
export class SolidsCentrifuge extends BioUnit {
  readonly line = 'Centrifuge';
  readonly costSource: CostSource = 'biosteam';
  /** Fraction of the solids that report to the cake. */
  solidsSplit: number;
  /** Fraction of the dissolved product that leaves with the cake — a loss. */
  productToCake: number;
  kWhr_per_m3 = 1.4;

  constructor(
    ID: string,
    ins: Stream[],
    opts: { solidsSplit: number; productToCake: number; area?: number },
  ) {
    super(ID, ins);
    this.solidsSplit = opts.solidsSplit;
    this.productToCake = opts.productToCake;
    this.area = opts.area ?? 400;
  }

  protected _run(): void {
    const feed = this.ins[0];
    const cake: Stream = { ...feed, ID: `${this.ID}-cake`, flow: {}, phase: 's' };
    const centrate: Stream = { ...feed, ID: `${this.ID}-centrate`, flow: {} };
    for (const k in feed.flow) {
      const f = feed.flow[k];
      const toCake =
        k === 'biomass' ? this.solidsSplit : k === 'product' ? this.productToCake : 0.05;
      cake.flow[k] = f * toCake;
      centrate.flow[k] = f * (1 - toCake);
    }
    this.outs = [centrate, cake];
  }

  protected _design(): void {
    const solids_kg_hr = this.ins.reduce((t, s) => t + (s.flow.biomass ?? 0), 0);
    // Upstream works in short tons per hour.
    const ts = solids_kg_hr * 0.0011023;
    this.setDesign('Solids loading', ts, 'ton/hr');
    this.setDesign('Number of centrifuges', Math.max(1, Math.ceil(ts / 40)), '');
    const F_vol = this.ins.reduce((t, s) => t + volFlow(s), 0);
    this.setDesign('Flow rate', F_vol, 'm^3/hr');
    this.powerUtility += F_vol * this.kWhr_per_m3;
  }

  protected _cost(): void {
    const ts = this.designResults['Solids loading'].value;
    // Reciprocating-pusher branch: 68040 · ts^0.5.
    const cost = 68040 * Math.sqrt(Math.max(ts, 1e-6)) * (CE.value / 567);
    this.baselinePurchaseCosts['Centrifuges'] = cost;
    this.parallel['Centrifuges'] = this.designResults['Number of centrifuges'].value;
    this.F_BM['Centrifuges'] = 2.03;
    if (ts < 2) {
      this.warnings.push(
        `Solids loading ${ts.toPrecision(3)} ton/hr is below the range bioSTEAM's centrifuge correlation was fitted over — the cost is an extrapolation downwards.`,
      );
    }
  }
}

/** Spray dryer. bioSTEAM `units/drying.py` SprayDryer. */
export class SprayDryer extends BioUnit {
  readonly line = 'Spray dryer';
  readonly costSource: CostSource = 'biosteam';
  /** Solids fraction of the dried product. */
  finalSolids = 0.95;

  constructor(ID: string, ins: Stream[]) {
    super(ID, ins);
    this.area = 600;
  }

  protected _run(): void {
    const feed = this.ins[0];
    const solids = (feed.flow.product ?? 0) + (feed.flow.biomass ?? 0);
    const dry: Stream = {
      ...feed,
      ID: `${this.ID}-powder`,
      phase: 's',
      flow: {
        ...feed.flow,
        water: (solids / this.finalSolids) * (1 - this.finalSolids),
      },
    };
    this.outs = [dry];
  }

  protected _design(): void {
    const feed = this.ins[0];
    const evaporated = Math.max(0, massFlow(feed) - massFlow(this.outs[0]));
    // Upstream's basis is lb/hr of evaporation.
    this.setDesign('Evaporation rate', evaporated * 2.20462, 'lb/hr');
    // Latent heat of water plus sensible heating of the feed to the dryer inlet.
    this.addHeatUtility('low_pressure_steam', evaporated * 2260 + massFlow(feed) * CP_BROTH * 60);
  }

  protected _cost(): void {
    const W = Math.max(30, this.designResults['Evaporation rate'].value);
    const logW = Math.log(W);
    const Cb = Math.exp(8.5133 + 0.9847 * logW - 0.0561 * logW * logW) * (CE.value / 567);
    this.baselinePurchaseCosts['Spray dryer'] = Cb;
    this.F_BM['Spray dryer'] = 2.06;
  }
}

/**
 * Aerated stirred-tank bioreactor.
 *
 * This is the unit the whole plant turns on, and the one place where a
 * fermentation TEA earns the right to be called one rather than a spreadsheet.
 * Three couplings are real here:
 *
 *  - the vessel is sized by `size_batch`, so cleaning and loading time buy
 *    volume rather than being absorbed into a fudge factor;
 *  - the agitator power comes from the oxygen the culture demands, inverted
 *    through van 't Riet's kLa correlation — so a denser culture is charged for
 *    the electricity it actually needs, not a fixed W/m³;
 *  - the cooling duty comes from the same oxygen uptake through the
 *    oxycalorific equivalent, which is why you cannot buy your way out of the
 *    aeration bill by chilling harder.
 *
 * The vessel itself is designed and costed as an ASME pressure vessel from
 * bioSTEAM's `flash_vessel_design`, jacketed.
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
  U = 0.03;
  /** Oxygen uptake, mol O₂ per litre of broth per hour. */
  OUR: number;
  /** Broth temperature, K. */
  T: number;
  vesselMaterial = 'Stainless steel 304';

  constructor(
    ID: string,
    ins: Stream[],
    opts: {
      tau: number;
      tau_cleaning?: number;
      V_max?: number;
      OUR: number;
      T?: number;
      area?: number;
    },
  ) {
    super(ID, ins);
    this.tau = opts.tau;
    this.tau_cleaning = opts.tau_cleaning ?? 12;
    this.V_max = opts.V_max ?? 500;
    this.OUR = opts.OUR;
    this.T = opts.T ?? 303;
    this.area = opts.area ?? 300;
  }

  protected _run(): void {
    this.outs = this.ins.map((s) => ({ ...s, ID: `${this.ID}-broth`, T: this.T }));
  }

  protected _design(): void {
    const F_vol = this.ins.reduce((t, s) => t + volFlow(s), 0); // m³/hr
    const batch = sizeBatch(F_vol, this.tau, this.tau_cleaning, this.V_wf, {
      V_max: this.V_max,
    });
    this.setDesign('Reactor volume', batch.reactorVolume, 'm^3');
    this.setDesign('Batch time', batch.batchTime, 'hr');
    this.setDesign('Loading time', batch.loadingTime, 'hr');
    this.setDesign('Number of reactors', batch.nReactors, '');

    // Geometry: a 2:1 vertical vessel, which is the usual aspect ratio for a
    // stirred fermenter and the one the kLa correlations were fitted on.
    const V = batch.reactorVolume;
    const D_m = Math.cbrt((2 * V) / Math.PI); // V = π/4 · D² · L with L = 2D
    const L_m = 2 * D_m;
    this.setDesign('Diameter', D_m, 'm');
    this.setDesign('Length', L_m, 'm');

    // Oxygen demand -> required kLa -> gassed power.
    //
    // The driving force is the number this whole calculation pivots on, and it
    // is worth taking seriously rather than assuming. Saturation comes from the
    // ported Henry's law rather than a remembered "0.21 mol/m³ in air": at the
    // pressure a real fermenter runs at, that figure is 17% low, and because
    // power goes as kLa^(1/b) with b = 0.6, a 17% error in the driving force is
    // a 30% error in the electricity bill.
    //
    // Two things raise it above the textbook air-water value. The headspace is
    // held at a slight overpressure for sterility, and the liquid is twelve
    // metres deep, so the sparger sees roughly twice the partial pressure the
    // surface does. Averaging the two logarithmically is the same correction a
    // counter-current exchanger gets, and it is what the ported
    // `log_mean_driving_force` is for.
    const workingV_m3 = V * this.V_wf;
    const workingV_L = workingV_m3 * 1000;
    const OTR_mol_hr = this.OUR * workingV_L; // mol O₂/hr per vessel

    const P_head = 1.3e5; // Pa absolute, sterile overpressure
    const liquidHeight_m = L_m * this.V_wf;
    const P_sparger = P_head + 1000 * 9.80665 * liquidHeight_m;
    const Y_O2 = 0.21; // air, and gas-phase depletion up the column is not modelled
    // C_O2_L returns kmol/m³; the rest of this works in mol/m³.
    const C_sat_top = C_O2_L(this.T, Y_O2 * P_head) * 1000;
    const C_sat_bottom = C_O2_L(this.T, Y_O2 * P_sparger) * 1000;
    // Held at 20% of air saturation, the usual dissolved-oxygen setpoint.
    const C_dissolved = 0.2 * C_sat_top;
    const driving = logMeanDrivingForce(C_sat_top, C_sat_bottom, C_dissolved);
    this.setDesign('Oxygen driving force', driving, 'mol/m^3');
    const kLa = OTR_mol_hr / 3600 / (driving * workingV_m3); // 1/s
    this.setDesign('kLa', kLa, '1/s');
    const P_W = PAtKLaRiet(kLa, workingV_m3, this.U);
    const nReactors = batch.nReactors;
    this.powerUtility += (P_W / 1000) * nReactors;
    this.setDesign('Agitation power', P_W / 1000, 'kW');

    // Cooling: metabolic heat from the same oxygen uptake, plus the agitator's
    // shaft work, which all ends up in the broth.
    const metabolic_kJ_hr = OTR_mol_hr * HEAT_PER_MOL_O2;
    const shaft_kJ_hr = (P_W / 1000) * 3600;
    this.addHeatUtility('chilled_water', -(metabolic_kJ_hr + shaft_kJ_hr) * nReactors, this.T);

    // Air compression to sparge, at the superficial velocity assumed above.
    const area_m2 = (Math.PI / 4) * D_m * D_m;
    const Q_air_m3_s = this.U * area_m2;
    // Isothermal compression to 1.5 bar over 70% efficiency.
    const P_comp_kW = ((Q_air_m3_s * 101325 * Math.log(1.5)) / 0.7 / 1000) * nReactors;
    this.powerUtility += P_comp_kW;
    this.setDesign('Air compression power', P_comp_kW, 'kW');
  }

  protected _cost(): void {
    const D_ft = this.designResults['Diameter'].value * FT_PER_M;
    const L_ft = this.designResults['Length'].value * FT_PER_M;
    const N = this.designResults['Number of reactors'].value;
    const rho = MATERIAL_DENSITIES_LB_PER_FT3[this.vesselMaterial] ?? 499.4;
    // Sterile operation is run at a slight overpressure; 3 barg is the usual
    // design pressure for a vessel that also has to survive steam-in-place.
    const P_psia = (4 * 101325) * PSI_PER_PA;
    const { weight, thickness } = computeVesselWeightAndWallThickness(
      P_psia,
      D_ft,
      L_ft,
      rho,
      0.5, // jacket annulus, ft
    );
    this.setDesign('Weight', weight, 'lb');
    this.setDesign('Wall thickness', thickness, 'in');
    const F_M = PRESSURE_VESSEL_MATERIAL_FACTORS[this.vesselMaterial] ?? 1.7;
    this.baselinePurchaseCosts['Vertical pressure vessel (jacketed)'] =
      computeVerticalVesselPurchaseCost(weight) * F_M;
    this.parallel['Vertical pressure vessel (jacketed)'] = N;
    this.F_BM['Vertical pressure vessel (jacketed)'] = 4.16;
    this.baselinePurchaseCosts['Platform and ladders'] =
      computeVerticalVesselPlatformAndLaddersPurchaseCost(D_ft, L_ft);
    this.parallel['Platform and ladders'] = N;
    this.F_BM['Platform and ladders'] = 1;
    // Agitator, on bioSTEAM's stirred-tank basis of USD/kW installed.
    const agitator_kW = this.designResults['Agitation power'].value;
    this.baselinePurchaseCosts['Agitator'] = 3200 * Math.pow(Math.max(agitator_kW, 1), 0.72) * (CE.value / 567);
    this.parallel['Agitator'] = N;
    this.F_BM['Agitator'] = 1.5;

    // Upstream raises these from inside `PressureVessel._vertical_vessel_design`.
    // This port left them to the calling unit, which means a unit that forgets
    // to ask gets no warning at all — a silent extrapolation, which is the one
    // outcome worse than a loud one. Both bounds are asked here, in bioSTEAM's
    // own words.
    for (const w of [
      checkVesselBounds('Vertical vessel weight', weight),
      checkVesselBounds('Vertical vessel length', L_ft),
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
 * across two years. That anchors the order of magnitude and nothing finer. The
 * exponent is the six-tenths rule.
 *
 * The lighting term is the part that makes an algal route expensive and it is
 * modelled explicitly rather than folded into utilities, because a reader will
 * want to argue with it.
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
  T: number;

  constructor(
    ID: string,
    ins: Stream[],
    opts: { tau: number; lightingWPerM3?: number; T?: number },
  ) {
    super(ID, ins);
    this.tau = opts.tau;
    this.lightingWPerM3 = opts.lightingWPerM3 ?? 60;
    this.T = opts.T ?? 298;
    this.area = 300;
  }

  protected _run(): void {
    this.outs = this.ins.map((s) => ({ ...s, ID: `${this.ID}-broth`, T: this.T }));
  }

  protected _design(): void {
    const F_vol = this.ins.reduce((t, s) => t + volFlow(s), 0);
    const batch = sizeBatch(F_vol, this.tau, 24, this.V_wf, { V_max: this.V_max });
    this.setDesign('Reactor volume', batch.reactorVolume, 'm^3');
    this.setDesign('Batch time', batch.batchTime, 'hr');
    this.setDesign('Number of reactors', batch.nReactors, '');
    const totalV = batch.reactorVolume * batch.nReactors * this.V_wf;
    this.setDesign('Total culture volume', totalV, 'm^3');

    // Lighting, and the circulation that keeps cells moving through the light.
    const lighting_kW = (this.lightingWPerM3 * totalV) / 1000;
    this.powerUtility += lighting_kW;
    this.setDesign('Lighting load', lighting_kW, 'kW');
    const circulation_kW = 0.15 * totalV;
    this.powerUtility += circulation_kW;
    this.setDesign('Circulation power', circulation_kW, 'kW');

    // Nearly all the lighting energy lands in the culture as heat and has to
    // come back out; a closed tubular loop in daylight has no other exit.
    //
    // Chilled water, not cooling water. A cooling tower supplies at 305.4 K and
    // a Chlamydomonas culture is held at 298 K, so the tower loop cannot take
    // heat out of it at all — passing the process temperature into the utility
    // makes that pairing throw instead of quietly costing the impossible.
    this.addHeatUtility('chilled_water', -(lighting_kW + circulation_kW) * 3600, this.T);
  }

  protected _cost(): void {
    const totalV = this.designResults['Total culture volume'].value;
    // 9.5 MUSD at 120 m³, six-tenths.
    const Cp = 9.5e6 * Math.pow(totalV / 120, 0.6) * (CE.value / 567);
    this.baselinePurchaseCosts['Tubular loops'] = Cp;
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

  constructor(ID: string, ins: Stream[], releaseYield: number) {
    super(ID, ins);
    this.releaseYield = releaseYield;
    this.area = 400;
  }

  protected _run(): void {
    const feed = this.ins[0];
    this.outs = [
      {
        ...feed,
        ID: `${this.ID}-lysate`,
        flow: { ...feed.flow, product: (feed.flow.product ?? 0) * this.releaseYield },
      },
    ];
  }

  protected _design(): void {
    const m = this.ins.reduce((t, s) => t + massFlow(s), 0);
    this.setDesign('Throughput', m, 'kg/hr');
    const kW = (m * this.specificEnergy) / 3600;
    this.powerUtility += kW;
    this.setDesign('Pulse energy', kW, 'kW');
  }

  protected _cost(): void {
    const m = this.designResults['Throughput'].value;
    const Cp = 480000 * Math.pow(Math.max(m, 1) / 5000, 0.65) * (CE.value / 567);
    this.baselinePurchaseCosts['PEF skid'] = Cp;
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
 */
export class MembraneSkid extends BioUnit {
  readonly line = 'Membrane skid';
  readonly costSource: CostSource = 'authored';
  readonly costBasis =
    'Installed membrane area at a module price, with flux as the design variable. Vendor-class pricing, not a published correlation.';

  /** L per m² per hour. */
  flux: number;
  /** Fraction of the product retained. */
  productYield: number;
  /** USD per m² of installed membrane, module plus skid. */
  usdPerM2 = 850;
  label: string;
  /** Diavolumes, for a diafiltration step; drives water use and pumping. */
  diavolumes: number;

  constructor(
    ID: string,
    ins: Stream[],
    opts: {
      flux: number;
      productYield: number;
      label: string;
      diavolumes?: number;
      area?: number;
      usdPerM2?: number;
    },
  ) {
    super(ID, ins);
    this.flux = opts.flux;
    this.productYield = opts.productYield;
    this.label = opts.label;
    this.diavolumes = opts.diavolumes ?? 0;
    this.area = opts.area ?? 500;
    if (opts.usdPerM2) this.usdPerM2 = opts.usdPerM2;
  }

  protected _run(): void {
    const feed = this.ins[0];
    const retentate: Stream = {
      ...feed,
      ID: `${this.ID}-retentate`,
      flow: {},
    };
    for (const k in feed.flow) {
      retentate.flow[k] =
        k === 'product' ? feed.flow[k] * this.productYield : k === 'water' ? feed.flow[k] * 0.1 : feed.flow[k] * 0.2;
    }
    this.outs = [retentate];
  }

  protected _design(): void {
    const F_vol_L = this.ins.reduce((t, s) => t + volFlow(s), 0) * 1000; // L/hr
    const throughput = F_vol_L * (1 + this.diavolumes);
    const A = throughput / this.flux;
    this.setDesign('Membrane area', A, 'm^2');
    this.setDesign('Design flux', this.flux, 'L/m^2/hr');
    // Crossflow recirculation is the pumping cost, roughly 0.5 kW per m² of
    // installed area at typical crossflow velocities.
    this.powerUtility += A * 0.05;
  }

  protected _cost(): void {
    const A = this.designResults['Membrane area'].value;
    this.baselinePurchaseCosts[this.label] = A * this.usdPerM2 * (CE.value / 567);
    this.F_BM[this.label] = 2.1;
  }
}
