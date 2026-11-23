"""Row 2's local-model half: a route naming only openai-compatible:<model> answers a single call (llm.call) at the
endpoint OPENFERMENT_LOCAL_BASE_URL names. The stub of stub_models.py (on 8951) stands for the endpoint; every
proxy points at a dead port. Run keyless with the repository's Python; pass `placeholder` to set a placeholder
ANTHROPIC_API_KEY, which the local route never sends anywhere.

usage: bh_py row02_local.py [placeholder]"""
import json, os, sys
os.environ["OPENFERMENT_LOCAL_BASE_URL"] = "http://127.0.0.1:8951/v1"
os.environ["OPENFERMENT_ROUTES"] = json.dumps({"explain": {"models": ["openai-compatible:local-stub"]}})
for k in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
    os.environ[k] = "http://127.0.0.1:9"
os.environ["NO_PROXY"] = os.environ["no_proxy"] = "127.0.0.1,localhost"
os.environ["ANTHROPIC_BASE_URL"] = "http://127.0.0.1:9"  # an Anthropic call, were one made, reaches nothing
if sys.argv[1:] == ["placeholder"]:
    os.environ["ANTHROPIC_API_KEY"] = "placeholder-not-a-key"
from openferment_core import llm
print("route:", llm.routes()["explain"], "| ANTHROPIC_API_KEY set:", bool(os.environ.get("ANTHROPIC_API_KEY")))
try:
    r = llm.call(system="s", user="q", schema=None, max_tokens=50, family="explain")
    print("call answered by", r.model, "text", (r.text or "")[:80], "cost", r.usage.costUsd)
except Exception as e:
    print("call raised", type(e).__name__ + ":", str(e)[:200])
