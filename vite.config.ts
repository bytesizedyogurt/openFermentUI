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
    // OF-BLD-007 §8 — /api goes to openferment-core on localhost. Dev only:
    // the built artifact is a single file with no server behind it, and
    // src/lib/postdoc.ts says so plainly when the fetch fails rather than
    // pretending the service is there.
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
