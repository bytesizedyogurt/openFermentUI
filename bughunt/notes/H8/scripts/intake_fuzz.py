"""Feed every Intake door odd documents and record each answer and what the project keeps.

Usage: python intake_fuzz.py ORIGIN PROJECT FILESDIR [OUT.jsonl]
Run make_files.py FILESDIR first. Talks to a local service alone (trust_env off, no proxy).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

origin, project, files = sys.argv[1], sys.argv[2], Path(sys.argv[3])
out = Path(sys.argv[4]) if len(sys.argv) > 4 else None
class _Fresh:
    """A new connection for every request: a 500 may close the one before."""

    def __getattr__(self, name: str):
        client = httpx.Client(base_url=origin, trust_env=False, timeout=600, headers={"X-OpenFerment-Project": project})
        return getattr(client, name)


c = _Fresh()
SKIP = int(sys.argv[5]) if len(sys.argv) > 5 else 0
rows: list[dict] = []


def note(door: str, case: str, r: httpx.Response) -> dict:
    try:
        body = r.json()
    except ValueError:
        body = r.text[:300]
    row = {"door": door, "case": case, "status": r.status_code, "body": body}
    rows.append(row)
    short = body if isinstance(body, str) else {k: body.get(k) for k in ("status", "reason", "documentId", "title",
                                                                         "identifier", "chunks", "licenceClass",
                                                                         "detail") if isinstance(body, dict) and k in body}
    print(f"[{door}] {case}: {r.status_code} {json.dumps(short, ensure_ascii=False)[:400]}")
    return row


def upload(case: str, name: str, data: bytes, **form: str) -> dict:
    fields = {"by": "h8", **form}
    r = c.post("/api/intake/upload", files={"file": (name, data, "application/octet-stream")}, data=fields)
    return note("upload", case, r)


def paste(case: str, **body: object) -> dict:
    r = c.post("/api/intake/paste", json={"by": "h8", **body})
    return note("paste", case, r)


def rd(name: str) -> bytes:
    return (files / name).read_bytes()


# ── upload ──
upload("empty .md", "empty.md", rd("empty.md"))
upload("whitespace-only .md", "blank.md", rd("blank.md"))
upload("heading-only .md", "heading-only.md", rd("heading-only.md"))
upload("UTF-16 .md", "utf16.md", rd("utf16.md"))
upload("Latin-1 .txt", "latin1.txt", rd("latin1.txt"))
upload("invalid UTF-8 .md", "badutf8.md", rd("badutf8.md"))
upload("PDF with no text layer", "blank.pdf", rd("blank.pdf"))
upload("damaged PDF", "damaged.pdf", rd("damaged.pdf"))
upload("PDF with text", "text.pdf", rd("text.pdf"), title="H8 text PDF")
upload("PDF with text, again (same bytes)", "text.pdf", rd("text.pdf"), title="H8 text PDF")
upload("JATS UTF-8", "jats.xml", rd("jats.xml"))
upload("JATS UTF-16", "jats-utf16.xml", rd("jats-utf16.xml"))
upload("JATS Latin-1", "jats-latin1.xml", rd("jats-latin1.xml"))
upload("non-JATS XML", "x.xml", b"<?xml version='1.0'?><root><p>hi</p></root>")
upload("XML entity bomb", "bomb.xml", b"<?xml version='1.0'?><!DOCTYPE l [<!ENTITY a 'aaaaaaaaaa'><!ENTITY b '&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;'><!ENTITY c '&b;&b;&b;&b;&b;&b;&b;&b;&b;&b;'><!ENTITY d '&c;&c;&c;&c;&c;&c;&c;&c;&c;&c;'><!ENTITY e '&d;&d;&d;&d;&d;&d;&d;&d;&d;&d;'><!ENTITY f '&e;&e;&e;&e;&e;&e;&e;&e;&e;&e;'><!ENTITY g '&f;&f;&f;&f;&f;&f;&f;&f;&f;&f;'>]><article><body><p>&g;</p></body></article>")
upload("XML external entity", "xxe.xml", b"<?xml version='1.0'?><!DOCTYPE a [<!ENTITY x SYSTEM 'file:///etc/hostname'>]><article><body><sec><title>T</title><p>leak: &x;</p></sec></body></article>")
upload("wrong suffix .docx", "paper.docx", b"PK\x03\x04 not a doc")
upload("no suffix", "README", b"words")
upload("HTML with script", "page.html", b"<html><head><title>H8 <b>page</b></title><script>alert(1)</script></head><body><h1>Head</h1><p>Body text of the H8 html page.</p></body></html>")
upload("same identifier, other bytes (1)", "same-name.md", b"# Same name\n\nFirst version of the words in this H8 note.\n")
upload("same identifier, other bytes (2)", "same-name.md", b"# Same name\n\nSecond version, other words entirely, in this H8 note.\n")
upload("dot-dot name", "../../../etc/passwd.md", b"# Traversal\n\nA note whose name climbs directories.\n")
upload("percent-encoded dot-dot name", "..%2F..%2Fetc%2Fpasswd2.md", b"# Traversal two\n\nAnother climbing name, percent-encoded.\n")
upload("very long name", ("n" * 300) + ".md", b"# Long name\n\nA note with a very long file name.\n")
upload("unicode name", "résumé ✓ 文献.md", b"# Unicode name\n\nA note with a unicode name.\n")
upload("HTML in the name", "<img src=x onerror=alert(1)>.md", b"# HTML name\n\nA note named with markup.\n")
upload("script in the name", "<script>alert(1)</script>.md", b"# Script name\n\nA note named with a script tag.\n")
upload("NUL in the name", "nul\x00byte.md", b"# NUL name\n\nA note whose name carries a NUL.\n")
upload("licence class not a class", "lc.md", b"# LC\n\nwords for the licence class test\n", licenceClass="cc-by")
upload("licence class empty", "lc2.md", b"# LC2\n\nwords for the empty licence class test\n", licenceClass="")
upload("by empty", "byempty.md", b"# By\n\nwords\n", by="")
r = c.post("/api/intake/upload", files={"file": ("big.txt", rd("big.txt"), "text/plain")}, data={"by": "h8"})
note("upload", "51 MB text (past 50 MB)", r)

# ── paste ──
paste("empty text", title="T", text="")
paste("whitespace text", title="T", text="   \n ")
paste("empty title", title="", text="words")
paste("whitespace title", title="   ", text="words")
paste("title with markup", title="<img src=x onerror=alert(1)>", text="Words pasted under a title with markup.")
paste("javascript url", title="JS url", text="Words pasted with a javascript address.", url="javascript:alert(1)",
      licence="CC BY 4.0")
paste("text past the limit", title="Big", text="x" * 2_000_001)
paste("same text as the text PDF", title="Pasted twin", text="H8 text layer: ethanol titre 41 g/L from corn stover")

# ── collect ──
for ident in ["", "   ", "12345", "PMID:", "OSTI:abc", "https://www.osti.gov/biblio/notdigits",
              "http://127.0.0.1:8885/x.yeastgenome.org", "https://yeastgenome.org@127.0.0.1:8885/",
              "javascript:alert(1)"]:  # none of these reaches the network
    r = c.post("/api/intake/collect", json={"identifier": ident, "by": "h8"})
    note("collect", repr(ident), r)

docs = c.get("/api/literature/documents").json()
print("\nDOCUMENTS HELD:", len(docs))
for d in docs:
    print(" ", d["documentId"], "|", d["title"][:60], "|", d["collector"], "|", d["chunks"], "chunks |", d["licenceClass"],
          "|", d["source"], "|", d["sourceRef"])
rows.append({"door": "documents", "body": docs})
if out:
    out.write_text("\n".join(json.dumps(r, ensure_ascii=False, default=str) for r in rows) + "\n")
