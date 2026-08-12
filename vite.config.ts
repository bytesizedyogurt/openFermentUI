import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig(({ mode }) => {
  // The offline build folds the dynamic imports flat (see below), and flattening
  // them HOISTS the module bodies of App and the store to top level — so every
  // module-scope derivation over the corpus evaluates before `boot()` reaches
  // `await initCorpus()`. Under the bundled backend that is harmless, because the
  // arrays are already filled at import. Under `api` it is not: the fetches all
  // succeed, nothing throws, and the app renders a complete, silent, EMPTY
  // workspace — the outcome src/main.tsx calls unacceptable, arrived at without a
  // single error to notice.
  //
  // So the combination is refused rather than documented. This was a comment
  // claiming the offline bundle "is always the bundled backend by construction";
  // nothing enforced it, which made it a wish rather than a constraint.
  if (mode === 'offline' && process.env.VITE_CORPUS_BACKEND === 'api') {
    throw new Error(
      'vite: --mode offline cannot be built with VITE_CORPUS_BACKEND=api.\n' +
        '  The offline bundle inlines dynamic imports, which defeats the ordering\n' +
        '  main.tsx relies on to land the corpus before anything derives from it.\n' +
        '  A file:// bundle has no server to fetch from in any case.',
    );
  }
  return {
  plugins: [react()],
  base: './',
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  build: {
    chunkSizeWarningLimit: 1500,
    rollupOptions: {
      output: {
        // `src/main.tsx` imports App and the store DYNAMICALLY, so the corpus
        // has landed before any module-scope derivation over it evaluates.
        // Rollup answers a dynamic import with a separate chunk, which is right
        // for the hosted build and fatal for the offline one: a file:// page
        // cannot fetch a sibling script, and `scripts/bundle-single.mjs` inlines
        // exactly one. So the offline build folds everything back into a single
        // chunk.
        //
        // Coherent rather than a workaround: the single-file bundle has no
        // server by construction, so it is always the "bundled" backend, and
        // the ordering that the dynamic import buys only matters under "api".
        inlineDynamicImports: mode === 'offline',
      },
    },
  },
  };
});
