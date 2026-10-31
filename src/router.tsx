// Hash-based router (OF-DES-001 §13.2) — self-contained, no history API,
// so deep links survive inside an embedded artifact frame.
//
// A PROJECT'S VIEWS (execution prompt §8.5). `/p/:project` is a project's home,
// and `/p/:project/<path>` a module screen as a view inside that project. The
// prefix is read off here: `project` names it, and `path` and `segments` are
// the module's own, so every screen reads the path it always read. A link or a
// navigation to a plain path from inside a project stays inside it.
import { useEffect, useState } from 'react';

export interface Route {
  path: string; // "/biorepo/paper/SP-004", the project's prefix read off
  segments: string[];
  query: URLSearchParams;
  hash: string; // full raw hash
  /** The project the address names (`/p/:project/...`), or null. */
  project: string | null;
}

const PREFIX = /^\/p\/([^/?]+)(\/[^?]*)?$/;

function parseHash(): Route {
  const raw = window.location.hash.replace(/^#/, '') || '/';
  const [pathPart, queryPart] = raw.split('?');
  const whole = pathPart || '/';
  const named = PREFIX.exec(whole);
  const path = named ? named[2] || '/' : whole;
  return {
    path,
    segments: path.split('/').filter(Boolean),
    query: new URLSearchParams(queryPart ?? ''),
    hash: raw,
    project: named ? decodeURIComponent(named[1]) : null,
  };
}

/** The project the current address names, or null. */
function addressedProject(): string | null {
  if (typeof window === 'undefined') return null;
  return parseHash().project;
}

/** `to` inside the project the address names, when it is a plain app path. */
export function inProject(to: string, project: string | null = addressedProject()): string {
  if (!project || !to.startsWith('/') || to.startsWith('/p/')) return to;
  return `/p/${encodeURIComponent(project)}${to === '/' ? '' : to}`;
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
  const target = to.startsWith('#') ? `#${inProject(to.slice(1))}` : `#${inProject(to)}`;
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

/** <a href> that routes internally; keeps middle-click / cmd-click semantics. */
export function href(path: string): string {
  return `#${inProject(path)}`;
}
