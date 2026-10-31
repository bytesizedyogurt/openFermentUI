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

    uv run --project core --all-extras python -m openferment_core.mcp_server [--project <id>]

IT ACTS IN ONE PROJECT (ADR-005; execution prompt §7.3 item 4): the one
`--project` names, else OPENFERMENT_PROJECT. Every call runs in it
(`ToolContext.project`), and a server started in none answers every call
with the words to start it in one. It reaches the database at
OPENFERMENT_DATABASE_URL (ADR-001). The project and the address are read
from the environment, or from core/.env when the environment lacks them;
nothing else is read from that file here.

A number an outside assistant types into a quantity is its estimate
(ADR-006), and a write it makes is audited as its own: both are marked
`AUTHOR`, since the protocol does not say which model the assistant runs.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import dotenv_values

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.utilities.func_metadata import ArgModelBase
from pydantic import ConfigDict

from . import db, projects, tools

NAME = "openferment"
EXTRA = ("ask_postdoc", "get_artifact")
# Who an outside assistant's typed numbers and writes are marked as (ADR-006).
AUTHOR = "an assistant over MCP"
NO_PROJECT = ("This openFerment server acts in no project. Start it with --project <id>, or set OPENFERMENT_PROJECT "
              "(in the environment or core/.env) to the project's id.")


class _Raw(ArgModelBase):
    """Every argument, as sent: the registry validates, never this layer."""

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    def model_dump_one_level(self) -> dict[str, Any]:
        return dict(self.model_extra or {})


def named_project(argv: list[str] | None = None) -> str | None:
    """The project this server acts in: `--project <id>`, else OPENFERMENT_PROJECT."""
    args = list(sys.argv[1:] if argv is None else argv)
    if "--project" in args:
        at = args.index("--project") + 1
        if at < len(args) and args[at].strip():
            return args[at].strip()
    return (os.environ.get(projects.ENV) or "").strip() or None


def _register(server: MCPServer, name: str, project: str | None) -> None:
    tool = tools.REGISTRY[name]

    def call(**arguments: Any) -> str:
        if project is None:
            return json.dumps({"error": NO_PROJECT})
        result = tools.run(name, arguments, tools.ToolContext(project=project, model=AUTHOR))
        return result.model_dump_json(exclude_none=True)

    server.add_tool(call, name=name, description=tool.description, structured_output=False)
    registered = server._tool_manager.get_tool(name)
    registered.parameters = tool.input_model.model_json_schema()
    registered.fn_metadata.arg_model = _Raw


def build(project: str | None = None) -> MCPServer:
    """The server, acting in `project` (OPENFERMENT_PROJECT when None)."""
    acting = project or named_project([])
    server = MCPServer(NAME, instructions=(
        f"openFerment's tools, acting in the project {acting}." if acting else NO_PROJECT))
    for info in tools.infos():
        _register(server, info.name, acting)

    @server.tool(name="ask_postdoc", description=(
        "Ask Postdoc a question. It runs its bounded loop over openFerment's tools and returns the plan: claims "
        "that carry no numbers of their own, each citing records, quoted sentences or computed values."))
    def ask_postdoc(question: str) -> str:
        from . import postdoc_agent
        from .models import AnswerPlan

        # §10.R: a loop that cannot run declines in words, as over HTTP,
        # rather than surfacing as a protocol error.
        if acting is None:
            return AnswerPlan(question=question, declined=NO_PROJECT).model_dump_json()
        try:
            with projects.using(acting):
                return postdoc_agent.ask(question, ctx=tools.ToolContext(project=acting)).model_dump_json()
        except Exception as e:
            return AnswerPlan(question=question, declined=f"Postdoc could not run: {e}").model_dump_json()

    @server.tool(name="get_artifact", description="Read one kept artifact by its id: what was computed, from which inputs, with its provenance.")
    def get_artifact(id: str) -> str:  # noqa: A002 (the E.6 name)
        from . import artifacts

        if acting is None:
            return json.dumps({"error": NO_PROJECT})
        try:
            with projects.using(acting):
                return artifacts.get(id).model_dump_json()
        except (artifacts.ArtifactNotFound, artifacts.ArtifactDamaged) as e:
            return json.dumps({"error": f"no readable artifact {id!r}: {e}"})

    return server


def _settings() -> None:
    """The database address and the project, from core/.env when the
    environment does not set them: these two names alone."""
    held = dotenv_values(Path(__file__).parent.parent / ".env")
    for name in (db.URL_SETTING, projects.ENV):
        if held.get(name) and not os.environ.get(name):
            os.environ[name] = str(held[name])


def main() -> None:
    _settings()
    build(named_project()).run("stdio")


if __name__ == "__main__":
    main()
