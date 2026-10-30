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
// Nothing here computes: each screen shows what the service answered. With the
// service down a call says so (ServiceDown); a refusal comes back in the
// service's words (ServiceRefused).
import type {
  ComparisonCreate,
  ComparisonReport,
  EngineRun,
  RunReport,
  Runbook,
  RunbookCreate,
  StudyComparison,
  StudyScenario,
} from '@/data/types';
import { downloadBlob } from './csv';
import { ServiceDown, ServiceRefused, call } from './http';
import { apiFetch } from './project';

export { ServiceDown as StudiesDown, ServiceRefused as StudiesRefused };

const post = (body: unknown, signal?: AbortSignal): RequestInit => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
  signal,
});

const id = (s: string) => encodeURIComponent(s);

export const listRuns = (signal?: AbortSignal) => call<EngineRun[]>('/api/runs', { signal });
export const runReport = (runId: string, signal?: AbortSignal) => call<RunReport>(`/api/runs/${id(runId)}`, { signal });

export const listScenarios = (signal?: AbortSignal) => call<StudyScenario[]>('/api/studies/scenarios', { signal });
export const runScenario = (scenarioId: string, by: string) => call<RunReport>(`/api/studies/scenarios/${id(scenarioId)}/run`, post({ by }));

export const listComparisons = (signal?: AbortSignal) => call<StudyComparison[]>('/api/studies/comparisons', { signal });
export const comparisonReport = (comparisonId: string, signal?: AbortSignal) =>
  call<ComparisonReport>(`/api/studies/comparisons/${id(comparisonId)}`, { signal });
export const compareRuns = (asked: ComparisonCreate) => call<ComparisonReport>('/api/studies/comparisons', post(asked));

export const listStudyRunbooks = (signal?: AbortSignal) => call<Runbook[]>('/api/studies/runbooks', { signal });
export const makeRunbook = (asked: RunbookCreate) => call<Runbook>('/api/studies/runbooks', post(asked));

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
      detail = String(((await response.json()) as { detail?: unknown }).detail ?? '');
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

/** The numbers a run answers that a runbook may predict: each `price.<key>` and `outputs.<key>` with its unit, in the artifact's order. */
export function predictable(art: { output: Record<string, unknown> } | null): { output: string; value: number; unit: string }[] {
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
