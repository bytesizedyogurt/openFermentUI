// The browser's side of Proforma's simulator (OF-BLD-014 §8.2).
//
// The simulator's status and the benchmark it reproduced. The service runs
// BioSTEAM and keeps the benchmark as an artifact; with it down this says so,
// and nothing stands in for a result (E.2). Shares lib/rag.ts's call.
import type { Artifact, CostLine, InputAssumption, ProformaGrid, ProformaRunResult, ProformaScenarioInfo, ResultGrid, ScenarioInput } from '@/data/types';
import { RagDown, RagRefused, call } from './rag';

export { RagDown as ProformaDown, RagRefused as ProformaRefused };

export interface SimulatorStatus {
  status: 'cold' | 'starting' | 'ready' | 'failed';
  error: string | null;
}

export interface BenchmarkResponse {
  artifact: Artifact | null;
  simulator: SimulatorStatus;
}

/** What the benchmark's artifact holds, as `flowsheets/cornstover_benchmark.py` writes it. */
export interface BenchmarkOutput {
  package: string;
  biosteam: string;
  mespUsdPerGal: number;
  mespUsdPerKg: number;
  settings: { rateOfReturn: number; operatingDays: number; incomeTax: number; startYear: number; endYear: number };
  references: string[];
}

export const proformaBenchmark = (signal?: AbortSignal) => call<BenchmarkResponse>('/api/proforma/benchmark', { signal });

export const runProformaBenchmark = (signal?: AbortSignal) =>
  call<BenchmarkResponse>('/api/proforma/benchmark', { method: 'POST', signal });

/** B.3: the price the package's defaults give for version 2.35.1, measured when this build was written. */
export const BENCHMARK_EXPECTED = { usdPerGal: 1.968, tolerance: 0.005, package: 'biorefineries.cornstover@2.35.1' };

// ── The BioSTEAM scenario (§8.4) ────────────────────────────────────────

export const proformaScenarios = (host: string | null, signal?: AbortSignal) =>
  call<ProformaScenarioInfo[]>(`/api/proforma/scenarios${host ? `?host=${encodeURIComponent(host)}` : ''}`, { signal });

export const runProformaScenario = (scenarioId: string, assumptions: InputAssumption[], host: string | null, signal?: AbortSignal) =>
  call<ProformaRunResult>('/api/proforma/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenarioId, assumptions, host, seed: 0 }),
    signal,
  });

/** The words for an infeasible sample's reason (flowsheets/pha_sugar_v0.REASONS). */
export const INFEASIBLE_WORDS: Record<string, string> = {
  carbon: 'left no sugar for respiration',
  oxygen: 'asked for more oxygen than the aerated tank transfers',
  balance: "left the fermenter's mass balance open",
  error: 'failed in the simulator',
};

const COST_LINES: CostLine[] = ['capex', 'media', 'utilities', 'labor', 'downstream', 'other'];

/**
 * The run's grid in the shape the sliders already read. A cell the
 * flowsheet could not hold is NaN, so an interpolation touching it is NaN
 * and the screen says the point is infeasible rather than show a number.
 */
export function asResultGrid(modelId: string, g: ProformaGrid): ResultGrid {
  const arr = (xs: (number | null)[]) => Float64Array.from(xs, (v) => (v == null ? Number.NaN : v));
  return {
    modelId,
    dims: g.dims,
    msp: arr(g.msp),
    costLines: Object.fromEntries(COST_LINES.map((l) => [l, arr(g.costLines[l] ?? [])])) as Record<CostLine, Float64Array>,
    sensitivity: [],
  };
}

/** The question a process modeller is asked about each input that rests on an assumption. */
export const QUESTION: Record<string, string> = {
  recovery:
    'What share of cell mass does a solids centrifuge recover from a PHA broth at this scale, and what does a second pass or a flocculant change?',
  sugarPrice:
    'What does a kilogram of fermentable sugar from this feedstock cost delivered to the fermenter, after pretreatment and hydrolysis?',
  sugarFeed: 'What plant size, in sugar fed per hour, is a sensible first commercial train for this product?',
  titre: 'What PHA titre at harvest is credible for a fed-batch on hydrolysate sugars in this host?',
  yield: 'What PHA yield on sugar holds at scale, and how far below the network ceiling does a real culture sit?',
  content: 'What PHA share of dry cell mass is reached at harvest without losing productivity?',
  productivity: 'What volumetric productivity holds across a full batch, including the growth phase?',
};

/**
 * The inputs that rest on an assumption, ordered by how strongly they move
 * the price in the latest run (|Spearman ρ|), each with its question; the
 * flowsheet's omissions follow. Inputs absent from a run keep input order.
 */
export function modellerQuestions(inputs: ScenarioInput[], run: ProformaRunResult | null): { key: string; label: string; rho: number | null; question: string }[] {
  const rho = new Map((run?.sensitivity ?? []).map((s) => [s.key, s.rho]));
  return inputs
    .filter((i) => i.binding === 'assumption' || i.binding === 'waiting')
    .map((i, n) => ({ key: i.key, label: i.label, rho: rho.get(i.key) ?? null, question: QUESTION[i.key] ?? `Where should ${i.label} come from?`, n }))
    // An input the run did not rank (held fixed, or no run yet) follows every ranked one.
    .sort((a, b) => (b.rho == null ? -1 : Math.abs(b.rho)) - (a.rho == null ? -1 : Math.abs(a.rho)) || a.n - b.n)
    .map(({ n: _n, ...q }) => q);
}

export function questionsText(scenario: ProformaScenarioInfo, run: ProformaRunResult | null): string {
  const qs = modellerQuestions(scenario.inputs, run);
  const lines = [
    `Questions for a process modeller: ${scenario.name} (${scenario.flowsheet})`,
    '',
    'Inputs that rest on an assumption, the strongest mover first:',
    ...qs.map((q, i) => `${i + 1}. ${q.label}${q.rho == null ? '' : ` (Spearman rho ${q.rho.toFixed(2)})`}: ${q.question}`),
    '',
    'What the flowsheet leaves out:',
    ...scenario.leavesOut.map((l) => `- ${l}`),
    '',
    `The price is ${scenario.priceBasis}.`,
  ];
  return lines.join('\n') + '\n';
}
