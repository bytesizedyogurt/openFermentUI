// A System: the set of units the TEA prices, plus the feeds it buys and the
// products it sells.
//
// Ported in spirit from BioSTEAM v2.53.11 `_system.py` and
// `process_tools/unit_group.py` (UIUC/NCSA licence; see NOTICE.md).
//
// Upstream a System is a directed graph solved to convergence, with recycle
// loops torn and iterated. Nothing here tears a recycle: the flowsheets in
// `src/sim/flowsheets` are feed-forward by construction, and a model that
// needed a recycle loop to close would need thermosteam to close it honestly.
// What survives the simplification is the part the TEA actually consumes —
// installed cost, utility demand, material cost — and the grouping by process
// area that makes a capital breakdown readable.
import type { BioUnit } from './unit';
import { AREA_NAMES, massFlow, type Stream, type UnitResult } from './types';
import { costPower } from './utilities';

export interface AreaSummary {
  area: number;
  name: string;
  installedCost: number;
  purchaseCost: number;
  powerKW: number;
  /** kJ/hr, heating only. */
  heatingDuty: number;
  /** kJ/hr, cooling only, reported positive. */
  coolingDuty: number;
  units: number;
}

export class BioSystem {
  ID: string;
  units: BioUnit[];
  feeds: Stream[];
  products: Stream[];
  /** hr/yr. */
  operatingHours: number;

  constructor(opts: {
    ID: string;
    units: BioUnit[];
    feeds: Stream[];
    products: Stream[];
    operatingHours: number;
  }) {
    this.ID = opts.ID;
    this.units = opts.units;
    this.feeds = opts.feeds;
    this.products = opts.products;
    this.operatingHours = opts.operatingHours;
  }

  simulate(): void {
    for (const u of this.units) u.simulate();
  }

  get purchaseCost(): number {
    return this.units.reduce((t, u) => t + u.purchaseCost, 0);
  }

  get installedEquipmentCost(): number {
    return this.units.reduce((t, u) => t + u.installedCost, 0);
  }

  /** USD/yr paid for feeds. */
  get materialCost(): number {
    return this.feeds.reduce((t, s) => t + s.price * massFlow(s), 0) * this.operatingHours;
  }

  /** USD/yr for electricity and heat-transfer agents. */
  get utilityCost(): number {
    return this.units.reduce((t, u) => t + u.utilityCostPerHr, 0) * this.operatingHours;
  }

  /** kW, net across the plant. */
  get powerConsumption(): number {
    return this.units.reduce((t, u) => t + u.powerUtility, 0);
  }

  get powerCost(): number {
    return costPower(this.powerConsumption) * this.operatingHours;
  }

  /** kJ/hr. */
  get heatingDuty(): number {
    return this.units.reduce(
      (t, u) => t + u.heatUtilities.filter((h) => h.duty > 0).reduce((s, h) => s + h.duty, 0),
      0,
    );
  }

  /** kJ/hr, reported positive. */
  get coolingDuty(): number {
    return this.units.reduce(
      (t, u) => t + u.heatUtilities.filter((h) => h.duty < 0).reduce((s, h) => s - h.duty, 0),
      0,
    );
  }

  /** kg/yr of the stream the TEA solves a price for. */
  annualProduction(streamID: string): number {
    const s = this.products.find((p) => p.ID === streamID);
    if (!s) throw new Error(`no product stream '${streamID}' in system ${this.ID}`);
    return massFlow(s) * this.operatingHours;
  }

  results(): UnitResult[] {
    return this.units.map((u) => u.results());
  }

  /** Capital and utility rolled up by process area — bioSTEAM's UnitGroup. */
  byArea(): AreaSummary[] {
    const m = new Map<number, AreaSummary>();
    for (const u of this.units) {
      let g = m.get(u.area);
      if (!g) {
        g = {
          area: u.area,
          name: AREA_NAMES[u.area] ?? `Area ${u.area}`,
          installedCost: 0,
          purchaseCost: 0,
          powerKW: 0,
          heatingDuty: 0,
          coolingDuty: 0,
          units: 0,
        };
        m.set(u.area, g);
      }
      g.installedCost += u.installedCost;
      g.purchaseCost += u.purchaseCost;
      g.powerKW += u.powerUtility;
      g.units += 1;
      for (const h of u.heatUtilities) {
        if (h.duty > 0) g.heatingDuty += h.duty;
        else g.coolingDuty -= h.duty;
      }
    }
    return [...m.values()].sort((a, b) => a.area - b.area);
  }

  /**
   * Installed cost split by whose correlation produced it.
   *
   * The headline number is only as good as its worst-attributed component, and
   * a plant whose capital is 70% authored correlation is a different claim from
   * one that is 95% Seider. The split is reported rather than averaged away.
   */
  costSourceSplit(): { biosteam: number; authored: number } {
    let biosteam = 0;
    let authored = 0;
    for (const u of this.units) {
      if (u.costSource === 'biosteam') biosteam += u.installedCost;
      else authored += u.installedCost;
    }
    return { biosteam, authored };
  }

  /** Every warning any unit raised, so the UI can refuse to hide them. */
  get warnings(): { ID: string; message: string }[] {
    return this.units.flatMap((u) => u.warnings.map((message) => ({ ID: u.ID, message })));
  }
}
