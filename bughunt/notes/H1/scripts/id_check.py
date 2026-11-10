"""Recompute a run's id from engines.md's formula (The run's row) with no openFerment code:
sha256 over canonical JSON of {tool, toolVersion, inputs}, keys sorted, separators , and :,
ensure_ascii off; first 16 hex. Reads a RunReport JSON (GET /api/runs/{id}) on stdin."""
import hashlib, json, sys
t = sys.stdin.read().rsplit("\n[", 1)[0]
rep = json.loads(t)
art = rep["artifact"]
payload = {"tool": art["tool"], "toolVersion": art["toolVersion"], "inputs": art["inputs"]}
text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
mine = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
print("run id", rep["run"]["id"], "recomputed", mine, "match" if mine == rep["run"]["id"] else "DIFFER")
