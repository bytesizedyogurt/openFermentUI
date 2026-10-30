"""One tool registry, three callers (OF-BLD-014 §3.4, E.6).

Postdoc's loop, the HTTP endpoints (`GET /api/tools`, `POST /api/tools/{name}`)
and the MCP server all run a tool through `run`, so a rule enforced here is
enforced for every caller.

The whitelist is closed, added phase by phase: `search_records` and
`convert_units` (OF-BLD-014 Phase 3), `search_passages` (5), `yield_ceiling`
(6), `growth_forecast` (7), `selling_price` (8), `draft_runbook` (9); then one
read tool per module (OF-BLD-015 §7.2), written `<module>_read` because the
Messages API refuses a dot in a tool name, and its write pair (§7.3); then
`thermo_props` (OF-BLD-019 §4.2), a read offered loose; then Proforma's two
(OF-BLD-019 §6.1): `run_flowsheet`, a free write through `proforma.run`, and
`stream_table`, a read of a kept run's streams; then fermOS's two (OF-BLD-020):
`fermos_simulate` (§3.4), a free write through `fermos.simulate`, and
`fermos_vessel` (§4.2), a free write through `fermos_write`'s `design_vessel`;
then pureOS's `pureos_build` (OF-BLD-020 §5.4), a free write through
`pureos_write`'s train actions that builds and runs a train from unit type
names and record ids; then `pureos_propose` (§7.2), a read: a train proposed
by written rules, each naming the property it read; then the study tools of
alpha 2.0 stage 6 (execution prompt §4.6, §10 stage 6): `engine_plants`,
`engine_parameters`, `engine_run` and `engine_report` over the library shelf
and the project's runs, `study_scenario`, `study_compare` and `study_read`
over its studies, and `literature_sources` and `literature_document` over the
documents it holds. Forty-three names. A tool outside it is a new decision.
`test_tools.NAMES` is the one literal list the tests hold the registry to;
every other count is derived from `WHITELIST`. `docs/TOOLS.md` is written
from this registry (`pnpm gen:tools`).

TOOL INPUTS CARRY IDS, WORDS AND QUANTITIES (ADR-006). A model names a
record, an artifact, a model file, a field or a scenario, and the service
looks the quantity up. A number stands only inside a quantity, an object of
`value` and `unit` (and `low` and `high` for a range), and only where a tool
asks for one; a JSON number anywhere else, outside the two count fields `k`
and `limit`, refuses the call, the refusal reaching the model as the result's
`error`, and nothing runs. The service writes each quantity's origin from who
called (`ToolContext.author`): the answering model's estimate, with its id,
or a named person's assumption; of what the caller wrote there, the note
alone is kept. A quantity nobody can be named for is refused.

EVERY TOOL ACTS IN ONE PROJECT (ADR-005): the request's, the question's, or
the one the MCP server was started in (`ToolContext.project`).

TOOL OUTPUT DISCIPLINE. A tool summarises in code before a model reads
anything. `summary` is at most `MAX_SUMMARY_CHARS` as JSON; a tool that
returns more is a defect in the tool, and the result says so in place of the
oversized summary. A tool whose whole output is larger (a stream table) cuts
its own summary, says how much it left out, and carries the whole in `data`,
which the endpoint and the MCP server return and no model reads.
"""
from __future__ import annotations

import contextlib
import functools
import json
import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from pydantic.json_schema import SkipJsonSchema

from ..models import Origin, Quantity, ToolInfo, ToolResult

# The names E.6, OF-BLD-015, OF-BLD-019 §6.1 and OF-BLD-020 allow, whichever have been built.
WHITELIST = (
    "search_records",
    "convert_units",
    "search_passages",
    "yield_ceiling",
    "growth_forecast",
    "selling_price",
    "draft_runbook",
    # OF-BLD-015 §7.2 — one read tool per module, in the rail's order.
    "runbooks_read",
    "geneos_read",
    "fermos_read",
    "pureos_read",
    "proforma_read",
    "biorepo_read",
    "guild_read",
    "primer_read",
    "intake_read",
    "home_read",
    # OF-BLD-015 §7.3 — its pair, one write tool per module.
    "runbooks_write",
    "geneos_write",
    "fermos_write",
    "pureos_write",
    "proforma_write",
    "biorepo_write",
    "guild_write",
    "primer_write",
    "intake_write",
    "home_write",
    # OF-BLD-019 §4.2 — thermosteam answers property questions, a read.
    "thermo_props",
    # OF-BLD-019 §6.1 — a flowsheet run and the stream table it kept, both
    # loose (the module tools' grammar, §7.2).
    "run_flowsheet",
    "stream_table",
    # OF-BLD-020 §3.4 — a simulation from a model family, record ids and
    # words, a free write, loose like the module tools.
    "fermos_simulate",
    # OF-BLD-020 §4.2 — the vessel a kept simulation needs, designed on
    # BioSTEAM: a free write through fermos_write's design_vessel, loose.
    "fermos_vessel",
    # OF-BLD-020 §5.4 — a train built and run from unit type names and record
    # ids: a free write through pureos_write's train actions, loose.
    "pureos_build",
    # OF-BLD-020 §7.2 — a train proposed by written rules that each name the
    # property they read: a read, loose, ids and words in.
    "pureos_propose",
    # Alpha 2.0 stage 6 — the library shelf and the project's runs, its
    # studies, and the documents it holds; loose like the module tools.
    "engine_plants",
    "engine_parameters",
    "engine_run",
    "engine_report",
    "study_scenario",
    "study_compare",
    "study_read",
    "literature_sources",
    "literature_document",
)
# The fields a number may stand in outside a quantity: how many results to return.
COUNT_FIELDS = frozenset({"k", "limit"})
# The fields a number may stand in inside a quantity (ADR-006): its value and its range.
QUANTITY_FIELDS = frozenset({"value", "low", "high"})
MAX_SUMMARY_CHARS = 9_000


@dataclass
class ToolContext:
    """What a tool may read. Built lazily, so a tool that needs no pool
    never loads one, and a test can hand in a fixture."""

    pool_factory: Callable[[], Any] | None = None
    _pool: Any = field(default=None, repr=False)
    # What this run's tool calls returned (validate.SeenSet), when a loop
    # owns the run; draft_runbook accepts only ids in it (§9.2).
    seen: Any = None
    # Every module's store (module_stores.Stores), read on first use; its
    # records come from this context's pool (OF-BLD-015 §7.1). A fixture
    # hands in its own factory.
    stores_factory: Callable[[], Any] | None = None
    _stores: Any = field(default=None, repr=False)
    # The ask this run belongs to, on every audit line a write makes (§7.3);
    # empty for a call from the endpoint or the MCP server.
    ask_id: str = ""
    # The model answering this run, set by the loop before it runs a turn's
    # tools, so an audit line names the model that asked for the write and
    # not the chain's first name; empty for a call from outside the app.
    model: str = ""
    # The person calling, named at the HTTP endpoint (`?by=`): the author of a
    # quantity the call types when no model is answering.
    person: str = ""
    # The project the call acts in; None acts in the current one (the
    # request's or the command's, projects.current).
    project: str | None = None

    def author(self) -> Origin | None:
        """The origin of a number this call types into a tool (ADR-006): the
        answering model's estimate, or the named person's assumption; None
        when nobody can be named."""
        at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        if self.model.strip():
            return Origin(kind="model-estimate", by=self.model.strip(), at=at)
        if self.person.strip():
            return Origin(kind="person-assumption", by=self.person.strip(), at=at)
        return None

    @property
    def pool(self) -> Any:
        if self._pool is None:
            if self.pool_factory is None:
                from .. import evidence_pool

                self.pool_factory = lambda: evidence_pool.load()
            self._pool = self.pool_factory()
        return self._pool

    @property
    def stores(self) -> Any:
        if self._stores is None:
            if self.stores_factory is None:
                from .. import module_stores

                self.stores_factory = lambda: module_stores.Stores(pool_factory=lambda: self.pool)
            self._stores = self.stores_factory()
        return self._stores


@dataclass(frozen=True)
class Tool:
    name: str
    # One paragraph, plain words, says what it returns.
    description: str
    # Small, mostly required fields (B.4's limits on strict schemas).
    input_model: type[BaseModel]
    run: Callable[[BaseModel, ToolContext], ToolResult]
    # Whether the model is offered it strict. The API compiles one grammar for
    # every strict tool in a request and refuses one that grows too large;
    # `run` validates the input of every tool alike, strict or not.
    strict: bool = True
    # Whether it keeps something new in the project (a run, a scenario, a
    # train, a candidate, a proposal), audited as its caller's; a read keeps
    # nothing but the computations it caches.
    writes: bool = False
    # Every tool acts in one project (ADR-005; acceptance A5): the request's,
    # the question's, or the MCP server's. None acts across projects.
    scope: str = "project"

    def info(self) -> ToolInfo:
        return ToolInfo(name=self.name, description=self.description, inputSchema=self.input_model.model_json_schema())


# A number as a caller types it into a tool (ADR-006). The registry writes
# its origin from who called (`stamped`), so the caller's own is never read.
class QuantityIn(BaseModel):
    """A number you type: a value in a unit, and in words what it rests on.
    The service marks it with who typed it."""

    # A range or any other field is refused in words, never dropped unread.
    model_config = ConfigDict(extra="forbid")

    value: float
    unit: str = Field(max_length=40, description="The value's unit, as the tool names it.")
    note: str = Field(default="", max_length=600, description="What the value rests on, in words.")
    origin: SkipJsonSchema[Origin | None] = None

    @field_validator("value", mode="before")
    @classmethod
    def _a_number(cls, v: Any) -> Any:
        if isinstance(v, bool):
            raise ValueError("a quantity's value is a number, never true or false")
        return v

    def quantity(self) -> Quantity:
        return Quantity(value=self.value, unit=self.unit, origin=self.origin)


REGISTRY: dict[str, Tool] = {}


def register(tool: Tool) -> Tool:
    if tool.name not in WHITELIST:
        raise ValueError(f"{tool.name!r} is not in WHITELIST; a tool outside it does not exist")
    REGISTRY[tool.name] = tool
    return tool


def is_quantity(value: Any) -> bool:
    """A quantity as a caller types one: an object with a `value` and a
    `unit` in words."""
    return isinstance(value, dict) and "value" in value and isinstance(value.get("unit"), str)


def quantity_paths(schema: dict[str, Any]) -> frozenset[str]:
    """Where a tool's input schema asks for a quantity: the path of each
    object of `value` and a string `unit`, a list's items written `[]`
    (`values[].quantity`)."""
    defs = schema.get("$defs") or {}
    found: set[str] = set()

    def walk(node: Any, path: str, seen: frozenset[str]) -> None:
        if not isinstance(node, dict):
            return
        if "$ref" in node:
            name = str(node["$ref"]).rsplit("/", 1)[-1]
            if name not in seen:
                walk(defs.get(name) or {}, path, seen | {name})
            return
        for key in ("anyOf", "oneOf", "allOf"):
            for sub in node.get(key) or []:
                walk(sub, path, seen)
        props = node.get("properties") or {}
        if "value" in props and (props.get("unit") or {}).get("type") == "string":
            found.add(path)
        for name, sub in props.items():
            walk(sub, f"{path}.{name}" if path else name, seen)
        if isinstance(node.get("items"), dict):
            walk(node["items"], f"{path}[]", seen)

    walk(schema, "", frozenset())
    return frozenset(found)


@functools.lru_cache(maxsize=None)
def _quantity_paths_of(name: str) -> frozenset[str]:
    return quantity_paths(REGISTRY[name].input_model.model_json_schema())


def _shape(path: str) -> str:
    return re.sub(r"\[\d+\]", "[]", path)


def numbers_in(value: Any, path: str = "", quantities: frozenset[str] = frozenset()) -> list[str]:
    """Where a JSON number stands in `value`, outside the count fields and
    outside the value and range of a quantity standing where the tool asks
    for one (`quantities`, from `quantity_paths`)."""
    found: list[str] = []
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return found
    if isinstance(value, (int, float)):
        return [path or "input"]
    if isinstance(value, dict):
        quantity = _shape(path) in quantities and is_quantity(value)
        for k, v in value.items():
            if k in COUNT_FIELDS and isinstance(v, int) and not isinstance(v, bool) and not path:
                continue
            if quantity and k in QUANTITY_FIELDS and isinstance(v, (int, float)) and not isinstance(v, bool):
                if not math.isfinite(float(v)):
                    found.append(f"{path}.{k}" if path else str(k))
                continue
            found += numbers_in(v, f"{path}.{k}" if path else str(k), quantities)
    elif isinstance(value, list):
        for n, v in enumerate(value):
            found += numbers_in(v, f"{path}[{n}]", quantities)
    return found


def quantities_in(value: Any, quantities: frozenset[str], path: str = "") -> bool:
    """Whether a quantity stands in `value` where the tool asks for one."""
    if _shape(path) in quantities and is_quantity(value):
        return True
    if isinstance(value, dict):
        return any(quantities_in(v, quantities, f"{path}.{k}" if path else str(k)) for k, v in value.items())
    if isinstance(value, list):
        return any(quantities_in(v, quantities, f"{path}[{n}]") for n, v in enumerate(value))
    return False


def stamped(value: Any, origin: Origin, quantities: frozenset[str], path: str = "") -> Any:
    """`value` with the origin of every quantity standing where the tool asks
    for one written by the service: `origin`, with the note the caller wrote
    beside the value (or in its origin), and nothing else the caller wrote
    there (ADR-006)."""
    if isinstance(value, list):
        return [stamped(v, origin, quantities, f"{path}[{n}]") for n, v in enumerate(value)]
    if not isinstance(value, dict):
        return value
    out = {k: stamped(v, origin, quantities, f"{path}.{k}" if path else str(k)) for k, v in value.items()}
    if _shape(path) in quantities and is_quantity(value):
        wrote = value.get("origin")
        note = value.get("note") if isinstance(value.get("note"), str) else (
            wrote.get("note") if isinstance(wrote, dict) and isinstance(wrote.get("note"), str) else None)
        out["origin"] = origin.model_copy(update={"note": (note or "").strip() or None}).model_dump(
            mode="json", exclude_none=True)
    return out


def run(name: str, raw: Any, ctx: ToolContext | None = None) -> ToolResult:
    """Run one tool on a raw input as a model or a client sent it, in the
    context's project. Every refusal is a result with `error` set; nothing
    here raises."""
    ctx = ctx or ToolContext()
    tool = REGISTRY.get(name)
    if tool is None:
        return ToolResult(error=f"There is no tool named {name!r}. The tools are: {', '.join(sorted(REGISTRY))}.")
    if not isinstance(raw, dict):
        return ToolResult(error=f"{name} takes an object of named fields.")
    quantities = _quantity_paths_of(name)
    numbers = numbers_in(raw, quantities=quantities)
    if numbers:
        return ToolResult(
            error=(
                f"{name} refused: a number was typed into {', '.join(numbers)}. Tool inputs carry ids, words and "
                "quantities; name a record, an artifact, a model, a field or a scenario, and the service looks the "
                "value up. A number stands only inside a quantity (value and unit, low and high) where a tool asks "
                "for one, and k and limit are counts."
            )
        )
    if quantities_in(raw, quantities):
        author = ctx.author()
        if author is None:
            return ToolResult(error=f"{name} refused: a quantity typed into a tool names who typed it, a model or a "
                                    "named person (at the HTTP endpoint, ?by= with the person's name)")
        raw = stamped(raw, author, quantities)
    try:
        parsed = tool.input_model.model_validate(raw)
    except ValidationError as e:
        problems = "; ".join(f"{'.'.join(str(p) for p in err['loc']) or 'input'}: {err['msg']}" for err in e.errors())
        return ToolResult(error=f"{name} refused its input: {problems}")
    try:
        from .. import projects

        with projects.using(ctx.project) if ctx.project else contextlib.nullcontext():
            result = tool.run(parsed, ctx)
    except Exception as e:  # a defect or an outage, said in words to the caller
        return ToolResult(error=f"{name} failed: {type(e).__name__}: {e}")
    size = len(json.dumps(result.summary, ensure_ascii=False, default=str))
    if size > MAX_SUMMARY_CHARS:
        # Nothing the model never read may become citable (§5.R): the ids go
        # with the summary. What the tool spent stays.
        return result.model_copy(
            update={
                "summary": {},
                "recordIds": [],
                "rows": [],
                "passages": [],
                "evidence": [],
                "data": None,
                "error": f"{name} returned a summary of {size} characters, over the {MAX_SUMMARY_CHARS} a model may read.",
            }
        )
    return result


def infos() -> list[ToolInfo]:
    return [REGISTRY[n].info() for n in WHITELIST if n in REGISTRY]


# The tools this phase builds register on import.
from . import engine as _engine  # noqa: E402,F401
from . import fermos as _fermos  # noqa: E402,F401
from . import geneos as _geneos  # noqa: E402,F401
from . import literature as _literature  # noqa: E402,F401
from . import modules as _modules  # noqa: E402,F401
from . import writes as _writes  # noqa: E402,F401
from . import passages as _passages  # noqa: E402,F401
from . import proforma as _proforma  # noqa: E402,F401
from . import pureos as _pureos  # noqa: E402,F401
from . import records as _records  # noqa: E402,F401
from . import runbook as _runbook  # noqa: E402,F401
from . import studies as _studies  # noqa: E402,F401
from . import thermo as _thermo  # noqa: E402,F401
from . import units as _units  # noqa: E402,F401
