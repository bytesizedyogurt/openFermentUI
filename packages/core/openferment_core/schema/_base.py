"""Conventions every schema module in this package follows.

Two decisions are worth stating once here rather than repeating in ten files.

**Field names are snake_case in Python and camelCase on the wire.** The
TypeScript this package generates has to read like TypeScript, and the Python has
to read like Python; an alias generator is what lets both be true without anybody
hand-maintaining a mapping. `populate_by_name` means a model can also be
constructed from its Python names, which is what the tests and the seed loader
do.

**Unknown fields are an error, not a shrug.** `extra='forbid'` is the whole
point of validating the corpus against these models: a field the model has never
heard of means either the corpus grew a concept the schema does not know, or a
name was misspelled somewhere. Both are things to find out about now rather than
after a silent drop. Where a real corpus instance fails to parse, the model is
wrong and the model gets fixed — never the data.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

__all__ = ["OFModel"]


class OFModel(BaseModel):
    """Base for every openFerment entity."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
        # The corpus is full of characters that matter: µ in µg, ⁻¹ in g L⁻¹, §
        # in a curation reference. Nothing here may normalise a string.
        str_strip_whitespace=False,
        # Validation on assignment so an invariant cannot be broken after
        # construction — a record whose provenance is edited to
        # 'industry-estimate' must stop being aggregatable at that moment, not at
        # the next reload.
        validate_assignment=True,
    )
