// Hash-based router (OF-DES-001 §13.2) — self-contained, no history API,
// so deep links survive inside an embedded artifact frame.
import { useEffect, useState, useCallback } from 'react';

export interface Route {
  path: string; // "/biorepo/paper/SP-004"
  segments: string[];
  query: URLSearchParams;
  hash: string; // full raw hash
}

function parseHash(): Route {
  const raw = window.location.hash.replace(/^#/, '') || '/';
  const [pathPart, queryPart] = raw.split('?');
  const path = pathPart || '/';
  return {
    path,
    segments: path.split('/').filter(Boolean),
    query: new URLSearchParams(queryPart ?? ''),
    hash: raw,
  };
}

let listeners: (() => void)[] = [];
// Guarded so this module can be imported outside a browser. The check scripts
// pull in components that transitively reach the router, and a bare
// addEventListener at module scope makes the whole graph unimportable in Node
// for no benefit — the listener is useless there anyway.
if (typeof window !== 'undefined') {
  window.addEventListener('hashchange', () => listeners.forEach((l) => l()));
}

export function useRoute(): Route {
  const [route, setRoute] = useState<Route>(parseHash);
  useEffect(() => {
    const l = () => setRoute(parseHash());
    listeners.push(l);
    return () => {
      listeners = listeners.filter((x) => x !== l);
    };
  }, []);
  return route;
}

export function navigate(to: string, opts?: { replace?: boolean }) {
  const target = to.startsWith('#') ? to : `#${to}`;
  if (opts?.replace) {
    window.location.replace(target);
  } else {
    window.location.hash = target.slice(1);
  }
  // Scroll the main region to top on navigation, but keep anchored deep links.
  if (!target.includes('?span=') && !target.includes('?record=')) {
    requestAnimationFrame(() => {
      document.getElementById('of-main')?.scrollTo({ top: 0 });
    });
  }
}

export function useNavigate() {
  return useCallback(navigate, []);
}

/** <a href> that routes internally; keeps middle-click / cmd-click semantics. */
export function href(path: string): string {
  return `#${path}`;
}
