# H9-12: a 400-digit integer in a quantity's value makes tools.run raise

**Statement.** `study_scenario` with `values[].quantity.value` a 400-digit JSON integer raises `OverflowError` in `tools.numbers_in`, outside `tools.run`'s `try`, so `POST /api/tools/study_scenario` answers `500 Internal Server Error` with a traceback in the service log, and the MCP server answers `isError: true` with the text `Error executing tool study_scenario` and no reason.

**Contract.**
- `core/openferment_core/tools/__init__.py:501-503`, `run`: "Every refusal is a result with `error` set; nothing here raises."
- `core/openferment_core/api.py:2924`, `tools_run`: "A refusal is a result with `error` set; an unknown tool is a 404."
- `docs/TOOLS.md:896`: "A tool's refusal is its ToolResult with `error` set ... `is_error` stays false, and no `structured_content` is sent."

**Command.** From the repository root: `bash bughunt/repro/H9-12/run.sh`. It makes the test database `bh_r_h9_12_door` fresh, starts a keyless service on 127.0.0.1:10350, makes the project `h9-12`, and sends `study_scenario` two inputs, a `1e309` value (the control) and a 400-digit integer value, at three doors: `tools.run` in process (`direct_call.py`), the REST tool door, and the MCP server in its own process over raw JSON-RPC (`mcp_call.py`). It stops the service, drops the database and removes its data copy on exit. About 15 s; no model call.

**Expected.** The 400-digit integer is refused as the `1e309` control is: `tools.run` returns a ToolResult whose `error` says the value is no finite number ("... NaN or infinite, and a number a tool takes is finite; nothing ran"), the REST door answers 200 with that ToolResult, and MCP answers it as JSON with `isError` false.

**Observed (run1.log, run2.log).** The control is refused in words at all three doors. The 400-digit integer:
- `tools.run` raises `OverflowError: int too large to convert to float` at `tools/__init__.py:415 numbers_in`, reached from `tools/__init__.py:516 run`;
- REST: `Internal Server Error [500]`, the service log holding the traceback ending in `OverflowError`;
- MCP: `{"content": [{"text": "Error executing tool study_scenario"}], "isError": true}`, the reason on the server's stderr alone.

Both runs end `RESULT: DEFECT`.

**Likely cause.** `core/openferment_core/tools/__init__.py:415`, `if not math.isfinite(float(v)):`, converts a Python `int` past a float's range, and `float()` raises. `non_finite_in` (`:425`) checks floats alone, so it passes a big integer through, and `run` calls `numbers_in` at `:516`, before the `try` at `:547` that turns an exception into a ToolResult. Confidence high. A small fix: treat an `int` whose `float()` overflows as non-finite; `non_finite_in` could refuse it too, so it gets the NaN-and-infinity refusal's words.

**Severity.** S3: an edge input a caller can avoid (any value within a float's range is refused or taken in words); the door answers with no words, and over MCP the client learns nothing of why.
