/**
 * Minimal stdio client that proves the server actually runs.
 *
 * Spawns `src/server.ts` over stdio, then drives the full declared surface:
 * tools/list, guild_health, list_chapters. Prints each request name and the
 * raw result. This is the transcript in the README — if this script's output
 * and the README disagree, the README is stale.
 */
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

const HERE = dirname(fileURLToPath(import.meta.url));
const SERVER_DIR = join(HERE, '..');

const transport = new StdioClientTransport({
  command: process.execPath,
  args: ['--import', 'tsx', join(SERVER_DIR, 'src', 'server.ts')],
  cwd: SERVER_DIR,
});

const client = new Client({ name: 'guild-smoke-client', version: '0.1.0' });
await client.connect(transport);

function show(label: string, payload: unknown) {
  console.log(`\n== ${label} ==`);
  console.log(JSON.stringify(payload, null, 2));
}

const tools = await client.listTools();
show(
  'tools/list',
  tools.tools.map((t) => ({ name: t.name, description: t.description })),
);

show('tools/call guild_health', await client.callTool({ name: 'guild_health', arguments: {} }));
show(
  'tools/call list_sealable_protocols',
  await client.callTool({ name: 'list_sealable_protocols', arguments: {} }),
);
show('tools/call list_chapters', await client.callTool({ name: 'list_chapters', arguments: {} }));

await client.close();
