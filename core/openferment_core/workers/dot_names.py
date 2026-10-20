"""Stable node names for a BioSTEAM digraph (OF-BLD-019 §7.R, finding 5).

BioSTEAM names every node of the digraph it hands Graphviz `str(hash(obj))`,
the unit's or the stream's address in that process, and Graphviz writes each
name into the SVG it draws (a node's `<title>` and comment, an edge's
`a->b`). Two builds of one plant therefore drew two different SVGs, and a
kept run whose output holds the drawing never replayed identically. The
Proforma worker renames the nodes by their order of first appearance in the
digraph's body before Graphviz draws it, so the drawing is a function of the
plant alone. Labels, tooltips and every attribute are BioSTEAM's own and are
left as they are; a name that is not all digits (an address) is left too.

Pure text: no BioSTEAM here, so the service and its tests import it freely.
"""
from __future__ import annotations

import re

# A statement starts a line with tabs (one a level: a cluster's subgraph
# nests its own); a label's or tooltip's next line starts with its text.
# A node statement: `\t<name> [attrs]`, or `\t<name>` alone.
_NODE = re.compile(r'^(\t+)("?)(-?\d+)\2(?=\s*(?:\[|$))')
# An edge statement: `\t<name>[:port] -> <name>[:port] ...`.
_EDGE = re.compile(r'^(\t+)("?)(-?\d+)\2((?::\w+)?\s*->\s*)("?)(-?\d+)\5')


def stable_names(body: list[str]) -> list[str]:
    """The digraph body with each address-named node renamed `n1`, `n2`, …
    in the order the body first names it; every other line and every
    attribute as it was."""
    names: dict[str, str] = {}

    def name(raw: str) -> str:
        if raw not in names:
            names[raw] = f"n{len(names) + 1}"
        return names[raw]

    def renamed(line: str) -> str:
        edge = _EDGE.match(line)
        if edge:
            return f"{edge[1]}{name(edge[3])}{edge[4]}{name(edge[6])}{line[edge.end():]}"
        node = _NODE.match(line)
        if node:
            return f"{node[1]}{name(node[3])}{line[node.end():]}"
        return line

    # An element of the body may hold several lines (a subgraph's, or a
    # label's line breaks): each is read on its own.
    return ["\n".join(renamed(line) for line in element.split("\n")) for element in body]
