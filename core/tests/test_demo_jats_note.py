"""The saved JATS keeps its note before the article (live test, 2026-10-16).

Europe PMC now sends the XML declaration and <article> on one line. save_real
split at the first newline, took the whole article as the "head", and wrote
its comment after it; the saved file no longer parsed.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from openferment_core.demo import with_note

NOTE = "<!--\n  a note\n-->\n"
DECL = '<?xml version="1.0" encoding="UTF-8"?>'
ARTICLE = '<article article-type="research-article"><front/><body><p>Text.</p></body></article>'


@pytest.mark.parametrize(
    "xml",
    [
        DECL + ARTICLE,  # the one-line form Europe PMC sends now
        DECL + "\n" + ARTICLE,  # the form it sent before
        DECL + "\r\n" + ARTICLE + "\n",
        ARTICLE,  # no declaration at all
        "<!DOCTYPE article>" + ARTICLE,
    ],
)
def test_the_note_sits_before_the_article_and_the_file_parses(xml):
    out = with_note(xml, NOTE)
    ET.fromstring(out.encode("utf-8"))
    assert out.index("a note") < out.index("<article")
    if xml.startswith("<?xml"):
        assert out.startswith(DECL)
    assert ARTICLE in out


def test_the_note_save_real_writes_is_a_comment_xml_accepts():
    # "--" may not appear inside an XML comment; the note named the command
    # by its flag, "--real", and the saved file failed to parse at that spot.
    from openferment_core.demo import real_note

    out = with_note(DECL + ARTICLE, real_note("PMC8471596"))
    ET.fromstring(out.encode("utf-8"))
    assert "PMC8471596" in out
