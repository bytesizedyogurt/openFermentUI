#!/bin/bash
# placeholder-key-doors.sh LIB OUT: "does core/.env hold a key?" asked of four doors, over the core/.env
# the runbook's step 1 makes (core/.env.example with its database line taken out, the example's
# placeholder `ANTHROPIC_API_KEY=sk-ant-...` still on its key line), and over files of two key lines.
#   1. lib.sh's has_key (install.sh prints its answer)
#   2. ready.check_key (pnpm ready's key row), after load_dotenv as ready.run reads the file
#   3. checks.main's test before `brief --missing` drafts briefs (os.environ.get after load_dotenv)
#   4. GET /api/health's hasKey (the Postdoc screen shows its no-key warning on hasKey false), from a
#      service started over a test database with the file's key in its environment, as the service
#      reads core/.env; ANTHROPIC_BASE_URL points at a closed loopback port so no call leaves the machine.
# The placeholder is the example's own text; no key is read or written anywhere.
set -uo pipefail
source /home/user/openFermentUI/bughunt/lib/env.sh
LIB="$1"; OUT="$2"
rm -rf "$OUT"; mkdir -p "$OUT/core" "$OUT/home"
PY=/home/user/openFermentUI/core/.venv/bin/python
ask() { # ask FILE-CONTENT LABEL
  printf '%s' "$1" > "$OUT/core/.env"
  local a b c
  a=$(env -i PATH=/usr/bin:/bin HOME="$OUT/home" OPENFERMENT_LAUNCHD_DIR="$OUT/none" bash -c \
      'source "$1"; REPO="$2"; has_key && echo "key" || echo "no key"' _ "$LIB" "$OUT")
  read -r b c < <(cd /home/user/openFermentUI/core && env -u ANTHROPIC_API_KEY -u OPENFERMENT_API_KEY "$PY" -I -c '
import os, sys
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv(sys.argv[1], override=False)
from openferment_core.ready import check_key
k = check_key()
print(("key" if k.mark in ("ok", "warn") else "no-key") + "(" + k.mark + ")",
      "drafts-briefs" if os.environ.get("ANTHROPIC_API_KEY") else "waits")' "$OUT/core/.env" 2>/dev/null)
  printf '%-34s has_key=%-7s ready=%-12s checks-brief=%s\n' "$2" "$a" "$b" "$c"
}
step1="$(sed '/^OPENFERMENT_DATABASE_URL=/d' /home/user/openFermentUI/core/.env.example)"
ask "$step1"$'\n' "runbook step 1's core/.env"
ask $'ANTHROPIC_API_KEY=sk-ant-...\nANTHROPIC_API_KEY=sk-ant-H11-NOT-A-KEY\n' "placeholder line, then a key line"
ask $'ANTHROPIC_API_KEY=sk-ant-H11-NOT-A-KEY\nANTHROPIC_API_KEY=\n' "a key line, then an empty one"

# Door 4: the service over a test database, its environment holding what dotenv reads from step 1's file.
bh_db_fresh bh_h11_health || exit 1
data=$(bh_data bh_h11_health)
key="$(printf '%s\n' "$step1" | sed -n 's/^ANTHROPIC_API_KEY=//p')"
(
  cd /home/user/openFermentUI/core || exit 1
  env -u OPENFERMENT_MODEL -u OPENFERMENT_FALLBACK_MODEL -u OPENFERMENT_INDEX_MODEL -u OPENFERMENT_EFFORT \
    -u OPENFERMENT_API_KEY ANTHROPIC_API_KEY="$key" ANTHROPIC_BASE_URL=http://127.0.0.1:8919 \
    OPENFERMENT_DATABASE_URL="$BH_SERVER/bh_h11_health" OPENFERMENT_DATA_DIR="$data" \
    OPENFERMENT_SFF_LIBRARY="$data/sff-library" OPENFERMENT_DIST_DIR=/home/user/openFermentUI/dist \
    setsid .venv/bin/python -m uvicorn openferment_core.api:app --host 127.0.0.1 --port 8912 --log-level warning \
    < /dev/null > "$BH_WORK/svc-8912.log" 2>&1 &
)
for _ in $(seq 1 240); do curl -sf --noproxy '*' http://127.0.0.1:8912/api/health > "$OUT/health.json" 2>/dev/null && break; sleep 0.5; done
printf '%-34s /api/health hasKey=%s\n' "runbook step 1's core/.env" \
  "$("$PY" -I -c 'import json,sys; print(json.load(open(sys.argv[1]))["hasKey"])' "$OUT/health.json")"
bh_svc_stop 8912; bh_db_drop bh_h11_health
