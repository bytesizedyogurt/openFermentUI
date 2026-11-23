"""H7: fetch each GET answer the client reads and hold it to the generated schema it is typed by.

For every object in an answer, a field the schema lists as required that the answer leaves out is named, as is a
field the schema types without null that the answer sends as null. These are the places where the generated type
(src/api/types.gen.ts, from docs/api/openapi.json) says a field is there and the service's answer says otherwise.

    python3 answers_vs_types.py <origin> <project> <path> [<path> ...]
"""
import json
import sys
import urllib.request
from collections import Counter

ROOT = "/home/user/openFermentUI"
doc = json.load(open(f"{ROOT}/docs/api/openapi.json"))
S = doc["components"]["schemas"]
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
origin, project, paths = sys.argv[1], sys.argv[2], sys.argv[3:]


def deref(sch):
    while "$ref" in sch:
        name = sch["$ref"].split("/")[-1]
        sch = S[name]
    return sch


def ref_name(sch):
    return sch["$ref"].split("/")[-1] if "$ref" in sch else None


def nullable(sch):
    sch = deref(sch)
    if sch.get("type") == "null":
        return True
    return any(deref(a).get("type") == "null" for a in sch.get("anyOf", []) + sch.get("oneOf", []))


def check(val, sch, name, path, out):
    nm = ref_name(sch) or name
    sch = deref(sch)
    if val is None:
        return
    alts = sch.get("anyOf") or sch.get("oneOf")
    if alts:
        objs = [a for a in alts if "properties" in deref(a)]
        if isinstance(val, dict) and objs:
            disc = sch.get("discriminator", {}).get("propertyName")
            if disc and disc in val:
                mapping = sch["discriminator"].get("mapping", {})
                if val[disc] in mapping:
                    return check(val, {"$ref": mapping[val[disc]]}, nm, path, out)
            # the first object alternative whose required fields are all there, else the first
            best = next((a for a in objs if all(r in val for r in deref(a).get("required", []))), objs[0])
            return check(val, best, nm, path, out)
        arrs = [a for a in alts if deref(a).get("type") == "array"]
        if isinstance(val, list) and arrs:
            return check(val, arrs[0], nm, path, out)
        return
    if isinstance(val, dict) and "properties" in sch:
        for r in sch.get("required", []):
            if r not in val:
                out[(nm, r, "absent")] += 1
        for k, v in val.items():
            p = sch["properties"].get(k)
            if p is None:
                continue
            if v is None and not nullable(p):
                out[(nm, k, "null")] += 1
            check(v, p, k, f"{path}.{k}", out)
    elif isinstance(val, dict) and isinstance(sch.get("additionalProperties"), dict):
        for k, v in val.items():
            check(v, sch["additionalProperties"], nm, f"{path}[{k}]", out)
    elif isinstance(val, list) and "items" in sch:
        for v in val:
            check(v, sch["items"], name, f"{path}[]", out)


def operation(path):
    bare = path.split("?")[0]
    for p, ops in doc["paths"].items():
        parts, have = p.split("/"), bare.split("/")
        if len(parts) == len(have) and all(a == b or a.startswith("{") for a, b in zip(parts, have)) and "get" in ops:
            return p, ops["get"]
    return None, None


for path in paths:
    p, op = operation(path)
    if not op:
        print(f"{path}: no GET in the document")
        continue
    sch = op["responses"].get("200", {}).get("content", {}).get("application/json", {}).get("schema")
    req = urllib.request.Request(origin + path, headers={"X-OpenFerment-Project": project})
    try:
        with opener.open(req, timeout=120) as r:
            body = json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"{path}: {e.code}")
        continue
    out = Counter()
    check(body, sch or {}, p, "", out)
    print(f"{path} ({p}): {'held' if not out else ''}")
    for (n, f, how), c in sorted(out.items()):
        print(f"    {n}.{f} {how} x{c}")
