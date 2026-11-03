"""The `biosteam` engine behind the contract (docs/api/engines.md; ADR-015),
on the real Proforma worker: registered by core/pyproject.toml's own entry
point, its run the adapter's own row, a value set as a quantity the adapter's
override, its SFF file answered as the flowsheet record, and the eight
conformance checks holding on a plant.
"""
from __future__ import annotations

import pytest

from openferment_core import proforma
from openferment_core.engine import conform, registry, runs
from openferment_core.models import EngineInput, Origin, Quantity, SFFFlowsheet

pytestmark = pytest.mark.sim

BY = "Ada Moreno"
ENTRY = "openferment_core.engine.biosteam:ENGINE"


@pytest.fixture(scope="module")
def biosteam():
    proforma.start(background=False)
    assert proforma.status()["status"] == "ready", proforma.status()
    registry.reset()
    yield registry.get("biosteam")
    registry.reset()


def test_the_cores_own_entry_point_registers_it_and_it_keeps_the_contract(biosteam):
    assert registry.found()["biosteam"].entry == ENTRY
    found = conform.checks(biosteam, by="conformance test", things=["cornstover"], entry=ENTRY)
    assert [c.number for c in found] == list(range(1, 9))
    assert all(c.ok for c in found), [(c.number, c.said) for c in found if not c.ok]


def test_a_run_through_the_engine_is_the_adapters_own_row_and_its_file_the_record(biosteam):
    run = biosteam.run("cornstover", None, [], BY)
    assert (run.engine, run.status, run.by) == ("biosteam", "done", BY)
    assert runs.run("cornstover", None, [], by=BY).run.id == run.id
    record = biosteam.export_sff(run)
    assert isinstance(record, SFFFlowsheet) and record.id == run.sff.recordId and record.validation.valid
    assert record.runArtifactId == run.artifactId


def test_a_value_set_as_a_quantity_is_the_adapters_override_and_makes_the_run_assumed(biosteam):
    p = {x.key: x for x in biosteam.parameters("cornstover", None)}["stream.cornstover.price"]
    assert p.origin.kind == "library-default" and p.origin.ref and p.boundsReason.strip()
    q = Quantity(value=p.value * 1.5, unit=p.unit,
                 origin=Origin(kind="person-assumption", by=BY, note="half again the package's own"))
    run = biosteam.run("cornstover", None, [EngineInput(name=p.key, quantity=q)], BY)
    assert run.provenance == "assumed"
    (given,) = [i for i in run.inputs if i.name == p.key]
    assert given.quantity.value == pytest.approx(p.value * 1.5) and given.quantity.origin.kind == "person-assumption"
    assert given.quantity.origin.by == BY
    at_default = biosteam.run("cornstover", None, [], BY)
    assert run.outputs["price"]["solvedPrice"] > at_default.outputs["price"]["solvedPrice"]


def test_a_plant_that_takes_a_configuration_runs_in_its_default_when_asked_with_none(biosteam):
    (cane,) = [t for t in biosteam.things() if t.id == "cane"]
    assert cane.configurations and cane.defaultConfiguration in cane.configurations
    run = biosteam.run("cane", None, [], BY)
    assert run.status == "done" and run.configuration == cane.defaultConfiguration
