"""FastAPI app — openferment-core's first surface (OF-BLD-007 §4).

The seam is Python rather than a Node proxy on purpose. An API key cannot live
in the browser, so a server is required either way; and every tool Postdoc will
eventually orchestrate — COBRApy, BioSTEAM, the sequence stack — is Python.
A throwaway JS proxy would mean building this boundary twice.

Run it from `core/`:

    uv run uvicorn openferment_core.api:app --reload
"""
from fastapi import FastAPI

app = FastAPI(title="openferment-core", version="0.1.0")


@app.get("/api/health")
def health() -> dict:
    """Liveness. The UI uses this to tell "service down" from "request failed"."""
    return {"ok": True, "service": "openferment-core"}
