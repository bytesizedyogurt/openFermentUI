"""`python -m openferment_core.flowsheets.recipes environment`: each recipe's
environment.yaml written from core/uv.lock."""
import sys

from . import main

sys.exit(main(sys.argv[1:]))
