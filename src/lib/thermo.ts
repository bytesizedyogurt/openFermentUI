// The browser's side of thermosteam's answers (OF-BLD-019 §4.2, D9).
//
// A question names a mixture on file and carries no number: a stream of a
// Proforma run (its artifact id and the stream's id), or a preset the service
// fills — `ethanol-water-azeotrope`, or `beer-at-titre-of` an ethanol titre
// record. The service reads the composition, temperature and pressure from
// what is on file, the Proforma worker asks thermosteam, and the answer is one
// `thermo_props` artifact (`core/openferment_core/thermo.py`). This file asks
// and reads; it computes no property. With the service down it says so, and
// nothing stands in for an answer (E.2). Shares lib/rag.ts's call.
import type { Artifact, ThermoProps, ThermoPropsRequest, Train } from '@/data/types';
import { ServiceDown, ServiceRefused, call } from './http';

export { ServiceDown as ThermoDown, ServiceRefused as ThermoRefused };

export const BEER = 'beer-at-titre-of';
export const TITRE_FIELD = 'ethanol_titre';

const query = (q: ThermoPropsRequest) =>
  Object.entries(q)
    .filter(([, v]) => v)
    .map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`)
    .join('&');

/** The answer stored for this question, or null when nobody has asked it here; starts no simulator. */
export const thermoStored = (q: ThermoPropsRequest, signal?: AbortSignal) =>
  call<{ artifact: Artifact | null }>(`/api/thermo/props?${query(q)}`, { signal }).then((r) => r.artifact);

/** Ask thermosteam (or get the stored answer): one `thermo_props` artifact. */
export const thermoAsk = (q: ThermoPropsRequest, signal?: AbortSignal) =>
  call<Artifact>('/api/thermo/props', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(q),
    signal,
  });

/** The answer an artifact holds, as the service wrote it. */
export const propsOf = (a: Artifact) => a.output as unknown as ThermoProps;

/** The rows a Properties card shows, in order: the output key and its words. */
export const PROPERTY_ROWS: { key: 'density' | 'Cp' | 'viscosity' | 'bubblePoint' | 'dewPoint'; label: string }[] = [
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
