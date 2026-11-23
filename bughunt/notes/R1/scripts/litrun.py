"""R1: the kept Ethanol retrieval run (F.5's offline part) against what docs/reports/literature-retrieval.md says of it.
Usage: python3 -I litrun.py <kept run json> <report.md>"""
import json, re, sys
from collections import Counter
run = json.load(open(sys.argv[1])); md = open(sys.argv[2]).read()
truth = {q["id"]: q for q in run["truth"]["questions"]}
print("public.commit", run["public"].get("commit"), "at", run["at"])
for cfg, r in run["retrieval"].items():
    rec = {x["question_id"]: x for x in r["passage"]["records"]}
    kit = {x["question_id"]: x for x in r["kit"]["records"]}
    miss = sorted(q for q, x in rec.items() if not x["hit_at_10"])
    # the report's list
    m = re.search(rf"- `{cfg}` missed at ten under the passage rule: ([^\n]+)\.", md)
    listed = [s.strip() for s in m.group(1).split(",")] if m else None
    counts = Counter(x["retrieved"] for x in rec.values())
    # passage rule recomputed from ranked chunk ids
    hits10 = sum(1 for q, ranked in r["ranked"].items() if truth[q]["chunkId"] in [c["chunkId"] for c in ranked[:10]])
    doc10 = sum(1 for q, ranked in r["ranked"].items() if truth[q]["documentId"] in [c["documentId"] for c in ranked[:10]])
    print(cfg, "seconds", r["seconds"], "retrieved counts", dict(counts),
          "passage hit@10 recorded", sum(x["hit_at_10"] for x in rec.values()), "recomputed by chunk id", hits10,
          "kit hit@10 recorded", sum(x["hit_at_10"] for x in kit.values()), "by document alone", doc10,
          "| missed listed==records:", listed == miss, len(miss), len(listed or []),
          "metrics", {k: round(v["mean"], 2) for k, v in r["passage"]["metrics"].items() if isinstance(v, dict)},
          {k: round(v["mean"], 2) for k, v in r["kit"]["metrics"].items() if isinstance(v, dict)})
t = run["truth"]
print("truth", {k: t[k] for k in ("read", "kept", "groups", "documents", "covered")}, "questions", len(t["questions"]))
fields = Counter(q["field"] for q in t["questions"]); print("fields", dict(sorted(fields.items())))
print("documents with questions", len({q["documentId"] for q in t["questions"]}))
