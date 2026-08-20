/**
 * The real agent over MCP. Nothing is implemented; every method says so.
 */
import type { AdapterResponse, AgentAdapter, TurnResult } from '@/adapters/types';
import { NotImplementedError } from '@/adapters/types';

const A = 'AgentAdapter';

export const mcpAgentAdapter: AgentAdapter = {
  async send(_sessionId: string, _input: string): Promise<AdapterResponse<TurnResult>> {
    throw new NotImplementedError(
      A,
      'send',
      'PaperQA2 retrieval and a real model answer this; neither is wired up.',
    );
  },

  async sendFlow(_sessionId: string, _flowId: string, _label: string): Promise<AdapterResponse<null>> {
    throw new NotImplementedError(
      A,
      'sendFlow',
      'Scripted-clarify continuation; the real agent treats a clarify reply as text.',
    );
  },
};
