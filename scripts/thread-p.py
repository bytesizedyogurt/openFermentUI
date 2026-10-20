#!/usr/bin/env python
"""Threads P and Q, proposed by a rule and written on a person's approval
(OF-BLD-014 §2.3).

    pnpm thread:propose                                         # LIVE, no key
    pnpm thread:apply <file.tsv> --approved-by "<name>"
    pnpm thread:propose:q                                       # thread Q
    pnpm thread:apply:q <file.tsv> --approved-by "<name>"

`--thread P|Q` picks the rule; thread P is the default. The first command asks
Europe PMC once with the thread's rule in `threadp.py`, looks up every id in
its include file (`docs/thread-p-include.txt`, `docs/thread-q-include.txt`),
and writes its proposal file (`core/data/thread-p-proposed.tsv`,
`core/data/thread-q-proposed.tsv`). IT WRITES NOTHING TO THE SEED. The file
travels on the data branch (`pnpm data:push`), so the list a person approves
survives a rebuilt VM. Thread Q's include file may also name a report on OSTI
(`osti:<id>`) or a strain entry in the Saccharomyces Genome Database
(`sgd:<id>`); each is looked up at its source and carries the address Intake
fetches its text from in the last column, `sourceUrl`.

Then a person reads it. The first column is the verdict:

    PROPOSE   the rule's opinion: among the most-cited research articles or
              reviews that pass its filters. Not an approval.
    REVIEW    passed the filters, outside the rule's count.
    INCLUDE   named in the include file; written whatever the rule says.

Change the verdict to APPROVED on each row you want in the thread. The second
command writes the APPROVED and INCLUDE rows, and no others, into the
thread's seed file (`src/data/corpus/threadP.ts`, `threadQ.ts`) under your
name, and prints the diff to commit.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

CORE = Path(__file__).resolve().parent.parent / "core"
ROOT = CORE.parent
sys.path.insert(0, str(CORE))

from openferment_core import atomic, threadp  # noqa: E402


def _path(raw: str) -> Path:
    """A path typed at the repository root, even though pnpm runs this from
    core/: `core/data/thread-p-proposed.tsv` must not become core/core/…"""
    p = Path(raw)
    return p if p.is_absolute() else ROOT / p


def _found(key: str, found: object) -> str:
    if isinstance(found, threadp.Row):
        return f"found at its source: {found.title}"
    if isinstance(found, dict):
        return "found with open-access text"
    return "no open-access text; catalogued without it"


def do_propose(out: Path, rule: threadp.ThreadRule) -> int:
    print(f"thread {rule.letter}, asking Europe PMC: {rule.query}\n")
    results = threadp.search(rule=rule)
    if results:
        print("keys of the first result:", ", ".join(sorted(results[0].keys())), "\n")
        threadp.check_keys(results[0])
    includes = []
    for key in threadp.read_includes(rule=rule):
        try:
            found = threadp.lookup(key, rule)
        except threadp.LookupFailed as e:
            print(f"✗ include {key}: {e}", file=sys.stderr)
            return 1
        includes.append(found)
        print(f"  include {key}: {_found(key, found)}")
    rows = threadp.propose(results, includes, threadp.seeded_ids(threadp.read_seed(rule=rule)), rule)
    atomic.write_text(out, threadp.to_tsv(rows))
    kept = sum(1 for r in results if threadp.eligible(r, rule))
    counts = {v: sum(1 for r in rows if r.verdict == v) for v in threadp.VERDICTS}
    print(f"{len(results)} results asked for, {kept} pass the filters.")
    print(f"  {counts['PROPOSE']} PROPOSE, {counts['REVIEW']} REVIEW, {counts['INCLUDE']} INCLUDE — nothing written to the seed.")
    print(f"wrote {out}")
    print("  Mark the rows you approve APPROVED, then:")
    command = "thread:apply" if rule is threadp.THREAD_P else f"thread:apply:{rule.letter.lower()}"
    print(f'    pnpm {command} {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out} --approved-by "<your name>"')
    return 0


def do_apply(path: Path, approved_by: str, rule: threadp.ThreadRule) -> int:
    if not path.exists():
        print(f"✗ {path} does not exist", file=sys.stderr)
        return 1
    rows = threadp.from_tsv(path.read_text(encoding="utf-8"))
    try:
        added = threadp.apply(rows, approved_by, rule=rule)
    except threadp.ThreadRefused as e:
        print(f"✗ {e}", file=sys.stderr)
        return 1
    for line in added:
        print(f"  {line}")
    print(f"\n{len(added)} paper(s) added to {rule.seed_file.relative_to(ROOT)}.")
    diff = subprocess.run(["git", "diff", "--", str(rule.seed_file)], cwd=ROOT, capture_output=True, text=True)
    if diff.stdout:
        print(diff.stdout)
    print("Run `pnpm verify` and commit the seed change. Then `pnpm export:corpus` and `pnpm intake:fetch --all`.")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--thread", default="P", type=str.upper, choices=sorted(threadp.THREADS),
                        help="the thread whose rule runs (default P)")
    parser.add_argument("--apply", metavar="FILE", help="write the APPROVED and INCLUDE rows of FILE into the seed")
    parser.add_argument("--approved-by", metavar="NAME", default="", help="the person approving (required with --apply)")
    parser.add_argument("--out", default=None, help="where propose writes (default: the thread's proposal file)")
    args = parser.parse_args(argv)
    rule = threadp.THREADS[args.thread]
    if args.apply:
        return do_apply(_path(args.apply), args.approved_by, rule)
    return do_propose(_path(args.out) if args.out else rule.proposals, rule)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
