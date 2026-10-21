// The browser's side of the parameter panel (OF-BLD-020 §2.1–§2.2, D2–D4).
//
// Two calls, both binding only (no worker starts, nothing is kept):
//
//   GET  /api/params/{scope}?flowsheet=&host=&fits=   a scope's specs and
//        each value as the service binds it now, with its source
//        (`ParamScope`);
//   POST /api/params/{scope}/resolve   a person's overrides laid on, each an
//        assumption by the person it names, with every value outside its
//        bounds said in words (`ParamResolveResult`).
//
// A scope is `proforma:<scenario id>`, `fermos:family:<id>`,
// `fermos:vessel:<simulation id>` or `pureos:unit:<train>:<unit>`. With the
// service down these say so (RagDown), and a refusal comes back in the
// service's words (RagRefused); nothing stands in for an answer (E.2). The
// overrides themselves live in the store's Durable tier
// (`parameterOverrides`); the service keeps none.
import type { Override, ParamResolveRequest, ParamResolveResult, ParamScope } from '@/data/types';
import { RagDown, RagRefused, call } from './rag';

export { RagDown as ParamsDown, RagRefused as ParamsRefused };

/** What a scope is asked with besides its name: a Proforma scenario made here names its flowsheet; host and fits bind as Proforma's binding does. */
export interface ParamAsk {
  flowsheet?: string | null;
  host?: string | null;
  fits?: Record<string, string>;
}

/** A scope's path: each id between the colons encoded, the colons kept (`params.parse_scope`'s forms). */
export const scopePath = (scope: string) => `/api/params/${scope.split(':').map(encodeURIComponent).join(':')}`;

const askQuery = (ask: ParamAsk) => {
  const q = new URLSearchParams();
  if (ask.flowsheet) q.set('flowsheet', ask.flowsheet);
  if (ask.host) q.set('host', ask.host);
  if (ask.fits && Object.keys(ask.fits).length > 0) q.set('fits', JSON.stringify(ask.fits));
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
