// The browser's side of geneOS's computations (OF-BLD-014 §6.4).
//
// The shelf, and a ceiling, a frontier or a sugar mix for one model. The
// service computes and keeps each as an artifact; with it down this says so,
// and nothing stands in for a result (E.2). Shares lib/rag.ts's call, so the
// two failures are the same two: down, or refused in words.
import type { ExtractionRecord, GeneosModelInfo, GeneosResult } from '@/data/types';
import { carbonSourceId } from '@/data/vocabulary';
import { RagDown, RagRefused, call } from './rag';

export { RagDown as GeneosDown, RagRefused as GeneosRefused };

const post = <T>(path: string, body: unknown, signal?: AbortSignal) =>
  call<T>(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal });

export const geneosModels = (signal?: AbortSignal) => call<GeneosModelInfo[]>('/api/geneos/models', { signal });

export const geneosCeiling = (modelId: string, substrate: string, product = 'phb', signal?: AbortSignal) =>
  post<GeneosResult>('/api/geneos/ceiling', { modelId, product, substrate }, signal);

export const geneosFrontier = (modelId: string, substrate: string, product = 'phb', signal?: AbortSignal) =>
  post<GeneosResult>('/api/geneos/frontier', { modelId, product, substrate }, signal);

export const geneosMix = (modelId: string, a: string, b: string, product = 'phb', signal?: AbortSignal) =>
  post<GeneosResult>('/api/geneos/mix', { modelId, product, a, b }, signal);

/** The sugars geneOS's shelf knows, in the order a view offers them. */
export const SUBSTRATES = ['glucose', 'xylose', 'fructose'] as const;

/** A frontier's or a mix's points, as the worker returns them. */
export interface FrontierPointOut {
  growth: number;
  flux: number;
  gPerG: number;
}
export interface MixPointOut {
  shareA: number;
  uptakeA: number;
  uptakeB: number;
  flux: number;
  gPerG: number;
}

/**
 * The reported PHA yields a ceiling on `sugar` can be held against: those
 * whose carbon source, in the paper's words, resolves to that sugar. The rest
 * (another feed, or none stated) are counted and not drawn, so a yield on oil
 * or glycerol is never ringed as above a glucose ceiling (§6.R).
 */
export function yieldsOnSugar(records: ExtractionRecord[], sugar: string): { on: ExtractionRecord[]; elsewhere: number } {
  const yields = records.filter((r) => r.field === 'pha_yield_substrate');
  const on = yields.filter((r) => r.carbonSource && carbonSourceId(r.carbonSource) === sugar);
  return { on, elsewhere: yields.length - on.length };
}
