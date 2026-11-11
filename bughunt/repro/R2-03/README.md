# R2-03: no test holds the MCP `--service` relay's "no proxy" rule

**Statement.** Flipping the relay's `httpx.Client` to `trust_env=True` (mutation M16) leaves
`core/tests/test_mcp_service.py` green, 51 of 51, because every relay test but one hands the client a stand-in
transport and httpx reads no proxy from the environment once a client is given a transport, and the one served
test runs where no proxy reaches loopback; the same mutant, run where `HTTP_PROXY` names a proxy and `NO_PROXY`
is unset, sends every relayed call, its project header and the client's declared name to that proxy.

Kind: Hollow test. Severity: S4 (the code as it stands keeps its rule, and no test guards it).

## Contract

- Commit 6f85338's message, line 6: "MCP: `--service <origin>` (a loopback address alone, no proxy, no
  redirect) relays each call to the running service's tool door".
- `core/openferment_core/mcp_server.py:232-233` (the `Service` docstring): "Through no proxy: the call is a
  loopback one, and a cloud container's HTTPS_PROXY names a proxy elsewhere."
- `core/openferment_core/mcp_server.py:239`: `httpx.Client(base_url=origin, trust_env=False, follow_redirects=False, transport=transport, ...)`.

The "no redirect" half of the same rule has its test (`test_a_redirect_the_service_answers_is_followed_nowhere`),
and it fails for `follow_redirects=True` (M17, the control). No line of `core/tests/test_mcp_service.py` names a
proxy.

## Command

```
bash bughunt/repro/R2-03/run.sh
```

It makes a worktree of 2047f5a under `$BH_WORK/R2-03/`, runs the main checkout's Python over the worktree's core
(PYTHONPATH, checked by the module's own path), keyless, and moves only the served test's port into 10920 (its
`_free_port`). The suite's own fixture makes a fresh migrated database each pytest session on
`OPENFERMENT_TEST_DATABASE_URL=.../bh_r_r2_03_t` and drops it; every `bh_r_r2_03_*` database left is dropped at
the start and the end. A stand-in proxy on 127.0.0.1:10921 records each request it gets and answers 502. The
worktree is removed at the end. About 50 s.

Steps: (0) the contract's words; (1) the test's stand-in transport (test line 63) and httpx's rule
`allow_env_proxies = trust_env and transport is None` (`httpx/_client.py:685`, httpx 0.28.1); (2) M16 with the
whole test file in this container's environment, then the served test with no proxy variable at all (as CI runs
it); (3) the control M17; (4) the served test with `HTTP_PROXY` and `HTTPS_PROXY` naming the recorder and
`NO_PROXY` unset, the code as it stands and then M16.

## Expected

A test of `test_mcp_service.py` fails when the relay reads the environment's proxy settings, as the redirect test
fails when it follows redirects.

## Observed (run1.log, run2.log: RESULT: DEFECT both)

- M16 applied: `51 passed` for the whole file in this container (`HTTPS_PROXY` set, `NO_PROXY` listing
  127.0.0.1, `HTTP_PROXY` unset); the served test `1 passed` with no proxy variable set.
- M17 applied: `1 failed` (the redirect test), so the suite holds the rule written beside "no proxy".
- Under `HTTP_PROXY=http://127.0.0.1:10921` with `NO_PROXY` unset: the code as it stands passes the served test
  and the recorder receives nothing; M16 fails it with `{'error': 'the service at http://127.0.0.1:10920 answered
  502 Bad Gateway: a proxy stand-in'}`, and the recorder holds both relayed calls, e.g.
  `POST http://127.0.0.1:10920/api/tools/catalogue_write HTTP/1.1`, project `test-project`, assistant
  `example-test/0.1`, the tool's arguments in the body.

So M16 is a real break, and the suite as it runs here and in CI cannot see it.

## Likely cause

`core/tests/test_mcp_service.py:63`: the relay tests build the server with
`mcp_server.build(project, origin, transport=httpx.MockTransport(handle))`, and a client handed a transport reads
no environment proxy whatever `trust_env` says (`httpx/_client.py:685`). The one test whose relay is built with no
transport, `test_the_server_started_with_service_writes_through_it_and_the_audit_names_the_client`
(`core/tests/test_mcp_service.py:448`), passes its own `os.environ` to the server's process, and wherever the
suite runs that environment either sets no `HTTP_PROXY` or lists 127.0.0.1 in `NO_PROXY`. A test that runs the
served path with a proxy named and `NO_PROXY` unset (step 4 here) holds the rule; the fix is small.

## Claims checked

- The candidate's contract quotes hold: the commit message and the docstring say "no proxy". The docstring's words
  stand at lines 232-233 (the candidate's 231-234 names the docstring whole).
- "httpx reads no proxy from the environment once a transport is given" holds for httpx 0.28.1 (line 685).
- Through an `http://` origin, only `HTTP_PROXY` or `ALL_PROXY` with `NO_PROXY` leaving loopback out sends the
  mutant's calls to a proxy; `HTTPS_PROXY` alone reaches an `https://` origin. In this container `HTTP_PROXY` is
  unset and `NO_PROXY` lists 127.0.0.1, so the code's own comment about the cloud container's `HTTPS_PROXY` names
  a case the mutant would also survive here.
