"""Git merge driver for core/data/biorepo.json (OF-BLD-012 §B.8).

    python scripts/host/merge_biorepo.py BASE OURS THEIRS

Guild writes review decisions into biorepo.json on whichever machine the
reviewer used, and two machines adding decisions to one JSON object always
collide as text, even when they decided different records. Git then writes
conflict markers into the file the running service reads, and Guild stops.

This merges by record instead. For every record id in `decisions` and in
`records`, three-way: the side that changed it since BASE wins; a change on
both sides to the same thing is one change; two different decisions on the
same record are settled by the later one (`at`), and named on stderr. What
cannot be settled that way (a withdrawal on one side and a change on the
other, two decisions at the same instant) leaves OURS exactly as it was,
goes to stderr, and exits 1, so git stops and nothing unparseable is ever
written. A clean merge is written to OURS and exits 0.

Registered per clone by scripts/host/lib.sh (`git config merge.biorepo.*`)
and attached to the file by .gitattributes. Needs only the standard library;
when openferment_core is importable it also validates the result against
the BioRepo model and writes it in the model's own format.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "core"))

EMPTY = {"version": 1, "decisions": {}, "records": []}


def load(path: Path) -> dict[str, Any]:
    """A side of the merge. An empty file (git's BASE when the file is new on
    both sides) is an empty repository."""
    text = path.read_text(encoding="utf-8").strip()
    return json.loads(text) if text else dict(EMPTY)


def _keys(base: dict, ours: dict, theirs: dict) -> list[str]:
    return list(ours) + [k for k in theirs if k not in ours] + [k for k in base if k not in ours and k not in theirs]


def _later(o: Any, t: Any) -> str | None:
    """Which side's decision is the later one, 'ours' or 'theirs', or None
    when that cannot be told (a withdrawal on one side, no time, a tie)."""
    if not (isinstance(o, dict) and isinstance(t, dict)):
        return None
    a, b = o.get("at"), t.get("at")
    if not a or not b or a == b:
        return None
    return "ours" if a > b else "theirs"


def merge(base: dict, ours: dict, theirs: dict) -> tuple[dict, list[str], list[str]]:
    """The merged repository, the records two sides decided differently that
    the later decision settled, and the disagreements left (empty when clean).

    A record decided differently on two machines is settled by the later
    decision (ISO-8601 `at` strings order as times): one reviewer on two
    devices means the later is the current judgement, and git history keeps
    the other. A withdrawal against a change, or two decisions at the same
    instant, cannot be settled that way and is left for a person."""
    conflicts: list[str] = []
    settled: list[str] = []
    versions = {d.get("version", 1) for d in (base, ours, theirs)}
    if len(versions) > 1:
        return ours, settled, [f"version {sorted(versions)}"]

    bd, od, td = base.get("decisions", {}), ours.get("decisions", {}), theirs.get("decisions", {})
    winner: dict[str, str] = {}
    decisions: dict[str, Any] = {}
    for key in _keys(bd, od, td):
        b, o, t = bd.get(key), od.get(key), td.get(key)
        if o == t or t == b:
            value = o
        elif o == b:
            value = t
        elif (side := _later(o, t)) is not None:
            winner[key] = side
            settled.append(key)
            value = o if side == "ours" else t
        else:
            conflicts.append(f"decision {key}")
            value = o
        if value is not None:
            decisions[key] = value

    by_id = lambda side: {r["id"]: r for r in side.get("records", [])}  # noqa: E731
    br, orr, tr = by_id(base), by_id(ours), by_id(theirs)
    records: dict[str, Any] = {}
    for key in _keys(br, orr, tr):
        b, o, t = br.get(key), orr.get(key), tr.get(key)
        if o == t or t == b:
            value = o
        elif o == b:
            value = t
        elif key in winner:
            # The candidate copy follows the decision it sits beside.
            value = o if winner[key] == "ours" else t
        else:
            conflicts.append(f"record {key}")
            value = o
        if value is not None:
            records[key] = value
    merged = {**ours, "version": versions.pop(), "decisions": decisions, "records": list(records.values())}
    return merged, settled, conflicts


def render(repo: dict) -> str:
    try:
        from openferment_core.models import BioRepo
    except ImportError:
        return json.dumps(repo, indent=2, ensure_ascii=False) + "\n"
    return BioRepo.model_validate(repo).model_dump_json(indent=2, exclude_none=True) + "\n"


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: merge_biorepo.py BASE OURS THEIRS", file=sys.stderr)
        return 2
    base_p, ours_p, theirs_p = (Path(a) for a in argv)
    try:
        base, ours, theirs = load(base_p), load(ours_p), load(theirs_p)
        merged, settled, conflicts = merge(base, ours, theirs)
        text = render(merged) if not conflicts else ""
    except (OSError, ValueError, KeyError) as e:
        print(f"biorepo merge: cannot merge, left as it was: {e}", file=sys.stderr)
        return 1
    if conflicts:
        print("biorepo merge: these cannot be settled by the later decision, left as it was:", file=sys.stderr)
        for c in conflicts:
            print(f"  {c}", file=sys.stderr)
        return 1
    if settled:
        print(f"biorepo merge: decided differently on two machines, the later decision kept: {', '.join(settled)}",
              file=sys.stderr)
    tmp = ours_p.with_name(ours_p.name + ".merge-tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(ours_p)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
