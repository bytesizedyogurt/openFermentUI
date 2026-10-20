"""The gates (OF-BLD-015 §7.4): one table, one row a gate.

A write tool whose (module, action) a row names writes nothing: the call
becomes a proposal (`proposals.propose`) with `state: proposed`, and Home
shows it with the one button a person presses. Adding a gate is a row here
and a row in `docs/TOOLS.md`, never a special case in a tool.

`server` says whether the service can carry the action out itself in the
person's name when they press the button (a check asked for; an extraction
once the budget allows). Otherwise the button takes the person to `route`,
and the proposal records that it was handed to them.

The spend gate is the one a tool reaches at run time: an extraction is free
until the budget refuses it, and then it is proposed for when the budget
allows. Its row is here like the others so the table is the whole list.
"""
from __future__ import annotations

from dataclasses import dataclass

# Names a person cannot sign with (biorepo.write's list, kept in step by test).
PLACEHOLDER_NAMES = frozenset({"you", "me", "reviewer", "user", "test", "model", "postdoc"})


@dataclass(frozen=True)
class Gate:
    id: str
    # What the gate covers, in words, as docs/TOOLS.md says it.
    covers: str
    # The (module, action) pairs that stop here.
    actions: tuple[tuple[str, str], ...]
    # What the button on Home does, in words.
    how: str
    # Where the button takes the person when the server cannot act; None when it can.
    route: str | None
    server: bool


GATES: tuple[Gate, ...] = (
    Gate("publish", "publish to the commons",
         (("biorepo", "publish"), ("dominion", "publish"), ("runbooks", "publish")),
         "publish it from the module, in your name", "/biorepo", False),
    Gate("spend", "spend past the ask or the daily budget",
         (("intake", "extract"),),
         "extract it when the budget allows", None, True),
    Gate("lock", "lock a prediction a person will test",
         (("runbooks", "lock"),),
         "open the runbook and press Lock predictions", "/runbooks", False),
    Gate("sign", "sign a Guild entry",
         (("guild", "evidence"), ("guild", "person"), ("guild", "policy")),
         "record it on Guild in your name", "/guild", False),
    # A check's outcome is never proposed: an assessor runs it at the bench,
    # and guild record_check is refused in words (OF-BLD-016 §1.R finding 12).
    Gate("personnel", "mark a personnel check",
         (("guild", "propose_check"),),
         "ask for the check in your name", None, True),
    Gate("bench", "send a protocol to the bench",
         (("runbooks", "deposit"), ("runbooks", "run")),
         "start the deposition on the bench", "/runbooks/protocols", False),
    Gate("notebook", "write a note under a person's name",
         (("home", "note"),),
         "accept the note; it is kept under your name", None, True),
)

BY_ACTION: dict[tuple[str, str], Gate] = {pair: g for g in GATES for pair in g.actions}
BY_ID: dict[str, Gate] = {g.id: g for g in GATES}


def gated(module: str, action: str) -> Gate | None:
    return BY_ACTION.get((module, action))
