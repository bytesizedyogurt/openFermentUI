/**
 * geneOS over MCP. Nothing is implemented; every method says so.
 */
import type { ExtractionRecord, Strain } from '@/data/types';
import type {
  AdapterResponse,
  CellAdapter,
  FluxPrediction,
  FluxRequest,
} from '@/adapters/types';
import { NotImplementedError } from '@/adapters/types';

const A = 'CellAdapter';

export const mcpCellAdapter: CellAdapter = {
  async listStrains(): Promise<AdapterResponse<Strain[]>> {
    throw new NotImplementedError(A, 'listStrains');
  },

  async getStrain(_strainId: string): Promise<AdapterResponse<Strain | null>> {
    throw new NotImplementedError(A, 'getStrain');
  },

  async getStrainRecords(_strainId: string): Promise<AdapterResponse<ExtractionRecord[]>> {
    throw new NotImplementedError(A, 'getStrainRecords');
  },

  async predictFlux(_request: FluxRequest): Promise<AdapterResponse<FluxPrediction | null>> {
    throw new NotImplementedError(A, 'predictFlux', 'COBRApy answers this, in Python.');
  },
};
