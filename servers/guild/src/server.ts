/**
 * The Guild, as an MCP server — which today means answered honestly, which
 * means answered mostly empty.
 *
 * This is the server-side sibling of `src/adapters/fixture/guild.ts` and it
 * inherits that file's discipline: no chapter registry exists, so
 * `list_chapters` returns the ABSENCE of a registry, with a notice saying so,
 * rather than an invented institution. When a real registry exists (ORCID for
 * who, in-toto for what was attested), this tool's shape does not change —
 * only its contents do.
 *
 * DELIBERATE ABSENCE — read before adding a tool here: there is NO tool that
 * publishes, and there must not be. Disclosure drafting (a future
 * `prepare_disclosure`) is reversible; publication is initiated by a human
 * outside the agent loop. An MCP tool that triggers irreversible public
 * disclosure is exactly the tool not to hand an agent. The same reasoning
 * already lives on `requestSeal` in the fixture, which REFUSES rather than
 * mints: a seal is an attestation, and there is no chapter here to make one.
 *
 * NO ZOD, deliberately. Whether this repo grows Zod validators (generated
 * from the Pydantic canon or otherwise) is an open question with the user.
 * Tool inputs are declared as plain JSON Schema — both tools take no
 * arguments — and the entity shapes come, type-only, from the repo's
 * canonical seam.
 */
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  McpError,
  ErrorCode,
} from '@modelcontextprotocol/sdk/types.js';

// Type-only, and that is load-bearing: `GuildChapter` deliberately has NO
// Pydantic model yet ("no chapter registry exists" — its docstring), so the
// canonical shape lives in the adapter seam. Redeclaring it here would be the
// hand-maintained twin CLAUDE.md's one rule forbids. When the Guild entities
// gain Pydantic models, this import moves to the generated `@/data/types`.
import type { GuildChapter } from '@/adapters/types';

import { CORPUS_FILES, SERVER_VERSION, corpusSnapshot, envelope } from './meta.ts';

/** Verbatim from `src/adapters/fixture/guild.ts`, which set the pattern. */
const NO_CHAPTER_REGISTRY =
  'No chapter registry exists. The empty list is the absence of a registry, not a guild with no ' +
  'chapters in it, and inventing an institution to populate it would be inventing an affiliation.';

const NO_ARGS = {
  type: 'object' as const,
  properties: {},
  additionalProperties: false,
};

const TOOLS = [
  {
    name: 'guild_health',
    description:
      'Liveness and provenance check for the Guild server. Returns { ok, serverVersion, ' +
      'corpusSnapshotId }. `ok` is true only if the corpus files this server reads were ' +
      'readable and parsed; `corpusSnapshotId` is a digest derived from those files, so it ' +
      'moves when the corpus does.',
    inputSchema: NO_ARGS,
    annotations: { readOnlyHint: true, openWorldHint: false },
  },
  {
    name: 'list_sealable_protocols',
    description:
      'The protocols a chapter could be equipped to run and asked to seal, as { id, title, bsl, ' +
      'currentVersion }. Read from data/corpus/protocols.json — the collection the Guild’s entities are ' +
      'defined against, and the one this server’s corpusSnapshotId is a digest of. `bsl` is the ' +
      'constraint that matters: a chapter may only run a protocol its own biosafety level covers.',
    inputSchema: NO_ARGS,
    annotations: { readOnlyHint: true, openWorldHint: false },
  },
  {
    name: 'list_chapters',
    description:
      'List guild chapters — the places with benches, people and a biosafety level that can ' +
      'run protocols and attest to results. Currently returns an empty list with a notice: no ' +
      'chapter registry exists yet, and this server will not invent one. The response envelope ' +
      'is { data, serverVersion, corpusSnapshotId, notice? }.',
    inputSchema: NO_ARGS,
    annotations: { readOnlyHint: true, openWorldHint: false },
  },
] as const;

function asText(payload: unknown) {
  return { content: [{ type: 'text' as const, text: JSON.stringify(payload, null, 2) }] };
}

const server = new Server(
  { name: 'openferment-guild', version: '0.1.0' },
  { capabilities: { tools: {} } },
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools: [...TOOLS] }));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  switch (request.params.name) {
    case 'guild_health': {
      const snapshot = corpusSnapshot();
      return asText({
        ok: snapshot.ok,
        serverVersion: SERVER_VERSION,
        corpusSnapshotId: snapshot.id,
      });
    }

    case 'list_sealable_protocols': {
      const snapshot = corpusSnapshot();
      const raw = snapshot.contents[CORPUS_FILES[0]];
      if (!Array.isArray(raw)) {
        throw new McpError(
          ErrorCode.InternalError,
          `${CORPUS_FILES[0]} did not parse as an array; this server cannot vouch for a corpus it ` +
            'could not read.',
        );
      }
      // A thin projection, and thin on purpose: the Guild's interest in a
      // protocol is what it takes to RUN one, not the steps. Whoever wants the
      // steps asks fermOS's protocol surface, which validates them through the
      // canonical Protocol model — this server has no Pydantic and must not
      // pretend to have vetted the rest of the entity.
      const rows = raw.map((p) => {
        const entry = p as Record<string, unknown>;
        return {
          id: entry.id,
          title: entry.title,
          bsl: entry.bsl,
          // `currentVersion`, not a bare id: a SealSubject of kind
          // 'protocol-version' carries a version, and a seal that does not
          // commit to a specific one attests to nothing.
          currentVersion: entry.currentVersion,
        };
      });
      return asText(
        envelope(
          rows,
          'These are protocols a chapter could be asked to seal, not protocols any chapter has ' +
            'sealed. No seal exists — see requestSeal, which refuses.',
        ),
      );
    }

    case 'list_chapters': {
      const chapters: GuildChapter[] = [];
      return asText(envelope(chapters, NO_CHAPTER_REGISTRY));
    }

    default:
      throw new McpError(
        ErrorCode.MethodNotFound,
        `Unknown tool: ${request.params.name}. This server declares: ${TOOLS.map((t) => t.name).join(', ')}.`,
      );
  }
});

const transport = new StdioServerTransport();
await server.connect(transport);
// stdout belongs to the protocol; stderr is for humans.
console.error(`openferment-guild ${SERVER_VERSION} listening on stdio`);
