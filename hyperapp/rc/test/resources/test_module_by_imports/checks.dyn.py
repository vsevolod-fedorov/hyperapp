# Has a tested code import, so is a test module, though not named with tests suffix.
from .tested.code import module_1


def test_fn_1():
    assert module_1.fn_1() == 111
