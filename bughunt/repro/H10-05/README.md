# H10-05: guard.py's list of the hosts it answers to leaves out `.localhost`

**Statement.** The docstring of `core/openferment_core/guard.py` lists the hosts a changing request
may come under: an IP address, a dotless name, a `.local` name, a `.ts.net` name and the names
`OPENFERMENT_ALLOWED_HOSTS` lists. `OWN_SUFFIXES` at guard.py:37 also holds `.localhost`. A POST under
`Host: evil.localhost` passes the guard and gets to its endpoint, and the OpenAPI description, which
is written from `OWN_SUFFIXES`, lists `.localhost`.

## The contract it breaks

- `core/openferment_core/guard.py:22-24`: "A host this service answers to: an IP address, a name with
  no dot, a `.local` name (Bonjour), a `.ts.net` name (Tailscale's names for the owner's devices), or
  one listed in OPENFERMENT_ALLOWED_HOSTS."
- That sentence disagrees with the code next to it, `core/openferment_core/guard.py:37`:
  `OWN_SUFFIXES = (".local", ".localhost", ".ts.net")`, and with the generated description in
  `docs/api/openapi.json` (`info.description`, from `core/openferment_core/api.py:200-206`): "a name
  ending `.local`, `.localhost` or `.ts.net`".
- `core/tests/test_openapi.py:53` checks the OpenAPI description against `guard.OWN_SUFFIXES` and
  calls that list "every name the guard admits, as guard.py lists"; the prose list in guard.py names
  two of its three suffixes.

## Command

```
bash bughunt/repro/H10-05/run.sh
```

The script makes a fresh database `bh_r_h10_05_svc`, starts the service keyless on 127.0.0.1:9470 and
makes project `r1`. It sends `POST /api/biorepo/check` with body `{}` three times, under `Host`
`evil.localhost:9470`, `evil.local:9470` and `evil.example.com:9470`, each with an `Origin` naming the
same host and port. It then reads, with `ast` and without importing anything, the module docstring
and `OWN_SUFFIXES` from guard.py, and `info.description` from `docs/api/openapi.json`, and checks each
suffix against both texts. Last, it stops the service and drops the database.

## Expected

The docstring's list of hosts this service answers to names every suffix in `OWN_SUFFIXES`, the set
the guard admits: `.local`, `.localhost` and `.ts.net`. api.py's description already names all three
in `openapi.json`.

## Observed (run1.log, run2.log)

- `Host: evil.localhost:9470` gets 422 from the endpoint's body validation (`"loc":["body","status"]`
  ... "Field required"), so the guard let it through. `evil.local` also gets 422. The control,
  `evil.example.com`, gets 403 `{"detail":"this service does not answer to 'evil.example.com'. Add the
  name to OPENFERMENT_ALLOWED_HOSTS if it is yours"}`.
- `OWN_SUFFIXES = ('.local', '.localhost', '.ts.net')`.
- Which suffixes appear in guard.py's docstring: `{'.local': True, '.localhost': False, '.ts.net': True}`.
- Which suffixes appear in openapi.json's `info.description`: all three, "a name ending `.local`,
  `.localhost` or `.ts.net`".
- Both runs print RESULT: DEFECT. The two logs match line for line apart from the commit and the
  project's `createdAt`.

## Likely cause

`core/openferment_core/guard.py:22-24` is written by hand and lists two of the three suffixes in
`core/openferment_core/guard.py:37`. api.py's `_OWN_NAMES` (`core/openferment_core/api.py:200`) is
built from `OWN_SUFFIXES`, which keeps the generated description in step with the code.

The candidate gave a cause that does not hold. It said the docstring "was written before .localhost
joined OWN_SUFFIXES". Both arrived in one commit, `4b8d872` ("OF-BLD-012 §B.6: only the owner's own
pages may change anything"): that commit's `OWN_SUFFIXES` already reads `(".local", ".localhost",
".ts.net")` and its docstring already lists only `.local` and `.ts.net`. The docstring has left out
`.localhost` since it was first written.

Severity S4 (drift in a docstring). Admitting `.localhost` is safe. RFC 6761 reserves the name for
loopback and browsers resolve it there, so the docstring's next sentence ("a rebinding attack needs a
public domain whose DNS the attacker answers, and none of these is one") holds for it too. The fix is
one phrase in the docstring, a `.localhost` name (the loopback names RFC 6761 reserves).
