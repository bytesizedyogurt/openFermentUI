#!/usr/bin/env bash
# H12-08: two rules of the per-request key override are held by no test.
#   M31  guard.key_refusal's Funnel rule (guard.py:100-101) dropped: test_key_override's one Funnel case is
#        POST /api/ask, which guard.refusal (guard.py:113-114) refuses first with a detail that also says "Funnel".
#   M28  llm.request_key's strip-and-empty rule (llm.py:699) dropped: its one caller, the API's middleware,
#        refuses a blank X-OpenFerment-Key (api.py:364-365) before it reaches request_key.
# In a worktree of 2047f5a of this run's own: a probe of each rule on the tree as it stands, then each rule dropped
# in turn, the probe again (the break is real) and the tests that hold the override and the guard
# (test_key_override.py, test_request_guard.py, test_llm.py). A green run under a real break is the defect. A control
# drops guard.refusal's Funnel rule, which test_request_guard holds, so a red run there shows the tests read the worktree.
# Keyless: the worktree carries no core/.env and the stand-in clients make no call. A fresh database of its own
# (bh_r_h12_08_db) serves the probe; the tests' session databases are made under bh_r_h12_08_t; all are dropped,
# and the worktree removed, at the end.
#   bash bughunt/repro/H12-08/run.sh        (from the repository root; exits 0 either way)
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PYTHONDONTWRITEBYTECODE=1 PGOPTIONS='-c client_min_messages=warning'
REV=2047f5a
DB=bh_r_h12_08_db
TPREFIX=bh_r_h12_08_t
S=$BH_WORK/H12-08; mkdir -p "$S"
WT=$S/wt-$$
T=$(mktemp -d "$S/run.XXXXXX")
PY=$BH_ROOT/core/.venv/bin/python
TESTS=(tests/test_key_override.py tests/test_request_guard.py tests/test_llm.py)
cleanup() {
  bh_db_drop "$DB"
  for d in $(psql "$BH_SERVER/postgres" -XAtc "select datname from pg_database where datname like '${TPREFIX}%'" 2>/dev/null); do
    bh_db_drop "$d"; done
  git -C "$BH_ROOT" worktree remove --force "$WT" >/dev/null 2>&1; git -C "$BH_ROOT" worktree prune
  rm -rf "$T" "$WT"; rmdir "$S" 2>/dev/null
}
trap cleanup EXIT
fail() { echo "the steps did not complete: $*"; echo "RESULT: NO-DEFECT"; exit 0; }

git -C "$BH_ROOT" worktree add --detach "$WT" "$REV" >/dev/null 2>&1 || fail "no worktree at $REV"
# The ignored fixture files the tests read (core/tests/fixtures/*.json, made by the client's scripts).
cp "$BH_ROOT"/core/tests/fixtures/{units,competence-unrated,competence,fields,lock-digests,resolvers}.json "$WT/core/tests/fixtures/" \
  || fail "the ignored fixtures"
[ -e "$WT/core/.env" ] && fail "the worktree holds a core/.env"
bh_db_fresh "$DB" || fail "bh_db_fresh $DB"
echo "worktree $WT at $(git -C "$WT" rev-parse --short HEAD); database $DB (fresh)"

# The probe: a read through Funnel naming a key, and request_key given a blank key.
cat > "$T/probe.py" <<'EOF'
import contextlib, os, sys
from fastapi.testclient import TestClient
from openferment_core import api, audit, guard, llm, projects
assert api.__file__.startswith(os.environ["WT"]), api.__file__
taken = []
real = llm.request_key
@contextlib.contextmanager
def recording(key):  # the middleware's own call, watched: whether the key is held for the request
    with real(key):
        taken.append(llm.key_named())
        yield
llm.request_key = recording
c = TestClient(api.app, base_url="http://127.0.0.1")
p = os.environ["PROJECT"]
made = c.post("/api/projects", json={"id": p, "name": p, "by": "bughunt"})
assert made.status_code == 201, made.text
NEEDLE = "named-by-a-funnel-read-H12-08"
r = c.get("/api/audit", headers={llm.KEY_HEADER: NEEDLE, guard.FUNNEL: "?1", "host": "mini.tail1234.ts.net",
                                 projects.HEADER: p})
with projects.using(p):
    rows = [a for a in audit.read() if a.action == "key_override"]
detail = r.json().get("detail") if r.status_code != 200 else None
print(f"funnel GET /api/audit naming a key: {r.status_code} detail={detail!r} key_held={any(taken)} "
      f"key_override_rows={[a.target for a in rows]}")
with real("  "):
    print(f"request_key('  '): key_named()={llm.key_named()} whose={llm._whose_key()!r}")
with real(""):
    print(f"request_key(''): key_named()={llm.key_named()} whose={llm._whose_key()!r}")
EOF
probe() {  # probe LABEL
  (cd "$WT/core" && bh_env WT="$WT" PROJECT="h12-08-$1" PYTHONPATH="$WT/core" OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" \
     "$PY" "$T/probe.py" 2>&1 | grep -E "^(funnel|request_key|Traceback|[A-Za-z]+Error)" ) || echo "probe failed"
}
tests() {
  (cd "$WT/core" && bh_env PYTHONPATH="$WT/core" OPENFERMENT_DATABASE_URL="$BH_SERVER/$DB" \
     OPENFERMENT_TEST_DATABASE_URL="$BH_SERVER/$TPREFIX" "$PY" -m pytest "${TESTS[@]}" -q -p no:randomly -p no:cacheprovider \
     -m "not live and not sim and not slow and not lit" 2>&1 | tail -1)
}
mutate() {  # mutate FILE OLD NEW: replace the one occurrence of OLD in the worktree's FILE
  OLD="$2" NEW="$3" "$PY" - "$WT/$1" <<'EOF'
import os, sys
path, old, new = sys.argv[1], os.environ["OLD"], os.environ["NEW"]
text = open(path).read()
assert text.count(old) == 1, f"{old!r} occurs {text.count(old)} times in {path}"
open(path, "w").write(text.replace(old, new))
EOF
}
restore() { git -C "$WT" checkout -q -- core/openferment_core; git -C "$WT" diff --quiet || fail "the worktree did not restore"; }

echo "0. the tree as it stands:"
P0=$(probe base); echo "$P0" | sed 's/^/   /'

M31_OLD='    if FUNNEL in headers:
        return "a request through Tailscale Funnel comes from the public internet and may not name a key"'
M31_NEW='    if False:
        return "a request through Tailscale Funnel comes from the public internet and may not name a key"'
mutate core/openferment_core/guard.py "$M31_OLD" "$M31_NEW" || fail "M31 does not apply"
echo "1. M31, key_refusal's Funnel rule dropped: $(git -C "$WT" diff --stat | tail -1 | sed 's/^ *//')"
git -C "$WT" diff -U0 | grep -E '^[-+] ' | sed 's/^/   /'
P1=$(probe m31); echo "$P1" | sed 's/^/   /'
R1=$(tests); echo "   pytest ${TESTS[*]}: $R1"
restore

M28_OLD='    token = _REQUEST_KEY.set((key or "").strip() or None)'
M28_NEW='    token = _REQUEST_KEY.set(key)'
mutate core/openferment_core/llm.py "$M28_OLD" "$M28_NEW" || fail "M28 does not apply"
echo "2. M28, request_key's strip-and-empty rule dropped: $(git -C "$WT" diff --stat | tail -1 | sed 's/^ *//')"
git -C "$WT" diff -U0 | grep -E '^[-+] ' | sed 's/^/   /'
P2=$(probe m28); echo "$P2" | sed 's/^/   /'
R2=$(tests); echo "   pytest ${TESTS[*]}: $R2"
restore

# The control: guard.refusal's own Funnel rule dropped, a rule test_request_guard holds; the same selection fails,
# so the tests above ran on the worktree's mutated code.
C_OLD='    if FUNNEL in headers:
        return "a request through Tailscale Funnel comes from the public internet and may not change anything"'
C_NEW='    if False:
        return "a request through Tailscale Funnel comes from the public internet and may not change anything"'
mutate core/openferment_core/guard.py "$C_OLD" "$C_NEW" || fail "the control does not apply"
echo "3. control, guard.refusal's Funnel rule dropped: $(git -C "$WT" diff --stat | tail -1 | sed 's/^ *//')"
RC=$(tests); echo "   pytest ${TESTS[*]}: $RC"
restore

green() { echo "$1" | grep -qE '^[0-9]+ passed' && ! echo "$1" | grep -qE 'failed|error'; }
B_FUN=$(echo "$P0" | grep -c "^funnel GET /api/audit naming a key: 403 .*Funnel.*may not name a key.* key_held=False key_override_rows=\[\]")
B_KEY=$(echo "$P0" | grep -c "^request_key('  '): key_named()=False")
M_FUN=$(echo "$P1" | grep -c "^funnel GET /api/audit naming a key: 200 .* key_held=True key_override_rows=\['GET /api/audit'\]")
M_KEY=$(echo "$P2" | grep -c "^request_key('  '): key_named()=True")
echo "EXPECTED: guard.py:95-99 refuses a key named through Tailscale Funnel on a read or a change alike, and llm.py:693-698 takes an empty key as none; so with either rule dropped a test of the override fails: a GET naming a key through Funnel answered 403, and request_key('  ') leaving key_named() False"
echo "OBSERVED: on the tree, the Funnel GET is $(echo "$P0" | grep -oP '^funnel GET /api/audit naming a key: \K[0-9]+') and request_key('  ') gives $(echo "$P0" | grep -oP "^request_key\('  '\): \Kkey_named\(\)=\w+"); with the Funnel rule dropped (M31) the Funnel GET is answered $(echo "$P1" | grep -oP '^funnel GET /api/audit naming a key: \K[0-9]+'), the key held for the request and an override row kept ($(echo "$P1" | grep -oP 'key_override_rows=\K.*')), and the tests give $R1; with the blank-key rule dropped (M28) request_key('  ') gives $(echo "$P2" | grep -oP "^request_key\('  '\): \Kkey_named\(\)=\w+") and $(echo "$P2" | grep -oP "^request_key\('  '\): key_named\(\)=\w+ \Kwhose=.*"), and the tests give $R2; the control (guard.refusal's Funnel rule dropped) gives $RC"
if [ "$B_FUN" = 1 ] && [ "$B_KEY" = 1 ] && [ "$M_FUN" = 1 ] && [ "$M_KEY" = 1 ] && green "$R1" && green "$R2" \
   && echo "$RC" | grep -qE '[0-9]+ failed'; then
  echo "RESULT: DEFECT"
else
  echo "RESULT: NO-DEFECT"
fi
exit 0
