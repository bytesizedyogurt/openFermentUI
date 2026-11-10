"""H9: a stand-in for the model API on a loopback port. It records every request it
receives (method, path, headers, the body's length and head) as a JSON line and answers
each with an error, so no model ever runs and nothing is spent.

    python3 standin_model_api.py PORT RECORD.jsonl [status]

`status` is the HTTP status it answers with: 400 (invalid_request_error, the default),
401 (authentication_error) or 529 (overloaded_error).
"""
from __future__ import annotations

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT, RECORD = int(sys.argv[1]), sys.argv[2]
STATUS = int(sys.argv[3]) if len(sys.argv) > 3 else 400
KINDS = {400: "invalid_request_error", 401: "authentication_error", 529: "overloaded_error"}
lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def _any(self) -> None:
        n = int(self.headers.get("content-length") or 0)
        body = self.rfile.read(n) if n else b""
        line = {"method": self.command, "path": self.path, "headers": dict(self.headers.items()),
                "bodyLength": len(body), "bodyHead": body[:4000].decode("utf-8", "replace")}
        with lock, open(RECORD, "a", encoding="utf-8") as f:
            f.write(json.dumps(line) + "\n")
        out = json.dumps({"type": "error", "error": {"type": KINDS.get(STATUS, "api_error"),
                                                     "message": "the bughunt stand-in answers no model call"}}).encode()
        self.send_response(STATUS)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(out)))
        self.send_header("request-id", "req_bughunt_standin")
        self.end_headers()
        self.wfile.write(out)

    do_POST = do_GET = do_PUT = _any

    def log_message(self, *a) -> None:  # quiet
        pass


ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
