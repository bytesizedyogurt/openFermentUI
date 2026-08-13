/**
 * The Guild over MCP. Nothing is implemented; every method says so.
 */
import type { RunOutcome } from '@/data/types';
import type {
  AdapterResponse,
  DepositQuery,
  GuildAdapter,
  GuildChapter,
  Seal,
  SealQuery,
  SealRequest,
} from '@/adapters/types';
import { NotImplementedError } from '@/adapters/types';

const A = 'GuildAdapter';

export const mcpGuildAdapter: GuildAdapter = {
  async listChapters(): Promise<AdapterResponse<GuildChapter[]>> {
    throw new NotImplementedError(A, 'listChapters');
  },

  async getChapter(_chapterId: string): Promise<AdapterResponse<GuildChapter | null>> {
    throw new NotImplementedError(A, 'getChapter');
  },

  async listDeposits(_query?: DepositQuery): Promise<AdapterResponse<RunOutcome[]>> {
    throw new NotImplementedError(A, 'listDeposits');
  },

  async submitDeposit(_outcome: RunOutcome): Promise<AdapterResponse<RunOutcome>> {
    throw new NotImplementedError(A, 'submitDeposit');
  },

  async listSeals(_query?: SealQuery): Promise<AdapterResponse<Seal[]>> {
    throw new NotImplementedError(A, 'listSeals');
  },

  async requestSeal(_request: SealRequest): Promise<AdapterResponse<Seal>> {
    throw new NotImplementedError(A, 'requestSeal');
  },
};
