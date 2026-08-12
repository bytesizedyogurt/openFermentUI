/**
 * Generate src/data/types.generated.ts from the Pydantic models.
 *
 * Three steps, in this order, and none of them touches the TypeScript by hand:
 * emit JSON Schema from Python, run the generator over it, then prepend a header
 * saying where the file came from. If the generated output ever needs an edit to
 * compile, the fix belongs in the models — a generated file that somebody has
 * patched is a file that has quietly stopped being generated, and the whole
 * point of this phase is that the schema has exactly one home.
 */
import { execFileSync } from 'node:child_process';
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const ROOT = process.cwd();
const SCHEMA = join(ROOT, 'packages/core/schema/openferment.schema.json');
const OUT = join(ROOT, 'src/data/types.generated.ts');

console.log('openFerment type generation');
console.log('───────────────────────────');

execFileSync('python3', [join(ROOT, 'packages/core/scripts/emit_schema.py')], {
  stdio: 'inherit',
  cwd: ROOT,
});

execFileSync(
  join(ROOT, 'node_modules/.bin/json2ts'),
  [
    '--input', SCHEMA,
    '--output', OUT,
    // The models set extra='forbid', so every object is closed. Without this the
    // generator adds an index signature to anything it thinks might be open, and
    // an index signature makes every typo compile.
    '--additionalProperties', 'false',
    '--bannerComment', '',
    '--style.singleQuote',
    '--style.printWidth', '100',
  ],
  { stdio: 'inherit', cwd: ROOT },
);

const HEADER = `/* eslint-disable */
/**
 * GENERATED — do not edit.
 *
 * Source of truth: the Pydantic models in \`packages/core/openferment_core/schema\`.
 * Regenerate with \`pnpm gen:types\`.
 *
 * Editing this file is the failure the migration exists to prevent: a schema
 * maintained in two languages is two schemas, and they diverge on the day
 * nobody is looking. Change the Python and run the generator.
 *
 * Two types are NOT here and cannot be: \`CostModel\` carries a function and
 * \`ResultGrid\` carries \`Float64Array\`. Neither is a data shape and neither
 * survives JSON Schema. They are hand-written in \`types.ts\`, which re-exports
 * everything below.
 */

`;

const body = readFileSync(OUT, 'utf8');
writeFileSync(OUT, HEADER + body.replace(/^\s*\n/, ''), 'utf8');

const exported = [...body.matchAll(/^export (?:interface|type) (\w+)/gm)].map((m) => m[1]);
console.log(`  src/data/types.generated.ts   ${exported.length} exported types`);
