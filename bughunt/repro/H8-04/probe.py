"""H8-04's probe: one JATS XML file declaring ISO-8859-1, uploaded through POST /api/intake/upload.

Usage: python -I probe.py ORIGIN       (run.sh starts the service over a fresh database and calls this)
Talks to the local service alone (trust_env off). Prints what each upload answered and what the project
keeps, then one VERDICT line.
"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET

import httpx

ORIGIN = sys.argv[1]
SENTENCE = "The supernatant held 5 µg/L of furfural at 30 °C after 48 h in the H8-04 repro."


def doc(encoding: str, sentence: str) -> bytes:
    return (f'<?xml version="1.0" encoding="{encoding}"?>\n<article><front><article-meta><title-group>'
            f"<article-title>Assay in {encoding}</article-title></title-group></article-meta></front>"
            f"<body><sec><title>Assay</title><p>{sentence}</p></sec></body></article>\n").encode(encoding)


def client(project: str | None = None) -> httpx.Client:
    h = {"X-OpenFerment-Project": project} if project else {}
    return httpx.Client(base_url=ORIGIN, trust_env=False, timeout=300, headers=h)


def upload(c: httpx.Client, name: str, data: bytes, kind: str) -> dict:
    return c.post("/api/intake/upload", files={"file": (name, data, kind)}, data={"by": "h8-04"}).json()


def kept(c: httpx.Client, document_id: str) -> str:
    paper = c.get("/api/biorepo/overlay").json()["papers"][document_id]
    return " / ".join(s["text"] for s in paper["sections"] if "furfural" in s["text"])


client().post("/api/projects", json={"id": "enc", "name": "enc", "by": "h8-04"})
p = client("enc")

latin = doc("ISO-8859-1", SENTENCE)
print("the file: assay.xml, ISO-8859-1 declared and used; its bytes for the units:",
      latin[latin.index(b"5 "):latin.index(b"5 ") + 4], "and", latin[latin.index(b"30 "):latin.index(b"30 ") + 4])
print("the XML parser given the file's bytes reads:", ET.fromstring(latin).find(".//p").text)

out = upload(p, "assay.xml", latin, "application/xml")
print("upload of assay.xml (ISO-8859-1):", out.get("status"), "|", out.get("reason") or "no reason given")
text_latin = kept(p, out["documentId"]) if out.get("documentId") else ""
print("  the project keeps:", ascii(text_latin))

md = upload(p, "assay.md", f"# Assay\n\n{SENTENCE}\n".encode("latin-1"), "text/markdown")
print("the same sentence in Latin-1 as assay.md:", md.get("status"), "|", md.get("reason"))

utf = upload(p, "assay-utf8.xml", doc("UTF-8", SENTENCE.replace("H8-04", "H8-04 UTF-8")), "application/xml")
text_utf = kept(p, utf["documentId"]) if utf.get("documentId") else ""
print("control, the same article in UTF-8 as assay-utf8.xml:", utf.get("status"), "| kept:", ascii(text_utf))

defect = (out.get("status") == "ingested" and "\ufffdg/L" in text_latin and "\ufffdC" in text_latin
          and "µg/L" not in text_latin and md.get("status") == "failed" and "µg/L" in text_utf)
print("VERDICT:", "DEFECT" if defect else "NO-DEFECT")
