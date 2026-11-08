// Engine runs and studies, the browser's side (execution prompt §7.4, §9.1
// step 5; core/openferment_core/engine/runs.py and studies/).
//
//   GET  /api/runs, /api/runs/{id}              the project's engine runs; one run's
//                                               report (the run, its artifact, its SFF
//                                               record, its parameters as the panel reads them)
//   GET  /api/studies/scenarios                 the study scenarios, newest first
//   POST /api/studies/scenarios/{id}/run        a scenario run as an engine run
//   GET  /api/studies/comparisons[/{id}]        the comparisons, or one with its artifact
//   POST /api/studies/comparisons               runs set side by side, kept
//   GET  /api/studies/runbooks                  the runbooks studies made
//   POST /api/studies/runbooks                  a runbook predicting a run's outputs
//   GET  /api/studies/export                    the export package, one zip
//   GET  /api/flowsheets/{id}/file              an SFF file, byte for byte as held
//
// And the person's own starts (alpha 2.1 stage B):
//
//   GET  /api/engines                           the engines registered here, each with its things
//   POST /api/engines/{name}/run                one run of an engine's thing, in a person's name
//   GET  /api/library                           the installed plants and the configurations each built in
//   POST /api/library/{plant}/run               one engine run of a plant in a configuration, in a person's name
//   POST /api/studies/scenarios                 a scenario whose values are a person's assumptions or readings
//   GET  /api/depositions/readings?unit=        the readings a run may take as measurements, in a unit
//   GET  /api/flowsheets                        the project's SFF records
//   GET  /api/flowsheets/library                the toolkit's reference files at the pinned commit
//   POST /api/flowsheets/library/{id}           one reference file kept in the project
//   POST /api/flowsheets/import                 an SFF file a person uploads
//   POST /api/flowsheets/import-url             an SFF file fetched from the https address a person names
//
// Nothing here computes: each screen shows what the service answered. With the
// service down a call says so (ServiceDown); a refusal comes back in the
// service's words (ServiceRefused).
//
// Every shape here is the service's own, generated from its models into
// src/api/types.gen.ts (ADR-007); the screens read a run, its artifact and
// the values it rests on by these names.
import type { components } from '@/api/types.gen';
import type { LibraryShelf } from './library';

type S = components['schemas'];

/** The provenance classes the service computes (models.py `Provenance`), the strongest first in `PROVENANCE_ORDER`. */
export type Provenance = S['Artifact']['provenance'];
/** Where a value came from (ADR-006): a record, an artifact, a person, a model, a reading, the library or a convention. */
export type Origin = S['Origin'];
/** A value and its unit, with its range and its origin (ADR-006). */
export type Quantity = S['Quantity'];
/** One value a request sets or a run took: a name and its quantity (src/lib/params.ts `inputsOf` makes one from a person's change). */
export type EngineInput = S['EngineInput'];
/** Where one input of a computation came from, as its basis names it. */
export type BasisSource = S['BasisSource'];
export type BasisInput = S['BasisInput'];
/** The calculation behind a computed value: its tool and version, every input with its source, its artifact. */
export type ComputedBasis = S['ComputedBasis'];
/** What the service computed and keeps, read and replayed by its id (BioRepo's artifact store). */
export type Artifact = S['Artifact'];
/** One engine run in a project: a row of `runs` (GET /api/runs). */
export type EngineRun = S['EngineRun'];
/** A value a run's computation reports about itself, kept on the run beside its outputs. */
export type RunDiagnostic = S['RunDiagnostic'];
/** GET /api/runs/{id}: a run with its computation, its SFF record and its parameters as the panel reads them. */
export type RunReport = S['RunReport'];
/** An SFF file as the project keeps it, and the graph drawn from it (docs/api/sff.md). */
export type SFFFlowsheet = S['SFFFlowsheet'];
export type SFFGraph = S['SFFGraph'];
/** A scenario's value as a person or a reading sets it, and the scenario a person makes (POST /api/studies/scenarios). */
export type ScenarioValue = S['ScenarioValue'];
export type ScenarioCreate = S['ScenarioCreate'];
export type StudyScenario = S['StudyScenario'];
/** Runs set side by side and kept, and what a comparison answers (docs/api/studies.md). */
export type ComparisonCreate = S['ComparisonCreate'];
export type StudyComparison = S['StudyComparison'];
export type ComparisonReport = S['ComparisonReport'];
/** A runbook predicting a run's outputs, as studies make it and as the service keeps it. */
export type RunbookCreate = S['RunbookCreate'];
/**
 * A runbook as the project keeps it, a person's or a study's, served as kept (studies/runbooks.py, project_state.py):
 * a field its row never set stays out of the answer. A reader reads its stages, predictions, measures and outputs
 * through `stagesOf`, `predictionsOf`, `measuresOf` and `outputsOf`, and its note and its progress as a row may leave
 * them out, which the document names as present for their defaults.
 */
export type Runbook = S['Runbook'];
export type RunbookStatus = Runbook['status'];
/** One stage of a runbook and where it stands. */
export type RunbookStage = S['RunbookStage'];
export type RunbookStageStatus = RunbookStage['status'];
/**
 * A claim a runbook makes before anything runs, and a value the bench records against it. A prediction's kind,
 * interval, artifact and records, and a measure's prediction, stand absent or null as the service or the page wrote
 * them: the lock's digest reads the two apart (src/engine/lock.ts, runbook_lock.py), so a reader passes each on as it
 * arrived.
 */
export type Prediction = S['Prediction'];
export type Measure = S['Measure'];
/**
 * The bench's record of a run against a runbook (project_state.py): its readings and observations as they were
 * taken, its state, its reconciliation, and a reading's hours into the run and a measure's series role where a
 * person set them. A row keeps every field the page sent.
 */
export type Deposition = S['Deposition'];
export type DepositionEntry = S['DepositionEntry'];
/** What a measure's series is, as a person named it. */
export type SeriesRole = NonNullable<Deposition['seriesRoles']>[string];
/** A measured value a reconciliation released, with what it was true under and the run's deviations. */
export type MeasuredEvidence = S['MeasuredEvidence'];

/** A runbook's stages; a row that set none has none. */
export const stagesOf = (r: Pick<Runbook, 'stages'>): RunbookStage[] => r.stages ?? [];
/** A runbook's predictions; a row that set none has none. */
export const predictionsOf = (r: Pick<Runbook, 'predictions'>): Prediction[] => r.predictions ?? [];
/** A runbook's measures, the bench's schema; a row that set none has none. */
export const measuresOf = (r: Pick<Runbook, 'measurementSchema'>): Measure[] => r.measurementSchema ?? [];
/** What a complete runbook hands over; a row that set none hands over none. */
export const outputsOf = (r: Pick<Runbook, 'outputs'>): string[] => r.outputs ?? [];

/** One of the toolkit's reference SFF files at the pinned commit. */
export type SFFLibraryEntry = components['schemas']['SFFLibraryEntry'];
/** An engine registered here, with its things, its worker and its last conformance verdict (GET /api/engines). */
export type EngineInfo = components['schemas']['EngineInfo'];
export type EngineThing = components['schemas']['EngineThing'];

/**
 * A configuration as a person reads it on Studies' run card: the engine's title for it beside its name
 * (`EngineThing.configurationTitles`; the kinetics engine's names the kind of artifact the configuration names and when
 * the project kept it), or its name where the engine gives none.
 */
export const titledConfiguration = (configuration: string, titles?: Record<string, string> | null): string =>
  titles?.[configuration] ? `${titles[configuration]} · ${configuration}` : configuration;

/**
 * A configuration a thing of another engine is offered in on Studies' run card: its name, null for a thing that takes
 * none and runs in its own, and the words the card shows for it.
 */
interface OfferedConfiguration {
  configuration: string | null;
  words: string;
}

/**
 * The configurations a thing of another engine is offered in on Studies' run card: its default first, then the rest in
 * the engine's order (the kinetics engine's, newest first), each read by the engine's title for it beside its name
 * (`titledConfiguration`); a thing that takes no configuration is offered in its own.
 */
export function offeredConfigurations(thing: EngineThing | null): OfferedConfiguration[] {
  const named = thing?.configurations ?? [];
  if (!thing || named.length === 0) return [{ configuration: null, words: 'its own' }];
  const own = thing.defaultConfiguration;
  const ordered = own !== null && named.includes(own) ? [own, ...named.filter((c) => c !== own)] : named;
  return ordered.map((c) => ({ configuration: c, words: titledConfiguration(c, thing.configurationTitles) }));
}

/**
 * A reading a run may take as a measurement (GET /api/depositions/readings): a confirmed entry of one of the
 * project's depositions that stands for its measure, with its runbook, its measure, its depositor and its time; asked
 * in a unit, its value in that unit (`inUnit`) beside its own.
 */
export type DepositionReading = components['schemas']['DepositionReading'];
import { downloadBlob } from './csv';
import { ServiceDown, ServiceRefused, call, detailWords } from './http';
import { apiFetch } from './project';

export { ServiceDown as StudiesDown, ServiceRefused as StudiesRefused };

const post = (body: unknown, signal?: AbortSignal): RequestInit => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
  signal,
});

const id = (s: string) => encodeURIComponent(s);

/** The project's runs, newest first; those of one engine when `engine` names it (`GET /api/runs?engine=`). */
export const listRuns = (signal?: AbortSignal, engine?: string) =>
  call<EngineRun[]>(engine ? `/api/runs?engine=${id(engine)}` : '/api/runs', { signal });
export const runReport = (runId: string, signal?: AbortSignal) => call<RunReport>(`/api/runs/${id(runId)}`, { signal });

export const listScenarios = (signal?: AbortSignal) => call<StudyScenario[]>('/api/studies/scenarios', { signal });
export const runScenario = (scenarioId: string, by: string) => call<RunReport>(`/api/studies/scenarios/${id(scenarioId)}/run`, post({ by }));

export const listComparisons = (signal?: AbortSignal) => call<StudyComparison[]>('/api/studies/comparisons', { signal });
export const comparisonReport = (comparisonId: string, signal?: AbortSignal) =>
  call<ComparisonReport>(`/api/studies/comparisons/${id(comparisonId)}`, { signal });
export const compareRuns = (asked: ComparisonCreate) => call<ComparisonReport>('/api/studies/comparisons', post(asked));

export const listStudyRunbooks = (signal?: AbortSignal) => call<Runbook[]>('/api/studies/runbooks', { signal });
export const getFlowsheet = (recordId: string, signal?: AbortSignal) =>
  call<SFFFlowsheet>(`/api/flowsheets/${id(recordId)}`, { signal });
export const makeRunbook = (asked: RunbookCreate) => call<Runbook>('/api/studies/runbooks', post(asked));

export const libraryShelf = (signal?: AbortSignal) => call<LibraryShelf>('/api/library', { signal });
/** The engines of the entry-point group openferment.engines, each listed with its error when it cannot be used. */
export const listEngines = (signal?: AbortSignal) => call<EngineInfo[]>('/api/engines', { signal });
/** One run of an engine's thing at the engine's own defaults, in a configuration it names (null: the thing's own). */
export const runEngine = (engine: string, thing: string, configuration: string | null, by: string) =>
  call<RunReport>(`/api/engines/${id(engine)}/run`, post({ thing, configuration, inputs: [], by }));
/**
 * One engine run of a plant on its package's own values, in a configuration it built in (null: the plant's default,
 * as the biosteam engine names it). It sets no value of its own: `inputs` is the typed values a run sets (alpha 2.2
 * D2), and a run with values is a scenario's (`makeScenario`, then `runScenario`).
 */
export const runPlant = (plant: string, configuration: string | null, by: string) =>
  call<RunReport>(`/api/library/${id(plant)}/run`, post({ configuration, inputs: [], by }));
export const makeScenario = (asked: ScenarioCreate) => call<StudyScenario>('/api/studies/scenarios', post(asked));
/**
 * The project's readings a run may take as measurements, the latest taken first; with `unit`, those whose unit is
 * `unit` or converts into it, each with its value in `unit`. The service's lookup decides, so a reading listed is one
 * a scenario's value may name: `{value, unit, origin: {kind: 'measurement', ref}}`, its own value and unit.
 */
export const depositionReadings = (unit: string | null, signal?: AbortSignal) =>
  call<DepositionReading[]>(unit === null ? '/api/depositions/readings' : `/api/depositions/readings?unit=${id(unit)}`, { signal });

export const listFlowsheets = (signal?: AbortSignal) => call<SFFFlowsheet[]>('/api/flowsheets', { signal });
export const flowsheetLibrary = (signal?: AbortSignal) => call<SFFLibraryEntry[]>('/api/flowsheets/library', { signal });
export const importLibraryFlowsheet = (fileId: string, by: string) =>
  call<SFFFlowsheet>(`/api/flowsheets/library/${id(fileId)}`, post({ by }));
/** An SFF file the person chose, kept in the project as the toolkit checked it (a file that fails validation is kept with its findings). */
export function importFlowsheet(file: File, by: string): Promise<SFFFlowsheet> {
  const form = new FormData();
  form.append('file', file);
  form.append('by', by);
  return call<SFFFlowsheet>('/api/flowsheets/import', { method: 'POST', body: form });
}
/**
 * The SFF file an https address serves, fetched by the service and kept in the project as an uploaded file is, the
 * address its source. A refusal comes back in the service's words: an address that is not https, a file past the size
 * an import takes, a host that failed or answered an error, a file that is not an SFF flowsheet.
 */
export const importFlowsheetUrl = (url: string, by: string) =>
  call<SFFFlowsheet>('/api/flowsheets/import-url', post({ url, by }));


/** A file the service answers, fetched with the open project named and handed to the person; its name as the service gave it. */
async function fetchFile(path: string, fallback: string): Promise<string> {
  let response: Response;
  try {
    response = await apiFetch(path);
  } catch {
    throw new ServiceDown('The service is not running.');
  }
  if (!response.ok) {
    let detail = '';
    try {
      detail = detailWords(((await response.json()) as { detail?: unknown }).detail);
    } catch {
      /* the status is the message */
    }
    throw new ServiceRefused(response.status, detail || `The service answered ${response.status}.`);
  }
  const name = /filename="([^"]+)"/.exec(response.headers.get('content-disposition') ?? '')?.[1] ?? fallback;
  downloadBlob(name, await response.blob());
  return name;
}

/** The project's studies as one zip that opens without the service (studies/exports.py). */
export const downloadExport = (by: string) => fetchFile(`/api/studies/export?by=${id(by)}`, 'studies.zip');

/** A run's SFF file, byte for byte as the project holds it. */
export const downloadFlowsheet = (recordId: string) => fetchFile(`/api/flowsheets/${id(recordId)}/file`, `${recordId}.sff.json`);

/**
 * The numbers a run answers that a runbook may predict, each with its unit, in the order the service gives them:
 * a library run's `price.<key>` and `outputs.<key>` from its artifact, and any other engine's run's `values.<name>`
 * from its outputs.values (docs/api/runs.md, Outputs).
 */
export function predictable(
  run: { tool: string; outputs: Record<string, unknown> },
  art: { output: Record<string, unknown> } | null,
): { output: string; value: number; unit: string }[] {
  if (run.tool !== 'library.run') {
    const values = Array.isArray(run.outputs.values) ? (run.outputs.values as { name?: unknown; quantity?: { value?: unknown; unit?: unknown } }[]) : [];
    return values.flatMap((v) => {
      const value = v.quantity?.value;
      const unit = v.quantity?.unit;
      return typeof v.name === 'string' && typeof value === 'number' && Number.isFinite(value) && typeof unit === 'string'
        ? [{ output: `values.${v.name}`, value, unit }]
        : [];
    });
  }
  if (!art) return [];
  const out: { output: string; value: number; unit: string }[] = [];
  const price = (art.output.price ?? {}) as Record<string, unknown>;
  const priceUnits = (price.units ?? {}) as Record<string, unknown>;
  for (const [k, v] of Object.entries(price)) {
    if (typeof v === 'number' && Number.isFinite(v) && typeof priceUnits[k] === 'string') out.push({ output: `price.${k}`, value: v, unit: priceUnits[k] as string });
  }
  const outputs = (art.output.outputs ?? {}) as Record<string, unknown>;
  const outputUnits = (art.output.outputUnits ?? {}) as Record<string, unknown>;
  for (const [k, v] of Object.entries(outputs)) {
    if (typeof v === 'number' && Number.isFinite(v) && typeof outputUnits[k] === 'string') out.push({ output: `outputs.${k}`, value: v, unit: outputUnits[k] as string });
  }
  return out;
}
