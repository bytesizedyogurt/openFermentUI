"""An entry module that imports cobra, then fails to import."""
import cobra  # noqa: F401

raise ImportError("h1b fails after importing cobra")
