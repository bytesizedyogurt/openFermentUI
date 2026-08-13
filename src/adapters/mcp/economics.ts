/**
 * Proforma over MCP. Nothing is implemented; every method says so.
 */
import type { PlantResult } from '@/engine/plant';
import type { EvaluatedPoint } from '@/engine/grids';
import type {
  AdapterResponse,
  CostModelSummary,
  EconomicsAdapter,
  PointRequest,
  SensitivityBar,
} from '@/adapters/types';
import { NotImplementedError } from '@/adapters/types';

const A = 'EconomicsAdapter';

export const mcpEconomicsAdapter: EconomicsAdapter = {
  async listCostModels(): Promise<AdapterResponse<CostModelSummary[]>> {
    throw new NotImplementedError(A, 'listCostModels');
  },

  async getCostModel(_modelId: string): Promise<AdapterResponse<CostModelSummary | null>> {
    throw new NotImplementedError(A, 'getCostModel');
  },

  async evaluatePoint(_request: PointRequest): Promise<AdapterResponse<EvaluatedPoint | null>> {
    throw new NotImplementedError(A, 'evaluatePoint');
  },

  async solvePlant(_request: PointRequest): Promise<AdapterResponse<PlantResult | null>> {
    throw new NotImplementedError(A, 'solvePlant', 'BioSTEAM authors the cost model, in Python.');
  },

  async getSensitivity(_request: PointRequest): Promise<AdapterResponse<SensitivityBar[]>> {
    throw new NotImplementedError(A, 'getSensitivity');
  },
};
