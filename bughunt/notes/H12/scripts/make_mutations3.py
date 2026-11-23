"""Write bughunt/notes/H12/mutations3.json: H12's third batch."""
import json
from pathlib import Path

T = lambda *fs: [f"tests/{f}" for f in fs]  # noqa: E731
NOT_SIGNAL = ["-k", "not sigterm_ends_the_command"]
M = []


def m(id_, target, file, old, new, tests, why, **kw):
    M.append({"id": id_, "target": target, "file": file, "old": old, "new": new, "tests": tests, "why": why, **kw})


m("N09", "the worker boundary (a service module importing biorefineries)", "openferment_core/proforma.py",
  "    if art.tool == REFERENCE:\n        entry = str(_named(art.inputs, \"flowsheet\")",
  "    if art.tool == REFERENCE:\n        import biorefineries  # noqa: F401  (the retired entries are the library's plants)\n\n"
  "        entry = str(_named(art.inputs, \"flowsheet\")",
  T("test_workers.py", "test_boundaries.py", "test_proforma.py", "test_proforma_runs.py", "test_engines.py") + NOT_SIGNAL,
  "a service module imports biorefineries (and BioSTEAM with it) in the service process")
m("N10", "units.to_canonical", "openferment_core/units.py",
  "    if f[\"categorical\"]:\n        raise UnitError(f\"{field_id} is categorical; it has no unit to convert to\")\n", "",
  T("test_units.py", "test_units_minus.py", "test_biorepo.py", "test_anchor.py", "test_extract.py"),
  "a categorical field's value is converted as a number")
m("N11", "biorepo.write", "openferment_core/biorepo.py",
  "    if _is_gold(decision) and decision.status != \"verified\":", "    if False:",
  T("test_biorepo.py", "test_writes.py", "test_estimates.py", "test_evidence_pool.py"),
  "a gold value on a decision that is not verified is kept")
m("N12", "measurements.unnamed", "openferment_core/measurements.py",
  "    why = reviewer_refusal(name)\n    return f\"was kept under the name {name!r}, which names nobody: {why}\" if why else None",
  "    return None", T("test_measurements.py", "test_basis.py", "test_project_state.py"),
  "a reading kept under a placeholder name is taken as a person's")
m("N13", "tools.numbers_in", "openferment_core/tools/__init__.py",
  "            if k in COUNT_FIELDS and isinstance(v, int) and not isinstance(v, bool) and not path:",
  "            if k in COUNT_FIELDS and isinstance(v, int) and not isinstance(v, bool):",
  T("test_tools.py", "test_module_tools.py", "test_finite_inputs.py", "test_mcp.py", "test_tools_study.py"),
  "a count field nested inside a tool input's object passes as a number")
m("N14", "project_state.put refusal (kinds)", "openferment_core/project_state.py",
  'RECORD_KINDS = ("depositions", "measuredEvidence")', 'RECORD_KINDS = ("depositions",)',
  T("test_estimates.py", "test_project_state.py", "test_measurements.py"), "measured evidence keeps an estimate")
m("N15", "basis.override_of", "openferment_core/basis.py",
  "    if q.basis is not None:\n        raise InputRefused(", "    if False:\n        raise InputRefused(",
  T("test_basis.py", "test_finite_inputs.py", "test_params.py"), "a value carrying a basis of its own is taken")
Path("/home/user/openFermentUI/bughunt/notes/H12/mutations3.json").write_text(json.dumps(M, indent=1))
print([x["id"] for x in M])
