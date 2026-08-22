// Hash-based router (OF-DES-001 §13.2) — self-contained, no history API,
// so deep links survive inside an embedded artifact frame.
import { useEffect, useState, useCallback } from 'react';
import { flushSync } from 'react-dom';

export interface Route {
  path: string; // "/trawl/sources/SP-004"
  segments: string[];
  query: URLSearchParams;
  hash: string; // full raw hash
  /**
   * The `#frag` after the route, if any — `/parchment#PF-003` gives `PF-003`.
   *
   * A hash router already spends the URL's one fragment on the route, so a
   * second `#` is the only way to anchor within a screen. It used to be left
   * in `path`, which meant `segments` was `['parchment#PF-003']`, no `case`
   * matched, and three families of link — the demo patent chips, the FTO flag
   * and the disclosure back-links — landed on "Route not found".
   */
  fragment: string;
}

function parseHash(): Route {
  const raw = window.location.hash.replace(/^#/, '') || '/';
  // Fragment first, then query — `/a?b=1#c` has to yield path `/a`, query
  // `b=1` and fragment `c`, not a query of `b=1#c`.
  const cut = raw.indexOf('#');
  const route = cut === -1 ? raw : raw.slice(0, cut);
  const fragment = cut === -1 ? '' : raw.slice(cut + 1);
  const [pathPart, queryPart] = route.split('?');
  const path = pathPart || '/';
  return {
    path,
    segments: path.split('/').filter(Boolean),
    query: new URLSearchParams(queryPart ?? ''),
    hash: raw,
    fragment,
  };
}

let listeners: (() => void)[] = [];

/**
 * Route changes go through a View Transition where the browser has one.
 *
 * Hooked HERE and not in `navigate()`, which is the obvious-looking place and
 * the wrong one: 120 links in this build are plain `<a href={href(...)}>` and
 * never call `navigate` at all. The `hashchange` listener is the single funnel
 * every navigation passes through, whichever way it started.
 *
 * What it buys is not decoration. Two elements carry `view-transition-name`s —
 * the page title and the active rail item — so they MORPH between screens
 * instead of disappearing and reappearing somewhere else. That tells a reader
 * the two screens are the same application in a different place, which is the
 * one thing a hash router is otherwise bad at saying.
 *
 * Feature-detected, no polyfill, and inert under reduced motion: the CSS that
 * drives the transition is disabled by `[data-reduced-motion]`, so on that
 * setting the callback still runs and simply swaps without animating.
 */
function announce() {
  listeners.forEach((l) => l());
}

window.addEventListener('hashchange', () => {
  const doc = document as Document & {
    startViewTransition?: (cb: () => void) => { finished: Promise<void> };
  };
  if (typeof doc.startViewTransition !== 'function') {
    announce();
    return;
  }
  doc.startViewTransition(() => {
    // React must have committed before the browser takes its "after"
    // screenshot, so the swap happens synchronously inside the callback.
    flushSync(announce);
  });
});

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
  // ?record= is not one: it filters the table down to that row rather than
  // scrolling to it, so suppressing the reset left the reader mid-page on a
  // one-row table. A `#frag` IS one, and scrolling to it is `useFragmentScroll`
  // below rather than here, because most navigation is a plain <a href> that
  // never calls this function.
  if (!target.includes('?span=') && !target.slice(1).includes('#')) {
    requestAnimationFrame(() => {
      document.getElementById('of-main')?.scrollTo({ top: 0 });
    });
  }
}

/**
 * Bring `#frag` into view once the screen that owns it has rendered.
 *
 * Mounted once in the shell rather than per screen: the anchor is a property
 * of the address, and a screen that grows an `id` should not also have to
 * remember to wire up scrolling to it. Two frames, because the target is
 * usually rendered by the same commit that changed the route.
 */
export function useFragmentScroll(fragment: string): void {
  useEffect(() => {
    if (!fragment) return;
    let raf = 0;
    const attempt = (tries: number) => {
      const el = document.getElementById(fragment);
      if (el) {
        el.scrollIntoView({ block: 'start' });
        return;
      }
      if (tries > 0) raf = requestAnimationFrame(() => attempt(tries - 1));
    };
    raf = requestAnimationFrame(() => attempt(3));
    return () => cancelAnimationFrame(raf);
  }, [fragment]);
}

export function useNavigate() {
  return useCallback(navigate, []);
}

/** <a href> that routes internally; keeps middle-click / cmd-click semantics. */
export function href(path: string): string {
  return `#${path}`;
}
