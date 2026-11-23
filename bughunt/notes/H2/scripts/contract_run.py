"""Keep runs of the contract's own sample engine (a WorkerEngine over workers/sample_worker.py) in a test database's
project, through engine/runs.run_engine, and print each row as runs.md's contract-engine section reads it.

    OPENFERMENT_DATABASE_URL=postgresql://.../bh_h2_<x> python -I contract_run.py PROJECT

The sample engine computes nothing (placeholders in placeholder units); nothing here is science.
"""
import json
import sys

sys.path.insert(0, "/home/user/openFermentUI/core")
from openferment_core import artifacts, projects  # noqa: E402
from openferment_core.engine import EngineRefused, runs  # noqa: E402
from openferment_core.engine.sample import SAMPLE  # noqa: E402
from openferment_core.models import EngineInput  # noqa: E402

sys.path.insert(0, "/home/user/openFermentUI/bughunt/notes/H2/scripts")
from check_run import artifact_id  # noqa: E402


def show(rep):
    r = rep.run
    print(json.dumps({"id": r.id, "engine": r.engine, "plant": r.plant, "configuration": r.configuration,
                      "tool": r.tool, "toolVersion": r.toolVersion, "status": r.status, "provenance": r.provenance,
                      "versions": r.versions, "sff": r.sff.model_dump() if r.sff else None, "sffRefused": r.sffRefused,
                      "diagnostics": [d.model_dump() for d in r.diagnostics], "by": r.by,
                      "inputs": [(i.name, i.quantity.value, i.quantity.unit, i.quantity.origin.kind) for i in r.inputs],
                      "values": (r.outputs or {}).get("values")}, indent=1, ensure_ascii=False))
    if rep.artifact is not None:
        a = rep.artifact
        print("  id == artifact id of basis:", artifact_id(a.tool, a.toolVersion, [i.model_dump(mode="json") for i in a.inputs], a.seed) == r.id)


def main(project):
    with projects.using(project):
        value = EngineInput.model_validate({"name": "a-parameter", "quantity": {"value": 2.5, "unit": "placeholder-unit", "origin": {
            "kind": "person-assumption", "by": "Hunter H2", "at": "2026-11-10", "note": "a placeholder"}}})
        show(runs.run_engine(SAMPLE, "placeholder", None, [value], by="Hunter H2"))
        again = runs.run_engine(SAMPLE, "placeholder", None, [value], by="Someone Else")
        print("  asked again: same row", again.run.id, "by", again.run.by)
        show(runs.run_engine(SAMPLE, "placeholder-configured", None, [], by="Hunter H2"))
        try:
            runs.run_engine(SAMPLE, "refuses", None, [], by="Hunter H2")
        except (EngineRefused, runs.RunRefused) as e:
            print("  refused:", type(e).__name__, e, getattr(e, "run_id", None))
        rep = runs.run_engine(SAMPLE, "placeholder", None, [value], by="Hunter H2")
        print("  replay:", artifacts.replay(rep.run.artifactId).model_dump(include={"identical", "withinTolerance", "tolerance"}))


if __name__ == "__main__":
    main(sys.argv[1])
