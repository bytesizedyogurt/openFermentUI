"""Read every kept run, artifact, scenario, comparison and runbook of a project through the head's routes.

    python3 -I read_kept.py ORIGIN PROJECT OUT_DIR [--replay]

Writes OUT_DIR/summary.json and prints one line a thing read: its route, its status and what it says.
With --replay, replays every run's artifact and every comparison's.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from api import call  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from check_run import artifact_id  # noqa: E402


def main(origin, project, out_dir, replay=False):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    summary = {"runs": [], "artifacts": [], "scenarios": [], "comparisons": [], "runbooks": [], "replays": []}

    def get(path):
        status, body = call(origin, project, "GET", path)
        return status, body

    s, runs = get("/api/runs")
    print("GET /api/runs", s, len(runs) if isinstance(runs, list) else runs)
    for r in runs if isinstance(runs, list) else []:
        s2, rep = get(f"/api/runs/{r['id']}")
        line = {"id": r["id"], "status": s2, "engine": r.get("engine"), "plant": r.get("plant"),
                "tool": r.get("tool"), "provenance": r.get("provenance"), "runStatus": r.get("status")}
        if s2 == 200:
            art = rep.get("artifact")
            run = rep["run"]
            if art:
                line["idMatchesBasis"] = artifact_id(art["tool"], art["toolVersion"], art["inputs"], art.get("seed")) == run["id"]
                vals = (run.get("outputs") or {}).get("values")
                line["values"] = None if vals is None else len(vals)
                line["valuesOriginOk"] = vals is None or all(v["quantity"].get("origin", {}).get("ref") == art["id"] for v in vals)
            line["versions"] = run.get("versions")
            line["sff"] = (run.get("sff") or {}).get("recordId")
            line["sffRefused"] = run.get("sffRefused")
            line["parameters"] = None if rep.get("parameters") is None else len(rep["parameters"].get("values") or [])
            for sub in ("tables", "checks"):
                if run.get("artifactId"):
                    s3, b3 = get(f"/api/biorepo/artifacts/{run['artifactId']}/{sub}")
                    line[sub] = s3 if s3 != 200 else ("ok", len(b3) if isinstance(b3, list) else len(b3.get("streams") or []))
        else:
            line["said"] = rep
        summary["runs"].append(line)
        print("  run", json.dumps(line, ensure_ascii=False)[:400])
        if replay and r.get("artifactId"):
            status, res = call(origin, project, "POST", f"/api/biorepo/artifacts/{r['artifactId']}/replay", {})
            rl = {"artifact": r["artifactId"], "status": status}
            if status == 200:
                rl.update(identical=res["identical"], within=res.get("withinTolerance"),
                          tolerance=(res.get("tolerance") or {}).get("rtol"),
                          differences=[(d["path"], d["stored"], d["replayed"]) for d in res["differences"][:5]])
            else:
                rl["said"] = res
            summary["replays"].append(rl)
            print("    replay", json.dumps(rl, ensure_ascii=False)[:600])
    s, arts = get("/api/biorepo/artifacts")
    print("GET /api/biorepo/artifacts", s, len(arts) if isinstance(arts, list) else arts)
    for a in arts if isinstance(arts, list) else []:
        s2, one = get(f"/api/biorepo/artifacts/{a['id']}")
        summary["artifacts"].append({"id": a["id"], "tool": a["tool"], "version": a["toolVersion"], "status": s2,
                                     "provenance": a.get("provenance")})
    for kind, path in (("scenarios", "/api/studies/scenarios"), ("comparisons", "/api/studies/comparisons"),
                       ("runbooks", "/api/studies/runbooks")):
        s, listed = get(path)
        print("GET", path, s, len(listed) if isinstance(listed, list) else listed)
        for x in listed if isinstance(listed, list) else []:
            s2, one = get(f"{path}/{x['id']}")
            line = {"id": x["id"], "status": s2}
            if kind == "comparisons" and s2 == 200:
                line["artifact"] = one["artifact"]["toolVersion"]
                if replay:
                    status, res = call(origin, project, "POST", f"/api/biorepo/artifacts/{x['artifactId']}/replay", {})
                    line["replay"] = (status, res.get("identical") if status == 200 else res,
                                      [(d["path"], d["stored"], d["replayed"]) for d in res.get("differences", [])[:3]]
                                      if status == 200 else None)
            if s2 != 200:
                line["said"] = one
            summary[kind].append(line)
            print(" ", kind[:-1], json.dumps(line, ensure_ascii=False)[:500])
    (out / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], "--replay" in sys.argv)
