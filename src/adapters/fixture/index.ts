/**
 * The fixture backend: the five interfaces, answered out of the data layer
 * that is already here.
 *
 * "Fixture" rather than "bundled" — `src/data/source.ts` uses `bundled` for
 * the corpus that ships in the build, and this is a different axis. A fixture
 * adapter would still be the right thing in front of an `api` corpus for any
 * subsystem whose server has not been written yet, and the two selections are
 * independent.
 *
 * Every method here reads through the existing modules — `@/data/source`,
 * `@/data/designs`, `@/engine/*` — and none of them reimplements anything
 * those already do. Where a fixture cannot answer, it says so in `notice`
 * rather than returning something that looks like an answer.
 */
import type { OpenFermentAdapters } from '@/adapters/types';
import { fixtureCorpusAdapter } from './corpus';
import { fixtureCellAdapter } from './cell';
import { fixtureProcessAdapter } from './process';
import { fixtureEconomicsAdapter } from './economics';
import { fixtureGuildAdapter } from './guild';
import { fixtureAgentAdapter } from './agent';

export const fixtureAdapters: OpenFermentAdapters = {
  corpus: fixtureCorpusAdapter,
  cell: fixtureCellAdapter,
  process: fixtureProcessAdapter,
  economics: fixtureEconomicsAdapter,
  guild: fixtureGuildAdapter,
  agent: fixtureAgentAdapter,
};

export {
  fixtureCorpusAdapter,
  fixtureCellAdapter,
  fixtureProcessAdapter,
  fixtureEconomicsAdapter,
  fixtureGuildAdapter,
  fixtureAgentAdapter,
};
export { corpusSnapshotId, FIXTURE_SERVER_VERSION } from './meta';
