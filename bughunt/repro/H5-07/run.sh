#!/usr/bin/env bash
# H5-07: Guild's and Practice's refusal for a skill the project's skill catalogue lacks says
# "'X' is not a skill Guild holds (none ship with alpha 2.0)", while Guild's skills come from the
# project's skill catalogue, kept on /catalogues.
#   bash bughunt/repro/H5-07/run.sh        (from the repository root; exits 0 either way)
# A fresh test database bh_r_h5_07_skillwords, a keyless service on the first free port of
# 127.0.0.1:9800-9809 from core/ as at 2047f5a, one project bh-a keeping one skill SK-A, then the
# refusals asked naming SK-NONE (probe.py), and the words found in the tree (grep). The service is
# stopped, the database dropped, its data copy removed. Nothing is mutated, so no worktree is made.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1
HERE=/home/user/openFermentUI/bughunt/repro/H5-07
DB=bh_r_h5_07_skillwords
PORT=
for p in $(seq 9800 9809); do [ -z "$(bh_port_pid "$p")" ] && { PORT=$p; break; }; done
[ -n "$PORT" ] || { echo "EXPECTED: a free port in 9800-9809"; echo "OBSERVED: none free"; echo "RESULT: NO-DEFECT"; exit 0; }
cleanup() {
  bh_svc_stop "$PORT"
  PGOPTIONS='-c client_min_messages=warning' bh_db_drop "$DB"
  rm -rf "$BH_WORK/data-$DB"
}
trap cleanup EXIT
rm -rf "$BH_WORK/data-$DB"
ORIGIN=$(PGOPTIONS='-c client_min_messages=warning' bh_svc_start "$DB" "$PORT") \
  || { echo "EXPECTED: a service to test"; echo "OBSERVED: the service did not start"; echo "RESULT: NO-DEFECT"; exit 0; }
echo "service: $ORIGIN over a fresh $DB (keyless)"
echo "commit: $(git -C "$BH_ROOT" rev-parse --short HEAD); core/ src/ docs/ as at 2047f5a: $(git -C "$BH_ROOT" diff --quiet 2047f5a -- core src docs && echo yes || echo no)"
echo
OUT=$(bh_env ORIGIN="$ORIGIN" "$BH_ROOT/core/.venv/bin/python" -I "$HERE/probe.py" 2>&1) \
  || OUT="$OUT
OBSERVED: probe.py failed
RESULT: NO-DEFECT"
echo "$OUT" | grep -v -E '^(EXPECTED|OBSERVED|RESULT):'
echo
echo "the words in the tree at 2047f5a (grep -rn 'none ship with alpha 2.0'):"
HITS=$(cd "$BH_ROOT" && grep -rn --exclude-dir=__pycache__ "none ship with alpha 2.0" core/openferment_core src docs/api 2>/dev/null)
echo "$HITS" | sed 's/^/  /' | cut -c1-220
echo "the protocol keep's words for the same fact (protocols.py):"
grep -n -A3 "which the project's skill catalogue" "$BH_ROOT/core/openferment_core/protocols.py" | sed 's/^/  /'
if grep -qi "api.anthropic.com" "$BH_WORK/svc-$PORT.log" 2>/dev/null; then echo "note: the service log names api.anthropic.com"; fi
echo
echo "$OUT" | grep -E '^(EXPECTED|OBSERVED):'
echo "the tree: $(echo "$HITS" | grep -c . ) lines carry 'none ship with alpha 2.0' (guild.py, practice.py, models.py, and the generated openapi.json and types.gen.ts)"
echo "$OUT" | grep -E '^RESULT: ' | tail -1 || echo "RESULT: NO-DEFECT (the probe did not complete)"
exit 0
