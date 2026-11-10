"""Small helpers for H5's scripts: a keyless httpx client to a local service, no proxy."""
import json
import os
import sys

import httpx

ORIGIN = os.environ.get("H5_ORIGIN", "http://127.0.0.1:8850")
OUT = os.environ.get("H5_OUT", "/tmp/claude-0/-home-user-openFermentUI/cfbc5c9f-640a-5002-a705-5ceaf850fdc6/scratchpad/bh/work/H5")
C = httpx.Client(base_url=ORIGIN, trust_env=False, timeout=600)


def call(method, path, project=None, headers=None, **kw):
    h = dict(headers or {})
    if project is not None:
        h["X-OpenFerment-Project"] = project
    r = C.request(method, path, headers=h, **kw)
    return r


def j(r):
    try:
        return r.json()
    except Exception:
        return r.text


def show(label, r, n=400):
    body = r.text if len(r.text) < n else r.text[:n] + "..."
    print(f"{label}: {r.status_code} {body}")
    sys.stdout.flush()
