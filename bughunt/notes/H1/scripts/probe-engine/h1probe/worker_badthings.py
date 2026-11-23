"""A worker whose things op answers another op's result."""
import json, os, sys
from openferment_core import workers
OUT = os.fdopen(workers.RESPONSES_FD if workers.RESPONSES_FD is not None else os.dup(1), "w", buffering=1)
for line in sys.stdin:
    req = json.loads(line)
    OUT.write(json.dumps({"id": req["id"], "ok": True, "result": {"parameters": []}}) + "\n"); OUT.flush()
