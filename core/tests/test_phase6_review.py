"""What the review of Phase 6 found (OF-BLD-014 §6.R), on the service's side.
Each test failed before its fix."""
from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from openferment_core import geneos, geneos_models as shelf, intake, tools

CORE = Path(__file__).resolve().parents[1]


# R1 — the toy network is a stand-in: refused through the API and the tool,
# and modeled (demo) wherever a fixture uses it.
def test_the_public_paths_refuse_the_toy():
    with pytest.raises(geneos.GeneosUnavailable, match="no model toy"):
        geneos.ceiling("toy", "phb", "glucose", keep=False)
    r = tools.run("yield_ceiling", {"modelId": "toy", "product": "phb", "substrate": "glucose"})
    assert r.error and "no model toy" in r.error and r.evidence == []


def test_the_toy_in_a_fixture_is_modeled_never_computed():
    r = geneos.ceiling("toy", "phb", "glucose", keep=False, allow_toy=True)
    assert r.evidence.provenance == "demo"
    assert next(i for i in r.evidence.basis.inputs if i.name == "model").source.kind == "assumption"


# R2 — a mix is of two different sugars.
def test_a_mix_of_a_sugar_with_itself_is_refused():
    with pytest.raises(geneos.GeneosUnavailable, match="two different sugars"):
        geneos.mix("iJO1366", "phb", "glucose", "glucose", keep=False)


# R3 — the hash is checked where the file is used, not only where it is fetched.
def test_a_changed_model_file_is_not_used(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    f = shelf.SHELF["RehMBEL1391"].fetched
    f.local.parent.mkdir(parents=True)
    f.local.write_text("<sbml>not the pinned file</sbml>", encoding="utf-8")
    why = shelf.available(shelf.SHELF["RehMBEL1391"])
    assert why and "does not match" in why
    with pytest.raises(geneos.GeneosUnavailable, match="does not match"):
        geneos.model_args("RehMBEL1391")


def test_fetch_on_a_present_file_checks_it_and_skips_git(monkeypatch, tmp_path):
    monkeypatch.setattr(intake, "DATA_DIR", tmp_path)
    model = shelf.SHELF["RehMBEL1391"]
    model.fetched.local.parent.mkdir(parents=True)
    model.fetched.local.write_text("changed", encoding="utf-8")
    calls = []

    def git(cmd, check):
        calls.append(cmd)
        if "checkout" in cmd:
            model.fetched.local.write_text("still not it", encoding="utf-8")

    with pytest.raises(geneos.GeneosUnavailable, match="stop condition"):
        geneos.fetch(model, run=git)
    assert any("checkout" in c for c in calls), "a present file that does not match is fetched again"


# R9 — the sugar-mix line carries its basis.
def test_a_mix_carries_evidence_with_its_basis():
    r = geneos.mix("iJO1366", "phb", "glucose", "xylose", keep=False)
    assert r.evidence is not None and r.evidence.figure == "mix"
    assert {i.name for i in r.evidence.basis.inputs} >= {"model", "substrate a", "substrate b", "uptake"}
    assert r.evidence.value == pytest.approx(min(p["gPerG"] for p in r.output["points"]))


# R11 — the licence ledger and the shelf pin the same file.
def test_the_licence_ledger_pins_the_file_the_shelf_fetches():
    ledger = tomllib.loads((CORE / "licences.toml").read_text(encoding="utf-8"))["data"]["RehMBEL1391"]
    f = shelf.SHELF["RehMBEL1391"].fetched
    assert (ledger["sha256"], ledger["revision"], ledger["licence"]) == (f.sha256, f.commit, f.licence)
    assert f.path in ledger["source"] and Path(f.repository).name in ledger["source"]
