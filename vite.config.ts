import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig(({ mode }) => ({
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
}));
