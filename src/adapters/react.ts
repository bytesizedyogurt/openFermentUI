/**
 * The React binding for the five adapters — one hook, and nothing else.
 *
 * ── WHY THIS IS A SEPARATE FILE ───────────────────────────────────────────
 * `types.ts`, `fixture/` and `mcp/` are importable by the Node scripts:
 * `check:corpus`, `check:seed` and the capture scripts all pull the data layer
 * in with no DOM and no React in the picture. This module imports React, so it
 * is kept out of `index.ts`'s export surface — a screen reaches for it by name,
 * and a script that imports `@/adapters` never drags React in behind it.
 *
 * ── WHY A HOOK AT ALL ─────────────────────────────────────────────────────
 * Every method on the seam is async, on purpose and permanently: the fixture
 * has no latency and a corpus server, a COBRApy solve and a BioSTEAM cash flow
 * all do (`types.ts`, "EVERY METHOD IS ASYNC"). Screens that read those
 * methods therefore have three states rather than one, and six screens each
 * inventing their own `useState`/`useEffect` pair is six chances to forget the
 * cancellation guard or to conflate "still loading" with "not there".
 *
 * That last conflation is the one that matters and it is not hypothetical.
 * `DesignDetail` rendered "Design not found" for any id it could not resolve;
 * with an awaited read, the first frame of EVERY design is an unresolved id,
 * so the honest-looking screen would have opened by telling the reader their
 * design does not exist and then quietly replacing it. `Notary` had the same
 * shape in arithmetic: `0 of 0 designs are publishable` reads as a finding
 * about the corpus and would have been a statement about a promise. The three
 * states are distinct here so that a screen cannot accidentally render one as
 * another.
 */
import { useEffect, useRef, useState } from 'react';
import type { DependencyList } from 'react';
import type { AdapterResponse } from './types';

/**
 * Where an adapter read has got to.
 *
 * A discriminated union rather than `{ data, loading, error }`, so that a
 * screen cannot read `data` without having said which case it is in. `failed`
 * rather than `error` as the tag, because `state.error` is then the Error and
 * `state.status === 'error'` never reads as a field access on it.
 */
export type AdapterState<T> =
  | { readonly status: 'loading' }
  | {
      readonly status: 'ready';
      readonly data: T;
      /**
       * The response's `notice`, carried through rather than dropped. A caller
       * that renders a payload with a notice on it must render the notice —
       * `AdapterResponse` says so — and a hook that discarded it would make
       * that rule unfollowable.
       */
      readonly notice?: string;
    }
  | { readonly status: 'failed'; readonly error: Error };

/**
 * Read one adapter method into component state.
 *
 * `load` is called on mount and whenever `deps` change. It is held in a ref so
 * that an inline arrow — which is what every call site passes — does not
 * re-fire the effect on every render; `deps` is the whole of what decides when
 * the read runs again, exactly as it would be for `useMemo`.
 *
 * A read that is superseded (deps changed) or unmounted is DROPPED, not
 * applied: `alive` is checked after the await, so a slow response for an old
 * design id cannot arrive late and overwrite the new one. The fixture resolves
 * in a microtask and this never happens today, which is precisely why it has
 * to be written now rather than discovered against a server.
 *
 * A rejection lands in `failed` and is not swallowed. The seam has two failure
 * classes — `NotImplementedError` from the MCP backend and `AdapterRefusal`
 * where answering would mean manufacturing an artifact — and both carry a
 * message written to be read. Screens render `state.error.message` rather than
 * a generic apology, so a missing subsystem is visible at the place that
 * wanted it.
 */
export function useAdapterData<T>(
  load: () => Promise<AdapterResponse<T>>,
  deps: DependencyList,
): AdapterState<T> {
  const [state, setState] = useState<AdapterState<T>>({ status: 'loading' });
  const loadRef = useRef(load);
  loadRef.current = load;

  useEffect(() => {
    let alive = true;
    // Reset on a deps change, so a screen showing design A does not show A's
    // data under B's heading while B is in flight.
    setState({ status: 'loading' });
    loadRef.current().then(
      (res) => {
        if (alive) setState({ status: 'ready', data: res.data, notice: res.notice });
      },
      (err: unknown) => {
        if (alive) {
          setState({
            status: 'failed',
            error: err instanceof Error ? err : new Error(String(err)),
          });
        }
      },
    );
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return state;
}
