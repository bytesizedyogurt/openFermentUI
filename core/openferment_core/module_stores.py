"""Every module's store, read the same way (OF-BLD-015 §7.1, §7.2).

Postdoc was asked what is open in Dominion and answered that the corpus held
nothing, while Dominion showed the molecules: it could read records and
passages and nothing else. This module reads all eleven destinations behind
Home's rail and gives every row one shape, `Row`: the module, the kind of
row, its id, a label, the module's own word for where it stands, and the one
`state` Postdoc reads, which is computed here from that word.

Where each module's rows come from:

- the TypeScript seed, through `modules.json`, which `pnpm export:corpus`
  writes beside `corpus.json` (Dominion's molecules and clearance findings,
  the runbooks and protocols, geneOS's hosts and pathways, pureOS's unit
  operations, Proforma's scenarios, Primer's lessons);
- the service's own stores (records and candidates through the evidence
  pool, artifacts, Guild's ledger and checks, Intake's fetch state, the
  geneOS shelf).

Some of a module lives only in a browser (depositions, unposted review
decisions, runbooks adopted and locked there). `PARTIAL` names it, and the
answer's footer says the module was read in part. Nothing here syncs.

`coverage(question)` is code and calls no model: it finds the rows the
question names, and the modules it names, before Postdoc's first turn.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

from .models import CoverageHit, CoverageMap, ModuleCoverage, ModuleRow

PROJECTION = Path(__file__).parent / "data" / "modules.json"

# The rail's order (src/data/nav.ts), Home last because it gathers the rest.
MODULES = ("dominion", "runbooks", "geneos", "fermos", "pureos", "proforma", "biorepo", "guild", "primer", "intake",
           "home")
LABEL = {
    "dominion": "Dominion", "runbooks": "Runbooks", "geneos": "geneOS", "fermos": "fermOS", "pureos": "pureOS",
    "proforma": "Proforma", "biorepo": "BioRepo", "guild": "Guild", "primer": "Primer", "intake": "Intake",
    "home": "Home",
}
STATES = ("open", "fenced", "approved", "locked", "proposed", "retired")

# What the service cannot see of a module, said once, in the footer's words.
PARTIAL = {
    "runbooks": "depositions, and runbooks adopted or locked in a browser, stay in that browser; "
                "the service read the seed's runbooks and protocols",
    "fermos": "depositions stay in the browser; the service read the fits and forecasts it computed",
    "biorepo": "review decisions not yet posted from a browser stay in that browser",
    "home": "proposals awaiting a person arrive with OF-BLD-015 §7.4; the service read the review queue and open checks",
}

# Words that name a module itself. Common nouns ("record", "host") are left
# out: they would name a module in nearly every question.
MODULE_WORDS = {
    "dominion": ("dominion", "clearance"),
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

def clearance_state(clearance: str) -> str:
    """A molecule or finding is open when its foundational IP is expired or no
    blocking claim was found; every other clearance is fenced, `unknown`
    included: Dominion's action for it is to run clearance before any
    commitment, so nothing may be made on it yet."""
    return "open" if clearance in ("clear-expired", "clear-none") else "fenced"


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
    if ingest == "complete":
        return "approved"
    if ingest.startswith("failed"):
        return "fenced"
    return "proposed"


# ── the sources ───────────────────────────────────────────────────────────

class ProjectionMissing(FileNotFoundError):
    pass


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


def _projection() -> dict[str, Any]:
    if not PROJECTION.exists():
        raise ProjectionMissing(f"{PROJECTION.name} is missing; run `pnpm export:corpus`")
    return json.loads(PROJECTION.read_text())


def _strain_aliases() -> dict[str, str]:
    from .validate import CORPUS_PATH

    return json.loads(CORPUS_PATH.read_text()).get("strainAliases") or {}


def default_sources(pool_factory: Callable[[], Any] | None = None) -> Sources:
    from . import artifacts, checks, evidence_pool, geneos, guild, intake, witness

    return Sources(
        projection=_projection,
        pool=pool_factory or evidence_pool.load,
        artifacts=artifacts.all_artifacts,
        guild=guild.read,
        checks=checks.read,
        intake=intake.all_statuses,
        shelf=geneos.models,
        strain_aliases=_strain_aliases,
        witness=witness.runs,
    )


def seed_sources(pool_factory: Callable[[], Any]) -> Sources:
    """The seed's modules and the given pool, with every store this machine
    keeps (artifacts, the ledger, checks, fetches, the shelf) empty: what a
    fixture sweeps, so it reads the same on every machine."""
    from .models import Checks, Guild

    return Sources(projection=_projection, pool=pool_factory, artifacts=list, guild=Guild, checks=Checks,
                   intake=dict, shelf=list, strain_aliases=_strain_aliases)


# ── rows per module ───────────────────────────────────────────────────────

ARTIFACT_MODULE = {
    "growth_fit": "fermos", "kinetic_fit": "fermos", "growth_forecast": "fermos",
    "geneos.ceiling": "geneos", "geneos.frontier": "geneos", "geneos.mix": "geneos",
    "proforma.run": "proforma", "proforma_benchmark": "proforma",
}


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


def _artifact_row(module: str, a: Any) -> Row:
    inputs = [f"{i.name}={i.value}" for i in a.inputs if isinstance(getattr(i, "value", None), str)][:MAX_ITEMS]
    return Row(module=module, kind="artifact", id=a.id, label=f"{a.tool} artifact", state="open", status="computed",
               provenance=a.provenance, words=" ".join([a.tool, *inputs]),
               detail={"tool": a.tool, "createdAt": a.createdAt, "inputs": inputs, "output": _headline(a.output),
                       "cite": "cite the value through get_artifact or the tool that computes it; this row names it"})


class Stores:
    """Every module's rows, loaded on first use and kept for one question."""

    def __init__(self, sources: Sources | None = None, pool_factory: Callable[[], Any] | None = None) -> None:
        self.sources = sources or default_sources(pool_factory)
        self._rows: dict[str, list[Row]] = {}
        self._errors: dict[str, str] = {}
        self._cache: dict[str, Any] = {}

    def _get(self, name: str) -> Any:
        if name not in self._cache:
            self._cache[name] = getattr(self.sources, name)()
        return self._cache[name]

    def pool(self) -> Any:
        return self._get("pool")

    def rows(self, module: str) -> list[Row]:
        if module not in self._rows:
            try:
                self._rows[module] = list(getattr(self, f"_{module}")())
            except Exception as e:  # one module failing is said, and the rest are read
                self._rows[module] = []
                self._errors[module] = f"{LABEL[module]} could not be read: {type(e).__name__}: {e}"
        return self._rows[module]

    def error(self, module: str) -> str | None:
        self.rows(module)
        return self._errors.get(module)

    def _artifacts(self, module: str) -> Iterable[Row]:
        for a in self._get("artifacts"):
            if ARTIFACT_MODULE.get(a.tool) == module:
                yield _artifact_row(module, a)

    def _dominion(self) -> Iterable[Row]:
        p = self._get("projection")["dominion"]
        for m in p["molecules"]:
            yield Row("dominion", "molecule", m["id"], m["name"], clearance_state(m["clearanceState"]), m["clearanceState"],
                      provenance=m.get("provenance"), names=tuple(m.get("aliases") or ()),
                      words=" ".join([m["category"], m["clearanceLabel"], m.get("note") or "", m.get("processCode") or ""]
                                     + (m.get("unitOperationIds") or []) + (m.get("pathwayIds") or [])),
                      # The train and the pathways are the seams to pureOS and
                      # geneOS: their ids are what pureos_read and geneos_read take.
                      detail={"clearance": m["clearanceLabel"], "category": m["category"],
                              "defaultStrainId": m.get("defaultStrainId"), "processCode": m.get("processCode"),
                              "unitOperationIds": m.get("unitOperationIds") or [], "pathwayIds": m.get("pathwayIds") or [],
                              "note": m.get("note")})
        for f in p["findings"]:
            fid = f"{f['productId']}.{f['jurisdictionId']}"
            yield Row("dominion", "finding", fid, f"Clearance finding: {f['productId']} in {f['jurisdictionId']}",
                      clearance_state(f["state"]), f["state"], provenance=f.get("provenance"),
                      words=" ".join([f["productId"], f.get("summary") or ""] + [x["title"] for x in f.get("patents") or []]),
                      detail={"productId": f["productId"], "jurisdiction": f["jurisdictionId"], "summary": f.get("summary"),
                              "readAt": f.get("readAt"), "patents": f.get("patents") or []})

    def _runbooks(self) -> Iterable[Row]:
        p = self._get("projection")["runbooks"]
        for r in p["runbooks"]:
            # Named by its title, the title's head ("Brazzein" of "Brazzein —
            # pilot process") and the molecule it makes, so a question about a
            # molecule finds the runbooks that touch it.
            names = tuple(n for n in (r["title"].split(" — ")[0], r.get("productId")) if n)
            yield Row("runbooks", "runbook", r["id"], r["title"], runbook_state(r["status"], r.get("lockedAt")), r["status"],
                      names=names,
                      words=" ".join([r["kind"], r.get("productId") or "", r.get("strainId") or ""] + r.get("predictions", [])),
                      detail={"kind": r["kind"], "productId": r.get("productId"), "strainId": r.get("strainId"),
                              "lockedAt": r.get("lockedAt"), "predictions": r.get("predictions", [])})
        for x in p["protocols"]:
            yield Row("runbooks", "protocol", x["id"], x["title"], "approved", f"version {x['currentVersion']} current",
                      words=" ".join([x["category"], x.get("purpose") or ""] + x.get("organisms", [])),
                      detail={"category": x["category"], "organisms": x.get("organisms", []),
                              "currentVersion": x["currentVersion"], "versions": x.get("versions", [])})

    def _geneos(self) -> Iterable[Row]:
        p = self._get("projection")["geneos"]
        aliases: dict[str, list[str]] = {}
        for alias, sid in self._get("strain_aliases").items():
            aliases.setdefault(sid, []).append(alias)
        for h in p["hosts"]:
            yield Row("geneos", "host", h["id"], h["name"], "open", "in the catalogue",
                      names=tuple(aliases.get(h["id"], ())), words=" ".join(h.get("badges") or []),
                      detail={"bsl": h.get("bsl"), "badges": h.get("badges") or []})
        for x in p["pathways"]:
            yield Row("geneos", "pathway", x["id"], x["label"], "open", "in the catalogue",
                      words=" ".join(x.get("products") or []), detail={"products": x.get("products") or []})
        for m in self._get("shelf"):
            ok = m.unavailable is None
            yield Row("geneos", "model", m.id, m.name, "open" if ok else "fenced", "on the shelf" if ok else "not fetched",
                      words=m.host or "", detail={"host": m.host, "unavailable": m.unavailable})
        yield from self._artifacts("geneos")

    def _fermos(self) -> Iterable[Row]:
        yield from self._artifacts("fermos")

    def _pureos(self) -> Iterable[Row]:
        for u in self._get("projection")["pureos"]["unitOperations"]:
            yield Row("pureos", "unit-operation", u["id"], u["label"], "open", "in the vocabulary",
                      words=" ".join([u["stage"], u.get("note") or ""]), detail={"stage": u["stage"], "note": u.get("note")})

    def _proforma(self) -> Iterable[Row]:
        for s in self._get("projection")["proforma"]["scenarios"]:
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
                      detail={"paperId": r.get("paperId"), "field": r.get("field"), "strainId": r.get("strainId")})
        for a in self._get("artifacts"):
            yield _artifact_row("biorepo", a)
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
        fetched = self._get("intake")
        for paper in self.pool().corpus.papers:
            status = fetched.get(paper["id"])
            ingest = status.ingest if status is not None else str(paper.get("ingest") or "queued")
            yield Row("intake", "source", paper["id"], paper.get("title") or paper["id"], intake_state(ingest), ingest,
                      words=str(paper.get("year") or ""),
                      detail={"textSource": status.textSource if status is not None else paper.get("textSource"),
                              "reason": status.reason if status is not None else None}, id_names=False)

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


# ── reading, for the read tools ───────────────────────────────────────────

KINDS = {
    "dominion": ("molecule", "finding"),
    "runbooks": ("runbook", "protocol"),
    "geneos": ("host", "pathway", "model", "artifact"),
    "fermos": ("artifact",),
    "pureos": ("unit-operation",),
    "proforma": ("scenario", "artifact"),
    "biorepo": ("record", "candidate", "artifact", "witness-run"),
    "guild": ("person", "check"),
    "primer": ("lesson",),
    "intake": ("source",),
    "home": ("review", "check"),
}


def _tokens(text: str) -> set[str]:
    from .corpus import tokenize

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
        rows = [r for r in rows if r.id in wanted or r.ref in wanted]
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


def named_rows(question: str, rows: Iterable[Row]) -> list[tuple[Row, str]]:
    """Rows whose label, id or a spelling stands in the question as whole
    words, with the spelling that matched."""
    q = f" {norm(question)} "
    out = []
    for row in rows:
        for name in sorted(_names(row), key=len, reverse=True):
            if f" {name} " in q:
                out.append((row, name))
                break
    return out


_CLAUSE = re.compile(r"[,;:?!.]|\band\b|\bwhich\b|\bwhat\b|\bthat\b", re.IGNORECASE)


def _states_in(text: str) -> set[str]:
    words = set(norm(text).split())
    return {state for word, state in STATE_WORDS.items() if word in words}


def states_asked(question: str, module: str | None = None) -> set[str]:
    """The states the question asks about. Given a module, only those asked in
    a clause that names it: in "what is open in Dominion and which runbooks
    touch it", open is asked of Dominion and not of the runbooks."""
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
    """`searched eleven, found in three`, as the trace and the footer say it."""
    return f"searched {in_words(cmap.searched)}, found in {in_words(cmap.found) if cmap.found else 'none'}"


def for_model(cmap: CoverageMap) -> str:
    """The map as the first turn reads it: one line a module, ids and states,
    and what was read only in part."""
    lines = [
        "COVERAGE MAP, built by code before you began. It says which of the app's modules hold what this question "
        "names. When a module below found something, do not say the app or the corpus holds nothing about it: "
        "read that module with its tool and answer from what it returns, or say in `gaps` why you could not.",
        f"Names found in the question: {', '.join(cmap.entities) or 'none'}.",
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
