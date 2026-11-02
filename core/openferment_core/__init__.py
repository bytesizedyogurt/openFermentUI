"""openFerment's Python service layer.

Importing it writes Sci RAG Kit's settings into the environment first
(literature/__init__.py): the kit sizes its vector column when its models are
first imported, so they must never be imported before these are set.
"""
from . import literature as _literature  # noqa: F401
