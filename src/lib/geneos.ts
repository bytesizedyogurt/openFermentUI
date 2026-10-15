// The browser's side of geneOS's computations (OF-BLD-014 §6.4).
//
// The shelf, and a ceiling, a frontier or a sugar mix for one model. The
// service computes and keeps each as an artifact; with it down this says so,
// and nothing stands in for a result (E.2). Shares lib/rag.ts's call, so the
// two failures are the same two: down, or refused in words.
import type { GeneosModelInfo, GeneosResult } from '@/data/types';
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
