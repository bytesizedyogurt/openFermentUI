"""H13: `scripts/prove.py` run with two changes made at run time, in memory, for the hunt's rules:
its service listens on BH_PROVE_PORT (default 8931, inside the hunt's 8930-8939) where prove picks a
free port of the kernel's, and its database is named `bh_h13_proof_<hex>` where prove names it
`openferment_proof_<hex>`. Every other line of the proof runs as it is.

Usage (from a checkout's core/): uv run --frozen --all-extras python prove_bh.py ../scripts/prove.py <prove's args>
"""
import importlib.util
import os
import sys

path = sys.argv[1]
spec = importlib.util.spec_from_file_location("prove", path)
prove = importlib.util.module_from_spec(spec)
sys.modules["prove"] = prove
spec.loader.exec_module(prove)

prove.free_port = lambda: int(os.environ.get("BH_PROVE_PORT", "8931"))
_Proof = prove.Proof


def _named(*args, **kwargs):
    kwargs["database"] = kwargs["database"].replace("openferment_proof_", "bh_h13_proof_")
    return _Proof(*args, **kwargs)


prove.Proof = _named
sys.argv = [path, *sys.argv[2:]]
sys.exit(prove.main(sys.argv[1:]))
