"""A worker for the tests (OF-BLD-014 §3.4). It echoes, sleeps on request and
exits on request, so start, timeout, crash and restart are each exercised.
It computes nothing.
"""
from __future__ import annotations

import os
import sys
import time

from . import serve


def _echo(args):
    return args


def _sleep(args):
    time.sleep(float(args.get("seconds", 0)))
    return {"slept": True}


def _exit(args):
    print(str(args.get("say", "")), file=sys.stderr, flush=True)
    os._exit(int(args.get("code", 1)))


def _fail(args):
    raise ValueError(str(args.get("why", "asked to fail")))


def _chatter(args):
    # A library printing to stdout must not corrupt the stream.
    print("noise a library printed")
    return {"quiet": True}


def _cwrite(args):
    # A C library writes to file descriptor 1 directly, past sys.stdout.
    os.write(1, b"a solver banner written to fd 1\n")
    return {"quiet": True}


def _unserialisable(args):
    return {"a set": {1, 2}}


if __name__ == "__main__":
    serve(
        {
            "echo": _echo,
            "sleep": _sleep,
            "exit": _exit,
            "fail": _fail,
            "chatter": _chatter,
            "cwrite": _cwrite,
            "unserialisable": _unserialisable,
        },
        name="echo",
    )
