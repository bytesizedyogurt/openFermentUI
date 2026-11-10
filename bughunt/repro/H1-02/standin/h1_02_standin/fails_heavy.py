"""Imports cobra (a worker library), then raises: discovery sets it aside as one that could not be loaded."""
import cobra  # noqa: F401

raise ImportError("h1b-fails-heavy raises after importing cobra")
