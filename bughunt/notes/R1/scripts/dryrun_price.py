"""R1: `pnpm lit:graph --project <id> --dry-run` prices the whole build as one prompt.

Drives literature_live.graph_command's own dry-run branch with 92 batch prompts of the size the F.5 run measured
(1,758,899 prompt characters over 92 batches, docs/reports/literature-retrieval.md:114-117 and docs/PROGRESS.md:3371-3373),
the database read stubbed so nothing is touched, then prices the same prompts one call at a time with the cost function
every model response is charged through (llm.usage_of -> llm.cost_usd, one response at a time).
Run: cd core && .venv/bin/python ../bughunt/notes/R1/scripts/dryrun_price.py (keyless; no database, no network)."""
import argparse, contextlib, io, json, sys
from openferment_core import db, llm, literature_live
from openferment_core.literature import graph

TOTAL, BATCHES = 1_758_899, 92
sizes = [TOTAL // BATCHES + (1 if i < TOTAL % BATCHES else 0) for i in range(BATCHES)]
prompts = ["x" * n for n in sizes]
assert sum(map(len, prompts)) == TOTAL
db.run = lambda awaitable: []                    # no database read
graph.pending = lambda *a, **k: None
graph.prompts = lambda rows: prompts
out = io.StringIO()
with contextlib.redirect_stdout(out):
    literature_live.graph_command(argparse.Namespace(project="r1", rebuild=False, limit=None, dry_run=True))
said = json.loads(out.getvalue())
model = said["model"]
answer = max(graph.ANSWER_TOKENS, llm.KIT_ROOM[llm.routes()["index"].effort])
per_call_input = sum(llm.cost_usd(model, round(len(p) / 4), 0) for p in prompts)
per_call_most = sum(llm.cost_usd(model, len(p) // llm.CHARS_PER_TOKEN_ESTIMATE + 1, answer) for p in prompts)
print("dry run says:", {k: said[k] for k in ("batches", "promptCharacters", "kitTokens", "model", "inputUsd", "mostUsd")})
print("largest batch prompt, kit tokens:", max(round(len(p) / 4) for p in prompts), "; the long-prompt tier starts past",
      llm.LONG_PROMPT_PRICES.get(model, (None,))[0])
print(f"priced one call at a time, as each response is charged: input {per_call_input:.4f} USD, most {per_call_most:.4f} USD")
print(f"the dry run's input figure is {said['inputUsd'] / per_call_input:.1f} times the per-call sum, its most {said['mostUsd'] / per_call_most:.1f} times")
