"""geneOS on the service's side (OF-BLD-014 §6.2).

The geneOS worker does the flux balance analysis in a process of its own;
this module holds the one `SimWorker` that runs it, tells the worker where a
fetched model file lives, and fetches that file:

    pnpm geneos:fetch     the C. necator reconstruction at its pinned commit,
                          into core/data/models/, checked against its sha256

A hash that does not match is a stop condition (§6.2): the file is moved
aside, never used, and the command fails.
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

from . import artifacts, geneos_models as shelf
from .models import BasisInput, BasisSource, Evidence, GeneosModelInfo, GeneosResult
from .workers import SimWorker

# Loading iJO1366 takes a few seconds and a frontier a little longer; the
# first call on a cold worker pays both. A setting, not a measurement.
WORKER_TIMEOUT_S = 180.0

_WORKER: SimWorker | None = None
_LOCK = threading.Lock()


def worker() -> SimWorker:
    global _WORKER
    with _LOCK:
        if _WORKER is None:
            _WORKER = SimWorker("openferment_core.workers.geneos_worker", timeout_s=WORKER_TIMEOUT_S)
        return _WORKER


class GeneosUnavailable(RuntimeError):
    """The model cannot be loaded here, in words."""


TOY = "toy"


def model_args(model_id: str, *, allow_toy: bool = False) -> dict[str, Any]:
    """The worker's arguments for a model: its id, and its file when fetched.
    The toy network is a STAND-IN for tests and fixtures: the API and the
    tool never pass `allow_toy`, so it is refused there like any model not
    on the shelf (§6.R)."""
    if model_id == TOY and allow_toy:
        return {"modelId": TOY}
    entry = shelf.SHELF.get(model_id)
    if entry is None:
        raise GeneosUnavailable(f"there is no model {model_id} on the shelf; it holds {', '.join(shelf.SHELF)}")
    why = shelf.available(entry)
    if why:
        raise GeneosUnavailable(why)
    args: dict[str, Any] = {"modelId": model_id}
    if entry.fetched:
        args["path"] = str(entry.fetched.local)
    return args


def describe(model_id: str, *, allow_toy: bool = False) -> dict[str, Any]:
    return worker().call("describe", model_args(model_id, allow_toy=allow_toy))


# ── the ceiling, the frontier and the sugar mix (§6.3) ─────────────────
#
# Each is an artifact (E.5): a registered tool whose inputs name the model
# file, the add-on and the uptake rate, so a repeat returns what was stored
# and a replay recomputes it in the worker. A sugar the model cannot take up
# is a finding, said in words, and nothing is stored.

CEILING, FRONTIER, MIX = "geneos.ceiling", "geneos.frontier", "geneos.mix"
_HERE = Path(__file__).resolve().parent


def version() -> str:
    """cobra's version, the worker's code and the shelf's data, hashed: a
    change to any of them is a new version, and replay says so."""
    from importlib.metadata import version as installed

    code = (_HERE / "workers" / "geneos_worker.py").read_bytes() + (_HERE / "geneos_models.py").read_bytes()
    return f"cobra {installed('cobra')} · worker {hashlib.sha256(code).hexdigest()[:12]}"


def _model_input(model_id: str) -> BasisInput:
    if model_id == TOY:
        # An assumption, so whatever is computed on it is modeled (demo),
        # never computed evidence (basis_provenance; §6.R).
        return BasisInput(name="model", value="toy", unit="", source=BasisSource(
            kind="assumption", id=TOY, by="openFerment test fixture",
            note="the STAND-IN toy network built in the geneOS worker for tests and fixtures; not a published model"))
    entry = shelf.SHELF[model_id]
    if entry.fetched:
        f = entry.fetched
        note = f"{f.repository} at {f.commit}, {f.path}, sha256 {f.sha256} ({f.licence})"
    else:
        note = f"bundled with cobra as {entry.bundled} ({entry.licence})"
    return BasisInput(name="model", value=entry.name, unit="", source=BasisSource(kind="model", id=model_id, note=note))


def _route_input(model_id: str) -> BasisInput | None:
    entry = shelf.SHELF.get(model_id)
    if entry is None or not entry.addon:
        return None
    addon = shelf.ADDONS[entry.addon]
    return BasisInput(name="add-on", value=addon["id"], unit="", source=BasisSource(
        kind="model", id=addon["source"].removeprefix("model: "),
        note=f"{', '.join(r['id'] for r in addon['reactions'])}; the route {addon['source'].removeprefix('model: ')} carries, each reaction checked for mass balance"))


def _conventions(product: str, substrates: list[str]) -> list[BasisInput]:
    prod = shelf.PRODUCTS[product]
    out = [
        BasisInput(name="uptake", value=shelf.UPTAKE, unit=shelf.UPTAKE_UNIT, source=BasisSource(
            kind="convention", note="the substrate's uptake opened for a ceiling; every other bound stays as the model file publishes it")),
        BasisInput(name="product", value=product, unit="", source=BasisSource(
            kind="convention", note=f"a demand on {prod['metabolite']}; {prod['note']}")),
    ]
    for i, sub in enumerate(substrates):
        s = shelf.SUBSTRATES[sub]
        out.append(BasisInput(name="substrate" if len(substrates) == 1 else f"substrate {'ab'[i]}", value=sub, unit="",
                              source=BasisSource(kind="convention", note=f"through {s['exchange']}, {s['molarMass']} g mol-1, {s['carbons']} carbons")))
    return out


def _inputs(model_id: str, product: str, substrates: list[str]) -> list[BasisInput]:
    route = _route_input(model_id)
    return [_model_input(model_id), *([route] if route else []), *_conventions(product, substrates)]


def _value(inputs: list[BasisInput], name: str) -> str:
    return str(next(i for i in inputs if i.name == name).value)


def _model_id(inputs: list[BasisInput]) -> str:
    return str(next(i for i in inputs if i.name == "model").source.id)


def _run_ceiling(inputs, seed):
    return worker().call("ceiling", {**model_args(_model_id(inputs), allow_toy=True), "product": _value(inputs, "product"),
                                     "substrate": _value(inputs, "substrate")})


def _run_frontier(inputs, seed):
    return worker().call("frontier", {**model_args(_model_id(inputs), allow_toy=True), "product": _value(inputs, "product"),
                                      "substrate": _value(inputs, "substrate")})


def _run_mix(inputs, seed):
    return worker().call("mix", {**model_args(_model_id(inputs), allow_toy=True), "product": _value(inputs, "product"),
                                 "a": _value(inputs, "substrate a"), "b": _value(inputs, "substrate b")})


def _register() -> None:
    v = version()
    artifacts.register(CEILING, v, _run_ceiling)
    artifacts.register(FRONTIER, v, _run_frontier)
    artifacts.register(MIX, v, _run_mix)


for _name in (CEILING, FRONTIER, MIX):
    artifacts.register_lazy(_name, _register)


def _check(model_id: str, product: str, substrates: list[str], allow_toy: bool = False) -> str | None:
    """A finding in words when the model cannot make this product from these
    sugars; None when it can. Raises GeneosUnavailable for a bad request."""
    if product not in shelf.PRODUCTS:
        raise GeneosUnavailable(f"there is no product {product}; the shelf knows {', '.join(shelf.PRODUCTS)}")
    for sub in substrates:
        if sub not in shelf.SUBSTRATES:
            raise GeneosUnavailable(f"there is no substrate {sub}; the shelf knows {', '.join(shelf.SUBSTRATES)}")
    d = describe(model_id, allow_toy=allow_toy)
    if not d["products"].get(product):
        return f"this reconstruction has no route to {shelf.PRODUCTS[product]['name']}"
    for sub in substrates:
        if not d["substrates"].get(sub):
            return f"this reconstruction has no uptake reaction for {sub}"
    return None


def _label(model_id: str, what: str) -> str:
    entry = shelf.SHELF.get(model_id)
    return f"{what}, {entry.name if entry else model_id}{f' ({entry.scope})' if entry else ''}"


def ceiling(model_id: str, product: str, substrate: str, *, keep: bool = True, allow_toy: bool = False) -> GeneosResult:
    finding = _check(model_id, product, [substrate], allow_toy)
    if finding:
        return GeneosResult(kind="ceiling", modelId=model_id, product=product, substrates=[substrate], finding=finding)
    art = artifacts.compute(CEILING, _inputs(model_id, product, [substrate]), keep=keep)
    out = art.output
    ev = Evidence(
        id=f"ev-{art.id}", label=_label(model_id, f"most {product.upper()} from {substrate}"),
        value=out["gPerG"], unit="g g-1", provenance=art.provenance, basis=artifacts.basis_of(art), figure="ceiling",
    )
    return GeneosResult(kind="ceiling", modelId=model_id, product=product, substrates=[substrate],
                        artifactId=art.id, evidence=ev, output=out)


def frontier(model_id: str, product: str, substrate: str, *, keep: bool = True, allow_toy: bool = False) -> GeneosResult:
    finding = _check(model_id, product, [substrate], allow_toy)
    if finding:
        return GeneosResult(kind="frontier", modelId=model_id, product=product, substrates=[substrate], finding=finding)
    art = artifacts.compute(FRONTIER, _inputs(model_id, product, [substrate]), keep=keep)
    top = max(art.output["points"], key=lambda p: p["gPerG"])
    ev = Evidence(
        id=f"ev-{art.id}", label=_label(model_id, f"{product.upper()} against growth on {substrate}"),
        value=top["gPerG"], unit="g g-1", provenance=art.provenance, basis=artifacts.basis_of(art), figure="frontier",
    )
    return GeneosResult(kind="frontier", modelId=model_id, product=product, substrates=[substrate],
                        artifactId=art.id, evidence=ev, output=art.output)


def mix(model_id: str, product: str, a: str, b: str, *, keep: bool = True, allow_toy: bool = False) -> GeneosResult:
    if a == b:
        raise GeneosUnavailable(f"a mix is of two different sugars; {a} was named twice")
    finding = _check(model_id, product, [a, b], allow_toy)
    if finding:
        return GeneosResult(kind="mix", modelId=model_id, product=product, substrates=[a, b], finding=finding)
    art = artifacts.compute(MIX, _inputs(model_id, product, [a, b]), keep=keep)
    # The line's lowest point, as the value a plan may cite; the basis travels
    # with it to the figure (§6.R).
    low = min(art.output["points"], key=lambda p: p["gPerG"])
    ev = Evidence(
        id=f"ev-{art.id}", label=_label(model_id, f"lowest {product.upper()} ceiling across mixtures of {a} and {b}"),
        value=low["gPerG"], unit="g g-1", provenance=art.provenance, basis=artifacts.basis_of(art), figure="mix",
    )
    return GeneosResult(kind="mix", modelId=model_id, product=product, substrates=[a, b],
                        artifactId=art.id, evidence=ev, output=art.output)


def models() -> list[GeneosModelInfo]:
    """The shelf as the browser sees it; nothing here loads a model."""
    out = []
    for m in shelf.SHELF.values():
        out.append(GeneosModelInfo(
            id=m.id, name=m.name, host=m.host, scope=m.scope, route=m.route, licence=m.licence,
            source=(f"{m.fetched.repository} at {m.fetched.commit}" if m.fetched else f"bundled with cobra as {m.bundled}"),
            unavailable=shelf.available(m), feed=m.feed, notes=list(m.notes),
        ))
    return out


# ── fetching the published file ────────────────────────────────────────


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(model: shelf.ShelfModel = shelf.SHELF["RehMBEL1391"], *, run=subprocess.run) -> Path:
    """Clone the pinned commit without its blobs, check out the one file, and
    verify its hash. Returns the file's path; raises on a mismatch."""
    f = model.fetched
    assert f is not None, f"{model.id} is not a fetched model"
    if f.local.is_file() and sha256_of(f.local) == f.sha256:
        return f.local  # present and the pinned file: nothing to fetch
    clone = f.local.parents[len(Path(f.path).parts) - 1]
    if not (clone / ".git").is_dir():
        clone.parent.mkdir(parents=True, exist_ok=True)
        run(["git", "clone", "--filter=blob:none", "--no-checkout", "--quiet", f.repository, str(clone)], check=True)
    run(["git", "-C", str(clone), "checkout", "--quiet", f.commit, "--", f.path], check=True)
    got = sha256_of(f.local)
    if got != f.sha256:
        aside = f.local.with_suffix(f.local.suffix + ".mismatch")
        shutil.move(str(f.local), aside)
        raise GeneosUnavailable(
            f"{model.id}: the file at {f.commit} hashes to {got}, not the pinned {f.sha256}. "
            f"It was moved to {aside.name} and is not used. This is a stop condition (OF-BLD-014 §6.2)."
        )
    return f.local


def main(argv: list[str]) -> int:
    if argv[:1] != ["fetch"]:
        print("usage: python -m openferment_core.geneos fetch", file=sys.stderr)
        return 2
    model = shelf.SHELF["RehMBEL1391"]
    try:
        path = fetch(model)
    except subprocess.CalledProcessError as e:
        print(f"✗ git failed ({e.returncode}) fetching {model.fetched.repository}", file=sys.stderr)
        return 1
    except GeneosUnavailable as e:
        print(f"✗ {e}", file=sys.stderr)
        return 1
    print(f"✓ {model.id} at {model.fetched.commit}: {path.relative_to(shelf.model_dir().parent.parent)}, sha256 {model.fetched.sha256}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
