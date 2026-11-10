#!/usr/bin/env bash
# H13-06: the CI workflow's header comment says "smoke.mjs also honours CHROMIUM_PATH"; the tree at
# 2047f5a holds no smoke.mjs, and the smoke `pnpm smoke` runs is scripts/smoke.ts, which reads CHROMIUM_PATH.
# A static defect, shown mechanically from the commit's own objects (git show, git ls-tree, git grep) and
# from the checkout's files: no database, no service, no worktree, no key, no network. Nothing is written
# outside a scratch directory this script removes.
# usage, from the repository root: bash bughunt/repro/H13-06/run.sh
source /home/user/openFermentUI/bughunt/lib/env.sh
C=2047f5a
T="$BH_WORK/H13-06/run"
TOP="$BH_WORK/H13-06"
cleanup() { rm -rf "${TOP:?}"; }
trap cleanup EXIT
rm -rf "${T:?}"; mkdir -p "$T"
g() { git -C "$BH_ROOT" "$@"; }

echo "EXPECTED: the comment in .github/workflows/verify.yml that says which browser script honours CHROMIUM_PATH"
echo "EXPECTED: names a script the tree holds: scripts/smoke.ts, the script package.json's \"smoke\" runs"
echo "EXPECTED: (\"smoke\": \"tsx scripts/smoke.ts\"), which reads CHROMIUM_PATH (scripts/walk.ts reads it too)."

# 1. The comment, at the commit and in the checkout.
g show "$C:.github/workflows/verify.yml" > "$T/verify.yml" 2>/dev/null \
  || { echo "OBSERVED: $C holds no .github/workflows/verify.yml"; echo "RESULT: NO-DEFECT"; exit 0; }
grep -n 'smoke\.mjs' "$T/verify.yml" > "$T/comment.txt"
names_mjs=$(wc -l < "$T/comment.txt")
cmp -s "$T/verify.yml" "$BH_ROOT/.github/workflows/verify.yml" && same_wf=1 || same_wf=0

# 2. Every file named smoke.* in the commit's tree, and any smoke.mjs anywhere in it.
g ls-tree -r --name-only "$C" | grep -E '(^|/)smoke\.[^/]*$' > "$T/smoke-files.txt"
mjs_files=$(grep -c 'smoke\.mjs$' "$T/smoke-files.txt")
ts_held=$(grep -cx 'scripts/smoke.ts' "$T/smoke-files.txt")
ls_checkout=$(cd "$BH_ROOT" && ls -1 scripts/smoke.* 2>&1 | tr '\n' ' ')

# 3. What `pnpm smoke` runs, and which scripts read CHROMIUM_PATH.
smoke_cmd=$(g show "$C:package.json" | grep -n '"smoke":' | sed 's/^ *//; s/  */ /g')
g grep -n 'CHROMIUM_PATH' "$C" -- scripts > "$T/chromium.txt"
ts_reads=$(grep -c "^$C:scripts/smoke.ts:" "$T/chromium.txt")

# 4. Where smoke.mjs went: the commit that deleted it, and the commit that added smoke.ts.
gone=$(g log --format='%h %s' --diff-filter=D -1 "$C" -- scripts/smoke.mjs | cut -c1-110)
came=$(g log --format='%h %s' --diff-filter=A -1 "$C" -- scripts/smoke.ts | cut -c1-110)
said=$(g log --format='%h %s' -S'smoke.mjs also honours' -1 "$C" -- .github/workflows/verify.yml | cut -c1-110)
others=$(g grep -n 'smoke\.mjs' "$C" -- . ':!docs/history' ':!bughunt' | grep -vc '^2047f5a:.github/workflows/verify.yml:')

sed "s/^/OBSERVED: $C:.github\/workflows\/verify.yml:/" "$T/comment.txt"
echo "OBSERVED: the checkout's verify.yml is byte for byte the commit's: $([ $same_wf = 1 ] && echo yes || echo no)"
echo "OBSERVED: files named smoke.* in $C's tree: $(tr '\n' ' ' < "$T/smoke-files.txt")(smoke.mjs: $mjs_files)"
echo "OBSERVED: \`ls scripts/smoke.*\` in the checkout: $ls_checkout"
echo "OBSERVED: $C:package.json:$smoke_cmd"
sed 's/^/OBSERVED: /; s/  */ /g' "$T/chromium.txt"
echo "OBSERVED: scripts/smoke.mjs deleted in $gone"
echo "OBSERVED: scripts/smoke.ts added in $came"
echo "OBSERVED: the comment written in $said"
echo "OBSERVED: other lines naming smoke.mjs outside docs/history/ and bughunt/: $others"

if [ "$names_mjs" -ge 1 ] && [ "$mjs_files" = 0 ] && [ "$ts_held" = 1 ] && [ "$ts_reads" -ge 1 ]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
