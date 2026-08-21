// Archetype 5, carried to its end: the burger question as a programme of work.
//
// ── WHY THIS EXISTS ───────────────────────────────────────────────────────
//
// The decomposition tree restructures a question nobody can answer into six
// questions somebody could. That is where Archetype 5 stopped, and stopping
// there leaves the most quotable sentence in the demo unearned: a tree is a
// diagram, and a diagram is not a plan.
//
// This is the plan. Eight decisions, ordered, each naming the ONE measurement
// that would settle it and what a result would have to say to change the
// recommendation sitting on that branch today.
//
// ── WHAT "OPTIMAL" IS ALLOWED TO MEAN HERE ────────────────────────────────
//
// Not "the best burger". Nobody has an objective function over a burger, and a
// system that pretended to would be lying about the easiest thing to check.
// What is optimised is the ORDER: run first whatever most reduces uncertainty
// about the branch that dominates the outcome, per unit of cost and time. That
// is a real optimisation over a real quantity — expected information per
// pound-week — and the programme states its own objective at the top so a
// reader can disagree with it rather than having to infer it.
//
// `informationValue` and `cost` are stated per decision; `PROGRAMME_ORDER`
// derives the sequence from them rather than hardcoding it, so changing a cost
// reorders the runbook and a reviewer can watch it move.
//
// ── PROVENANCE ────────────────────────────────────────────────────────────
//
// Every decision names the Accessions that put it on the list, and every
// `wouldProduce` names the field the new measurement would land on. Nothing
// here carries a number that is not either an Accession or a stated cost of
// doing work. The three costs are estimates and are typed as such — a bench
// week and a pound figure are not measurements and must not wear the same
// tick as one.
import type { FieldId } from './types';

export type DecisionStatus = 'open' | 'leaning' | 'settled-enough';

export interface Decision {
  id: string;
  /** The tree node this settles. */
  nodeId: string;
  question: string;
  /** What the tree currently recommends, and how firmly. */
  standing: string;
  status: DecisionStatus;
  /** The single measurement that would settle it. */
  decisiveMeasurement: string;
  /**
   * What a result would have to SAY to flip the standing recommendation. A
   * decisive measurement without this is just a measurement.
   */
  flipsIf: string;
  /** Protocol in the Runbook this would be run under, where one exists. */
  protocolId?: string;
  /** The field a result would land on, as an Accession. */
  wouldProduce: FieldId;
  /** Accessions that put this decision on the list. */
  restsOn: string[];
  /**
   * Expected information, 0–1: how much of the outcome hangs on this branch
   * multiplied by how uncertain it currently is. An ESTIMATE, and typed as
   * one — it orders the programme and is not a measurement.
   */
  informationValue: number;
  /** Bench weeks, estimated. */
  weeks: number;
  /** Consumables and analysis, GBP, estimated. */
  costGBP: number;
  /** Decisions that must land first, because their answer changes this one. */
  blockedBy?: string[];
}

export interface DecisionProgramme {
  id: string;
  title: string;
  question: string;
  /** Stated so a reader can disagree with the ordering rather than infer it. */
  objective: string;
  /** What this programme cannot decide, however it runs. */
  outOfScope: string[];
  decisions: Decision[];
  /** Deliverable this came out of. */
  fromDeliverableId: string;
}

export const BURGER_PROGRAMME: DecisionProgramme = {
  id: 'RB-AR5-001',
  title: 'Burger indistinguishability — decision programme',
  question: 'I want to make a burger indistinguishable from beef.',
  objective:
    'Maximise expected information per bench-week per pound, discounted by how much uncertainty is left on each branch — measuring something you have already decided is the cheapest way to learn nothing. Not "make the best burger" — nobody holds an objective function over a burger, and a system that claimed one would be lying about the easiest thing to check. What is optimised is the ORDER: settle first whatever most reduces uncertainty about the branch that dominates the outcome. Change a cost below and the sequence changes with it.',
  outOfScope: [
    'Consumer preference. Indistinguishability is a discrimination test against a panel, and no panel result exists in this corpus. Every decision below is a precondition for running one, not a substitute.',
    'Regulatory clearance. The RNA-reduction step (D-310) exists because a nucleotide limit exists, but nothing here reads a dossier.',
    'Cost of goods at scale. That is Proforma’s, and it needs a flowsheet that does not exist until the fat phase is settled.',
  ],
  fromDeliverableId: 'DLV-AR5-001',
  decisions: [
    {
      id: 'D-100',
      nodeId: 'PN-100',
      question: 'Is the heme carrier route worth entering at all, given the claim position?',
      standing:
        'Avoid. Eight jurisdictions enclosed against one open, on a branch that carries the flavour and the colour together.',
      status: 'leaning',
      decisiveMeasurement:
        'Sensory discrimination between a globin-carried and a non-globin Maillard precursor system, at matched cook temperature.',
      flipsIf:
        'A trained panel cannot separate them above chance. Then the enclosed branch is worth nothing and PN-110 becomes the main line rather than the alternative.',
      wouldProduce: 'purity',
      restsOn: ['OF-A-00501', 'OF-A-00502', 'OF-A-00503', 'OF-A-00504'],
      informationValue: 0.92,
      weeks: 6,
      costGBP: 18000,
    },
    {
      id: 'D-110',
      nodeId: 'PN-110',
      question: 'Does the non-globin precursor system reach the same Maillard endpoint?',
      standing: 'Build. Low patent density, and it is the only open route to the same sensory outcome.',
      status: 'open',
      decisiveMeasurement:
        'Headspace GC-MS of the cooked patty at 68 °C, against a beef reference, on the sixteen markers that separate cooked beef from cooked plant protein.',
      flipsIf:
        'Fewer than twelve of sixteen markers land inside the beef envelope. Then no amount of process work closes the gap and the enclosed heme route is the only one that reaches the target.',
      protocolId: 'PR-PHOS-01',
      wouldProduce: 'purity',
      restsOn: ['OF-A-00504'],
      informationValue: 0.88,
      weeks: 4,
      costGBP: 11000,
      blockedBy: ['D-100'],
    },
    {
      id: 'D-200',
      nodeId: 'PN-200',
      question: 'Which structured fat phase holds its shape from fridge to griddle?',
      standing: 'Build. Open surface, and it is the branch the mouthfeel argument rests on entirely.',
      status: 'open',
      decisiveMeasurement:
        'Solid fat content by pNMR across 4–45 °C, with the drop-melt point read on the same sample.',
      flipsIf:
        'The candidate melts below 25 °C. Then it renders out during forming rather than during cooking, and the whole fat-phase branch restarts on a different lipid.',
      protocolId: 'PR-ACM-01',
      wouldProduce: 'temperature',
      restsOn: ['OF-A-00505', 'OF-A-00506', 'OF-A-00507', 'OF-A-00508'],
      informationValue: 0.95,
      weeks: 3,
      costGBP: 7500,
    },
    {
      id: 'D-210',
      nodeId: 'PN-210',
      question: 'Can the fat phase be produced where the plant is, at 26 °C ambient?',
      standing:
        'Build, with a siting constraint inherited from Archetype 3 rather than assumed here.',
      status: 'leaning',
      decisiveMeasurement:
        'Crystallisation hold trial at the ambient the Kigali plant actually sees, not at a controlled 20 °C.',
      flipsIf:
        'The phase will not set without active chilling. Then the fat step moves off-site and the import-displacement argument for making it locally goes with it.',
      wouldProduce: 'temperature',
      restsOn: ['OF-A-00507', 'OF-A-00325'],
      informationValue: 0.71,
      weeks: 2,
      costGBP: 4200,
      blockedBy: ['D-200'],
    },
    {
      id: 'D-300',
      nodeId: 'PN-300',
      question: 'Which route to the fibrous matrix — native morphology or claimed texturisation?',
      standing:
        'Build. The two reach an identical anisotropy index by different means, and one of them is enclosed.',
      status: 'open',
      decisiveMeasurement:
        'Anisotropy index by tensile ratio on both routes, cut from the same batch, measured blind.',
      flipsIf:
        'The native route lands below 3.0. Then the identical-outcome argument collapses and the claimed unit operation is the only way to the target — which turns a routing decision into a licensing one.',
      wouldProduce: 'purity',
      restsOn: ['OF-A-00509', 'OF-A-00511'],
      informationValue: 0.84,
      weeks: 5,
      costGBP: 14000,
    },
    {
      id: 'D-310',
      nodeId: 'PN-310',
      question: 'Does RNA reduction survive contact with the texturisation step?',
      standing:
        'Build. The unit operation is unclaimed and nobody has published it downstream of texturisation.',
      status: 'open',
      decisiveMeasurement:
        'Nucleotide content by HPLC before and after texturisation, on material that has already been RNA-reduced.',
      flipsIf:
        'Nucleotide content rises above the limit after texturisation. Then the order of operations is wrong and the whole downstream train reorders.',
      protocolId: 'PR-BCN-01',
      wouldProduce: 'purity',
      restsOn: ['OF-A-00512', 'OF-A-00510'],
      informationValue: 0.66,
      weeks: 4,
      costGBP: 9800,
      blockedBy: ['D-300'],
    },
    {
      id: 'D-400',
      nodeId: 'PN-400',
      question: 'Binding and cook-loss: license the incumbent system or route around it?',
      standing: 'License. Moderate density, and the incumbent works.',
      status: 'settled-enough',
      decisiveMeasurement:
        'Cook-loss by mass at 71 °C core, incumbent binder against two unencumbered alternatives.',
      flipsIf:
        'An unencumbered binder lands within two points of the incumbent. Then licensing buys nothing and the recommendation flips to build.',
      wouldProduce: 'yield_product_substrate',
      restsOn: [],
      informationValue: 0.34,
      weeks: 2,
      costGBP: 3600,
    },
    {
      id: 'D-000',
      nodeId: 'PN-000',
      question: 'Does the assembled patty pass a triangle test against beef?',
      standing:
        'Unanswerable today. It is the question that was asked, and it cannot be run until the branches above are settled.',
      status: 'open',
      decisiveMeasurement:
        'Triangle test, n = 60 untrained panellists, against a beef control at matched fat percentage.',
      flipsIf:
        'Nothing. This one does not flip a recommendation — it is the terminal measurement, and it is on the list so the programme ends where the question started rather than trailing off into sub-problems.',
      wouldProduce: 'purity',
      restsOn: [],
      informationValue: 1.0,
      weeks: 3,
      costGBP: 22000,
      blockedBy: ['D-110', 'D-210', 'D-300', 'D-310', 'D-400'],
    },
  ],
};

/**
 * The programme in the order it should be run.
 *
 * DERIVED, not authored. Decisions sort by information value per pound-week,
 * subject to their dependencies — a decision cannot be scheduled before
 * anything that would change its answer. Change a cost in the table above and
 * this reorders, which is the whole reason the costs are data rather than
 * prose.
 *
 * The dependency pass is a plain Kahn topological sort with the ratio as the
 * tie-break, so the result is stable and a reader can check it by hand.
 */
export function programmeOrder(p: DecisionProgramme = BURGER_PROGRAMME): Decision[] {
  const byId = new Map(p.decisions.map((d) => [d.id, d]));

  /**
   * How much uncertainty is left to remove.
   *
   * Information value is how much of the outcome hangs on a branch; it is not
   * how much is still UNKNOWN about it. Without this factor the ordering put
   * D-400 first — the cheapest decisive test, on the one branch already marked
   * settled enough — which is a real consequence of a ratio that had no term
   * for "we already know the answer". Measuring something you have decided is
   * the cheapest way to learn nothing.
   */
  const REMAINING: Record<DecisionStatus, number> = {
    open: 1,
    leaning: 0.7,
    'settled-enough': 0.3,
  };

  const ratio = (d: Decision) =>
    (d.informationValue * REMAINING[d.status]) / Math.max(0.1, d.weeks * (d.costGBP / 10000));
  const done = new Set<string>();
  const out: Decision[] = [];

  while (out.length < p.decisions.length) {
    const ready = p.decisions
      .filter((d) => !done.has(d.id) && (d.blockedBy ?? []).every((b) => done.has(b) || !byId.has(b)))
      .sort((a, b) => ratio(b) - ratio(a));
    if (!ready.length) {
      // A cycle. Emit the rest in declaration order rather than looping — a
      // programme that cannot be scheduled is a defect the screen should show,
      // not a hang.
      for (const d of p.decisions) if (!done.has(d.id)) out.push(d);
      break;
    }
    out.push(ready[0]);
    done.add(ready[0].id);
  }
  return out;
}

/**
 * The longest dependency chain, in weeks. Standard longest-path over a DAG,
 * memoised — the programme is small enough that clarity beats cleverness.
 */
export function criticalPath(p: DecisionProgramme = BURGER_PROGRAMME): number {
  const byId = new Map(p.decisions.map((d) => [d.id, d]));
  const memo = new Map<string, number>();
  const walk = (id: string, seen: Set<string>): number => {
    if (memo.has(id)) return memo.get(id)!;
    const d = byId.get(id);
    if (!d || seen.has(id)) return 0;
    const next = new Set(seen).add(id);
    const upstream = (d.blockedBy ?? []).filter((b) => byId.has(b));
    const longest = upstream.length ? Math.max(...upstream.map((b) => walk(b, next))) : 0;
    const total = longest + d.weeks;
    memo.set(id, total);
    return total;
  };
  return Math.max(...p.decisions.map((d) => walk(d.id, new Set())));
}

/** Totals, for the header. Estimates, and the screen says so. */
export function programmeTotals(p: DecisionProgramme = BURGER_PROGRAMME) {
  const order = programmeOrder(p);
  return {
    decisions: order.length,
    /** One bench, one decision at a time. */
    weeks: order.reduce((s, d) => s + d.weeks, 0),
    /**
     * Unlimited benches: the longest chain of dependencies.
     *
     * Computed rather than asserted. An earlier draft of the screen claimed
     * two benches saved five weeks, which was a guess — this is the actual
     * critical path, and the gap between it and the serial figure is what
     * parallelism is worth on this programme.
     */
    criticalPathWeeks: criticalPath(p),
    costGBP: order.reduce((s, d) => s + d.costGBP, 0),
    blocked: order.filter((d) => (d.blockedBy ?? []).length > 0).length,
  };
}
