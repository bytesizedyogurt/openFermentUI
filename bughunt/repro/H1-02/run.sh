#!/usr/bin/env bash
# H1-02: an entry module that imports cobra and is then set aside for another reason (its object misnamed,
# or an import that raises) leaves cobra in the service's process, and a later entry module that imports
# cobra loads with no word said.
# Each scenario is the service's startup in one process (probe.py imports openferment_core.api, which runs
# discovery, api.py:196) over the head's own venv, read only: the stand-in modules in standin/ and a
# dist-info made here in scratch reach the entry-point group through PYTHONPATH, so nothing is installed,
# patched or built. Keyless, no model call, no service port, a fresh test database.
# usage, from the repository root: bash bughunt/repro/H1-02/run.sh
source /home/user/openFermentUI/bughunt/lib/env.sh
HERE=/home/user/openFermentUI/bughunt/repro/H1-02
DB=bh_r_h1_02_probe
T=$BH_WORK/H1-02/run-$$; mkdir -p "$T/data"
cleanup() { bh_db_drop "$DB"; rm -rf "$T"; rmdir "$BH_WORK/H1-02" 2>/dev/null; true; }
trap cleanup EXIT

# site KEY ENTRY...: a dist-info for the stand-in distribution registering the entry points named.
site() {
  local d="$T/site-$1/h1_02_standin-0.0.1.dist-info"; shift; mkdir -p "$d"
  printf 'Metadata-Version: 2.1\nName: h1-02-standin\nVersion: 0.0.1\n' > "$d/METADATA"
  { echo "[openferment.engines]"; for e in "$@"; do echo "$e"; done; } > "$d/entry_points.txt"
}
A='h1a-misnamed-heavy = h1_02_standin.misnamed_heavy:ENGINE'
B='h1b-fails-heavy = h1_02_standin.fails_heavy:ENGINE'
Z='h1z-heavy-unseen = h1_02_standin.heavy_unseen:ENGINE'
site alone "$Z"; site a "$A"; site az "$A" "$Z"; site bz "$B" "$Z"

bh_db_fresh "$DB" || { echo "OBSERVED: the test database could not be made"; echo "RESULT: NO-DEFECT"; exit 0; }
probe() {
  (cd "$BH_ROOT/core" && bh_env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$HERE/standin:$T/site-$1" \
     OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" OPENFERMENT_DATA_DIR="$T/data" \
     .venv/bin/python "$HERE/probe.py" 2>&1) | grep -v '^INFO' > "$T/$1.log"
  sed "s/^/  [$1] /" "$T/$1.log"
}

echo "EXPECTED: after discovery cobra stands outside the service's process in every scenario (CLAUDE.md:41, the"
echo "EXPECTED: service process imports none of them), and h1z-heavy-unseen, whose entry module imports cobra, is"
echo "EXPECTED: set aside with cobra named whatever was loaded before it (docs/api/engines.md:141-144)."
echo "-- alone: h1z-heavy-unseen alone (the control)"; probe alone
echo "-- a: h1a-misnamed-heavy alone (imports cobra, set aside for its object's name)"; probe a
echo "-- az: h1a-misnamed-heavy, then h1z-heavy-unseen"; probe az
echo "-- bz: h1b-fails-heavy (imports cobra, then raises ImportError), then h1z-heavy-unseen"; probe bz

z_of() { grep '^VERDICT h1z-heavy-unseen:' "$T/$1.log" | sed 's/^VERDICT h1z-heavy-unseen: //'; }
cobra_of() { grep '^COBRA_AFTER' "$T/$1.log" | awk '{print $2}'; }
ctl_ok=0
case "$(z_of alone)" in "set aside:"*cobra*) [ "$(cobra_of alone)" = False ] && ctl_ok=1;; esac
defect=0
for k in a az bz; do [ "$(cobra_of $k)" = True ] && defect=1; done
for k in az bz; do case "$(z_of $k)" in LOADED*) defect=1;; esac; done
a_words=$(grep '^VERDICT h1a-misnamed-heavy:' "$T/a.log" | sed 's/^VERDICT h1a-misnamed-heavy: set aside: //')
echo "OBSERVED: alone: h1z-heavy-unseen $(z_of alone | cut -c1-90); cobra in sys.modules after: $(cobra_of alone)"
echo "OBSERVED: a: cobra in sys.modules after discovery: $(cobra_of a); h1a's words: $a_words"
echo "OBSERVED: az: h1z-heavy-unseen $(z_of az | cut -c1-90); cobra in sys.modules after: $(cobra_of az)"
echo "OBSERVED: bz: h1z-heavy-unseen $(z_of bz | cut -c1-90); cobra in sys.modules after: $(cobra_of bz)"
if [ "$ctl_ok" != 1 ]; then
  echo "OBSERVED: the control did not set h1z-heavy-unseen aside with cobra named and taken out, so the probe proves nothing"
  echo "RESULT: NO-DEFECT"
elif [ "$defect" = 1 ]; then echo "RESULT: DEFECT"; else echo "RESULT: NO-DEFECT"; fi
exit 0
