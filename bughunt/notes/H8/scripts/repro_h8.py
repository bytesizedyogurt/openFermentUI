"""H8's reproductions, one function a candidate, each against a service over a fresh test database.

Usage: python repro_h8.py ID ORIGIN      (repro_h8.sh starts the service and calls this)
Prints what the contract expects and what the service answered, and the line SHOWN when the
defect shows, NOT SHOWN otherwise. Talks to the local service alone (trust_env off).
"""
from __future__ import annotations

import json
import sys

import httpx

ID, ORIGIN = sys.argv[1], sys.argv[2]


def client(project: str | None = None) -> httpx.Client:
    h = {"X-OpenFerment-Project": project} if project else {}
    return httpx.Client(base_url=ORIGIN, trust_env=False, timeout=600, headers=h)


def project(pid: str) -> httpx.Client:
    client().post("/api/projects", json={"id": pid, "name": pid, "by": "h8"})
    return client(pid)


def shown(ok: bool) -> None:
    print("SHOWN" if ok else "NOT SHOWN")
    sys.exit(0 if ok else 1)


def h8_01() -> None:
    a, b = project("ra"), project("rb")
    text = "The biorefinery processes 2000 Mg of dry corn stover per day in the H8 repro."
    other = text.replace("2000 Mg", "2000 mg").upper()
    ga = a.post("/api/intake/paste", json={"title": "A note", "text": text, "by": "a"}).json()
    gb = b.post("/api/intake/paste", json={"title": "B note", "text": other, "by": "b"}).json()
    held = b.get("/api/biorepo/overlay").json()["papers"][gb["documentId"]]["sections"][0]["text"]
    print("project ra pasted:", text)
    print("project rb pasted:", other)
    print("rb's outcome:", gb["status"], gb["documentId"], "| ra's document:", ga["documentId"])
    print("rb's document reads:", held)
    shown(gb["status"] == "linked" and gb["documentId"] == ga["documentId"] and "2000 Mg" in held)


def h8_02() -> None:
    a, b = project("ra"), project("rb")
    text = "Shared H8 passage about stover saccharification, pasted by two projects alike."
    a.post("/api/intake/paste", json={"title": "Project ra's own title", "text": text, "by": "a",
                                       "licenceClass": "restricted", "licence": "ra's words: internal use alone"})
    out = b.post("/api/intake/paste", json={"title": "rb's title", "text": text, "by": "b",
                                             "licenceClass": "open_commercial"}).json()
    doc = b.get("/api/literature/documents").json()[0]
    paper = b.get("/api/biorepo/overlay").json()["papers"][doc["documentId"]]
    hit = b.get("/api/literature/search", params={"q": "stover saccharification"}).json()["hits"][0]
    print("rb's outcome: status", out["status"], "| title", out["title"], "| licenceClass", out["licenceClass"])
    print("rb's documents: title", doc["title"], "| licenceClass", doc["licenceClass"], "| source", doc["source"],
          "| selection licence", doc["selection"].get("licence"))
    print("rb's overlay: license", paper["license"], "| licenceClass", paper["licenceClass"])
    print("rb's search hit: licenceClass", hit["licenceClass"], "| title", hit["title"])
    shown(out["licenceClass"] == "open_commercial" and doc["licenceClass"] == "restricted"
          and paper["license"] == "ra's words: internal use alone" and doc["source"] == "project:ra:paste")


def h8_03() -> None:
    a, b = project("ra"), project("rb")
    body = b"# H8 percent name\n\nA note whose file name carries a percent-encoded NUL.\n"
    try:
        r = a.post("/api/intake/upload", files={"file": ("report%00.md", body, "text/markdown")}, data={"by": "a"})
        first = (r.status_code, r.text[:120])
    except httpx.HTTPError as e:
        first = ("connection", str(e))
    held_a = client("ra").get("/api/literature/documents").json()
    again = client("rb").post("/api/intake/upload", files={"file": ("report.md", body, "text/markdown")},
                              data={"by": "b"}).json()
    doc = client("rb").get("/api/literature/documents").json()[0]
    print("ra's upload of report%00.md:", first)
    print("documents ra holds afterwards:", len(held_a))
    print("rb's upload of the same bytes as report.md:", again["status"])
    print("rb's document: source", doc["source"], "| sourceRef", doc["sourceRef"])
    shown(first[0] == 500 and not held_a and again["status"] == "linked" and doc["source"] == "project:ra:upload")


def h8_04() -> None:
    a = project("ra")
    xml = ("<?xml version=\"1.0\" encoding=\"ISO-8859-1\"?>\n<article><front><article-meta><title-group>"
           "<article-title>Latin-1 assay</article-title></title-group></article-meta></front><body><sec><title>Assay"
           "</title><p>The supernatant held 5 µg/L of furfural at 30 °C after 48 h in the H8 repro.</p>"
           "</sec></body></article>\n").encode("latin-1")
    out = a.post("/api/intake/upload", files={"file": ("assay.xml", xml, "application/xml")}, data={"by": "a"}).json()
    text = a.get("/api/biorepo/overlay").json()["papers"][out["documentId"]]["sections"][0]["text"]
    md = a.post("/api/intake/upload", files={"file": ("assay.md", "# A\n\n5 µg/L\n".encode("latin-1"),
                                                      "text/markdown")}, data={"by": "a"}).json()
    print("the file says: 5 µg/L ... 30 °C (Latin-1, declared)")
    print("upload outcome:", out["status"], "| kept passage:", text)
    print("the same bytes as Markdown:", md["status"], "|", md["reason"])
    shown(out["status"] == "ingested" and "�g/L" in text and md["status"] == "failed")


def h8_06() -> None:
    a = project("ra")
    a.post("/api/intake/paste", json={"title": "Deep", "text": "Corn stover pretreatment releases xylose.", "by": "a"})
    got = a.get("/api/literature/search", params={"q": "corn stover", "profile": "deep"}).json()
    print("deep search with no model reachable: profile", got["profile"], "| degradedStages", got["degradedStages"],
          "| hits", len(got["hits"]))
    shown(got["profile"] == "deep" and got["degradedStages"] == [])


def h8_08() -> None:
    a = project("ra")
    a.post("/api/intake/paste", json={"title": "Ans", "text": "Corn stover pretreatment releases xylose.", "by": "a"})
    with client("ra").stream("POST", "/api/literature/answer", json={"question": "What does pretreatment release?"}) as r:
        text = "".join(r.iter_text())
    error = [line for line in text.splitlines() if line.startswith("data:") and "generation" in line]
    print("health hasKey:", client().get("/api/health").json().get("hasKey"))
    print("the stream's error:", error)
    shown(bool(error) and "key" not in error[-1].lower())


def h8_09() -> None:
    a = project("ra")
    a.post("/api/intake/paste", json={"title": "Rag", "text": "Corn stover pretreatment releases xylose.", "by": "a"})
    out = {}
    for path in ("/rag/v1/corpus-manifest", "/rag/health", "/rag/openapi.json", "/rag/v1/status"):
        r = client("ra").get(path)
        out[path] = r.status_code
    manifest = client("ra").get("/rag/v1/corpus-manifest").json()
    print("answers with no key:", out)
    print("the manifest's stats:", manifest.get("stats"))
    shown(out["/rag/v1/corpus-manifest"] == 200 and out["/rag/v1/status"] == 401)


def h8_10() -> None:
    a = project("ra")
    r = a.post("/api/intake/catalogue", files={"file": ("dup.csv", b"id,name\nS5,First\nS5,Second\n", "text/csv")},
               data={"kind": "strain", "by": "a"}).json()
    got = a.get("/api/catalogues/strain").json()
    print("answer:", r)
    print("the catalogue holds:", [(e["id"], e["name"]) for e in got])
    shown(r["kept"] == ["S5", "S5"] and len(got) == 1)


def h8_11() -> None:
    a = project("ra")
    rows = json.dumps([{"id": "S6", "name": "Six", "source": "a row's own words"}]).encode()
    a.post("/api/intake/catalogue", files={"file": ("rows.json", rows, "application/json")},
           data={"kind": "strain", "by": "a"})
    got = a.get("/api/catalogues/strain/S6").json()
    print("source kept for a row of the file rows.json:", got.get("source"))
    shown(got.get("source") == "a row's own words")


def h8_12() -> None:
    a = project("ra")
    sff = json.dumps({"units": [], "streams": [], "metadata": {"process_title": "BOM"}}).encode()
    r = a.post("/api/flowsheets/import", files={"file": ("bom.json", b"\xef\xbb\xbf" + sff, "application/json")},
               data={"by": "a"})
    c = a.post("/api/intake/catalogue", files={"file": ("bom.csv", b"\xef\xbb\xbfid,name\nS1,One\n", "text/csv")},
               data={"kind": "strain", "by": "a"})
    print("SFF with a UTF-8 BOM:", r.status_code, r.json().get("detail"))
    print("catalogue CSV with a UTF-8 BOM:", c.status_code, c.json())
    shown(r.status_code == 422 and "not JSON" in r.json().get("detail", "") and c.status_code == 200)


{"H8-01": h8_01, "H8-02": h8_02, "H8-03": h8_03, "H8-04": h8_04, "H8-06": h8_06, "H8-08": h8_08, "H8-09": h8_09,
 "H8-10": h8_10, "H8-11": h8_11, "H8-12": h8_12}[ID]()
