"""Every GET operation in docs/api/openapi.json, sent once in project P with each required parameter
given a plausible value (none of them a real plant, so no BioSTEAM build starts), with ?project= in the
query as a page with no header would send it. Prints each status. Run rowcounts.py before and after to
see whether any read keeps a row. Usage: python get_sweep.py http://127.0.0.1:8900 p1"""
import http.client
import json
import re
import sys
from urllib.parse import urlsplit, quote

origin, project = sys.argv[1], sys.argv[2]
u = urlsplit(origin)
spec = json.load(open("/home/user/openFermentUI/docs/api/openapi.json"))
SKIP = {"/api/events"}  # a stream that stays open
VALUES = {"by": "attacker", "q": "ethanol", "family": "monod", "flowsheet": "x", "thing": "x", "scenarioId": "x",
          "simulation": "x"}
for path, item in spec["paths"].items():
    op = item.get("get")
    if not op or path in SKIP:
        continue
    p = re.sub(r"{([^}:]+)(:[^}]*)?}", "x", path)
    q = [f"project={project}"]
    for prm in op.get("parameters", []):
        if prm["in"] == "query" and prm["name"] != "project" and (prm.get("required") or prm["name"] in VALUES):
            q.append(f"{prm['name']}={quote(VALUES.get(prm['name'], 'x'))}")
    url = p + "?" + "&".join(q)
    c = http.client.HTTPConnection(u.hostname, u.port, timeout=120)
    c.request("GET", url, headers={"Host": f"127.0.0.1:{u.port}"})
    r = c.getresponse()
    body = r.read()[:160].decode("utf-8", "replace").replace("\n", " ")
    print(r.status, url, body)
