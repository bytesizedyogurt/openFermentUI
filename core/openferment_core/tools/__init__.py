"""One tool registry, three callers (OF-BLD-014 §3.4, E.6).

Postdoc's loop, the HTTP endpoints (`GET /api/tools`, `POST /api/tools/{name}`)
and the MCP server all run a tool through `run`, so a rule enforced here is
enforced for every caller.

The whitelist is closed, added phase by phase: `search_records` and
`convert_units` (OF-BLD-014 Phase 3), `search_passages` (5), `yield_ceiling`
(6), `growth_forecast` (7), `selling_price` (8), `draft_runbook` (9); then one
read tool per module (OF-BLD-015 §7.2), written `<module>_read` because the
Messages API refuses a dot in a tool name. A tool outside it is a new
document.

TOOL INPUTS CARRY IDS AND WORDS. A model names a record, an artifact, a model
file, a field or a scenario, and the service looks the quantity up. A JSON
number anywhere in a tool's input, outside the two count fields `k` and
`limit`, refuses the call; the refusal reaches the model as the result's
`error`, and nothing runs.

TOOL OUTPUT DISCIPLINE. A tool summarises in code before a model reads
anything. `summary` is at most `MAX_SUMMARY_CHARS` as JSON; a tool that
returns more is a defect in the tool, and the result says so in place of the
oversized summary.

THE PROGRAM SWITCH (OF-BLD-016 §2.3) is not a tool input: no model sets it.
It rides in `ToolContext.include_archived`, from the request that started the
run (`AskRequest.includeArchived`, `?includeArchived=` on
`POST /api/tools/{name}`, the MCP server's environment), and the pool, the
passages and every module's rows read through it. Off is the default.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from pydantic import BaseModel, ValidationError

from ..models import ToolInfo, ToolResult

# The names E.6 and OF-BLD-015 allow, whichever have been built.
WHITELIST = (
    "search_records",
    "convert_units",
    "search_passages",
    "yield_ceiling",
    "growth_forecast",
    "selling_price",
    "draft_runbook",
    # OF-BLD-015 §7.2 — one read tool per module, in the rail's order.
    "dominion_read",
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
    "dominion_write",
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
)
# The only fields a number may stand in: how many results to return.
COUNT_FIELDS = frozenset({"k", "limit"})
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
    # The browser's "show archived programs" switch, from the request
    # (OF-BLD-016 §2.3). Off, the pool, the passages and the module rows
    # leave archived programs out. Never a tool input.
    include_archived: bool = False

    @property
    def pool(self) -> Any:
        if self._pool is None:
            if self.pool_factory is None:
                from .. import evidence_pool

                self.pool_factory = lambda: evidence_pool.load(include_archived=self.include_archived)
            self._pool = self.pool_factory()
        return self._pool

    @property
    def stores(self) -> Any:
        if self._stores is None:
            if self.stores_factory is None:
                from .. import module_stores

                self.stores_factory = lambda: module_stores.Stores(pool_factory=lambda: self.pool,
                                                                   include_archived=self.include_archived)
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

    def info(self) -> ToolInfo:
        return ToolInfo(name=self.name, description=self.description, inputSchema=self.input_model.model_json_schema())


REGISTRY: dict[str, Tool] = {}


def register(tool: Tool) -> Tool:
    if tool.name not in WHITELIST:
        raise ValueError(f"{tool.name!r} is not in WHITELIST; a tool outside it does not exist")
    REGISTRY[tool.name] = tool
    return tool


def numbers_in(value: Any, path: str = "") -> list[str]:
    """Where a JSON number stands in `value`, outside the count fields."""
    found: list[str] = []
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return found
    if isinstance(value, (int, float)):
        return [path or "input"]
    if isinstance(value, dict):
        for k, v in value.items():
            if k in COUNT_FIELDS and isinstance(v, int) and not isinstance(v, bool) and not path:
                continue
            found += numbers_in(v, f"{path}.{k}" if path else str(k))
    elif isinstance(value, list):
        for n, v in enumerate(value):
            found += numbers_in(v, f"{path}[{n}]")
    return found


def run(name: str, raw: Any, ctx: ToolContext | None = None) -> ToolResult:
    """Run one tool on a raw input as a model or a client sent it. Every
    refusal is a result with `error` set; nothing here raises."""
    tool = REGISTRY.get(name)
    if tool is None:
        return ToolResult(error=f"There is no tool named {name!r}. The tools are: {', '.join(sorted(REGISTRY))}.")
    if not isinstance(raw, dict):
        return ToolResult(error=f"{name} takes an object of named fields.")
    numbers = numbers_in(raw)
    if numbers:
        return ToolResult(
            error=(
                f"{name} refused: a number was typed into {', '.join(numbers)}. Tool inputs carry ids and words; "
                "name a record, an artifact, a model, a field or a scenario, and the service looks the quantity up. "
                "Only k and limit may be numbers."
            )
        )
    try:
        parsed = tool.input_model.model_validate(raw)
    except ValidationError as e:
        problems = "; ".join(f"{'.'.join(str(p) for p in err['loc']) or 'input'}: {err['msg']}" for err in e.errors())
        return ToolResult(error=f"{name} refused its input: {problems}")
    try:
        result = tool.run(parsed, ctx or ToolContext())
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
                "error": f"{name} returned a summary of {size} characters, over the {MAX_SUMMARY_CHARS} a model may read.",
            }
        )
    return result


def infos() -> list[ToolInfo]:
    return [REGISTRY[n].info() for n in WHITELIST if n in REGISTRY]


# The tools this phase builds register on import.
from . import fermos as _fermos  # noqa: E402,F401
from . import geneos as _geneos  # noqa: E402,F401
from . import modules as _modules  # noqa: E402,F401
from . import writes as _writes  # noqa: E402,F401
from . import passages as _passages  # noqa: E402,F401
from . import proforma as _proforma  # noqa: E402,F401
from . import records as _records  # noqa: E402,F401
from . import runbook as _runbook  # noqa: E402,F401
from . import units as _units  # noqa: E402,F401
