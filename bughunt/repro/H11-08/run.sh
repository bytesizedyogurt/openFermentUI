#!/bin/bash
# H11-08: has_key (scripts/host/lib.sh) answers for any ANTHROPIC_API_KEY line in core/.env, while
# python-dotenv, which the service (api.py) and pnpm ready (ready.run) read the file with, keeps the last one.
# Three core/.env files are asked of three doors, each file written into a scratch worktree of 2047f5a:
#   A  one key line (the control)
#   B  the example's placeholder line, then a key line
#   C  a key line, then an empty one
# Doors: install.sh's own has_key block (from the worktree's install.sh, over the worktree's lib.sh);
# pnpm ready's key row (python -m openferment_core.ready --no-network --no-workers, from the worktree's core/);
# GET /api/health's hasKey from the service started in the worktree's core/ over a fresh test database.
# The key-shaped strings are made up (sk-ant-H11-08-NOT-A-KEY); ANTHROPIC_BASE_URL points at a closed
# loopback port, so no call can leave the machine. Run from the repository root:
#   bash bughunt/repro/H11-08/run.sh
set -uo pipefail
source /home/user/openFermentUI/bughunt/lib/env.sh
D="$BH_WORK/H11-08"; WT="$D/wt"; OUT="$D/out"; PORT=10070; DB=bh_r_h11_08_svc
PY="$BH_ROOT/core/.venv/bin/python"
cleanup() {
  bh_svc_stop "$PORT"; bh_db_drop "$DB"; rm -rf "$BH_WORK/data-$DB" "$OUT"
  git -C "$BH_ROOT" worktree remove --force "$WT" >/dev/null 2>&1; git -C "$BH_ROOT" worktree prune
}
trap cleanup EXIT
git -C "$BH_ROOT" worktree remove --force "$WT" >/dev/null 2>&1; rm -rf "$WT"; mkdir -p "$D" "$OUT/home"
git -C "$BH_ROOT" worktree add --detach "$WT" 2047f5a >/dev/null 2>&1 || { echo "could not add the worktree"; echo "RESULT: NO-DEFECT"; exit 0; }
bh_db_fresh "$DB" 2>/dev/null || { echo "could not make $DB"; echo "RESULT: NO-DEFECT"; exit 0; }
data=$(bh_data "$DB")

# What the service and ready see: keyless shell, ANTHROPIC_API_KEY unset so core/.env's line is the one read.
py_env() {
  env -u OPENFERMENT_MODEL -u OPENFERMENT_FALLBACK_MODEL -u OPENFERMENT_INDEX_MODEL -u OPENFERMENT_EFFORT \
      -u OPENFERMENT_API_KEY -u ANTHROPIC_API_KEY -u OPENFERMENT_DATA_DIR \
      ANTHROPIC_BASE_URL=http://127.0.0.1:10079 OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" \
      OPENFERMENT_DATA_DIR="$data" OPENFERMENT_SFF_LIBRARY="$data/sff-library" OPENFERMENT_DIST_DIR="$BH_ROOT/dist" \
      OPENFERMENT_PORT="$PORT" OPENFERMENT_POLL_HOST=127.0.0.1 "$@"
}
echo "worktree $WT at $(git -C "$WT" rev-parse --short HEAD); the Python doors import $(cd "$WT/core" && py_env "$PY" -c 'import openferment_core.ready as r; print(r.__file__)')"

# install.sh's block, lines 51 to 56, run as written over the worktree's lib.sh (REPO is the worktree).
block="$(sed -n '/^if has_key; then$/,/^fi$/p' "$WT/scripts/host/install.sh")"
install_door() {
  env -i PATH=/usr/bin:/bin HOME="$OUT/home" OPENFERMENT_LAUNCHD_DIR="$OUT/none" bash -c \
    'source "$1"; has_key && echo -n "key: " || echo -n "no key: "; eval "$2" | head -1' _ "$WT/scripts/host/lib.sh" "$block"
}
ready_door() { (cd "$WT/core" && py_env "$PY" -m openferment_core.ready --no-network --no-workers 2>&1 | grep -E '^[^ ]+ key ' | sed 's/  */ /g'); }
service_door() {
  (cd "$WT/core" && py_env setsid "$PY" -m uvicorn openferment_core.api:app --host 127.0.0.1 --port "$PORT" \
      --log-level warning < /dev/null > "$OUT/svc.log" 2>&1 &)
  local i; for i in $(seq 1 240); do
    curl -sf --noproxy '*' "http://127.0.0.1:$PORT/api/health" > "$OUT/health.json" 2>/dev/null && break; sleep 0.5
  done
  "$PY" -I -c 'import json,sys; print("hasKey", json.load(open(sys.argv[1])).get("hasKey"))' "$OUT/health.json" 2>/dev/null || echo "no answer"
  bh_svc_stop "$PORT"; rm -f "$OUT/health.json"
}
verdict() { # install-line ready-line service-line -> "agree" or "disagree"
  local i r s; case "$1" in key:*) i=1;; *) i=0;; esac
  case "$2" in "✓ key"*|"! key"*) r=1;; *) r=0;; esac
  case "$3" in "hasKey True") s=1;; *) s=0;; esac
  [ "$i" = "$r" ] && [ "$r" = "$s" ] && echo agree || echo disagree
}

declare -A V S
for c in A B C; do
  case $c in
    A) content=$'ANTHROPIC_API_KEY=sk-ant-H11-08-NOT-A-KEY\n'; label="A one key line (control)";;
    B) content=$'ANTHROPIC_API_KEY=sk-ant-...\nANTHROPIC_API_KEY=sk-ant-H11-08-NOT-A-KEY\n'; label="B placeholder line, then a key line";;
    C) content=$'ANTHROPIC_API_KEY=sk-ant-H11-08-NOT-A-KEY\nANTHROPIC_API_KEY=\n'; label="C a key line, then an empty one";;
  esac
  printf '%s' "$content" > "$WT/core/.env"; chmod 600 "$WT/core/.env"
  i=$(install_door); r=$(ready_door); s=$(service_door)
  V[$c]=$(verdict "$i" "$r" "$s")
  S[$c]="has_key ${i%%:*}, ready ${r%% core*}, service $s"
  echo "--- $label"
  printf '%s' "$content" | sed 's/^/    core\/.env | /'
  echo "    install.sh (has_key): $i"
  echo "    pnpm ready key row:   $r"
  echo "    service /api/health:  $s"
  echo "    doors: ${V[$c]}"
done

echo "EXPECTED: for each file the three doors give one answer: has_key (install.sh's message) says a key is held exactly when pnpm ready's key row and the service's hasKey do, since the service and ready read core/.env's last ANTHROPIC_API_KEY line."
echo "OBSERVED: A (control) ${V[A]} (${S[A]}); B (placeholder, then a key line) ${V[B]} (${S[B]}); C (a key line, then an empty one) ${V[C]} (${S[C]})."
if [ "${V[A]}" = agree ] && { [ "${V[B]}" = disagree ] || [ "${V[C]}" = disagree ]; }; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
