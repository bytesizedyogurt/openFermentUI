"""POST /api/flowsheets/import with odd files and names; record each answer and what is kept.

Usage: python sff_import_fuzz.py ORIGIN PROJECT FILESDIR [LIBRARY_FILE]
LIBRARY_FILE: a reference flowsheet (SF_BST_01.json) to import under hostile names.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

origin, project, files = sys.argv[1], sys.argv[2], Path(sys.argv[3])
library = Path(sys.argv[4]) if len(sys.argv) > 4 else None


def post(case: str, name: str, data: bytes, by: str = "h8") -> dict:
    c = httpx.Client(base_url=origin, trust_env=False, timeout=900, headers={"X-OpenFerment-Project": project})
    try:
        r = c.post("/api/flowsheets/import", files={"file": (name, data, "application/json")}, data={"by": by})
        status = r.status_code
        try:
            body = r.json()
        except ValueError:
            body = r.text[:200]
    except httpx.HTTPError as e:
        status, body = "client-error", f"{type(e).__name__}: {e}"
    if isinstance(body, dict) and "id" in body:
        said = {k: body.get(k) for k in ("id", "title", "origin", "source", "libraryId")}
        said["valid"] = (body.get("validation") or {}).get("valid")
    else:
        said = body.get("detail") if isinstance(body, dict) else body
    print(f"{status} | {case} | {json.dumps(said, ensure_ascii=False)[:300]}")
    return body if isinstance(body, dict) else {}


TINY = {"units": [{"id": "U1", "unit_type": "Mixer"}], "streams": [
    {"id": "s1", "source_unit_id": "None", "sink_unit_id": "U1"},
    {"id": "s2", "source_unit_id": "U1", "sink_unit_id": "None"}], "metadata": {"process_title": "H8 tiny"}}
tiny = json.dumps(TINY).encode()

post("empty file", "empty.json", b"")
post("whitespace", "ws.json", b"  \n ")
post("17 MB file (past 16 MB)", "big.json", (files / "big.json").read_bytes())
post("UTF-16 JSON", "u16.json", json.dumps(TINY).encode("utf-16"))
post("UTF-8 with BOM", "bom.json", b"\xef\xbb\xbf" + tiny)
post("Latin-1 title", "l1.json", json.dumps({**TINY, "metadata": {"process_title": "café"}},
                                              ensure_ascii=False).encode("latin-1"))
post("invalid UTF-8", "bad.json", b'{"units": [], "streams": [], "x": "\xff\xfe"}')
post("not JSON", "x.json", b"<html>no</html>")
post("JSON list", "l.json", b"[]")
post("units not a list", "u.json", b'{"units": {}, "streams": []}')
post("nested 100k deep", "deep.json", b"[" * 100000 + b"]" * 100000)
post("NaN in a flow", "nan.json", json.dumps({**TINY, "streams": [
    {"id": "s1", "source_unit_id": "None", "sink_unit_id": "U1",
     "stream_properties": {"total_mass_flow": {"value": float("nan"), "units": "kg/hr"}}}]}).encode())
post("tiny valid shape", "tiny.json", tiny)
post("tiny again, same bytes, other name", "tiny-copy.json", tiny)
post("same name, other bytes", "tiny.json", json.dumps({**TINY, "metadata": {"process_title": "H8 tiny two"}}).encode())
post("dot-dot name", "../../etc/x.json", json.dumps({**TINY, "metadata": {}, "pad": 1}).encode())
post("NUL in the name", "nul\x00.json", json.dumps({**TINY, "metadata": {}, "pad": 2}).encode())
post("HTML in the name", "<img src=x onerror=alert(1)>.json", json.dumps({**TINY, "metadata": {}, "pad": 3}).encode())
post("very long name", "n" * 400 + ".json", json.dumps({**TINY, "metadata": {}, "pad": 4}).encode())
post("unicode name", "流程✓.json", json.dumps({**TINY, "metadata": {}, "pad": 5}).encode())
post("empty name", "", json.dumps({**TINY, "metadata": {}, "pad": 6}).encode())
post("by empty", "byempty.json", json.dumps({**TINY, "pad": 7}).encode(), by="")
post("by 201 chars", "bylong.json", json.dumps({**TINY, "pad": 8}).encode(), by="b" * 201)
if library and library.is_file():
    post("a reference flowsheet under a hostile name", "../<script>.json", library.read_bytes())

c = httpx.Client(base_url=origin, trust_env=False, timeout=60, headers={"X-OpenFerment-Project": project})
kept = c.get("/api/flowsheets").json()
print("\nKEPT:", len(kept))
for k in kept:
    print("  ", k["id"], "|", k["title"][:60], "|", k["origin"], "|", k["source"][:120])
    f = c.get(f"/api/flowsheets/{k['id']}/file")
    print("     file:", f.status_code, f.headers.get("content-disposition"), len(f.content), "bytes")
