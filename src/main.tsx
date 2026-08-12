import React from 'react';
import { createRoot } from 'react-dom/client';
import '@fontsource/spectral/300.css';
import '@fontsource/spectral/400.css';
import '@fontsource/spectral/500.css';
import '@fontsource/spectral/600.css';
import '@fontsource/ibm-plex-sans/400.css';
import '@fontsource/ibm-plex-sans/500.css';
import '@fontsource/ibm-plex-sans/600.css';
import '@fontsource/ibm-plex-mono/400.css';
import '@fontsource/ibm-plex-mono/500.css';
import './styles.css';
import { initCorpus } from './data/source';

// The corpus lands before anything that derives from it is imported.
//
// `App` and the store are pulled in DYNAMICALLY, after `initCorpus()` resolves,
// and that ordering is the whole point: `src/data/contradictions.ts` runs the
// referee over RECORDS at module scope and `src/data/designs.ts` sweeps
// SCENARIOS at module scope, so a static import of either would evaluate those
// derivations against an empty corpus under the "api" backend. Under "bundled"
// `initCorpus()` is a no-op and this costs one already-resolved promise.
async function boot() {
  await initCorpus();
  const [{ default: App }, { useStore }] = await Promise.all([
    import('./App'),
    import('./store'),
  ]);

  // A handle on the store for the headless test harness (scripts/deep-paths.mjs).
  //
  // Deliberate, not a leak. This build has no auth, no secrets and no persistence
  // — the store is already fully inspectable through React DevTools, and the
  // Inspector shows its contents by design. Exposing it lets a test drive a
  // correction and watch it propagate, which is the behaviour under test; the
  // alternative is scripting a fragile path through the review queue and testing
  // the affordance instead of the propagation.
  (window as unknown as { __ofStore: typeof useStore }).__ofStore = useStore;

  createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  );
}

// A corpus that will not load is a hard failure, not an empty workspace: an app
// rendered over nothing looks like a working app with no literature in it.
void boot().catch((err: unknown) => {
  console.error(err);
  const root = document.getElementById('root');
  if (root) root.textContent = `Corpus failed to load: ${String(err)}`;
});
