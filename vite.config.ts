import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  base: './',
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  build: {
    chunkSizeWarningLimit: 1500,
  },
  server: {
    // OF-BLD-007 §8 — /api goes to openferment-core on localhost. Dev only.
    // A build reaches the service one of two ways: served by openferment-core
    // itself at / (OF-BLD-012 §B.4), where /api is the same origin and needs no
    // proxy; or as the `bundle:single` file with no server behind it, where
    // src/lib/postdoc.ts says so plainly when the fetch fails rather than
    // pretending the service is there.
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // Says which address the page is on (X-Forwarded-Host), which the
        // service's guard compares with the page's Origin before a change
        // (core/openferment_core/guard.py, OF-BLD-012 §B.6).
        xfwd: true,
      },
    },
  },
});
