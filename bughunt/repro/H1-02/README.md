# H1-02: an engine set aside for its name or a failed import leaves cobra in the service's process

**Statement.** An entry module that imports a worker library (cobra here) and is then set aside for
another reason (its object misnamed, or its import raising after the library came in) leaves that
library in the service's `sys.modules`, its words never name the library, and a later entry module that
imports the same library loads with no error.

**Contract.**

- `CLAUDE.md:41` (an R rule): "BioSTEAM, thermosteam, biorefineries, the vendored SFF toolkit and cobra
  run in worker processes (`core/openferment_core/workers/`), one JSON request a line; the service
  process imports none of them".
- `docs/api/engines.md:141-144`: "An entry module whose import brings into the service's process its
  worker module (or a module below it), a heavy module it declares, or one of `biosteam`,
  `thermosteam`, `biorefineries`, `pisces_sff` and `cobra` is set aside, those modules named."
- The registry's own account, `core/openferment_core/engine/registry.py:13-16`, holds the measure to
  engines "set aside for them": "an engine set aside for them has them taken out of `sys.modules`, so
  the next entry point's import is measured afresh". The two paths below fall outside that sentence,
  so the next entry point is measured against a `sys.modules` that already holds cobra.

**Command** (from the repository root): `bash bughunt/repro/H1-02/run.sh`

The script makes a fresh test database (`bh_r_h1_02_probe`) and runs four scenarios, each the service's
startup in one process: `probe.py` imports `openferment_core.api`, whose import runs discovery
(`api.py:196`, `_engines.found()`), over the head's own venv, read only. The three stand-in entry
modules in `standin/h1_02_standin/` reach the real entry-point group `openferment.engines` through a
dist-info the script writes in scratch and puts on `PYTHONPATH`; nothing is installed, patched or
built, and `PYTHONDONTWRITEBYTECODE=1` keeps the tree's bytes as they are. Keyless, no model call, no
port. The scratch files and the database go when it ends.

| scenario | entry points (in the group's name order) |
| --- | --- |
| alone (control) | `h1z-heavy-unseen`: imports cobra, otherwise well formed |
| a | `h1a-misnamed-heavy`: imports cobra, its object names itself `not-its-entry-name` |
| az | `h1a-misnamed-heavy`, then `h1z-heavy-unseen` |
| bz | `h1b-fails-heavy` (imports cobra, then raises `ImportError`), then `h1z-heavy-unseen` |

**Expected.** After discovery cobra stands outside the service's `sys.modules` in every scenario, and
`h1z-heavy-unseen` is set aside with cobra named in every scenario, as it is in the control.

**Observed** (run1.log and run2.log alike):

- alone: `h1z-heavy-unseen` set aside, "importing h1_02_standin.heavy_unseen:ENGINE imported cobra,
  cobra.core, ... which belong in its worker"; cobra out of `sys.modules` after discovery.
- a: `h1a-misnamed-heavy` set aside with words about its name alone; cobra and 67 modules below it stay
  in `sys.modules` after discovery.
- az: `h1z-heavy-unseen` LOADED, error `None`; cobra in `sys.modules` after discovery.
- bz: `h1b-fails-heavy` set aside as "could not be loaded: ImportError: ..."; `h1z-heavy-unseen`
  LOADED, error `None`; cobra in `sys.modules` after discovery.

Both runs print `RESULT: DEFECT`.

**Likely cause** (high confidence). `core/openferment_core/engine/registry.py:142-156`, in `_load`:
`before` is taken at 142; the failed-load return at 148 leaves whatever the import added; the count of
the added modules and their `sys.modules.pop` (152-156) run only under `if why is None:` (151), so an
entry point that `_why_not` refuses at 150 keeps its imports, as does one whose check raises (the
"could not be checked" return at 160). The next entry point's `before` then already holds cobra, and
`_imported_in_service` finds nothing new. A scratch worktree at 2047f5a with the worker-library modules
an import added popped on those two paths as well set `h1z-heavy-unseen` aside with cobra named in az
and bz, and left cobra out of `sys.modules` after discovery (a check made by hand, outside `run.sh`;
the worktree is removed).

**Severity** S3: an edge case that needs a broken engine package installed beside the service, with a
workaround (mend or uninstall the broken package and restart). Fix size small.
