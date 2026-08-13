/**
 * fermOS over MCP. Nothing is implemented; every method says so — with one
 * exception, at the foot of the file, which is not an exception at all.
 */
import type { DesignRecord, Scenario } from '@/data/types';
import type {
  AdapterResponse,
  EvaluationRequest,
  EvaluationStatus,
  JobId,
  JobPosition,
  JobRunner,
  ProcessAdapter,
} from '@/adapters/types';
import { NotImplementedError } from '@/adapters/types';

const A = 'ProcessAdapter';

export const mcpProcessAdapter: ProcessAdapter = {
  async listScenarios(): Promise<AdapterResponse<Scenario[]>> {
    throw new NotImplementedError(A, 'listScenarios');
  },

  async getScenario(_scenarioId: string): Promise<AdapterResponse<Scenario | null>> {
    throw new NotImplementedError(A, 'getScenario');
  },

  async listDesigns(_scenarioId?: string): Promise<AdapterResponse<DesignRecord[]>> {
    throw new NotImplementedError(A, 'listDesigns');
  },

  async getDesign(_designId: string): Promise<AdapterResponse<DesignRecord | null>> {
    throw new NotImplementedError(A, 'getDesign');
  },

  async submitEvaluation(_request: EvaluationRequest): Promise<AdapterResponse<JobId>> {
    throw new NotImplementedError(A, 'submitEvaluation', 'This is where T2 and T3 go.');
  },

  async getEvaluation(_jobId: JobId): Promise<AdapterResponse<EvaluationStatus>> {
    throw new NotImplementedError(A, 'getEvaluation');
  },

  /**
   * The one method here that does NOT throw, and it is not a stub pretending
   * to work — it is the defined behaviour for a runner with no connection.
   *
   * `src/sim/jobs.ts` states it directly: a runner reports the jobs it has
   * heard about and omits the rest, and "returning an empty map is the correct
   * behaviour on a frame where nothing new was heard". A runner attached to a
   * server that has not been written has heard nothing, every frame. Throwing
   * instead would put an exception inside a requestAnimationFrame loop sixty
   * times a second, which is a worse answer to the same question.
   */
  jobRunner(): JobRunner {
    return {
      report(): Map<string, JobPosition> {
        return new Map();
      },
    };
  },
};
