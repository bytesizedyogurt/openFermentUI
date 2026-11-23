#!/usr/bin/env bash
# H11-05: scripts/session-start.sh appends OPENFERMENT_DATABASE_URL (and OPENFERMENT_WORKSPACE_ID) to
# core/.env with printf '...\n' and no leading newline, so over a core/.env whose last line has no newline
# the setting joins that line: a key line saved without a final newline reads as the key with the setting
# stuck to its end, and the setting itself reads as unset.
# usage, from the repository root: bash bughunt/repro/H11-05/run.sh
#
# A detached worktree of 2047f5a under $BH_WORK/H11-05/wt runs its own scripts/session-start.sh over its own
# core/.env; the repository's own core/.env is never read and never written. Stand-ins answer for pnpm and uv
# (each records its call and exits 0, so no install, no migration and no `pnpm ready` runs); pg_isready is the
# real /usr/bin/pg_isready, which finds the test server on 127.0.0.1, and the run makes the fresh database
# bh_r_h11_05_pg there to confirm it answers. The key line holds the example's placeholder text `sk-ant-...`
# alone; no key is used and nothing reaches the network. The file is then read twice: by python-dotenv's
# dotenv_values, and by the service's own loader (load_dotenv(..., override=False) as api.py:178 calls it) in
# the worktree's code, followed by db.engine.database_url() and the key read llm.py:716 makes.
#   case A (control): the key line ends in a newline.
#   case B: the key line has no newline at its end.
#   case B2: session-start run a second time over case B's file.
#   case C: as B, with OPENFERMENT_WORKSPACE_ID set in the session.
# Everything (worktree, stand-ins, database) is removed at exit.
source /home/user/openFermentUI/bughunt/lib/env.sh
SHA=2047f5a; DB=bh_r_h11_05_pg
T="$BH_WORK/H11-05"; W="$T/wt"; OUT="$T/out"
PY="$BH_ROOT/core/.venv/bin/python"

cleanup() {
  bh_db_drop "$DB" 2>/dev/null
  git -C "$BH_ROOT" worktree remove --force "$W" >/dev/null 2>&1; git -C "$BH_ROOT" worktree prune
  rm -rf "$OUT"; rmdir "$T" 2>/dev/null
}
trap cleanup EXIT
cleanup; mkdir -p "$OUT/bin" "$OUT/home"
cd "$BH_ROOT" || exit 0

git -C "$BH_ROOT" worktree add --detach "$W" "$SHA" >/dev/null 2>&1 ||
  { echo "OBSERVED: no worktree"; echo "RESULT: NO-DEFECT"; exit 0; }
echo "worktree: $W at $(git -C "$W" rev-parse --short HEAD)"

echo; echo "== 1. the contract and the code, as $SHA holds them"
show() { local f="$1"; shift; for n in "$@"; do sed -n "${n}p" "$W/$f" | sed "s|^|   $f:$n: |"; done; }
show scripts/session-start.sh 6 7 18 19 20 44 45 46 47 48 62 63
show scripts/host/lib.sh 162 163
show core/tests/test_host.py 243 247 256 257
echo "   lines in core/tests naming session-start.sh: $(grep -rn 'session-start' "$W/core/tests" --include='*.py' | wc -l)"
grep -rn 'session-start' "$W/core/tests" --include='*.py' | sed "s|$W/||; s|  *| |g; s|^|   |"
echo "   core/.env.example's last byte: $(tail -c1 "$W/core/.env.example" | od -An -c | tr -d ' ')"

echo; echo "== 2. PostgreSQL on 127.0.0.1 (session-start's condition for the database line)"
bh_db_fresh "$DB" 2>/dev/null || { echo "OBSERVED: could not make $DB"; echo "RESULT: NO-DEFECT"; exit 0; }
/usr/bin/pg_isready -h 127.0.0.1 -d "$DB" | sed 's/^/   pg_isready: /'

# Stand-ins for pnpm and uv: each records its call and exits 0.
for t in pnpm uv; do
  printf '#!/bin/bash\nprintf "%%s\\n" "%s $*" >> "%s/calls"\nexit 0\n' "$t" "$OUT" > "$OUT/bin/$t"
  chmod 755 "$OUT/bin/$t"
done

# read_env LABEL: core/.env's bytes, dotenv_values, and the service's loader in the worktree's code.
read_env() {
  echo "   core/.env now holds (cat -A: \$ marks a line's end):"
  cat -A "$W/core/.env" | sed 's/^/   | /'
  (cd "$W/core" && env -i PATH=/usr/bin:/bin HOME="$OUT/home" OUT_FILE="$OUT/reads" "$PY" -c '
import os, sys
from dotenv import dotenv_values, load_dotenv
path, label = sys.argv[1], sys.argv[2]
v = dotenv_values(path)
print("   dotenv_values: ANTHROPIC_API_KEY =", repr(v.get("ANTHROPIC_API_KEY")),
      "| OPENFERMENT_DATABASE_URL =", repr(v.get("OPENFERMENT_DATABASE_URL")),
      "| OPENFERMENT_WORKSPACE_ID =", repr(v.get("OPENFERMENT_WORKSPACE_ID")))
load_dotenv(path, override=False)              # as api.py:178 loads core/.env
import importlib
engine = importlib.import_module("openferment_core.db.engine")
try:
    url = engine.database_url().render_as_string(hide_password=True)
except engine.DatabaseUnavailable as e:
    url = "DatabaseUnavailable: " + str(e).split(".")[0]
key = os.environ.get("ANTHROPIC_API_KEY")       # as llm.py:716 reads the key
where = os.path.relpath(engine.__file__, os.path.dirname(os.path.dirname(path)))
print("   the service loader (" + where + "): key =", repr(key), "| database_url() ->", url)
with open(os.environ["OUT_FILE"], "a") as f:
    f.write("\t".join([label, str(v.get("ANTHROPIC_API_KEY")), str(v.get("OPENFERMENT_DATABASE_URL")),
                       str(v.get("OPENFERMENT_WORKSPACE_ID")), str(os.environ.get("OPENFERMENT_DATABASE_URL"))]) + "\n")
' "$W/core/.env" "$1") 2>&1
}

# start LABEL [WORKSPACE]: session-start.sh in the worktree, as a session runs it, keyless.
start() {
  : > "$OUT/calls"
  (cd "$W" && env -i PATH="$OUT/bin:/usr/bin:/bin" HOME="$OUT/home" ${2:+OPENFERMENT_WORKSPACE_ID=$2} \
     bash scripts/session-start.sh) > "$OUT/start-$1.log" 2>&1
  echo "   session-start exit $?; its lines naming core/.env:"
  grep -E 'core/.env' "$OUT/start-$1.log" | sed 's/^/   > /'
  echo "   stand-in calls: $(tr '\n' ';' < "$OUT/calls")"
}

: > "$OUT/reads"
echo; echo "== 3. case A (control): '# hand-written\\nANTHROPIC_API_KEY=sk-ant-...\\n', the key line ending in a newline"
printf '# hand-written\nANTHROPIC_API_KEY=sk-ant-...\n' > "$W/core/.env"; chmod 600 "$W/core/.env"
start A; read_env A

echo; echo "== 4. case B: '# hand-written\\nANTHROPIC_API_KEY=sk-ant-...', no newline at the key line's end"
printf '# hand-written\nANTHROPIC_API_KEY=sk-ant-...' > "$W/core/.env"; chmod 600 "$W/core/.env"
start B; read_env B

echo; echo "== 5. case B2: session-start run again over case B's file (the script calls itself idempotent)"
start B2; read_env B2

echo; echo "== 6. case C: as case B, with OPENFERMENT_WORKSPACE_ID=wrkspc_h11_placeholder in the session"
printf '# hand-written\nANTHROPIC_API_KEY=sk-ant-...' > "$W/core/.env"; chmod 600 "$W/core/.env"
start C wrkspc_h11_placeholder; read_env C
rm -f "$W/core/.env"

field() { awk -F'\t' -v l="$1" -v c="$2" '$1 == l { print $c }' "$OUT/reads"; }
DEV=postgresql://openferment:openferment@127.0.0.1:5432/openferment_dev
echo
echo "EXPECTED: in every case the setting session-start adds lands on a line of its own (lib.sh:162 \"On a line of its own, whether or not the file's last line ends in one\"): the key reads as 'sk-ant-...', the database as the development address, and in case C the workspace as 'wrkspc_h11_placeholder' (session-start.sh:45-46 \"it joins core/.env when the file lacks it, so a service started from the file sends it too\")."
echo "OBSERVED: case A (control): key '$(field A 2)', database '$(field A 3)'. Case B: key '$(field B 2)', database '$(field B 3)', the service loader's database '$(field B 5)'. Case B2 (second run): key '$(field B2 2)', database '$(field B2 3)'. Case C: key '$(field C 2)', workspace '$(field C 4)', database '$(field C 3)'."
if [ "$(field A 2)" = "sk-ant-..." ] && [ "$(field A 3)" = "$DEV" ] &&
   [ "$(field B 2)" = "sk-ant-...OPENFERMENT_DATABASE_URL=$DEV" ] && [ "$(field B 3)" = None ] && [ "$(field B 5)" = None ]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
