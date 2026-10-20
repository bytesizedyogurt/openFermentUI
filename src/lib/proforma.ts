// The browser's side of Proforma's simulator (OF-BLD-014 §8.2).
//
// The simulator's status and the benchmark it reproduced. The service runs
// BioSTEAM and keeps the benchmark as an artifact; with it down this says so,
// and nothing stands in for a result (E.2). Shares lib/rag.ts's call.
import type {
  Artifact,
  BasisInput,
  CeilingCheck,
  ComputedBasis,
  CostLine,
  FermosFitInfo,
  FlowsheetInfo,
  HistogramBin,
  InputAssumption,
  InputSensitivity,
  PackageRegression,
  ProformaGrid,
  ProformaRunRequest,
  ProformaRunResult,
  ProformaScenarioInfo,
  ProformaTables,
  Provenance,
  RegressionCheck,
  ResultGrid,
  Scenario,
  ScenarioInput,
  StreamRow,
  TeaBreakdown,
  UnitRow,
  UtilityDuties,
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

/**
 * A reference biorefinery's newest stored run, or none, and the worker's
 * status: `ProformaReference` as GET and POST /api/proforma/reference/{id}
 * answer it, with the shelf's entry and the package test's values, which a
 * service that predates that endpoint does not send.
 */
export interface ReferenceResponse {
  flowsheet?: FlowsheetInfo | null;
  artifact: Artifact | null;
  /** The package's own regression test, as the service read it from the installed file. */
  regression?: PackageRegression | null;
  simulator: SimulatorStatus;
  /** What the service said when it answered that it holds no run, in its words. */
  note?: string | null;
}

/** Where a reference biorefinery's page lives (OF-BLD-019 §3.3; 'reference' is reserved under /proforma). */
export const referencePath = (id: string) => `/proforma/reference/${encodeURIComponent(id)}`;

/**
 * Whether the service has no such endpoint, rather than no such run: FastAPI's
 * own 404 or 405, the built app's static mount answering a path no /api route
 * holds (a 404 with no JSON body), or the service double's 404.
 */
const noEndpoint = (e: unknown) =>
  (e instanceof RagRefused && (e.status === 405 || (e.status === 404 && /^(Not Found|not part of the smoke double)$/.test(e.message)))) ||
  (e instanceof RagDown && /answered 40[45]\./.test(e.message));

/**
 * The newest stored run of a reference flowsheet, its shelf entry and its
 * package test's values, at `GET /api/proforma/reference/{id}` (OF-BLD-019
 * §2.2), the corn stover benchmark included (§3.3): one artifact per
 * reference run, `proforma.reference`, with its tables and its checks. A
 * service that predates that endpoint says so in the note; for the benchmark
 * it still answers at `/api/proforma/benchmark` (OF-BLD-014 §8.2), which
 * keeps its price and no table. A 404 in words is the service saying the id
 * is not a reference it holds.
 */
export async function proformaReference(id: string, signal?: AbortSignal): Promise<ReferenceResponse> {
  try {
    return await call<ReferenceResponse>(`/api/proforma/reference/${encodeURIComponent(id)}`, { signal });
  } catch (e) {
    if (noEndpoint(e)) {
      if (id === BENCHMARK_FLOWSHEET) {
        const old = await proformaBenchmark(signal);
        return { ...old, note: 'This service keeps the benchmark at its old address, with its price and no table: the reference endpoint is newer than it.' };
      }
      return { artifact: null, simulator: await proformaStatus(signal), note: `This service has no reference endpoint, so it cannot run ${id} yet.` };
    }
    if (e instanceof RagRefused && e.status === 404) return { artifact: null, simulator: await proformaStatus(signal), note: e.message };
    throw e;
  }
}

/** Run a reference flowsheet whole, on its package's defaults: `POST /api/proforma/reference/{id}`. */
export async function runProformaReference(id: string, signal?: AbortSignal): Promise<ReferenceResponse> {
  try {
    return await call<ReferenceResponse>(`/api/proforma/reference/${encodeURIComponent(id)}`, { method: 'POST', signal });
  } catch (e) {
    if (!noEndpoint(e)) throw e;
    if (id === BENCHMARK_FLOWSHEET) return runProformaBenchmark(signal);
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
 * (`priceOutput`, in `priceBasis`), else the price a run's tables were read
 * at. Null when the run holds neither. How the price was had (the corn
 * stover plant solves its; the corn plant's is the package's own, set, and
 * its TEA solves the IRR at it) is the shelf's `priceBasis` to say; `reads`
 * claims nothing beyond where the number was read (OF-BLD-019 §2.R).
 */
export function referencePrice(info: FlowsheetInfo | null, art: Artifact): PriceRead | null {
  const o = art.output as Record<string, unknown>;
  const named = info?.priceOutput ? num(o[info.priceOutput]) : null;
  if (named != null) return { value: named, basis: info?.priceBasis ?? info?.priceOutput ?? '', low: null, high: null, reads: 'as the package\u2019s own run left it' };
  const tea = o.tea as { productPrice?: unknown } | null | undefined;
  const read = num(tea?.productPrice) ?? num(o.basePrice);
  return read == null ? null : { value: read, basis: info?.priceBasis ?? 'USD per kg of product', low: null, high: null, reads: 'the price the run\u2019s TEA was read at' };
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
 * service's binding (`GET /api/proforma/scenarios` for a seed scenario, `GET
 * /api/proforma/bind` for one made here, as its page asks), an input is
 * bound to records, assumed, or waiting; when the service could not be asked,
 * the shelf says which inputs can bind to records, and no more (OF-BLD-019
 * §2.R: the card once said four bound where the service bound three).
 */
export interface InputCounts {
  total: number;
  /** Bound to records by the service, or, with no binding to read, inputs that can bind to records. */
  records: number;
  /**
   * Inputs a person chose a fermOS fit for in this browser (OF-BLD-019 §5.1),
   * counted from the choice: the index binds without the fits, so it says
   * "with a fermOS fit chosen", never that the service bound one (§5.R).
   */
  computed: number;
  assumed: number;
  conventions: number;
  waiting: number;
  /** True when `records` counts what the service bound; false when it counts what can bind. */
  bound: boolean;
}

export function inputCounts(
  scenario: Scenario,
  info: ProformaScenarioInfo | null,
  shelf: FlowsheetInfo[],
  assumptions: InputAssumption[],
  fits: Record<string, string> = {},
): InputCounts | null {
  const typed = new Set(assumptions.map((a) => a.key));
  if (info) {
    const c = { total: info.inputs.length, records: 0, computed: 0, assumed: 0, conventions: 0, waiting: 0, bound: true };
    for (const i of info.inputs) {
      if (i.binding === 'artifact' || fits[i.key]) c.computed++;
      else if (i.binding === 'records') c.records++;
      else if (i.binding === 'assumption' || typed.has(i.key)) c.assumed++;
      else c.waiting++;
    }
    return c;
  }
  const flowsheet = shelf.find((f) => f.id === (scenario.flowsheetId ?? scenario.modelId));
  if (!flowsheet) return null;
  const c = { total: flowsheet.inputs.length, records: 0, computed: 0, assumed: 0, conventions: 0, waiting: 0, bound: false };
  for (const i of flowsheet.inputs) {
    if (fits[i.key]) c.computed++;
    else if (i.fields.length > 0) c.records++;
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

// ── The BioSTEAM scenario (§8.4), and the scenario run contract ─────────
//
// OF-BLD-019 §3.2 is the browser's side of the contract §2.3 builds in the
// service, names included:
//
//   (b) GET  /api/proforma/scenarios?includeArchived=&host=  every SEED
//       scenario of kind 'biosteam' whose program the switch shows, bound
//       (`ProformaScenarioInfo`, carrying its `flowsheet`);
//   (c) GET  /api/proforma/bind?flowsheet=&includeArchived=&host=  the same
//       shape for a flowsheet, id and name empty: what a scenario a person
//       made here (D6) shows as its inputs; a reference flowsheet, the toy or
//       an unknown id is a refusal in words;
//   (d) POST /api/proforma/run  a seed scenario by its id; a scenario made
//       here by its flowsheet, bound as (c) binds it, with the request's
//       assumptions. Inputs that still wait are a 422 listing them.

/** What a binding is asked with: the host filter, and the program switch as the page applies it. */
export interface BindAsk {
  host: string | null;
  includeArchived: boolean;
  /** The fermOS fits a person chose, by input key (OF-BLD-019 §5.1); sent to (c) alone. */
  fits?: Record<string, string>;
}

const bindQuery = (ask: BindAsk, extra: Record<string, string> = {}) => {
  const q = new URLSearchParams(extra);
  q.set('includeArchived', ask.includeArchived ? 'true' : 'false');
  if (ask.host) q.set('host', ask.host);
  if (ask.fits && Object.keys(ask.fits).length > 0) q.set('fits', JSON.stringify(ask.fits));
  return q.toString();
};

/** (b) The seed BioSTEAM scenarios the switch shows, each bound by the service. */
export const proformaScenarios = (ask: BindAsk, signal?: AbortSignal) =>
  call<ProformaScenarioInfo[]>(`/api/proforma/scenarios?${bindQuery(ask)}`, { signal });

/**
 * (c) A flowsheet's inputs, bound as the service binds a scenario made here.
 * A service that predates the endpoint says so in words, rather than as a
 * bare 404.
 */
export async function proformaBind(flowsheet: string, ask: BindAsk, signal?: AbortSignal): Promise<ProformaScenarioInfo> {
  try {
    return await call<ProformaScenarioInfo>(`/api/proforma/bind?${bindQuery(ask, { flowsheet })}`, { signal });
  } catch (e) {
    if (!noEndpoint(e)) throw e;
    throw new RagRefused(404, 'This service has no bind endpoint, so it cannot bind the inputs of a scenario made here yet.');
  }
}

/** What the page posts to run a scenario: `ProformaRunRequest`, and the flowsheet of a scenario made here. */
export interface RunAsk {
  scenarioId: string;
  /** Sent for a scenario made here alone: the service runs a seed scenario by its id. */
  flowsheet?: string | null;
  assumptions: InputAssumption[];
  host: string | null;
  /** The fermOS fits a person chose, by input key (OF-BLD-019 §5.1). */
  fits?: Record<string, string>;
}

/** (d) Run a scenario; the service keeps the run as one `proforma.run` artifact (D1). */
export const runProformaScenario = (ask: RunAsk, signal?: AbortSignal) => {
  // `flowsheet` joins ProformaRunRequest in the service with OF-BLD-019 §2.3;
  // a service that predates it ignores the field and refuses a scenario it
  // does not hold, in words. It is sent only for a scenario made here, and
  // `fits` only when a person chose one (§5.1).
  const body: ProformaRunRequest = {
    scenarioId: ask.scenarioId,
    assumptions: ask.assumptions,
    host: ask.host,
    seed: 0,
    ...(ask.flowsheet ? { flowsheet: ask.flowsheet } : {}),
    ...(ask.fits && Object.keys(ask.fits).length > 0 ? { fits: ask.fits } : {}),
  };
  return call<ProformaRunResult>('/api/proforma/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  });
};

// ── A fermOS fit feeds the fermenter (OF-BLD-019 §5.1, D10) ─────────────
//
// The fits fermOS keeps, each with what it can feed a flowsheet's titre,
// yield and productivity and why not, as the service computes them from the
// artifact: the browser shows them and keeps which artifact a person chose
// for which input (`proformaFits`, Durable), and computes no value.

/** Every kinetic fit and forecast fermOS keeps, with what it can feed `flowsheet`: `GET /api/fermos/fits`. */
export async function fermosFits(flowsheet: string, signal?: AbortSignal): Promise<FermosFitInfo[]> {
  try {
    return await call<FermosFitInfo[]>(`/api/fermos/fits?flowsheet=${encodeURIComponent(flowsheet)}`, { signal });
  } catch (e) {
    if (!noEndpoint(e)) throw e;
    throw new RagRefused(404, 'This service has no fermOS fit list, so it cannot offer a fit to this scenario yet.');
  }
}

/** The inputs a fit can feed, each to its artifact: what choosing it binds. */
export const fitsFrom = (info: FermosFitInfo): Record<string, string> =>
  info.refused ? {} : Object.fromEntries(info.feeds.filter((f) => !f.refused && f.value != null).map((f) => [f.key, info.artifactId]));

/** What a fermOS artifact is, in words. */
export const FIT_TOOL_WORDS: Record<string, string> = { kinetic_fit: 'kinetic fit', growth_forecast: 'forecast' };

/** The scenario page a fit is sent to, with the fit to attach when it opens. */
export const sendFitPath = (scenarioId: string, artifactId: string) =>
  `/proforma/scenario/${encodeURIComponent(scenarioId)}?fit=${encodeURIComponent(artifactId)}`;

// ── The geneOS ceiling check (OF-BLD-019 §5.2, D11) ─────────────────────
//
// A scenario's fermenter yield beside the newest stored geneOS ceiling of
// each shelf model of its organism, on its flowsheet's sugar, as the service
// computes it on read. A flag, never a bound: nothing here computes a
// number, and the binding and the run are untouched.

/** What the check is asked with: the scenario as its page binds it. */
export interface CeilingAsk {
  scenarioId: string;
  /** Sent for a scenario made here alone: the service reads a seed scenario's own. */
  flowsheet?: string | null;
  host: string | null;
  includeArchived: boolean;
  /** The fermOS fits a person chose, by input key (§5.1). */
  fits?: Record<string, string>;
  /** The yield's assumption, when a person typed one; the rest do not bear on the check. */
  assumptions?: InputAssumption[];
}

/** `GET /api/proforma/ceiling-check`: a service that predates it says so in words. */
export async function ceilingCheck(ask: CeilingAsk, signal?: AbortSignal): Promise<CeilingCheck> {
  const q = new URLSearchParams({ scenarioId: ask.scenarioId, includeArchived: ask.includeArchived ? 'true' : 'false' });
  if (ask.flowsheet) q.set('flowsheet', ask.flowsheet);
  if (ask.host) q.set('host', ask.host);
  if (ask.fits && Object.keys(ask.fits).length > 0) q.set('fits', JSON.stringify(ask.fits));
  if (ask.assumptions && ask.assumptions.length > 0) q.set('assumptions', JSON.stringify(ask.assumptions));
  try {
    return await call<CeilingCheck>(`/api/proforma/ceiling-check?${q.toString()}`, { signal });
  } catch (e) {
    if (!noEndpoint(e)) throw e;
    throw new RagRefused(404, 'This service has no ceiling check, so it cannot read this scenario\u2019s yield against a geneOS ceiling yet.');
  }
}

// ── One run, as every reader reads it (D1) ──────────────────────────────

/** The tool every scenario run is kept under (proforma.RUN). */
export const RUN_TOOL = 'proforma.run';

/**
 * One run of a scenario, read from its `proforma.run` artifact, or from the
 * run's answer, which carries the same output: the price's samples, the
 * sensitivity, the base case and its tables. Nothing here is recomputed; a
 * run stored before the tables (OF-BLD-019 §2.1) reads with empty ones.
 */
export interface RunView {
  artifactId: string;
  /** When the run was computed, and how long it took, when its artifact says. */
  createdAt: string | null;
  durationMs: number | null;
  provenance: Provenance;
  basis: ComputedBasis;
  /** The scenario its basis names (an input named `scenario`), when it names one. */
  scenarioId: string | null;
  flowsheet: string | null;
  basePrice: number | null;
  /** Why the base case could not run, in the service's words. */
  baseInfeasible: string | null;
  quantiles: Record<string, number>;
  histogram: HistogramBin[];
  sensitivity: InputSensitivity[];
  samples: number;
  feasible: number;
  infeasible: Record<string, number>;
  /** Null when the flowsheet declares no grid inputs. */
  grid: ProformaGrid | null;
  readBack: Record<string, number>;
  tables: ProformaTables;
}

const arr = <T,>(v: unknown): T[] => (Array.isArray(v) ? (v as T[]) : []);
const rec = <T,>(v: unknown): Record<string, T> => (v && typeof v === 'object' && !Array.isArray(v) ? (v as Record<string, T>) : {});
const str = (v: unknown): string | null => (typeof v === 'string' ? v : null);

function tablesOf(o: Record<string, unknown>, inputs: BasisInput[]): ProformaTables {
  return {
    flowsheet: str(o.flowsheet) ?? str(inputs.find((i) => i.name === 'flowsheet')?.value),
    tablesSource: str(o.tablesSource),
    tea: (o.tea as TeaBreakdown | null | undefined) ?? null,
    streams: arr<StreamRow>(o.streams),
    units: arr<UnitRow>(o.units),
    utilities: (o.utilities as UtilityDuties | null | undefined) ?? null,
    diagram: str(o.diagram),
    diagramNote: str(o.diagramNote),
    unitOrder: arr<string>(o.unitOrder),
    tableUnits: rec<string>(o.tableUnits),
  };
}

function viewOf(o: Record<string, unknown>, head: Pick<RunView, 'artifactId' | 'createdAt' | 'durationMs' | 'provenance' | 'basis'>): RunView {
  const tables = tablesOf(o, head.basis.inputs);
  const grid = o.grid as ProformaGrid | null | undefined;
  return {
    ...head,
    scenarioId: str(head.basis.inputs.find((i) => i.name === 'scenario')?.value),
    flowsheet: tables.flowsheet,
    basePrice: num(o.basePrice),
    baseInfeasible: str(o.baseInfeasible),
    quantiles: rec<number>(o.quantiles),
    histogram: arr<HistogramBin>(o.histogram),
    sensitivity: arr<InputSensitivity>(o.sensitivity),
    samples: num(o.samples) ?? 0,
    feasible: num(o.feasible) ?? 0,
    infeasible: rec<number>(o.infeasible),
    grid: grid && Array.isArray(grid.dims) && grid.dims.length > 0 ? grid : null,
    readBack: rec<number>(o.readBack),
    tables,
  };
}

/** A run as its artifact keeps it, or null when the artifact is not a scenario run. */
export function runViewOfArtifact(art: Artifact): RunView | null {
  if (art.tool !== RUN_TOOL) return null;
  return viewOf(art.output, {
    artifactId: art.id,
    createdAt: art.createdAt,
    durationMs: art.durationMs,
    provenance: art.provenance,
    basis: { tool: art.tool, toolVersion: art.toolVersion, inputs: art.inputs, artifactId: art.id, at: art.createdAt, seed: art.seed },
  });
}

/** A run as `POST /api/proforma/run` answers it: the same output, its basis in its evidence. */
export function runViewOfResult(r: ProformaRunResult): RunView {
  return viewOf(r as unknown as Record<string, unknown>, {
    artifactId: r.artifactId,
    createdAt: r.evidence?.basis?.at ?? null,
    durationMs: null,
    provenance: r.provenance,
    basis: r.evidence.basis,
  });
}

/** The tool every reference biorefinery's run is kept under (proforma.REFERENCE). */
export const REFERENCE_TOOL = 'proforma.reference';

/**
 * A reference run in the shape a scenario run reads (OF-BLD-019 §3.3): the
 * same tables under the same keys, and one case, so no samples, no
 * sensitivity and no grid. Its base case is the run itself, and its price on
 * the TEA's own basis is the product price the worker read from the TEA,
 * which the cost breakdown closes on; nothing is computed here.
 */
export function runViewOfReference(art: Artifact): RunView | null {
  if (art.tool !== REFERENCE_TOOL) return null;
  const view = viewOf(art.output, {
    artifactId: art.id,
    createdAt: art.createdAt,
    durationMs: art.durationMs,
    provenance: art.provenance,
    basis: { tool: art.tool, toolVersion: art.toolVersion, inputs: art.inputs, artifactId: art.id, at: art.createdAt, seed: art.seed },
  });
  return { ...view, basePrice: num(view.tables.tea?.productPrice) };
}

/** One of a reference run's checks against its package's own test, as the service wrote it (`output.checks`). */
export const referenceChecks = (art: Artifact | null): RegressionCheck[] => arr<RegressionCheck>(art?.output?.checks);

/** A basis input a reference run names, by name ('compatibility', 'simulator'), or null. */
export const basisInput = (art: Artifact | null, name: string): BasisInput | null => art?.inputs.find((i) => i.name === name) ?? null;

// ── The inputs a run was bound with, read from its basis (Compare) ──────

/** One input of a run as its basis states it: the source, and its range when it has one. */
export interface RunInput {
  key: string;
  label: string;
  /** 'record', 'assumption', 'artifact', 'model', 'convention', or 'absent' when the basis names it nowhere. */
  kind: string;
  unit: string;
  /** Records: how many, and the lowest and highest value the basis lists, in its unit. */
  count: number;
  low: number | null;
  high: number | null;
  /** An assumption's or an artifact's value; a record-bound input has none of its own here. */
  value: number | string | null;
  /** Who typed an assumption, or the artifact's id, or a source's note. */
  by: string | null;
  note: string | null;
}

/**
 * Each input the run's flowsheet takes, as the run's basis names it (D1):
 * `<key> record` once per record, `<key>`, `<key> low` and `<key> high` for an
 * assumption, `<key>` alone for an artifact, a model or a convention. The
 * range of a record-bound input is the lowest and highest record value the
 * basis lists; every other number is the basis's own.
 */
export function runInputs(view: RunView, flowsheet: FlowsheetInfo | null, labels: Record<string, string> = {}): RunInput[] {
  const keys = (flowsheet?.inputs ?? []).map((i) => i.key);
  // A run whose flowsheet the shelf no longer holds still names its inputs.
  for (const i of view.basis.inputs) {
    const m = /^(.+?) (record|low|high)$/.exec(i.name);
    const key = m ? m[1] : null;
    if (key && !keys.includes(key)) keys.push(key);
  }
  return keys.map((key) => {
    const declared = flowsheet?.inputs.find((i) => i.key === key);
    const label = labels[key] ?? declared?.name ?? key;
    const records = view.basis.inputs.filter((i) => i.name === `${key} record` && i.source.kind === 'record');
    const own = view.basis.inputs.find((i) => i.name === key);
    const unit = records[0]?.unit ?? own?.unit ?? declared?.unit ?? '';
    if (records.length) {
      const vals = records.map((r) => num(r.value)).filter((v): v is number => v != null);
      const scale = view.basis.inputs.find((i) => i.name === `${key} scale`);
      return {
        key, label, kind: 'record', unit, count: records.length,
        low: vals.length ? Math.min(...vals) : null, high: vals.length ? Math.max(...vals) : null,
        value: null, by: null, note: scale ? `scaled by the basis's convention ${String(scale.value)}${scale.source.note ? `, ${scale.source.note}` : ''}` : null,
      };
    }
    if (!own) return { key, label, kind: 'absent', unit, count: 0, low: null, high: null, value: null, by: null, note: declared?.kind === 'convention' ? 'a convention the run states elsewhere in its basis' : null };
    const part = (p: string) => num(view.basis.inputs.find((i) => i.name === `${key} ${p}`)?.value);
    const value = typeof own.value === 'number' || typeof own.value === 'string' ? own.value : null;
    return {
      key, label, kind: own.source.kind, unit, count: 0,
      low: own.source.kind === 'assumption' ? part('low') : null, high: own.source.kind === 'assumption' ? part('high') : null,
      value, by: own.source.by ?? own.source.id ?? null, note: own.source.note ?? null,
    };
  });
}

/** A run's price: the median of the samples that ran with their 5th to 95th percentile, else the base case's. */
export function viewPrice(view: RunView, basis: string): PriceRead | null {
  const p50 = num(view.quantiles.p50);
  if (p50 != null) return { value: p50, basis, low: num(view.quantiles.p5), high: num(view.quantiles.p95), reads: 'median of the samples that ran' };
  return view.basePrice == null ? null : { value: view.basePrice, basis, low: null, high: null, reads: 'the base case' };
}

/** The base case in words: why it could not run, as the service said, without the exception's class name. */
export const baseCaseRefusal = (why: string) => why.replace(/^[A-Z][A-Za-z]*(Error|Exception|Infeasible)?: /, '');

/**
 * D8's line, said when a run carries no diagram and no note of its own (a
 * run stored before the worker wrote one).
 */
export const NO_DIAGRAM =
  'This run keeps no diagram: Graphviz draws one on a host that has it (brew install graphviz on the Mini).';

/**
 * The diagram as an image source: an <img> never runs a script the SVG
 * might carry, and the text is BioSTEAM's own, read from the run.
 */
export const diagramSrc = (svg: string) => `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;

/** The words for an infeasible sample's reason (flowsheets/pha_sugar_v0.REASONS and ethanol_glucose_v0.REASONS). */
export const INFEASIBLE_WORDS: Record<string, string> = {
  carbon: 'left no sugar for respiration',
  oxygen: 'asked for more oxygen than the aerated tank transfers',
  balance: "left the fermenter's mass balance open",
  yield: 'asked for a yield above the theoretical yield of ethanol on glucose',
  concentration: 'asked for more glucose than a litre of feed can hold',
  convergence: 'did not converge in the simulator',
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
export function modellerQuestions(
  inputs: ScenarioInput[],
  run: { sensitivity: InputSensitivity[] } | null,
): { key: string; label: string; rho: number | null; question: string }[] {
  const rho = new Map((run?.sensitivity ?? []).map((s) => [s.key, s.rho]));
  return inputs
    .filter((i) => i.binding === 'assumption' || i.binding === 'waiting')
    .map((i, n) => ({ key: i.key, label: i.label, rho: rho.get(i.key) ?? null, question: QUESTION[i.key] ?? `Where should ${i.label} come from?`, n }))
    // An input the run did not rank (held fixed, or no run yet) follows every ranked one.
    .sort((a, b) => (b.rho == null ? -1 : Math.abs(b.rho)) - (a.rho == null ? -1 : Math.abs(a.rho)) || a.n - b.n)
    .map(({ n: _n, ...q }) => q);
}

export function questionsText(scenario: ProformaScenarioInfo, run: { sensitivity: InputSensitivity[] } | null): string {
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
