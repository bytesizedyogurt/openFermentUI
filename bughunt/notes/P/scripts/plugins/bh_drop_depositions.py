"""A pytest plugin (hunt P, row 29 of the Paid table, fd17f32): the train engine's rests_on with the depositions
left out, to see whether the completeness test fails as the row says it does. Loaded with -p; it changes no file.
    PYTHONPATH=bughunt/notes/P/scripts/plugins pytest -p bh_drop_depositions tests/test_engines.py -k copy_holds
"""
import pytest


@pytest.fixture(autouse=True)
def _drop_depositions(monkeypatch):
    from openferment_core.pureos import engine as pe

    cls = next(v for v in vars(pe).values() if isinstance(v, type) and "rests_on" in vars(v))
    held = cls.rests_on

    def rests_on(self):
        got = dict(held(self))
        got.pop("depositions", None)
        return got

    monkeypatch.setattr(cls, "rests_on", rests_on)
    yield
