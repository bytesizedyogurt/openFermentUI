# P-01: a route that names a local model alone fails with no Anthropic key

**Statement.** `llm._call` builds the Anthropic client through `_default_client` before it reads the route's
provider, so with `ANTHROPIC_API_KEY` empty a route naming only `openai-compatible:<model>` raises
`ModelUnavailable: ANTHROPIC_API_KEY is not set` and the local endpoint is never asked.

## The contract it breaks

- `CLAUDE.md:104`: "Anthropic is the served provider, beside a local model behind an OpenAI-compatible endpoint
  `core/.env` names (`OPENFERMENT_LOCAL_BASE_URL`), which answers single calls through the kit's adapter".
- `core/openferment_core/llm.py:160-165`: "a route's `openai-compatible:<model>` is called through Sci RAG Kit's
  adapter, its key read from core/.env too, at no charge on the day's cap. It answers a single call (`call`)".
- `docs/decisions/ADR-008-postdoc-memory-routing.md:186-191` (Implementation 11): "`OPENFERMENT_LOCAL_BASE_URL`
  names the endpoint and `OPENFERMENT_LOCAL_API_KEY` its key (many local servers take any); a route's
  `openai-compatible:<model>` is then served (`llm.served_providers`). `llm.call` asks it through Sci RAG Kit's
  `OpenAICompatLLM`".

The local path names its own key (`OPENFERMENT_LOCAL_API_KEY`) and never uses the Anthropic client, so a route of
local models alone has no use for an Anthropic key.

## Command

From the repository root: `bash bughunt/repro/P-01/run.sh`

It makes a fresh database `bh_r_p_01_<pid>`, starts `stub_models.py` (a copy of the hunt's stub) on
127.0.0.1:9160 as the local OpenAI-compatible endpoint, and runs `local_call.py` twice through the repository's
Python, keyless: once with `ANTHROPIC_API_KEY` empty, once with a placeholder value as the control.
`ANTHROPIC_BASE_URL` points at the stub too and every proxy at the dead port 9161, so no request can leave the
machine; the stub logs every path it is asked. The stub, the database and the scratch directory go at the end.

## Expected

With `OPENFERMENT_LOCAL_BASE_URL` naming the stub and `OPENFERMENT_ROUTES` giving `explain` the one model
`openai-compatible:local-stub`, `llm.call(family="explain")` is answered by the stub at no charge whatever
`ANTHROPIC_API_KEY` holds: one `POST /v1/chat/completions` at the stub in each arm.

## Observed (run1.log, run2.log)

- Keyless arm: `RAISED ModelUnavailable: ANTHROPIC_API_KEY is not set. Put it in core/.env (gitignored) and
  restart the service.`; the stub saw 0 requests.
- Placeholder arm: `ANSWERED openai-compatible:local-stub cost=0.0`; the stub saw one `POST /v1/chat/completions`
  and no `POST /v1/messages`, so the placeholder key is built into a client and never sent.

Both runs print `RESULT: DEFECT`. The workaround is any value in `ANTHROPIC_API_KEY`.

## Likely cause

- `core/openferment_core/llm.py:844`: `client = (client_factory or _default_client)()` runs before the loop over
  `route.models`; the provider is read at `llm.py:861` and the local branch starts at `llm.py:867`
  (`if provider == LOCAL:`).
- `core/openferment_core/llm.py:714-720`: `_default_client` raises `ModelUnavailable` when neither the request's
  key nor `ANTHROPIC_API_KEY` is set.
- `core/openferment_core/extract.py:328` calls `llm.call` with no `client_factory`, so an `extract` route of local
  models alone meets the same refusal in the service.
- `core/tests/test_llm.py:887-901` passes `client_factory=lambda: unasked` (line 900), so `_default_client` never
  runs in the test that pays the row; its comment at lines 897-898 says the stand-in client is what lets it hold
  "with no key in the environment, as CI runs it".

A fix builds the Anthropic client lazily, on the first Anthropic model the loop reaches.
