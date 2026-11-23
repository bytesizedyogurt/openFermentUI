"""Write bughunt/notes/H12/coverage.jsonl: every item of H12's area, and the service modules it mutated."""
import csv
import json
from pathlib import Path

ROOT = Path("/home/user/openFermentUI")
rows = list(csv.DictReader((ROOT / "bughunt" / "coverage.csv").open()))
mine = [r for r in rows if r["assigned"].split()[0:1] == ["H12"] or "H12" in r["assigned"].split()]

FINDINGS = {
    "core/tests/test_spend.py": ["H12-01", "H12-03"],
    "core/tests/test_engines.py": ["H12-02", "H12-06", "H12-10"],
    "core/tests/test_engine_diagnostics.py": ["H12-02", "H12-10"],
    "core/tests/test_engines_sim.py": ["H12-02"],
    "core/tests/test_train.py": ["H12-02"],
    "core/tests/test_measurements.py": ["H12-02", "H12-12", "H12-13"],
    "core/tests/test_runs.py": ["H12-10"],
    "core/tests/test_key_override.py": ["H12-04", "H12-08"],
    "core/tests/test_llm.py": ["H12-08"],
    "core/tests/test_no_seed.py": ["H12-05"],
    "core/tests/test_boundaries.py": ["H12-06"],
    "core/tests/test_workers.py": ["H12-06"],
    "core/tests/test_proforma_runs.py": ["H12-06", "H12-10"],
    "core/tests/test_ready.py": ["H12-01", "H12-11"],
    "core/tests/test_basis.py": ["H12-13", "H12-14"],
    "core/tests/test_sff_url.py": ["H12-15"],
    "core/tests/test_guidance.py": ["H12-05"],
    "core/tests/test_projects.py": ["H12-04", "H12-09"],
}
NOTES = {
    "core/tests/standins.py": "read whole; the tests restating its values are listed in notes.md and standin-restates.txt",
    "core/tests/fixtures/kept_bases.json": "read; the kept bases test_proforma and test_engines replay",
    "core/tests/fixtures/sim/toy.json": "read; made by standins.sim_fixtures under test:sim, which H12 did not run",
    "core/tests/test_engines_sim.py": "read: sim-marked, its conformance tests assert all eight hold on conforming engines",
    "core/tests/test_proforma_slow.py": "read: slow-marked, outside verify",
    "core/tests/test_proforma_worker.py": "read: sim-marked",
    "core/tests/test_runs_sim.py": "read: sim-marked",
    "core/tests/test_sff_sim.py": "read: sim-marked",
    "core/tests/test_literature_live.py": "executed for its offline tests; the live ones need the network",
}
SIM_ONLY = {"core/tests/test_engines_sim.py", "core/tests/test_proforma_slow.py", "core/tests/test_proforma_worker.py",
            "core/tests/test_runs_sim.py", "core/tests/test_sff_sim.py"}

out = []
for r in mine:
    item = r["item"]
    if item.startswith("core/tests/test_") and item not in SIM_ONLY:
        method, note = "executed", NOTES.get(item, "ran under Python 3.12 and 3.13 and in a network namespace "
                                                   "(pyver.sh, offline.sh); same outcome in all three")
    else:
        method, note = "read", NOTES.get(item, "read")
    if item in ("core/tests/test_spend.py", "core/tests/test_basis.py", "core/tests/test_measurements.py",
                "core/tests/test_request_guard.py", "core/tests/test_key_override.py", "core/tests/test_no_seed.py",
                "core/tests/test_boundaries.py", "core/tests/test_workers.py", "core/tests/test_engines.py",
                "core/tests/test_ready.py", "core/tests/test_sff_url.py"):
        method = "fuzzed"
        note = "the tests mutation testing ran against (mutations/results.jsonl); " + note
    out.append({"kind": r["kind"], "item": item, "method": method, "findings": FINDINGS.get(item, []), "note": note})

# The service modules H12 mutated: their tests' strength, not their own correctness, is H12's area.
MUTATED = {
    "core/openferment_core/basis.py": (["H12-13"], "M01-M10, N15"),
    "core/openferment_core/units.py": ([], "M14-M16, N10: all caught"),
    "core/openferment_core/guard.py": (["H12-04", "H12-08", "H12-09"], "M29-M32"),
    "core/openferment_core/measurements.py": (["H12-12"], "M33-M37, N12"),
    "core/openferment_core/validate.py": ([], "M38-M40: all caught"),
    "core/openferment_core/spend.py": (["H12-01", "H12-03"], "M42-M45, and the nan setting run on the head"),
    "core/openferment_core/llm.py": (["H12-08"], "M25, M28, N01, N02"),
    "core/openferment_core/migrations.py": ([], "M67: caught"),
    "core/openferment_core/project_state.py": ([], "M12, M59-M63, N14: all caught"),
    "core/openferment_core/engine/runs.py": (["H12-10"], "M20-M24"),
    "core/openferment_core/engine/registry.py": ([], "M46-M49: all caught"),
    "core/openferment_core/engine/conform.py": (["H12-02"], "M50-M54"),
    "core/openferment_core/api.py": ([], "M17-M19, M26, M27: all caught"),
    "core/openferment_core/biorepo.py": ([], "M13, M69, M70 (M70 equivalent: RecordStatus holds no 'corrected'), N11"),
    "core/openferment_core/extract.py": ([], "M11: caught"),
    "core/openferment_core/literature/collectors.py": (["H12-15"], "M55-M58, N05-N07"),
    "core/openferment_core/ready.py": (["H12-11"], "M64, M65"),
    "core/openferment_core/import_alpha1.py": ([], "M66: caught"),
    "core/openferment_core/models.py": (["H12-14"], "M68, G2-G4"),
    "core/openferment_core/tools/__init__.py": ([], "M41, N13: caught"),
    "core/openferment_core/proforma.py": (["H12-06"], "N08 (caught), N09"),
}
known = {r["item"] for r in rows}
for item, (found, note) in MUTATED.items():
    if item in known:
        out.append({"kind": "file", "item": item, "method": "fuzzed", "findings": found,
                    "note": f"mutated to test its tests: {note}"})
for item, found, note in (
        (".github/workflows/verify.yml", ["H12-07"], "compared with CLAUDE.md, ADR-011 and PROGRESS.md's CI lines"),
        ("docs/decisions/ADR-011-guards.md", ["H12-02"], "read: the stage list and the negative-test rule"),
        ("package.json", ["H12-07"], "read: the verify stages and the uv run calls"),
        ("scripts/check-plan.mjs", ["H12-14"], "executed with four ranking mutations (G1-G4)"),
        ("scripts/check-secrets.mjs", [], "executed with a key-shaped string planted in src/ and in a service module")):
    if item in known:
        out.append({"kind": "file", "item": item, "method": "executed" if item.startswith("scripts/") else "read",
                    "findings": found, "note": note})
(ROOT / "bughunt" / "notes" / "H12" / "coverage.jsonl").write_text("".join(json.dumps(o) + "\n" for o in out))
print(len(mine), "assigned;", len(out), "lines")
