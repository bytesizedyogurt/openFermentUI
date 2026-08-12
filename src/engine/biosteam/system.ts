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
import { AREA_NAMES, massFlow, type CostSource, type Stream, type UnitResult } from './types';
import { costPower } from './utilities';

/** One row of bioSTEAM's `report.stream_table`. */
export interface StreamRow {
  ID: string;
  /** Unit that produced it, or null for a feed. */
  source: string | null;
  /** Unit that consumes it, or null for a product or waste stream. */
  sink: string | null;
  phase: 'l' | 'g' | 's';
  /** K. */
  T: number;
  /** Pa. */
  P: number;
  /** kg/hr. */
  massFlow: number;
  /** USD/kg. */
  price: number;
  /** Percent of total mass, per component. */
  composition: Record<string, number>;
  /** kg/hr, per component. */
  flow: Record<string, number>;
}

export interface FlowsheetNode {
  id: string;
  label: string;
  line?: string;
  kind: 'unit' | 'feed' | 'product' | 'waste';
  area: number;
  costSource?: CostSource;
  installedCost?: number;
  warnings?: number;
}

export interface FlowsheetEdge {
  from: string;
  to: string;
  label: string;
  kind: 'feed' | 'process' | 'product' | 'waste';
}

export interface FlowsheetGraph {
  nodes: FlowsheetNode[];
  edges: FlowsheetEdge[];
}

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

  /**
   * Resolve every unit's inlets from the declared graph, then run the train.
   *
   * Units are simulated in declaration order, which is process order in all
   * three flowsheets. There is no tearing and no recycle iteration: a loop
   * would need a convergence scheme, and a convergence scheme without a
   * property package would be arithmetic pretending to be thermodynamics. A
   * unit whose source has not run yet gets an empty stream and will size to
   * nothing, which is loud rather than subtle.
   */
  simulate(): void {
    const byId = new Map(this.units.map((u) => [u.ID, u]));
    for (const u of this.units) {
      u.ins = u.sources.map((src) => {
        if (src.kind === 'feed') return src.stream;
        const from = byId.get(src.from);
        if (!from) throw new Error(`${u.ID}: no unit '${src.from}' upstream of it`);
        const out = from.outs[src.port];
        if (!out) {
          throw new Error(
            `${u.ID}: unit '${src.from}' has no outlet ${src.port} — it produced ${from.outs.length}`,
          );
        }
        return out;
      });
      u.simulate();
    }
  }

  /**
   * Every stream in the flowsheet, with what made it and what consumes it.
   *
   * The columns are bioSTEAM's `report.stream_table`: source, sink, phase,
   * temperature, pressure, total flow, then the composition. Feeds have no
   * source and products no sink, which is how upstream marks them too.
   */
  streamTable(): StreamRow[] {
    const rows: StreamRow[] = [];
    const sinkOf = new Map<string, string>();
    for (const u of this.units) {
      for (const src of u.sources) {
        const id = src.kind === 'feed' ? src.stream.ID : `${src.from}#${src.port}`;
        sinkOf.set(id, u.ID);
      }
    }
    const push = (s: Stream, key: string, source: string | null): void => {
      const total = massFlow(s);
      rows.push({
        ID: s.ID,
        source,
        sink: sinkOf.get(key) ?? null,
        phase: s.phase ?? 'l',
        T: s.T,
        P: s.P,
        massFlow: total,
        price: s.price,
        composition: Object.fromEntries(
          Object.entries(s.flow)
            .filter(([, v]) => v > 0)
            .map(([k, v]) => [k, total > 0 ? (v / total) * 100 : 0]),
        ),
        flow: { ...s.flow },
      });
    };
    for (const f of this.feeds) push(f, f.ID, null);
    for (const u of this.units) {
      u.outs.forEach((o, i) => push(o, `${u.ID}#${i}`, u.ID));
    }
    return rows;
  }

  /** Nodes and edges for the flowsheet diagram, read off the same graph. */
  diagram(): FlowsheetGraph {
    const productIDs = new Set(this.products.map((p) => p.ID));
    const nodes: FlowsheetNode[] = [];
    const edges: FlowsheetEdge[] = [];
    const feedIDs = new Set(this.feeds.map((f) => f.ID));

    for (const f of this.feeds) {
      nodes.push({ id: `feed:${f.ID}`, label: f.ID, kind: 'feed', area: 0 });
    }
    for (const u of this.units) {
      nodes.push({
        id: u.ID,
        label: u.ID,
        line: u.line,
        kind: 'unit',
        area: u.area,
        costSource: u.costSource,
        installedCost: u.installedCost,
        warnings: u.warnings.length,
      });
    }
    for (const u of this.units) {
      u.sources.forEach((src, port) => {
        const stream = u.ins[port];
        const label = stream ? stream.ID : '';
        if (src.kind === 'feed') {
          edges.push({ from: `feed:${src.stream.ID}`, to: u.ID, label, kind: 'feed' });
        } else {
          edges.push({ from: src.from, to: u.ID, label, kind: 'process' });
        }
      });
    }
    // Terminal products, and any outlet nobody consumes — a purge or a waste
    // stream is still a stream, and hiding it would make the diagram lie about
    // where the mass went.
    const consumed = new Set(
      this.units.flatMap((u) =>
        u.sources.filter((s) => s.kind === 'unit').map((s) => `${(s as { from: string }).from}#${(s as { port: number }).port}`),
      ),
    );
    for (const u of this.units) {
      u.outs.forEach((o, i) => {
        if (consumed.has(`${u.ID}#${i}`)) return;
        const isProduct = productIDs.has(o.ID) || (!feedIDs.has(o.ID) && massFlow(o) > 0 && i === 0);
        const id = `out:${u.ID}#${i}`;
        nodes.push({
          id,
          label: o.ID,
          kind: isProduct ? 'product' : 'waste',
          area: 0,
        });
        edges.push({ from: u.ID, to: id, label: o.ID, kind: isProduct ? 'product' : 'waste' });
      });
    }
    return { nodes, edges };
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
