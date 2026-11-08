"""Validator tests (OF-BLD-007 §5, §10.5).

Written and passing BEFORE the first API call. The validator is the Rule 1
safety rail, and a safety rail you have not tested is a safety rail you are
hoping about. Every case here is a hand-written plan — good ones that must
survive intact, bad ones that must be dropped and counted — so the behaviour is
pinned against claims a human wrote rather than against whatever the model
happened to emit on the day.

Offline and free. No key, no network.
"""
from __future__ import annotations

import pytest

from openferment_core.models import weakest_provenance
from openferment_core.validate import decline_reason, find_number

# ── the number detector ────────────────────────────────────────────────


@pytest.mark.parametrize(
    "text",
    [
        "Titre reached 4.2 g/L",
        "about 4200 units",
        "roughly 1e6 cells",
        "a 12-fold improvement",
        "four point two grams per litre",
        "expression was twofold higher",
        "half of the total soluble protein",
        "an order of magnitude higher than the control",
        "the first of three runs",
        "yields around ½ the control",
        "reached 10% TSP",
    ],
)
def test_numbers_are_found_in_every_disguise(text):
    assert find_number(text) is not None, f"missed a number in {text!r}"


@pytest.mark.parametrize(
    "text",
    [
        "Titre in cw15 under mixotrophic conditions",
        "Secreted fraction for the strain in question",
        "Nobody has measured this in this host",
        "Often the tension between yield and purity decides the train",
        "Someone should reconsider this alone",
        "Phosphorylation state of a placeholder protein as expressed in a placeholder host",
        "The wavelength used for the absorbance reading",
        # Identifiers carry digits without being quantities. A claim that cannot
        # name its strain is useless, and the first of these is the
        # specification's own worked example of a GOOD claim.
        "Titre in cw15 under mixotrophic conditions",
        "Expression in UVM4 relative to the parental line",
        "Optical density measured as OD600 at harvest",
        "Phosphorylation by CK2 in the E. coli system",
        "The CC-4350 background used throughout",
        "Elow47 before the UV mutagenesis step",
        # OF-BLD-016 §3.2 — the yeast program's strains are identifiers the same way.
        "Ethanol yield on glucose in cenpk113-7d under anaerobic batch conditions",
        "Ethanol yield on glucose in CEN.PK113-7D under anaerobic batch conditions",
        "Glucose uptake in S288C as modelled by iMM904 and Yeast9",
    ],
)
def test_ordinary_prose_is_not_flagged(text):
    """False positives are the failure mode that gets a validator switched off.

    'oneself', 'tension', 'often', 'alone' and 'wavelength' all contain a
    written numeral as a substring. A word-boundary rule that catches them
    would reject correct claims, and a rail that rejects correct output is a
    rail somebody disables.
    """
    assert find_number(text) is None, f"false positive on {text!r}"


# ── provenance is computed, never model-chosen ─────────────────────────


def test_weakest_provenance_ranks_measured_above_gold():
    assert weakest_provenance(["measured", "gold"]) == "gold"
    assert weakest_provenance(["measured"]) == "measured"
    assert weakest_provenance([]) == "unverified"


def test_an_unknown_provenance_class_is_treated_as_the_weakest():
    # An unrecognised provenance is not a reason for confidence.
    assert weakest_provenance(["gold", "something-new"]) == "assumed"


# ── the paper's wording, resolved (OF-BLD-014 §2.1) ────────────────────
#
# `core/tests/fixtures/resolvers.json` is not written by hand: `scripts/
# export-unit-fixtures.ts` records what `normalizeStrain` and `carbonSourceId`
# answer for a fixed set of wordings, and `pnpm test:core` regenerates it
# before pytest runs. The mirror here must answer the same, case by case;
# when it does not, the TypeScript side is right.

import json  # noqa: E402
from pathlib import Path  # noqa: E402

from openferment_core.validate import (  # noqa: E402
    anchor_all,
    anchor_candidate,
    carbon_source_id,
    match_whole_word,
)

RESOLVERS = Path(__file__).parent / "fixtures" / "resolvers.json"


def _resolvers() -> dict:
    if not RESOLVERS.exists():
        raise FileNotFoundError(
            f"{RESOLVERS} not found. It is generated from the TypeScript resolvers — run "
            "`pnpm export:unit-fixtures` from the repository root, or `pnpm test:core`, which does."
        )
    return json.loads(RESOLVERS.read_text())


RX = _resolvers()


@pytest.mark.parametrize("case", RX["strains"], ids=lambda c: repr(c["text"]))
def test_the_strain_resolver_answers_as_the_browser_does(case):
    assert match_whole_word(case["text"], RX["strainAliases"]) == case["id"]


@pytest.mark.parametrize("case", RX["carbon"], ids=lambda c: repr(c["text"]))
def test_the_carbon_source_resolver_answers_as_the_browser_does(case):
    assert carbon_source_id(case["text"]) == case["id"]


def test_the_resolver_fixture_covers_both_rules_and_their_refusals():
    # The cases that make the rule a rule: an exact alias, one found as a
    # whole word, one glued to other letters, and two ids in one wording.
    strains = {c["text"]: c["id"] for c in RX["strains"]}
    assert strains["ab12"] == "strain-ab12"
    assert strains["Genus species CD34"] == "strain-cd34"
    assert strains["cd340"] is None and strains["xcd34"] is None
    assert strains["ab12 and cd34 crossed"] is None
    assert strains["Genus  species   ab12-3"] == "strain-ab12"
    assert strains["X. testus"] is None and strains["constructor"] is None
    carbon = {c["text"]: c["id"] for c in RX["carbon"]}
    assert carbon["crude glycerol"] == "glycerol"
    assert carbon["glucosamine"] is None and carbon["glucose and xylose"] is None


# One fetched section about an imaginary run, and a candidate on it whose
# organism is the only thing each test changes. Test values, stated as such.
WORDING_SECTION = [
    {
        "id": "s1",
        "text": "In the imaginary run, Testus organismus AB12 secreted the reporter to 15 mg L-1.",
    }
]


@pytest.fixture(autouse=True)
def _test_strains(monkeypatch):
    """A strain alias table of fictional strains: the service ships none, since
    strains arrive with a project's records (alpha 2.0, ADR-010)."""
    import openferment_core.validate as module

    real = module.vocabulary()
    monkeypatch.setattr(module, "vocabulary", lambda path=None: {
        **real, "strains": {"ab12": "strain-ab12", "ab12-3": "strain-ab12", "cd34": "strain-cd34"},
    })


def _anchored(organism: str):
    raw = {
        "sectionId": "s1", "field": "titer_secreted", "value": 15, "unit": "mg L-1",
        "quote": "secreted the reporter to 15 mg L-1", "organism": organism,
        "isPrimary": True, "confidence": 0.9,
    }
    candidate, rule, detail = anchor_candidate(raw, WORDING_SECTION, paper_id="W1")
    assert candidate is not None, f"{rule}: {detail}"
    return candidate


def test_wording_that_contains_a_known_designation_resolves_to_its_strain_id():
    c = _anchored("Testus organismus AB12")
    assert c.organism == "strain-ab12", "the strain id, which every screen matches on"
    assert c.organismText == "Testus organismus AB12", "the paper's wording, kept beside it"


def test_an_exact_alias_resolves_too():
    c = _anchored("AB12-3")
    assert c.organism == "strain-ab12" and c.organismText == "AB12-3"


def test_wording_that_names_the_species_alone_stays_as_written():
    c = _anchored("Testus organismus")
    assert c.organism == "Testus organismus"
    assert c.organismText is None, "nothing was resolved, so organism already holds the wording"


def test_wording_that_names_two_strains_is_not_resolved_to_either():
    c = _anchored("AB12 crossed with CD34")
    assert c.organism == "AB12 crossed with CD34" and c.organismText is None


def test_resolving_the_organism_does_not_move_the_content_id():
    # A decision keyed by content stays on its candidate when anchoring
    # learns to resolve the wording it was made about.
    assert _anchored("Testus organismus AB12").id == _anchored("Testus organismus").id


# ── the carbon source at anchoring ─────────────────────────────────────

CARBON_SECTION = [
    {
        "id": "s1",
        "text": "On crude glycerol the imaginary strain secreted the reporter to 15 mg L-1.",
    }
]


def _with_carbon(carbon):
    raw = {
        "sectionId": "s1", "field": "titer_secreted", "value": 15, "unit": "mg L-1",
        "quote": "secreted the reporter to 15 mg L-1", "carbonSource": carbon,
        "isPrimary": True, "confidence": 0.9,
    }
    return anchor_all([raw], CARBON_SECTION, paper_id="W2")


def test_a_carbon_source_in_the_section_is_kept_in_the_papers_words():
    out = _with_carbon("Crude glycerol")
    [c] = out.accepted
    assert c.carbonSource == "Crude glycerol", "kept as written; case aside, it is in the section"
    assert carbon_source_id(c.carbonSource) == "glycerol"
    assert out.field_drops == {"carbonSource": 0} and out.rejected == 0


@pytest.mark.parametrize(
    "carbon, why",
    [
        ("glucose", "is not in section"),
        ("two percent glycerol", "contains a number"),
        ("glycerol 20", "contains a number"),
        (5, "is not text"),
    ],
)
def test_a_carbon_source_that_fails_is_dropped_and_its_candidate_kept(carbon, why):
    out = _with_carbon(carbon)
    [c] = out.accepted
    assert c.carbonSource is None
    assert out.rejected == 0 and out.reasons == {r: 0 for r in out.reasons}, "not a rejection"
    assert out.field_drops == {"carbonSource": 1}
    assert len(out.field_drop_details) == 1 and why in out.field_drop_details[0]


def test_no_carbon_source_is_no_drop():
    for carbon in (None, "", "   "):
        out = _with_carbon(carbon)
        assert out.accepted[0].carbonSource is None and out.field_drops == {"carbonSource": 0}


# OF-BLD-014 §2.R: a drop counts once per candidate KEPT. An emission that
# collapses into a duplicate, or is rejected, leaves no kept candidate to
# have lost a field.


def _emission(carbon, confidence, value=15):
    return {
        "sectionId": "s1", "field": "titer_secreted", "value": value, "unit": "mg L-1",
        "quote": "secreted the reporter to 15 mg L-1", "carbonSource": carbon,
        "isPrimary": True, "confidence": confidence,
    }


def test_a_duplicate_emission_does_not_count_its_drop_twice():
    out = anchor_all([_emission("glucose", 0.9), _emission("glucose", 0.8)], CARBON_SECTION, paper_id="W2")
    assert len(out.accepted) == 1 and out.duplicates == 1
    assert out.field_drops == {"carbonSource": 1} and len(out.field_drop_details) == 1


def test_the_count_follows_the_emission_that_is_kept():
    out = anchor_all([_emission("glucose", 0.5), _emission("crude glycerol", 0.9)], CARBON_SECTION, paper_id="W2")
    assert out.accepted[0].carbonSource == "crude glycerol"
    assert out.field_drops == {"carbonSource": 0} and out.field_drop_details == []


def test_a_rejected_emission_counts_no_field_drop():
    out = anchor_all([_emission("glucose", 0.9, value=99)], CARBON_SECTION, paper_id="W2")
    assert out.rejected == 1 and out.accepted == []
    assert out.field_drops == {"carbonSource": 0}


# ── the agent's plan (OF-BLD-014 §5.1) ─────────────────────────────────
# A stand-in pool and run: records, passages and evidence invented here.

from openferment_core.models import BasisInput, BasisSource, ComputedBasis, Evidence, Passage
from openferment_core.validate import MAX_QUOTE_CHARS, SeenSet, validate_plan


class _Pool:
    RECORDS = {
        "r-X1-1": {"id": "r-X1-1", "paperId": "X1", "provenance": "verified"},
        "r-X2-1": {"id": "r-X2-1", "paperId": "X2", "provenance": "curated"},
        "cl1-X3-aaaaaaaa": {"id": "cl1-X3-aaaaaaaa", "paperId": "X3", "provenance": "unverified"},
    }

    def record(self, rid):
        return self.RECORDS.get(rid)


PASSAGE = Passage(id="X4:s1:0", paperId="X4", sectionId="s1", heading="Results", kind="prose",
                  text="Cells fed the placeholder sugar accumulated the product.  The content rose over four days.", start=0, end=90)


def _evidence(prov="computed"):
    basis = ComputedBasis(tool="convert_units", toolVersion="v", artifactId="a" * 16, at="t",
                          inputs=[BasisInput(name="record value", value=1.0, unit="d", source=BasisSource(kind="record", id="r-X1-1"))])
    return Evidence(id="ev-1", label="r-X1-1 in h", value=24.0, unit="h", provenance=prov, basis=basis)


def _seen(**kw):
    s = SeenSet()
    s.records = set(kw.get("records", ["r-X1-1", "r-X2-1", "cl1-X3-aaaaaaaa"]))
    s.passages = {PASSAGE.id: PASSAGE}
    s.evidence = {"ev-1": kw.get("evidence", _evidence())}
    return s


def _one(claim, seen=None):
    return validate_plan([claim], seen or _seen(), _Pool())


def test_plan_happy_path_keeps_every_kind_of_citation():
    r = _one({
        "id": "c1", "text": "Cells on the placeholder sugar accumulated the product.", "support": "direct",
        "recordIds": ["r-X1-1"], "evidenceIds": ["ev-1"],
        "passages": [{"passageId": PASSAGE.id, "quote": "Cells fed the placeholder sugar accumulated the product."}],
        "paperIds": ["Z9"],
    })
    assert r.rejected == 0
    c = r.claims[0]
    assert c.paperIds == ["X1", "X4"], "papers come from records and passages, never the model"
    assert c.evidenceIds == ["ev-1"] and c.passages[0].passageId == PASSAGE.id
    assert c.provenance == "computed", "weakest of verified and computed"


def test_plan_rule_1_a_number_drops_the_claim():
    r = _one({"text": "The content reached 40 percent.", "recordIds": ["r-X1-1"]})
    assert r.rejected == 1 and "number" in r.reasons[0]


def test_plan_rule_2_a_record_that_does_not_resolve():
    r = _one({"text": "A claim.", "recordIds": ["r-nowhere"]}, _seen(records=["r-nowhere"]))
    assert r.rejected == 1 and "do not exist" in r.reasons[0]


def test_plan_rule_3_a_citation_no_tool_returned():
    for claim in (
        {"text": "A claim.", "recordIds": ["r-X2-1"]},
        {"text": "A claim.", "evidenceIds": ["ev-9"]},
        {"text": "A claim.", "passages": [{"passageId": "X9:s1:0", "quote": "anything"}]},
    ):
        r = _one(claim, _seen(records=["r-X1-1"]))
        assert r.rejected == 1 and "no tool returned" in r.reasons[0], claim


def test_plan_rule_4_a_long_or_made_up_quote():
    made_up = _one({"text": "A claim.", "passages": [{"passageId": PASSAGE.id, "quote": "Cells fed glucose did better."}]})
    assert made_up.rejected == 1 and "not a whole sentence" in made_up.reasons[0]
    long_p = PASSAGE.model_copy(update={"text": "word " * 200})
    seen = _seen()
    seen.passages = {PASSAGE.id: long_p}
    too_long = _one({"text": "A claim.", "passages": [{"passageId": PASSAGE.id, "quote": "word " * (MAX_QUOTE_CHARS // 5 + 2)}]}, seen)
    assert too_long.rejected == 1 and "longer than" in too_long.reasons[0]
    spaced = _one({"text": "A claim.", "passages": [{"passageId": PASSAGE.id, "quote": "The   content rose over four days."}]})
    assert spaced.rejected == 0, "whitespace is normalised; the words are not"


def test_plan_rule_5_citing_nothing_needs_unsupported():
    r = _one({"text": "Nobody has measured it in this host.", "support": "direct"})
    assert r.rejected == 1 and "cites nothing" in r.reasons[0]
    ok = _one({"text": "Nobody has measured it in this host.", "support": "unsupported"})
    assert ok.rejected == 0 and ok.claims[0].provenance == "unverified"


def test_plan_provenance_across_mixed_citations():
    passages_only = _one({"text": "A claim.", "passages": [{"passageId": PASSAGE.id, "quote": "The content rose over four days."}]})
    assert passages_only.claims[0].provenance == "unverified"
    candidate = _one({"text": "A claim.", "recordIds": ["r-X1-1", "cl1-X3-aaaaaaaa"]})
    assert candidate.claims[0].provenance == "unverified"
    modeled = _one({"text": "A claim.", "recordIds": ["r-X1-1"], "evidenceIds": ["ev-1"]}, _seen(evidence=_evidence("assumed")))
    assert modeled.claims[0].provenance == "assumed"
    curated = _one({"text": "A claim.", "recordIds": ["r-X1-1", "r-X2-1"]})
    assert curated.claims[0].provenance == "curated"


# The rules alpha 1.0's one-call path held, held here on the loop's plan.


def test_plan_a_rejected_claim_is_never_repaired():
    """A validator that strips the number and keeps the sentence produces prose
    the model never wrote, attached to citations chosen for the prose it did
    write. Nothing that failed comes back in any form."""
    r = _one({"id": "c1", "text": "The content reached 40 percent.", "recordIds": ["r-X1-1"]})
    assert r.claims == [], "a rejected claim must not reappear repaired"


def test_plan_one_real_record_rescues_no_ghost_beside_it():
    # A partly real citation list is how a fabricated corroboration gets through.
    r = _one({"text": "A claim.", "recordIds": ["r-X1-1", "r-nowhere"]}, _seen(records=["r-X1-1", "r-nowhere"]))
    assert r.claims == [] and r.rejected == 1 and "do not exist" in r.reasons[0]


def test_plan_empty_text_is_dropped():
    r = _one({"id": "c1", "text": "   ", "recordIds": ["r-X1-1"]})
    assert r.claims == [] and r.rejected == 1 and "empty claim text" in r.reasons[0]


def test_plan_the_models_provenance_field_is_discarded():
    r = _one({"text": "A claim.", "recordIds": ["r-X2-1"], "support": "direct", "provenance": "measured"})
    assert r.claims[0].provenance == "curated", "a promotion the model is not allowed"


def test_plan_rejections_are_counted_and_reasoned_by_claim():
    r = validate_plan([
        {"id": "c1", "text": "The content reached 40 percent.", "recordIds": ["r-X1-1"]},
        {"id": "c2", "text": "A claim.", "recordIds": ["r-nowhere"]},
        {"id": "c3", "text": "A claim.", "recordIds": ["r-X1-1"]},
    ], _seen(), _Pool())
    assert len(r.claims) == 1 and r.rejected == 2 and len(r.reasons) == 2
    assert r.reasons[0].startswith("c1:") and r.reasons[1].startswith("c2:")


def test_plan_malformed_claims_are_counted_and_never_raised():
    r = validate_plan([{}, {"text": "A claim."}, {"recordIds": ["r-X1-1"]}, "not a claim"], _seen(), _Pool())
    assert r.rejected == 4 and r.claims == []


def test_plan_a_claim_with_no_id_gets_a_positional_one_and_a_bad_support_falls_back():
    r = _one({"text": "A claim.", "recordIds": ["r-X1-1"], "support": "vibes"})
    assert r.claims[0].id == "c1" and r.claims[0].support == "direct"


# ── what the answer says when nothing stands ───────────────────────────


def test_when_every_claim_is_rejected_the_plan_declines():
    reason = decline_reason(_one({"text": "The content reached 40 percent.", "recordIds": ["r-X1-1"]}), None)
    assert reason is not None
    assert "validation" in reason
    assert "fault in the answer, not in the corpus" in reason


def test_the_models_own_decline_wins():
    # It knows what it was missing and can say so specifically.
    empty = validate_plan([], _seen(), _Pool())
    assert decline_reason(empty, "No study measures this in a microalga.") == "No study measures this in a microalga."


def test_no_claims_and_no_rejections_declines_on_the_corpus():
    assert "corpus does not contain evidence" in decline_reason(validate_plan([], _seen(), _Pool()), None)


def test_a_valid_plan_does_not_decline():
    assert decline_reason(_one({"text": "A claim.", "recordIds": ["r-X1-1"]}), None) is None
