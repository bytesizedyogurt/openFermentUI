#!/usr/bin/env bash
# H11-01: over the core/.env that the live-host runbook's step 1 makes (core/.env.example with its database
# line taken out, so the example's placeholder line `ANTHROPIC_API_KEY=sk-ant-...` still stands), install.sh's
# has_key and `pnpm ready` read it as no key; GET /api/health reads it as a key (hasKey true), and so does the
# nightly's `checks brief --missing`, which takes the branch that drafts briefs.
# usage, from the repository root: bash bughunt/repro/H11-01/run.sh
#
# Everything runs in a detached worktree of 2047f5a under $BH_WORK/H11-01/wt, whose own core/.env is the file
# step 1 makes; the repository's own core/ is never read for .env and never written. The repository's
# core/.venv runs the worktree's code (its cwd comes first on sys.path). Keyless: the only key value is the
# example's placeholder, ANTHROPIC_API_KEY is unset in the environment so each door reads the file as the live
# host would, and ANTHROPIC_BASE_URL and every proxy variable name closed loopback ports, so no request can
# leave the machine. Ports 10260 (service), 10268 and 10269 (closed). Database bh_r_h11_01_svc, made fresh.
source /home/user/openFermentUI/bughunt/lib/env.sh
DB=bh_r_h11_01_svc
PORT=10260
T=$BH_WORK/H11-01; WT=$T/wt; OUT=$T/out
PY=$BH_ROOT/core/.venv/bin/python

cleanup() {
  bh_svc_stop "$PORT"
  bh_db_drop "$DB" 2>/dev/null
  rm -rf "$BH_WORK/data-$DB" "$OUT"
  git -C "$BH_ROOT" worktree remove --force "$WT" >/dev/null 2>&1
  rmdir "$T" 2>/dev/null
}
trap cleanup EXIT
cleanup; mkdir -p "$OUT/home"

# The environment each door runs in: the session's model pins and keys unset, ANTHROPIC_API_KEY unset so
# load_dotenv(override=False) takes the file's line, every outbound route pointed at a closed loopback port.
door_env() {
  env -u OPENFERMENT_MODEL -u OPENFERMENT_FALLBACK_MODEL -u OPENFERMENT_INDEX_MODEL -u OPENFERMENT_EFFORT \
      -u OPENFERMENT_API_KEY -u OPENFERMENT_DATA_DIR -u ANTHROPIC_API_KEY \
      -u https_proxy -u http_proxy -u all_proxy -u no_proxy \
      ANTHROPIC_BASE_URL=http://127.0.0.1:10269 HTTPS_PROXY=http://127.0.0.1:10268 HTTP_PROXY=http://127.0.0.1:10268 \
      ALL_PROXY=http://127.0.0.1:10268 NO_PROXY=127.0.0.1,localhost \
      OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" "$@"
}

echo "EXPECTED: over runbook step 1's core/.env (the example's placeholder on its key line) every door reads 'no key':"
echo "EXPECTED:   install.sh's has_key false (it prints 'core/.env holds no key yet. The app runs; Postdoc and extraction"
echo "EXPECTED:   wait for one.'), pnpm ready's key row fail, the nightly's 'checks brief --missing' prints that the checks"
echo "EXPECTED:   wait (nightly.sh:50-51), and GET /api/health hasKey false, so the Postdoc screen shows its no-key callout"
echo "EXPECTED:   (api.py:471-472: hasKey tells 'the service is down' from 'the service is up but has no key')."

git -C "$BH_ROOT" worktree add --detach "$WT" 2047f5a >/dev/null 2>&1 || { echo "OBSERVED: could not add the worktree"; echo "RESULT: NO-DEFECT"; exit 0; }
bh_db_fresh "$DB" 2>/dev/null || { echo "OBSERVED: could not make $DB"; echo "RESULT: NO-DEFECT"; exit 0; }
DATA=$(bh_data "$DB")
where=$(cd "$WT/core" && door_env "$PY" -c 'import openferment_core.api as a, openferment_core.checks as c; print(a.__file__, c.ENV_FILE)' 2>/dev/null)
echo "setup: the doors' code and the file they read: $where"

# Runbook step 1, verbatim (docs/runbooks/live-host-install.md:81-84), in the worktree's core/.
(cd "$WT/core" && { [ -e .env ] || (umask 077 && sed '/^OPENFERMENT_DATABASE_URL=/d' .env.example > .env); chmod 600 .env; })
echo "setup: step 1's core/.env key line: $(grep -n '^ANTHROPIC_API_KEY' "$WT/core/.env")"

start_service() {
  (
    cd "$WT/core" || exit 1
    door_env OPENFERMENT_DATA_DIR="$DATA" OPENFERMENT_SFF_LIBRARY="$DATA/sff-library" OPENFERMENT_DIST_DIR="$BH_ROOT/dist" \
      OPENFERMENT_POLL_HOST=127.0.0.1 OPENFERMENT_PORT="$PORT" \
      setsid "$PY" -m uvicorn openferment_core.api:app --app-dir . --host 127.0.0.1 --port "$PORT" \
      --log-level warning < /dev/null > "$BH_WORK/svc-$PORT.log" 2>&1 &
  )
  local i; for i in $(seq 1 240); do
    curl -sf --noproxy '*' "http://127.0.0.1:$PORT/api/health" > "$OUT/health.json" 2>/dev/null && return 0
    sleep 0.5
  done
  return 1
}

# The four doors over the worktree's core/.env as it stands. Prints one row and sets $verdict.
doors() {
  local label="$1" a b c d bout bst
  a=$(env -i PATH=/usr/bin:/bin HOME="$OUT/home" OPENFERMENT_LAUNCHD_DIR="$OUT/none" bash -c \
      'source "$1"; has_key && echo key || echo no-key' _ "$WT/scripts/host/lib.sh")
  b=$(cd "$WT/core" && door_env "$PY" -m openferment_core.ready --no-network --no-workers 2>/dev/null | awk '$2=="key"{print; exit}' | cut -c1-80)
  case "$b" in "✗"*) b="no-key ($b)";; "✓"*|"!"*) b="key ($b)";; *) b="unread ($b)";; esac
  bout=$(cd "$WT/core" && door_env "$PY" -m openferment_core.checks brief --missing 2>&1); bst=$?
  if grep -q 'so they wait' <<<"$bout"; then c="waits"; else c="drafts-briefs"; fi
  c="$c (exit $bst; output: ${bout:-<none>})"
  if start_service; then
    d=$("$PY" -I -c 'import json,sys; h=json.load(open(sys.argv[1])); print("hasKey=%s" % h["hasKey"])' "$OUT/health.json")
  else
    d="no answer (see $BH_WORK/svc-$PORT.log)"
  fi
  bh_svc_stop "$PORT"
  echo "OBSERVED: [$label] has_key: $a"
  echo "OBSERVED: [$label] pnpm ready key row: $b"
  echo "OBSERVED: [$label] checks brief --missing: $c"
  echo "OBSERVED: [$label] GET /api/health: $d"
  verdict="$a|${b%% *}|${c%% *}|$d"
}

doors "runbook step 1's core/.env"
step1="$verdict"

# Control: the same file with the key line emptied, the form the example could have offered.
sed -i 's/^ANTHROPIC_API_KEY=.*/ANTHROPIC_API_KEY=/' "$WT/core/.env"
doors "control: key line emptied"
control="$verdict"

echo "OBSERVED: src/screens/Postdoc.tsx shows the no-key callout only on hasKey false: $(git -C "$BH_ROOT" show 2047f5a:src/screens/Postdoc.tsx | grep -n 'health.ok && !health.hasKey' | head -1 | sed 's/^ *//')"
echo "OBSERVED: summary (has_key|ready|brief|health): step 1 = $step1; control = $control"

if [ "$step1" = "no-key|no-key|drafts-briefs|hasKey=True" ] && [ "$control" = "no-key|no-key|waits|hasKey=False" ]; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
