/**
 * What the fixture backend puts in `ResponseMeta`, and why.
 *
 * Three constants would have been less code. Two of these are not constants,
 * and that is the whole exercise: versioning that never changes cannot tell
 * two traces apart, which is the one thing versioning is for.
 */
import { PAPERS, RECORDS, ONTOLOGY, STRAINS, PROTOCOLS, SCENARIOS, MODULES } from '@/data/source';
import { CE } from '@/engine/biosteam/cepci';
import { DESIGN_ENGINE_VERSION } from '@/engine/designs';
import type { AdapterResponse } from '@/adapters/types';

/**
 * The `serverVersion` of a response no server produced.
 *
 * The `fixture-` prefix is the load-bearing part. A real deployment reports its
 * own build id — a git describe, an image tag — and anything replaying a trace
 * has to be able to tell at a glance that this one was answered out of the
 * bundled corpus by code running in the reader's own browser.
 */
export const FIXTURE_SERVER_VERSION = 'fixture-0.1.0';

/**
 * `modelVersion` for anything the design engine computed. Real, already
 * exported, and already stamped on every `TierResult.engineVersion`.
 */
export const FIXTURE_DESIGN_MODEL_VERSION = DESIGN_ENGINE_VERSION;

/**
 * `modelVersion` for anything the plant solve computed.
 *
 * Read at response time rather than captured once, because `setCEPCI` can move
 * the index mid-session and every cost in the answer moves with it. A replay
 * that did not know which index was in effect could not reproduce the number,
 * which makes the cost basis part of the model version rather than a detail of
 * it.
 */
export function plantModelVersion(): string {
  return `plant-cepci-${CE.value}`;
}

// ── corpusSnapshotId ──────────────────────────────────────────────────────

/**
 * FNV-1a, 32-bit. A digest, not a cryptographic one — it is here to change
 * when the corpus changes, not to resist anybody.
 */
function fnv1a(text: string): string {
  let h = 0x811c9dc5;
  for (let i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i);
    // The 32-bit FNV prime, by shift-add rather than multiplication: `*` on a
    // number this size loses the low bits to float rounding.
    h = (h + ((h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24))) >>> 0;
  }
  return h.toString(16).padStart(8, '0');
}

let cached: string | null = null;

/**
 * An identifier for the corpus revision this answer was computed against.
 *
 * WHAT A REAL SERVER PUTS HERE: something immutable that it holds and the
 * client cannot compute — the git commit of `data/corpus` it was built from, a
 * Postgres transaction id or snapshot LSN, or a digest the exporter wrote
 * alongside the files. It has to come from the server, because only the server
 * knows what it actually served; a client digest can only describe what
 * arrived.
 *
 * WHAT THE FIXTURE PUTS HERE, and why not a constant: a digest of the seven
 * assembled collections. A hardcoded string would be a version number that
 * never versions anything — every trace ever recorded would carry it, and two
 * traces taken either side of a corpus edit would be indistinguishable, which
 * is precisely the failure this field exists to prevent. Deriving it from the
 * content means an edit to `data/corpus/*.json` moves it, for free.
 *
 * It digests the collections as `@/data/source` exposes them — after the
 * entry-id sort and the SI recomputation — rather than the raw JSON, so it
 * describes what the app is actually holding. Under the `api` backend that is
 * what the server sent, which is the only thing the client is entitled to
 * attest to.
 *
 * Computed on first use and cached, because it is one pass over roughly half a
 * megabyte. The cache is not written until the corpus is non-empty: under the
 * `api` backend a call landing before `initCorpus()` resolves would otherwise
 * pin the digest of nothing for the rest of the session.
 */
export function corpusSnapshotId(): string {
  if (cached) return cached;
  const parts = [
    ['papers', PAPERS],
    ['records', RECORDS],
    ['ontology', ONTOLOGY],
    ['strains', STRAINS],
    ['protocols', PROTOCOLS],
    ['scenarios', SCENARIOS],
    ['learn', MODULES],
  ] as const;
  const digest = fnv1a(parts.map(([name, rows]) => `${name}:${JSON.stringify(rows)}`).join('\n'));
  const id = `fixture-${digest}`;
  if (PAPERS.length > 0) cached = id;
  return id;
}

// ── The envelope ──────────────────────────────────────────────────────────

/** Everything a fixture method may add to the payload. */
export interface FixtureMeta {
  modelVersion?: string;
  notice?: string;
}

/**
 * Wrap a payload with the versioning every response carries.
 *
 * One helper, so no fixture method can forget a field or invent a fourth.
 */
export function respond<T>(data: T, meta: FixtureMeta = {}): AdapterResponse<T> {
  return {
    data,
    serverVersion: FIXTURE_SERVER_VERSION,
    corpusSnapshotId: corpusSnapshotId(),
    ...(meta.modelVersion ? { modelVersion: meta.modelVersion } : {}),
    ...(meta.notice ? { notice: meta.notice } : {}),
  };
}
