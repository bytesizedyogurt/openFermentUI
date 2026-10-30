"""No seeded science ships (alpha 2.0, acceptance A4; ADR-010).

The TypeScript seed, its projections and the program machinery were deleted
in stage 1. This holds the deletion: the modules are absent, no file under
src/data/ exports records, papers, products, strains, scenarios, protocols,
runbooks or lessons, no projection of the seed waits on disk for the service
to read, the shipped corpus is empty, and no seed record id is written into
the app or the service.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from openferment_core import corpus, guild, module_stores

ROOT = Path(__file__).resolve().parent.parent.parent
SRC = ROOT / "src"
PACKAGE = ROOT / "core" / "openferment_core"

DELETED = [
    # The TypeScript seed and the program machinery (5.1, 5.2).
    "src/data/corpus",
    "src/data/papers.ts",
    "src/data/records.ts",
    "src/data/strains.ts",
    "src/data/products.ts",
    "src/data/runbooks.ts",
    "src/data/protocols.ts",
    "src/data/scenarios.ts",
    "src/data/learn.ts",
    "src/data/flows.ts",
    "src/data/livePrompts.ts",
    "src/data/reference.ts",
    "src/data/figureSamples.json",
    "src/data/programs.ts",
    "src/data/skills.ts",
    "src/data/clearanceFindings.ts",
    "src/engine/grids.ts",
    "src/engine/clearance.ts",
    "src/lib/programShows.ts",
    "scripts/export-corpus.ts",
    "core/openferment_core/programs.py",
    "core/openferment_core/threadp.py",
    "core/openferment_core/identifiers.py",
    "core/openferment_core/evalo.py",
    "core/openferment_core/flowsheets/pha_sugar_v0.py",
    # The demo infrastructure and the bespoke retrieval (5.3, 5.4).
    "core/openferment_core/demo.py",
    "core/openferment_core/passages.py",
    "core/openferment_core/retrieve.py",
    "core/openferment_core/embed.py",
    "core/openferment_core/rerank.py",
    "core/openferment_core/expand.py",
    "core/openferment_core/rageval.py",
    "core/openferment_core/anchor_report.py",
    "core/tests/fixtures/demo",
    "core/tests/fixtures/overlay-smoke.json",
    # Dominion (5.6).
    "src/screens/Dominion.tsx",
    "src/screens/Molecules.tsx",
    "src/screens/MoleculeDetail.tsx",
    "src/components/Clearance.tsx",
]

# What the seed was projected into for the service to read. A stale copy left
# on a machine would feed the service the deleted seed without a word.
PROJECTIONS = ["corpus.json", "modules.json", "skills.json"]

SEEDED_TYPES = ("ExtractionRecord", "Paper", "Product", "Strain", "Scenario", "Protocol", "Runbook", "Lesson",
                "LearnModule")
SEEDED_NAMES = re.compile(r"^(RECORDS|PAPERS|PRODUCTS|STRAINS|SCENARIOS|PROTOCOLS|RUNBOOKS|LESSONS|MODULES|LEARN)"
                          r"(_|$)")
EXPORT = re.compile(r"^export\s+const\s+(\w+)\s*(?::\s*([\w<>\[\], ]+?))?\s*=", re.MULTILINE)
SEED_RECORD_ID = re.compile(r"\br-[A-S]\d{1,2}-\d+\b")


@pytest.mark.parametrize("path", DELETED)
def test_a_deleted_module_is_absent(path):
    assert not (ROOT / path).exists(), f"{path} was deleted with the seed (ADR-010)"


@pytest.mark.parametrize("name", PROJECTIONS)
def test_no_projection_of_the_seed_waits_on_disk(name):
    stale = PACKAGE / "data" / name
    assert not stale.exists(), f"{stale} is a projection of the deleted seed: delete it"


def test_no_file_under_src_data_exports_seeded_content():
    found = []
    for path in sorted((SRC / "data").rglob("*.ts")):
        for m in EXPORT.finditer(path.read_text(encoding="utf-8")):
            name, annotation = m.group(1), (m.group(2) or "")
            typed = any(re.search(rf"\b{t}\b\s*\[\]", annotation) for t in SEEDED_TYPES)
            if SEEDED_NAMES.match(name) or typed:
                found.append(f"{path.relative_to(ROOT)}: {name}")
    assert found == [], found


def test_the_shipped_stores_are_empty():
    assert corpus.DATA == PACKAGE / "data" / "corpus.json"
    corpus.load_corpus.cache_clear()
    try:
        shipped = corpus.load_corpus()
        assert shipped.papers == [] and shipped.records == []
        assert shipped.products == () and shipped.strains == ()
    finally:
        corpus.load_corpus.cache_clear()
    projection = module_stores._projection()
    assert all(not rows for module in projection.values() for rows in module.values())


def test_guild_ships_no_skill():
    guild._projection.cache_clear()
    try:
        assert not guild._projection(str(PACKAGE / "data" / "skills.json")).get("skills")
    finally:
        guild._projection.cache_clear()


def test_no_seed_record_id_is_written_into_the_app_or_the_service():
    found = []
    for base, suffixes in ((SRC, {".ts", ".tsx"}), (PACKAGE, {".py", ".json", ".yaml"})):
        for path in sorted(base.rglob("*")):
            if path.suffix not in suffixes or "__pycache__" in path.parts or not path.is_file():
                continue
            for m in SEED_RECORD_ID.finditer(path.read_text(encoding="utf-8")):
                found.append(f"{path.relative_to(ROOT)}: {m.group(0)}")
    assert found == [], found
