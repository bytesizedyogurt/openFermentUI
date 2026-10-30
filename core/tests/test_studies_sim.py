"""Studies in the real worker (studies/; execution prompt §9.1 step 5).

Marked `sim`. openFerment's cellulosic ethanol flowsheet on the library's
own defaults, and a scenario on it with one person's assumption and one
model's estimate, run as engine runs and compared: the comparison holds the
price and the flowsheet's outputs in their units with the scenario's change
from the base, each value the scenario set with its origin beside the
library's default, and it is `assumed`.
"""
from __future__ import annotations

import pytest

from openferment_core import proforma
from openferment_core.engine import runs
from openferment_core.models import ComparisonCreate, Origin, Quantity, ScenarioCreate, ScenarioValue
from openferment_core.studies import comparisons, scenarios

pytestmark = pytest.mark.sim

FLOWSHEET = "cellulosic_ethanol_v0"
MODEL = "claude-opus-5-5"


@pytest.fixture(scope="module")
def warm():
    proforma.start(background=False)
    assert proforma.status()["status"] == "ready", proforma.status()


def study():
    base = runs.run(FLOWSHEET, by="Ada Moreno").run
    made = scenarios.make(ScenarioCreate(title="Dearer stover, two-day co-fermentation", plant=FLOWSHEET, by="Ada Moreno",
                                         values=[
        ScenarioValue(key="stream.cornstover.price", quantity=Quantity(value=0.08, unit="USD/kg", origin=Origin(
            kind="person-assumption", by="Ada Moreno", at="2026-10-30", note="a delivered price quoted to us"))),
        ScenarioValue(key="unit.R303.tau_cofermentation", quantity=Quantity(value=48.0, unit="hr", origin=Origin(
            kind="model-estimate", by=MODEL, at="2026-10-30T12:00:00Z", note="two days, as such plants are often run"))),
    ]))
    return base, made, scenarios.run(made.id, by="Ada Moreno")


def test_a_scenario_on_the_flowsheet_runs_assumed_and_compares_with_its_base(warm):
    base, made, rep = study()
    assert rep.run.provenance == "assumed" and rep.run.scenarioId == made.id and rep.run.sff.valid
    compared = comparisons.make(ComparisonCreate(title="The scenario against the flowsheet as built",
                                                 runIds=[base.id, rep.run.id], by="Ada Moreno"))
    out = compared.artifact.output
    assert compared.comparison.provenance == "assumed"
    rows = {r["key"]: r for r in out["rows"]}
    mesp = rows["outputs.mespUsdPerKg"]
    assert mesp["unit"] == "USD/kg" and mesp["values"][1] > mesp["values"][0] and mesp["change"][1] > 0
    assert rows["price.solvedPrice"]["unit"] == "USD/kg" and rows["price.TCI"]["unit"] == "USD"
    values = {v["key"]: v["values"] for v in out["values"]}
    stover = values["stream.cornstover.price"]
    assert [c["origin"] for c in stover] == ["library-default", "person-assumption"] and stover[1]["value"] == 0.08
    defaults = runs.report(base.id).artifact.output["libraryDefaults"]
    assert stover[0]["value"] == defaults["stream.cornstover.price"] and stover[0]["unit"] == "USD/kg"
    assert [c["origin"] for c in values["unit.R303.tau_cofermentation"]] == ["library-default", "model-estimate"]
