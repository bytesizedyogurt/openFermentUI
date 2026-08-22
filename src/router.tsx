// Hash-based router (OF-DES-001 §13.2) — self-contained, no history API,
// so deep links survive inside an embedded artifact frame.
import { useEffect, useState, useCallback, useRef } from 'react';
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

// ── THE TRAIL ──────────────────────────────────────────────────────────────
//
// Where you were, so you can get back to it.
//
// Two things were wrong and the second is the one that matters. Browser back
// returned to the right route but at scroll position zero — you could be two
// thousand pixels down a six-thousand-pixel statement of account, click a unit,
// come back, and be at the top with no idea where you had been. And inside the
// shared artifact the visible back button belongs to the HOST page, not to this
// application in its iframe, so for anybody reading the published build there
// was no back at all.
//
// ── WHY A TRAIL AND NOT THE HISTORY API ───────────────────────────────────
//
// This router's own header says it: self-contained, no history API, so deep
// links survive inside an embedded frame. `history.pushState` would let the
// browser carry the scroll position for us and is exactly what that constraint
// rules out. So the trail is held in memory, keyed on the route path, and
// `hashchange` — already the single funnel every navigation passes through — is
// where it is maintained.
//
// ── WHAT COUNTS AS GOING BACK ─────────────────────────────────────────────
//
// A hash change whose path already appears earlier in the trail. That covers
// the browser's own back button, a keyboard chord, and the in-page control
// alike, without any of them having to announce themselves. Everything else is
// a step forward and lands at the top of the new screen, which is what a reader
// expects of a screen they have not seen before.

interface TrailEntry {
  path: string;
  hash: string;
  /** Where `#of-main` was scrolled to when this screen was left. */
  scrollTop: number;
  /** The screen's `<h1>`, filled in after it renders. */
  label: string;
}

/** The scroll container every screen lives in. */
const main = (): HTMLElement | null => document.getElementById('of-main');

let trail: TrailEntry[] = [{ path: parseHash().path, hash: parseHash().hash, scrollTop: 0, label: '' }];

/** Scroll to apply once the incoming screen has committed. `null` = top. */
let pendingScroll: number | null = null;

/**
 * Fold the new address into the trail and decide where it should land.
 *
 * Called from the `hashchange` listener BEFORE React is told anything, so the
 * outgoing screen's scroll position is still readable off the DOM.
 */
function recordNavigation(): void {
  const next = parseHash();
  const top = trail[trail.length - 1];

  // A fragment or a query change on the same path is not a navigation between
  // screens — it is a move within one, and it must not overwrite the scroll
  // position the trail is holding for that screen.
  if (top && top.path === next.path) {
    top.hash = next.hash;
    pendingScroll = null;
    return;
  }

  if (top) top.scrollTop = main()?.scrollTop ?? 0;

  const seen = trail.findIndex((e) => e.path === next.path);
  if (seen !== -1 && seen < trail.length - 1) {
    // Going back. Everything after the screen we are returning to is no longer
    // ahead of us, and the scroll we saved for it is where the reader was.
    trail = trail.slice(0, seen + 1);
    pendingScroll = trail[trail.length - 1].scrollTop;
  } else {
    trail.push({ path: next.path, hash: next.hash, scrollTop: 0, label: '' });
    pendingScroll = null;
  }
}

/**
 * Put the reader where they were, or at the top of somewhere new.
 *
 * `navigate()` used to do this, which meant it only ever ran for the small
 * fraction of navigations that go through it — 120 links in this build are
 * plain `<a href>`. It is here now, on the one funnel, so every navigation is
 * treated the same way whichever way it started.
 *
 * The two exemptions are the ones `navigate()` carried and they are unchanged:
 * `?span=` filters a table down to one row rather than scrolling to it, and a
 * `#frag` is handled by `useFragmentScroll`, which is taking the reader
 * somewhere specific already.
 */
function applyScroll(): void {
  const { hash } = parseHash();
  if (hash.includes('?span=') || hash.includes('#')) return;
  const top = pendingScroll ?? 0;
  requestAnimationFrame(() => main()?.scrollTo({ top }));
}

/** The screen behind this one, when there is one. */
export function previousEntry(): { to: string; label: string } | null {
  if (trail.length < 2) return null;
  const prev = trail[trail.length - 2];
  return { to: prev.hash || prev.path, label: prev.label };
}

/** Go back one screen. A no-op at the root of the trail. */
export function back(): void {
  const prev = previousEntry();
  if (!prev) return;
  navigate(prev.to);
}

/**
 * Name the screen the reader is on, so the trail can offer it by name later.
 *
 * A route knows its path immediately and its title only after the screen has
 * rendered, which is why this is written back rather than derived.
 */
export function labelCurrent(label: string): void {
  const top = trail[trail.length - 1];
  if (top && label) top.label = label;
}

/**
 * Re-render when the trail changes, so a back control can appear and disappear.
 *
 * The trail moves on exactly the same events the route does, so it rides the
 * same listener list rather than keeping its own.
 */
export function useBack(): { to: string; label: string } | null {
  const [entry, setEntry] = useState(previousEntry);
  useEffect(() => {
    const l = () => setEntry(previousEntry());
    listeners.push(l);
    return () => {
      listeners = listeners.filter((x) => x !== l);
    };
  }, []);
  return entry;
}



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
  // Before anything renders: the outgoing screen's scroll position is only
  // readable while it is still on screen.
  recordNavigation();
  const doc = document as Document & {
    startViewTransition?: (cb: () => void) => { finished: Promise<void> };
  };
  if (typeof doc.startViewTransition !== 'function') {
    announce();
    applyScroll();
    return;
  }
  doc.startViewTransition(() => {
    // React must have committed before the browser takes its "after"
    // screenshot, so the swap happens synchronously inside the callback.
    flushSync(announce);
    // Inside the callback too, so the transition's "after" screenshot is taken
    // at the restored position rather than at the top — otherwise the page
    // animates in and then jumps.
    applyScroll();
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
  // Scroll is NOT handled here any more. It used to be, which meant it ran only
  // for the navigations that came through this function — and most do not, since
  // 120 links in this build are plain `<a href={href(...)}>`. `applyScroll`, on
  // the `hashchange` funnel, now owns it for every navigation and can put a
  // reader back where they were instead of always at the top.
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

/**
 * Move focus to the new screen and say its name.
 *
 * A hash router changes the document without a page load, so a screen reader
 * is told nothing and the keyboard focus stays wherever it was — usually on a
 * rail link, meaning the next Tab continues through the navigation rather than
 * entering the content. Both were true here on all 79 routes.
 *
 * Focus goes to the page's `<h1>` rather than to the main region, because the
 * heading is what answers "where am I"; `PageHeader` gives it `tabIndex={-1}`
 * so it can receive focus without joining the tab order.
 *
 * Returns the announcement text for a polite live region. Two separate
 * mechanisms on purpose: moving focus reads the heading in most screen
 * readers, but not all, and the live region is what makes it reliable.
 */
export function useRouteAnnouncement(path: string, fragment: string): string {
  const [label, setLabel] = useState('');
  // The FIRST render is not a navigation. Taking focus on arrival would both
  // surprise a reader who has not asked to go anywhere and put the skip link
  // permanently out of reach, since it sits before the heading in the document
  // and Tab only moves forward.
  //
  // Tracked by comparing the PATH rather than by a "have I run yet" boolean.
  // StrictMode double-invokes effects, so the boolean flipped true on the first
  // pass and the second pass stole focus on arrival — the exact behaviour it
  // was written to prevent, and invisible in dev because both passes look the
  // same from outside.
  const seen = useRef(path);
  useEffect(() => {
    let raf = 0;
    const attempt = (tries: number) => {
      const h1 = document.querySelector<HTMLElement>('#of-main h1');
      if (h1) {
        const text = h1.textContent?.trim() ?? '';
        setLabel(text);
        // The trail can only offer "back to X" by name once X has rendered.
        labelCurrent(text);
        // Never steal focus from a fragment deep link — `useFragmentScroll` is
        // already taking the reader somewhere specific, and two things
        // competing for the viewport is worse than neither.
        if (!fragment && seen.current !== path) h1.focus({ preventScroll: true });
        seen.current = path;
        return;
      }
      if (tries > 0) raf = requestAnimationFrame(() => attempt(tries - 1));
    };
    raf = requestAnimationFrame(() => attempt(3));
    return () => cancelAnimationFrame(raf);
  }, [path, fragment]);
  return label;
}
