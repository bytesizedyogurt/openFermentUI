# H12-04: the guard's forwarded-host check can go and every test stays green

**Statement.** With `answers_to(hostname(forwarded))` deleted from `guard.refusal`, a POST whose Host is a proxy's loopback address and whose Origin and X-Forwarded-Host name a hostile site gets through to the endpoint and writes, and `test_request_guard`, `test_key_override` and `test_projects` all pass (58 of 58).

**Kind.** Hollow test. **Severity.** S3: the head's behaviour is right, and the one check that stops a rebinding page behind a proxy that rewrites Host has no test that fails when it goes.

## Contract

- `CLAUDE.md:52`: "The service binds `127.0.0.1`; the loopback bind and `core/openferment_core/guard.py` are the access control until accounts exist".
- `core/openferment_core/guard.py:10-12`: "**DNS rebinding.** A hostile name is made to resolve to the Mini, so the page and the service look like one site to the browser. The request then names that hostile domain in `Host`."
- `core/openferment_core/guard.py:14-15`: "a request that changes something (POST, PUT, PATCH, DELETE) must name a host this service answers to".
- `core/openferment_core/guard.py:124-125`: "A proxy in front may present itself as Host and pass the address the browser used in X-Forwarded-Host."
- `core/tests/test_request_guard.py:1`: "Only the owner's own pages may change anything", and `core/tests/test_request_guard.py:99-103` lets through "a proxy that rewrites Host" (Host `127.0.0.1:8000`, X-Forwarded-Host the owner's `.ts.net` name), the same shape the hostile request takes.

## Command

```
bash bughunt/repro/H12-04/run.sh
```

From the repository root. It makes a worktree of 2047f5a of its own, links the repository's venv into it, and runs:

1. at the head: `probe.py` over a fresh database `bh_r_h12_04_db` (a POST `/api/projects` with Host `127.0.0.1:8000`, Origin `http://rebind.evil.example.com`, X-Forwarded-Host `rebind.evil.example.com`, through the app's whole middleware stack in a TestClient, then a plain read of the projects), and the three test files;
2. with the one-line mutation (`forwarded and answers_to(hostname(forwarded)) and same_site(origin, forwarded)` becomes `forwarded and same_site(origin, forwarded)`): the probe over the database made fresh again, and the same three test files.

Test session databases take the prefix `bh_r_h12_04_t`. Every database is dropped and the worktree removed at the end. Keyless, no service, no port, no network, no model call; about 25 s.

## Expected

With the check deleted, the hostile POST is let through, and a test fails: a case with a loopback Host and a hostile Origin and X-Forwarded-Host answered 403.

## Observed (run1.log, run2.log)

- Head: `guard.refusal` says "a page on 'http://rebind.evil.example.com' may not change anything here"; the POST answers 403 and no project is made; the three files: 58 passed.
- Mutation: `guard.refusal` answers None; the POST answers 201 and the project `rebound-write` is made in the database; the three files: 58 passed.

`RESULT: DEFECT` on both runs.

## Likely cause

`core/tests/test_request_guard.py:70-77` (`test_a_forwarded_name_cannot_launder_a_hostile_host`) sends a hostile Host with a loopback X-Forwarded-Host, which the Host check at `core/openferment_core/guard.py:115-120` already refuses. Every other case with X-Forwarded-Host (`test_request_guard.py:87`, `:91`, `:97`, `:102`) is one the guard lets through. So no case sends a loopback Host with a hostile forwarded name, and the check at `core/openferment_core/guard.py:133` (`answers_to(hostname(forwarded))`) stands untested. No other test in `core/tests/` sends X-Forwarded-Host. A fix is one parametrized case in `test_request_guard.py`'s refused section: Host `127.0.0.1:8000`, Origin `http://rebind.evil.example.com`, X-Forwarded-Host `rebind.evil.example.com`, answered 403.

## Note

On the dev path the installed Vite (5.4.21) runs its own `server.allowedHosts` check before proxying, and `tailscale serve` keeps Host, which the Host check holds. The exposure is a later regression in this check reaching a proxy that rewrites Host, the case the guard's own comment and `test_request_guard.py:99-103` name.
