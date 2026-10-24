from .tested.code import module_1
from .code import helper

# Imported function is called at import time, so the first import attempt is incomplete,
# not getting to the tested import below: module_2 is not decided to be tested by this test module.
VALUE = helper.value()

from .tested.code import module_2


def test_fn():
    assert module_1.fn_1() * 2 == module_2.fn_2()
