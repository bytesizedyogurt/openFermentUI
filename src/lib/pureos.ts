// The browser's side of pureOS's trains (OF-BLD-019 §4.1, D1).
//
// The service reads a train from one `proforma.run` artifact's stream and
// unit tables (`core/openferment_core/pureos/__init__.py`); the browser shows it and
// computes nothing of its own: every mass, recovery and cumulative share on
// the page is a field the service sent. With the service down this says so,
// and nothing stands in for a train (E.2). Shares lib/http.ts's call.
//
// Every shape the service answers or takes here is generated from its models
// into src/api/types.gen.ts (ADR-007) and named below: a run's train and its
// units, a proposal with its reasons, the catalogue's unit types and their
// specs, a train as data with its validation, check and run, a train read
// from a run, and a train a model kept. A stream, a train on file and a vessel
// are named in lib/proforma.ts, which reads them for Proforma's pages too.
import type { components } from '@/api/types.gen';
import { ServiceDown, ServiceRefused, call } from './http';
import { inputsOf, type Override, type ParameterSpec } from './params';
import {
  keptReferenceRuns,
  proformaArtifact,
  proformaNewestRun,
  proformaScenarios,
  proformaShelf,
  retiredEntryOf,
  type StreamRow,
  type TrainSummary,
  type VesselSummary,
} from './proforma';
import { listRuns, titledConfiguration, type Artifact, type EngineInput } from './studies';

export { ServiceDown as PureosDown, ServiceRefused as PureosRefused };

type S = components['schemas'];

/** `GET /api/pureos/train/{key}`: a run's train as the service reads it from the run's stream and unit tables. */
export type Train = S['Train'];
/** One unit of a run's train, in run order, with the product's flow through it as the stream table states it. */
export type TrainUnit = S['TrainUnit'];
/** `POST /api/pureos/propose`: a product, a host and optionally an inlet, each by its id. */
export type ProposeRequest = S['ProposeRequest'];
/** What the written rules propose: a train with each unit's reason, or none with each property nothing holds. */
export type TrainProposal = S['TrainProposal'];
export type ProposalReason = S['ProposalReason'];
export type ProposalMissing = S['ProposalMissing'];
/** `GET /api/pureos/catalogue`: a unit type; `GET /api/pureos/catalogue/{id}/specs`: its specs with the class's defaults. */
export type UnitType = S['UnitType'];
export type UnitSpecs = S['UnitSpecs'];
/**
 * A train as data: its inlet, its units in order, each with the values a person typed for it. The service takes one
 * in a request that may leave its units out, so a reader takes a train's units through `unitsOf`.
 */
export type TrainSpec = S['TrainSpec'];
export type TrainUnitSpec = S['TrainUnitSpec'];
/** A value a person typed for one parameter of a train's place: an Override without its scope and key. */
export type TrainParam = S['TrainParam'];
/** `POST /api/pureos/train/validate`, and `/check`: every refusal at once, by its place. */
export type TrainValidation = S['TrainValidation'];
/** `POST /api/pureos/train/run`, and `/check`: the train, a person's values as typed inputs, and who asks. */
export type TrainRunRequest = S['TrainRunRequest'];
/** `POST /api/pureos/train/run`: the one `pureos.train_run` artifact, read; a stream's purity within it. */
export type TrainRun = S['TrainRun'];
export type StreamPurity = S['StreamPurity'];
/** `POST /api/pureos/train/from-run`: a kept run's units read into a train, and what it leaves out. */
export type TrainFromRunRequest = S['TrainFromRunRequest'];
export type TrainFromRun = S['TrainFromRun'];
/** `GET /api/pureos/trains-kept`: a train a model built, kept on the service. */
export type KeptTrain = S['KeptTrain'];

/** A train's units in order: each one it holds, and none when the train as sent left them out. */
export const unitsOf = (t: Pick<TrainSpec, 'units'>): TrainUnitSpec[] => t.units ?? [];

/** Every train on file. */
export const pureosTrains = (signal?: AbortSignal) => call<TrainSummary[]>('/api/pureos/trains', { signal });

/** One train: the newest run of a scenario, or one run by its artifact id. */
export const pureosTrain = (key: string, signal?: AbortSignal) =>
  call<Train>(`/api/pureos/train/${encodeURIComponent(key)}`, { signal });

/** Where a train opens: by its scenario when one claims the run, else by the run. */
export const trainPath = (t: { scenarioId: string | null; artifactId: string }) =>
  `/pureos/train/${encodeURIComponent(t.scenarioId ?? t.artifactId)}`;

/** The streams that enter or leave one unit, inlets first, in the unit's own order. */
export function streamsOf(train: Train, unit: TrainUnit | null): StreamRow[] {
  if (!unit) return train.streams;
  const byId = new Map(train.streams.map((s) => [s.id, s]));
  return [...unit.ins, ...unit.outs].map((id) => byId.get(id)).filter((s): s is StreamRow => !!s);
}

/** A stream's product flow as the run's table states it, or null when the run names no product. */
export const productIn = (train: Train, s: StreamRow): number | null =>
  train.product ? (s.massFlows[train.product] ?? 0) : null;

/** A share as a percentage, or the words for why there is none. */
export function share(v: number | null, digits = 1): string {
  return v == null || !Number.isFinite(v) ? '—' : `${(v * 100).toFixed(digits)}%`;
}

/**
 * OF-BLD-020 §7.2 — a train proposed by the service's written rules
 * (`core/openferment_core/pureos/proposer.py`): ids and words go out, and the
 * proposal comes back with every unit's reason, the property it read and the
 * artifact that holds it, or what is missing. The browser decides nothing.
 */
export const proposeTrain = (ask: ProposeRequest, signal?: AbortSignal) =>
  call<TrainProposal>('/api/pureos/propose', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(ask),
    signal,
  });

/** What a train's run was made from, in words the page shows beside its numbers. */
export const RUN_WORDS =
  'Read from the run Proforma priced: one artifact holds its stream and unit tables, and every number here is ' +
  'arithmetic over that stream table, done by the service. Nothing is typed and nothing is simulated again.';

// ── pureOS → Builder (OF-BLD-020 §5.3, D9, D10) ───────────────────────
//
// A train is data the browser holds and sends whole: its structure (the
// inlet's kind and source, the units in order, each with its catalogue type,
// its outlets' routes and what it reads from a flowsheet), and every value a
// person typed into its panels, which live in the store's
// `parameterOverrides` under the train's scopes
// (`pureos:unit:<train id>:<unit id | inlet>`) and are laid into the train's
// params as it is sent (`trainSpecOf`). A run or a check also sends each of
// those changes as a typed input named by its place (`trainInputs`, through
// lib/params.ts `inputsOf`, alpha 2.2 D2), which the service converts back
// into the Override of the place's scope at its door. The service validates
// the train, says what a run would refuse, runs it and keeps one
// `pureos.train_run` artifact and its run of the engine `train`; the browser
// shows the answer and computes nothing.

const post = <T>(path: string, body: unknown, signal?: AbortSignal) =>
  call<T>(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal });

/** The catalogue's unit types, in stage order (`GET /api/pureos/catalogue`): data, no simulator. */
export const pureosCatalogue = (signal?: AbortSignal) => call<UnitType[]>('/api/pureos/catalogue', { signal });

/** One unit type's parameters with BioSTEAM's defaults read from its code (`GET /api/pureos/catalogue/{id}/specs`). */
export const unitSpecs = (typeId: string, signal?: AbortSignal) =>
  call<UnitSpecs>(`/api/pureos/catalogue/${encodeURIComponent(typeId)}/specs`, { signal });

/** Every structural refusal of a train at once, by its place (`POST /api/pureos/train/validate`); runs nothing. */
export const validateTrain = (train: TrainSpec, signal?: AbortSignal) => post<TrainValidation>('/api/pureos/train/validate', train, signal);

/** Everything a run of the train would refuse, in the run's words, by its place (`POST /api/pureos/train/check`); runs no train. */
export const checkTrain = (req: TrainRunRequest, signal?: AbortSignal) => post<TrainValidation>('/api/pureos/train/check', req, signal);

/** Run the train (`POST /api/pureos/train/run`): one `pureos.train_run` artifact, read. */
export const runTrain = (req: TrainRunRequest, signal?: AbortSignal) => post<TrainRun>('/api/pureos/train/run', req, signal);

/** Every kept train run, newest first. */
export const pureosTrainRuns = (signal?: AbortSignal) => call<TrainSummary[]>('/api/pureos/train-runs', { signal });

/**
 * OF-BLD-020 §5.R — the trains a model built with `pureos_build` or
 * `pureos_write`, kept on the service (`GET /api/pureos/trains-kept`), the
 * most recently changed first.
 */
export const pureosTrainsKept = (signal?: AbortSignal) => call<KeptTrain[]>('/api/pureos/trains-kept', { signal });

/** A kept run's units read into a train by the service (`POST /api/pureos/train/from-run`). */
export const trainFromRun = (req: TrainFromRunRequest, signal?: AbortSignal) => post<TrainFromRun>('/api/pureos/train/from-run', req, signal);

/** The train's own inlet, a pseudo-unit with a scope of its own. */
export const INLET = 'inlet';
/** The Builder's id for a train not yet made: `/pureos/build/new`. */
export const NEW_TRAIN = 'new';
/** A place's scope in a train: a unit's or the inlet's. */
export const unitScope = (trainId: string, place: string) => `pureos:unit:${trainId}:${place}`;
/** Where the Builder opens a train. */
export const builderPath = (trainId: string) => `/pureos/build/${encodeURIComponent(trainId)}`;
/**
 * OF-BLD-020 §5.R — where the Builder opens a copy of a train a model built:
 * a new train of this browser, the kept one left the model's.
 */
export const builderCopyPath = (keptTrainId: string) => `/pureos/build/${NEW_TRAIN}?copy=${encodeURIComponent(keptTrainId)}`;
/** Where the Builder opens a fresh train read from a kept run's units. */
export const builderFromRunPath = (artifactId: string) => `/pureos/build/${NEW_TRAIN}?from=${encodeURIComponent(artifactId)}`;

/**
 * The train a run of the engine `train` ran, as its basis holds it (its `train` input, the train as data the request
 * sent, docs/api/runs.md, A train run): its id, its name and how many units it holds; null for any other run, or a
 * basis whose train does not read.
 */
export function trainOfRun(run: { engine: string; inputs: { name: string; quantity: { value: unknown } }[] }): { id: string; name: string; units: number } | null {
  if (run.engine !== 'train') return null;
  const held = run.inputs.find((i) => i.name === 'train')?.quantity.value;
  if (typeof held !== 'string') return null;
  try {
    const t = JSON.parse(held) as { id?: unknown; name?: unknown; units?: unknown };
    if (typeof t.id !== 'string' || typeof t.name !== 'string') return null;
    return { id: t.id, name: t.name, units: Array.isArray(t.units) ? t.units.length : 0 };
  } catch {
    return null;
  }
}

/**
 * What a run ran, as a person reads it, from its runs row: a train run names its train's name beside its id
 * (`trainOfRun`), any other its thing and the configuration it ran in, read by the engine's title for it beside its
 * name where the reader holds the thing's titles (`titles`, `titledConfiguration`: Studies' run card holds them from
 * GET /api/engines).
 */
export function ranWhat(
  run: { engine: string; plant: string; configuration?: string | null; inputs: { name: string; quantity: { value: unknown } }[] },
  titles?: Record<string, string> | null,
): string {
  const t = trainOfRun(run);
  return t ? `${t.name} (${run.plant})` : run.plant + (run.configuration ? ` (${titledConfiguration(run.configuration, titles)})` : '');
}

/**
 * OF-BLD-020 §6.2 — where the Builder opens a fresh train with its inlet set:
 * a kept simulation's harvest (`simulation:<artifact id>`, fermOS → Simulate's
 * **Use as a train's inlet**) or a scenario's newest run, whose broth its
 * flowsheet names (`scenario:<scenario id>`).
 */
type InletFrom = { kind: 'simulation' | 'scenario'; id: string };
export const builderInletPath = (from: InletFrom) => `/pureos/build/${NEW_TRAIN}?inlet=${from.kind}:${encodeURIComponent(from.id)}`;

/** The inlet a `?inlet=` names, as a train holds it; null for anything else. */
export function inletOfQuery(q: string | null): TrainSpec['inlet'] | null {
  const m = /^(simulation|scenario):([A-Za-z0-9][A-Za-z0-9._-]{0,127})$/.exec(q ?? '');
  if (!m) return null;
  return m[1] === 'simulation'
    ? { kind: 'simulation', ref: m[2], streamId: null, vessel: null, params: {} }
    : { kind: 'run-stream', ref: m[2], streamId: null, vessel: null, params: {} };
}

/** A person's override as a train's params hold it: an Override without its scope and key. */
const paramOf = (o: Override): TrainParam => ({ value: o.value, low: o.low, high: o.high, by: o.by, at: o.at, note: o.note });

/**
 * The train as the Builder sends it: the structure it holds, with every
 * value a person typed into each place's panel laid in as that place's
 * params. Nothing is computed: each value is the person's, as typed.
 */
export function trainSpecOf(draft: TrainSpec, overrides: Record<string, Override[]>): TrainSpec {
  const params = (place: string) => Object.fromEntries((overrides[unitScope(draft.id, place)] ?? []).map((o) => [o.key, paramOf(o)]));
  return {
    ...draft,
    inlet: { ...draft.inlet, params: params(INLET) },
    units: unitsOf(draft).map((u) => ({ ...u, params: params(u.id) })),
  };
}

/** Every override of a train's places: the browser's own bookkeeping of what a person typed there. */
export const trainOverrides = (train: TrainSpec, overrides: Record<string, Override[]>): Override[] =>
  [INLET, ...unitsOf(train).map((u) => u.id)].flatMap((place) => overrides[unitScope(train.id, place)] ?? []);

/**
 * A train's overrides as the inputs a run or a check sends (alpha 2.2 D2): each turned by `inputsOf` in the unit its
 * parameter is in, as its place's scope serves its specs (`specs`, by scope), and named `<place>.<key>`, the place its
 * scope names. A place whose specs the page has not read yet sends no input: its values travel in the train's own
 * params (`trainSpecOf`), each a person's as typed, and its inputs follow once its panel has read the units.
 */
export function trainInputs(train: TrainSpec, overrides: Override[], specs: Record<string, ParameterSpec[]>): EngineInput[] {
  return [INLET, ...unitsOf(train).map((u) => u.id)].flatMap((place) => {
    const scope = unitScope(train.id, place);
    const read = specs[scope];
    if (!read) return [];
    return inputsOf(overrides.filter((o) => o.scope === scope), read).map((i) => ({ ...i, name: `${place}.${i.name}` }));
  });
}

/** A value with every object's keys in order, so two copies of a train compare by what they hold, never by the order a serializer wrote. */
function canonical(v: unknown): unknown {
  if (Array.isArray(v)) return v.map(canonical);
  if (v && typeof v === 'object')
    return Object.fromEntries(
      Object.entries(v as Record<string, unknown>)
        .filter(([, x]) => x !== undefined)
        .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
        .map(([k, x]) => [k, canonical(x)]),
    );
  return v;
}

/** One train as text whatever wrote it (the browser, or the service echoing it), an absent optional field the same as null. */
const trainText = (t: TrainSpec): string =>
  JSON.stringify(
    canonical({
      ...t,
      inlet: { ...t.inlet, ref: t.inlet.ref ?? null, streamId: t.inlet.streamId ?? null, vessel: t.inlet.vessel ?? null, params: t.inlet.params ?? {} },
      units: unitsOf(t).map((u) => ({ ...u, params: u.params ?? {}, records: u.records ?? {}, readFrom: u.readFrom ?? null, outlets: u.outlets ?? {} })),
    }),
  );

/** Whether two copies of a train hold the same thing. */
export const sameTrain = (a: TrainSpec, b: TrainSpec) => trainText(a) === trainText(b);

/** The id the next unit added takes: U and one more than the highest U-number the train holds (a name, not a quantity). */
export function nextUnitId(units: TrainUnitSpec[]): string {
  const taken = units.map((u) => /^U(\d+)$/.exec(u.id)?.[1]).filter((n): n is string => !!n).map(Number);
  return `U${(taken.length ? Math.max(...taken) : 0) + 1}`;
}

/** A unit of a type as the Builder adds it: each outlet routed as the catalogue routes it, its onward port on and the rest to waste. */
export function unitOf(type: UnitType, id: string): TrainUnitSpec {
  return {
    id,
    type: type.id,
    params: {},
    outlets: Object.fromEntries(type.insOuts.filter((p) => p.side === 'out').map((p) => [p.name, p.onward ? 'onward' : 'waste'])),
    records: {},
    readFrom: null,
  };
}

/** What an outlet of the unit at `index` may be routed to (D9): on, to waste, or back to an earlier unit; a later unit is never offered. */
export const routeChoices = (units: TrainUnitSpec[], index: number): string[] => [
  'onward',
  'waste',
  ...units.slice(0, index).map((u) => `recycle:${u.id}`),
];

/** A route in words. */
export const routeWords = (route: string) =>
  route === 'onward' ? 'on to the next unit' : route === 'waste' ? 'to waste' : route.startsWith('recycle:') ? `back to ${route.slice('recycle:'.length)}` : route;

/** The streams a kept run's table holds, as its artifact keeps them (a Proforma run's, a reference's): read, never made. */
function streamsOfArtifact(a: Artifact | null | undefined): StreamRow[] {
  const s = (a?.output as Record<string, unknown> | undefined)?.streams;
  return Array.isArray(s) ? (s as StreamRow[]) : [];
}

/** A kept run a train can take a stream of, or be read from. */
export interface RunChoice {
  artifactId: string;
  /**
   * What a train's inlet names for it (OF-BLD-020 §6.2): the run's artifact
   * id, or, for a scenario's newest run, the scenario's id, so the service
   * reads whichever run is newest when the train runs.
   */
  ref: string;
  /** The scenario whose newest run this is; null for any other run. */
  scenarioId: string | null;
  /** The stream the run's flowsheet names as its broth on the shelf (`brothStream`); null when it names none. */
  broth: string | null;
  tool: string;
  label: string;
  createdAt: string;
  streams: StreamRow[];
}

/** The flowsheet a kept run names: its output's, else its basis's. */
function flowsheetOfRun(a: Artifact): string | null {
  const o = (a.output as Record<string, unknown> | undefined)?.flowsheet;
  if (typeof o === 'string' && o) return o;
  const i = a.inputs.find((x) => x.name === 'flowsheet');
  return i && typeof i.value === 'string' ? i.value : null;
}

/**
 * The kept runs a train can take a stream of, or be read from: pureOS's own
 * train runs, the newest run of every BioSTEAM scenario of the project, each
 * listed once (the service's, then those this browser holds that the service
 * does not list yet, ADR-014; alpha 2.2 D9), every library plant's run the
 * project keeps (alpha 2.2 D8: `GET /api/runs?engine=biosteam`, its tool
 * `library.run`), the reference plants' among them, and every reference run a
 * person kept from the shelf's retired reference entries (`proforma.reference`,
 * read as kept), each with its streams as its artifact or its train holds them.
 * Read, never made; a source the service cannot answer is said in words and
 * the rest still come back.
 */
export async function runChoices(
  held: { id: string; name: string }[],
  signal?: AbortSignal,
): Promise<{ choices: RunChoice[]; problems: string[] }> {
  const problems: string[] = [];
  const said = (what: string) => (e: unknown) => {
    if (signal?.aborted) return null;
    problems.push(`${what}: ${e instanceof Error ? e.message : String(e)}`);
    return null;
  };
  const choices: RunChoice[] = [];
  const runs = (await pureosTrainRuns(signal).catch(said('pureOS’s train runs'))) ?? [];
  for (const r of runs) {
    const t = await pureosTrain(r.artifactId, signal).catch(said(`train run ${r.artifactId}`));
    if (t)
      choices.push({ artifactId: r.artifactId, ref: r.artifactId, scenarioId: null, broth: null, tool: r.tool, label: `train run of ${r.trainName ?? r.trainId ?? r.artifactId}`, createdAt: r.createdAt, streams: t.streams });
  }
  // The shelf names each scenario flowsheet's broth (OF-BLD-020 §6.2).
  const shelf = (await proformaShelf(signal).catch(said('Proforma’s shelf'))) ?? [];
  const brothOf = new Map(shelf.map((f) => [f.id, f.brothStream ?? null]));
  const served = (await proformaScenarios({ host: null }, signal).catch(said('Proforma’s scenarios'))) ?? [];
  const listed = new Set(served.map((s) => s.id));
  const scenarios = [...served.map((s) => ({ id: s.id, name: s.name })), ...held.filter((s) => !listed.has(s.id))];
  for (const sc of scenarios) {
    const a = await proformaNewestRun(sc.id, signal).catch(said(`the runs of ${sc.id}`));
    if (!a) continue;
    const flowsheet = flowsheetOfRun(a);
    const broth = flowsheet ? (brothOf.get(flowsheet) ?? null) : null;
    choices.push({
      artifactId: a.id,
      ref: sc.id,
      scenarioId: sc.id,
      broth,
      tool: a.tool,
      label: `newest run of ${sc.name}${broth ? `, its broth ${broth}` : ''}`,
      createdAt: a.createdAt,
      streams: streamsOfArtifact(a),
    });
  }
  const library = (await listRuns(signal, 'biosteam').catch(said('the library plants’ runs'))) ?? [];
  for (const r of library) {
    if (r.tool !== 'library.run' || r.status !== 'done' || !r.artifactId) continue;
    const a = await proformaArtifact(r.artifactId, signal).catch(said(`library run ${r.id}`));
    if (a)
      choices.push({ artifactId: a.id, ref: a.id, scenarioId: null, broth: null, tool: a.tool, label: `library run of ${r.plant}${r.configuration ? ` (${r.configuration})` : ''}`, createdAt: a.createdAt, streams: streamsOfArtifact(a) });
  }
  const kept = (await keptReferenceRuns(signal).catch(said('the runs kept from the retired reference entries'))) ?? [];
  for (const a of kept) {
    const entry = retiredEntryOf(a);
    if (a.tool !== 'proforma.reference' || !entry) continue;
    choices.push({ artifactId: a.id, ref: a.id, scenarioId: null, broth: null, tool: a.tool, label: `reference run of ${entry}, kept from the retired entry`, createdAt: a.createdAt, streams: streamsOfArtifact(a) });
  }
  return { choices, problems };
}

/** The vessels fermOS designed (`GET /api/fermos/vessels`): one of a simulation gives a train's broth flow. */
export const fermosVessels = (signal?: AbortSignal) => call<VesselSummary[]>('/api/fermos/vessels', { signal });
