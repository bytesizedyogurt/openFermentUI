// The browser's side of pureOS's trains (OF-BLD-019 §4.1, D1).
//
// The service reads a train from one `proforma.run` artifact's stream and
// unit tables (`core/openferment_core/pureos/__init__.py`); the browser shows it and
// computes nothing of its own: every mass, recovery and cumulative share on
// the page is a field the service sent. With the service down this says so,
// and nothing stands in for a train (E.2). Shares lib/rag.ts's call.
import type {
  Artifact,
  KeptTrain,
  Override,
  ProposeRequest,
  StreamRow,
  Train,
  TrainFromRun,
  TrainFromRunRequest,
  TrainParam,
  TrainProposal,
  TrainRun,
  TrainRunRequest,
  TrainSpec,
  TrainSummary,
  TrainUnit,
  TrainUnitSpec,
  TrainValidation,
  UnitSpecs,
  UnitType,
  VesselSummary,
} from '@/data/types';
import { ServiceDown, ServiceRefused, call } from './http';
import { proformaNewestRun, proformaReference, proformaScenarios, proformaShelf } from './proforma';

export { ServiceDown as PureosDown, ServiceRefused as PureosRefused };

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
// params as it is sent (`trainSpecOf`). The service validates it, says what a
// run would refuse, runs it and keeps one `pureos.train_run` artifact; the
// browser shows the answer and computes nothing.

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
 * OF-BLD-020 §6.2 — where the Builder opens a fresh train with its inlet set:
 * a kept simulation's harvest (`simulation:<artifact id>`, fermOS → Simulate's
 * **Use as a train's inlet**) or a scenario's newest run, whose broth its
 * flowsheet names (`scenario:<scenario id>`).
 */
export type InletFrom = { kind: 'simulation' | 'scenario'; id: string };
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
    units: draft.units.map((u) => ({ ...u, params: params(u.id) })),
  };
}

/** Every override of a train's places, as a run request carries them. */
export const trainOverrides = (train: TrainSpec, overrides: Record<string, Override[]>): Override[] =>
  [INLET, ...train.units.map((u) => u.id)].flatMap((place) => overrides[unitScope(train.id, place)] ?? []);

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
export const trainText = (t: TrainSpec): string =>
  JSON.stringify(
    canonical({
      ...t,
      inlet: { ...t.inlet, ref: t.inlet.ref ?? null, streamId: t.inlet.streamId ?? null, vessel: t.inlet.vessel ?? null, params: t.inlet.params ?? {} },
      units: t.units.map((u) => ({ ...u, params: u.params ?? {}, records: u.records ?? {}, readFrom: u.readFrom ?? null, outlets: u.outlets ?? {} })),
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
export function streamsOfArtifact(a: Artifact | null | undefined): StreamRow[] {
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
export function flowsheetOfRun(a: Artifact): string | null {
  const o = (a.output as Record<string, unknown> | undefined)?.flowsheet;
  if (typeof o === 'string' && o) return o;
  const i = a.inputs.find((x) => x.name === 'flowsheet');
  return i && typeof i.value === 'string' ? i.value : null;
}

/**
 * The kept runs a train can take a stream of, or be read from: pureOS's own
 * train runs, the newest run of every BioSTEAM scenario (the seed's and the
 * ones made here), and every reference run on the shelf, each with its
 * streams as its artifact or its train holds them.
 * Read, never made; a source the service cannot answer is said in words and
 * the rest still come back.
 */
export async function runChoices(
  made: { id: string; name: string }[],
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
  const seeds = (await proformaScenarios({ host: null }, signal).catch(said('Proforma’s scenarios'))) ?? [];
  const scenarios = [...seeds.map((s) => ({ id: s.id, name: s.name })), ...made];
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
  for (const f of shelf.filter((x) => x.reference)) {
    const ref = await proformaReference(f.id, signal).catch(said(`the reference run of ${f.id}`));
    const a = ref?.artifact;
    if (a && a.tool === 'proforma.reference')
      choices.push({ artifactId: a.id, ref: a.id, scenarioId: null, broth: null, tool: a.tool, label: `reference run of ${f.title}`, createdAt: a.createdAt, streams: streamsOfArtifact(a) });
  }
  return { choices, problems };
}

/** The vessels fermOS designed (`GET /api/fermos/vessels`): one of a simulation gives a train's broth flow. */
export const fermosVessels = (signal?: AbortSignal) => call<VesselSummary[]>('/api/fermos/vessels', { signal });
