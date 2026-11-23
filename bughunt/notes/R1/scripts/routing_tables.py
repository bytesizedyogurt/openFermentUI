"""R1: docs/reports/model-routing-2026-11.md's alpha 2.2 per-question rows, recomputed into the report's one-row-a-table
figures and its rule table. Usage: python3 -I routing_tables.py <report.md>"""
import re, sys, statistics as st
md = open(sys.argv[1]).read()
part = md[md.index("# Alpha 2.2, stage F"):]
tables = {}
for tag in ("haiku", "sonnet", "opus-high", "opus-max"):
    i = part.index(f"**{tag}**")
    rows = []
    for line in part[i:].splitlines()[4:]:
        if not line.startswith("| "):
            break
        c = [x.strip() for x in line.strip("|").split("|")]
        if not c[1][:1].isdigit():
            continue
        rows.append(c)
    tables[tag] = rows
COLS = ["tools", "citations", "estimates", "bare", "answers", "grounded", "labelled", "coverage"]
means = {}
for tag, rows in tables.items():
    sc = {k: [float(r[1 + j]) for r in rows] for j, k in enumerate(COLS)}
    means[tag] = {k: st.mean(v) for k, v in sc.items()}
    calls = [int(r[9]) for r in rows]
    kept = [int(r[10].split("/")[0]) for r in rows]
    dropped = [int(r[10].split("/")[1].split("(")[0]) for r in rows]
    fornum = [int(r[10].split("(")[1].rstrip(")")) for r in rows]
    secs = [[float(x) for x in r[12].split(",")] for r in rows]
    usd = [float(r[13]) for r in rows]
    judge = [float(r[14].split()[0]) for r in rows if r[14] not in ("none",)]
    print(f"== {tag}: n={len(rows)}")
    print("  code means", [f"{means[tag][k]:.3f}" for k in COLS[:4]], " judge means", [f"{means[tag][k]:.3f}" for k in COLS[4:]])
    print(f"  tool calls mean/median {st.mean(calls):.1f} / {st.median(calls)}; claims kept/dropped {sum(kept)}/{sum(dropped)}; for numbers {sum(fornum)}")
    print(f"  median seconds {st.median(s[0] for s in secs):.2f}, {st.median(s[1] for s in secs):.2f}, {st.median(s[2] for s in secs):.1f}")
    print(f"  USD answer sum {sum(usd):.4f} mean {st.mean(usd):.4f} median {st.median(usd):.4f} min {min(usd)} max {max(usd)}; judge sum {sum(judge):.4f}")
    if tag == "haiku":
        both = [float(r[14].split("(")[1].rstrip(")")) for r in rows]
        print(f"  haiku judge both passes {sum(both):.4f}, first pass {sum(both)-sum(judge):.4f}")
    stops = [r[11].split(";")[0] for r in rows]; print("  stops", {s: stops.count(s) for s in set(stops)})
    bare_dropping = sum(1 for r in rows if float(r[4]) == 0.0)
    print("  questions with bare numbers 0:", bare_dropping)
print("\n== the rule table, recomputed from the per-question rows")
pairs = [("sonnet", "haiku"), ("opus-high", "haiku"), ("opus-high", "sonnet")]
for b, a in pairs:
    for j, k in enumerate(COLS[4:]):
        bv = [float(r[5 + j]) for r in tables[b]]; av = [float(r[5 + j]) for r in tables[a]]
        above = sum(x > y for x, y in zip(bv, av)); below = sum(x < y for x, y in zip(bv, av)); level = sum(x == y for x, y in zip(bv, av))
        print(f"  {b} - {a} {k}: {means[b][k]-means[a][k]:+.3f}  {above} / {below} / {level}")
