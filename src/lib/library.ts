// The installed package's plants, as the browser reads them (alpha 2.1 stage
// B; GET /api/library, engine/library.py's discovery). Types generated from
// the service's models; nothing here asks the service, so `pnpm check:state`
// holds it offline.
import type { components } from '@/api/types.gen';

/** The installed package's plants as discovery read them (GET /api/library). */
export type LibraryShelf = components['schemas']['LibraryShelf'];
export type LibraryPlant = components['schemas']['LibraryPlant'];

/**
 * The configurations a plant can be run in here: each one it built in when
 * discovery built it (null for the plant's own), its default first; and the
 * ones that did not build, with the package's words.
 */
export function runnable(plant: LibraryPlant): { configurations: (string | null)[]; failed: { configuration: string | null; error: string }[] } {
  const builds = plant.builds ?? [];
  const built = builds.filter((b) => b.ok).map((b) => b.configuration ?? null);
  const first = plant.defaultConfiguration ?? null;
  const configurations = built.includes(first) ? [first, ...built.filter((c) => c !== first)] : built;
  const failed = builds.filter((b) => !b.ok).map((b) => ({ configuration: b.configuration ?? null, error: b.error ?? 'it did not build' }));
  return { configurations, failed };
}
