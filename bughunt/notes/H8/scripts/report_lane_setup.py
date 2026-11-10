"""Set up a project whose two documents share a title, with one kept candidate, for the report lane.

Usage: (1) python report_lane_setup.py paste ORIGIN PROJECT   -> pastes two documents titled alike
       (2) from core/: OPENFERMENT_DATABASE_URL=<bh_ db> .venv/bin/python -I report_lane_setup.py candidate PROJECT DOC_A
           -> keeps one candidate on DOC_A's p0, through extract.add_candidate (no model is asked)
Then run literature_live report --project PROJECT --configs interactive,vector_only,keyword_only (no --render).
"""
from __future__ import annotations

import sys

A_TEXT = ("The batch fermentation reached an ethanol titre of 41 g/L after 48 h in the H8 lane probe.\n\n"
          "Agitation was held constant through the run and the vessel was sampled twice a day.")
B_TEXT = ("What ethanol titre is reported? This review lists what ethanol titre is reported across strains and "
          "feeds, and which titre each study reported, as a guide to the reported ethanol titres.")

if sys.argv[1] == "paste":
    import httpx

    origin, project = sys.argv[2], sys.argv[3]
    root = httpx.Client(base_url=origin, trust_env=False, timeout=120)
    root.post("/api/projects", json={"id": project, "name": project, "by": "h8"})
    c = httpx.Client(base_url=origin, trust_env=False, timeout=300, headers={"X-OpenFerment-Project": project})
    for text in (A_TEXT, B_TEXT):
        r = c.post("/api/intake/paste", json={"title": "Strain report", "text": text, "by": "h8"}).json()
        print(r["status"], r["documentId"], r["title"])
else:
    sys.path.insert(0, ".")
    from openferment_core import extract, projects

    project, doc = sys.argv[2], sys.argv[3]
    with projects.using(project):
        made, rule, detail = extract.add_candidate(doc, {
            "sectionId": "p0", "field": "ethanol_titre", "value": 41, "unit": "g/L",
            "quote": "The batch fermentation reached an ethanol titre of 41 g/L after 48 h in the H8 lane probe.",
        }, who="h8")
    print("candidate:", made.id if made else None, rule, detail)
