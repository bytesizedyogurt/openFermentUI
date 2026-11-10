#!/usr/bin/env bash
# H10-05: guard.py's docstring names the hosts a changing request may come under (an IP address, a
# dotless name, `.local`, `.ts.net`, OPENFERMENT_ALLOWED_HOSTS) and leaves out `.localhost`, which
# OWN_SUFFIXES holds, the guard admits, and the generated OpenAPI description lists.
#   bash bughunt/repro/H10-05/run.sh            (from the repository root)
# Fresh database bh_r_h10_05_svc, the service on 127.0.0.1:9470, keyless, no model call; then the
# docstring, OWN_SUFFIXES and openapi.json's description read mechanically from the tree.
set -u
export PGOPTIONS="-c client_min_messages=warning"
source /home/user/openFermentUI/bughunt/lib/env.sh
cd "$BH_ROOT" || exit 0
DB=bh_r_h10_05_svc; PORT=9470; O="http://127.0.0.1:$PORT"
OUT="$BH_WORK/H10-05"
cleanup() { bh_svc_stop "$PORT"; bh_db_drop "$DB"; rm -rf "$OUT" "$BH_WORK/data-$DB"; }
trap cleanup EXIT
cleanup; mkdir -p "$OUT"

echo "tree: $(git -C "$BH_ROOT" rev-parse --short HEAD); core/ src/ scripts/ examples/ as at 2047f5a: $(git -C "$BH_ROOT" diff --quiet 2047f5a -- core src scripts examples docs/api/openapi.json && echo yes || echo NO)"
bh_svc_start "$DB" "$PORT" >/dev/null || { echo "OBSERVED: the service did not start"; echo "RESULT: NO-DEFECT"; exit 0; }
echo "service on $O over fresh database $DB"
echo "project r1: $(bh_project "$O" r1 | cut -c1-80)"
echo

# One changing request under each Host, its Origin the same host and port (as a page at that name sends).
post() {  # post HOSTNAME -> "code body"
  local h="$1"
  curl -s --noproxy '*' -o "$OUT/body-$h" -w '%{http_code}' -X POST "$O/api/biorepo/check" \
    -H 'content-type: application/json' -H 'X-OpenFerment-Project: r1' \
    -H "Host: $h:$PORT" -H "Origin: http://$h:$PORT" -d '{}' > "$OUT/code-$h"
  printf '%s %s' "$(cat "$OUT/code-$h")" "$(head -c 150 "$OUT/body-$h")"
}
echo "-- POST /api/biorepo/check with body {} (a 422 from the endpoint means the guard let it through; the guard refuses with 403)"
for h in evil.localhost evil.local evil.example.com; do
  printf '  Host %-17s -> %s\n' "$h:$PORT" "$(post "$h")"
done
echo

echo "-- the tree"
sed -n 22,24p core/openferment_core/guard.py | sed 's/^/  core\/openferment_core\/guard.py:22-24: /'
grep -n '^OWN_SUFFIXES' core/openferment_core/guard.py | sed 's/^/  core\/openferment_core\/guard.py:/'
grep -n '^_OWN_NAMES' core/openferment_core/api.py | cut -c1-120 | sed 's/^/  core\/openferment_core\/api.py:/'
grep -n 'OWN_SUFFIXES), "every name' core/tests/test_openapi.py | sed 's/^ *//' | sed 's/^/  core\/tests\/test_openapi.py:/'
echo

python3 -I - "$(cat "$OUT/code-evil.localhost")" "$(cat "$OUT/code-evil.local")" "$(cat "$OUT/code-evil.example.com")" <<'PY'
import ast, json, re, sys
code_lh, code_local, code_public = sys.argv[1:4]
src = open("core/openferment_core/guard.py").read()
mod = ast.parse(src)
doc = ast.get_docstring(mod) or ""
suffixes = next(ast.literal_eval(n.value) for n in mod.body
                if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "OWN_SUFFIXES" for t in n.targets))
para = " ".join(doc[doc.index("A host this service answers to"):].split("\n\n")[0].split())
said = json.load(open("docs/api/openapi.json"))["info"]["description"]
in_doc = {s: f"`{s}`" in doc for s in suffixes}
in_api = {s: f"`{s}`" in said for s in suffixes}
api_clause = re.search(r"a name ending [^,]*(, [^,]*)*? or `[^`]+`", said)
print(f"  OWN_SUFFIXES = {suffixes}")
print(f"  each suffix in guard.py's docstring: {in_doc}")
print(f"  each suffix in openapi.json's info.description: {in_api}")
print(f"  openapi.json says: '... {api_clause.group(0) if api_clause else '?'} ...'")
print()
print("EXPECTED: guard.py's docstring, the list of hosts 'this service answers to' (guard.py:22-24), names every suffix "
      "OWN_SUFFIXES holds and the guard admits, as api.py's DESCRIPTION (written from OWN_SUFFIXES) does in openapi.json: "
      + ", ".join(f"`{s}`" for s in suffixes))
missing = [s for s, ok in in_doc.items() if not ok]
print(f"OBSERVED: the docstring reads '{para[:200]}...'; it leaves out {missing}; "
      f"POST under Host evil.localhost answers {code_lh} (passed the guard), under evil.local {code_local}, "
      f"under evil.example.com {code_public} (refused); openapi.json lists `.localhost`: {in_api.get('.localhost')}")
defect = (".localhost" in suffixes and not in_doc.get(".localhost", True) and in_api.get(".localhost")
          and code_lh != "403" and code_public == "403")
print("RESULT: DEFECT" if defect else "RESULT: NO-DEFECT")
PY
exit 0
