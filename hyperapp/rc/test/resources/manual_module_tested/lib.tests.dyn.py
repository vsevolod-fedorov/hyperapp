# Manual module lib is not imported by a job, so there is nothing to record its uses.
from .tested.code import lib


def test_fn():
    assert lib.fn() == 1
