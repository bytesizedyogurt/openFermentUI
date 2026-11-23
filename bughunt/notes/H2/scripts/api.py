"""H2's small client for a local openFerment service (no proxy, no key).

    python3 api.py ORIGIN PROJECT METHOD PATH [JSON-BODY | @file] [> out.json]

Prints the status line to stderr and the body to stdout. Used by every H2 script.
"""
import json
import sys
import urllib.request


def call(origin: str, project: str, method: str, path: str, body=None, timeout: float = 1800.0):
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(origin + path, data=data, method=method)
    req.add_header("X-OpenFerment-Project", project)
    if data is not None:
        req.add_header("content-type", "application/json")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=timeout) as r:
            raw = r.read()
            status = r.status
            ctype = r.headers.get("content-type", "")
    except urllib.error.HTTPError as e:
        raw = e.read()
        status = e.code
        ctype = e.headers.get("content-type", "")
    if "json" in ctype:
        return status, json.loads(raw or b"null")
    return status, raw


if __name__ == "__main__":
    origin, project, method, path = sys.argv[1:5]
    body = None
    if len(sys.argv) > 5:
        arg = sys.argv[5]
        body = json.load(open(arg[1:])) if arg.startswith("@") else json.loads(arg)
    status, out = call(origin, project, method, path, body)
    print(status, file=sys.stderr)
    if isinstance(out, (bytes, bytearray)):
        sys.stdout.buffer.write(out)
    else:
        print(json.dumps(out, indent=1, ensure_ascii=False))
