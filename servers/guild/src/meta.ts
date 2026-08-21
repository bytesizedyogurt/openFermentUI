/**
 * What this server puts in its response envelope, and why.
 *
 * MIRROR of `openferment_core/snapshot.py`. That file is canonical and states
 * the framing at length; this is the TypeScript half, and
 * `scripts/check-servers.mjs` feeds both the same inputs and fails if the two
 * ever produce different ids.
 *
 * An earlier version of this file grew its own framing (`name:bytes`, a
 * `sha256:` prefix, 12 hex characters) while the Python server grew a
 * different one (`name\0bytes`, a `corpus-` prefix, 12 characters). Two
 * servers reading the SAME file reported different ids — while this file's own
 * docstring promised that reading the same files would yield the same id. That
 * is why the framing now lives in one place with a gate on it.
 */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

import pkg from '../package.json' with { type: 'json' };

/**
 * The server's own build id. `guild-` prefix is the load-bearing part, the
 * same way `fixture-` is in the fixture backend: anything replaying a trace
 * must be able to tell at a glance WHICH backend answered. A real deployment
 * substitutes a git describe or an image tag at build time.
 */
export const SERVER_VERSION = `guild-${pkg.version}`;

const HERE = dirname(fileURLToPath(import.meta.url));
/** servers/guild/src → repo root is three levels up. */
const REPO_ROOT = join(HERE, '..', '..', '..');

/** Hex characters of digest kept. Mirrors SNAPSHOT_HEX_CHARS. */
const SNAPSHOT_HEX_CHARS = 16;

/**
 * The corpus files this server reads, as repo-relative paths — the same
 * spelling the Python reader uses, because the path is part of the digest.
 *
 * `protocols.json` and not the other six, because protocols are the one corpus
 * collection the Guild's entities are DEFINED against: a `GuildChapter`
 * carries `protocolIds` (what the chapter is equipped to run) and `bsl` (which
 * `Protocol.bsl` bounds), and a deposit is a `RunOutcome` of a protocol run.
 * `list_sealable_protocols` serves it, so this server does not digest a file it
 * never opens.
 *
 * Consequence, stated so nobody trips on it: this id will NOT equal another
 * server's `corpusSnapshotId` unless that server read exactly the same files.
 * Per-server scope is the honest reading of "what was this answer computed
 * against"; a corpus-wide revision id is the exporter's to mint, and when it
 * exists every server should report that instead.
 */
export const CORPUS_FILES = ['data/corpus/protocols.json'] as const;

export interface CorpusSnapshot {
  /** `sha256:<16 hex>` over the files in `CORPUS_FILES`. */
  id: string;
  /** True when every file in `CORPUS_FILES` was read and parsed as JSON. */
  ok: boolean;
  /** The parsed contents, keyed by repo-relative path. */
  contents: Record<string, unknown>;
}

/**
 * Digest a set of files. Mirrors `corpus_snapshot_id` exactly: names sorted,
 * each entry framed `name \0 length \0 bytes` with the length in decimal
 * ASCII. Without the length, a file named `a` holding `b\0c` and a file named
 * `a\0b` holding `c` would digest identically.
 */
export function corpusSnapshotId(files: Record<string, Buffer>): string {
  const hash = createHash('sha256');
  for (const name of Object.keys(files).sort()) {
    const content = files[name]!;
    hash.update(Buffer.from(name, 'utf8'));
    hash.update(Buffer.from([0]));
    hash.update(Buffer.from(String(content.length), 'ascii'));
    hash.update(Buffer.from([0]));
    hash.update(content);
  }
  return `sha256:${hash.digest('hex').slice(0, SNAPSHOT_HEX_CHARS)}`;
}

let cached: CorpusSnapshot | null = null;

/**
 * Read the corpus files, verify they parse, digest their raw bytes.
 *
 * Raw bytes rather than a re-serialisation, because this server serves files it
 * did not shape — the exporter's bytes are the thing being attested.
 *
 * Computed once and cached: the files are read at first use and the process
 * serves that snapshot for its lifetime. A corpus edit requires a restart to be
 * visible, and the id moving is how a trace shows the restart happened.
 *
 * UNLIKE THE PYTHON SERVERS, an unreadable file does not stop the process — it
 * sets `ok: false` and the health tool reports it. The Python side refuses to
 * start because it VALIDATES what it reads through the canonical models and a
 * corpus it cannot validate is one it cannot serve; this server has no Pydantic
 * to validate against (see `server.ts` on why `GuildChapter` has no model), so
 * the strongest thing it can honestly do is say that the read failed.
 */
export function corpusSnapshot(): CorpusSnapshot {
  if (cached) return cached;
  const files: Record<string, Buffer> = {};
  const contents: Record<string, unknown> = {};
  let ok = true;
  for (const name of CORPUS_FILES) {
    try {
      const bytes = readFileSync(join(REPO_ROOT, name));
      contents[name] = JSON.parse(bytes.toString('utf8'));
      files[name] = bytes;
    } catch {
      ok = false;
    }
  }
  cached = { id: corpusSnapshotId(files), ok, contents };
  return cached;
}

/**
 * The response envelope every tool answer carries, mirroring the repo's
 * `AdapterResponse<T>`: `{ data, serverVersion, corpusSnapshotId, notice? }`.
 * One helper, so no tool can forget a field or invent a fourth.
 *
 * `modelVersion` is absent from everything this server returns, and the
 * absence means NO MODEL RAN rather than "version unknown".
 */
export function envelope<T>(data: T, notice?: string) {
  return {
    data,
    serverVersion: SERVER_VERSION,
    corpusSnapshotId: corpusSnapshot().id,
    ...(notice ? { notice } : {}),
  };
}
