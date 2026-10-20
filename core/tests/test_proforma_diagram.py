"""A drawn diagram replays (OF-BLD-019 §7.R, finding 5).

BioSTEAM names every node of its digraph `str(hash(obj))`, an object's
address, so two builds of the same plant hand Graphviz different names and
Graphviz writes each into the SVG (a node's `<title>` and comment, an edge's
`a->b`). A kept run's output hash took that SVG whole, so a drawn reference
run never replayed identically. The worker now renames the nodes by their
order in the digraph before Graphviz draws it: the drawing is a function of
the plant alone.
"""
from __future__ import annotations

import os
import re
import sys

import pytest

from openferment_core import proforma

# The toy plant's digraph body as BioSTEAM writes it, twice, from two
# builds whose objects sat at different addresses (shortened from a real
# build): every node and edge statement names a hash.
BUILD_A = [
    '\tDamping=0.995 K=0.5 bgcolor="#000000" maxiter=10000000000000000000 rankdir=LR',
    '\t8737733816409 [label="toy_M\nMixer" shape=triangle width=0.6]',
    '\t8737733816430 [label="toy_S\nSplitter" shape=triangle width=0.6]',
    '\tedge [dir=foward fontname=Arial]',
    '\t8737734100272 [label="" color="#98a2ad" height=0.15 shape=diamond width=0.15]',
    '\t8737734100272 -> 8737733816409 [labeltooltip="Temperature: 298.15 K\nLiquid flow: 5.55 kmol/hr"]',
    '\t8737733816409:e -> 8737733816430:w [label=" s1"]',
    '\t"-8737734100404" [label="" shape=triangle width=0.15]',
    '\t8737733816430 -> "-8737734100404" [labeltooltip="Liquid flow: 3.98 kmol/hr"]',
]
BUILD_B = [line.replace("87377338164", "87448321810").replace("87377341004", "87448321999")
           .replace("87377341002", "87448321888") for line in BUILD_A]


def test_two_builds_of_one_plant_draw_the_same_digraph():
    from openferment_core.workers.dot_names import stable_names

    assert BUILD_A != BUILD_B
    a, b = stable_names(BUILD_A), stable_names(BUILD_B)
    assert a == b
    text = "\n".join(a)
    # No address survives in a statement's names; labels, tooltips and
    # attributes are BioSTEAM's own, untouched (the maxiter keeps its digits).
    assert not re.search(r"\b\d{9,}\b(?!0{6})", text.replace("10000000000000000000", ""))
    assert "maxiter=10000000000000000000" in text
    assert 'n1 [label="toy_M\nMixer"' in text and 'n2 [label="toy_S\nSplitter"' in text
    assert "n3 -> n1 [" in text and "n1:e -> n2:w [" in text and "n2 -> n4 [" in text
    assert "Liquid flow: 5.55 kmol/hr" in text


def test_a_cluster_s_nodes_are_renamed_and_a_label_line_of_digits_is_not():
    from openferment_core.workers.dot_names import stable_names

    body = ['\tsubgraph cluster_sys {', '\t\t8737733816409 [label="M101\n123\nMixer"]', '\t}',
            '\t8737733816409 -> 8737734100272', '\tsubgraph cluster_b {\n\t\t8737734100272 [label="S"]\n\t}']
    assert stable_names(body) == ['\tsubgraph cluster_sys {', '\t\tn1 [label="M101\n123\nMixer"]', '\t}',
                                  '\tn1 -> n2', '\tsubgraph cluster_b {\n\t\tn2 [label="S"]\n\t}']


def test_a_body_with_no_hashed_names_is_left_as_it_is():
    from openferment_core.workers.dot_names import stable_names

    body = ['\tgraph [rankdir=LR]', '\tM1 [label="M1"]', '\tM1 -> S1']
    assert stable_names(body) == body


@pytest.mark.sim
def test_a_drawn_run_names_no_address_and_two_workers_draw_it_alike(tmp_path, monkeypatch):
    # A STAND-IN `dot` that copies each node name it reads into a <title>,
    # as Graphviz does: what it draws is a function of the names it is fed.
    from openferment_core.workers import SimWorker

    fake = tmp_path / "bin"
    fake.mkdir()
    dot = fake / "dot"
    dot.write_text(
        f"#!{sys.executable}\n"
        "import re, sys\n"
        "src = sys.stdin.read()\n"
        "names = re.findall(r'^\\t(\"?[^\\s\\[\"]+\"?) \\[', src, re.M)\n"
        "sys.stdout.write('<svg>' + ''.join('<title>%s</title>' % n for n in names) + '</svg>')\n")
    dot.chmod(0o755)
    monkeypatch.setenv("PATH", f"{fake}{os.pathsep}{os.environ.get('PATH', '')}")
    drawn = []
    for _ in range(2):
        w = SimWorker("openferment_core.workers.proforma_worker", timeout_s=proforma.START_TIMEOUT_S)
        try:
            r = w.call("run", {"flowsheet": "toy", "base": {}, "specs": {}, "samples": 0, "seed": 0, "diagram": True})
        finally:
            w.close()
        drawn.append(r["tables"]["diagram"])
    titles = re.findall(r"<title>([^<]*)</title>", drawn[0])
    assert titles and not any(re.fullmatch(r'"?-?\d+"?', t) for t in titles), titles
    assert drawn[0] == drawn[1]
