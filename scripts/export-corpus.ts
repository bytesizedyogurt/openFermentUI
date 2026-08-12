/**
 * Export the seven corpus collections to `data/corpus/*.json`, validating every
 * entity through the Phase 1 Pydantic models on the way out.
 *
 *   pnpm export:corpus    →  tsx scripts/export-corpus.ts
 *
 * ── What this is for ───────────────────────────────────────────────────
 *
 * The corpus is authored today in `src/data/corpus/*.ts` and assembled by
 * `papers.ts` / `records.ts`. Those thread files are being deleted; after that
 * the JSON under `data/corpus/` IS the corpus, and this script stops being a
 * migration step and becomes a round-trip check.
 *
 * So it reads from `@/data/source` — the adapter — and never from the thread
 * files. Reading the thread files would keep working right up until they were
 * deleted and would then export nothing, and pointing at what is about to be
 * the source rather than what is about to be deleted is the whole reason the
 * adapter was specified before either side was written.
 *
 * Once the migration lands, running this is a FIXED POINT: it reads the JSON
 * through the adapter, validates it against the models, and writes it back
 * byte-identically. `git diff --stat data/corpus` after a run is the acceptance
 * test, and it is what makes it safe to hand-edit the JSON later — an edit that
 * breaks the schema is reported with the entity id and the field, and an edit
 * that does not is normalised into the canonical form on the next run.
 *
 * ── The rule when validation fails ─────────────────────────────────────
 *
 * Per CLAUDE.md and `packages/core/scripts/validate_fixtures.py`: where a real
 * corpus entity fails to parse, the MODEL is wrong and the model gets fixed —
 * never the data. Every failure is reported, with its entity id and field,
 * BEFORE anything is written; a failed run writes nothing at all, so a partial
 * export can never leave the seven files disagreeing with each other.
 *
 * ── What is not here ───────────────────────────────────────────────────
 *
 * `COST_MODELS` in `src/data/scenarios.ts` stays in TypeScript. It carries an
 * `evaluate` function, and `CostModel` / `ResultGrid` were established in Phase
 * 1 as the two types that cannot round-trip through JSON Schema (see the module
 * docstring of `packages/core/openferment_core/schema/econ.py`). Only
 * `SCENARIOS` moves. The serialisability audit below exists partly so that a
 * function which ever leaks into an exported collection is a loud failure
 * rather than a key that `JSON.stringify` drops in silence.
 *
 * ── Determinism ────────────────────────────────────────────────────────
 *
 * Two consecutive runs must produce byte-identical files. Every source of
 * instability that was available to this script, and what closed it:
 *
 *  1. KEY ORDER. Not JavaScript object insertion order, and not a sort. The
 *     bytes are emitted by `model_dump()`, so key order is Pydantic field
 *     declaration order — fixed by the model source, identical for every
 *     instance of a type, and the one ordering that stays meaningful when a
 *     human reads the file. The single free-form mapping in the exported set
 *     (`Scenario.point`) keeps its source order rather than being sorted,
 *     because that order mirrors `dims` and sorting would destroy the
 *     correspondence for no gain; preserving it is equally deterministic.
 *  2. COLLECTION ORDER. Preserved exactly as the adapter yields it, never
 *     re-sorted. Array order is data here: `LearnModule.index` and the
 *     catalogue order of papers are authored. A sort would be stable and
 *     deterministic and would still be wrong.
 *  3. FLOAT FORMATTING. Python's `repr` (shortest round-trip), not JavaScript's
 *     `Number#toString`, because Python writes the bytes. The models widen many
 *     integer-valued fields to `float`, which would have rewritten 460 of the
 *     corpus's 1133 numbers from `10` to `10.0` on the first run — a diff large
 *     enough to hide a real change during the cutover review. `keep_int` puts
 *     the source's own integer spelling back wherever the model's value is
 *     numerically equal, so the models canonicalise structure without rewriting
 *     values. Still a fixed point: `10` parses to a Python int on the next run
 *     and stays one.
 *  4. NaN / Infinity. Rejected here, on the live objects, BEFORE serialisation.
 *     `JSON.stringify` turns both into `null` without complaint, so by the time
 *     Python sees the payload the evidence is gone. Python also passes
 *     `allow_nan=False` as a backstop.
 *  5. ABSENT vs EXPLICIT NULL. One representation: absent. `exclude_none=True`
 *     on the way out, matching `JSON.stringify` dropping an `undefined` value
 *     and matching the convention `validate_fixtures.py` already enforces. A
 *     hand-written `null` on an optional field normalises to an absent key on
 *     the next export rather than persisting as a third state.
 *  6. UNICODE. `ensure_ascii=False`. The corpus is full of µ, ⁻¹, β, §, em
 *     dashes and °; they are written as themselves, in UTF-8, with zero `\uXXXX`
 *     escapes. `PYTHONIOENCODING=utf-8` is set so the report survives a host
 *     whose locale is not UTF-8.
 *  7. LINE ENDINGS. `\n`, written explicitly by Python's `json.dumps` and
 *     passed through by `writeFileSync` — never the platform's.
 *  8. TRAILING NEWLINE. Exactly one, at end of file. No trailing whitespace on
 *     any line: `separators=(',', ': ')` with `indent=2` never emits any.
 *  9. NO GENERATION METADATA IN THE FILES. No timestamp, no git sha, no host,
 *     no counts header. Each file is a bare top-level array — which is also
 *     what lets the adapter fill its arrays from a static JSON import with no
 *     unwrapping. A `generatedAt` field would make every single run differ, and
 *     is the most common way an exporter quietly loses this property.
 * 10. CWD. Paths derive from this file's own URL, not `process.cwd()`, so the
 *     output does not depend on where it was invoked from.
 * 11. SET ITERATION. Nothing in the emitting path iterates a Python set, so
 *     `PYTHONHASHSEED` cannot leak into the bytes.
 * 12. THE FILESYSTEM ITSELF. Each file is read back after writing and compared
 *     to the exact string that was meant to land there.
 */
import { execFileSync } from 'node:child_process';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  MODULES,
  ONTOLOGY,
  PAPERS,
  PROTOCOLS,
  RECORDS,
  SCENARIOS,
  STRAINS,
  corpusBackend,
  initCorpus,
} from '@/data/source';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const OUT = join(ROOT, 'data', 'corpus');

const errors: string[] = [];
const fail = (m: string) => errors.push(m);

/**
 * A no-op under the bundled backend, which is what Node always gets. It is
 * awaited anyway because the adapter's contract says a reader awaits it, and a
 * script that skips the step because it happens to know the answer today is a
 * script that breaks the day the answer changes.
 */
await initCorpus();

if (corpusBackend() !== 'bundled') {
  console.error(
    `✗ corpusBackend() is "${corpusBackend()}" under Node — it must be "bundled".\n` +
      '  Exporting the bundled JSON from the API backend would write the server’s\n' +
      '  answer back over the file the server is meant to be serving.',
  );
  process.exit(1);
}

/** Collection key → `data/corpus/<key>.json`. The key is also what the Python
 *  half maps to a model, so the two tables are checked against each other. */
const COLLECTIONS: [key: string, items: readonly unknown[]][] = [
  ['papers', PAPERS],
  ['records', RECORDS],
  ['ontology', ONTOLOGY],
  ['strains', STRAINS],
  ['protocols', PROTOCOLS],
  ['scenarios', SCENARIOS],
  ['learn', MODULES],
];

// ── 1. every collection must be non-empty ──────────────────────────────
// An exporter that writes `[]` for the whole corpus and exits 0 is the worst
// bug available to this script: it destroys the corpus and reports success.
// Emptiness is therefore a failure, not an edge case, and it is checked before
// anything is serialised.
for (const [key, items] of COLLECTIONS) {
  if (items.length === 0) fail(`${key}: collection is empty — refusing to export an empty corpus`);
}

// ── 2. everything must survive JSON without silent damage ──────────────
// `JSON.stringify` does not throw on most of what it cannot represent; it drops
// function-valued keys, turns NaN and Infinity into null, turns a Float64Array
// into an object of numeric keys, and turns a Date into a string. Each of those
// is a silent corpus edit. The walk is over the LIVE objects, before any
// serialisation, because afterwards the evidence is gone.
function auditSerializable(node: unknown, path: string, seen: Set<object>, bad: string[]): void {
  if (node === null) return;
  const t = typeof node;
  if (t === 'string' || t === 'boolean') return;
  if (t === 'number') {
    if (!Number.isFinite(node)) bad.push(`${path}: ${String(node)} has no JSON representation`);
    return;
  }
  if (t === 'function') {
    bad.push(`${path}: a function cannot be exported — JSON.stringify drops the key in silence`);
    return;
  }
  if (t === 'bigint' || t === 'symbol' || t === 'undefined') {
    bad.push(`${path}: ${t} cannot be exported`);
    return;
  }
  const obj = node as object;
  if (seen.has(obj)) {
    bad.push(`${path}: circular reference`);
    return;
  }
  seen.add(obj);
  if (Array.isArray(node)) {
    node.forEach((v, i) => {
      // An `undefined` array slot becomes `null`, which is a value, not an
      // absence — unlike an `undefined` object property, which is a real absence.
      if (v === undefined) bad.push(`${path}[${i}]: undefined inside an array becomes null`);
      else auditSerializable(v, `${path}[${i}]`, seen, bad);
    });
  } else {
    const proto = Object.getPrototypeOf(obj);
    if (proto !== null && proto !== Object.prototype) {
      const name = obj.constructor?.name ?? 'a class instance';
      bad.push(`${path}: ${name} is not a plain object and does not survive JSON intact`);
    } else {
      for (const [k, v] of Object.entries(obj)) {
        // An absent optional. JSON.stringify drops the key and `exclude_none`
        // on the Python side agrees, so the two ends mean the same thing.
        if (v === undefined) continue;
        auditSerializable(v, `${path}.${k}`, seen, bad);
      }
    }
  }
  seen.delete(obj);
}

for (const [key, items] of COLLECTIONS) {
  const bad: string[] = [];
  const ids = new Map<string, number>();
  items.forEach((item, i) => {
    if (item === null || typeof item !== 'object' || Array.isArray(item)) {
      bad.push(`${key}[${i}]: not an entity object`);
      return;
    }
    const id = (item as { id?: unknown }).id;
    if (typeof id !== 'string' || id === '') {
      bad.push(`${key}[${i}]: has no string id`);
    } else if (ids.has(id)) {
      // A duplicate id survives JSON and then silently overwrites its twin in
      // every by-id map the app builds. It has to die here.
      bad.push(`${key}[${i}]: duplicate id "${id}", already used at [${ids.get(id)}]`);
    } else {
      ids.set(id, i);
    }
    auditSerializable(item, `${key}[${i}]${typeof id === 'string' ? ` (${id})` : ''}`, new Set(), bad);
  });
  for (const b of bad) fail(b);
}

if (errors.length) {
  console.error('✗ the corpus cannot be serialised as it stands:');
  for (const e of errors) console.error(`  - ${e}`);
  console.error('\nNothing was written.');
  process.exit(1);
}

// ── 3. validate and canonicalise in Python ─────────────────────────────
// The models are the schema; the schema is Python; so Python decides what the
// bytes look like. This script hands over the collections and gets back the
// exact text to write, which keeps every serialisation decision in one place
// instead of half here and half there.
const PY = String.raw`
import json
import sys
from pathlib import Path
from typing import Any


def bail(msg: str) -> None:
    json.dump({"ok": False, "fatal": msg}, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    raise SystemExit(0)


ROOT = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(ROOT / "packages" / "core"))
sys.path.insert(0, str(ROOT / "packages" / "core" / "scripts"))

try:
    from pydantic import ValidationError
    from openferment_core import schema as S

    # Imported rather than reimplemented. These three decide what counts as the
    # model having altered an entity, and check:schema already enforces that
    # definition against the same corpus; a second copy here would be a second
    # answer to the same question, which is the failure mode CLAUDE.md names.
    from validate_fixtures import diff_summary, identify, prune_none
except Exception as exc:
    bail(f"{type(exc).__name__}: {exc}")

MODELS = {
    "papers": S.Paper,
    "records": S.ExtractionRecord,
    "ontology": S.ParameterDef,
    "strains": S.Strain,
    "protocols": S.Protocol,
    "scenarios": S.Scenario,
    "learn": S.LearnModule,
}

DUMP = dict(by_alias=True, exclude_none=True, mode="json")


def keep_int(raw: Any, emitted: Any) -> Any:
    """Give back the source's integer spelling where the model widened it.

    Many corpus fields are typed float and hold whole numbers, so a plain dump
    rewrites 10 as 10.0 throughout. The value is identical either way and the
    fidelity check below proves it, but the diff is not: 460 of the corpus's
    1133 numbers would move on the first run and a real change could hide among
    them. Structure is canonicalised by the models; the numbers stay as the
    corpus wrote them. Idempotent, because 10 parses back to a Python int.
    """
    if isinstance(emitted, bool) or isinstance(raw, bool):
        return emitted
    if isinstance(emitted, float) and isinstance(raw, int) and raw == emitted:
        return raw
    if isinstance(emitted, dict) and isinstance(raw, dict):
        return {k: keep_int(raw[k], v) if k in raw else v for k, v in emitted.items()}
    if isinstance(emitted, list) and isinstance(raw, list) and len(raw) == len(emitted):
        return [keep_int(a, b) for a, b in zip(raw, emitted)]
    return emitted


def canon(model: Any, raw: Any) -> Any:
    return keep_int(raw, model.model_validate(raw).model_dump(**DUMP))


def short(v: Any) -> str:
    r = repr(v)
    return r if len(r) <= 110 else r[:110] + "…"


def canonical(items: list[Any]) -> str:
    return json.dumps(
        items,
        ensure_ascii=False,
        indent=2,
        separators=(",", ": "),
        allow_nan=False,
        sort_keys=False,
    ) + "\n"


def main() -> None:
    payload = json.load(sys.stdin)
    failures: list[str] = []
    out: list[dict[str, Any]] = []

    for key, items in payload["collections"]:
        model = MODELS.get(key)
        if model is None:
            failures.append(f"{key}: no Pydantic model is mapped to this collection")
            continue
        if not items:
            failures.append(f"{key}: collection is empty")
            continue

        dumped: list[Any] = []
        for i, raw in enumerate(items):
            ident = identify(raw, i)
            try:
                parsed = model.model_validate(raw)
            except ValidationError as e:
                for err in e.errors():
                    loc = ".".join(str(p) for p in err["loc"]) or "(entity)"
                    failures.append(
                        f"{key}/{ident}: {loc} — {err['msg']} (got {short(err.get('input'))})"
                    )
                continue

            emitted = keep_int(raw, parsed.model_dump(**DUMP))

            # The model parsed it — but did it keep it? A model that accepts an
            # entity and re-emits something different has renamed or dropped a
            # field, and this exporter would write the difference to disk.
            drift = diff_summary(prune_none(raw), emitted)
            if drift:
                failures.append(f"{key}/{ident}: {model.__name__} altered the entity — {drift}")
                continue

            # And is the emitted form a fixed point of the models? This is the
            # per-entity proof of the property the whole script claims. It also
            # catches the one way exclude_none can bite: a required field whose
            # value is None is dropped on the way out and then fails to parse on
            # the way back in.
            try:
                again = canon(model, emitted)
            except ValidationError as e:
                err = e.errors()[0]
                loc = ".".join(str(p) for p in err["loc"]) or "(entity)"
                failures.append(
                    f"{key}/{ident}: emitted JSON does not re-validate — {loc}: {err['msg']}"
                )
                continue
            if again != emitted:
                failures.append(
                    f"{key}/{ident}: not a fixed point — {diff_summary(emitted, again)}"
                )
                continue

            dumped.append(emitted)

        if len(dumped) != len(items):
            continue
        text = canonical(dumped)
        out.append(
            {
                "key": key,
                "model": model.__name__,
                "count": len(dumped),
                "bytes": len(text.encode("utf-8")),
                "text": text,
            }
        )

    report: dict[str, Any] = {
        "ok": not failures,
        "pydantic": __import__("pydantic").VERSION,
        "failures": failures,
        # No failures, no text: a run that is not going to be written does not
        # need to ship 550 KB back across the pipe.
        "collections": out
        if not failures
        else [{k: v for k, v in c.items() if k != "text"} for c in out],
    }
    json.dump(report, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


main()
`;

interface Emitted {
  key: string;
  model: string;
  count: number;
  bytes: number;
  text: string;
}
interface Report {
  ok: boolean;
  fatal?: string;
  pydantic?: string;
  failures: string[];
  collections: Emitted[];
}

let stdout: string;
try {
  stdout = execFileSync('python3', ['-c', PY, ROOT], {
    input: JSON.stringify({ collections: COLLECTIONS }),
    encoding: 'utf8',
    // The report carries the full text of all seven files; the 1 MB default
    // would truncate it into a parse error that looked like a Python bug.
    maxBuffer: 512 * 1024 * 1024,
    stdio: ['pipe', 'pipe', 'inherit'],
    env: { ...process.env, PYTHONIOENCODING: 'utf-8', PYTHONDONTWRITEBYTECODE: '1' },
  });
} catch (e) {
  console.error(`✗ python3 failed: ${e instanceof Error ? e.message : String(e)}`);
  console.error('\nNothing was written.');
  process.exit(1);
}

// The report is the last line, not the whole stream: a site-wide `sitecustomize`
// or a deprecation notice printed to stdout would otherwise turn a clean run
// into an unreadable parse error.
const lastLine = stdout.trimEnd().split('\n').pop() ?? '';
let report: Report;
try {
  report = JSON.parse(lastLine) as Report;
} catch {
  console.error('✗ could not read the validator report. python3 said:\n');
  console.error(stdout);
  process.exit(1);
}

if (report.fatal) {
  console.error(`✗ the Python side could not start: ${report.fatal}`);
  console.error('  packages/core must be importable and pydantic installed.');
  console.error('\nNothing was written.');
  process.exit(1);
}

if (!report.ok) {
  console.error(
    `✗ ${report.failures.length} validation failure(s). Per CLAUDE.md the MODEL is wrong here,\n` +
      '  not the data — the corpus is real literature and its gaps are deliberate.\n' +
      '  Report these before changing anything:\n',
  );
  for (const f of report.failures) console.error(`  - ${f}`);
  console.error('\nNothing was written.');
  process.exit(1);
}

if (report.collections.length !== COLLECTIONS.length) {
  console.error(
    `✗ asked for ${COLLECTIONS.length} collections, got ${report.collections.length} back.`,
  );
  process.exit(1);
}

// ── 4. write ───────────────────────────────────────────────────────────
// Only now, and only all seven. Everything above this line is a check, so a
// failed run leaves the previous export exactly as it was.
mkdirSync(OUT, { recursive: true });

console.log('openFerment corpus export');
console.log('─────────────────────────');
let totalEntities = 0;
let totalBytes = 0;
for (const c of report.collections) {
  const path = join(OUT, `${c.key}.json`);
  writeFileSync(path, c.text, { encoding: 'utf8' });
  const readBack = readFileSync(path, 'utf8');
  if (readBack !== c.text) {
    console.error(`\n✗ ${relative(ROOT, path)} does not read back as it was written.`);
    process.exit(1);
  }
  totalEntities += c.count;
  totalBytes += c.bytes;
  console.log(
    `  ${`${c.key}.json`.padEnd(16)} ${String(c.count).padStart(4)} ${c.model.padEnd(17)} ` +
      `${(c.bytes / 1024).toFixed(0).padStart(4)} KB`,
  );
}

console.log('  ────────────────────────────────────────────────');
console.log(
  `  ${totalEntities} entities · ${(totalBytes / 1024).toFixed(0)} KB · ` +
    `${report.collections.length} files · pydantic ${report.pydantic}`,
);
console.log(`  written to ${relative(ROOT, OUT)}/`);
console.log(
  '\n  Every entity parsed, round-tripped unchanged through its model, and is a\n' +
    '  fixed point of it. Run again and `git diff --stat data/corpus` stays empty.',
);
