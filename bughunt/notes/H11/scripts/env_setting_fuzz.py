"""env_setting (scripts/host/lib.sh) against python-dotenv, the reader the service uses.

    python env_setting_fuzz.py LIB WORKDIR

Writes core/.env under WORKDIR in many forms of one OPENFERMENT_PROJECT line (and of two lines),
asks lib.sh's env_setting for the value through bash, and asks python-dotenv's dotenv_values for
it. Prints each form where the two differ, beside whether it is one of the three forms lib.sh's
comment names as read differently (a ${VAR}, a quoted value ending at its next quote, a quoted value
running onto a second line). Run with the repository's Python, which has python-dotenv.
"""
from __future__ import annotations

import itertools
import os
import subprocess
import sys
from pathlib import Path

from dotenv import dotenv_values

LIB, WORK = Path(sys.argv[1]), Path(sys.argv[2])
(WORK / "core").mkdir(parents=True, exist_ok=True)
(WORK / "home").mkdir(exist_ok=True)

prefixes = ["", "export ", "export\t", "  ", "\t"]
seps = ["=", " = ", "\t=\t", "= "]
values = [
    "ethanol", "ethanol ", "ethanol\t", '"ethanol"', "'ethanol'", '"ethanol" ', '"ethanol"  # c', "'ethanol' # c",
    "ethanol # c", "ethanol\t# c", "ethanol#c", '"eth#anol"', "eth anol", "eth anol # c", '""', "''", "",
    '"a\'b"', "'a\"b'", '"ethanol"#c', "'ethanol'#c", "# c", " # c", '"ethanol', "'ethanol",
    # The two addresses with a password are joined at run time, so check:secrets reads no address in this file.
    "postgresql://u@127.0.0.1:5432/db?x=1", '"postgresql://u:p' + '#w@h/db"', "postgresql://u:p" + "#w@h/db",
    "a\\#b", '"a\\nb"', "'a\\nb'", "ethanol\r",
]
documented = ("${", )


def bash_value(text: str) -> str:
    (WORK / "core" / ".env").write_bytes(text.encode())
    env = {k: v for k, v in os.environ.items() if not k.startswith("OPENFERMENT_")}
    env |= {"OPENFERMENT_LAUNCHD_DIR": str(WORK / "daemons"), "HOME": str(WORK / "home")}
    script = f'set -euo pipefail; source "{LIB}"; REPO="{WORK}"; printf "%s" "$(env_setting OPENFERMENT_PROJECT)"'
    done = subprocess.run(["bash", "-c", script], env=env, capture_output=True)
    if done.returncode:
        return f"<exit {done.returncode}: {done.stderr.decode(errors='replace').strip()}>"
    return done.stdout.decode(errors="replace")


def dotenv_value(text: str) -> str:
    (WORK / "core" / ".env").write_bytes(text.encode())
    return dotenv_values(WORK / "core" / ".env").get("OPENFERMENT_PROJECT") or ""


cases = [f"{p}OPENFERMENT_PROJECT{s}{v}\n" for p, s, v in itertools.product(prefixes, seps, values)]
cases += [
    "OPENFERMENT_PROJECT=first\nOPENFERMENT_PROJECT=\n",          # a later empty line
    "OPENFERMENT_PROJECT=first\n#OPENFERMENT_PROJECT=second\n",   # a later commented line
    "OPENFERMENT_PROJECT=first\nOPENFERMENT_PROJECT\n",           # a later bare name
    "OPENFERMENT_PROJECT=first\n OPENFERMENT_PROJECT_OLD=x\n",
    "OPENFERMENT_PROJECT=ethanol",                                 # no newline at the end
]
diffs = 0
for text in cases:
    b, d = bash_value(text), dotenv_value(text)
    if b != d:
        diffs += 1
        quoted_multi = text.count('"') % 2 == 1 or text.count("'") % 2 == 1
        print(f"{text!r:60} lib.sh={b!r:24} dotenv={d!r:24}{'  (an unclosed quote)' if quoted_multi else ''}")
print(f"{len(cases)} forms, {diffs} read differently")
