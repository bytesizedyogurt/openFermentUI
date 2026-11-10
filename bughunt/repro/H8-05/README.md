# H8-05: import-url answers 500 when a host's redirect carries a Location with a scheme and no host

**Statement.** A public host answering `POST /api/flowsheets/import-url`'s fetch with 302 and `Location: https:127.0.0.1/x` or `Location: javascript:alert(1)` makes the route answer `500 Internal Server Error` with no words, because httpx raises `httpx.InvalidURL` while it builds the redirect, and `InvalidURL` is no `httpx.HTTPError`, so neither `collectors._fetch` nor the route catches it.

## Contract

- `docs/api/sff.md:88-96`: "Each refusal is said in words a person reads: 413 for a file past the size; 422 for an address that is not https, that names a user or a password, or that names an address outside the public internet (a redirect to any of these included), ...; 502 when the host name could not be found, the host refused the connection, could not be reached, or was not read in time, or it answered an error; 503 when the worker could not check the file. The log keeps each failure's exception in its own words. A refused request keeps nothing."
- `core/openferment_core/literature/collectors.py:469-471`, `fetch_file`'s docstring: "Raises AddressRefused, TooLarge, HostFailed (the host could not be found, reached or read in time, or answered an error) or NetworkRefused, each in words."
- `core/openferment_core/api.py:996-1008`: the route's OpenAPI document lists 413, 422, 502 and 503 as its refusals, each "in words, nothing kept".

## Command

```
bash bughunt/repro/H8-05/run.sh
```

From the repository root. It makes a fresh test database `bh_r_h8_05_importurl` (migrated to head), runs `repro.py` with the repository's Python, keyless, and drops the database and its scratch directory on exit. `repro.py` drives the app in process through FastAPI's `TestClient`: it makes project `h8-05` through `POST /api/projects`, then posts three addresses to `POST /api/flowsheets/import-url`. The network is a stand-in: `httpx.AsyncHTTPTransport` is replaced in that process by a `MockTransport`, and `collectors._resolve` by a resolver that maps `public.test` to 93.184.216.34, a public address; every request the fetch made is listed in the output, so nothing leaves the machine. It then calls `collectors.fetch_file` through its own test seams (`transport`, `resolve`) to name the exception that escapes, and `run.sh` counts the project's `openferment.flowsheets` rows.

## Expected

Each malformed redirect is refused in words that name the address, 502 (the host answered something unreadable) or 422 (a redirect to an address that is not https), as the control redirect is: `https://public.test/to-http` redirecting to `http://public.test/x` answers 422 "https://public.test/to-http redirected to http://public.test/x, which is not an https address; a redirect is followed to another https address alone". Nothing kept.

## Observed (both runs)

- Control `/to-http` (Location `http://public.test/x`): 422 with the words above.
- `/bad-location` (Location `https:127.0.0.1/x`): `500 Internal Server Error`, body `Internal Server Error`.
- `/js-location` (Location `javascript:alert(1)`): `500 Internal Server Error`, body `Internal Server Error`.
- `collectors.fetch_file("https://public.test/bad-location", ...)` raises `httpx.InvalidURL: For absolute URLs, path must be empty or begin with '/'`; it is an `httpx.HTTPError`: False; it is one of `AddressRefused`, `TooLarge`, `HostFailed`, `NetworkRefused`: False.
- `openferment.flowsheets` rows in the project: 0, so nothing is kept; the break is in the answer's status and words.
- `RESULT: DEFECT` in `run1.log` and `run2.log`.

## Likely cause

- `core/.venv/lib/python3.13/site-packages/httpx/_client.py:532-533` (httpx 0.28.1): for a Location with a scheme and no host, `_redirect_url` calls `url.copy_with(host=request.url.host)`, which raises `InvalidURL` when the Location's path does not begin with `/` (`127.0.0.1/x`, `alert(1)`). The parse step above it (`:523-528`) turns `InvalidURL` into `RemoteProtocolError`; this second step has no such wrapping. `client.stream` builds `next_request` even with redirects off, so the raise happens inside `collectors.py:435` `async with client.stream("GET", at)`.
- `core/openferment_core/literature/collectors.py:445`: `except httpx.HTTPError` catches the fetch's failures alone, and `httpx.InvalidURL` derives from `Exception` directly.
- `core/openferment_core/api.py:1031-1036`: the route catches `TooLarge`, `AddressRefused`, `NetworkRefused` and `HostFailed` alone, so the `InvalidURL` reaches FastAPI as an unhandled exception and becomes a 500.

A small fix: catch `httpx.InvalidURL` beside `httpx.HTTPError` at `collectors.py:445` (or around reading `response.next_request`) and raise `HostFailed` ("the host redirected to an address that could not be read") so the route answers 502 in words.
