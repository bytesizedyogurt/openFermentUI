#!/usr/bin/env bash
# H7-08: inside a project, the rail's logo links to #/, which drops the project from the address.
#
#   bash bughunt/repro/H7-08/run.sh        (from the repository root)
#
# The static half: the logo's anchor in src/App.tsx and in the built bundle in dist/ is written by hand as "#/",
# beside every other rail anchor written through href(). The live half: a fresh database (bh_r_h7_08_logo, made by
# bh_db_fresh through bh_svc_start), the service on 127.0.0.1:9131 over the built app in dist/, one project made
# through the API, then logo.mjs in Chromium: open #/p/<project>/runbooks, read the rail's links, click the logo,
# read the address, the screen, the top bar and the rail again, then follow the rail's Intake link. Keyless; no model
# call. Ends with RESULT: DEFECT or RESULT: NO-DEFECT and exits 0; the service is stopped and the database and its
# data copy removed on the way out.
set -u
source /home/user/openFermentUI/bughunt/lib/env.sh
export PGOPTIONS='-c client_min_messages=warning'
HERE=$(cd "$(dirname "$0")" && pwd)
DB=bh_r_h7_08_logo; PORT=9131; ORIGIN=http://127.0.0.1:$PORT; PROJECT=h7-08
OUT=$BH_WORK/H7-08/out; mkdir -p "$OUT"; FACTS=$OUT/facts.json; rm -f "$FACTS"
cleanup() { bh_svc_stop $PORT; bh_db_drop $DB; rm -rf "$BH_WORK/data-$DB" "$BH_WORK/H7-08"; }
trap cleanup EXIT
finish() { echo "OBSERVED: $1"; echo "RESULT: NO-DEFECT"; exit 0; }

echo "EXPECTED: inside a project (#/p/$PROJECT/...) the rail's logo is a link to a plain path like every other rail link, so it stays inside the project (ADR-009 7.1, docs/decisions/ADR-009-ui.md:21): it opens #/p/$PROJECT, the project's home, and the rail's links after it keep #/p/$PROJECT/."

# Static: the logo's anchor, by hand, in the source and in the bundle the service serves.
LOGO_SRC=$(grep -n '<a href="#/" className="flex items-center gap-2 min-w-0">' "$BH_ROOT/src/App.tsx" || true)
RAIL_SRC=$(grep -n 'href={href(item.to)}' "$BH_ROOT/src/App.tsx" || true)
LOGO_DIST=$(grep -l 'children:t.jsxs("a",{href:"#/",className:"flex items-center gap-2 min-w-0"' "$BH_ROOT"/dist/assets/*.js 2>/dev/null | wc -l)
echo "OBSERVED: src/App.tsx logo anchor: ${LOGO_SRC:-none}"
echo "OBSERVED: src/App.tsx rail anchors: ${RAIL_SRC:-none}"
echo "OBSERVED: bundles in dist/assets carrying the logo as href \"#/\": $LOGO_DIST"

bh_svc_start $DB $PORT >/dev/null || finish "the service did not start on $PORT"
bh_project "$ORIGIN" "$PROJECT" "H7-08 repro" >/dev/null
LISTED=$(curl -s --noproxy '*' "$ORIGIN/api/projects" | python3 -c "import json,sys; print(','.join(p['id'] for p in json.load(sys.stdin)))")
echo "SETUP: the service holds the projects [$LISTED]"
[ "$LISTED" = "$PROJECT" ] || finish "the service holds [$LISTED], expected [$PROJECT] alone"

(cd "$HERE" && env -u HTTPS_PROXY -u HTTP_PROXY -u https_proxy -u http_proxy timeout 300 \
  node logo.mjs "$ORIGIN" "$PROJECT" "$FACTS")
[ -s "$FACTS" ] || finish "the browser steps wrote no facts"

python3 - "$FACTS" "${LOGO_SRC:+1}" "$LOGO_DIST" <<'PY'
import json, sys
f = json.load(open(sys.argv[1])); static_src = sys.argv[2] == "1"; static_dist = int(sys.argv[3]) >= 1
p = f["project"]; pre = f"#/p/{p}"
b, l, i = f["before"], f["afterLogo"], f["afterIntake"]
logo, others = b["rail"][0], b["rail"][1:]
kept = [h for h in others if h.startswith(pre + "/") or h == pre]
print(f"OBSERVED: start address {b['address']}; top bar \"{b['topBar']}\"; the logo's href {logo}; "
      f"{len(kept)} of the {len(others)} other rail links keep {pre}/ ({' '.join(others[:3])} ...)")
print(f"OBSERVED: the rail's own Home entry (src/data/nav.ts, to '/') reads {others[0]}; the logo, aimed at the same "
      f"'/', reads {logo}")
print(f"OBSERVED: after the logo: address {l['address']}; top bar \"{l['topBar']}\"; localStorage openferment.project "
      f"{l['stored']!r}; the screen: \"{l['main'][:90]}\"")
lr = l["rail"][1:]
plain = [h for h in lr if not h.startswith(pre)]
print(f"OBSERVED: after the logo: {len(plain)} of the {len(lr)} rail links are plain paths ({' '.join(lr[:4])} ...)")
print(f"OBSERVED: after the rail's Intake link: address {i['address']}; top bar \"{i['topBar']}\"")
defect = (static_src and static_dist and logo == "#/" and len(kept) == len(others) and len(others) > 0
          and l["address"] in ("#/", "") and l["stored"] == p and len(plain) == len(lr) and len(lr) > 0
          and i["address"] == "#/intake")
print("RESULT: " + ("DEFECT" if defect else "NO-DEFECT"))
PY
exit 0
