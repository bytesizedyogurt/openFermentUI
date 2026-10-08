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
    // The dev server answers no cross-site request at all: no page on another
    // origin gets a preflight approved, so none can send the header below.
    cors: false,
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
        // Tells the service which address the page is on, as X-Forwarded-Host,
        // which its guard compares with the page's Origin before a change
        // (core/openferment_core/guard.py, OF-BLD-012 §B.6). Set from the Host
        // the browser used and OVERWRITING any value the request carried:
        // `xfwd` would keep a forged one.
        configure: (proxy) => {
          proxy.on('proxyReq', (proxyReq, req) => {
            if (req.headers.host) proxyReq.setHeader('x-forwarded-host', req.headers.host);
          });
        },
      },
    },
  },
});
