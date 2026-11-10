"""Check a run report (GET /api/runs/{id} answer) field by field against docs/api/runs.md.

    python3 -I check_run.py REPORT.json

Prints one line a check, `ok` or `DIFF` with what differs. Reads the file alone: no service.
"""
import hashlib
import json
import sys

ORIGIN_OF = {"assumption": "person-assumption", "model": "library-default"}


def canonical(v):
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def artifact_id(tool, version, inputs, seed):
    payload = {"tool": tool, "toolVersion": version, "inputs": inputs}
    if seed is not None:
        payload["seed"] = seed
    return hashlib.sha256(canonical(payload).encode("utf-8")).hexdigest()[:16]


def origin_kind(source):
    k = source["kind"]
    if k == "deposition":
        return "measurement" if source.get("id") else "record"
    return ORIGIN_OF.get(k, k)


def main(path):
    rep = json.load(open(path))
    run, art = rep["run"], rep.get("artifact")
    out = []

    def check(name, ok, said=""):
        out.append(f"{'ok  ' if ok else 'DIFF'} {name}" + (f": {said}" if said else ""))

    if art is None:
        check("receipt has no artifact", run["status"] == "refused", run["status"])
        print("\n".join(out))
        return
    aid = artifact_id(art["tool"], art["toolVersion"], art["inputs"], art.get("seed"))
    check("id == artifact id of basis", run["id"] == aid == art["id"], f"run {run['id']} art {art['id']} computed {aid}")
    check("artifactId == id", run["artifactId"] == run["id"])
    check("tool/version", (run["tool"], run["toolVersion"]) == (art["tool"], art["toolVersion"]),
          f"{run['tool']} {run['toolVersion']} / {art['tool']} {art['toolVersion']}")
    check("provenance == artifact's", run["provenance"] == art["provenance"], f"{run['provenance']} / {art['provenance']}")
    ins = art["inputs"]
    check("inputs count", len(run["inputs"]) == len(ins), f"{len(run['inputs'])} / {len(ins)}")
    for r, b in zip(run["inputs"], ins):
        q = r["quantity"]
        same = (r["name"], q["value"], q["unit"]) == (b["name"], b["value"], b["unit"])
        kind = origin_kind(b["source"])
        if not same or q["origin"]["kind"] != kind:
            check(f"input {b['name']}", False, f"row {r['name']}={q['value']} {q['unit']} {q['origin']['kind']}; "
                                                f"basis {b['value']} {b['unit']} {b['source']['kind']}->{kind}")
    check("inputs typed with origins", all(i["quantity"].get("origin") for i in run["inputs"]))
    vals = (run.get("outputs") or {}).get("values")
    check("outputs.values present", isinstance(vals, list), str(type(vals)))
    bad = [v["name"] for v in vals or [] if v["quantity"].get("origin") != {"kind": "artifact", "ref": art["id"]}]
    check("every output's origin is the run's artifact", not bad, ", ".join(bad[:5]))
    check("versions non-empty", bool(run.get("versions")), str(run.get("versions")))
    sff = run.get("sff")
    check("sff xor sffRefused", (sff is None) != (run.get("sffRefused") is None), f"sff={sff} refused={run.get('sffRefused')}")
    if sff:
        fs = rep.get("flowsheet") or {}
        check("sff record is run-<id>", sff["recordId"] == f"run-{run['id']}" == fs.get("id"), f"{sff['recordId']} {fs.get('id')}")
        check("flowsheet names the run's artifact", fs.get("runArtifactId") == art["id"], str(fs.get("runArtifactId")))
    check("durationMs == artifact's", run.get("durationMs") == art.get("durationMs"), f"{run.get('durationMs')} / {art.get('durationMs')}")
    check("by set", bool(run.get("by")), str(run.get("by")))
    print(f"run {run['id']} engine={run['engine']} plant={run['plant']} configuration={run['configuration']} "
          f"tool={run['tool']} provenance={run['provenance']} scenarioId={run.get('scenarioId')} versions={run.get('versions')}")
    print("\n".join(out))


if __name__ == "__main__":
    main(sys.argv[1])
