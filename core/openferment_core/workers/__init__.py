"""Heavy libraries run in workers (OF-BLD-014 §3.4, E.6).

A worker is a separate Python process that reads one JSON request per line on
stdin and writes one JSON response per line on stdout:

    in   {"id": 1, "op": "ping", "args": {}}
    out  {"id": 1, "ok": true, "result": {...}, "ms": 0}
    out  {"id": 1, "ok": false, "error": "what went wrong, in words", "ms": 3}

`SimWorker` is the service's side: it starts the process on first use, keeps
it warm, sends one request at a time under a lock, kills and restarts it on a
timeout, and reports the tail of its stderr when it crashes. `serve` is the
worker's side: a loop over stdin that answers `ping` itself and dispatches
every other op to the module's handlers.

`cobra` is imported in the geneOS worker module alone, and `biosteam` in the
Proforma worker and `flowsheets/` alone (Part G, rule 8); `test_workers`
greps the package for both.
"""
from __future__ import annotations

import collections
import itertools
import json
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable

_CORE = Path(__file__).resolve().parent.parent.parent

# How long one request may take before the worker is killed, and how many
# stderr lines a crash report keeps. Software settings, conventions in E.1's
# sense; a worker that needs longer says so when it is constructed.
DEFAULT_TIMEOUT_S = 60.0
STDERR_LINES = 40


class WorkerError(RuntimeError):
    """The worker answered, and the answer was an error."""


class WorkerCrashed(RuntimeError):
    """The process ended or wrote something that is not a response. Carries
    the tail of its stderr."""

    def __init__(self, message: str, stderr_tail: str = ""):
        super().__init__(f"{message}\n{stderr_tail}".rstrip())
        self.stderr_tail = stderr_tail


class WorkerTimeout(RuntimeError):
    """No answer in time; the process was killed and the next call starts a
    new one."""


class SimWorker:
    def __init__(self, module: str, *, timeout_s: float = DEFAULT_TIMEOUT_S, python: str | None = None) -> None:
        self.module = module
        self.timeout_s = timeout_s
        self.python = python or sys.executable
        self._proc: subprocess.Popen[str] | None = None
        self._out: queue.Queue[str | None] = queue.Queue()
        self._err: collections.deque[str] = collections.deque(maxlen=STDERR_LINES)
        self._ids = itertools.count(1)
        self._lock = threading.Lock()
        self.starts = 0

    # ── the process ────────────────────────────────────────────────────

    @property
    def alive(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def _start(self) -> None:
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(p for p in (str(_CORE), env.get("PYTHONPATH", "")) if p)
        env["PYTHONUNBUFFERED"] = "1"
        self._out = queue.Queue()
        self._err = collections.deque(maxlen=STDERR_LINES)
        self._proc = subprocess.Popen(
            [self.python, "-m", self.module],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
            cwd=str(_CORE),
            env=env,
        )
        self.starts += 1
        proc, out, err = self._proc, self._out, self._err

        def read_out() -> None:
            assert proc.stdout is not None
            for line in proc.stdout:
                out.put(line)
            out.put(None)  # end of stream: the process is gone

        def read_err() -> None:
            assert proc.stderr is not None
            for line in proc.stderr:
                err.append(line.rstrip("\n"))

        threading.Thread(target=read_out, daemon=True).start()
        threading.Thread(target=read_err, daemon=True).start()

    def _kill(self) -> None:
        proc, self._proc = self._proc, None
        if proc is None:
            return
        try:
            proc.kill()
            proc.wait(timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            pass

    def _tail(self) -> str:
        # Give the stderr reader a moment to catch the last lines of a crash.
        time.sleep(0.05)
        return "\n".join(self._err)

    def close(self) -> None:
        with self._lock:
            self._kill()

    # ── one request ────────────────────────────────────────────────────

    def call(self, op: str, args: dict[str, Any] | None = None, *, timeout_s: float | None = None) -> Any:
        with self._lock:
            if not self.alive:
                self._kill()
                self._start()
            assert self._proc is not None and self._proc.stdin is not None
            rid = next(self._ids)
            try:
                self._proc.stdin.write(json.dumps({"id": rid, "op": op, "args": args or {}}) + "\n")
                self._proc.stdin.flush()
            except (BrokenPipeError, OSError):
                tail = self._tail()
                self._kill()
                raise WorkerCrashed(f"{self.module} could not be sent {op!r}: the process had ended", tail) from None
            deadline = time.monotonic() + (timeout_s if timeout_s is not None else self.timeout_s)
            while True:
                left = deadline - time.monotonic()
                try:
                    line = self._out.get(timeout=max(left, 0.0)) if left > 0 else self._out.get_nowait()
                except queue.Empty:
                    self._kill()
                    raise WorkerTimeout(
                        f"{self.module} gave no answer to {op!r} in {timeout_s or self.timeout_s:g} s; it was stopped "
                        "and the next call starts it again"
                    ) from None
                if line is None:
                    tail = self._tail()
                    self._kill()
                    raise WorkerCrashed(f"{self.module} ended while answering {op!r}", tail)
                try:
                    response = json.loads(line)
                except ValueError:
                    tail = self._tail()
                    self._kill()
                    raise WorkerCrashed(f"{self.module} wrote a line that is not a response: {line[:200]!r}", tail) from None
                if not isinstance(response, dict) or response.get("id") != rid:
                    continue  # not this request's answer
                if response.get("ok"):
                    return response.get("result")
                raise WorkerError(str(response.get("error") or f"{self.module} failed {op!r} without saying why"))

    def ping(self, *, timeout_s: float | None = None) -> Any:
        return self.call("ping", timeout_s=timeout_s)


# ── the worker's side ──────────────────────────────────────────────────

Handler = Callable[[dict[str, Any]], Any]


def serve(handlers: dict[str, Handler], *, name: str = "worker", stdin=None, stdout=None) -> None:
    """Answer requests on stdin until it closes. `ping` is answered here; an
    unknown op, a handler that raises, or a result JSON cannot hold is an
    error response, and the loop goes on.

    Only responses reach the stream. Run as a process (`stdout` not given),
    the responses go out on a duplicate of file descriptor 1, and descriptor
    1 itself is pointed at stderr, so a library that prints, from Python or
    from C (a solver's banner), writes to stderr (§3.R)."""
    stdin = stdin or sys.stdin
    if stdout is None:
        sys.stdout.flush()
        out = os.fdopen(os.dup(1), "w", encoding="utf-8", buffering=1)
        os.dup2(2, 1)
        sys.stdout = sys.stderr
    else:
        out = stdout
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        started = time.perf_counter()
        rid: Any = None
        try:
            request = json.loads(line)
            rid = request.get("id")
            op = request.get("op")
            args = request.get("args") or {}
            if op == "ping":
                result: Any = {"worker": name, "pid": os.getpid()}
            elif op in handlers:
                saved, sys.stdout = sys.stdout, sys.stderr
                try:
                    result = handlers[op](args)
                finally:
                    sys.stdout = saved
            else:
                raise KeyError(f"{name} has no op {op!r}")
            body = {"id": rid, "ok": True, "result": result}
            body["ms"] = int(round((time.perf_counter() - started) * 1000))
            text = json.dumps(body, allow_nan=False)
        except Exception as e:  # said to the caller, and the loop goes on
            body = {"id": rid, "ok": False, "error": f"{type(e).__name__}: {e}"}
            body["ms"] = int(round((time.perf_counter() - started) * 1000))
            text = json.dumps(body)
        out.write(text + "\n")
        out.flush()
