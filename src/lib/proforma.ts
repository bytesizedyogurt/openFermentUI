// The browser's side of Proforma's simulator (OF-BLD-014 §8.2).
//
// The simulator's status and the benchmark it reproduced. The service runs
// BioSTEAM and keeps the benchmark as an artifact; with it down this says so,
// and nothing stands in for a result (E.2). Shares lib/rag.ts's call.
import type {
  Artifact,
  CostLine,
  FlowsheetInfo,
  InputAssumption,
  ProformaGrid,
  ProformaRunResult,
  ProformaScenarioInfo,
  ResultGrid,
  Scenario,
  ScenarioInput,
} from '@/data/types';
import { RagDown, RagRefused, call } from './rag';

export { RagDown as ProformaDown, RagRefused as ProformaRefused };

export interface SimulatorStatus {
  status: 'cold' | 'starting' | 'ready' | 'failed';
  error: string | null;
}

/** The worker's status in words, for the status line beside every Run (OF-BLD-019 §3.1). */
export const SIMULATOR_SAYS: Record<SimulatorStatus['status'], string> = {
  cold: 'The simulator has not started on this service yet.',
  starting: 'The simulator is starting: importing BioSTEAM takes most of a minute.',
  ready: 'The simulator is warm.',
  failed: 'The simulator failed to start.',
};

export const proformaStatus = (signal?: AbortSignal) => call<SimulatorStatus>('/api/proforma/status', { signal });

// ── The shelf (OF-BLD-019 §2.1, D2) ─────────────────────────────────────

/**
 * The flowsheets a scenario can name, as `GET /api/proforma/shelf` serves
 * them. Archived programs' flowsheets come only when the switch is on; the
 * toy never comes.
 */
export const proformaShelf = (includeArchived: boolean, signal?: AbortSignal) =>
  call<FlowsheetInfo[]>(`/api/proforma/shelf${includeArchived ? '?includeArchived=true' : ''}`, { signal });

// ── Reference runs (OF-BLD-019 §2.2, D3) ────────────────────────────────

/** A reference biorefinery's newest stored run, or none, and the worker's status. */
export interface ReferenceResponse {
  artifact: Artifact | null;
  simulator: SimulatorStatus;
  /** What the service said when it answered that it holds no run, in its words. */
  note?: string | null;
}

/**
 * Whether the service has no such endpoint, rather than no such run: FastAPI's
 * own 404 or 405, the built app's static mount answering a path no /api route
 * holds (a 404 with no JSON body), or the service double's 404.
 */
const noEndpoint = (e: unknown) =>
  (e instanceof RagRefused && (e.status === 405 || (e.status === 404 && /^(Not Found|not part of the smoke double)$/.test(e.message)))) ||
  (e instanceof RagDown && /answered 40[45]\./.test(e.message));

/**
 * The newest stored run of a reference flowsheet. The corn stover benchmark
 * reads at `/api/proforma/benchmark`, which every service answers in this
 * shape (OF-BLD-014 §8.2; OF-BLD-019 §2.2 keeps it as it was), so no browser
 * asks a service for an endpoint it may not have; every other reference reads
 * at `GET /api/proforma/reference/{id}`. A service that predates that
 * endpoint says so in the card's note, and a 404 in words is a reference not
 * run yet.
 */
export async function proformaReference(id: string, signal?: AbortSignal): Promise<ReferenceResponse> {
  if (id === BENCHMARK_FLOWSHEET) return proformaBenchmark(signal);
  try {
    return await call<ReferenceResponse>(`/api/proforma/reference/${encodeURIComponent(id)}`, { signal });
  } catch (e) {
    if (noEndpoint(e)) {
      return { artifact: null, simulator: await proformaStatus(signal), note: `This service has no reference endpoint, so it cannot run ${id} yet.` };
    }
    // A 404 in words is the service saying it holds no run of this reference.
    if (e instanceof RagRefused && e.status === 404) return { artifact: null, simulator: await proformaStatus(signal), note: e.message };
    throw e;
  }
}

/** Run a reference flowsheet whole, on its package's defaults: `POST /api/proforma/reference/{id}`, the benchmark as above. */
export async function runProformaReference(id: string, signal?: AbortSignal): Promise<ReferenceResponse> {
  if (id === BENCHMARK_FLOWSHEET) return runProformaBenchmark(signal);
  try {
    return await call<ReferenceResponse>(`/api/proforma/reference/${encodeURIComponent(id)}`, { method: 'POST', signal });
  } catch (e) {
    if (!noEndpoint(e)) throw e;
    throw new RagRefused(404, `This service cannot run ${id} yet: it has no reference endpoint.`);
  }
}

/** One artifact the service keeps (`GET /api/biorepo/artifacts/{id}`). */
export const proformaArtifact = (id: string, signal?: AbortSignal) =>
  call<Artifact>(`/api/biorepo/artifacts/${encodeURIComponent(id)}`, { signal });

/** A price read from a run, with the words that say per what. */
export interface PriceRead {
  value: number;
  basis: string;
  /** The 5th and 95th percentiles when the run drew a distribution. */
  low: number | null;
  high: number | null;
  /** What the value is: the package's own price, or the median of the samples. */
  reads: string;
}

const num = (v: unknown): number | null => (typeof v === 'number' && Number.isFinite(v) ? v : null);

/**
 * A reference run's price: the output the shelf names as its price
 * (`priceOutput`, in `priceBasis`), else the solved price a run's tables
 * hold. Null when the run holds neither.
 */
export function referencePrice(info: FlowsheetInfo | null, art: Artifact): PriceRead | null {
  const o = art.output as Record<string, unknown>;
  const named = info?.priceOutput ? num(o[info.priceOutput]) : null;
  if (named != null) return { value: named, basis: info?.priceBasis ?? info?.priceOutput ?? '', low: null, high: null, reads: 'the price the package solves' };
  const tea = o.tea as { productPrice?: unknown } | null | undefined;
  const solved = num(tea?.productPrice) ?? num(o.basePrice);
  return solved == null ? null : { value: solved, basis: info?.priceBasis ?? 'USD per kg of product', low: null, high: null, reads: 'the price the package solves' };
}

/**
 * A scenario run's price (a `proforma.run` artifact, D1): the median of the
 * feasible samples with their 5th to 95th percentile, else the base case's
 * price. The basis is the run's flowsheet's, from the shelf.
 */
export function runPrice(art: Artifact, shelf: FlowsheetInfo[]): PriceRead | null {
  const o = art.output as Record<string, unknown>;
  const flowsheet = typeof o.flowsheet === 'string' ? o.flowsheet : null;
  const basis = shelf.find((f) => f.id === flowsheet)?.priceBasis ?? 'on the basis its flowsheet states';
  const q = (o.quantiles ?? {}) as Record<string, unknown>;
  const p50 = num(q.p50);
  if (p50 != null) return { value: p50, basis, low: num(q.p5), high: num(q.p95), reads: 'median of the samples that ran' };
  const base = num(o.basePrice);
  return base == null ? null : { value: base, basis, low: null, high: null, reads: 'the base case' };
}

/**
 * How a scenario's inputs stand, for its card on the index. With the
 * service's binding (`GET /api/proforma/scenarios`), an input is bound to
 * records, assumed, or waiting; for a scenario the service has not bound (one
 * made here), the shelf says which inputs bind to records when it runs.
 */
export interface InputCounts {
  total: number;
  /** Bound to records by the service, or, unbound yet, inputs that bind to records. */
  records: number;
  assumed: number;
  conventions: number;
  waiting: number;
  /** True when `records` counts what the service bound; false when it counts what will bind. */
  bound: boolean;
}

export function inputCounts(
  scenario: Scenario,
  info: ProformaScenarioInfo | null,
  shelf: FlowsheetInfo[],
  assumptions: InputAssumption[],
): InputCounts | null {
  const typed = new Set(assumptions.map((a) => a.key));
  if (info) {
    const c = { total: info.inputs.length, records: 0, assumed: 0, conventions: 0, waiting: 0, bound: true };
    for (const i of info.inputs) {
      if (i.binding === 'records') c.records++;
      else if (i.binding === 'assumption' || typed.has(i.key)) c.assumed++;
      else c.waiting++;
    }
    return c;
  }
  const flowsheet = shelf.find((f) => f.id === (scenario.flowsheetId ?? scenario.modelId));
  if (!flowsheet) return null;
  const c = { total: flowsheet.inputs.length, records: 0, assumed: 0, conventions: 0, waiting: 0, bound: false };
  for (const i of flowsheet.inputs) {
    if (i.fields.length > 0) c.records++;
    else if (i.kind === 'convention') c.conventions++;
    else if (typed.has(i.key)) c.assumed++;
    else c.waiting++;
  }
  return c;
}

/** The program a new scenario starts in: its flowsheet's, when that is offered, else the first offered. */
export function defaultProgram<T extends string>(flowsheet: FlowsheetInfo | null, offered: T[]): T | null {
  const own = flowsheet?.program as T | null | undefined;
  if (own && offered.includes(own)) return own;
  return offered[0] ?? null;
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

/** The shelf id of the corn stover benchmark (flowsheets/shelf.py). */
export const BENCHMARK_FLOWSHEET = 'cornstover_benchmark';

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
