// The Unit base class and the @cost decorator's arithmetic.
//
// Ported from BioSTEAM v2.53.11 `_unit.py` and `units/decorators/_cost.py`
// (UIUC/NCSA licence; see NOTICE.md).
//
// bioSTEAM's `Unit` runs in three steps — `_run` (mass and energy balance),
// `_design` (size it), `_cost` (price it) — and that separation is worth
// keeping, because it is what lets a design result and a purchase cost be
// audited independently. A number that is wrong because the vessel is the wrong
// size is a different bug from a number that is wrong because the correlation
// was applied outside its bounds, and collapsing the two hides which one you
// have.
import { CE } from './cepci';
import {
  type CostSource,
  type DesignResults,
  type HeatUtilityDemand,
  type Stream,
  type UnitResult,
  AREA_NAMES,
} from './types';
import { costHeatUtility, costPower } from './utilities';

/**
 * An exponential cost item, the thing bioSTEAM's `@cost` decorator attaches.
 *
 *   Cp = N · cost · (S / S_ref / N)^n · (CE / CE_ref)
 *
 * with `f` replacing `cost · F^n` when the correlation is not a power law.
 */
export interface CostItem {
  /** Design result this scales on. */
  basis: string;
  units: string;
  /** Reference size. */
  S: number;
  /** Purchase cost at the reference size, USD, at index `CE`. */
  cost?: number;
  /** Scaling exponent. */
  n?: number;
  /** Non-power-law correlation, given the size ratio F. */
  f?: (F: number) => number;
  /** Cost index the correlation was published at. */
  CE: number;
  /** Bare-module factor. */
  BM: number;
  /** kW per reference size. */
  kW?: number;
  /** Lower bound of validity; sizes below are costed at the bound. */
  lb?: number;
  /** Upper bound; sizes above are split across ⌈S/ub⌉ parallel units. */
  ub?: number;
}

/**
 * An editable unit specification — one of the attributes you would set on a
 * bioSTEAM unit before simulating it.
 *
 * `biosteamName` is the attribute as upstream spells it, so a reader who knows
 * the library can see that the control labelled "Residence time" is `tau` and
 * behaves the way `tau` behaves. Every spec here is live: changing one re-sizes
 * and re-costs the plant and re-solves the cash flow. None of them is a display
 * that shrugs.
 */
export interface UnitSpec {
  key: string;
  label: string;
  /** The attribute name upstream, e.g. 'tau', 'V_wf', 'vessel_material'. */
  biosteamName: string;
  kind: 'number' | 'select';
  value: number | string;
  options?: { value: string; label: string }[];
  min?: number;
  max?: number;
  step?: number;
  units: string;
  /** What the attribute does upstream, in one sentence. */
  note: string;
}

/** Where a unit's inlet comes from. */
export type Inlet =
  | { kind: 'feed'; stream: Stream }
  | { kind: 'unit'; from: string; port: number };

export abstract class BioUnit {
  ID: string;
  area = 300;
  /**
   * Declared connectivity, resolved by the System at simulate time.
   *
   * Upstream a Unit holds its inlet Stream objects directly and the System
   * infers the graph from shared references. Declaring the graph instead means
   * the flowsheet diagram and the stream table are read off the same structure
   * that ran the mass balance, rather than drawn beside it — a diagram that can
   * disagree with the model is worse than no diagram.
   */
  sources: Inlet[] = [];
  ins: Stream[] = [];
  outs: Stream[] = [];
  /**
   * Override the default outlet names.
   *
   * Streams are named after the unit that made them, which is right for the
   * ninety per cent of a flowsheet nobody looks at twice and wrong for the one
   * stream the whole plant exists to produce. A stream table reading
   * "T801 product silo-out" where it should read "product" is a small thing that
   * makes the table feel machine-generated rather than read.
   */
  outIDs?: string[];

  designResults: DesignResults = {};
  baselinePurchaseCosts: Record<string, number> = {};
  F_BM: Record<string, number> = {};
  parallel: Record<string, number> = {};
  /** kW. */
  powerUtility = 0;
  heatUtilities: HeatUtilityDemand[] = [];
  warnings: string[] = [];

  /** Equipment class, upstream's `line`. */
  abstract readonly line: string;
  /** Whether the purchase-cost correlation is bioSTEAM's or ours. */
  abstract readonly costSource: CostSource;
  /** What an authored correlation is anchored on. Empty for bioSTEAM's own. */
  readonly costBasis: string = '';

  constructor(ID: string, sources: Inlet[] = []) {
    this.ID = ID;
    this.sources = sources;
  }

  /**
   * The attributes this unit exposes for editing. Override to publish them.
   *
   * Empty by default rather than throwing: a unit with nothing worth setting is
   * a legitimate unit, and forcing every subclass to declare an empty list
   * would just add noise.
   */
  specs(): UnitSpec[] {
    return [];
  }

  /** Apply an edited spec. Returns false when the key is not one of ours. */
  setSpec(key: string, value: number | string): boolean {
    const spec = this.specs().find((s) => s.key === key);
    if (!spec) return false;
    (this as unknown as Record<string, number | string>)[key] = value;
    return true;
  }

  /** Mass balance. Fills `outs`. */
  protected abstract _run(): void;
  /** Sizing. Fills `designResults`. */
  protected abstract _design(): void;
  /** Costing. Fills `baselinePurchaseCosts` and `F_BM`. */
  protected abstract _cost(): void;

  simulate(): void {
    this.designResults = {};
    this.baselinePurchaseCosts = {};
    this.F_BM = {};
    this.parallel = {};
    this.heatUtilities = [];
    this.powerUtility = 0;
    this.warnings = [];
    this._run();
    if (this.outIDs) {
      this.outs = this.outs.map((o, i) => (this.outIDs?.[i] ? { ...o, ID: this.outIDs[i] } : o));
    }
    this._design();
    this._cost();
  }

  protected setDesign(key: string, value: number, units: string): void {
    this.designResults[key] = { value, units };
  }

  /**
   * Apply a set of cost items, exactly as `_decorated_cost` does: bound the
   * size, split across parallel units above the upper bound, index to the
   * current CE, and accumulate electricity.
   */
  protected decoratedCost(items: Record<string, CostItem>): void {
    for (const name in items) {
      const x = items[name];
      const entry = this.designResults[x.basis];
      if (!entry) throw new Error(`${this.ID}: cost item '${name}' needs design result '${x.basis}'`);
      const I = CE.value / x.CE;
      let S = entry.value;
      let N = 1;
      if (x.lb !== undefined && S < x.lb) {
        this.warnings.push(
          `${name}: ${x.basis} ${S.toPrecision(3)} ${x.units} is below the correlation's lower bound of ${x.lb} — costed at the bound.`,
        );
        S = x.lb;
      } else if (x.ub !== undefined && S > x.ub) {
        N = Math.ceil(S / x.ub);
      }
      const q = S / x.S;
      const F = q / N;
      const unitCost = x.f ? x.f(F) : (x.cost ?? 0) * Math.pow(F, x.n ?? 0.6);
      this.baselinePurchaseCosts[name] = I * unitCost;
      this.parallel[name] = N;
      this.F_BM[name] = x.BM;
      if (x.kW) this.powerUtility += x.kW * q;
    }
  }

  /**
   * Add a heating (duty > 0) or cooling (duty < 0) demand in kJ/hr.
   *
   * `T_process_in` is the temperature of the stream being served. It is
   * optional in the signature and should not be: a cooling agent only achieves
   * its full temperature rise against a hot enough process, and omitting the
   * temperature quietly prices every duty at the most favourable case. Passing
   * it also makes an impossible pairing throw — cooling water supplied at 90 °F
   * cannot chill a culture held at 25 °C, and finding that out from an
   * exception is much better than finding it out from a plausible bill.
   */
  protected addHeatUtility(agent: string, duty: number, T_process_in?: number): void {
    if (!duty) return;
    this.heatUtilities.push({ agent, duty, cost: costHeatUtility(agent, duty, T_process_in) });
  }

  get purchaseCost(): number {
    let t = 0;
    for (const k in this.baselinePurchaseCosts) {
      t += this.baselinePurchaseCosts[k] * (this.parallel[k] ?? 1);
    }
    return t;
  }

  get installedCost(): number {
    let t = 0;
    for (const k in this.baselinePurchaseCosts) {
      t += this.baselinePurchaseCosts[k] * (this.parallel[k] ?? 1) * (this.F_BM[k] ?? 1);
    }
    return t;
  }

  get utilityCostPerHr(): number {
    let t = costPower(this.powerUtility);
    for (const h of this.heatUtilities) t += h.cost;
    return t;
  }

  results(): UnitResult {
    return {
      ID: this.ID,
      line: this.line,
      costSource: this.costSource,
      costBasis: this.costBasis,
      area: this.area,
      areaName: AREA_NAMES[this.area] ?? `Area ${this.area}`,
      design: this.designResults,
      purchaseCosts: { ...this.baselinePurchaseCosts },
      F_BM: { ...this.F_BM },
      parallel: { ...this.parallel },
      purchaseCost: this.purchaseCost,
      installedCost: this.installedCost,
      powerKW: this.powerUtility,
      heatUtilities: this.heatUtilities,
      utilityCostPerHr: this.utilityCostPerHr,
      warnings: this.warnings,
      specs: this.specs(),
    };
  }
}
