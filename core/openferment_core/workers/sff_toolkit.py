"""The PISCES SFF toolkit, called in the Proforma worker (ADR-003; execution
prompt §8.3).

The toolkit is vendored unmodified at core/vendor/pisces_sff/ (commit
e236e32, MIT, schema 0.2.4). Importing it imports BioSTEAM
(`export/_export.py` does at its top), so it is imported here, in a worker
module, and nowhere in the service: this module puts core/vendor on the
worker's path first. The Proforma worker registers the three ops:

    sff_export    a plant's base case written as an SFF file at a path the
                  service names, then validated, scored and tagged
                  (proforma_worker.py builds the plant; `export_checked`
                  writes and checks it)
    sff_validate  a file checked against the schema and every semantic
                  check of the toolkit's catalogue (validate/sff_checks.md)
    sff_score     a file's completeness report, its plain-text rendering,
                  and the tags it earns (the conda harness never runs)

Every answer is the toolkit's own, turned into JSON: a check result's id,
severity, status, message and path; a criterion's score and what it found
missing. Nothing here judges a file; the service stores what the toolkit
said beside the file (engine/sff.py).
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from importlib.metadata import version
from pathlib import Path
from typing import Any

VENDOR = Path(__file__).resolve().parents[2] / "vendor"
if str(VENDOR) not in sys.path:
    sys.path.insert(0, str(VENDOR))

import pisces_sff  # noqa: E402  (after the path above)
import thermosteam as tmo  # noqa: E402  (BioSTEAM's property engine, which the toolkit imports)
from pisces_sff.export import _export as _exporter  # noqa: E402

# The schema the toolkit validates against, read from its own schema file.
SCHEMA_VERSION: str = pisces_sff.__version__
# The words a file's own `metadata` carries for what openFerment adds
# (docs/api/sff.md).
OPENFERMENT_KEY = "openferment"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validation(path: str | Path) -> dict[str, Any]:
    """The toolkit's verdict on one file: valid unless the schema gate or
    an error-severity check fails; every result counted by severity and
    status; each result that did not pass listed whole."""
    valid, results = pisces_sff.validate_flowsheet_against_SFF(str(path))
    counted = Counter((r.severity, r.status) for r in results)
    summary: dict[str, dict[str, int]] = {}
    for (severity, status), n in sorted(counted.items()):
        summary.setdefault(severity, {})[status] = n
    findings = [
        {"checkId": r.check_id, "severity": r.severity, "status": r.status, "message": r.message, "path": r.path}
        for r in results if r.status != "pass"
    ]
    return {"valid": bool(valid), "schemaVersion": SCHEMA_VERSION, "summary": summary, "findings": findings}


def completeness(path: str | Path) -> dict[str, Any]:
    """The toolkit's completeness report: the weighted scores, each
    criterion as it scored, the re-execution route it found, and the
    report as the toolkit renders it."""
    report = pisces_sff.score_flowsheet_completeness(str(path))
    return {
        "score": report.score,
        "representableScore": report.representable_score,
        "categories": dict(report.category_scores),
        "criticalities": dict(report.criticality_scores),
        "criteria": [
            {"id": c.criterion_id, "category": c.category, "criticality": c.criticality, "weight": c.weight,
             "representable": bool(c.representable), "status": c.status, "score": c.score, "message": c.message,
             "missing": list(c.missing)}
            for c in report.criteria
        ],
        "sffVersion": report.sff_version,
        "recipe": dict(report.recipe),
        "report": pisces_sff.format_completeness_report(report),
    }


def tags(path: str | Path) -> dict[str, Any]:
    """Each tag the toolkit knows: whether the file earns it, declares it,
    and what blocks it. The reproducible tag is left unevaluated: earning it
    runs the toolkit's conda harness, which openFerment does not run."""
    verdict = pisces_sff.evaluate_sff_tags(str(path))
    return {tag: {"earned": v["earned"], "declared": bool(v["declared"]), "blocking": [str(b) for b in v["blocking"]]}
            for tag, v in verdict.items()}


def checked(path: str | Path) -> dict[str, Any]:
    """Everything the service stores beside a file: its hash and size, the
    validation, the completeness report and the tags."""
    p = Path(path)
    return {
        "path": str(p),
        "sha256": _sha256(p),
        "bytes": p.stat().st_size,
        "validation": validation(p),
        "completeness": completeness(p),
        "tags": tags(p),
        "toolkit": f"pisces_sff {SCHEMA_VERSION}",
    }


# What the toolkit's JSON writer is taught while openFerment exports: a
# reaction in thermosteam's own words, a stream by its id (`_writes_objects`).
REACTIONS = (tmo.Reaction, tmo.ReactionSet, tmo.ReactionItem)


@contextmanager
def _writes_objects() -> Iterator[None]:
    """The toolkit's JSON writer (`export/_export.py`, `_json_default`) fails
    closed on a design input whose value is a thermosteam object, and its
    design-spec registry names some: NRELEthanolFermentation's
    `fermentation_reaction` and `cell_growth_reaction`, MassBalance's
    stream lists (measured at e236e32 on the sugarcane, lipidcane, oilcane
    and cane plants, whose exports it refused). While openFerment exports,
    such a value is written in words, a reaction as thermosteam writes it
    (its equation, reactant, conversion and basis) and a stream as its id;
    anything else still fails closed. The vendored files are unchanged; the
    toolkit's own writer is put back after. To be offered upstream."""
    original = _exporter._json_default

    def default(value: Any) -> Any:
        try:
            return original(value)
        except TypeError:
            if isinstance(value, tmo.Stream):
                return value.ID
            if isinstance(value, REACTIONS):
                return repr(value)
            raise

    _exporter._json_default = default
    try:
        yield
    finally:
        _exporter._json_default = original


def export_checked(system: Any, tea: Any, path: str | Path, *, metadata: dict[str, Any] | None = None,
                   process_title: str | None = None) -> dict[str, Any]:
    """Write the system's present state as an SFF file at `path` (the
    toolkit's exporter for the schema it ships, its writer taught to write
    a reaction and a stream in words), add openFerment's block to the file's
    `metadata` when one is given, and check the file as written."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with _writes_objects():
        pisces_sff.export_biosteam_flowsheet(system, str(p), SCHEMA_VERSION, tea=tea, process_title=process_title)
    if metadata:
        doc = json.loads(p.read_text(encoding="utf-8"))
        doc["metadata"][OPENFERMENT_KEY] = metadata
        p.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    out = checked(p)
    out["simulator"] = f"BioSTEAM {version('biosteam')}"
    return out


def design_spec_registry() -> dict[str, Any]:
    """The toolkit's design-spec registry (`export/design_specs/biosteam.yaml`):
    each BioSTEAM unit class's design inputs and the accessors that read them.
    The library plant runner reads a unit's parameters through it."""
    return pisces_sff.load_design_spec_registry()


def _path(args: dict[str, Any]) -> Path:
    p = Path(str(args.get("path") or ""))
    if not p.is_absolute() or not p.is_file():
        raise FileNotFoundError(f"there is no SFF file at {p}: the service names an absolute path to a file it wrote")
    return p


def op_validate(args: dict[str, Any]) -> dict[str, Any]:
    p = _path(args)
    return {"path": str(p), "sha256": _sha256(p), **validation(p)}


def op_score(args: dict[str, Any]) -> dict[str, Any]:
    p = _path(args)
    return {"path": str(p), "sha256": _sha256(p), "completeness": completeness(p), "tags": tags(p)}
