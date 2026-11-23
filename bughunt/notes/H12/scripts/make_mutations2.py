"""Write bughunt/notes/H12/mutations2.json: H12's second batch, and the first batch's mutations whose only
failure was the conform signal test (it asserts the scratch name, which H12's worktree renames to bh_h12_conform
so no database outside bh_h12_* is made), run again with that one test left out."""
import json
from pathlib import Path

T = lambda *fs: [f"tests/{f}" for f in fs]  # noqa: E731
NOT_SIGNAL = ["-k", "not sigterm_ends_the_command"]
first = {m["id"]: m for m in json.loads(Path("/home/user/openFermentUI/bughunt/notes/H12/mutations.json").read_text())}
results = [json.loads(x) for x in Path("/home/user/openFermentUI/bughunt/notes/H12/mutations/results.jsonl").read_text().splitlines()]
M = []
for r in results:
    if any("sigterm_ends_the_command" in f for f in r["first_failure"]):
        m = dict(first[r["id"]])
        m["id"] = m["id"] + "b"
        m["tests"] = m["tests"] + NOT_SIGNAL
        M.append(m)


def m(id_, target, file, old, new, tests, why, **kw):
    M.append({"id": id_, "target": target, "file": file, "old": old, "new": new, "tests": tests, "why": why, **kw})


m("N01", "llm.kit_client", "openferment_core/llm.py",
  '            result = await asyncio.to_thread(\n'
  '                call, system=system or "", user=prompt, schema=None, max_tokens=max(max_tokens, room),\n'
  '                family=family, label="sci-rag-kit: ",\n'
  '            )',
  '            result = await asyncio.get_running_loop().run_in_executor(None, lambda: call(\n'
  '                system=system or "", user=prompt, schema=None, max_tokens=max(max_tokens, room),\n'
  '                family=family, label="sci-rag-kit: "))',
  T("test_key_override.py", "test_llm.py", "test_api_intake.py", "test_literature_kit.py", "test_literature_graph.py"),
  "the kit's model calls run on a thread that does not copy the request's context, so on core/.env's key")
m("N02", "llm._default_client", "openferment_core/llm.py",
  "def key_named() -> bool:\n    \"\"\"Whether this request's model calls run on a key the request named.\"\"\"\n    return _REQUEST_KEY.get() is not None",
  "def key_named() -> bool:\n    \"\"\"Whether this request's model calls run on a key the request named.\"\"\"\n    return False",
  T("test_key_override.py", "test_llm.py"), "a failure on a named key is said to be core/.env's")
m("N03", "events.recent", "openferment_core/events.py",
  "        return [e for e in _kept if e.project == project and e.id > after]",
  "        return [e for e in _kept if e.id > after]", T("test_events.py", "test_projects.py"),
  "a page reconnecting reads every project's kept events")
m("N04", "events.reader", "openferment_core/events.py",
  "        _readers[rid] = (project, inbox)", "        _readers[rid] = (None, inbox)", T("test_events.py", "test_projects.py"),
  "a page's inbox is filled with every project's events")
m("N05", "collectors._redirect", "openferment_core/literature/collectors.py",
  '    if following.scheme != "https" or not following.host:', '    if not following.host:',
  T("test_sff_url.py", "test_collectors.py"), "a redirect to plain http is followed")
m("N06", "collectors._fetch", "openferment_core/literature/collectors.py",
  "            try:\n                pins[(url.raw_host.decode(\"ascii\"), url.port or 443)] = await anyio.to_thread.run_sync(\n"
  "                    public_addresses, url, resolve, abandon_on_cancel=True)",
  "            try:\n                pins[(url.raw_host.decode(\"ascii\"), url.port or 443)] = await anyio.to_thread.run_sync(\n"
  "                    public_addresses, url, resolve, abandon_on_cancel=True) if not came_from else tuple(\n"
  "                    a for a in resolve(url.raw_host.decode(\"ascii\"), url.port or 443))",
  T("test_sff_url.py", "test_collectors.py"), "a redirect's host is pinned unchecked")
m("N07", "collectors._whole", "openferment_core/literature/collectors.py",
  "        if len(data) > limit:\n            raise TooLarge(", "        if len(data) > limit * 2:\n            raise TooLarge(",
  T("test_sff_url.py", "test_collectors.py"), "a file twice the limit is taken")
m("N08", "the worker boundary (proforma._installed)", "openferment_core/proforma.py",
  "def _installed(dist: str) -> str:\n    from importlib.metadata import PackageNotFoundError, version\n\n    try:",
  "def _installed(dist: str) -> str:\n    from importlib.metadata import PackageNotFoundError, version\n\n"
  "    if dist == \"biorefineries\":\n        import biorefineries\n\n        return getattr(biorefineries, \"__version__\", None) or version(dist)\n    try:",
  T("test_workers.py", "test_boundaries.py", "test_proforma.py", "test_ready.py", "test_engines.py") + NOT_SIGNAL,
  "the service process imports biorefineries (and with it BioSTEAM) to read its version")
Path("/home/user/openFermentUI/bughunt/notes/H12/mutations2.json").write_text(json.dumps([x for x in M if not x.get("skip")], indent=1))
print([x["id"] for x in M if not x.get("skip")])
