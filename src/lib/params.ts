// The browser's side of the parameter panel (OF-BLD-020 §2.1–§2.2, D2–D4).
//
// Two calls, neither of which keeps anything:
//
//   GET  /api/params/{scope}?flowsheet=&host=&fits=&vesselType=   a scope's specs and
//        each value as the service binds it now, with its source
//        (`ParamScope`);
//   POST /api/params/{scope}/resolve   a person's overrides laid on, each an
//        assumption by the person it names, bound as a run of the scope
//        binds them (a refusal is the run's, in its words), with every value
//        outside its bounds said in words and the basis inputs a run adds
//        for them (`ParamResolveResult`).
//
// A scope is `proforma:<scenario id>`, `fermos:family:<id>`,
// `fermos:vessel:<simulation id>` or `pureos:unit:<train>:<unit>`. What a
// call starts depends on the scope (OF-BLD-020 §2.R, finding 7): a
// `proforma:` scope binds only and starts no worker; a `fermos:vessel:`
// scope reads BioSTEAM's defaults through the Proforma worker, once per
// process, so its first read on a cold service starts that worker and waits
// for it. With the
// service down these say so (RagDown), and a refusal comes back in the
// service's words (RagRefused); nothing stands in for an answer (E.2). The
// overrides themselves live in the store's Durable tier
// (`parameterOverrides`); the service keeps none.
import type { Override, ParamResolveRequest, ParamResolveResult, ParamScope } from '@/data/types';
import { RagDown, RagRefused, call } from './rag';

export { RagDown as ParamsDown, RagRefused as ParamsRefused };

/** What a scope is asked with besides its name: a Proforma scenario made here names its flowsheet; host and fits bind as Proforma's binding does; a vessel scope names the vessel type its design is (OF-BLD-020 §4.2). */
export interface ParamAsk {
  flowsheet?: string | null;
  host?: string | null;
  fits?: Record<string, string>;
  vesselType?: 'stirred-tank' | 'bubble-column' | null;
}

/** A scope's path: each id between the colons encoded, the colons kept (`params.parse_scope`'s forms). */
export const scopePath = (scope: string) => `/api/params/${scope.split(':').map(encodeURIComponent).join(':')}`;

const askQuery = (ask: ParamAsk) => {
  const q = new URLSearchParams();
  if (ask.flowsheet) q.set('flowsheet', ask.flowsheet);
  if (ask.host) q.set('host', ask.host);
  if (ask.fits && Object.keys(ask.fits).length > 0) q.set('fits', JSON.stringify(ask.fits));
  if (ask.vesselType) q.set('vesselType', ask.vesselType);
  const s = q.toString();
  return s ? `?${s}` : '';
};

/** GET a scope's parameters, each with its value and source as the service binds it now. */
export const paramScope = (scope: string, ask: ParamAsk = {}, signal?: AbortSignal) =>
  call<ParamScope>(`${scopePath(scope)}${askQuery(ask)}`, { signal });

/** The resolve request the panel posts: the scope's overrides, with what the caller binds by. */
export function resolveRequest(overrides: Override[], ask: ParamAsk = {}): ParamResolveRequest {
  return {
    overrides,
    ...(ask.flowsheet ? { flowsheet: ask.flowsheet } : {}),
    ...(ask.host ? { host: ask.host } : {}),
    ...(ask.fits && Object.keys(ask.fits).length > 0 ? { fits: ask.fits } : {}),
    ...(ask.vesselType ? { vesselType: ask.vesselType } : {}),
  };
}

/** POST a person's overrides to their scope: the values with the overrides laid on, and every value outside its bounds, in words. */
export const resolveParams = (scope: string, overrides: Override[], ask: ParamAsk = {}, signal?: AbortSignal) =>
  call<ParamResolveResult>(`${scopePath(scope)}/resolve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(resolveRequest(overrides, ask)),
    signal,
  });
