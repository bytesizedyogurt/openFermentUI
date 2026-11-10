#!/usr/bin/env bash
# H5-06: a request that names no project is answered as a project with an empty catalogue (protparam,
# pureOS propose, Guild check and evidence) and the tool door answers 200 with the exception's class,
# where the contract is a 422 in words naming X-OpenFerment-Project.
#   bash bughunt/repro/H5-06/run.sh        (from the repository root; exits 0 either way)
# A fresh test database bh_r_h5_06_noproj, a keyless service on the first free port of 127.0.0.1:9120-9129
# from core/ as at 2047f5a, one project bh-a holding a product, a strain and a skill, then each route asked
# naming bh-a and naming none. The service is stopped, the database dropped, its data copy removed.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1
HERE=/home/user/openFermentUI/bughunt/repro/H5-06
DB=bh_r_h5_06_noproj
PORT=
for p in $(seq 9120 9129); do [ -z "$(bh_port_pid "$p")" ] && { PORT=$p; break; }; done
[ -n "$PORT" ] || { echo "EXPECTED: a free port in 9120-9129"; echo "OBSERVED: none free"; echo "RESULT: NO-DEFECT"; exit 0; }
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
echo "commit: $(git -C "$BH_ROOT" rev-parse --short HEAD); core/ as at 2047f5a: $(git -C "$BH_ROOT" diff --quiet 2047f5a -- core && echo yes || echo no)"
OUT=$(bh_env ORIGIN="$ORIGIN" "$BH_ROOT/core/.venv/bin/python" -I "$HERE/probe.py" 2>&1) \
  || OUT="$OUT
OBSERVED: probe.py failed
RESULT: NO-DEFECT"
echo "$OUT" | grep -v -E '^(EXPECTED|OBSERVED|RESULT):'
echo
echo "where the empty answers come from (core/openferment_core at 2047f5a):"
grep -n -A1 "except projects.ProjectRequired:" "$BH_ROOT/core/openferment_core/catalogues.py" "$BH_ROOT/core/openferment_core/protocols.py" | sed 's/^/  /'
grep -n 'failed: {type(e).__name__}: {e}' "$BH_ROOT/core/openferment_core/tools/__init__.py" | sed 's/^/  /'
grep -n "the project holds no readable document" "$BH_ROOT/core/openferment_core/tools/literature.py" | sed 's/^/  /'
if grep -qi "api.anthropic.com" "$BH_WORK/svc-$PORT.log" 2>/dev/null; then echo "note: the service log names api.anthropic.com"; fi
echo
echo "$OUT" | grep -E '^(EXPECTED|OBSERVED):'
echo "$OUT" | grep -E '^RESULT: ' | tail -1 || echo "RESULT: NO-DEFECT (the probe did not complete)"
exit 0
