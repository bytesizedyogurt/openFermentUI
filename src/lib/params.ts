// The browser's side of the parameter panel (OF-BLD-020 §2.1–§2.2, D2–D4).
//
// Two calls, neither of which keeps anything:
//
//   GET  /api/params/{scope}?flowsheet=&host=&fits=&vesselType=&strain=&…   a scope's specs and
//        each value as the service binds it now, with its source
//        (`ParamScope`);
//   POST /api/params/{scope}/resolve   a person's overrides laid on, each sent
//        as a typed quantity with its origin (`inputsOf`) and taken as an
//        assumption by the person it names, bound as a run of the scope
//        binds them (a refusal is the run's, in its words), with every value
//        outside its bounds said in words and the basis inputs a run adds
//        for them (`ParamResolveResult`).
//
// A scope is `proforma:<scenario id>`, `fermos:family:<id>`,
// `fermos:vessel:<simulation id>`, `fermos:forecast:<kinetic fit id>` or
// `pureos:unit:<train>:<unit>` (with the train, OF-BLD-020 §5.3). What a call starts depends on the scope
// (OF-BLD-020 §2.R, finding 7): a `proforma:` scope binds only and starts no
// worker; a `fermos:vessel:` scope reads BioSTEAM's defaults through the
// Proforma worker, once per process, so its first read on a cold service
// starts that worker and waits for it. With the
// service down these say so (ServiceDown), and a refusal comes back in the
// service's words (ServiceRefused); nothing stands in for an answer (E.2). The
// overrides themselves are the project's rows (`parameterOverrides`), and a
// write the service has not acknowledged waits in the outbox.
//
// AN OVERRIDE BECOMES AN INPUT HERE ALONE (alpha 2.2 D2). The browser keeps a
// person's change as an `Override`; every request that carries changes (the
// resolve here, fermOS's bind, simulation, vessel and forecast, pureOS's train
// run, Proforma's run) sends them as typed inputs through `inputsOf`, each in
// the unit its parameter is in, and the service converts each back into that
// Override at its door.
import type { components } from '@/api/types.gen';
import type { EngineInput } from './studies';
import { ServiceDown, ServiceRefused, call } from './http';

type S = components['schemas'];

/** One parameter as its model, unit or flowsheet declares it, with its bounds and the reason for them. */
export type ParameterSpec = S['ParameterSpec'];
/** A parameter's value in one scope, with where it came from. */
export type ParameterValue = S['ParameterValue'];
/**
 * A person's change to one parameter of one scope, kept in the project's rows and sent with every request the scope
 * makes. The service serves a row as the page kept it, so a row kept before `origin` was written carries none, and it
 * reads as a person's assumption here as on the service (`inputsOf`).
 */
export type Override = S['Override'];
/** `GET /api/params/{scope}`: a scope's specs with their current values. */
export type ParamScope = S['ParamScope'];
/** `POST /api/params/{scope}/resolve`, and what it answers. Runs nothing. */
export type ParamResolveRequest = S['ParamResolveRequest'];
export type ParamResolveResult = S['ParamResolveResult'];
/** pureOS's train, which a unit scope is asked with (src/lib/pureos.ts makes one). */
type TrainSpec = S['TrainSpec'];

export { ServiceDown as ParamsDown, ServiceRefused as ParamsRefused };

/** What a scope is asked with besides its name: a Proforma scenario names its flowsheet (one not yet saved binds by it, ADR-014); host and fits bind as Proforma's binding does; a vessel scope names the vessel type its design is (OF-BLD-020 §4.2); a family scope binds as a simulation binds (§3.3). */
export interface ParamAsk {
  flowsheet?: string | null;
  host?: string | null;
  fits?: Record<string, string>;
  vesselType?: 'stirred-tank' | 'bubble-column' | null;
  // fermOS's family scope (OF-BLD-020 §3.2–§3.3), bound as a simulation
  // binds: the strain whose records bind (none: every strain the evidence
  // pool holds), the product, the sugar, the fit a person chose, where the
  // simulation starts and the run-length preset.
  strain?: string | null;
  product?: string | null;
  sugar?: string | null;
  fit?: string | null;
  startFrom?: string | null;
  durationPreset?: 'until-sugar-runs-out' | 'fit-length' | null;
  /** A Proforma scenario on `custom_train_v1` (OF-BLD-020 §6.1): the vessel design and the train run it is built from. */
  vessel?: string | null;
  trainRun?: string | null;
  // pureOS's unit scope (OF-BLD-020 §5.3): the whole train the unit belongs
  // to, so its per-component keys expand over the train's chemicals and its
  // records bind by its program and product (`?train=` as JSON on the GET,
  // `train` in the resolve's body), and the unit's catalogue type.
  train?: TrainSpec | null;
  unitType?: string | null;
}

/** The fermOS fields of an ask, as query parameters and as the resolve's body fields alike. */
const FERMOS_ASK = ['strain', 'product', 'sugar', 'fit', 'startFrom', 'durationPreset'] as const;

/** A scope's path: each id between the colons encoded, the colons kept (`params.parse_scope`'s forms). */
export const scopePath = (scope: string) => `/api/params/${scope.split(':').map(encodeURIComponent).join(':')}`;

const askQuery = (ask: ParamAsk) => {
  const q = new URLSearchParams();
  if (ask.flowsheet) q.set('flowsheet', ask.flowsheet);
  if (ask.host) q.set('host', ask.host);
  if (ask.fits && Object.keys(ask.fits).length > 0) q.set('fits', JSON.stringify(ask.fits));
  if (ask.vesselType) q.set('vesselType', ask.vesselType);
  for (const k of FERMOS_ASK) {
    const v = ask[k];
    if (v) q.set(k, v);
  }
  if (ask.vessel) q.set('vessel', ask.vessel);
  if (ask.trainRun) q.set('trainRun', ask.trainRun);
  if (ask.unitType) q.set('unitType', ask.unitType);
  if (ask.train) q.set('train', JSON.stringify(ask.train));
  const s = q.toString();
  return s ? `?${s}` : '';
};

/** GET a scope's parameters, each with its value and source as the service binds it now. */
export const paramScope = (scope: string, ask: ParamAsk = {}, signal?: AbortSignal) =>
  call<ParamScope>(`${scopePath(scope)}${askQuery(ask)}`, { signal });

/**
 * A person's changes as the inputs a request sends: each Override's key, and a
 * quantity holding its value, low and high in the unit its parameter is in (the
 * scope's `specs`: the key's own spec, or for a key expanded per item,
 * `<key>.<item>`, its template's), with the person or the model that set it,
 * the day and the note as its origin, and a deposition's reading with its ref
 * and its depositor. The one place an Override becomes an
 * input (core/tests/standins.py's `as_inputs` mirrors it); a key the specs do
 * not name goes with no unit, and the service says why it cannot stand.
 */
export function inputsOf(overrides: Override[], specs: Pick<ParameterSpec, 'key' | 'unit'>[]): EngineInput[] {
  const unit = new Map(specs.map((s) => [s.key, s.unit]));
  return overrides.map((o) => ({
    name: o.key,
    quantity: {
      value: o.value,
      unit: unit.get(o.key) ?? unit.get(o.key.split('.')[0]) ?? '',
      ...(o.low != null ? { low: o.low } : {}),
      ...(o.high != null ? { high: o.high } : {}),
      origin: {
        kind: o.origin ?? 'person-assumption',
        by: o.by,
        at: o.at,
        ...(o.note ? { note: o.note } : {}),
        // A deposition's reading names itself (`<deposition id>/<entry id>`).
        ...(o.origin === 'measurement' && o.ref ? { ref: o.ref } : {}),
      },
    },
  }));
}

/** The resolve request the panel posts: the scope's overrides as inputs in its specs' units, with what the caller binds by. */
export function resolveRequest(overrides: Override[], specs: ParameterSpec[], ask: ParamAsk = {}): ParamResolveRequest {
  return {
    inputs: inputsOf(overrides, specs),
    ...(ask.flowsheet ? { flowsheet: ask.flowsheet } : {}),
    ...(ask.host ? { host: ask.host } : {}),
    ...(ask.fits && Object.keys(ask.fits).length > 0 ? { fits: ask.fits } : {}),
    ...(ask.vesselType ? { vesselType: ask.vesselType } : {}),
    ...Object.fromEntries(FERMOS_ASK.filter((k) => ask[k]).map((k) => [k, ask[k]])),
    ...(ask.vessel ? { vessel: ask.vessel } : {}),
    ...(ask.trainRun ? { trainRun: ask.trainRun } : {}),
    ...(ask.unitType ? { unitType: ask.unitType } : {}),
    ...(ask.train ? { train: ask.train } : {}),
  };
}

/** POST a person's overrides to their scope, each in the unit its spec names: the values with the overrides laid on, and every value outside its bounds, in words. */
export const resolveParams = (scope: string, overrides: Override[], specs: ParameterSpec[], ask: ParamAsk = {}, signal?: AbortSignal) =>
  call<ParamResolveResult>(`${scopePath(scope)}/resolve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(resolveRequest(overrides, specs, ask)),
    signal,
  });
