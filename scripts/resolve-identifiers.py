#!/usr/bin/env python
"""Propose DOIs for the seed papers that have none (OF-BLD-012.1 F9).

    pnpm ids:propose              # asks Crossref, writes the proposal file
    pnpm ids:apply <file.tsv>     # writes the APPROVED rows into the seed

LIVE. The first command makes one Crossref request per unidentified paper —
73 of them as this is written — at one a second, and writes
`core/data/identifiers-proposed.tsv`, which is gitignored. IT WRITES NOTHING
TO THE SEED. Crossref is free and needs no key.

Then a person reads the file. Each row carries the seed's title and year, the
best match Crossref returned, its DOI, Crossref's own score and a title
similarity. The first column is the verdict, and it is the only column that
matters to the second command:

    PROPOSE   the title matches to 92 % and the year is within one — this
              script's opinion, and not enough on its own
    REVIEW    everything else, including a paper Crossref did not recognise

Change a verdict to APPROVED for every row you have actually checked, and
delete or leave the rest. `--apply` writes those and only those. Nothing in
this file is a fact until a person has said so, because a wrong DOI attaches
a paper's whole record set to somebody else's work and every later fetch,
quote and promotion inherits the mistake in silence.

After the DOIs land, `pnpm intake:fetch --all` resolves PMCIDs through
Europe PMC as it already does, and the records on those papers stop being
refused by `biorepo.write`.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

CORE = Path(__file__).resolve().parent.parent / "core"
sys.path.insert(0, str(CORE))

from openferment_core import identifiers as ids  # noqa: E402
from openferment_core.corpus import load_corpus  # noqa: E402

PAUSE_SECONDS = 1.0


def unidentified() -> list[dict]:
    """Every seed paper with no PMCID, DOI or PMID — the ones a decision
    about which `biorepo.write` refuses."""
    return [
        p for p in load_corpus().papers
        if not (p.get("pmcid") or p.get("doi") or p.get("pmid"))
    ]


def do_propose(out: Path, limit: int | None) -> int:
    papers = unidentified()
    if limit:
        papers = papers[:limit]
    print(f"{len(papers)} papers with no identifier; asking Crossref, one a second.\n")

    rows: list[ids.Proposal] = []
    for n, paper in enumerate(papers, 1):
        if n > 1:
            time.sleep(PAUSE_SECONDS)
        try:
            hits = ids.crossref(str(paper.get("title") or ""), paper.get("year"))
        except Exception as e:  # a failed lookup is a REVIEW row, not a dead run
            print(f"  {paper['id']:5} ! {type(e).__name__}: {e}")
            hits = []
        row = ids.propose([paper], lambda *_: hits)[0]
        rows.append(row)
        print(f"  {row.paperId:5} {row.verdict:8} {row.similarity:>5} {row.doi or '—'}")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(ids.to_tsv(rows), encoding="utf-8")
    proposed = sum(1 for r in rows if r.verdict == "PROPOSE")
    print(f"\nwrote {out}")
    print(f"  {proposed} PROPOSE, {len(rows) - proposed} REVIEW — nothing written to the seed.")
    print("  Read it, change the verdicts you have CHECKED to APPROVED, then:")
    print(f"    pnpm ids:apply {out}")
    return 0


def do_apply(path: Path) -> int:
    if not path.exists():
        print(f"✗ {path} does not exist", file=sys.stderr)
        return 1
    rows = ids.from_tsv(path.read_text(encoding="utf-8"))
    approved = [r for r in rows if r.verdict == "APPROVED"]
    if not approved:
        print(f"{len(rows)} rows, none marked APPROVED. Nothing to write.")
        print("  This command writes a DOI into the seed only for a row a person has approved.")
        return 0
    try:
        changed = ids.apply_approved(approved)
    except ids.SeedPatchRefused as e:
        print(f"✗ {e}", file=sys.stderr)
        return 1
    for line in changed:
        print(f"  {line}")
    skipped = len(approved) - len(changed)
    print(f"\n{len(changed)} paper(s) patched in src/data/corpus/" + (f"; {skipped} already had one." if skipped else "."))
    if changed:
        print()
        print(_diff() or "  (no diff available — `git diff src/data/corpus/` will show it)")
        print("  Run `pnpm verify` and commit the seed change.")
        print("  Then `pnpm intake:fetch --all` to resolve PMCIDs for the newly identified papers.")
    return 0


def _diff() -> str:
    """The patch, as a person would read it before committing it. The seed is
    the one thing in this repo a script may not change quietly, so the change
    is shown here and not merely announced."""
    import subprocess

    try:
        out = subprocess.run(
            ["git", "diff", "--", "src/data/corpus/"],
            cwd=Path(__file__).resolve().parent.parent,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except Exception:
        return ""
    return out.stdout if out.returncode == 0 else ""


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", metavar="FILE", help="write the APPROVED rows of FILE into the seed")
    parser.add_argument("--out", default=str(ids.PROPOSALS), help="where to write the proposal file")
    parser.add_argument("--limit", type=int, help="ask about only the first N papers (for a trial run)")
    args = parser.parse_args(argv)

    if args.apply:
        return do_apply(Path(args.apply))
    try:
        return do_propose(Path(args.out), args.limit)
    except FileNotFoundError as e:
        print(f"✗ {e}\n  Run `pnpm export:corpus` first — this reads the projection, not the TypeScript.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
