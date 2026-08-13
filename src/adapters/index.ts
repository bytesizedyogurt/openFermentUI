/**
 * Backend selection for the five adapters.
 *
 * Deliberately the same shape as the selection in `src/data/source.ts`, down
 * to the Node guard, because there is no good reason for two seams in one repo
 * to be configured two different ways:
 *
 *   - read `import.meta.env` through a cast, so the module stays importable by
 *     the Node scripts, which have no Vite in the picture;
 *   - refuse to select a network backend under Node at all;
 *   - default to the local one, and require an explicit opt-in for the other.
 *
 * The two flags are INDEPENDENT, and that is on purpose.
 * `VITE_CORPUS_BACKEND` chooses where the seven corpus collections come from;
 * `VITE_ADAPTER_BACKEND` chooses who answers the five subsystems. A corpus
 * served over HTTP with fermOS still unwritten is a real intermediate state,
 * and one flag could not express it.
 */
import type { OpenFermentAdapters, AdapterBackend } from './types';
import { fixtureAdapters } from './fixture';
import { mcpAdapters } from './mcp';

export * from './types';

interface AdapterEnv {
  VITE_ADAPTER_BACKEND?: string;
}

const ENV: AdapterEnv = (import.meta as unknown as { env?: AdapterEnv }).env ?? {};

/**
 * Scripts always run against the fixture: `check:corpus`, `check:seed` and the
 * capture scripts must not depend on a server being up, and a gate that can
 * fail because something was not running is not a gate.
 */
const IS_NODE =
  typeof process !== 'undefined' && process.versions != null && process.versions.node != null;

/**
 * `fixture` unless something explicitly asks for `mcp`. An unrecognised value
 * selects the fixture rather than throwing — a typo in an environment variable
 * should not be the thing that decides whether the app boots, and the backend
 * in force is readable at runtime through `adapterBackend()` and stamped on
 * every response's `serverVersion` besides.
 */
const BACKEND: AdapterBackend = !IS_NODE && ENV.VITE_ADAPTER_BACKEND === 'mcp' ? 'mcp' : 'fixture';

export function adapterBackend(): AdapterBackend {
  return BACKEND;
}

/**
 * The five, from whichever backend is selected.
 *
 * One object rather than five exports, so a caller reaches for
 * `adapters.corpus` and cannot end up holding a fixture corpus and an MCP
 * process adapter at the same time by importing from two places.
 */
export const adapters: OpenFermentAdapters = BACKEND === 'mcp' ? mcpAdapters : fixtureAdapters;

export { fixtureAdapters } from './fixture';
export { mcpAdapters } from './mcp';
