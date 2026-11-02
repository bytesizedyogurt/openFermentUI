"""openFerment's cellulosic ethanol flowsheet as an SFF recipe (ADR-003,
ADR-004; execution prompt §8.3, §8.4), offline.

Read without BioSTEAM: the recipe directory has the SFF toolkit's
model-directory shape and its declarations; its `load.py` imports nothing of
openFerment, so the toolkit's harness can run it with BioSTEAM and
biorefineries alone; its environment is the one core/uv.lock pins; its
authored metadata names only the toolkit exporter's arguments; and no
number of the process is typed in the flowsheet or its recipe. The plant
itself is the `sim` tests in test_cellulosic_sim.py.
"""
from __future__ import annotations

import ast
import inspect
from importlib.metadata import version
from pathlib import Path

import yaml

from openferment_core.flowsheets import recipes

CORE = Path(__file__).resolve().parent.parent
FLOWSHEET = CORE / "openferment_core" / "flowsheets" / "cellulosic_ethanol_v0.py"
RECIPE = CORE / "openferment_core" / "flowsheets" / "recipes" / "cellulosic_ethanol_v0"


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def _declared(path: Path) -> dict[str, object]:
    out = {}
    for node in _tree(path).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                out[node.targets[0].id] = ast.literal_eval(node.value)
            except ValueError:
                pass
    return out


def test_the_recipe_has_the_toolkits_model_directory_shape():
    assert {p.name for p in RECIPE.iterdir() if p.suffix in (".py", ".yaml")} >= {
        "load.py", "environment.yaml", "extended_metadata.yaml"}
    said = _declared(RECIPE / "load.py")
    assert said["SIMULATOR"] == said["SIMULATOR_PACKAGE"] == "biosteam"
    assert said["FLOWSHEET_MODEL_PACKAGE"] == "biorefineries" and said["MODEL_NAME"] == "cellulosic_ethanol_v0"
    assert said["PACKAGE_DEFAULT"] == ("dilute acid", "IB")
    assert set(said["PRETREATMENTS"]) == {"dilute acid", "hot water", "AFEX", "alkaline"}
    assert said["FERMENTATIONS"] == ("IB", "SCF"), "the package's SSCF raises 'not yet implemented'"
    names = {n.name for n in _tree(RECIPE / "load.py").body if isinstance(n, ast.FunctionDef)}
    assert {"load", "create_system"} <= names


def test_the_recipe_imports_nothing_of_openferment():
    for node in ast.walk(_tree(RECIPE / "load.py")):
        if isinstance(node, ast.ImportFrom):
            assert node.level == 0 and not (node.module or "").startswith("openferment_core"), ast.unparse(node)
        if isinstance(node, ast.Import):
            assert not any(a.name.startswith("openferment_core") for a in node.names), ast.unparse(node)


def test_the_environment_is_the_one_the_lock_pins():
    held = (RECIPE / "environment.yaml").read_text(encoding="utf-8")
    assert held == recipes.environment_text("cellulosic_ethanol_v0"), \
        "regenerate it: python -m openferment_core.flowsheets.recipes environment"
    pip = yaml.safe_load(held)["dependencies"][-1]["pip"]
    for dist in ("biosteam", "thermosteam", "biorefineries"):
        assert f"{dist}=={version(dist)}" in pip


def test_the_authored_metadata_names_only_the_toolkit_exporters_arguments():
    said = yaml.safe_load((RECIPE / "extended_metadata.yaml").read_text(encoding="utf-8"))
    assert set(said) <= {"source_doi", "process_title", "flowsheet_designers", "microorganisms"}
    assert said["microorganisms"] == [{"name": "Zymomonas mobilis", "label": "ethanologen"}]
    # The exporter the toolkit's runner forwards these to takes each by name.
    exporter = (CORE / "vendor" / "pisces_sff" / "export" / "_export.py").read_text(encoding="utf-8")
    fn = next(n for n in ast.parse(exporter).body
              if isinstance(n, ast.FunctionDef) and n.name == "export_biosteam_flowsheet_sff_0_2_4")
    assert set(said) <= {a.arg for a in fn.args.args}


def _numbers(path: Path) -> list[tuple[int, object]]:
    """Every numeric literal in a file, but in a module-level assignment to a
    named precision (a tolerance) and the zero or one of a count or a share."""
    tree = _tree(path)
    named = set()
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id.endswith("_TOLERANCE")
                                                for t in node.targets):
            named |= {id(n) for n in ast.walk(node.value)}
    return [(n.lineno, n.value) for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool)
            and id(n) not in named and n.value not in (0, 1)]


def test_no_number_of_the_process_is_typed_in_the_flowsheet_or_its_recipe():
    assert _numbers(FLOWSHEET) == []
    assert _numbers(RECIPE / "load.py") == []


def test_the_configurations_are_every_pretreatment_with_every_fermentation_kind():
    said = _declared(RECIPE / "load.py")
    expected = [f"{p}, {f}" for p in said["PRETREATMENTS"] for f in said["FERMENTATIONS"]]
    source = FLOWSHEET.read_text(encoding="utf-8")
    assert 'CONFIGURATIONS = [f"{p}, {f}" for p in _RECIPE.PRETREATMENTS for f in _RECIPE.FERMENTATIONS]' in source
    assert len(expected) == 8 and expected[0] == "dilute acid, IB"


def test_the_generator_pins_the_closure_of_the_simulator_and_reads_markers():
    pinned = dict(recipes.pins())
    assert {"biosteam", "biorefineries", "thermosteam", "numpy", "scipy", "jsonschema", "pyyaml"} <= set(pinned)
    assert inspect.signature(recipes.environment_text).parameters["name"]
    assert recipes._applies(None) and recipes._applies("sys_platform == 'linux'")
    assert not recipes._applies("sys_platform == 'win32'")
