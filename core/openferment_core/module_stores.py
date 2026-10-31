"""Every module's store, read the same way (OF-BLD-015 §7.1, §7.2).

Postdoc once answered that a module held nothing while its screen showed
rows: it could read records and passages and nothing else. This module reads
every destination behind Home's rail and gives every row one shape, `Row`:
the module, the kind of row, its id, a label, the module's own word for where
it stands, and the one `state` Postdoc reads, which is computed here from
that word.

Where each module's rows come from:

- the project's own rows (project_state.py): its runbooks, each with its
  lock, and the BioSTEAM scenarios made with New scenario;
- the module projection (protocols, geneOS's hosts and pathways, Primer's
  lessons): no store holds these catalogues yet, so each list is empty, and
  a test hands its own in;
- pureOS's unit operations, from `schema/vocabulary.yaml`;
- the service's own stores (records and candidates through the evidence
  pool, artifacts, Guild's ledger and checks, Intake's fetch state, the
  geneOS shelf).

A read leaves part of some modules out: a project's depositions and
measurements, and review decisions a browser has not posted yet. `PARTIAL`
names what, and the answer's footer says the module was read in part.

`coverage(question)` is code and calls no model: it finds the rows the
question names, and the modules it names, before Postdoc's first turn.

A read shows every row the project holds (ADR-005).
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from .models import CoverageHit, CoverageMap, ModuleCoverage, ModuleRow

# The rail's order (src/data/nav.ts), Home last because it gathers the rest.
MODULES = ("runbooks", "geneos", "fermos", "pureos", "proforma", "biorepo", "guild", "primer", "intake", "home")
LABEL = {
    "runbooks": "Runbooks", "geneos": "geneOS", "fermos": "fermOS", "pureos": "pureOS",
    "proforma": "Proforma", "biorepo": "BioRepo", "guild": "Guild", "primer": "Primer", "intake": "Intake",
    "home": "Home",
}
STATES = ("open", "fenced", "approved", "locked", "proposed", "retired")

# What the service cannot see of a module, said once, in the footer's words.
PARTIAL = {
    "runbooks": "the project's depositions and measurements are kept with it and shown on the Runbooks page; this "
                "read lists its runbooks and protocols",
    "fermos": "the project's depositions are kept with its runbooks; this read lists what the service computed: "
              "fits, forecasts, simulations and vessel designs",
    "biorepo": "review decisions a browser has not posted yet wait in that browser",
}

# Words that name a module itself. Common nouns ("record", "host") are left
# out: they would name a module in nearly every question.
MODULE_WORDS = {
    "runbooks": ("runbooks", "runbook", "protocols"),
    "geneos": ("geneos",),
    "fermos": ("fermos",),
    "pureos": ("pureos",),
    "proforma": ("proforma",),
    "biorepo": ("biorepo",),
    "guild": ("guild",),
    "primer": ("primer",),
    "intake": ("intake",),
    "home": (),
}
# A state the question asks about, in its words.
STATE_WORDS = {
    "open": "open", "free": "open", "fenced": "fenced", "blocked": "fenced", "approved": "approved",
    "locked": "locked", "proposed": "proposed", "retired": "retired",
}
COVERAGE_HITS = 8
MIN_NAME = 3
PREFIX_MIN = 4


@dataclass(frozen=True)
class Row:
    module: str
    kind: str
    id: str
    label: str
    state: str
    # The module's own word for where the row stands, kept beside `state`.
    status: str
    provenance: str | None = None
    # Spellings the question may use for it; the label and the id always count.
    names: tuple[str, ...] = ()
    # What else a search by words may match.
    words: str = ""
    detail: dict[str, Any] = field(default_factory=dict)
    # Whether the bare id counts as a name. A paper's id ("H16") is too short
    # to tell from a strain's designation, so a source is named by its title.
    id_names: bool = True
    # The species the row is of, as "genus species" in lower case: a host's
    # or a shelf model's by its label, a record's by its strain. A question
    # naming the species, in full or abbreviated, names the row
    # (OF-BLD-016 D10).
    species: tuple[str, ...] = ()
    # Other ids a read by id finds the row by: a train's run artifact, and a
    # train's units by their train's scenario and run (OF-BLD-019 §4.1).
    alt_ids: tuple[str, ...] = ()

    @property
    def ref(self) -> str:
        return f"{self.module}/{self.kind}/{self.id}"

    def model(self) -> ModuleRow:
        return ModuleRow(module=self.module, kind=self.kind, id=self.id, ref=self.ref, label=self.label,  # type: ignore[arg-type]
                         state=self.state, status=self.status, provenance=self.provenance,  # type: ignore[arg-type]
                         detail=_short(self.detail))

    def hit(self) -> CoverageHit:
        return CoverageHit(ref=self.ref, id=self.id, kind=self.kind, label=self.label, state=self.state)  # type: ignore[arg-type]


MAX_TEXT = 300
MAX_ITEMS = 10


def _short(value: Any) -> Any:
    """A row's detail kept short enough that a page of rows stays readable."""
    if isinstance(value, str):
        return value if len(value) <= MAX_TEXT else value[: MAX_TEXT - 1] + "…"
    if isinstance(value, list):
        return [_short(v) for v in value[:MAX_ITEMS]]
    if isinstance(value, dict):
        return {k: _short(v) for k, v in value.items()}
    return value


# ── states, computed from each module's own word ──────────────────────────

def runbook_state(status: str, locked_at: str | None) -> str:
    if locked_at:
        return "locked"
    if status in ("needs_review", "awaiting_budget"):
        return "proposed"
    if status == "blocked_unverified":
        return "fenced"
    return "open"


def record_state(provenance: str | None, status: str | None) -> str:
    if status == "rejected":
        return "retired"
    if provenance in ("measured", "gold", "verified", "curated"):
        return "approved"
    return "proposed"


def check_state(state: str) -> str:
    return {"proposed": "proposed", "scheduled": "open", "done": "locked", "dismissed": "retired"}.get(state, "open")


def intake_state(ingest: str) -> str:
    """A document's state: held by the project (collected, or linked from
    another project's), refused, or waiting."""
    if ingest in ("complete", "ingested", "linked", "held"):
        return "approved"
    if ingest.startswith("failed"):
        return "fenced"
    return "proposed"


# ── the sources ───────────────────────────────────────────────────────────

@dataclass
class Sources:
    """Where rows are read from. Each is a callable so a test hands in a
    fixture and a module that fails to load fails alone, said in words."""

    projection: Callable[[], dict[str, Any]]
    pool: Callable[[], Any]
    artifacts: Callable[[], list[Any]]
    guild: Callable[[], Any]
    checks: Callable[[], Any]
    intake: Callable[[], dict[str, Any]]
    shelf: Callable[[], list[Any]]
    strain_aliases: Callable[[], dict[str, str]]
    witness: Callable[[], list[Any]] = list
    proposals: Callable[[], list[Any]] = list
    # The trains a model built (OF-BLD-020 §5.4, pureos.kept).
    kept_trains: Callable[[], list[Any]] = list
    # The project's own rows (project_state.py): the BioSTEAM scenarios made
    # with New scenario, and its runbooks, each with its lock.
    scenarios: Callable[[], list[Any]] = list
    runbooks: Callable[[], list[Any]] = list


def _kept_trains() -> list[Any]:
    from .pureos import kept

    return list(kept.read().trains)


# The catalogues a module reads that no store holds yet (protocols, hosts and
# pathways, lessons), each list empty; a test hands its own in through
# `Sources.projection`, or in place of `_projection`, and may hand runbooks and
# scenarios this way beside the project's own (`Sources.runbooks`,
# `Sources.scenarios`).
EMPTY_PROJECTION: dict[str, Any] = {
    "runbooks": {"runbooks": [], "protocols": []},
    "geneos": {"hosts": [], "pathways": []},
    "proforma": {"scenarios": []},
    "primer": {"lessons": []},
}


def _projection() -> dict[str, Any]:
    """The empty projection, a copy of its own for each caller."""
    return copy.deepcopy(EMPTY_PROJECTION)


def _scenarios() -> list[Any]:
    from . import proforma

    return proforma.held_scenarios()


def _project_runbooks() -> list[Any]:
    from . import project_state

    return project_state.kept("runbooks")


def _strain_aliases() -> dict[str, str]:
    """Strain aliases arrive with a project's records (stage 2); none here."""
    return {}


def default_sources(pool_factory: Callable[[], Any] | None = None) -> Sources:
    from . import artifacts, checks, evidence_pool, geneos, guild, intake, proposals, witness

    return Sources(
        projection=_projection,
        pool=pool_factory or (lambda: evidence_pool.load()),
        artifacts=artifacts.all_artifacts,
        guild=guild.read,
        checks=checks.read,
        intake=intake.held,
        shelf=geneos.models,
        strain_aliases=_strain_aliases,
        witness=witness.runs,
        proposals=proposals.open_ones,
        kept_trains=_kept_trains,
        scenarios=_scenarios,
        runbooks=_project_runbooks,
    )


def fixture_sources(pool_factory: Callable[[], Any]) -> Sources:
    """The empty projection (unless a test hands one) and the given pool,
    with every other store (artifacts, the ledger, checks, fetches, the
    shelf, the project's runbooks and scenarios) empty: what a fixture
    sweeps, so it reads the same on every machine."""
    from .models import Checks, Guild

    return Sources(projection=_projection, pool=pool_factory, artifacts=list, guild=Guild, checks=Checks,
                   intake=dict, shelf=list, strain_aliases=_strain_aliases)


# ── rows per module ───────────────────────────────────────────────────────

ARTIFACT_MODULE = {
    "growth_fit": "fermos", "kinetic_fit": "fermos", "growth_forecast": "fermos",
    "geneos.ceiling": "geneos", "geneos.frontier": "geneos", "geneos.mix": "geneos",
    "proforma.run": "proforma", "proforma_benchmark": "proforma",
    # A reference biorefinery's run (OF-BLD-019 §2.2), so Proforma's rows
    # list the reference runs beside the scenarios' (§6.1).
    "proforma.reference": "proforma",
}


# A kept simulation (OF-BLD-020 §3.4): fermOS reads it as its own kind,
# `simulation`, never as a bare artifact row.
SIMULATION = "fermos.simulation"



HEADLINE_VALUES = 8


def _headline(output: Any) -> dict[str, Any]:
    """An artifact's top-level scalars (a price, a ceiling, a unit, a note),
    so a read says what was computed and not only that it was. Anything
    nested is left to `get_artifact` and the evidence a tool returns."""
    out: dict[str, Any] = {}
    for k, v in (output.items() if isinstance(output, dict) else []):
        if isinstance(v, (str, int, float, bool)) and not (isinstance(v, str) and len(v) > MAX_TEXT):
            out[k] = v
        if len(out) >= HEADLINE_VALUES:
            break
    return out


def _artifact_row(module: str, a: Any, provenance: str) -> Row:
    inputs = [f"{i.name}={i.value}" for i in a.inputs if isinstance(getattr(i, "value", None), str)][:MAX_ITEMS]
    return Row(module=module, kind="artifact", id=a.id, label=f"{a.tool} artifact", state="open", status="computed",
               provenance=provenance, words=" ".join([a.tool, *inputs]),
               detail={"tool": a.tool, "createdAt": a.createdAt, "inputs": inputs, "output": _headline(a.output),
                       "cite": "cite the value through get_artifact or the tool that computes it; this row names it"})


VESSEL_TOOL = "fermos.vessel"
# A pureOS train run (OF-BLD-020 §5.2): pureOS reads it as its own kind,
# `train-run` (§5.4).
TRAIN_RUN = "pureos.train_run"


def _vessel_row(a: Any, provenance: str) -> Row:
    from . import vessel

    v = vessel.summary(a)
    kind = f", {v.vesselType.replace('-', ' ')}" if v.vesselType else ""
    return Row(module="fermos", kind="vessel", id=a.id, label=f"Vessel design: BioSTEAM's {v.unitClass}{kind}, for "
               f"{v.sourceTool} {v.source}", state="open", status="computed", provenance=provenance,
               words=" ".join(["vessel", "fermenter", "bioreactor", v.unitClass, v.vesselType or "", v.source]), alt_ids=(v.source,) if v.source else (),
               detail={"tool": a.tool, "createdAt": a.createdAt, "unitClass": v.unitClass, "vesselType": v.vesselType,
                       "source": v.source, "sourceTool": v.sourceTool, "vessels": v.vessels, "volume": v.volume,
                       "volumeUnit": "m3", "installed": v.installed, "installedUnit": "USD",
                       "cite": "cite a design's numbers by its artifact id, as fermos_vessel returns it, or by this "
                               "row's ref; get_artifact reads the whole design table"})


class Stores:
    """Every module's rows, loaded on first use and kept for one question."""

    def __init__(self, sources: Sources | None = None, pool_factory: Callable[[], Any] | None = None) -> None:
        self.sources = sources or default_sources(pool_factory)
        self._all: dict[str, list[Row]] = {}
        self._rows: dict[str, list[Row]] = {}
        self._errors: dict[str, str] = {}
        self._cache: dict[str, Any] = {}

    def _get(self, name: str) -> Any:
        if name not in self._cache:
            self._cache[name] = getattr(self.sources, name)()
        return self._cache[name]

    def forget(self, *sources: str) -> None:
        """Read the named sources afresh on next use, and every module's rows
        with them (OF-BLD-020 §5.R, finding 21): a write in the middle of a
        question (a model's train changed, a run kept) changes what a later
        read of the same question must see. The other sources stay as read."""
        for name in sources:
            self._cache.pop(name, None)
        self._all.clear()
        self._rows.clear()
        self._errors.clear()

    def pool(self) -> Any:
        return self._get("pool")

    def all_rows(self, module: str) -> list[Row]:
        """Every row the module holds."""
        if module not in self._all:
            try:
                self._all[module] = list(getattr(self, f"_{module}")())
            except Exception as e:  # one module failing is said, and the rest are read
                self._all[module] = []
                self._errors[module] = f"{LABEL[module]} could not be read: {type(e).__name__}: {e}"
        return self._all[module]

    def rows(self, module: str) -> list[Row]:
        """The rows this question may see."""
        if module not in self._rows:
            self._rows[module] = list(self.all_rows(module))
        return self._rows[module]

    def error(self, module: str) -> str | None:
        self.rows(module)
        return self._errors.get(module)

    def _artifact_mark(self, a: Any) -> str:
        """What an artifact is worth now: `basis_provenance` over its inputs
        as they stand (the pool's records, the store's artifacts as stored),
        as `artifacts.compute` reads a repeat. The stored file's word is what
        they were worth when it was computed; a record demoted or rejected
        since would leave a claim citing the row ranked too high."""
        from .artifacts import basis_of
        from .basis import basis_provenance

        kinds = {i.source.kind for i in a.inputs}
        records = self.pool().records_by_id if "record" in kinds else {}
        stored = {x.id: x for x in self._get("artifacts")} if "artifact" in kinds else {}
        return basis_provenance(basis_of(a), records, stored)

    def _artifacts(self, module: str) -> Iterable[Row]:
        for a in self._get("artifacts"):
            if ARTIFACT_MODULE.get(a.tool) == module:
                yield _artifact_row(module, a, self._artifact_mark(a))

    def _species(self) -> dict[str, str]:
        """Each host's species by its label."""
        if "_species" not in self._cache:
            hosts = self._get("projection")["geneos"]["hosts"]
            self._cache["_species"] = {h["id"]: sp for h in hosts if (sp := species_of(h["name"]))}
        return self._cache["_species"]

    def _species_of(self, strain_ids: Iterable[str | None]) -> tuple[str, ...]:
        by_strain = self._species()
        return tuple(sorted({by_strain[s] for s in strain_ids if s and s in by_strain}))

    def _runbooks(self) -> Iterable[Row]:
        p = self._get("projection")["runbooks"]
        for r in [*self._get("runbooks"), *p["runbooks"]]:
            # Named by its title, the title's head ("Ethanol" of "Ethanol —
            # pilot run") and the product it makes, so a question about a
            # product finds the runbooks that touch it. A prediction is read
            # by its label, as the page shows it.
            predictions = [x if isinstance(x, str) else str(x.get("label") or "") for x in r.get("predictions") or []]
            names = tuple(n for n in (r["title"].split(" — ")[0], r.get("productId")) if n)
            yield Row("runbooks", "runbook", r["id"], r["title"], runbook_state(r["status"], r.get("lockedAt")), r["status"],
                      names=names,
                      words=" ".join([r["kind"], r.get("productId") or "", r.get("strainId") or ""] + predictions),
                      detail={"kind": r["kind"], "productId": r.get("productId"), "strainId": r.get("strainId"),
                              "lockedAt": r.get("lockedAt"), "predictions": predictions})
        for x in p["protocols"]:
            organisms = list(x.get("organisms", []))
            yield Row("runbooks", "protocol", x["id"], x["title"], "approved", f"version {x['currentVersion']} current",
                      words=" ".join([x["category"], x.get("purpose") or ""] + organisms),
                      detail={"category": x["category"], "organisms": organisms,
                              "currentVersion": x["currentVersion"], "versions": x.get("versions", [])})

    def _geneos(self) -> Iterable[Row]:
        p = self._get("projection")["geneos"]
        aliases: dict[str, list[str]] = {}
        for alias, sid in self._get("strain_aliases").items():
            aliases.setdefault(sid, []).append(alias)
        for h in p["hosts"]:
            yield Row("geneos", "host", h["id"], h["name"], "open", "in the catalogue",
                      names=tuple(aliases.get(h["id"], ())), words=" ".join(h.get("badges") or []),
                      detail={"bsl": h.get("bsl"), "badges": h.get("badges") or []},
                      species=self._species_of([h["id"]]))
        for x in p["pathways"]:
            yield Row("geneos", "pathway", x["id"], x["label"], "open", "in the catalogue",
                      words=" ".join(x.get("products") or []), detail={"products": x.get("products") or []})
        for m in self._get("shelf"):
            ok = m.unavailable is None
            yield Row("geneos", "model", m.id, m.name, "open" if ok else "fenced", "on the shelf" if ok else "not fetched",
                      words=m.host or "", detail={"host": m.host, "unavailable": m.unavailable},
                      species=self._species_of([m.host]) or tuple(x for x in [species_of(m.name)] if x))
        yield from self._artifacts("geneos")

    def _fermos(self) -> Iterable[Row]:
        yield from self._artifacts("fermos")
        yield from self._simulations()
        # OF-BLD-020 §4.2 — a kept vessel design, kind `vessel`: what BioSTEAM
        # sized for which simulation, read from the artifact (vessel.summary).
        for a in self._get("artifacts"):
            if a.tool == VESSEL_TOOL:
                yield _vessel_row(a, self._artifact_mark(a))

    def _simulations(self) -> Iterable[Row]:
        """One row a kept simulation (OF-BLD-020 §3.4), `fermos/simulation/<id>`:
        its family and strain in the label, the mark worked out from its
        inputs as they stand (`_artifact_mark`), and a detail of words, ids
        and flags alone. Its numbers stay in the artifact: a claim cites the
        row by its ref, or the simulation by the evidence id fermos_simulate
        returns."""
        hosts = {h["id"]: h["name"] for h in self._get("projection")["geneos"]["hosts"] if h.get("id")}
        for a in self._get("artifacts"):
            if a.tool != SIMULATION:
                continue
            o = a.output if isinstance(a.output, dict) else {}
            family, title = str(o.get("family") or ""), str(o.get("title") or o.get("family") or "")
            strain, product, sugar = o.get("strain"), o.get("product"), o.get("sugar")
            who = hosts.get(str(strain), str(strain)) if strain else "every strain the evidence pool holds"
            bound: dict[str, list[str]] = {}
            for v in [*(o.get("parameters") or []), *(o.get("start") or [])]:
                if isinstance(v, dict) and v.get("key"):
                    bound.setdefault(str(v.get("origin") or "waiting"), []).append(str(v["key"]))
            ceiling = o.get("ceiling") if isinstance(o.get("ceiling"), dict) else {}
            yield Row("fermos", "simulation", a.id, f"{title} ({family}) simulation of {who}", "open", "computed",
                      provenance=self._artifact_mark(a),
                      words=" ".join(str(x) for x in ("simulation", family, title, strain or "", product or "",
                                                      sugar or "", who) if x),
                      detail={"artifactId": a.id, "family": family, "title": title, "strain": strain,
                              "product": product, "sugar": sugar, "boundBy": bound,
                              "aerobic": bool(o.get("aerobic")), "aboveCeiling": bool(ceiling.get("flagged")),
                              "flagged": bool(o.get("flags")),
                              "cite": "cite the row by its ref; its numbers are in the artifact, and fermos_simulate "
                                      "returns a simulation's evidence id"}, species=self._species_of([strain]))

    def _pureos(self) -> Iterable[Row]:
        from .validate import unit_operations

        ops = unit_operations()
        for u in ops:
            classes = u.get("biosteamClasses") or []
            yield Row("pureos", "unit-operation", u["id"], u["label"], "open", "in the vocabulary",
                      words=" ".join([u["stage"], u.get("note") or "", *classes]),
                      detail={"stage": u["stage"], "note": u.get("note"), "biosteamClasses": classes})
        yield from self._trains({c: u["id"] for u in ops for c in u.get("biosteamClasses") or []})
        yield from self._kept_trains()
        yield from self._train_runs()

    def _kept_trains(self) -> Iterable[Row]:
        """One row a train a model built (OF-BLD-020 §5.4), kind `train`,
        `pureos/train/<train id>`: the train as data in words and ids, who made
        it and when, and the ids of its runs, newest first; found by the
        train's id or a run's. It carries no mark: a train is data, and its
        runs carry theirs (kind `train-run`)."""
        runs: dict[str, list[Any]] = {}
        for a in self._get("artifacts"):
            if a.tool == TRAIN_RUN:
                tid = (a.output.get("train") or {}).get("id") if isinstance(a.output, dict) else None
                if tid:
                    runs.setdefault(str(tid), []).append(a)
        for k in self._get("kept_trains"):
            s = k.spec
            mine = sorted(runs.get(s.id, []), key=lambda a: a.createdAt, reverse=True)
            yield Row("pureos", "train", s.id, f"{s.name} ({s.id})", "open", "built by a model", names=(s.name,),
                      words=" ".join(["train built model", s.product, s.program, *(u.type for u in s.units)]),
                      alt_ids=tuple(a.id for a in mine),
                      detail={"trainId": s.id, "name": s.name, "program": s.program, "product": s.product,
                              "inlet": {"kind": s.inlet.kind, "ref": s.inlet.ref, "streamId": s.inlet.streamId,
                                        "vessel": s.inlet.vessel},
                              "units": [u.id for u in s.units], "unitTypes": [u.type for u in s.units],
                              "recordsNamed": {u.id: sorted(u.records) for u in s.units if u.records},
                              "madeBy": k.madeBy, "agent": k.agent, "at": k.at, "updatedAt": k.updatedAt,
                              "runs": [a.id for a in mine],
                              "cite": "cite the train by its ref; a run's numbers are cited by its evidence id, which "
                                      "pureos_build returns, or its train-run row's ref"})

    def _train_runs(self) -> Iterable[Row]:
        """One row a kept train run (OF-BLD-020 §5.4), kind `train-run`,
        `pureos/train-run/<artifact id>`: labelled with its train's name and
        product, its mark worked out from its inputs as they stand when read
        (`_artifact_mark`), and a detail of words, ids and flags alone; its
        numbers stay in the artifact. Found by its own id or its train's."""
        for a in self._get("artifacts"):
            if a.tool != TRAIN_RUN:
                continue
            o = a.output if isinstance(a.output, dict) else {}
            spec = o.get("train") if isinstance(o.get("train"), dict) else {}
            tid, tname = spec.get("id"), spec.get("name")
            product = o.get("productId") or spec.get("product")
            units = [u for u in spec.get("units") or [] if isinstance(u, dict)]
            inlet = spec.get("inlet") if isinstance(spec.get("inlet"), dict) else {}
            yield Row("pureos", "train-run", a.id, f"Run of train {tname or tid or a.id} ({product})", "open",
                      "computed", provenance=self._artifact_mark(a), id_names=False,
                      alt_ids=(str(tid),) if tid else (),
                      words=" ".join(str(x) for x in ("train run recovery purity", product, o.get("product"), tid,
                                                      *(u.get("type") for u in units)) if x),
                      detail={"artifactId": a.id, "tool": a.tool, "createdAt": a.createdAt, "trainId": tid,
                              "trainName": tname, "product": product, "productChemical": o.get("product"),
                              "productStream": o.get("productStream"), "units": [u.get("id") for u in units],
                              "unitTypes": [u.get("type") for u in units], "inletKind": inlet.get("kind"),
                              "inletRef": inlet.get("ref"), "flagged": bool(o.get("flags")),
                              "cite": "cite the run by this row's ref; its numbers are in the artifact, and "
                                      "pureos_build returns a run's evidence id"})

    def _trains(self, operation: dict[str, str]) -> Iterable[Row]:
        """The train of each scenario's newest Proforma run (OF-BLD-019 §4.1),
        and one row a unit of it, read by `pureos.train_of` from the run's
        stream table: the same numbers pureOS → Train shows. A read by the
        scenario's id or the run's artifact id finds the train and its units;
        the mark is the run's, worked out from its inputs as they stand."""
        from . import pureos

        scenarios = self._scenario_rows()
        runs = [a for a in self._get("artifacts") if a.tool == pureos.RUN]
        for key, group in pureos._runs(runs, scenarios).items():
            a = group[0]
            mark = self._artifact_mark(a)
            tr = pureos.train_of(a, scenarios=scenarios, provenance=mark, runs=len(group))
            name = tr.scenarioName or tr.flowsheet or a.id
            ids = tuple(x for x in (tr.scenarioId, a.id) if x and x != key)
            yield Row("pureos", "train", key, f"Train of {name}", "open", "computed", provenance=mark,
                      names=tuple(x for x in (tr.scenarioName,) if x), alt_ids=ids,
                      words=" ".join(["train recovery", tr.flowsheet or "", tr.product or "",
                                      *(u.unitClass for u in tr.units), *(operation.get(u.unitClass, "") for u in tr.units)]),
                      detail={"artifactId": a.id, "scenarioId": tr.scenarioId, "flowsheet": tr.flowsheet,
                              "product": tr.product, "productStream": tr.productStream, "productBasis": tr.productBasis,
                              "overallRecovery": tr.overallRecovery, "units": [u.id for u in tr.units],
                              "runsOnFile": tr.runs, "tablesSource": tr.tablesSource, "note": tr.note,
                              "cite": "cite the train or a unit of it by its ref; its numbers are read from the run artifact"})
            for u in tr.units:
                yield Row("pureos", "train-unit", f"{key}:{u.id}", f"{u.id} ({u.unitClass}) in the train of {name}", "open",
                          "computed", provenance=mark, id_names=False, alt_ids=(key, *ids),
                          words=" ".join([u.unitClass, operation.get(u.unitClass, ""), tr.flowsheet or ""]),
                          detail={"artifactId": a.id, "unit": u.id, "unitClass": u.unitClass,
                                  "operation": operation.get(u.unitClass), "order": u.order, "onPath": u.onPath,
                                  "product": tr.product, "productIn": u.productIn, "productOut": u.productOut,
                                  "productLost": u.productLost, "lostTo": u.lostTo, "recovery": u.recovery,
                                  "cumulative": u.cumulative, "massIn": u.massIn, "massOut": u.massOut, "note": u.note,
                                  "unitOfMass": tr.tableUnits.get("massFlow")})

    def _scenario_rows(self) -> list[dict[str, Any]]:
        """The project's scenarios, and any a test handed in the projection."""
        return [*self._get("scenarios"), *self._get("projection")["proforma"]["scenarios"]]

    def _proforma(self) -> Iterable[Row]:
        for s in self._scenario_rows():
            yield Row("proforma", "scenario", s["id"], s["name"], "open", s["kind"],
                      words=" ".join([s.get("product") or "", s.get("modelId") or ""]),
                      detail={"kind": s["kind"], "product": s.get("product"), "modelId": s.get("modelId")})
        yield from self._artifacts("proforma")

    def _biorepo(self) -> Iterable[Row]:
        for r in self.pool().records:
            kind = "candidate" if r.get("source") == "candidate" else "record"
            yield Row("biorepo", kind, r["id"], r.get("measurement") or r.get("field") or r["id"],
                      record_state(r.get("provenance"), r.get("status")), r.get("provenance") or "unverified",
                      provenance=r.get("provenance") or "unverified",
                      words=" ".join(str(r.get(k) or "") for k in ("field", "paperId", "strainId", "organism", "productId",
                                                                   "carbonSource")),
                      detail={"paperId": r.get("paperId"), "field": r.get("field"), "strainId": r.get("strainId")},
                      species=self._species_of([r.get("strainId"), r.get("organism")]))
        for a in self._get("artifacts"):
            yield _artifact_row("biorepo", a, self._artifact_mark(a))
        for run in self._get("witness"):
            outcomes: dict[str, int] = {}
            for x in run.results:
                outcomes[x.outcome] = outcomes.get(x.outcome, 0) + 1
            # A run's scores are provisional until a person has decided every
            # record they rest on; Witness says so, and so does the row.
            yield Row("biorepo", "witness-run", run.run, f"Witness run {run.run}", "open", "provisional",
                      words="witness extractor run", detail={"outcomes": outcomes, "falsePositives": len(run.falsePositives),
                                                             "models": run.models})

    def _guild(self) -> Iterable[Row]:
        # Personnel fields are reduced to what the ledger shows: a name, a
        # role and whether the person is active. Levels are computed by the
        # browser and are never stored, so none is read here.
        ledger = self._get("guild")
        for person in ledger.people:
            yield Row("guild", "person", person.id, person.name, "open" if person.active else "retired",
                      "active" if person.active else "inactive", words=person.role, detail={"role": person.role})
        for c in self._get("checks").checks:
            yield Row("guild", "check", c.id, f"Check on {', '.join(c.skillIds)}", check_state(c.state), c.state,
                      words=" ".join(c.skillIds), detail={"skillIds": c.skillIds})

    def _primer(self) -> Iterable[Row]:
        for lesson in self._get("projection")["primer"]["lessons"]:
            yield Row("primer", "lesson", lesson["id"], lesson["title"], "approved", "published",
                      words=" ".join([lesson["moduleTitle"], lesson.get("blurb") or ""] + lesson.get("skills", [])),
                      detail={"module": lesson["moduleTitle"], "skills": lesson.get("skills", [])})

    def _intake(self) -> Iterable[Row]:
        for document_id, held in self._get("intake").items():
            title = str(held.get("title") or document_id)
            yield Row("intake", "source", document_id, title, "approved", "held",
                      words=str(held.get("year") or ""),
                      detail={"collector": held.get("collector"), "licenceClass": held.get("licenceClass"),
                              "passages": held.get("passages")}, id_names=False,
                      species=self._species_of([]))

    def _home(self) -> Iterable[Row]:
        for r in self.pool().records:
            if r.get("source") == "candidate" and record_state(r.get("provenance"), r.get("status")) == "proposed":
                yield Row("home", "review", r["id"], f"Awaiting review: {r.get('measurement') or r['id']}", "proposed",
                          "awaiting review", detail={"paperId": r.get("paperId")})
        for c in self._get("checks").checks:
            if c.state in ("proposed", "scheduled"):
                # Who a check names is never shown before it is run.
                yield Row("home", "check", c.id, f"Open check on {', '.join(c.skillIds)}", check_state(c.state), c.state,
                          detail={"skillIds": c.skillIds})
        from .proposals import shown

        for p in map(shown, self._get("proposals")):
            # What a model asked for at a gate (§7.4), waiting for a person,
            # as a reader sees it: a Guild proposal without its words, since
            # who a check names is never shown before it is run (OF-BLD-016
            # §1.R finding 9).
            yield Row("home", "proposal", p.id, p.title, "proposed", p.gate, words=" ".join([p.module, p.action, p.why]),
                      detail={"module": p.module, "action": p.action, "gate": p.gate, "how": p.how, "by": p.by, "at": p.at})


# ── reading, for the read tools ───────────────────────────────────────────

KINDS = {
    "runbooks": ("runbook", "protocol"),
    "geneos": ("host", "pathway", "model", "artifact"),
    "fermos": ("artifact", "simulation", "vessel"),
    "pureos": ("unit-operation", "train", "train-unit", "train-run"),
    "proforma": ("scenario", "artifact"),
    "biorepo": ("record", "candidate", "artifact", "witness-run"),
    "guild": ("person", "check"),
    "primer": ("lesson",),
    "intake": ("source",),
    "home": ("review", "check", "proposal"),
}


def _tokens(text: str) -> set[str]:
    from .evidence_pool import tokenize

    return set(tokenize(text))


def find(stores: Stores, module: str, *, ids: Iterable[str] = (), words: str = "", kind: str | None = None,
         state: str | None = None) -> list[Row]:
    """A module's rows by id or ref, by words, by kind and by state; every
    filter given is applied. Words rank by how many of them a row holds, its
    label, names and words together; a row holding none is left out."""
    rows = stores.rows(module)
    if kind:
        rows = [r for r in rows if r.kind == kind]
    if state:
        rows = [r for r in rows if r.state == state]
    wanted = {i.strip() for i in ids if i.strip()}
    if wanted:
        rows = [r for r in rows if r.id in wanted or r.ref in wanted or wanted.intersection(r.alt_ids)]
    query = _tokens(words)
    if query:
        scored = []
        for n, r in enumerate(rows):
            have = _tokens(" ".join([r.label, r.id, r.words, *r.names]))
            # A query word matches a row word whole, or as its head when
            # four letters or longer: "depos" finds "deposition", "polymer"
            # finds "polymerase".
            score = sum(1 for q in query if q in have or (len(q) >= PREFIX_MIN and any(h.startswith(q) for h in have)))
            if score:
                scored.append((-score, n, r))
        rows = [r for _, _, r in sorted(scored, key=lambda x: (x[0], x[1]))]
    return rows


# ── matching ──────────────────────────────────────────────────────────────

_NON_WORD = re.compile(r"[^0-9a-zÀ-ɏͰ-Ͽ]+")


def norm(text: str) -> str:
    return " ".join(_NON_WORD.sub(" ", text.lower()).split())


def _names(row: Row) -> list[str]:
    out = {norm(row.label)} | {norm(n) for n in row.names}
    if row.id_names:
        out.add(norm(row.id))
    return [n for n in out if len(n) >= MIN_NAME]


_SPECIES = re.compile(r"^([A-Z][a-z]{2,}) ([a-z]{3,})\b")


def species_of(label: str) -> str | None:
    """"saccharomyces cerevisiae" from "Saccharomyces cerevisiae S288C": a
    label that opens with a genus and an epithet. None for anything else
    ("E. coli K-12 …" names no genus in full)."""
    m = _SPECIES.match(label or "")
    return f"{m.group(1).lower()} {m.group(2)}" if m else None


def species_spellings(species: str) -> tuple[str, str]:
    """A species in full and abbreviated, normalised: ("saccharomyces
    cerevisiae", "s cerevisiae")."""
    genus, epithet = species.split(" ", 1)
    return species, f"{genus[0]} {epithet}"


def named_rows(question: str, rows: Iterable[Row]) -> list[tuple[Row, str]]:
    """Rows whose label, id or a spelling stands in the question as whole
    words, with the spelling that matched; and rows of a species the question
    names in full or abbreviated (OF-BLD-016 D10)."""
    q = f" {norm(question)} "
    out = []
    for row in rows:
        for name in sorted(_names(row), key=len, reverse=True):
            if f" {name} " in q:
                out.append((row, name))
                break
        else:
            for sp in row.species:
                full, short = species_spellings(sp)
                if f" {full} " in q or f" {short} " in q:
                    out.append((row, full))
                    break
    return out


_CLAUSE = re.compile(r"[,;:?!.]|\band\b|\bwhich\b|\bwhat\b|\bthat\b", re.IGNORECASE)


def _states_in(text: str) -> set[str]:
    words = set(norm(text).split())
    return {state for word, state in STATE_WORDS.items() if word in words}


def states_asked(question: str, module: str | None = None) -> set[str]:
    """The states the question asks about. Given a module, only those asked in
    a clause that names it: in "what is open in Proforma and which runbooks
    touch it", open is asked of Proforma and not of the runbooks."""
    if module is None:
        return _states_in(question)
    out: set[str] = set()
    for clause in _CLAUSE.split(question):
        if module_named(module, clause):
            out |= _states_in(clause)
    return out


def module_named(module: str, question: str) -> bool:
    words = set(norm(question).split())
    return any(w in words for w in MODULE_WORDS[module])


def coverage(question: str, stores: Stores | None = None) -> CoverageMap:
    """Every module swept for what the question names, in code."""
    stores = stores or Stores()
    entities: list[str] = []
    out: list[ModuleCoverage] = []
    for module in MODULES:
        rows = stores.rows(module)
        named = module_named(module, question)
        asked = states_asked(question, module) if named else set()
        matched = named_rows(question, rows)
        for _, name in matched:
            if name not in entities:
                entities.append(name)
        hits = [row for row, _ in matched]
        if not hits and named:
            # The question names the module and nothing in it: what it holds,
            # in the states the question asks about, when it asks.
            hits = [r for r in rows if not asked or r.state in asked]
        elif asked and named:
            hits = [r for r in hits if r.state in asked] or hits
        out.append(ModuleCoverage(module=module, label=LABEL[module], count=len(hits),  # type: ignore[arg-type]
                                  hits=[r.hit() for r in hits[:COVERAGE_HITS]], named=named,
                                  partial=PARTIAL.get(module), error=stores.error(module)))
    return CoverageMap(entities=entities, searched=len(out), found=sum(1 for m in out if m.count), modules=out)


NUMBER_WORDS = ("no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve")


def in_words(n: int) -> str:
    return NUMBER_WORDS[n] if 0 <= n < len(NUMBER_WORDS) else str(n)


def footer(cmap: CoverageMap) -> str:
    """`searched ten, found in three`, as the trace and the footer say it."""
    return f"searched {in_words(cmap.searched)}, found in {in_words(cmap.found) if cmap.found else 'none'}"


def for_model(cmap: CoverageMap, said_in: str = "question") -> str:
    """The map as the first turn reads it: one line a module, ids and states,
    and what was read only in part. `said_in` is "conversation" for a
    follow-up, which is swept with the questions it follows."""
    lines = [
        "COVERAGE MAP, built by code before you began. It says which of the app's modules hold what this "
        f"{said_in} names. When a module below found something, do not say the app or the corpus holds nothing "
        "about it: read that module with its tool and answer from what it returns, or say in `gaps` why you could not. "
        "The refs below are for reading and are not citable: a ref goes in a claim's moduleRefs only after a "
        "read tool returns it in this conversation, and a claim citing one no read tool returned is discarded.",
        f"Names found in the {said_in}: {', '.join(cmap.entities) or 'none'}.",
    ]
    for m in cmap.modules:
        if m.error:
            lines.append(f"- {m.label}: could not be read ({m.error})")
            continue
        head = f"- {m.label}: {m.count} matching" + (" (the question names this module)" if m.named else "")
        if m.hits:
            head += ": " + "; ".join(f"{h.ref} {h.label!r} {h.state}" for h in m.hits)
            if m.count > len(m.hits):
                head += f"; and {m.count - len(m.hits)} more"
        if m.partial:
            head += f". Read in part: {m.partial}"
        lines.append(head)
    return "\n".join(lines)


def trace_lines(cmap: CoverageMap) -> list[str]:
    """One line a module for the trace, written by code."""
    out = []
    for m in cmap.modules:
        if m.error:
            out.append(f"{m.label} · could not be read")
            continue
        line = f"{m.label} · {m.count}"
        if m.hits:
            line += " · " + ", ".join(h.id for h in m.hits[:3]) + (" …" if m.count > 3 else "")
        if m.partial:
            line += " · read in part"
        out.append(line)
    return out
