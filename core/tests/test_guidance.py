"""The guidance files (execution prompt §10 stage 8.2; acceptance A7).

CLAUDE.md stays under 250 lines and labels every line: a heading names a
section, and every other line that holds words starts `- R:`, `- P:` or
`- C:`. It has the sections stage 8 names; each architecture line names a
decision record that exists, and each contract line a document that exists.
The decision records 000 to 014 exist, each with its decision and its
revisit condition. docs/PROGRESS.md opens with a Resume section of numbered
steps a fresh session follows cold.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LABEL = re.compile(r"^- (R|P|C): \S")
SECTIONS = ("Mission and scope", "Run and test", "Verified constraints and sources", "Architecture decisions",
            "Communication contracts", "Working assumptions", "Open questions", "Revisit conditions",
            "Stop conditions", "Where the history lives")
RECORDS = range(0, 15)


def _lines() -> list[str]:
    return (ROOT / "CLAUDE.md").read_text(encoding="utf-8").splitlines()


def _section(title: str) -> list[str]:
    lines = _lines()
    start = next(i for i, line in enumerate(lines) if line.startswith(f"## {title}"))
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return [line for line in lines[start + 1:end] if line.strip()]


def test_claude_md_is_under_250_lines_and_labels_every_line():
    lines = _lines()
    assert len(lines) < 250, len(lines)
    unlabelled = [(n, line) for n, line in enumerate(lines, 1)
                  if line.strip() and not line.startswith("#") and not LABEL.match(line)]
    assert not unlabelled


def test_claude_md_has_the_sections_stage_8_names_in_order():
    headings = [line[3:] for line in _lines() if line.startswith("## ")]
    assert [next(s for s in SECTIONS if h.startswith(s)) for h in headings] == list(SECTIONS)


def test_every_decision_record_exists_with_its_decision_and_revisit_condition():
    for n in RECORDS:
        (path,) = (ROOT / "docs" / "decisions").glob(f"ADR-{n:03d}-*.md")
        text = path.read_text(encoding="utf-8")
        assert "## Decision" in text and "## Revisit condition" in text, path.name


def test_each_architecture_line_names_a_decision_record_that_exists():
    named = [re.findall(r"ADR-(\d{3})", line) for line in _section("Architecture decisions")]
    assert all(named) and sorted(int(n[-1]) for n in named) == list(RECORDS)


def test_each_contract_line_names_a_document_that_exists():
    for line in _section("Communication contracts"):
        paths = re.findall(r"`((?:docs/|core/|COMPONENTS|\.mcp)[^`\s]*)`", line)
        assert paths, line
        assert all((ROOT / p).exists() for p in paths), line


def test_progress_opens_with_a_resume_section_a_fresh_session_follows():
    text = (ROOT / "docs" / "PROGRESS.md").read_text(encoding="utf-8")
    resume = text.split("## Resume", 1)[1].split("\n## ", 1)[0]
    steps = re.findall(r"^(\d+)\. ", resume, flags=re.M)
    assert steps and steps == [str(i) for i in range(1, len(steps) + 1)]
    assert "git checkout" in resume and "pnpm test:core" in resume and "db:migrate" in resume
