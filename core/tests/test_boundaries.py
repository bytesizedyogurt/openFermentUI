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
    # models.py is the schema of every row and request (ADR-007): the rows
    # that leave it out read it too.
    "studies": {"engine", "literature", "db", "models"},
    "postdoc": {"tools", "llm", "spend", "db", "models"},
}
# Libraries and modules each package must never import.
NEVER: dict[str, set[str]] = {
    "literature": SIMULATION | {"openferment_core.llm"},
    "engine": SIMULATION | {"sci_rag", "openferment_core.llm"},
    "db": SIMULATION | {"sci_rag", "openferment_core.llm"},
    "projects": SIMULATION | {"sci_rag", "openferment_core.llm"},
    "studies": SIMULATION | {"openferment_core.llm"},
}
# The engine reaches the worker through its client, never a module of the
# worker itself (which imports BioSTEAM).
WORKER_SIDE = {"workers.proforma_worker", "workers.library_plants", "workers.sff_toolkit", "workers.geneos_worker"}

EXCEPTIONS: dict[tuple[str, str], str] = {
    ("literature", "projects"): "every read and write of a project's documents is scoped to the current project (ADR-005)",
    ("literature", "migrations"): "the retrieval report (literature/report.py) migrates a disposable database of its own",
    ("engine", "artifacts"): "a run's computation is kept as an artifact, replayable, with the existing semantics (§7.4)",
    ("engine", "basis"): "provenance and origins are computed by the basis rules alone (ADR-006), and a value that "
                         "is a deposition's reading is looked up through basis.resolved, the one door (measurements.py)",
    ("engine", "flowsheets"): "the package-test reader in flowsheets/shelf.py, which imports no BioSTEAM (§8.4: "
                              "the regression check reads the package's own test by ast)",
    ("engine", "projects"): "a run and a flowsheet record belong to the current project (ADR-005)",
    ("engine", "events"): "a run is a job the project's event stream says as it happens (§7.3 item 2)",
    ("engine", "api"): "conformance check 1 (engine/conform.py) sends a bare number to the service's own run route "
                       "and sees it refused before the engine is reached (docs/api/engines.md)",
    ("engine", "tools"): "conformance check 1 sends a bare number through the engine_run tool as well, the second "
                         "door a number enters by (docs/api/engines.md)",
    ("studies", "projects"): "a scenario, a comparison and a runbook belong to the current project (ADR-005)",
    ("studies", "artifacts"): "a comparison is computed as an artifact over the runs' artifacts, replayable (§7.4)",
    ("studies", "basis"): "a value's origin and a comparison's provenance are the basis rules' (ADR-006), and a value "
                          "that is a deposition's reading is looked up through basis.resolved, the one door "
                          "(measurements.py)",
    ("studies", "project_state"): "a study's runbook is a row of the project's runbooks beside a person's, kept and "
                                  "its lock audited by the store the runbook page writes to",
    ("studies", "runbook_lock"): "a runbook is locked under the digest the browser writes (src/engine/lock.ts)",
    ("postdoc", "projects"): "a conversation and its turns belong to the current project (ADR-005)",
    ("postdoc", "audit"): "a conversation begun is audited as every row a person keeps is",
}


def _is_module(root: Path, dotted: str) -> bool:
    """Whether `dotted` names a module file or a package standing under `root`."""
    where = root.joinpath(*dotted.split("."))
    return where.with_suffix(".py").is_file() or (where / "__init__.py").is_file()


def _imports(path: Path, root: Path = PACKAGE.parent) -> list[tuple[int, str]]:
    """Every module a file imports, as an absolute dotted name, with its line;
    `root` is the directory its top-level package stands in. `from X import y`
    names X, and X.y as well when y is a module file or a package under X, as
    Python imports it."""
    parts = path.relative_to(root).with_suffix("").parts
    here = list(parts[:-1]) if path.name != "__init__.py" else list(parts[:-1])
    out = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            out += [(node.lineno, a.name) for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = here[: len(here) - (node.level - 1)] if node.level > 1 else here
                if node.module:
                    module = ".".join([*base, node.module])
                    out.append((node.lineno, module))
                    out += [(node.lineno, f"{module}.{a.name}") for a in node.names if _is_module(root, f"{module}.{a.name}")]
                else:
                    out += [(node.lineno, ".".join([*base, a.name])) for a in node.names]
            elif node.module:
                out.append((node.lineno, node.module))
                out += [(node.lineno, f"{node.module}.{a.name}") for a in node.names
                        if _is_module(root, f"{node.module}.{a.name}")]
    return out


def _files(package: str) -> list[Path]:
    root = PACKAGE / package
    return sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts) if root.is_dir() else []


def test_the_reader_resolves_relative_imports_as_python_does():
    found = dict((name, line) for line, name in _imports(PACKAGE / "engine" / "runs.py"))
    assert "openferment_core.basis" in found and "openferment_core.engine.library" in found
    assert "openferment_core.workers" in found and "sqlalchemy" not in found
    # `from ..db import models as t` imports the module db/models.py; `from ..workers import WorkerError` a name.
    assert "openferment_core.db.models" in found and "openferment_core.workers.WorkerError" not in found


def test_the_reader_names_a_worker_module_imported_from_its_package(tmp_path):
    """`from ..workers import proforma_worker` imports the worker's own module,
    which the engine's row forbids (WORKER_SIDE), relative or absolute."""
    engine = tmp_path / "openferment_core" / "engine"
    workers = tmp_path / "openferment_core" / "workers"
    for d in (engine, workers):
        d.mkdir(parents=True)
        (d / "__init__.py").write_text("")
    (workers / "proforma_worker.py").write_text("")
    (engine / "relative.py").write_text("from ..workers import proforma_worker, WorkerError\n")
    (engine / "absolute.py").write_text("from openferment_core.workers import proforma_worker\n")
    for name in ("relative", "absolute"):
        found = [n for _, n in _imports(engine / f"{name}.py", tmp_path)]
        assert "openferment_core.workers.proforma_worker" in found and "openferment_core.workers.WorkerError" not in found
        assert any(".".join(n.split(".")[1:3]) in WORKER_SIDE for n in found), name


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


# ── every registered engine (docs/api/engines.md, check 6, as a grep) ───


def heavy_outside_the_worker(root: Path, package: str, worker: str | None, heavy: set[str]) -> list[str]:
    """Each module of `package` (standing in `root`), beside its worker module
    and the modules below it, that imports the worker or a heavy module (a
    heavy name covering the module and every module below it)."""
    base = root / package
    files = sorted(base.rglob("*.py")) if base.is_dir() else [root / f"{package}.py"]
    inside = (lambda m: bool(worker) and (m == worker or m.startswith(worker + ".")))
    wrong = []
    for path in files:
        module = ".".join(path.relative_to(root).with_suffix("").parts).removesuffix(".__init__")
        if inside(module):
            continue
        for line, name in _imports(path, root):
            if inside(name) or any(name == h or name.startswith(h + ".") for h in heavy):
                wrong.append(f"{path.relative_to(root)}:{line} imports {name}")
    return wrong


def test_every_registered_engine_imports_what_it_computes_with_in_its_worker_alone():
    """The core's own engines keep their worker on the worker's side this
    package map and test_workers' grep hold; any other package registered here
    is read whole, and no module of it but its worker imports the worker or a
    heavy module it declares. Read inside the test, so the package map
    (`pnpm gen:components`) never depends on what is installed."""
    import importlib.util

    from openferment_core.engine import registry
    from openferment_core.workers import WORKER_LIBRARIES

    registry.reset()
    try:
        held = []
        for name, f in sorted(registry.found().items()):
            if f.engine is None:
                continue
            top = f.entry.split(":", 1)[0].split(".")[0]
            worker = f.engine.worker
            if top == "openferment_core":
                assert worker is None or worker.removeprefix("openferment_core.") in WORKER_SIDE, (name, worker)
                assert set(f.engine.heavy) <= set(WORKER_LIBRARIES), (name, f.engine.heavy)
            else:
                spec = importlib.util.find_spec(top)
                where = spec.submodule_search_locations
                root = Path(list(where)[0]).parent if where else Path(spec.origin).parent
                kept_out = set(f.engine.heavy) | set(WORKER_LIBRARIES)
                assert heavy_outside_the_worker(root, top, worker, kept_out) == [], name
            held.append(name)
        assert "biosteam" in held
    finally:
        registry.reset()


def test_the_grep_finds_a_heavy_import_outside_an_engines_worker(tmp_path):
    pkg = tmp_path / "an_engine"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("from .engine import ENGINE\n")
    (pkg / "engine.py").write_text("import a_heavy_library\nENGINE = None\n")
    (pkg / "worker.py").write_text("import a_heavy_library\nfrom another_heavy import x\n")
    assert heavy_outside_the_worker(tmp_path, "an_engine", "an_engine.worker", {"a_heavy_library"}) == [
        "an_engine/engine.py:1 imports a_heavy_library"]
    (pkg / "engine.py").write_text("from . import worker\nENGINE = None\n")
    assert heavy_outside_the_worker(tmp_path, "an_engine", "an_engine.worker", set()) == [
        "an_engine/engine.py:1 imports an_engine.worker"]
    # A dotted heavy name covers its module and every module below it.
    (pkg / "engine.py").write_text("import a_heavy_library.core.solve\nimport a_heavy_library\nENGINE = None\n")
    assert heavy_outside_the_worker(tmp_path, "an_engine", "an_engine.worker", {"a_heavy_library.core"}) == [
        "an_engine/engine.py:1 imports a_heavy_library.core.solve"]
