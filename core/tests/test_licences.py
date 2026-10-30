"""The licence check decides as the ledger says (OF-BLD-014 §1.2, E.9).

Offline, on packages built in the test: an allowed string passes, an unknown
one fails, an accepted one passes and names who accepted it, and the listing
is rewritten, with the stage failing, when the committed copy is stale. The
check over what is really installed is the verify stage `pnpm check:licences`.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


def _load():
    spec = importlib.util.spec_from_file_location("check_licences", REPO / "scripts" / "check-licences.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolve their annotations through it
    spec.loader.exec_module(module)
    return module


lic = _load()

LEDGER = """
allowed = ["MIT", "Apache2.0", "MIT AND ISC"]

[accepted.certifi]
licence = "MPL-2.0"
by = "Sean Creighton"
date = 2026-10-14
why = "a certificate bundle, used unmodified"

[accepted.py-rust-stemmers]
licence = "no licence metadata"
by = "Sean Creighton"
date = 2026-10-15
why = "a stemmer whose repository carries an MIT licence"
"""


@pytest.fixture
def policy(tmp_path):
    path = tmp_path / "licences.toml"
    path.write_text(LEDGER, encoding="utf-8")
    return lic.load_policy(path)


def package(name, strings, policy, side="python"):
    return lic.Package(side, name, "1.0", tuple(strings), "service", lic.decide(name, strings, policy))


# ── the decision ────────────────────────────────────────────────────────


def test_an_allowed_string_passes(policy):
    verdict = lic.decide("anthropic", ["MIT", "License :: OSI Approved :: MIT License"], policy)
    assert verdict.ok and verdict.string == "MIT" and verdict.how == "allowed"


def test_an_unknown_string_fails_and_says_which(policy):
    verdict = lic.decide("somelib", ["GPL-3.0-only"], policy)
    assert not verdict.ok and "GPL-3.0-only" in verdict.how and "core/licences.toml" in verdict.how


def test_an_accepted_package_passes_and_names_who_accepted_it(policy):
    verdict = lic.decide("certifi", ["MPL-2.0", "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)"], policy)
    assert verdict.ok and verdict.string == "MPL-2.0"
    assert verdict.how == "accepted by Sean Creighton on 2026-10-14"


def test_an_acceptance_covers_its_own_string_alone(policy):
    verdict = lic.decide("certifi", ["GPL-3.0-only"], policy)
    assert not verdict.ok and "accepted as MPL-2.0 by Sean Creighton" in verdict.how


def test_an_acceptance_belongs_to_its_package(policy):
    assert not lic.decide("another-bundle", ["MPL-2.0"], policy).ok


def test_any_of_the_three_fields_can_decide(policy):
    # A License field holding the whole licence text matches nothing; the
    # classifier or the expression beside it still can.
    assert lic.decide("pkg", ["Permission is hereby granted, free of charge...", "MIT"], policy).ok
    assert lic.decide("pkg", ["Permission is hereby granted, free of charge..."], policy).ok is False


def test_the_spelling_is_compared_as_written(policy):
    assert lic.decide("rank-bm25", ["Apache2.0"], policy).ok
    assert not lic.decide("other", ["Apache-2.0"], policy).ok, "Apache-2.0 is a second string"
    assert lic.decide("victory-vendor", ["MIT AND ISC"], policy).ok
    assert not lic.decide("other", ["ISC"], policy).ok, "an expression allows itself, never its parts"


def test_a_package_with_no_licence_metadata_fails(policy):
    verdict = lic.decide("bare", [], policy)
    assert not verdict.ok and "no licence metadata" in verdict.how


def test_names_are_compared_in_their_canonical_spelling(policy):
    assert lic.decide("Certifi", ["MPL-2.0"], policy).ok
    assert lic.canonical("typing_extensions") == lic.canonical("Typing.Extensions") == "typing-extensions"


# ── the ledger ──────────────────────────────────────────────────────────


def test_an_acceptance_needs_a_name_a_date_and_a_reason(tmp_path):
    path = tmp_path / "licences.toml"
    path.write_text('allowed = ["MIT"]\n[accepted.x]\nlicence = "GPL-3.0-only"\ndate = 2026-10-14\n', encoding="utf-8")
    with pytest.raises(ValueError, match="lacks by, why"):
        lic.load_policy(path)


def test_a_model_file_names_its_source_revision_hash_and_who_accepted_it(tmp_path):
    path = tmp_path / "licences.toml"
    path.write_text('allowed = ["MIT"]\n[data.m]\nlicence = "GPL-3.0"\nsource = "s"\nrevision = "r"\nby = "Sean Creighton"\ndate = 2026-10-15\nwhy = "w"\n')
    with pytest.raises(ValueError, match="sha256"):
        lic.load_policy(path)


def test_vendored_code_names_its_source_revision_directory_and_what_was_left_out(tmp_path):
    path = tmp_path / "licences.toml"
    path.write_text('allowed = ["MIT"]\n[vendored.v]\nlicence = "MIT"\nsource = "s"\nrevision = "r"\npath = "core/vendor/v"\nwhy = "w"\n')
    with pytest.raises(ValueError, match="left_out"):
        lic.load_policy(path)


def test_vendored_code_stands_where_the_ledger_says_under_an_allowed_licence(tmp_path):
    (tmp_path / "core" / "vendor" / "kept").mkdir(parents=True)
    (tmp_path / "core" / "vendor" / "kept" / "LICENSE").write_text("MIT License", encoding="utf-8")
    (tmp_path / "core" / "vendor" / "bare").mkdir(parents=True)
    path = tmp_path / "licences.toml"
    entry = 'source = "s"\nrevision = "r"\nleft_out = "nothing"\nwhy = "w"\n'
    path.write_text('allowed = ["MIT"]\n'
                    f'[vendored.kept]\nlicence = "MIT"\npath = "core/vendor/kept"\n{entry}'
                    f'[vendored.bare]\nlicence = "MIT"\npath = "core/vendor/bare"\n{entry}'
                    f'[vendored.gone]\nlicence = "MIT"\npath = "core/vendor/gone"\n{entry}'
                    f'[vendored.copyleft]\nlicence = "GPL-3.0-only"\npath = "core/vendor/kept"\n{entry}', encoding="utf-8")
    faults = lic.vendored_faults(lic.load_policy(path), repo=tmp_path)
    assert len(faults) == 3
    assert any("[vendored.bare]" in f and "no LICENSE" in f for f in faults)
    assert any("[vendored.gone]" in f and "not a directory" in f for f in faults)
    assert any("[vendored.copyleft]" in f and "GPL-3.0-only" in f for f in faults)


def test_the_committed_ledger_holds_the_vendored_sff_toolkit_where_it_stands():
    committed = lic.load_policy()
    [v] = [v for v in committed.vendored if v.id == "pisces_sff"]
    assert v.path == "core/vendor/pisces_sff" and v.licence == "MIT" and len(v.revision) == 40
    assert lic.vendored_faults(committed) == []


def test_the_model_files_are_listed_with_their_hash():
    from openferment_core import geneos_models

    committed = lic.load_policy()
    by_id = {d.id: d for d in committed.data}
    fetched = [m for m in geneos_models.SHELF.values() if m.fetched]
    assert fetched, "the shelf fetches at least one model file"
    for m in fetched:
        assert by_id[m.id].sha256 == m.fetched.sha256, m.id
        assert f"| {m.id} | {by_id[m.id].licence} |" in lic.render([], [], committed)


def test_the_committed_ledger_reads_and_every_acceptance_is_signed():
    committed = lic.load_policy()
    assert committed.allowed
    for acceptance in committed.accepted.values():
        assert acceptance.by.strip() and acceptance.date and acceptance.why.strip()


def test_the_project_itself_is_the_one_package_skipped():
    assert lic.SELF == "openferment-core"
    names = {p.name for p in lic.python_side(lic.load_policy())}
    assert lic.SELF not in {lic.canonical(n) for n in names}


# ── which part uses it ──────────────────────────────────────────────────


def test_the_part_follows_the_lock():
    lock = {"package": [
        {"name": "openferment-core", "dependencies": [{"name": "uvicorn", "extra": ["standard"]}, {"name": "rank-bm25"}],
         "optional-dependencies": {"dev": [{"name": "pytest"}]}},
        {"name": "uvicorn", "dependencies": [{"name": "click"}],
         "optional-dependencies": {"standard": [{"name": "uvloop"}]}},
        {"name": "rank-bm25", "dependencies": [{"name": "numpy"}]},
        {"name": "numpy"}, {"name": "click"}, {"name": "uvloop"},
        {"name": "pytest", "dependencies": [{"name": "pluggy"}]}, {"name": "pluggy"},
    ]}
    parts = lic.python_parts(lock)
    assert parts["rank-bm25"] == "service"
    assert parts["numpy"] == "service, through rank-bm25"
    assert parts["uvloop"] == "service, through uvicorn", "an extra asked of a dependency is followed"
    assert parts["pytest"] == "tests" and parts["pluggy"] == "tests, through pytest"


def test_a_javascript_package_nobody_imports_says_so(tmp_path):
    (tmp_path / "main.tsx").write_text("import { create } from 'zustand';\nimport '@fontsource/spectral/400.css';\n")
    tree = [{"dependencies": {
        "zustand": {"dependencies": {}},
        "@fontsource/spectral": {},
        "react-router-dom": {"dependencies": {"react-router": {"dependencies": {}}}},
    }}]
    parts = lic.javascript_parts(tree, src=tmp_path)
    assert parts["zustand"] == "browser app"
    assert parts["@fontsource/spectral"] == "browser app"
    assert parts["react-router-dom"] == "listed in package.json; no file under src/ imports it"
    assert parts["react-router"] == "through react-router-dom, which no file under src/ imports"


# ── the stage ───────────────────────────────────────────────────────────


def test_the_stage_passes_when_all_pass_and_the_listing_is_current(policy, tmp_path):
    python = [package("anthropic", ["MIT"], policy), package("certifi", ["MPL-2.0"], policy)]
    javascript = [package("victory-vendor", ["MIT AND ISC"], policy, side="javascript")]
    listing = tmp_path / "THIRD_PARTY.md"
    listing.write_text(lic.render(python, javascript, policy), encoding="utf-8")
    code, report = lic.check(python, javascript, policy, listing)
    assert code == 0, report
    assert any("certifi 1.0 (MPL-2.0): accepted by Sean Creighton on 2026-10-14" in line for line in report)


def test_one_failing_package_fails_the_stage_by_name(policy, tmp_path):
    python = [package("anthropic", ["MIT"], policy), package("somelib", ["GPL-3.0-only"], policy)]
    listing = tmp_path / "THIRD_PARTY.md"
    listing.write_text("# the committed listing\n", encoding="utf-8")
    code, report = lic.check(python, [], policy, listing)
    assert code == 1
    assert any("python somelib 1.0: GPL-3.0-only" in line for line in report)
    assert listing.read_text(encoding="utf-8") == "# the committed listing\n", "a failing tree is never listed"


def test_a_stale_listing_is_rewritten_and_fails_the_stage(policy, tmp_path):
    python = [package("anthropic", ["MIT"], policy)]
    listing = tmp_path / "THIRD_PARTY.md"
    listing.write_text("# an older listing\n", encoding="utf-8")
    code, report = lic.check(python, [], policy, listing)
    assert code == 1 and any("was stale and has been rewritten" in line for line in report)
    assert listing.read_text(encoding="utf-8") == lic.render(python, [], policy)
    assert lic.check(python, [], policy, listing)[0] == 0, "once rewritten it is current"


def test_the_listing_names_the_package_version_licence_and_part(policy):
    text = lic.render([package("certifi", ["MPL-2.0"], policy)], [], policy)
    assert "| certifi | 1.0 | MPL-2.0 | service | accepted by Sean Creighton on 2026-10-14 |" in text
    assert "| certifi | MPL-2.0 | Sean Creighton | 2026-10-14 | a certificate bundle, used unmodified |" in text


# ── what the review of Phase 1 found (OF-BLD-014 §1.R) ──────────────────


def _metadata(**fields):
    from email.message import Message

    m = Message()
    for key, value in fields.items():
        for v in value if isinstance(value, list) else [value]:
            m[key.replace("_", "-")] = v
    return m


def test_a_licence_expression_decides_alone_when_a_package_states_one(policy):
    # PEP 639: the expression is the licence; a stale License field or
    # classifier beside it cannot carry a copyleft package past the ledger.
    meta = _metadata(License_Expression="GPL-3.0-only", License="MIT",
                     Classifier=["License :: OSI Approved :: MIT License"])
    assert lic.deciding_strings(meta) == ("GPL-3.0-only",)
    assert not lic.decide("somepkg", lic.deciding_strings(meta), policy).ok
    # With no expression, the License field and the classifiers still decide.
    legacy = _metadata(License="MIT License", Classifier=["License :: OSI Approved :: MIT License"])
    assert lic.deciding_strings(legacy) == ("MIT License", "License :: OSI Approved :: MIT License")


def test_a_package_the_lock_holds_at_two_versions_lists_both():
    # uv.lock picks numpy by Python version, so the listing names both and
    # reads the same on every interpreter the project supports.
    lock = {"package": [
        {"name": "numpy", "version": "2.4.6", "resolution-markers": ["python_full_version < '3.12'"]},
        {"name": "numpy", "version": "2.5.2", "resolution-markers": ["python_full_version >= '3.12'"]},
        {"name": "rank-bm25", "version": "0.2.2"},
    ]}
    assert lic.listed_version("numpy", "2.4.6", lock) == "2.4.6 or 2.5.2, by Python version"
    assert lic.listed_version("numpy", "2.5.2", lock) == "2.4.6 or 2.5.2, by Python version"
    assert lic.listed_version("rank-bm25", "0.2.2", lock) == "0.2.2"


def test_the_listing_shows_the_listed_version(policy):
    p = lic.Package("python", "numpy", "2.5.2", ("MIT",), "service", lic.decide("numpy", ["MIT"], policy),
                    listed="2.4.6 or 2.5.2, by Python version")
    assert "| numpy | 2.4.6 or 2.5.2, by Python version | MIT |" in lic.render([p], [], policy)


def test_the_listing_says_what_it_leaves_out(policy):
    text = lic.render([], [], policy)
    assert "devDependencies" in text and "Every package openFerment installs" not in text


def test_a_package_with_no_licence_metadata_passes_only_on_its_named_acceptance(policy):
    # OF-BLD-014 §4.2: py_rust_stemmers states no licence in its metadata.
    ok = lic.decide("py_rust_stemmers", [], policy)
    assert ok.ok and "Sean Creighton" in ok.how
    assert not lic.decide("other_package", [], policy).ok, "no metadata and no acceptance fails"
    later = lic.decide("py_rust_stemmers", ["GPL-3.0-only"], policy)
    assert not later.ok, "once it states a licence, the acceptance of none no longer covers it"
