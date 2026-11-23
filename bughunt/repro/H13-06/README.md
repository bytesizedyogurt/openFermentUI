# H13-06: the CI workflow's comment names smoke.mjs, and the smoke is scripts/smoke.ts

**Statement.** The header of `.github/workflows/verify.yml` says "smoke.mjs also honours
CHROMIUM_PATH"; the tree at `2047f5a` holds no `smoke.mjs` anywhere, and the smoke `pnpm smoke` runs
is `scripts/smoke.ts`, which reads `CHROMIUM_PATH` at line 167 (as `scripts/walk.ts` does at line 170).

**Contract.**
- `.github/workflows/verify.yml:14-16`: "The browser scripts try the pre-installed one first
  (smoke.mjs also honours CHROMIUM_PATH) and fall back to Playwright's own cache, which is empty on a
  fresh runner."
- `package.json:41`: `"smoke": "tsx scripts/smoke.ts"`, the script verify's `pnpm smoke` stage runs
  (`package.json:13`).
- `CLAUDE.md` ("Run and test"): "`pnpm smoke` opens every rail entry against the real service and
  needs a build". The workflow's header is the record of what a runner lacks and how each gap is
  filled, so a name in it is a claim about the tree.

**Command** (from the repository root): `bash bughunt/repro/H13-06/run.sh`

A static check: it reads commit `2047f5a`'s own objects (`git show`, `git ls-tree`, `git grep`, `git
log`) and the checkout's files, which match the commit byte for byte for these paths. It needs no
database, service or worktree, makes no network call and spends nothing; its one scratch folder under
the scratchpad's `bh/work/H13-06/` is removed at exit. It prints the comment's line, every file named
`smoke.*` in the commit's tree, what `package.json` runs for `smoke`, every `CHROMIUM_PATH` read under
`scripts/`, and the commits that deleted `smoke.mjs`, added `smoke.ts` and wrote the comment.

**Expected.** The comment names `scripts/smoke.ts` (and, since the proof's walk launches Chromium the
same way, `scripts/walk.ts`), the scripts that read `CHROMIUM_PATH` in this tree.

**Observed** (both runs, `run1.log` and `run2.log`, `RESULT: DEFECT`, byte for byte the same):
- `2047f5a:.github/workflows/verify.yml:15`: `#     one first (smoke.mjs also honours CHROMIUM_PATH)
  and fall back to Playwright's`.
- Files named `smoke.*` in the commit's tree: `scripts/smoke.ts` alone; `ls scripts/smoke.*` in the
  checkout lists `scripts/smoke.ts` alone.
- `2047f5a:package.json:41`: `"smoke": "tsx scripts/smoke.ts",`.
- `2047f5a:scripts/smoke.ts:167` and `2047f5a:scripts/walk.ts:170`:
  `const executablePath = process.env.CHROMIUM_PATH ?? '/opt/pw-browsers/chromium';`.
- History: the comment came in `22a4eea` (OF-BLD-012 §8), when `scripts/smoke.mjs` existed and read
  `CHROMIUM_PATH` (its line 242 at `20bd36d^`); `20bd36d` (alpha2 1.1) deleted `smoke.mjs` with the
  demo infrastructure, and `d4c7ea6` (alpha2 1.6) added `scripts/smoke.ts`. The comment kept the old
  name through both.
- No other line outside `docs/history/` and `bughunt/` names `smoke.mjs`.

The behaviour the comment describes holds: both browser scripts try `CHROMIUM_PATH`, then
`/opt/pw-browsers/chromium`, then Playwright's own cache. The defect is the file name alone, so a
reader who follows the comment finds no such file.

**Likely cause** (confidence high). `.github/workflows/verify.yml:15` was written for alpha 1.0's
`scripts/smoke.mjs` and stayed as it was when stage 1 of alpha 2.0 replaced that script with
`scripts/smoke.ts`. The fix is one line: name `scripts/smoke.ts` and `scripts/walk.ts` there.

**Severity.** S4 (drift in a comment).
