#!/usr/bin/env python
"""Thread P, proposed by a rule and written on a person's approval
(OF-BLD-014 §2.3).

    pnpm thread:propose                                         # LIVE, no key
    pnpm thread:apply <file.tsv> --approved-by "<name>"

The first asks Europe PMC once with the rule in `threadp.py`, looks up every
id in `docs/thread-p-include.txt`, and writes `core/data/thread-p-proposed.tsv`.
IT WRITES NOTHING TO THE SEED. The file travels on the data branch
(`pnpm data:push`), so the list a person approves survives a rebuilt VM.

Then a person reads it. The first column is the verdict:

    PROPOSE   the rule's opinion: among the most-cited research articles or
              reviews that pass its filters. Not an approval.
    REVIEW    passed the filters, outside the rule's count.
    INCLUDE   named in docs/thread-p-include.txt; written whatever the rule says.

Change the verdict to APPROVED on each row you want in thread P. The second
command writes the APPROVED and INCLUDE rows, and no others, into
`src/data/corpus/threadP.ts` under your name, and prints the diff to commit.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

CORE = Path(__file__).resolve().parent.parent / "core"
ROOT = CORE.parent
sys.path.insert(0, str(CORE))

from openferment_core import threadp  # noqa: E402


def _path(raw: str) -> Path:
    """A path typed at the repository root, even though pnpm runs this from
    core/: `core/data/thread-p-proposed.tsv` must not become core/core/…"""
    p = Path(raw)
    return p if p.is_absolute() else ROOT / p


def do_propose(out: Path) -> int:
    print(f"asking Europe PMC: {threadp.QUERY}\n")
    results = threadp.search()
    if results:
        print("keys of the first result:", ", ".join(sorted(results[0].keys())), "\n")
        threadp.check_keys(results[0])
    includes = []
    for key in threadp.read_includes():
        found = threadp.lookup(key)
        includes.append(found)
        print(f"  include {key}: {'found with open-access text' if isinstance(found, dict) else 'no open-access text; catalogued without it'}")
    rows = threadp.propose(results, includes, threadp.seeded_ids(threadp.read_seed()))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(threadp.to_tsv(rows), encoding="utf-8")
    kept = sum(1 for r in results if threadp.eligible(r))
    counts = {v: sum(1 for r in rows if r.verdict == v) for v in threadp.VERDICTS}
    print(f"{len(results)} results asked for, {kept} pass the filters.")
    print(f"  {counts['PROPOSE']} PROPOSE, {counts['REVIEW']} REVIEW, {counts['INCLUDE']} INCLUDE — nothing written to the seed.")
    print(f"wrote {out}")
    print("  Mark the rows you approve APPROVED, then:")
    print(f'    pnpm thread:apply {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out} --approved-by "<your name>"')
    return 0


def do_apply(path: Path, approved_by: str) -> int:
    if not path.exists():
        print(f"✗ {path} does not exist", file=sys.stderr)
        return 1
    rows = threadp.from_tsv(path.read_text(encoding="utf-8"))
    try:
        added = threadp.apply(rows, approved_by)
    except threadp.ThreadPRefused as e:
        print(f"✗ {e}", file=sys.stderr)
        return 1
    for line in added:
        print(f"  {line}")
    print(f"\n{len(added)} paper(s) added to {threadp.SEED_FILE.relative_to(ROOT)}.")
    diff = subprocess.run(["git", "diff", "--", str(threadp.SEED_FILE)], cwd=ROOT, capture_output=True, text=True)
    if diff.stdout:
        print(diff.stdout)
    print("Run `pnpm verify` and commit the seed change. Then `pnpm export:corpus` and `pnpm intake:fetch --all`.")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", metavar="FILE", help="write the APPROVED and INCLUDE rows of FILE into the seed")
    parser.add_argument("--approved-by", metavar="NAME", default="", help="the person approving (required with --apply)")
    parser.add_argument("--out", default=str(threadp.PROPOSALS), help="where propose writes")
    args = parser.parse_args(argv)
    if args.apply:
        return do_apply(_path(args.apply), args.approved_by)
    return do_propose(_path(args.out))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
