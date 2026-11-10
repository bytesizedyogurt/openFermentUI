"""H5-07 probe: the words Guild and Practice give for a skill the project's skill catalogue lacks.

Against a keyless service over a fresh test database: project bh-a keeps one skill, SK-A, in its skill
catalogue (POST /api/catalogues/skill, what the /catalogues screen sends). Then:
  control   POST /api/guild/check naming SK-A passes the skill rule, so Guild's skills are the catalogue's;
  sibling   POST /api/protocols with a step naming SK-NONE is refused in words naming the project's skill
            catalogue and /catalogues (protocols.py), the alpha 2.2 words for the same fact;
  probes    POST /api/guild/evidence, POST /api/guild/check and POST /api/practice/draft naming SK-NONE.
Every probe is refused before any model call (practice._skill runs first in practice.draft), and the
service is keyless. Prints EXPECTED, OBSERVED and RESULT lines."""
import json
import os
import sys

import httpx

O = os.environ["ORIGIN"]
A = {"X-OpenFerment-Project": "bh-a"}
c = httpx.Client(base_url=O, trust_env=False, timeout=60)


def call(method, path, **kw):
    r = c.request(method, path, headers=A if kw.pop("scoped", True) else {}, **kw)
    try:
        body = r.json()
    except ValueError:
        body = r.text
    return r.status_code, body


def words(body):
    if isinstance(body, dict):
        for k in ("detail", "why", "error"):
            if body.get(k):
                return str(body[k])
    return json.dumps(body, ensure_ascii=False)


s, b = call("POST", "/api/projects", scoped=False, json={"id": "bh-a", "name": "bh-a", "by": "alice"})
print(f"setup: project bh-a: {s}")
s, b = call("POST", "/api/catalogues/skill", json={"by": "alice", "entry": {
    "kind": "skill", "id": "SK-A", "name": "Skill A", "family": "placeholder", "mastery": ["criterion"],
    "criticality": "routine", "recencyDays": 30, "supervisedRuns": 1}})
print(f"setup: skill SK-A kept in bh-a's skill catalogue: {s}")
if s != 200:
    print(f"  {words(b)[:300]}")
    print("EXPECTED: a project with a skill in its catalogue\nOBSERVED: the keep was refused\nRESULT: NO-DEFECT")
    sys.exit(0)
s, b = call("GET", "/api/catalogues/skill")
print(f"setup: GET /api/catalogues/skill in bh-a: {s} {[e.get('id') for e in b] if isinstance(b, list) else b}")


def evidence(skill_id):
    return {"id": "e-aaaa1", "personId": "p-a", "skillId": skill_id, "kind": "knowledge",
            "at": "2026-11-10T07:00:00Z", "source": {"kind": "lesson", "ref": "lesson-a"}, "raw": "x",
            "outcome": "pass"}


print()
s, b = call("POST", "/api/guild/check", json=evidence("SK-A"))
control_ok = s == 200 and isinstance(b, dict) and b.get("rule") != "skill"
print(f"control: POST /api/guild/check naming SK-A (kept): {s} {json.dumps(b)[:260]}")
print(f"  the skill rule passes for a skill the catalogue holds: {'yes' if control_ok else 'no'}")

protocol = {"id": "PR-A", "title": "A placeholder protocol", "category": "sop", "bsl": 1, "currentVersion": "1.0",
            "versions": [{"version": "1.0", "baseBatch": {"value": 1, "unit": "placeholder-unit",
                                                          "label": "placeholder batch"},
                          "steps": [{"id": "s1", "text": "A placeholder step.", "skills": ["SK-NONE"]}],
                          "estMinutes": {"active": 1, "total": 2}}]}
s, b = call("POST", "/api/protocols", json={"protocol": protocol, "by": "alice"})
sibling = words(b)
sibling_ok = s == 422 and "skill catalogue" in sibling and "/catalogues" in sibling
print(f"sibling: POST /api/protocols with a step naming SK-NONE: {s} {sibling[:300]}")
print(f"  names the project's skill catalogue and /catalogues: {'yes' if sibling_ok else 'no'}")

print()
PROBES = [
    ("POST /api/guild/evidence", "/api/guild/evidence", evidence("SK-NONE")),
    ("POST /api/guild/check", "/api/guild/check", evidence("SK-NONE")),
    ("POST /api/practice/draft", "/api/practice/draft", {"skillId": "SK-NONE"}),
]
stale = []
for label, path, payload in PROBES:
    s, b = call("POST", path, json=payload)
    w = words(b)
    says_20 = "alpha 2.0" in w
    names_catalogue = "catalogue" in w
    print(f"{label} naming SK-NONE: {s} {json.dumps(b)[:300]}")
    print(f"  names alpha 2.0: {'yes' if says_20 else 'no'}; names the skill catalogue or /catalogues: "
          f"{'yes' if names_catalogue else 'no'}")
    if says_20 and not names_catalogue:
        stale.append(f"{label} {s} {w!r}")

print()
print("EXPECTED: a skill the project's skill catalogue lacks is refused in words naming that catalogue and where a "
      "skill is kept (/catalogues), as the protocol keep's refusal words it (CLAUDE.md:15; protocols.py:97-100)")
print(f"OBSERVED: {len(stale)} of {len(PROBES)} refusals name alpha 2.0 and no catalogue: " + "; ".join(stale)
      + f". Control (SK-A from the catalogue passes the skill rule): {'yes' if control_ok else 'no'}; "
      f"sibling (protocol refusal names the catalogue): {'yes' if sibling_ok else 'no'}")
defect = control_ok and sibling_ok and len(stale) >= 2
print(f"RESULT: {'DEFECT' if defect else 'NO-DEFECT'}")
