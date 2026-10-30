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

`.mcp.json` at the repository root starts it:

    uv run --project core --all-extras python -m openferment_core.mcp_server
"""
from __future__ import annotations

import json
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.utilities.func_metadata import ArgModelBase
from pydantic import ConfigDict

from . import tools

NAME = "openferment"
EXTRA = ("ask_postdoc", "get_artifact")


class _Raw(ArgModelBase):
    """Every argument, as sent: the registry validates, never this layer."""

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    def model_dump_one_level(self) -> dict[str, Any]:
        return dict(self.model_extra or {})


def _register(server: MCPServer, name: str) -> None:
    tool = tools.REGISTRY[name]

    def call(**arguments: Any) -> str:
        result = tools.run(name, arguments, tools.ToolContext())
        return result.model_dump_json(exclude_none=True)

    server.add_tool(call, name=name, description=tool.description, structured_output=False)
    registered = server._tool_manager.get_tool(name)
    registered.parameters = tool.input_model.model_json_schema()
    registered.fn_metadata.arg_model = _Raw


def build() -> MCPServer:
    server = MCPServer(NAME)
    for info in tools.infos():
        _register(server, info.name)

    @server.tool(name="ask_postdoc", description=(
        "Ask Postdoc a question. It runs its bounded loop over openFerment's tools and returns the plan: claims "
        "that carry no numbers of their own, each citing records, quoted sentences or computed values."))
    def ask_postdoc(question: str) -> str:
        from . import postdoc_agent
        from .models import AnswerPlan

        # §10.R: a loop that cannot run declines in words, as over HTTP,
        # rather than surfacing as a protocol error.
        try:
            return postdoc_agent.ask(question, ctx=tools.ToolContext()).model_dump_json()
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
