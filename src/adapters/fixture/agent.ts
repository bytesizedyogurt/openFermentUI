/**
 * The scripted agent, behind the seam it will be replaced through.
 *
 * This is the Phase 4 quarantine: `src/sim/chat.ts` keeps every line of its
 * playback — the flows, the pacing, the honest declines — and the ONLY path a
 * screen reaches it by is this adapter. When the real agent lands, this file
 * and the sim it wraps retire together (the sim's own headers say so), and the
 * MCP implementation takes the same two methods.
 */
import { send as simSend, sendFlow as simSendFlow } from '@/sim/chat';
import type { AdapterResponse, AgentAdapter, TurnResult } from '@/adapters/types';
import { respond } from './meta';

/**
 * Stamped as `modelVersion` on every turn: what "answered" was the scripted
 * flow player, and a trace carrying this string cannot be mistaken for a model
 * run. The real agent stamps its model id here instead.
 */
const SCRIPTED_PLAYER = 'sim-scripted-flows';

export const fixtureAgentAdapter: AgentAdapter = {
  async send(sessionId: string, input: string): Promise<AdapterResponse<TurnResult>> {
    // The sim's signature is (input, sessionId); the adapter is session-first
    // like every other session-scoped method on this seam.
    const result = await simSend(input, sessionId);
    return respond<TurnResult>(result, { modelVersion: SCRIPTED_PLAYER });
  },

  async sendFlow(sessionId: string, flowId: string, label: string): Promise<AdapterResponse<null>> {
    await simSendFlow(flowId, label, sessionId);
    return respond<null>(null, { modelVersion: SCRIPTED_PLAYER });
  },
};
