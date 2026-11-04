// The browser's side of thermosteam's answers (OF-BLD-019 §4.2, D9).
//
// A question names a mixture on file and carries no number: a stream of a
// Proforma run (its artifact id and the stream's id), or a preset the service
// fills — `ethanol-water-azeotrope`, or `beer-at-titre-of` an ethanol titre
// record. The service reads the composition, temperature and pressure from
// what is on file, the Proforma worker asks thermosteam, and the answer is one
// `thermo_props` artifact (`core/openferment_core/thermo.py`). This file asks
// and reads; it computes no property. With the service down it says so, and
// nothing stands in for an answer (E.2). Shares lib/http.ts's call.
//
// The question and the answer are the service's own shapes, generated from its
// models into src/api/types.gen.ts (ADR-007): both doors answer the
// `thermo_props` artifact beside what it holds, which the service reads as
// `ThermoProps`, so a page reads each property as typed.
import type { components } from '@/api/types.gen';
import type { Train } from '@/data/types';
import { ServiceDown, ServiceRefused, call } from './http';

export { ServiceDown as ThermoDown, ServiceRefused as ThermoRefused };

type S = components['schemas'];

/** `POST /api/thermo/props`, and the same question as `GET` query parameters: a run's stream, or a preset, by ids and words. */
export type ThermoPropsRequest = S['ThermoPropsRequest'];
/** What a `thermo_props` artifact holds: thermosteam's answer for one mixture, in the library's units. */
export type ThermoProps = S['ThermoProps'];
/** `POST /api/thermo/props`: the `thermo_props` artifact beside what it holds. */
export type ThermoPropsAnswer = S['ThermoPropsAnswer'];
/** `GET /api/thermo/props`: the same pair as stored, or both null when nobody has asked the question here. */
export type ThermoPropsStored = S['ThermoPropsStored'];

export const BEER = 'beer-at-titre-of';
export const TITRE_FIELD = 'ethanol_titre';

const query = (q: ThermoPropsRequest) =>
  Object.entries(q)
    .filter(([, v]) => v)
    .map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`)
    .join('&');

/** The answer stored for this question, its artifact beside what it holds, or null when nobody has asked it here; starts no simulator. */
export const thermoStored = (q: ThermoPropsRequest, signal?: AbortSignal): Promise<ThermoPropsAnswer | null> =>
  call<ThermoPropsStored>(`/api/thermo/props?${query(q)}`, { signal }).then((r) =>
    r.artifact && r.props ? { artifact: r.artifact, props: r.props } : null,
  );

/** Ask thermosteam (or get the stored answer): one `thermo_props` artifact beside what it holds. */
export const thermoAsk = (q: ThermoPropsRequest, signal?: AbortSignal) =>
  call<ThermoPropsAnswer>('/api/thermo/props', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(q),
    signal,
  });

/** A property a Properties card shows: a number of the answer, or null where the library could not compute it. */
type PropertyKey = keyof Pick<ThermoProps, 'density' | 'Cp' | 'viscosity' | 'bubblePoint' | 'dewPoint'>;

/** The rows a Properties card shows, in order: the output key and its words. */
export const PROPERTY_ROWS: { key: PropertyKey; label: string }[] = [
  { key: 'density', label: 'Density' },
  { key: 'Cp', label: 'Heat capacity' },
  { key: 'viscosity', label: 'Viscosity' },
  { key: 'bubblePoint', label: 'Bubble point, at its pressure' },
  { key: 'dewPoint', label: 'Dew point, at its pressure' },
];

/**
 * The two streams of a train a Properties card opens on: the broth (the
 * outlet carrying the most product from the first unit on the product's path
 * that forms it) and the product stream. Which streams to ask about is a
 * choice of the page; every number shown is the service's.
 */
export function trainSubjects(train: Train): { role: string; streamId: string }[] {
  const out: { role: string; streamId: string }[] = [];
  const product = train.product;
  const byId = new Map(train.streams.map((s) => [s.id, s]));
  const forms = product
    ? train.units.find((u) => u.onPath && (u.productIn ?? 0) <= 0 && (u.productOut ?? 0) > 0)
    : undefined;
  if (forms && product) {
    const broth = [...forms.outs].sort((a, b) => (byId.get(b)?.massFlows[product] ?? 0) - (byId.get(a)?.massFlows[product] ?? 0))[0];
    if (broth) out.push({ role: 'Broth', streamId: broth });
  }
  if (train.productStream && byId.has(train.productStream) && !out.some((s) => s.streamId === train.productStream))
    out.push({ role: 'Product', streamId: train.productStream });
  return out;
}
