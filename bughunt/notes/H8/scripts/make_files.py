"""Make the odd files the H8 intake fuzz feeds every document door.

Usage: python make_files.py OUTDIR
Writes: a PDF with no text layer, a PDF with a text layer, a damaged PDF, a JATS XML,
the same XML in UTF-16, text in UTF-16 / Latin-1 / invalid UTF-8, a 51 MB text file and
a 17 MB JSON, an empty file, and a whitespace-only file.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path


def pdf_blank(pages: int = 2) -> bytes:
    from pypdf import PdfWriter

    w = PdfWriter()
    for _ in range(pages):
        w.add_blank_page(width=612, height=792)
    out = io.BytesIO()
    w.write(out)
    return out.getvalue()


def pdf_text(words: str) -> bytes:
    """A one-page PDF whose content stream draws `words` in Helvetica: a text layer."""
    stream = f"BT /F1 12 Tf 72 720 Td ({words}) Tj ET".encode("latin-1")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    return bytes(out)


JATS = """<?xml version="1.0" encoding="UTF-8"?>
<article><front><article-meta><title-group><article-title>H8 JATS café study</article-title></title-group>
<abstract><p>An abstract about ethanol from stover.</p></abstract></article-meta></front>
<body><sec><title>Results</title><p>The fermentation gave a titre of 42 g/L in the H8 test.</p></sec></body></article>
"""


def main(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "blank.pdf").write_bytes(pdf_blank())
    (out / "text.pdf").write_bytes(pdf_text("H8 text layer: ethanol titre 41 g/L from corn stover"))
    (out / "damaged.pdf").write_bytes(b"%PDF-1.4\n%garbage that is not a pdf\n" + b"\x00\xff" * 50)
    (out / "jats.xml").write_text(JATS, encoding="utf-8")
    (out / "jats-utf16.xml").write_bytes(JATS.replace('encoding="UTF-8"', 'encoding="UTF-16"').encode("utf-16"))
    (out / "jats-latin1.xml").write_bytes(JATS.replace('encoding="UTF-8"', 'encoding="ISO-8859-1"').encode("latin-1"))
    note = "# H8 note\n\nSugar yield café µg per litre, a note in a person's words.\n"
    (out / "utf16.md").write_bytes(note.encode("utf-16"))
    (out / "latin1.txt").write_bytes(note.encode("latin-1"))
    (out / "badutf8.md").write_bytes(b"# H8 bad\n\nabc \xff\xfe\xc3\x28 def\n")
    (out / "empty.md").write_bytes(b"")
    (out / "blank.md").write_bytes(b"   \n\n\t\n")
    (out / "heading-only.md").write_bytes(b"# Only a title\n")
    big = b"a word of text. " * (51 * 1024 * 1024 // 16 + 1)
    (out / "big.txt").write_bytes(big)
    (out / "big.json").write_bytes(b'{"units": [], "streams": [], "pad": "' + b"x" * (17 * 1024 * 1024) + b'"}')


if __name__ == "__main__":
    main(Path(sys.argv[1]))
