# H9-01: the literature answer route spends core/.env's key when the request names its own

**Statement.** `POST /api/literature/answer` with `X-OpenFerment-Key` makes its model call on the key the service's environment holds (core/.env's), while the kit's answer through `/rag/v1/answer` and every other model-calling route uses the key the request named, and the request's audit row still says an override was used.

## Contract

- `CLAUDE.md:90`: "A request may name its own Anthropic key in `X-OpenFerment-Key`: its calls, openFerment's and the kit's, run on it, never stored, logged or echoed, and the audit row says an override was used"
- `CLAUDE.md:116`: "Q10 the per-request key override — authorized: a key sent on a request serves that request's model calls, openFerment's and the kit's"
- `docs/api/postdoc.md:226-228`: "every model call it makes, Postdoc's, extraction's and the kit's, runs on that key, and a request that names none runs on `core/.env`'s"
- `docs/decisions/ADR-008-postdoc-memory-routing.md:174-177`: "`_default_client` builds every client on it in place of core/.env's; the kit's calls reach it through `llm.call` on asyncio's worker thread, and the ask stream's thread through `contextvars.copy_context`, both of which carry the context."
- `core/openferment_core/llm.py:694-698` (`request_key`): "the kit's, which call through `call` here on a thread that copies this context, as the threads a request starts do."

## Command

```
bash bughunt/repro/H9-01/run.sh
```

The script makes the database `bh_r_h9_01_key` fresh and starts a loopback stand-in for the model API on 127.0.0.1:9351 (`standin_model_api.py`: it records each request's headers and answers every one with a 400, so no model runs and nothing is spent). It starts the service on 127.0.0.1:9350 with `ANTHROPIC_BASE_URL` at the stand-in, `ANTHROPIC_API_KEY` set to a fresh sentinel ENVKEY (standing where core/.env's key would), `OPENFERMENT_RAG_KEY` for the control, and every proxy setting pointed at a closed loopback port. It makes a project, pastes one document, then sends two requests that each name a second fresh sentinel SENTINEL in `X-OpenFerment-Key`: the subject `POST /api/literature/answer`, and the control `POST /rag/v1/answer` (the same kit `answer_stream` through its REST door). `drive.py` ties each stand-in request to the route that made it and reads `GET /api/audit?action=key_override`. A short check in the repository's Python shows the mechanism. Everything it made is dropped on exit.

## Expected

Every model request `POST /api/literature/answer` makes carries the request's key (`x-api-key` = SENTINEL), as `/rag/v1/answer`'s do, and the audit row's `{"override": true}` describes what happened.

## Observed

Both runs (`run1.log`, `run2.log`) print the same:

- `/api/literature/answer`: 1 model request, carrying ENVKEY.
- `/rag/v1/answer` (control): 3 model requests, each carrying SENTINEL.
- `GET /api/audit?action=key_override` holds `{"target": "POST /api/literature/answer", "detail": {"override": true}}`.
- Inside `llm.request_key`, `llm.key_named()` reads False in a plain `threading.Thread` and True in `asyncio.to_thread`.
- `RESULT: DEFECT`.

## Likely cause

`core/openferment_core/literature/kit.py:825` starts `threading.Thread(target=lambda: db.run(pump()), name="kit-answer", daemon=True)`. A plain thread begins with an empty context on Python 3.12 and 3.13 (`llm.py:769-771`, the tally's docstring, says so), and `db.run` (`core/openferment_core/db/engine.py:106`, `asyncio.run_coroutine_threadsafe`) hands the database loop that empty context. So `llm._REQUEST_KEY` is None inside `pump`, and `llm._default_client` (`core/openferment_core/llm.py:715-716`) falls back to `os.environ["ANTHROPIC_API_KEY"]`. `pump` re-enters the project by hand (`projects.using`, `kit.py:817`) and carries no key. The ask stream's thread at `core/openferment_core/api.py:614` copies the context (`contextvars.copy_context().run`); the kit-answer thread does not. `core/tests/test_key_override.py` covers `/api/ask` and a thread that copies the context, and no route that runs `kit.answer`.

A small fix: start the kit-answer thread on `contextvars.copy_context().run`, as `api.py:614` does, with a test that sends `X-OpenFerment-Key` to `/api/literature/answer` and checks the key the client was built on.
