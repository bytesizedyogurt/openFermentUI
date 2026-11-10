"""Probe for M30: a rebinding page behind a proxy that rewrites Host. The browser names the hostile site in
Origin; the proxy (tailscale serve, Vite) puts the name the browser used in X-Forwarded-Host and its own loopback
address in Host. guard.refusal must refuse it (the forwarded name is not one this service answers to).
Run from a tree's core/ with that tree's Python: prints the refusal or None."""
from openferment_core import guard

headers = {"host": "127.0.0.1:8000", "origin": "http://rebind.evil.example.com",
           "x-forwarded-host": "rebind.evil.example.com"}
print("refusal:", guard.refusal("POST", headers))
