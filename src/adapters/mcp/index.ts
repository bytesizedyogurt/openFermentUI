/**
 * The MCP backend: the shape of the five, with nothing behind them.
 *
 * These are stubs, and they are here so that the day a server exists there is
 * a file with its name on it rather than a decision to make. Each method
 * rejects with `NotImplementedError`, which names the adapter and the method,
 * so a caller that reaches one gets told exactly which subsystem it was
 * expecting to find.
 *
 * They are NOT selected by default. `VITE_ADAPTER_BACKEND=mcp` is an explicit
 * choice to run against servers, and running it today fails loudly on the
 * first call — which is the intended behaviour of a backend that does not
 * exist yet, and the reason the fixture is the default.
 */
import type { OpenFermentAdapters } from '@/adapters/types';
import { mcpCorpusAdapter } from './corpus';
import { mcpCellAdapter } from './cell';
import { mcpProcessAdapter } from './process';
import { mcpEconomicsAdapter } from './economics';
import { mcpGuildAdapter } from './guild';
import { mcpAgentAdapter } from './agent';

export const mcpAdapters: OpenFermentAdapters = {
  corpus: mcpCorpusAdapter,
  cell: mcpCellAdapter,
  process: mcpProcessAdapter,
  economics: mcpEconomicsAdapter,
  guild: mcpGuildAdapter,
  agent: mcpAgentAdapter,
};

export {
  mcpCorpusAdapter,
  mcpCellAdapter,
  mcpProcessAdapter,
  mcpEconomicsAdapter,
  mcpGuildAdapter,
};
