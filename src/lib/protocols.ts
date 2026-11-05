// A project's protocols, the browser's side (alpha 2.2 E.12; ADR-017; core/openferment_core/protocols.py):
//
//   GET  /api/protocols                  every protocol the project keeps, each whole with every version
//   GET  /api/protocols/{id}             one protocol, whole
//   POST /api/protocols                  a protocol made once under its id, in a person's name
//   POST /api/protocols/{id}/versions    a new version kept in a person's name and made the current one
//
// A version is kept as it was kept: the service writes its keeper and time (`by`, `at`) over what the page sends, a
// version the protocol holds already is refused in words, and nothing here takes a protocol or a version out. A
// step names the skills a person needs to do it by their ids in the project's skill catalogue
// (lib/catalogues.ts, `Skill`), and the service refuses in words a step naming a skill the catalogue does not hold.
// With the service down a call says so (ServiceDown); a refusal comes back in the service's words (ServiceRefused).
//
// Every shape here is the service's own, generated from its models into src/api/types.gen.ts (ADR-007). A protocol
// is served whole, so every field arrives, an absent one as null; the generated types name a field with a default as
// one a reader may find absent, since a keep's body takes the same models, so a reader reads a version's lists with
// `?? []` where it stands. A screen that names a protocol by its address reads it through the store's `useProtocol`,
// which asks `protocolOf` for one made after the page opened.
import type { components } from '@/api/types.gen';
import { ServiceDown, ServiceRefused, call } from './http';

type S = components['schemas'];

/** A protocol the lab writes: its title, category, biosafety level and purpose, and every version kept of it. */
export type Protocol = S['Protocol'];
/** One version of a protocol: its base batch, materials, equipment, safety notes, steps and references. */
export type ProtocolVersion = S['ProtocolVersion'];
/** One step of a version: its words, which may bind a material's amount, its timer, checks, refs and skills. */
export type Step = S['Step'];
/** One material of a version, its amount written for the base batch, with how it scales and its rounding. */
export type Material = S['Material'];
/** A material's stock solution: the concentration a step's `{{stock:…}}` binding reads. */
export type MaterialStock = S['MaterialStock'];
/** The batch a version's amounts are written for. */
export type BaseBatch = S['BaseBatch'];
/** The minutes a run of a version takes, active and in all. */
export type EstMinutes = S['EstMinutes'];
/** A paper, a record or a note a version rests on. */
export type ProtocolReference = S['ProtocolReference'];
/** What kind of protocol it is: media, culture, analytics, harvest, fermentation or a standing procedure. */
export type ProtocolCategory = Protocol['category'];
/** How a material's amount scales with the batch: with its volume, with its biomass, or not at all. */
export type ScalingClass = Material['scaling'];
/** `POST /api/protocols`: one protocol and who keeps it. */
export type ProtocolKeep = S['ProtocolKeep'];
/** `POST /api/protocols/{id}/versions`: one version and who keeps it. */
export type ProtocolVersionKeep = S['ProtocolVersionKeep'];

export { ServiceDown as ProtocolsDown, ServiceRefused as ProtocolsRefused };

const id = (s: string) => encodeURIComponent(s);
const posted = (body: unknown): RequestInit => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
});

/** The open project's protocols, by id, each whole. */
export const listProtocols = (signal?: AbortSignal) => call<Protocol[]>('/api/protocols', { signal });

/** One of the open project's protocols, whole. */
export const protocolOf = (protocolId: string, signal?: AbortSignal) =>
  call<Protocol>(`/api/protocols/${id(protocolId)}`, { signal });

/** A protocol made in the open project in `asked.by`'s name: the protocol whole, as kept. */
export const makeProtocol = (asked: ProtocolKeep) => call<Protocol>('/api/protocols', posted(asked));

/** A new version kept in `asked.by`'s name and made the protocol's current one: the protocol whole, as it now stands. */
export const keepVersion = (protocolId: string, asked: ProtocolVersionKeep) =>
  call<Protocol>(`/api/protocols/${id(protocolId)}/versions`, posted(asked));
