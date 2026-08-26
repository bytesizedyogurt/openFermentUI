// Enumeration funnel (OF-BLD-005 §7) — how a research runbook narrows a
// candidate space, read back out of the stages it has already run.
//
// UNDER geneOS (OF-BLD-011 §7.4). Genus enumeration is a sequence-space search:
// it asks which proteins occupy the space a claim fences, which is the same
// question homology search and structure prediction ask with different tools.
// It sat in a flat `engine/` directory that said nothing about who owned it;
// the path now does. The file itself is unchanged — this is an ownership move,
// not a rewrite.
//
// The funnel is derived rather than authored, so it cannot drift from the
// stage list beside it. That makes the parsing rules load-bearing, and they
// are deliberately strict: a number is a candidate count only when the stage's
// own words say what it counts. "BL21(DE3)" contains a 21 and "50% glycerol"
// contains a 50; neither is a population, and a looser reader turns both into
// funnel steps and draws a chart out of nothing.
//
// Where a stage has produced no count the funnel says so rather than
// interpolating. An unquantified step is a real state — often the interesting
// one, because it is where the run stopped.
// LONG TERM this is the wrong shape. Parsing prose for populations is a
// heuristic dressed as a data model: it works on the stages written so far and
// will mis-read the first one phrased differently, and the failure is silent —
// a missed count just vanishes from the chart. The right fix is optional typed
// `inputCount` / `outputCount` fields on RunbookStage, authored alongside the
// prose, with this parser kept only as a fallback for stages that predate them.
// Deliberately not built here: it changes the stage fixture format, which is a
// separate change from the screens that read it.
import type { Runbook, RunbookStage } from '@/data/types';

export interface FunnelStep {
  stage: RunbookStage;
  count: number;
  /** What the number counts, in the stage's own noun. */
  unit: string;
}

export interface Funnel {
  /** Quantified stages, widest first — the narrowing itself. */
  steps: FunnelStep[];
  /**
   * Stages that have not produced a count: still queued, still running, or
   * halted. Listed in declaration order, because where a run stopped matters.
   */
  unquantified: RunbookStage[];
}

/**
 * Nouns that name a population of candidates. A number only becomes a funnel
 * step when one of these follows it, which is what keeps process parameters,
 * strain designations and percentages out of the chart.
 */
const POPULATION =
  '(sequences?|candidates?|orthologs?|homologs?|homologues?|variants?|configurations?|structures?|hits?|entries|entry|proteins?|enzymes?|famil(?:y|ies)|gener[a]?|genus)';

const A_OF_B = new RegExp(`(\\d[\\d,]*)\\s+of\\s+(\\d[\\d,]*)\\s+${POPULATION}`, 'i');
const PLAIN = new RegExp(`(\\d[\\d,]*)\\s+${POPULATION}`, 'i');

const toNumber = (s: string) => Number(s.replace(/,/g, ''));

/**
 * The count a stage produced, or null.
 *
 * "112 of 3,400 candidates unpublished" is read as 112: the 3,400 is what the
 * stage started from, and whichever stage produced that reports it itself.
 * Taking the larger number would make every narrowing stage look identical to
 * the one before it.
 */
function stageCount(text: string | null): { n: number; unit: string } | null {
  if (!text) return null;
  const pair = text.match(A_OF_B);
  if (pair) return { n: toNumber(pair[1]), unit: pair[3].toLowerCase() };
  const one = text.match(PLAIN);
  if (one) return { n: toNumber(one[1]), unit: one[2].toLowerCase() };
  return null;
}

/**
 * Sorted widest first rather than by stage order, because stage order is the
 * order the work was written down and a funnel is the order the space
 * narrowed. Retrieval reports 3,400 sequences and the novelty scan that ran
 * against them reports 112; listing them the other way round would draw a
 * funnel that widens.
 */
export function enumerationFunnel(runbook: Runbook): Funnel {
  const steps: FunnelStep[] = [];
  const unquantified: RunbookStage[] = [];
  for (const stage of runbook.stages) {
    const hit = stageCount(stage.value) ?? stageCount(stage.detail);
    if (hit) steps.push({ stage, count: hit.n, unit: hit.unit });
    else unquantified.push(stage);
  }
  steps.sort((a, b) => b.count - a.count);
  return { steps, unquantified };
}

/** Denominator every bar is drawn against. Zero when nothing is quantified. */
export function funnelWidest(funnel: Funnel): number {
  return funnel.steps.length > 0 ? funnel.steps[0].count : 0;
}

/**
 * One sentence describing the narrowing, or null when fewer than two stages
 * have produced a count. A funnel drawn from a single number is not a funnel,
 * and a sentence claiming otherwise is exactly the sort of confident nonsense
 * this platform exists to avoid.
 */
export function funnelSummary(funnel: Funnel): string | null {
  const { steps } = funnel;
  if (steps.length < 2) return null;
  const first = steps[0];
  const last = steps[steps.length - 1];
  if (first.count === last.count) return null;
  const share = last.count / first.count;
  const pct = (share * 100).toFixed(share < 0.1 ? 1 : 0);
  return `${first.count.toLocaleString()} ${first.unit} narrowed to ${last.count.toLocaleString()} — ${pct}% of the starting set survives the stages run so far.`;
}
