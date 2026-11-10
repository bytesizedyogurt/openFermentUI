"""H13: `python -m openferment_core.engine.conform <args>` with one change, made at run time and in
memory: the checks' own scratch database is named `bh_h13_conform_...` (the hunt's naming rule)
where the command names it `openferment_conform_...`. Every other line of the command runs as it is.

Usage (from a checkout's core/, its venv's python): python conform_bh.py <conform's own arguments>
"""
import sys

from openferment_core.engine import conform

conform.SCRATCH = "bh_h13_conform"
sys.exit(conform.main(sys.argv[1:]))
