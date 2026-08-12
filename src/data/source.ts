/**
 * Data-source adapter — the single seam between the UI and the corpus.
 *
 * The corpus is on its way out of TypeScript. It now lives as JSON at
 * `data/corpus/*.json` (repo root `data/`, deliberately NOT `src/data/`, so a
 * Python exporter and eventually a Postgres loader own the same files without
 * writing into the front-end source tree). This module is what everything in
 * `src/` reads instead of the authored `.ts` corpus modules.
 *
 * ── WHY THE SURFACE IS SYNCHRONOUS ────────────────────────────────────────
 * Nineteen files read these collections as plain arrays, and two modules
 * (`contradictions.ts`, `designs.ts`) derive from them AT MODULE SCOPE — the
 * referee runs over RECORDS at load, and DESIGNS is a sweep of SCENARIOS.
 * Making the surface async would mean rewriting components, which the brief
 * forbids. So the collections are exported as arrays that are FILLED IN PLACE,
 * never reassigned, and the two backends differ only in when the fill happens:
 *
 *   "bundled"  filled EAGERLY at module load from a static JSON import. No
 *              await, no bootstrap. `initCorpus()` is a no-op. Node scripts
 *              (check-seed, capture-fixtures, …) that import this module keep
 *              working exactly as they do against the authored modules today.
 *
 *   "api"      the arrays start EMPTY and are filled by `await initCorpus()`.
 *              Nothing may read a collection before that promise resolves —
 *              `src/main.tsx` awaits it and only then DYNAMICALLY imports App
 *              and the store, so every module-scope derivation downstream is
 *              evaluated after the data has landed. A read before then sees an
 *              empty array; it does not throw and it does not block. That is
 *              the whole contract, and main.tsx is the only place that has to
 *              honour it.
 *
 * ── WHERE THE ASSEMBLY LOGIC LIVES ────────────────────────────────────────
 * Two pieces of behaviour came out of `papers.ts` and `records.ts` and had to
 * land somewhere: the entry-id sort (H2 before H10) and the recomputation of
 * each record's SI twin from (value, unit). BOTH ARE APPLIED HERE, ON READ, not
 * baked into the JSON by the exporter. One rule, applied consistently:
 *
 *     the JSON carries authored facts; every derivation the app depends on is
 *     applied by this adapter, identically for both backends.
 *
 * The sort, because row order is not a property a store preserves. `SELECT`
 * without `ORDER BY` returns whatever Postgres feels like, and an API response
 * assembled from a query carries whatever order the query gave it. Baked into
 * the exporter, the ordering invariant would hold under "bundled" and quietly
 * break the day the same collection arrives over HTTP. Applied here it holds
 * for every backend, by construction, for the cost of one comparator over a few
 * hundred entries.
 *
 * The SI twin, because `si` is a derivation of (value, unit), not an
 * independent datum — that is exactly why `records.ts` recomputed it rather
 * than trusting what was authored. Recomputing at the boundary keeps the
 * guarantee the original comment claims: no transport (file, HTTP, or a
 * Postgres round trip through a float column) can hand the app a record whose
 * `si` disagrees with its `value`. It is idempotent, so an exporter that also
 * emits `si` loses nothing, and it leaves the exporter's job purely mechanical:
 * serialize what was authored, derive nothing. The canonical unit engine stays
 * one per language — Python for the pipeline, the parity-checked TS mirror in
 * `@/engine/units` here — rather than a converted number copied between them.
 *
 * ── WHAT DID NOT MOVE ─────────────────────────────────────────────────────
 * `COST_MODELS` stays in `src/data/scenarios.ts`. Its `evaluate` is a function;
 * `CostModel` and `ResultGrid` were established in Phase 1 as the two types
 * that cannot round-trip through JSON Schema. Only `SCENARIOS` moves.
 */
import type {
  ExtractionRecord,
  LearnModule,
  Paper,
  ParameterDef,
  Protocol,
  Scenario,
  Strain,
} from './types';
import { toSI } from '@/engine/units';

// Static JSON imports. These are the "bundled" backend's payload, and they are
// what makes the eager fill possible — a dynamic import here would reintroduce
// the await this whole design exists to avoid. Each is cast through `unknown`:
// TypeScript infers a structural type from the file contents, and a corpus of
// real literature will not narrow cleanly onto the generated union literals
// (`Provenance`, `FieldId`, `AnalysisMethod`, …) no matter how correct it is.
// The generated schema, not tsc's read of a data file, is the authority on
// shape; `pnpm check:schema` validates the JSON against the Pydantic models.
import papersJson from '../../data/corpus/papers.json';
import recordsJson from '../../data/corpus/records.json';
import ontologyJson from '../../data/corpus/ontology.json';
import strainsJson from '../../data/corpus/strains.json';
import protocolsJson from '../../data/corpus/protocols.json';
import scenariosJson from '../../data/corpus/scenarios.json';
import learnJson from '../../data/corpus/learn.json';

// ── The exported collections ──────────────────────────────────────────────
// Filled in place, never reassigned. Anything that captured the array
// reference — a module-scope `const X = PAPERS.filter(...)` does not, but a
// closure over `PAPERS` does — keeps seeing the live contents.

export const PAPERS: Paper[] = [];
export const RECORDS: ExtractionRecord[] = [];
export const ONTOLOGY: ParameterDef[] = [];
export const STRAINS: Strain[] = [];
export const PROTOCOLS: Protocol[] = [];
export const SCENARIOS: Scenario[] = [];
export const MODULES: LearnModule[] = [];

// ── Backend selection ─────────────────────────────────────────────────────

export type CorpusBackend = 'bundled' | 'api';

interface CorpusEnv {
  VITE_CORPUS_BACKEND?: string;
  VITE_CORPUS_API_BASE?: string;
}

/**
 * `import.meta.env` exists under Vite and nowhere else. Reading it through a
 * cast rather than a `vite/client` reference keeps this module importable by
 * the Node scripts, which have no Vite in the picture at all.
 */
const ENV: CorpusEnv = (import.meta as unknown as { env?: CorpusEnv }).env ?? {};

/** Scripts always read the bundled corpus: no fetch, no bootstrap, no server. */
const IS_NODE =
  typeof process !== 'undefined' && process.versions != null && process.versions.node != null;

const BACKEND: CorpusBackend = !IS_NODE && ENV.VITE_CORPUS_BACKEND === 'api' ? 'api' : 'bundled';

/** Trailing slashes trimmed so `${API_BASE}/papers.json` is always well formed. */
const API_BASE = (ENV.VITE_CORPUS_API_BASE ?? '/data/corpus').replace(/\/+$/, '');

export function corpusBackend(): CorpusBackend {
  return BACKEND;
}

// ── Assembly ──────────────────────────────────────────────────────────────

/**
 * Sort by thread letter then numeric index, so H2 precedes H10.
 * Lifted verbatim from `src/data/papers.ts`, which this module supersedes.
 */
function byEntryId(a: Paper, b: Paper): number {
  const pa = a.id.match(/^([A-O])(\d+)(\w*)$/);
  const pb = b.id.match(/^([A-O])(\d+)(\w*)$/);
  if (!pa || !pb) return a.id.localeCompare(b.id);
  if (pa[1] !== pb[1]) return pa[1].localeCompare(pb[1]);
  if (Number(pa[2]) !== Number(pb[2])) return Number(pa[2]) - Number(pb[2]);
  return pa[3].localeCompare(pb[3]);
}

/**
 * Recompute the SI twin from (value, unit) so the invariant holds by
 * construction rather than by authoring discipline. Categorical records carry a
 * string value and are passed through with `si.value = 0`, keeping their unit.
 * Lifted verbatim from `src/data/records.ts`, which this module supersedes.
 */
function withSI(r: ExtractionRecord): ExtractionRecord {
  if (typeof r.value !== 'number') return { ...r, si: { value: 0, unit: r.unit } };
  return { ...r, si: toSI(r.value, r.unit) };
}

/** Replace a collection's contents without replacing the array itself. */
function fill<T>(target: T[], items: readonly T[]): void {
  target.length = 0;
  // A loop rather than `push(...items)`: spreading a few thousand records into
  // an argument list is how you find out what the engine's argument limit is.
  for (const item of items) target.push(item);
}

interface RawCorpus {
  papers: unknown;
  records: unknown;
  ontology: unknown;
  strains: unknown;
  protocols: unknown;
  scenarios: unknown;
  learn: unknown;
}

function install(raw: RawCorpus): void {
  fill(PAPERS, (raw.papers as Paper[]).slice().sort(byEntryId));
  fill(RECORDS, (raw.records as ExtractionRecord[]).map(withSI));
  fill(ONTOLOGY, raw.ontology as ParameterDef[]);
  fill(STRAINS, raw.strains as Strain[]);
  fill(PROTOCOLS, raw.protocols as Protocol[]);
  fill(SCENARIOS, raw.scenarios as Scenario[]);
  fill(MODULES, raw.learn as LearnModule[]);
}

// ── "bundled": eager, at module load ──────────────────────────────────────

if (BACKEND === 'bundled') {
  install({
    papers: papersJson,
    records: recordsJson,
    ontology: ontologyJson,
    strains: strainsJson,
    protocols: protocolsJson,
    scenarios: scenariosJson,
    learn: learnJson,
  });
}

// ── "api": explicit, awaited once ─────────────────────────────────────────

const COLLECTION_FILES = [
  'papers',
  'records',
  'ontology',
  'strains',
  'protocols',
  'scenarios',
  'learn',
] as const;

async function fetchCollection(name: string): Promise<unknown[]> {
  const url = `${API_BASE}/${name}.json`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`openFerment corpus: GET ${url} failed — ${res.status} ${res.statusText}`);
  }
  const body: unknown = await res.json();
  if (!Array.isArray(body)) {
    throw new Error(`openFerment corpus: ${url} did not return a JSON array`);
  }
  return body;
}

async function fetchAll(): Promise<void> {
  const [papers, records, ontology, strains, protocols, scenarios, learn] = await Promise.all(
    COLLECTION_FILES.map((name) => fetchCollection(name)),
  );
  install({ papers, records, ontology, strains, protocols, scenarios, learn });
}

let pending: Promise<void> | null = null;

/**
 * Make the collections readable.
 *
 * A no-op under "bundled" — the arrays were filled at module load. Under "api"
 * it fetches all seven files in parallel and fills them, and it is idempotent:
 * concurrent callers share one in-flight promise. A failed fetch REJECTS rather
 * than leaving the app running on an empty corpus; rendering a plausible-looking
 * but empty workspace would be a worse outcome than not rendering.
 */
export function initCorpus(): Promise<void> {
  if (BACKEND === 'bundled') return Promise.resolve();
  if (!pending) pending = fetchAll();
  return pending;
}
