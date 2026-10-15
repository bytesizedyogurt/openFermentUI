// The browser's side of Proforma's simulator (OF-BLD-014 §8.2).
//
// The simulator's status and the benchmark it reproduced. The service runs
// BioSTEAM and keeps the benchmark as an artifact; with it down this says so,
// and nothing stands in for a result (E.2). Shares lib/rag.ts's call.
import type { Artifact } from '@/data/types';
import { RagDown, RagRefused, call } from './rag';

export { RagDown as ProformaDown, RagRefused as ProformaRefused };

export interface SimulatorStatus {
  status: 'cold' | 'starting' | 'ready' | 'failed';
  error: string | null;
}

export interface BenchmarkResponse {
  artifact: Artifact | null;
  simulator: SimulatorStatus;
}

/** What the benchmark's artifact holds, as `flowsheets/cornstover_benchmark.py` writes it. */
export interface BenchmarkOutput {
  package: string;
  biosteam: string;
  mespUsdPerGal: number;
  mespUsdPerKg: number;
  settings: { rateOfReturn: number; operatingDays: number; incomeTax: number; startYear: number; endYear: number };
  references: string[];
}

export const proformaBenchmark = (signal?: AbortSignal) => call<BenchmarkResponse>('/api/proforma/benchmark', { signal });

export const runProformaBenchmark = (signal?: AbortSignal) =>
  call<BenchmarkResponse>('/api/proforma/benchmark', { method: 'POST', signal });

/** B.3: the price the package's defaults give for version 2.35.1, measured when this build was written. */
export const BENCHMARK_EXPECTED = { usdPerGal: 1.968, tolerance: 0.005, package: 'biorefineries.cornstover@2.35.1' };
