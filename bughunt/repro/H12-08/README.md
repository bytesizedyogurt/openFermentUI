# H12-08: two rules of the key override are held by no test

**Statement.** Dropping `guard.key_refusal`'s Funnel rule passes the tests that hold the key override and the guard, since `test_key_override.py`'s one Funnel case is a POST that `guard.refusal` refuses first with a detail that also says "Funnel"; dropping `llm.request_key`'s strip-and-empty rule passes them too, since its one caller, the API's middleware, refuses a blank `X-OpenFerment-Key` before it reaches `request_key`.

**Contract.**
- `core/openferment_core/guard.py:95-99` (`key_refusal`): "never one through Tailscale Funnel from the public internet. Read or change alike, since a key spends."
- `core/openferment_core/llm.py:693-698` (`request_key`): "An empty key is none, and core/.env's serves."
- `core/tests/test_key_override.py:1-8` names this file as the one that holds the override (owner question 10); `CLAUDE.md` names it for the override too ("`core/tests/test_key_override.py`").

**Command.** From the repository root: `bash bughunt/repro/H12-08/run.sh`

The script makes its own worktree of 2047f5a under `$BH_WORK/H12-08/` and a fresh database `bh_r_h12_08_db`. The tests make their session databases under `bh_r_h12_08_t`. The script is keyless (the worktree carries no `core/.env`, and the stand-in clients make no call) and needs no service. It then runs four steps:

0. It probes the tree as it stands. The probe makes a project, sends `GET /api/audit` naming a key with `tailscale-funnel-request` and a `.ts.net` Host, and watches the middleware's own `request_key` call. It then calls `request_key('  ')` and `request_key('')`.
1. It applies M31 (`if FUNNEL in headers:` in `key_refusal` becomes `if False:`), runs the probe again and then the tests `test_key_override.py`, `test_request_guard.py` and `test_llm.py`.
2. It does the same with M28 (`_REQUEST_KEY.set((key or "").strip() or None)` becomes `_REQUEST_KEY.set(key)`).
3. As a control, it drops `guard.refusal`'s own Funnel rule, which `test_request_guard` holds. The same selection then fails, which shows the tests ran on the worktree's mutated code.

**Expected.** With either rule dropped, a test of the override fails: a GET naming a key through Funnel is answered 403, and `request_key('  ')` leaves `key_named()` False.

**Observed** (run1.log and run2.log, both `RESULT: DEFECT`).
- On the tree, the Funnel GET is 403 with "may not name a key", and `request_key('  ')` gives `key_named()=False`.
- With M31, the Funnel GET is answered 200. The middleware holds the key for the request and keeps a `key_override` audit row for `GET /api/audit`. The tests give `130 passed`.
- With M28, `request_key('  ')` and `request_key('')` each give `key_named()=True` and `_whose_key()` 'the key this request named'. The tests give `130 passed`.
- The control gives `1 failed, 129 passed`.

**Likely cause.**
- `core/tests/test_key_override.py:127-131` sends the Funnel case as `POST /api/ask`. The guard middleware (`core/openferment_core/api.py:457-463`) runs before the key middleware (`api.py:347-348`), and `guard.refusal` (`guard.py:113-114`) answers that POST 403 with "may not change anything" before `key_refusal` (`guard.py:100-101`) is reached. The test asserts only a 403 with "Funnel" in the detail, and both refusals carry that word. No test sends a read (GET) through Funnel naming a key, the one case where `key_refusal` alone stands.
- `request_key`'s blank rule (`llm.py:699`) is shadowed by `api.py:364-365`, which answers a blank header 422 first. `test_key_override.py:133-134` holds that 422, and no test calls `request_key` with an empty or blank key.

**Severity S4 (hollow test).** The code on the tree keeps both rules. The gap is in the tests: a regression in either rule would pass `test:core`.

**Beside the candidate.** While checking, I found that `test_key_override.py:131-132`'s hostile-host case is a POST as well, so `guard.refusal`'s host check refuses it first. I dropped `key_refusal`'s own host rule (`guard.py:103`, `if not answers_to(host):` becomes `if False:`) in a separate scratch worktree, and the same three files gave `130 passed`. `run.sh` does not include this check.
