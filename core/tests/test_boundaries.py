"""The package rules (execution prompt §7.2), read from the code by `ast`.

Each package imports, of openFerment's own modules, what its row allows,
and none of the libraries its row forbids, at the top of a module or inside
a function alike. A documented exception names why it stands. A package
that does not exist yet (studies/ arrives with stage 5, postdoc/ with stage
6) is held to its row from the commit that makes it.

    db/          models
    projects/    db, models
    literature/  db, models, units, Sci RAG Kit; never BioSTEAM or llm
    engine/      db, models, the workers client, params, binding; never
                 BioSTEAM, Sci RAG Kit or llm
    studies/     engine, literature, db
    postdoc/     tools, llm, spend, db
    BioSTEAM, thermosteam and biorefineries: the worker's side alone
                 (workers/, flowsheets/, the vendored SFF toolkit and the
                 pureOS functions that run in the worker; test_workers.py
                 names each file)
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parent.parent / "openferment_core"
SIMULATION = {"biosteam", "thermosteam", "biorefineries", "pisces_sff"}

# Of openFerment's own modules, what each package may import, by first name
# under openferment_core (a package's own modules are always its own).
MAY: dict[str, set[str]] = {
    "db": {"models"},
    "projects": {"db", "models"},
    "literature": {"db", "models", "units"},
    "engine": {"db", "models", "workers", "params", "binding"},
    "studies": {"engine", "literature", "db"},
    "postdoc": {"tools", "llm", "spend", "db"},
}
# Libraries and modules each package must never import.
NEVER: dict[str, set[str]] = {
    "literature": SIMULATION | {"openferment_core.llm"},
    "engine": SIMULATION | {"sci_rag", "openferment_core.llm"},
    "db": SIMULATION | {"sci_rag", "openferment_core.llm"},
    "projects": SIMULATION | {"sci_rag", "openferment_core.llm"},
}
# The engine reaches the worker through its client, never a module of the
# worker itself (which imports BioSTEAM).
WORKER_SIDE = {"workers.proforma_worker", "workers.library_plants", "workers.sff_toolkit", "workers.geneos_worker"}

EXCEPTIONS: dict[tuple[str, str], str] = {
    ("literature", "projects"): "every read and write of a project's documents is scoped to the current project (ADR-005)",
    ("literature", "migrations"): "the retrieval report (literature/report.py) migrates a disposable database of its own",
    ("engine", "artifacts"): "a run's computation is kept as an artifact, replayable, with the existing semantics (§7.4)",
    ("engine", "basis"): "provenance and origins are computed by the basis rules alone (ADR-006)",
    ("engine", "flowsheets"): "the package-test reader in flowsheets/shelf.py, which imports no BioSTEAM (§8.4: "
                              "the regression check reads the package's own test by ast)",
    ("engine", "projects"): "a run and a flowsheet record belong to the current project (ADR-005)",
}


def _imports(path: Path) -> list[tuple[int, str]]:
    """Every module a file imports, as an absolute dotted name, with its line."""
    parts = path.relative_to(PACKAGE.parent).with_suffix("").parts
    here = list(parts[:-1]) if path.name != "__init__.py" else list(parts[:-1])
    out = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            out += [(node.lineno, a.name) for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = here[: len(here) - (node.level - 1)] if node.level > 1 else here
                if node.module:
                    out.append((node.lineno, ".".join([*base, node.module])))
                else:
                    out += [(node.lineno, ".".join([*base, a.name])) for a in node.names]
            elif node.module:
                out.append((node.lineno, node.module))
    return out


def _files(package: str) -> list[Path]:
    root = PACKAGE / package
    return sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts) if root.is_dir() else []


def test_the_reader_resolves_relative_imports_as_python_does():
    found = dict((name, line) for line, name in _imports(PACKAGE / "engine" / "runs.py"))
    assert "openferment_core.basis" in found and "openferment_core.engine.library" in found
    assert "openferment_core.workers" in found and "sqlalchemy" not in found


@pytest.mark.parametrize("package", sorted(MAY))
def test_each_package_imports_what_its_row_allows(package):
    wrong = []
    for path in _files(package):
        for line, name in _imports(path):
            if not name.startswith("openferment_core."):
                continue
            first = name.split(".")[1]
            if first == package or first in MAY[package] or (package, first) in EXCEPTIONS:
                if package == "engine" and ".".join(name.split(".")[1:3]) in WORKER_SIDE:
                    wrong.append(f"{path.relative_to(PACKAGE)}:{line} imports {name}, the worker's own side")
                continue
            wrong.append(f"{path.relative_to(PACKAGE)}:{line} imports {name}")
    assert wrong == [], "§7.2: " + "; ".join(wrong)


@pytest.mark.parametrize("package", sorted(NEVER))
def test_no_package_imports_what_its_row_forbids(package):
    wrong = [f"{path.relative_to(PACKAGE)}:{line} imports {name}"
             for path in _files(package) for line, name in _imports(path)
             if name.split(".")[0] in NEVER[package] or name in NEVER[package]]
    assert wrong == [], "§7.2: " + "; ".join(wrong)


def test_every_exception_names_a_package_with_a_row_and_is_still_needed():
    used = {(pkg, name.split(".")[1]) for pkg in MAY for path in _files(pkg) for _, name in _imports(path)
            if name.startswith("openferment_core.")}
    for (pkg, first), why in EXCEPTIONS.items():
        assert pkg in MAY and why.strip()
        assert (pkg, first) in used, f"the exception {pkg} → {first} is no longer used: remove it"
