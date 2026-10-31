"""Postdoc (execution prompt §7.2, §4.8; ADR-008): the loop, its validator, the
conversation store and the routes.

    plan           the system prompt and the plan schema the loop answers in, and the
                   shape evidence takes in a tool's result
    conversations  conversations, turns and their tool calls, kept under the project: a
                   follow-up reads its history from here, and each turn names the tool
                   calls it made and the artifacts they produced

The bounded loop itself is `postdoc_agent.py` and its validator `validate.py`, beside this
package until their imports keep its row of §7.2 (test_boundaries.py). Postdoc imports the
tool registry, the model client, the spend ledger and the store, and the project, provenance
and event modules a turn is kept and said with (test_boundaries.py names each).
"""
from .plan import MAX_TOKENS, SYSTEM, TOOL  # noqa: F401  (the plan the loop answers in)
