"""H12-02's mutations of core/openferment_core/engine/conform.py, one at a time.

    python3 mutate.py <conform.py> <id>       apply mutation <id> (its old text must occur exactly once)
    python3 mutate.py <conform.py> --list     print each id, the check it touches, the function it lies in

M50 to M54 are the candidate's five (bughunt/notes/H12/mutations.json); C2 is a control the suite is known
to catch (check 2 holding whatever the parameters' origins are; test_engines.py:571-582 fails it).
"""
from __future__ import annotations

import sys
from pathlib import Path

MUTATIONS = {
    "M52": ("check 1", "_bare_number",
            "    ok = codes == [422, 422] and bool(tool.error) and not calls and not kept",
            "    ok = codes == [422, 422] and bool(tool.error) and not kept"),
    "M51": ("check 3", "_run_twice",
            '        ok = a.id == b.id and rows == 1 and a.status == "done" and a.engine == engine.name and keyed and diagnosed',
            '        ok = a.id == b.id and a.status == "done" and a.engine == engine.name and keyed and diagnosed'),
    "M50": ("check 4", "_replayed",
            "        four = (bool(r.withinTolerance or r.identical),",
            "        four = (True,"),
    "M53": ("check 5", "_replayed",
            "        return four, (bool(run.sff.valid and run.sff.score is not None),",
            "        return four, (run.sff.score is not None,"),
    "M54": ("check 8", "_asked_by",
            "    ok = who == by and run.by == by",
            "    ok = run.by == by"),
    "C2": ("check 2", "_origins",
           "    if wrong:\n        lack = ",
           "    if False and wrong:\n        lack = "),
}


def main(argv: list[str]) -> int:
    path, which = Path(argv[0]), argv[1]
    if which == "--list":
        for k, (check, fn, _, _) in MUTATIONS.items():
            print(k, check.replace(" ", "_"), fn)
        return 0
    _, _, old, new = MUTATIONS[which]
    text = path.read_text(encoding="utf-8")
    n = text.count(old)
    if n != 1:
        print(f"{which}: its old text occurs {n} times in {path}", file=sys.stderr)
        return 2
    path.write_text(text.replace(old, new), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
