#!/usr/bin/env bash
# offline.sh <files...>: H12's selection in its second worktree under Python 3.13 inside a network namespace of
# its own (loopback alone), the database reached through relay.py (a unix socket out to the host's PostgreSQL):
# test:core's "offline, no network" held to the letter. Databases are named bh_h12_off_*.
source /home/user/openFermentUI/bughunt/lib/env.sh
WT2=${WT2:-$BH_WORK/H12/wt2}; S=/home/user/openFermentUI/bughunt/notes/H12/scripts
SOCK=$BH_WORK/H12/pg-relay.sock; rm -f "$SOCK"
python3 $S/relay.py out "$SOCK" & OUT=$!
trap 'kill $OUT 2>/dev/null; rm -f "$SOCK"' EXIT
for i in $(seq 1 50); do [ -S "$SOCK" ] && break; sleep 0.1; done
cd "$WT2/core" || exit 2
unshare -n sh -c 'python3 "$0"/lo_up.py && python3 "$0"/relay.py in "$1" >/dev/null 2>&1 & sleep 0.5; shift 1; exec "$@"' $S "$SOCK" \
  env -u OPENFERMENT_MODEL -u OPENFERMENT_FALLBACK_MODEL -u OPENFERMENT_INDEX_MODEL -u OPENFERMENT_EFFORT \
      -u OPENFERMENT_API_KEY -u OPENFERMENT_DATABASE_URL ANTHROPIC_API_KEY= PYTHONPATH="$WT2/core" \
      OPENFERMENT_TEST_DATABASE_URL="$BH_SERVER/bh_h12_off" \
  /home/user/openFermentUI/core/.venv/bin/python -m pytest "$@" -q -p no:randomly -p no:cacheprovider -rA \
  -m "not live and not sim and not slow and not lit" -k "not sigterm_ends_the_command"
