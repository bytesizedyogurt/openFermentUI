"""The export package of a project's studies (execution prompt §9.1 step 5).

One zip that opens with nothing of openFerment's: the standard library
reads all of it (test_exports.py opens it in `python -I -S`, which leaves
out every installed package). It holds

    study.json          every engine run with its inputs and their origins,
                        its outputs, versions and SFF record; every study
                        scenario, comparison and runbook; and, whole, the
                        artifacts that computed the runs and comparisons
    study.md            the same in words and tables
    sff/<run>.sff.json  each run's flowsheet, byte for byte as the project
                        holds it
    versions.json       openFerment's own version; each run's tool, its
                        simulator, property engine and package; each SFF
                        file's toolkit and schema; each comparison's
                        version; and the lock digest's algorithm
    manifest.json       the project, when and by whom, and each other
                        file's size and sha256

The same study gives the same study.json, study.md, versions.json and SFF
files, byte for byte; the manifest says when it was taken. A run its plant
refused is there as its receipt, with no artifact and no SFF file.

    GET /api/studies/export                          the package, application/zip
    python -m openferment_core.studies.exports OUT.zip
                                                     the same, for the project
                                                     OPENFERMENT_PROJECT names (ADR-005)
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import platform
import sys
import zipfile
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any

from dotenv import dotenv_values

from .. import db, projects
from ..engine import runs, sff
from . import comparisons, runbooks, scenarios

FORMAT = "openferment study export 1"
# Every member stamped alike, so the package's bytes are its files'.
STAMP = (1980, 1, 1, 0, 0, 0)
LOCK_DIGEST = "FNV-1a, 32 bits, two passes over the canonical text (src/engine/lock.ts; core/openferment_core/runbook_lock.py)"
NONE = "—"
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class ExportRefused(ValueError):
    """A package that cannot be made, in words."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _json(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def _version() -> str:
    try:
        return metadata.version("openferment-core")
    except metadata.PackageNotFoundError:
        return "unknown"


def _sff_path(run_id: str) -> str:
    return f"sff/{run_id}.sff.json"


# ── study.json ─────────────────────────────────────────────────────────


def study() -> dict[str, Any]:
    """Everything the project's studies hold, oldest first, in the shapes
    the service answers them."""
    pid = projects.current()
    project = projects.get(pid)
    if project is None:
        raise ExportRefused(f"the database holds no project {pid}")
    reports = [runs.report(r.id) for r in reversed(runs.listed())]
    compared = [comparisons.get(c.id) for c in reversed(comparisons.listed())]
    artifacts: dict[str, Any] = {}
    for rep in reports:
        if rep.artifact is not None:
            artifacts[rep.artifact.id] = rep.artifact.model_dump(mode="json")
    for rep in compared:
        artifacts[rep.artifact.id] = rep.artifact.model_dump(mode="json")
    return {
        "format": FORMAT,
        "project": {"id": pid, "name": project.name},
        "runs": [rep.run.model_dump(mode="json") for rep in reports],
        "flowsheets": {rep.run.id: rep.flowsheet.model_dump(mode="json", exclude={"graph"})
                       for rep in reports if rep.flowsheet is not None},
        "scenarios": [s.model_dump(mode="json") for s in reversed(scenarios.listed())],
        "comparisons": [rep.comparison.model_dump(mode="json") for rep in compared],
        # As kept: the lock's digest reads a prediction's absent field and a null one differently.
        "runbooks": [b.model_dump(mode="json", exclude_unset=True) for b in reversed(runbooks.listed())],
        "artifacts": artifacts,
    }


def versions(held: dict[str, Any]) -> dict[str, Any]:
    arts = held["artifacts"]
    return {
        "openferment": _version(),
        "python": platform.python_version(),
        "runs": {r["id"]: {"tool": r["tool"], "toolVersion": r["toolVersion"], **r["versions"]} for r in held["runs"]},
        "sff": {run_id: {"record": f["id"], "toolkit": f["toolkit"], "sffVersion": f.get("sffVersion"),
                         "schemaVersion": (f.get("validation") or {}).get("schemaVersion")}
                for run_id, f in held["flowsheets"].items()},
        "comparisons": {c["id"]: arts[c["artifactId"]]["toolVersion"] for c in held["comparisons"]},
        "lockDigest": LOCK_DIGEST,
    }


# ── study.md ───────────────────────────────────────────────────────────


def _cell(value: Any) -> str:
    if value is None or value == "":
        return NONE
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        # The ten significant digits a library run keeps.
        return f"{value:.10g}"
    return str(value).replace("|", "\\|").replace("\n", " ")


def _table(head: list[str], rows: list[list[Any]]) -> list[str]:
    return ["| " + " | ".join(head) + " |", "|" + "---|" * len(head),
            *("| " + " | ".join(_cell(c) for c in row) + " |" for row in rows), ""]


def _change(value: Any) -> str:
    return f"{value:+.2%}" if isinstance(value, (int, float)) and not isinstance(value, bool) else NONE


def _run_section(run: dict[str, Any], art: dict[str, Any] | None, scenario_titles: dict[str, str]) -> list[str]:
    where = run["plant"] + (f" ({run['configuration']})" if run.get("configuration") else "")
    out = [f"### Run `{run['id']}`: {where}", ""]
    said = f"By {_cell(run['by'])}, {run['at']}; {run['status']}"
    said += f", {run['provenance']}." if run.get("provenance") else "."
    if run.get("scenarioId"):
        said += f" Asked for by scenario `{run['scenarioId']}` ({_cell(scenario_titles.get(run['scenarioId']))})."
    out += [said, ""]
    if run["status"] == "refused":
        return [*out, f"The plant refused it: {_cell(run.get('refused'))}", ""]
    out += ["Its inputs, each with its origin:", ""]
    out += _table(["Input", "Value", "Unit", "Origin", "By", "Rests on"], [
        [i["name"], i["quantity"]["value"], i["quantity"]["unit"], (i["quantity"].get("origin") or {}).get("kind"),
         (i["quantity"].get("origin") or {}).get("by") or (i["quantity"].get("origin") or {}).get("ref"),
         (i["quantity"].get("origin") or {}).get("note")] for i in run["inputs"]])
    output = (art or {}).get("output") or {}
    price = output.get("price") or {}
    units = price.get("units") or {}
    numbers = [[k, v, units.get(k)] for k, v in sorted(price.items())
               if isinstance(v, (int, float)) and not isinstance(v, bool)]
    if numbers:
        out += ["Its price, in BioSTEAM's TEA units:", "", *_table(["Key", "Value", "Unit"], numbers)]
    flows, flow_units = output.get("outputs") or {}, output.get("outputUnits") or {}
    if flows:
        out += ["The flowsheet's outputs:", "", *_table(["Output", "Value", "Unit"],
                                                       [[k, v, flow_units.get(k)] for k, v in sorted(flows.items())])]
    held = run.get("outputs", {}).get("regression")
    if held:
        out += [f"The package's own test holds {held['within']} of its {held['of']} values within its tolerance.", ""]
    if run.get("sff"):
        s = run["sff"]
        out += [f"Its SFF file is `{_sff_path(run['id'])}` (record `{s['recordId']}`): "
                f"{'valid' if s['valid'] else 'not valid'}, scored {_cell(s.get('score'))}.", ""]
    elif run.get("sffRefused"):
        out += [f"No SFF file could be written: {_cell(run['sffRefused'])}", ""]
    return out


def markdown(held: dict[str, Any], vers: dict[str, Any]) -> str:
    arts = held["artifacts"]
    titles = {s["id"]: s["title"] for s in held["scenarios"]}
    out = [f"# {_cell(held['project']['name'])}: studies", "",
           f"Exported from openFerment {vers['openferment']}, project `{held['project']['id']}`. `study.json` holds "
           "every number below with its unit and its origin, and the artifacts that computed them; `sff/` holds each "
           "run's flowsheet; `versions.json` names every tool; `manifest.json` says when the package was taken and "
           "gives each file's sha256.", ""]

    out += ["## Engine runs", ""]
    if not held["runs"]:
        out += ["The project holds no engine run.", ""]
    else:
        out += _table(["Run", "Plant", "Configuration", "Status", "Provenance", "SFF file"], [
            [f"`{r['id']}`", r["plant"], r.get("configuration"), r["status"], r.get("provenance"),
             f"`{_sff_path(r['id'])}`" if r.get("sff") else None] for r in held["runs"]])
        for r in held["runs"]:
            out += _run_section(r, arts.get(r.get("artifactId") or ""), titles)

    out += ["## Scenarios", ""]
    if not held["scenarios"]:
        out += ["The project holds no study scenario.", ""]
    for s in held["scenarios"]:
        where = s["plant"] + (f" ({s['configuration']})" if s.get("configuration") else "")
        out += [f"### {_cell(s['title'])} (`{s['id']}`)", "",
                f"On {where}, made by {_cell(s['by'])}, {s['at']}." + (f" {_cell(s['note'])}" if s.get("note") else ""),
                "", *_table(["Parameter", "Value", "Unit", "Origin", "By", "At", "Rests on"], [
                    [v["key"], v["quantity"]["value"], v["quantity"]["unit"], v["quantity"]["origin"]["kind"],
                     v["quantity"]["origin"].get("by"), v["quantity"]["origin"].get("at"),
                     v["quantity"]["origin"].get("note")] for v in s["values"]]),
                "Its runs: " + (", ".join(f"`{r}`" for r in s["runIds"]) or "none yet") + ".", ""]

    out += ["## Comparisons", ""]
    if not held["comparisons"]:
        out += ["The project holds no comparison.", ""]
    for c in held["comparisons"]:
        output = arts[c["artifactId"]]["output"]
        named = [f"`{r['artifactId']}`" for r in output["runs"]]
        out += [f"### {_cell(c['title'])} (`{c['id']}`)", "",
                f"{c['provenance']}; by {_cell(c['by'])}, {c['at']}. The runs, in order: {', '.join(named)}; each "
                "change is reckoned from the first.", ""]
        head = ["Output", "Unit", *(f"Run {n}" for n in range(1, len(named) + 1)),
                *(f"Change {n}" for n in range(2, len(named) + 1))]
        out += _table(head, [[row["key"], row["unit"], *row["values"], *map(_change, row["change"][1:])]
                             for row in output["rows"]])
        if output["values"]:
            out += ["The values the runs set, each with its origin:", ""]
            out += _table(["Value", *(f"Run {n}" for n in range(1, len(named) + 1))], [
                [v["key"], *(f"{_cell(x['value'])} {x['unit']} ({x['origin']}, {_cell(x.get('by'))})"
                             for x in v["values"])] for v in output["values"]])

    out += ["## Runbooks", ""]
    if not held["runbooks"]:
        out += ["No study has made a runbook.", ""]
    for b in held["runbooks"]:
        state = (f"Locked {b['lockedAt']} under `{b['lockHash']}`." if b.get("lockedAt")
                 else "A draft: its predictions are not locked.")
        measured = {m.get("predictionId"): m["timepoint"] for m in b["measurementSchema"]}
        out += [f"### {_cell(b['title'])} (`{b['id']}`)", "", state, "",
                *_table(["Prediction", "Value", "Unit", "Confidence", "Measured at", "Basis"], [
                    [p["label"], p["value"], p["unit"], p["confidence"], measured.get(p["id"]), p["basis"]]
                    for p in b["predictions"]])]

    out += ["## Versions", "", f"openFerment {vers['openferment']} on Python {vers['python']}. A runbook's lock digest: "
            f"{vers['lockDigest']}.", ""]
    if vers["runs"]:
        out += _table(["Run", "Tool", "BioSTEAM", "thermosteam", "biorefineries", "SFF toolkit", "SFF schema"], [
            [f"`{rid}`", f"{v['tool']} ({v['toolVersion']})", v.get("biosteam"), v.get("thermosteam"),
             v.get("biorefineries"), vers["sff"].get(rid, {}).get("toolkit"), vers["sff"].get(rid, {}).get("schemaVersion")]
            for rid, v in vers["runs"].items()])
    return "\n".join(out).rstrip() + "\n"


# ── the package ────────────────────────────────────────────────────────


def files(*, by: str = "") -> dict[str, bytes]:
    """The package's files by path, the manifest last of them."""
    held = study()
    vers = versions(held)
    at = _now()
    pid = held["project"]["id"]
    out = {"study.json": _json(held), "study.md": markdown(held, vers).encode("utf-8"), "versions.json": _json(vers)}
    for run_id, f in held["flowsheets"].items():
        out[_sff_path(run_id)] = sff.document(f["id"], project_id=pid).encode("utf-8")
    out["manifest.json"] = _json({
        "format": FORMAT, "project": held["project"], "exportedAt": at, "exportedBy": (by or "").strip() or "this browser",
        "files": [{"path": p, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()} for p, data in sorted(out.items())],
    })
    return out


def filename() -> str:
    return f"{projects.current()}-studies.zip"


def package(*, by: str = "") -> bytes:
    """The package as one zip, its members stamped alike."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for path, data in files(by=by).items():
            info = zipfile.ZipInfo(path, date_time=STAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, data)
    return buf.getvalue()


def _settings() -> None:
    """The database address and the project, from core/.env when the
    environment does not set them: these two names alone (ADR-005)."""
    held = dotenv_values(ENV_FILE)
    for name in (db.URL_SETTING, projects.ENV):
        if held.get(name) and not os.environ.get(name):
            os.environ[name] = str(held[name])


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    _settings()
    try:
        data = package(by="the command line")
        name = projects.current()
    except (ExportRefused, projects.ProjectRequired, db.DatabaseUnavailable) as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    Path(argv[0]).write_bytes(data)
    print(f"✓ {argv[0]}: the studies of project {name}, {len(data)} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
