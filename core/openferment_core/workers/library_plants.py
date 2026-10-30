"""The `biorefineries` package's plants, found by inspection and run whole
(ADR-004; execution prompt §4.4, §8.4).

Imported by the Proforma worker alone (BioSTEAM and biorefineries are
imported here). Its ops (`library_discover`, `library_parameters`,
`library_run`, and `sff_export` for a library run) call these functions and
hand them the worker's own `package_defaults()` and table readers.

DISCOVERY READS; IT BUILDS NOTHING. Every subpackage of the installed package
is imported and read from its own namespace (`vars`), never by attribute
access: some build their whole plant when a name is asked of them (LAOs). A
plant's entry point is the first the package defines of `load`, a
`Biorefinery` class and `create_system`. Read beside it: the entry's
parameters; the configurations the package names (`configuration_names` in
its namespace or a submodule's, else the package test's `configurations`);
a ProcessModel's scenario fields with their defaults; the title of its
README. The package's own test file is read by `ast`: which tests a plant
has, and the names of its feedstock, product and TEA as the test finds them.

A BUILD IS FRESH. It runs inside `package_defaults()` and bypasses the
package's caches: `cache={}` where the entry (or the class `load` hands its
arguments to) takes one, `load=False, save=False` for a ProcessModel, and a
ProcessModel class's own cache emptied while `load()` builds it and put back
after. What the package's own plant needs to build under the pinned BioSTEAM
is a compatibility change, named in `COMPAT` with its reason and stated in
every run's basis.

THE PLANT'S PARTS ARE FOUND, NOT ASSUMED: by the names the package's test
uses (`feedstocks_by_module`, `products_by_module`, the TEA names it tries),
else from what the entry returned (a ProcessModel's `system`, `tea` and its
scenario's feedstock and product streams), else the flowsheet's largest
system that carries a TEA. Each part says how it was found.

PARAMETERS are read back from the built objects, each with the accessor that
sets it: the main feedstock's flow and every priced boundary stream's price;
the TEA's numeric settings; the electricity price, the plant cost index and
each heating and cooling agent a unit used; and each unit's design inputs as
the vendored SFF toolkit's design-spec registry names them. A run sets a
person's values through the same accessors, simulates, prices (the product's
price solved at the TEA's IRR) and reads the run back.
"""
from __future__ import annotations

import ast
import importlib
import inspect
import io
import math
import pkgutil
import re
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager, redirect_stdout
from dataclasses import dataclass, field
from importlib.metadata import PackageNotFoundError, distribution, version
from pathlib import Path
from typing import Any

import biorefineries
import biosteam as bst

from . import sff_toolkit

PACKAGE = "biorefineries"
TEST_FILE = "biorefineries/tests/test_biorefineries.py"
ENTRIES = ("load", "Biorefinery", "create_system")
# openFerment's own flowsheets, composed from a package's factories and run
# through this same adapter (flowsheets/cellulosic_ethanol_v0.py): id → module.
COMPOSED = {"cellulosic_ethanol_v0": "openferment_core.flowsheets.cellulosic_ethanol_v0"}
# Subpackages that are not plants by their own description: the package's test suite.
NOT_PLANTS = {"tests"}


# BioSTEAM writes a unit's name in its own colours, as terminal escapes; a
# refusal carries the words alone.
_ESCAPES = re.compile(r"\x1b\[[0-9;]*m")


class Refused(ValueError):
    """The request cannot be computed, in words (BioSTEAM's colour escapes
    taken out)."""

    def __init__(self, message: str) -> None:
        super().__init__(_ESCAPES.sub("", message))


# ── compatibility changes (stated in every run's basis) ─────────────────


def _corn_inlets(module: Any) -> None:
    module.units.SimultaneousSaccharificationFermentation._ins_size_is_fixed = False


# What a plant needs to build under the pinned BioSTEAM, with why: (the change
# in words, why, the function that makes it). The words travel to the service
# through discovery and are stated in the basis of every run of the plant.
COMPAT: dict[str, tuple[str, str, Callable[[Any], None]]] = {
    "corn": (
        "SimultaneousSaccharificationFermentation takes its two inlets",
        "biorefineries 2.35.1's SimultaneousSaccharificationFermentation passes two inlets to bst.BatchBioreactor, "
        "which declares one fixed inlet in biosteam 2.54.0, so corn.load() stops before it builds; the unit is let "
        "take its inlets, as biosteam's own NRELEthanolFermentation declares; no value of the package's changes",
        _corn_inlets,
    ),
}


# ── the package test, read by ast ──────────────────────────────────────


def _test_path() -> Path | None:
    """The installed test file, found through the distribution's metadata.
    Never through the import system: finding `biorefineries.tests.…` imports
    the `biorefineries.tests` package, whose side effects break later builds
    in the same worker (milk after cellulosic, measured)."""
    try:
        path = Path(str(distribution(PACKAGE).locate_file(TEST_FILE)))
    except PackageNotFoundError:
        return None
    return path if path.is_file() else None


def package_test_tables() -> dict[str, Any]:
    """The package test's plant tables (`feedstocks_by_module`,
    `products_by_module`, `must_load`, `configurations`, as literals) and
    the names of its test functions. Empty when the test is not installed."""
    path = _test_path()
    if path is None:
        return {"file": TEST_FILE, "tests": []}
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: dict[str, Any] = {"file": TEST_FILE}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in ("feedstocks_by_module", "products_by_module", "must_load", "configurations"):
                try:
                    value = ast.literal_eval(node.value)
                except ValueError:
                    continue
                out[name] = sorted(value) if isinstance(value, set) else value
    out["tests"] = [n.name for n in tree.body if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]
    return out


def package_test_name(plant: str, configuration: str | None) -> str:
    """The test the package's code generator writes for a plant and
    configuration (`generate_code`: `test_<module><_configuration>`, a `*`
    spelled `_agile`)."""
    tag = f"_{configuration}".replace("*", "_agile") if configuration else ""
    return f"test_{plant}{tag}"


# ── discovery ──────────────────────────────────────────────────────────


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple)) and all(isinstance(v, (bool, int, float, str)) for v in value):
        return list(value)
    return repr(value)


def _parameters(obj: Any) -> list[dict[str, Any]]:
    try:
        sig = inspect.signature(obj)
    except (TypeError, ValueError):
        return []
    out = []
    for p in sig.parameters.values():
        if p.name in ("self", "cls"):
            continue
        out.append({"name": p.name, "kind": p.kind.name.lower(),
                    "required": p.default is inspect.Parameter.empty
                    and p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD),
                    "default": None if p.default is inspect.Parameter.empty else _jsonable(p.default)})
    return out


def _scenario(entry: Any) -> list[dict[str, Any]]:
    """A ProcessModel's scenario fields, with their defaults, read from the
    scenario class's own signature."""
    scenario = vars(entry).get("Scenario") if inspect.isclass(entry) else None
    if scenario is None:
        return []
    out = []
    for p in inspect.signature(scenario).parameters.values():
        annotation = p.annotation if isinstance(p.annotation, str) else getattr(p.annotation, "__name__", None)
        out.append({"name": p.name, "type": annotation, "default": _jsonable(p.default)})
    return out


def _forwarded(ns: dict[str, Any], entry: str, params: list[dict[str, Any]]) -> Any:
    """The `Biorefinery` class a `load(*args, **kwargs)` hands its arguments
    to, when the package defines one."""
    cls = ns.get("Biorefinery")
    takes_any = any(p["kind"] in ("var_positional", "var_keyword") for p in params)
    return cls if entry == "load" and takes_any and inspect.isclass(cls) else None


def _requires_configuration(ns: dict[str, Any], entry: str, params: list[dict[str, Any]]) -> bool:
    forwarded = _forwarded(ns, entry, params)
    return any(p["required"] for p in params) or (
        forwarded is not None and any(p["required"] for p in _parameters(forwarded)))


def _configurations(module: Any, plant: str, tests: dict[str, Any]) -> tuple[list[str], str | None]:
    """The configurations the package names for a plant: a
    `configuration_names` in its namespace or in one of its own submodules,
    else the package test's `configurations` for it."""
    names = vars(module).get("configuration_names")
    if isinstance(names, (list, tuple)) and names and all(isinstance(n, str) for n in names):
        return list(names), f"{module.__name__}.configuration_names"
    for value in vars(module).values():
        if inspect.ismodule(value) and value.__name__.startswith(module.__name__ + "."):
            names = vars(value).get("configuration_names")
            if isinstance(names, (list, tuple)) and names and all(isinstance(n, str) for n in names):
                return list(names), f"{value.__name__}.configuration_names"
    said = (tests.get("configurations") or {}).get(plant)
    if said:
        return list(said), f"{TEST_FILE}, configurations"
    return [], None


def _title(module: Any) -> tuple[str | None, str | None]:
    """The first heading of the package's README, and the file's path."""
    folder = Path(module.__file__).parent
    for name in ("README.md", "README.rst"):
        path = folder / name
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            s = line.strip()
            if not s or set(s) <= set("=-~*#^") or s.startswith(".."):
                continue
            return s.lstrip("#").strip(), f"{PACKAGE}/{folder.name}/{name}"
    return None, None


def discover() -> dict[str, Any]:
    """Every subpackage of the installed package, read; nothing built."""
    tests = package_test_tables()
    found = []
    for info in sorted(pkgutil.iter_modules(biorefineries.__path__), key=lambda m: m.name.lower()):
        if not info.ispkg or info.name in NOT_PLANTS:
            continue
        entry_out: dict[str, Any] = {"id": info.name, "module": f"{PACKAGE}.{info.name}"}
        try:
            with redirect_stdout(io.StringIO()):
                module = importlib.import_module(f"{PACKAGE}.{info.name}")
        except Exception as e:  # a subpackage that cannot be imported here is said so
            found.append({**entry_out, "kind": "unimportable", "error": f"{type(e).__name__}: {e}"})
            continue
        ns = vars(module)
        entry = next((e for e in ENTRIES if e in ns and callable(ns[e])), None)
        title, readme = _title(module)
        factories = sorted(n for n, v in ns.items() if n.startswith("create_") and n.endswith("system") and callable(v))
        if entry is None:
            found.append({**entry_out, "kind": "subsystems" if factories else "none", "title": title, "readme": readme,
                          "factories": factories})
            continue
        obj = ns[entry]
        configurations, said = _configurations(module, info.name, tests)
        params = _parameters(obj)
        process_model = inspect.isclass(obj) and issubclass(obj, bst.ProcessModel)
        forwarded = _forwarded(ns, entry, params)
        takes_cache = any(p["name"] == "cache" for p in params) or (
            forwarded is not None and any(p["name"] == "cache" for p in _parameters(forwarded)))
        plant_tests = [t for t in tests["tests"] if t == f"test_{info.name}" or t.startswith(f"test_{info.name}_")]
        compat = COMPAT.get(info.name)
        found.append({
            **entry_out, "kind": "plant", "title": title, "readme": readme, "entry": entry, "parameters": params,
            "processModel": process_model, "scenario": _scenario(obj),
            "requiresConfiguration": _requires_configuration(ns, entry, params),
            "configurations": configurations, "configurationsFrom": said, "takesCache": takes_cache,
            "tests": plant_tests, "testNames": {
                "feedstock": (tests.get("feedstocks_by_module") or {}).get(info.name),
                "product": (tests.get("products_by_module") or {}).get(info.name),
                "products": {c: p for c, p in (tests.get("products_by_module") or {}).items() if c in configurations},
            } if info.name in (tests.get("feedstocks_by_module") or {}) else None,
            "compat": [{"change": compat[0], "why": compat[1]}] if compat else [],
            "factories": factories,
        })
    for plant_id, module_name in COMPOSED.items():
        flowsheet = importlib.import_module(module_name)
        found.append({
            "id": plant_id, "module": module_name, "kind": "flowsheet", "title": flowsheet.TITLE,
            "composedFrom": flowsheet.COMPOSED_FROM, "entry": "recipe", "recipe": str(flowsheet.RECIPE_DIR.relative_to(
                Path(flowsheet.__file__).parents[2])),
            "configurations": list(flowsheet.CONFIGURATIONS), "configurationsFrom": f"{module_name}.CONFIGURATIONS",
            "defaultConfiguration": flowsheet.DEFAULT_CONFIGURATION, "requiresConfiguration": False,
            "parameters": [], "scenario": [], "tests": [], "testNames": None, "compat": [], "factories": [],
        })
    return {"package": f"{PACKAGE} {version(PACKAGE)}", "simulator": f"biosteam {version('biosteam')}",
            "thermosteam": f"thermosteam {version('thermosteam')}", "testFile": TEST_FILE,
            "testTables": {k: v for k, v in tests.items() if k != "tests"}, "plants": found}


# ── a build ────────────────────────────────────────────────────────────


@dataclass
class Plant:
    """One plant as built: its parts, and how each was found."""

    id: str
    configuration: str | None
    module: Any
    made: Any
    system: Any
    tea: Any
    feedstock: Any
    product: Any
    how: dict[str, str] = field(default_factory=dict)
    # A composed flowsheet's module (its parameters, gates and read-back), and
    # what a person set that it lays on together (`finalize`).
    flowsheet: Any = None
    pending: dict[str, Any] = field(default_factory=dict)


def _module(plant: str) -> Any:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", plant) or plant in NOT_PLANTS:
        raise Refused(f"{plant!r} is not a plant of {PACKAGE}")
    try:
        with redirect_stdout(io.StringIO()):
            return importlib.import_module(f"{PACKAGE}.{plant}")
    except ModuleNotFoundError:
        raise Refused(f"{PACKAGE} {version(PACKAGE)} has no plant {plant}") from None


def _process_models() -> list[Any]:
    """Every ProcessModel class BioSTEAM knows, its subclasses' subclasses
    included."""
    out, stack = [], list(bst.ProcessModel.__subclasses__())
    while stack:
        cls = stack.pop()
        if cls not in out:
            out.append(cls)
            stack += cls.__subclasses__()
    return out


@contextmanager
def _empty_class_caches() -> Iterator[None]:
    """Every ProcessModel class's own cache, emptied while a package's
    `load()` builds and put back after: a build never returns a plant an
    earlier build left. A `load()` that takes no arguments names no class
    (cornstover's builds `cellulosic.Biorefinery('corn stover ethanol')`),
    and a cached plant skips the `create_system` that sets the package's
    process settings, so it would keep BioSTEAM's defaults (measured: the
    second cornstover build in a worker costed at CEPCI 567.5 and
    electricity at 0.0782 USD/kWh, the first at the package's 525.4 and
    0.0572)."""
    held = {cls: vars(cls)["cache"] for cls in _process_models() if isinstance(vars(cls).get("cache"), dict)}
    for cls in held:
        cls.cache = {}
    try:
        yield
    finally:
        for cls, cache in held.items():
            cls.cache = cache


def _largest_priced_system() -> tuple[Any, str]:
    systems = [s for s in bst.main_flowsheet.system if getattr(s, "TEA", None) is not None]
    if not systems:
        systems = list(bst.main_flowsheet.system)
    if not systems:
        raise Refused("the plant built no system")
    s = max(systems, key=lambda s: len(s.units))
    return s, f"the flowsheet's largest system{' that carries a TEA' if s.TEA is not None else ''}, {s.ID}"


def _stream(made: Any, system: Any, stream_id: str | None) -> Any:
    if not stream_id:
        return None
    found = vars(made).get(stream_id) if made is not None and hasattr(made, "__dict__") else None
    if isinstance(found, bst.Stream):
        return found
    return next((s for s in system.streams if s.ID == stream_id), None)


def build(plant: str, configuration: str | None = None) -> Plant:
    """The plant built afresh through its entry point (an openFerment
    flowsheet through its recipe). Called inside the worker's
    `package_defaults()`; a build the package itself cannot finish is refused
    with the package's own error."""
    if plant in COMPOSED:
        return importlib.import_module(COMPOSED[plant]).build(configuration)
    module = _module(plant)
    ns = vars(module)
    entry = next((e for e in ENTRIES if e in ns and callable(ns[e])), None)
    if entry is None:
        raise Refused(f"{PACKAGE}.{plant} defines no plant entry point ({', '.join(ENTRIES)}): it offers subsystems alone")
    obj = ns[entry]
    params = _parameters(obj)
    configurations, _ = _configurations(module, plant, package_test_tables())
    if configuration is None and _requires_configuration(ns, entry, params):
        raise Refused(f"{PACKAGE}.{plant} is built in one of its configurations, which this request does not name"
                      + (f": {', '.join(configurations)}" if configurations else ""))
    if configuration is not None and configurations and configuration not in configurations:
        raise Refused(f"{PACKAGE}.{plant} names no configuration {configuration!r}; it names {', '.join(configurations)}")
    if configuration is not None and not configurations and not _requires_configuration(ns, entry, params):
        raise Refused(f"{PACKAGE}.{plant} is built in one configuration, its own; it takes no configuration name")
    if plant in COMPAT:
        COMPAT[plant][2](module)
    names = [p["name"] for p in params]
    kwargs: dict[str, Any] = {}
    forwarded = _forwarded(ns, entry, params)
    if "cache" in names or (forwarded is not None and "cache" in [p["name"] for p in _parameters(forwarded)]):
        kwargs["cache"] = {}
    process_model = inspect.isclass(obj) and issubclass(obj, bst.ProcessModel)
    if process_model:
        kwargs.update(load=False, save=False)
    args = [configuration] if configuration is not None else []
    try:
        with redirect_stdout(io.StringIO()):
            if entry == "load":
                with _empty_class_caches():
                    made = obj(*args, **kwargs)
            elif entry == "Biorefinery":
                made = obj(*args, **kwargs)
            else:
                made = obj(*args, **kwargs)
                if isinstance(made, bst.System):
                    made.simulate()
    except Refused:
        raise
    except Exception as e:
        raise Refused(f"{PACKAGE}.{plant}{f' {configuration}' if configuration else ''} could not be built under "
                      f"biosteam {version('biosteam')}: {type(e).__name__}: {e}") from e
    return _parts(plant, configuration, module, made)


def _parts(plant: str, configuration: str | None, module: Any, made: Any) -> Plant:
    tests = package_test_tables()
    how: dict[str, str] = {}
    ns = vars(module)
    feed_name = (tests.get("feedstocks_by_module") or {}).get(plant)
    product_name = (tests.get("products_by_module") or {}).get(configuration or "") or \
        (tests.get("products_by_module") or {}).get(plant)
    if feed_name and isinstance(ns.get(feed_name), bst.Stream):
        feedstock = ns[feed_name]
        how["feedstock"] = f"the package test's name for it, {plant}.{feed_name}"
        product = ns.get(product_name) if product_name else None
        how["product"] = f"the package test's name for it, {plant}.{product_name}"
        tea = None
        for name in ("tea", f"{plant}_tea", f"{feed_name}_tea", f"{product_name}_tea"):
            if isinstance(ns.get(name), bst.TEA):
                tea, how["tea"] = ns[name], f"the first TEA name the package test tries that it defines, {plant}.{name}"
                break
        system = getattr(tea, "system", None) or getattr(made, "system", None)
        if system is None:
            system, how["system"] = _largest_priced_system()
        else:
            how["system"] = "the TEA's own system" if getattr(tea, "system", None) is not None else "the built plant's system"
    elif made is not None and isinstance(getattr(made, "system", None), bst.System):
        system, how["system"] = made.system, "the built plant's own system"
        tea = getattr(made, "tea", None) or system.TEA
        how["tea"] = "the built plant's own TEA" if getattr(made, "tea", None) is not None else "the system's TEA"
        scenario = getattr(made, "scenario", None)
        feed_id = getattr(scenario, "feedstock", None) or getattr(scenario, "feed", None)
        product_id = getattr(scenario, "product", None)
        feedstock = _stream(made, system, feed_id)
        product = _stream(made, system, product_id if isinstance(product_id, str) else None)
        if product is None and isinstance(product_id, str):
            product = _stream(made, system, product_id.lower())
        how["feedstock"] = f"the stream its scenario names, {feed_id}" if feedstock is not None else "not named"
        how["product"] = f"the stream its scenario names, {product_id}" if product is not None else "not named"
    else:
        system = made if isinstance(made, bst.System) else None
        if system is None:
            system, how["system"] = _largest_priced_system()
        else:
            how["system"] = "the system its entry point returned"
        tea = system.TEA
        how["tea"] = "the system's TEA" if tea is not None else "none: the plant is not priced"
        feedstock = product = None
        how["feedstock"] = how["product"] = "not named by the package"
    if tea is not None and not isinstance(tea, bst.TEA):
        tea = None
    if feedstock is None:
        named = vars(made).get("feedstock") if made is not None and hasattr(made, "__dict__") else None
        if isinstance(named, bst.Stream):
            feedstock, how["feedstock"] = named, "the stream the built plant names feedstock"
        else:
            priced_feeds = [s for s in system.feeds if (_number(s.price) or 0) > 0 and s.F_mass > 0]
            if priced_feeds:
                feedstock = max(priced_feeds, key=lambda s: s.F_mass)
                how["feedstock"] = f"not named by the package: the priced feed with the largest mass flow, {feedstock.ID}"
    if product is None:
        sold = [s for s in system.products if (_number(s.price) or 0) > 0 and s.F_mass > 0]
        if sold:
            product = max(sold, key=lambda s: s.price * s.F_mass)
            how["product"] = f"not named by the package: the product with the largest sales, {product.ID}"
    return Plant(plant, configuration, module, made, system, tea, feedstock, product, how)


# ── parameters ─────────────────────────────────────────────────────────

# The TEA settings read back, when the plant's TEA has them: (attribute, label, unit).
TEA_SETTINGS = (
    ("IRR", "Internal rate of return", ""),
    ("income_tax", "Income tax", ""),
    ("operating_days", "Operating days", "d/yr"),
    ("lang_factor", "Lang factor", ""),
    ("startup_months", "Start-up months", "month"),
    ("startup_FOCfrac", "Fixed operating cost during start-up, share", ""),
    ("startup_VOCfrac", "Variable operating cost during start-up, share", ""),
    ("startup_salesfrac", "Sales during start-up, share", ""),
    ("WC_over_FCI", "Working capital over fixed capital", ""),
    ("finance_interest", "Finance interest", ""),
    ("finance_years", "Finance years", "yr"),
    ("finance_fraction", "Financed share of the capital", ""),
)
# The units BioSTEAM's design inputs are stated in, by name, where the name
# says it: a design input whose name is not here is read back with no unit
# and offered as BioSTEAM states it.
DESIGN_UNITS = {"T": "K", "P": "Pa", "tau": "hr", "tau_0": "hr", "V": "m3", "V_max": "m3", "kW_per_m3": "kW/m3",
                "dT_hx_loop": "K", "T_condenser": "K", "Q": "kJ/hr", "power": "kW"}
SHARE_NAMES = ("V_wf", "efficiency", "split", "conversion", "moisture_content", "x_", "y_", "_frac", "fraction")


@dataclass
class Param:
    key: str
    label: str
    group: str
    unit: str
    value: float | str
    setter: Callable[[Any], None] | None
    note: str
    kind: str  # "number", or "text": read back in words, never set


def _set_path(obj: Any, path: str, value: Any) -> None:
    """Set `value` at an accessor path the design-spec registry writes
    ('T', 'outs[0].P', 'effluent.T')."""
    parts = path.split(".")
    for part in parts[:-1]:
        obj = _step(obj, part)
    last = parts[-1]
    m = re.fullmatch(r"(\w+)\[(\d+)\]", last)
    if m:
        getattr(obj, m[1])[int(m[2])] = value
    else:
        setattr(obj, last, value)


def writable(obj: Any, path: str) -> bool:
    """Whether the attribute at an accessor path can be set: a property of
    the object's class without a setter is computed, read back alone."""
    parts = path.split(".")
    try:
        for part in parts[:-1]:
            obj = _step(obj, part)
    except Exception:  # noqa: BLE001 — a path the object cannot answer is not set
        return False
    name = re.sub(r"\[\d+\]$", "", parts[-1])
    found = inspect.getattr_static(type(obj), name, None)
    return not (isinstance(found, property) and found.fset is None)


def _step(obj: Any, part: str) -> Any:
    m = re.fullmatch(r"(\w+)\[(\d+)\]", part)
    return getattr(obj, m[1])[int(m[2])] if m else getattr(obj, part)


def _number(v: Any) -> float | None:
    if isinstance(v, bool):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f and abs(f) != float("inf") else None


def _stream_params(p: Plant) -> list[Param]:
    out: list[Param] = []
    if p.feedstock is not None:
        fs = p.feedstock
        out.append(Param(f"stream.{fs.ID}.F_mass", f"{fs.ID}: flow", "feedstock", "kg/hr", float(fs.F_mass),
                         lambda v, s=fs: setattr(s, "F_mass", v), "the main feedstock's mass flow, as the package builds it",
                         "number"))
    seen = set()
    for s in [*p.system.feeds, *p.system.products]:
        if s.ID in seen or not _number(s.price):
            continue
        seen.add(s.ID)
        role = "feedstock" if s is p.feedstock else "product" if s is p.product else \
            "feed" if s in p.system.feeds else "co-product"
        out.append(Param(f"stream.{s.ID}.price", f"{s.ID}: price", "prices", "USD/kg", float(s.price),
                         lambda v, s=s: setattr(s, "price", v), f"the {role}'s price as the package sets it", "number"))
    return out


def _tea_params(p: Plant) -> list[Param]:
    out: list[Param] = []
    if p.tea is None:
        return out
    for attr, label, unit in TEA_SETTINGS:
        raw = getattr(p.tea, attr, None)
        # An integer stays one: the TEA slices its cash flows with some (finance_years).
        v = raw if isinstance(raw, int) and not isinstance(raw, bool) else _number(raw)
        if v is None:
            continue
        out.append(Param(f"tea.{attr}", label, "TEA", unit, v, lambda x, t=p.tea, a=attr: setattr(t, a, x),
                         f"{type(p.tea).__name__}.{attr}, as the package sets it", "number"))
    return out


def _utility_params(p: Plant) -> list[Param]:
    out = [
        Param("utility.CEPCI", "Plant cost index (CEPCI)", "utilities", "", float(bst.CE),
              lambda v: setattr(bst, "CE", v), "biosteam.CE as the plant left it", "number"),
        Param("utility.electricity_price", "Electricity price", "utilities", "USD/kWh", float(bst.PowerUtility.price),
              lambda v: setattr(bst.PowerUtility, "price", v), "biosteam.PowerUtility.price as the plant left it", "number"),
    ]
    agents: dict[str, Any] = {}
    for unit in p.system.units:
        for hu in unit.heat_utilities:
            if hu.agent is not None:
                agents.setdefault(hu.agent.ID, hu.agent)
    for agent_id in sorted(agents):
        a = agents[agent_id]
        for attr, unit in (("regeneration_price", "USD/kmol"), ("heat_transfer_price", "USD/kJ")):
            v = _number(getattr(a, attr, None))
            if v is None:
                continue
            out.append(Param(f"utility.{agent_id}.{attr}", f"{agent_id}: {attr.replace('_', ' ')}", "utilities", unit, v,
                             lambda x, a=a, at=attr: setattr(a, at, x), f"the {agent_id} agent's {attr}", "number"))
    return out


def _unit_params(p: Plant) -> list[Param]:
    registry = sff_toolkit.design_spec_registry()
    out: list[Param] = []
    for unit in p.system.units:
        entry = next((registry[c.__name__] for c in type(unit).__mro__ if c.__name__ in registry), None)
        if entry is None:
            continue
        for name, spec in (entry.get("design_input_spec_params") or {}).items():
            for accessor in spec.get("accessors") or []:
                try:
                    raw = _step_path(unit, accessor)
                except Exception:  # noqa: BLE001 — an accessor the unit cannot answer is the next one's turn
                    continue
                # An integer stays one (a vessel count is used as an index).
                v = raw if isinstance(raw, int) and not isinstance(raw, bool) else _number(raw)
                if v is None:
                    if isinstance(raw, str) and raw:
                        out.append(Param(f"unit.{unit.ID}.{name}", f"{unit.ID}: {name}", f"unit {unit.ID}", "", raw, None,
                                         f"{type(unit).__name__}.{accessor}, in words; read back, not set: BioSTEAM "
                                         "states no choices for it here", "text"))
                    break
                setter = (lambda x, u=unit, a=accessor: _set_path(u, a, x)) if writable(unit, accessor) else None
                out.append(Param(f"unit.{unit.ID}.{name}", f"{unit.ID}: {name}", f"unit {unit.ID}",
                                 DESIGN_UNITS.get(name, ""), v, setter,
                                 f"{type(unit).__name__}.{accessor}" + ("" if setter else ", computed by the unit: "
                                                                         "read back, not set"), "number"))
                break
    return out


def _step_path(obj: Any, path: str) -> Any:
    for part in path.split("."):
        obj = _step(obj, part)
    return obj


def parameters(p: Plant) -> list[Param]:
    """Every parameter read back from the built plant, in panel order; a
    composed flowsheet's own first, and a key it offers is offered once."""
    own = p.flowsheet.parameters(p) if p.flowsheet is not None else []
    keys = {q.key for q in own}
    return [*own, *(q for q in [*_stream_params(p), *_tea_params(p), *_utility_params(p), *_unit_params(p)]
                    if q.key not in keys)]


def is_share(name: str) -> bool:
    return any(s in name for s in SHARE_NAMES)


def param_json(param: Param) -> dict[str, Any]:
    return {"key": param.key, "label": param.label, "group": param.group, "unit": param.unit, "value": param.value,
            "note": param.note, "kind": param.kind}


# ── a run ──────────────────────────────────────────────────────────────


def apply(params: list[Param], overrides: dict[str, Any], plant: Plant | None = None) -> None:
    """A person's values set through each parameter's own accessor; a key
    the plant does not read back, or a value of the wrong kind, is refused.
    A composed flowsheet then lays on what it holds together and checks it
    (`finalize`: share sums, conversion sums)."""
    by_key = {p.key: p for p in params}
    unknown = sorted(set(overrides) - set(by_key))
    if unknown:
        raise Refused(f"the plant has no parameter {', '.join(unknown)}")
    for key, value in overrides.items():
        param = by_key[key]
        if param.setter is None:
            raise Refused(f"{key} is read back, not set: {param.note}")
        v = _number(value)
        if v is None:
            raise Refused(f"{key} takes a finite number")
        if isinstance(param.value, int):
            if not v.is_integer():
                raise Refused(f"{key} takes a whole number, as the package holds it")
            v = int(v)
        try:
            param.setter(v)
        except Exception as e:  # the package's own refusal of the value
            raise Refused(f"{key} could not be set to {value!r}: {type(e).__name__}: {e}") from e
    if plant is not None and plant.flowsheet is not None:
        plant.flowsheet.finalize(plant)


def simulate(p: Plant) -> None:
    """The plant simulated after a person's values were set: a composed
    flowsheet settles first (A→B→A); a case BioSTEAM finds infeasible is
    refused with its words, a receipt naming the unit."""
    if p.flowsheet is not None:
        p.flowsheet.settle(p)
    try:
        with redirect_stdout(io.StringIO()):
            p.system.simulate()
    except bst.exceptions.InfeasibleRegion as e:
        raise Refused(f"infeasible here (BioSTEAM's InfeasibleRegion): {e}") from e
    except Exception as e:
        raise Refused(f"the plant could not be simulated with these values: {type(e).__name__}: {e}") from e


def priced(p: Plant) -> dict[str, Any]:
    """The TEA's numbers at the package's prices, and the product's price
    solved at the TEA's IRR."""
    tea = p.tea
    if tea is None:
        return {"priced": False, "why": "the plant carries no TEA"}
    out: dict[str, Any] = {"priced": True, "teaClass": type(tea).__name__, "IRR": _number(tea.IRR)}
    for attr in ("sales", "material_cost", "utility_cost", "installed_equipment_cost", "TCI", "FCI", "FOC", "VOC", "NPV"):
        out[attr] = _number(getattr(tea, attr, None))
    if p.product is not None:
        out["product"] = p.product.ID
        out["packagePrice"] = _number(p.product.price)
        try:
            out["solvedPrice"] = _number(tea.solve_price(p.product))
        except Exception as e:  # said, never guessed
            out["solvedPrice"], out["solvedPriceRefused"] = None, f"{type(e).__name__}: {e}"
    if p.feedstock is not None:
        out["feedstock"] = p.feedstock.ID
        out["feedstockKgPerH"] = _number(p.feedstock.F_mass)
    return out


def npv_to_capital(price: dict[str, Any], digits: int) -> dict[str, Any]:
    """The price block with its NPV kept to one unit in the last of `digits`
    significant digits of the plant's total capital investment, the money it
    is reckoned from. An NPV is a difference of discounted cash flows a
    hundred million dollars large; at a price the TEA solved its last digits
    are the arithmetic's (measured: -1.16e-7 and -5.63e-8 USD on two builds
    of cornstover), and they are no part of the run."""
    npv, tci = price.get("NPV"), price.get("TCI")
    if not isinstance(npv, (int, float)) or not isinstance(tci, (int, float)) or not tci:
        return price
    step = 10.0 ** (math.floor(math.log10(abs(tci))) - (digits - 1))
    kept = float(f"{round(npv / step) * step:.{digits}g}")
    return {**price, "NPV": kept if kept else 0.0}


def run(plant: str, configuration: str | None, overrides: dict[str, Any], *,
        defaults: Callable[[], AbstractContextManager[None]],
        read_tables: Callable[[Any, Any, bool | None], dict[str, Any]],
        test_quantities: Callable[[dict[str, Any]], dict[str, float]],
        draw: bool | None = False) -> dict[str, Any]:
    """One run of a library plant: built afresh, its parameters read back,
    a person's values set, simulated, priced, read back again and its tables
    read, before the worker's settings go back. The worker rounds what it
    returns to the digits the run's basis states. Graphviz draws no diagram
    for a library run (`draw` False): its SFF file's graph is its drawing,
    and its basis does not depend on the host."""
    with defaults():
        p = build(plant, configuration)
        before = parameters(p)
        library = {q.key: q.value for q in before}
        if overrides:
            apply(before, overrides, p)
            simulate(p)
        after = parameters(p)
        parts = {"system": p.system, "tea": p.tea, "product": p.product, "feedstock": p.feedstock, "price": None}
        out = {
            "plant": plant, "configuration": configuration,
            "simulator": f"biosteam {version('biosteam')}", "package": f"{PACKAGE} {version(PACKAGE)}",
            "found": p.how, "price": priced(p),
            "measured": test_quantities(parts) if p.tea is not None and p.feedstock is not None and p.product is not None else {},
            "parameters": [param_json(q) for q in after],
            "libraryDefaults": library,
            "overrides": dict(overrides),
        }
        if p.flowsheet is not None:
            out["readBack"] = p.flowsheet.read_back(p)
            out["outputs"] = p.flowsheet.outputs(p)
        try:
            out.update(read_tables(_Module(), p, draw))
        except Exception as e:  # noqa: BLE001 — the tables are read without the TEA's breakdown, and say why
            out.update(read_tables(_Module(tea=False), p, draw))
            out["teaNote"] = f"the TEA's breakdown could not be read from BioSTEAM: {type(e).__name__}: {e}"
    return out


class _Module:
    """What the worker's `tables` reads a plant's parts through; without the
    TEA when BioSTEAM cannot break it down (an agile system's market values,
    measured on oilcane's `*` configurations)."""

    def __init__(self, tea: bool = True) -> None:
        self.tea = tea

    def parts(self, p: Plant) -> dict[str, Any]:
        return {"system": p.system, "tea": p.tea if self.tea else None, "product": p.product,
                "feedstock": p.feedstock, "price": None}


def export(plant: str, configuration: str | None, overrides: dict[str, Any], path: str, *,
           defaults: Callable[[], AbstractContextManager[None]], metadata: dict[str, Any] | None,
           title: str | None) -> dict[str, Any]:
    """A library run's plant, built and set as the run set it, written as an
    SFF file and checked (`sff_export`)."""
    with defaults():
        p = build(plant, configuration)
        if overrides:
            apply(parameters(p), overrides, p)
            simulate(p)
        if p.flowsheet is None:
            return sff_toolkit.export_checked(p.system, p.tea, path, metadata=metadata, process_title=title)
        authored = p.flowsheet.authored()
        return sff_toolkit.export_checked(
            p.system, p.tea, path, metadata=metadata,
            process_title=title or f"{authored.get('process_title')}: {p.configuration}",
            recipe=p.flowsheet.RECIPE_DIR,
            authored={k: v for k, v in authored.items() if k != "process_title"})


def cases(plant: str, configuration: str | None, values: list[dict[str, Any]], *,
          defaults: Callable[[], AbstractContextManager[None]]) -> list[dict[str, Any]]:
    """Cases run one after another on one warm build (`library_cases`): each
    sets every parameter to its library default and then its own values, and
    runs from a settled plant; a case the plant cannot hold is a receipt in
    its place. The A→B→A gate runs here."""
    out = []
    with defaults():
        p = build(plant, configuration)
        params = parameters(p)
        library = {q.key: q.value for q in params if q.setter is not None}
        for case in values:
            try:
                apply(params, {**library, **case}, p)
                simulate(p)
            except Refused as e:
                out.append({"values": case, "refused": str(e)})
                continue
            row = {"values": case, "price": priced(p)}
            if p.flowsheet is not None:
                row["outputs"] = p.flowsheet.outputs(p)
            out.append(row)
    return out


def check_builds(found: dict[str, Any], *, defaults: Callable[[], AbstractContextManager[None]]) -> dict[str, Any]:
    """Each plant discovery found, built here in each configuration it names
    (else its own), as a run would build it: its units and whether it is
    priced, or the package's own error. Nothing it builds is kept. (How many
    parameters a plant reads back is left out: the heating and cooling agents
    its units name can follow what the worker built before.)"""
    for entry in found["plants"]:
        if entry.get("kind") not in ("plant", "flowsheet"):
            continue
        builds = []
        for configuration in entry.get("configurations") or [None]:
            try:
                with defaults():
                    p = build(entry["id"], configuration)
                    builds.append({"configuration": configuration, "ok": True, "units": len(p.system.units),
                                   "priced": p.tea is not None})
            except Refused as e:
                builds.append({"configuration": configuration, "ok": False, "error": str(e)})
        entry["builds"] = builds
    return found


def parameters_of(plant: str, configuration: str | None, *,
                  defaults: Callable[[], AbstractContextManager[None]]) -> dict[str, Any]:
    """A plant's parameters as the package builds it, with how its parts
    were found (`library_parameters`)."""
    with defaults():
        p = build(plant, configuration)
        return {"plant": plant, "configuration": configuration, "found": p.how,
                "parameters": [param_json(q) for q in parameters(p)],
                "simulator": f"biosteam {version('biosteam')}", "package": f"{PACKAGE} {version(PACKAGE)}"}


