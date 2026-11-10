"""Open a study export package with the standard library alone and check it against docs/api/studies.md.

    python3 -I -S open_export.py PACKAGE.zip

Checks: every manifest entry's size and sha256; each SFF file's sha256 against its record in study.json;
every run's artifact present; every artifact a run or comparison names (an `artifact` source in a basis)
present; every comparison's artifact present. Prints one line a check.
"""
import hashlib
import json
import sys
import zipfile


def main(path):
    z = zipfile.ZipFile(path)
    names = z.namelist()
    man = json.loads(z.read("manifest.json"))
    bad = []
    for f in man["files"]:
        data = z.read(f["path"])
        if len(data) != f["bytes"] or hashlib.sha256(data).hexdigest() != f["sha256"]:
            bad.append(f["path"])
    print("manifest sizes and sha256:", "ok" if not bad else f"DIFF {bad}")
    listed = {f["path"] for f in man["files"]} | {"manifest.json"}
    print("every member listed:", "ok" if set(names) == listed else f"DIFF {set(names) ^ listed}")
    held = json.loads(z.read("study.json"))
    arts = held["artifacts"]
    for run_id, fs in held["flowsheets"].items():
        data = z.read(f"sff/{run_id}.sff.json")
        ok = hashlib.sha256(data).hexdigest() == fs["sha256"]
        print(f"sff/{run_id}.sff.json sha256 == record's:", "ok" if ok else "DIFF")
    missing_run_art = [r["id"] for r in held["runs"] if r.get("artifactId") and r["artifactId"] not in arts]
    print("each run's artifact held:", "ok" if not missing_run_art else f"DIFF {missing_run_art}")
    rested = {}
    for a in arts.values():
        for i in a["inputs"]:
            if i["source"]["kind"] == "artifact" and i["source"].get("id"):
                rested.setdefault(i["source"]["id"], set()).add(f"{a['tool']} {a['id']} ({i['name']})")
    absent = {k: sorted(v) for k, v in rested.items() if k not in arts}
    print("each artifact a kept artifact rests on held:", "ok" if not absent else "MISSING")
    for k, v in absent.items():
        print("   ", k, "named by", "; ".join(v))
    missing_cmp = [c["id"] for c in held["comparisons"] if c["artifactId"] not in arts]
    print("each comparison's artifact held:", "ok" if not missing_cmp else f"DIFF {missing_cmp}")
    print("counts:", {k: len(held[k]) for k in ("runs", "scenarios", "comparisons", "runbooks", "depositions")},
          "artifacts", len(arts), "sff files", len(held["flowsheets"]))
    print("python -S, site imported:", "site" in sys.modules)


if __name__ == "__main__":
    main(sys.argv[1])
