"""A local stand-in for the Anthropic Messages API and an OpenAI-compatible endpoint, on 127.0.0.1 alone.

It keeps each request's path and the headers that carry a key (x-api-key, authorization) in a JSON-lines file, and
answers every message with an empty plan, streamed or whole, so a service pointed at it (ANTHROPIC_BASE_URL,
OPENFERMENT_LOCAL_BASE_URL) runs its real call path to the wire with no spend. Hunt P, row 2.

usage: python stub_models.py PORT LOGFILE
"""
from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT, LOG = int(sys.argv[1]), sys.argv[2]
PLAN = json.dumps({"claims": [], "gaps": [], "declined": None})


def _sse(model: str) -> bytes:
    events = [
        ("message_start", {"type": "message_start", "message": {
            "id": "msg_stub", "type": "message", "role": "assistant", "model": model, "content": [],
            "stop_reason": None, "stop_sequence": None,
            "usage": {"input_tokens": 10, "output_tokens": 1}}}),
        ("content_block_start", {"type": "content_block_start", "index": 0,
                                 "content_block": {"type": "text", "text": ""}}),
        ("content_block_delta", {"type": "content_block_delta", "index": 0,
                                 "delta": {"type": "text_delta", "text": PLAN}}),
        ("content_block_stop", {"type": "content_block_stop", "index": 0}),
        ("message_delta", {"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                           "usage": {"output_tokens": 5}}),
        ("message_stop", {"type": "message_stop"}),
    ]
    return "".join(f"event: {e}\ndata: {json.dumps(d)}\n\n" for e, d in events).encode()


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):  # quiet
        pass

    def do_POST(self):  # noqa: N802
        n = int(self.headers.get("content-length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}")
        with open(LOG, "a") as f:
            f.write(json.dumps({"path": self.path, "x-api-key": self.headers.get("x-api-key"),
                                "authorization": self.headers.get("authorization"),
                                "model": body.get("model"), "stream": body.get("stream")}) + "\n")
        if self.path.endswith("/messages"):
            model = body.get("model") or "claude-opus-5-5"
            if body.get("stream"):
                out = _sse(model)
                self.send_response(200)
                self.send_header("content-type", "text/event-stream")
                self.send_header("content-length", str(len(out)))
                self.end_headers()
                self.wfile.write(out)
                return
            out = json.dumps({"id": "msg_stub", "type": "message", "role": "assistant", "model": model,
                              "content": [{"type": "text", "text": PLAN}], "stop_reason": "end_turn",
                              "stop_sequence": None, "usage": {"input_tokens": 10, "output_tokens": 5}}).encode()
        elif self.path.endswith("/chat/completions"):
            out = json.dumps({"id": "cmpl_stub", "object": "chat.completion", "model": body.get("model"),
                              "choices": [{"index": 0, "finish_reason": "stop",
                                           "message": {"role": "assistant", "content": PLAN}}],
                              "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}}).encode()
        else:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)


ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
