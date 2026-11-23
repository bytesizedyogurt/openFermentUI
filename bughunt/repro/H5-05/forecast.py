"""H5-05: POST /api/fermos/forecast naming a fit the project does not hold.

    ORIGIN=http://127.0.0.1:PORT python -I forecast.py

Two projects. In h505-a, one kinetic fit kept through POST /api/fermos/fit from a SYNTHETIC batch generated
here from parameters chosen here (no measurement, no model, no network). Then the forecast door asked three
ways for a fit the acting project does not hold: an unknown hex id in h505-a, A's own fit id sent from h505-b,
and the tool door's growth_forecast with the unknown id. A neighbour door, the forecast scope's read
GET /api/params/fermos:forecast:<id>, is asked the same id for contrast. Prints EXPECTED, OBSERVED and the
per-check verdicts; run.sh reads the RESULT line.
"""
import math
import os
import sys

import httpx

ORIGIN = os.environ["ORIGIN"]
A, B = "h505-a", "h505-b"
BY = "bob"
UNKNOWN = "0123456789abcdef"


def call(method, path, project, **kw):
    # One connection a request: after a 500 the server drops the kept-alive connection.
    with httpx.Client(base_url=ORIGIN, trust_env=False, timeout=600) as c:
        r = c.request(method, path, headers={"X-OpenFerment-Project": project}, **kw)
    try:
        body = r.json()
    except ValueError:
        body = r.text
    return r.status_code, body


def stop(label, got):
    print(f"setup stopped at {label}: {got[0]} {str(got[1])[:300]}")
    print("RESULT: NO-DEFECT")
    sys.exit(0)


def logistic_batch():
    """A synthetic batch: logistic biomass, Luedeking-Piret product, substrate by yield. Chosen here."""
    x0, mu, xmax, p0, alpha, beta, s0, gamma, delta = 0.1, 0.35, 8.0, 0.05, 0.4, 0.02, 60.0, 4.5, 0.05
    ts = [30.0 * i / 9 for i in range(10)]
    xs, ints = [], []
    for t in ts:
        e = math.exp(mu * t)
        xs.append(xmax * x0 * e / (xmax - x0 + x0 * e))
        ints.append((xmax / mu) * math.log((xmax - x0 + x0 * e) / xmax))
    ps = [p0 + alpha * (x - x0) + beta * i for x, i in zip(xs, ints)]
    ss = [s0 - gamma * (x - x0) - delta * i for x, i in zip(xs, ints)]

    def series(role, vals):
        return {"measureId": f"m-{role}", "label": role, "unit": "g L-1", "role": role,
                "points": [{"t": t, "value": v, "entryId": f"{role}-{k}", "confirmed": True}
                           for k, (t, v) in enumerate(zip(ts, vals))]}

    return [series("biomass", xs), series("product", ps), series("substrate", ss)]


for p in (A, B):
    got = call("POST", "/api/projects", p, json={"id": p, "name": p, "by": BY})
    if got[0] not in (200, 201):
        stop(f"project {p}", got)
    print(f"project {p}: {got[0]}")

fit = call("POST", "/api/fermos/fit", A, json={"depositionId": "dep-h505", "series": logistic_batch()})
if fit[0] != 200 or not fit[1].get("kineticArtifactId"):
    stop("fit in A", fit)
FIT = fit[1]["kineticArtifactId"]
print(f"A kept kinetic fit {FIT} (POST /api/fermos/fit: {fit[0]})")

checks = []


def forecast(label, project, fit_id):
    s, body = call("POST", "/api/fermos/forecast", project, json={"by": BY, "fitArtifactId": fit_id})
    detail = body.get("detail") if isinstance(body, dict) else body
    print(f"{label}: POST /api/fermos/forecast in {project} fitArtifactId={fit_id} -> {s} {str(detail)[:200]!r}")
    in_words = s in (404, 422) and isinstance(detail, str) and fit_id in detail
    checks.append((label, in_words, s, detail))
    return s, detail


print()
print("EXPECTED: each forecast of a fit the acting project does not hold answers a 404 or 422 with a `detail` in "
      "words naming the fit (fermos.py:928's own words: 'there is no kept fit <id>'), as the forecast scope's "
      "read and the other fit doors answer; the tool door's refusal says the same in words")

# Contrast: the forecast scope's own read of the same unknown fit.
s, body = call("GET", f"/api/params/fermos:forecast:{UNKNOWN}", A)
print(f"contrast: GET /api/params/fermos:forecast:{UNKNOWN} in {A} -> {s} "
      f"{str(body.get('detail') if isinstance(body, dict) else body)[:200]!r}")

forecast("check 1 (unknown id)", A, UNKNOWN)
forecast("check 2 (A's fit asked from B)", B, FIT)

s, body = call("POST", "/api/tools/growth_forecast", A, params={"by": BY}, json={"fitArtifactId": UNKNOWN})
err = body.get("error") if isinstance(body, dict) else body
print(f"check 3 (tool door): POST /api/tools/growth_forecast in {A} -> {s} error={err!r}")
tool_words = isinstance(err, str) and "no kept fit" in err
checks.append(("check 3 (tool door)", tool_words, s, err))

# A's own fit still answers from A: the forecast door works for a fit the project holds.
s, body = call("POST", "/api/fermos/forecast", A, json={"by": BY, "fitArtifactId": FIT})
print(f"control: POST /api/fermos/forecast in {A} fitArtifactId={FIT} (A's own) -> {s}"
      + (f" artifactId={body.get('artifactId')}" if isinstance(body, dict) and s == 200 else f" {str(body)[:200]!r}"))

print()
bad = [c for c in checks if not c[1]]
http_500 = [c for c in checks[:2] if c[2] == 500]
print("OBSERVED: " + "; ".join(f"{lab}: {'in words' if ok else 'NOT in words'} ({st} {str(d)[:80]!r})"
                               for lab, ok, st, d in checks))
print(f"http 500 on the REST door: {len(http_500)} of 2")
print("RESULT: DEFECT" if http_500 else "RESULT: NO-DEFECT")
