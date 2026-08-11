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
import App from './App';
import { useStore } from './store';

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
