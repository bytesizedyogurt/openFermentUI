"""openFerment's tools for assistants outside the app (OF-BLD-014 §10.1).

An MCP server over stdio. It lists every tool in the registry under the
registry's own name, description and input schema, and adds the two E.6
names: `ask_postdoc(question)`, which runs Postdoc's loop and returns the
plan, and `get_artifact(id)`. Every registry call goes through `tools.run`
with the arguments exactly as the client sent them, so the registry's rules
hold here as at the HTTP endpoint and inside the loop: a number in an input
is refused, and a refusal comes back as the tool's error.

No tool here writes to BioRepo, to Guild's ledger or to any store a person
signs.

THE PROGRAM SWITCH (OF-BLD-016 §2.3). A client here is a model, and no model
sets the switch: it is the server's, read from `OPENFERMENT_INCLUDE_ARCHIVED`
(`1` or `true` shows archived programs; unset, the default, hides them) when
the server is built, and every call runs with it in its tool context.
`.mcp.json` at the repository root starts it:

    uv run --project core --all-extras python -m openferment_core.mcp_server
"""
from __future__ import annotations

import json
import os
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.utilities.func_metadata import ArgModelBase
from pydantic import ConfigDict

from . import tools

NAME = "openferment"
EXTRA = ("ask_postdoc", "get_artifact")
SWITCH_ENV = "OPENFERMENT_INCLUDE_ARCHIVED"


def include_archived_from_env() -> bool:
    """The server's program switch: off unless the environment turns it on."""
    return os.environ.get(SWITCH_ENV, "").strip().lower() in ("1", "true", "yes", "on")


class _Raw(ArgModelBase):
    """Every argument, as sent: the registry validates, never this layer."""

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    def model_dump_one_level(self) -> dict[str, Any]:
        return dict(self.model_extra or {})


def _register(server: MCPServer, name: str, include_archived: bool = False) -> None:
    tool = tools.REGISTRY[name]

    def call(**arguments: Any) -> str:
        result = tools.run(name, arguments, tools.ToolContext(include_archived=include_archived))
        return result.model_dump_json(exclude_none=True)

    server.add_tool(call, name=name, description=tool.description, structured_output=False)
    registered = server._tool_manager.get_tool(name)
    registered.parameters = tool.input_model.model_json_schema()
    registered.fn_metadata.arg_model = _Raw


def build(include_archived: bool | None = None) -> MCPServer:
    archived = include_archived_from_env() if include_archived is None else include_archived
    server = MCPServer(NAME)
    for info in tools.infos():
        _register(server, info.name, archived)

    @server.tool(name="ask_postdoc", description=(
        "Ask Postdoc a question. It runs its bounded loop over openFerment's tools and returns the plan: claims "
        "that carry no numbers of their own, each citing records, quoted sentences or computed values."))
    def ask_postdoc(question: str) -> str:
        from . import postdoc_agent
        from .models import AnswerPlan

        # §10.R: a loop that cannot run declines in words, as over HTTP,
        # rather than surfacing as a protocol error.
        try:
            return postdoc_agent.ask(question, ctx=tools.ToolContext(include_archived=archived)).model_dump_json()
        except Exception as e:
            return AnswerPlan(question=question, declined=f"Postdoc could not run: {e}").model_dump_json()

    @server.tool(name="get_artifact", description="Read one kept artifact by its id: what was computed, from which inputs, with its provenance.")
    def get_artifact(id: str) -> str:  # noqa: A002 (the E.6 name)
        from . import artifacts

        try:
            return artifacts.get(id).model_dump_json()
        except (artifacts.ArtifactNotFound, artifacts.ArtifactDamaged) as e:
            return json.dumps({"error": f"no readable artifact {id!r}: {e}"})

    return server


def main() -> None:
    build().run("stdio")


if __name__ == "__main__":
    main()
