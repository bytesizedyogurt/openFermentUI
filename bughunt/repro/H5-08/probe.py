"""H5-08: the sci-rag MCP server and the openferment MCP server, each started over stdio with --project
naming a project the database does not hold (bh-zzz), a malformed id (../bh-a) and an upper-case id
(BH-A), beside two controls: no project at all, and bh-a, a project the database holds (made here, empty).

Both servers run from a scratch worktree of 2047f5a (H5_WT), whose core/ holds no .env, so neither server
falls back to a database or a project of a .env: each reads OPENFERMENT_DATABASE_URL from this process
alone. No key, no model call, no network: every tool called reads the store alone.
"""
import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

WT = os.environ["H5_WT"]
HELD = "bh-a"
UNKNOWN = ["bh-zzz", "../bh-a", "BH-A"]
DOC = "0123456789abcdef0123456789abcdef"
RAG_CALLS = [
    ("corpus_stats", {}),
    ("list_sources", {}),
    ("get_document", {"document_id": DOC}),
    ("get_citations", {"document_id": DOC}),
    ("search_entities", {"name_contains": "a"}),
    ("get_entity_relationships", {"entity_name": "a"}),
]
OF_CALLS = [("literature_sources", {})]


def make_held() -> None:
    sys.path.insert(0, WT)
    from openferment_core import projects
    from openferment_core.models import ProjectCreate

    made = projects.create(ProjectCreate(id=HELD, name=HELD, by="bughunt"))
    print(f"made project {made.id!r} in the database (no document, no passage)")


async def session(module: str, project: str | None, calls):
    env = dict(os.environ)
    env.pop("VIRTUAL_ENV", None)
    env.pop("OPENFERMENT_PROJECT", None)
    args = ["-m", module] + (["--project", project] if project is not None else [])
    params = StdioServerParameters(command=sys.executable, args=args, env=env, cwd=WT)
    out = []
    errlog = open(os.environ.get("H5_ERRLOG", os.devnull), "a")
    async with stdio_client(params, errlog=errlog) as (r, w), ClientSession(r, w) as c:
        await c.initialize()
        for tool, a in calls:
            res = await c.call_tool(tool, a)
            text = " ".join(getattr(x, "text", "") for x in res.content).replace("\n", " ")
            out.append((tool, bool(res.is_error), text))
    return out


def short(text: str, n: int = 230) -> str:
    return text if len(text) <= n else text[:n] + "..."


def names_missing_project(text: str, project: str) -> bool:
    """Words saying the database holds no project of this id (the openferment server's refusal), or that
    the id is no project's id."""
    low = text.lower()
    return ("holds no project" in low or "no project named" in low or "does not hold" in low
            or "not a project" in low or "no such project" in low)


def main() -> None:
    make_held()
    rows = {}
    for project in [None, HELD] + UNKNOWN:
        label = "(none)" if project is None else project
        of = asyncio.run(session("openferment_core.mcp_server", project, OF_CALLS))
        rag = asyncio.run(session("openferment_core.literature_mcp", project, RAG_CALLS))
        rows[label] = (of, rag)
        print(f"\n--project {label}")
        for tool, err, text in of:
            print(f"  openferment {tool:26s} is_error={err!s:5s} {short(text)}")
        for tool, err, text in rag:
            print(f"  sci-rag     {tool:26s} is_error={err!s:5s} {short(text)}")

    print()
    defect = []
    for project in UNKNOWN:
        of, rag = rows[project]
        of_says = all(names_missing_project(t, project) for _, _, t in of)
        rag_says = [tool for tool, _, t in rag if names_missing_project(t, project)]
        # The sci-rag answers for the unknown id, with the id written as bh-a's, beside bh-a's own answers.
        same = [tool for (tool, _, t), (_, _, h) in zip(rag, rows[HELD][1])
                if t.replace(project, HELD) == h]
        intake = [tool for tool, _, t in rag if "its documents enter on Intake" in t]
        print(f"{project}: openferment server names the missing project: {of_says}; "
              f"sci-rag tools naming it: {rag_says or 'none'}; sci-rag answers identical to held empty bh-a's: "
              f"{len(same)}/{len(rag)} ({', '.join(same)}); answers saying documents enter on Intake: "
              f"{', '.join(intake) or 'none'}")
        if of_says and not rag_says:
            defect.append(project)

    none_of, none_rag = rows["(none)"]
    print(f"control, no project: sci-rag refuses every call in words: "
          f"{all(e and 'acts in no project' in t for _, e, t in none_rag)}")

    print("EXPECTED: started with --project naming a project the database does not hold (bh-zzz, ../bh-a, BH-A), "
          "the sci-rag server refuses every call in words saying the database holds no such project, as the "
          "openferment server does for the same ids")
    print(f"OBSERVED: the openferment server refuses each id in words naming the database and the project; the "
          f"sci-rag server answers {len(defect)} of {len(UNKNOWN)} such ids ({', '.join(defect) or 'none'}) as a "
          f"held empty project (documents 0, sources {{}}, 'No such document') and its graph tools say "
          f"'The project <id> holds no passage yet: its documents enter on Intake', with no word that the "
          f"project is missing")
    print("RESULT: DEFECT" if defect == UNKNOWN else "RESULT: NO-DEFECT")


if __name__ == "__main__":
    main()
