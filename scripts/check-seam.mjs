/**
 * Do the screens still reach past the adapter seam?
 *
 *   pnpm check:seam   (→ node scripts/check-seam.mjs)
 *
 * `servers/economics/proforma_mcp/server.py` says it plainly: the TypeScript
 * bioSTEAM port in `src/engine/biosteam/` "is exactly the second implementation
 * the migration exists to retire." A port with a removal date is only safe while
 * the code that calls it is small enough to move in one commit — and until this
 * gate existed, `screens/Plant.tsx` alone imported `evaluatePlantCached`,
 * `FLOWSHEET_BY_MODEL`, `runPlantUncertainty` and the module-global `CE`
 * directly, so "one commit" was a hope rather than a property.
 *
 * ── WHAT IS FORBIDDEN, AND WHY EXACTLY THESE THREE ────────────────────────
 *
 * The solve, and only the solve:
 *
 *   @/engine/plant        — build, size, cost, and solve the price
 *   @/engine/uncertainty  — two hundred of the above
 *   @/sim/flowsheets/*    — the plant definitions the solve runs on
 *
 * These are the three a real fermOS or Proforma server owns. Everything that
 * reaches them goes through `src/lib/use-plant.ts` and `src/lib/use-uncertainty.ts`,
 * which is what makes the eventual swap to `adapters.economics.solvePlant()` a
 * two-file change instead of an archaeology project.
 *
 * ── WHAT IS DELIBERATELY *NOT* FORBIDDEN ──────────────────────────────────
 *
 * `@/engine/biosteam/*` — the constant tables. `CEPCI_BY_YEAR` is the Chemical
 * Engineering Plant Cost Index, `DEPRECIATION_SCHEDULES` is MACRS, the utility
 * agents are upstream's published price list, and `AREA_NAMES` is a naming
 * convention. None of them retire with the port, because none of them are the
 * port: they are reference data reproduced rather than summarised, and
 * `BiosteamSettings.tsx` argues at length that a reviewer can only challenge the
 * number upstream actually ships. A gate that forbade them would force an
 * indirection that protects nothing.
 *
 * `@/engine/grids` — `evaluateGrid`, `buildGrid`, `mspSweep`. CLAUDE.md's table
 * keeps grid interpolation in TypeScript on purpose ("legitimate UI
 * convenience"), `adapters/types.ts` restates it where `CostModelSummary` is
 * defined, and five screens depend on it. Naming the carve-out here is what
 * stops somebody "tightening" this gate later and breaking a deliberate
 * decision.
 *
 * TYPE-ONLY IMPORTS PASS. `import type { PlantResult }` is erased at compile
 * time and couples nothing at runtime — the same distinction `check-purity.mjs`
 * draws, for the same reason.
 *
 * ── THE ALLOWLIST IS A LEDGER ─────────────────────────────────────────────
 *
 * Same discipline as `check-purity.mjs`: a NEW violation fails, and a STALE
 * entry fails too. An allowlist nobody prunes is a gate quietly widened.
 */
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { dirname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const ROOTS = [join(ROOT, 'src', 'screens'), join(ROOT, 'src', 'components')];

/** Runtime-forbidden import targets. */
const FORBIDDEN = [
  {
    test: (s) => s === '@/engine/plant',
    label: '@/engine/plant — the solve belongs behind src/lib/use-plant.ts',
  },
  {
    test: (s) => s === '@/engine/uncertainty',
    label: '@/engine/uncertainty — behind src/lib/use-uncertainty.ts',
  },
  {
    test: (s) => s.startsWith('@/sim/flowsheets'),
    label: '@/sim/flowsheets/* — a screen does not pick the plant it solves',
  },
];

/**
 * (file, specifier) pairs tolerated today, each with why.
 *
 * Empty, and that is the point: the pass that split fermOS's plant from
 * Proforma's price closed every one of these. An entry added here must carry a
 * reason a reader would accept, and must be pruned the day it stops matching.
 */
const ALLOWLIST = [];

function* tsxFiles(dir) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) yield* tsxFiles(p);
    else if (name.endsWith('.ts') || name.endsWith('.tsx')) yield p;
  }
}

const violations = [];
const matchedAllowlist = new Set();
let files = 0;
let imports = 0;

for (const root of ROOTS) {
  for (const file of tsxFiles(root)) {
    files += 1;
    const rel = relative(ROOT, file);
    const src = readFileSync(file, 'utf8');
    const lines = src.split('\n');
    for (const m of src.matchAll(
      /^import\s+(type\s+)?(?:[^'"]*?from\s+)?['"]([^'"]+)['"]/gm,
    )) {
      imports += 1;
      // `import type { X } from` — erased, couples nothing.
      if (m[1]) continue;
      const spec = m[2];
      const hit = FORBIDDEN.find((f) => f.test(spec));
      if (!hit) continue;
      const allowed = ALLOWLIST.find(([f, s]) => f === rel && s === spec);
      if (allowed) {
        matchedAllowlist.add(`${rel}|${spec}`);
        continue;
      }
      const line = lines.findIndex((l) => l.includes(spec) && l.startsWith('import')) + 1;
      violations.push({ rel, line, spec, label: hit.label });
    }
  }
}

const stale = ALLOWLIST.filter(([f, s]) => !matchedAllowlist.has(`${f}|${s}`));

let failed = false;

if (violations.length > 0) {
  failed = true;
  console.error('\n✗ a screen or component reaches past the seam:\n');
  for (const v of violations) {
    console.error(`  ${v.rel}:${v.line}`);
    console.error(`    ${v.label}`);
  }
  console.error(
    '\n  Route it through src/lib/use-plant.ts or src/lib/use-uncertainty.ts, or add an\n' +
      '  allowlist entry in scripts/check-seam.mjs with a reason a reader would accept.\n',
  );
}

if (stale.length > 0) {
  failed = true;
  console.error('\n✗ stale allowlist entries — the debt was paid, prune them:\n');
  for (const [f, s, why] of stale) console.error(`  ${f} → ${s}  (${why})`);
  console.error('\n  A stale allowlist is a gate quietly widened.\n');
}

if (failed) process.exit(1);

console.log(
  `✓ seam intact — ${files} screen/component files, ${imports} imports, ` +
    `0 runtime reaches into the solve (${ALLOWLIST.length} allowlisted)`,
);
