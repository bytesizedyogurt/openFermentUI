"""H9: claims whose words state a quantity, held to Postdoc's validator
(validate.validate_plan), each citing a sentence a tool returned. The plan prompt
(postdoc/plan.py SYSTEM) lists "Ethanol titre roughly doubled under anaerobic
conditions" as a bad claim that is discarded whole; rule 9 of the loop's prompt says a
table or figure number in claim text discards it. No database, no model.

    bh_py ../bughunt/notes/H9/scripts/numbers_in_claims.py
"""
from __future__ import annotations

import json

from openferment_core.models import Passage
from openferment_core.postdoc.plan import SYSTEM
from openferment_core.validate import SeenSet, validate_plan

SENTENCE = "Saccharomyces cerevisiae ferments glucose to ethanol under anaerobic conditions."
seen = SeenSet()
seen.passages["doc1:s0:0"] = Passage(id="doc1:s0:0", paperId="doc1", sectionId="s0", heading="Notes", kind="prose",
                                     text=SENTENCE, start=0, end=len(SENTENCE))
TEXTS = [
    "Ethanol titre roughly doubled under anaerobic conditions",
    "The ethanol titre tripled once xylose was added",
    "The yield halved on xylose",
    "The titre quadrupled in the evolved strain",
    "Hundreds of strains were screened before this one",
    "Table IV lists the yields of the strains",
    "The phase III fermentation reached its titre",
    "A x10 rise in productivity followed the change",
    "The strain grew best at pH7 in the cited batch",
    "The titre fell at pH-4 in the cited batch",
]
print(json.dumps({"promptListsAsBad": "Ethanol titre roughly doubled under anaerobic conditions" in SYSTEM}))
for text in TEXTS:
    claim = {"id": "c1", "text": text, "recordIds": [], "support": "direct", "paperIds": [],
             "passages": [{"passageId": "doc1:s0:0", "quote": SENTENCE}], "evidenceIds": [], "moduleRefs": [],
             "values": []}
    result = validate_plan([claim], seen, pool=None, model="claude-opus-5-5")
    print(json.dumps({"claim": text, "kept": len(result.claims), "dropped": result.rejected,
                      "reasons": result.reasons}))
