"""H8-06's in-process probe: the kit's own stage traces for one deep search over a project's documents.

Usage: python -I traces.py PROJECT QUERY   (run.sh calls it keyless, over the service's own database)
Installs the model client the service installs (api.py: kit.install_model(llm.kit_client)), calls openFerment's
kit.search exactly as GET /api/literature/search does, with profile 'deep', and prints one TRACES line (a JSON
object: each stage's status, and the result's degraded_stages). The kit's structlog warnings
(query_entity_extraction_failed, hyde_generation_failed) go to stdout as the kit prints them.
"""
from __future__ import annotations

import json
import sys

from openferment_core import llm
from openferment_core.literature import kit

kit.install_model(llm.kit_client)

project, query = sys.argv[1], sys.argv[2]
hits, result = kit.search(query, project_id=project, top_k=10, profile="deep")
print("TRACES " + json.dumps({
    "profile": result.profile,
    "stages": {t.stage: t.status for t in result.traces},
    "degraded_stages": result.degraded_stages,
    "hits": len(hits),
}))
