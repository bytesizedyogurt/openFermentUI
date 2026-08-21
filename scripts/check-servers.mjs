/**
 * The gate over `servers/` — five things that can drift silently, watched.
 *
 * 1. every manifest agrees with the server beside it, and names corpus
 *    files that exist;
 * 2. the corpus snapshot id is byte-identical from TypeScript and Python;
 * 3. the cost model matches across both implementations;
 * 4. record attribution matches across both;
 * 5. and neither side attributed nothing — two implementations agreeing on
 *    an empty result prove nothing, so that agreement is a failure. This
 *    fifth check is why the docstring used to say four: a guard against a
 *    vacuous pass is as much a check as the comparison it guards.
 *
 * A server skeleton is mostly documentation, and documentation is exactly what
 * rots without a gate. Each check below exists because there is a specific way
 * this directory can start lying while every other test still passes.
 *
 *  1. MANIFEST ↔ SERVER. Every manifest declares a tool list. A manifest is
 *     what an operator reads before wiring a server into an agent, so a
 *     manifest that names a tool the server does not register — or misses one
 *     it does — is worse than no manifest. Checked by parsing the tool names
 *     out of each server's source and comparing the sets.
 *
 *  2. SNAPSHOT PARITY, TypeScript against Python. `corpusSnapshotId` is the
 *     one field that says what an answer was computed against. The first two
 *     servers written each grew their own framing and disagreed, so two
 *     servers reading the same file reported different ids. Both halves are
 *     now fed the same inputs — including the adversarial pair that a framing
 *     without a length prefix collapses — and must agree exactly.
 *
 *  3. COST MODEL DERIVATION. `proforma_mcp` derives its CostModelSummary from
 *     `data/corpus/scenarios.json` rather than carrying a copy. That is only
 *     safe while the derivation still equals the TypeScript `COST_MODELS`; the
 *     day someone edits one and not the other, the server starts serving a
 *     frame nothing else is quoted in.
 *
 *  4. ATTRIBUTION PARITY. "Which records count for a strain" now exists in
 *     Python (canonical) and TypeScript (`src/adapters/fixture/cell.ts`, which
 *     names its own retirement). Every strain is replayed through both and the
 *     record ids must match, in order.
 *
 * Deliberately NOT checked here: that the servers start. They do — each has a
 * smoke client that drives it over real stdio, and the transcripts are in the
 * READMEs — but running five MCP servers needs five virtualenvs and a node
 * install per server, which is a CI job and not a `pnpm verify` stage. The
 * READMEs say which parts are PROVEN and which are merely written.
 */
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { join } from 'node:path';

const ROOT = process.cwd();
const SERVERS = join(ROOT, 'servers');
const failures = [];
const notes = [];

function fail(msg) {
  failures.push(msg);
}

// ── 1. Manifest ↔ server ──────────────────────────────────────────────────
//
// Tool names are read out of the source rather than by importing it: importing
// a Python server means having its venv, and importing the TypeScript one
// means starting it. A regex over the registration site is enough, because the
// registration site is the only place a tool name appears as a definition.

/** `@mcp.tool(name="x", ...)` in the Python servers. */
const PY_TOOL = /@mcp\.tool\(\s*name\s*=\s*"([^"]+)"/g;
/** `name: 'x',` at the indentation the guild server's TOOLS array uses. */
const TS_TOOL = /^ {4}name: '([^']+)',$/gm;

function toolNamesFromSource(dir) {
  const py = readdirSync(dir, { withFileTypes: true })
    .filter((e) => e.isDirectory() && e.name.endsWith('_mcp'))
    .map((e) => join(dir, e.name, 'server.py'))
    .filter(existsSync);
  if (py.length === 1) {
    return [...readFileSync(py[0], 'utf8').matchAll(PY_TOOL)].map((m) => m[1]);
  }
  const ts = join(dir, 'src', 'server.ts');
  if (existsSync(ts)) {
    return [...readFileSync(ts, 'utf8').matchAll(TS_TOOL)].map((m) => m[1]);
  }
  return null;
}

/**
 * The only statuses a manifest may give a tool.
 *
 *  - `implemented` — answers for real.
 *  - `implemented-empty` — answers, and the answer is permanently empty because
 *    the thing it would list does not exist. Distinct from a refusal: the tool
 *    works, and the emptiness is the finding.
 *  - `declared-refuses` — the shape is fixed and the tool raises, naming what is
 *    missing and what it will return once that exists.
 */
const TOOL_STATUS = new Set(['implemented', 'implemented-empty', 'declared-refuses']);

const dirs = readdirSync(SERVERS, { withFileTypes: true })
  .filter((e) => e.isDirectory())
  .map((e) => e.name)
  .sort();

if (dirs.length === 0) fail('servers/ holds no server directories.');

for (const name of dirs) {
  const dir = join(SERVERS, name);
  const manifestPath = join(dir, 'manifest.json');
  if (!existsSync(manifestPath)) {
    fail(
      `servers/${name}: no manifest.json. A server an operator cannot read before wiring it up is not a skeleton, it is a surprise.`,
    );
    continue;
  }
  if (!existsSync(join(dir, 'README.md'))) {
    fail(`servers/${name}: no README.md stating what is PROVEN versus merely written.`);
  }
  if (!existsSync(join(dir, 'Dockerfile'))) {
    fail(`servers/${name}: no Dockerfile.`);
  }

  let manifest;
  try {
    manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
  } catch (err) {
    fail(`servers/${name}/manifest.json does not parse: ${err.message}`);
    continue;
  }

  const declared = (manifest.tools ?? []).map((t) => t.name);
  if (declared.length === 0) fail(`servers/${name}/manifest.json declares no tools.`);

  // A closed vocabulary, because an operator reads five of these and must not
  // have to work out whether 'stub' and 'declared-refuses' mean the same thing.
  // They did diverge: `process` said 'stub' where the other four said
  // 'declared-refuses' for exactly the same behaviour.
  for (const tool of manifest.tools ?? []) {
    if (!TOOL_STATUS.has(tool.status)) {
      fail(
        `servers/${name}: tool '${tool.name}' has status '${tool.status}', which is not one of ` +
          `${[...TOOL_STATUS].map((v) => `'${v}'`).join(', ')}. One vocabulary across all five manifests.`,
      );
    }
  }

  const registered = toolNamesFromSource(dir);
  if (registered === null) {
    fail(
      `servers/${name}: no server.py under a *_mcp package and no src/server.ts — cannot read its tool names.`,
    );
    continue;
  }

  const missing = declared.filter((t) => !registered.includes(t));
  const extra = registered.filter((t) => !declared.includes(t));
  if (missing.length) {
    fail(
      `servers/${name}: manifest declares ${missing.map((t) => `'${t}'`).join(', ')} but the server registers no such tool.`,
    );
  }
  if (extra.length) {
    fail(
      `servers/${name}: the server registers ${extra.map((t) => `'${t}'`).join(', ')} which the manifest does not declare. An undeclared tool is one nobody reviewed.`,
    );
  }

  // Every corpus file a manifest claims must exist, or the snapshot id it
  // promises is a digest over something else.
  for (const rel of manifest.corpus ?? []) {
    if (!existsSync(join(ROOT, rel))) {
      fail(`servers/${name}/manifest.json names corpus file ${rel}, which does not exist.`);
    }
  }
  notes.push(`servers/${name}: ${registered.length} tools, manifest agrees`);
}

// ── 2. Snapshot parity, TypeScript against Python ─────────────────────────

const NUL = Buffer.from([0]);

/** Mirror of `corpusSnapshotId` in servers/guild/src/meta.ts. */
function tsSnapshotId(files) {
  const hash = createHash('sha256');
  for (const name of Object.keys(files).sort()) {
    const content = files[name];
    hash.update(Buffer.from(name, 'utf8'));
    hash.update(NUL);
    hash.update(Buffer.from(String(content.length), 'ascii'));
    hash.update(NUL);
    hash.update(content);
  }
  return `sha256:${hash.digest('hex').slice(0, 16)}`;
}

/**
 * The inputs both halves are fed.
 *
 * The two synthetic entries are the adversarial pair: without a length prefix,
 * a file whose name ends in a NUL and a file whose content begins with one
 * frame to identical bytes, so a framing that dropped the length would pass
 * every realistic case and collide on this one. Real corpus files are in here
 * too, because a mirror that only agrees on synthetic input has not been
 * tested against the thing it actually runs on.
 */
const SNAPSHOT_CASES = [
  {},
  { 'data/corpus/protocols.json': readFileSync(join(ROOT, 'data/corpus/protocols.json')) },
  {
    'data/corpus/papers.json': readFileSync(join(ROOT, 'data/corpus/papers.json')),
    'data/corpus/records.json': readFileSync(join(ROOT, 'data/corpus/records.json')),
  },
  { a: Buffer.concat([Buffer.from('b'), NUL, Buffer.from('c')]) },
  { [`a${String.fromCharCode(0)}b`]: Buffer.from('c') },
  { 'unicode-π-Δ.json': Buffer.from('{"β":"casein"}', 'utf8') },
];

{
  const payload = SNAPSHOT_CASES.map((files) =>
    Object.fromEntries(Object.entries(files).map(([k, v]) => [k, v.toString('base64')])),
  );
  const script = [
    'import base64, json, sys',
    'sys.path.insert(0, "packages/core")',
    'from openferment_core.snapshot import corpus_snapshot_id',
    'cases = json.load(sys.stdin)',
    'out = [corpus_snapshot_id({k: base64.b64decode(v) for k, v in c.items()}) for c in cases]',
    'json.dump(out, sys.stdout)',
  ].join('\n');

  let pyIds = null;
  try {
    pyIds = JSON.parse(
      execFileSync('python3', ['-c', script], {
        input: JSON.stringify(payload),
        encoding: 'utf8',
        cwd: ROOT,
        maxBuffer: 64 * 1024 * 1024,
      }),
    );
  } catch (err) {
    fail(`snapshot parity: the Python half could not be run — ${err.message}`);
  }

  if (pyIds) {
    const tsIds = SNAPSHOT_CASES.map(tsSnapshotId);
    // Distinctness first: two halves that both returned a constant would agree
    // perfectly and prove nothing.
    const distinct = new Set(tsIds).size;
    if (distinct !== tsIds.length) {
      fail(
        `snapshot parity: ${tsIds.length - distinct} of ${tsIds.length} cases collide — the digest is not discriminating between them.`,
      );
    }
    for (let i = 0; i < tsIds.length; i += 1) {
      if (tsIds[i] !== pyIds[i]) {
        const label = Object.keys(SNAPSHOT_CASES[i]).join(', ') || 'empty';
        fail(
          `snapshot parity case ${i} (${label}): TypeScript says ${tsIds[i]}, Python says ${pyIds[i]}.`,
        );
      }
    }
    notes.push(`snapshot parity: ${tsIds.length} cases, TS and Python agree, all distinct`);
  }
}

// ── 3 and 4 need the TypeScript side loaded, which needs tsx. ─────────────
//
// Run as a child so this file stays a plain .mjs the other gates sit beside,
// and so a failure to load the app's module graph is reported as a gate
// failure rather than a crash.
{
  const probe = join(ROOT, 'scripts', 'check-servers-ts.ts');
  let tsSide = null;
  try {
    tsSide = JSON.parse(
      execFileSync('npx', ['tsx', probe], { encoding: 'utf8', cwd: ROOT, maxBuffer: 64 * 1024 * 1024 }),
    );
  } catch (err) {
    fail(`could not load the TypeScript side (${probe}): ${err.message}`);
  }

  if (tsSide) {
    const script = [
      'import json, sys',
      'sys.path.insert(0, "packages/core")',
      'from openferment_core.corpus import CorpusReader, records_attributed_to',
      'from openferment_core.schema import ExtractionRecord, Paper, Scenario, Strain',
      'r = CorpusReader()',
      'scenarios = r.load("scenarios", Scenario)',
      'strains = r.load("strains", Strain)',
      'papers = r.load("papers", Paper)',
      'records = r.load("records", ExtractionRecord)',
      'summaries = [{',
      '    "modelId": s.model_id,',
      '    "dims": [{"key": d.key, "label": d.label, "unit": d.unit, "values": list(d.values),',
      '              **({"field": d.field} if d.field is not None else {})} for d in s.dims],',
      '    "referencePoint": dict(s.point),',
      '} for s in scenarios]',
      'attribution = {s.id: [x.id for x in records_attributed_to(records, papers, s.id)] for s in strains}',
      'json.dump({"summaries": summaries, "attribution": attribution}, sys.stdout)',
    ].join('\n');

    let pySide = null;
    try {
      pySide = JSON.parse(
        execFileSync('python3', ['-c', script], {
          encoding: 'utf8',
          cwd: ROOT,
          maxBuffer: 64 * 1024 * 1024,
        }),
      );
    } catch (err) {
      fail(`cost-model / attribution parity: the Python half could not be run — ${err.message}`);
    }

    if (pySide) {
      const fromCorpus = JSON.stringify(pySide.summaries);
      const fromModels = JSON.stringify(tsSide.summaries);
      if (fromCorpus !== fromModels) {
        fail(
          'cost-model derivation: proforma_mcp derives its CostModelSummary from ' +
            'data/corpus/scenarios.json, and that derivation no longer equals COST_MODELS in ' +
            'src/data/scenarios.ts. One of the two was edited without the other.\n' +
            `      from scenarios.json: ${fromCorpus.slice(0, 300)}\n` +
            `      from COST_MODELS:    ${fromModels.slice(0, 300)}`,
        );
      } else {
        notes.push(
          `cost models: ${pySide.summaries.length} summaries derive exactly from the corpus`,
        );
      }

      const pyStrains = Object.keys(pySide.attribution).sort();
      const tsStrains = Object.keys(tsSide.attribution).sort();
      if (JSON.stringify(pyStrains) !== JSON.stringify(tsStrains)) {
        fail(
          `attribution parity: strain sets differ — Python ${pyStrains.join(', ')} vs TypeScript ${tsStrains.join(', ')}.`,
        );
      }
      let total = 0;
      for (const id of pyStrains) {
        const py = pySide.attribution[id] ?? [];
        const ts = tsSide.attribution[id] ?? [];
        total += py.length;
        if (JSON.stringify(py) !== JSON.stringify(ts)) {
          const firstOnlyInPy = py.find((x, i) => ts[i] !== x);
          fail(
            `attribution parity for strain '${id}': Python attributes ${py.length} records, ` +
              `TypeScript ${ts.length}. First divergence: ` +
              `${firstOnlyInPy ?? '(none — TypeScript has extras)'}.`,
          );
        }
      }
      // A rule that attributed nothing to anything would agree trivially.
      if (total === 0) {
        fail(
          'attribution parity: both sides attributed zero records to every strain. That agreement proves nothing.',
        );
      } else {
        notes.push(
          `attribution: ${total} records across ${pyStrains.length} strains, Python and TypeScript agree`,
        );
      }
    }
  }
}

// ── Report ────────────────────────────────────────────────────────────────

if (failures.length) {
  console.error('✗ servers/ gate failed:\n');
  for (const f of failures) console.error(`  • ${f}`);
  process.exit(1);
}
for (const n of notes) console.log(`  ${n}`);
console.log(`✓ servers/ — ${dirs.length} servers, manifests agree, TS/Python parity holds.`);
