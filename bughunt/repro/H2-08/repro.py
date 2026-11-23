"""H2-08: a comparison asked again with a title of spaces loses the title it was kept with.

    python3 -I repro.py ORIGIN PROJECT

Two kinetics forecast runs (from two fits of placeholder logistic series the script writes), one
comparison kept with a title, the same runs asked again with a title of three spaces by another
asker, and the comparison read back. Prints CASE lines and a final VERDICT line; exit 0.
"""
import json
import math
import sys
import urllib.error
import urllib.request

ORIGIN, PROJECT = sys.argv[1], sys.argv[2]
KEPT_TITLE = "default beside measured"


def call(method, path, body=None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(ORIGIN + path, data=data, method=method)
    req.add_header("X-OpenFerment-Project", PROJECT)
    if data is not None:
        req.add_header("content-type", "application/json")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=600) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw or b"null")
        except ValueError:
            return e.code, raw.decode("utf-8", "replace")


def fit_request(dep, scale):
    """Placeholder logistic series (test input, no science): biomass, product, substrate."""
    ts = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 24]
    x = lambda t: 5.0 / (1 + (5.0 - 0.1) / 0.1 * math.exp(-0.4 * t))
    pt = lambda pre, t, v: {"t": t, "value": round(v, 5), "entryId": f"{pre}{t}", "confirmed": True}
    return {"depositionId": dep, "series": [
        {"measureId": "m-x", "label": "biomass", "unit": "g L-1", "role": "biomass",
         "points": [pt("x", t, x(t)) for t in ts]},
        {"measureId": "m-p", "label": "ethanol", "unit": "g L-1", "role": "product",
         "points": [pt("p", t, 4.0 * (x(t) - 0.1) * scale) for t in ts]},
        {"measureId": "m-s", "label": "glucose", "unit": "g L-1", "role": "substrate",
         "points": [pt("s", t, max(0.0, 60 - 10 * (x(t) - 0.1))) for t in ts]},
    ]}


def forecast_run(dep, scale):
    st, fit = call("POST", "/api/fermos/fit", fit_request(dep, scale))
    if st != 200:
        sys.exit(f"SETUP: fit {dep} answered {st}: {fit}")
    st, fc = call("POST", "/api/fermos/forecast", {"fitArtifactId": fit["kineticArtifactId"], "by": "Hunter H2-08"})
    if st != 200:
        sys.exit(f"SETUP: forecast of {dep} answered {st}: {fc}")
    return fc["artifactId"]


def listed_title(cid):
    st, rows = call("GET", "/api/studies/comparisons")
    return next((r["title"] for r in rows if r["id"] == cid), "<absent>") if st == 200 else f"<{st}>"


ra, rb = forecast_run("dep-h208-a", 1), forecast_run("dep-h208-b", 2)
print(f"SETUP: two kinetics runs {ra} and {rb}")

st1, first = call("POST", "/api/studies/comparisons", {"title": KEPT_TITLE, "runIds": [ra, rb], "by": "Hunter H2-08"})
if st1 != 200:
    sys.exit(f"SETUP: the first comparison answered {st1}: {first}")
cid = first["comparison"]["id"]
print(f"CASE first ask: {st1} id {cid} title {first['comparison']['title']!r} by {first['comparison']['by']!r}")

st2, again = call("POST", "/api/studies/comparisons", {"title": "   ", "runIds": [ra, rb], "by": "Someone Else"})
if st2 == 200:
    c = again["comparison"]
    print(f"CASE asked again, title of three spaces: {st2} id {c['id']} title {c['title']!r} by {c['by']!r}")
else:
    print(f"CASE asked again, title of three spaces: {st2} {again}")

st3, one = call("GET", f"/api/studies/comparisons/{cid}")
got = one["comparison"]["title"] if st3 == 200 else f"<{st3}>"
lst = listed_title(cid)
print(f"CASE read back: GET /api/studies/comparisons/{cid} title {got!r}; the list's title {lst!r}")

st4, fresh = call("POST", "/api/studies/comparisons", {"title": "   ", "runIds": [rb, ra], "by": "Hunter H2-08"})
if st4 == 200:
    print(f"CASE first ask with a title of three spaces (runs reversed): {st4} title {fresh['comparison']['title']!r}")
else:
    print(f"CASE first ask with a title of three spaces (runs reversed): {st4} {fresh}")

lost = st2 == 200 and got == "" and lst == ""
blank_kept = st4 == 200 and fresh["comparison"]["title"] == ""
print(f"COMPARISON_ID {cid}")
print(f"VERDICT {'DEFECT' if lost else 'NO-DEFECT'} lost={lost} blank_first_ask_kept={blank_kept}")
