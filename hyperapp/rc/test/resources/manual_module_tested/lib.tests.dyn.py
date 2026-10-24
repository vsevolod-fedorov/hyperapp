# Manual module lib is not compiled, so its uses are not recorded: it is tested as it is.
from .tested.code import lib


def test_fn():
    assert lib.fn() == 1
