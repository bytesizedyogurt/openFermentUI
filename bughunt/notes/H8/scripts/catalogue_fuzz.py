"""POST /api/intake/catalogue with odd files; record each answer and what the catalogue keeps.

Usage: python catalogue_fuzz.py ORIGIN PROJECT
"""
from __future__ import annotations

import json
import sys

import httpx

origin, project = sys.argv[1], sys.argv[2]


def post(case: str, name: str, data: bytes, kind: str = "strain", by: str = "h8") -> None:
    c = httpx.Client(base_url=origin, trust_env=False, timeout=120, headers={"X-OpenFerment-Project": project})
    try:
        r = c.post("/api/intake/catalogue", files={"file": (name, data, "text/plain")}, data={"kind": kind, "by": by})
        try:
            body = r.json()
        except ValueError:
            body = r.text[:200]
        print(f"{r.status_code} | {case} | {json.dumps(body, ensure_ascii=False)[:330]}")
    except httpx.HTTPError as e:
        print(f"client-error | {case} | {type(e).__name__}: {e}")


post("empty file", "e.csv", b"")
post("whitespace", "w.csv", b"  \n")
post("CSV with BOM", "bom.csv", b"\xef\xbb\xbfid,name,aliases\nS1,Strain one,a;b\n")
post("UTF-16 CSV", "u16.csv", "id,name\nS2,Two\n".encode("utf-16"))
post("Latin-1 CSV", "l1.csv", "id,name\nS3,Levédure\n".encode("latin-1"))
post("invalid UTF-8", "bad.csv", b"id,name\nS4,\xff\xfe\n")
post("duplicate id in one file", "dup.csv", b"id,name\nS5,First\nS5,Second\n")
post("row naming another keeper and lane", "who.json",
     json.dumps([{"id": "S6", "name": "Six", "by": "someone else", "agent": "model", "via": "mcp",
                  "source": "a row's own words"}]).encode())
post("JSON null row", "n.json", b"[null]")
post("JSON number", "num.json", b"42")
post("JSON under entries", "ent.json", json.dumps({"entries": [{"id": "S7", "name": "Seven"}]}).encode())
post("2001 rows", "many.csv", ("id,name\n" + "".join(f"R{i},Row {i}\n" for i in range(2001))).encode())
post("past 4 MB", "big.csv", b"id,name\n" + b"X,y\n" * (1024 * 1024 + 10))
post("kind not a catalogue", "k.csv", b"id,name\nS8,Eight\n", kind="bogus")
post("by empty", "b.csv", b"id,name\nS9,Nine\n", by="")
post("by whitespace", "b2.csv", b"id,name\nS10,Ten\n", by="   ")
post("hostile file name", "../<script>alert(1)</script>.csv", b"id,name\nS11,Eleven\n")
post("formula in a cell", "f.csv", b"id,name,summary\nS12,=HYPERLINK(\"x\"),=1+1\n")
post("id with a slash", "slash.csv", b"id,name\na/b,Slashed\n")
post("product with a number in its words", "p.csv", b"id,name,category,summary\nP1,Prod,hmo,titre 41 g/L\n",
     kind="product")
c = httpx.Client(base_url=origin, trust_env=False, timeout=60, headers={"X-OpenFerment-Project": project})
for kind in ("strain", "product"):
    got = c.get(f"/api/catalogues/{kind}").json()
    print(f"\n{kind}:", [(e["id"], e["name"], e.get("by"), e.get("agent"), e.get("source")) for e in got][:20],
          f"({len(got)} in all)")
