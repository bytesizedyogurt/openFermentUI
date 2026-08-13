/**
 * BioRepo over MCP. Nothing is implemented; every method says so.
 */
import type { ExtractionRecord, Paper, Patent, ScopeHit } from '@/data/types';
import type { CorpusSearchOptions, CorpusSearchResult } from '@/data/source';
import type {
  AdapterResponse,
  CorpusAdapter,
  GoldSetPlan,
  RecordQuery,
  ScopeRequest,
  WhitespaceRegion,
  WhitespaceRequest,
} from '@/adapters/types';
import { NotImplementedError } from '@/adapters/types';

const A = 'CorpusAdapter';

/**
 * Each method is `async` so the failure arrives as a REJECTED PROMISE rather
 * than a synchronous throw. A caller written against this seam awaits it; a
 * stub that threw before returning a promise would blow up in a different
 * place from the one the real implementation will fail in, and callers would
 * end up guarding both.
 */
export const mcpCorpusAdapter: CorpusAdapter = {
  async searchPapers(
    _query: string,
    _options?: CorpusSearchOptions,
  ): Promise<AdapterResponse<CorpusSearchResult>> {
    throw new NotImplementedError(A, 'searchPapers', 'PaperQA2 answers this; it is not wired up.');
  },

  async getPaper(_paperId: string): Promise<AdapterResponse<Paper | null>> {
    throw new NotImplementedError(A, 'getPaper');
  },

  async getRecords(_query?: RecordQuery): Promise<AdapterResponse<ExtractionRecord[]>> {
    throw new NotImplementedError(A, 'getRecords');
  },

  async listPatents(): Promise<AdapterResponse<Patent[]>> {
    throw new NotImplementedError(A, 'listPatents');
  },

  async getGoldSetPlan(): Promise<AdapterResponse<GoldSetPlan>> {
    throw new NotImplementedError(
      A,
      'getGoldSetPlan',
      'The plan is prose in OF-COR-001 §18 and has no server behind it yet.',
    );
  },

  async writeRecord(_record: ExtractionRecord): Promise<AdapterResponse<ExtractionRecord>> {
    throw new NotImplementedError(A, 'writeRecord');
  },

  async getScope(_request: ScopeRequest): Promise<AdapterResponse<ScopeHit[]>> {
    throw new NotImplementedError(A, 'getScope', 'Requires parsed claim bounds, which do not exist yet.');
  },

  async getWhitespace(
    _request?: WhitespaceRequest,
  ): Promise<AdapterResponse<WhitespaceRegion[]>> {
    throw new NotImplementedError(A, 'getWhitespace', 'Requires parsed claim bounds, which do not exist yet.');
  },
};
